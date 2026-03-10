"""Tests for prompt templates and LLM response schemas."""

import pytest

from app.llm.prompts import (
    ENTITY_EXTRACTION_SYSTEM_PROMPT,
    ENTITY_EXTRACTION_USER_PROMPT_TEMPLATE,
)
from app.llm.schemas import EntityExtractionResponse, ExtractedEntity


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
