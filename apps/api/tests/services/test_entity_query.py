"""Unit tests for EntityQueryService."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.entity import EntityDetailResponse
from app.services.entity_query import EntityQueryService


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
def doc_id_1():
    return "dddddddd-dddd-dddd-dddd-dddddddddddd"


@pytest.fixture
def doc_id_2():
    return "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"


def _make_neo4j_driver(entity_record, rels_data, sources_data):
    """Build a mock async Neo4j driver returning fixed query data."""
    mock_driver = MagicMock()
    mock_session = AsyncMock()
    mock_driver.session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_driver.session.return_value.__aexit__ = AsyncMock(return_value=False)

    async def fake_execute_read(fn, *args, **kwargs):
        # Detect which query function is being called by function name
        fname = fn.__name__
        if fname == "_fetch_entity":
            return entity_record
        elif fname == "_fetch_relationships":
            return rels_data
        elif fname == "_fetch_sources":
            return sources_data
        return None

    mock_session.execute_read.side_effect = fake_execute_read
    return mock_driver, mock_session


def _make_db_session(doc_rows):
    """Build a mock async SQLAlchemy session returning fixed document rows."""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.__iter__ = MagicMock(return_value=iter(doc_rows))
    mock_db.execute = AsyncMock(return_value=mock_result)
    return mock_db


# ---------------------------------------------------------------------------
# Tests: get_entity_detail
# ---------------------------------------------------------------------------

class TestGetEntityDetail:
    @pytest.mark.asyncio
    async def test_returns_entity_detail_response(self, investigation_id, entity_id, doc_id_1):
        entity_record = {
            "id": entity_id,
            "name": "John Smith",
            "type": "Person",
            "confidence_score": 0.9,
        }
        rels_data = [
            {
                "relation_type": "WORKS_FOR",
                "target_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
                "target_name": "Acme Corp",
                "target_type": "Organization",
                "confidence_score": 0.85,
            }
        ]
        sources_data = [
            {
                "document_id": doc_id_1,
                "chunk_id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
                "page_start": 1,
                "page_end": 2,
                "text_excerpt": "John Smith works at Acme Corp.",
            }
        ]
        doc_row = MagicMock()
        doc_row.id = uuid.UUID(doc_id_1)
        doc_row.filename = "report.pdf"

        neo4j_driver, _ = _make_neo4j_driver(entity_record, rels_data, sources_data)
        db = _make_db_session([doc_row])

        service = EntityQueryService(neo4j_driver, db)
        result = await service.get_entity_detail(investigation_id, entity_id)

        assert isinstance(result, EntityDetailResponse)
        assert result.name == "John Smith"
        assert result.type == "person"
        assert result.confidence_score == 0.9
        assert len(result.relationships) == 1
        assert result.relationships[0].relation_type == "WORKS_FOR"
        assert result.relationships[0].target_name == "Acme Corp"
        assert len(result.sources) == 1
        assert result.sources[0].document_filename == "report.pdf"
        assert result.sources[0].page_start == 1

    @pytest.mark.asyncio
    async def test_returns_none_when_entity_not_found(self, investigation_id, entity_id):
        neo4j_driver, _ = _make_neo4j_driver(None, [], [])
        db = _make_db_session([])

        service = EntityQueryService(neo4j_driver, db)
        result = await service.get_entity_detail(investigation_id, entity_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_evidence_strength_corroborated(self, investigation_id, entity_id, doc_id_1, doc_id_2):
        """Entity mentioned in 2+ documents → evidence_strength = 'corroborated'."""
        entity_record = {
            "id": entity_id,
            "name": "Alice",
            "type": "Person",
            "confidence_score": 0.8,
        }
        sources_data = [
            {
                "document_id": doc_id_1,
                "chunk_id": "cc1",
                "page_start": 1,
                "page_end": 1,
                "text_excerpt": "Alice was here.",
            },
            {
                "document_id": doc_id_2,
                "chunk_id": "cc2",
                "page_start": 3,
                "page_end": 3,
                "text_excerpt": "Alice was there.",
            },
        ]
        doc_row_1 = MagicMock()
        doc_row_1.id = uuid.UUID(doc_id_1)
        doc_row_1.filename = "doc1.pdf"
        doc_row_2 = MagicMock()
        doc_row_2.id = uuid.UUID(doc_id_2)
        doc_row_2.filename = "doc2.pdf"

        neo4j_driver, _ = _make_neo4j_driver(entity_record, [], sources_data)
        db = _make_db_session([doc_row_1, doc_row_2])

        service = EntityQueryService(neo4j_driver, db)
        result = await service.get_entity_detail(investigation_id, entity_id)

        assert result.evidence_strength == "corroborated"

    @pytest.mark.asyncio
    async def test_evidence_strength_single_source(self, investigation_id, entity_id, doc_id_1):
        """Entity mentioned in 1 document → evidence_strength = 'single_source'."""
        entity_record = {
            "id": entity_id,
            "name": "Bob",
            "type": "Person",
            "confidence_score": 0.7,
        }
        sources_data = [
            {
                "document_id": doc_id_1,
                "chunk_id": "cc1",
                "page_start": 1,
                "page_end": 1,
                "text_excerpt": "Bob was mentioned.",
            }
        ]
        doc_row = MagicMock()
        doc_row.id = uuid.UUID(doc_id_1)
        doc_row.filename = "only.pdf"

        neo4j_driver, _ = _make_neo4j_driver(entity_record, [], sources_data)
        db = _make_db_session([doc_row])

        service = EntityQueryService(neo4j_driver, db)
        result = await service.get_entity_detail(investigation_id, entity_id)

        assert result.evidence_strength == "single_source"

    @pytest.mark.asyncio
    async def test_evidence_strength_none_when_no_sources(self, investigation_id, entity_id):
        """Entity with no MENTIONED_IN edges → evidence_strength = 'none'."""
        entity_record = {
            "id": entity_id,
            "name": "Ghost",
            "type": "Person",
            "confidence_score": 0.5,
        }
        neo4j_driver, _ = _make_neo4j_driver(entity_record, [], [])
        db = _make_db_session([])

        service = EntityQueryService(neo4j_driver, db)
        result = await service.get_entity_detail(investigation_id, entity_id)

        assert result.evidence_strength == "none"
        assert result.sources == []

    @pytest.mark.asyncio
    async def test_unknown_filename_when_doc_not_in_postgres(
        self, investigation_id, entity_id, doc_id_1
    ):
        """If document not found in PostgreSQL, filename defaults to 'unknown'."""
        entity_record = {
            "id": entity_id,
            "name": "Test",
            "type": "Person",
            "confidence_score": 0.6,
        }
        sources_data = [
            {
                "document_id": doc_id_1,
                "chunk_id": "cc1",
                "page_start": 1,
                "page_end": 1,
                "text_excerpt": "Test.",
            }
        ]
        neo4j_driver, _ = _make_neo4j_driver(entity_record, [], sources_data)
        db = _make_db_session([])  # empty — doc not found

        service = EntityQueryService(neo4j_driver, db)
        result = await service.get_entity_detail(investigation_id, entity_id)

        assert result.sources[0].document_filename == "unknown"

    @pytest.mark.asyncio
    async def test_no_relationships_returns_empty_list(self, investigation_id, entity_id):
        """Entity with no outgoing relationships returns empty relationships list."""
        entity_record = {
            "id": entity_id,
            "name": "Loner",
            "type": "Person",
            "confidence_score": 0.9,
        }
        neo4j_driver, _ = _make_neo4j_driver(entity_record, [], [])
        db = _make_db_session([])

        service = EntityQueryService(neo4j_driver, db)
        result = await service.get_entity_detail(investigation_id, entity_id)

        assert result.relationships == []
