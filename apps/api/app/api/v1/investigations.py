import uuid

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgres import get_db
from app.models.document import Document
from app.schemas.investigation import (
    InvestigationCreate,
    InvestigationListResponse,
    InvestigationResponse,
)
from app.services.investigation import InvestigationService

router = APIRouter(prefix="/investigations", tags=["investigations"])


def _to_response(investigation, document_count: int = 0) -> InvestigationResponse:
    return InvestigationResponse(
        id=investigation.id,
        name=investigation.name,
        description=investigation.description,
        created_at=investigation.created_at,
        updated_at=investigation.updated_at,
        document_count=document_count,
        entity_count=0,
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


@router.get("/", response_model=InvestigationListResponse)
async def list_investigations(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    service = InvestigationService(db)
    investigations, total = await service.list_investigations(limit, offset)
    counts = await _get_document_counts_batch(
        [inv.id for inv in investigations], db
    )
    items = [_to_response(inv, counts.get(inv.id, 0)) for inv in investigations]
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
    return _to_response(investigation, doc_count)


@router.delete("/{investigation_id}", status_code=204)
async def delete_investigation(
    investigation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    service = InvestigationService(db)
    await service.delete_investigation(investigation_id)
    return Response(status_code=204)
