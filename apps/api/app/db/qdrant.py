from loguru import logger
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from app.config import get_settings

COLLECTION_NAME = "document_chunks"
VECTOR_SIZE = 4096  # qwen3-embedding:8b default output dimensions

# Lazy singleton — avoids creating a QdrantClient at import time, which is not
# fork-safe (Celery prefork workers inherit broken connection state → SIGSEGV).
_client: QdrantClient | None = None


def get_client() -> QdrantClient:
    """Return a module-level QdrantClient, creating it on first call."""
    global _client
    if _client is None:
        settings = get_settings()
        _client = QdrantClient(url=settings.qdrant_url)
    return _client


def ensure_qdrant_collection(qdrant_client: QdrantClient) -> None:
    """Create Qdrant collection if it doesn't exist. Idempotent — safe to call on every deploy."""
    existing_names = {c.name for c in qdrant_client.get_collections().collections}
    if COLLECTION_NAME not in existing_names:
        qdrant_client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )
        logger.info("Created Qdrant collection", collection=COLLECTION_NAME)
    else:
        logger.debug("Qdrant collection already exists", collection=COLLECTION_NAME)
