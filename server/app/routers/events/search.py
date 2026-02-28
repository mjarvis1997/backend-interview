from fastapi import APIRouter

router = APIRouter()


@router.get("/search")
async def search_events():
    """Full-text search across event metadata using Elasticsearch.

    TODO: Implement Elasticsearch full-text search functionality.
    """
    return {"message": "Search endpoint - TODO: implement Elasticsearch integration"}
