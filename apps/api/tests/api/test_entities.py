"""Integration tests for GET /api/v1/investigations/{id}/entities/{entity_id}."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.schemas.entity import EntityDetailResponse, EntityRelationship, EntitySource


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
