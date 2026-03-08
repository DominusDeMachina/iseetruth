# Story 2.5: Extracted Text Viewer

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an investigator,
I want to view the extracted text of a processed document,
so that I can verify the system correctly parsed my PDFs before relying on entity extraction.

## Acceptance Criteria

1. GIVEN a document with status `complete`, WHEN the investigator clicks "View Text" on the document card, THEN a modal opens displaying the extracted text fetched via `GET /api/v1/investigations/{id}/documents/{doc_id}/text`.
2. GIVEN the extracted text contains page markers (`--- Page N ---`), WHEN displayed in the viewer, THEN the text preserves basic structure (paragraphs, page breaks) in a readable format.
3. GIVEN a document with status `queued` or `extracting_text`, WHEN the investigator views the document list, THEN no "View Text" button is shown for that document (current behavior — already implemented in Story 2.4).
4. GIVEN a document with status `failed`, WHEN the investigator views the document list, THEN the document shows the failure reason via `error_message` field (already displayed via status badge — verify no additional work needed).
5. GIVEN a document with status `complete` but `extracted_text` is null or empty, WHEN the investigator clicks "View Text", THEN the viewer shows a clear "No text extracted" message.
6. GIVEN the text viewer is open, WHEN the investigator presses Escape or clicks outside the modal, THEN the modal closes.

## Tasks / Subtasks

- [x] **Task 1: Backend — Add dedicated `/text` endpoint** (AC: 1)
  - [x] 1.1: Add `GET /investigations/{investigation_id}/documents/{document_id}/text` endpoint in `app/api/v1/documents.py`
  - [x] 1.2: Create `DocumentTextResponse` schema in `app/schemas/document.py` with fields: `document_id`, `filename`, `page_count`, `extracted_text`, `status`
  - [x] 1.3: Return 404 if document not found, return 409 (Conflict) if document status is not `complete`
  - [x] 1.4: Write backend tests for the new endpoint (happy path, 404, 409)
  - [x] 1.5: Regenerate OpenAPI types: `cd apps/web && pnpm run generate-types`
- [x] **Task 2: Frontend — `useDocumentText` hook** (AC: 1)
  - [x] 2.1: Add `useDocumentText(investigationId, documentId)` hook in `apps/web/src/hooks/useDocuments.ts`
  - [x] 2.2: Query key: `["document-text", investigationId, documentId]`
  - [x] 2.3: Only fetch when `documentId` is non-null (lazy fetch — triggered when modal opens)
  - [x] 2.4: Write hook test
- [x] **Task 3: Frontend — `DocumentTextViewer` modal component** (AC: 1, 2, 5, 6)
  - [x] 3.1: Create `apps/web/src/components/investigation/DocumentTextViewer.tsx`
  - [x] 3.2: Use shadcn/ui `Dialog` (same pattern as `DeleteDocumentDialog`)
  - [x] 3.3: Display filename and page count in the dialog header
  - [x] 3.4: Render extracted text with page markers parsed into visual separators (horizontal rule + "Page N" label)
  - [x] 3.5: Use `font-serif` (Source Serif 4) for text body per UX spec
  - [x] 3.6: Handle empty/null text with "No text could be extracted from this document" message
  - [x] 3.7: Loading state while text is fetching
  - [x] 3.8: Write component tests (loading, text display, empty state, close behavior)
- [x] **Task 4: Frontend — Wire "View Text" button in `DocumentCard`** (AC: 1, 3)
  - [x] 4.1: Remove `disabled` from the existing "View Text" button in `DocumentCard.tsx` (line 84)
  - [x] 4.2: Remove "coming soon" title
  - [x] 4.3: Add `onViewText` callback prop to `DocumentCardProps`
  - [x] 4.4: Wire button `onClick` to call `onViewText(document.id)`
  - [x] 4.5: Update `DocumentList` to accept and pass through `onViewText` prop
  - [x] 4.6: In `$id.tsx` (investigation detail page): add state for `viewingDocumentId`, pass `onViewText` callback to `DocumentList`, render `DocumentTextViewer` dialog
  - [x] 4.7: Update existing DocumentCard tests, add new tests for button click behavior

## Dev Notes

### Backend Implementation

**New endpoint only — no model/migration changes needed.** The `extracted_text` field already exists on the Document model (added in Story 2.3 migration 003). The `DocumentService.get_document()` method already fetches the full document including text.

**Dedicated `/text` endpoint rationale:** The architecture specifies `GET /api/v1/investigations/{id}/documents/{doc_id}/text` as a separate endpoint. While the existing `GET /documents/{doc_id}` already returns `extracted_text` with `include_text=True`, add the dedicated endpoint for:
- Architecture compliance (endpoint is explicitly listed)
- Cleaner API semantics (text-only response without full document metadata)
- Future optimization (text can be large; separating it avoids bloating the general document endpoint)

**New schema — `DocumentTextResponse`:**
```python
class DocumentTextResponse(BaseModel):
    document_id: uuid.UUID
    filename: str
    page_count: int | None
    extracted_text: str | None
```

