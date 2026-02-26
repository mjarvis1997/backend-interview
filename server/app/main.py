from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI
from app.routers.tests import router as tests_router
from app.routers.events import router as events_router
from app.dependencies.redis import pool
from app.dependencies.database import init_database

# Load environment variables from .env file
# In docker, we will set env vars directly, this is mainly for local development
load_dotenv()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Initialize the database connection and beanie on application startup."""

    # ***** Initialization code for setup here *****

    await init_database()

    # Attach routers to app
    _app.include_router(tests_router)
    _app.include_router(events_router)

    yield
    # ***** Cleanup code for teardown here *****

    # Close redis connection pool
    pool.close()


# Initialize FastAPI app
app = FastAPI(lifespan=lifespan)
