"""Unit tests for EntityExtractionService."""

import json
import uuid
from unittest.mock import MagicMock, call, patch

import pytest

from app.llm.schemas import EntityType, ExtractedEntity, ExtractedRelationship, RelationType
from app.services.extraction import EntityExtractionService, ExtractionSummary


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def investigation_id():
    return uuid.UUID("11111111-1111-1111-1111-111111111111")


@pytest.fixture
def sample_chunk():
    chunk = MagicMock()
    chunk.id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    chunk.text = "John Smith works at Acme Corp in New York."
    return chunk


@pytest.fixture
def second_chunk():
    chunk = MagicMock()
    chunk.id = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    chunk.text = "John Smith was seen in London."
    return chunk


@pytest.fixture
def mock_ollama():
    return MagicMock()


@pytest.fixture
def mock_neo4j_driver():
    driver = MagicMock()
    mock_session = MagicMock()
    driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
    driver.session.return_value.__exit__ = MagicMock(return_value=False)
    return driver


@pytest.fixture
def person_entity():
    return ExtractedEntity(name="John Smith", type=EntityType.person, confidence=0.9)


@pytest.fixture
def org_entity():
    return ExtractedEntity(name="Acme Corp", type=EntityType.organization, confidence=0.85)


@pytest.fixture
def location_entity():
    return ExtractedEntity(name="New York", type=EntityType.location, confidence=0.92)


# ---------------------------------------------------------------------------
# Tests: _extract_entities
# ---------------------------------------------------------------------------

class TestExtractEntities:
    def test_successful_entity_extraction(self, mock_ollama, mock_neo4j_driver, sample_chunk):
        mock_ollama.chat.return_value = {
            "message": {
                "content": '{"entities": [{"name": "John Smith", "type": "person", "confidence": 0.9}]}'
            }
        }
        service = EntityExtractionService(mock_ollama, mock_neo4j_driver)
        entities = service._extract_entities(sample_chunk)

        assert len(entities) == 1
        assert entities[0].name == "John Smith"
        assert entities[0].type == EntityType.person
        assert entities[0].confidence == 0.9

    def test_extract_entities_parse_failure_returns_empty(self, mock_ollama, mock_neo4j_driver, sample_chunk):
        mock_ollama.chat.return_value = {"message": {"content": "sorry, i cannot help with that"}}
        service = EntityExtractionService(mock_ollama, mock_neo4j_driver)
        entities = service._extract_entities(sample_chunk)

        assert entities == []

    def test_extract_entities_invalid_json_returns_empty(self, mock_ollama, mock_neo4j_driver, sample_chunk):
        mock_ollama.chat.return_value = {"message": {"content": "not valid json {"}}
        service = EntityExtractionService(mock_ollama, mock_neo4j_driver)
        entities = service._extract_entities(sample_chunk)

        assert entities == []

    def test_extract_entities_validation_error_returns_empty(self, mock_ollama, mock_neo4j_driver, sample_chunk):
        mock_ollama.chat.return_value = {
            "message": {
                "content": '{"entities": [{"name": "X", "type": "invalid_type", "confidence": 0.5}]}'
            }
        }
        service = EntityExtractionService(mock_ollama, mock_neo4j_driver)
        entities = service._extract_entities(sample_chunk)

        assert entities == []

    def test_extract_entities_missing_key_returns_empty(self, mock_ollama, mock_neo4j_driver, sample_chunk):
        mock_ollama.chat.return_value = {}  # Missing "message" key
        service = EntityExtractionService(mock_ollama, mock_neo4j_driver)
        entities = service._extract_entities(sample_chunk)

        assert entities == []

    def test_extract_entities_calls_ollama_with_correct_format(self, mock_ollama, mock_neo4j_driver, sample_chunk):
        mock_ollama.chat.return_value = {"message": {"content": '{"entities": []}'}}
        service = EntityExtractionService(mock_ollama, mock_neo4j_driver)
        service._extract_entities(sample_chunk)

        call_kwargs = mock_ollama.chat.call_args[1]
        assert call_kwargs["format"] == "json"
        assert call_kwargs["temperature"] == 0


# ---------------------------------------------------------------------------
# Tests: _extract_relationships
# ---------------------------------------------------------------------------