**409 Conflict for non-complete documents:** If a client requests text for a document that is still `queued`, `extracting_text`, or `failed`, return 409 with a clear error message. This prevents confusion from returning null text for a document that's still processing.

**Error handling — reuse existing patterns:**
- `DocumentNotFoundError` already exists in `app/exceptions.py`
- Add `DocumentNotReadyError(DomainError)` for 409 responses
- Follow RFC 7807 pattern established in previous stories

### Frontend Implementation

**Component architecture follows DeleteDocumentDialog pattern exactly:**
- `DocumentTextViewer` is a controlled dialog component
- Parent component (`$id.tsx`) manages open/close state via `viewingDocumentId`
- Text fetched lazily only when dialog opens (via `enabled: !!documentId` in query)

**Text rendering — parse page markers into visual separators:**
The PyMuPDF extraction (Story 2.3) inserts `--- Page N ---` markers between pages. Parse these into styled dividers:
```
Split text on /^--- Page (\d+) ---$/m regex
Render each page section with a subtle divider + "Page N" label
```

**Typography per UX spec:**
- Text body: `font-serif` (Source Serif 4) — editorial content optimization for dense factual prose
- Metadata/labels: default `font-sans` (Inter)
- Use `text-base` (15px) for text body
- Use `text-sm` for page labels

**Dialog sizing:** Use `max-w-3xl` and `max-h-[80vh]` with scrollable content area. Since shadcn/ui Dialog already handles scroll, use `overflow-y-auto` on the text container div.

**No shadcn/ui ScrollArea needed** — the Dialog's `DialogContent` with a scrollable div is sufficient and avoids adding a new dependency.

### Project Structure Notes

**Files to create:**
- `apps/web/src/components/investigation/DocumentTextViewer.tsx`
- `apps/web/src/components/investigation/DocumentTextViewer.test.tsx`

**Files to modify:**
- `apps/api/app/api/v1/documents.py` — add `/text` endpoint
- `apps/api/app/schemas/document.py` — add `DocumentTextResponse`
- `apps/api/app/exceptions.py` — add `DocumentNotReadyError` (if needed)
- `apps/web/src/hooks/useDocuments.ts` — add `useDocumentText` hook
- `apps/web/src/components/investigation/DocumentCard.tsx` — enable "View Text" button, add `onViewText` prop
- `apps/web/src/components/investigation/DocumentList.tsx` — pass through `onViewText` prop
- `apps/web/src/routes/investigations/$id.tsx` — add viewer state, render `DocumentTextViewer`
- `apps/web/src/lib/api-types.generated.ts` — regenerated automatically

**Files to add tests to:**
- `apps/api/tests/api/v1/test_documents.py` — new endpoint tests
- `apps/web/src/components/investigation/DocumentCard.test.tsx` — update for enabled button
- `apps/web/src/hooks/useDocuments.test.ts` — if exists, add hook test (or create)

### Existing Code to Reuse (DO NOT REINVENT)

| What | Where | How to Reuse |
|------|-------|--------------|
| Document model with `extracted_text` | `app/models/document.py:22` | Already stores text — no changes |
| `DocumentService.get_document()` | `app/services/document.py` | Fetches full document — call from new endpoint |
| `_to_response()` helper | `app/api/v1/documents.py:24` | Reference for response mapping pattern |
| `DocumentNotFoundError` | `app/exceptions.py:26` | Reuse for 404 |
| `DeleteDocumentDialog` pattern | `components/investigation/DeleteDocumentDialog.tsx` | Copy dialog structure exactly |
| `renderWithProviders()` test util | `apps/web/src/test-utils.tsx` | Use for all component tests |
| `createTestQueryClient()` | `apps/web/src/test-utils.tsx` | Use for all hook/component tests |
| shadcn/ui Dialog components | `components/ui/dialog.tsx` | Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription |
| CSS design tokens | Root CSS | `--bg-elevated`, `--border-subtle`, `--text-primary`, `--text-secondary`, `--text-muted` |
| openapi-fetch API client | `lib/api-client.ts` | `api.GET(...)` pattern for typed fetch |
| TanStack Query patterns | `hooks/useDocuments.ts` | `useQuery` with typed response, `queryKey` hierarchy |

### Anti-Patterns to Avoid

- **DO NOT** add a new database migration — `extracted_text` already exists on the model
- **DO NOT** create a separate page/route for text viewing — use a modal dialog on the investigation detail page
- **DO NOT** fetch text in the document list endpoint — keep list responses lightweight (no `extracted_text`)
- **DO NOT** use `dangerouslySetInnerHTML` — render extracted text as plain text with whitespace preservation (`whitespace-pre-wrap`)
- **DO NOT** add a new shadcn/ui component (e.g., ScrollArea) unless absolutely needed — scrollable div is sufficient
- **DO NOT** modify the `useDocuments` list query to include text — create a separate `useDocumentText` query

