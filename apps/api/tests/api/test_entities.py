"""Integration tests for entities API endpoints."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.schemas.entity import (
    EntityDetailResponse,
    EntityListItem,
    EntityListResponse,
    EntityRelationship,
    EntitySource,
    EntityTypeSummary,
)


INVESTIGATION_ID = "11111111-1111-1111-1111-111111111111"
ENTITY_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"


def _sample_response() -> EntityDetailResponse:
    return EntityDetailResponse(
        id=ENTITY_ID,
        name="John Smith",
        type="person",
        confidence_score=0.9,
        investigation_id=INVESTIGATION_ID,
        relationships=[
            EntityRelationship(
                relation_type="WORKS_FOR",
                target_id="bbbb",
                target_name="Acme Corp",
                target_type="organization",
                confidence_score=0.85,
            )
        ],
        sources=[
            EntitySource(
                document_id="dddd",
                document_filename="report.pdf",
                chunk_id="cccc",
                page_start=1,
                page_end=2,
                text_excerpt="John Smith works at Acme Corp.",
            )
        ],
        evidence_strength="single_source",
    )


@pytest.fixture
def entity_client(mock_db_session):
    """TestClient with get_db and neo4j driver overridden."""
    from app.db.postgres import get_db
    from app.main import app

    async def override_get_db():
        yield mock_db_session

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


class TestGetEntityDetail:
    def test_returns_200_with_entity_detail(self, entity_client):
        with patch(
            "app.api.v1.entities.EntityQueryService"
        ) as mock_svc_cls:
            mock_svc = AsyncMock()
            mock_svc.get_entity_detail = AsyncMock(return_value=_sample_response())
            mock_svc_cls.return_value = mock_svc

            response = entity_client.get(
                f"/api/v1/investigations/{INVESTIGATION_ID}/entities/{ENTITY_ID}"
            )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == ENTITY_ID
        assert data["name"] == "John Smith"
        assert data["type"] == "person"
        assert data["confidence_score"] == 0.9
        assert data["evidence_strength"] == "single_source"
        assert len(data["relationships"]) == 1
        assert data["relationships"][0]["relation_type"] == "WORKS_FOR"
        assert len(data["sources"]) == 1
        assert data["sources"][0]["document_filename"] == "report.pdf"

    def test_returns_404_when_entity_not_found(self, entity_client):
        with patch(
            "app.api.v1.entities.EntityQueryService"
        ) as mock_svc_cls:
            mock_svc = AsyncMock()
            mock_svc.get_entity_detail = AsyncMock(return_value=None)
            mock_svc_cls.return_value = mock_svc

            response = entity_client.get(
                f"/api/v1/investigations/{INVESTIGATION_ID}/entities/{ENTITY_ID}"
            )

        assert response.status_code == 404
        data = response.json()
        assert "entity_not_found" in data["type"]
        assert ENTITY_ID in data["detail"]

    def test_returns_422_for_non_uuid_investigation_id(self, entity_client):
        """Non-UUID investigation_id path param → FastAPI 422 Unprocessable Entity."""
        response = entity_client.get(
            "/api/v1/investigations/not-a-uuid/entities/some-entity-id"
        )
        assert response.status_code == 422

    def test_empty_relationships_and_sources(self, entity_client):
        """Response with no relationships or sources is valid."""
        empty_response = EntityDetailResponse(
            id=ENTITY_ID,
            name="Ghost",
            type="person",
            confidence_score=0.5,
            investigation_id=INVESTIGATION_ID,
            relationships=[],
            sources=[],
            evidence_strength="none",
        )
        with patch(
            "app.api.v1.entities.EntityQueryService"
        ) as mock_svc_cls:
            mock_svc = AsyncMock()
            mock_svc.get_entity_detail = AsyncMock(return_value=empty_response)
            mock_svc_cls.return_value = mock_svc

            response = entity_client.get(
                f"/api/v1/investigations/{INVESTIGATION_ID}/entities/{ENTITY_ID}"
            )

        assert response.status_code == 200
        data = response.json()
        assert data["relationships"] == []
        assert data["sources"] == []
        assert data["evidence_strength"] == "none"


def _list_response(items: list[EntityListItem], total: int | None = None) -> EntityListResponse:
    """Helper to build an EntityListResponse for search tests."""
    type_counts = {"Person": 0, "Organization": 0, "Location": 0}
    for item in items:
        key = item.type.capitalize()
        if key in type_counts:
            type_counts[key] += 1
    t = total if total is not None else len(items)
    return EntityListResponse(
        items=items,
        total=t,
        summary=EntityTypeSummary(
            people=type_counts["Person"],
            organizations=type_counts["Organization"],
            locations=type_counts["Location"],
            total=t,
        ),
    )


_JOHN = EntityListItem(
    id="e1", name="John Smith", type="person", confidence_score=0.9,
    source_count=3, evidence_strength="corroborated",
)
_JANE = EntityListItem(
    id="e2", name="Jane Johnson", type="person", confidence_score=0.85,
    source_count=2, evidence_strength="corroborated",
)
_ACME = EntityListItem(
    id="e3", name="Acme Organization", type="organization", confidence_score=0.8,
    source_count=1, evidence_strength="single_source",
)
_BERLIN = EntityListItem(
    id="e4", name="Berlin", type="location", confidence_score=0.7,
    source_count=1, evidence_strength="single_source",
)


class TestListEntitiesSearch:
    """Tests for GET /investigations/{id}/entities/?search=..."""

    def test_search_returns_matching_entities(self, entity_client):
        """search=john returns only entities whose names contain 'john' (case-insensitive)."""
        resp = _list_response([_JOHN, _JANE])
        with patch("app.api.v1.entities.EntityQueryService") as mock_cls:
            mock_svc = AsyncMock()
            mock_svc.list_entities = AsyncMock(return_value=resp)
            mock_cls.return_value = mock_svc

            response = entity_client.get(
                f"/api/v1/investigations/{INVESTIGATION_ID}/entities/?search=john"
            )

        assert response.status_code == 200
        mock_svc.list_entities.assert_called_once()
        call_kwargs = mock_svc.list_entities.call_args
        assert call_kwargs.kwargs.get("search") == "john"
        data = response.json()
        assert len(data["items"]) == 2

    def test_search_combined_with_type_filter(self, entity_client):
        """search=john&type=person — combined search + type filter (AND logic)."""
        resp = _list_response([_JOHN])
        with patch("app.api.v1.entities.EntityQueryService") as mock_cls:
            mock_svc = AsyncMock()
            mock_svc.list_entities = AsyncMock(return_value=resp)
            mock_cls.return_value = mock_svc

            response = entity_client.get(
                f"/api/v1/investigations/{INVESTIGATION_ID}/entities/?search=john&type=person"
            )

        assert response.status_code == 200
        call_kwargs = mock_svc.list_entities.call_args
        assert call_kwargs.kwargs.get("entity_type") == "person"
        assert call_kwargs.kwargs.get("search") == "john"

    def test_search_no_results(self, entity_client):
        """search=nonexistent returns empty results with total: 0."""
        resp = _list_response([], total=0)
        with patch("app.api.v1.entities.EntityQueryService") as mock_cls:
            mock_svc = AsyncMock()
            mock_svc.list_entities = AsyncMock(return_value=resp)
            mock_cls.return_value = mock_svc

            response = entity_client.get(
                f"/api/v1/investigations/{INVESTIGATION_ID}/entities/?search=nonexistent"
            )

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_empty_search_returns_all_entities(self, entity_client):
        """search= (empty string) — same as no search, returns all entities."""
        resp = _list_response([_JOHN, _JANE, _ACME, _BERLIN])
        with patch("app.api.v1.entities.EntityQueryService") as mock_cls:
            mock_svc = AsyncMock()
            mock_svc.list_entities = AsyncMock(return_value=resp)
            mock_cls.return_value = mock_svc

            response = entity_client.get(
                f"/api/v1/investigations/{INVESTIGATION_ID}/entities/?search="
            )

        assert response.status_code == 200
        # Empty search string should be passed as empty string (service treats it as no filter)
        mock_svc.list_entities.assert_called_once()

    def test_search_case_insensitive(self, entity_client):
        """search=ORG — case-insensitive match returns entities with 'org' in the name."""
        resp = _list_response([_ACME])
        with patch("app.api.v1.entities.EntityQueryService") as mock_cls:
            mock_svc = AsyncMock()
            mock_svc.list_entities = AsyncMock(return_value=resp)
            mock_cls.return_value = mock_svc

            response = entity_client.get(
                f"/api/v1/investigations/{INVESTIGATION_ID}/entities/?search=ORG"
            )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["name"] == "Acme Organization"

    def test_search_type_summary_reflects_filtered_results(self, entity_client):
        """type_summary in response reflects search-filtered results, not all entities."""
        resp = _list_response([_JOHN])
        with patch("app.api.v1.entities.EntityQueryService") as mock_cls:
            mock_svc = AsyncMock()
            mock_svc.list_entities = AsyncMock(return_value=resp)
            mock_cls.return_value = mock_svc

            response = entity_client.get(
                f"/api/v1/investigations/{INVESTIGATION_ID}/entities/?search=john"
            )

        assert response.status_code == 200
        data = response.json()
        summary = data["summary"]
        assert summary["people"] == 1
        assert summary["organizations"] == 0
        assert summary["locations"] == 0
        assert summary["total"] == 1
