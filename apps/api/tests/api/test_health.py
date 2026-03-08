"""Integration tests for GET /api/v1/health/ endpoint."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def test_health_endpoint_all_healthy(client, all_healthy):
    response = client.get("/api/v1/health/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "postgres" in data["services"]
    assert "neo4j" in data["services"]
    assert "qdrant" in data["services"]
    assert "redis" in data["services"]
    assert "ollama" in data["services"]
    assert data["services"]["ollama"]["models_ready"] is True
    assert "timestamp" in data
    assert isinstance(data["warnings"], list)


def test_health_endpoint_degraded_when_service_down(
    client, mock_postgres, mock_neo4j, mock_qdrant, mock_redis, mock_ollama_no_models, mock_hardware_ok
):
    response = client.get("/api/v1/health/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["services"]["ollama"]["models_ready"] is False
    assert "Models not ready" in data["services"]["ollama"]["detail"]


def test_health_endpoint_models_not_ready(
    client, mock_postgres, mock_neo4j, mock_qdrant, mock_redis, mock_ollama_no_models, mock_hardware_ok
):
    response = client.get("/api/v1/health/")
    data = response.json()
    ollama = data["services"]["ollama"]
    assert ollama["models_ready"] is False
    assert len(ollama["models"]) == 2
    assert all(m["available"] is False for m in ollama["models"])


def test_health_endpoint_hardware_warning(
    client, mock_postgres, mock_neo4j, mock_qdrant, mock_redis, mock_ollama_healthy, mock_hardware_low
):
    response = client.get("/api/v1/health/")
    data = response.json()
    assert len(data["warnings"]) > 0
    assert "RAM" in data["warnings"][0]


def test_health_endpoint_trailing_slash_redirect(client, all_healthy):
    """Ensure /api/v1/health (no trailing slash) is handled."""
    response = client.get("/api/v1/health", follow_redirects=False)
    # FastAPI may redirect to /api/v1/health/ or serve it directly
    assert response.status_code in (200, 307)


def test_domain_error_returns_rfc7807(client):
    """Verify DomainError produces RFC 7807 JSON response."""
    from unittest.mock import patch

    from app.exceptions import ServiceUnavailableError

    with patch(
        "app.services.health.HealthService.get_health",
        side_effect=ServiceUnavailableError("DB down"),
    ):
        response = client.get("/api/v1/health/")
    assert response.status_code == 503
    data = response.json()
    assert data["type"] == "urn:osint:error:service_unavailable"
    assert data["title"] == "Service Unavailable"
    assert data["status"] == 503
    assert data["detail"] == "DB down"
    assert data["instance"] == "/api/v1/health/"


def test_generic_error_returns_rfc7807():
    """Verify unhandled exceptions produce RFC 7807 JSON response."""
    from unittest.mock import patch

    from fastapi.testclient import TestClient

    from app.main import app

    error_client = TestClient(app, raise_server_exceptions=False)
    with patch(
        "app.services.health.HealthService.get_health",
        side_effect=RuntimeError("unexpected"),
    ):
        response = error_client.get("/api/v1/health/")
    assert response.status_code == 500
    data = response.json()
    assert data["type"] == "urn:osint:error:internal"
    assert data["title"] == "Internal Server Error"
    assert data["status"] == 500
    assert data["instance"] == "/api/v1/health/"
