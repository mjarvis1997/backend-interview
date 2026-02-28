from typing import Optional, Literal
import json
from fastapi import APIRouter, Query
from app.models.event import Event
from app.helpers.date import dt_from_iso
from app.dependencies.redis import DependsCacheRedis, generate_cache_key


router = APIRouter()


def build_stats_query(
    start_date: Optional[str],
    end_date: Optional[str],
    time_bucket: Optional[Literal['hourly', 'daily', 'weekly']]
):
    """Helper function to build the MongoDB aggregation pipeline for stats."""
    match_stage = {}
    if start_date:
        match_stage["timestamp"] = {"$gte": dt_from_iso(start_date)}
    if end_date:
        match_stage.setdefault("timestamp", {})["$lte"] = dt_from_iso(end_date)

    group_id = None
    if time_bucket == "hourly":
        group_id = {
            "$dateTrunc": {
                "date": "$timestamp",
                "unit": "hour"
            }
        }
    elif time_bucket == "daily":
        group_id = {
            "$dateTrunc": {
                "date": "$timestamp",
                "unit": "day"
            }
        }
    elif time_bucket == "weekly":
        # Return the start date of the week (Monday) instead of week number
        group_id = {
            "$dateTrunc": {
                "date": "$timestamp",
                "unit": "week",
                "startOfWeek": "monday"
            }
        }

    # throw error if invalid time_bucket value
    if time_bucket and not group_id:
        raise ValueError(
            "Invalid time_bucket value. Must be 'hourly', 'daily', or 'weekly'.")

    pipeline = []

    # Only add match stage if we have date filters to apply
    if match_stage:
        pipeline.append({"$match": match_stage})

    # Group by the specified time bucket and count events in each bucket
    pipeline.append({
        "$group": {
            "_id": group_id,
            "count": {"$sum": 1}
        }
    })

    # Sort by timestamp grouping in descending order (most recent first)
    pipeline.append({"$sort": {"_id": -1}})

    return pipeline


@router.get("/stats")
async def get_event_stats(
    cache: DependsCacheRedis,
    start_date: Optional[str] = Query(
        None, description="Filter events after this date (ISO format)"),
    end_date: Optional[str] = Query(
        None, description="Filter events before this date (ISO format)"),
    time_bucket: Optional[Literal['hourly', 'daily', 'weekly']] = Query(
        "daily", description="Time bucket for grouping stats (hourly, daily, weekly)"),
):
    """Get event statistics using MongoDB aggregation pipeline with Redis caching."""

    # Generate cache key from query parameters
    cache_key = generate_cache_key(start_date, end_date, time_bucket)

    # Try to get result from cache first
    cached_result = cache.get(cache_key)
    if cached_result:
        print("Cache hit for key:", cache_key)
        # TODO: return json.loads(cached_result)  # type: ignore

    # If not in cache, run the aggregation query
    query = build_stats_query(start_date, end_date, time_bucket)
    stats = await Event.aggregate(query).to_list()

    # Store result in cache for future use
    cache.set(cache_key, json.dumps(stats, default=str))

    return stats


@router.get("/stats/realtime")
async def get_realtime_stats(
    cache: DependsCacheRedis,
    start_date: Optional[str] = Query(
        None, description="Filter events after this date (ISO format)"),
    end_date: Optional[str] = Query(
        None, description="Filter events before this date (ISO format)"),
    time_bucket: Optional[Literal['hourly', 'daily', 'weekly']] = Query(
        "daily", description="Time bucket for grouping stats (hourly, daily, weekly)"),
):
    """Get lightweight real-time stats served from Redis cache only.

    This endpoint only returns cached results - if no cache exists, returns empty result.
    Use the main /stats endpoint to populate the cache.
    """

    # Generate cache key from query parameters
    cache_key = generate_cache_key(start_date, end_date, time_bucket)

    # Try to get result from cache
    cached_result = cache.get(cache_key)
    if cached_result:
        return {
            "cached": True,
            "data": json.loads(cached_result)  # type: ignore
        }

    return {
        "cached": False,
        "data": [],
        "message": "No cached data available. Call /events/stats first to populate cache."
    }
