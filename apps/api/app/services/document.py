import asyncio
import hashlib
import os
import uuid
from pathlib import Path

import pymupdf
from fastapi import UploadFile
from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import DocumentNotFoundError, DocumentNotRetryableError
from app.models.chunk import DocumentChunk
from app.models.document import Document
from app.services.investigation import InvestigationNotFoundError, InvestigationService

STORAGE_ROOT = Path(os.environ.get("STORAGE_ROOT", "storage"))


def _get_page_count(file_path: Path) -> int | None:
    try:
        doc = pymupdf.open(str(file_path))
        count = len(doc)
        doc.close()
        return count
    except Exception:
        return None


class DocumentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def upload_document(
        self, investigation_id: uuid.UUID, file: UploadFile
    ) -> Document:
        # Verify investigation exists
        inv_service = InvestigationService(self.db)
        await inv_service.get_investigation(investigation_id)

        # Generate document ID and storage path
        document_id = uuid.uuid4()
        file_path = STORAGE_ROOT / str(investigation_id) / f"{document_id}.pdf"
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Stream file to disk and compute SHA-256 in a single pass
        sha256 = hashlib.sha256()
        size_bytes = 0
        with open(file_path, "wb") as f:
            while True:
                chunk = await file.read(8192)
                if not chunk:
                    break
                f.write(chunk)
                sha256.update(chunk)
                size_bytes += len(chunk)

        checksum = sha256.hexdigest()
        page_count = await asyncio.to_thread(_get_page_count, file_path)

        # Create database record
        document = Document(
            id=document_id,
            investigation_id=investigation_id,
            filename=file.filename or "untitled.pdf",
            size_bytes=size_bytes,
            sha256_checksum=checksum,
            status="queued",
            page_count=page_count,
        )
        self.db.add(document)
        await self.db.commit()
        await self.db.refresh(document)

        logger.info(
            "Document uploaded",
            document_id=str(document_id),
            filename=file.filename,
            size_bytes=size_bytes,
            investigation_id=str(investigation_id),
        )

        # Enqueue Celery task for async text extraction
        try:
            from app.worker.tasks.process_document import process_document_task

            process_document_task.delay(str(document_id), str(investigation_id))
        except Exception as exc:
            logger.warning(
                "Failed to enqueue processing task",
                document_id=str(document_id),
                investigation_id=str(investigation_id),
                error=str(exc),
            )

        return document

    async def list_documents(
        self, investigation_id: uuid.UUID, limit: int = 50, offset: int = 0
    ) -> tuple[list[Document], int]:
        count_result = await self.db.execute(
            select(func.count(Document.id)).where(
                Document.investigation_id == investigation_id
            )
        )
        total = count_result.scalar_one()

        stmt = (
            select(Document)
            .where(Document.investigation_id == investigation_id)
            .order_by(Document.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(stmt)
        documents = list(result.scalars().all())
        return documents, total

    async def get_document(
        self, investigation_id: uuid.UUID, document_id: uuid.UUID
    ) -> Document:
        stmt = select(Document).where(
            Document.id == document_id,
            Document.investigation_id == investigation_id,
        )
        result = await self.db.execute(stmt)
        document = result.scalar_one_or_none()
        if document is None:
            raise DocumentNotFoundError(str(document_id))
        return document

    async def retry_failed_document(
        self, investigation_id: uuid.UUID, document_id: uuid.UUID
    ) -> Document:
        document = await self.get_document(investigation_id, document_id)

        if document.status != "failed":
            raise DocumentNotRetryableError(str(document_id), document.status)

        failed_stage = document.failed_stage

        # Determine resume_from_stage based on failed_stage
        # For extracting_entities failure, safer to re-chunk (see Dev Notes)
        if failed_stage in ("chunking", "extracting_entities"):
            resume_from_stage = "chunking"
            # Clean up existing chunks for this document
            stmt = select(DocumentChunk).where(
                DocumentChunk.document_id == document_id
            )
            result = await self.db.execute(stmt)
            chunks = result.scalars().all()
            for chunk in chunks:
                await self.db.delete(chunk)
        elif failed_stage == "embedding":
            resume_from_stage = "embedding"
            # Qdrant uses upsert (idempotent by chunk ID) — no explicit cleanup needed
        else:
            # preflight, extracting_text, or None (unknown) → run all stages
            resume_from_stage = None

        # Reset document state
        document.status = "queued"
        document.error_message = None
        document.failed_stage = None
        await self.db.commit()
        await self.db.refresh(document)

        logger.info(
            "Document retry enqueued",
            document_id=str(document_id),
            investigation_id=str(investigation_id),
            failed_stage=failed_stage,
            resume_from_stage=resume_from_stage,
        )

        # Enqueue Celery task
        try:
            from app.worker.tasks.process_document import process_document_task

            process_document_task.delay(
                str(document_id), str(investigation_id), resume_from_stage
            )
        except Exception as exc:
            logger.warning(
                "Failed to enqueue retry processing task",
                document_id=str(document_id),
                investigation_id=str(investigation_id),
                error=str(exc),
            )

        return document

    async def delete_document(
        self, investigation_id: uuid.UUID, document_id: uuid.UUID
    ) -> None:
        document = await self.get_document(investigation_id, document_id)

        # Remove file from storage
        try:
            file_path = STORAGE_ROOT / str(investigation_id) / f"{document_id}.pdf"
            if file_path.exists():
                file_path.unlink()
                logger.info(
                    "Document file deleted",
                    document_id=str(document_id),
                    investigation_id=str(investigation_id),
                )
        except Exception as exc:
            logger.error(
                "Document file deletion failed",
                document_id=str(document_id),
                investigation_id=str(investigation_id),
                error=str(exc),
            )

        # Delete database record
        await self.db.delete(document)
        await self.db.commit()
        logger.info(
            "Document deleted",
            document_id=str(document_id),
            investigation_id=str(investigation_id),
        )
