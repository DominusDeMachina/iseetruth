"""Unit tests for cross-investigation matching Celery task."""

import uuid
from unittest.mock import MagicMock, patch

import pytest


INVESTIGATION_ID = "aaaa1111-1111-1111-1111-111111111111"
DOCUMENT_ID = "dddd2222-2222-2222-2222-222222222222"


@pytest.fixture
def mock_neo4j_driver():
    with patch("neo4j.GraphDatabase") as mock_gdb:
        mock_driver = MagicMock()
        mock_gdb.driver.return_value = mock_driver
        yield mock_driver


@pytest.fixture
def mock_publisher():
    with patch(
        "app.worker.tasks.cross_investigation_match.EventPublisher"
    ) as mock_cls:
        mock_pub = MagicMock()
        mock_cls.return_value = mock_pub
        yield mock_pub


@pytest.fixture
def mock_sync_session():
    with patch(
        "app.worker.tasks.cross_investigation_match.SyncSessionLocal"
    ) as mock_factory:
        mock_session = MagicMock()
        mock_factory.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_factory.return_value.__exit__ = MagicMock(return_value=False)
        yield mock_session


class TestRunCrossInvestigationMatchTask:
    def test_publishes_event_when_matches_found(
        self, mock_neo4j_driver, mock_publisher, mock_sync_session
    ):
        # Mock Neo4j returning matches
        match_records = [
            {
                "entity_name": "John Doe",
                "entity_type": "Person",
                "match_entity_id": "e2-id",
                "match_investigation_id": "bbbb2222-2222-2222-2222-222222222222",
            },
        ]
        mock_neo4j_session = MagicMock()
        mock_neo4j_driver.session.return_value.__enter__ = MagicMock(
            return_value=mock_neo4j_session
        )
        mock_neo4j_driver.session.return_value.__exit__ = MagicMock(return_value=False)
        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(return_value=iter(match_records))
        mock_neo4j_session.run.return_value = mock_result

        # Mock PostgreSQL returning investigation name
        inv_row = MagicMock()
        inv_row.id = uuid.UUID("bbbb2222-2222-2222-2222-222222222222")
        inv_row.name = "Investigation B"
        mock_pg_result = MagicMock()
        mock_pg_result.__iter__ = MagicMock(return_value=iter([inv_row]))
        mock_sync_session.execute.return_value = mock_pg_result

        from app.worker.tasks.cross_investigation_match import (
            run_cross_investigation_match_task,
        )

        run_cross_investigation_match_task(INVESTIGATION_ID, DOCUMENT_ID)

        mock_publisher.publish.assert_called_once()
        call_args = mock_publisher.publish.call_args
        assert call_args.kwargs["event_type"] == "cross_investigation.matches_found"
        assert call_args.kwargs["investigation_id"] == INVESTIGATION_ID
        assert call_args.kwargs["payload"]["match_count"] == 1

    def test_no_event_when_no_matches(
        self, mock_neo4j_driver, mock_publisher, mock_sync_session
    ):
        mock_neo4j_session = MagicMock()
        mock_neo4j_driver.session.return_value.__enter__ = MagicMock(
            return_value=mock_neo4j_session
        )
        mock_neo4j_driver.session.return_value.__exit__ = MagicMock(return_value=False)
        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(return_value=iter([]))
        mock_neo4j_session.run.return_value = mock_result

        from app.worker.tasks.cross_investigation_match import (
            run_cross_investigation_match_task,
        )

        run_cross_investigation_match_task(INVESTIGATION_ID, DOCUMENT_ID)

        mock_publisher.publish.assert_not_called()

    def test_handles_neo4j_unavailability_gracefully(
        self, mock_neo4j_driver, mock_publisher, mock_sync_session
    ):
        mock_neo4j_driver.session.side_effect = Exception("Neo4j connection refused")

        from app.worker.tasks.cross_investigation_match import (
            run_cross_investigation_match_task,
        )

        # Should not raise
        run_cross_investigation_match_task(INVESTIGATION_ID, DOCUMENT_ID)
        mock_publisher.publish.assert_not_called()
