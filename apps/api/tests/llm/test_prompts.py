"""Tests for prompt templates and LLM response schemas."""

import pytest

from app.llm.prompts import (
    ENTITY_EXTRACTION_SYSTEM_PROMPT,
    ENTITY_EXTRACTION_USER_PROMPT_TEMPLATE,
    RELATIONSHIP_EXTRACTION_SYSTEM_PROMPT,
    RELATIONSHIP_EXTRACTION_USER_PROMPT_TEMPLATE,
)
from app.llm.schemas import (
    EntityExtractionResponse,
    ExtractedEntity,
    ExtractedRelationship,
    RelationType,
    RelationshipExtractionResponse,
)


class TestPromptTemplates:
    def test_system_prompt_is_non_empty_string(self):
        assert isinstance(ENTITY_EXTRACTION_SYSTEM_PROMPT, str)
        assert len(ENTITY_EXTRACTION_SYSTEM_PROMPT) > 0

    def test_user_prompt_template_is_non_empty_string(self):
        assert isinstance(ENTITY_EXTRACTION_USER_PROMPT_TEMPLATE, str)
        assert len(ENTITY_EXTRACTION_USER_PROMPT_TEMPLATE) > 0

    def test_user_prompt_template_has_chunk_text_variable(self):
        assert "{chunk_text}" in ENTITY_EXTRACTION_USER_PROMPT_TEMPLATE

    def test_user_prompt_template_can_be_formatted(self):
        result = ENTITY_EXTRACTION_USER_PROMPT_TEMPLATE.format(
            chunk_text="John Smith works at Acme Corp in New York."
        )
        assert "John Smith" in result
        assert "Acme Corp" in result

    def test_system_prompt_mentions_entity_types(self):
        prompt = ENTITY_EXTRACTION_SYSTEM_PROMPT.lower()
        assert "person" in prompt
        assert "organization" in prompt
        assert "location" in prompt


class TestEntityExtractionResponse:
    def test_valid_response(self):
        data = {
            "entities": [
                {"name": "John Smith", "type": "person", "confidence": 0.95},
                {"name": "Acme Corp", "type": "organization", "confidence": 0.88},
                {"name": "New York", "type": "location", "confidence": 0.92},
            ]
        }
        response = EntityExtractionResponse(**data)
        assert len(response.entities) == 3
        assert response.entities[0].name == "John Smith"
        assert response.entities[0].type == "person"
        assert response.entities[0].confidence == 0.95

    def test_empty_entities_list(self):
        response = EntityExtractionResponse(entities=[])
        assert response.entities == []

    def test_invalid_entity_type_rejected(self):
        data = {
            "entities": [
                {"name": "Test", "type": "invalid_type", "confidence": 0.5},
            ]
        }
        with pytest.raises(Exception):  # Pydantic ValidationError
            EntityExtractionResponse(**data)

    def test_confidence_out_of_range_rejected(self):
        data = {
            "entities": [
                {"name": "Test", "type": "person", "confidence": 1.5},
            ]
        }
        with pytest.raises(Exception):
            EntityExtractionResponse(**data)

    def test_negative_confidence_rejected(self):
        data = {
            "entities": [
                {"name": "Test", "type": "person", "confidence": -0.1},
            ]
        }
        with pytest.raises(Exception):
            EntityExtractionResponse(**data)

    def test_missing_name_rejected(self):
        data = {
            "entities": [
                {"type": "person", "confidence": 0.5},
            ]
        }
        with pytest.raises(Exception):
            EntityExtractionResponse(**data)


class TestRelationshipExtractionPrompts:
    def test_system_prompt_is_non_empty_string(self):
        assert isinstance(RELATIONSHIP_EXTRACTION_SYSTEM_PROMPT, str)
        assert len(RELATIONSHIP_EXTRACTION_SYSTEM_PROMPT) > 0

    def test_user_prompt_template_is_non_empty_string(self):
        assert isinstance(RELATIONSHIP_EXTRACTION_USER_PROMPT_TEMPLATE, str)
        assert len(RELATIONSHIP_EXTRACTION_USER_PROMPT_TEMPLATE) > 0

    def test_user_prompt_template_has_chunk_text_variable(self):
        assert "{chunk_text}" in RELATIONSHIP_EXTRACTION_USER_PROMPT_TEMPLATE

    def test_user_prompt_template_has_entities_json_variable(self):
        assert "{entities_json}" in RELATIONSHIP_EXTRACTION_USER_PROMPT_TEMPLATE

    def test_user_prompt_template_can_be_formatted(self):
        result = RELATIONSHIP_EXTRACTION_USER_PROMPT_TEMPLATE.format(
            chunk_text="John Smith works at Acme Corp.",
            entities_json='[{"name": "John Smith", "type": "person"}]',
        )
        assert "John Smith" in result
        assert "Acme Corp" in result

    def test_system_prompt_mentions_all_relation_types(self):
        prompt = RELATIONSHIP_EXTRACTION_SYSTEM_PROMPT
        assert "WORKS_FOR" in prompt
        assert "KNOWS" in prompt
        assert "LOCATED_AT" in prompt


class TestRelationshipExtractionResponse:
    def test_valid_response(self):
        data = {
            "relationships": [
                {
                    "source_entity_name": "John Smith",
                    "target_entity_name": "Acme Corp",
                    "relation_type": "WORKS_FOR",
                    "confidence": 0.9,
                }
            ]
        }
        response = RelationshipExtractionResponse(**data)
        assert len(response.relationships) == 1
        assert response.relationships[0].source_entity_name == "John Smith"
        assert response.relationships[0].relation_type == RelationType.WORKS_FOR
        assert response.relationships[0].confidence == 0.9

    def test_empty_relationships_list(self):
        response = RelationshipExtractionResponse(relationships=[])
        assert response.relationships == []

    def test_invalid_relation_type_rejected(self):
        data = {
            "relationships": [
                {
                    "source_entity_name": "A",
                    "target_entity_name": "B",
                    "relation_type": "INVALID_TYPE",
                    "confidence": 0.5,
                }
            ]
        }
        with pytest.raises(Exception):
            RelationshipExtractionResponse(**data)

    def test_confidence_out_of_range_rejected(self):
        data = {
            "relationships": [
                {
                    "source_entity_name": "A",
                    "target_entity_name": "B",
                    "relation_type": "WORKS_FOR",
                    "confidence": 1.5,
                }
            ]
        }
        with pytest.raises(Exception):
            RelationshipExtractionResponse(**data)

    def test_negative_confidence_rejected(self):
        data = {
            "relationships": [
                {
                    "source_entity_name": "A",
                    "target_entity_name": "B",
                    "relation_type": "KNOWS",
                    "confidence": -0.1,
                }
            ]
        }
        with pytest.raises(Exception):
            RelationshipExtractionResponse(**data)

    def test_all_relation_types_valid(self):
        for rel_type in ("WORKS_FOR", "KNOWS", "LOCATED_AT"):
            data = {
                "relationships": [
                    {
                        "source_entity_name": "A",
                        "target_entity_name": "B",
                        "relation_type": rel_type,
                        "confidence": 0.5,
                    }
                ]
            }
            response = RelationshipExtractionResponse(**data)
            assert len(response.relationships) == 1

    def test_malformed_json_raises(self):
        import json
        with pytest.raises(json.JSONDecodeError):
            json.loads("not valid json")

    def test_missing_relationships_key_rejected(self):
        with pytest.raises(Exception):
            RelationshipExtractionResponse.model_validate({})
