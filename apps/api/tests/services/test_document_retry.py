"""Unit tests for DocumentService.retry_failed_document business logic."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.exceptions import DocumentNotFoundError, DocumentNotRetryableError
from app.models.chunk import DocumentChunk
from app.models.document import Document
from app.services.document import DocumentService


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


def _make_failed_document(doc_id, inv_id, failed_stage="extracting_entities"):
    """Create a mock Document in failed state with given failed_stage."""
    doc = MagicMock(spec=Document)
    doc.id = doc_id
    doc.investigation_id = inv_id
    doc.filename = "test.pdf"
    doc.size_bytes = 1024
    doc.sha256_checksum = "a" * 64
    doc.status = "failed"
    doc.failed_stage = failed_stage
    doc.error_message = "Entity extraction failed: Neo4j down"
    doc.retry_count = 0
    doc.page_count = 3
    doc.extracted_text = "Some extracted text"
    doc.entity_count = None
    doc.extraction_confidence = None
    doc.created_at = datetime(2026, 3, 15, 12, 0, 0, tzinfo=timezone.utc)
    doc.updated_at = datetime(2026, 3, 15, 12, 0, 0, tzinfo=timezone.utc)
    return doc


# ---------------------------------------------------------------------------
# retry_failed_document — status validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_retry_raises_not_retryable_when_status_is_complete(
    service, mock_db, sample_inv_id, sample_doc_id
):
    """Retry on non-failed document should raise DocumentNotRetryableError."""
    doc = _make_failed_document(sample_doc_id, sample_inv_id)
    doc.status = "complete"

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = doc
    mock_db.execute = AsyncMock(return_value=result_mock)

    with pytest.raises(DocumentNotRetryableError) as exc_info:
        await service.retry_failed_document(sample_inv_id, sample_doc_id)

    assert exc_info.value.status_code == 409
    assert "document_not_retryable" in exc_info.value.error_type


@pytest.mark.asyncio
async def test_retry_raises_not_retryable_when_status_is_queued(
    service, mock_db, sample_inv_id, sample_doc_id
):
    """Retry on queued document should raise DocumentNotRetryableError."""
    doc = _make_failed_document(sample_doc_id, sample_inv_id)
    doc.status = "queued"

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = doc
    mock_db.execute = AsyncMock(return_value=result_mock)

    with pytest.raises(DocumentNotRetryableError):
        await service.retry_failed_document(sample_inv_id, sample_doc_id)


@pytest.mark.asyncio
async def test_retry_raises_not_found_for_nonexistent_document(
    service, mock_db, sample_inv_id
):
    """Retry on missing document should raise DocumentNotFoundError."""
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=result_mock)

    fake_id = uuid.uuid4()
    with pytest.raises(DocumentNotFoundError):
        await service.retry_failed_document(sample_inv_id, fake_id)


# ---------------------------------------------------------------------------
# retry_failed_document — state reset
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_retry_resets_status_error_and_failed_stage(
    service, mock_db, sample_inv_id, sample_doc_id
):
    """Retry should reset status to queued, clear error_message and failed_stage."""
    doc = _make_failed_document(sample_doc_id, sample_inv_id, "chunking")

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = doc
    # First call: get_document, second call: chunk query
    chunks_result = MagicMock()
    chunks_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(side_effect=[result_mock, chunks_result])

    with patch("app.services.document.process_document_task", create=True):
        from app.worker.tasks.process_document import process_document_task

        with patch(
            "app.services.document.process_document_task",
            MagicMock(delay=MagicMock()),
        ):
            result = await service.retry_failed_document(sample_inv_id, sample_doc_id)

    assert doc.status == "queued"
    assert doc.error_message is None
    assert doc.failed_stage is None
    mock_db.commit.assert_awaited()
    mock_db.refresh.assert_awaited()


# ---------------------------------------------------------------------------
# retry_failed_document — cleanup logic per failed_stage
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_retry_from_chunking_deletes_existing_chunks(
    service, mock_db, sample_inv_id, sample_doc_id
):
    """Retry from 'chunking' failure should delete existing chunks before re-queuing."""
    doc = _make_failed_document(sample_doc_id, sample_inv_id, "chunking")

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = doc

    # Simulate existing chunks in DB
    chunk1 = MagicMock(spec=DocumentChunk)
    chunk2 = MagicMock(spec=DocumentChunk)
    chunks_result = MagicMock()
    chunks_result.scalars.return_value.all.return_value = [chunk1, chunk2]

    mock_db.execute = AsyncMock(side_effect=[result_mock, chunks_result])

    with patch.dict(
        "sys.modules",
        {
            "app.worker.tasks.process_document": MagicMock(
                process_document_task=MagicMock(delay=MagicMock())
            )
        },
    ):
        await service.retry_failed_document(sample_inv_id, sample_doc_id)

    # Both chunks should be deleted
    assert mock_db.delete.await_count == 2
    mock_db.delete.assert_any_await(chunk1)
    mock_db.delete.assert_any_await(chunk2)


@pytest.mark.asyncio
async def test_retry_from_extracting_entities_deletes_chunks(
    service, mock_db, sample_inv_id, sample_doc_id
):
    """Retry from 'extracting_entities' failure should delete chunks (re-run from chunking)."""
    doc = _make_failed_document(sample_doc_id, sample_inv_id, "extracting_entities")

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = doc

    chunk = MagicMock(spec=DocumentChunk)
    chunks_result = MagicMock()
    chunks_result.scalars.return_value.all.return_value = [chunk]

    mock_db.execute = AsyncMock(side_effect=[result_mock, chunks_result])

    with patch.dict(
        "sys.modules",
        {
            "app.worker.tasks.process_document": MagicMock(
                process_document_task=MagicMock(delay=MagicMock())
            )
        },
    ):
        await service.retry_failed_document(sample_inv_id, sample_doc_id)

    mock_db.delete.assert_awaited_once_with(chunk)


@pytest.mark.asyncio
async def test_retry_from_embedding_does_not_delete_chunks(
    service, mock_db, sample_inv_id, sample_doc_id
):
    """Retry from 'embedding' failure should NOT delete chunks (upsert handles Qdrant)."""
    doc = _make_failed_document(sample_doc_id, sample_inv_id, "embedding")

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = doc
    mock_db.execute = AsyncMock(return_value=result_mock)

    with patch.dict(
        "sys.modules",
        {
            "app.worker.tasks.process_document": MagicMock(
                process_document_task=MagicMock(delay=MagicMock())
            )
        },
    ):
        await service.retry_failed_document(sample_inv_id, sample_doc_id)

    mock_db.delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_retry_from_preflight_runs_all_stages(
    service, mock_db, sample_inv_id, sample_doc_id
):
    """Retry from 'preflight' failure should enqueue with resume_from_stage=None."""
    doc = _make_failed_document(sample_doc_id, sample_inv_id, "preflight")

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = doc
    mock_db.execute = AsyncMock(return_value=result_mock)

    mock_task = MagicMock()
    with patch.dict(
        "sys.modules",
        {
            "app.worker.tasks.process_document": MagicMock(
                process_document_task=mock_task
            )
        },
    ):
        await service.retry_failed_document(sample_inv_id, sample_doc_id)

    mock_task.delay.assert_called_once_with(
        str(sample_doc_id), str(sample_inv_id), None
    )


@pytest.mark.asyncio
async def test_retry_from_unknown_stage_runs_all_stages(
    service, mock_db, sample_inv_id, sample_doc_id
):
    """Retry with failed_stage=None (unknown) should run all stages."""
    doc = _make_failed_document(sample_doc_id, sample_inv_id, None)

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = doc
    mock_db.execute = AsyncMock(return_value=result_mock)

    mock_task = MagicMock()
    with patch.dict(
        "sys.modules",
        {
            "app.worker.tasks.process_document": MagicMock(
                process_document_task=mock_task
            )
        },
    ):
        await service.retry_failed_document(sample_inv_id, sample_doc_id)

    mock_task.delay.assert_called_once_with(
        str(sample_doc_id), str(sample_inv_id), None
    )


# ---------------------------------------------------------------------------
# retry_failed_document — retry_count reset on manual retry
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_manual_retry_resets_retry_count_to_zero(
    service, mock_db, sample_inv_id, sample_doc_id
):
    """Manual retry should reset retry_count to 0 for a fresh auto-retry budget."""
    doc = _make_failed_document(sample_doc_id, sample_inv_id, "preflight")
    doc.retry_count = 3  # Previously auto-retried 3 times

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = doc
    mock_db.execute = AsyncMock(return_value=result_mock)

    mock_task = MagicMock()
    with patch.dict(
        "sys.modules",
        {
            "app.worker.tasks.process_document": MagicMock(
                process_document_task=mock_task
            )
        },
    ):
        await service.retry_failed_document(sample_inv_id, sample_doc_id)

    assert doc.retry_count == 0
