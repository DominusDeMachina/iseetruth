"""Integration tests for document upload/list/get/delete endpoints."""

import io
import uuid
from unittest.mock import patch

from app.exceptions import DocumentNotFoundError, DocumentNotReadyError
from app.services.investigation import InvestigationNotFoundError


def test_upload_single_pdf_returns_201(
    investigation_client, mock_document_service, sample_investigation_id
):
    pdf_content = b"%PDF-1.4 fake pdf content"
    response = investigation_client.post(
        f"/api/v1/investigations/{sample_investigation_id}/documents",
        files=[("files", ("report.pdf", io.BytesIO(pdf_content), "application/pdf"))],
    )
    assert response.status_code == 201
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["filename"] == "test-report.pdf"
    assert data["items"][0]["status"] == "queued"
    assert data["errors"] == []
    mock_document_service.upload_document.assert_called_once()


def test_upload_multiple_pdfs_returns_201(
    investigation_client, mock_document_service, sample_investigation_id
):
    pdf_content = b"%PDF-1.4 fake pdf content"
    response = investigation_client.post(
        f"/api/v1/investigations/{sample_investigation_id}/documents",
        files=[
            ("files", ("report1.pdf", io.BytesIO(pdf_content), "application/pdf")),
            ("files", ("report2.pdf", io.BytesIO(pdf_content), "application/pdf")),
        ],
    )
    assert response.status_code == 201
    data = response.json()
    assert len(data["items"]) == 2


def test_upload_non_pdf_rejected_422(
    investigation_client, mock_document_service, sample_investigation_id
):
    response = investigation_client.post(
        f"/api/v1/investigations/{sample_investigation_id}/documents",
        files=[("files", ("image.png", io.BytesIO(b"PNG data"), "image/png"))],
    )
    assert response.status_code == 422
    data = response.json()
    assert data["type"] == "urn:osint:error:invalid_file_type"


def test_upload_invalid_magic_bytes_rejected_422(
    investigation_client, mock_document_service, sample_investigation_id
):
    """File with PDF MIME type but non-PDF magic bytes should be rejected."""
    fake_pdf = b"NOT_A_PDF_FILE_CONTENT"
    response = investigation_client.post(
        f"/api/v1/investigations/{sample_investigation_id}/documents",
        files=[("files", ("fake.pdf", io.BytesIO(fake_pdf), "application/pdf"))],
    )
    assert response.status_code == 422
    data = response.json()
    assert "invalid PDF magic bytes" in data["detail"]


def test_upload_oversized_file_rejected_422(
    investigation_client, mock_document_service, sample_investigation_id
):
    """File exceeding MAX_FILE_SIZE should be rejected."""
    pdf_content = b"%PDF-1.4 " + b"x" * 100
    with patch("app.api.v1.documents.MAX_FILE_SIZE", 50):
        response = investigation_client.post(
            f"/api/v1/investigations/{sample_investigation_id}/documents",
            files=[("files", ("big.pdf", io.BytesIO(pdf_content), "application/pdf"))],
        )
    assert response.status_code == 422
    data = response.json()
    assert "200 MB limit" in data["detail"]


def test_upload_mixed_valid_and_invalid_files(
    investigation_client, mock_document_service, sample_investigation_id
):
    """Mix of valid PDFs and non-PDFs returns 201 with items and errors."""
    pdf_content = b"%PDF-1.4 valid pdf"
    response = investigation_client.post(
        f"/api/v1/investigations/{sample_investigation_id}/documents",
        files=[
            ("files", ("valid.pdf", io.BytesIO(pdf_content), "application/pdf")),
            ("files", ("image.png", io.BytesIO(b"PNG data"), "image/png")),
        ],
    )
    assert response.status_code == 201
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["filename"] == "test-report.pdf"
    assert len(data["errors"]) == 1
    assert "image.png" in data["errors"][0]


