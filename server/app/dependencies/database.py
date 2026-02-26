"""Shared database initialization for FastAPI app and RQ workers."""
import os
from pymongo import AsyncMongoClient
from beanie import init_beanie
from app.models.event import Event


async def init_database():
    """Initialize database connection and Beanie. Used by both FastAPI and workers."""
    client = AsyncMongoClient(
        os.getenv("MONGODB_URI", "mongodb://root:example@localhost:27017/"))
    await init_beanie(database=client.main, document_models=[Event])
    return client
