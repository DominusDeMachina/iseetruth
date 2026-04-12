"""Tests for process_document Celery task."""

import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.services.extraction import ExtractionSummary


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
    doc.failed_stage = None
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
    @patch("app.worker.tasks.process_document.EntityExtractionService")
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
        mock_entity_svc_cls,
        sample_doc_record,
    ):
        """Full pipeline: Ollama check → extract text → chunk → extract entities → complete."""
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

        mock_entity_svc = MagicMock()
        mock_entity_svc.extract_from_chunks.return_value = ExtractionSummary(3, 1, 2)
        mock_entity_svc_cls.return_value = mock_entity_svc

        process_document_task(
            str(sample_doc_record.id),
            str(sample_doc_record.investigation_id),
        )

        # Verify final status
        assert sample_doc_record.status == "complete"
        assert sample_doc_record.extracted_text == "--- Page 1 ---\nHello world"
        mock_session.commit.assert_called()

        # Verify chunking and extraction were called
        mock_chunking.chunk_document.assert_called_once()
        mock_entity_svc.extract_from_chunks.assert_called_once()

        # Verify events: extracting_text, chunking, chunking_complete,
        #                extracting_entities, document.complete (5 total minimum)
        calls = mock_publisher.publish.call_args_list
        event_types = [c[1]["event_type"] for c in calls]
        stages = [
            c[1]["payload"].get("stage")
            for c in calls
            if c[1]["event_type"] == "document.processing"
        ]

        assert "extracting_text" in stages
        assert "chunking" in stages
        assert "chunking_complete" in stages
        assert "extracting_entities" in stages
        assert "document.complete" in event_types

        # Verify document.complete includes entity/relationship counts
        complete_events = [c for c in calls if c[1]["event_type"] == "document.complete"]
        assert complete_events[0][1]["payload"]["entity_count"] == 3
        assert complete_events[0][1]["payload"]["relationship_count"] == 1

        mock_publisher.close.assert_called_once()

    @patch("app.worker.tasks.process_document.STORAGE_ROOT", Path("/tmp/storage"))
    @patch("app.worker.tasks.process_document.EntityExtractionService")
    @patch("app.worker.tasks.process_document.ChunkingService")
    @patch("app.worker.tasks.process_document.OllamaClient")
    @patch("app.worker.tasks.process_document.EventPublisher")
    @patch("app.worker.tasks.process_document.TextExtractionService")
    @patch("app.worker.tasks.process_document.SyncSessionLocal")
    def test_text_extraction_failure(
        self,
        mock_session_cls,
        mock_extraction_cls,
        mock_publisher_cls,
        mock_ollama_cls,
        mock_chunking_cls,
        mock_entity_svc_cls,
        sample_doc_record,
    ):
        """Failed text extraction: status → failed, error_message stored."""
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
    @patch("app.worker.tasks.process_document.EntityExtractionService")
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
        mock_entity_svc_cls,
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
    @patch("app.worker.tasks.process_document.EntityExtractionService")
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
        mock_entity_svc_cls,
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

        mock_entity_svc = MagicMock()
        mock_entity_svc.extract_from_chunks.return_value = ExtractionSummary(0, 0, 0)
        mock_entity_svc_cls.return_value = mock_entity_svc

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
    @patch("app.worker.tasks.process_document.EntityExtractionService")
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
        mock_entity_svc_cls,
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

        # Story 6.3: document stays queued when Ollama is unavailable (not failed)
        assert sample_doc_record.status == "queued"
        assert "Waiting for LLM service" in sample_doc_record.error_message

        # Text extraction should NOT have been called
        mock_extraction_cls.return_value.extract_text.assert_not_called()

        # Failed event published
        calls = mock_publisher.publish.call_args_list
        assert any(c[1]["event_type"] == "document.failed" for c in calls)
        mock_publisher.close.assert_called_once()


