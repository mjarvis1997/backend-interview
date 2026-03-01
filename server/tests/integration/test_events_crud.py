"""Integration tests for the events CRUD endpoints.

Requires all compose services to be running:
    docker compose up -d

The POST endpoint only enqueues — writes happen asynchronously in RQ workers.
`poll_for_events` retries GET until the expected count arrives or times out.
"""
import asyncio

from httpx import AsyncClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_EVENT = {
    "type": "click",
    "timestamp": "2024-06-01T12:00:00Z",
    "user_id": "user-integration-1",
    "source_url": "https://example.com/page",
    "metadata": {"button": "signup", "browser": "chrome"},
}


async def poll_for_events(
    client: AsyncClient,
    *,
    expected_count: int = 1,
    timeout: float = 10.0,
    interval: float = 0.5,
    params: dict | None = None,
) -> list:
    """Poll GET /events/ until at least `expected_count` events are returned.

    Raises AssertionError on timeout so failures are reported clearly.
    """
    deadline = asyncio.get_event_loop().time() + timeout
    while True:
        response = await client.get("/events/", params=params or {})
        events = response.json()
        if len(events) >= expected_count:
            return events
        if asyncio.get_event_loop().time() >= deadline:
            raise AssertionError(
                f"Timed out waiting for {expected_count} event(s); "
                f"last response had {len(events)}"
            )
        await asyncio.sleep(interval)


# ---------------------------------------------------------------------------
# GET /events/
# ---------------------------------------------------------------------------

async def test_get_events_empty(client: AsyncClient):
    """GET /events/ should return an empty list when no events exist."""
    response = await client.get("/events/")
    assert response.status_code == 200
    assert response.json() == []


# ---------------------------------------------------------------------------
# POST /events/
# ---------------------------------------------------------------------------

async def test_post_event_returns_job_id(client: AsyncClient):
    """POST /events/ should immediately return a job_id without blocking."""
    response = await client.post("/events/", json=SAMPLE_EVENT)
    assert response.status_code == 200
    body = response.json()
    assert "job_id" in body
    assert body["job_id"] is not None


async def test_post_event_is_persisted(client: AsyncClient):
    """After POST, the event should eventually appear in GET /events/."""
    await client.post("/events/", json=SAMPLE_EVENT)
    events = await poll_for_events(client, expected_count=1)
    assert len(events) == 1


async def test_post_event_fields_are_correct(client: AsyncClient):
    """The persisted event should match the submitted payload."""
    await client.post("/events/", json=SAMPLE_EVENT)
    events = await poll_for_events(client, expected_count=1)
    event = events[0]

    assert event["type"] == SAMPLE_EVENT["type"]
    assert event["user_id"] == SAMPLE_EVENT["user_id"]
    assert event["source_url"] == SAMPLE_EVENT["source_url"]
    assert event["metadata"] == SAMPLE_EVENT["metadata"]


async def test_multiple_posts_all_persisted(client: AsyncClient):
    """Posting N events should result in N events being stored."""
    for _ in range(3):
        await client.post("/events/", json=SAMPLE_EVENT)
    events = await poll_for_events(client, expected_count=3)
    assert len(events) == 3


# ---------------------------------------------------------------------------
# GET /events/ — filters
# ---------------------------------------------------------------------------

async def test_filter_by_event_type(client: AsyncClient):
    """event_type filter should return only matching events."""
    other = {**SAMPLE_EVENT, "type": "pageview"}
    await client.post("/events/", json=SAMPLE_EVENT)
    await client.post("/events/", json=other)
    await poll_for_events(client, expected_count=2)

    response = await client.get("/events/", params={"event_type": "click"})
    events = response.json()
    assert all(e["type"] == "click" for e in events)
    assert len(events) == 1


async def test_filter_by_user_id(client: AsyncClient):
    """user_id filter should return only events for that user."""
    other_user = {**SAMPLE_EVENT, "user_id": "user-other"}
    await client.post("/events/", json=SAMPLE_EVENT)
    await client.post("/events/", json=other_user)
    await poll_for_events(client, expected_count=2)

    response = await client.get("/events/", params={"user_id": SAMPLE_EVENT["user_id"]})
    events = response.json()
    assert all(e["user_id"] == SAMPLE_EVENT["user_id"] for e in events)
    assert len(events) == 1


async def test_filter_by_source_url(client: AsyncClient):
    """source_url filter should return only events from that URL."""
    other_url = {**SAMPLE_EVENT, "source_url": "https://other.com"}
    await client.post("/events/", json=SAMPLE_EVENT)
    await client.post("/events/", json=other_url)
    await poll_for_events(client, expected_count=2)

    response = await client.get("/events/", params={"source_url": SAMPLE_EVENT["source_url"]})
    events = response.json()
    assert all(e["source_url"] == SAMPLE_EVENT["source_url"] for e in events)
    assert len(events) == 1


# ---------------------------------------------------------------------------
# DELETE /events/
# ---------------------------------------------------------------------------

async def test_delete_removes_all_events(client: AsyncClient):
    """DELETE /events/ should remove all stored events."""
    await client.post("/events/", json=SAMPLE_EVENT)
    await poll_for_events(client, expected_count=1)

    delete_response = await client.delete("/events/")
    assert delete_response.status_code == 200

    get_response = await client.get("/events/")
    assert get_response.json() == []
