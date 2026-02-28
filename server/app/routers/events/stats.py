from typing import Optional, Literal
from fastapi import APIRouter, Query
from app.models.event import Event
from app.helpers.date import dt_from_iso


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
    start_date: Optional[str] = Query(
        None, description="Filter events after this date (ISO format)"),
    end_date: Optional[str] = Query(
        None, description="Filter events before this date (ISO format)"),
    time_bucket: Optional[Literal['hourly', 'daily', 'weekly']] = Query(
        "daily", description="Time bucket for grouping stats (hourly, daily, weekly)")
):
    """Get event statistics using MongoDB aggregation pipeline."""
    query = build_stats_query(start_date, end_date, time_bucket)

    stats = await Event.aggregate(query).to_list()

    return stats


@router.get("/stats/realtime")
async def get_realtime_stats():
    """Get lightweight real-time stats from Redis cache.

    TODO: Implement Redis caching with configurable TTL.
    """
    return {"message": "Realtime stats endpoint - TODO: implement Redis caching"}
