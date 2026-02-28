import os
import hashlib
from typing import Annotated
from redis import Redis, ConnectionPool
from fastapi import Depends


# Redis configuration and connection pool setup
def create_redis_pool(db=0):
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    return ConnectionPool(
        decode_responses=True,
        max_connections=10
    ).from_url(f"{redis_url}/{db}")


# Instantiate connection pools for different purposes
queue_pool = create_redis_pool(db=0)  # For RQ queuing
cache_pool = create_redis_pool(db=1)   # For caching


def get_redis():
    """Dependency function to get a Redis connection from the queue pool for FastAPI routes."""
    return Redis(connection_pool=queue_pool)


def get_cache_redis():
    """Dependency function to get a Redis connection from the cache pool for FastAPI routes."""
    return Redis(connection_pool=cache_pool)


def generate_cache_key(*args):
    """Generate a cache key from arguments by hashing them."""
    key_string = "|".join(str(arg) for arg in args if arg is not None)
    key_hash = hashlib.md5(key_string.encode()).hexdigest()
    return f"events:stats:{key_hash}"


# Reusable dependencies for FastAPI routes
DependsRedis = Annotated[Redis, Depends(get_redis)]
DependsCacheRedis = Annotated[Redis, Depends(get_cache_redis)]
