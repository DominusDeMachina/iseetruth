import os
from pathlib import Path

from loguru import logger

from app.config import get_settings
from app.db.sync_postgres import SyncSessionLocal
from app.llm.client import OllamaClient
from app.llm.embeddings import EMBEDDING_MODEL, OllamaEmbeddingClient
from app.models.chunk import DocumentChunk
from app.models.document import Document
from app.services.chunking import ChunkingService
from app.services.embedding import EmbeddingService
from app.services.events import EventPublisher
from app.services.extraction import EntityExtractionService
from app.services.image_extraction import ImageExtractionService
from app.services.text_extraction import TextExtractionService
from app.services import web_capture
from app.worker.celery_app import celery_app

settings = get_settings()
STORAGE_ROOT = Path(os.environ.get("STORAGE_ROOT", "storage"))


@celery_app.task(name="process_document")
def process_document_task(
    document_id: str, investigation_id: str, resume_from_stage: str | None = None
) -> None:
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
                document.failed_stage = "preflight"
                document.error_message = (
                    "LLM service unavailable — retry when service recovers"
                )
                session.commit()
                logger.warning(
                    "Ollama unavailable, document marked failed for retry",
                    document_id=document_id,
                )
                _publish_safe(
                    "document.failed",
                    {
                        "document_id": document_id,
                        "stage": "preflight",
                        "error": "LLM service unavailable — document will be retried when service recovers",
                    },
                )
                return

            # Warn if embedding model is absent — Stage 4 will complete with 0 embeddings
            embedding_check_client = OllamaClient(settings.ollama_embedding_url)
            if not embedding_check_client.check_available(model=EMBEDDING_MODEL):
                logger.warning(
                    "Embedding model unavailable — Stage 4 will produce 0 embeddings",
                    model=EMBEDDING_MODEL,
                    document_id=document_id,
                )

            # Determine which stages to skip based on resume_from_stage
            skip_text_extraction = resume_from_stage in ("chunking", "embedding")
            skip_chunking = resume_from_stage == "embedding"
            skip_entity_extraction = resume_from_stage == "embedding"

            # Initialize variables that may be set by skipped stages
            extracted_text = document.extracted_text if skip_text_extraction else None
            chunks = []
            summary = None

            # Stage 1: Text extraction
            if not skip_text_extraction:
                document.status = "extracting_text"
                session.commit()

                _publish_safe(
                    "document.processing",
                    {"document_id": document_id, "stage": "extracting_text"},
                )

                try:
                    # Build file path using actual extension from stored filename
                    ext = Path(document.filename).suffix.lower() or ".pdf"
                    file_path = STORAGE_ROOT / investigation_id / f"{document_id}{ext}"

                    # Route extraction by document type
                    if document.document_type == "web":
                        # Web documents: fetch URL, store HTML, convert to text
                        web_capture.fetch_and_store(
                            document_id, investigation_id, document.source_url, session
                        )
                        # Re-read document to get updated extracted_text
                        session.refresh(document)
                        extracted_text = document.extracted_text
                    elif document.document_type == "image":
                        extractor = ImageExtractionService()
                        extracted_text = extractor.extract_text(file_path, document_id=document_id)
                    else:
                        extractor = TextExtractionService()
                        extracted_text = extractor.extract_text(file_path)

                    document.extracted_text = extracted_text
                    session.commit()

                    # Early exit for empty text: mark complete, skip remaining stages
                    if document.document_type in ("image", "web") and not extracted_text:
                        document.status = "complete"
                        document.entity_count = 0
                        session.commit()

                        logger.info(
                            "Text extraction returned no text — marking complete",
                            document_id=document_id,
                            investigation_id=investigation_id,
                        )

                        _publish_safe(
                            "document.complete",
                            {
                                "document_id": document_id,
                                "entity_count": 0,
                                "relationship_count": 0,
                                "embedded_count": 0,
                                "extraction_confidence": None,
                            },
                        )
                        return

                    logger.info(
                        "Text extraction complete",
                        document_id=document_id,
                        investigation_id=investigation_id,
                    )

                except Exception as exc:
                    document.status = "failed"
                    document.failed_stage = "extracting_text"
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
                        {"document_id": document_id, "stage": "extracting_text", "error": str(exc)},
                    )
                    return

            # Stage 2: Chunking
            if not skip_chunking:
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
                    document.failed_stage = "chunking"
                    document.error_message = f"Chunking failed: {exc}"
                    session.commit()

                    logger.error(
                        "Chunking failed",
                        document_id=document_id,
                        error=str(exc),
                    )

                    _publish_safe(
                        "document.failed",
                        {"document_id": document_id, "stage": "chunking", "error": f"Chunking failed: {exc}"},
                    )
                    return

            # Stage 3: Entity extraction
            if not skip_entity_extraction:
                document.status = "extracting_entities"
                session.commit()

                # Clean up Neo4j entities/provenance from previous failed run
                if resume_from_stage is not None:
                    try:
                        with neo4j_driver.session() as neo4j_session:
                            neo4j_session.run(
                                "MATCH (e)-[m:MENTIONED_IN]->(d:Document {id: $doc_id}) DELETE m",
                                doc_id=document_id,
                            )
                            neo4j_session.run(
                                "MATCH (d:Document {id: $doc_id}) DELETE d",
                                doc_id=document_id,
                            )
                        logger.info(
                            "Neo4j cleanup complete for retry",
                            document_id=document_id,
                        )
                    except Exception as cleanup_exc:
                        logger.warning(
                            "Neo4j cleanup failed, continuing with extraction",
                            document_id=document_id,
                            error=str(cleanup_exc),
                        )

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

                    def on_extraction_progress(completed: int, total: int) -> None:
                        _publish_safe(
                            "document.processing",
                            {
                                "document_id": document_id,
                                "stage": "extracting_entities",
                                "chunk_count": total,
                                "chunks_done": completed,
                                "progress": completed / total if total > 0 else 0.0,
                            },
                        )

                    summary = extraction_service.extract_from_chunks(
                        chunks,
                        investigation_id=document.investigation_id,
                        on_entity_discovered=on_entity_discovered,
                        on_chunk_progress=on_extraction_progress,
                    )

                    document.entity_count = summary.entity_count
                    document.extraction_confidence = summary.average_confidence
                    session.commit()

                    logger.info(
                        "Entity extraction complete",
                        document_id=document_id,
                        entity_count=summary.entity_count,
                        relationship_count=summary.relationship_count,
                        average_confidence=summary.average_confidence,
                    )

                    # Trigger cross-investigation matching (fire-and-forget)
                    if summary.entity_count > 0:
                        try:
                            from app.worker.tasks.cross_investigation_match import (
                                run_cross_investigation_match_task,
                            )
                            run_cross_investigation_match_task.apply_async(
                                args=[investigation_id, document_id],
                                ignore_result=True,
                            )
                        except Exception as cross_exc:
                            logger.warning(
                                "Failed to dispatch cross-investigation matching",
                                document_id=document_id,
                                error=str(cross_exc),
                            )

                except Exception as exc:
                    session.rollback()
                    document.status = "failed"
                    document.failed_stage = "extracting_entities"
                    document.error_message = f"Entity extraction failed: {exc}"
                    session.commit()

                    logger.error(
                        "Entity extraction failed",
                        document_id=document_id,
                        error=str(exc),
                    )

                    _publish_safe(
                        "document.failed",
                        {"document_id": document_id, "stage": "extracting_entities", "error": f"Entity extraction failed: {exc}"},
                    )
                    return

            # Stage 4: Embedding generation
            try:
                document.status = "embedding"
                session.commit()

                # When resuming from embedding, load existing chunks from DB
                if skip_chunking:
                    from sqlalchemy import select as sa_select

                    db_chunks = session.execute(
                        sa_select(DocumentChunk).where(
                            DocumentChunk.document_id == document_id
                        )
                    ).scalars().all()
                    chunks = list(db_chunks)

                _publish_safe(
                    "document.processing",
                    {
                        "document_id": document_id,
                        "stage": "embedding",
                        "chunk_count": len(chunks),
                        "progress": 0.0,
                    },
                )

                embedding_client = OllamaEmbeddingClient(settings.ollama_embedding_url)
                embedding_service = EmbeddingService(embedding_client, qdrant_client)

                def on_embedding_progress(completed: int, total: int) -> None:
                    _publish_safe(
                        "document.processing",
                        {
                            "document_id": document_id,
                            "stage": "embedding",
                            "chunk_count": total,
                            "chunks_done": completed,
                            "progress": completed / total if total > 0 else 0.0,
                        },
                    )

                emb_summary = embedding_service.embed_chunks(
                    chunks,
                    investigation_id=document.investigation_id,
                    on_chunk_progress=on_embedding_progress,
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

                entity_count = summary.entity_count if summary else (document.entity_count or 0)
                relationship_count = summary.relationship_count if summary else 0
                avg_confidence = summary.average_confidence if summary else document.extraction_confidence

                logger.info(
                    "Document processing complete",
                    document_id=document_id,
                    investigation_id=investigation_id,
                    entity_count=entity_count,
                    relationship_count=relationship_count,
                    embedded_count=emb_summary.embedded_count,
                )

                _publish_safe(
                    "document.complete",
                    {
                        "document_id": document_id,
                        "entity_count": entity_count,
                        "relationship_count": relationship_count,
                        "embedded_count": emb_summary.embedded_count,
                        "extraction_confidence": avg_confidence,
                    },
                )

            except Exception as exc:
                session.rollback()
                document.status = "failed"
                document.failed_stage = "embedding"
                document.error_message = f"Embedding stage failed: {exc}"
                session.commit()

                logger.error(
                    "Embedding stage infrastructure failed",
                    document_id=document_id,
                    error=str(exc),
                )

                _publish_safe(
                    "document.failed",
                    {"document_id": document_id, "stage": "embedding", "error": f"Embedding stage failed: {exc}"},
                )
                return
    finally:
        publisher.close()
        neo4j_driver.close()
