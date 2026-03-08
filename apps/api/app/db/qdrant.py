from qdrant_client import QdrantClient

from app.config import get_settings

settings = get_settings()

client = QdrantClient(url=settings.qdrant_url)
