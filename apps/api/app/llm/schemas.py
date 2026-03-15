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


class ExtractedRelationship(BaseModel):
    source_entity_name: str
    target_entity_name: str
    relation_type: str
    confidence: float = Field(ge=0.0, le=1.0)


class RelationshipExtractionResponse(BaseModel):
    relationships: list[ExtractedRelationship]


class QueryTranslation(BaseModel):
    cypher_queries: list[str]
    search_terms: list[str]
    entity_names: list[str]
