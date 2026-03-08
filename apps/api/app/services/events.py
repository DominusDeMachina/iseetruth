import json
from datetime import datetime, timezone

import redis


class EventPublisher:
    def __init__(self, redis_url: str):
        self._redis = redis.from_url(redis_url)

    def publish(self, investigation_id: str, event_type: str, payload: dict) -> None:
        """Publish an event to the Redis pub/sub channel for an investigation."""
        event = {
            "type": event_type,
            "investigation_id": investigation_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
        }
        self._redis.publish(f"events:{investigation_id}", json.dumps(event))

    def close(self) -> None:
        """Close the underlying Redis connection."""
        self._redis.close()
