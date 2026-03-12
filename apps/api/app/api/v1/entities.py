import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.neo4j import driver as neo4j_driver
from app.db.postgres import get_db
from app.exceptions import EntityNotFoundError
from app.schemas.entity import EntityDetailResponse
from app.services.entity_query import EntityQueryService

router = APIRouter(prefix="/investigations", tags=["entities"])


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
