import time
from random import random
from rq import Queue
from app.dependencies.redis import get_redis
from app.models.event import Event
from app.core.database import sync_init_database, sync_insert_event
from dotenv import load_dotenv


q = Queue(
    name="ingestion_queue",
    connection=get_redis()
)

# Global flag to track if database is initialized in this worker process
_db_initialized = False


def ingest_event(event_data: dict):
    """Synchronous function to ingest an event, runs on each task in the queue.

    Args:
        event_data: Dictionary containing event data (serializable)
    """

    # Load env vars
    load_dotenv()

    # Initialize database connection if not already done in this worker process
    global _db_initialized
    if not _db_initialized:
        sync_init_database()
        _db_initialized = True

    # Simulate some processing time randomly between 0.1 and 1 second
    simulated_delay = 0.1 + (0.9 * random())
    time.sleep(simulated_delay)

    # Actually ingest the event into mongo - let RQ handle exceptions
    event_id = sync_insert_event(event_data)
    return event_id


def enqueue_event_ingestion(event: Event):
    """Helper function to enqueue a task to the RQ queue."""
    # Convert Pydantic model to dict for serialization
    event_data = event.model_dump()
    job = q.enqueue(ingest_event, event_data)
    return job.id
