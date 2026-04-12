from pydantic import BaseModel


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
