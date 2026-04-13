import uuid
from datetime import datetime, timezone
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
    with patch("app.services.health.get_qdrant_client", return_value=mock_client):
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
    """Mock httpx call to Ollama returning all required models."""
    import httpx

    async def mock_get(self, url, **kwargs):
        resp = MagicMock(spec=httpx.Response)
        resp.status_code = 200
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {
            "models": [
                {"name": "qwen3.5:9b"},
                {"name": "moondream2"},
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


# ---------------------------------------------------------------------------
# Investigation fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def sample_investigation_id():
    return uuid.UUID("11111111-1111-1111-1111-111111111111")


@pytest.fixture
def sample_investigation(sample_investigation_id):
    """Return a mock Investigation ORM object."""
    from app.models.investigation import Investigation

    inv = MagicMock(spec=Investigation)
    inv.id = sample_investigation_id
    inv.name = "Test Investigation"
    inv.description = "A test investigation"
    inv.created_at = datetime(2026, 3, 8, 12, 0, 0, tzinfo=timezone.utc)
    inv.updated_at = datetime(2026, 3, 8, 12, 0, 0, tzinfo=timezone.utc)
    return inv


@pytest.fixture
def mock_investigation_service(sample_investigation, mock_db_session):
    """Mock InvestigationService for API endpoint tests."""
    # Mock the DB execute for document count query in _get_document_count / _get_document_counts_batch
    count_result = MagicMock()
    count_result.scalar_one.return_value = 0
    count_result.all.return_value = []
    mock_db_session.execute = AsyncMock(return_value=count_result)

    with patch("app.api.v1.investigations.InvestigationService") as mock_cls:
        mock_service = AsyncMock()
        mock_cls.return_value = mock_service
        mock_service.create_investigation = AsyncMock(return_value=sample_investigation)
        mock_service.list_investigations = AsyncMock(
            return_value=([sample_investigation], 1)
        )
        mock_service.get_investigation = AsyncMock(return_value=sample_investigation)
        mock_service.delete_investigation = AsyncMock(return_value=None)
        yield mock_service


@pytest.fixture
def mock_db_session():
    """Mock async database session for the get_db dependency."""
    mock_session = AsyncMock()
    return mock_session


@pytest.fixture
def investigation_client(mock_db_session):
    """TestClient with get_db dependency overridden."""
    from app.db.postgres import get_db
    from app.main import app

    async def override_get_db():
        yield mock_db_session

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Document fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def sample_document_id():
    return uuid.UUID("22222222-2222-2222-2222-222222222222")


@pytest.fixture
def sample_document(sample_document_id, sample_investigation_id):
    """Return a mock Document ORM object."""
    from app.models.document import Document

    doc = MagicMock(spec=Document)
    doc.id = sample_document_id
    doc.investigation_id = sample_investigation_id
    doc.filename = "test-report.pdf"
    doc.size_bytes = 102400
    doc.sha256_checksum = "a" * 64
    doc.document_type = "pdf"
    doc.source_url = None
    doc.status = "queued"
    doc.page_count = 5
    doc.entity_count = None
    doc.extraction_confidence = None
    doc.ocr_confidence = None
    doc.extracted_text = None
    doc.ocr_method = None
    doc.error_message = None
    doc.failed_stage = None
    doc.retry_count = 0
    doc.created_at = datetime(2026, 3, 8, 12, 0, 0, tzinfo=timezone.utc)
    doc.updated_at = datetime(2026, 3, 8, 12, 0, 0, tzinfo=timezone.utc)
    return doc


@pytest.fixture
def mock_document_service(sample_document):
    """Mock DocumentService for API endpoint tests."""
    with patch("app.api.v1.documents.DocumentService") as mock_cls:
        mock_service = AsyncMock()
        mock_cls.return_value = mock_service
        mock_service.upload_document = AsyncMock(return_value=sample_document)
        mock_service.list_documents = AsyncMock(return_value=([sample_document], 1))
        mock_service.get_document = AsyncMock(return_value=sample_document)
        mock_service.delete_document = AsyncMock(return_value=None)
        mock_service.retry_failed_document = AsyncMock(return_value=sample_document)
        yield mock_service


@pytest.fixture
def mock_pdf_file():
    """Create a mock UploadFile that looks like a PDF (supports chunked reads)."""
    import io

    content = b"%PDF-1.4 fake pdf content for testing"
    file = io.BytesIO(content)
    upload = MagicMock()
    upload.filename = "test-report.pdf"
    upload.content_type = "application/pdf"
    upload.read = AsyncMock(side_effect=[content, b""])
    upload.seek = AsyncMock()
    upload.file = file
    return upload


# ---------------------------------------------------------------------------
# Chunk fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def sample_chunk_id():
    return uuid.UUID("33333333-3333-3333-3333-333333333333")


@pytest.fixture
def sample_chunk_context(sample_chunk_id, sample_document_id):
    """Return a mock ChunkWithContextResponse."""
    from app.schemas.chunk import ChunkWithContextResponse

    return ChunkWithContextResponse(
        chunk_id=sample_chunk_id,
        document_id=sample_document_id,
        document_filename="test-report.pdf",
        sequence_number=5,
        total_chunks=20,
        text="Deputy Mayor Horvat signed the contract.",
        page_start=3,
        page_end=3,
        context_before="Previous paragraph text.",
        context_after="Next paragraph text.",
    )


@pytest.fixture
def mock_chunk_service(sample_chunk_context):
    """Mock ChunkService for API endpoint tests."""
    with patch("app.api.v1.chunks.ChunkService") as mock_cls:
        mock_service = AsyncMock()
        mock_cls.return_value = mock_service
        mock_service.get_chunk_with_context = AsyncMock(
            return_value=sample_chunk_context
        )
        yield mock_service
