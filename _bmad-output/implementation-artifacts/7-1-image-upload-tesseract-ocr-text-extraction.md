# Story 7.1: Image Upload & Tesseract OCR Text Extraction

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an investigator,
I want to upload image files (JPEG, PNG, TIFF) to my investigation and have text extracted automatically via OCR,
So that I can include scanned documents and photographs in my investigation alongside PDFs.

## Acceptance Criteria

1. **GIVEN** the investigator is in an investigation workspace, **WHEN** they drag and drop or select image files (JPEG, PNG, TIFF) alongside PDFs, **THEN** image files are validated (accepted MIME types: image/jpeg, image/png, image/tiff), **AND** each image is stored immutably at `storage/{investigation_id}/{document_id}.{ext}` with SHA-256 checksum, **AND** a document record is created in PostgreSQL with `document_type` field distinguishing "pdf" from "image".

2. **GIVEN** an image document is queued for processing, **WHEN** the Celery worker picks up the job, **THEN** the pipeline detects the document type is "image" and routes to Tesseract OCR instead of PyMuPDF, **AND** Tesseract extracts text from the image, **AND** extracted text is stored as derived data following the same chunking and provenance pattern as PDF text, **AND** the document proceeds through the existing entity extraction and embedding pipeline.

3. **GIVEN** Tesseract OCR produces no text (blank image, non-text image), **WHEN** extraction completes with empty output, **THEN** the document is marked as complete with zero entities and a "no text extracted" indicator, **AND** the document is not marked as failed — empty OCR output is a valid result.

4. **GIVEN** an unsupported image format is uploaded, **WHEN** the file middleware validates the upload, **THEN** the upload is rejected with an RFC 7807 error: "Unsupported file type. Accepted: PDF, JPEG, PNG, TIFF".

## Tasks / Subtasks

- [x] **Task 1: Add `document_type` column to Document model + Alembic migration** (AC: 1)
  - [x] 1.1: Add `document_type: Mapped[str] = mapped_column(String(10), nullable=False, server_default="pdf")` to `apps/api/app/models/document.py`
  - [x] 1.2: Create Alembic migration (next sequence number after existing migrations) adding the `document_type` column with `server_default="pdf"` so existing rows get backfilled
  - [x] 1.3: Add `document_type` field to `DocumentResponse` schema in `apps/api/app/schemas/document.py`
  - [x] 1.4: Regenerate OpenAPI types: run `scripts/generate-api-types.sh` to update `apps/web/src/lib/api-types.generated.ts`

- [x] **Task 2: Install Tesseract OCR system package in Docker** (AC: 2)
  - [x] 2.1: In `docker/app.Dockerfile`, add `RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr && rm -rf /var/lib/apt/lists/*` BEFORE the `uv sync` step (must run as root, before `USER appuser`)
  - [x] 2.2: Add `pytesseract>=0.3.13` and `Pillow>=11.0.0` to `apps/api/pyproject.toml` dependencies
  - [x] 2.3: Run `cd apps/api && uv lock` to update the lockfile
  - [x] 2.4: Verify Tesseract is available in the dev container: `docker compose -f docker/docker-compose.dev.yml build app` and test `tesseract --version` inside the container

- [x] **Task 3: Extend upload endpoint to accept image files** (AC: 1, 4)
  - [x] 3.1: In `apps/api/app/api/v1/documents.py`, update the MIME type validation (currently line ~56) to accept: `application/pdf`, `image/jpeg`, `image/png`, `image/tiff`
  - [x] 3.2: Update magic bytes validation (currently line ~63) to check file type-specific headers: PDF → `%PDF`, JPEG → `FF D8 FF`, PNG → `89 50 4E 47`, TIFF → `49 49 2A 00` or `4D 4D 00 2A`
  - [x] 3.3: Determine `document_type` from MIME type: `application/pdf` → `"pdf"`, `image/*` → `"image"`
  - [x] 3.4: Pass `document_type` to `DocumentService.upload_document()` so it's stored on the DB record
  - [x] 3.5: Update file extension handling in storage path: use original extension (`.pdf`, `.jpg`, `.png`, `.tiff`) instead of hardcoded `.pdf`. Current code at `DocumentService.upload_document()` line ~44 uses `f"{document_id}.pdf"` — change to `f"{document_id}{ext}"` where `ext` is derived from the original filename
  - [x] 3.6: For image documents, skip the `page_count` extraction (currently uses `pymupdf.open()` which only works for PDFs) — set `page_count = 1` for single images

