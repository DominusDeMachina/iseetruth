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
    extracted_text: str | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentTextResponse(BaseModel):
    document_id: uuid.UUID
    filename: str
    page_count: int | None
    extracted_text: str | None
    status: str


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]
    total: int


class UploadDocumentsResponse(BaseModel):
    items: list[DocumentResponse]
    errors: list[str]
