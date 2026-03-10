"""Tests for process_document Celery task."""

import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def sample_doc_record():
    """Create a mock Document ORM object."""
    doc = MagicMock()
    doc.id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    doc.investigation_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    doc.filename = "test.pdf"
    doc.status = "queued"
    doc.extracted_text = None
    doc.error_message = None
    return doc


def _setup_mocks(mock_session_cls, mock_extraction_cls, mock_publisher_cls, doc_record):
    """Helper to setup common mock wiring."""
    mock_session = MagicMock()
    mock_session_cls.return_value.__enter__ = MagicMock(return_value=mock_session)
    mock_session_cls.return_value.__exit__ = MagicMock(return_value=False)
    mock_session.get.return_value = doc_record

    mock_extractor = MagicMock()
    mock_extraction_cls.return_value = mock_extractor

    mock_publisher = MagicMock()
    mock_publisher_cls.return_value = mock_publisher

    return mock_session, mock_extractor, mock_publisher


class TestProcessDocumentTask:
    @patch("app.worker.tasks.process_document.STORAGE_ROOT", Path("/tmp/storage"))
    @patch("app.worker.tasks.process_document.ChunkingService")
    @patch("app.worker.tasks.process_document.OllamaClient")
    @patch("app.worker.tasks.process_document.EventPublisher")
    @patch("app.worker.tasks.process_document.TextExtractionService")
    @patch("app.worker.tasks.process_document.SyncSessionLocal")
    def test_successful_full_pipeline(
        self,
        mock_session_cls,
        mock_extraction_cls,
        mock_publisher_cls,
        mock_ollama_cls,
        mock_chunking_cls,
        sample_doc_record,
    ):
        """Full pipeline: Ollama check → extract → chunk → complete."""
        from app.worker.tasks.process_document import process_document_task

        mock_session, mock_extractor, mock_publisher = _setup_mocks(
            mock_session_cls, mock_extraction_cls, mock_publisher_cls, sample_doc_record
        )
        mock_extractor.extract_text.return_value = "--- Page 1 ---\nHello world"

        mock_ollama = MagicMock()
        mock_ollama.check_available.return_value = True
        mock_ollama_cls.return_value = mock_ollama

        mock_chunking = MagicMock()
        mock_chunking.chunk_document.return_value = [MagicMock(), MagicMock()]
        mock_chunking_cls.return_value = mock_chunking

        process_document_task(
            str(sample_doc_record.id),
            str(sample_doc_record.investigation_id),
        )

        # Verify final status
        assert sample_doc_record.status == "complete"
        assert sample_doc_record.extracted_text == "--- Page 1 ---\nHello world"
        mock_session.commit.assert_called()

        # Verify chunking was called
        mock_chunking.chunk_document.assert_called_once()

        # Verify events: extracting_text, chunking, chunking_complete, complete
        assert mock_publisher.publish.call_count == 4
        calls = mock_publisher.publish.call_args_list
        assert calls[0][1]["event_type"] == "document.processing"
        assert calls[0][1]["payload"]["stage"] == "extracting_text"
        assert calls[1][1]["event_type"] == "document.processing"
        assert calls[1][1]["payload"]["stage"] == "chunking"
        assert calls[2][1]["event_type"] == "document.processing"
        assert calls[2][1]["payload"]["stage"] == "chunking_complete"
        assert calls[2][1]["payload"]["chunk_count"] == 2
        assert calls[3][1]["event_type"] == "document.complete"

        mock_publisher.close.assert_called_once()

    @patch("app.worker.tasks.process_document.STORAGE_ROOT", Path("/tmp/storage"))
    @patch("app.worker.tasks.process_document.ChunkingService")
    @patch("app.worker.tasks.process_document.OllamaClient")
    @patch("app.worker.tasks.process_document.EventPublisher")
    @patch("app.worker.tasks.process_document.TextExtractionService")
    @patch("app.worker.tasks.process_document.SyncSessionLocal")
    def test_extraction_failure(
        self,
        mock_session_cls,
        mock_extraction_cls,
        mock_publisher_cls,
        mock_ollama_cls,
        mock_chunking_cls,
        sample_doc_record,
    ):
        """Failed extraction: status → failed, error_message stored."""
        from app.worker.tasks.process_document import process_document_task

        mock_session, mock_extractor, mock_publisher = _setup_mocks(
            mock_session_cls, mock_extraction_cls, mock_publisher_cls, sample_doc_record
        )
        mock_extractor.extract_text.side_effect = RuntimeError("Corrupt PDF")

        mock_ollama = MagicMock()
        mock_ollama.check_available.return_value = True
        mock_ollama_cls.return_value = mock_ollama

        process_document_task(
            str(sample_doc_record.id),
            str(sample_doc_record.investigation_id),
        )

        assert sample_doc_record.status == "failed"
        assert "Corrupt PDF" in sample_doc_record.error_message

        calls = mock_publisher.publish.call_args_list
        assert any(c[1]["event_type"] == "document.failed" for c in calls)
        mock_publisher.close.assert_called_once()

    @patch("app.worker.tasks.process_document.STORAGE_ROOT", Path("/tmp/storage"))
    @patch("app.worker.tasks.process_document.ChunkingService")
    @patch("app.worker.tasks.process_document.OllamaClient")
    @patch("app.worker.tasks.process_document.EventPublisher")
    @patch("app.worker.tasks.process_document.TextExtractionService")
    @patch("app.worker.tasks.process_document.SyncSessionLocal")
    def test_document_not_found(
        self,
        mock_session_cls,
        mock_extraction_cls,
        mock_publisher_cls,
        mock_ollama_cls,
        mock_chunking_cls,
    ):
        """If document not found in DB, task should log error and return."""
        from app.worker.tasks.process_document import process_document_task

        mock_session = MagicMock()
        mock_session_cls.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_session_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_session.get.return_value = None

        mock_publisher = MagicMock()
        mock_publisher_cls.return_value = mock_publisher

        process_document_task("nonexistent-id", "inv-id")

        mock_publisher.publish.assert_not_called()
        mock_publisher.close.assert_called_once()

    @patch("app.worker.tasks.process_document.STORAGE_ROOT", Path("/tmp/storage"))
    @patch("app.worker.tasks.process_document.ChunkingService")
    @patch("app.worker.tasks.process_document.OllamaClient")
    @patch("app.worker.tasks.process_document.EventPublisher")
    @patch("app.worker.tasks.process_document.TextExtractionService")
    @patch("app.worker.tasks.process_document.SyncSessionLocal")
    def test_publish_failure_does_not_corrupt_status(
        self,
        mock_session_cls,
        mock_extraction_cls,
        mock_publisher_cls,
        mock_ollama_cls,
        mock_chunking_cls,
        sample_doc_record,
    ):
        """If event publishing fails, document status must remain correct."""
        from app.worker.tasks.process_document import process_document_task

        mock_session, mock_extractor, _ = _setup_mocks(
            mock_session_cls, mock_extraction_cls, mock_publisher_cls, sample_doc_record
        )
        mock_extractor.extract_text.return_value = "extracted text"

        mock_ollama = MagicMock()
        mock_ollama.check_available.return_value = True
        mock_ollama_cls.return_value = mock_ollama

        mock_chunking = MagicMock()
        mock_chunking.chunk_document.return_value = []
        mock_chunking_cls.return_value = mock_chunking

        mock_publisher = MagicMock()
        mock_publisher.publish.side_effect = ConnectionError("Redis unavailable")
        mock_publisher_cls.return_value = mock_publisher

        process_document_task(
            str(sample_doc_record.id),
            str(sample_doc_record.investigation_id),
        )

        assert sample_doc_record.status == "complete"
        assert sample_doc_record.extracted_text == "extracted text"
        assert sample_doc_record.error_message is None