- [x] **Task 4: Create image text extraction via Tesseract** (AC: 2, 3)
  - [x] 4.1: Create `apps/api/app/services/image_extraction.py` with class `ImageExtractionService`
  - [x] 4.2: Method `extract_text(self, file_path: Path) -> str` that: opens the image with Pillow (`Image.open(file_path)`), runs Tesseract OCR (`pytesseract.image_to_string(image)`), returns extracted text with page marker `--- Page 1 ---\n{text}` (single image = single page, matching PyMuPDF format for downstream compatibility with `ChunkingService`)
  - [x] 4.3: Handle empty OCR output gracefully: if Tesseract returns empty/whitespace-only text, return empty string (not an error)
  - [x] 4.4: Handle Tesseract not installed or crash: catch `pytesseract.TesseractNotFoundError` and `pytesseract.TesseractError`, log via Loguru, re-raise as `DocumentProcessingError`
  - [x] 4.5: Log OCR results: `logger.info("Image OCR completed", document_id=doc_id, chars_extracted=len(text), file_path=str(file_path))`

- [x] **Task 5: Route processing pipeline by document type** (AC: 2, 3)
  - [x] 5.1: In `apps/api/app/worker/tasks/process_document.py`, at Stage 1 (text extraction, currently line ~109), load the document record and check `document.document_type`
  - [x] 5.2: If `document_type == "pdf"`: use existing `TextExtractionService().extract_text(file_path)` (no change)
  - [x] 5.3: If `document_type == "image"`: use new `ImageExtractionService().extract_text(file_path)`
  - [x] 5.4: Construct the correct file path using the actual file extension from the stored filename (not hardcoded `.pdf`). Current code: `file_path = STORAGE_ROOT / investigation_id / f"{document_id}.pdf"` — change to look up the document record's filename extension
  - [x] 5.5: If OCR returns empty text: set `document.extracted_text = ""`, set `document.status = "complete"`, set `document.entity_count = 0`, publish `document.complete` SSE event, and return early (skip chunking/entity extraction/embedding stages — nothing to extract from)
  - [x] 5.6: If OCR returns text: continue through existing stages 2-4 (chunking → entity extraction → embedding) identically to PDF flow

- [x] **Task 6: Update frontend upload to accept image files** (AC: 1, 4)
  - [x] 6.1: In `apps/web/src/components/investigation/DocumentUploadZone.tsx`, update the `accept` attribute (currently `.pdf,application/pdf` at line ~131) to: `.pdf,.jpg,.jpeg,.png,.tiff,.tif,application/pdf,image/jpeg,image/png,image/tiff`
  - [x] 6.2: Update the `handleFiles` validation (currently `file.type !== "application/pdf"` at line ~35) to accept the extended MIME types
  - [x] 6.3: Update the error message for rejected files to reflect all accepted types
  - [x] 6.4: Update the upload zone label/text to indicate images are accepted (e.g., "Drag PDFs or images here")

- [x] **Task 7: Update frontend document display for image documents** (AC: 1)
  - [x] 7.1: In `apps/web/src/components/investigation/DocumentCard.tsx`, conditionally render `<Image />` icon (lucide-react) for image documents instead of `<FileText />`. Detect via the new `document_type` field from `DocumentResponse` (available after OpenAPI type regeneration in Task 1.4)
  - [x] 7.2: For image documents, hide the "page count" display (line ~78-84) or show "1 page" — images don't have multi-page counts
  - [x] 7.3: In `ProcessingDashboard.tsx`, the overall document count should distinguish PDF vs image if desired (optional — can show combined count initially)

