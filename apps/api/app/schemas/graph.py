from typing import Literal

from pydantic import BaseModel


class GraphNodeData(BaseModel):
    id: str
    name: str
    type: str
    confidence_score: float
    relationship_count: int


class GraphNode(BaseModel):
    group: Literal["nodes"]
    data: GraphNodeData


class GraphEdgeData(BaseModel):
    id: str
    source: str
    target: str
    type: str
    confidence_score: float
    origin: str = "extracted"
    source_annotation: str | None = None


class GraphEdge(BaseModel):
    group: Literal["edges"]
    data: GraphEdgeData


class GraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    total_nodes: int
    total_edges: int