class TestChunkingStage:
    @patch("app.worker.tasks.process_document.STORAGE_ROOT", Path("/tmp/storage"))
    @patch("app.worker.tasks.process_document.EntityExtractionService")
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
        mock_entity_svc_cls,
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
    @patch("app.worker.tasks.process_document.EntityExtractionService")
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
        mock_entity_svc_cls,
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

        mock_entity_svc = MagicMock()
        mock_entity_svc.extract_from_chunks.return_value = ExtractionSummary(0, 0, 5)
        mock_entity_svc_cls.return_value = mock_entity_svc

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
    @patch("app.worker.tasks.process_document.EntityExtractionService")
    @patch("app.worker.tasks.process_document.ChunkingService")
    @patch("app.worker.tasks.process_document.OllamaClient")
    @patch("app.worker.tasks.process_document.EventPublisher")
    @patch("app.worker.tasks.process_document.TextExtractionService")
    @patch("app.worker.tasks.process_document.SyncSessionLocal")
    def test_status_transitions_through_all_stages(
        self,
        mock_session_cls,
        mock_extraction_cls,
        mock_publisher_cls,
        mock_ollama_cls,
        mock_chunking_cls,
        mock_entity_svc_cls,
        sample_doc_record,
    ):
        """Verify status goes through: extracting_text → chunking → extracting_entities → complete."""
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

        mock_entity_svc = MagicMock()
        mock_entity_svc.extract_from_chunks.return_value = ExtractionSummary(2, 1, 1)
        mock_entity_svc_cls.return_value = mock_entity_svc

        try:
            process_document_task(
                str(sample_doc_record.id),
                str(sample_doc_record.investigation_id),
            )
        finally:
            type(sample_doc_record).__setattr__ = original_setattr

        assert "extracting_text" in status_log
        assert "chunking" in status_log
        assert "extracting_entities" in status_log
        assert "complete" in status_log
        # Verify order
        et_idx = status_log.index("extracting_text")
        ch_idx = status_log.index("chunking")
        ee_idx = status_log.index("extracting_entities")
        co_idx = status_log.index("complete")
        assert et_idx < ch_idx < ee_idx < co_idx