- [x] **Task 8: Backend tests** (AC: 1, 2, 3, 4)
  - [x] 8.1: In `apps/api/tests/api/test_documents.py`, add test: upload JPEG file → 201 with `document_type: "image"` in response
  - [x] 8.2: Add test: upload PNG file → 201 with `document_type: "image"`
  - [x] 8.3: Add test: upload unsupported file (e.g., `.txt`) → 422 with RFC 7807 error
  - [x] 8.4: Add test: mixed upload (1 PDF + 1 JPEG) → 201 with correct `document_type` for each
  - [x] 8.5: Add test for `ImageExtractionService.extract_text()` — mock pytesseract, verify returns text with page marker format
  - [x] 8.6: Add test for empty OCR result — verify document marked complete with 0 entities, not failed
  - [x] 8.7: Add test for process_document_task routing — mock document with `document_type="image"`, verify `ImageExtractionService` is called instead of `TextExtractionService`

- [x] **Task 9: Frontend tests** (AC: 1, 4)
  - [x] 9.1: In `DocumentUploadZone.test.tsx`, add test: accepts JPEG file (no rejection error)
  - [x] 9.2: Add test: accepts PNG file
  - [x] 9.3: Add test: rejects `.txt` file with error message listing accepted types
  - [x] 9.4: In `DocumentCard.test.tsx`, add test: renders Image icon when `document_type === "image"`, FileText icon when `document_type === "pdf"`

## Dev Notes

### Architecture Context

This is **Story 7.1** — the first story in Phase 2, Epic 7 (Image Document Processing - OCR). All MVP infrastructure (Epics 1-6) is complete. This story extends the existing document pipeline to accept image files alongside PDFs, routing them through Tesseract OCR for text extraction.

**FRs covered:** FR48 (image upload), FR49 (Tesseract OCR extraction)
**NFRs relevant:** All existing MVP NFRs (data integrity, immutable storage, privacy) apply to image documents identically

### What Already Exists — DO NOT RECREATE

| Component | Location | What It Does |
|---|---|---|
| Document upload endpoint | `app/api/v1/documents.py` | PDF-only upload with MIME/magic/size validation |
| Document model | `app/models/document.py` | SQLAlchemy model — NO document_type field yet |
| DocumentResponse schema | `app/schemas/document.py` | Pydantic schema with computed `extraction_quality` |
| DocumentService | `app/services/document.py` | Upload, list, retry, delete — stores at `{id}.pdf` |
| TextExtractionService | `app/services/text_extraction.py` | PyMuPDF extraction with page markers |
| ChunkingService | `app/services/chunking.py` | Splits text by `--- Page N ---` markers |
| process_document_task | `app/worker/tasks/process_document.py` | 4-stage pipeline: text → chunk → entities → embed |
| DocumentUploadZone | `components/investigation/DocumentUploadZone.tsx` | Drag-drop + file picker, PDF-only validation |
| DocumentCard | `components/investigation/DocumentCard.tsx` | Status card with FileText icon, quality badge |
| ProcessingDashboard | `components/investigation/ProcessingDashboard.tsx` | Real-time progress with SSE |

### Critical Implementation Details

#### File Storage Path Change

**Current:** `storage/{investigation_id}/{document_id}.pdf` (hardcoded `.pdf`)
**New:** `storage/{investigation_id}/{document_id}.{ext}` (dynamic extension)

This affects TWO locations:
1. `DocumentService.upload_document()` (line ~44 of `app/services/document.py`) — where the file is written
2. `process_document_task` (line ~112 of `app/worker/tasks/process_document.py`) — where the file is read for processing

Both must use the same extension logic. Derive extension from the original filename stored in the DB record.

#### Magic Bytes for Image Validation

| Format | Magic Bytes | Length |
|--------|------------|--------|
| PDF | `%PDF` (25 50 44 46) | 4 bytes |
| JPEG | `FF D8 FF` | 3 bytes |
| PNG | `89 50 4E 47` (‰PNG) | 4 bytes |
| TIFF (LE) | `49 49 2A 00` | 4 bytes |
| TIFF (BE) | `4D 4D 00 2A` | 4 bytes |

Read 4 bytes for all checks (minimum 3 for JPEG).

#### Tesseract OCR Output Format

Tesseract's `image_to_string()` returns raw text. Wrap it in the same page-marker format the ChunkingService expects:

```python
def extract_text(self, file_path: Path) -> str:
    image = Image.open(file_path)
    text = pytesseract.image_to_string(image)
    if not text.strip():
        return ""
    return f"--- Page 1 ---\n{text}"
```

This ensures the existing chunking pipeline works without modification — it parses `--- Page N ---` markers to track page provenance.

