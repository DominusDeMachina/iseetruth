"""Integration tests for GET /api/v1/investigations/{id}/chunks/{chunk_id} endpoint."""

import uuid

from app.exceptions import ChunkNotFoundError


def test_get_chunk_with_context_returns_200(
    investigation_client,
    mock_chunk_service,
    sample_investigation_id,
    sample_chunk_id,
):
    response = investigation_client.get(
        f"/api/v1/investigations/{sample_investigation_id}/chunks/{sample_chunk_id}"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["chunk_id"] == str(sample_chunk_id)
    assert data["document_filename"] == "test-report.pdf"
    assert data["sequence_number"] == 5
    assert data["total_chunks"] == 20
    assert data["text"] == "Deputy Mayor Horvat signed the contract."
    assert data["page_start"] == 3
    assert data["page_end"] == 3
    assert data["context_before"] == "Previous paragraph text."
    assert data["context_after"] == "Next paragraph text."
    mock_chunk_service.get_chunk_with_context.assert_called_once_with(
        sample_investigation_id, sample_chunk_id
    )


def test_get_chunk_not_found_returns_404(
    investigation_client,
    mock_chunk_service,
    sample_investigation_id,
):
    not_found_id = uuid.UUID("99999999-9999-9999-9999-999999999999")
    mock_chunk_service.get_chunk_with_context.side_effect = ChunkNotFoundError(
        str(not_found_id)
    )
    response = investigation_client.get(
        f"/api/v1/investigations/{sample_investigation_id}/chunks/{not_found_id}"
    )
    assert response.status_code == 404
    data = response.json()
    assert data["type"] == "urn:osint:error:chunk_not_found"
    assert data["status"] == 404


def test_get_chunk_cross_investigation_returns_404(
    investigation_client,
    mock_chunk_service,
    sample_chunk_id,
):
    """Chunk belonging to different investigation should return 404."""
    wrong_investigation_id = uuid.UUID("88888888-8888-8888-8888-888888888888")
    mock_chunk_service.get_chunk_with_context.side_effect = ChunkNotFoundError(
        str(sample_chunk_id)
    )
    response = investigation_client.get(
        f"/api/v1/investigations/{wrong_investigation_id}/chunks/{sample_chunk_id}"
    )
    assert response.status_code == 404
    data = response.json()
    assert data["type"] == "urn:osint:error:chunk_not_found"


def test_get_chunk_invalid_uuid_returns_422(
    investigation_client,
    mock_chunk_service,
    sample_investigation_id,
):
    response = investigation_client.get(
        f"/api/v1/investigations/{sample_investigation_id}/chunks/not-a-uuid"
    )
    assert response.status_code == 422
