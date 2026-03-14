"""Integration tests for graph API endpoints."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.schemas.graph import (
    GraphEdge,
    GraphEdgeData,
    GraphNode,
    GraphNodeData,
    GraphResponse,
)


INVESTIGATION_ID = "11111111-1111-1111-1111-111111111111"
ENTITY_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
NEIGHBOR_ID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"


def _sample_subgraph_response() -> GraphResponse:
    return GraphResponse(
        nodes=[
            GraphNode(
                group="nodes",
                data=GraphNodeData(
                    id=ENTITY_ID,
                    name="Deputy Mayor Horvat",
                    type="Person",
                    confidence_score=0.92,
                    relationship_count=7,
                ),
            ),
            GraphNode(
                group="nodes",
                data=GraphNodeData(
                    id=NEIGHBOR_ID,
                    name="City Hall",
                    type="Organization",
                    confidence_score=0.88,
                    relationship_count=5,
                ),
            ),
        ],
        edges=[
            GraphEdge(
                group="edges",
                data=GraphEdgeData(
                    id=f"{ENTITY_ID}-WORKS_FOR-{NEIGHBOR_ID}",
                    source=ENTITY_ID,
                    target=NEIGHBOR_ID,
                    type="WORKS_FOR",
                    confidence_score=0.85,
                ),
            ),
        ],
        total_nodes=150,
        total_edges=300,
    )


def _sample_neighbors_response() -> GraphResponse:
    return GraphResponse(
        nodes=[
            GraphNode(
                group="nodes",
                data=GraphNodeData(
                    id=ENTITY_ID,
                    name="Deputy Mayor Horvat",
                    type="Person",
                    confidence_score=0.92,
                    relationship_count=7,
                ),
            ),
            GraphNode(
                group="nodes",
                data=GraphNodeData(
                    id=NEIGHBOR_ID,
                    name="City Hall",
                    type="Organization",
                    confidence_score=0.88,
                    relationship_count=5,
                ),
            ),
        ],
        edges=[
            GraphEdge(
                group="edges",
                data=GraphEdgeData(
                    id=f"{ENTITY_ID}-WORKS_FOR-{NEIGHBOR_ID}",
                    source=ENTITY_ID,
                    target=NEIGHBOR_ID,
                    type="WORKS_FOR",
                    confidence_score=0.85,
                ),
            ),
        ],
        total_nodes=2,
        total_edges=1,
    )


def _empty_graph_response() -> GraphResponse:
    return GraphResponse(nodes=[], edges=[], total_nodes=0, total_edges=0)


@pytest.fixture
def graph_client():
    from app.main import app

    yield TestClient(app)


class TestGetSubgraph:
    def test_returns_200_with_nodes_and_edges(self, graph_client):
        with patch("app.api.v1.graph.GraphQueryService") as mock_svc_cls:
            mock_svc = AsyncMock()
            mock_svc.get_subgraph = AsyncMock(
                return_value=_sample_subgraph_response()
            )
            mock_svc_cls.return_value = mock_svc

            response = graph_client.get(
                f"/api/v1/investigations/{INVESTIGATION_ID}/graph/"
            )

        assert response.status_code == 200
        data = response.json()
        assert len(data["nodes"]) == 2
        assert len(data["edges"]) == 1
        assert data["total_nodes"] == 150
        assert data["total_edges"] == 300

    def test_nodes_have_cytoscape_format(self, graph_client):
        with patch("app.api.v1.graph.GraphQueryService") as mock_svc_cls:
            mock_svc = AsyncMock()
            mock_svc.get_subgraph = AsyncMock(
                return_value=_sample_subgraph_response()
            )
            mock_svc_cls.return_value = mock_svc

            response = graph_client.get(
                f"/api/v1/investigations/{INVESTIGATION_ID}/graph/"
            )

        data = response.json()
        node = data["nodes"][0]
        assert node["group"] == "nodes"
        assert "id" in node["data"]
        assert "name" in node["data"]
        assert "type" in node["data"]
        assert "confidence_score" in node["data"]
        assert "relationship_count" in node["data"]

    def test_edges_have_cytoscape_format(self, graph_client):
        with patch("app.api.v1.graph.GraphQueryService") as mock_svc_cls:
            mock_svc = AsyncMock()
            mock_svc.get_subgraph = AsyncMock(
                return_value=_sample_subgraph_response()
            )
            mock_svc_cls.return_value = mock_svc

            response = graph_client.get(
                f"/api/v1/investigations/{INVESTIGATION_ID}/graph/"
            )

        data = response.json()
        edge = data["edges"][0]
        assert edge["group"] == "edges"
        assert "id" in edge["data"]
        assert "source" in edge["data"]
        assert "target" in edge["data"]
        assert "type" in edge["data"]
        assert "confidence_score" in edge["data"]

    def test_empty_graph_returns_empty_arrays(self, graph_client):
        with patch("app.api.v1.graph.GraphQueryService") as mock_svc_cls:
            mock_svc = AsyncMock()
            mock_svc.get_subgraph = AsyncMock(return_value=_empty_graph_response())
            mock_svc_cls.return_value = mock_svc

            response = graph_client.get(
                f"/api/v1/investigations/{INVESTIGATION_ID}/graph/"
            )

        assert response.status_code == 200
        data = response.json()
        assert data["nodes"] == []
        assert data["edges"] == []
        assert data["total_nodes"] == 0
        assert data["total_edges"] == 0

    def test_returns_422_for_non_uuid_investigation_id(self, graph_client):
        response = graph_client.get(
            "/api/v1/investigations/not-a-uuid/graph/"
        )
        assert response.status_code == 422

    def test_pagination_params_passed_to_service(self, graph_client):
        with patch("app.api.v1.graph.GraphQueryService") as mock_svc_cls:
            mock_svc = AsyncMock()
            mock_svc.get_subgraph = AsyncMock(return_value=_empty_graph_response())
            mock_svc_cls.return_value = mock_svc

            graph_client.get(
                f"/api/v1/investigations/{INVESTIGATION_ID}/graph/?limit=10&offset=20"
            )

            mock_svc.get_subgraph.assert_called_once()
            call_kwargs = mock_svc.get_subgraph.call_args
            assert call_kwargs.kwargs["limit"] == 10
            assert call_kwargs.kwargs["offset"] == 20


class TestGetSubgraphFilters:
    """Tests for entity type and document filter params on GET /graph/."""

    def test_entity_types_filter_passed_to_service(self, graph_client):
        """entity_types query param is parsed and passed to service."""
        with patch("app.api.v1.graph.GraphQueryService") as mock_svc_cls:
            mock_svc = AsyncMock()
            mock_svc.get_subgraph = AsyncMock(return_value=_empty_graph_response())
            mock_svc_cls.return_value = mock_svc

            graph_client.get(
                f"/api/v1/investigations/{INVESTIGATION_ID}/graph/?entity_types=person"
            )

            mock_svc.get_subgraph.assert_called_once()
            call_kwargs = mock_svc.get_subgraph.call_args
            assert call_kwargs.kwargs["entity_types"] == ["person"]

    def test_multiple_entity_types_filter(self, graph_client):
        """Comma-separated entity_types are parsed into a list."""
        with patch("app.api.v1.graph.GraphQueryService") as mock_svc_cls:
            mock_svc = AsyncMock()
            mock_svc.get_subgraph = AsyncMock(return_value=_empty_graph_response())
            mock_svc_cls.return_value = mock_svc

            graph_client.get(
                f"/api/v1/investigations/{INVESTIGATION_ID}/graph/?entity_types=person,organization"
            )

            call_kwargs = mock_svc.get_subgraph.call_args
            assert call_kwargs.kwargs["entity_types"] == ["person", "organization"]

    def test_document_id_filter_passed_to_service(self, graph_client):
        """document_id query param is passed to service."""
        doc_id = "22222222-2222-2222-2222-222222222222"
        with patch("app.api.v1.graph.GraphQueryService") as mock_svc_cls:
            mock_svc = AsyncMock()
            mock_svc.get_subgraph = AsyncMock(return_value=_empty_graph_response())
            mock_svc_cls.return_value = mock_svc

            graph_client.get(
                f"/api/v1/investigations/{INVESTIGATION_ID}/graph/?document_id={doc_id}"
            )

            call_kwargs = mock_svc.get_subgraph.call_args
            assert call_kwargs.kwargs["document_id"] == doc_id

    def test_combined_filters_passed_to_service(self, graph_client):
        """entity_types + document_id applied simultaneously (AND logic)."""
        doc_id = "22222222-2222-2222-2222-222222222222"
        with patch("app.api.v1.graph.GraphQueryService") as mock_svc_cls:
            mock_svc = AsyncMock()
            mock_svc.get_subgraph = AsyncMock(return_value=_empty_graph_response())
            mock_svc_cls.return_value = mock_svc

            graph_client.get(
                f"/api/v1/investigations/{INVESTIGATION_ID}/graph/"
                f"?entity_types=person&document_id={doc_id}"
            )

            call_kwargs = mock_svc.get_subgraph.call_args
            assert call_kwargs.kwargs["entity_types"] == ["person"]
            assert call_kwargs.kwargs["document_id"] == doc_id

    def test_no_filters_passes_none(self, graph_client):
        """No filter params → entity_types=None, document_id=None."""
        with patch("app.api.v1.graph.GraphQueryService") as mock_svc_cls:
            mock_svc = AsyncMock()
            mock_svc.get_subgraph = AsyncMock(return_value=_empty_graph_response())
            mock_svc_cls.return_value = mock_svc

            graph_client.get(
                f"/api/v1/investigations/{INVESTIGATION_ID}/graph/"
            )

            call_kwargs = mock_svc.get_subgraph.call_args
            assert call_kwargs.kwargs["entity_types"] is None
            assert call_kwargs.kwargs["document_id"] is None

    def test_invalid_entity_type_returns_422(self, graph_client):
        """Invalid entity type returns 422."""
        response = graph_client.get(
            f"/api/v1/investigations/{INVESTIGATION_ID}/graph/?entity_types=invalid"
        )
        assert response.status_code == 422

    def test_invalid_document_id_returns_422(self, graph_client):
        """Non-UUID document_id returns 422."""
        response = graph_client.get(
            f"/api/v1/investigations/{INVESTIGATION_ID}/graph/?document_id=not-a-uuid"
        )
        assert response.status_code == 422


class TestGetNeighbors:
    def test_returns_200_with_neighbors(self, graph_client):
        with patch("app.api.v1.graph.GraphQueryService") as mock_svc_cls:
            mock_svc = AsyncMock()
            mock_svc.get_neighbors = AsyncMock(
                return_value=_sample_neighbors_response()
            )
            mock_svc_cls.return_value = mock_svc

            response = graph_client.get(
                f"/api/v1/investigations/{INVESTIGATION_ID}/graph/neighbors/{ENTITY_ID}"
            )

        assert response.status_code == 200
        data = response.json()
        assert len(data["nodes"]) == 2
        assert len(data["edges"]) == 1

    def test_returns_404_for_unknown_entity(self, graph_client):
        with patch("app.api.v1.graph.GraphQueryService") as mock_svc_cls:
            mock_svc = AsyncMock()
            mock_svc.get_neighbors = AsyncMock(return_value=None)
            mock_svc_cls.return_value = mock_svc

            response = graph_client.get(
                f"/api/v1/investigations/{INVESTIGATION_ID}/graph/neighbors/{ENTITY_ID}"
            )

        assert response.status_code == 404
        data = response.json()
        assert "entity_not_found" in data["type"]

    def test_returns_422_for_non_uuid_investigation_id(self, graph_client):
        response = graph_client.get(
            f"/api/v1/investigations/not-a-uuid/graph/neighbors/{ENTITY_ID}"
        )
        assert response.status_code == 422

    def test_limit_param_passed_to_service(self, graph_client):
        with patch("app.api.v1.graph.GraphQueryService") as mock_svc_cls:
            mock_svc = AsyncMock()
            mock_svc.get_neighbors = AsyncMock(
                return_value=_sample_neighbors_response()
            )
            mock_svc_cls.return_value = mock_svc

            graph_client.get(
                f"/api/v1/investigations/{INVESTIGATION_ID}/graph/neighbors/{ENTITY_ID}?limit=10"
            )

            mock_svc.get_neighbors.assert_called_once()
            call_kwargs = mock_svc.get_neighbors.call_args
            assert call_kwargs.kwargs["limit"] == 10


class TestBuildLabelExpr:
    """Unit tests for _build_label_expr — critical Cypher label construction."""

    def test_no_filter_returns_all_labels(self):
        from app.services.graph_query import _build_label_expr

        assert _build_label_expr(None) == "Person|Organization|Location"

    def test_empty_list_returns_all_labels(self):
        from app.services.graph_query import _build_label_expr

        assert _build_label_expr([]) == "Person|Organization|Location"

    def test_single_type(self):
        from app.services.graph_query import _build_label_expr

        assert _build_label_expr(["person"]) == "Person"

    def test_multiple_types(self):
        from app.services.graph_query import _build_label_expr

        result = _build_label_expr(["person", "organization"])
        assert result == "Person|Organization"

    def test_all_types(self):
        from app.services.graph_query import _build_label_expr

        result = _build_label_expr(["person", "organization", "location"])
        assert result == "Person|Organization|Location"

    def test_case_insensitive_mapping(self):
        from app.services.graph_query import _build_label_expr

        assert _build_label_expr(["Person"]) == "Person"
        assert _build_label_expr(["ORGANIZATION"]) == "Organization"
