import os
from typing import Annotated
from redis import Redis, ConnectionPool
from fastapi import Depends


# Redis configuration and connection pool setup
def create_redis_pool():
    return ConnectionPool(
        decode_responses=True,
        max_connections=10
    ).from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))


# Instantiate the connection pool at module level so it can be accessed elsewhere
pool = create_redis_pool()


def get_redis():
    """Dependency function to get a Redis connection from the pool for FastAPI routes."""
    # Fetch a Redis connection from the pool
    return Redis(connection_pool=pool)


# Reusable dependencies for FastAPI routes that need redis access
DependsRedis = Annotated[Redis, Depends(get_redis)]
