"""Events router module.

Aggregates all events-related endpoints into a single router.
"""
from fastapi import APIRouter

from . import crud, stats, search

# Create main events router
router = APIRouter(prefix="/events", tags=["events"])

# Include sub-routers
router.include_router(crud.router)
router.include_router(stats.router)
router.include_router(search.router)