class TestExtractRelationships:
    def test_relationship_extraction_skipped_if_zero_entities(self, mock_ollama, mock_neo4j_driver, sample_chunk):
        service = EntityExtractionService(mock_ollama, mock_neo4j_driver)
        rels = service._extract_relationships(sample_chunk, [])

        assert rels == []
        mock_ollama.chat.assert_not_called()

    def test_relationship_extraction_skipped_if_one_entity(self, mock_ollama, mock_neo4j_driver, sample_chunk, person_entity):
        service = EntityExtractionService(mock_ollama, mock_neo4j_driver)
        rels = service._extract_relationships(sample_chunk, [person_entity])

        assert rels == []
        mock_ollama.chat.assert_not_called()

    def test_relationship_extraction_with_two_entities(
        self, mock_ollama, mock_neo4j_driver, sample_chunk, person_entity, org_entity
    ):
        mock_ollama.chat.return_value = {
            "message": {
                "content": json.dumps({
                    "relationships": [
                        {
                            "source_entity_name": "John Smith",
                            "target_entity_name": "Acme Corp",
                            "relation_type": "WORKS_FOR",
                            "confidence": 0.88,
                        }
                    ]
                })
            }
        }
        service = EntityExtractionService(mock_ollama, mock_neo4j_driver)
        rels = service._extract_relationships(sample_chunk, [person_entity, org_entity])

        assert len(rels) == 1
        assert rels[0].source_entity_name == "John Smith"
        assert rels[0].relation_type == RelationType.WORKS_FOR

    def test_relationship_with_unknown_entity_name_is_excluded(
        self, mock_ollama, mock_neo4j_driver, sample_chunk, person_entity, org_entity
    ):
        mock_ollama.chat.return_value = {
            "message": {
                "content": json.dumps({
                    "relationships": [
                        {
                            "source_entity_name": "Unknown Person",  # not in entity list
                            "target_entity_name": "Acme Corp",
                            "relation_type": "WORKS_FOR",
                            "confidence": 0.7,
                        }
                    ]
                })
            }
        }
        service = EntityExtractionService(mock_ollama, mock_neo4j_driver)
        rels = service._extract_relationships(sample_chunk, [person_entity, org_entity])

        assert rels == []  # filtered out

    def test_relationship_extraction_parse_failure_returns_empty(
        self, mock_ollama, mock_neo4j_driver, sample_chunk, person_entity, org_entity
    ):
        mock_ollama.chat.return_value = {"message": {"content": "cannot extract"}}
        service = EntityExtractionService(mock_ollama, mock_neo4j_driver)
        rels = service._extract_relationships(sample_chunk, [person_entity, org_entity])

        assert rels == []

    def test_relationship_extraction_passes_entities_json(
        self, mock_ollama, mock_neo4j_driver, sample_chunk, person_entity, org_entity
    ):
        mock_ollama.chat.return_value = {"message": {"content": '{"relationships": []}'}}
        service = EntityExtractionService(mock_ollama, mock_neo4j_driver)
        service._extract_relationships(sample_chunk, [person_entity, org_entity])

        call_kwargs = mock_ollama.chat.call_args[1]
        messages = call_kwargs["messages"]
        user_content = messages[1]["content"]
        assert "John Smith" in user_content
        assert "Acme Corp" in user_content


# ---------------------------------------------------------------------------
# Tests: extract_from_chunks (integration)
# ---------------------------------------------------------------------------

