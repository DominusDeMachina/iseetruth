"""Tests for auto_retry_failed_documents periodic task."""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.worker.tasks.auto_retry import (
    OLLAMA_RELATED_STAGES,
    auto_retry_failed_documents_task,
)


def _make_doc(
    *,
    failed_stage: str = "preflight",
    retry_count: int = 0,
    updated_at: datetime | None = None,
    investigation_id: uuid.UUID | None = None,
):
    """Create a mock Document with sensible defaults for auto-retry tests."""
    doc = MagicMock()
    doc.id = uuid.uuid4()
    doc.investigation_id = investigation_id or uuid.uuid4()
    doc.status = "failed"
    doc.failed_stage = failed_stage
    doc.retry_count = retry_count
    doc.error_message = "Ollama unavailable"
    doc.updated_at = updated_at or datetime(2026, 1, 1, tzinfo=timezone.utc)
    return doc


@pytest.fixture
def mock_settings():
    settings = MagicMock()
    settings.ollama_base_url = "http://ollama:11434"
    settings.ollama_embedding_url = "http://ollama-embedding:11434"
    settings.redis_url = "redis://redis:6379/0"
    settings.auto_retry_max_retries = 5
    settings.auto_retry_base_delay_seconds = 30
    settings.auto_retry_check_interval_seconds = 60
    return settings


@pytest.fixture
def patch_deps(mock_settings):
    """Patch all external dependencies for the auto-retry task."""
    with (
        patch("app.worker.tasks.auto_retry.get_settings", return_value=mock_settings),
        patch("app.worker.tasks.auto_retry.SyncSessionLocal") as mock_session_cls,
        patch("app.worker.tasks.auto_retry.OllamaClient") as mock_ollama_cls,
        patch("app.worker.tasks.auto_retry.EventPublisher") as mock_publisher_cls,
        patch(
            "app.worker.tasks.process_document.process_document_task"
        ) as mock_process_task,
    ):
        mock_session = MagicMock()
        mock_session_cls.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_session_cls.return_value.__exit__ = MagicMock(return_value=False)

        mock_publisher = MagicMock()
        mock_publisher_cls.return_value = mock_publisher

        yield {
            "settings": mock_settings,
            "session": mock_session,
            "ollama_cls": mock_ollama_cls,
            "publisher": mock_publisher,
            "process_task": mock_process_task,
        }


class TestAutoRetryTaskOllamaUnavailable:
    def test_returns_early_when_both_ollama_unavailable(self, patch_deps):
        """AC1: Task returns early when Ollama is down."""
        # Both Ollama instances unavailable
        chat_client = MagicMock()
        chat_client.check_available.return_value = False
        embed_client = MagicMock()
        embed_client.check_available.return_value = False
        patch_deps["ollama_cls"].side_effect = [chat_client, embed_client]

        result = auto_retry_failed_documents_task()

        assert result["retried"] == 0
        assert result["reason"] == "ollama_unavailable"
        # DB should NOT have been queried
        patch_deps["session"].query.assert_not_called()