class TestEntityExtractionStage:
    @patch("app.worker.tasks.process_document.STORAGE_ROOT", Path("/tmp/storage"))
    @patch("app.worker.tasks.process_document.EntityExtractionService")
    @patch("app.worker.tasks.process_document.ChunkingService")
    @patch("app.worker.tasks.process_document.OllamaClient")
    @patch("app.worker.tasks.process_document.EventPublisher")
    @patch("app.worker.tasks.process_document.TextExtractionService")
    @patch("app.worker.tasks.process_document.SyncSessionLocal")
    def test_extracting_entities_stage_runs_after_chunking(
        self,
        mock_session_cls,
        mock_extraction_cls,
        mock_publisher_cls,
        mock_ollama_cls,
        mock_chunking_cls,
        mock_entity_svc_cls,
        sample_doc_record,
    ):
        """Pipeline runs extracting_entities stage after chunking."""
        from app.worker.tasks.process_document import process_document_task

        mock_session, mock_extractor, mock_publisher = _setup_mocks(
            mock_session_cls, mock_extraction_cls, mock_publisher_cls, sample_doc_record
        )
        mock_extractor.extract_text.return_value = "text"

        mock_ollama = MagicMock()
        mock_ollama.check_available.return_value = True
        mock_ollama_cls.return_value = mock_ollama

        mock_chunking = MagicMock()
        chunks = [MagicMock(), MagicMock()]
        mock_chunking.chunk_document.return_value = chunks
        mock_chunking_cls.return_value = mock_chunking

        mock_entity_svc = MagicMock()
        mock_entity_svc.extract_from_chunks.return_value = ExtractionSummary(3, 1, 2)
        mock_entity_svc_cls.return_value = mock_entity_svc

        process_document_task(
            str(sample_doc_record.id),
            str(sample_doc_record.investigation_id),
        )

        assert sample_doc_record.status == "complete"
        mock_entity_svc.extract_from_chunks.assert_called_once()

        calls = mock_publisher.publish.call_args_list
        extracting_entities_events = [
            c for c in calls
            if c[1]["event_type"] == "document.processing"
            and c[1]["payload"].get("stage") == "extracting_entities"
        ]
        assert len(extracting_entities_events) == 1
        assert extracting_entities_events[0][1]["payload"]["chunk_count"] == 2

    @patch("app.worker.tasks.process_document.STORAGE_ROOT", Path("/tmp/storage"))
    @patch("app.worker.tasks.process_document.EntityExtractionService")
    @patch("app.worker.tasks.process_document.ChunkingService")
    @patch("app.worker.tasks.process_document.OllamaClient")
    @patch("app.worker.tasks.process_document.EventPublisher")
    @patch("app.worker.tasks.process_document.TextExtractionService")
    @patch("app.worker.tasks.process_document.SyncSessionLocal")
    def test_entity_discovered_sse_events_published(
        self,
        mock_session_cls,
        mock_extraction_cls,
        mock_publisher_cls,
        mock_ollama_cls,
        mock_chunking_cls,
        mock_entity_svc_cls,
        sample_doc_record,
    ):
        """entity.discovered SSE events are published during extraction via callback."""
        from app.llm.schemas import EntityType, ExtractedEntity
        from app.worker.tasks.process_document import process_document_task

        mock_session, mock_extractor, mock_publisher = _setup_mocks(
            mock_session_cls, mock_extraction_cls, mock_publisher_cls, sample_doc_record
        )
        mock_extractor.extract_text.return_value = "text"

        mock_ollama = MagicMock()
        mock_ollama.check_available.return_value = True
        mock_ollama_cls.return_value = mock_ollama

        mock_chunking = MagicMock()
        mock_chunking.chunk_document.return_value = [MagicMock()]
        mock_chunking_cls.return_value = mock_chunking

        # Simulate extract_from_chunks calling the on_entity_discovered callback
        def fake_extract(chunks, investigation_id, on_entity_discovered=None):
            if on_entity_discovered:
                entity = ExtractedEntity(name="John Smith", type=EntityType.person, confidence=0.9)
                on_entity_discovered(entity)
            return ExtractionSummary(1, 0, 1)

        mock_entity_svc = MagicMock()
        mock_entity_svc.extract_from_chunks.side_effect = fake_extract
        mock_entity_svc_cls.return_value = mock_entity_svc

        process_document_task(
            str(sample_doc_record.id),
            str(sample_doc_record.investigation_id),
        )

        calls = mock_publisher.publish.call_args_list
        entity_discovered_events = [
            c for c in calls if c[1]["event_type"] == "entity.discovered"
        ]
        assert len(entity_discovered_events) == 1
        assert entity_discovered_events[0][1]["payload"]["entity_name"] == "John Smith"
        assert entity_discovered_events[0][1]["payload"]["entity_type"] == "person"

    @patch("app.worker.tasks.process_document.STORAGE_ROOT", Path("/tmp/storage"))
    @patch("app.worker.tasks.process_document.EntityExtractionService")
    @patch("app.worker.tasks.process_document.ChunkingService")
    @patch("app.worker.tasks.process_document.OllamaClient")
    @patch("app.worker.tasks.process_document.EventPublisher")
    @patch("app.worker.tasks.process_document.TextExtractionService")
    @patch("app.worker.tasks.process_document.SyncSessionLocal")
    def test_extraction_failure_marks_document_failed(
        self,
        mock_session_cls,
        mock_extraction_cls,
        mock_publisher_cls,
        mock_ollama_cls,
        mock_chunking_cls,
        mock_entity_svc_cls,
        sample_doc_record,
    ):
        """Extraction failure → document.status = failed, document.failed SSE published."""
        from app.worker.tasks.process_document import process_document_task

        mock_session, mock_extractor, mock_publisher = _setup_mocks(
            mock_session_cls, mock_extraction_cls, mock_publisher_cls, sample_doc_record
        )
        mock_extractor.extract_text.return_value = "text"

        mock_ollama = MagicMock()
        mock_ollama.check_available.return_value = True
        mock_ollama_cls.return_value = mock_ollama

        mock_chunking = MagicMock()
        mock_chunking.chunk_document.return_value = [MagicMock()]
        mock_chunking_cls.return_value = mock_chunking

        mock_entity_svc = MagicMock()
        mock_entity_svc.extract_from_chunks.side_effect = RuntimeError("neo4j down")
        mock_entity_svc_cls.return_value = mock_entity_svc

        process_document_task(
            str(sample_doc_record.id),
            str(sample_doc_record.investigation_id),
        )

        assert sample_doc_record.status == "failed"
        assert "Entity extraction failed" in sample_doc_record.error_message

        calls = mock_publisher.publish.call_args_list
        assert any(c[1]["event_type"] == "document.failed" for c in calls)
        # Verify rollback was called before failure commit
        mock_session.rollback.assert_called()

    @patch("app.worker.tasks.process_document.STORAGE_ROOT", Path("/tmp/storage"))
    @patch("app.worker.tasks.process_document.EntityExtractionService")
    @patch("app.worker.tasks.process_document.ChunkingService")
    @patch("app.worker.tasks.process_document.OllamaClient")
    @patch("app.worker.tasks.process_document.EventPublisher")
    @patch("app.worker.tasks.process_document.TextExtractionService")
    @patch("app.worker.tasks.process_document.SyncSessionLocal")
    def test_document_complete_includes_entity_counts(
        self,
        mock_session_cls,
        mock_extraction_cls,
        mock_publisher_cls,
        mock_ollama_cls,
        mock_chunking_cls,
        mock_entity_svc_cls,
        sample_doc_record,
    ):
        """document.complete event includes entity_count and relationship_count."""
        from app.worker.tasks.process_document import process_document_task

        mock_session, mock_extractor, mock_publisher = _setup_mocks(
            mock_session_cls, mock_extraction_cls, mock_publisher_cls, sample_doc_record
        )
        mock_extractor.extract_text.return_value = "text"

        mock_ollama = MagicMock()
        mock_ollama.check_available.return_value = True
        mock_ollama_cls.return_value = mock_ollama

        mock_chunking = MagicMock()
        mock_chunking.chunk_document.return_value = [MagicMock()]
        mock_chunking_cls.return_value = mock_chunking

        mock_entity_svc = MagicMock()
        mock_entity_svc.extract_from_chunks.return_value = ExtractionSummary(5, 3, 1)
        mock_entity_svc_cls.return_value = mock_entity_svc

        process_document_task(
            str(sample_doc_record.id),
            str(sample_doc_record.investigation_id),
        )

        calls = mock_publisher.publish.call_args_list
        complete_events = [c for c in calls if c[1]["event_type"] == "document.complete"]
        assert len(complete_events) == 1
        payload = complete_events[0][1]["payload"]
        assert payload["entity_count"] == 5
        assert payload["relationship_count"] == 3


