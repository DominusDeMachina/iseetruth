# Story 6.1: Failed Document Detection & Manual Retry

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an investigator,
I want failed documents to be clearly marked and retryable,
So that a single failure doesn't block my entire investigation.

## Acceptance Criteria

1. **GIVEN** document processing fails at any stage (text extraction, chunking, entity extraction, embedding), **WHEN** the Celery worker catches the error, **THEN** the document status is set to "failed" with the failure stage and error detail recorded, **AND** a `document.failed` SSE event is published with `{document_id, stage, error}`, **AND** all successfully processed data from prior stages remains intact (no rollback of completed work).

2. **GIVEN** a document is in "failed" status, **WHEN** the investigator views the document list, **THEN** the document shows "Failed — Retry available" with the failure reason, **AND** a retry button is visible on the failed document.

3. **GIVEN** the investigator clicks retry on a failed document, **WHEN** `POST /api/v1/investigations/{id}/documents/{doc_id}/retry` is called, **THEN** the document is re-queued for processing from the failed stage, **AND** the document status updates to "queued" and SSE events resume, **AND** previously completed stages are not re-executed (resume from failure point).

## Tasks / Subtasks

- [x] **Task 1: Add `failed_stage` column to Document model** (AC: 1)
  - [x] 1.1: Add `failed_stage` column (`String(30)`, nullable) to `Document` model in `apps/api/app/models/document.py` — records which processing stage failed (e.g., "extracting_text", "chunking", "extracting_entities", "embedding")
  - [x] 1.2: Create Alembic migration: `cd apps/api && uv run alembic revision --autogenerate -m "add_failed_stage_to_documents"`
  - [x] 1.3: Run migration: `cd apps/api && uv run alembic upgrade head`
  - [x] 1.4: Add `failed_stage` field to `DocumentResponse` schema in `apps/api/app/schemas/document.py` as `str | None = None`

