import uuid
from datetime import datetime

from pydantic import BaseModel


class DocumentResponse(BaseModel):
    id: uuid.UUID
    investigation_id: uuid.UUID
    filename: str
    size_bytes: int
    sha256_checksum: str
    status: str
    page_count: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]
    total: int


class UploadDocumentsResponse(BaseModel):
    items: list[DocumentResponse]
    errors: list[str]
