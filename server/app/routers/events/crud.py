from typing import Optional
from fastapi import APIRouter, Query
from app.models.event import Event
from app.dependencies.rq import enqueue_event_ingestion
from app.helpers.date import dt_from_iso

router = APIRouter()


def build_event_query(
    event_type: Optional[str],
    start_date: Optional[str],
    end_date: Optional[str],
    user_id: Optional[str],
    source_url: Optional[str]
):
    """Helper function to build the event query with optional filters."""
    query = Event.find()

    if event_type:
        query = query.find(Event.type == event_type)

    if user_id:
        query = query.find(Event.user_id == user_id)

    if source_url:
        query = query.find(Event.source_url == source_url)

    if start_date:
        query = query.find(Event.timestamp >= dt_from_iso(start_date))

    if end_date:
        query = query.find(Event.timestamp <= dt_from_iso(end_date))

    return query


@router.get("/")
async def get_events(
    event_type: Optional[str] = Query(
        None, description="Filter by event type"),
    start_date: Optional[str] = Query(
        None, description="Filter events after this date (ISO format)"),
    end_date: Optional[str] = Query(
        None, description="Filter events before this date (ISO format)"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    source_url: Optional[str] = Query(None, description="Filter by source URL")
):
    """Get events with optional filtering by type, date range, user ID, or source URL."""

    query = build_event_query(
        event_type,
        start_date,
        end_date,
        user_id,
        source_url
    )

    events = await query.to_list()
    return events


@router.post("/")
async def create_event(event: Event):
    job_id = enqueue_event_ingestion(event)
    return {
        "message": "Event ingestion enqueued",
        "job_id": job_id
    }
