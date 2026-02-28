import os
from random import random
from dotenv import load_dotenv
from rq import Queue, Retry
from app.dependencies.redis import get_redis
from app.models.event import Event
from app.dependencies.database import init_database
from app.dependencies.elasticsearch import get_elasticsearch, EVENTS_INDEX


# Initialize RQ queue with connection from redis pool
q = Queue(
    name="ingestion_queue",
    connection=get_redis()
)

# Global flag to track if database is initialized in this worker process
_DB_INITIALIZED = False


async def save_event_to_mongodb(event_data: dict) -> str:
    """Insert a single event document into MongoDB.

    Initializes the database connection on first call within this worker process.
    Returns the string representation of the inserted document's ID.
    """
    global _DB_INITIALIZED
    if not _DB_INITIALIZED:
        load_dotenv()
        await init_database()
        _DB_INITIALIZED = True

    event = Event(**event_data)
    await event.insert()
    return str(event.id)


async def index_event_in_elasticsearch(event_id: str, event_data: dict) -> None:
    """Index a single event document into Elasticsearch.

    Uses the MongoDB document ID as the ES document ID to keep both stores in sync
    and allow targeted updates or deletions later.
    """
    es = get_elasticsearch()
    try:
        print(f"Indexing event {event_id} into Elasticsearch")
        await es.index(
            index=EVENTS_INDEX,
            id=event_id,
            document=event_data,
        )
    finally:
        await es.close()


async def ingest_event(event_data: dict):
    """Async function to ingest an event - RQ will handle the event loop.

    Args:
        event_data: Dictionary containing event data (serializable)
    """
    # Randomly fail to simulate transient errors and trigger retries (10% failure rate)
    if random() < 0.1:
        raise Exception("Simulated transient error during event ingestion")

    event_id = await save_event_to_mongodb(event_data)
    await index_event_in_elasticsearch(event_id, event_data)

    return event_id


def enqueue_event_ingestion(event: Event):
    """Helper function to enqueue a task to the RQ queue.

    This function must be sync (per RQ requirements) even when called from async context.
    """
    # Convert Pydantic model to dict for serialization
    event_data = event.model_dump()
    job = q.enqueue(
        f=ingest_event,
        args=[event_data],
        retry=Retry(max=3, interval=[1, 5, 15])
    )

    return job.id
