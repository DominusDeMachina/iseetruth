import uuid
from dataclasses import dataclass

from loguru import logger
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

from app.db.qdrant import COLLECTION_NAME
from app.llm.embeddings import OllamaEmbeddingClient


@dataclass
class EmbeddingSummary:
    embedded_count: int
    failed_count: int
    chunk_count: int


class EmbeddingService:
    def __init__(self, embedding_client: OllamaEmbeddingClient, qdrant_client: QdrantClient):
        self.embedding_client = embedding_client
        self.qdrant_client = qdrant_client

    def embed_chunks(
        self,
        chunks: list,
        investigation_id: uuid.UUID,
    ) -> EmbeddingSummary:
        """Generate embeddings for all chunks and store in Qdrant.

        Per-chunk failures are logged and skipped — they do NOT abort the batch.
        Returns summary with counts for caller to decide on logging/alerting.
        """
        embedded_count = 0
        failed_count = 0

        for chunk in chunks:
            try:
                vector = self.embedding_client.embed(chunk.text)
                self.qdrant_client.upsert(
                    collection_name=COLLECTION_NAME,
                    points=[
                        PointStruct(
                            id=str(chunk.id),
                            vector=vector,
                            payload={
                                "chunk_id": str(chunk.id),
                                "document_id": str(chunk.document_id),
                                "investigation_id": str(investigation_id),
                                "page_start": chunk.page_start,
                                "page_end": chunk.page_end,
                                "text_excerpt": chunk.text[:500],
                            },
                        )
                    ],
                )
                embedded_count += 1
            except Exception as exc:
                logger.error(
                    "Embedding failed for chunk",
                    chunk_id=str(chunk.id),
                    document_id=str(chunk.document_id),
                    error=str(exc),
                )
                failed_count += 1

        return EmbeddingSummary(
            embedded_count=embedded_count,
            failed_count=failed_count,
            chunk_count=len(chunks),
        )
