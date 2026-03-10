import os
from pathlib import Path

from loguru import logger

from app.config import get_settings
from app.db.sync_postgres import SyncSessionLocal
from app.llm.client import OllamaClient
from app.models.document import Document
from app.services.chunking import ChunkingService
from app.services.events import EventPublisher
from app.services.text_extraction import TextExtractionService
from app.worker.celery_app import celery_app

settings = get_settings()
STORAGE_ROOT = Path(os.environ.get("STORAGE_ROOT", "storage"))


@celery_app.task(name="process_document")
def process_document_task(document_id: str, investigation_id: str) -> None:
    """Process a document: extract text, chunk, and prepare for entity extraction."""
    publisher = EventPublisher(settings.celery_broker_url)

    def _publish_safe(event_type: str, payload: dict) -> None:
        """Best-effort event publishing — never raises."""
        try:
            publisher.publish(
                investigation_id=investigation_id,
                event_type=event_type,
                payload=payload,
            )
        except Exception as pub_exc:
            logger.warning(
                "Failed to publish event",
                event_type=event_type,
                document_id=document_id,
                error=str(pub_exc),
            )

    try:
        with SyncSessionLocal() as session:
            document = session.get(Document, document_id)
            if document is None:
                logger.error("Document not found", document_id=document_id)
                return

            # Fail fast: check Ollama availability before heavy processing
            ollama_client = OllamaClient(settings.ollama_base_url)
            if not ollama_client.check_available():
                document.status = "failed"
                document.error_message = (
                    "Ollama LLM service is unavailable — cannot process document"
                )
                session.commit()
                logger.error(
                    "Ollama unavailable, failing document",
                    document_id=document_id,
                )
                _publish_safe(
                    "document.failed",
                    {
                        "document_id": document_id,
                        "error": "Ollama LLM service unavailable",
                    },
                )
                return

            # Stage 1: Text extraction
            document.status = "extracting_text"
            session.commit()

            _publish_safe(
                "document.processing",
                {"document_id": document_id, "stage": "extracting_text"},
            )

            try:
                file_path = STORAGE_ROOT / investigation_id / f"{document_id}.pdf"
                extractor = TextExtractionService()
                extracted_text = extractor.extract_text(file_path)

                document.extracted_text = extracted_text
                session.commit()

                logger.info(
                    "Text extraction complete",
                    document_id=document_id,
                    investigation_id=investigation_id,
                )

            except Exception as exc:
                document.status = "failed"
                document.error_message = str(exc)
                session.commit()

                logger.error(
                    "Text extraction failed",
                    document_id=document_id,
                    investigation_id=investigation_id,
                    error=str(exc),
                )

                _publish_safe(
                    "document.failed",
                    {"document_id": document_id, "error": str(exc)},
                )
                return

            # Stage 2: Chunking
            document.status = "chunking"
            session.commit()

            _publish_safe(
                "document.processing",
                {
                    "document_id": document_id,
                    "stage": "chunking",
                    "progress": 0.0,
                },
            )

            try:
                chunking_service = ChunkingService()
                chunks = chunking_service.chunk_document(
                    document_id=document.id,
                    investigation_id=document.investigation_id,
                    extracted_text=extracted_text,
                    session=session,
                )
                session.commit()

                _publish_safe(
                    "document.processing",
                    {
                        "document_id": document_id,
                        "stage": "chunking_complete",
                        "chunk_count": len(chunks),
                    },
                )

                logger.info(
                    "Document chunking complete",
                    document_id=document_id,
                    chunk_count=len(chunks),
                )

            except Exception as exc:
                session.rollback()
                document.status = "failed"
                document.error_message = f"Chunking failed: {exc}"
                session.commit()

                logger.error(
                    "Chunking failed",
                    document_id=document_id,
                    error=str(exc),
                )

                _publish_safe(
                    "document.failed",
                    {"document_id": document_id, "error": f"Chunking failed: {exc}"},
                )
                return

            # All stages complete
            document.status = "complete"
            session.commit()

            logger.info(
                "Document processing complete",
                document_id=document_id,
                investigation_id=investigation_id,
            )

            _publish_safe("document.complete", {"document_id": document_id})
    finally:
        publisher.close()
