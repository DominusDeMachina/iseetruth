"""Integration tests for relationships API endpoint."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.exceptions import EntityNotFoundError
from app.schemas.relationship import RelationshipResponse


INVESTIGATION_ID = "11111111-1111-1111-1111-111111111111"
SOURCE_ENTITY_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
TARGET_ENTITY_ID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
RELATIONSHIP_ID = "cccccccc-cccc-cccc-cccc-cccccccccccc"


def _relationship_response(**overrides) -> RelationshipResponse:
    """Helper for a manual relationship response."""
    defaults = dict(
        id=RELATIONSHIP_ID,
        source_entity_id=SOURCE_ENTITY_ID,
        target_entity_id=TARGET_ENTITY_ID,
        source_entity_name="John Smith",
        target_entity_name="Acme Corp",
        type="WORKS_FOR",
        confidence_score=1.0,
        source="manual",
        source_annotation="Found in public records",
        already_existed=False,
    )
    defaults.update(overrides)
    return RelationshipResponse(**defaults)


@pytest.fixture
def rel_client(mock_db_session):
    """TestClient with get_db and neo4j driver overridden."""
    from app.db.postgres import get_db
    from app.main import app

    async def override_get_db():
        yield mock_db_session

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


class TestCreateRelationship:
    """Tests for POST /investigations/{id}/relationships/."""

    def test_create_relationship_returns_201(self, rel_client):
        expected = _relationship_response()
        with patch("app.api.v1.relationships.EntityQueryService") as mock_cls:
            mock_svc = AsyncMock()
            mock_svc.create_relationship = AsyncMock(return_value=expected)
            mock_cls.return_value = mock_svc

            response = rel_client.post(
                f"/api/v1/investigations/{INVESTIGATION_ID}/relationships/",
                json={
                    "source_entity_id": SOURCE_ENTITY_ID,
                    "target_entity_id": TARGET_ENTITY_ID,
                    "type": "WORKS_FOR",
                    "source_annotation": "Found in public records",
                },
            )

        assert response.status_code == 201
        data = response.json()
        assert data["type"] == "WORKS_FOR"
        assert data["source"] == "manual"
        assert data["confidence_score"] == 1.0
        assert data["source_entity_name"] == "John Smith"
        assert data["target_entity_name"] == "Acme Corp"
        assert data["already_existed"] is False

    def test_create_relationship_missing_source_entity_id_returns_422(self, rel_client):
        response = rel_client.post(
            f"/api/v1/investigations/{INVESTIGATION_ID}/relationships/",
            json={
                "target_entity_id": TARGET_ENTITY_ID,
                "type": "WORKS_FOR",
            },
        )
        assert response.status_code == 422

    def test_create_relationship_nonexistent_source_entity_returns_404(self, rel_client):
        with patch("app.api.v1.relationships.EntityQueryService") as mock_cls:
            mock_svc = AsyncMock()
            mock_svc.create_relationship = AsyncMock(
                side_effect=EntityNotFoundError(SOURCE_ENTITY_ID)
            )
            mock_cls.return_value = mock_svc

            response = rel_client.post(
                f"/api/v1/investigations/{INVESTIGATION_ID}/relationships/",
                json={
                    "source_entity_id": SOURCE_ENTITY_ID,
                    "target_entity_id": TARGET_ENTITY_ID,
                    "type": "WORKS_FOR",
                },
            )

        assert response.status_code == 404
        data = response.json()
        assert "entity_not_found" in data["type"]

    def test_create_relationship_nonexistent_target_entity_returns_404(self, rel_client):
        with patch("app.api.v1.relationships.EntityQueryService") as mock_cls:
            mock_svc = AsyncMock()
            mock_svc.create_relationship = AsyncMock(
                side_effect=EntityNotFoundError(TARGET_ENTITY_ID)
            )
            mock_cls.return_value = mock_svc

            response = rel_client.post(
                f"/api/v1/investigations/{INVESTIGATION_ID}/relationships/",
                json={
                    "source_entity_id": SOURCE_ENTITY_ID,
                    "target_entity_id": TARGET_ENTITY_ID,
                    "type": "WORKS_FOR",
                },
            )

        assert response.status_code == 404

    def test_create_duplicate_relationship_returns_200(self, rel_client):
        existing = _relationship_response(already_existed=True)
        with patch("app.api.v1.relationships.EntityQueryService") as mock_cls:
            mock_svc = AsyncMock()
            mock_svc.create_relationship = AsyncMock(return_value=existing)
            mock_cls.return_value = mock_svc

            response = rel_client.post(
                f"/api/v1/investigations/{INVESTIGATION_ID}/relationships/",
                json={
                    "source_entity_id": SOURCE_ENTITY_ID,
                    "target_entity_id": TARGET_ENTITY_ID,
                    "type": "WORKS_FOR",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["already_existed"] is True

    def test_create_relationship_same_source_target_returns_422(self, rel_client):
        response = rel_client.post(
            f"/api/v1/investigations/{INVESTIGATION_ID}/relationships/",
            json={
                "source_entity_id": SOURCE_ENTITY_ID,
                "target_entity_id": SOURCE_ENTITY_ID,
                "type": "KNOWS",
            },
        )
        assert response.status_code == 422

    def test_create_relationship_invalid_type_returns_422(self, rel_client):
        response = rel_client.post(
            f"/api/v1/investigations/{INVESTIGATION_ID}/relationships/",
            json={
                "source_entity_id": SOURCE_ENTITY_ID,
                "target_entity_id": TARGET_ENTITY_ID,
                "type": "123BAD",
            },
        )
        assert response.status_code == 422

    def test_create_relationship_custom_upper_snake_type_returns_201(self, rel_client):
        expected = _relationship_response(type="FUNDS")
        with patch("app.api.v1.relationships.EntityQueryService") as mock_cls:
            mock_svc = AsyncMock()
            mock_svc.create_relationship = AsyncMock(return_value=expected)
            mock_cls.return_value = mock_svc

            response = rel_client.post(
                f"/api/v1/investigations/{INVESTIGATION_ID}/relationships/",
                json={
                    "source_entity_id": SOURCE_ENTITY_ID,
                    "target_entity_id": TARGET_ENTITY_ID,
                    "type": "FUNDS",
                    "source_annotation": "Financial records show transfer",
                },
            )

        assert response.status_code == 201
        data = response.json()
        assert data["type"] == "FUNDS"

    def test_create_relationship_annotation_too_long_returns_422(self, rel_client):
        response = rel_client.post(
            f"/api/v1/investigations/{INVESTIGATION_ID}/relationships/",
            json={
                "source_entity_id": SOURCE_ENTITY_ID,
                "target_entity_id": TARGET_ENTITY_ID,
                "type": "KNOWS",
                "source_annotation": "x" * 2001,
            },
        )
        assert response.status_code == 422

    def test_create_relationship_graph_edges_include_source_field(self, rel_client):
        """Verify the relationship response includes the source field."""
        expected = _relationship_response()
        with patch("app.api.v1.relationships.EntityQueryService") as mock_cls:
            mock_svc = AsyncMock()
            mock_svc.create_relationship = AsyncMock(return_value=expected)
            mock_cls.return_value = mock_svc

            response = rel_client.post(
                f"/api/v1/investigations/{INVESTIGATION_ID}/relationships/",
                json={
                    "source_entity_id": SOURCE_ENTITY_ID,
                    "target_entity_id": TARGET_ENTITY_ID,
                    "type": "WORKS_FOR",
                },
            )

        assert response.status_code == 201
        data = response.json()
        assert "source" in data
        assert data["source"] == "manual"
        assert "source_annotation" in data