### Testing Standards

**Backend (pytest):**
- Test `/text` endpoint: 200 with complete document, 404 for missing document, 409 for non-complete document, 200 with null extracted_text
- Follow existing test patterns in `tests/api/v1/test_documents.py`
- Use existing fixtures from `conftest.py`

**Frontend (Vitest + React Testing Library):**
- `DocumentTextViewer.test.tsx`: renders loading state, renders text content, handles empty text, close behavior
- `DocumentCard.test.tsx`: update existing tests — button is now enabled and clickable for complete docs, fires `onViewText`
- Use `renderWithProviders()` from `test-utils.tsx`
- Mock `api.GET` for hook tests

### References

- [Source: _bmad-output/planning-artifacts/epics.md — Epic 2, Story 2.5 acceptance criteria]
- [Source: _bmad-output/planning-artifacts/architecture.md — API Endpoints: GET /documents/{doc_id}/text]
- [Source: _bmad-output/planning-artifacts/prd.md — FR10: View extracted text of processed document]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — Typography system, color tokens, dialog patterns]
- [Source: apps/api/app/api/v1/documents.py — existing endpoint with include_text=True]
- [Source: apps/web/src/components/investigation/DocumentCard.tsx:80-91 — disabled "View Text" button]
- [Source: apps/web/src/components/investigation/DeleteDocumentDialog.tsx — dialog pattern to follow]
- [Source: apps/api/app/services/text_extraction.py — PyMuPDF page marker format: "--- Page N ---"]
- [Source: _bmad-output/implementation-artifacts/2-4-real-time-processing-dashboard-with-sse.md — View Text button added]
- [Source: _bmad-output/implementation-artifacts/2-3-async-document-processing-pipeline-with-text-extraction.md — extracted_text field, text extraction service]

## Change Log

- 2026-03-09: Implemented Story 2.5 — Extracted Text Viewer. Added dedicated `/text` API endpoint with 409 conflict handling, `useDocumentText` hook with lazy fetching, `DocumentTextViewer` modal with page marker parsing, and wired "View Text" button in DocumentCard. All 100 backend + 74 frontend tests pass.
- 2026-03-09: Code review fixes — Added error state handling to DocumentTextViewer (M1), fixed `.gitignore` pattern for nested storage dirs (M2), added `status` field to DocumentTextResponse per task spec (L1), added 2 additional 409 backend tests for queued/failed statuses (L4), added frontend tests for error state and text-without-markers edge case (L3). All 17 backend document tests + 76 frontend tests pass.

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

No issues encountered during implementation.

### Completion Notes List

- **Task 1 (Backend):** Added `GET /documents/{doc_id}/text` endpoint returning `DocumentTextResponse`. Added `DocumentNotReadyError` (409) for non-complete documents. 4 new backend tests added (200 happy path, 200 null text, 404, 409).
- **Task 2 (Frontend hook):** Added `useDocumentText` hook with lazy fetching (`enabled: !!documentId`), query key `["document-text", investigationId, documentId]`. 4 new hook tests added.
- **Task 3 (Frontend component):** Created `DocumentTextViewer` modal using shadcn/ui Dialog. Parses `--- Page N ---` markers into visual separators. Uses `font-serif` for text body, handles empty/null text state, loading spinner. 6 new component tests.
- **Task 4 (Frontend wiring):** Enabled "View Text" button in DocumentCard (removed disabled + "coming soon"), added `onViewText` prop chain through DocumentList to `$id.tsx`, managing `viewingDocumentId` state. Updated 1 existing test, added 1 new test.

### File List

**New files:**
- `apps/web/src/components/investigation/DocumentTextViewer.tsx`
- `apps/web/src/components/investigation/DocumentTextViewer.test.tsx`
- `apps/web/src/hooks/useDocuments.test.ts`

**Modified files:**
- `apps/api/app/api/v1/documents.py` — added `/text` endpoint
- `apps/api/app/schemas/document.py` — added `DocumentTextResponse`
- `apps/api/app/exceptions.py` — added `DocumentNotReadyError`
- `apps/api/tests/api/test_documents.py` — added 6 new endpoint tests (4 original + 2 review fixes)
- `apps/web/src/hooks/useDocuments.ts` — added `useDocumentText` hook + `DocumentTextResponse` type export
- `apps/web/src/components/investigation/DocumentCard.tsx` — enabled "View Text" button, added `onViewText` prop
- `apps/web/src/components/investigation/DocumentCard.test.tsx` — updated button test, added click behavior test
- `apps/web/src/components/investigation/DocumentList.tsx` — added `onViewText` passthrough prop
- `apps/web/src/routes/investigations/$id.tsx` — added `viewingDocumentId` state, `DocumentTextViewer` component
- `apps/web/src/lib/api-types.generated.ts` — regenerated with new endpoint types
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — status update
- `_bmad-output/implementation-artifacts/2-5-extracted-text-viewer.md` — story updates