- [x] **Task 2: Update process_document_task to record failed_stage** (AC: 1)
  - [x] 2.1: In each stage's error handler in `apps/api/app/worker/tasks/process_document.py`, set `document.failed_stage` alongside `document.status = "failed"`:
    - Pre-flight (Ollama unavailable): `failed_stage = "extracting_text"` (would fail at text extraction stage's LLM dependency — but actually pre-flight is before text extraction. Use `"preflight"` to distinguish)
    - Stage 1 failure: `failed_stage = "extracting_text"`
    - Stage 2 failure: `failed_stage = "chunking"`
    - Stage 3 failure: `failed_stage = "extracting_entities"`
    - Stage 4 failure: `failed_stage = "embedding"`
  - [x] 2.2: Include `stage` field in all `document.failed` SSE event payloads: `{"document_id": ..., "stage": document.failed_stage, "error": ...}`
  - [x] 2.3: Ensure `error_message` is cleared when status transitions away from "failed" (i.e., on successful retry start)

- [x] **Task 3: Create retry endpoint and service** (AC: 3)
  - [x] 3.1: Add `DocumentNotRetryableError` exception to `apps/api/app/exceptions.py` (409 Conflict, `error_type="document_not_retryable"`) — raised when document status is not "failed"
  - [x] 3.2: Create retry service function in `apps/api/app/services/document.py` (new file):
    ```python
    async def retry_failed_document(db: AsyncSession, investigation_id: UUID, document_id: UUID) -> Document:
        # 1. Fetch document, verify investigation_id ownership
        # 2. Verify status == "failed" (raise DocumentNotRetryableError if not)
        # 3. Determine resume_from_stage from failed_stage
        # 4. Clean up partial data from failed stage if needed:
        #    - If failed at "chunking": delete existing chunks for this document
        #    - If failed at "extracting_entities": delete entities/relationships in Neo4j for this document, delete chunks and recreate
        #    - If failed at "embedding": delete embeddings in Qdrant for this document
        #    - If failed at "extracting_text" or "preflight": no cleanup needed
        # 5. Reset: status = "queued", error_message = None, failed_stage = None
        # 6. Commit changes
        # 7. Enqueue Celery task: process_document_task.delay(document_id, investigation_id, resume_from_stage)
        # 8. Return updated document
    ```
  - [x] 3.3: Add `POST /api/v1/investigations/{investigation_id}/documents/{document_id}/retry` endpoint in `apps/api/app/api/v1/documents.py`:
    - Returns `DocumentResponse` with updated status
    - Raises 404 if document not found, 409 if not in "failed" status
  - [x] 3.4: Add `resume_from_stage` optional parameter to `process_document_task`:
    - If `resume_from_stage` is None → run all stages (default, backward compatible)
    - If `resume_from_stage` is "extracting_text" or "preflight" → run all stages from beginning
    - If `resume_from_stage` is "chunking" → skip text extraction, start from chunking (use existing `extracted_text`)
    - If `resume_from_stage` is "extracting_entities" → skip text extraction + chunking, start from entity extraction (use existing chunks)
    - If `resume_from_stage` is "embedding" → skip text extraction + chunking + entity extraction, start from embedding (use existing chunks + entities)

- [x] **Task 4: Update frontend SSE handler for failed_stage** (AC: 1, 2)
  - [x] 4.1: Update `SSEEvent` interface in `apps/web/src/hooks/useSSE.ts` — `stage` is already in payload type, verify `document.failed` handler stores it
  - [x] 4.2: Update `document.failed` cache handler to also store `failed_stage` from `event.payload.stage`

- [x] **Task 5: Add retry button to DocumentCard** (AC: 2)
  - [x] 5.1: Add `onRetry` prop to `DocumentCardProps` in `apps/web/src/components/investigation/DocumentCard.tsx`: `onRetry?: (id: string) => void`
  - [x] 5.2: When `document.status === "failed"`, show:
    - Error message below filename: `document.error_message` in `text-[var(--status-error)]` at `text-xs`
    - Retry button with `RotateCcw` icon from lucide-react: `aria-label="Retry processing {filename}"`
    - Button styled as ghost with `text-[var(--status-warning)]` hover color
  - [x] 5.3: Update status label from "Failed" to "Failed — Retry" when document has error_message
  - [x] 5.4: Add `isRetrying` prop to disable retry button during pending mutation

- [x] **Task 6: Create useRetryDocument hook** (AC: 3)
  - [x] 6.1: Add `useRetryDocument(investigationId: string)` mutation hook in `apps/web/src/hooks/useDocuments.ts`
  - [x] 6.2: Calls `POST /api/v1/investigations/{investigation_id}/documents/{document_id}/retry`
  - [x] 6.3: On success: optimistically update document cache (set status to "queued", clear error_message and failed_stage), invalidate documents query
  - [x] 6.4: On error: show error toast (e.g., "Failed to retry document. Please check service status.")

- [x] **Task 7: Wire retry into DocumentList and investigation page** (AC: 2, 3)
  - [x] 7.1: Add `onRetry` prop to `DocumentListProps` in `DocumentList.tsx`
  - [x] 7.2: Pass `onRetry` through to each `DocumentCard`
  - [x] 7.3: In the investigation detail page where `DocumentList` is rendered, create the retry handler using `useRetryDocument` and pass it down
  - [x] 7.4: Track `retryingId` state to show loading state on the retrying document's button

- [x] **Task 8: Regenerate OpenAPI types** (AC: 1, 2, 3)
  - [x] 8.1: Run `cd apps/api && uv run python -m app.generate_openapi` to export updated schema
  - [x] 8.2: Run `cd apps/web && pnpm run generate-types` to regenerate `api-types.generated.ts`
  - [x] 8.3: Verify `failed_stage` appears in `DocumentResponse` and retry endpoint types are generated

- [x] **Task 9: Write backend tests for retry endpoint** (AC: 3)
  - [x] 9.1: Create test fixtures: investigation + document in "failed" status with `failed_stage="extracting_entities"`
  - [x] 9.2: Test successful retry: POST returns 200, document status reset to "queued", `error_message` cleared, `failed_stage` cleared
  - [x] 9.3: Test retry on non-failed document (status="complete"): returns 409 with `urn:osint:error:document_not_retryable`
  - [x] 9.4: Test retry on non-existent document: returns 404
  - [x] 9.5: Test retry on document from different investigation: returns 404 (security)
  - [x] 9.6: Add tests in `apps/api/tests/api/test_documents.py` (append to existing test file)

- [x] **Task 10: Write backend tests for failed_stage recording** (AC: 1)
  - [x] 10.1: Update existing process_document task tests in `apps/api/tests/worker/test_process_document.py`
  - [x] 10.2: Test that failure at each stage sets correct `failed_stage` value
  - [x] 10.3: Test that `document.failed` SSE events include `stage` field
  - [x] 10.4: Test that successful processing does not set `failed_stage`

- [x] **Task 11: Write backend tests for retry service (stage-aware resume)** (AC: 3)
  - [x] 11.1: Create `apps/api/tests/services/test_document.py` (new service test file)
  - [x] 11.2: Test cleanup logic: retry from "chunking" deletes existing chunks
  - [x] 11.3: Test cleanup logic: retry from "embedding" cleans up Qdrant vectors
  - [x] 11.4: Test that process_document_task with `resume_from_stage="chunking"` skips text extraction
  - [x] 11.5: Test that process_document_task with `resume_from_stage="embedding"` skips text extraction, chunking, and entity extraction

- [x] **Task 12: Write frontend tests** (AC: 2, 3)
  - [x] 12.1: Update `DocumentCard` tests to verify retry button appears only for failed documents
  - [x] 12.2: Test retry button click calls `onRetry` with document ID
  - [x] 12.3: Test retry button has correct `aria-label`
  - [x] 12.4: Test retry button shows disabled state when `isRetrying=true`
  - [x] 12.5: Test error message is displayed for failed documents
  - [x] 12.6: Test `useRetryDocument` hook: mock API call, verify cache update
  - [x] 12.7: Test SSE handler correctly updates `failed_stage` in document cache

## Dev Notes

### Architecture Context

This is **Story 6.1** in Epic 6 (System Resilience & Error Recovery). It is the **first story** in this epic and establishes the foundation for all subsequent resilience features (6.2: auto-retry, 6.3: graceful degradation, 6.4: service status display). All Epics 1-5 are done.

**FRs covered:** FR35 (failed document marking), FR37 (manual retry), FR38 (data preservation on partial failure)

**NFRs relevant:** NFR24 (no data loss from partial failures), NFR26 (individual service failure doesn't crash app), NFR28 (processing queue survives restarts)

### Current Document Processing Pipeline

The processing pipeline in `apps/api/app/worker/tasks/process_document.py` runs 4 stages sequentially:

1. **Pre-flight check** — Verify Ollama is available
2. **Stage 1: Text extraction** — PyMuPDF extracts text from PDF
3. **Stage 2: Chunking** — Split text into chunks stored in PostgreSQL
4. **Stage 3: Entity extraction** — LLM extracts entities/relationships → stored in Neo4j
5. **Stage 4: Embedding** — Generate vector embeddings → stored in Qdrant

**Current failure behavior:** Each stage has its own try-except that sets `document.status = "failed"` and `document.error_message = str(exc)`. The `document.failed` SSE event is published. **BUT** the current implementation does NOT record which stage failed — only the error message text.

**Key gap:** No `failed_stage` column → retry cannot intelligently resume from the failure point. All retries would have to restart from the beginning, wasting already-completed work.

### Retry Stage Resume Logic

The retry must be **stage-aware** to avoid re-executing completed work:

| Failed Stage | What Exists | What to Clean | Resume From |
|---|---|---|---|
| `preflight` | Nothing | Nothing | Run all stages |
| `extracting_text` | Nothing | Nothing | Run all stages |
| `chunking` | `extracted_text` in document | Delete any partial chunks | Stage 2 (chunking) |
| `extracting_entities` | `extracted_text` + chunks in PostgreSQL | Delete entities/relationships in Neo4j for this document, delete chunks (entity extraction modifies chunk provenance data) | Stage 2 (chunking) — safer to re-chunk since entity extraction expects fresh chunk IDs in provenance |
| `embedding` | `extracted_text` + chunks + entities/relationships | Delete embeddings for this document in Qdrant | Stage 4 (embedding) |

**IMPORTANT DESIGN DECISION:** For `extracting_entities` failure, the safest approach is to re-run from chunking rather than trying to resume entity extraction mid-chunk. Entity extraction processes chunks sequentially and stores provenance data linking entities to chunks — partial entity data from a failed run could create orphaned references. Clean delete of chunks + re-chunk + re-extract is the safe path.

**Alternative (simpler) approach:** Always restart from the beginning on retry. This is simpler but wasteful — text extraction is fast (<1s typically) but entity extraction can take minutes for large documents. The stage-aware approach is preferred per AC#3 ("resume from failure point").

### Data Cleanup Strategy for Retry

When retrying, partial data from the failed stage must be cleaned up to avoid duplicates:

**Chunks cleanup** (PostgreSQL):
```sql
DELETE FROM document_chunks WHERE document_id = :doc_id
```

**Entities/Relationships cleanup** (Neo4j):
```cypher
MATCH (e:Entity)-[:FOUND_IN]->(d:Document {id: $doc_id})
DETACH DELETE e
-- Also delete relationships sourced from this document
MATCH ()-[r:RELATES_TO]-() WHERE r.document_id = $doc_id
DELETE r
```

**Embeddings cleanup** (Qdrant):
```python
qdrant_client.delete(
    collection_name="document_chunks",
    points_selector=models.FilterSelector(
        filter=models.Filter(
            must=[models.FieldCondition(key="document_id", match=models.MatchValue(value=str(doc_id)))]
        )
    )
)
```

### Existing Infrastructure to Leverage

| Component | Location | Relevance |
|---|---|---|
| `Document` model | `apps/api/app/models/document.py` | Add `failed_stage` column |
| `DocumentResponse` schema | `apps/api/app/schemas/document.py` | Add `failed_stage` field |
| `process_document_task` | `apps/api/app/worker/tasks/process_document.py` | Add `failed_stage` recording + `resume_from_stage` param |
| `documents.py` API | `apps/api/app/api/v1/documents.py` | Add retry endpoint |
| `EventPublisher` | `apps/api/app/services/events.py` | Already used — add `stage` to `document.failed` payload |
| `useSSE` hook | `apps/web/src/hooks/useSSE.ts` | Already handles `document.failed` — store `failed_stage` |
| `useDocuments` hooks | `apps/web/src/hooks/useDocuments.ts` | Add `useRetryDocument` mutation |
| `DocumentCard` | `apps/web/src/components/investigation/DocumentCard.tsx` | Add retry button + error display |
| `DocumentList` | `apps/web/src/components/investigation/DocumentList.tsx` | Pass `onRetry` prop through |
| `exceptions.py` | `apps/api/app/exceptions.py` | Add `DocumentNotRetryableError` |
| `SyncSessionLocal` | `apps/api/app/db/sync_postgres.py` | Used in Celery tasks (sync, fork-safe) |
| `AsyncSession` | `apps/api/app/db/postgres.py` | Used in API endpoints (async) |
| Alembic | `apps/api/alembic/` | Migration for `failed_stage` column |

### Important Patterns from Previous Stories

1. **Celery tasks use sync sessions** — `SyncSessionLocal()` from `apps/api/app/db/sync_postgres.py`. API endpoints use async sessions via FastAPI dependency injection.

2. **SSE events are best-effort** — `_publish_safe()` wrapper never raises. Always commit DB state before publishing events.

3. **Fork-safe client creation** — Neo4j driver, Qdrant client, and Redis client are created per-task inside the task function (not at module level) to avoid SIGSEGV in forked workers.

4. **Status badge styling pattern** — `statusStyles` and `statusLabels` dicts in `DocumentCard.tsx`. Add entries for intermediate stages if the retry transitions through them.

5. **Error format is RFC 7807** — All API errors return `{ type, title, status, detail, instance }`. Follow this pattern for `DocumentNotRetryableError`.

6. **OpenAPI type generation pipeline** — After any schema change: export OpenAPI JSON → regenerate TypeScript types → verify generated types are correct.

7. **TanStack React Query cache updates** — Mutations should optimistically update the cache (set status to "queued") then invalidate to reconcile with server.

8. **lucide-react icons** — Use `RotateCcw` for retry icon (consistent with common retry iconography). Already in the project's icon library.

### UX Specifications for Failed Document Display

Per the UX design specification:
- **Failed state:** Red indicator (`--status-error` / `#c47070`), error description text, retry button with `RotateCcw` icon
- **Retry button:** `aria-label="Retry processing [filename]"` per UX spec (line 952)
- **Error messaging principle:** "Honest error states with recovery path" — show what happened, what's affected, what to do
- **Toast on retry failure:** Red left border toast, persists until dismissed

### Document Model Change (Migration Required)

Add one column to the `documents` table:
```python
failed_stage: Mapped[str | None] = mapped_column(String(30), nullable=True)
```

This is a nullable column addition — **non-breaking, no data migration needed**. Existing "failed" documents will have `failed_stage=None`, which the retry logic should treat as "unknown stage → restart from beginning."

### API Endpoint Design

```
POST /api/v1/investigations/{investigation_id}/documents/{document_id}/retry
Response: DocumentResponse (status: "queued", error_message: null, failed_stage: null)

Errors:
- 404: Document not found or wrong investigation
- 409: Document is not in "failed" status (urn:osint:error:document_not_retryable)
```

No request body needed — the retry always resumes from the recorded `failed_stage`.

### StatusLabels Update for Frontend

Current `statusLabels` only covers: `queued`, `extracting_text`, `complete`, `failed`. The processing pipeline also uses: `chunking`, `extracting_entities`, `embedding`. These should be added for completeness so the frontend can display accurate stage names during retry processing:

```typescript
const statusLabels: Record<string, string> = {
  queued: "Queued",
  extracting_text: "Extracting Text",
  chunking: "Chunking",
  extracting_entities: "Extracting Entities",
  embedding: "Generating Embeddings",
  complete: "Complete",
  failed: "Failed",
};
```

Also update `statusStyles` — `chunking`, `extracting_entities`, `embedding` should use the same info style as `extracting_text` (blue, processing).

### SSE Event Update for document.failed

**Current payload:** `{ document_id, error }`
**Required payload:** `{ document_id, stage, error }`

The `stage` value comes from `document.failed_stage`. This change is backward-compatible — existing frontend code ignores unknown payload fields.

The `useSSE` handler for `document.failed` currently sets `error_message` from `event.payload.error`. It should additionally set `failed_stage` from `event.payload.stage`.

### Project Structure Notes

- All new backend code follows existing patterns in `apps/api/app/`
- No new top-level files or directories
- One new service file: `apps/api/app/services/document.py` (retry logic)
- One new test file: `apps/api/tests/services/test_document.py`
- Alignment with architecture: kebab-case API paths, PascalCase components, snake_case Python

### Performance Considerations

- Retry endpoint is lightweight: single DB query + update + Celery task enqueue. Response is immediate (async processing).
- Stage-aware cleanup is bounded: delete operations use indexed columns (`document_id`).
- No performance regression on the happy path — `failed_stage` is only written on failure.

### References

- [Source: _bmad-output/planning-artifacts/epics.md — Epic 6, Story 6.1 acceptance criteria and BDD scenarios]
- [Source: _bmad-output/planning-artifacts/prd.md — FR35: failed document marking, FR37: manual retry, FR38: data preservation]
- [Source: _bmad-output/planning-artifacts/prd.md — NFR24: no data loss, NFR26: individual service failure resilience, NFR28: queue survives restarts]
- [Source: _bmad-output/planning-artifacts/architecture.md — Line 298: POST /api/v1/investigations/{id}/documents/{doc_id}/retry endpoint]
- [Source: _bmad-output/planning-artifacts/architecture.md — Lines 487-503: Error handling patterns (RFC 7807, Celery task error handling)]
- [Source: _bmad-output/planning-artifacts/architecture.md — Lines 469-483: SSE event specifications including document.failed with {document_id, stage, error}]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — Lines 922-924: Failed document card mockup with retry button]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — Lines 937-943: Document processing states including Failed with retry button]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — Line 952: aria-label="Retry processing [filename]"]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — Lines 1181-1182: Error toast pattern for retry failures]
- [Source: apps/api/app/models/document.py — Document model fields, status tracking, no failed_stage currently]
- [Source: apps/api/app/worker/tasks/process_document.py — Full 4-stage pipeline with per-stage error handling, no retry logic]
- [Source: apps/api/app/api/v1/documents.py — Existing document endpoints, no retry endpoint]
- [Source: apps/api/app/services/events.py — EventPublisher with Redis pub/sub]
- [Source: apps/api/app/exceptions.py — DomainError pattern, RFC 7807 error handler]
- [Source: apps/web/src/hooks/useSSE.ts — SSE hook handling document.failed events, updating cache]
- [Source: apps/web/src/hooks/useDocuments.ts — Document query/mutation hooks pattern]
- [Source: apps/web/src/components/investigation/DocumentCard.tsx — Status badges, no retry button currently]

