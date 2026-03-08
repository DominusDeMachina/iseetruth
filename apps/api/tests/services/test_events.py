"""Tests for EventPublisher Redis pub/sub service."""

import json
from unittest.mock import MagicMock, patch

from app.services.events import EventPublisher


class TestEventPublisher:
    def test_publishes_event_to_correct_channel(self):
        """Event should be published to events:{investigation_id} channel."""
        mock_redis = MagicMock()

        with patch("app.services.events.redis.from_url", return_value=mock_redis):
            publisher = EventPublisher("redis://localhost:6379/0")
            publisher.publish(
                investigation_id="inv-123",
                event_type="document.processing",
                payload={"document_id": "doc-456", "stage": "extracting_text"},
            )

        mock_redis.publish.assert_called_once()
        channel = mock_redis.publish.call_args[0][0]
        assert channel == "events:inv-123"

    def test_event_json_format(self):
        """Published event must contain type, investigation_id, timestamp, payload."""
        mock_redis = MagicMock()

        with patch("app.services.events.redis.from_url", return_value=mock_redis):
            publisher = EventPublisher("redis://localhost:6379/0")
            publisher.publish(
                investigation_id="inv-123",
                event_type="document.complete",
                payload={"document_id": "doc-456"},
            )

        raw_data = mock_redis.publish.call_args[0][1]
        event = json.loads(raw_data)
        assert event["type"] == "document.complete"
        assert event["investigation_id"] == "inv-123"
        assert "timestamp" in event
        assert event["payload"]["document_id"] == "doc-456"

    def test_publish_failed_event(self):
        """Failed events should include error details in payload."""
        mock_redis = MagicMock()

        with patch("app.services.events.redis.from_url", return_value=mock_redis):
            publisher = EventPublisher("redis://localhost:6379/0")
            publisher.publish(
                investigation_id="inv-123",
                event_type="document.failed",
                payload={"document_id": "doc-456", "error": "Corrupt PDF"},
            )

        raw_data = mock_redis.publish.call_args[0][1]
        event = json.loads(raw_data)
        assert event["type"] == "document.failed"
        assert event["payload"]["error"] == "Corrupt PDF"

    def test_close_closes_redis_connection(self):
        """close() should close the underlying Redis connection."""
        mock_redis = MagicMock()

        with patch("app.services.events.redis.from_url", return_value=mock_redis):
            publisher = EventPublisher("redis://localhost:6379/0")
            publisher.close()

        mock_redis.close.assert_called_once()

    def test_reuses_single_connection_across_publishes(self):
        """Multiple publish calls should reuse the same Redis connection."""
        mock_redis = MagicMock()

        with patch("app.services.events.redis.from_url", return_value=mock_redis) as mock_from_url:
            publisher = EventPublisher("redis://localhost:6379/0")
            publisher.publish("inv-1", "document.processing", {"document_id": "d1"})
            publisher.publish("inv-1", "document.complete", {"document_id": "d1"})
            publisher.close()

        # from_url called only once (in __init__), not per publish
        mock_from_url.assert_called_once()
        assert mock_redis.publish.call_count == 2
        mock_redis.close.assert_called_once()
