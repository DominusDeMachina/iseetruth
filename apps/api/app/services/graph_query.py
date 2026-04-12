import uuid
from contextlib import asynccontextmanager

from loguru import logger
from neo4j.exceptions import ServiceUnavailable, SessionExpired

from app.exceptions import GraphUnavailableError
from app.schemas.graph import (
    GraphEdge,
    GraphEdgeData,
    GraphNode,
    GraphNodeData,
    GraphResponse,
)


class GraphQueryService:
    def __init__(self, neo4j_driver):
        self.neo4j_driver = neo4j_driver

    @asynccontextmanager
    async def _safe_session(self):
        """Wrap Neo4j session creation with graceful error handling."""
        try:
            async with self.neo4j_driver.session() as session:
                yield session
        except (ServiceUnavailable, SessionExpired, ConnectionRefusedError, OSError) as exc:
            logger.error("Neo4j unavailable", error=str(exc))
            raise GraphUnavailableError("Graph database unavailable")

    async def get_subgraph(
        self,
        investigation_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
        entity_types: list[str] | None = None,
        document_id: str | None = None,
    ) -> GraphResponse:
        """Return hub nodes ordered by relationship_count DESC and edges between them."""
        inv_id_str = str(investigation_id)

        async with self._safe_session() as session:
            hub_records = await session.execute_read(
                _fetch_hub_nodes, inv_id_str, limit, offset, entity_types, document_id
            )

            if not hub_records:
                total_counts = await session.execute_read(
                    _fetch_total_counts, inv_id_str, entity_types, document_id
                )
                return GraphResponse(
                    nodes=[],
                    edges=[],
                    total_nodes=total_counts["total_nodes"],
                    total_edges=total_counts["total_edges"],
                )

            node_ids = [r["id"] for r in hub_records]

            edge_records = await session.execute_read(
                _fetch_edges_between, inv_id_str, node_ids
            )
            total_counts = await session.execute_read(
                _fetch_total_counts, inv_id_str, entity_types, document_id
            )

        nodes = [
            GraphNode(
                group="nodes",
                data=GraphNodeData(
                    id=r["id"],
                    name=r["name"],
                    type=r["type"],
                    confidence_score=r["confidence_score"] or 0.0,
                    relationship_count=r["relationship_count"],
                ),
            )
            for r in hub_records
        ]

        edges = [
            GraphEdge(
                group="edges",
                data=GraphEdgeData(
                    id=f"{r['source']}-{r['type']}-{r['target']}",
                    source=r["source"],
                    target=r["target"],
                    type=r["type"],
                    confidence_score=r["confidence_score"] or 0.0,
                ),
            )
            for r in edge_records
        ]

        return GraphResponse(
            nodes=nodes,
            edges=edges,
            total_nodes=total_counts["total_nodes"],
            total_edges=total_counts["total_edges"],
        )

    async def get_neighbors(
        self, investigation_id: uuid.UUID, entity_id: str, limit: int = 50
    ) -> GraphResponse | None:
        """Return immediate neighbors of an entity and connecting edges.

        Returns None if the entity does not exist.
        ``total_nodes`` / ``total_edges`` reflect the full neighborhood size
        (before any limit truncation), consistent with ``get_subgraph``.
        """
        inv_id_str = str(investigation_id)

        async with self._safe_session() as session:
            # Verify entity exists
            entity_record = await session.execute_read(
                _fetch_entity_exists, entity_id, inv_id_str
            )
            if entity_record is None:
                return None

            neighbor_records = await session.execute_read(
                _fetch_neighbors, entity_id, inv_id_str
            )

        # Build nodes and edges from neighbor records
        seen_node_ids: set[str] = set()
        nodes: list[GraphNode] = []
        edges: list[GraphEdge] = []

        # Include the expanded entity itself
        nodes.append(
            GraphNode(
                group="nodes",
                data=GraphNodeData(
                    id=entity_record["id"],
                    name=entity_record["name"],
                    type=entity_record["type"],
                    confidence_score=entity_record["confidence_score"] or 0.0,
                    relationship_count=entity_record["relationship_count"],
                ),
            )
        )
        seen_node_ids.add(entity_record["id"])

        for r in neighbor_records:
            # Add neighbor node (deduplicate)
            if r["id"] not in seen_node_ids:
                seen_node_ids.add(r["id"])
                nodes.append(
                    GraphNode(
                        group="nodes",
                        data=GraphNodeData(
                            id=r["id"],
                            name=r["name"],
                            type=r["type"],
                            confidence_score=r["confidence_score"] or 0.0,
                            relationship_count=r["relationship_count"],
                        ),
                    )
                )

            # Add connecting edge
            source = r["rel_source"]
            target = r["rel_target"]
            rel_type = r["rel_type"]
            edge_id = f"{source}-{rel_type}-{target}"
            edges.append(
                GraphEdge(
                    group="edges",
                    data=GraphEdgeData(
                        id=edge_id,
                        source=source,
                        target=target,
                        type=rel_type,
                        confidence_score=r["rel_confidence"] or 0.0,
                    ),
                )
            )

        # Full neighborhood totals before truncation (consistent with get_subgraph)
        full_total_nodes = len(nodes)
        full_total_edges = len(edges)

        # Limit neighbors to requested count (first node is the expanded entity)
        if len(nodes) > limit + 1:
            nodes = [nodes[0]] + nodes[1 : limit + 1]
            included_ids = {n.data.id for n in nodes}
            edges = [
                e
                for e in edges
                if e.data.source in included_ids and e.data.target in included_ids
            ]

        return GraphResponse(
            nodes=nodes,
            edges=edges,
            total_nodes=full_total_nodes,
            total_edges=full_total_edges,
        )


