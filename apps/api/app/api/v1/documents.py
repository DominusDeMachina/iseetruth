import uuid

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgres import get_db
from app.exceptions import DocumentNotReadyError, InvalidFileTypeError
from app.schemas.document import (
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


def _to_response(document, include_text: bool = False) -> DocumentResponse:
    return DocumentResponse(
        id=document.id,
        investigation_id=document.investigation_id,
        filename=document.filename,
        size_bytes=document.size_bytes,
        sha256_checksum=document.sha256_checksum,
        status=document.status,
        page_count=document.page_count,
        extracted_text=document.extracted_text if include_text else None,
        error_message=document.error_message,
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
        # Validate PDF MIME type
        if file.content_type != "application/pdf":
            errors.append(
                f"Rejected '{file.filename}': not a PDF (got {file.content_type})"
            )
            continue

        # Validate magic bytes
        header = await file.read(4)
        await file.seek(0)
        if header[:4] != b"%PDF":
            errors.append(f"Rejected '{file.filename}': invalid PDF magic bytes")
            continue

        # Validate file size
        if file.size is not None and file.size > MAX_FILE_SIZE:
            size_mb = file.size / (1024 * 1024)
            errors.append(
                f"Rejected '{file.filename}': exceeds 200 MB limit ({size_mb:.1f} MB)"
            )
            continue

        # Upload with error handling for partial failure resilience
        try:
            document = await service.upload_document(investigation_id, file)
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
