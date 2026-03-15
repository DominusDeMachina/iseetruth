"""Unit tests for the GRAPH FIRST query pipeline service."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.llm.schemas import QueryTranslation
from app.schemas.query import Citation, EntityReference, QueryResponse
from app.services.query import (
    _fallback_translation,
    _format_answer,
    _format_citation_list,
    _format_graph_results,
    _format_vector_results,
    _generate_followups,
    _merge_results,
    _resolve_provenance,
    _sanitize_cypher,
    _search_graph,
    _search_vectors,
    _translate_question,
    execute_query,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_ollama():
    client = MagicMock()
    client.chat.return_value = {
        "message": {
            "content": json.dumps({
                "cypher_queries": [
                    "MATCH p = shortestPath((a)-[*..5]-(b)) "
                    "WHERE a.investigation_id = $investigation_id "
                    "AND toLower(a.name) CONTAINS toLower('Horvat') "
                    "AND toLower(b.name) CONTAINS toLower('GreenBuild') "
                    "RETURN p"
                ],
                "search_terms": ["Horvat GreenBuild connection"],
                "entity_names": ["Horvat", "GreenBuild"],
            })
        }
    }
    return client


@pytest.fixture
def mock_embedding_client():
    client = MagicMock()
    client.embed.return_value = [0.1] * 4096
    return client


@pytest.fixture
def mock_neo4j_driver():
    driver = AsyncMock()
    session = AsyncMock()
    driver.session.return_value.__aenter__ = AsyncMock(return_value=session)
    driver.session.return_value.__aexit__ = AsyncMock(return_value=False)
    return driver


@pytest.fixture
def mock_qdrant():
    client = MagicMock()
    point = MagicMock()
    point.payload = {
        "chunk_id": "chunk-1",
        "document_id": "doc-1",
        "investigation_id": "inv-1",
        "page_start": 1,
        "page_end": 2,
        "text_excerpt": "Horvat met with GreenBuild representatives.",
    }
    point.score = 0.92
    query_response = MagicMock()
    query_response.points = [point]
    client.query_points.return_value = query_response
    return client


@pytest.fixture
def mock_event_publisher():
    publisher = MagicMock()
    publisher.publish = MagicMock()
    publisher.close = MagicMock()
    return publisher


@pytest.fixture
def mock_db_session():
    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.__iter__ = MagicMock(return_value=iter([]))
    session.execute = AsyncMock(return_value=mock_result)
    return session


# ---------------------------------------------------------------------------
# Translation Tests
# ---------------------------------------------------------------------------


class TestTranslateQuestion:
    def test_parses_valid_llm_json(self, mock_ollama):
        """LLM returns valid JSON → parsed into QueryTranslation."""
        result = _translate_question(mock_ollama, "inv-1", "How is Horvat connected to GreenBuild?", None)

        assert isinstance(result, QueryTranslation)
        assert len(result.cypher_queries) == 1
        assert "Horvat" in result.cypher_queries[0]
        assert "GreenBuild" in result.entity_names

    def test_fallback_on_invalid_json(self, mock_ollama):
        """LLM returns invalid JSON → fallback to entity name extraction."""
        mock_ollama.chat.return_value = {"message": {"content": "not valid json at all"}}

        result = _translate_question(mock_ollama, "inv-1", "How is Horvat connected to GreenBuild?", None)

        assert isinstance(result, QueryTranslation)
        assert "Horvat" in result.entity_names
        assert "GreenBuild" in result.entity_names

    def test_conversation_history_included_in_messages(self, mock_ollama):
        """Conversation history is added to LLM messages."""
        history = [
            {"role": "user", "content": "Who is Horvat?"},
            {"role": "assistant", "content": "A person of interest."},
        ]

        _translate_question(mock_ollama, "inv-1", "Tell me more", history)

        call_args = mock_ollama.chat.call_args
        messages = call_args.kwargs.get("messages") or call_args[1].get("messages") or call_args[0][1] if len(call_args[0]) > 1 else call_args.kwargs["messages"]
        # System + 2 history turns + 1 user turn = 4
        assert len(messages) == 4
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "Who is Horvat?"


class TestFallbackTranslation:
    def test_extracts_capitalized_names(self):
        """Capitalized words extracted as entity names."""
        result = _fallback_translation("How is Horvat connected to GreenBuild LLC?")
        assert "Horvat" in result.entity_names

    def test_extracts_quoted_strings(self):
        """Quoted strings extracted as entity names."""
        result = _fallback_translation('Find "John Smith" in the documents')
        assert "John Smith" in result.entity_names

    def test_generates_shortest_path_for_two_entities(self):
        """Two entities → shortestPath Cypher query."""
        result = _fallback_translation("Connection between Horvat and GreenBuild")
        assert len(result.cypher_queries) >= 1
        assert "shortestPath" in result.cypher_queries[0]

    def test_fallback_shortest_path_excludes_mentioned_in(self):
        """Fallback shortestPath excludes MENTIONED_IN edges."""
        result = _fallback_translation("Connection between Horvat and GreenBuild")
        cypher = result.cypher_queries[0]
        assert "MENTIONED_IN" in cypher
        assert "NONE(" in cypher

    def test_single_entity_excludes_mentioned_in(self):
        """Single entity fallback excludes MENTIONED_IN."""
        result = _fallback_translation("Tell me about Horvat")
        assert len(result.cypher_queries) >= 1
        cypher = result.cypher_queries[0]
        assert "$investigation_id" in cypher
        assert "MENTIONED_IN" in cypher


class TestSanitizeCypher:
    def test_adds_mentioned_in_exclusion_to_unprotected_path(self):
        """Untyped [*..5] without MENTIONED_IN exclusion gets a NONE filter added."""
        cypher = (
            "MATCH p = shortestPath((a)-[*..5]-(b)) "
            "WHERE a.name = 'X' "
            "RETURN p"
        )
        result = _sanitize_cypher(cypher)
        assert "MENTIONED_IN" in result
        assert "NONE(" in result

    def test_preserves_query_with_existing_exclusion(self):
        """Queries that already exclude MENTIONED_IN are left unchanged."""
        cypher = (
            "MATCH p = shortestPath((a)-[*..5]-(b)) "
            "WHERE a.name = 'X' "
            "AND NONE(r IN relationships(p) WHERE type(r) = 'MENTIONED_IN') "
            "RETURN p"
        )
        result = _sanitize_cypher(cypher)
        assert result == cypher

    def test_no_variable_length_path_left_unchanged(self):
        """Queries without variable-length paths are not modified."""
        cypher = "MATCH (a)-[r]->(b) RETURN a, r, b"
        result = _sanitize_cypher(cypher)
        assert result == cypher

    def test_adds_where_when_none_exists(self):
        """If no WHERE clause, adds WHERE before RETURN."""
        cypher = "MATCH p = shortestPath((a)-[*..3]-(b)) RETURN p"
        result = _sanitize_cypher(cypher)
        assert "WHERE NONE(" in result


# ---------------------------------------------------------------------------
# Graph Search Tests
# ---------------------------------------------------------------------------


def _make_neo4j_driver_mock(execute_read_side_effect=None):
    """Create a properly-mocked Neo4j async driver.

    ``neo4j_driver.session()`` is a sync call that returns an async context manager.
    """
    mock_session = AsyncMock()
    if execute_read_side_effect:
        mock_session.execute_read = AsyncMock(side_effect=execute_read_side_effect)
    else:
        mock_session.execute_read = AsyncMock(return_value=[])

    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=mock_session)
    ctx.__aexit__ = AsyncMock(return_value=False)

    mock_driver = MagicMock()
    mock_driver.session.return_value = ctx
    return mock_driver, mock_session


class TestSearchGraph:
    @pytest.mark.asyncio
    async def test_executes_cypher_and_resolves_provenance(self):
        """Cypher queries are executed, provenance resolved for discovered entities."""
        cypher_result_data = [
            {"entity_id": "e1", "id": "e1", "name": "Horvat", "type": "Person", "confidence_score": 0.9}
        ]

        provenance_map = {
            "e1": [
                {
                    "chunk_id": "c1",
                    "page_start": 1,
                    "page_end": 2,
                    "text_excerpt": "Horvat attended the meeting.",
                    "document_id": "d1",
                }
            ]
        }

        call_count = [0]

        async def mock_execute_read(func, *args, **kwargs):
            call_count[0] += 1
            if call_count[0] <= 1:
                return cypher_result_data
            else:
                return provenance_map

        mock_driver, _ = _make_neo4j_driver_mock(execute_read_side_effect=mock_execute_read)

        translation = QueryTranslation(
            cypher_queries=["MATCH (e) WHERE e.investigation_id = $investigation_id RETURN e"],
            search_terms=["Horvat"],
            entity_names=["Horvat"],
        )

        results = await _search_graph(mock_driver, "inv-1", translation)
        assert len(results) > 0


# ---------------------------------------------------------------------------
# Vector Search Tests
# ---------------------------------------------------------------------------


class TestSearchVectors:
    @pytest.mark.asyncio
    async def test_embeds_question_and_searches_qdrant(self, mock_qdrant, mock_embedding_client):
        """Question is embedded and Qdrant searched with investigation filter."""
        results = await _search_vectors(mock_qdrant, mock_embedding_client, "inv-1", "Who is Horvat?")

        mock_embedding_client.embed.assert_called_once_with("Who is Horvat?")
        mock_qdrant.query_points.assert_called_once()
        assert len(results) == 1
        assert results[0]["chunk_id"] == "chunk-1"
        assert results[0]["text_excerpt"] == "Horvat met with GreenBuild representatives."


# ---------------------------------------------------------------------------
# Result Merge Tests
# ---------------------------------------------------------------------------


class TestMergeResults:
    @pytest.mark.asyncio
    async def test_deduplication_by_chunk_id(self, mock_db_session):
        """Overlapping chunks from graph and vector results are deduplicated."""
        graph_results = [
            {
                "entity_id": "e1",
                "id": "e1",
                "name": "Horvat",
                "type": "Person",
                "provenance": [
                    {"chunk_id": "c1", "document_id": "d1", "page_start": 1, "page_end": 2, "text_excerpt": "Text 1"},
                ],
            }
        ]
        vector_results = [
            {"chunk_id": "c1", "document_id": "d1", "page_start": 1, "page_end": 2, "text_excerpt": "Horvat report text 1", "score": 0.9},
            {"chunk_id": "c2", "document_id": "d1", "page_start": 3, "page_end": 4, "text_excerpt": "Horvat additional details", "score": 0.8},
        ]

        citations, entities, graph_text, vector_text = await _merge_results(
            graph_results, vector_results, mock_db_session, entity_names=["Horvat"]
        )

        # c1 appears in both but should only be counted once
        chunk_ids = [c.chunk_id for c in citations]
        assert chunk_ids.count("c1") == 1
        assert "c2" in chunk_ids
        assert len(citations) == 2

    @pytest.mark.asyncio
    async def test_citation_numbering(self, mock_db_session):
        """Citations are numbered sequentially starting at 1."""
        graph_results = [
            {
                "entity_id": "e1", "id": "e1", "name": "Person A", "type": "Person",
                "provenance": [
                    {"chunk_id": "c1", "document_id": "d1", "page_start": 1, "page_end": 2, "text_excerpt": "A"},
                    {"chunk_id": "c2", "document_id": "d2", "page_start": 3, "page_end": 4, "text_excerpt": "B"},
                ],
            }
        ]

        citations, _, _, _ = await _merge_results(graph_results, [], mock_db_session)

        numbers = [c.citation_number for c in citations]
        assert numbers == [1, 2]

    @pytest.mark.asyncio
    async def test_entities_extracted_from_graph_results(self, mock_db_session):
        """Entity references are extracted from graph results."""
        graph_results = [
            {"entity_id": "e1", "id": "e1", "name": "Horvat", "type": "Person", "provenance": [
                {"chunk_id": "c1", "document_id": "d1", "page_start": 1, "page_end": 1, "text_excerpt": "t"},
            ]},
            {"entity_id": "e2", "id": "e2", "name": "GreenBuild", "type": "Organization", "provenance": [
                {"chunk_id": "c2", "document_id": "d1", "page_start": 2, "page_end": 2, "text_excerpt": "t"},
            ]},
        ]

        _, entities, _, _ = await _merge_results(graph_results, [], mock_db_session)

        names = {e.name for e in entities}
        assert "Horvat" in names
        assert "GreenBuild" in names


class TestVectorEntityFiltering:
    @pytest.mark.asyncio
    async def test_irrelevant_vectors_filtered_when_graph_exists(self, mock_db_session):
        """Vector results not mentioning any entity are dropped when graph results exist."""
        graph_results = [
            {
                "entity_id": "e1", "id": "e1", "name": "Horvat", "type": "Person",
                "provenance": [
                    {"chunk_id": "c1", "document_id": "d1", "page_start": 1, "page_end": 1, "text_excerpt": "Horvat info"},
                ],
            }
        ]
        vector_results = [
            {"chunk_id": "c2", "document_id": "d2", "page_start": 1, "page_end": 2,
             "text_excerpt": "Completely unrelated URL analysis text", "score": 0.8},
            {"chunk_id": "c3", "document_id": "d2", "page_start": 3, "page_end": 4,
             "text_excerpt": "Horvat met with representatives", "score": 0.7},
        ]

        citations, _, _, _ = await _merge_results(
            graph_results, vector_results, mock_db_session, entity_names=["Horvat"]
        )

        chunk_ids = [c.chunk_id for c in citations]
        assert "c2" not in chunk_ids  # irrelevant vector filtered out
        assert "c3" in chunk_ids      # relevant vector kept

    @pytest.mark.asyncio
    async def test_all_vectors_pass_when_no_graph_results(self, mock_db_session):
        """Without graph results, all above-threshold vectors are kept."""
        vector_results = [
            {"chunk_id": "c1", "document_id": "d1", "page_start": 1, "page_end": 2,
             "text_excerpt": "Any text at all", "score": 0.8},
        ]

        citations, _, _, _ = await _merge_results(
            [], vector_results, mock_db_session
        )

        assert len(citations) == 1
        assert citations[0].chunk_id == "c1"


# ---------------------------------------------------------------------------
# Empty Results Tests
# ---------------------------------------------------------------------------


class TestEmptyResults:
    @pytest.mark.asyncio
    async def test_no_results_short_circuit(self, mock_db_session):
        """Zero graph + zero vector results → empty citations list."""
        citations, entities, graph_text, vector_text = await _merge_results([], [], mock_db_session)

        assert citations == []
        assert entities == []


# ---------------------------------------------------------------------------
# Answer Formatting Tests
# ---------------------------------------------------------------------------


class TestAnswerFormatting:
    def test_format_answer_calls_llm(self):
        """LLM is called with formatting prompts and returns cited prose."""
        mock_client = MagicMock()
        mock_client.chat.return_value = {
            "message": {"content": "**Horvat** works for **GreenBuild** [1]."}
        }

        result = _format_answer(mock_client, "question", "graph text", "vector text", "[1] report.pdf")

        mock_client.chat.assert_called_once()
        assert "[1]" in result
        assert "Horvat" in result


# ---------------------------------------------------------------------------
# SSE Event Order Tests
# ---------------------------------------------------------------------------


class TestSSEEventOrder:
    @pytest.mark.asyncio
    async def test_events_published_in_correct_order(
        self, mock_ollama, mock_embedding_client, mock_qdrant,
        mock_event_publisher, mock_db_session,
    ):
        """SSE events are emitted in order: translating → searching → streaming → complete."""
        mock_neo4j, _ = _make_neo4j_driver_mock()

        # Make qdrant return no results so we get no_results path
        empty_response = MagicMock()
        empty_response.points = []
        mock_qdrant.query_points.return_value = empty_response

        events = []
        async for event in execute_query(
            investigation_id="inv-1",
            question="Any question?",
            conversation_history=None,
            neo4j_driver=mock_neo4j,
            qdrant_client=mock_qdrant,
            ollama_client=mock_ollama,
            embedding_client=mock_embedding_client,
            event_publisher=mock_event_publisher,
            db=mock_db_session,
        ):
            events.append(event["event"])

        assert events[0] == "query.translating"
        assert events[1] == "query.searching"
        # With no results, should go straight to complete
        assert "query.complete" in events


# ---------------------------------------------------------------------------
# Follow-up Suggestions Tests
# ---------------------------------------------------------------------------


class TestFollowupSuggestions:
    def test_parses_json_array(self):
        """LLM returns JSON array of follow-up questions."""
        mock_client = MagicMock()
        mock_client.generate.return_value = '["What else about Horvat?", "Where is GreenBuild based?"]'

        entities = [EntityReference(entity_id="e1", name="Horvat", type="Person")]
        result = _generate_followups(mock_client, "question", "answer", entities)

        assert len(result) == 2
        assert "Horvat" in result[0]

    def test_handles_invalid_json_gracefully(self):
        """Invalid JSON from LLM → empty list."""
        mock_client = MagicMock()
        mock_client.generate.return_value = "not json"

        result = _generate_followups(mock_client, "q", "a", [])

        assert result == []

    def test_limits_to_three_suggestions(self):
        """At most 3 follow-up suggestions returned."""
        mock_client = MagicMock()
        mock_client.generate.return_value = '["Q1?", "Q2?", "Q3?", "Q4?", "Q5?"]'

        result = _generate_followups(mock_client, "q", "a", [])

        assert len(result) == 3
