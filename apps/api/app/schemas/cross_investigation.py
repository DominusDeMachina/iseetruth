import uuid

from pydantic import BaseModel, Field


class InvestigationEntityInfo(BaseModel):
    investigation_id: str
    investigation_name: str
    entity_id: str
    relationship_count: int
    confidence_score: float


class CrossInvestigationMatch(BaseModel):
    entity_name: str
    entity_type: str
    match_confidence: float
    match_type: str  # "exact" or "case_insensitive"
    source_entity_id: str
    source_relationship_count: int
    source_confidence_score: float
    investigations: list[InvestigationEntityInfo]


class CrossInvestigationResponse(BaseModel):
    matches: list[CrossInvestigationMatch]
    total_matches: int
    query_duration_ms: float


# --- Story 10.2: Entity detail across investigations ---


class EntityRelationshipInfo(BaseModel):
    type: str
    target_name: str | None = None
    target_type: str | None = None
    confidence_score: float = 0.0


class EntityDocumentInfo(BaseModel):
    document_id: str
    filename: str
    mention_count: int = 1


class InvestigationPresence(BaseModel):
    investigation_id: str
    investigation_name: str
    entity_id: str
    relationships: list[EntityRelationshipInfo] = Field(default_factory=list)
    source_documents: list[EntityDocumentInfo] = Field(default_factory=list)
    relationship_count: int = 0
    confidence_score: float = 0.0


class CrossInvestigationEntityDetail(BaseModel):
    entity_name: str
    entity_type: str
    investigations: list[InvestigationPresence] = Field(default_factory=list)
    total_investigations: int = 0


# --- Story 10.2: Cross-investigation search ---


class CrossInvestigationSearchResultInvestigation(BaseModel):
    investigation_id: str
    investigation_name: str
    entity_id: str
    relationship_count: int = 0


class CrossInvestigationSearchResult(BaseModel):
    entity_name: str
    entity_type: str
    investigation_count: int = 0
    investigations: list[CrossInvestigationSearchResultInvestigation] = Field(
        default_factory=list
    )
    match_score: float = 1.0


class CrossInvestigationSearchResponse(BaseModel):
    results: list[CrossInvestigationSearchResult] = Field(default_factory=list)
    total_results: int = 0
    query_duration_ms: float = 0.0


# --- Story 10.2: Dismiss false-positive matches ---


class DismissMatchRequest(BaseModel):
    entity_name: str
    entity_type: str
    target_investigation_id: uuid.UUID
