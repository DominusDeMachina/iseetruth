import asyncio
import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.api.v1.router import v1_router
from app.config import get_settings
from app.db.neo4j import driver as neo4j_driver
from app.db.redis import client as redis_client
from app.exceptions import DomainError, domain_error_handler, generic_error_handler

# ---------------------------------------------------------------------------
# Loguru configuration (Task 2)
# ---------------------------------------------------------------------------
logger.remove()
logger.add(
    sys.stdout,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
    level="INFO",
)


class InterceptHandler(logging.Handler):
    """Route stdlib logging (uvicorn, celery, etc.) through Loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno  # type: ignore[assignment]
        logger.opt(depth=6, exception=record.exc_info).log(level, record.getMessage())


logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)


# ---------------------------------------------------------------------------
# Lifespan (startup / shutdown)
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    logger.info("Running Alembic migrations")
    await asyncio.to_thread(_run_alembic_upgrade)

    logger.info("Application startup complete")
    yield
    # --- Shutdown ---
    logger.info("Closing Neo4j driver")
    await neo4j_driver.close()
    logger.info("Closing Redis connection")
    await redis_client.aclose()
    logger.info("Application shutdown complete")


def _run_alembic_upgrade() -> None:
    """Run ``alembic upgrade head`` programmatically."""
    from alembic import command
    from alembic.config import Config

    cfg = Config("alembic.ini")
    try:
        command.upgrade(cfg, "head")
        logger.info("Alembic migrations applied successfully")
    except Exception as exc:
        logger.warning("Alembic migration skipped or failed: {}", exc)


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
settings = get_settings()

app = FastAPI(
    title="OSINT Document Analyzer API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(v1_router)

app.add_exception_handler(DomainError, domain_error_handler)  # type: ignore[arg-type]
app.add_exception_handler(Exception, generic_error_handler)  # type: ignore[arg-type]
