import os
from typing import Annotated
from elasticsearch import AsyncElasticsearch
from fastapi import Depends

# Index name for all event documents
EVENTS_INDEX = "events"

# Index mapping for event documents.
# Field type choices:
#   - type, user_id, source_url: keyword — identifiers used for exact-match filtering,
#     tokenizing these would produce meaningless results
#   - timestamp: date — enables range queries and time-based sorting
#   - metadata: object with dynamic:true — flexible JSON payload, ES infers sub-field
#     types and all sub-fields are indexed for full-text search by default
EVENTS_INDEX_MAPPING = {
    "mappings": {
        "properties": {
            "type":       {"type": "keyword"},
            "timestamp":  {"type": "date"},
            "user_id":    {"type": "keyword"},
            "source_url": {"type": "keyword"},
            "metadata":   {"type": "object", "dynamic": True},
        }
    }
}


def get_elasticsearch_url() -> str:
    return os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")


def get_elasticsearch() -> AsyncElasticsearch:
    """Dependency function to get an AsyncElasticsearch client for FastAPI routes."""
    return AsyncElasticsearch(get_elasticsearch_url())


async def init_elasticsearch() -> None:
    """Create the events index with the defined mapping if it does not already exist.

    Called once during app startup. Safe to call on every startup — no-ops if the
    index already exists.
    """
    es = get_elasticsearch()
    try:
        exists = await es.indices.exists(index=EVENTS_INDEX)
        if not exists:
            await es.indices.create(index=EVENTS_INDEX, body=EVENTS_INDEX_MAPPING)
    finally:
        await es.close()


# Reusable dependency for FastAPI routes
DependsElasticsearch = Annotated[AsyncElasticsearch, Depends(
    get_elasticsearch)]
