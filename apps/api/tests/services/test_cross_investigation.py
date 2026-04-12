"""Unit tests for CrossInvestigationService."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.schemas.cross_investigation import CrossInvestigationResponse
from app.services.cross_investigation import CrossInvestigationService


INVESTIGATION_A = "aaaa1111-1111-1111-1111-111111111111"
INVESTIGATION_B = "bbbb2222-2222-2222-2222-222222222222"
INVESTIGATION_C = "cccc3333-3333-3333-3333-333333333333"


def _make_neo4j_driver(match_records):
    """Build a mock async Neo4j driver returning fixed cross-investigation data."""
    mock_driver = MagicMock()
    mock_session = AsyncMock()
    mock_driver.session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_driver.session.return_value.__aexit__ = AsyncMock(return_value=False)

    async def fake_execute_read(fn, *args, **kwargs):
        return match_records

    mock_session.execute_read.side_effect = fake_execute_read
    return mock_driver


def _make_db_session(inv_rows):
    """Build a mock async SQLAlchemy session returning investigation names."""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.__iter__ = MagicMock(return_value=iter(inv_rows))
    mock_db.execute = AsyncMock(return_value=mock_result)
    return mock_db


class TestFindMatches:
    @pytest.mark.asyncio
    async def test_two_investigations_same_entity_returns_match(self):
        records = [
            {
                "entity_name": "John Doe",
                "entity_type": "Person",
                "source_entity_id": "e1-id",
                "source_confidence": 0.9,
                "source_rel_count": 3,
                "match_entity_id": "e2-id",
                "match_investigation_id": INVESTIGATION_B,
                "match_confidence": 0.85,
                "match_rel_count": 2,
                "is_exact_match": True,
            },
        ]
        inv_row = MagicMock()
        inv_row.id = uuid.UUID(INVESTIGATION_B)
        inv_row.name = "Investigation B"

        driver = _make_neo4j_driver(records)
        db = _make_db_session([inv_row])

        service = CrossInvestigationService(driver, db)
        result = await service.find_matches(uuid.UUID(INVESTIGATION_A))

        assert isinstance(result, CrossInvestigationResponse)
        assert result.total_matches == 1
        assert result.matches[0].entity_name == "John Doe"
        assert result.matches[0].entity_type == "person"
        assert result.matches[0].match_confidence == 1.0
        assert result.matches[0].match_type == "exact"
        assert len(result.matches[0].investigations) == 1
        assert result.matches[0].investigations[0].investigation_name == "Investigation B"
        assert result.matches[0].investigations[0].relationship_count == 2

    @pytest.mark.asyncio
    async def test_same_name_different_type_returns_no_match(self):
        """Neo4j query filters by label (type), so different types won't match."""
        driver = _make_neo4j_driver([])
        db = _make_db_session([])

        service = CrossInvestigationService(driver, db)
        result = await service.find_matches(uuid.UUID(INVESTIGATION_A))

        assert result.total_matches == 0
        assert result.matches == []

    @pytest.mark.asyncio
    async def test_case_insensitive_matching(self):
        records = [
            {
                "entity_name": "JOHN DOE",
                "entity_type": "Person",
                "source_entity_id": "e1-id",
                "source_confidence": 0.9,
                "source_rel_count": 1,
                "match_entity_id": "e2-id",
                "match_investigation_id": INVESTIGATION_B,
                "match_confidence": 0.85,
                "match_rel_count": 0,
                "is_exact_match": False,
            },
        ]
        inv_row = MagicMock()
        inv_row.id = uuid.UUID(INVESTIGATION_B)
        inv_row.name = "Investigation B"

        driver = _make_neo4j_driver(records)
        db = _make_db_session([inv_row])

        service = CrossInvestigationService(driver, db)
        result = await service.find_matches(uuid.UUID(INVESTIGATION_A))

        assert result.total_matches == 1
        assert result.matches[0].match_confidence == 0.9
        assert result.matches[0].match_type == "case_insensitive"

    @pytest.mark.asyncio
    async def test_single_investigation_returns_empty(self):
        """When no other investigations exist, Neo4j returns empty."""
        driver = _make_neo4j_driver([])
        db = _make_db_session([])

        service = CrossInvestigationService(driver, db)
        result = await service.find_matches(uuid.UUID(INVESTIGATION_A))

        assert result.total_matches == 0
        assert result.matches == []
        assert result.query_duration_ms >= 0

    @pytest.mark.asyncio
    async def test_multiple_investigations_grouped(self):
        """Entity appearing in 2 other investigations should be grouped."""
        records = [
            {
                "entity_name": "Acme Corp",
                "entity_type": "Organization",
                "source_entity_id": "e1-id",
                "source_confidence": 0.95,
                "source_rel_count": 5,
                "match_entity_id": "e2-id",
                "match_investigation_id": INVESTIGATION_B,
                "match_confidence": 0.9,
                "match_rel_count": 3,
                "is_exact_match": True,
            },
            {
                "entity_name": "Acme Corp",
                "entity_type": "Organization",
                "source_entity_id": "e1-id",
                "source_confidence": 0.95,
                "source_rel_count": 5,
                "match_entity_id": "e3-id",
                "match_investigation_id": INVESTIGATION_C,
                "match_confidence": 0.88,
                "match_rel_count": 1,
                "is_exact_match": True,
            },
        ]
        inv_row_b = MagicMock()
        inv_row_b.id = uuid.UUID(INVESTIGATION_B)
        inv_row_b.name = "Investigation B"
        inv_row_c = MagicMock()
        inv_row_c.id = uuid.UUID(INVESTIGATION_C)
        inv_row_c.name = "Investigation C"

        driver = _make_neo4j_driver(records)
        db = _make_db_session([inv_row_b, inv_row_c])

        service = CrossInvestigationService(driver, db)
        result = await service.find_matches(uuid.UUID(INVESTIGATION_A))

        assert result.total_matches == 1
        match = result.matches[0]
        assert match.entity_name == "Acme Corp"
        assert len(match.investigations) == 2
        inv_names = {i.investigation_name for i in match.investigations}
        assert inv_names == {"Investigation B", "Investigation C"}

    @pytest.mark.asyncio
    async def test_query_duration_tracked(self):
        driver = _make_neo4j_driver([])
        db = _make_db_session([])

        service = CrossInvestigationService(driver, db)
        result = await service.find_matches(uuid.UUID(INVESTIGATION_A))

        assert result.query_duration_ms >= 0
