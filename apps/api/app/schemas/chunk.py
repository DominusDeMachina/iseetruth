import uuid

from pydantic import BaseModel


class ChunkWithContextResponse(BaseModel):
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_filename: str
    sequence_number: int
    total_chunks: int
    text: str
    page_start: int
    page_end: int
    context_before: str | None
    context_after: str | None