# ---------------------------------------------------------------------------
# Neo4j read transaction helpers
# ---------------------------------------------------------------------------


def _build_label_expr(entity_types: list[str] | None) -> str:
    """Build a Neo4j label expression from entity types.

    Maps lowercase API types to PascalCase Neo4j labels.
    Returns 'Person|Organization|Location' when no filter is applied.
    """
    type_map = {"person": "Person", "organization": "Organization", "location": "Location"}
    if not entity_types:
        return "Person|Organization|Location"
    return "|".join(type_map[t.lower()] for t in entity_types)


async def _fetch_hub_nodes(
    tx,
    investigation_id: str,
    limit: int,
    offset: int,
    entity_types: list[str] | None = None,
    document_id: str | None = None,
):
    """Fetch entity nodes ordered by relationship count (hub detection)."""
    label_expr = _build_label_expr(entity_types)
    params: dict = {
        "investigation_id": investigation_id,
        "offset": offset,
        "limit": limit,
    }

    if document_id:
        # Filter by document via MENTIONED_IN relationship
        params["document_id"] = document_id
        query = (
            f"MATCH (e:{label_expr} {{investigation_id: $investigation_id}})"
            "-[:MENTIONED_IN]->(d:Document {id: $document_id, investigation_id: $investigation_id}) "
            "WITH DISTINCT e "
            "OPTIONAL MATCH (e)-[r]-({investigation_id: $investigation_id}) "
            "WHERE type(r) <> 'MENTIONED_IN' "
            "WITH e, labels(e)[0] AS type, COUNT(r) AS relationship_count "
            "ORDER BY relationship_count DESC "
            "SKIP $offset LIMIT $limit "
            "RETURN e.id AS id, e.name AS name, type, "
            "e.confidence_score AS confidence_score, relationship_count"
        )
    else:
        query = (
            f"MATCH (e:{label_expr} {{investigation_id: $investigation_id}}) "
            "OPTIONAL MATCH (e)-[r]-({investigation_id: $investigation_id}) "
            "WHERE type(r) <> 'MENTIONED_IN' "
            "WITH e, labels(e)[0] AS type, COUNT(r) AS relationship_count "
            "ORDER BY relationship_count DESC "
            "SKIP $offset LIMIT $limit "
            "RETURN e.id AS id, e.name AS name, type, "
            "e.confidence_score AS confidence_score, relationship_count"
        )

    result = await tx.run(query, **params)
    return await result.data()


