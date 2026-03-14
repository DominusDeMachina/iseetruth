import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgres import get_db
from app.schemas.chunk import ChunkWithContextResponse
from app.services.chunk import ChunkService

router = APIRouter(
    prefix="/investigations/{investigation_id}/chunks",
    tags=["chunks"],
)


@router.get("/{chunk_id}", response_model=ChunkWithContextResponse)
async def get_chunk_with_context(
    investigation_id: uuid.UUID,
    chunk_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    service = ChunkService(db)
    return await service.get_chunk_with_context(investigation_id, chunk_id)
