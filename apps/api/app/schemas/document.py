import uuid
from datetime import datetime

from pydantic import BaseModel, computed_field


class DocumentResponse(BaseModel):
    id: uuid.UUID
    investigation_id: uuid.UUID
    filename: str
    size_bytes: int
    sha256_checksum: str
    document_type: str = "pdf"
    status: str
    page_count: int | None
    entity_count: int | None = None
    extraction_confidence: float | None = None
    extracted_text: str | None = None
    error_message: str | None = None
    failed_stage: str | None = None
    retry_count: int = 0

    @computed_field
    @property
    def extraction_quality(self) -> str | None:
        if self.extraction_confidence is None:
            return None
        if self.extraction_confidence >= 0.7:
            return "high"
        if self.extraction_confidence >= 0.4:
            return "medium"
        return "low"

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
