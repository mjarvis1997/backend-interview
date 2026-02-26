from fastapi import APIRouter
from app.models.event import Event

router = APIRouter(prefix="/events")


@router.get("/")
async def get_events():
    events = await Event.find_all().to_list()
    return events


@router.post("/")
async def create_event(event: Event):
    await event.insert()
    return event
