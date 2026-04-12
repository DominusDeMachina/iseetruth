"""Periodic task: detect Ollama recovery and auto-retry failed documents."""

from datetime import datetime, timezone

from loguru import logger

from app.config import get_settings
from app.db.sync_postgres import SyncSessionLocal
from app.llm.client import DEFAULT_MODEL, OllamaClient
from app.llm.embeddings import EMBEDDING_MODEL
from app.models.document import Document
from app.services.events import EventPublisher
from app.worker.celery_app import celery_app

# Only auto-retry documents that failed at Ollama-dependent stages.
# extracting_text (PyMuPDF) and chunking (text splitting) are NOT Ollama-related.
OLLAMA_RELATED_STAGES = {"preflight", "extracting_entities", "embedding"}


@celery_app.task(name="auto_retry_failed_documents")
def auto_retry_failed_documents_task() -> dict:
    """Check Ollama health and auto-retry eligible failed documents.

    Runs on a Celery Beat schedule. Only retries documents whose failure was
    at an Ollama-dependent stage, respecting exponential backoff and a
    maximum retry count.
    """
    settings = get_settings()

    # Fork-safe: create clients inside the task, never at module level.
    chat_client = OllamaClient(settings.ollama_base_url)
    chat_available = chat_client.check_available(DEFAULT_MODEL)

    embed_client = OllamaClient(settings.ollama_embedding_url)
    embed_available = embed_client.check_available(EMBEDDING_MODEL)

    if not chat_available and not embed_available:
        return {"retried": 0, "reason": "ollama_unavailable"}

    with SyncSessionLocal() as db:
        failed_docs = (
            db.query(Document)
            .filter(
                Document.status == "failed",
                Document.failed_stage.in_(OLLAMA_RELATED_STAGES),
                Document.retry_count < settings.auto_retry_max_retries,
            )
            .all()
        )

        if not failed_docs:
            return {"retried": 0}

        now = datetime.now(timezone.utc)
        retried = 0
        publisher = EventPublisher(settings.redis_url)

        # Import here (not module-level) to stay fork-safe
        from app.worker.tasks.process_document import process_document_task

        try:
            for doc in failed_docs:
                # Check if the relevant Ollama instance is available
                if doc.failed_stage in ("preflight", "extracting_entities") and not chat_available:
                    continue
                if doc.failed_stage == "embedding" and not embed_available:
                    continue

                # Enforce exponential backoff: base_delay * 2^retry_count
                backoff_delay = settings.auto_retry_base_delay_seconds * (
                    2**doc.retry_count
                )
                elapsed = (now - doc.updated_at).total_seconds()
                if elapsed < backoff_delay:
                    continue

                # Capture original stage before resetting (for logging)
                original_stage = doc.failed_stage

                # Determine resume_from_stage (mirrors Story 6.1 logic)
                if doc.failed_stage in ("preflight", "extracting_text"):
                    resume_from_stage = None  # run all stages
                elif doc.failed_stage in ("chunking", "extracting_entities"):
                    resume_from_stage = "chunking"
                elif doc.failed_stage == "embedding":
                    resume_from_stage = "embedding"
                else:
                    resume_from_stage = None

                # Update document state
                doc.retry_count += 1
                doc.status = "queued"
                doc.error_message = None
                doc.failed_stage = None

                try:
                    db.commit()

                    process_document_task.delay(
                        str(doc.id), str(doc.investigation_id), resume_from_stage
                    )

                    # Publish SSE event so the frontend sees the status change
                    publisher.publish(
                        str(doc.investigation_id),
                        "document.queued",
                        {"document_id": str(doc.id)},
                    )

                    logger.info(
                        "Auto-retrying failed document",
                        document_id=str(doc.id),
                        retry_count=doc.retry_count,
                        failed_stage=original_stage,
                        resume_from_stage=resume_from_stage,
                    )
                    retried += 1
                except Exception as exc:
                    db.rollback()
                    logger.error(
                        "Auto-retry failed for document",
                        document_id=str(doc.id),
                        error=str(exc),
                    )
        finally:
            publisher.close()

        return {"retried": retried}
