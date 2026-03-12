"""Tests for ExtractionSummary.average_confidence computation."""

import json
import uuid
from unittest.mock import MagicMock

import pytest

from app.services.extraction import EntityExtractionService, ExtractionSummary


@pytest.fixture
def investigation_id():
    return uuid.UUID("11111111-1111-1111-1111-111111111111")


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
def sample_chunk():
    chunk = MagicMock()
    chunk.id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    chunk.document_id = uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
    chunk.page_start = 1
    chunk.page_end = 1
    chunk.text = "Test chunk text."
    return chunk


class TestExtractionSummaryAverageConfidence:
    def test_average_confidence_default_zero(self):
        summary = ExtractionSummary(entity_count=0, relationship_count=0, chunk_count=0)
        assert summary.average_confidence == 0.0

    def test_average_confidence_single_entity(
        self, mock_ollama, mock_neo4j_driver, sample_chunk, investigation_id
    ):
        mock_ollama.chat.return_value = {
            "message": {
                "content": json.dumps({
                    "entities": [
                        {"name": "John Smith", "type": "person", "confidence": 0.8}
                    ]
                })
            }
        }

        service = EntityExtractionService(mock_ollama, mock_neo4j_driver)
        summary = service.extract_from_chunks(
            [sample_chunk], investigation_id=investigation_id
        )

        assert summary.average_confidence == 0.8

    def test_average_confidence_multiple_entities(
        self, mock_ollama, mock_neo4j_driver, sample_chunk, investigation_id
    ):
        mock_ollama.chat.side_effect = [
            # entity extraction
            {
                "message": {
                    "content": json.dumps({
                        "entities": [
                            {"name": "John", "type": "person", "confidence": 0.9},
                            {"name": "Acme", "type": "organization", "confidence": 0.7},
                        ]
                    })
                }
            },
            # relationship extraction (2 entities)
            {"message": {"content": '{"relationships": []}'}},
        ]

        service = EntityExtractionService(mock_ollama, mock_neo4j_driver)
        summary = service.extract_from_chunks(
            [sample_chunk], investigation_id=investigation_id
        )

        assert summary.average_confidence == pytest.approx(0.8)  # (0.9 + 0.7) / 2

    def test_average_confidence_uses_max_per_entity(
        self, mock_ollama, mock_neo4j_driver, investigation_id
    ):
        """When same entity appears in multiple chunks, max confidence is used."""
        chunk1 = MagicMock()
        chunk1.id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
        chunk1.document_id = uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
        chunk1.page_start = 1
        chunk1.page_end = 1
        chunk1.text = "Chunk 1"

        chunk2 = MagicMock()
        chunk2.id = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
        chunk2.document_id = uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
        chunk2.page_start = 2
        chunk2.page_end = 2
        chunk2.text = "Chunk 2"

        mock_ollama.chat.side_effect = [
            # chunk1: John with confidence 0.6
            {
                "message": {
                    "content": json.dumps({
                        "entities": [
                            {"name": "John", "type": "person", "confidence": 0.6}
                        ]
                    })
                }
            },
            # chunk2: John with confidence 0.9 (higher)
            {
                "message": {
                    "content": json.dumps({
                        "entities": [
                            {"name": "John", "type": "person", "confidence": 0.9}
                        ]
                    })
                }
            },
        ]

        service = EntityExtractionService(mock_ollama, mock_neo4j_driver)
        summary = service.extract_from_chunks(
            [chunk1, chunk2], investigation_id=investigation_id
        )

        assert summary.entity_count == 1
        assert summary.average_confidence == 0.9  # max of 0.6, 0.9

    def test_average_confidence_zero_entities_returns_zero(
        self, mock_ollama, mock_neo4j_driver, sample_chunk, investigation_id
    ):
        mock_ollama.chat.return_value = {
            "message": {"content": '{"entities": []}'}
        }

        service = EntityExtractionService(mock_ollama, mock_neo4j_driver)
        summary = service.extract_from_chunks(
            [sample_chunk], investigation_id=investigation_id
        )

        assert summary.entity_count == 0
        assert summary.average_confidence == 0.0

    def test_average_confidence_parse_failure_returns_zero(
        self, mock_ollama, mock_neo4j_driver, sample_chunk, investigation_id
    ):
        """If all extractions fail to parse, average is 0.0."""
        mock_ollama.chat.return_value = {
            "message": {"content": "invalid json"}
        }

        service = EntityExtractionService(mock_ollama, mock_neo4j_driver)
        summary = service.extract_from_chunks(
            [sample_chunk], investigation_id=investigation_id
        )

        assert summary.entity_count == 0
        assert summary.average_confidence == 0.0


