"""Shared fixtures for integration tests.

Prerequisites — all compose services must be running before executing these tests:
    docker compose --profile test up -d

Run integration tests with:
    poetry run pytest tests/integration/ -v
"""
import asyncio

import pytest_asyncio
from httpx import AsyncClient
from rq.registry import StartedJobRegistry, ScheduledJobRegistry

from app.dependencies.rq import q

API_BASE_URL = "http://localhost:8000"


async def wait_for_queue_drain(timeout: float = 15.0) -> None:
    """Block until the RQ ingestion queue has no queued, in-progress, or scheduled jobs.

    Checks three registries:
    - len(q):               jobs waiting to be picked up by a worker
    - StartedJobRegistry:   jobs currently executing in a worker
    - ScheduledJobRegistry: jobs waiting to be retried after a failure

    All three must be empty before it is safe to DELETE events, otherwise a
    retry scheduled after a transient failure (e.g. ES hiccup) could fire
    after the DELETE and leave a stale event in MongoDB.
    """
    started_registry = StartedJobRegistry(queue=q)
    scheduled_registry = ScheduledJobRegistry(queue=q)
    deadline = asyncio.get_event_loop().time() + timeout
    while True:
        queued = len(q)
        in_progress = started_registry.count
        scheduled = scheduled_registry.count
        if queued == 0 and in_progress == 0 and scheduled == 0:
            return
        if asyncio.get_event_loop().time() >= deadline:
            raise RuntimeError(
                f"Timed out waiting for queue to drain: "
                f"{queued} queued, {in_progress} in progress, {scheduled} scheduled"
            )
        await asyncio.sleep(0.25)


@pytest_asyncio.fixture
async def client():
    """Function-scoped AsyncClient pointed at the running API container."""
    async with AsyncClient(base_url=API_BASE_URL) as ac:
        yield ac


@pytest_asyncio.fixture(autouse=True)
async def clean_events(client: AsyncClient):
    """Ensure the events collection is empty before each test.

    1. Waits for any in-flight RQ jobs from the previous test to finish.
    2. Deletes all events from MongoDB.
    3. Polls until MongoDB confirms the collection is empty.
    """
    await wait_for_queue_drain()
    await client.delete("/events/")
    deadline = asyncio.get_event_loop().time() + 10.0
    while True:
        response = await client.get("/events/")
        if response.json() == []:
            break
        if asyncio.get_event_loop().time() >= deadline:
            raise RuntimeError(
                "Timed out waiting for events collection to empty before test")
        await asyncio.sleep(0.25)

    yield
