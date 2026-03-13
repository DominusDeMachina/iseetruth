"""Unit tests for GraphQueryService."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.schemas.graph import GraphResponse
from app.services.graph_query import GraphQueryService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def investigation_id():
    return uuid.UUID("11111111-1111-1111-1111-111111111111")


@pytest.fixture
def entity_id():
    return "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"


@pytest.fixture
def neighbor_id():
    return "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"


def _make_neo4j_driver(execute_read_side_effect):
    """Build a mock async Neo4j driver with configurable execute_read behavior."""
    mock_driver = MagicMock()
    mock_session = AsyncMock()
    mock_driver.session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_driver.session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_session.execute_read.side_effect = execute_read_side_effect
    return mock_driver, mock_session


# ---------------------------------------------------------------------------
# Tests: get_subgraph
# ---------------------------------------------------------------------------

class TestGetSubgraph:
    @pytest.mark.asyncio
    async def test_returns_hub_nodes_ordered_by_relationship_count(
        self, investigation_id, entity_id, neighbor_id
    ):
        """Hub nodes should be sorted by relationship_count DESC."""
        hub_records = [
            {
                "id": entity_id,
                "name": "Horvat",
                "type": "Person",
                "confidence_score": 0.92,
                "relationship_count": 7,
            },
            {
                "id": neighbor_id,
                "name": "City Hall",
                "type": "Organization",
                "confidence_score": 0.88,
                "relationship_count": 5,
            },
        ]
        edge_records = [
            {
                "source": entity_id,
                "target": neighbor_id,
                "type": "WORKS_FOR",
                "confidence_score": 0.85,
            }
        ]
        total_counts = {"total_nodes": 10, "total_edges": 15}

        async def fake_execute_read(fn, *args, **kwargs):
            fname = fn.__name__
            if fname == "_fetch_hub_nodes":
                return hub_records
            elif fname == "_fetch_edges_between":
                return edge_records
            elif fname == "_fetch_total_counts":
                return total_counts
            return None

        driver, _ = _make_neo4j_driver(fake_execute_read)
        service = GraphQueryService(driver)
        result = await service.get_subgraph(investigation_id, limit=50, offset=0)

        assert isinstance(result, GraphResponse)
        assert len(result.nodes) == 2
        # First node should have higher relationship_count
        assert result.nodes[0].data.relationship_count == 7
        assert result.nodes[1].data.relationship_count == 5

    @pytest.mark.asyncio
    async def test_edge_filtering_between_hub_nodes(
        self, investigation_id, entity_id, neighbor_id
    ):
        """Only edges between hub nodes should be included."""
        hub_records = [
            {
                "id": entity_id,
                "name": "Horvat",
                "type": "Person",
                "confidence_score": 0.92,
                "relationship_count": 7,
            },
            {
                "id": neighbor_id,
                "name": "City Hall",
                "type": "Organization",
                "confidence_score": 0.88,
                "relationship_count": 5,
            },
        ]
        edge_records = [
            {
                "source": entity_id,
                "target": neighbor_id,
                "type": "WORKS_FOR",
                "confidence_score": 0.85,
            }
        ]
        total_counts = {"total_nodes": 10, "total_edges": 15}

        async def fake_execute_read(fn, *args, **kwargs):
            fname = fn.__name__
            if fname == "_fetch_hub_nodes":
                return hub_records
            elif fname == "_fetch_edges_between":
                return edge_records
            elif fname == "_fetch_total_counts":
                return total_counts
            return None

        driver, _ = _make_neo4j_driver(fake_execute_read)
        service = GraphQueryService(driver)
        result = await service.get_subgraph(investigation_id, limit=50, offset=0)

        assert len(result.edges) == 1
        edge = result.edges[0]
        assert edge.data.source == entity_id
        assert edge.data.target == neighbor_id
        assert edge.data.type == "WORKS_FOR"
        assert edge.data.id == f"{entity_id}-WORKS_FOR-{neighbor_id}"

    @pytest.mark.asyncio
    async def test_empty_investigation_returns_empty_response(self, investigation_id):
        """Empty investigation returns empty nodes/edges arrays."""
        total_counts = {"total_nodes": 0, "total_edges": 0}

        async def fake_execute_read(fn, *args, **kwargs):
            fname = fn.__name__
            if fname == "_fetch_hub_nodes":
                return []
            elif fname == "_fetch_total_counts":
                return total_counts
            return None

        driver, _ = _make_neo4j_driver(fake_execute_read)
        service = GraphQueryService(driver)
        result = await service.get_subgraph(investigation_id, limit=50, offset=0)

        assert isinstance(result, GraphResponse)
        assert result.nodes == []
        assert result.edges == []
        assert result.total_nodes == 0
        assert result.total_edges == 0

    @pytest.mark.asyncio
    async def test_total_counts_reflect_full_graph(
        self, investigation_id, entity_id
    ):
        """total_nodes/total_edges should reflect full investigation, not just the page."""
        hub_records = [
            {
                "id": entity_id,
                "name": "Horvat",
                "type": "Person",
                "confidence_score": 0.92,
                "relationship_count": 7,
            },
        ]
        total_counts = {"total_nodes": 150, "total_edges": 300}

        async def fake_execute_read(fn, *args, **kwargs):
            fname = fn.__name__
            if fname == "_fetch_hub_nodes":
                return hub_records
            elif fname == "_fetch_edges_between":
                return []
            elif fname == "_fetch_total_counts":
                return total_counts
            return None

        driver, _ = _make_neo4j_driver(fake_execute_read)
        service = GraphQueryService(driver)
        result = await service.get_subgraph(investigation_id, limit=1, offset=0)

        assert len(result.nodes) == 1
        assert result.total_nodes == 150
        assert result.total_edges == 300

    @pytest.mark.asyncio
    async def test_node_cytoscape_format(self, investigation_id, entity_id):
        """Nodes must have group='nodes' and proper data fields."""
        hub_records = [
            {
                "id": entity_id,
                "name": "Horvat",
                "type": "Person",
                "confidence_score": 0.92,
                "relationship_count": 7,
            },
        ]
        total_counts = {"total_nodes": 1, "total_edges": 0}

        async def fake_execute_read(fn, *args, **kwargs):
            fname = fn.__name__
            if fname == "_fetch_hub_nodes":
                return hub_records
            elif fname == "_fetch_edges_between":
                return []
            elif fname == "_fetch_total_counts":
                return total_counts
            return None

        driver, _ = _make_neo4j_driver(fake_execute_read)
        service = GraphQueryService(driver)
        result = await service.get_subgraph(investigation_id, limit=50, offset=0)

        node = result.nodes[0]
        assert node.group == "nodes"
        assert node.data.id == entity_id
        assert node.data.name == "Horvat"
        assert node.data.type == "Person"


# ---------------------------------------------------------------------------
# Tests: get_neighbors
# ---------------------------------------------------------------------------

class TestGetNeighbors:
    @pytest.mark.asyncio
    async def test_returns_neighbors_with_connecting_edges(
        self, investigation_id, entity_id, neighbor_id
    ):
        """Neighbor expansion returns the entity, its neighbors, and edges."""
        entity_record = {
            "id": entity_id,
            "name": "Horvat",
            "type": "Person",
            "confidence_score": 0.92,
            "relationship_count": 7,
        }
        neighbor_records = [
            {
                "id": neighbor_id,
                "name": "City Hall",
                "type": "Organization",
                "confidence_score": 0.88,
                "relationship_count": 5,
                "rel_source": entity_id,
                "rel_target": neighbor_id,
                "rel_type": "WORKS_FOR",
                "rel_confidence": 0.85,
            }
        ]

        async def fake_execute_read(fn, *args, **kwargs):
            fname = fn.__name__
            if fname == "_fetch_entity_exists":
                return entity_record
            elif fname == "_fetch_neighbors":
                return neighbor_records
            return None

        driver, _ = _make_neo4j_driver(fake_execute_read)
        service = GraphQueryService(driver)
        result = await service.get_neighbors(investigation_id, entity_id)

        assert isinstance(result, GraphResponse)
        # Should include the entity itself + the neighbor
        assert len(result.nodes) == 2
        assert len(result.edges) == 1
        # The expanded entity should be first
        assert result.nodes[0].data.id == entity_id
        assert result.nodes[1].data.id == neighbor_id
        # Edge direction must reflect actual Neo4j direction
        assert result.edges[0].data.source == entity_id
        assert result.edges[0].data.target == neighbor_id

    @pytest.mark.asyncio
    async def test_returns_none_for_nonexistent_entity(
        self, investigation_id, entity_id
    ):
        """get_neighbors returns None when entity doesn't exist."""

        async def fake_execute_read(fn, *args, **kwargs):
            fname = fn.__name__
            if fname == "_fetch_entity_exists":
                return None
            return None

        driver, _ = _make_neo4j_driver(fake_execute_read)
        service = GraphQueryService(driver)
        result = await service.get_neighbors(investigation_id, entity_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_entity_with_no_neighbors(self, investigation_id, entity_id):
        """Entity with no neighbors returns just the entity node."""
        entity_record = {
            "id": entity_id,
            "name": "Isolated Node",
            "type": "Person",
            "confidence_score": 0.5,
            "relationship_count": 0,
        }

        async def fake_execute_read(fn, *args, **kwargs):
            fname = fn.__name__
            if fname == "_fetch_entity_exists":
                return entity_record
            elif fname == "_fetch_neighbors":
                return []
            return None

        driver, _ = _make_neo4j_driver(fake_execute_read)
        service = GraphQueryService(driver)
        result = await service.get_neighbors(investigation_id, entity_id)

        assert isinstance(result, GraphResponse)
        assert len(result.nodes) == 1
        assert result.nodes[0].data.id == entity_id
        assert result.edges == []

    @pytest.mark.asyncio
    async def test_edge_id_is_deterministic_composite(
        self, investigation_id, entity_id, neighbor_id
    ):
        """Edge ID must be {source}-{type}-{target} composite."""
        entity_record = {
            "id": entity_id,
            "name": "Horvat",
            "type": "Person",
            "confidence_score": 0.92,
            "relationship_count": 7,
        }
        neighbor_records = [
            {
                "id": neighbor_id,
                "name": "City Hall",
                "type": "Organization",
                "confidence_score": 0.88,
                "relationship_count": 5,
                "rel_source": entity_id,
                "rel_target": neighbor_id,
                "rel_type": "WORKS_FOR",
                "rel_confidence": 0.85,
            }
        ]

        async def fake_execute_read(fn, *args, **kwargs):
            fname = fn.__name__
            if fname == "_fetch_entity_exists":
                return entity_record
            elif fname == "_fetch_neighbors":
                return neighbor_records
            return None

        driver, _ = _make_neo4j_driver(fake_execute_read)
        service = GraphQueryService(driver)
        result = await service.get_neighbors(investigation_id, entity_id)

        expected_edge_id = f"{entity_id}-WORKS_FOR-{neighbor_id}"
        assert result.edges[0].data.id == expected_edge_id

    @pytest.mark.asyncio
    async def test_null_confidence_defaults_to_zero(
        self, investigation_id, entity_id, neighbor_id
    ):
        """Null confidence_score from Neo4j should default to 0.0."""
        entity_record = {
            "id": entity_id,
            "name": "Horvat",
            "type": "Person",
            "confidence_score": None,
            "relationship_count": 1,
        }
        neighbor_records = [
            {
                "id": neighbor_id,
                "name": "Unknown Org",
                "type": "Organization",
                "confidence_score": None,
                "relationship_count": 1,
                "rel_source": entity_id,
                "rel_target": neighbor_id,
                "rel_type": "KNOWS",
                "rel_confidence": None,
            }
        ]

        async def fake_execute_read(fn, *args, **kwargs):
            fname = fn.__name__
            if fname == "_fetch_entity_exists":
                return entity_record
            elif fname == "_fetch_neighbors":
                return neighbor_records
            return None

        driver, _ = _make_neo4j_driver(fake_execute_read)
        service = GraphQueryService(driver)
        result = await service.get_neighbors(investigation_id, entity_id)

        assert result.nodes[0].data.confidence_score == 0.0
        assert result.nodes[1].data.confidence_score == 0.0
        assert result.edges[0].data.confidence_score == 0.0

    @pytest.mark.asyncio
    async def test_multiple_neighbors_with_different_rel_types(
        self, investigation_id, entity_id, neighbor_id
    ):
        """Multiple relationship types to the same neighbor produce 1 node + N edges."""
        third_id = "cccccccc-cccc-cccc-cccc-cccccccccccc"
        entity_record = {
            "id": entity_id,
            "name": "Horvat",
            "type": "Person",
            "confidence_score": 0.92,
            "relationship_count": 3,
        }
        neighbor_records = [
            {
                "id": neighbor_id,
                "name": "City Hall",
                "type": "Organization",
                "confidence_score": 0.88,
                "relationship_count": 5,
                "rel_source": entity_id,
                "rel_target": neighbor_id,
                "rel_type": "WORKS_FOR",
                "rel_confidence": 0.85,
            },
            {
                "id": neighbor_id,
                "name": "City Hall",
                "type": "Organization",
                "confidence_score": 0.88,
                "relationship_count": 5,
                "rel_source": entity_id,
                "rel_target": neighbor_id,
                "rel_type": "KNOWS",
                "rel_confidence": 0.70,
            },
            {
                "id": third_id,
                "name": "Zagreb",
                "type": "Location",
                "confidence_score": 0.75,
                "relationship_count": 2,
                "rel_source": entity_id,
                "rel_target": third_id,
                "rel_type": "LOCATED_AT",
                "rel_confidence": 0.90,
            },
        ]

        async def fake_execute_read(fn, *args, **kwargs):
            fname = fn.__name__
            if fname == "_fetch_entity_exists":
                return entity_record
            elif fname == "_fetch_neighbors":
                return neighbor_records
            return None

        driver, _ = _make_neo4j_driver(fake_execute_read)
        service = GraphQueryService(driver)
        result = await service.get_neighbors(investigation_id, entity_id)

        # 3 unique nodes: entity + neighbor_id + third_id
        assert len(result.nodes) == 3
        node_ids = [n.data.id for n in result.nodes]
        assert entity_id in node_ids
        assert neighbor_id in node_ids
        assert third_id in node_ids

        # 3 edges: WORKS_FOR + KNOWS to neighbor_id, LOCATED_AT to third_id
        assert len(result.edges) == 3
        edge_types = {e.data.type for e in result.edges}
        assert edge_types == {"WORKS_FOR", "KNOWS", "LOCATED_AT"}

        # Totals reflect full neighborhood
        assert result.total_nodes == 3
        assert result.total_edges == 3

    @pytest.mark.asyncio
    async def test_limit_truncates_neighbors(
        self, investigation_id, entity_id
    ):
        """Limit parameter caps the number of returned neighbor nodes."""
        entity_record = {
            "id": entity_id,
            "name": "Horvat",
            "type": "Person",
            "confidence_score": 0.92,
            "relationship_count": 3,
        }
        # Create 3 neighbors
        neighbor_records = []
        for i in range(3):
            nid = f"n{i}n{i}n{i}n{i}-n{i}n{i}-n{i}n{i}-n{i}n{i}-n{i}n{i}n{i}n{i}n{i}n{i}"
            neighbor_records.append(
                {
                    "id": nid,
                    "name": f"Neighbor {i}",
                    "type": "Person",
                    "confidence_score": 0.5,
                    "relationship_count": 1,
                    "rel_source": entity_id,
                    "rel_target": nid,
                    "rel_type": "KNOWS",
                    "rel_confidence": 0.5,
                }
            )

        async def fake_execute_read(fn, *args, **kwargs):
            fname = fn.__name__
            if fname == "_fetch_entity_exists":
                return entity_record
            elif fname == "_fetch_neighbors":
                return neighbor_records
            return None

        driver, _ = _make_neo4j_driver(fake_execute_read)
        service = GraphQueryService(driver)
        result = await service.get_neighbors(investigation_id, entity_id, limit=2)

        # 2 neighbors + the entity itself = 3 nodes returned
        assert len(result.nodes) == 3
        # But total_nodes reflects full neighborhood (3 neighbors + entity = 4)
        assert result.total_nodes == 4
        assert result.total_edges == 3
