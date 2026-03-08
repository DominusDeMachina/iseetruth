# Story 2.2: PDF Upload with Immutable Storage

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an investigator,
I want to upload multiple PDF files at once by dragging a folder into the upload area,
so that I can quickly ingest all my investigation documents with guaranteed immutability.

## Acceptance Criteria

1. **AC1: Drag-and-Drop Upload with Validation**
   - Given the investigator is in an investigation workspace at `/investigations/:id`
   - When they drag and drop PDF files or a folder onto the upload area
   - Then each file is validated (PDF MIME type `application/pdf`, max 200MB per file)
   - And valid files are uploaded to `POST /api/v1/investigations/{id}/documents`
   - And immediate feedback shows each file as "uploading" then "queued"
   - And non-PDF files are rejected with a clear error message

2. **AC2: File Picker Upload**
   - Given the investigator is in an investigation workspace
   - When they click the "Choose Files" button in the upload area
   - Then a native file picker opens allowing multi-file selection
   - And selected PDF files are uploaded identically to drag-and-drop flow

3. **AC3: File Storage with Immutability Verification**
   - Given a valid PDF is uploaded
   - When the backend receives the file
   - Then the file is stored at `storage/{investigation_id}/{document_id}.pdf`
   - And a SHA-256 checksum is computed from the stored file bytes
   - And a document record is created in PostgreSQL with metadata: filename, size_bytes, sha256_checksum, status="queued"
   - And the stored file is byte-for-byte identical to the uploaded file (verified by checksum)
   - And the document is never modified, re-encoded, or compressed after storage

4. **AC4: Bulk Upload Support**
   - Given multiple files are uploaded simultaneously
   - When the backend processes the uploads
   - Then each file gets its own document record with a UUID v4 primary key
   - And bulk upload of 50+ documents completes without failure
   - And each file is stored independently (partial failure does not prevent other files from saving)

5. **AC5: Document List Display**
   - Given documents have been uploaded to an investigation
   - When the investigator views the investigation workspace
   - Then a document list displays below the upload zone
   - And each document shows: filename, file size (human-readable), status badge, upload date
   - And data is fetched via TanStack Query from `GET /api/v1/investigations/{id}/documents`

6. **AC6: Document Deletion**
   - Given a document exists in an investigation
   - When the investigator clicks the delete button on a document
   - Then a confirmation dialog appears
   - And upon confirmation, the document file is removed from storage and the record is deleted from PostgreSQL
   - And the document list updates automatically

7. **AC7: Backend Document Persistence**
   - Given the backend receives a `POST /api/v1/investigations/{id}/documents`
   - When the request contains one or more PDF files as multipart form data
   - Then for each file: a UUID is generated, the file is saved to disk, checksum is computed, and a document record is persisted
   - And the Alembic migration has created the `documents` table with foreign key to `investigations`
   - And the document record includes: id, investigation_id, filename, size_bytes, sha256_checksum, status, page_count, created_at, updated_at

## Tasks / Subtasks

