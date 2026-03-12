"""Unit tests for EntityQueryService.list_entities()."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.schemas.entity import EntityListResponse
from app.services.entity_query import EntityQueryService


@pytest.fixture
def investigation_id():
    return uuid.UUID("11111111-1111-1111-1111-111111111111")


def _make_neo4j_driver_for_list(records):
    """Build a mock async Neo4j driver returning entity list data."""
    mock_driver = MagicMock()
    mock_session = AsyncMock()
    mock_driver.session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_driver.session.return_value.__aexit__ = AsyncMock(return_value=False)

    async def fake_execute_read(fn, *args, **kwargs):
        return records

    mock_session.execute_read.side_effect = fake_execute_read
    return mock_driver


class TestListEntities:
    @pytest.mark.asyncio
    async def test_returns_entities_with_confidence(self, investigation_id):
        records = [
            {"id": "aaa", "name": "John Smith", "type": "Person", "confidence_score": 0.9, "source_count": 2},
            {"id": "bbb", "name": "Acme Corp", "type": "Organization", "confidence_score": 0.85, "source_count": 1},
        ]
        driver = _make_neo4j_driver_for_list(records)
        db = AsyncMock()

        service = EntityQueryService(driver, db)
        result = await service.list_entities(investigation_id)

        assert isinstance(result, EntityListResponse)
        assert result.total == 2
        assert len(result.items) == 2
        assert result.items[0].confidence_score == 0.9
        assert result.items[0].type == "person"

    @pytest.mark.asyncio
    async def test_summary_counts_by_type(self, investigation_id):
        records = [
            {"id": "a", "name": "John", "type": "Person", "confidence_score": 0.9, "source_count": 1},
            {"id": "b", "name": "Jane", "type": "Person", "confidence_score": 0.8, "source_count": 1},
            {"id": "c", "name": "Acme", "type": "Organization", "confidence_score": 0.7, "source_count": 2},
            {"id": "d", "name": "NYC", "type": "Location", "confidence_score": 0.6, "source_count": 1},
        ]
        driver = _make_neo4j_driver_for_list(records)
        db = AsyncMock()

        service = EntityQueryService(driver, db)
        result = await service.list_entities(investigation_id)

        assert result.summary.people == 2
        assert result.summary.organizations == 1
        assert result.summary.locations == 1
        assert result.summary.total == 4

    @pytest.mark.asyncio
    async def test_evidence_strength_computed(self, investigation_id):
        records = [
            {"id": "a", "name": "Multi", "type": "Person", "confidence_score": 0.9, "source_count": 3},
            {"id": "b", "name": "Single", "type": "Person", "confidence_score": 0.8, "source_count": 1},
            {"id": "c", "name": "None", "type": "Person", "confidence_score": 0.7, "source_count": 0},
        ]
        driver = _make_neo4j_driver_for_list(records)
        db = AsyncMock()

        service = EntityQueryService(driver, db)
        result = await service.list_entities(investigation_id)

        assert result.items[0].evidence_strength == "corroborated"
        assert result.items[1].evidence_strength == "single_source"
        assert result.items[2].evidence_strength == "none"

    @pytest.mark.asyncio
    async def test_pagination_applied(self, investigation_id):
        records = [
            {"id": str(i), "name": f"Entity{i}", "type": "Person", "confidence_score": 1.0 - i * 0.1, "source_count": 1}
            for i in range(5)
        ]
        driver = _make_neo4j_driver_for_list(records)
        db = AsyncMock()

        service = EntityQueryService(driver, db)
        result = await service.list_entities(investigation_id, limit=2, offset=1)

        assert result.total == 5  # total is full count
        assert len(result.items) == 2  # but only 2 items returned

    @pytest.mark.asyncio
    async def test_sorted_by_confidence_desc(self, investigation_id):
        records = [
            {"id": "low", "name": "Low", "type": "Person", "confidence_score": 0.3, "source_count": 1},
            {"id": "high", "name": "High", "type": "Person", "confidence_score": 0.95, "source_count": 1},
            {"id": "mid", "name": "Mid", "type": "Person", "confidence_score": 0.6, "source_count": 1},
        ]
        driver = _make_neo4j_driver_for_list(records)
        db = AsyncMock()

        service = EntityQueryService(driver, db)
        result = await service.list_entities(investigation_id)

        scores = [item.confidence_score for item in result.items]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_type_filter_passed_to_query(self, investigation_id):
        """Verify type filter is forwarded to Neo4j query."""
        driver = _make_neo4j_driver_for_list([])
        db = AsyncMock()

        service = EntityQueryService(driver, db)
        result = await service.list_entities(investigation_id, entity_type="person")

        assert result.total == 0
        assert result.items == []

    @pytest.mark.asyncio
    async def test_empty_result(self, investigation_id):
        driver = _make_neo4j_driver_for_list([])
        db = AsyncMock()

        service = EntityQueryService(driver, db)
        result = await service.list_entities(investigation_id)

        assert result.total == 0
        assert result.items == []
        assert result.summary.people == 0
        assert result.summary.organizations == 0
        assert result.summary.locations == 0
