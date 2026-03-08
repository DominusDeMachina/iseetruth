import uuid

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgres import get_db
from app.schemas.investigation import (
    InvestigationCreate,
    InvestigationListResponse,
    InvestigationResponse,
)
from app.services.investigation import InvestigationService

router = APIRouter(prefix="/investigations", tags=["investigations"])


def _to_response(investigation) -> InvestigationResponse:
    return InvestigationResponse(
        id=investigation.id,
        name=investigation.name,
        description=investigation.description,
        created_at=investigation.created_at,
        updated_at=investigation.updated_at,
        document_count=0,
        entity_count=0,
    )


@router.post("/", status_code=201, response_model=InvestigationResponse)
async def create_investigation(
    data: InvestigationCreate,
    db: AsyncSession = Depends(get_db),
):
    service = InvestigationService(db)
    investigation = await service.create_investigation(data)
    return _to_response(investigation)


@router.get("/", response_model=InvestigationListResponse)
async def list_investigations(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    service = InvestigationService(db)
    investigations, total = await service.list_investigations(limit, offset)
    return InvestigationListResponse(
        items=[_to_response(inv) for inv in investigations],
        total=total,
    )


@router.get("/{investigation_id}", response_model=InvestigationResponse)
async def get_investigation(
    investigation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    service = InvestigationService(db)
    investigation = await service.get_investigation(investigation_id)
    return _to_response(investigation)


@router.delete("/{investigation_id}", status_code=204)
async def delete_investigation(
    investigation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    service = InvestigationService(db)
    await service.delete_investigation(investigation_id)
    return Response(status_code=204)
