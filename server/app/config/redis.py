from typing import Annotated
import redis
from fastapi import Depends
from redis import Redis


# Redis configuration and connection pool setup
def create_redis_pool():
    return redis.ConnectionPool(
        host='localhost',
        port=6379,
        db=0,
        decode_responses=True,
        max_connections=10
    )


# Instantiate the connection pool at module level so it can be accessed elsewhere
pool = create_redis_pool()


def get_redis():
    """Dependency function to get a Redis connection from the pool for FastAPI routes."""
    # Fetch a Redis connection from the pool
    return redis.Redis(connection_pool=pool)


# Reusable dependencies for FastAPI routes that need redis access
DependsRedis = Annotated[Redis, Depends(get_redis)]