- [x] Task 1: Create Document database model and Alembic migration (AC: #3, #7)
  - [x] 1.1: Create `app/models/document.py` with SQLAlchemy model — `Document` table with id (UUID), investigation_id (UUID FK), filename (String 255), size_bytes (BigInteger), sha256_checksum (String 64), status (String 20, default="queued"), page_count (Integer, nullable), created_at (DateTime), updated_at (DateTime)
  - [x] 1.2: Add relationship to Investigation model (one-to-many: Investigation has many Documents)
  - [x]1.3: Export Document from `app/models/__init__.py`
  - [x]1.4: Generate Alembic migration: `alembic revision --autogenerate -m "create_documents_table"`
  - [x]1.5: Verify migration includes `updated_at` trigger (same pattern as investigations table)
  - [x]1.6: Verify migration applies cleanly on fresh database

- [x]Task 2: Create Document Pydantic schemas (AC: #7)
  - [x]2.1: Create `app/schemas/document.py` with `DocumentResponse` (id, investigation_id, filename, size_bytes, sha256_checksum, status, page_count, created_at, updated_at), `DocumentListResponse` (items: list[DocumentResponse], total: int)
  - [x]2.2: No `DocumentCreate` schema needed — upload is via multipart form, not JSON body

- [x]Task 3: Create Document service layer (AC: #3, #4, #6)
  - [x]3.1: Create `app/services/document.py` with `DocumentService` class accepting `db: AsyncSession`
  - [x]3.2: Implement `upload_document(investigation_id, file: UploadFile)` — validate investigation exists, generate UUID, save file to `STORAGE_ROOT/{investigation_id}/{document_id}.pdf`, compute SHA-256, compute page_count via PyMuPDF, create document record with status="queued", return document
  - [x]3.3: Implement `list_documents(investigation_id, limit, offset)` — query documents for investigation, return paginated list with total count
  - [x]3.4: Implement `get_document(investigation_id, document_id)` — fetch single document or raise DocumentNotFoundError
  - [x]3.5: Implement `delete_document(investigation_id, document_id)` — remove file from storage, delete PostgreSQL record
  - [x]3.6: Add `DocumentNotFoundError(DomainError)` to `app/exceptions.py`

- [x]Task 4: Create Document API endpoints (AC: #1, #4, #5, #6, #7)
  - [x]4.1: Create `app/api/v1/documents.py` with FastAPI router (prefix depends on investigation: nested under `/investigations/{investigation_id}/documents`)
  - [x]4.2: `POST /api/v1/investigations/{investigation_id}/documents` — accepts `files: list[UploadFile]` (multipart), validates each is PDF, calls service for each valid file, returns list of DocumentResponse with status 201
  - [x]4.3: `GET /api/v1/investigations/{investigation_id}/documents` — returns DocumentListResponse with pagination (limit/offset query params)
  - [x]4.4: `GET /api/v1/investigations/{investigation_id}/documents/{document_id}` — returns single DocumentResponse
  - [x]4.5: `DELETE /api/v1/investigations/{investigation_id}/documents/{document_id}` — returns 204 No Content
  - [x]4.6: Register documents router in `app/api/v1/router.py`

- [x]Task 5: Update Investigation response with document count (AC: #5)
  - [x]5.1: Update `_to_response()` in `investigations.py` router to compute actual `document_count` from DB instead of hardcoded 0
  - [x]5.2: Query `SELECT COUNT(*) FROM documents WHERE investigation_id = ?` for the count

- [x]Task 6: Write backend tests (AC: #1, #3, #4, #5, #6, #7)
  - [x]6.1: Create `tests/api/test_documents.py` — test upload single PDF (201), upload multiple PDFs (201), upload non-PDF rejected (422), list documents (200 with items/total), get document (200), get not found (404), delete document (204), delete not found (404)
  - [x]6.2: Create `tests/services/test_document_service.py` — test upload (file stored + DB record + checksum), list (pagination), get (found + not found), delete (file removed + DB deleted), upload to nonexistent investigation (error)
  - [x]6.3: Add document test fixtures to `tests/conftest.py` — mock UploadFile, sample document factory

- [x]Task 7: Create frontend upload components (AC: #1, #2, #5)
  - [x]7.1: Create `src/components/investigation/DocumentUploadZone.tsx` — drag-and-drop zone with dashed border, supports file picker button, validates PDF MIME type on client side, shows upload progress per file
  - [x]7.2: Create `src/components/investigation/DocumentList.tsx` — vertical list of document cards, shows filename/size/status/date, loading skeleton, empty state (integrated with upload zone)
  - [x]7.3: Create `src/components/investigation/DocumentCard.tsx` — single document card with filename, human-readable size, status badge (queued/complete/failed), delete button with confirmation
  - [x]7.4: Create `src/components/investigation/DeleteDocumentDialog.tsx` — confirmation dialog: "Delete Document? {filename} will be permanently removed." Cancel (default focus) + Delete (destructive)

- [x]Task 8: Create Document hooks (AC: #1, #5, #6)
  - [x]8.1: Create `src/hooks/useDocuments.ts` — `useDocuments(investigationId)` query hook for list, `useUploadDocuments(investigationId)` mutation for upload, `useDeleteDocument(investigationId)` mutation for delete
  - [x]8.2: All hooks use openapi-fetch typed client (`api.GET`, `api.POST`, `api.DELETE`)
  - [x]8.3: Upload mutation uses `FormData` for multipart file upload
  - [x]8.4: Mutations invalidate `['documents', investigationId]` and `['investigations']` query keys on success

- [x]Task 9: Update investigation workspace route (AC: #1, #2, #5)
  - [x]9.1: Update `src/routes/investigations/$id.tsx` — replace Story 2.2 placeholder with DocumentUploadZone + DocumentList
  - [x]9.2: Show upload zone above document list; when no documents exist, show full-width empty state with drag zone

- [x]Task 10: Regenerate OpenAPI types (AC: #5)
  - [x]10.1: Run `scripts/generate-api-types.sh` against running backend to generate TypeScript types for document endpoints
  - [x]10.2: Verify generated types match DocumentResponse and DocumentListResponse schemas

- [x]Task 11: Write frontend tests (AC: #1, #2, #5, #6)
  - [x]11.1: Create `src/components/investigation/DocumentUploadZone.test.tsx` — test: renders drop zone; test: file picker triggers; test: rejects non-PDF with error; test: shows upload progress
  - [x]11.2: Create `src/components/investigation/DocumentList.test.tsx` — test: renders document cards; test: empty state; test: loading skeleton
  - [x]11.3: Create `src/components/investigation/DocumentCard.test.tsx` — test: renders card data; test: delete confirmation flow; test: status badge display

## Dev Notes

### CRITICAL: Backend Architecture Patterns (MUST follow)

**ORM: SQLAlchemy 2.0 + Pydantic v2 (NOT SQLModel)**
The architecture doc mentions SQLModel, but the actual codebase uses SQLAlchemy 2.0 async with separate Pydantic v2 schemas. Follow the established pattern from Story 2.1:
- Database models: `app/models/` using SQLAlchemy `DeclarativeBase` with `Mapped[]` type hints
- API schemas: `app/schemas/` using Pydantic `BaseModel` with `model_config = {"from_attributes": True}`
- [Source: _bmad-output/implementation-artifacts/2-1-investigation-crud-api-list-view.md — "SQLModel dropped for SQLAlchemy 2.0 + Pydantic v2"]

**Document Model Pattern (follow Investigation model exactly):**
```python
# app/models/document.py
import uuid
from datetime import datetime
from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    investigation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued")
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    investigation = relationship("Investigation", back_populates="documents")
```

**Database Session Pattern (from `app/db/postgres.py`):**
```python
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
```

**API Response Format — NO wrapper:**
- Success: Direct response body (NOT `{data: ...}`)
- List: `{ "items": [...], "total": 42 }`
- Error: RFC 7807 Problem Details
- [Source: _bmad-output/planning-artifacts/architecture.md#API Response Format]

**RFC 7807 Error Responses:**
```json
{
  "type": "urn:osint:error:document_not_found",
  "title": "Document Not Found",
  "status": 404,
  "detail": "No document found with id: {id}",
  "instance": "/api/v1/investigations/{investigation_id}/documents/{id}"
}
```

**File Upload Endpoint Pattern:**
```python
from fastapi import APIRouter, Depends, File, UploadFile
from typing import List

@router.post("", status_code=201, response_model=list[DocumentResponse])
async def upload_documents(
    investigation_id: uuid.UUID,
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
):
```

**SHA-256 Checksum Computation:**
```python
import hashlib

async def compute_sha256(file_path: Path) -> str:
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()
```

**Page Count via PyMuPDF (pymupdf already in dependencies):**
```python
import pymupdf  # import name for PyMuPDF

def get_page_count(file_path: Path) -> int | None:
    try:
        doc = pymupdf.open(str(file_path))
        count = len(doc)
        doc.close()
        return count
    except Exception:
        return None
```

**PDF MIME Validation:**
- Validate `content_type == "application/pdf"` from UploadFile
- Also check file magic bytes (first 4 bytes should be `%PDF`)
- Reject non-PDF with 422 status and RFC 7807 error

**File Storage Path:**
```python
STORAGE_ROOT = Path(os.environ.get("STORAGE_ROOT", "storage"))
file_path = STORAGE_ROOT / str(investigation_id) / f"{document_id}.pdf"
file_path.parent.mkdir(parents=True, exist_ok=True)
```
- [Source: _bmad-output/implementation-artifacts/2-1-investigation-crud-api-list-view.md — "STORAGE_ROOT configurable via env var"]

**Logging: Loguru (NOT print/logging)**
```python
from loguru import logger
logger.info("Document uploaded", document_id=str(id), filename=filename, size_bytes=size, investigation_id=str(inv_id))
logger.error("Document upload failed", investigation_id=str(inv_id), error=str(exc))
```

**Exception Pattern (from `app/exceptions.py`):**
```python
class DocumentNotFoundError(DomainError):
    def __init__(self, document_id: str):
        super().__init__(
            detail=f"No document found with id: {document_id}",
            status_code=404,
            error_type="document_not_found",
        )
```

**Alembic Migration Pattern:**
- Use sync psycopg2 driver (not asyncpg) in migration env
- Include `updated_at` trigger function (same as investigations migration)
- Add foreign key constraint with `ondelete="CASCADE"` to investigations
- Create index on `investigation_id` for efficient queries

### CRITICAL: Frontend Architecture Patterns (MUST follow)

**API Client: openapi-fetch (NOT raw fetch, NOT axios)**
```typescript
// Already configured in src/lib/api-client.ts
import createClient from "openapi-fetch";
import type { paths } from "./api-types.generated";
export const api = createClient<paths>({ baseUrl: "" });
```
- baseUrl is empty string (NOT `/api/v1`) — Nginx proxies `/api/*` to backend
- [Source: _bmad-output/implementation-artifacts/1-3-frontend-shell-with-system-status-page.md — "fixed baseUrl to empty string"]

**TanStack Query for ALL server state:**
```typescript
// Query keys: hierarchical arrays
['documents', investigationId]  // list for investigation
['investigations']              // invalidate to update doc count

// Upload mutation uses FormData:
const formData = new FormData();
files.forEach(file => formData.append('files', file));
```

**File Upload via openapi-fetch:**
```typescript
// openapi-fetch supports FormData natively
const { data, error } = await api.POST(
  "/api/v1/investigations/{investigation_id}/documents",
  {
    params: { path: { investigation_id: id } },
    body: formData,
    bodySerializer: (body) => body, // pass FormData as-is, don't JSON.stringify
  }
);
```

**TanStack Router navigation:**
```typescript
import { useNavigate, Link } from '@tanstack/react-router';
```

**Component placement:**
- Document components: `src/components/investigation/`
- Hooks: `src/hooks/`
- Tests: co-located (`.test.tsx` next to source)

**Design tokens (already in globals.css):**
```css
--bg-primary    /* page background */
--bg-elevated   /* cards, dialogs */
--bg-hover      /* hover states, drop zone hover */
--border-subtle /* dashed drop zone border */
--border-strong /* focused inputs, active drop zone */
--text-primary  /* filenames */
--text-secondary /* metadata, labels */
--text-muted    /* placeholders */
--status-info   /* processing/queued badges: #6b9bd2 */
--status-success /* complete badge: #7dab8f */
--status-error  /* failed badge: #c47070 */
--status-warning /* low confidence: #c4a265 */
```

**Existing shadcn/ui components available:** button, badge, card, separator, dialog, input, label, textarea
**No new shadcn/ui components needed for this story.**

### UX Design Requirements

**Upload Zone (investigation workspace):**
- Dashed border (2px, `--border-subtle`), centered content
- Default message: "Drag PDF files here to start your investigation"
- File picker button: primary style
- Drag hover state: background transitions to `--bg-hover`, border intensifies
- Non-PDF rejection: show warning inline, continue with valid PDFs
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Document Upload Area]

**Document Card (in list):**
- Filename (bold, `--text-primary`)
- File size (human-readable: "2.4 MB", `--text-secondary`)
- Status badge: "Queued" (`--status-info`), "Complete" (`--status-success`), "Failed" (`--status-error`)
- Upload date (`--text-sm`, `--text-muted`)
- Delete button (icon, shows on hover)

**Empty State (no documents yet):**
- Full-width drop zone with message and file picker button
- "Drag PDF files here to start your investigation"
- Minimal, warm-toned icon

**Upload Progress Feedback:**
- Per-file: show filename + small progress indicator during upload
- After upload: file appears in list with "Queued" status
- Use local state for upload progress (not TanStack Query)

**Delete Document Dialog:**
```
"Delete Document?"
"{filename}" will be permanently removed.
[Cancel]  [Delete]
```
- Cancel button: default focus (safe option)
- Delete button: destructive style (`--status-error`)
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Confirmation Dialogs]

### Scope Boundaries — What This Story Does NOT Include

**Deferred to Story 2.3 (Async Document Processing Pipeline):**
- Celery worker task for text extraction
- PyMuPDF text extraction from uploaded PDFs
- Status transitions beyond "queued" (extracting_text, complete, failed)
- Redis pub/sub event publishing
- Storing extracted text in PostgreSQL

**Deferred to Story 2.4 (Real-Time Processing Dashboard with SSE):**
- SSE endpoint for real-time status updates
- Processing dashboard with per-document phase indicators
- Live entity counter
- Auto-transition from processing view to split view

**Deferred to Story 2.5 (Extracted Text Viewer):**
- Text viewing endpoint and UI
- Document text display component

**For Story 2.2, all documents will remain in "queued" status after upload.** The processing pipeline (2.3) will transition them through extracting_text → complete/failed.

### Project Structure Notes

**Files to CREATE:**
```
apps/api/
├── app/
│   ├── models/document.py              # SQLAlchemy Document model
│   ├── schemas/document.py             # Pydantic response schemas
│   ├── services/document.py            # Upload + CRUD service
│   └── api/v1/documents.py             # FastAPI router with upload/list/get/delete
├── migrations/versions/
│   └── 002_create_documents_table.py   # Alembic migration
└── tests/
    ├── api/test_documents.py           # API endpoint tests
    └── services/test_document_service.py # Service layer tests

apps/web/src/
├── components/investigation/
│   ├── DocumentUploadZone.tsx
│   ├── DocumentUploadZone.test.tsx
│   ├── DocumentList.tsx
│   ├── DocumentList.test.tsx
│   ├── DocumentCard.tsx
│   ├── DocumentCard.test.tsx
│   └── DeleteDocumentDialog.tsx
└── hooks/
    └── useDocuments.ts
```

**Files to MODIFY:**
```
apps/api/app/models/__init__.py          # Export Document
apps/api/app/models/investigation.py     # Add documents relationship
apps/api/app/api/v1/router.py            # Register documents router
apps/api/app/api/v1/investigations.py    # Update _to_response for real document_count
apps/api/app/exceptions.py               # Add DocumentNotFoundError
apps/api/tests/conftest.py               # Add document test fixtures
apps/web/src/routes/investigations/$id.tsx # Replace placeholder with upload zone + doc list
apps/web/src/lib/api-types.generated.ts  # Regenerated with document types
```

### Naming Conventions

| Context | Convention | Example |
|---------|-----------|---------|
| Python files | snake_case | `document.py` |
| Python classes | PascalCase | `Document`, `DocumentService` |
| Python functions | snake_case | `upload_document()` |
| PostgreSQL tables | snake_case, plural | `documents` |
| PostgreSQL columns | snake_case | `investigation_id`, `size_bytes` |
| React components | PascalCase files | `DocumentUploadZone.tsx` |
| React hooks | camelCase with `use` prefix | `useDocuments.ts` |
| Test files | co-located `.test.tsx` | `DocumentList.test.tsx` |
| API endpoints | plural nouns, nested | `/api/v1/investigations/{id}/documents` |
| Query keys | hierarchical arrays | `['documents', investigationId]` |

### Previous Story Intelligence

**From Story 2.1 (CRITICAL — follow these patterns):**
- SQLAlchemy 2.0 `Mapped[]` type hints — NOT legacy `Column()` definitions
- Pydantic v2 with `model_config = {"from_attributes": True}` for ORM conversion
- Service layer: `__init__(self, db: AsyncSession)`, all methods async
- Router: `APIRouter(prefix="/investigations", tags=["investigations"])`, dependency injection via `Depends(get_db)`
- Helper `_to_response()` function in router converts ORM model to schema
- `STORAGE_ROOT` configurable via env var with fallback to `"storage"`
- Test pattern: `TestClient(app)` with `app.dependency_overrides` for mocking
- Cascading delete order: external services first, PostgreSQL last
- All tests use `AsyncMock()` for async service methods
- `updated_at` trigger function in PostgreSQL migration
- shadcn/ui CLI: `pnpm dlx shadcn@latest add`

**From Story 1.3 (frontend patterns):**
- TanStack Query: staleTime 30s, gcTime 5m, retry 1
- openapi-fetch client at `src/lib/api-client.ts` with `baseUrl=""`
- Vitest + Testing Library configured
- Test helpers: `createTestQueryClient()` + `renderWithProviders()` in `src/test-utils.tsx`
- CSS Grid root layout: `grid-rows-[auto_1fr_auto]`

**Git Intelligence (last 4 commits):**
```
9ffcec7 feat: Story 1.3 — frontend shell with system status page
77b379e feat: Story 1.2 — backend health checks & model readiness
4feffbb feat: Story 1.1 — monorepo scaffolding & Docker Compose infrastructure
8b59842 Product idea
```
- Clean linear history, TypeScript strict mode passing, all tests passing
- Story 2.1 code is in working tree (not yet committed) — build on it

**Dependencies already available:**
- Backend: `pymupdf>=1.27.1` (already in pyproject.toml), `fastapi[standard]`, `sqlalchemy[asyncio]`, `loguru`, `pydantic`
- Frontend: `@tanstack/react-query`, `@tanstack/react-router`, `openapi-fetch`

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic 2: Investigation & Document Management]
- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.2: PDF Upload with Immutable Storage]
- [Source: _bmad-output/planning-artifacts/architecture.md#Document Storage — storage/{investigation_id}/{document_id}.pdf]
- [Source: _bmad-output/planning-artifacts/architecture.md#API Endpoints — Document Upload POST multipart]
- [Source: _bmad-output/planning-artifacts/architecture.md#PostgreSQL Schema — documents table]
- [Source: _bmad-output/planning-artifacts/architecture.md#Document Processing States — queued/extracting_text/complete/failed]
- [Source: _bmad-output/planning-artifacts/architecture.md#API Response Format — RFC 7807, list format]
- [Source: _bmad-output/planning-artifacts/architecture.md#SHA-256 Checksum — immutability verification]
- [Source: _bmad-output/planning-artifacts/architecture.md#Frontend Data Layer — TanStack Query, openapi-fetch]
- [Source: _bmad-output/planning-artifacts/architecture.md#Monorepo & Directory Structure]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Document Upload Area — drag-and-drop zone]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Document Status Indicators — queued/complete/failed badges]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Empty States — "Drag PDF files here to start your investigation"]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Color Palette — status-info, status-success, status-error tokens]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Confirmation Dialogs — Cancel focused, Delete destructive]
- [Source: _bmad-output/planning-artifacts/prd.md#FR5 — upload multiple PDFs simultaneously]
- [Source: _bmad-output/planning-artifacts/prd.md#FR6 — drag and drop folder of PDFs]
- [Source: _bmad-output/planning-artifacts/prd.md#FR8 — immutable document storage]
- [Source: _bmad-output/planning-artifacts/prd.md#NFR18 — byte-for-byte identical storage verified by checksum]
- [Source: _bmad-output/planning-artifacts/prd.md#NFR19 — never modify, re-encode, compress source documents]
- [Source: _bmad-output/planning-artifacts/prd.md#NFR3 — bulk upload 50+ documents without failure]
- [Source: _bmad-output/implementation-artifacts/2-1-investigation-crud-api-list-view.md#Dev Notes — all established patterns]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

No debug issues encountered. All tests passed on first run.

### Completion Notes List

- Implemented Document SQLAlchemy model with UUID PK, FK to investigations (CASCADE), all required fields including sha256_checksum for immutability verification
- Created Alembic migration 002 with documents table, investigation_id index, and updated_at trigger (reuses function from migration 001)
- Implemented DocumentService with upload (file storage + SHA-256 + page count via PyMuPDF), list (paginated), get, delete (file + DB record)
- Created REST endpoints: POST (multipart upload with PDF MIME + magic byte validation), GET list, GET single, DELETE — all nested under /investigations/{id}/documents
- Updated investigation _to_response to compute real document_count from DB instead of hardcoded 0
- Added DocumentNotFoundError to exceptions.py following RFC 7807 pattern
- Created frontend DocumentUploadZone with drag-and-drop, file picker, client-side PDF validation, upload progress feedback
- Created DocumentList, DocumentCard (with status badges, human-readable sizes, delete confirmation), DeleteDocumentDialog
- Created useDocuments, useUploadDocuments, useDeleteDocument hooks with TanStack Query cache invalidation
- Updated investigation detail route to replace placeholder with functional upload zone + document list
- Updated api-types.generated.ts with document endpoints and schemas
- All 70 backend tests pass (8 new document API tests + 7 new document service tests)
- All 37 frontend tests pass (4 upload zone + 3 list + 5 card tests)
- TypeScript strict mode passes with no errors

### File List

**New files:**
- apps/api/app/models/document.py
- apps/api/app/schemas/document.py
- apps/api/app/services/document.py
- apps/api/app/api/v1/documents.py
- apps/api/migrations/versions/002_create_documents_table.py
- apps/api/tests/api/test_documents.py
- apps/api/tests/services/test_document_service.py
- apps/web/src/hooks/useDocuments.ts
- apps/web/src/components/investigation/DocumentUploadZone.tsx
- apps/web/src/components/investigation/DocumentUploadZone.test.tsx
- apps/web/src/components/investigation/DocumentList.tsx
- apps/web/src/components/investigation/DocumentList.test.tsx
- apps/web/src/components/investigation/DocumentCard.tsx
- apps/web/src/components/investigation/DocumentCard.test.tsx
- apps/web/src/components/investigation/DeleteDocumentDialog.tsx

**Modified files:**
- apps/api/app/models/__init__.py — Export Document
- apps/api/app/models/investigation.py — Add documents relationship
- apps/api/app/exceptions.py — Add DocumentNotFoundError
- apps/api/app/api/v1/router.py — Register documents router
- apps/api/app/api/v1/investigations.py — Async _to_response with real document_count
- apps/api/tests/conftest.py — Add document fixtures
- apps/web/src/lib/api-types.generated.ts — Add document endpoints and schemas
- apps/web/src/routes/investigations/$id.tsx — Replace placeholder with upload zone + document list

## Change Log

- 2026-03-08: Story 2.2 implemented — PDF upload with immutable storage. Backend: Document model, Alembic migration, service layer, REST API with multipart upload, SHA-256 checksums, PyMuPDF page count. Frontend: drag-and-drop upload zone, document list with status badges, delete with confirmation. 107 tests passing (70 backend + 37 frontend).
- 2026-03-08: Code review fixes (Claude Opus 4.6) — 3 HIGH + 5 MEDIUM issues resolved:
  - H1: Added 200MB file size validation (backend + frontend)
  - H2: Added try/except around individual uploads for partial failure resilience (AC4)
  - H3: Upload response now returns both items and errors (UploadDocumentsResponse)
  - M1: Error responses use DomainError (InvalidFileTypeError) for RFC 7807 compliance
  - M2: Fixed N+1 query in investigation list (batch document count query)
  - M3: Streaming file upload — SHA-256 computed inline during chunked write (no full in-memory read)
  - M4: PyMuPDF page count runs in thread executor (asyncio.to_thread)
  - M5: Added 3 new backend tests (magic bytes, oversized file, mixed upload) + 1 frontend test (oversized file)
  - Tests: 73 backend + 38 frontend = 111 total, all passing
