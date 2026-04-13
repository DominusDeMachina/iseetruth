"""Integration tests for entities API endpoints."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.exceptions import (
    EntityDuplicateError,
    EntityMergeError,
    EntitySelfMergeError,
    EntityTypeMismatchError,
)
from app.schemas.entity import (
    EntityDetailResponse,
    EntityListItem,
    EntityListResponse,
    EntityMergePreview,
    EntityMergeResponse,
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


def _manual_entity_response(**overrides) -> EntityDetailResponse:
    """Helper for a manual entity response."""
    defaults = dict(
        id=str(uuid.uuid4()),
        name="Viktor Novak",
        type="person",
        confidence_score=1.0,
        investigation_id=INVESTIGATION_ID,
        relationships=[],
        sources=[],
        evidence_strength="none",
        source="manual",
        source_annotation="Found in public records",
        aliases=[],
    )
    defaults.update(overrides)
    return EntityDetailResponse(**defaults)


class TestCreateEntity:
    """Tests for POST /investigations/{id}/entities/."""

    def test_create_entity_returns_201(self, entity_client):
        expected = _manual_entity_response()
        with patch("app.api.v1.entities.EntityQueryService") as mock_cls:
            mock_svc = AsyncMock()
            mock_svc.create_entity = AsyncMock(return_value=expected)
            mock_cls.return_value = mock_svc

            response = entity_client.post(
                f"/api/v1/investigations/{INVESTIGATION_ID}/entities/",
                json={"name": "Viktor Novak", "type": "person", "source_annotation": "Found in public records"},
            )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Viktor Novak"
        assert data["type"] == "person"
        assert data["confidence_score"] == 1.0
        assert data["source"] == "manual"
        assert data["source_annotation"] == "Found in public records"
        assert data["aliases"] == []

    def test_create_entity_missing_name_returns_422(self, entity_client):
        response = entity_client.post(
            f"/api/v1/investigations/{INVESTIGATION_ID}/entities/",
            json={"type": "person"},
        )
        assert response.status_code == 422

    def test_create_entity_invalid_type_returns_422(self, entity_client):
        response = entity_client.post(
            f"/api/v1/investigations/{INVESTIGATION_ID}/entities/",
            json={"name": "Test", "type": "vehicle"},
        )
        assert response.status_code == 422

    def test_create_entity_duplicate_returns_409(self, entity_client):
        with patch("app.api.v1.entities.EntityQueryService") as mock_cls:
            mock_svc = AsyncMock()
            mock_svc.create_entity = AsyncMock(
                side_effect=EntityDuplicateError("Viktor Novak", "person")
            )
            mock_cls.return_value = mock_svc

            response = entity_client.post(
                f"/api/v1/investigations/{INVESTIGATION_ID}/entities/",
                json={"name": "Viktor Novak", "type": "person"},
            )

        assert response.status_code == 409
        data = response.json()
        assert "entity_duplicate" in data["type"]
        assert "Viktor Novak" in data["detail"]

    def test_create_entity_empty_name_returns_422(self, entity_client):
        response = entity_client.post(
            f"/api/v1/investigations/{INVESTIGATION_ID}/entities/",
            json={"name": "   ", "type": "person"},
        )
        assert response.status_code == 422


class TestUpdateEntity:
    """Tests for PATCH /investigations/{id}/entities/{entity_id}."""

    def test_update_name_returns_200_with_alias(self, entity_client):
        updated = _manual_entity_response(
            name="Viktor J. Novak",
            aliases=["Viktor Novak"],
        )
        with patch("app.api.v1.entities.EntityQueryService") as mock_cls:
            mock_svc = AsyncMock()
            mock_svc.update_entity = AsyncMock(return_value=updated)
            mock_cls.return_value = mock_svc

            response = entity_client.patch(
                f"/api/v1/investigations/{INVESTIGATION_ID}/entities/{ENTITY_ID}",
                json={"name": "Viktor J. Novak"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Viktor J. Novak"
        assert "Viktor Novak" in data["aliases"]

    def test_update_nonexistent_entity_returns_404(self, entity_client):
        with patch("app.api.v1.entities.EntityQueryService") as mock_cls:
            mock_svc = AsyncMock()
            mock_svc.update_entity = AsyncMock(return_value=None)
            mock_cls.return_value = mock_svc

            response = entity_client.patch(
                f"/api/v1/investigations/{INVESTIGATION_ID}/entities/nonexistent-id",
                json={"name": "New Name"},
            )

        assert response.status_code == 404

    def test_update_only_source_annotation(self, entity_client):
        updated = _manual_entity_response(
            source_annotation="Updated source info",
        )
        with patch("app.api.v1.entities.EntityQueryService") as mock_cls:
            mock_svc = AsyncMock()
            mock_svc.update_entity = AsyncMock(return_value=updated)
            mock_cls.return_value = mock_svc

            response = entity_client.patch(
                f"/api/v1/investigations/{INVESTIGATION_ID}/entities/{ENTITY_ID}",
                json={"source_annotation": "Updated source info"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["source_annotation"] == "Updated source info"
        assert data["aliases"] == []  # Name didn't change, no alias added


class TestEntityResponseFields:
    """Tests for new source/aliases/source_annotation fields in responses."""

    def test_list_entities_includes_source_field(self, entity_client):
        manual_item = EntityListItem(
            id="e5", name="Manual Entity", type="person",
            confidence_score=1.0, source_count=0,
            evidence_strength="none", source="manual",
        )
        resp = _list_response([_JOHN, manual_item])
        with patch("app.api.v1.entities.EntityQueryService") as mock_cls:
            mock_svc = AsyncMock()
            mock_svc.list_entities = AsyncMock(return_value=resp)
            mock_cls.return_value = mock_svc

            response = entity_client.get(
                f"/api/v1/investigations/{INVESTIGATION_ID}/entities/"
            )

        assert response.status_code == 200
        data = response.json()
        sources = [item["source"] for item in data["items"]]
        assert "extracted" in sources
        assert "manual" in sources

    def test_entity_detail_includes_source_aliases_annotation(self, entity_client):
        detail = _manual_entity_response(
            aliases=["Old Name"],
            source_annotation="Found in records",
        )
        with patch("app.api.v1.entities.EntityQueryService") as mock_cls:
            mock_svc = AsyncMock()
            mock_svc.get_entity_detail = AsyncMock(return_value=detail)
            mock_cls.return_value = mock_svc

            response = entity_client.get(
                f"/api/v1/investigations/{INVESTIGATION_ID}/entities/{ENTITY_ID}"
            )

        assert response.status_code == 200
        data = response.json()
        assert data["source"] == "manual"
        assert data["source_annotation"] == "Found in records"
        assert data["aliases"] == ["Old Name"]


# ---------------------------------------------------------------------------
# Merge entity helpers and constants
# ---------------------------------------------------------------------------

SOURCE_ENTITY_ID = "ssssssss-ssss-ssss-ssss-ssssssssssss"
TARGET_ENTITY_ID = "tttttttt-tttt-tttt-tttt-tttttttttttt"


def _source_entity() -> EntityDetailResponse:
    return EntityDetailResponse(
        id=SOURCE_ENTITY_ID,
        name="Dep. Mayor Horvat",
        type="person",
        confidence_score=0.8,
        investigation_id=INVESTIGATION_ID,
        relationships=[
            EntityRelationship(
                relation_type="WORKS_FOR",
                target_id="org1",
                target_name="City Hall",
                target_type="organization",
                confidence_score=0.7,
            )
        ],
        sources=[
            EntitySource(
                document_id="doc1",
                document_filename="contract.pdf",
                chunk_id="chunk1",
                page_start=1,
                page_end=2,
                text_excerpt="Dep. Mayor Horvat signed the contract.",
            )
        ],
        evidence_strength="single_source",
    )


def _target_entity() -> EntityDetailResponse:
    return EntityDetailResponse(
        id=TARGET_ENTITY_ID,
        name="Deputy Mayor Horvat",
        type="person",
        confidence_score=0.9,
        investigation_id=INVESTIGATION_ID,
        relationships=[
            EntityRelationship(
                relation_type="KNOWS",
                target_id="p1",
                target_name="Marko Petrovic",
                target_type="person",
                confidence_score=0.85,
            )
        ],
        sources=[
            EntitySource(
                document_id="doc2",
                document_filename="report.pdf",
                chunk_id="chunk2",
                page_start=3,
                page_end=4,
                text_excerpt="Deputy Mayor Horvat met with Petrovic.",
            )
        ],
        evidence_strength="single_source",
    )


def _merge_preview() -> EntityMergePreview:
    return EntityMergePreview(
        source_entity=_source_entity(),
        target_entity=_target_entity(),
        duplicate_relationships=[],
        total_relationships_after=2,
        total_sources_after=2,
    )


def _merge_response(**overrides) -> EntityMergeResponse:
    merged = _target_entity().model_copy(
        update={"aliases": ["Dep. Mayor Horvat"], "confidence_score": 0.9}
    )
    defaults = dict(
        merged_entity=merged,
        relationships_transferred=1,
        citations_transferred=1,
        aliases_added=["Dep. Mayor Horvat"],
        duplicate_relationships_consolidated=0,
    )
    defaults.update(overrides)
    return EntityMergeResponse(**defaults)


class TestMergePreview:
    """Tests for POST /investigations/{id}/entities/merge/preview."""

    def test_preview_returns_200(self, entity_client):
        preview = _merge_preview()
        with patch("app.api.v1.entities.EntityQueryService") as mock_cls:
            mock_svc = AsyncMock()
            mock_svc.get_entity_detail = AsyncMock(
                side_effect=[_source_entity(), _target_entity()]
            )
            mock_svc.preview_merge = AsyncMock(return_value=preview)
            mock_cls.return_value = mock_svc

            response = entity_client.post(
                f"/api/v1/investigations/{INVESTIGATION_ID}/entities/merge/preview",
                json={
                    "source_entity_id": SOURCE_ENTITY_ID,
                    "target_entity_id": TARGET_ENTITY_ID,
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["source_entity"]["id"] == SOURCE_ENTITY_ID
        assert data["target_entity"]["id"] == TARGET_ENTITY_ID
        assert data["total_relationships_after"] == 2
        assert data["total_sources_after"] == 2

    def test_preview_source_not_found_returns_404(self, entity_client):
        with patch("app.api.v1.entities.EntityQueryService") as mock_cls:
            mock_svc = AsyncMock()
            mock_svc.get_entity_detail = AsyncMock(return_value=None)
            mock_cls.return_value = mock_svc

            response = entity_client.post(
                f"/api/v1/investigations/{INVESTIGATION_ID}/entities/merge/preview",
                json={
                    "source_entity_id": "nonexistent",
                    "target_entity_id": TARGET_ENTITY_ID,
                },
            )

        assert response.status_code == 404

    def test_preview_self_merge_returns_422(self, entity_client):
        response = entity_client.post(
            f"/api/v1/investigations/{INVESTIGATION_ID}/entities/merge/preview",
            json={
                "source_entity_id": SOURCE_ENTITY_ID,
                "target_entity_id": SOURCE_ENTITY_ID,
            },
        )

        assert response.status_code == 422
        data = response.json()
        assert "entity_self_merge" in data["type"]

    def test_preview_type_mismatch_returns_422(self, entity_client):
        source = _source_entity()
        target = _target_entity().model_copy(update={"type": "organization"})
        with patch("app.api.v1.entities.EntityQueryService") as mock_cls:
            mock_svc = AsyncMock()
            mock_svc.get_entity_detail = AsyncMock(
                side_effect=[source, target]
            )
            mock_cls.return_value = mock_svc

            response = entity_client.post(
                f"/api/v1/investigations/{INVESTIGATION_ID}/entities/merge/preview",
                json={
                    "source_entity_id": SOURCE_ENTITY_ID,
                    "target_entity_id": TARGET_ENTITY_ID,
                },
            )

        assert response.status_code == 422
        data = response.json()
        assert "entity_type_mismatch" in data["type"]


class TestMergeEntities:
    """Tests for POST /investigations/{id}/entities/merge."""

    def test_merge_returns_200(self, entity_client):
        resp = _merge_response()
        with patch("app.api.v1.entities.EntityQueryService") as mock_cls, \
             patch("app.api.v1.entities.EventPublisher"):
            mock_svc = AsyncMock()
            mock_svc.get_entity_detail = AsyncMock(
                side_effect=[_source_entity(), _target_entity()]
            )
            mock_svc.merge_entities = AsyncMock(return_value=resp)
            mock_cls.return_value = mock_svc

            response = entity_client.post(
                f"/api/v1/investigations/{INVESTIGATION_ID}/entities/merge",
                json={
                    "source_entity_id": SOURCE_ENTITY_ID,
                    "target_entity_id": TARGET_ENTITY_ID,
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["relationships_transferred"] == 1
        assert data["citations_transferred"] == 1
        assert "Dep. Mayor Horvat" in data["aliases_added"]

    def test_merge_with_primary_name(self, entity_client):
        resp = _merge_response(
            merged_entity=_target_entity().model_copy(
                update={
                    "name": "Dep. Mayor Horvat",
                    "aliases": ["Deputy Mayor Horvat"],
                }
            ),
            aliases_added=["Deputy Mayor Horvat"],
        )
        with patch("app.api.v1.entities.EntityQueryService") as mock_cls, \
             patch("app.api.v1.entities.EventPublisher"):
            mock_svc = AsyncMock()
            mock_svc.get_entity_detail = AsyncMock(
                side_effect=[_source_entity(), _target_entity()]
            )
            mock_svc.merge_entities = AsyncMock(return_value=resp)
            mock_cls.return_value = mock_svc

            response = entity_client.post(
                f"/api/v1/investigations/{INVESTIGATION_ID}/entities/merge",
                json={
                    "source_entity_id": SOURCE_ENTITY_ID,
                    "target_entity_id": TARGET_ENTITY_ID,
                    "primary_name": "Dep. Mayor Horvat",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["merged_entity"]["name"] == "Dep. Mayor Horvat"

    def test_merge_consolidates_duplicates(self, entity_client):
        resp = _merge_response(duplicate_relationships_consolidated=1)
        with patch("app.api.v1.entities.EntityQueryService") as mock_cls, \
             patch("app.api.v1.entities.EventPublisher"):
            mock_svc = AsyncMock()
            mock_svc.get_entity_detail = AsyncMock(
                side_effect=[_source_entity(), _target_entity()]
            )
            mock_svc.merge_entities = AsyncMock(return_value=resp)
            mock_cls.return_value = mock_svc

            response = entity_client.post(
                f"/api/v1/investigations/{INVESTIGATION_ID}/entities/merge",
                json={
                    "source_entity_id": SOURCE_ENTITY_ID,
                    "target_entity_id": TARGET_ENTITY_ID,
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["duplicate_relationships_consolidated"] == 1

    def test_merge_self_returns_422(self, entity_client):
        response = entity_client.post(
            f"/api/v1/investigations/{INVESTIGATION_ID}/entities/merge",
            json={
                "source_entity_id": SOURCE_ENTITY_ID,
                "target_entity_id": SOURCE_ENTITY_ID,
            },
        )

        assert response.status_code == 422
        data = response.json()
        assert "entity_self_merge" in data["type"]

    def test_merge_source_not_found_returns_404(self, entity_client):
        with patch("app.api.v1.entities.EntityQueryService") as mock_cls:
            mock_svc = AsyncMock()
            mock_svc.get_entity_detail = AsyncMock(return_value=None)
            mock_cls.return_value = mock_svc

            response = entity_client.post(
                f"/api/v1/investigations/{INVESTIGATION_ID}/entities/merge",
                json={
                    "source_entity_id": "nonexistent",
                    "target_entity_id": TARGET_ENTITY_ID,
                },
            )

        assert response.status_code == 404

    def test_merge_type_mismatch_returns_422(self, entity_client):
        source = _source_entity()
        target = _target_entity().model_copy(update={"type": "organization"})
        with patch("app.api.v1.entities.EntityQueryService") as mock_cls:
            mock_svc = AsyncMock()
            mock_svc.get_entity_detail = AsyncMock(
                side_effect=[source, target]
            )
            mock_cls.return_value = mock_svc

            response = entity_client.post(
                f"/api/v1/investigations/{INVESTIGATION_ID}/entities/merge",
                json={
                    "source_entity_id": SOURCE_ENTITY_ID,
                    "target_entity_id": TARGET_ENTITY_ID,
                },
            )

        assert response.status_code == 422
        data = response.json()
        assert "entity_type_mismatch" in data["type"]

    def test_merge_transaction_failure_returns_422(self, entity_client):
        with patch("app.api.v1.entities.EntityQueryService") as mock_cls, \
             patch("app.api.v1.entities.EventPublisher"):
            mock_svc = AsyncMock()
            mock_svc.get_entity_detail = AsyncMock(
                side_effect=[_source_entity(), _target_entity()]
            )
            mock_svc.merge_entities = AsyncMock(
                side_effect=EntityMergeError("Neo4j transaction failed")
            )
            mock_cls.return_value = mock_svc

            response = entity_client.post(
                f"/api/v1/investigations/{INVESTIGATION_ID}/entities/merge",
                json={
                    "source_entity_id": SOURCE_ENTITY_ID,
                    "target_entity_id": TARGET_ENTITY_ID,
                },
            )

        assert response.status_code == 422
        data = response.json()
        assert "entity_merge_failed" in data["type"]
