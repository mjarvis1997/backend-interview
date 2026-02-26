"""Shared database initialization for FastAPI app and RQ workers."""
import os
import asyncio
from pymongo import AsyncMongoClient
from beanie import init_beanie
from app.models.event import Event


async def init_database():
    """Initialize database connection and Beanie. Used by both FastAPI and workers."""
    client = AsyncMongoClient(
        os.getenv("MONGODB_URI", "mongodb://root:example@localhost:27017/"))
    await init_beanie(database=client.main, document_models=[Event])

    return client


def sync_init_database():
    """Synchronous wrapper for database initialization in RQ workers."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(init_database())
    except Exception as e:
        print(f"Failed to initialize database: {e}")
        raise


async def async_insert_event(event_data: dict):
    """Async function to insert event into database."""
    event = Event(**event_data)
    await event.insert()
    return str(event.id)


def sync_insert_event(event_data: dict):
    """Synchronous wrapper for inserting event in RQ workers."""
    loop = asyncio.get_event_loop()
    if loop.is_running():
        # If we're in an existing event loop, create a new one for this thread
        new_loop = asyncio.new_event_loop()
        return new_loop.run_until_complete(async_insert_event(event_data))
    else:
        return loop.run_until_complete(async_insert_event(event_data))
