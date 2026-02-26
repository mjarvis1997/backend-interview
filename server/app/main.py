import os
from contextlib import asynccontextmanager
from beanie import init_beanie
from dotenv import load_dotenv
from fastapi import FastAPI
from pymongo import AsyncMongoClient
from app.models.event import Event
from app.routers.tests import router as tests_router
from app.routers.events import router as events_router
from app.config.redis import pool

# Load environment variables from .env file
# In docker, we will set env vars directly, this is mainly for local development
load_dotenv()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Initialize the database connection and beanie on application startup."""

    # ***** Initialization code for setup here *****

    # Create Async PyMongo client
    client = AsyncMongoClient(os.getenv("MONGODB_URI", "foo"))

    # Init beanie with the Product document class
    await init_beanie(database=client.main, document_models=[Event])

    # Attach routers to app
    _app.include_router(tests_router)
    _app.include_router(events_router)

    yield
    # ***** Cleanup code for teardown here *****

    # Close redis connection pool
    pool.close()


# Initialize FastAPI app
app = FastAPI(lifespan=lifespan)