class TestAutoRetryTaskRetries:
    def _setup_ollama(self, patch_deps, *, chat=True, embed=True):
        chat_client = MagicMock()
        chat_client.check_available.return_value = chat
        embed_client = MagicMock()
        embed_client.check_available.return_value = embed
        patch_deps["ollama_cls"].side_effect = [chat_client, embed_client]

    def test_retries_preflight_failed_doc(self, patch_deps):
        """AC1: Failed doc at preflight stage is retried when Ollama recovers."""
        self._setup_ollama(patch_deps)
        doc = _make_doc(failed_stage="preflight")
        query_mock = MagicMock()
        query_mock.filter.return_value.all.return_value = [doc]
        patch_deps["session"].query.return_value = query_mock

        result = auto_retry_failed_documents_task()

        assert result["retried"] == 1
        assert doc.status == "queued"
        assert doc.error_message is None
        assert doc.failed_stage is None
        assert doc.retry_count == 1
        patch_deps["session"].commit.assert_called()
        patch_deps["process_task"].delay.assert_called_once_with(
            str(doc.id), str(doc.investigation_id), None
        )
        patch_deps["publisher"].publish.assert_called_once()

    def test_does_not_retry_non_ollama_stage(self, patch_deps):
        """AC1: extracting_text failures are NOT auto-retried."""
        self._setup_ollama(patch_deps)
        # This doc has a non-Ollama stage failure — it should not appear in
        # the DB query results since the query filters by OLLAMA_RELATED_STAGES.
        # Simulate an empty result set.
        query_mock = MagicMock()
        query_mock.filter.return_value.all.return_value = []
        patch_deps["session"].query.return_value = query_mock

        result = auto_retry_failed_documents_task()

        assert result["retried"] == 0
        patch_deps["process_task"].delay.assert_not_called()

    def test_retries_embedding_when_embed_ollama_available(self, patch_deps):
        """AC1: Embedding failure retried with resume_from_stage='embedding'."""
        self._setup_ollama(patch_deps, chat=False, embed=True)
        doc = _make_doc(failed_stage="embedding")
        query_mock = MagicMock()
        query_mock.filter.return_value.all.return_value = [doc]
        patch_deps["session"].query.return_value = query_mock

        result = auto_retry_failed_documents_task()

        assert result["retried"] == 1
        patch_deps["process_task"].delay.assert_called_once_with(
            str(doc.id), str(doc.investigation_id), "embedding"
        )

    def test_skips_embedding_when_embed_ollama_unavailable(self, patch_deps):
        """Embedding failure NOT retried if embedding Ollama is down."""
        self._setup_ollama(patch_deps, chat=True, embed=False)
        doc = _make_doc(failed_stage="embedding")
        query_mock = MagicMock()
        query_mock.filter.return_value.all.return_value = [doc]
        patch_deps["session"].query.return_value = query_mock

        result = auto_retry_failed_documents_task()

        assert result["retried"] == 0

    def test_extracting_entities_resumes_from_chunking(self, patch_deps):
        """AC1: extracting_entities failure retried with resume_from_stage='chunking'."""
        self._setup_ollama(patch_deps)
        doc = _make_doc(failed_stage="extracting_entities")
        query_mock = MagicMock()
        query_mock.filter.return_value.all.return_value = [doc]
        patch_deps["session"].query.return_value = query_mock

        result = auto_retry_failed_documents_task()

        assert result["retried"] == 1
        patch_deps["process_task"].delay.assert_called_once_with(
            str(doc.id), str(doc.investigation_id), "chunking"
        )


class TestAutoRetryBackoff:
    def _setup_ollama(self, patch_deps):
        chat_client = MagicMock()
        chat_client.check_available.return_value = True
        embed_client = MagicMock()
        embed_client.check_available.return_value = True
        patch_deps["ollama_cls"].side_effect = [chat_client, embed_client]

    def test_backoff_not_elapsed_skips_retry(self, patch_deps):
        """AC3: Doc within backoff window is NOT retried."""
        self._setup_ollama(patch_deps)
        now = datetime.now(timezone.utc)
        # retry_count=2 → backoff = 30 * 2^2 = 120s; updated_at 60s ago → skip
        doc = _make_doc(retry_count=2, updated_at=now - timedelta(seconds=60))
        query_mock = MagicMock()
        query_mock.filter.return_value.all.return_value = [doc]
        patch_deps["session"].query.return_value = query_mock

        result = auto_retry_failed_documents_task()

        assert result["retried"] == 0

    def test_backoff_elapsed_retries(self, patch_deps):
        """AC3: Doc past backoff window IS retried."""
        self._setup_ollama(patch_deps)
        now = datetime.now(timezone.utc)
        # retry_count=2 → backoff = 120s; updated_at 130s ago → retry
        doc = _make_doc(retry_count=2, updated_at=now - timedelta(seconds=130))
        query_mock = MagicMock()
        query_mock.filter.return_value.all.return_value = [doc]
        patch_deps["session"].query.return_value = query_mock

        result = auto_retry_failed_documents_task()

        assert result["retried"] == 1
        assert doc.retry_count == 3

    def test_max_retries_exceeded_not_retried(self, patch_deps):
        """AC3: Doc at max retry count is NOT retried."""
        self._setup_ollama(patch_deps)
        # retry_count=5 (max) — should not appear in DB query due to filter,
        # but if it did, the task would skip it. Simulate empty result.
        query_mock = MagicMock()
        query_mock.filter.return_value.all.return_value = []
        patch_deps["session"].query.return_value = query_mock

        result = auto_retry_failed_documents_task()

        assert result["retried"] == 0


