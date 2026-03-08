from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import get_settings

settings = get_settings()

# Convert async URL to sync: postgresql+asyncpg:// → postgresql+psycopg2://
_raw_url = settings.database_url
if _raw_url.startswith("postgresql+asyncpg://"):
    _sync_url = _raw_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
elif _raw_url.startswith("postgresql://"):
    _sync_url = _raw_url.replace("postgresql://", "postgresql+psycopg2://", 1)
elif _raw_url.startswith("postgres://"):
    _sync_url = _raw_url.replace("postgres://", "postgresql+psycopg2://", 1)
else:
    _sync_url = _raw_url

sync_engine = create_engine(_sync_url)
SyncSessionLocal = sessionmaker(bind=sync_engine)