class TestFailedStageRecording:
    """Tests for Story 6.1: failed_stage is recorded at each failure point."""

    @patch("app.worker.tasks.process_document.STORAGE_ROOT", Path("/tmp/storage"))
    @patch("app.worker.tasks.process_document.EntityExtractionService")
    @patch("app.worker.tasks.process_document.ChunkingService")
    @patch("app.worker.tasks.process_document.OllamaClient")
    @patch("app.worker.tasks.process_document.EventPublisher")
    @patch("app.worker.tasks.process_document.TextExtractionService")
    @patch("app.worker.tasks.process_document.SyncSessionLocal")
    def test_preflight_failure_sets_failed_stage(
        self,
        mock_session_cls,
        mock_extraction_cls,
        mock_publisher_cls,
        mock_ollama_cls,
        mock_chunking_cls,
        mock_entity_svc_cls,
        sample_doc_record,
    ):
        """Ollama unavailable → failed_stage = 'preflight'."""
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

        # Story 6.3: document stays queued when Ollama unavailable at preflight
        assert sample_doc_record.status == "queued"
        assert sample_doc_record.failed_stage == "preflight"

        # SSE event includes stage
        calls = mock_publisher.publish.call_args_list
        failed_events = [c for c in calls if c[1]["event_type"] == "document.failed"]
        assert len(failed_events) == 1
        assert failed_events[0][1]["payload"]["stage"] == "preflight"

    @patch("app.worker.tasks.process_document.STORAGE_ROOT", Path("/tmp/storage"))
    @patch("app.worker.tasks.process_document.EntityExtractionService")
    @patch("app.worker.tasks.process_document.ChunkingService")
    @patch("app.worker.tasks.process_document.OllamaClient")
    @patch("app.worker.tasks.process_document.EventPublisher")
    @patch("app.worker.tasks.process_document.TextExtractionService")
    @patch("app.worker.tasks.process_document.SyncSessionLocal")
    def test_text_extraction_failure_sets_failed_stage(
        self,
        mock_session_cls,
        mock_extraction_cls,
        mock_publisher_cls,
        mock_ollama_cls,
        mock_chunking_cls,
        mock_entity_svc_cls,
        sample_doc_record,
    ):
        """Text extraction failure → failed_stage = 'extracting_text'."""
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
        assert sample_doc_record.failed_stage == "extracting_text"

        calls = mock_publisher.publish.call_args_list
        failed_events = [c for c in calls if c[1]["event_type"] == "document.failed"]
        assert len(failed_events) == 1
        assert failed_events[0][1]["payload"]["stage"] == "extracting_text"

    @patch("app.worker.tasks.process_document.STORAGE_ROOT", Path("/tmp/storage"))
    @patch("app.worker.tasks.process_document.EntityExtractionService")
    @patch("app.worker.tasks.process_document.ChunkingService")
    @patch("app.worker.tasks.process_document.OllamaClient")
    @patch("app.worker.tasks.process_document.EventPublisher")
    @patch("app.worker.tasks.process_document.TextExtractionService")
    @patch("app.worker.tasks.process_document.SyncSessionLocal")
    def test_chunking_failure_sets_failed_stage(
        self,
        mock_session_cls,
        mock_extraction_cls,
        mock_publisher_cls,
        mock_ollama_cls,
        mock_chunking_cls,
        mock_entity_svc_cls,
        sample_doc_record,
    ):
        """Chunking failure → failed_stage = 'chunking'."""
        from app.worker.tasks.process_document import process_document_task

        mock_session, mock_extractor, mock_publisher = _setup_mocks(
            mock_session_cls, mock_extraction_cls, mock_publisher_cls, sample_doc_record
        )
        mock_extractor.extract_text.return_value = "text"

        mock_ollama = MagicMock()
        mock_ollama.check_available.return_value = True
        mock_ollama_cls.return_value = mock_ollama

        mock_chunking = MagicMock()
        mock_chunking.chunk_document.side_effect = RuntimeError("DB error")
        mock_chunking_cls.return_value = mock_chunking

        process_document_task(
            str(sample_doc_record.id),
            str(sample_doc_record.investigation_id),
        )

        assert sample_doc_record.status == "failed"
        assert sample_doc_record.failed_stage == "chunking"

        calls = mock_publisher.publish.call_args_list
        failed_events = [c for c in calls if c[1]["event_type"] == "document.failed"]
        assert len(failed_events) == 1
        assert failed_events[0][1]["payload"]["stage"] == "chunking"

    @patch("app.worker.tasks.process_document.STORAGE_ROOT", Path("/tmp/storage"))
    @patch("app.worker.tasks.process_document.EntityExtractionService")
    @patch("app.worker.tasks.process_document.ChunkingService")
    @patch("app.worker.tasks.process_document.OllamaClient")
    @patch("app.worker.tasks.process_document.EventPublisher")
    @patch("app.worker.tasks.process_document.TextExtractionService")
    @patch("app.worker.tasks.process_document.SyncSessionLocal")
    def test_entity_extraction_failure_sets_failed_stage(
        self,
        mock_session_cls,
        mock_extraction_cls,
        mock_publisher_cls,
        mock_ollama_cls,
        mock_chunking_cls,
        mock_entity_svc_cls,
        sample_doc_record,
    ):
        """Entity extraction failure → failed_stage = 'extracting_entities'."""
        from app.worker.tasks.process_document import process_document_task

        mock_session, mock_extractor, mock_publisher = _setup_mocks(
            mock_session_cls, mock_extraction_cls, mock_publisher_cls, sample_doc_record
        )
        mock_extractor.extract_text.return_value = "text"

        mock_ollama = MagicMock()
        mock_ollama.check_available.return_value = True
        mock_ollama_cls.return_value = mock_ollama

        mock_chunking = MagicMock()
        mock_chunking.chunk_document.return_value = [MagicMock()]
        mock_chunking_cls.return_value = mock_chunking

        mock_entity_svc = MagicMock()
        mock_entity_svc.extract_from_chunks.side_effect = RuntimeError("Neo4j down")
        mock_entity_svc_cls.return_value = mock_entity_svc

        process_document_task(
            str(sample_doc_record.id),
            str(sample_doc_record.investigation_id),
        )

        assert sample_doc_record.status == "failed"
        assert sample_doc_record.failed_stage == "extracting_entities"

        calls = mock_publisher.publish.call_args_list
        failed_events = [c for c in calls if c[1]["event_type"] == "document.failed"]
        assert len(failed_events) == 1
        assert failed_events[0][1]["payload"]["stage"] == "extracting_entities"

    @patch("app.worker.tasks.process_document.EmbeddingService")
    @patch("app.worker.tasks.process_document.STORAGE_ROOT", Path("/tmp/storage"))
    @patch("app.worker.tasks.process_document.EntityExtractionService")
    @patch("app.worker.tasks.process_document.ChunkingService")
    @patch("app.worker.tasks.process_document.OllamaClient")
    @patch("app.worker.tasks.process_document.EventPublisher")
    @patch("app.worker.tasks.process_document.TextExtractionService")
    @patch("app.worker.tasks.process_document.SyncSessionLocal")
    def test_embedding_failure_sets_failed_stage(
        self,
        mock_session_cls,
        mock_extraction_cls,
        mock_publisher_cls,
        mock_ollama_cls,
        mock_chunking_cls,
        mock_entity_svc_cls,
        mock_embedding_svc_cls,
        sample_doc_record,
    ):
        """Embedding failure → failed_stage = 'embedding'."""
        from app.worker.tasks.process_document import process_document_task

        mock_session, mock_extractor, mock_publisher = _setup_mocks(
            mock_session_cls, mock_extraction_cls, mock_publisher_cls, sample_doc_record
        )
        mock_extractor.extract_text.return_value = "text"

        mock_ollama = MagicMock()
        mock_ollama.check_available.return_value = True
        mock_ollama_cls.return_value = mock_ollama

        mock_chunking = MagicMock()
        mock_chunking.chunk_document.return_value = [MagicMock()]
        mock_chunking_cls.return_value = mock_chunking

        mock_entity_svc = MagicMock()
        mock_entity_svc.extract_from_chunks.return_value = ExtractionSummary(1, 0, 1)
        mock_entity_svc_cls.return_value = mock_entity_svc

        mock_embedding_svc = MagicMock()
        mock_embedding_svc.embed_chunks.side_effect = RuntimeError("Qdrant unreachable")
        mock_embedding_svc_cls.return_value = mock_embedding_svc

        process_document_task(
            str(sample_doc_record.id),
            str(sample_doc_record.investigation_id),
        )

        assert sample_doc_record.status == "failed"
        assert sample_doc_record.failed_stage == "embedding"

        calls = mock_publisher.publish.call_args_list
        failed_events = [c for c in calls if c[1]["event_type"] == "document.failed"]
        assert len(failed_events) == 1
        assert failed_events[0][1]["payload"]["stage"] == "embedding"

    @patch("app.worker.tasks.process_document.STORAGE_ROOT", Path("/tmp/storage"))
    @patch("app.worker.tasks.process_document.EntityExtractionService")
    @patch("app.worker.tasks.process_document.ChunkingService")
    @patch("app.worker.tasks.process_document.OllamaClient")
    @patch("app.worker.tasks.process_document.EventPublisher")
    @patch("app.worker.tasks.process_document.TextExtractionService")
    @patch("app.worker.tasks.process_document.SyncSessionLocal")
    def test_successful_processing_does_not_set_failed_stage(
        self,
        mock_session_cls,
        mock_extraction_cls,
        mock_publisher_cls,
        mock_ollama_cls,
        mock_chunking_cls,
        mock_entity_svc_cls,
        sample_doc_record,
    ):
        """Successful processing → failed_stage remains None."""
        from app.worker.tasks.process_document import process_document_task

        mock_session, mock_extractor, mock_publisher = _setup_mocks(
            mock_session_cls, mock_extraction_cls, mock_publisher_cls, sample_doc_record
        )
        mock_extractor.extract_text.return_value = "text"

        mock_ollama = MagicMock()
        mock_ollama.check_available.return_value = True
        mock_ollama_cls.return_value = mock_ollama

        mock_chunking = MagicMock()
        mock_chunking.chunk_document.return_value = [MagicMock()]
        mock_chunking_cls.return_value = mock_chunking

        mock_entity_svc = MagicMock()
        mock_entity_svc.extract_from_chunks.return_value = ExtractionSummary(1, 0, 1)
        mock_entity_svc_cls.return_value = mock_entity_svc

        process_document_task(
            str(sample_doc_record.id),
            str(sample_doc_record.investigation_id),
        )

        assert sample_doc_record.status == "complete"
        assert sample_doc_record.failed_stage is None


