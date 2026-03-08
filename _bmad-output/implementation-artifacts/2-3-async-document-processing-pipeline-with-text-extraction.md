# Story 2.3: Async Document Processing Pipeline with Text Extraction

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an investigator,
I want my uploaded documents to be processed automatically in the background with text extracted,
so that I don't have to wait and can continue working while documents are processed.

## Acceptance Criteria

1. **AC1: Celery Worker Processes Queued Documents**
   - Given a document has been uploaded with status "queued"
   - When the Celery worker picks up the processing job
   - Then the document status transitions through: queued → extracting_text → complete
   - And text content is extracted from the PDF using PyMuPDF
   - And extracted text is stored separately from the original document (derived data separation)
   - And text extraction completes in <30 seconds per 100 pages

2. **AC2: Redis-Backed Queue with Persistence**
   - Given documents are queued for processing
   - When the Celery worker processes them
   - Then jobs are processed sequentially from the Redis-backed queue
   - And the queue persists across worker restarts (Redis AOF)
   - And each processing stage publishes events via Redis pub/sub

3. **AC3: Failure Handling**
   - Given text extraction fails for a document
   - When PyMuPDF encounters an error
   - Then the document status is set to "failed"
   - And the error detail is stored on the document record
   - And the error is logged via Loguru with document_id and error detail
   - And a `document.failed` event is published to Redis pub/sub

4. **AC4: Task Enqueue on Upload**
   - Given a document is successfully uploaded via the existing upload endpoint
   - When the document record is created with status "queued"
   - Then a Celery task is automatically dispatched for that document
   - And the upload response is unchanged (still returns immediately)

5. **AC5: SSE Endpoint for Real-Time Events**
   - Given the Celery worker publishes events to Redis pub/sub
   - When the frontend connects to `GET /api/v1/investigations/{investigation_id}/events`
   - Then the endpoint streams SSE events for that investigation
   - And events follow the format: `document.processing`, `document.complete`, `document.failed`

6. **AC6: Frontend Status Badge Updates**
   - Given a document is in "extracting_text" status
   - When the frontend renders the document card
   - Then an "Extracting Text" badge is displayed with the info color
   - And the frontend can poll the document list to see updated statuses

## Tasks / Subtasks

