import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.neo4j import driver as neo4j_driver
from app.db.postgres import get_db
from app.exceptions import EntityNotFoundError
from app.schemas.entity import EntityDetailResponse, EntityListResponse
from app.services.entity_query import EntityQueryService

router = APIRouter(prefix="/investigations", tags=["entities"])

ALLOWED_ENTITY_TYPES = {"person", "organization", "location"}


@router.get(
    "/{investigation_id}/entities/",
    response_model=EntityListResponse,
)
async def list_entities(
    investigation_id: uuid.UUID,
    type: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Return paginated entity list with confidence scores and summary counts."""
    if type is not None and type.lower() not in ALLOWED_ENTITY_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid entity type: {type}. Allowed: person, organization, location",
        )
    service = EntityQueryService(neo4j_driver, db)
    return await service.list_entities(
        investigation_id, entity_type=type, limit=limit, offset=offset
    )


@router.get(
    "/{investigation_id}/entities/{entity_id}",
    response_model=EntityDetailResponse,
)
async def get_entity_detail(
    investigation_id: uuid.UUID,
    entity_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Return entity detail with relationships and provenance sources."""
    service = EntityQueryService(neo4j_driver, db)
    result = await service.get_entity_detail(investigation_id, entity_id)
    if result is None:
        raise EntityNotFoundError(entity_id)
    return result
