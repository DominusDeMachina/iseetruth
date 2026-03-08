"""Unit tests for DocumentService business logic."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.exceptions import DocumentNotFoundError
from app.models.document import Document
from app.services.document import DocumentService
from app.services.investigation import InvestigationNotFoundError


@pytest.fixture
def mock_db():
    """Mock async database session."""
    db = AsyncMock()
    db.add = MagicMock()
    return db


@pytest.fixture
def service(mock_db):
    return DocumentService(mock_db)


@pytest.fixture
def sample_inv_id():
    return uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


@pytest.fixture
def sample_doc_id():
    return uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


@pytest.fixture
def sample_document(sample_doc_id, sample_inv_id):
    doc = MagicMock(spec=Document)
    doc.id = sample_doc_id
    doc.investigation_id = sample_inv_id
    doc.filename = "test.pdf"
    doc.size_bytes = 1024
    doc.sha256_checksum = "a" * 64
    doc.status = "queued"
    doc.page_count = 3
    doc.created_at = datetime(2026, 3, 8, 12, 0, 0, tzinfo=timezone.utc)
    doc.updated_at = datetime(2026, 3, 8, 12, 0, 0, tzinfo=timezone.utc)
    return doc


@pytest.fixture
def mock_upload_file():
    """Create a mock UploadFile supporting chunked reads."""
    content = b"%PDF-1.4 fake content for testing purposes"
    upload = MagicMock()
    upload.filename = "test.pdf"
    upload.content_type = "application/pdf"
    upload.read = AsyncMock(side_effect=[content, b""])
    upload.seek = AsyncMock()
    return upload


# ---------------------------------------------------------------------------
# upload_document
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_upload_document_stores_file_and_creates_record(
    service, mock_db, mock_upload_file, sample_inv_id, tmp_path
):
    """upload_document should save file to disk, compute checksum, create DB record."""
    # Mock investigation lookup
    inv_mock = MagicMock()
    inv_mock.id = sample_inv_id
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = inv_mock
    mock_db.execute = AsyncMock(return_value=result_mock)

    async def fake_refresh(obj):
        obj.created_at = datetime.now(timezone.utc)
        obj.updated_at = datetime.now(timezone.utc)

    mock_db.refresh = AsyncMock(side_effect=fake_refresh)

    with (
        patch("app.services.document.STORAGE_ROOT", tmp_path),
        patch("app.services.document._get_page_count", return_value=5),
    ):
        result = await service.upload_document(sample_inv_id, mock_upload_file)

    mock_db.add.assert_called_once()
    mock_db.commit.assert_awaited_once()
    mock_db.refresh.assert_awaited_once()
    assert isinstance(result, Document)

    # Verify file was written to disk
    inv_dir = tmp_path / str(sample_inv_id)
    assert inv_dir.exists()
    pdf_files = list(inv_dir.glob("*.pdf"))
    assert len(pdf_files) == 1


@pytest.mark.asyncio
async def test_upload_document_to_nonexistent_investigation(
    service, mock_db, mock_upload_file
):
    """upload_document should raise InvestigationNotFoundError if investigation doesn't exist."""
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=result_mock)

    fake_inv_id = uuid.uuid4()
    with pytest.raises(InvestigationNotFoundError):
        await service.upload_document(fake_inv_id, mock_upload_file)


# ---------------------------------------------------------------------------
# list_documents
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_list_documents_returns_paginated(service, mock_db, sample_inv_id):
    """list_documents should return (documents, total)."""
    count_result = MagicMock()
    count_result.scalar_one.return_value = 3

    doc1 = MagicMock(spec=Document)
    doc2 = MagicMock(spec=Document)
    list_result = MagicMock()
    list_result.scalars.return_value.all.return_value = [doc1, doc2]

    mock_db.execute = AsyncMock(side_effect=[count_result, list_result])

    documents, total = await service.list_documents(sample_inv_id, limit=10, offset=0)

    assert total == 3
    assert len(documents) == 2
    assert mock_db.execute.await_count == 2


# ---------------------------------------------------------------------------
# get_document
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_get_document_returns_found(
    service, mock_db, sample_inv_id, sample_doc_id
):
    """get_document should return document when found."""
    doc = MagicMock(spec=Document)
    doc.id = sample_doc_id
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = doc
    mock_db.execute = AsyncMock(return_value=result_mock)

    result = await service.get_document(sample_inv_id, sample_doc_id)
    assert result.id == sample_doc_id


@pytest.mark.asyncio
async def test_get_document_raises_not_found(
    service, mock_db, sample_inv_id, sample_doc_id
):
    """get_document should raise DocumentNotFoundError when not found."""
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=result_mock)

    with pytest.raises(DocumentNotFoundError) as exc_info:
        await service.get_document(sample_inv_id, sample_doc_id)

    assert str(sample_doc_id) in str(exc_info.value)
    assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# delete_document
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_delete_document_removes_file_and_db(
    service, mock_db, sample_inv_id, sample_doc_id, tmp_path
):
    """delete_document should delete file from storage and DB record."""
    doc = MagicMock(spec=Document)
    doc.id = sample_doc_id
    doc.investigation_id = sample_inv_id
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = doc
    mock_db.execute = AsyncMock(return_value=result_mock)

    # Create a fake file on disk
    file_path = tmp_path / str(sample_inv_id) / f"{sample_doc_id}.pdf"
    file_path.parent.mkdir(parents=True)
    file_path.write_bytes(b"fake pdf")
    assert file_path.exists()

    with patch("app.services.document.STORAGE_ROOT", tmp_path):
        await service.delete_document(sample_inv_id, sample_doc_id)

    assert not file_path.exists()
    mock_db.delete.assert_awaited_once_with(doc)
    mock_db.commit.assert_awaited()


@pytest.mark.asyncio
async def test_delete_document_not_found(service, mock_db, sample_inv_id, sample_doc_id):
    """delete_document should raise DocumentNotFoundError if document doesn't exist."""
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=result_mock)

    with pytest.raises(DocumentNotFoundError):
        await service.delete_document(sample_inv_id, sample_doc_id)

    mock_db.delete.assert_not_awaited()
