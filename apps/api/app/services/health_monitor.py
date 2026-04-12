"""Background health monitor that detects service state transitions and publishes SSE events.

Polls all services every POLL_INTERVAL seconds, compares against last-known state
stored in Redis, and emits ``service.status`` SSE events only when a service
transitions between healthy/unhealthy/unavailable.
"""

import asyncio
import json

import redis.asyncio as aioredis
from loguru import logger

from app.config import get_settings
from app.services.events import EventPublisher
from app.services.health import HealthService

POLL_INTERVAL = 15  # seconds
REDIS_STATE_KEY = "health:last_status"


class HealthMonitorService:
    """Async background loop that publishes service.status SSE events on transitions."""

    def __init__(self) -> None:
        self._health = HealthService()
        self._settings = get_settings()
        self._redis: aioredis.Redis | None = None
        self._polling = False

    async def _get_redis(self) -> aioredis.Redis:
        if self._redis is None:
            self._redis = aioredis.from_url(self._settings.redis_url)
        return self._redis

    async def close(self) -> None:
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None

    async def run(self) -> None:
        """Run the polling loop indefinitely (meant to be wrapped in asyncio.create_task)."""
        logger.info("Health monitor started, polling every {}s", POLL_INTERVAL)
        try:
            while True:
                try:
                    await self._check_and_publish()
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    logger.warning("Health monitor poll error", error=str(exc))
                await asyncio.sleep(POLL_INTERVAL)
        finally:
            await self.close()

    async def _check_and_publish(self) -> None:
        """Single poll: get health, compare to previous, publish deltas."""
        if self._polling:
            return  # Skip if previous poll is still running
        self._polling = True
        try:
            health = await self._health.get_health()

            current: dict[str, str] = {}
            for name, svc in health.services.items():
                current[name] = svc.status.value

            previous = await self._load_previous()
            await self._save_current(current)

            if previous is None:
                # First run — no previous state, nothing to compare
                return

            publisher = EventPublisher(self._settings.redis_url)
            try:
                for service_name, new_status in current.items():
                    old_status = previous.get(service_name)
                    if old_status != new_status:
                        detail = ""
                        svc_obj = health.services.get(service_name)
                        if svc_obj:
                            detail = svc_obj.detail
                        publisher.publish(
                            "system",
                            "service.status",
                            {
                                "service": service_name,
                                "status": new_status,
                                "detail": detail,
                            },
                        )
                        logger.info(
                            "Service status changed",
                            service=service_name,
                            old_status=old_status,
                            new_status=new_status,
                        )
            finally:
                publisher.close()
        finally:
            self._polling = False

    async def _load_previous(self) -> dict[str, str] | None:
        """Load previous service states from Redis."""
        r = await self._get_redis()
        raw = await r.get(REDIS_STATE_KEY)
        if raw is None:
            return None
        return json.loads(raw)

    async def _save_current(self, state: dict[str, str]) -> None:
        """Persist current service states to Redis."""
        r = await self._get_redis()
        await r.set(REDIS_STATE_KEY, json.dumps(state))