class TestOllamaUnavailableHandling:
    @patch("app.worker.tasks.process_document.STORAGE_ROOT", Path("/tmp/storage"))
    @patch("app.worker.tasks.process_document.ChunkingService")
    @patch("app.worker.tasks.process_document.OllamaClient")
    @patch("app.worker.tasks.process_document.EventPublisher")
    @patch("app.worker.tasks.process_document.TextExtractionService")
    @patch("app.worker.tasks.process_document.SyncSessionLocal")
    def test_ollama_unavailable_fails_fast(
        self,
        mock_session_cls,
        mock_extraction_cls,
        mock_publisher_cls,
        mock_ollama_cls,
        mock_chunking_cls,
        sample_doc_record,
    ):
        """If Ollama is unavailable, fail document immediately without extracting text."""
        from app.worker.tasks.process_document import process_document_task

        mock_session = MagicMock()
        mock_session_cls.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_session_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_session.get.return_value = sample_doc_record

        mock_ollama = MagicMock()
        mock_ollama.check_available.return_value = False
        mock_ollama_cls.return_value = mock_ollama

        mock_publisher = MagicMock()
        mock_publisher_cls.return_value = mock_publisher

        process_document_task(
            str(sample_doc_record.id),
            str(sample_doc_record.investigation_id),
        )

        assert sample_doc_record.status == "failed"
        assert "Ollama" in sample_doc_record.error_message

        # Text extraction should NOT have been called
        mock_extraction_cls.return_value.extract_text.assert_not_called()

        # Failed event published
        calls = mock_publisher.publish.call_args_list
        assert any(c[1]["event_type"] == "document.failed" for c in calls)
        mock_publisher.close.assert_called_once()


