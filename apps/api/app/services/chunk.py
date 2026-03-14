import uuid

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ChunkNotFoundError
from app.models.chunk import DocumentChunk
from app.models.document import Document
from app.schemas.chunk import ChunkWithContextResponse


class ChunkService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_chunk_with_context(
        self, investigation_id: uuid.UUID, chunk_id: uuid.UUID
    ) -> ChunkWithContextResponse:
        # 1. Fetch the target chunk and verify investigation_id
        stmt = select(DocumentChunk).where(
            DocumentChunk.id == chunk_id,
            DocumentChunk.investigation_id == investigation_id,
        )
        result = await self.db.execute(stmt)
        chunk = result.scalar_one_or_none()
        if chunk is None:
            raise ChunkNotFoundError(str(chunk_id))

        # 2. Fetch document filename
        doc_stmt = select(Document.filename).where(Document.id == chunk.document_id)
        doc_result = await self.db.execute(doc_stmt)
        document_filename = doc_result.scalar_one()

        # 3. Count total chunks for this document
        count_stmt = select(func.count(DocumentChunk.id)).where(
            DocumentChunk.document_id == chunk.document_id
        )
        count_result = await self.db.execute(count_stmt)
        total_chunks = count_result.scalar_one()

        # 4. Fetch adjacent chunks for context
        context_before = None
        context_after = None

        if chunk.sequence_number > 0:
            prev_stmt = (
                select(DocumentChunk.text)
                .where(
                    DocumentChunk.document_id == chunk.document_id,
                    DocumentChunk.sequence_number == chunk.sequence_number - 1,
                )
                .limit(1)
            )
            prev_result = await self.db.execute(prev_stmt)
            context_before = prev_result.scalar_one_or_none()

        next_stmt = (
            select(DocumentChunk.text)
            .where(
                DocumentChunk.document_id == chunk.document_id,
                DocumentChunk.sequence_number == chunk.sequence_number + 1,
            )
            .limit(1)
        )
        next_result = await self.db.execute(next_stmt)
        context_after = next_result.scalar_one_or_none()

        logger.debug(
            "Chunk context fetched",
            chunk_id=str(chunk_id),
            investigation_id=str(investigation_id),
            sequence_number=chunk.sequence_number,
            total_chunks=total_chunks,
        )

        return ChunkWithContextResponse(
            chunk_id=chunk.id,
            document_id=chunk.document_id,
            document_filename=document_filename,
            sequence_number=chunk.sequence_number,
            total_chunks=total_chunks,
            text=chunk.text,
            page_start=chunk.page_start,
            page_end=chunk.page_end,
            context_before=context_before,
            context_after=context_after,
        )
