"""Tests for HealthMonitorService — service.status SSE event publishing."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.health import (
    HealthResponse,
    OllamaStatus,
    OverallStatusEnum,
    ServiceStatus,
    StatusEnum,
)
from app.services.health_monitor import HealthMonitorService, REDIS_STATE_KEY


def _build_health_response(**overrides) -> HealthResponse:
    """Build a HealthResponse with all services healthy unless overridden."""
    defaults = {
        "postgres": ServiceStatus(status=StatusEnum.healthy, detail="Connected"),
        "neo4j": ServiceStatus(status=StatusEnum.healthy, detail="Connected"),
        "qdrant": ServiceStatus(status=StatusEnum.healthy, detail="Connected"),
        "redis": ServiceStatus(status=StatusEnum.healthy, detail="Connected"),
        "ollama": OllamaStatus(
            status=StatusEnum.healthy,
            detail="Running",
            models_ready=True,
            models=[],
        ),
    }
    defaults.update(overrides)
    return HealthResponse(
        status=OverallStatusEnum.healthy,
        timestamp="2026-04-12T00:00:00Z",
        services=defaults,
        warnings=[],
    )


class TestHealthMonitorCheckAndPublish:
    """Unit tests for _check_and_publish detecting transitions."""

    @pytest.mark.asyncio
    async def test_first_poll_no_events(self):
        """First poll (no previous state) should save state but not publish events."""
        monitor = HealthMonitorService()
        health = _build_health_response()

        with (
            patch.object(monitor._health, "get_health", new=AsyncMock(return_value=health)),
            patch.object(monitor, "_load_previous", new=AsyncMock(return_value=None)),
            patch.object(monitor, "_save_current", new=AsyncMock()) as mock_save,
            patch("app.services.health_monitor.EventPublisher") as mock_pub_cls,
        ):
            await monitor._check_and_publish()

            # State saved
            mock_save.assert_awaited_once()
            saved = mock_save.call_args[0][0]
            assert saved["postgres"] == "healthy"
            assert saved["ollama"] == "healthy"

            # No events published (first run)
            mock_pub_cls.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_change_no_events(self):
        """When all services remain in the same state, no SSE events should fire."""
        monitor = HealthMonitorService()
        health = _build_health_response()
        previous = {
            "postgres": "healthy",
            "neo4j": "healthy",
            "qdrant": "healthy",
            "redis": "healthy",
            "ollama": "healthy",
        }

        with (
            patch.object(monitor._health, "get_health", new=AsyncMock(return_value=health)),
            patch.object(monitor, "_load_previous", new=AsyncMock(return_value=previous)),
            patch.object(monitor, "_save_current", new=AsyncMock()),
            patch("app.services.health_monitor.EventPublisher") as mock_pub_cls,
        ):
            mock_publisher = MagicMock()
            mock_pub_cls.return_value = mock_publisher

            await monitor._check_and_publish()

            # Publisher opened but no events published
            mock_publisher.publish.assert_not_called()

    @pytest.mark.asyncio
    async def test_service_goes_down_publishes_event(self):
        """When a service transitions from healthy to unavailable, publish event."""
        monitor = HealthMonitorService()
        health = _build_health_response(
            neo4j=ServiceStatus(status=StatusEnum.unavailable, detail="Connection refused"),
        )
        previous = {
            "postgres": "healthy",
            "neo4j": "healthy",
            "qdrant": "healthy",
            "redis": "healthy",
            "ollama": "healthy",
        }

        with (
            patch.object(monitor._health, "get_health", new=AsyncMock(return_value=health)),
            patch.object(monitor, "_load_previous", new=AsyncMock(return_value=previous)),
            patch.object(monitor, "_save_current", new=AsyncMock()),
            patch("app.services.health_monitor.EventPublisher") as mock_pub_cls,
        ):
            mock_publisher = MagicMock()
            mock_pub_cls.return_value = mock_publisher

            await monitor._check_and_publish()

            mock_publisher.publish.assert_called_once_with(
                "system",
                "service.status",
                {
                    "service": "neo4j",
                    "status": "unavailable",
                    "detail": "Connection refused",
                },
            )
            mock_publisher.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_service_recovers_publishes_event(self):
        """When a service transitions from unavailable to healthy, publish event."""
        monitor = HealthMonitorService()
        health = _build_health_response()  # all healthy
        previous = {
            "postgres": "healthy",
            "neo4j": "healthy",
            "qdrant": "unavailable",
            "redis": "healthy",
            "ollama": "healthy",
        }

        with (
            patch.object(monitor._health, "get_health", new=AsyncMock(return_value=health)),
            patch.object(monitor, "_load_previous", new=AsyncMock(return_value=previous)),
            patch.object(monitor, "_save_current", new=AsyncMock()),
            patch("app.services.health_monitor.EventPublisher") as mock_pub_cls,
        ):
            mock_publisher = MagicMock()
            mock_pub_cls.return_value = mock_publisher

            await monitor._check_and_publish()

            mock_publisher.publish.assert_called_once_with(
                "system",
                "service.status",
                {
                    "service": "qdrant",
                    "status": "healthy",
                    "detail": "Connected",
                },
            )

    @pytest.mark.asyncio
    async def test_multiple_transitions_publish_multiple_events(self):
        """Multiple simultaneous transitions should each get their own event."""
        monitor = HealthMonitorService()
        health = _build_health_response(
            neo4j=ServiceStatus(status=StatusEnum.unavailable, detail="Down"),
            qdrant=ServiceStatus(status=StatusEnum.unavailable, detail="Down"),
        )
        previous = {
            "postgres": "healthy",
            "neo4j": "healthy",
            "qdrant": "healthy",
            "redis": "healthy",
            "ollama": "healthy",
        }

        with (
            patch.object(monitor._health, "get_health", new=AsyncMock(return_value=health)),
            patch.object(monitor, "_load_previous", new=AsyncMock(return_value=previous)),
            patch.object(monitor, "_save_current", new=AsyncMock()),
            patch("app.services.health_monitor.EventPublisher") as mock_pub_cls,
        ):
            mock_publisher = MagicMock()
            mock_pub_cls.return_value = mock_publisher

            await monitor._check_and_publish()

            assert mock_publisher.publish.call_count == 2
            services_notified = {
                call[0][2]["service"] for call in mock_publisher.publish.call_args_list
            }
            assert services_notified == {"neo4j", "qdrant"}