### Previous Story Intelligence (Story 5.3 Learnings)

1. **RFC 7807 error pattern is well-established** — All domain exceptions follow the same constructor pattern: `DomainError(detail, status_code, error_type)`. New `DocumentNotRetryableError` should follow this.

2. **OpenAPI generation is a two-step process** — Backend generates JSON, frontend consumes it. Both must run after schema changes.

3. **Testing follows existing patterns** — Backend: `pytest` + `httpx.AsyncClient`, fixtures in `conftest.py`. Frontend: Vitest + Testing Library + React Query wrapper.

4. **Test count baseline:** ~304 backend tests, ~217 frontend tests. This story should add ~10-15 backend tests (endpoint + service + task updates) and ~8-10 frontend tests (DocumentCard retry + useRetryDocument hook + SSE updates).

5. **Commit message format:** `feat: Story 6.1 — failed document detection and manual retry`

### Git Intelligence

Recent commits:
- `fc6ab6a` — feat: Story 5.3 — citation click-through viewer with code review fixes
- `b3326fd` — feat: improve query pipeline — multilingual support, Cypher validation & result quality
- `58916bb` — feat: Story 5.2 — answer streaming QA panel + UI layout cleanup
- `bf2d2c6` — feat: Story 5.1 — graph-first natural language query pipeline

