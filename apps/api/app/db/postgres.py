from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings

settings = get_settings()

# Convert database URL to use the asyncpg driver
_raw_url = settings.database_url
if _raw_url.startswith("postgresql+asyncpg://"):
    _async_url = _raw_url
elif _raw_url.startswith("postgresql://"):
    _async_url = _raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)
elif _raw_url.startswith("postgres://"):
    _async_url = _raw_url.replace("postgres://", "postgresql+asyncpg://", 1)
else:
    raise ValueError(f"Unsupported database URL scheme: {_raw_url}")

engine = create_async_engine(_async_url, echo=False)

async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncSession:
    """FastAPI dependency: yields an async SQLAlchemy session."""
    async with async_session_factory() as session:
        yield session
