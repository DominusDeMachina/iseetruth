import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.neo4j import driver as neo4j_driver
from app.db.postgres import get_db
from app.exceptions import (
    EntityNotFoundError,
    EntitySelfMergeError,
    EntityTypeMismatchError,
)
from app.schemas.entity import (
    EntityCreateRequest,
    EntityDetailResponse,
    EntityListResponse,
    EntityMergePreview,
    EntityMergeRequest,
    EntityMergeResponse,
    EntityUpdateRequest,
)
from app.services.entity_query import EntityQueryService
from app.services.events import EventPublisher

router = APIRouter(prefix="/investigations", tags=["entities"])

ALLOWED_ENTITY_TYPES = {"person", "organization", "location"}


@router.get(
    "/{investigation_id}/entities/",
    response_model=EntityListResponse,
)
async def list_entities(
    investigation_id: uuid.UUID,
    type: str | None = None,
    search: str | None = Query(None),
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
        investigation_id, entity_type=type, search=search, limit=limit, offset=offset
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


@router.post(
    "/{investigation_id}/entities/",
    response_model=EntityDetailResponse,
    status_code=201,
)
async def create_entity(
    investigation_id: uuid.UUID,
    body: EntityCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a manual entity in the investigation's knowledge graph."""
    service = EntityQueryService(neo4j_driver, db)
    return await service.create_entity(
        investigation_id,
        name=body.name,
        entity_type=body.type,
        source_annotation=body.source_annotation,
    )


@router.patch(
    "/{investigation_id}/entities/{entity_id}",
    response_model=EntityDetailResponse,
)
async def update_entity(
    investigation_id: uuid.UUID,
    entity_id: str,
    body: EntityUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update an entity's name and/or source annotation."""
    service = EntityQueryService(neo4j_driver, db)
    result = await service.update_entity(
        investigation_id,
        entity_id,
        name=body.name,
        source_annotation=body.source_annotation,
    )
    if result is None:
        raise EntityNotFoundError(entity_id)
    return result


async def _validate_merge_request(
    service: EntityQueryService,
    investigation_id: uuid.UUID,
    body: EntityMergeRequest,
) -> tuple:
    """Validate merge request: entities exist, same type, not self-merge.

    Returns (source_detail, target_detail) on success.
    """
    if body.source_entity_id == body.target_entity_id:
        raise EntitySelfMergeError()

    source = await service.get_entity_detail(
        investigation_id, body.source_entity_id
    )
    if source is None:
        raise EntityNotFoundError(body.source_entity_id)

    target = await service.get_entity_detail(
        investigation_id, body.target_entity_id
    )
    if target is None:
        raise EntityNotFoundError(body.target_entity_id)

    if source.type != target.type:
        raise EntityTypeMismatchError(source.type, target.type)

    return source, target


@router.post(
    "/{investigation_id}/entities/merge/preview",
    response_model=EntityMergePreview,
)
async def merge_entities_preview(
    investigation_id: uuid.UUID,
    body: EntityMergeRequest,
    db: AsyncSession = Depends(get_db),
):
    """Preview the result of merging two entities."""
    service = EntityQueryService(neo4j_driver, db)
    await _validate_merge_request(service, investigation_id, body)

    preview = await service.preview_merge(
        investigation_id,
        body.source_entity_id,
        body.target_entity_id,
    )
    if preview is None:
        raise EntityNotFoundError(body.source_entity_id)
    return preview


@router.post(
    "/{investigation_id}/entities/merge",
    response_model=EntityMergeResponse,
)
async def merge_entities(
    investigation_id: uuid.UUID,
    body: EntityMergeRequest,
    db: AsyncSession = Depends(get_db),
):
    """Merge source entity into target entity, preserving all relationships and citations."""
    service = EntityQueryService(neo4j_driver, db)
    await _validate_merge_request(service, investigation_id, body)

    result = await service.merge_entities(
        investigation_id,
        body.source_entity_id,
        body.target_entity_id,
        primary_name=body.primary_name,
    )

    # Publish SSE event (best-effort)
    try:
        settings = get_settings()
        publisher = EventPublisher(settings.redis_url)
        publisher.publish(
            investigation_id=str(investigation_id),
            event_type="entity.merged",
            payload={
                "source_entity_id": body.source_entity_id,
                "target_entity_id": body.target_entity_id,
                "merged_entity_name": result.merged_entity.name,
            },
        )
        publisher.close()
    except Exception as exc:
        logger.warning(
            "Failed to publish entity.merged SSE event",
            error=str(exc),
            investigation_id=str(investigation_id),
        )

    return result