class TestChunkingStage:
    @patch("app.worker.tasks.process_document.STORAGE_ROOT", Path("/tmp/storage"))
    @patch("app.worker.tasks.process_document.ChunkingService")
    @patch("app.worker.tasks.process_document.OllamaClient")
    @patch("app.worker.tasks.process_document.EventPublisher")
    @patch("app.worker.tasks.process_document.TextExtractionService")
    @patch("app.worker.tasks.process_document.SyncSessionLocal")
    def test_chunking_failure_sets_failed_status(
        self,
        mock_session_cls,
        mock_extraction_cls,
        mock_publisher_cls,
        mock_ollama_cls,
        mock_chunking_cls,
        sample_doc_record,
    ):
        """If chunking fails, document status should be 'failed'."""
        from app.worker.tasks.process_document import process_document_task

        mock_session, mock_extractor, mock_publisher = _setup_mocks(
            mock_session_cls, mock_extraction_cls, mock_publisher_cls, sample_doc_record
        )
        mock_extractor.extract_text.return_value = "--- Page 1 ---\nSome text"

        mock_ollama = MagicMock()
        mock_ollama.check_available.return_value = True
        mock_ollama_cls.return_value = mock_ollama

        mock_chunking = MagicMock()
        mock_chunking.chunk_document.side_effect = RuntimeError("DB error during chunking")
        mock_chunking_cls.return_value = mock_chunking

        process_document_task(
            str(sample_doc_record.id),
            str(sample_doc_record.investigation_id),
        )

        assert sample_doc_record.status == "failed"
        assert "Chunking failed" in sample_doc_record.error_message

        # Rollback must be called to expunge pending chunks before committing failure
        mock_session.rollback.assert_called_once()

        calls = mock_publisher.publish.call_args_list
        assert any(c[1]["event_type"] == "document.failed" for c in calls)
        mock_publisher.close.assert_called_once()

    @patch("app.worker.tasks.process_document.STORAGE_ROOT", Path("/tmp/storage"))
    @patch("app.worker.tasks.process_document.ChunkingService")
    @patch("app.worker.tasks.process_document.OllamaClient")
    @patch("app.worker.tasks.process_document.EventPublisher")
    @patch("app.worker.tasks.process_document.TextExtractionService")
    @patch("app.worker.tasks.process_document.SyncSessionLocal")
    def test_chunking_sse_events_published(
        self,
        mock_session_cls,
        mock_extraction_cls,
        mock_publisher_cls,
        mock_ollama_cls,
        mock_chunking_cls,
        sample_doc_record,
    ):
        """Verify chunking stage publishes correct SSE events."""
        from app.worker.tasks.process_document import process_document_task

        mock_session, mock_extractor, mock_publisher = _setup_mocks(
            mock_session_cls, mock_extraction_cls, mock_publisher_cls, sample_doc_record
        )
        mock_extractor.extract_text.return_value = "--- Page 1 ---\nText"

        mock_ollama = MagicMock()
        mock_ollama.check_available.return_value = True
        mock_ollama_cls.return_value = mock_ollama

        mock_chunking = MagicMock()
        mock_chunking.chunk_document.return_value = [MagicMock()] * 5
        mock_chunking_cls.return_value = mock_chunking

        process_document_task(
            str(sample_doc_record.id),
            str(sample_doc_record.investigation_id),
        )

        calls = mock_publisher.publish.call_args_list

        # Find chunking events
        chunking_start = [
            c
            for c in calls
            if c[1]["event_type"] == "document.processing"
            and c[1]["payload"].get("stage") == "chunking"
        ]
        chunking_complete = [
            c
            for c in calls
            if c[1]["event_type"] == "document.processing"
            and c[1]["payload"].get("stage") == "chunking_complete"
        ]

        assert len(chunking_start) == 1
        assert chunking_start[0][1]["payload"]["progress"] == 0.0

        assert len(chunking_complete) == 1
        assert chunking_complete[0][1]["payload"]["chunk_count"] == 5

    @patch("app.worker.tasks.process_document.STORAGE_ROOT", Path("/tmp/storage"))
    @patch("app.worker.tasks.process_document.ChunkingService")
    @patch("app.worker.tasks.process_document.OllamaClient")
    @patch("app.worker.tasks.process_document.EventPublisher")
    @patch("app.worker.tasks.process_document.TextExtractionService")
    @patch("app.worker.tasks.process_document.SyncSessionLocal")
    def test_status_transitions_through_chunking(
        self,
        mock_session_cls,
        mock_extraction_cls,
        mock_publisher_cls,
        mock_ollama_cls,
        mock_chunking_cls,
        sample_doc_record,
    ):
        """Verify status goes through: queued → extracting_text → chunking → complete."""
        from app.worker.tasks.process_document import process_document_task

        status_log = []
        original_setattr = type(sample_doc_record).__setattr__

        def track_status(self, name, value):
            if name == "status":
                status_log.append(value)
            original_setattr(self, name, value)

        type(sample_doc_record).__setattr__ = track_status

        mock_session, mock_extractor, mock_publisher = _setup_mocks(
            mock_session_cls, mock_extraction_cls, mock_publisher_cls, sample_doc_record
        )
        mock_extractor.extract_text.return_value = "--- Page 1 ---\nText"

        mock_ollama = MagicMock()
        mock_ollama.check_available.return_value = True
        mock_ollama_cls.return_value = mock_ollama

        mock_chunking = MagicMock()
        mock_chunking.chunk_document.return_value = [MagicMock()]
        mock_chunking_cls.return_value = mock_chunking

        try:
            process_document_task(
                str(sample_doc_record.id),
                str(sample_doc_record.investigation_id),
            )
        finally:
            type(sample_doc_record).__setattr__ = original_setattr

        assert "extracting_text" in status_log
        assert "chunking" in status_log
        assert "complete" in status_log
        # Verify order
        et_idx = status_log.index("extracting_text")
        ch_idx = status_log.index("chunking")
        co_idx = status_log.index("complete")
        assert et_idx < ch_idx < co_idx
