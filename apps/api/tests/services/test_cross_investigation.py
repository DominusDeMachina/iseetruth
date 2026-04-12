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
    """Build a mock async SQLAlchemy session returning investigation names.

    The service now makes multiple db.execute calls:
    1. _load_dismissed_matches (returns dismissed match rows)
    2. _resolve_investigation_names (returns investigation rows)

    We mock execute to return an empty dismissed set first, then inv names.
    """
    mock_db = AsyncMock()
    call_count = 0

    async def _side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # First call: _load_dismissed_matches — return empty result
            empty_result = MagicMock()
            empty_result.__iter__ = MagicMock(return_value=iter([]))
            return empty_result
        else:
            # Subsequent calls: _resolve_investigation_names
            inv_result = MagicMock()
            inv_result.__iter__ = MagicMock(return_value=iter(inv_rows))
            return inv_result

    mock_db.execute = AsyncMock(side_effect=_side_effect)
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

    @pytest.mark.asyncio
    async def test_dismissed_matches_excluded(self):
        """Dismissed matches should be filtered out of find_matches results."""
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

        # Mock DB to return a dismissed match on first call
        mock_db = AsyncMock()
        call_count = 0

        async def _side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # _load_dismissed_matches: return dismissed entry
                dismissed_row = MagicMock()
                dismissed_row.entity_name = "John Doe"
                dismissed_row.entity_type = "person"
                dismissed_row.target_investigation_id = uuid.UUID(INVESTIGATION_B)
                result = MagicMock()
                result.__iter__ = MagicMock(return_value=iter([dismissed_row]))
                return result
            else:
                inv_result = MagicMock()
                inv_result.__iter__ = MagicMock(return_value=iter([inv_row]))
                return inv_result

        mock_db.execute = AsyncMock(side_effect=_side_effect)

        service = CrossInvestigationService(driver, mock_db)
        result = await service.find_matches(uuid.UUID(INVESTIGATION_A))

        # John Doe should be excluded because it was dismissed
        assert result.total_matches == 0


class TestSearchAcrossInvestigations:
    @pytest.mark.asyncio
    async def test_search_returns_grouped_results(self):
        search_records = [
            {
                "entity_name": "Acme Corp",
                "entity_type": "Organization",
                "investigation_id": INVESTIGATION_A,
                "entity_id": "e1",
                "confidence_score": 0.9,
                "rel_count": 3,
            },
            {
                "entity_name": "Acme Corp",
                "entity_type": "Organization",
                "investigation_id": INVESTIGATION_B,
                "entity_id": "e2",
                "confidence_score": 0.85,
                "rel_count": 1,
            },
        ]
        inv_row_a = MagicMock()
        inv_row_a.id = uuid.UUID(INVESTIGATION_A)
        inv_row_a.name = "Investigation A"
        inv_row_b = MagicMock()
        inv_row_b.id = uuid.UUID(INVESTIGATION_B)
        inv_row_b.name = "Investigation B"

        driver = _make_neo4j_driver(search_records)
        db = _make_db_session([inv_row_a, inv_row_b])

        service = CrossInvestigationService(driver, db)
        result = await service.search_across_investigations("acme")

        assert result.total_results == 1
        assert result.results[0].entity_name == "Acme Corp"
        assert result.results[0].investigation_count == 2

    @pytest.mark.asyncio
    async def test_search_returns_empty_for_no_matches(self):
        driver = _make_neo4j_driver([])
        db = _make_db_session([])

        service = CrossInvestigationService(driver, db)
        result = await service.search_across_investigations("nonexistent")

        assert result.total_results == 0
        assert result.results == []

    @pytest.mark.asyncio
    async def test_search_with_type_filter(self):
        search_records = [
            {
                "entity_name": "London",
                "entity_type": "Location",
                "investigation_id": INVESTIGATION_A,
                "entity_id": "e1",
                "confidence_score": 0.9,
                "rel_count": 2,
            },
        ]
        inv_row = MagicMock()
        inv_row.id = uuid.UUID(INVESTIGATION_A)
        inv_row.name = "Investigation A"

        driver = _make_neo4j_driver(search_records)
        db = _make_db_session([inv_row])

        service = CrossInvestigationService(driver, db)
        result = await service.search_across_investigations(
            "london", entity_type="location"
        )

        assert result.total_results == 1
        assert result.results[0].entity_type == "location"


class TestGetEntityDetailAcross:
    @pytest.mark.asyncio
    async def test_entity_detail_across_investigations(self):
        detail_records = [
            {
                "investigation_id": INVESTIGATION_A,
                "entity_id": "e1",
                "confidence_score": 0.9,
                "relationships": [
                    {
                        "type": "WORKS_FOR",
                        "target_name": "Corp X",
                        "target_type": "Organization",
                        "confidence": 0.85,
                    }
                ],
                "documents": [
                    {"document_id": "doc1", "mention_count": 1}
                ],
            },
        ]
        inv_row = MagicMock()
        inv_row.id = uuid.UUID(INVESTIGATION_A)
        inv_row.name = "Investigation A"
        doc_row = MagicMock()
        doc_row.id = uuid.UUID("11111111-0000-0000-0000-000000000001")
        doc_row.filename = "report.pdf"

        driver = _make_neo4j_driver(detail_records)

        # Mock DB with multiple calls: inv names + doc filenames
        mock_db = AsyncMock()
        call_count = 0

        async def _side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                result = MagicMock()
                result.__iter__ = MagicMock(return_value=iter([inv_row]))
                return result
            else:
                result = MagicMock()
                result.__iter__ = MagicMock(return_value=iter([doc_row]))
                return result

        mock_db.execute = AsyncMock(side_effect=_side_effect)

        service = CrossInvestigationService(driver, mock_db)
        result = await service.get_entity_detail_across_investigations(
            "John Doe", "person"
        )

        assert result.entity_name == "John Doe"
        assert result.total_investigations == 1
        assert result.investigations[0].relationship_count == 1
        assert result.investigations[0].relationships[0].type == "WORKS_FOR"


class TestGetCrossLinkCounts:
    @pytest.mark.asyncio
    async def test_returns_counts_per_investigation(self):
        count_records = [
            {"investigation_id": INVESTIGATION_A, "link_count": 3},
            {"investigation_id": INVESTIGATION_B, "link_count": 1},
        ]
        driver = _make_neo4j_driver(count_records)

        # Mock DB for _count_dismissed_matches calls (return 0)
        mock_db = AsyncMock()
        count_result = MagicMock()
        count_result.scalar_one.return_value = 0
        mock_db.execute = AsyncMock(return_value=count_result)

        service = CrossInvestigationService(driver, mock_db)
        result = await service.get_cross_link_counts(
            [INVESTIGATION_A, INVESTIGATION_B]
        )

        assert result[INVESTIGATION_A] == 3
        assert result[INVESTIGATION_B] == 1

    @pytest.mark.asyncio
    async def test_empty_investigation_list(self):
        driver = _make_neo4j_driver([])
        mock_db = AsyncMock()

        service = CrossInvestigationService(driver, mock_db)
        result = await service.get_cross_link_counts([])

        assert result == {}
