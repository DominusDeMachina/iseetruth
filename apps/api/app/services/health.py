import asyncio
from datetime import datetime, timezone

import httpx
import psutil
from loguru import logger
from sqlalchemy import text

from app.config import get_settings
from app.db.neo4j import driver as neo4j_driver
from app.db.postgres import async_session_factory
from app.db.qdrant import get_client as get_qdrant_client
from app.db.redis import client as redis_client
from app.schemas.health import (
    HealthResponse,
    ModelInfo,
    OllamaStatus,
    OverallStatusEnum,
    ServiceStatus,
    StatusEnum,
)

CHAT_MODELS = ["qwen3.5:9b"]
VISION_MODELS = ["moondream2"]
EMBEDDING_MODELS = ["qwen3-embedding:8b"]
REQUIRED_MODELS = CHAT_MODELS + VISION_MODELS + EMBEDDING_MODELS
CHECK_TIMEOUT = 5.0  # seconds
MIN_RAM_GB = 12


class HealthService:
    async def check_postgres(self) -> ServiceStatus:
        try:
            async with async_session_factory() as session:
                await asyncio.wait_for(
                    session.execute(text("SELECT 1")), timeout=CHECK_TIMEOUT
                )
            return ServiceStatus(status=StatusEnum.healthy, detail="Connected")
        except Exception as exc:
            logger.warning("PostgreSQL health check failed", error=str(exc))
            return ServiceStatus(
                status=StatusEnum.unavailable,
                detail=f"Connection failed: {exc}",
            )

    async def check_neo4j(self) -> ServiceStatus:
        try:
            await asyncio.wait_for(
                neo4j_driver.verify_connectivity(), timeout=CHECK_TIMEOUT
            )
            server_info = await neo4j_driver.get_server_info()
            agent = server_info.agent if server_info else "unknown"
            return ServiceStatus(
                status=StatusEnum.healthy,
                detail=f"Connected, server agent: {agent}",
            )
        except Exception as exc:
            logger.warning("Neo4j health check failed", error=str(exc))
            return ServiceStatus(
                status=StatusEnum.unavailable,
                detail=f"Connection failed: {exc}",
            )

    async def check_qdrant(self) -> ServiceStatus:
        try:
            info = await asyncio.wait_for(
                asyncio.to_thread(get_qdrant_client().info), timeout=CHECK_TIMEOUT
            )
            version = getattr(info, "version", "unknown")
            return ServiceStatus(
                status=StatusEnum.healthy,
                detail=f"Connected, version: {version}",
            )
        except Exception as exc:
            logger.warning("Qdrant health check failed", error=str(exc))
            return ServiceStatus(
                status=StatusEnum.unavailable,
                detail=f"Connection failed: {exc}",
            )

    async def check_redis(self) -> ServiceStatus:
        try:
            result = await asyncio.wait_for(
                redis_client.ping(), timeout=CHECK_TIMEOUT
            )
            if result:
                return ServiceStatus(status=StatusEnum.healthy, detail="Connected")
            return ServiceStatus(
                status=StatusEnum.unhealthy, detail="Ping returned False"
            )
        except Exception as exc:
            logger.warning("Redis health check failed", error=str(exc))
            return ServiceStatus(
                status=StatusEnum.unavailable,
                detail=f"Connection failed: {exc}",
            )

    async def _check_ollama_instance(self, base_url: str, required: list[str]) -> tuple[set[str], list[ModelInfo]]:
        """Query a single Ollama instance and return (downloaded_set, model_infos)."""
        async with httpx.AsyncClient(timeout=CHECK_TIMEOUT) as http:
            resp = await http.get(f"{base_url}/api/tags")
            resp.raise_for_status()
            data = resp.json()
        downloaded = {m["name"] for m in data.get("models", [])}
        infos = [ModelInfo(name=name, available=name in downloaded) for name in required]
        return downloaded, infos

    async def check_ollama(self) -> OllamaStatus:
        settings = get_settings()
        models: list[ModelInfo] = []
        chat_failed = False
        emb_failed = False

        try:
            _, chat_infos = await self._check_ollama_instance(
                settings.ollama_base_url, CHAT_MODELS + VISION_MODELS
            )
            models.extend(chat_infos)
        except Exception as exc:
            chat_failed = True
            logger.warning("Ollama chat instance health check failed", error=str(exc))
            models.extend([ModelInfo(name=name, available=False) for name in CHAT_MODELS + VISION_MODELS])

        try:
            _, emb_infos = await self._check_ollama_instance(settings.ollama_embedding_url, EMBEDDING_MODELS)
            models.extend(emb_infos)
        except Exception as exc:
            emb_failed = True
            logger.warning("Ollama embedding instance health check failed", error=str(exc))
            models.extend([ModelInfo(name=name, available=False) for name in EMBEDDING_MODELS])

        all_ready = all(m.available for m in models)
        both_failed = chat_failed and emb_failed

        if all_ready:
            return OllamaStatus(
                status=StatusEnum.healthy,
                detail="Running, all models ready",
                models_ready=True,
                models=models,
            )
        missing = [m.name for m in models if not m.available]
        return OllamaStatus(
            status=StatusEnum.unavailable if both_failed else StatusEnum.unhealthy,
            detail=f"Connection failed" if both_failed else f"Models not ready: {', '.join(missing)}",
            models_ready=False,
            models=models,
        )

    def check_hardware(self) -> list[str]:
        warnings: list[str] = []
        try:
            ram_gb = psutil.virtual_memory().total / (1024**3)
            if ram_gb < MIN_RAM_GB:
                warnings.append(
                    f"System RAM ({ram_gb:.1f}GB) below recommended {MIN_RAM_GB}GB minimum"
                )
        except Exception as exc:
            logger.warning("Hardware check failed", error=str(exc))
        return warnings

    async def get_health(self) -> HealthResponse:
        pg, neo, qd, rd, ol = await asyncio.gather(
            self.check_postgres(),
            self.check_neo4j(),
            self.check_qdrant(),
            self.check_redis(),
            self.check_ollama(),
        )

        services: dict = {
            "postgres": pg,
            "neo4j": neo,
            "qdrant": qd,
            "redis": rd,
            "ollama": ol,
        }

        warnings = self.check_hardware()

        statuses = [s.status for s in services.values()]
        if all(s == StatusEnum.healthy for s in statuses):
            overall = OverallStatusEnum.healthy
        elif any(s == StatusEnum.unavailable for s in statuses) or all(
            s != StatusEnum.healthy for s in statuses
        ):
            overall = OverallStatusEnum.unhealthy
        else:
            overall = OverallStatusEnum.degraded

        return HealthResponse(
            status=overall,
            timestamp=datetime.now(timezone.utc),
            services=services,
            warnings=warnings,
        )