class TestExtractFromChunks:
    def test_entity_deduplication_fires_callback_once(
        self, mock_ollama, mock_neo4j_driver, sample_chunk, second_chunk, investigation_id
    ):
        """entity.discovered callback fires only for first occurrence of each entity."""
        # Both chunks extract "John Smith" — callback should fire only once
        mock_ollama.chat.side_effect = [
            # chunk 1 entity extraction
            {"message": {"content": '{"entities": [{"name": "John Smith", "type": "person", "confidence": 0.9}]}'}},
            # chunk 1 only 1 entity so no relationship call
            # chunk 2 entity extraction
            {"message": {"content": '{"entities": [{"name": "John Smith", "type": "person", "confidence": 0.85}]}'}},
            # chunk 2 only 1 entity so no relationship call
        ]

        discovered = []
        service = EntityExtractionService(mock_ollama, mock_neo4j_driver)
        summary = service.extract_from_chunks(
            [sample_chunk, second_chunk],
            investigation_id=investigation_id,
            on_entity_discovered=discovered.append,
        )

        entity_names = [e.name for e in discovered]
        assert entity_names.count("John Smith") == 1
        assert summary.entity_count == 1  # unique entities
        assert summary.chunk_count == 2

    def test_new_entities_in_second_chunk_fire_callback(
        self, mock_ollama, mock_neo4j_driver, sample_chunk, second_chunk, investigation_id
    ):
        """New entity appearing in chunk 2 fires callback; duplicate doesn't."""
        mock_ollama.chat.side_effect = [
            # chunk 1 entity extraction — "John Smith" only
            {"message": {"content": '{"entities": [{"name": "John Smith", "type": "person", "confidence": 0.9}]}'}},
            # chunk 2 entity extraction — "John Smith" + "London"
            {"message": {"content": json.dumps({
                "entities": [
                    {"name": "John Smith", "type": "person", "confidence": 0.85},
                    {"name": "London", "type": "location", "confidence": 0.95},
                ]
            })}},
            # chunk 2 relationship extraction (2 entities)
            {"message": {"content": '{"relationships": []}'}},
        ]

        discovered = []
        service = EntityExtractionService(mock_ollama, mock_neo4j_driver)
        summary = service.extract_from_chunks(
            [sample_chunk, second_chunk],
            investigation_id=investigation_id,
            on_entity_discovered=discovered.append,
        )

        names = [e.name for e in discovered]
        assert "John Smith" in names
        assert "London" in names
        assert names.count("John Smith") == 1
        assert summary.entity_count == 2

    def test_extraction_summary_counts_correct(
        self, mock_ollama, mock_neo4j_driver, sample_chunk, investigation_id
    ):
        mock_ollama.chat.side_effect = [
            # entity extraction
            {"message": {"content": json.dumps({
                "entities": [
                    {"name": "John Smith", "type": "person", "confidence": 0.9},
                    {"name": "Acme Corp", "type": "organization", "confidence": 0.85},
                ]
            })}},
            # relationship extraction
            {"message": {"content": json.dumps({
                "relationships": [
                    {
                        "source_entity_name": "John Smith",
                        "target_entity_name": "Acme Corp",
                        "relation_type": "WORKS_FOR",
                        "confidence": 0.88,
                    }
                ]
            })}},
        ]

        service = EntityExtractionService(mock_ollama, mock_neo4j_driver)
        summary = service.extract_from_chunks(
            [sample_chunk],
            investigation_id=investigation_id,
        )

        assert summary.entity_count == 2
        assert summary.relationship_count == 1
        assert summary.chunk_count == 1

    def test_no_callback_provided_does_not_raise(
        self, mock_ollama, mock_neo4j_driver, sample_chunk, investigation_id
    ):
        mock_ollama.chat.return_value = {
            "message": {"content": '{"entities": [{"name": "X", "type": "person", "confidence": 0.5}]}'}
        }

        service = EntityExtractionService(mock_ollama, mock_neo4j_driver)
        # Should not raise even with no callback
        summary = service.extract_from_chunks([sample_chunk], investigation_id=investigation_id)
        assert summary.entity_count == 1

    def test_chunk_with_parse_failure_continues_processing(
        self, mock_ollama, mock_neo4j_driver, sample_chunk, second_chunk, investigation_id
    ):
        mock_ollama.chat.side_effect = [
            # chunk 1 entity extraction fails
            {"message": {"content": "invalid json {{{"}},
            # chunk 2 entity extraction succeeds
            {"message": {"content": '{"entities": [{"name": "Alice", "type": "person", "confidence": 0.8}]}'}},
        ]

        discovered = []
        service = EntityExtractionService(mock_ollama, mock_neo4j_driver)
        summary = service.extract_from_chunks(
            [sample_chunk, second_chunk],
            investigation_id=investigation_id,
            on_entity_discovered=discovered.append,
        )

        assert len(discovered) == 1
        assert discovered[0].name == "Alice"
        assert summary.entity_count == 1


# ---------------------------------------------------------------------------
# Tests: _store_in_neo4j — MERGE is used (not CREATE)
# ---------------------------------------------------------------------------

class TestStoreInNeo4j:
    def test_merge_cypher_used_for_entity(
        self, mock_ollama, mock_neo4j_driver, sample_chunk, person_entity, investigation_id
    ):
        """Verify MERGE Cypher is called for entity storage (not CREATE)."""
        mock_session = MagicMock()
        mock_neo4j_driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_neo4j_driver.session.return_value.__exit__ = MagicMock(return_value=False)

        service = EntityExtractionService(mock_ollama, mock_neo4j_driver)
        service._store_in_neo4j(sample_chunk, [person_entity], [], investigation_id)

        mock_session.execute_write.assert_called_once()
        # The write transaction was called — verify the session was used
        write_fn = mock_session.execute_write.call_args[0][0]
        mock_tx = MagicMock()
        write_fn(mock_tx)

        # Verify MERGE is used in the Cypher query — not a standalone CREATE
        run_calls = mock_tx.run.call_args_list
        assert len(run_calls) >= 1
        cypher = run_calls[0][0][0]
        assert cypher.strip().startswith("MERGE")
        assert not cypher.strip().startswith("CREATE")

    def test_no_neo4j_write_when_no_entities_or_relationships(
        self, mock_ollama, mock_neo4j_driver, sample_chunk, investigation_id
    ):
        service = EntityExtractionService(mock_ollama, mock_neo4j_driver)
        service._store_in_neo4j(sample_chunk, [], [], investigation_id)

        mock_neo4j_driver.session.assert_not_called()


# ---------------------------------------------------------------------------
# Tests: ensure_neo4j_constraints
# ---------------------------------------------------------------------------

class TestEnsureNeo4jConstraints:
    def test_constraints_created_for_all_labels(self):
        from app.services.extraction import ensure_neo4j_constraints

        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)

        ensure_neo4j_constraints(mock_driver)

        # Should have been called for Person, Organization, Location (constraints + indexes = 6 calls)
        assert mock_session.run.call_count == 6

    def test_constraints_are_idempotent(self):
        """Calling ensure_neo4j_constraints twice should not raise."""
        from app.services.extraction import ensure_neo4j_constraints

        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)

        ensure_neo4j_constraints(mock_driver)
        ensure_neo4j_constraints(mock_driver)

        assert mock_session.run.call_count == 12  # 6 per call
