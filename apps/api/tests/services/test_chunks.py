"""Unit tests for ChunkService.get_chunk_with_context."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.exceptions import ChunkNotFoundError
from app.models.chunk import DocumentChunk
from app.services.chunk import ChunkService


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def investigation_id():
    return uuid.UUID("11111111-1111-1111-1111-111111111111")


@pytest.fixture
def document_id():
    return uuid.UUID("22222222-2222-2222-2222-222222222222")


@pytest.fixture
def chunk_id():
    return uuid.UUID("33333333-3333-3333-3333-333333333333")


def _make_chunk(chunk_id, document_id, investigation_id, sequence_number=5):
    """Create a mock DocumentChunk."""
    chunk = MagicMock(spec=DocumentChunk)
    chunk.id = chunk_id
    chunk.document_id = document_id
    chunk.investigation_id = investigation_id
    chunk.sequence_number = sequence_number
    chunk.text = "Deputy Mayor Horvat signed the contract."
    chunk.page_start = 3
    chunk.page_end = 3
    return chunk


@pytest.mark.asyncio
async def test_get_chunk_with_context_happy_path(
    mock_db, investigation_id, document_id, chunk_id
):
    chunk = _make_chunk(chunk_id, document_id, investigation_id, sequence_number=5)

    # Mock: fetch chunk
    chunk_result = MagicMock()
    chunk_result.scalar_one_or_none.return_value = chunk

    # Mock: fetch document filename
    filename_result = MagicMock()
    filename_result.scalar_one.return_value = "contract-award-089.pdf"

    # Mock: count total chunks
    count_result = MagicMock()
    count_result.scalar_one.return_value = 20

    # Mock: fetch context_before (previous chunk)
    prev_result = MagicMock()
    prev_result.scalar_one_or_none.return_value = "Previous chunk text."

    # Mock: fetch context_after (next chunk)
    next_result = MagicMock()
    next_result.scalar_one_or_none.return_value = "Next chunk text."

    mock_db.execute = AsyncMock(
        side_effect=[chunk_result, filename_result, count_result, prev_result, next_result]
    )

    service = ChunkService(mock_db)
    result = await service.get_chunk_with_context(investigation_id, chunk_id)

    assert result.chunk_id == chunk_id
    assert result.document_id == document_id
    assert result.document_filename == "contract-award-089.pdf"
    assert result.sequence_number == 5
    assert result.total_chunks == 20
    assert result.text == "Deputy Mayor Horvat signed the contract."
    assert result.page_start == 3
    assert result.page_end == 3
    assert result.context_before == "Previous chunk text."
    assert result.context_after == "Next chunk text."


@pytest.mark.asyncio
async def test_get_chunk_not_found_raises_error(mock_db, investigation_id, chunk_id):
    """Chunk not found should raise ChunkNotFoundError."""
    chunk_result = MagicMock()
    chunk_result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=chunk_result)

    service = ChunkService(mock_db)
    with pytest.raises(ChunkNotFoundError):
        await service.get_chunk_with_context(investigation_id, chunk_id)


@pytest.mark.asyncio
async def test_get_chunk_cross_investigation_raises_error(
    mock_db, document_id, chunk_id
):
    """Chunk with wrong investigation_id should raise ChunkNotFoundError."""
    wrong_investigation_id = uuid.UUID("99999999-9999-9999-9999-999999999999")
    # The WHERE clause filters by investigation_id, so no match found
    chunk_result = MagicMock()
    chunk_result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=chunk_result)

    service = ChunkService(mock_db)
    with pytest.raises(ChunkNotFoundError):
        await service.get_chunk_with_context(wrong_investigation_id, chunk_id)


@pytest.mark.asyncio
async def test_first_chunk_has_no_context_before(
    mock_db, investigation_id, document_id, chunk_id
):
    """First chunk (sequence_number=0) should have context_before=None."""
    chunk = _make_chunk(chunk_id, document_id, investigation_id, sequence_number=0)

    chunk_result = MagicMock()
    chunk_result.scalar_one_or_none.return_value = chunk

    filename_result = MagicMock()
    filename_result.scalar_one.return_value = "report.pdf"

    count_result = MagicMock()
    count_result.scalar_one.return_value = 10

    # No previous chunk query (sequence_number=0 skips it)
    # Only context_after query
    next_result = MagicMock()
    next_result.scalar_one_or_none.return_value = "Second chunk text."

    mock_db.execute = AsyncMock(
        side_effect=[chunk_result, filename_result, count_result, next_result]
    )

    service = ChunkService(mock_db)
    result = await service.get_chunk_with_context(investigation_id, chunk_id)

    assert result.context_before is None
    assert result.context_after == "Second chunk text."
    assert result.sequence_number == 0


@pytest.mark.asyncio
async def test_last_chunk_has_no_context_after(
    mock_db, investigation_id, document_id, chunk_id
):
    """Last chunk should have context_after=None."""
    chunk = _make_chunk(chunk_id, document_id, investigation_id, sequence_number=9)

    chunk_result = MagicMock()
    chunk_result.scalar_one_or_none.return_value = chunk

    filename_result = MagicMock()
    filename_result.scalar_one.return_value = "report.pdf"

    count_result = MagicMock()
    count_result.scalar_one.return_value = 10

    prev_result = MagicMock()
    prev_result.scalar_one_or_none.return_value = "Previous chunk text."

    # Last chunk: next chunk doesn't exist
    next_result = MagicMock()
    next_result.scalar_one_or_none.return_value = None

    mock_db.execute = AsyncMock(
        side_effect=[chunk_result, filename_result, count_result, prev_result, next_result]
    )

    service = ChunkService(mock_db)
    result = await service.get_chunk_with_context(investigation_id, chunk_id)

    assert result.context_before == "Previous chunk text."
    assert result.context_after is None
    assert result.sequence_number == 9


@pytest.mark.asyncio
async def test_duplicate_adjacent_chunks_does_not_crash(
    mock_db, investigation_id, document_id, chunk_id
):
    """Duplicate sequence numbers (e.g. reprocessed doc) should not raise MultipleResultsFound."""
    chunk = _make_chunk(chunk_id, document_id, investigation_id, sequence_number=5)

    chunk_result = MagicMock()
    chunk_result.scalar_one_or_none.return_value = chunk

    filename_result = MagicMock()
    filename_result.scalar_one.return_value = "report.pdf"

    count_result = MagicMock()
    count_result.scalar_one.return_value = 20

    # Adjacent chunk queries return one row thanks to .limit(1)
    prev_result = MagicMock()
    prev_result.scalar_one_or_none.return_value = "Previous text."

    next_result = MagicMock()
    next_result.scalar_one_or_none.return_value = "Next text."

    mock_db.execute = AsyncMock(
        side_effect=[chunk_result, filename_result, count_result, prev_result, next_result]
    )

    service = ChunkService(mock_db)
    result = await service.get_chunk_with_context(investigation_id, chunk_id)

    assert result.context_before == "Previous text."
    assert result.context_after == "Next text."
