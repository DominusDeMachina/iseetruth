from pydantic import BaseModel


class EntityRelationship(BaseModel):
    relation_type: str
    target_id: str | None
    target_name: str | None
    target_type: str | None
    confidence_score: float


class EntitySource(BaseModel):
    document_id: str
    document_filename: str
    chunk_id: str
    page_start: int
    page_end: int
    text_excerpt: str


class EntityListItem(BaseModel):
    id: str
    name: str
    type: str
    confidence_score: float
    source_count: int
    evidence_strength: str


class EntityTypeSummary(BaseModel):
    people: int
    organizations: int
    locations: int
    total: int


class EntityListResponse(BaseModel):
    items: list[EntityListItem]
    total: int
    summary: EntityTypeSummary


class EntityDetailResponse(BaseModel):
    id: str
    name: str
    type: str
    confidence_score: float
    investigation_id: str
    relationships: list[EntityRelationship]
    sources: list[EntitySource]
    evidence_strength: str
