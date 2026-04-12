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


# ---------------------------------------------------------------------------
# System-level SSE endpoint (service.status events)
# ---------------------------------------------------------------------------

system_router = APIRouter(tags=["events"])


async def _system_event_generator():
    """Subscribe to the global system events channel for service status changes."""
    redis = aioredis.from_url(settings.redis_url)
    pubsub = redis.pubsub()
    await pubsub.subscribe("events:system")
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                yield {"data": message["data"].decode()}
    finally:
        await pubsub.unsubscribe("events:system")
        await redis.aclose()


@system_router.get("/events/system")
async def stream_system_events():
    """Stream SSE events for system-level service status changes."""
    return EventSourceResponse(_system_event_generator())