class TestAutoRetryMultipleInvestigations:
    def test_retries_docs_across_investigations(self, patch_deps):
        """AC1: All eligible docs across investigations are retried."""
        chat_client = MagicMock()
        chat_client.check_available.return_value = True
        embed_client = MagicMock()
        embed_client.check_available.return_value = True
        patch_deps["ollama_cls"].side_effect = [chat_client, embed_client]

        inv1 = uuid.uuid4()
        inv2 = uuid.uuid4()
        doc1 = _make_doc(investigation_id=inv1, failed_stage="preflight")
        doc2 = _make_doc(investigation_id=inv2, failed_stage="extracting_entities")
        query_mock = MagicMock()
        query_mock.filter.return_value.all.return_value = [doc1, doc2]
        patch_deps["session"].query.return_value = query_mock

        result = auto_retry_failed_documents_task()

        assert result["retried"] == 2
        assert patch_deps["process_task"].delay.call_count == 2
        assert patch_deps["publisher"].publish.call_count == 2


class TestAutoRetrySSEEvents:
    def test_publishes_document_queued_event(self, patch_deps):
        """AC1: document.queued SSE event published for each retried doc."""
        chat_client = MagicMock()
        chat_client.check_available.return_value = True
        embed_client = MagicMock()
        embed_client.check_available.return_value = True
        patch_deps["ollama_cls"].side_effect = [chat_client, embed_client]

        doc = _make_doc(failed_stage="preflight")
        query_mock = MagicMock()
        query_mock.filter.return_value.all.return_value = [doc]
        patch_deps["session"].query.return_value = query_mock

        auto_retry_failed_documents_task()

        patch_deps["publisher"].publish.assert_called_once_with(
            str(doc.investigation_id),
            "document.queued",
            {"document_id": str(doc.id)},
        )

    def test_publisher_closed_even_on_per_doc_error(self, patch_deps):
        """EventPublisher.close() is called even if per-document retry fails."""
        chat_client = MagicMock()
        chat_client.check_available.return_value = True
        embed_client = MagicMock()
        embed_client.check_available.return_value = True
        patch_deps["ollama_cls"].side_effect = [chat_client, embed_client]

        doc = _make_doc(failed_stage="preflight")
        query_mock = MagicMock()
        query_mock.filter.return_value.all.return_value = [doc]
        patch_deps["session"].query.return_value = query_mock
        patch_deps["session"].commit.side_effect = Exception("DB error")

        # Per-document errors are caught and logged, not propagated
        result = auto_retry_failed_documents_task()

        assert result["retried"] == 0
        patch_deps["session"].rollback.assert_called_once()
        patch_deps["publisher"].close.assert_called_once()


class TestCeleryBeatConfiguration:
    def test_beat_schedule_configured(self):
        """AC1: Celery Beat schedule includes auto-retry task at 60s interval."""
        from app.worker.celery_app import celery_app

        schedule = celery_app.conf.beat_schedule
        assert "auto-retry-failed-documents" in schedule
        entry = schedule["auto-retry-failed-documents"]
        assert entry["task"] == "auto_retry_failed_documents"
        assert entry["schedule"].total_seconds() == 60

    def test_task_is_registered(self):
        """Task name matches what beat_schedule references."""
        assert auto_retry_failed_documents_task.name == "auto_retry_failed_documents"


class TestOllamaRelatedStages:
    def test_stages_constant(self):
        """Verify OLLAMA_RELATED_STAGES includes correct stages."""
        assert OLLAMA_RELATED_STAGES == {"preflight", "extracting_entities", "embedding"}
        assert "extracting_text" not in OLLAMA_RELATED_STAGES
        assert "chunking" not in OLLAMA_RELATED_STAGES
