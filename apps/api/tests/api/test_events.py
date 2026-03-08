"""Tests for SSE events endpoint."""

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def events_client():
    from app.main import app

    return TestClient(app)


class TestSSEEndpoint:
    def test_sse_endpoint_invalid_uuid_returns_422(self, events_client):
        """Invalid investigation ID should return 422."""
        response = events_client.get("/api/v1/investigations/not-a-uuid/events")
        assert response.status_code == 422

    def test_sse_endpoint_route_registered(self):
        """Verify the events route is registered in the FastAPI app."""
        from app.main import app

        routes = [r.path for r in app.routes]
        assert any("/investigations/{investigation_id}/events" in r for r in routes)


class TestEventGenerator:
    @pytest.mark.asyncio
    async def test_event_generator_yields_messages(self):
        """_event_generator should yield decoded messages from Redis pub/sub."""
        from app.api.v1.events import _event_generator

        inv_id = str(uuid.uuid4())
        event_data = json.dumps(
            {
                "type": "document.processing",
                "investigation_id": inv_id,
                "timestamp": "2026-03-08T14:30:00Z",
                "payload": {"document_id": "doc-123"},
            }
        )

        mock_pubsub = AsyncMock()
        mock_pubsub.subscribe = AsyncMock()
        mock_pubsub.unsubscribe = AsyncMock()

        async def mock_listen():
            yield {"type": "message", "data": event_data.encode()}

        mock_pubsub.listen = mock_listen

        mock_redis = MagicMock()
        mock_redis.pubsub.return_value = mock_pubsub
        mock_redis.aclose = AsyncMock()

        with patch("app.api.v1.events.aioredis.from_url", return_value=mock_redis):
            events = []
            async for event in _event_generator(inv_id):
                events.append(event)

            assert len(events) == 1
            parsed = json.loads(events[0]["data"])
            assert parsed["type"] == "document.processing"
            assert parsed["payload"]["document_id"] == "doc-123"

        mock_pubsub.subscribe.assert_called_once_with(f"events:{inv_id}")
        mock_pubsub.unsubscribe.assert_called_once_with(f"events:{inv_id}")
        mock_redis.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_event_generator_skips_non_message_types(self):
        """Non-message pub/sub types (subscribe confirmations) should be skipped."""
        from app.api.v1.events import _event_generator

        mock_pubsub = AsyncMock()
        mock_pubsub.subscribe = AsyncMock()
        mock_pubsub.unsubscribe = AsyncMock()

        async def mock_listen():
            yield {"type": "subscribe", "data": None}  # Subscribe confirmation
            yield {"type": "message", "data": b'{"type":"document.complete"}'}

        mock_pubsub.listen = mock_listen

        mock_redis = MagicMock()
        mock_redis.pubsub.return_value = mock_pubsub
        mock_redis.aclose = AsyncMock()

        with patch("app.api.v1.events.aioredis.from_url", return_value=mock_redis):
            events = []
            async for event in _event_generator("inv-123"):
                events.append(event)

            assert len(events) == 1
            parsed = json.loads(events[0]["data"])
            assert parsed["type"] == "document.complete"
