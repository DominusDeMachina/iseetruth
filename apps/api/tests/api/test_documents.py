"""Integration tests for document upload/list/get/delete endpoints."""

import io
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from app.exceptions import DocumentNotFoundError, DocumentNotReadyError, DocumentNotRetryableError
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


def test_upload_unsupported_type_rejected_422(
    investigation_client, mock_document_service, sample_investigation_id
):
    response = investigation_client.post(
        f"/api/v1/investigations/{sample_investigation_id}/documents",
        files=[("files", ("notes.txt", io.BytesIO(b"plain text"), "text/plain"))],
    )
    assert response.status_code == 422
    data = response.json()
    assert data["type"] == "urn:osint:error:invalid_file_type"
    assert "Accepted: PDF, JPEG, PNG, TIFF" in data["detail"]


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
    assert "invalid file magic bytes" in data["detail"]


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
    """Mix of valid files and unsupported types returns 201 with items and errors."""
    pdf_content = b"%PDF-1.4 valid pdf"
    response = investigation_client.post(
        f"/api/v1/investigations/{sample_investigation_id}/documents",
        files=[
            ("files", ("valid.pdf", io.BytesIO(pdf_content), "application/pdf")),
            ("files", ("notes.txt", io.BytesIO(b"plain text"), "text/plain")),
        ],
    )
    assert response.status_code == 201
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["filename"] == "test-report.pdf"
    assert len(data["errors"]) == 1
    assert "notes.txt" in data["errors"][0]


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