class TestResumeFromStage:
    """Tests for Story 6.1: resume_from_stage parameter skips completed stages."""

    @patch("app.worker.tasks.process_document.STORAGE_ROOT", Path("/tmp/storage"))
    @patch("app.worker.tasks.process_document.EntityExtractionService")
    @patch("app.worker.tasks.process_document.ChunkingService")
    @patch("app.worker.tasks.process_document.OllamaClient")
    @patch("app.worker.tasks.process_document.EventPublisher")
    @patch("app.worker.tasks.process_document.TextExtractionService")
    @patch("app.worker.tasks.process_document.SyncSessionLocal")
    def test_resume_from_chunking_skips_text_extraction(
        self,
        mock_session_cls,
        mock_extraction_cls,
        mock_publisher_cls,
        mock_ollama_cls,
        mock_chunking_cls,
        mock_entity_svc_cls,
        sample_doc_record,
    ):
        """resume_from_stage='chunking' skips text extraction, uses existing extracted_text."""
        from app.worker.tasks.process_document import process_document_task

        sample_doc_record.extracted_text = "Previously extracted text"

        mock_session, mock_extractor, mock_publisher = _setup_mocks(
            mock_session_cls, mock_extraction_cls, mock_publisher_cls, sample_doc_record
        )

        mock_ollama = MagicMock()
        mock_ollama.check_available.return_value = True
        mock_ollama_cls.return_value = mock_ollama

        mock_chunking = MagicMock()
        mock_chunking.chunk_document.return_value = [MagicMock()]
        mock_chunking_cls.return_value = mock_chunking

        mock_entity_svc = MagicMock()
        mock_entity_svc.extract_from_chunks.return_value = ExtractionSummary(1, 0, 1)
        mock_entity_svc_cls.return_value = mock_entity_svc

        process_document_task(
            str(sample_doc_record.id),
            str(sample_doc_record.investigation_id),
            resume_from_stage="chunking",
        )

        # Text extraction should NOT have been called
        mock_extractor.extract_text.assert_not_called()

        # Chunking should be called with existing text
        mock_chunking.chunk_document.assert_called_once()
        call_kwargs = mock_chunking.chunk_document.call_args
        assert call_kwargs[1]["extracted_text"] == "Previously extracted text"

        assert sample_doc_record.status == "complete"

    @patch("app.worker.tasks.process_document.STORAGE_ROOT", Path("/tmp/storage"))
    @patch("app.worker.tasks.process_document.EntityExtractionService")
    @patch("app.worker.tasks.process_document.ChunkingService")
    @patch("app.worker.tasks.process_document.OllamaClient")
    @patch("app.worker.tasks.process_document.EventPublisher")
    @patch("app.worker.tasks.process_document.TextExtractionService")
    @patch("app.worker.tasks.process_document.SyncSessionLocal")
    def test_resume_from_embedding_skips_all_prior_stages(
        self,
        mock_session_cls,
        mock_extraction_cls,
        mock_publisher_cls,
        mock_ollama_cls,
        mock_chunking_cls,
        mock_entity_svc_cls,
        sample_doc_record,
    ):
        """resume_from_stage='embedding' skips text extraction, chunking, and entity extraction."""
        from app.worker.tasks.process_document import process_document_task

        sample_doc_record.extracted_text = "existing text"
        sample_doc_record.entity_count = 5
        sample_doc_record.extraction_confidence = 0.8

        mock_session, mock_extractor, mock_publisher = _setup_mocks(
            mock_session_cls, mock_extraction_cls, mock_publisher_cls, sample_doc_record
        )

        mock_ollama = MagicMock()
        mock_ollama.check_available.return_value = True
        mock_ollama_cls.return_value = mock_ollama

        # Mock DB query for loading existing chunks
        mock_chunk = MagicMock()
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_chunk]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        process_document_task(
            str(sample_doc_record.id),
            str(sample_doc_record.investigation_id),
            resume_from_stage="embedding",
        )

        # Text extraction and chunking should NOT have been called
        mock_extractor.extract_text.assert_not_called()
        mock_chunking_cls.return_value.chunk_document.assert_not_called()
        mock_entity_svc_cls.return_value.extract_from_chunks.assert_not_called()

        assert sample_doc_record.status == "complete"
