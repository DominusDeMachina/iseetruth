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
from app.db.qdrant import get_client as get_qdrant_client, ensure_qdrant_collection
from app.db.redis import client as redis_client
from app.db.sync_neo4j import sync_neo4j_driver
from app.exceptions import DomainError, domain_error_handler, generic_error_handler
from app.services.extraction import ensure_neo4j_constraints
from app.services.health_monitor import HealthMonitorService

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

    logger.info("Setting up Neo4j constraints and indexes")
    await asyncio.to_thread(ensure_neo4j_constraints, sync_neo4j_driver)
    logger.info("Neo4j constraints setup complete")

    logger.info("Setting up Qdrant collection")
    await asyncio.to_thread(ensure_qdrant_collection, get_qdrant_client())
    logger.info("Qdrant collection setup complete")

    logger.info("Starting health monitor")
    health_monitor = HealthMonitorService()
    health_monitor_task = asyncio.create_task(health_monitor.run())

    logger.info("Application startup complete")
    yield

    # Cancel health monitor
    health_monitor_task.cancel()
    try:
        await health_monitor_task
    except asyncio.CancelledError:
        pass
    # --- Shutdown ---
    logger.info("Closing Neo4j driver")
    await neo4j_driver.close()
    logger.info("Closing sync Neo4j driver")
    sync_neo4j_driver.close()
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