async def _fetch_edges_between(tx, investigation_id: str, node_ids: list[str]):
    """Fetch directed edges between a set of node IDs."""
    result = await tx.run(
        "MATCH (src:Person|Organization|Location {investigation_id: $investigation_id})"
        "-[r]->"
        "(tgt:Person|Organization|Location {investigation_id: $investigation_id}) "
        "WHERE src.id IN $node_ids AND tgt.id IN $node_ids "
        "AND type(r) <> 'MENTIONED_IN' "
        "RETURN src.id AS source, tgt.id AS target, "
        "type(r) AS type, r.confidence_score AS confidence_score",
        investigation_id=investigation_id,
        node_ids=node_ids,
    )
    return await result.data()


async def _fetch_total_counts(
    tx,
    investigation_id: str,
    entity_types: list[str] | None = None,
    document_id: str | None = None,
):
    """Fetch total node and edge counts for an investigation (with optional filters)."""
    label_expr = _build_label_expr(entity_types)
    params: dict = {"investigation_id": investigation_id}

    if document_id:
        params["document_id"] = document_id
        query = (
            f"MATCH (e:{label_expr} {{investigation_id: $investigation_id}})"
            "-[:MENTIONED_IN]->(d:Document {id: $document_id, investigation_id: $investigation_id}) "
            "WITH DISTINCT e "
            "OPTIONAL MATCH (e)-[r]-({investigation_id: $investigation_id}) "
            "WHERE type(r) <> 'MENTIONED_IN' "
            "RETURN COUNT(DISTINCT e) AS total_nodes, COUNT(DISTINCT r) AS total_edges"
        )
    else:
        query = (
            f"MATCH (e:{label_expr} {{investigation_id: $investigation_id}}) "
            "OPTIONAL MATCH (e)-[r]-({investigation_id: $investigation_id}) "
            "WHERE type(r) <> 'MENTIONED_IN' "
            "RETURN COUNT(DISTINCT e) AS total_nodes, COUNT(DISTINCT r) AS total_edges"
        )

    result = await tx.run(query, **params)
    record = await result.single()
    if record is None:
        return {"total_nodes": 0, "total_edges": 0}
    return {"total_nodes": record["total_nodes"], "total_edges": record["total_edges"]}


async def _fetch_entity_exists(tx, entity_id: str, investigation_id: str):
    """Check if entity exists and return basic info with relationship count."""
    result = await tx.run(
        "MATCH (e:Person|Organization|Location "
        "{id: $entity_id, investigation_id: $investigation_id}) "
        "OPTIONAL MATCH (e)-[r]-({investigation_id: $investigation_id}) "
        "WHERE type(r) <> 'MENTIONED_IN' "
        "WITH e, labels(e)[0] AS type, COUNT(r) AS relationship_count "
        "RETURN e.id AS id, e.name AS name, type, "
        "e.confidence_score AS confidence_score, relationship_count",
        entity_id=entity_id,
        investigation_id=investigation_id,
    )
    return await result.single()


async def _fetch_neighbors(tx, entity_id: str, investigation_id: str):
    """Fetch immediate neighbors and connecting edges for an entity."""
    result = await tx.run(
        "MATCH (e:Person|Organization|Location "
        "{id: $entity_id, investigation_id: $investigation_id})"
        "-[r]-"
        "(neighbor:Person|Organization|Location "
        "{investigation_id: $investigation_id}) "
        "WHERE type(r) <> 'MENTIONED_IN' "
        "WITH neighbor, r, labels(neighbor)[0] AS type "
        "OPTIONAL MATCH (neighbor)-[r2]-"
        "({investigation_id: $investigation_id}) "
        "WHERE type(r2) <> 'MENTIONED_IN' "
        "RETURN neighbor.id AS id, neighbor.name AS name, type, "
        "neighbor.confidence_score AS confidence_score, "
        "COUNT(r2) AS relationship_count, "
        "startNode(r).id AS rel_source, endNode(r).id AS rel_target, "
        "type(r) AS rel_type, r.confidence_score AS rel_confidence",
        entity_id=entity_id,
        investigation_id=investigation_id,
    )
    return await result.data()
