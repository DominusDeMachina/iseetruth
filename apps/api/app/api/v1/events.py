import uuid

import redis.asyncio as aioredis
from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from app.config import get_settings

router = APIRouter(
    prefix="/investigations",
    tags=["events"],
)

settings = get_settings()


async def _event_generator(investigation_id: str):
    """Subscribe to Redis pub/sub and yield SSE events for an investigation."""
    redis = aioredis.from_url(settings.redis_url)
    pubsub = redis.pubsub()
    await pubsub.subscribe(f"events:{investigation_id}")
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                yield {"data": message["data"].decode()}
    finally:
        await pubsub.unsubscribe(f"events:{investigation_id}")
        await redis.aclose()


@router.get("/{investigation_id}/events")
async def stream_events(investigation_id: uuid.UUID):
    """Stream SSE events for an investigation's document processing."""
    return EventSourceResponse(_event_generator(str(investigation_id)))
