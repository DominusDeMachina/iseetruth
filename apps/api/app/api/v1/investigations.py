import uuid

from fastapi import APIRouter, Depends, Query, Response
from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.neo4j import driver as neo4j_driver
from app.db.postgres import get_db
from app.models.document import Document
from app.schemas.investigation import (
    InvestigationCreate,
    InvestigationListResponse,
    InvestigationResponse,
)
from app.services.cross_investigation import CrossInvestigationService
from app.services.investigation import InvestigationService

router = APIRouter(prefix="/investigations", tags=["investigations"])


def _to_response(
    investigation, document_count: int = 0, cross_link_count: int = 0
) -> InvestigationResponse:
    return InvestigationResponse(
        id=investigation.id,
        name=investigation.name,
        description=investigation.description,
        created_at=investigation.created_at,
        updated_at=investigation.updated_at,
        document_count=document_count,
        entity_count=0,
        cross_link_count=cross_link_count,
    )


async def _get_document_count(
    investigation_id: uuid.UUID, db: AsyncSession
) -> int:
    count_result = await db.execute(
        select(func.count(Document.id)).where(
            Document.investigation_id == investigation_id
        )
    )
    return count_result.scalar_one()


async def _get_document_counts_batch(
    investigation_ids: list[uuid.UUID], db: AsyncSession
) -> dict[uuid.UUID, int]:
    if not investigation_ids:
        return {}
    stmt = (
        select(Document.investigation_id, func.count(Document.id))
        .where(Document.investigation_id.in_(investigation_ids))
        .group_by(Document.investigation_id)
    )
    result = await db.execute(stmt)
    return dict(result.all())


@router.post("/", status_code=201, response_model=InvestigationResponse)
async def create_investigation(
    data: InvestigationCreate,
    db: AsyncSession = Depends(get_db),
):
    service = InvestigationService(db)
    investigation = await service.create_investigation(data)
    return _to_response(investigation, document_count=0)


async def _get_cross_link_counts_batch(
    investigation_ids: list[uuid.UUID], db: AsyncSession
) -> dict[uuid.UUID, int]:
    """Get cross-investigation entity link counts via Neo4j. Best-effort."""
    if not investigation_ids:
        return {}
    try:
        service = CrossInvestigationService(neo4j_driver, db)
        str_ids = [str(inv_id) for inv_id in investigation_ids]
        raw_counts = await service.get_cross_link_counts(str_ids)
        return {uuid.UUID(k): v for k, v in raw_counts.items()}
    except Exception as exc:
        logger.warning("Failed to fetch cross-link counts", error=str(exc))
        return {}


@router.get("/", response_model=InvestigationListResponse)
async def list_investigations(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    service = InvestigationService(db)
    investigations, total = await service.list_investigations(limit, offset)
    inv_ids = [inv.id for inv in investigations]
    counts = await _get_document_counts_batch(inv_ids, db)
    cross_counts = await _get_cross_link_counts_batch(inv_ids, db)
    items = [
        _to_response(inv, counts.get(inv.id, 0), cross_counts.get(inv.id, 0))
        for inv in investigations
    ]
    return InvestigationListResponse(
        items=items,
        total=total,
    )


@router.get("/{investigation_id}", response_model=InvestigationResponse)
async def get_investigation(
    investigation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    service = InvestigationService(db)
    investigation = await service.get_investigation(investigation_id)
    doc_count = await _get_document_count(investigation_id, db)
    cross_counts = await _get_cross_link_counts_batch([investigation_id], db)
    cross_count = cross_counts.get(investigation_id, 0)
    return _to_response(investigation, doc_count, cross_count)


@router.delete("/{investigation_id}", status_code=204)
async def delete_investigation(
    investigation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    service = InvestigationService(db)
    await service.delete_investigation(investigation_id)
    return Response(status_code=204)
