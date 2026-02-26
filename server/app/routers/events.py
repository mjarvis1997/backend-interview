from fastapi import APIRouter
from app.models.event import Event
from app.dependencies.rq import enqueue_event_ingestion

router = APIRouter(prefix="/events")


@router.get("/")
async def get_events():
    events = await Event.find_all().to_list()
    return events


@router.post("/")
async def create_event(event: Event):
    job_id = enqueue_event_ingestion(event)
    return {
        "message": "Event ingestion enqueued",
        "job_id": job_id
    }
