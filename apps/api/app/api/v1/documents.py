import uuid

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from urllib.parse import urlparse

from app.db.postgres import get_db
from app.exceptions import DocumentNotReadyError, DocumentNotRetryableError, InvalidFileTypeError, InvalidUrlError
from app.schemas.document import (
    CaptureWebPageRequest,
    DocumentListResponse,
    DocumentResponse,
    DocumentTextResponse,
    UploadDocumentsResponse,
)
from app.services.document import DocumentService

router = APIRouter(
    prefix="/investigations/{investigation_id}/documents",
    tags=["documents"],
)

MAX_FILE_SIZE = 200 * 1024 * 1024  # 200 MB

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/tiff",
}

# Magic byte signatures for file type validation
_MAGIC_SIGNATURES: list[tuple[bytes, str]] = [
    (b"%PDF", "application/pdf"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG", "image/png"),
    (b"II\x2a\x00", "image/tiff"),  # TIFF little-endian
    (b"MM\x00\x2a", "image/tiff"),  # TIFF big-endian
]


def _detect_mime_from_magic(header: bytes) -> str | None:
    """Return MIME type matching magic bytes, or None."""
    for sig, mime in _MAGIC_SIGNATURES:
        if header[: len(sig)] == sig:
            return mime
    return None


def _mime_to_document_type(mime: str) -> str:
    """Map MIME type to document_type value."""
    if mime == "application/pdf":
        return "pdf"
    return "image"


def _to_response(document, include_text: bool = False) -> DocumentResponse:
    return DocumentResponse(
        id=document.id,
        investigation_id=document.investigation_id,
        filename=document.filename,
        size_bytes=document.size_bytes,
        sha256_checksum=document.sha256_checksum,
        document_type=document.document_type,
        source_url=document.source_url,
        status=document.status,
        page_count=document.page_count,
        entity_count=document.entity_count,
        extraction_confidence=document.extraction_confidence,
        extracted_text=document.extracted_text if include_text else None,
        error_message=document.error_message,
        failed_stage=document.failed_stage,
        retry_count=document.retry_count,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


@router.post("", status_code=201, response_model=UploadDocumentsResponse)
async def upload_documents(
    investigation_id: uuid.UUID,
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
):
    service = DocumentService(db)
    results: list[DocumentResponse] = []
    errors: list[str] = []

    for file in files:
        # Validate MIME type
        if file.content_type not in ALLOWED_MIME_TYPES:
            errors.append(
                f"Rejected '{file.filename}': unsupported file type (got {file.content_type}). "
                "Accepted: PDF, JPEG, PNG, TIFF"
            )
            continue

        # Validate magic bytes and cross-check against claimed MIME type
        header = await file.read(4)
        await file.seek(0)
        detected_mime = _detect_mime_from_magic(header)
        if detected_mime is None:
            errors.append(f"Rejected '{file.filename}': invalid file magic bytes")
            continue
        if _mime_to_document_type(detected_mime) != _mime_to_document_type(file.content_type):
            errors.append(
                f"Rejected '{file.filename}': file content does not match declared type "
                f"(declared {file.content_type}, detected {detected_mime})"
            )
            continue

        # Validate file size
        if file.size is not None and file.size > MAX_FILE_SIZE:
            size_mb = file.size / (1024 * 1024)
            errors.append(
                f"Rejected '{file.filename}': exceeds 200 MB limit ({size_mb:.1f} MB)"
            )
            continue

        # Determine document type from MIME
        document_type = _mime_to_document_type(detected_mime)

        # Upload with error handling for partial failure resilience
        try:
            document = await service.upload_document(
                investigation_id, file, document_type=document_type
            )
            results.append(_to_response(document))
        except Exception as exc:
            logger.error(
                "Document upload failed",
                filename=file.filename,
                investigation_id=str(investigation_id),
                error=str(exc),
            )
            errors.append(f"Upload failed for '{file.filename}': {str(exc)}")

    if not results and errors:
        raise InvalidFileTypeError("; ".join(errors))

    return UploadDocumentsResponse(items=results, errors=errors)


@router.post("/capture", status_code=201, response_model=DocumentResponse)
async def capture_web_page(
    investigation_id: uuid.UUID,
    body: CaptureWebPageRequest,
    db: AsyncSession = Depends(get_db),
):
    url = body.url.strip()

    # Validate URL format
    if not url:
        raise InvalidUrlError("URL must not be empty")
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise InvalidUrlError(
            f"URL must use http or https scheme (got '{parsed.scheme or 'none'}')"
        )
    if not parsed.hostname:
        raise InvalidUrlError("URL must include a hostname")

    # Verify investigation exists
    from app.services.investigation import InvestigationService
    inv_service = InvestigationService(db)
    await inv_service.get_investigation(investigation_id)

    # Create document record with placeholder values — worker fills in after fetch
    from app.models.document import Document
    document_id = uuid.uuid4()
    document = Document(
        id=document_id,
        investigation_id=investigation_id,
        filename=parsed.hostname or "web-capture",
        size_bytes=0,
        sha256_checksum="",
        document_type="web",
        source_url=url,
        status="queued",
        page_count=None,
        retry_count=0,
    )
    db.add(document)
    await db.commit()
    await db.refresh(document)

    logger.info(
        "Web capture queued",
        document_id=str(document_id),
        url=url,
        investigation_id=str(investigation_id),
    )

    # Enqueue Celery task for async capture and processing
    try:
        from app.worker.tasks.process_document import process_document_task
        process_document_task.delay(str(document_id), str(investigation_id))
    except Exception as exc:
        logger.warning(
            "Failed to enqueue web capture task",
            document_id=str(document_id),
            investigation_id=str(investigation_id),
            error=str(exc),
        )

    return _to_response(document)


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    investigation_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    service = DocumentService(db)
    documents, total = await service.list_documents(investigation_id, limit, offset)
    return DocumentListResponse(
        items=[_to_response(doc) for doc in documents],
        total=total,
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    investigation_id: uuid.UUID,
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    service = DocumentService(db)
    document = await service.get_document(investigation_id, document_id)
    return _to_response(document, include_text=True)


@router.get("/{document_id}/text", response_model=DocumentTextResponse)
async def get_document_text(
    investigation_id: uuid.UUID,
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    service = DocumentService(db)
    document = await service.get_document(investigation_id, document_id)
    if document.status != "complete":
        raise DocumentNotReadyError(str(document_id), document.status)
    return DocumentTextResponse(
        document_id=document.id,
        filename=document.filename,
        page_count=document.page_count,
        extracted_text=document.extracted_text,
        status=document.status,
    )


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    investigation_id: uuid.UUID,
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    service = DocumentService(db)
    await service.delete_document(investigation_id, document_id)
    return Response(status_code=204)


@router.post("/{document_id}/retry", response_model=DocumentResponse)
async def retry_document(
    investigation_id: uuid.UUID,
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    service = DocumentService(db)
    document = await service.retry_failed_document(investigation_id, document_id)
    return _to_response(document)
