"""Integration tests for cross-investigation API endpoints."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.schemas.cross_investigation import (
    CrossInvestigationMatch,
    CrossInvestigationResponse,
    InvestigationEntityInfo,
)


INVESTIGATION_ID = "11111111-1111-1111-1111-111111111111"


def _sample_response() -> CrossInvestigationResponse:
    return CrossInvestigationResponse(
        matches=[
            CrossInvestigationMatch(
                entity_name="John Doe",
                entity_type="person",
                match_confidence=1.0,
                match_type="exact",
                source_entity_id="e1-id",
                source_relationship_count=3,
                source_confidence_score=0.9,
                investigations=[
                    InvestigationEntityInfo(
                        investigation_id="22222222-2222-2222-2222-222222222222",
                        investigation_name="Investigation B",
                        entity_id="e2-id",
                        relationship_count=2,
                        confidence_score=0.85,
                    )
                ],
            )
        ],
        total_matches=1,
        query_duration_ms=42.5,
    )


def _empty_response() -> CrossInvestigationResponse:
    return CrossInvestigationResponse(
        matches=[], total_matches=0, query_duration_ms=5.0
    )


@pytest.fixture
def cross_inv_client(mock_db_session):
    """TestClient with get_db overridden."""
    from app.db.postgres import get_db
    from app.main import app

    async def override_get_db():
        yield mock_db_session

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


class TestGetCrossInvestigationLinks:
    def test_returns_200_with_matches(self, cross_inv_client, mock_db_session):
        # Mock investigation exists check
        inv_result = MagicMock()
        inv_result.scalar_one_or_none.return_value = uuid.UUID(INVESTIGATION_ID)
        mock_db_session.execute = AsyncMock(return_value=inv_result)

        with patch(
            "app.api.v1.cross_investigation.CrossInvestigationService"
        ) as mock_svc_cls:
            mock_svc = AsyncMock()
            mock_svc.find_matches = AsyncMock(return_value=_sample_response())
            mock_svc_cls.return_value = mock_svc

            response = cross_inv_client.get(
                f"/api/v1/investigations/{INVESTIGATION_ID}/cross-links/"
            )

        assert response.status_code == 200
        data = response.json()
        assert data["total_matches"] == 1
        assert data["matches"][0]["entity_name"] == "John Doe"
        assert data["matches"][0]["match_confidence"] == 1.0
        assert len(data["matches"][0]["investigations"]) == 1

    def test_returns_404_for_nonexistent_investigation(self, cross_inv_client, mock_db_session):
        inv_result = MagicMock()
        inv_result.scalar_one_or_none.return_value = None
        mock_db_session.execute = AsyncMock(return_value=inv_result)

        response = cross_inv_client.get(
            f"/api/v1/investigations/{INVESTIGATION_ID}/cross-links/"
        )

        assert response.status_code == 404

    def test_returns_empty_for_single_investigation(self, cross_inv_client, mock_db_session):
        inv_result = MagicMock()
        inv_result.scalar_one_or_none.return_value = uuid.UUID(INVESTIGATION_ID)
        mock_db_session.execute = AsyncMock(return_value=inv_result)

        with patch(
            "app.api.v1.cross_investigation.CrossInvestigationService"
        ) as mock_svc_cls:
            mock_svc = AsyncMock()
            mock_svc.find_matches = AsyncMock(return_value=_empty_response())
            mock_svc_cls.return_value = mock_svc

            response = cross_inv_client.get(
                f"/api/v1/investigations/{INVESTIGATION_ID}/cross-links/"
            )

        assert response.status_code == 200
        data = response.json()
        assert data["total_matches"] == 0
        assert data["matches"] == []

    def test_response_schema_validation(self, cross_inv_client, mock_db_session):
        inv_result = MagicMock()
        inv_result.scalar_one_or_none.return_value = uuid.UUID(INVESTIGATION_ID)
        mock_db_session.execute = AsyncMock(return_value=inv_result)

        with patch(
            "app.api.v1.cross_investigation.CrossInvestigationService"
        ) as mock_svc_cls:
            mock_svc = AsyncMock()
            mock_svc.find_matches = AsyncMock(return_value=_sample_response())
            mock_svc_cls.return_value = mock_svc

            response = cross_inv_client.get(
                f"/api/v1/investigations/{INVESTIGATION_ID}/cross-links/"
            )

        data = response.json()
        assert "matches" in data
        assert "total_matches" in data
        assert "query_duration_ms" in data
        match = data["matches"][0]
        assert "entity_name" in match
        assert "entity_type" in match
        assert "match_confidence" in match
        assert "match_type" in match
        assert "investigations" in match
        inv = match["investigations"][0]
        assert "investigation_id" in inv
        assert "investigation_name" in inv
        assert "entity_id" in inv
        assert "relationship_count" in inv
        assert "confidence_score" in inv
