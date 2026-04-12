"""Unit tests for HealthService — each check method tested with mocked clients."""

import pytest

from app.services.health import HealthService


@pytest.fixture
def svc():
    return HealthService()


# ---------- check_postgres ----------

@pytest.mark.asyncio
async def test_check_postgres_healthy(svc, mock_postgres):
    result = await svc.check_postgres()
    assert result.status == "healthy"
    assert result.detail == "Connected"


@pytest.mark.asyncio
async def test_check_postgres_unavailable(svc):
    """Without mocks, the real connection will fail → unavailable."""
    from unittest.mock import AsyncMock, MagicMock, patch

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(side_effect=ConnectionRefusedError("refused"))
    mock_factory = MagicMock()
    mock_factory.__aenter__ = AsyncMock(return_value=mock_session)
    mock_factory.__aexit__ = AsyncMock(return_value=False)
    with patch("app.services.health.async_session_factory", return_value=mock_factory):
        result = await svc.check_postgres()
    assert result.status == "unavailable"
    assert "refused" in result.detail


# ---------- check_neo4j ----------

@pytest.mark.asyncio
async def test_check_neo4j_healthy(svc, mock_neo4j):
    result = await svc.check_neo4j()
    assert result.status == "healthy"
    assert "Neo4j/5.x" in result.detail


@pytest.mark.asyncio
async def test_check_neo4j_unavailable(svc):
    from unittest.mock import AsyncMock, patch

    mock_driver = AsyncMock()
    mock_driver.verify_connectivity = AsyncMock(side_effect=Exception("connection refused"))
    with patch("app.services.health.neo4j_driver", mock_driver):
        result = await svc.check_neo4j()
    assert result.status == "unavailable"


# ---------- check_qdrant ----------

@pytest.mark.asyncio
async def test_check_qdrant_healthy(svc, mock_qdrant):
    result = await svc.check_qdrant()
    assert result.status == "healthy"
    assert "1.17.0" in result.detail


@pytest.mark.asyncio
async def test_check_qdrant_unavailable(svc):
    from unittest.mock import MagicMock, patch

    mock_client = MagicMock()
    mock_client.info.side_effect = Exception("connection refused")
    with patch("app.services.health.get_qdrant_client", return_value=mock_client):
        result = await svc.check_qdrant()
    assert result.status == "unavailable"


# ---------- check_redis ----------

@pytest.mark.asyncio
async def test_check_redis_healthy(svc, mock_redis):
    result = await svc.check_redis()
    assert result.status == "healthy"
    assert result.detail == "Connected"


@pytest.mark.asyncio
async def test_check_redis_unavailable(svc):
    from unittest.mock import AsyncMock, patch

    mock_client = AsyncMock()
    mock_client.ping = AsyncMock(side_effect=ConnectionRefusedError("refused"))
    with patch("app.services.health.redis_client", mock_client):
        result = await svc.check_redis()
    assert result.status == "unavailable"


# ---------- check_ollama ----------

@pytest.mark.asyncio
async def test_check_ollama_healthy(svc, mock_ollama_healthy):
    result = await svc.check_ollama()
    assert result.status == "healthy"
    assert result.models_ready is True
    assert len(result.models) == 3  # qwen3.5:9b, moondream2, qwen3-embedding:8b
    assert all(m.available for m in result.models)


@pytest.mark.asyncio
async def test_check_ollama_includes_moondream2(svc, mock_ollama_healthy):
    result = await svc.check_ollama()
    model_names = [m.name for m in result.models]
    assert "moondream2" in model_names
    moondream = next(m for m in result.models if m.name == "moondream2")
    assert moondream.available is True


@pytest.mark.asyncio
async def test_check_ollama_no_models(svc, mock_ollama_no_models):
    result = await svc.check_ollama()
    assert result.status == "unhealthy"
    assert result.models_ready is False
    assert "Models not ready" in result.detail


@pytest.mark.asyncio
async def test_check_ollama_unavailable(svc, monkeypatch):
    import httpx

    async def mock_get(self, url, **kwargs):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)
    result = await svc.check_ollama()
    assert result.status == "unavailable"
    assert result.models_ready is False


# ---------- check_hardware ----------

def test_check_hardware_ok(svc, mock_hardware_ok):
    warnings = svc.check_hardware()
    assert warnings == []


def test_check_hardware_low_ram(svc, mock_hardware_low):
    warnings = svc.check_hardware()
    assert len(warnings) == 1
    assert "8.0GB" in warnings[0]


# ---------- get_health (orchestrated) ----------

@pytest.mark.asyncio
async def test_get_health_all_healthy(svc, all_healthy):
    result = await svc.get_health()
    assert result.status == "healthy"
    assert len(result.services) == 5
    assert result.warnings == []


@pytest.mark.asyncio
async def test_get_health_degraded_when_ollama_unhealthy(
    svc, mock_postgres, mock_neo4j, mock_qdrant, mock_redis, mock_ollama_no_models, mock_hardware_ok
):
    result = await svc.get_health()
    assert result.status == "degraded"
    assert result.services["ollama"].models_ready is False
