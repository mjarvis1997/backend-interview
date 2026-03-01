"""Integration tests for the events search endpoint.

Requires all compose services to be running:
    docker compose --profile test up -d

The full lifecycle under test: POST event → RQ worker writes to MongoDB and
indexes in Elasticsearch → GET /events/search returns the result.

Elasticsearch has a ~1s index refresh delay, so search results are polled
the same way MongoDB results are polled in test_events_crud.py.
"""
import asyncio

from httpx import AsyncClient


SAMPLE_EVENT = {
    "type": "click",
    "timestamp": "2024-06-01T12:00:00Z",
    "user_id": "user-search-1",
    "source_url": "https://example.com",
    "metadata": {"browser": "firefox", "device": "tablet"},
}


async def poll_for_search(
    client: AsyncClient,
    q: str,
    *,
    expected_count: int = 1,
    timeout: float = 15.0,
    interval: float = 0.5,
) -> dict:
    """Poll GET /events/search until at least `expected_count` results appear.

    Elasticsearch's refresh interval means a freshly indexed document may not
    be searchable immediately — polling mirrors the pattern used for MongoDB.
    """
    deadline = asyncio.get_event_loop().time() + timeout
    while True:
        response = await client.get("/events/search", params={"q": q})
        body = response.json()
        if body.get("total", 0) >= expected_count:
            return body
        if asyncio.get_event_loop().time() >= deadline:
            raise AssertionError(
                f"Timed out waiting for {expected_count} search result(s) for q={q!r}; "
                f"last total was {body.get('total', 0)}"
            )
        await asyncio.sleep(interval)


async def test_ingested_event_is_searchable(client: AsyncClient):
    """POST → worker indexes in ES → search by metadata value returns the event."""
    await client.post("/events/", json=SAMPLE_EVENT)
    body = await poll_for_search(client, "firefox", expected_count=1)

    assert body["total"] >= 1
    assert any(r["metadata"]["browser"] == "firefox" for r in body["results"])


async def test_search_with_no_match_returns_empty(client: AsyncClient):
    """Searching for a term that matches no documents should return zero results."""
    response = await client.get("/events/search", params={"q": "zzznomatchzzz"})
    body = response.json()
    assert response.status_code == 200
    assert body["total"] == 0
    assert body["results"] == []
