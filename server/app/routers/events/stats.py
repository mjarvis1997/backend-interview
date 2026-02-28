import os
from typing import Optional, Literal
import json
from datetime import datetime, timedelta
from fastapi import APIRouter, Query
from app.models.event import Event
from app.helpers.date import dt_from_iso
from app.dependencies.redis import DependsCacheRedis, generate_cache_key


router = APIRouter()

ONE_HOUR_IN_SECONDS = 3600

TimeBucket = Literal['hourly', 'daily', 'weekly']


def get_cache_ttl(time_bucket: Optional[TimeBucket]) -> int:
    """Determine cache TTL based on time bucket granularity."""

    # Cache daily stats for 6 hours
    if time_bucket == "daily":
        return ONE_HOUR_IN_SECONDS * 6

    # Cache weekly stats for 24 hours
    if time_bucket == "weekly":
        return ONE_HOUR_IN_SECONDS * 24

    # By default, cache stats for 1 hour
    return ONE_HOUR_IN_SECONDS * 6


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
        return {
            "cached": True,
            "data": json.loads(cached_result)  # type: ignore
        }

    # If not in cache, run the aggregation query
    query = build_stats_query(start_date, end_date, time_bucket)
    stats = await Event.aggregate(query).to_list()

    # Store result in cache for future use
    # Check if stats are valid before caching (e.g. not None or empty)
    if stats is not None:
        cache.set(
            name="cache_key",
            value=json.dumps(stats, default=str),
            ex=get_cache_ttl(time_bucket)
        )

    return {
        "cached": False,
        "data": stats
    }


@router.get("/stats/realtime")
async def get_realtime_stats(
    cache: DependsCacheRedis,
):
    """Get lightweight real-time stats.

    This is a non-configurable endpoint intended for convenient analytics use.
    It always returns a daily count of events from the past month.

    Cache entries live for 6 hours to 
    """

    # Generate cache key from query parameters
    cache_key = generate_cache_key("realtime", "daily")

    # Try to get result from cache
    cached_result = cache.get(cache_key)

    if cached_result:
        return {
            "cached": True,
            "data": json.loads(cached_result)  # type: ignore
        }

    # If not in cache, run the aggregation query
    # get iso date for 30 days ago
    one_month_ago = datetime.now() - timedelta(days=30)
    query = build_stats_query(one_month_ago.isoformat(), None, "daily")
    stats = await Event.aggregate(query).to_list()

    # Determine cache TTL based on environment var
    cache_ttl_setting = os.getenv("REALTIME_STATS_CACHE_TTL_MINUTES", "60")
    cache_ttl_seconds = int(cache_ttl_setting) * 60

    # Store result in cache for future use
    if stats is not None:
        cache.set(
            name=cache_key,
            value=json.dumps(stats, default=str),
            ex=cache_ttl_seconds
        )

    return {
        "cached": False,
        "data": stats
    }
