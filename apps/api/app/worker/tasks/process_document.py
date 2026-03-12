import os
from pathlib import Path

from loguru import logger

from app.config import get_settings
from app.db.sync_postgres import SyncSessionLocal
from app.llm.client import OllamaClient
from app.llm.embeddings import EMBEDDING_MODEL, OllamaEmbeddingClient
from app.models.document import Document
from app.services.chunking import ChunkingService
from app.services.embedding import EmbeddingService
from app.services.events import EventPublisher
from app.services.extraction import EntityExtractionService
from app.services.text_extraction import TextExtractionService
from app.worker.celery_app import celery_app

settings = get_settings()
STORAGE_ROOT = Path(os.environ.get("STORAGE_ROOT", "storage"))


@celery_app.task(name="process_document")
def process_document_task(document_id: str, investigation_id: str) -> None:
    """Process a document: extract text, chunk, and prepare for entity extraction."""
    # Create clients here (not at module level) — fork-safety: module-level Neo4j/Qdrant
    # singletons inherit file descriptors and thread state into forked children → SIGSEGV.
    from app.db.qdrant import ensure_qdrant_collection
    from neo4j import GraphDatabase
    from qdrant_client import QdrantClient

    _auth_parts = settings.neo4j_auth.split("/", 1)
    neo4j_driver = GraphDatabase.driver(
        settings.neo4j_uri, auth=(_auth_parts[0], _auth_parts[1])
    )
    qdrant_client = QdrantClient(url=settings.qdrant_url)
    ensure_qdrant_collection(qdrant_client)

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

            # Warn if embedding model is absent — Stage 4 will complete with 0 embeddings
            if not ollama_client.check_available(model=EMBEDDING_MODEL):
                logger.warning(
                    "Embedding model unavailable — Stage 4 will produce 0 embeddings",
                    model=EMBEDDING_MODEL,
                    document_id=document_id,
                )

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

            # Stage 3: Entity extraction
            document.status = "extracting_entities"
            session.commit()

            _publish_safe(
                "document.processing",
                {
                    "document_id": document_id,
                    "stage": "extracting_entities",
                    "chunk_count": len(chunks),
                    "progress": 0.0,
                },
            )

            try:
                extraction_service = EntityExtractionService(ollama_client, neo4j_driver)

                def on_entity_discovered(entity) -> None:
                    _publish_safe(
                        "entity.discovered",
                        {
                            "document_id": document_id,
                            "entity_type": entity.type.value,
                            "entity_name": entity.name,
                        },
                    )

                summary = extraction_service.extract_from_chunks(
                    chunks,
                    investigation_id=document.investigation_id,
                    on_entity_discovered=on_entity_discovered,
                )

                logger.info(
                    "Entity extraction complete",
                    document_id=document_id,
                    entity_count=summary.entity_count,
                    relationship_count=summary.relationship_count,
                )

            except Exception as exc:
                session.rollback()
                document.status = "failed"
                document.error_message = f"Entity extraction failed: {exc}"
                session.commit()

                logger.error(
                    "Entity extraction failed",
                    document_id=document_id,
                    error=str(exc),
                )

                _publish_safe(
                    "document.failed",
                    {"document_id": document_id, "error": f"Entity extraction failed: {exc}"},
                )
                return

            # Stage 4: Embedding generation
            try:
                document.status = "embedding"
                session.commit()

                _publish_safe(
                    "document.processing",
                    {
                        "document_id": document_id,
                        "stage": "embedding",
                        "chunk_count": len(chunks),
                        "progress": 0.0,
                    },
                )

                embedding_client = OllamaEmbeddingClient(settings.ollama_base_url)
                embedding_service = EmbeddingService(embedding_client, qdrant_client)
                emb_summary = embedding_service.embed_chunks(
                    chunks, investigation_id=document.investigation_id
                )

                if emb_summary.failed_count > 0:
                    logger.warning(
                        "Some chunks failed embedding — partial embeddings stored",
                        document_id=document_id,
                        embedded_count=emb_summary.embedded_count,
                        failed_count=emb_summary.failed_count,
                    )
                else:
                    logger.info(
                        "Embedding generation complete",
                        document_id=document_id,
                        embedded_count=emb_summary.embedded_count,
                    )

                # All stages complete
                document.status = "complete"
                session.commit()

                logger.info(
                    "Document processing complete",
                    document_id=document_id,
                    investigation_id=investigation_id,
                    entity_count=summary.entity_count,
                    relationship_count=summary.relationship_count,
                    embedded_count=emb_summary.embedded_count,
                )

                _publish_safe(
                    "document.complete",
                    {
                        "document_id": document_id,
                        "entity_count": summary.entity_count,
                        "relationship_count": summary.relationship_count,
                        "embedded_count": emb_summary.embedded_count,
                    },
                )

            except Exception as exc:
                session.rollback()
                document.status = "failed"
                document.error_message = f"Embedding stage failed: {exc}"
                session.commit()

                logger.error(
                    "Embedding stage infrastructure failed",
                    document_id=document_id,
                    error=str(exc),
                )

                _publish_safe(
                    "document.failed",
                    {"document_id": document_id, "error": f"Embedding stage failed: {exc}"},
                )
                return
    finally:
        publisher.close()
        neo4j_driver.close()
