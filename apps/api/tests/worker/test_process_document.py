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


class TestProcessDocumentTask:
    @patch("app.worker.tasks.process_document.STORAGE_ROOT", Path("/tmp/storage"))
    @patch("app.worker.tasks.process_document.EventPublisher")
    @patch("app.worker.tasks.process_document.TextExtractionService")
    @patch("app.worker.tasks.process_document.SyncSessionLocal")
    def test_successful_extraction(
        self,
        mock_session_cls,
        mock_extraction_cls,
        mock_publisher_cls,
        sample_doc_record,
    ):
        """Successful extraction: status → extracting_text → complete, text stored."""
        from app.worker.tasks.process_document import process_document_task

        # Setup mocks
        mock_session = MagicMock()
        mock_session_cls.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_session_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_session.get.return_value = sample_doc_record

        mock_extractor = MagicMock()
        mock_extractor.extract_text.return_value = "--- Page 1 ---\nHello world"
        mock_extraction_cls.return_value = mock_extractor

        mock_publisher = MagicMock()
        mock_publisher_cls.return_value = mock_publisher

        # Execute
        process_document_task(
            str(sample_doc_record.id),
            str(sample_doc_record.investigation_id),
        )

        # Verify status transitions and text stored
        assert sample_doc_record.status == "complete"
        assert sample_doc_record.extracted_text == "--- Page 1 ---\nHello world"
        mock_session.commit.assert_called()

        # Verify events published
        assert mock_publisher.publish.call_count == 2  # processing + complete
        calls = mock_publisher.publish.call_args_list
        assert calls[0][1]["event_type"] == "document.processing"
        assert calls[1][1]["event_type"] == "document.complete"

        # Verify publisher closed
        mock_publisher.close.assert_called_once()

    @patch("app.worker.tasks.process_document.STORAGE_ROOT", Path("/tmp/storage"))
    @patch("app.worker.tasks.process_document.EventPublisher")
    @patch("app.worker.tasks.process_document.TextExtractionService")
    @patch("app.worker.tasks.process_document.SyncSessionLocal")
    def test_extraction_failure(
        self,
        mock_session_cls,
        mock_extraction_cls,
        mock_publisher_cls,
        sample_doc_record,
    ):
        """Failed extraction: status → failed, error_message stored, failed event published."""
        from app.worker.tasks.process_document import process_document_task

        mock_session = MagicMock()
        mock_session_cls.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_session_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_session.get.return_value = sample_doc_record

        mock_extractor = MagicMock()
        mock_extractor.extract_text.side_effect = RuntimeError("Corrupt PDF")
        mock_extraction_cls.return_value = mock_extractor

        mock_publisher = MagicMock()
        mock_publisher_cls.return_value = mock_publisher

        # Execute
        process_document_task(
            str(sample_doc_record.id),
            str(sample_doc_record.investigation_id),
        )

        # Verify failure handling
        assert sample_doc_record.status == "failed"
        assert "Corrupt PDF" in sample_doc_record.error_message
        mock_session.commit.assert_called()

        # Verify failed event published
        calls = mock_publisher.publish.call_args_list
        # Should have processing event + failed event
        assert any(c[1]["event_type"] == "document.failed" for c in calls)

        # Verify publisher closed
        mock_publisher.close.assert_called_once()

    @patch("app.worker.tasks.process_document.STORAGE_ROOT", Path("/tmp/storage"))
    @patch("app.worker.tasks.process_document.EventPublisher")
    @patch("app.worker.tasks.process_document.TextExtractionService")
    @patch("app.worker.tasks.process_document.SyncSessionLocal")
    def test_document_not_found(
        self,
        mock_session_cls,
        mock_extraction_cls,
        mock_publisher_cls,
    ):
        """If document not found in DB, task should log error and return."""
        from app.worker.tasks.process_document import process_document_task

        mock_session = MagicMock()
        mock_session_cls.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_session_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_session.get.return_value = None  # Not found

        mock_publisher = MagicMock()
        mock_publisher_cls.return_value = mock_publisher

        # Should not raise
        process_document_task("nonexistent-id", "inv-id")

        # No events published, no commit
        mock_publisher.publish.assert_not_called()

        # Publisher still closed via finally
        mock_publisher.close.assert_called_once()

    @patch("app.worker.tasks.process_document.STORAGE_ROOT", Path("/tmp/storage"))
    @patch("app.worker.tasks.process_document.EventPublisher")
    @patch("app.worker.tasks.process_document.TextExtractionService")
    @patch("app.worker.tasks.process_document.SyncSessionLocal")
    def test_publish_failure_does_not_corrupt_status(
        self,
        mock_session_cls,
        mock_extraction_cls,
        mock_publisher_cls,
        sample_doc_record,
    ):
        """If event publishing fails, document status must remain correct (complete, not failed)."""
        from app.worker.tasks.process_document import process_document_task

        mock_session = MagicMock()
        mock_session_cls.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_session_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_session.get.return_value = sample_doc_record

        mock_extractor = MagicMock()
        mock_extractor.extract_text.return_value = "extracted text"
        mock_extraction_cls.return_value = mock_extractor

        # Make all publish calls fail
        mock_publisher = MagicMock()
        mock_publisher.publish.side_effect = ConnectionError("Redis unavailable")
        mock_publisher_cls.return_value = mock_publisher

        # Should not raise — publishes are best-effort
        process_document_task(
            str(sample_doc_record.id),
            str(sample_doc_record.investigation_id),
        )

        # Document status must still be "complete" despite publish failures
        assert sample_doc_record.status == "complete"
        assert sample_doc_record.extracted_text == "extracted text"
        assert sample_doc_record.error_message is None