def test_get_document_includes_ocr_confidence_fields(
    investigation_client,
    mock_document_service,
    sample_investigation_id,
    sample_document_id,
    sample_document,
):
    """Document response includes ocr_confidence and computed ocr_quality."""
    sample_document.document_type = "image"
    sample_document.ocr_confidence = 0.85
    sample_document.status = "complete"
    response = investigation_client.get(
        f"/api/v1/investigations/{sample_investigation_id}/documents/{sample_document_id}"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ocr_confidence"] == 0.85
    assert data["ocr_quality"] == "high"


def test_get_document_ocr_quality_none_when_no_confidence(
    investigation_client,
    mock_document_service,
    sample_investigation_id,
    sample_document_id,
    sample_document,
):
    """ocr_quality is None when ocr_confidence is None (e.g., PDF documents)."""
    sample_document.ocr_confidence = None
    response = investigation_client.get(
        f"/api/v1/investigations/{sample_investigation_id}/documents/{sample_document_id}"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ocr_confidence"] is None
    assert data["ocr_quality"] is None


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


# ---------------------------------------------------------------------------
# POST /documents/{document_id}/retry
# ---------------------------------------------------------------------------


def test_retry_failed_document_returns_200(
    investigation_client,
    mock_document_service,
    sample_investigation_id,
    sample_document_id,
    sample_document,
):
    """Retry on failed document should return 200 with reset status."""
    sample_document.status = "queued"
    sample_document.error_message = None
    sample_document.failed_stage = None
    mock_document_service.retry_failed_document = AsyncMock(return_value=sample_document)

    response = investigation_client.post(
        f"/api/v1/investigations/{sample_investigation_id}/documents/{sample_document_id}/retry"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "queued"
    assert data["error_message"] is None
    mock_document_service.retry_failed_document.assert_called_once_with(
        sample_investigation_id, sample_document_id
    )


def test_retry_non_failed_document_returns_409(
    investigation_client,
    mock_document_service,
    sample_investigation_id,
    sample_document_id,
):
    """Retry on document not in 'failed' status should return 409."""
    mock_document_service.retry_failed_document.side_effect = DocumentNotRetryableError(
        str(sample_document_id), "complete"
    )
    response = investigation_client.post(
        f"/api/v1/investigations/{sample_investigation_id}/documents/{sample_document_id}/retry"
    )
    assert response.status_code == 409
    data = response.json()
    assert data["type"] == "urn:osint:error:document_not_retryable"


def test_retry_nonexistent_document_returns_404(
    investigation_client,
    mock_document_service,
    sample_investigation_id,
):
    """Retry on non-existent document should return 404."""
    not_found_id = uuid.UUID("99999999-9999-9999-9999-999999999999")
    mock_document_service.retry_failed_document.side_effect = DocumentNotFoundError(
        str(not_found_id)
    )
    response = investigation_client.post(
        f"/api/v1/investigations/{sample_investigation_id}/documents/{not_found_id}/retry"
    )
    assert response.status_code == 404
    data = response.json()
    assert data["type"] == "urn:osint:error:document_not_found"


def test_retry_document_wrong_investigation_returns_404(
    investigation_client,
    mock_document_service,
    sample_document_id,
):
    """Retry on document from different investigation should return 404."""
    wrong_investigation = uuid.UUID("88888888-8888-8888-8888-888888888888")
    mock_document_service.retry_failed_document.side_effect = DocumentNotFoundError(
        str(sample_document_id)
    )
    response = investigation_client.post(
        f"/api/v1/investigations/{wrong_investigation}/documents/{sample_document_id}/retry"
    )
    assert response.status_code == 404
    data = response.json()
    assert data["type"] == "urn:osint:error:document_not_found"


# ---------------------------------------------------------------------------
# Image upload tests (Story 7.1)
# ---------------------------------------------------------------------------


def _make_image_document(sample_document, **overrides):
    """Return sample_document with image-specific defaults applied."""
    sample_document.document_type = overrides.get("document_type", "image")
    sample_document.filename = overrides.get("filename", "scan.jpg")
    sample_document.page_count = overrides.get("page_count", 1)
    for k, v in overrides.items():
        setattr(sample_document, k, v)
    return sample_document


def test_upload_jpeg_returns_201_with_image_type(
    investigation_client, mock_document_service, sample_investigation_id, sample_document
):
    """Upload JPEG file returns 201 with document_type: image."""
    _make_image_document(sample_document)
    jpeg_content = b"\xff\xd8\xff\xe0 fake jpeg content"
    response = investigation_client.post(
        f"/api/v1/investigations/{sample_investigation_id}/documents",
        files=[("files", ("scan.jpg", io.BytesIO(jpeg_content), "image/jpeg"))],
    )
    assert response.status_code == 201
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["document_type"] == "image"
    mock_document_service.upload_document.assert_called_once()
    call_kwargs = mock_document_service.upload_document.call_args
    assert call_kwargs.kwargs.get("document_type") == "image" or (
        len(call_kwargs.args) >= 3 and call_kwargs.args[2] == "image"
    )


def test_upload_png_returns_201_with_image_type(
    investigation_client, mock_document_service, sample_investigation_id, sample_document
):
    """Upload PNG file returns 201 with document_type: image."""
    _make_image_document(sample_document, filename="screenshot.png")
    # PNG magic bytes: \x89PNG
    png_content = b"\x89PNG\r\n\x1a\n fake png content"
    response = investigation_client.post(
        f"/api/v1/investigations/{sample_investigation_id}/documents",
        files=[("files", ("screenshot.png", io.BytesIO(png_content), "image/png"))],
    )
    assert response.status_code == 201
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["document_type"] == "image"


def test_upload_tiff_le_returns_201_with_image_type(
    investigation_client, mock_document_service, sample_investigation_id, sample_document
):
    """Upload TIFF (little-endian) file returns 201 with document_type: image."""
    _make_image_document(sample_document, filename="scan.tiff")
    # TIFF little-endian magic bytes: II\x2a\x00
    tiff_content = b"II\x2a\x00 fake tiff content"
    response = investigation_client.post(
        f"/api/v1/investigations/{sample_investigation_id}/documents",
        files=[("files", ("scan.tiff", io.BytesIO(tiff_content), "image/tiff"))],
    )
    assert response.status_code == 201
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["document_type"] == "image"


def test_upload_tiff_be_returns_201_with_image_type(
    investigation_client, mock_document_service, sample_investigation_id, sample_document
):
    """Upload TIFF (big-endian) file returns 201 with document_type: image."""
    _make_image_document(sample_document, filename="scan.tif")
    # TIFF big-endian magic bytes: MM\x00\x2a
    tiff_content = b"MM\x00\x2a fake tiff content"
    response = investigation_client.post(
        f"/api/v1/investigations/{sample_investigation_id}/documents",
        files=[("files", ("scan.tif", io.BytesIO(tiff_content), "image/tiff"))],
    )
    assert response.status_code == 201
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["document_type"] == "image"


def test_upload_unsupported_txt_rejected_422(
    investigation_client, mock_document_service, sample_investigation_id
):
    """Upload .txt file returns 422 with RFC 7807 error."""
    response = investigation_client.post(
        f"/api/v1/investigations/{sample_investigation_id}/documents",
        files=[("files", ("notes.txt", io.BytesIO(b"plain text"), "text/plain"))],
    )
    assert response.status_code == 422
    data = response.json()
    assert data["type"] == "urn:osint:error:invalid_file_type"
    assert "Accepted: PDF, JPEG, PNG, TIFF" in data["detail"]


def test_upload_mixed_pdf_and_jpeg(
    investigation_client, mock_document_service, sample_investigation_id, sample_document
):
    """Mixed upload of 1 PDF + 1 JPEG returns 201 with correct types."""
    # First call returns PDF doc, second returns image doc
    pdf_doc = MagicMock()
    pdf_doc.id = sample_document.id
    pdf_doc.investigation_id = sample_document.investigation_id
    pdf_doc.filename = "report.pdf"
    pdf_doc.size_bytes = 1024
    pdf_doc.sha256_checksum = "a" * 64
    pdf_doc.document_type = "pdf"
    pdf_doc.source_url = None
    pdf_doc.status = "queued"
    pdf_doc.page_count = 5
    pdf_doc.entity_count = None
    pdf_doc.extraction_confidence = None
    pdf_doc.extracted_text = None
    pdf_doc.ocr_method = None
    pdf_doc.error_message = None
    pdf_doc.failed_stage = None
    pdf_doc.retry_count = 0
    pdf_doc.created_at = sample_document.created_at
    pdf_doc.updated_at = sample_document.updated_at

    img_doc = MagicMock()
    img_doc.id = uuid.uuid4()
    img_doc.investigation_id = sample_document.investigation_id
    img_doc.filename = "scan.jpg"
    img_doc.size_bytes = 2048
    img_doc.sha256_checksum = "b" * 64
    img_doc.document_type = "image"
    img_doc.source_url = None
    img_doc.status = "queued"
    img_doc.page_count = 1
    img_doc.entity_count = None
    img_doc.extraction_confidence = None
    img_doc.extracted_text = None
    img_doc.ocr_method = None
    img_doc.error_message = None
    img_doc.failed_stage = None
    img_doc.retry_count = 0
    img_doc.created_at = sample_document.created_at
    img_doc.updated_at = sample_document.updated_at

    mock_document_service.upload_document = AsyncMock(side_effect=[pdf_doc, img_doc])

    pdf_content = b"%PDF-1.4 fake pdf"
    jpeg_content = b"\xff\xd8\xff\xe0 fake jpeg"
    response = investigation_client.post(
        f"/api/v1/investigations/{sample_investigation_id}/documents",
        files=[
            ("files", ("report.pdf", io.BytesIO(pdf_content), "application/pdf")),
            ("files", ("scan.jpg", io.BytesIO(jpeg_content), "image/jpeg")),
        ],
    )
    assert response.status_code == 201
    data = response.json()
    assert len(data["items"]) == 2
    types = {item["document_type"] for item in data["items"]}
    assert types == {"pdf", "image"}


# ---------------------------------------------------------------------------
# ImageExtractionService unit tests
# ---------------------------------------------------------------------------


def test_image_extraction_service_returns_text_with_page_marker():
    """ImageExtractionService wraps OCR text in page marker format and returns confidence."""
    with patch("app.services.image_extraction.Image") as mock_pil, \
         patch("app.services.image_extraction.pytesseract") as mock_tess:
        # Mock image dimensions for quality assessment
        mock_img = MagicMock()
        mock_img.width = 1000
        mock_img.height = 1000
        mock_img.__enter__ = MagicMock(return_value=mock_img)
        mock_img.__exit__ = MagicMock(return_value=False)
        mock_pil.open.return_value = mock_img
        mock_tess.image_to_string.return_value = "Hello World"

        from app.services.image_extraction import ImageExtractionService
        from pathlib import Path

        service = ImageExtractionService()
        text, method, confidence = service.extract_text(Path("/fake/image.jpg"), document_id="test-id")

        assert text == "--- Page 1 ---\nHello World"
        assert method == "tesseract"
        assert isinstance(confidence, float)
        assert 0.0 <= confidence <= 1.0


def test_image_extraction_service_empty_ocr_returns_empty_string():
    """Empty OCR result returns empty string with 0.0 confidence."""
    with patch("app.services.image_extraction.Image") as mock_pil, \
         patch("app.services.image_extraction.pytesseract") as mock_tess:
        mock_img = MagicMock()
        mock_img.width = 800
        mock_img.height = 600
        mock_img.__enter__ = MagicMock(return_value=mock_img)
        mock_img.__exit__ = MagicMock(return_value=False)
        mock_pil.open.return_value = mock_img
        mock_tess.image_to_string.return_value = "   \n  "

        from app.services.image_extraction import ImageExtractionService
        from pathlib import Path

        service = ImageExtractionService()
        text, method, confidence = service.extract_text(Path("/fake/blank.png"), document_id="test-id")

        assert text == ""
        assert method == "tesseract"
        assert confidence == 0.0


def test_process_document_routes_image_to_ocr():
    """process_document_task routes image documents to ImageExtractionService."""
    with patch("app.worker.tasks.process_document.SyncSessionLocal") as mock_session_cls, \
         patch("app.worker.tasks.process_document.ImageExtractionService") as mock_img_svc, \
         patch("app.worker.tasks.process_document.TextExtractionService") as mock_txt_svc, \
         patch("app.worker.tasks.process_document.get_settings") as mock_settings, \
         patch("app.worker.tasks.process_document.OllamaClient") as mock_ollama_cls, \
         patch("app.worker.tasks.process_document.OllamaEmbeddingClient"), \
         patch("app.worker.tasks.process_document.EventPublisher") as mock_pub_cls, \
         patch("app.worker.tasks.process_document.celery_app"), \
         patch("app.worker.tasks.process_document.ChunkingService") as mock_chunk_svc, \
         patch("app.worker.tasks.process_document.EntityExtractionService") as mock_extract_svc, \
         patch("app.worker.tasks.process_document.EmbeddingService") as mock_embed_svc, \
         patch("app.worker.tasks.process_document.EMBEDDING_MODEL", "test-model"), \
         patch("neo4j.GraphDatabase") as mock_neo4j, \
         patch("qdrant_client.QdrantClient") as mock_qdrant, \
         patch("app.db.qdrant.ensure_qdrant_collection"):

        # Setup settings
        settings = MagicMock()
        settings.neo4j_uri = "bolt://localhost:7687"
        settings.neo4j_auth = "neo4j/password"
        settings.qdrant_url = "http://localhost:6333"
        settings.celery_broker_url = "redis://localhost:6379/0"
        settings.ollama_base_url = "http://localhost:11434"
        settings.ollama_embedding_url = "http://localhost:11434"
        mock_settings.return_value = settings

        # Setup session
        mock_session = MagicMock()
        mock_session_cls.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_session_cls.return_value.__exit__ = MagicMock(return_value=False)

        # Setup document
        doc = MagicMock()
        doc.document_type = "image"
        doc.filename = "scan.jpg"
        doc.investigation_id = "inv-123"
        doc.id = "doc-456"
        doc.extracted_text = None
        mock_session.get.return_value = doc

        # Setup Ollama
        ollama_instance = MagicMock()
        ollama_instance.check_available.return_value = True
        mock_ollama_cls.return_value = ollama_instance

        # Setup publisher
        mock_publisher = MagicMock()
        mock_pub_cls.return_value = mock_publisher

        # Setup neo4j
        mock_neo4j.driver.return_value = MagicMock()

        # Setup extraction service to return text + method + confidence tuple
        mock_img_instance = MagicMock()
        mock_img_instance.extract_text.return_value = ("--- Page 1 ---\nExtracted text", "tesseract", 0.75)
        mock_img_svc.return_value = mock_img_instance

        # Setup chunking
        mock_chunk_instance = MagicMock()
        mock_chunk_instance.chunk_document.return_value = []
        mock_chunk_svc.return_value = mock_chunk_instance

        # Setup entity extraction
        mock_extract_instance = MagicMock()
        summary = MagicMock()
        summary.entity_count = 0
        summary.relationship_count = 0
        summary.average_confidence = None
        mock_extract_instance.extract_from_chunks.return_value = summary
        mock_extract_svc.return_value = mock_extract_instance

        # Setup embedding
        mock_embed_instance = MagicMock()
        emb_summary = MagicMock()
        emb_summary.embedded_count = 0
        emb_summary.failed_count = 0
        mock_embed_instance.embed_chunks.return_value = emb_summary
        mock_embed_svc.return_value = mock_embed_instance

        # Import and call - need to reimport to get patched version
        from app.worker.tasks.process_document import process_document_task
        process_document_task("doc-456", "inv-123")

        # Verify ImageExtractionService was used, not TextExtractionService
        mock_img_svc.assert_called_once()
        mock_txt_svc.assert_not_called()


# ---------------------------------------------------------------------------
# POST /documents/capture — web page capture (Story 9.1)
# ---------------------------------------------------------------------------


def test_capture_web_page_returns_201(
    investigation_client,
    mock_db_session,
    sample_investigation_id,
):
    """Capture endpoint with valid URL creates document and returns 201."""
    from datetime import datetime, timezone

    mock_db_session.add = MagicMock()
    mock_db_session.commit = AsyncMock()

    # refresh populates server-generated fields
    async def _refresh(obj, **kwargs):
        obj.created_at = datetime(2026, 4, 12, 0, 0, 0, tzinfo=timezone.utc)
        obj.updated_at = datetime(2026, 4, 12, 0, 0, 0, tzinfo=timezone.utc)

    mock_db_session.refresh = AsyncMock(side_effect=_refresh)

    with patch("app.services.investigation.InvestigationService") as mock_inv_cls, \
         patch("app.worker.tasks.process_document.process_document_task") as mock_task:
        mock_inv_svc = AsyncMock()
        mock_inv_cls.return_value = mock_inv_svc
        mock_inv_svc.get_investigation = AsyncMock()
        mock_task.delay = MagicMock()

        response = investigation_client.post(
            f"/api/v1/investigations/{sample_investigation_id}/documents/capture",
            json={"url": "https://example.com/article"},
        )

    assert response.status_code == 201
    data = response.json()
    assert data["document_type"] == "web"
    assert data["source_url"] == "https://example.com/article"
    assert data["status"] == "queued"
    assert data["filename"] == "example.com"


def test_capture_web_page_invalid_url_returns_422(
    investigation_client,
    mock_db_session,
    sample_investigation_id,
):
    """Capture endpoint with invalid URL returns 422."""
    response = investigation_client.post(
        f"/api/v1/investigations/{sample_investigation_id}/documents/capture",
        json={"url": "not-a-url"},
    )
    assert response.status_code == 422
    data = response.json()
    assert data["type"] == "urn:osint:error:invalid_url"


def test_capture_web_page_empty_url_returns_422(
    investigation_client,
    mock_db_session,
    sample_investigation_id,
):
    """Capture endpoint with empty URL returns 422."""
    response = investigation_client.post(
        f"/api/v1/investigations/{sample_investigation_id}/documents/capture",
        json={"url": ""},
    )
    assert response.status_code == 422
    data = response.json()
    assert data["type"] == "urn:osint:error:invalid_url"


def test_capture_web_page_ftp_scheme_returns_422(
    investigation_client,
    mock_db_session,
    sample_investigation_id,
):
    """Capture endpoint with ftp:// URL returns 422."""
    response = investigation_client.post(
        f"/api/v1/investigations/{sample_investigation_id}/documents/capture",
        json={"url": "ftp://files.example.com/doc.pdf"},
    )
    assert response.status_code == 422
    data = response.json()
    assert data["type"] == "urn:osint:error:invalid_url"
    assert "http or https" in data["detail"]


def test_capture_web_page_investigation_not_found_returns_404(
    investigation_client,
    mock_db_session,
):
    """Capture endpoint with invalid investigation_id returns 404."""
    bad_id = uuid.UUID("99999999-9999-9999-9999-999999999999")
    with patch("app.services.investigation.InvestigationService") as mock_inv_cls:
        mock_inv_svc = AsyncMock()
        mock_inv_cls.return_value = mock_inv_svc
        mock_inv_svc.get_investigation = AsyncMock(
            side_effect=InvestigationNotFoundError(str(bad_id))
        )

        response = investigation_client.post(
            f"/api/v1/investigations/{bad_id}/documents/capture",
            json={"url": "https://example.com"},
        )
    assert response.status_code == 404
