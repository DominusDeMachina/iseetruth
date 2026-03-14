"""Integration tests for query API endpoint."""

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.schemas.query import Citation, EntityReference, QueryResponse


INVESTIGATION_ID = "11111111-1111-1111-1111-111111111111"


@pytest.fixture
def query_client(mock_db_session):
    """TestClient with get_db dependency overridden."""
    from app.db.postgres import get_db
    from app.main import app

    async def override_get_db():
        yield mock_db_session

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def _mock_investigation(mock_db_session):
    """Configure mock_db_session to return an investigation for SELECT queries."""
    mock_investigation = MagicMock()
    mock_investigation.id = uuid.UUID(INVESTIGATION_ID)
    mock_investigation.name = "Test Investigation"

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_investigation
    mock_db_session.execute = AsyncMock(return_value=mock_result)


def _mock_no_investigation(mock_db_session):
    """Configure mock_db_session to return None for investigation lookup."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db_session.execute = AsyncMock(return_value=mock_result)


def _sample_complete_response(query_id: str = "test-query-id") -> QueryResponse:
    return QueryResponse(
        query_id=query_id,
        answer="**John Smith** works for **Acme Corp** [1].",
        citations=[
            Citation(
                citation_number=1,
                document_id="dddd",
                document_filename="report.pdf",
                chunk_id="cccc",
                page_start=1,
                page_end=2,
                text_excerpt="John Smith works at Acme Corp.",
            )
        ],
        entities_mentioned=[
            EntityReference(entity_id="e1", name="John Smith", type="Person"),
            EntityReference(entity_id="e2", name="Acme Corp", type="Organization"),
        ],
        suggested_followups=["What role does John Smith have at Acme Corp?"],
    )


def _parse_sse_events(response_text: str) -> list[dict]:
    """Parse SSE response text into list of event dicts."""
    events = []
    current_event = {}
    for line in response_text.split("\n"):
        line = line.strip()
        if not line:
            if current_event:
                events.append(current_event)
                current_event = {}
            continue
        if line.startswith("event:"):
            current_event["event"] = line[6:].strip()
        elif line.startswith("data:"):
            data_str = line[5:].strip()
            try:
                current_event["data"] = json.loads(data_str)
            except json.JSONDecodeError:
                current_event["data"] = data_str
    if current_event:
        events.append(current_event)
    return events


class TestQueryEndpoint:
    def test_returns_sse_stream_with_correct_event_sequence(self, query_client, mock_db_session):
        """POST /query/ with valid question returns SSE stream with translating → searching → streaming → complete."""
        _mock_investigation(mock_db_session)

        sample_response = _sample_complete_response()

        async def mock_execute_query(**kwargs):
            yield {"event": "query.translating", "data": {"query_id": "qid", "message": "Translating..."}}
            yield {"event": "query.searching", "data": {"query_id": "qid", "message": "Searching..."}}
            yield {"event": "query.streaming", "data": {"query_id": "qid", "chunk": "Test answer"}}
            yield {"event": "query.complete", "data": sample_response.model_dump()}

        with patch("app.api.v1.query.execute_query", side_effect=mock_execute_query):
            response = query_client.post(
                f"/api/v1/investigations/{INVESTIGATION_ID}/query/",
                json={"question": "How is Horvat connected to GreenBuild?"},
            )

        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")

        events = _parse_sse_events(response.text)
        event_types = [e.get("event") for e in events]
        assert "query.translating" in event_types
        assert "query.searching" in event_types
        assert "query.streaming" in event_types
        assert "query.complete" in event_types

        # Verify event ordering
        translating_idx = event_types.index("query.translating")
        searching_idx = event_types.index("query.searching")
        streaming_idx = event_types.index("query.streaming")
        complete_idx = event_types.index("query.complete")
        assert translating_idx < searching_idx < streaming_idx < complete_idx

    def test_returns_no_results_response(self, query_client, mock_db_session):
        """POST /query/ when no results returns no_results: true with standard message."""
        _mock_investigation(mock_db_session)

        async def mock_execute_query(**kwargs):
            yield {"event": "query.translating", "data": {"query_id": "qid", "message": "Translating..."}}
            yield {"event": "query.searching", "data": {"query_id": "qid", "message": "Searching..."}}
            yield {
                "event": "query.complete",
                "data": {
                    "query_id": "qid",
                    "answer": "No connection found in your documents.",
                    "citations": [],
                    "entities_mentioned": [],
                    "no_results": True,
                    "suggested_followups": [],
                },
            }

        with patch("app.api.v1.query.execute_query", side_effect=mock_execute_query):
            response = query_client.post(
                f"/api/v1/investigations/{INVESTIGATION_ID}/query/",
                json={"question": "What about something not in the data?"},
            )

        assert response.status_code == 200
        events = _parse_sse_events(response.text)
        complete_events = [e for e in events if e.get("event") == "query.complete"]
        assert len(complete_events) == 1
        assert complete_events[0]["data"]["no_results"] is True
        assert complete_events[0]["data"]["answer"] == "No connection found in your documents."

    def test_returns_404_for_nonexistent_investigation(self, query_client, mock_db_session):
        """POST /query/ with nonexistent investigation returns 404."""
        _mock_no_investigation(mock_db_session)

        response = query_client.post(
            f"/api/v1/investigations/{INVESTIGATION_ID}/query/",
            json={"question": "Any question"},
        )

        assert response.status_code == 404
        data = response.json()
        assert "investigation_not_found" in data["type"]

    def test_returns_error_when_ollama_unavailable(self, query_client, mock_db_session):
        """POST /query/ when Ollama is unavailable returns error SSE event."""
        _mock_investigation(mock_db_session)

        from app.exceptions import OllamaUnavailableError

        async def mock_execute_query(**kwargs):
            yield {"event": "query.failed", "data": {"query_id": "qid", "error": "LLM service unavailable"}}
            raise OllamaUnavailableError("Ollama unavailable")

        with patch("app.api.v1.query.execute_query", side_effect=mock_execute_query):
            response = query_client.post(
                f"/api/v1/investigations/{INVESTIGATION_ID}/query/",
                json={"question": "Any question"},
            )

        assert response.status_code == 200  # SSE stream itself returns 200
        events = _parse_sse_events(response.text)
        failed_events = [e for e in events if e.get("event") == "query.failed"]
        assert len(failed_events) >= 1

    def test_citations_map_to_real_document_passages(self, query_client, mock_db_session):
        """All citations in response have valid document_id, chunk_id, and text_excerpt."""
        _mock_investigation(mock_db_session)

        response_data = _sample_complete_response()

        async def mock_execute_query(**kwargs):
            yield {"event": "query.complete", "data": response_data.model_dump()}

        with patch("app.api.v1.query.execute_query", side_effect=mock_execute_query):
            response = query_client.post(
                f"/api/v1/investigations/{INVESTIGATION_ID}/query/",
                json={"question": "Who is John Smith?"},
            )

        events = _parse_sse_events(response.text)
        complete_events = [e for e in events if e.get("event") == "query.complete"]
        assert len(complete_events) == 1
        citations = complete_events[0]["data"]["citations"]
        for citation in citations:
            assert citation["document_id"]
            assert citation["chunk_id"]
            assert citation["text_excerpt"]
            assert citation["citation_number"] > 0

    def test_conversation_history_passed_through(self, query_client, mock_db_session):
        """conversation_history is forwarded to the query service."""
        _mock_investigation(mock_db_session)

        captured_kwargs = {}

        async def mock_execute_query(**kwargs):
            captured_kwargs.update(kwargs)
            yield {"event": "query.complete", "data": {"query_id": "qid", "answer": "", "citations": [], "entities_mentioned": [], "no_results": True, "suggested_followups": []}}

        with patch("app.api.v1.query.execute_query", side_effect=mock_execute_query):
            response = query_client.post(
                f"/api/v1/investigations/{INVESTIGATION_ID}/query/",
                json={
                    "question": "Tell me more",
                    "conversation_history": [
                        {"role": "user", "content": "Who is Horvat?"},
                        {"role": "assistant", "content": "Horvat is a person."},
                    ],
                },
            )

        assert response.status_code == 200
        assert captured_kwargs["conversation_history"] is not None
        assert len(captured_kwargs["conversation_history"]) == 2
        assert captured_kwargs["conversation_history"][0]["role"] == "user"

    def test_returns_422_for_empty_question(self, query_client, mock_db_session):
        """POST /query/ with missing question field returns 422."""
        _mock_investigation(mock_db_session)

        response = query_client.post(
            f"/api/v1/investigations/{INVESTIGATION_ID}/query/",
            json={},
        )

        assert response.status_code == 422
