from typing import Optional
from fastapi import APIRouter, Query
from app.dependencies.elasticsearch import DependsElasticsearch, EVENTS_INDEX
from app.helpers.date import dt_from_iso

router = APIRouter()


def build_search_query(
    q: str,
    event_type: Optional[str],
    user_id: Optional[str],
    start_date: Optional[str],
    end_date: Optional[str],
) -> dict:
    """Build an Elasticsearch bool query combining full-text search with structured filters.

    The `q` term is matched across all metadata sub-fields using multi_match.
    Structured fields (type, user_id, timestamp) are applied as filters — they
    do not affect relevance scoring and benefit from filter caching in ES.
    """
    filters = []

    if event_type:
        filters.append({"term": {"type": event_type}})

    if user_id:
        filters.append({"term": {"user_id": user_id}})

    if start_date or end_date:
        date_range: dict = {}
        if start_date:
            date_range["gte"] = dt_from_iso(start_date).isoformat()
        if end_date:
            date_range["lte"] = dt_from_iso(end_date).isoformat()
        filters.append({"range": {"timestamp": date_range}})

    query: dict = {
        "bool": {
            "must": {
                "multi_match": {
                    "query": q,
                    "fields": ["metadata.*"],
                }
            }
        }
    }

    if filters:
        query["bool"]["filter"] = filters

    return query


@router.get("/search")
async def search_events(
    es: DependsElasticsearch,
    q: str = Query(...,
                   description="Full-text search query against event metadata"),
    event_type: Optional[str] = Query(
        None, description="Filter by event type"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    start_date: Optional[str] = Query(
        None, description="Filter events after this date (ISO format)"),
    end_date: Optional[str] = Query(
        None, description="Filter events before this date (ISO format)"),
    size: int = Query(20, ge=1, le=100,
                      description="Number of results to return"),
):
    """Full-text search across event metadata using Elasticsearch.

    The `q` parameter is matched against all metadata sub-fields (browser, device, etc.).
    Optional filters narrow results by structured fields without affecting relevance scoring.
    """
    try:
        query = build_search_query(
            q, event_type, user_id, start_date, end_date)
        response = await es.search(
            index=EVENTS_INDEX,
            query=query,
            size=size,
            sort=[{"timestamp": "desc"}],
        )
        hits = response["hits"]["hits"]
        return {
            "total": response["hits"]["total"]["value"],
            "results": [hit["_source"] for hit in hits],
        }
    finally:
        await es.close()
