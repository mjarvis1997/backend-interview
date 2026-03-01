import os
from typing import Optional, Literal
import json
from datetime import datetime, timedelta
from fastapi import APIRouter, Query
from app.models.event import Event
from app.helpers.date import dt_from_iso
from app.dependencies.redis import DependsCacheRedis, generate_cache_key

TimeBucket = Literal['hourly', 'daily', 'weekly']

# Reused constants for cache TTL settings
ONE_HOUR_IN_SECONDS = 3600
REALTIME_STATS_CACHE_KEY = generate_cache_key("realtime-stats")

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

    time_range_start = None
    if time_bucket == "hourly":
        time_range_start = {
            "$dateTrunc": {
                "date": "$timestamp",
                "unit": "hour"
            }
        }
    elif time_bucket == "daily":
        time_range_start = {
            "$dateTrunc": {
                "date": "$timestamp",
                "unit": "day"
            }
        }
    elif time_bucket == "weekly":
        # Return the start date of the week (Monday) instead of week number
        time_range_start = {
            "$dateTrunc": {
                "date": "$timestamp",
                "unit": "week",
                "startOfWeek": "monday"
            }
        }

    pipeline = []

    # Only add match stage if we have date filters to apply
    if match_stage:
        pipeline.append({"$match": match_stage})

    # Group by both time bucket and event type, count events in each combination
    pipeline.append({
        "$group": {
            "_id": {
                "time_range_start": time_range_start,
                "type": "$type"
            },
            "count": {"$sum": 1}
        }
    })

    # Sort by time bucket in descending order (most recent first), then by event type
    pipeline.append(
        {"$sort": {"_id.time_range_start": -1, "_id.event_type": 1}})

    return pipeline


@router.get("/stats")
async def get_event_stats(
    start_date: Optional[str] = Query(
        None, description="Filter events after this date (ISO format)"),
    end_date: Optional[str] = Query(
        None, description="Filter events before this date (ISO format)"),
    time_bucket: Optional[Literal['hourly', 'daily', 'weekly']] = Query(
        "daily", description="Time bucket for grouping stats (hourly, daily, weekly)"),
):
    """Get event statistics using MongoDB aggregation pipeline with Redis caching."""

    query = build_stats_query(start_date, end_date, time_bucket)
    stats = await Event.aggregate(query).to_list()

    return stats


@router.get("/stats/realtime")
async def get_realtime_stats(
    cache: DependsCacheRedis,
):
    """Get lightweight real-time stats.

    This is a static endpoint intended for convenient analytics use.
    It always returns a daily count of events from the past month.

    The results are cached in Redis under a fixed key to ensure fast response times
    for repeated requests, with a TTL that can be configured via environment variable.
    """

    # Try to get result from cache
    cached_result = cache.get(REALTIME_STATS_CACHE_KEY)

    if cached_result:
        return {
            "cached": True,
            "data": json.loads(cached_result)  # type: ignore
        }

    # If not in cache, run the aggregation query
    # get iso date for 30 days ago
    seven_days_ago = datetime.now() - timedelta(days=7)
    query = build_stats_query(seven_days_ago.isoformat(), None, "hourly")
    stats = await Event.aggregate(query).to_list()

    # Determine cache TTL based on environment var
    cache_ttl_setting = os.getenv("REALTIME_STATS_CACHE_TTL_MINUTES", "60")
    cache_ttl_seconds = int(cache_ttl_setting) * 60

    # Store result in cache for future use
    if stats is not None:
        cache.set(
            name=REALTIME_STATS_CACHE_KEY,
            value=json.dumps(stats, default=str),
            ex=cache_ttl_seconds
        )

    return {
        "cached": False,
        "data": stats
    }


@router.delete("/stats/cache")
async def clear_stats_cache(cache: DependsCacheRedis):
    """Clear all cached event stats in Redis.
    This is a destructive operation intended for testing."""

    cache.flushdb()
    return {"message": "Cleared cached stats entries from Redis"}
