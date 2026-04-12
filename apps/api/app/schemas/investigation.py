import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class InvestigationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=2000)


class InvestigationResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime
    document_count: int = 0
    entity_count: int = 0
    cross_link_count: int = 0

    model_config = {"from_attributes": True}


class InvestigationListResponse(BaseModel):
    items: list[InvestigationResponse]
    total: int
