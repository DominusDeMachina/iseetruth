from enum import Enum

from pydantic import BaseModel, Field


class EntityType(str, Enum):
    person = "person"
    organization = "organization"
    location = "location"


class ExtractedEntity(BaseModel):
    name: str
    type: EntityType
    confidence: float = Field(ge=0.0, le=1.0)


class EntityExtractionResponse(BaseModel):
    entities: list[ExtractedEntity]
