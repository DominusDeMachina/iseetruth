"""Tests for ChunkingService."""

import uuid
from unittest.mock import MagicMock

import pytest

from app.services.chunking import ChunkingService


@pytest.fixture
def chunking_service():
    return ChunkingService()


@pytest.fixture
def document_id():
    return uuid.uuid4()


@pytest.fixture
def investigation_id():
    return uuid.uuid4()


@pytest.fixture
def mock_session():
    session = MagicMock()
    return session


class TestChunkDocumentMultiPage:
    """Multi-page document with page markers."""

    def test_chunks_multi_page_text(
        self, chunking_service, document_id, investigation_id, mock_session
    ):
        text = (
            "--- Page 1 ---\n"
            + "A" * 800
            + "\n\n--- Page 2 ---\n"
            + "B" * 800
            + "\n\n--- Page 3 ---\n"
            + "C" * 400
        )

        chunks = chunking_service.chunk_document(
            document_id=document_id,
            investigation_id=investigation_id,
            extracted_text=text,
            session=mock_session,
        )

        assert len(chunks) > 1
        # Verify sequential numbering
        for i, chunk in enumerate(chunks):
            assert chunk.sequence_number == i

    def test_page_tracking_preserved(
        self, chunking_service, document_id, investigation_id, mock_session
    ):
        text = (
            "--- Page 1 ---\n"
            + "A" * 500
            + "\n\n--- Page 2 ---\n"
            + "B" * 500
            + "\n\n--- Page 3 ---\n"
            + "C" * 500
        )

        chunks = chunking_service.chunk_document(
            document_id=document_id,
            investigation_id=investigation_id,
            extracted_text=text,
            session=mock_session,
        )

        # First chunk should start on page 1
        assert chunks[0].page_start == 1
        # Last chunk should end on page 3
        assert chunks[-1].page_end == 3

    def test_chunks_have_correct_ids(
        self, chunking_service, document_id, investigation_id, mock_session
    ):
        text = "--- Page 1 ---\n" + "A" * 1500

        chunks = chunking_service.chunk_document(
            document_id=document_id,
            investigation_id=investigation_id,
            extracted_text=text,
            session=mock_session,
        )

        for chunk in chunks:
            assert chunk.document_id == document_id
            assert chunk.investigation_id == investigation_id


class TestChunkDocumentOverlap:
    """Verify overlapping content between consecutive chunks."""

    def test_overlap_between_consecutive_chunks(
        self, chunking_service, document_id, investigation_id, mock_session
    ):
        # Create text that will produce multiple chunks
        text = "--- Page 1 ---\n" + "word " * 500  # ~2500 chars

        chunks = chunking_service.chunk_document(
            document_id=document_id,
            investigation_id=investigation_id,
            extracted_text=text,
            session=mock_session,
        )

        assert len(chunks) >= 2
        # Verify overlap: end of chunk N should overlap with start of chunk N+1
        for i in range(len(chunks) - 1):
            current_end = chunks[i].char_offset_end
            next_start = chunks[i + 1].char_offset_start
            assert next_start < current_end, "Chunks should overlap"


class TestChunkDocumentCharOffsets:
    """Verify character offset accuracy."""

    def test_char_offsets_are_accurate(
        self, chunking_service, document_id, investigation_id, mock_session
    ):
        text = "--- Page 1 ---\n" + "Hello world. " * 200

        chunks = chunking_service.chunk_document(
            document_id=document_id,
            investigation_id=investigation_id,
            extracted_text=text,
            session=mock_session,
        )

        for chunk in chunks:
            # The chunk text should correspond to the offsets in the original text
            assert chunk.char_offset_start >= 0
            assert chunk.char_offset_end > chunk.char_offset_start
            assert chunk.char_offset_end <= len(text)


class TestChunkDocumentSinglePage:
    """Single page document (short text)."""

    def test_single_page_short_text(
        self, chunking_service, document_id, investigation_id, mock_session
    ):
        text = "--- Page 1 ---\nShort document content."

        chunks = chunking_service.chunk_document(
            document_id=document_id,
            investigation_id=investigation_id,
            extracted_text=text,
            session=mock_session,
        )

        assert len(chunks) == 1
        assert chunks[0].page_start == 1
        assert chunks[0].page_end == 1
        assert chunks[0].sequence_number == 0
        assert "Short document content." in chunks[0].text


class TestChunkDocumentEmptyText:
    """Empty or whitespace-only text."""

    def test_empty_text_returns_empty_list(
        self, chunking_service, document_id, investigation_id, mock_session
    ):
        chunks = chunking_service.chunk_document(
            document_id=document_id,
            investigation_id=investigation_id,
            extracted_text="",
            session=mock_session,
        )

        assert chunks == []

    def test_whitespace_only_returns_empty_list(
        self, chunking_service, document_id, investigation_id, mock_session
    ):
        chunks = chunking_service.chunk_document(
            document_id=document_id,
            investigation_id=investigation_id,
            extracted_text="   \n\n  ",
            session=mock_session,
        )

        assert chunks == []


class TestChunkDocumentNoPageMarkers:
    """Text without page markers — should still chunk correctly."""

    def test_no_page_markers_uses_page_one(
        self, chunking_service, document_id, investigation_id, mock_session
    ):
        text = "This is a document without page markers. " * 50

        chunks = chunking_service.chunk_document(
            document_id=document_id,
            investigation_id=investigation_id,
            extracted_text=text,
            session=mock_session,
        )

        assert len(chunks) >= 1
        for chunk in chunks:
            assert chunk.page_start == 1
            assert chunk.page_end == 1


class TestChunkDocumentBulkInsert:
    """Verify chunks are bulk-inserted via session."""

    def test_chunks_added_to_session(
        self, chunking_service, document_id, investigation_id, mock_session
    ):
        text = "--- Page 1 ---\n" + "A" * 500

        chunks = chunking_service.chunk_document(
            document_id=document_id,
            investigation_id=investigation_id,
            extracted_text=text,
            session=mock_session,
        )

        assert len(chunks) >= 1
        mock_session.add_all.assert_called_once()
        mock_session.flush.assert_called_once()
