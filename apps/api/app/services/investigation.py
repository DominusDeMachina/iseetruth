import os
import shutil
import uuid
from pathlib import Path

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import DomainError
from app.models.investigation import Investigation
from app.schemas.investigation import InvestigationCreate

STORAGE_ROOT = Path(os.environ.get("STORAGE_ROOT", "storage"))


class InvestigationNotFoundError(DomainError):
    def __init__(self, investigation_id: uuid.UUID):
        super().__init__(
            detail=f"No investigation found with id: {investigation_id}",
            status_code=404,
            error_type="investigation_not_found",
        )


class InvestigationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_investigation(self, data: InvestigationCreate) -> Investigation:
        investigation = Investigation(
            name=data.name,
            description=data.description,
        )
        self.db.add(investigation)
        await self.db.commit()
        await self.db.refresh(investigation)

        # Create storage directory
        storage_path = STORAGE_ROOT / str(investigation.id)
        storage_path.mkdir(parents=True, exist_ok=True)
        logger.info(
            "Investigation created",
            investigation_id=str(investigation.id),
            name=investigation.name,
        )
        return investigation

    async def list_investigations(
        self, limit: int = 50, offset: int = 0
    ) -> tuple[list[Investigation], int]:
        # Count total
        count_result = await self.db.execute(select(func.count(Investigation.id)))
        total = count_result.scalar_one()

        # Fetch paginated list
        stmt = (
            select(Investigation)
            .order_by(Investigation.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(stmt)
        investigations = list(result.scalars().all())
        return investigations, total

    async def get_investigation(self, investigation_id: uuid.UUID) -> Investigation:
        stmt = select(Investigation).where(Investigation.id == investigation_id)
        result = await self.db.execute(stmt)
        investigation = result.scalar_one_or_none()
        if investigation is None:
            raise InvestigationNotFoundError(investigation_id)
        return investigation

    async def delete_investigation(self, investigation_id: uuid.UUID) -> None:
        investigation = await self.get_investigation(investigation_id)

        # Cascading delete order:
        # 1. Neo4j (entities/relationships) — no-op in Story 2.1
        try:
            logger.info(
                "Neo4j cleanup skipped (no data yet)",
                investigation_id=str(investigation_id),
            )
        except Exception as exc:
            logger.error(
                "Neo4j cleanup failed",
                investigation_id=str(investigation_id),
                error=str(exc),
            )

        # 2. Qdrant (embeddings) — no-op in Story 2.1
        try:
            logger.info(
                "Qdrant cleanup skipped (no data yet)",
                investigation_id=str(investigation_id),
            )
        except Exception as exc:
            logger.error(
                "Qdrant cleanup failed",
                investigation_id=str(investigation_id),
                error=str(exc),
            )

        # 3. Filesystem
        try:
            storage_path = STORAGE_ROOT / str(investigation_id)
            if storage_path.exists():
                shutil.rmtree(storage_path)
                logger.info(
                    "Storage directory deleted",
                    investigation_id=str(investigation_id),
                )
        except Exception as exc:
            logger.error(
                "Filesystem cleanup failed",
                investigation_id=str(investigation_id),
                error=str(exc),
            )

        # 4. PostgreSQL (LAST — consistency point)
        await self.db.delete(investigation)
        await self.db.commit()
        logger.info(
            "Investigation deleted",
            investigation_id=str(investigation_id),
        )
