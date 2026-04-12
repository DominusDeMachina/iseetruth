import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.neo4j import driver as neo4j_driver
from app.db.postgres import get_db
from app.models.investigation import Investigation
from app.schemas.cross_investigation import (
    CrossInvestigationEntityDetail,
    CrossInvestigationResponse,
    CrossInvestigationSearchResponse,
    DismissMatchRequest,
)
from app.services.cross_investigation import CrossInvestigationService

router = APIRouter(prefix="/investigations", tags=["cross-investigation"])


@router.get(
    "/{investigation_id}/cross-links/",
    response_model=CrossInvestigationResponse,
)
async def get_cross_investigation_links(
    investigation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Find entities in this investigation that also appear in other investigations."""
    # Validate investigation exists
    result = await db.execute(
        select(Investigation.id).where(Investigation.id == investigation_id)
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail=f"Investigation {investigation_id} not found")

    service = CrossInvestigationService(neo4j_driver, db)
    return await service.find_matches(investigation_id)


# --- Story 10.2: New endpoints ---


cross_links_router = APIRouter(prefix="/cross-links", tags=["cross-investigation"])


@cross_links_router.get(
    "/entity-detail/",
    response_model=CrossInvestigationEntityDetail,
)
async def get_cross_investigation_entity_detail(
    entity_name: str = Query(..., min_length=1),
    entity_type: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed entity presence across all investigations."""
    service = CrossInvestigationService(neo4j_driver, db)
    return await service.get_entity_detail_across_investigations(
        entity_name=entity_name,
        entity_type=entity_type,
    )


@cross_links_router.get(
    "/search/",
    response_model=CrossInvestigationSearchResponse,
)
async def search_cross_investigation(
    q: str = Query(..., min_length=1),
    type: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Search for entities by name across all investigations."""
    service = CrossInvestigationService(neo4j_driver, db)
    return await service.search_across_investigations(
        query=q,
        entity_type=type,
        limit=limit,
    )


@router.post(
    "/{investigation_id}/cross-links/dismiss",
    status_code=201,
)
async def dismiss_cross_investigation_match(
    investigation_id: uuid.UUID,
    body: DismissMatchRequest,
    db: AsyncSession = Depends(get_db),
):
    """Dismiss a cross-investigation match as false positive."""
    # Validate source investigation exists
    result = await db.execute(
        select(Investigation.id).where(Investigation.id == investigation_id)
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail=f"Investigation {investigation_id} not found")

    service = CrossInvestigationService(neo4j_driver, db)
    created = await service.dismiss_match(
        source_investigation_id=investigation_id,
        entity_name=body.entity_name,
        entity_type=body.entity_type,
        target_investigation_id=body.target_investigation_id,
    )
    if not created:
        raise HTTPException(status_code=409, detail="Match already dismissed")
    return {"status": "dismissed"}


@router.delete(
    "/{investigation_id}/cross-links/dismiss",
    status_code=204,
)
async def undismiss_cross_investigation_match(
    investigation_id: uuid.UUID,
    body: DismissMatchRequest,
    db: AsyncSession = Depends(get_db),
):
    """Undo a dismissed cross-investigation match."""
    service = CrossInvestigationService(neo4j_driver, db)
    deleted = await service.undismiss_match(
        source_investigation_id=investigation_id,
        entity_name=body.entity_name,
        entity_type=body.entity_type,
        target_investigation_id=body.target_investigation_id,
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Dismissed match not found")
