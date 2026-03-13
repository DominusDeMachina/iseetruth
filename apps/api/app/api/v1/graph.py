import uuid

from fastapi import APIRouter, Query

from app.db.neo4j import driver as neo4j_driver
from app.exceptions import EntityNotFoundError
from app.schemas.graph import GraphResponse
from app.services.graph_query import GraphQueryService

router = APIRouter(prefix="/investigations", tags=["graph"])


@router.get("/{investigation_id}/graph/", response_model=GraphResponse)
async def get_subgraph(
    investigation_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    service = GraphQueryService(neo4j_driver)
    return await service.get_subgraph(investigation_id, limit=limit, offset=offset)


@router.get(
    "/{investigation_id}/graph/neighbors/{entity_id}",
    response_model=GraphResponse,
)
async def get_neighbors(
    investigation_id: uuid.UUID,
    entity_id: str,
    limit: int = Query(50, ge=1, le=200),
):
    service = GraphQueryService(neo4j_driver)
    result = await service.get_neighbors(investigation_id, entity_id, limit=limit)
    if result is None:
        raise EntityNotFoundError(entity_id)
    return result
