from typing import Literal

from pydantic import BaseModel


class ConversationTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class QueryRequest(BaseModel):
    question: str
    conversation_history: list[ConversationTurn] | None = None


class Citation(BaseModel):
    citation_number: int
    document_id: str
    document_filename: str
    chunk_id: str
    page_start: int
    page_end: int
    text_excerpt: str


class EntityReference(BaseModel):
    entity_id: str
    name: str
    type: str


class QueryResponse(BaseModel):
    query_id: str
    answer: str
    citations: list[Citation]
    entities_mentioned: list[EntityReference]
    no_results: bool = False
    suggested_followups: list[str] = []


class QuerySSEEvent(BaseModel):
    event: Literal[
        "query.translating",
        "query.searching",
        "query.streaming",
        "query.complete",
        "query.failed",
    ]
    data: dict
