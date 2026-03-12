from loguru import logger
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from app.config import get_settings

settings = get_settings()

client = QdrantClient(url=settings.qdrant_url)

COLLECTION_NAME = "document_chunks"
VECTOR_SIZE = 4096  # qwen3-embedding:8b default output dimensions


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
