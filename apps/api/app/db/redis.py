import redis.asyncio as aioredis

from app.config import get_settings

settings = get_settings()

client = aioredis.from_url(settings.redis_url)
