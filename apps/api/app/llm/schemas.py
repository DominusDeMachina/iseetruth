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


class RelationType(str, Enum):
    WORKS_FOR = "WORKS_FOR"
    KNOWS = "KNOWS"
    LOCATED_AT = "LOCATED_AT"


class ExtractedRelationship(BaseModel):
    source_entity_name: str
    target_entity_name: str
    relation_type: RelationType
    confidence: float = Field(ge=0.0, le=1.0)


class RelationshipExtractionResponse(BaseModel):
    relationships: list[ExtractedRelationship]


class QueryTranslation(BaseModel):
    cypher_queries: list[str]
    search_terms: list[str]
    entity_names: list[str]
