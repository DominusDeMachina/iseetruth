import re

from pydantic import BaseModel, field_validator


ALLOWED_RELATIONSHIP_TYPES = {"WORKS_FOR", "KNOWS", "LOCATED_AT", "MENTIONED_IN"}

# Pattern for custom relationship types: UPPER_SNAKE_CASE, starts with letter
_UPPER_SNAKE_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")


class RelationshipCreateRequest(BaseModel):
    source_entity_id: str
    target_entity_id: str
    type: str
    source_annotation: str | None = None

    @field_validator("source_annotation")
    @classmethod
    def annotation_max_length(cls, v: str | None) -> str | None:
        if v is not None and len(v) > 2000:
            raise ValueError("Source annotation must not exceed 2000 characters")
        return v

    @field_validator("source_entity_id", "target_entity_id")
    @classmethod
    def id_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Entity ID must not be empty")
        return v.strip()

    @field_validator("type")
    @classmethod
    def valid_type(cls, v: str) -> str:
        v_upper = v.strip().upper()
        if v_upper in ALLOWED_RELATIONSHIP_TYPES:
            return v_upper
        if _UPPER_SNAKE_RE.match(v_upper):
            return v_upper
        raise ValueError(
            f"Invalid relationship type: {v}. Must be one of {sorted(ALLOWED_RELATIONSHIP_TYPES)} "
            "or a custom UPPER_SNAKE_CASE identifier"
        )

    def model_post_init(self, __context: object) -> None:
        if self.source_entity_id == self.target_entity_id:
            raise ValueError("Source and target entities must be different")


class RelationshipResponse(BaseModel):
    id: str
    source_entity_id: str
    target_entity_id: str
    source_entity_name: str
    target_entity_name: str
    type: str
    confidence_score: float
    source: str
    source_annotation: str | None = None
    already_existed: bool = False
