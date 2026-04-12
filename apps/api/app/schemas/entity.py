from pydantic import BaseModel, field_validator


ALLOWED_ENTITY_TYPES = {"person", "organization", "location"}


class EntityCreateRequest(BaseModel):
    name: str
    type: str
    source_annotation: str | None = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Entity name must not be empty")
        return v.strip()

    @field_validator("type")
    @classmethod
    def valid_type(cls, v: str) -> str:
        v_lower = v.lower()
        if v_lower not in ALLOWED_ENTITY_TYPES:
            raise ValueError(f"Invalid entity type: {v}. Allowed: person, organization, location")
        return v_lower


class EntityUpdateRequest(BaseModel):
    name: str | None = None
    source_annotation: str | None = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str | None) -> str | None:
        if v is not None and not v.strip():
            raise ValueError("Entity name must not be empty")
        return v.strip() if v is not None else None

    def model_post_init(self, __context: object) -> None:
        if self.name is None and self.source_annotation is None:
            raise ValueError("At least one of 'name' or 'source_annotation' must be provided")


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
    source: str = "extracted"


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
    source: str = "extracted"
    source_annotation: str | None = None
    aliases: list[str] = []
