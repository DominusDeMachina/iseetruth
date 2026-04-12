import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.neo4j import driver as neo4j_driver
from app.db.postgres import get_db
from app.models.investigation import Investigation
from app.schemas.cross_investigation import CrossInvestigationResponse
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
