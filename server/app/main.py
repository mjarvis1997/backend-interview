from fastapi import FastAPI
from pymongo import AsyncMongoClient
from beanie import init_beanie
from app.models import Event

app = FastAPI()


@app.on_event("startup")
async def app_init():
    """Initialize the database connection and beanie on application startup."""

    # Create Async PyMongo client
    client = AsyncMongoClient("mongodb://user:pass@host:27017")

    # Init beanie with the Product document class
    await init_beanie(database=client.db_name, document_models=[Event])


@app.get("/")
async def root():
    return {"message": "Hello World"}
