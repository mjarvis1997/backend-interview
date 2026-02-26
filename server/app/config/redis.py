import redis


def create_redis_pool():
    return redis.ConnectionPool(
        host='localhost',
        port=6379,
        db=0,
        decode_responses=True,
        max_connections=10
    )


pool = create_redis_pool()


def get_redis():
    # Here, we re-use our connection pool
    # not creating a new one
    return redis.Redis(connection_pool=pool)
