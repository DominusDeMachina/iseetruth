"""Integration tests for GET /api/v1/investigations/{id}/entities/."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.schemas.entity import (
    EntityListItem,
    EntityListResponse,
    EntityTypeSummary,
)


INVESTIGATION_ID = "11111111-1111-1111-1111-111111111111"


def _sample_list_response() -> EntityListResponse:
    return EntityListResponse(
        items=[
            EntityListItem(
                id="aaa",
                name="John Smith",
                type="person",
                confidence_score=0.9,
                source_count=2,
                evidence_strength="corroborated",
            ),
            EntityListItem(
                id="bbb",
                name="Acme Corp",
                type="organization",
                confidence_score=0.85,
                source_count=1,
                evidence_strength="single_source",
            ),
        ],
        total=3,
        summary=EntityTypeSummary(people=1, organizations=1, locations=1, total=3),
    )


@pytest.fixture
def entity_client(mock_db_session):
    from app.db.postgres import get_db
    from app.main import app

    async def override_get_db():
        yield mock_db_session

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


class TestListEntities:
    def test_returns_200_with_entity_list(self, entity_client):
        with patch("app.api.v1.entities.EntityQueryService") as mock_svc_cls:
            mock_svc = AsyncMock()
            mock_svc.list_entities = AsyncMock(return_value=_sample_list_response())
            mock_svc_cls.return_value = mock_svc

            response = entity_client.get(
                f"/api/v1/investigations/{INVESTIGATION_ID}/entities/"
            )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["items"]) == 2
        assert data["items"][0]["name"] == "John Smith"
        assert data["items"][0]["confidence_score"] == 0.9
        assert data["items"][0]["evidence_strength"] == "corroborated"
        assert data["summary"]["people"] == 1
        assert data["summary"]["organizations"] == 1
        assert data["summary"]["locations"] == 1
        assert data["summary"]["total"] == 3

    def test_passes_type_filter(self, entity_client):
        with patch("app.api.v1.entities.EntityQueryService") as mock_svc_cls:
            mock_svc = AsyncMock()
            mock_svc.list_entities = AsyncMock(
                return_value=EntityListResponse(
                    items=[],
                    total=0,
                    summary=EntityTypeSummary(people=0, organizations=0, locations=0, total=0),
                )
            )
            mock_svc_cls.return_value = mock_svc

            response = entity_client.get(
                f"/api/v1/investigations/{INVESTIGATION_ID}/entities/?type=person"
            )

        assert response.status_code == 200
        mock_svc.list_entities.assert_called_once()
        call_kwargs = mock_svc.list_entities.call_args
        assert call_kwargs[1]["entity_type"] == "person"

    def test_passes_pagination_params(self, entity_client):
        with patch("app.api.v1.entities.EntityQueryService") as mock_svc_cls:
            mock_svc = AsyncMock()
            mock_svc.list_entities = AsyncMock(
                return_value=EntityListResponse(
                    items=[],
                    total=0,
                    summary=EntityTypeSummary(people=0, organizations=0, locations=0, total=0),
                )
            )
            mock_svc_cls.return_value = mock_svc

            response = entity_client.get(
                f"/api/v1/investigations/{INVESTIGATION_ID}/entities/?limit=10&offset=20"
            )

        assert response.status_code == 200
        call_kwargs = mock_svc.list_entities.call_args
        assert call_kwargs[1]["limit"] == 10
        assert call_kwargs[1]["offset"] == 20

    def test_returns_422_for_non_uuid_investigation(self, entity_client):
        response = entity_client.get(
            "/api/v1/investigations/not-a-uuid/entities/"
        )
        assert response.status_code == 422

    def test_returns_422_for_limit_out_of_range(self, entity_client):
        response = entity_client.get(
            f"/api/v1/investigations/{INVESTIGATION_ID}/entities/?limit=0"
        )
        assert response.status_code == 422

    def test_returns_422_for_limit_too_large(self, entity_client):
        response = entity_client.get(
            f"/api/v1/investigations/{INVESTIGATION_ID}/entities/?limit=201"
        )
        assert response.status_code == 422

    def test_returns_422_for_invalid_entity_type(self, entity_client):
        response = entity_client.get(
            f"/api/v1/investigations/{INVESTIGATION_ID}/entities/?type=invalid_type"
        )
        assert response.status_code == 422
        assert "Invalid entity type" in response.json()["detail"]

    def test_returns_422_for_cypher_injection_attempt(self, entity_client):
        response = entity_client.get(
            f"/api/v1/investigations/{INVESTIGATION_ID}/entities/?type=person)%20return%20e%20//"
        )
        assert response.status_code == 422

    def test_accepts_valid_entity_types(self, entity_client):
        for valid_type in ("person", "organization", "location"):
            with patch("app.api.v1.entities.EntityQueryService") as mock_svc_cls:
                mock_svc = AsyncMock()
                mock_svc.list_entities = AsyncMock(
                    return_value=EntityListResponse(
                        items=[],
                        total=0,
                        summary=EntityTypeSummary(
                            people=0, organizations=0, locations=0, total=0
                        ),
                    )
                )
                mock_svc_cls.return_value = mock_svc

                response = entity_client.get(
                    f"/api/v1/investigations/{INVESTIGATION_ID}/entities/?type={valid_type}"
                )
            assert response.status_code == 200, f"Failed for type={valid_type}"
