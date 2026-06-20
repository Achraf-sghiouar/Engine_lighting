import os
import redis.asyncio as redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Singleton Redis connection pool
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

async def get_redis():
    """Dependency for FastAPI endpoints if needed"""
    yield redis_client
