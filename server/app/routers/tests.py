from datetime import datetime
from fastapi import APIRouter, Depends
from redis import Redis
from typing import Annotated
from app.models.event import Event
from app.config.redis import get_redis


router = APIRouter(prefix="/tests")

# Basic test endpoint to verify the server is running


@router.get("/")
async def root():
    return {"message": "Hello World"}


@router.get("/create-event")
async def create_event_test():
    """Test endpoint to create a sample event in the database."""
    event = Event(
        type="click",
        timestamp=datetime(2026, 2, 23),
        user_id=123,
        source_url="http://example.com",
        metadata={"key": "value"}
    )
    await event.insert()
    return {"message": "Event created"}


@router.get("/delete-events")
async def delete_events_test():
    await Event.delete_all()
    return {"message": "All events deleted"}


@router.get("/redis")
async def redis_test(r: Annotated[Redis, Depends(get_redis)]):
    r.set("test_key", "Hello Redis!")
    value = r.get("test_key")
    return {"message": value}
