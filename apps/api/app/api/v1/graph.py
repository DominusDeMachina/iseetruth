import uuid

from fastapi import APIRouter, HTTPException, Query

from app.api.v1.entities import ALLOWED_ENTITY_TYPES
from app.db.neo4j import driver as neo4j_driver
from app.exceptions import EntityNotFoundError, GraphUnavailableError
from app.schemas.graph import GraphResponse
from app.services.graph_query import GraphQueryService

router = APIRouter(prefix="/investigations", tags=["graph"])


@router.get("/{investigation_id}/graph/", response_model=GraphResponse)
async def get_subgraph(
    investigation_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    entity_types: str | None = Query(None),
    document_id: str | None = Query(None),
):
    # Parse and validate entity_types (normalize to lowercase at boundary)
    parsed_entity_types: list[str] | None = None
    if entity_types is not None:
        parsed_entity_types = [t.strip().lower() for t in entity_types.split(",") if t.strip()]
        for t in parsed_entity_types:
            if t not in ALLOWED_ENTITY_TYPES:
                raise HTTPException(
                    status_code=422,
                    detail=f"Invalid entity type: {t}. Allowed: person, organization, location",
                )
        if not parsed_entity_types:
            parsed_entity_types = None

    # Validate document_id is a valid UUID if provided
    if document_id is not None:
        try:
            uuid.UUID(document_id)
        except ValueError:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid document_id: {document_id}. Must be a valid UUID.",
            )

    service = GraphQueryService(neo4j_driver)
    return await service.get_subgraph(
        investigation_id,
        limit=limit,
        offset=offset,
        entity_types=parsed_entity_types,
        document_id=document_id,
    )


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
