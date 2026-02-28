from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI
from app.routers.tests import router as tests_router
from app.routers.events import router as events_router
from app.dependencies.redis import queue_pool, cache_pool
from app.dependencies.database import init_database
from app.dependencies.elasticsearch import init_elasticsearch

# Load environment variables from .env file
# In docker, we will set env vars directly, this is mainly for local development
load_dotenv()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Initialize the database connection and beanie on application startup."""

    # ***** Initialization code for setup here *****

    await init_database()
    await init_elasticsearch()

    # Attach routers to app
    _app.include_router(tests_router)
    _app.include_router(events_router)

    yield
    # ***** Cleanup code for teardown here *****

    # Close redis connection pools
    queue_pool.close()
    cache_pool.close()


# Initialize FastAPI app
app = FastAPI(lifespan=lifespan)