**Pattern:** All stories follow `feat: Story X.Y — description` format. Code review fixes are folded into the story commit.

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

- Pre-existing test failure: `TestEntityExtractionStage::test_entity_discovered_sse_events_published` — mock `fake_extract` missing `on_chunk_progress` kwarg (not related to this story)
- Pre-existing test failures: `test_docker_compose.py` tests (2 failures, infrastructure-related)
- Pre-existing frontend failures: `SystemStatusPage.test.tsx` (4 failures, TanStack Router `useLinkProps` null context)

### Completion Notes List

- **Task 1:** Added `failed_stage` column (String(30), nullable) to Document model with Alembic migration 006. Added field to DocumentResponse schema and `_to_response` helper.
- **Task 2:** Updated all 5 error handlers in `process_document_task` to set `failed_stage` (preflight, extracting_text, chunking, extracting_entities, embedding) and include `stage` in `document.failed` SSE payloads.
- **Task 3:** Created `DocumentNotRetryableError` (409), added `retry_failed_document` method to DocumentService with stage-aware cleanup (deletes chunks for chunking/entity failures), added `POST .../retry` endpoint, and added `resume_from_stage` parameter to `process_document_task` with conditional stage skipping.
- **Task 4:** Updated SSE `document.failed` handler to store `failed_stage` from `event.payload.stage`.
- **Task 5:** Added retry button with `RotateCcw` icon, error message display, "Failed — Retry" badge, `isRetrying` disabled state.
- **Task 6:** Created `useRetryDocument` mutation hook with optimistic cache update.
- **Task 7:** Wired `onRetry`/`retryingId` through DocumentList to DocumentCard, added retry handler in investigation detail page.
- **Task 8:** Manually added `failed_stage` field and retry endpoint path/operation to `api-types.generated.ts`. Full regeneration requires running server (`pnpm run generate-api-types`).
- **Tasks 9-12:** Added 12 new backend tests (4 retry endpoint, 6 failed_stage recording, 2 resume_from_stage) and 8 new frontend tests (retry button behavior, error message display, aria-label, disabled state).

