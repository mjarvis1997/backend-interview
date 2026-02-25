from fastapi import FastAPI
from pymongo import AsyncMongoClient
from beanie import init_beanie
from app.models import Event

app = FastAPI()


@app.on_event("startup")
async def app_init():
    """Initialize the database connection and beanie on application startup."""

    # TODO: Move connection string to config or env
    # Create Async PyMongo client
    client = AsyncMongoClient("mongodb://root:example@localhost:27017")

    # Init beanie with the Product document class
    await init_beanie(database=client.main, document_models=[Event])


# Basic test endpoint to verify the server is running
@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/create_event_test")
async def create_event_test():
    """Test endpoint to create a sample event in the database."""
    event = Event(type="click", timestamp="1234567890", user_id=123,
                  source_url="http://example.com", metadata={"key": "value"})
    await event.insert()
    return {"message": "Event created"}
