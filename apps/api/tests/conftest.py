from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def mock_postgres():
    """Mock PostgreSQL async session that succeeds on SELECT 1."""
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=None)
    mock_factory = MagicMock()
    mock_factory.__aenter__ = AsyncMock(return_value=mock_session)
    mock_factory.__aexit__ = AsyncMock(return_value=False)
    with patch("app.services.health.async_session_factory", return_value=mock_factory):
        yield mock_session


@pytest.fixture
def mock_neo4j():
    """Mock Neo4j driver that reports healthy."""
    mock_driver = AsyncMock()
    mock_driver.verify_connectivity = AsyncMock(return_value=None)
    server_info = MagicMock()
    server_info.agent = "Neo4j/5.x"
    mock_driver.get_server_info = AsyncMock(return_value=server_info)
    with patch("app.services.health.neo4j_driver", mock_driver):
        yield mock_driver


@pytest.fixture
def mock_qdrant():
    """Mock Qdrant client that reports healthy."""
    mock_client = MagicMock()
    mock_info = MagicMock()
    mock_info.version = "1.17.0"
    mock_client.info.return_value = mock_info
    with patch("app.services.health.qdrant_client", mock_client):
        yield mock_client


@pytest.fixture
def mock_redis():
    """Mock Redis client that reports healthy."""
    mock_client = AsyncMock()
    mock_client.ping = AsyncMock(return_value=True)
    with patch("app.services.health.redis_client", mock_client):
        yield mock_client


@pytest.fixture
def mock_ollama_healthy(monkeypatch):
    """Mock httpx call to Ollama returning both required models."""
    import httpx

    async def mock_get(self, url, **kwargs):
        resp = MagicMock(spec=httpx.Response)
        resp.status_code = 200
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {
            "models": [
                {"name": "qwen3.5:9b"},
                {"name": "qwen3-embedding:8b"},
            ]
        }
        return resp

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)


@pytest.fixture
def mock_ollama_no_models(monkeypatch):
    """Mock httpx call to Ollama returning no models."""
    import httpx

    async def mock_get(self, url, **kwargs):
        resp = MagicMock(spec=httpx.Response)
        resp.status_code = 200
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {"models": []}
        return resp

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)


@pytest.fixture
def mock_hardware_ok():
    """Mock psutil reporting 32GB RAM."""
    mock_vm = MagicMock()
    mock_vm.total = 32 * (1024**3)  # 32 GB
    with patch("app.services.health.psutil") as mock_psutil:
        mock_psutil.virtual_memory.return_value = mock_vm
        yield mock_psutil


@pytest.fixture
def mock_hardware_low():
    """Mock psutil reporting 8GB RAM."""
    mock_vm = MagicMock()
    mock_vm.total = 8 * (1024**3)  # 8 GB
    with patch("app.services.health.psutil") as mock_psutil:
        mock_psutil.virtual_memory.return_value = mock_vm
        yield mock_psutil


@pytest.fixture
def all_healthy(
    mock_postgres, mock_neo4j, mock_qdrant, mock_redis, mock_ollama_healthy, mock_hardware_ok
):
    """Combine all healthy mocks for integration-style tests."""
    pass


@pytest.fixture
def client():
    from app.main import app

    return TestClient(app)
