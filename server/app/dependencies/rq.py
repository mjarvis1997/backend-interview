import time
from random import random
from dotenv import load_dotenv
from rq import Queue
from app.dependencies.redis import get_redis
from app.models.event import Event
from app.dependencies.database import init_database


# Initialize RQ queue with connection from redis pool
q = Queue(
    name="ingestion_queue",
    connection=get_redis()
)

# Global flag to track if database is initialized in this worker process
_DB_INITIALIZED = False


async def ingest_event(event_data: dict):
    """Async function to ingest an event - RQ will handle the event loop.

    Args:
        event_data: Dictionary containing event data (serializable)
    """
    # Load env vars
    load_dotenv()

    # Initialize database connection if not already done in this worker process
    global _DB_INITIALIZED
    if not _DB_INITIALIZED:
        await init_database()
        _DB_INITIALIZED = True

    # Simulate some processing time randomly between 0.1 and 1 second
    simulated_delay = 0.1 + (0.9 * random())
    time.sleep(simulated_delay)

    # Create and insert the event
    event = Event(**event_data)
    await event.insert()
    return str(event.id)


def enqueue_event_ingestion(event: Event):
    """Helper function to enqueue a task to the RQ queue.

    This function must be sync (per RQ requirements) even when called from async context.
    """
    # Convert Pydantic model to dict for serialization
    event_data = event.model_dump()
    job = q.enqueue(ingest_event, event_data)
    return job.id
