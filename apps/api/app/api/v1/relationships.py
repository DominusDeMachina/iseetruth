import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.neo4j import driver as neo4j_driver
from app.db.postgres import get_db
from app.schemas.relationship import RelationshipCreateRequest, RelationshipResponse
from app.services.entity_query import EntityQueryService

router = APIRouter(prefix="/investigations", tags=["relationships"])


@router.post(
    "/{investigation_id}/relationships/",
    response_model=RelationshipResponse,
    status_code=201,
)
async def create_relationship(
    investigation_id: uuid.UUID,
    body: RelationshipCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a manual relationship between two entities in the investigation's knowledge graph."""
    service = EntityQueryService(neo4j_driver, db)
    result = await service.create_relationship(
        investigation_id,
        source_entity_id=body.source_entity_id,
        target_entity_id=body.target_entity_id,
        rel_type=body.type,
        source_annotation=body.source_annotation,
    )
    if result.already_existed:
        return JSONResponse(
            status_code=200,
            content=result.model_dump(),
        )
    return result