#### Empty OCR Early Exit

When OCR returns empty text, the worker task should exit early after Stage 1:
- Set `extracted_text = ""`
- Set `status = "complete"`
- Set `entity_count = 0`
- Publish `document.complete` SSE event with `entity_count=0, relationship_count=0`
- Do NOT proceed to chunking/entity extraction/embedding (nothing to process)
- Do NOT mark as "failed" — empty OCR is a valid result (blank image, decorative image, etc.)

#### Alembic Migration Naming

Existing migrations:
- 001 through 007 (sequence)

New migration should be `008_add_document_type.py`. Use `server_default="pdf"` so all existing rows get the default value without requiring a data migration.

#### Dockerfile Tesseract Installation

Must install BEFORE `USER appuser` (needs root). Order matters:

```dockerfile
FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install system dependencies (Tesseract for OCR)
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr && rm -rf /var/lib/apt/lists/*

WORKDIR /app
# ... rest of Dockerfile
```

### Project Structure Notes

**New files:**
- `apps/api/app/services/image_extraction.py` — Tesseract OCR service
- `apps/api/migrations/versions/008_add_document_type.py` — Alembic migration

**Modified files:**
- `apps/api/app/models/document.py` — add `document_type` field
- `apps/api/app/schemas/document.py` — add `document_type` to response
- `apps/api/app/api/v1/documents.py` — extend MIME/magic validation for images
- `apps/api/app/services/document.py` — dynamic file extension, pass document_type
- `apps/api/app/worker/tasks/process_document.py` — route by document_type, dynamic file path
- `apps/api/pyproject.toml` — add pytesseract, Pillow
- `docker/app.Dockerfile` — install tesseract-ocr
- `apps/web/src/components/investigation/DocumentUploadZone.tsx` — accept image MIME types
- `apps/web/src/components/investigation/DocumentCard.tsx` — type-aware icon
- `apps/web/src/lib/api-types.generated.ts` — regenerated (auto)
- `apps/api/tests/api/test_documents.py` — new image upload tests
- `apps/web/src/components/investigation/DocumentUploadZone.test.tsx` — image acceptance tests
- `apps/web/src/components/investigation/DocumentCard.test.tsx` — type-aware icon test

### Important Patterns from Previous Stories

1. **Celery tasks use sync sessions** — `SyncSessionLocal()`. API endpoints use async sessions.
2. **SSE events are best-effort** — `_publish_safe()` wrapper never raises. Commit DB state before publishing.
3. **RFC 7807 error format** — `{type, title, status, detail, instance}` via `DomainError` subclasses.
4. **Service layer pattern** — Business logic in `app/services/`, Celery tasks orchestrate services.
5. **Loguru structured logging** — `logger.info("Message", key=value, key2=value2)`.
6. **Commit pattern** — `feat: Story X.Y — description`.
7. **Backend test baselines** — ~316+ backend tests, ~225+ frontend tests.
8. **Pre-existing test failures** — `SystemStatusPage.test.tsx` (4 failures), `test_docker_compose.py` (2 infra), `test_entity_discovered_sse_events_published` (1 mock). Do not fix these.
9. **OpenAPI type generation** — run `scripts/generate-api-types.sh` after any schema change.
10. **File validation pattern** — partial success: upload endpoint returns `{items: [...], errors: [...]}` for mixed valid/invalid files.

### References

