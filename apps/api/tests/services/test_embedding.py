import uuid
from unittest.mock import MagicMock

import pytest

from app.db.qdrant import COLLECTION_NAME
from app.exceptions import OllamaUnavailableError
from app.services.embedding import EmbeddingService, EmbeddingSummary


@pytest.fixture
def mock_embedding_client():
    client = MagicMock()
    client.embed.return_value = [0.1] * 4096
    return client


@pytest.fixture
def mock_qdrant_client():
    return MagicMock()


@pytest.fixture
def make_chunk():
    def _make(text="Test chunk text", page_start=1, page_end=1):
        chunk = MagicMock()
        chunk.id = uuid.uuid4()
        chunk.document_id = uuid.uuid4()
        chunk.text = text
        chunk.page_start = page_start
        chunk.page_end = page_end
        return chunk

    return _make


def test_embed_chunks_generates_and_upserts(mock_embedding_client, mock_qdrant_client, make_chunk):
    investigation_id = uuid.uuid4()
    chunk = make_chunk()
    service = EmbeddingService(mock_embedding_client, mock_qdrant_client)

    summary = service.embed_chunks([chunk], investigation_id)

    mock_embedding_client.embed.assert_called_once_with(chunk.text)
    mock_qdrant_client.upsert.assert_called_once()
    call_kwargs = mock_qdrant_client.upsert.call_args
    assert call_kwargs.kwargs["collection_name"] == COLLECTION_NAME
    point = call_kwargs.kwargs["points"][0]
    assert point.id == str(chunk.id)
    assert point.vector == [0.1] * 4096
    assert point.payload["investigation_id"] == str(investigation_id)
    assert point.payload["chunk_id"] == str(chunk.id)
    assert point.payload["document_id"] == str(chunk.document_id)


def test_embed_chunks_returns_summary(mock_embedding_client, mock_qdrant_client, make_chunk):
    chunks = [make_chunk(), make_chunk()]
    service = EmbeddingService(mock_embedding_client, mock_qdrant_client)
    summary = service.embed_chunks(chunks, uuid.uuid4())
    assert summary.embedded_count == 2
    assert summary.failed_count == 0
    assert summary.chunk_count == 2


def test_embed_chunks_per_chunk_failure_continues(
    mock_embedding_client, mock_qdrant_client, make_chunk
):
    chunk1, chunk2 = make_chunk(), make_chunk()
    mock_embedding_client.embed.side_effect = [OllamaUnavailableError("timeout"), [0.1] * 4096]
    service = EmbeddingService(mock_embedding_client, mock_qdrant_client)
    summary = service.embed_chunks([chunk1, chunk2], uuid.uuid4())
    assert summary.failed_count == 1
    assert summary.embedded_count == 1
    mock_qdrant_client.upsert.assert_called_once()


def test_embed_chunks_empty_list(mock_embedding_client, mock_qdrant_client):
    service = EmbeddingService(mock_embedding_client, mock_qdrant_client)
    summary = service.embed_chunks([], uuid.uuid4())
    assert summary.chunk_count == 0
    assert summary.embedded_count == 0
    mock_embedding_client.embed.assert_not_called()
    mock_qdrant_client.upsert.assert_not_called()


def test_payload_contains_investigation_id(mock_embedding_client, mock_qdrant_client, make_chunk):
    investigation_id = uuid.uuid4()
    chunk = make_chunk()
    service = EmbeddingService(mock_embedding_client, mock_qdrant_client)
    service.embed_chunks([chunk], investigation_id)
    point = mock_qdrant_client.upsert.call_args.kwargs["points"][0]
    assert point.payload["investigation_id"] == str(investigation_id)


def test_text_excerpt_truncated_to_500(mock_embedding_client, mock_qdrant_client, make_chunk):
    long_text = "x" * 700
    chunk = make_chunk(text=long_text)
    service = EmbeddingService(mock_embedding_client, mock_qdrant_client)
    service.embed_chunks([chunk], uuid.uuid4())
    point = mock_qdrant_client.upsert.call_args.kwargs["points"][0]
    assert len(point.payload["text_excerpt"]) == 500