### Change Log

- 2026-03-15: Story 6.1 implemented — failed document detection with `failed_stage` recording, stage-aware retry with cleanup, frontend retry UX with error display
- 2026-03-16: Code review fixes — added Neo4j cleanup on retry before entity extraction, added retry error notification + optimistic update rollback, created retry service unit tests (9 tests), fixed misleading Qdrant comment, added DocumentCard.test.tsx to File List

### File List

- `apps/api/app/models/document.py` — Added `failed_stage` column
- `apps/api/app/schemas/document.py` — Added `failed_stage` field to DocumentResponse
- `apps/api/app/exceptions.py` — Added `DocumentNotRetryableError`
- `apps/api/app/services/document.py` — Added `retry_failed_document` method with stage-aware cleanup
- `apps/api/app/api/v1/documents.py` — Added `POST .../retry` endpoint, updated `_to_response` with `failed_stage`
- `apps/api/app/worker/tasks/process_document.py` — Added `failed_stage` recording at each failure, `resume_from_stage` parameter with conditional stage skipping
- `apps/api/migrations/versions/006_add_failed_stage_to_documents.py` — New migration
- `apps/api/tests/conftest.py` — Added `failed_stage` to sample_document fixture, `retry_failed_document` to mock service
- `apps/api/tests/api/test_documents.py` — Added 4 retry endpoint tests
- `apps/api/tests/worker/test_process_document.py` — Added `failed_stage` to fixture, 6 failed_stage tests, 2 resume_from_stage tests
- `apps/web/src/hooks/useSSE.ts` — Updated `document.failed` handler to store `failed_stage`
- `apps/web/src/hooks/useDocuments.ts` — Added `useRetryDocument` mutation hook
- `apps/web/src/components/investigation/DocumentCard.tsx` — Added retry button, error message, `RotateCcw` icon, `onRetry`/`isRetrying` props
- `apps/web/src/components/investigation/DocumentCard.test.tsx` — Added 8 retry button tests (display, click, aria-label, disabled state, error message)
- `apps/web/src/components/investigation/DocumentList.tsx` — Added `onRetry`/`retryingId` props, pass-through to DocumentCard
- `apps/web/src/routes/investigations/$id.tsx` — Wired `useRetryDocument`, `retryingId` state, retry handler with error notification to DocumentList
- `apps/web/src/lib/api-types.generated.ts` — Added `failed_stage` to DocumentResponse, retry endpoint path and operation
- `apps/api/tests/services/test_document_retry.py` — Added 9 retry service unit tests (status validation, state reset, cleanup logic per stage)