- [Source: _bmad-output/planning-artifacts/epics-phase2.md — Epic 7, Story 7.1 acceptance criteria]
- [Source: _bmad-output/planning-artifacts/prd.md — FR48 (image upload), FR49 (Tesseract OCR); Post-MVP Phase 2 scope lines 498-506]
- [Source: _bmad-output/planning-artifacts/architecture.md — Lines 66-77: Tech stack, Docker Compose, file storage pattern]
- [Source: _bmad-output/planning-artifacts/architecture.md — Lines 255-266: Data architecture — investigation-scoped storage, immutability]
- [Source: _bmad-output/planning-artifacts/architecture.md — Lines 346-358: Docker Compose 7 services, combined API+worker container]
- [Source: _bmad-output/planning-artifacts/architecture.md — Lines 399-424: Naming conventions table]
- [Source: _bmad-output/planning-artifacts/architecture.md — Lines 486-496: Process patterns — error handling, Celery task error flow]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — Lines 1207-1213: Confidence indicators (high/medium/low)]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — Lines 904-927: Processing Dashboard per-document status cards]
- [Source: apps/api/app/api/v1/documents.py — Current upload endpoint with PDF-only validation]
- [Source: apps/api/app/models/document.py — Document model fields, no document_type]
- [Source: apps/api/app/services/text_extraction.py — PyMuPDF extraction with page markers]
- [Source: apps/api/app/services/document.py — DocumentService.upload_document() with .pdf path]
- [Source: apps/api/app/worker/tasks/process_document.py — 4-stage pipeline, Stage 1 text extraction routing]
- [Source: apps/web/src/components/investigation/DocumentUploadZone.tsx — PDF-only file validation]
- [Source: apps/web/src/components/investigation/DocumentCard.tsx — FileText icon, page count display]
- [Source: docker/app.Dockerfile — python:3.13-slim, no tesseract installed]
- [Source: apps/api/pyproject.toml — Current dependencies, no pytesseract/Pillow]

## Change Log

- 2026-04-12: Story 7.1 implemented — image upload with Tesseract OCR text extraction, document type routing, frontend image support, backend + frontend tests
- 2026-04-12: Code review fixes — Pillow context manager for FD safety, MIME/magic cross-validation, TIFF upload tests (LE+BE), retry_count added to _to_response

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

- Worker tests (`tests/worker/test_process_document.py`) fail due to missing Docker infrastructure (Qdrant connection refused) — pre-existing, not caused by this story
- SystemStatusPage.test.tsx (4 failures) — pre-existing, documented in Dev Notes

### Completion Notes List

- Task 1: Added `document_type` column to Document model with `server_default="pdf"`, Alembic migration 008, updated schema and OpenAPI types
- Task 2: Added Tesseract OCR to Dockerfile, added pytesseract and Pillow dependencies
- Task 3: Extended upload endpoint to validate JPEG/PNG/TIFF MIME types and magic bytes, pass document_type to service, use dynamic file extensions
- Task 4: Created `ImageExtractionService` with Tesseract OCR, page-marker format output, graceful empty OCR handling
- Task 5: Routed process_document_task by document_type, dynamic file path with extension from filename, early exit for empty OCR results
- Task 6: Updated frontend upload zone to accept image MIME types, updated drag zone text and accept attribute
- Task 7: Conditionally render Image/FileText icon based on document_type in DocumentCard
- Task 8: Added 7 backend tests: JPEG upload, PNG upload, unsupported type rejection, mixed upload, OCR service unit tests, pipeline routing test
- Task 9: Added 5 frontend tests: JPEG acceptance, PNG acceptance, .txt rejection, DocumentCard image/pdf icon rendering

### File List

**New files:**
- `apps/api/app/services/image_extraction.py`
- `apps/api/migrations/versions/008_add_document_type.py`

**Modified files:**
- `apps/api/app/models/document.py` — added `document_type` field
- `apps/api/app/schemas/document.py` — added `document_type` to response schema
- `apps/api/app/api/v1/documents.py` — extended MIME/magic validation, document_type routing
- `apps/api/app/services/document.py` — dynamic file extension, document_type parameter
- `apps/api/app/worker/tasks/process_document.py` — document_type routing, dynamic file path, empty OCR early exit
- `apps/api/pyproject.toml` — added pytesseract, Pillow
- `apps/api/uv.lock` — updated lockfile
- `docker/app.Dockerfile` — install tesseract-ocr system package
- `apps/web/src/components/investigation/DocumentUploadZone.tsx` — accept image MIME types
- `apps/web/src/components/investigation/DocumentCard.tsx` — conditional Image/FileText icon
- `apps/web/src/lib/api-types.generated.ts` — added document_type field
- `apps/api/tests/conftest.py` — added document_type to sample_document fixture
- `apps/api/tests/api/test_documents.py` — updated existing tests for new validation, added 7 new image tests
- `apps/web/src/components/investigation/DocumentUploadZone.test.tsx` — updated tests, added 3 new image tests
- `apps/web/src/components/investigation/DocumentCard.test.tsx` — added 2 icon type tests