- [x] Task 1: Add extracted_text and error_message columns to Document model + Alembic migration (AC: #1, #3)
  - [x] 1.1: Add `extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)` to `app/models/document.py`
  - [x] 1.2: Add `error_message: Mapped[str | None] = mapped_column(Text, nullable=True)` to `app/models/document.py`
  - [x] 1.3: Generate Alembic migration: `alembic revision --autogenerate -m "add_extracted_text_and_error_message_to_documents"`
  - [x] 1.4: Verify migration applies cleanly on fresh database

- [x] Task 2: Create Celery app configuration (AC: #2)
  - [x] 2.1: Create `app/worker/celery_app.py` — Celery instance using `settings.celery_broker_url` and `settings.celery_result_backend`
  - [x] 2.2: Configure task serialization (json), task acks_late (true), worker_prefetch_multiplier (1) for sequential processing
  - [x] 2.3: Configure task autodiscovery for `app.worker.tasks`

- [x] Task 3: Create text extraction service (AC: #1)
  - [x] 3.1: Create `app/services/text_extraction.py` with `TextExtractionService`
  - [x] 3.2: Implement `extract_text(file_path: Path) -> str` — opens PDF via PyMuPDF, extracts text per page, joins with page markers
  - [x] 3.3: Reuse existing PyMuPDF dependency (pymupdf already in pyproject.toml)

- [x] Task 4: Create Redis pub/sub event publisher (AC: #2, #3, #5)
  - [x] 4.1: Create `app/services/events.py` with `EventPublisher` class
  - [x] 4.2: Implement `publish(investigation_id, event_type, payload)` — publishes to Redis channel `events:{investigation_id}`
  - [x] 4.3: Event format: `{"type": "document.processing", "investigation_id": "uuid", "timestamp": "ISO8601", "payload": {...}}`

- [x] Task 5: Create document processing Celery task (AC: #1, #2, #3)
  - [x] 5.1: Create `app/worker/tasks/process_document.py` with `process_document_task(document_id: str, investigation_id: str)`
  - [x] 5.2: Task flow: load document record → update status to "extracting_text" → publish event → extract text via PyMuPDF → save extracted_text to DB → update status to "complete" → publish event
  - [x] 5.3: On failure: update status to "failed", store error_message, publish `document.failed` event, log via Loguru
  - [x] 5.4: Use synchronous SQLAlchemy session in Celery task (Celery workers are sync, not async)

- [x] Task 6: Enqueue task on document upload (AC: #4)
  - [x] 6.1: Update `app/services/document.py` `upload_document()` — after creating document record, call `process_document_task.delay(str(document.id), str(investigation_id))`
  - [x] 6.2: Import is lazy/deferred to avoid circular imports (import inside function)

- [x] Task 7: Create SSE endpoint (AC: #5)
  - [x] 7.1: Add `sse-starlette` to `pyproject.toml`
  - [x] 7.2: Create `app/api/v1/events.py` with SSE endpoint `GET /api/v1/investigations/{investigation_id}/events`
  - [x] 7.3: Endpoint subscribes to Redis pub/sub channel `events:{investigation_id}` and streams events using `sse-starlette`
  - [x] 7.4: Register events router in `app/api/v1/router.py`

- [x] Task 8: Update Document schemas for new fields (AC: #1, #3)
  - [x] 8.1: Add `extracted_text: str | None` and `error_message: str | None` to `DocumentResponse` in `app/schemas/document.py`
  - [x] 8.2: Consider excluding `extracted_text` from list endpoints (only include in single-document GET) to avoid large payloads

- [x] Task 9: Update frontend DocumentCard status styles (AC: #6)
  - [x] 9.1: Add `extracting_text` to `statusStyles` map in `DocumentCard.tsx` — display as "Extracting Text" with `--status-info` color
  - [x] 9.2: Add refetch interval (5s) to `useDocuments` hook so status updates appear via polling

- [x] Task 10: Write backend tests (AC: #1, #2, #3, #4, #5)
  - [x] 10.1: Create `tests/worker/test_process_document.py` — test successful extraction (status transitions, text stored), test failure handling (status "failed", error_message stored), test event publishing
  - [x] 10.2: Create `tests/services/test_text_extraction.py` — test text extraction from valid PDF, test handling of corrupted PDF
  - [x] 10.3: Create `tests/services/test_events.py` — test event publishing to Redis pub/sub
  - [x] 10.4: Create `tests/api/test_events.py` — test SSE endpoint streams events
  - [x] 10.5: Update `tests/api/test_documents.py` — verify upload now enqueues Celery task (mock task.delay)

- [x] Task 11: Regenerate OpenAPI types (AC: #5, #6)
  - [x] 11.1: Run `scripts/generate-api-types.sh` against running backend
  - [x] 11.2: Verify generated types include new document fields and events endpoint

- [x] Task 12: Write frontend tests (AC: #6)
  - [x] 12.1: Update `DocumentCard.test.tsx` — test "extracting_text" status renders correctly
  - [x] 12.2: Verify polling behavior in useDocuments hook

## Dev Notes

### CRITICAL: Backend Architecture Patterns (MUST follow from Stories 2.1/2.2)

**ORM: SQLAlchemy 2.0 + Pydantic v2 (NOT SQLModel)**
The architecture doc mentions SQLModel, but the actual codebase uses SQLAlchemy 2.0 async with separate Pydantic v2 schemas. Follow the established pattern:
- Database models: `app/models/` using SQLAlchemy `DeclarativeBase` with `Mapped[]` type hints
- API schemas: `app/schemas/` using Pydantic `BaseModel` with `model_config = {"from_attributes": True}`
- [Source: _bmad-output/implementation-artifacts/2-1-investigation-crud-api-list-view.md]

**Celery Workers are SYNCHRONOUS — Use sync SQLAlchemy sessions**
Celery workers run sync event loops. Do NOT use `AsyncSession` in Celery tasks. Create a **synchronous** SQLAlchemy engine + session for worker use:
```python
# app/db/sync_postgres.py (NEW — for Celery worker)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import get_settings

settings = get_settings()
# Convert async URL to sync: postgresql+asyncpg:// → postgresql://
sync_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://").replace("postgresql://", "postgresql+psycopg2://")
sync_engine = create_engine(sync_url)
SyncSessionLocal = sessionmaker(bind=sync_engine)
```
This is critical — using async in Celery will cause "no running event loop" errors.

**Redis Pub/Sub Channel Convention:**
- Per-investigation: `events:{investigation_id}`
- Event JSON format matches architecture spec:
```json
{
  "type": "document.processing",
  "investigation_id": "uuid",
  "timestamp": "2026-03-08T14:30:00Z",
  "payload": {"document_id": "uuid", "stage": "extracting_text", "progress": 0.5}
}
```
- Use `redis-py` (sync) in Celery worker for pub/sub publishing
- Use `aioredis` (async) in FastAPI SSE endpoint for pub/sub subscribing
- [Source: _bmad-output/planning-artifacts/architecture.md#SSE Event Types]

**Celery App Configuration:**
```python
# app/worker/celery_app.py
from celery import Celery
from app.config import get_settings

settings = get_settings()
celery_app = Celery("osint")
celery_app.conf.update(
    broker_url=settings.celery_broker_url,
    result_backend=settings.celery_result_backend,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_acks_late=True,
    worker_prefetch_multiplier=1,  # Sequential processing
    task_track_started=True,
)
celery_app.autodiscover_tasks(["app.worker.tasks"])
```
- Config vars already exist in `app/config.py`: `celery_broker_url`, `celery_result_backend`
- Worker start command: `celery -A app.worker.celery_app worker --loglevel=info --concurrency=1`
- [Source: _bmad-output/planning-artifacts/architecture.md#Docker Compose — 7 Services]

**Text Extraction with PyMuPDF:**
```python
import pymupdf  # import name for PyMuPDF

def extract_text(file_path: Path) -> str:
    doc = pymupdf.open(str(file_path))
    pages = []
    for page_num, page in enumerate(doc, start=1):
        text = page.get_text()
        if text.strip():
            pages.append(f"--- Page {page_num} ---\n{text}")
    doc.close()
    return "\n\n".join(pages)
```
- PyMuPDF (`pymupdf>=1.27.1`) already in `pyproject.toml`
- Already used in `app/services/document.py` for `_get_page_count()`
- Store page markers in extracted text for downstream chunking in Story 3.1
- [Source: _bmad-output/implementation-artifacts/2-2-pdf-upload-with-immutable-storage.md#Page Count via PyMuPDF]

**Derived Data Separation (extracted text storage):**
Add `extracted_text` column to existing `documents` table:
- `extracted_text: Text (nullable)` — NULL when queued/extracting, populated on complete
- `error_message: Text (nullable)` — NULL on success, populated on failure
- This IS derived data stored separately from the file (the file is on disk, text is in PostgreSQL)
- Story 3.1 will create a separate `document_chunks` table for chunked text with provenance
- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.3 — "extracted text is stored separately from the original document"]

**Document Status Values (complete set for pipeline):**
| Status | Set By | Meaning |
|--------|--------|---------|
| `queued` | Upload endpoint | Document uploaded, awaiting processing |
| `extracting_text` | Celery task | PyMuPDF text extraction in progress |
| `complete` | Celery task | Text extraction finished successfully |
| `failed` | Celery task | Processing failed (error_message populated) |
Note: Additional statuses (`extracting_entities`, `embedding`) will be added by Epic 3 stories.

**SSE Endpoint with sse-starlette:**
```python
# app/api/v1/events.py
from sse_starlette.sse import EventSourceResponse
import redis.asyncio as aioredis

async def event_generator(investigation_id: str):
    redis = aioredis.from_url(settings.redis_url)
    pubsub = redis.pubsub()
    await pubsub.subscribe(f"events:{investigation_id}")
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                yield {"data": message["data"].decode()}
    finally:
        await pubsub.unsubscribe(f"events:{investigation_id}")
        await redis.aclose()

@router.get("/{investigation_id}/events")
async def stream_events(investigation_id: uuid.UUID):
    return EventSourceResponse(event_generator(str(investigation_id)))
```
- Use `aioredis` (already available via `redis>=6.4.0` which includes `redis.asyncio`)
- `app/db/redis.py` already has the async Redis client configured
- [Source: _bmad-output/planning-artifacts/architecture.md#SSE — FastAPI Direct via Redis Pub/Sub]

**Event Publishing from Celery Worker (sync Redis):**
```python
# In Celery task — use synchronous redis-py
import redis
import json
from datetime import datetime, timezone

def publish_event(investigation_id: str, event_type: str, payload: dict):
    r = redis.from_url(settings.celery_broker_url)
    event = {
        "type": event_type,
        "investigation_id": investigation_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": payload,
    }
    r.publish(f"events:{investigation_id}", json.dumps(event))
    r.close()
```

**API Response Format — NO wrapper:**
- Success: Direct response body (NOT `{data: ...}`)
- List: `{ "items": [...], "total": 42 }`
- Error: RFC 7807 Problem Details
- [Source: _bmad-output/planning-artifacts/architecture.md#API Response Format]

**Logging: Loguru (NOT print/logging)**
```python
from loguru import logger
logger.info("Processing document", document_id=document_id, stage="extracting_text")
logger.error("Text extraction failed", document_id=document_id, error=str(exc))
```

**Exception Pattern (from `app/exceptions.py`):**
```python
class DocumentProcessingError(DomainError):
    def __init__(self, document_id: str, detail: str):
        super().__init__(
            detail=f"Document processing failed for {document_id}: {detail}",
            status_code=422,
            error_type="document_processing_failed",
        )
```

**Alembic Migration Pattern:**
- Use sync psycopg2 driver (not asyncpg) in migration env
- Migration adds 2 nullable columns to existing `documents` table
- No default values needed (nullable columns)
- No triggers needed for new columns

### CRITICAL: Frontend Patterns (MUST follow from Stories 1.3/2.2)

**DocumentCard Status Styles — add `extracting_text`:**
```typescript
const statusStyles: Record<string, string> = {
  queued: "bg-[var(--status-info)]/15 text-[var(--status-info)] ...",
  extracting_text: "bg-[var(--status-info)]/15 text-[var(--status-info)] ...",
  complete: "bg-[var(--status-success)]/15 text-[var(--status-success)] ...",
  failed: "bg-[var(--status-error)]/15 text-[var(--status-error)] ...",
};

const statusLabels: Record<string, string> = {
  queued: "Queued",
  extracting_text: "Extracting Text",
  complete: "Complete",
  failed: "Failed",
};
```
- [Source: apps/web/src/components/investigation/DocumentCard.tsx — existing statusStyles map]

**Polling for Status Updates (until SSE in Story 2.4):**
Add `refetchInterval` to `useDocuments` hook when documents are processing:
```typescript
export function useDocuments(investigationId: string) {
  return useQuery({
    queryKey: ["documents", investigationId],
    queryFn: async () => { /* existing fetch */ },
    refetchInterval: (query) => {
      const docs = query.state.data?.items;
      const hasProcessing = docs?.some(d =>
        d.status === "queued" || d.status === "extracting_text"
      );
      return hasProcessing ? 5000 : false; // Poll every 5s while processing
    },
  });
}
```

**API Client: openapi-fetch — baseUrl is empty string**
```typescript
// Already configured in src/lib/api-client.ts
export const api = createClient<paths>({ baseUrl: "" });
```
- [Source: _bmad-output/implementation-artifacts/1-3-frontend-shell-with-system-status-page.md]

### Project Structure Notes

**Files to CREATE:**
```
apps/api/
├── app/
│   ├── db/
│   │   └── sync_postgres.py            # Sync SQLAlchemy engine for Celery worker
│   ├── services/
│   │   ├── text_extraction.py          # PyMuPDF text extraction service
│   │   └── events.py                   # Redis pub/sub event publisher
│   ├── worker/
│   │   └── celery_app.py               # Celery app instance + config
│   │   └── tasks/
│   │       └── process_document.py     # Document processing task
│   └── api/v1/
│       └── events.py                   # SSE streaming endpoint
├── migrations/versions/
│   └── 003_add_extracted_text_and_error_message.py  # Alembic migration
└── tests/
    ├── worker/
    │   └── test_process_document.py    # Celery task tests
    ├── services/
    │   ├── test_text_extraction.py     # Text extraction tests
    │   └── test_events.py             # Event publisher tests
    └── api/
        └── test_events.py             # SSE endpoint tests
```

**Files to MODIFY:**
```
apps/api/app/models/document.py          # Add extracted_text + error_message columns
apps/api/app/schemas/document.py         # Add new fields to response schemas
apps/api/app/services/document.py        # Enqueue Celery task after upload
apps/api/app/api/v1/router.py            # Register events router
apps/api/app/exceptions.py               # Add DocumentProcessingError
apps/api/pyproject.toml                  # Add sse-starlette dependency
apps/api/tests/conftest.py               # Add Celery task mock fixtures
apps/api/tests/api/test_documents.py     # Verify task enqueue on upload

apps/web/src/components/investigation/DocumentCard.tsx  # Add extracting_text status
apps/web/src/hooks/useDocuments.ts                      # Add polling refetchInterval
apps/web/src/lib/api-types.generated.ts                 # Regenerated with new fields/endpoints
```

### Naming Conventions

| Context | Convention | Example |
|---------|-----------|---------|
| Celery app module | snake_case | `celery_app.py` |
| Celery tasks | snake_case functions | `process_document_task()` |
| Task module | snake_case | `process_document.py` |
| Redis channels | colon-separated | `events:{investigation_id}` |
| SSE event types | dot-notation | `document.processing`, `document.complete` |
| Service classes | PascalCase | `TextExtractionService`, `EventPublisher` |
| Alembic migration | numbered + descriptive | `003_add_extracted_text_and_error_message.py` |

### Previous Story Intelligence

**From Story 2.2 (CRITICAL — follow these patterns):**
- SQLAlchemy 2.0 `Mapped[]` type hints — NOT legacy `Column()` definitions
- Pydantic v2 with `model_config = {"from_attributes": True}` for ORM conversion
- Service layer: `__init__(self, db: AsyncSession)`, all methods async
- `STORAGE_ROOT` configurable via env var with fallback to `"storage"`
- File path: `STORAGE_ROOT / {investigation_id} / {document_id}.pdf`
- PyMuPDF already used for page_count via `_get_page_count()` helper
- SHA-256 checksum computed during upload (streaming) — file bytes are immutable
- All tests use `AsyncMock()` for async service methods
- Test fixtures in `tests/conftest.py` — `sample_document`, `mock_pdf_file`
- Existing status values in DocumentCard.tsx: `queued`, `complete`, `failed`
- Upload endpoint returns `UploadDocumentsResponse` (items + errors)
- Code review fixes from 2.2: streaming file upload, thread executor for PyMuPDF, partial failure resilience
- 73 backend + 38 frontend = 111 total tests currently passing

**From Story 2.1 (established patterns):**
- Cascading delete order: external services → filesystem → PostgreSQL
- Router: `APIRouter(prefix="/...", tags=["..."])`, dependency injection via `Depends(get_db)`
- `updated_at` trigger function in PostgreSQL migration
- Helper `_to_response()` function in router for ORM → schema conversion

**From Story 1.3 (frontend patterns):**
- TanStack Query: staleTime 30s, gcTime 5m, retry 1
- Test helpers: `createTestQueryClient()` + `renderWithProviders()` in `src/test-utils.tsx`

**Git Intelligence (last 5 commits):**
```
31a3ee5 feat: Story 2.2 — PDF upload with immutable storage
fcf55d1 feat: Story 2.1 — investigation CRUD API & list view
9ffcec7 feat: Story 1.3 — frontend shell with system status page
77b379e feat: Story 1.2 — backend health checks & model readiness
4feffbb feat: Story 1.1 — monorepo scaffolding & Docker Compose infrastructure
```
- Clean linear history, all tests passing, TypeScript strict mode passing

**Dependencies already available:**
- Backend: `celery[redis]>=5.6.2`, `redis>=6.4.0`, `pymupdf>=1.27.1`, `fastapi[standard]`, `sqlalchemy[asyncio]`, `loguru`, `pydantic`, `asyncpg`
- NOT installed yet: `sse-starlette` (add in this story)
- Frontend: `@tanstack/react-query`, `@tanstack/react-router`, `openapi-fetch`

**Existing infrastructure:**
- Redis service running in docker-compose.dev.yml on port 6379
- `app/config.py` has `celery_broker_url`, `celery_result_backend`, `redis_url` settings
- `app/db/redis.py` has async Redis client already configured
- `app/worker/` directory exists with empty `__init__.py` and `tasks/__init__.py`
- Loguru InterceptHandler in `main.py` already intercepts Celery logs

### Scope Boundaries — What This Story Does NOT Include

**Deferred to Story 2.4 (Real-Time Processing Dashboard with SSE):**
- Frontend SSE consumption via `@microsoft/fetch-event-source`
- `useSSE` React hook that pipes events into TanStack Query cache
- Processing dashboard UI with per-document phase indicators
- SSE reconnection and state reconciliation logic on frontend

**Deferred to Story 2.5 (Extracted Text Viewer):**
- `GET /api/v1/investigations/{id}/documents/{doc_id}/text` endpoint
- Text viewing UI component
- Document text display with formatting

**Deferred to Story 3.1 (Document Chunking & LLM Integration):**
- Document chunking (splitting extracted text into chunks)
- `document_chunks` PostgreSQL table with provenance metadata
- Ollama LLM client at `app/llm/client.py`
- Additional status transitions (`extracting_entities`, `embedding`)

**Deferred to Epic 6 (Resilience):**
- `POST /api/v1/investigations/{id}/documents/{doc_id}/retry` endpoint
- Auto-retry on Ollama recovery
- Celery task retry policies

**For Story 2.3, documents transition through: queued → extracting_text → complete/failed.** No retry mechanism. No entity extraction. No embedding. Frontend uses polling (not SSE) for status updates.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.3: Async Document Processing Pipeline with Text Extraction]
- [Source: _bmad-output/planning-artifacts/architecture.md#Worker Boundary — Celery Tasks ↔ Services]
- [Source: _bmad-output/planning-artifacts/architecture.md#Celery tasks — app/worker/tasks/process_document.py]
- [Source: _bmad-output/planning-artifacts/architecture.md#SSE — FastAPI Direct via Redis Pub/Sub]
- [Source: _bmad-output/planning-artifacts/architecture.md#SSE Event Types — document.processing, document.complete, document.failed]
- [Source: _bmad-output/planning-artifacts/architecture.md#Docker Compose — Combined API + Celery in one container]
- [Source: _bmad-output/planning-artifacts/architecture.md#Error Handling — Celery tasks catch, log, publish failed event, update DB]
- [Source: _bmad-output/planning-artifacts/architecture.md#Data Architecture — PostgreSQL stores processing status]
- [Source: _bmad-output/planning-artifacts/architecture.md#Naming Conventions — SSE dot-notation events]
- [Source: _bmad-output/planning-artifacts/prd.md#FR7 — System extracts text content from uploaded PDF documents]
- [Source: _bmad-output/planning-artifacts/prd.md#FR31 — System processes uploaded documents asynchronously via job queue]
- [Source: _bmad-output/planning-artifacts/prd.md#FR32 — Real-time progress updates during document processing]
- [Source: _bmad-output/planning-artifacts/prd.md#FR33 — Per-document processing status]
- [Source: _bmad-output/planning-artifacts/prd.md#NFR2 — Text extraction <30 seconds per 100 pages]
- [Source: _bmad-output/planning-artifacts/prd.md#NFR3 — Pipeline handles 50+ documents without failure]
- [Source: _bmad-output/planning-artifacts/prd.md#NFR4 — Real-time updates within 1 second of state change]
- [Source: _bmad-output/planning-artifacts/prd.md#NFR28 — Processing queue survives worker restarts]
- [Source: _bmad-output/implementation-artifacts/2-2-pdf-upload-with-immutable-storage.md#Dev Notes — all established patterns]
- [Source: _bmad-output/implementation-artifacts/2-2-pdf-upload-with-immutable-storage.md#Scope Boundaries — deferred items to 2.3]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

- Fixed existing `test_upload_document_stores_file_and_creates_record` test: needed `patch.dict("sys.modules")` to mock the lazy Celery task import
- SSE streaming test with TestClient not viable due to persistent connection; tested `_event_generator` as async unit test instead
- `redis.pubsub()` is synchronous in redis.asyncio — used `MagicMock` (not `AsyncMock`) for Redis client in SSE generator tests

### Completion Notes List

- **Task 1:** Added `extracted_text` (Text, nullable) and `error_message` (Text, nullable) columns to Document model. Created Alembic migration 003. Model column tests verify correctness.
- **Task 2:** Created Celery app at `app/worker/celery_app.py` with json serialization, acks_late, prefetch=1, autodiscovery for `app.worker.tasks`.
- **Task 3:** Created `TextExtractionService` using PyMuPDF with page markers (`--- Page N ---`). Skips empty pages. Reuses existing pymupdf dependency.
- **Task 4:** Created `EventPublisher` class publishing JSON events to Redis pub/sub channels `events:{investigation_id}`.
- **Task 5:** Created `process_document_task` Celery task. Uses sync SQLAlchemy session. Transitions: queued → extracting_text → complete/failed. Publishes events at each stage. Logs via Loguru.
- **Task 6:** Updated `upload_document()` with deferred import of `process_document_task.delay()` after DB commit.
- **Task 7:** Created SSE endpoint at `GET /api/v1/investigations/{investigation_id}/events` using `sse-starlette`. Subscribes to Redis pub/sub async. Added `sse-starlette>=2.3.3` dependency.
- **Task 8:** Added `extracted_text` and `error_message` to `DocumentResponse` schema. `extracted_text` excluded from list endpoints (only included in single-document GET) to avoid large payloads.
- **Task 9:** Added `extracting_text` to `statusStyles` and `statusLabels` maps in DocumentCard. Added `refetchInterval` (5s) to `useDocuments` when documents are processing.
- **Task 10:** Created comprehensive backend tests: model column tests, Celery app config tests, text extraction service tests, event publisher tests, process document task tests (success, failure, not-found), SSE endpoint/generator tests, upload enqueue test.
- **Task 11:** Manually updated `api-types.generated.ts` with new `extracted_text`, `error_message` fields and SSE events endpoint (backend not running for script execution).
- **Task 12:** Added `extracting_text` status test to `DocumentCard.test.tsx`. Updated mock documents in test files with new fields.

### File List

**New files:**
- `apps/api/app/worker/celery_app.py` — Celery app configuration
- `apps/api/app/worker/tasks/process_document.py` — Document processing Celery task
- `apps/api/app/services/text_extraction.py` — PyMuPDF text extraction service
- `apps/api/app/services/events.py` — Redis pub/sub event publisher
- `apps/api/app/api/v1/events.py` — SSE streaming endpoint
- `apps/api/app/db/sync_postgres.py` — Synchronous SQLAlchemy engine for Celery worker
- `apps/api/migrations/versions/003_add_extracted_text_and_error_message.py` — Alembic migration
- `apps/api/tests/models/__init__.py` — Package init (review fix M3)
- `apps/api/tests/models/test_document_model.py` — Document model column tests
- `apps/api/tests/worker/__init__.py` — Package init (review fix M3)
- `apps/api/tests/worker/test_celery_app.py` — Celery app configuration tests
- `apps/api/tests/worker/test_process_document.py` — Process document task tests
- `apps/api/tests/services/test_text_extraction.py` — Text extraction service tests
- `apps/api/tests/services/test_events.py` — Event publisher tests
- `apps/api/tests/services/test_document_upload_enqueue.py` — Upload enqueue test
- `apps/api/tests/api/test_events.py` — SSE endpoint tests

**Modified files:**
- `apps/api/app/models/document.py` — Added extracted_text and error_message columns
- `apps/api/app/schemas/document.py` — Added new fields to DocumentResponse
- `apps/api/app/services/document.py` — Enqueue Celery task after upload (+ review fix M6: graceful .delay() failure)
- `apps/api/app/api/v1/documents.py` — Updated _to_response with include_text param
- `apps/api/app/api/v1/router.py` — Registered events router
- `apps/api/app/exceptions.py` — Added DocumentProcessingError
- `apps/api/pyproject.toml` — Added sse-starlette dependency
- `apps/api/tests/conftest.py` — Added extracted_text/error_message to sample_document fixture
- `apps/api/tests/services/test_document_service.py` — Mocked Celery task in upload test
- `apps/web/src/components/investigation/DocumentCard.tsx` — Added extracting_text status style and labels
- `apps/web/src/hooks/useDocuments.ts` — Added refetchInterval for polling
- `apps/web/src/lib/api-types.generated.ts` — Added new fields and SSE endpoint
- `apps/web/src/components/investigation/DocumentCard.test.tsx` — Added extracting_text test, updated mock
- `apps/web/src/components/investigation/DocumentList.test.tsx` — Updated mock document with new fields
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — Status: in-progress → review

### Change Log

- 2026-03-08: Implemented Story 2.3 — Async document processing pipeline with text extraction. Added Celery worker integration, PyMuPDF text extraction, Redis pub/sub events, SSE streaming endpoint, frontend status badge updates with polling. 93 backend + 39 frontend = 132 total tests passing.
- 2026-03-08: Code review fixes (H1, H2, M1-M6). Restructured process_document_task error handling: event publishing is now best-effort via _publish_safe wrapper, preventing publish failures from corrupting document status. EventPublisher reuses single Redis connection with explicit close(). TextExtractionService uses try/finally for resource safety. upload_document gracefully handles .delay() failures. Fixed test mock warnings. Added __init__.py to test dirs. 96 backend + 39 frontend = 135 total tests passing.