def test_list_documents_returns_200(
    investigation_client, mock_document_service, sample_investigation_id
):
    response = investigation_client.get(
        f"/api/v1/investigations/{sample_investigation_id}/documents"
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["filename"] == "test-report.pdf"


def test_get_document_returns_200(
    investigation_client,
    mock_document_service,
    sample_investigation_id,
    sample_document_id,
):
    response = investigation_client.get(
        f"/api/v1/investigations/{sample_investigation_id}/documents/{sample_document_id}"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(sample_document_id)
    assert data["filename"] == "test-report.pdf"


def test_get_document_not_found_returns_404(
    investigation_client, mock_document_service, sample_investigation_id
):
    not_found_id = uuid.UUID("99999999-9999-9999-9999-999999999999")
    mock_document_service.get_document.side_effect = DocumentNotFoundError(
        str(not_found_id)
    )
    response = investigation_client.get(
        f"/api/v1/investigations/{sample_investigation_id}/documents/{not_found_id}"
    )
    assert response.status_code == 404
    data = response.json()
    assert data["type"] == "urn:osint:error:document_not_found"


def test_delete_document_returns_204(
    investigation_client,
    mock_document_service,
    sample_investigation_id,
    sample_document_id,
):
    response = investigation_client.delete(
        f"/api/v1/investigations/{sample_investigation_id}/documents/{sample_document_id}"
    )
    assert response.status_code == 204
    mock_document_service.delete_document.assert_called_once_with(
        sample_investigation_id, sample_document_id
    )


def test_delete_document_not_found_returns_404(
    investigation_client, mock_document_service, sample_investigation_id
):
    not_found_id = uuid.UUID("99999999-9999-9999-9999-999999999999")
    mock_document_service.delete_document.side_effect = DocumentNotFoundError(
        str(not_found_id)
    )
    response = investigation_client.delete(
        f"/api/v1/investigations/{sample_investigation_id}/documents/{not_found_id}"
    )
    assert response.status_code == 404
    data = response.json()
    assert data["type"] == "urn:osint:error:document_not_found"


# ---------------------------------------------------------------------------
# GET /documents/{document_id}/text
# ---------------------------------------------------------------------------


def test_get_document_text_returns_200(
    investigation_client,
    mock_document_service,
    sample_investigation_id,
    sample_document_id,
    sample_document,
):
    """Complete document should return extracted text."""
    sample_document.status = "complete"
    sample_document.extracted_text = "--- Page 1 ---\nSome text"
    sample_document.page_count = 1

    response = investigation_client.get(
        f"/api/v1/investigations/{sample_investigation_id}/documents/{sample_document_id}/text"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["document_id"] == str(sample_document_id)
    assert data["filename"] == "test-report.pdf"
    assert data["page_count"] == 1
    assert data["extracted_text"] == "--- Page 1 ---\nSome text"
    assert data["status"] == "complete"


def test_get_document_text_null_text_returns_200(
    investigation_client,
    mock_document_service,
    sample_investigation_id,
    sample_document_id,
    sample_document,
):
    """Complete document with null extracted_text should return 200 with null."""
    sample_document.status = "complete"
    sample_document.extracted_text = None
    sample_document.page_count = 3

    response = investigation_client.get(
        f"/api/v1/investigations/{sample_investigation_id}/documents/{sample_document_id}/text"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["document_id"] == str(sample_document_id)
    assert data["extracted_text"] is None


def test_get_document_text_not_found_returns_404(
    investigation_client,
    mock_document_service,
    sample_investigation_id,
):
    """Missing document should return 404."""
    not_found_id = uuid.UUID("99999999-9999-9999-9999-999999999999")
    mock_document_service.get_document.side_effect = DocumentNotFoundError(
        str(not_found_id)
    )
    response = investigation_client.get(
        f"/api/v1/investigations/{sample_investigation_id}/documents/{not_found_id}/text"
    )
    assert response.status_code == 404
    data = response.json()
    assert data["type"] == "urn:osint:error:document_not_found"


def test_get_document_text_not_complete_returns_409(
    investigation_client,
    mock_document_service,
    sample_investigation_id,
    sample_document_id,
    sample_document,
):
    """Non-complete document should return 409 Conflict."""
    sample_document.status = "extracting_text"

    response = investigation_client.get(
        f"/api/v1/investigations/{sample_investigation_id}/documents/{sample_document_id}/text"
    )
    assert response.status_code == 409
    data = response.json()
    assert data["type"] == "urn:osint:error:document_not_ready"


def test_get_document_text_queued_returns_409(
    investigation_client,
    mock_document_service,
    sample_investigation_id,
    sample_document_id,
    sample_document,
):
    """Queued document should return 409 Conflict."""
    sample_document.status = "queued"

    response = investigation_client.get(
        f"/api/v1/investigations/{sample_investigation_id}/documents/{sample_document_id}/text"
    )
    assert response.status_code == 409
    data = response.json()
    assert data["type"] == "urn:osint:error:document_not_ready"


def test_get_document_text_failed_returns_409(
    investigation_client,
    mock_document_service,
    sample_investigation_id,
    sample_document_id,
    sample_document,
):
    """Failed document should return 409 Conflict."""
    sample_document.status = "failed"

    response = investigation_client.get(
        f"/api/v1/investigations/{sample_investigation_id}/documents/{sample_document_id}/text"
    )
    assert response.status_code == 409
    data = response.json()
    assert data["type"] == "urn:osint:error:document_not_ready"