class TestDocumentResponseExtractionQuality:
    """Test the computed extraction_quality field on DocumentResponse."""

    def test_extraction_quality_high(self):
        from app.schemas.document import DocumentResponse

        resp = DocumentResponse(
            id=uuid.uuid4(),
            investigation_id=uuid.uuid4(),
            filename="test.pdf",
            size_bytes=1000,
            sha256_checksum="a" * 64,
            status="complete",
            page_count=5,
            extraction_confidence=0.9,
            created_at="2026-03-12T00:00:00Z",
            updated_at="2026-03-12T00:00:00Z",
        )
        assert resp.extraction_quality == "high"

    def test_extraction_quality_high_threshold(self):
        from app.schemas.document import DocumentResponse

        resp = DocumentResponse(
            id=uuid.uuid4(),
            investigation_id=uuid.uuid4(),
            filename="test.pdf",
            size_bytes=1000,
            sha256_checksum="a" * 64,
            status="complete",
            page_count=5,
            extraction_confidence=0.7,
            created_at="2026-03-12T00:00:00Z",
            updated_at="2026-03-12T00:00:00Z",
        )
        assert resp.extraction_quality == "high"

    def test_extraction_quality_medium(self):
        from app.schemas.document import DocumentResponse

        resp = DocumentResponse(
            id=uuid.uuid4(),
            investigation_id=uuid.uuid4(),
            filename="test.pdf",
            size_bytes=1000,
            sha256_checksum="a" * 64,
            status="complete",
            page_count=5,
            extraction_confidence=0.5,
            created_at="2026-03-12T00:00:00Z",
            updated_at="2026-03-12T00:00:00Z",
        )
        assert resp.extraction_quality == "medium"

    def test_extraction_quality_medium_threshold(self):
        from app.schemas.document import DocumentResponse

        resp = DocumentResponse(
            id=uuid.uuid4(),
            investigation_id=uuid.uuid4(),
            filename="test.pdf",
            size_bytes=1000,
            sha256_checksum="a" * 64,
            status="complete",
            page_count=5,
            extraction_confidence=0.4,
            created_at="2026-03-12T00:00:00Z",
            updated_at="2026-03-12T00:00:00Z",
        )
        assert resp.extraction_quality == "medium"

    def test_extraction_quality_low(self):
        from app.schemas.document import DocumentResponse

        resp = DocumentResponse(
            id=uuid.uuid4(),
            investigation_id=uuid.uuid4(),
            filename="test.pdf",
            size_bytes=1000,
            sha256_checksum="a" * 64,
            status="complete",
            page_count=5,
            extraction_confidence=0.3,
            created_at="2026-03-12T00:00:00Z",
            updated_at="2026-03-12T00:00:00Z",
        )
        assert resp.extraction_quality == "low"

    def test_extraction_quality_none_when_no_confidence(self):
        from app.schemas.document import DocumentResponse

        resp = DocumentResponse(
            id=uuid.uuid4(),
            investigation_id=uuid.uuid4(),
            filename="test.pdf",
            size_bytes=1000,
            sha256_checksum="a" * 64,
            status="queued",
            page_count=None,
            extraction_confidence=None,
            created_at="2026-03-12T00:00:00Z",
            updated_at="2026-03-12T00:00:00Z",
        )
        assert resp.extraction_quality is None

    def test_entity_count_and_extraction_confidence_in_response(self):
        from app.schemas.document import DocumentResponse

        resp = DocumentResponse(
            id=uuid.uuid4(),
            investigation_id=uuid.uuid4(),
            filename="test.pdf",
            size_bytes=1000,
            sha256_checksum="a" * 64,
            status="complete",
            page_count=5,
            entity_count=12,
            extraction_confidence=0.75,
            created_at="2026-03-12T00:00:00Z",
            updated_at="2026-03-12T00:00:00Z",
        )
        assert resp.entity_count == 12
        assert resp.extraction_confidence == 0.75
        assert resp.extraction_quality == "high"

        # Verify these fields appear in serialized output
        data = resp.model_dump()
        assert "entity_count" in data
        assert "extraction_confidence" in data
        assert "extraction_quality" in data
