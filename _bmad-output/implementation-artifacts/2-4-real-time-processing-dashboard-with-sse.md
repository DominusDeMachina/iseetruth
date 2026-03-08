# Story 2.4: Real-Time Processing Dashboard with SSE

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an investigator,
I want to see live progress as my documents are processed,
so that I know what's happening without manually refreshing.

## Acceptance Criteria

1. **AC1: SSE Event Consumption**
   - Given the investigator is in an investigation workspace with documents processing
   - When documents move through processing stages
   - Then SSE events are received via `GET /api/v1/investigations/{investigation_id}/events`
   - And events follow the defined format: `document.processing`, `document.complete`, `document.failed`
   - And events arrive within 1 second of the state change (NFR4)

2. **AC2: Real-Time Document Status Updates**
   - Given the frontend receives SSE events
   - When a document's status changes
   - Then the processing dashboard updates the per-document status card in real-time (no page refresh)
   - And status cards show: queued, extracting text, complete, or failed
   - And the SSE connection uses `@microsoft/fetch-event-source` piped into TanStack Query cache

3. **AC3: SSE Reconnection with State Reconciliation**
   - Given the SSE connection drops
   - When the client detects disconnection
   - Then fetch-event-source auto-reconnects
   - And on reconnection, the frontend fetches current state from the REST API to reconcile

4. **AC4: Processing Dashboard with Progress Summary**
   - Given the investigator navigates to the investigation detail
   - When documents are being processed
   - Then the page shows an overall progress summary (counts by status: N complete, N processing, N failed, N queued)
   - And each document shows: filename, file size, processing status, and upload timestamp
   - And completed documents show a "View Text" link (disabled — implemented in Story 2.5)

5. **AC5: SSE Connection Lifecycle**
   - Given the investigator opens an investigation with processing documents
   - When the SSE hook connects
   - Then the connection is established only when documents are in non-terminal states (queued or extracting_text)
   - And the connection is cleanly closed when the user navigates away (component unmount)
   - And the connection is cleanly closed when all documents reach terminal state (complete or failed)

## Tasks / Subtasks

- [x] Task 1: Add `@microsoft/fetch-event-source` dependency (AC: #1, #2)
  - [x] 1.1: Run `pnpm add @microsoft/fetch-event-source` in `apps/web/`
  - [x] 1.2: Verify package installs and TypeScript types are available

- [x] Task 2: Create `useSSE` hook (AC: #1, #2, #3, #5)
  - [x] 2.1: Create `apps/web/src/hooks/useSSE.ts` with `useSSE(investigationId: string, enabled: boolean)` hook
  - [x] 2.2: Connect to `GET /api/v1/investigations/{investigation_id}/events` using `fetchEventSource`
  - [x] 2.3: Parse incoming SSE `data` field as JSON matching event format: `{type, investigation_id, timestamp, payload}`
  - [x] 2.4: On `document.processing` event — update the matching document's `status` in TanStack Query cache (`["documents", investigationId]`)
  - [x] 2.5: On `document.complete` event — update document status to `"complete"` in cache
  - [x] 2.6: On `document.failed` event — update document status to `"failed"` and set `error_message` from payload
  - [x] 2.7: Return `{ isConnected, connectionError, reconnectCount }` state from the hook
  - [x] 2.8: Use `AbortController` for cleanup on unmount; abort in `useEffect` cleanup function
  - [x] 2.9: On reconnection (`onopen`), invalidate the documents query to fetch fresh state from REST API
  - [x] 2.10: Track `reconnectCount`; after 3 failed reconnects, set `connectionError` state for UI display
  - [x] 2.11: Disable connection (`enabled: false`) when no documents are in processing states

- [x] Task 3: Update `useDocuments` hook — remove polling, integrate SSE (AC: #2, #5)
  - [x] 3.1: Remove `refetchInterval` logic from `useDocuments` (SSE replaces polling)
  - [x] 3.2: Add `useSSE` call inside investigation detail page, passing `enabled` based on whether documents have non-terminal statuses

- [x] Task 4: Create `ProcessingDashboard` component (AC: #4)
  - [x] 4.1: Create `apps/web/src/components/investigation/ProcessingDashboard.tsx`
  - [x] 4.2: Show overall progress summary bar: "Processing: {investigation_name} — {total} documents · {complete} complete · {failed} failed · {remaining} remaining"
  - [x] 4.3: Show per-document status cards using existing `DocumentCard` (no new card component needed)
  - [x] 4.4: Add SSE connection status indicator — show degraded badge when `connectionError` is set (after 3 failed reconnects)

- [x] Task 5: Integrate `ProcessingDashboard` into investigation detail page (AC: #2, #4)
  - [x] 5.1: Update `apps/web/src/routes/investigations/$id.tsx` to show `ProcessingDashboard` above the document list when documents are processing
  - [x] 5.2: Wire `useSSE` hook with `enabled` flag based on document processing state
  - [x] 5.3: Progress summary is always visible when any documents exist; SSE indicator only shows during active processing

- [x] Task 6: Write frontend tests (AC: #1, #2, #3, #4, #5)
  - [x] 6.1: Create `apps/web/src/hooks/useSSE.test.ts` — test SSE event parsing, TanStack Query cache updates, cleanup on unmount, reconnection state tracking
  - [x] 6.2: Create `apps/web/src/components/investigation/ProcessingDashboard.test.tsx` — test progress summary counts, status indicator rendering, connection error display
  - [x] 6.3: Update `apps/web/src/routes/investigations/$id.test.tsx` (if exists) or create — test SSE integration with investigation detail page

## Dev Notes

### CRITICAL: SSE Architecture (Backend Already Implemented in Story 2.3)

**The backend SSE infrastructure is COMPLETE. This story is frontend-only.**

The following already exist and MUST NOT be modified:
- `apps/api/app/api/v1/events.py` — SSE endpoint at `GET /api/v1/investigations/{investigation_id}/events`
- `apps/api/app/services/events.py` — `EventPublisher` class publishes JSON to Redis pub/sub channel `events:{investigation_id}`
- `apps/api/app/worker/tasks/process_document.py` — Celery task publishes events: `document.processing`, `document.complete`, `document.failed`
- `sse-starlette>=2.3.3` — already installed

**SSE Event Format (from backend):**
```json
{
  "type": "document.processing",
  "investigation_id": "uuid",
  "timestamp": "2026-03-08T14:30:00Z",
  "payload": {"document_id": "uuid", "stage": "extracting_text"}
}
```

**Event types published by the current Celery task:**
| Event | Payload | When |
|-------|---------|------|
| `document.processing` | `{document_id, stage: "extracting_text"}` | Status transitions to extracting_text |
| `document.complete` | `{document_id}` | Text extraction finished |
| `document.failed` | `{document_id, error}` | Processing failed |

Note: `document.queued` is NOT currently published by the Celery task. Documents start as "queued" immediately on upload (set by the upload endpoint), before the Celery task picks them up. Do NOT add a `document.queued` event — it would require backend changes out of scope.
[Source: apps/api/app/worker/tasks/process_document.py]

### CRITICAL: @microsoft/fetch-event-source v2.0.1

**Package:** `@microsoft/fetch-event-source@^2.0.1` — latest stable (1.14M weekly downloads)

**API:**
```typescript
import { fetchEventSource } from "@microsoft/fetch-event-source";

const ctrl = new AbortController();
await fetchEventSource(url, {
  signal: ctrl.signal,
  onopen: async (response) => { /* validate response, reconcile state */ },
  onmessage: (ev) => { /* ev.data contains the JSON string */ },
  onclose: () => { /* server closed connection */ },
  onerror: (err) => { /* return retry interval ms, or throw to stop */ },
});
// Cleanup: ctrl.abort()
```

**Key behaviors:**
- Auto-reconnects on disconnect (default 1s retry)
- `onerror` callback: return number (ms) to set retry delay, throw to stop retries
- `onclose` callback: throw to trigger retry, return to accept closure
- `signal` via AbortController for cleanup on React unmount
- Handles browser tab visibility (auto-pause/resume)

**Important:** `fetchEventSource` returns a Promise that resolves when the connection closes. In a React `useEffect`, call it without `await` and use `AbortController` for cleanup:
```typescript
useEffect(() => {
  const ctrl = new AbortController();
  fetchEventSource(url, { signal: ctrl.signal, ... });
  return () => ctrl.abort();
}, [url]);
```
[Source: https://www.npmjs.com/package/@microsoft/fetch-event-source]

### CRITICAL: TanStack Query Cache Integration Pattern

**The core pattern:** SSE events directly update the `["documents", investigationId]` query cache. This provides instant UI updates without refetching.

```typescript
import { useQueryClient } from "@tanstack/react-query";
import type { DocumentListResponse } from "@/hooks/useDocuments";

const queryClient = useQueryClient();

// On SSE event, update cache:
queryClient.setQueryData<DocumentListResponse>(
  ["documents", investigationId],
  (old) => {
    if (!old) return old;
    return {
      ...old,
      items: old.items.map((doc) =>
        doc.id === event.payload.document_id
          ? { ...doc, status: newStatus }
          : doc
      ),
    };
  }
);
```

**On reconnection (`onopen`):** Invalidate the documents query to fetch fresh state from the server. This reconciles any missed events during disconnection:
```typescript
queryClient.invalidateQueries({ queryKey: ["documents", investigationId] });
```

**Connection lifecycle:**
- `enabled` should be `true` only when `documents.some(d => d.status === "queued" || d.status === "extracting_text")`
- When all documents reach terminal state (complete/failed), the hook should stop connecting
- This replaces the current `refetchInterval: 5000` polling in `useDocuments`
[Source: _bmad-output/planning-artifacts/architecture.md#SSE — fetch-event-source + TanStack Query]

### CRITICAL: What to Remove

**Remove polling from `useDocuments` hook:**
The current `refetchInterval` logic (lines 22-28 of `apps/web/src/hooks/useDocuments.ts`) must be removed. SSE replaces polling entirely. The `useDocuments` hook should become a simple `useQuery` with no `refetchInterval`:
```typescript
export function useDocuments(investigationId: string) {
  return useQuery<DocumentListResponse>({
    queryKey: ["documents", investigationId],
    queryFn: async () => {
      const { data, error } = await api.GET(
        "/api/v1/investigations/{investigation_id}/documents",
        { params: { path: { investigation_id: investigationId } } },
      );
      if (error) throw error;
      return data;
    },
    enabled: !!investigationId,
  });
}
```
[Source: apps/web/src/hooks/useDocuments.ts]

### Frontend Patterns (MUST follow from Stories 1.3/2.1/2.2/2.3)

**Component file location:** `src/components/investigation/` for investigation-related components
**Hook file location:** `src/hooks/` for custom hooks
**Test co-location:** Tests co-located with source files (e.g., `useSSE.test.ts` next to `useSSE.ts`)

**TanStack Query patterns (from Story 1.3):**
- staleTime 30s, gcTime 5m, retry 1 (defaults in QueryClient)
- Test helpers: `createTestQueryClient()` + `renderWithProviders()` from `src/test-utils.tsx`

**CSS variables for status (from Story 2.3):**
```typescript
const statusStyles: Record<string, string> = {
  queued: "bg-[var(--status-info)]/15 text-[var(--status-info)] border-[var(--status-info)]/30",
  extracting_text: "bg-[var(--status-info)]/15 text-[var(--status-info)] border-[var(--status-info)]/30",
  complete: "bg-[var(--status-success)]/15 text-[var(--status-success)] border-[var(--status-success)]/30",
  failed: "bg-[var(--status-error)]/15 text-[var(--status-error)] border-[var(--status-error)]/30",
};
```
[Source: apps/web/src/components/investigation/DocumentCard.tsx]

**API client:** `openapi-fetch` with `baseUrl: ""` — already configured at `src/lib/api-client.ts`
**Testing:** Vitest + React Testing Library, mock via `vi.fn()`, `vi.mock()`

### CRITICAL: SSE Connection Degraded State

Per architecture doc: "Show degraded status in UI after 3 failed reconnects."

The `useSSE` hook should track reconnection attempts and expose a `connectionError` flag. The `ProcessingDashboard` component displays a subtle warning banner when degraded:
```
"Live updates unavailable — showing cached status. Refresh to update."
```
This banner uses `--status-warning` color. It does NOT block the UI or prevent document display.
[Source: _bmad-output/planning-artifacts/architecture.md#Error Handling — Frontend]

### Project Structure Notes

**Files to CREATE:**
```
apps/web/src/
├── hooks/
│   ├── useSSE.ts                          # SSE hook with fetch-event-source + TanStack Query integration
│   └── useSSE.test.ts                     # SSE hook unit tests
└── components/investigation/
    ├── ProcessingDashboard.tsx             # Progress summary + SSE status indicator
    └── ProcessingDashboard.test.tsx        # Processing dashboard tests
```

**Files to MODIFY:**
```
apps/web/package.json                       # Add @microsoft/fetch-event-source dependency
apps/web/src/hooks/useDocuments.ts          # Remove refetchInterval polling
apps/web/src/routes/investigations/$id.tsx  # Integrate useSSE + ProcessingDashboard
```

**Files NOT to modify:**
```
apps/api/**                                 # No backend changes — SSE infra complete from Story 2.3
apps/web/src/components/investigation/DocumentCard.tsx     # Reuse as-is
apps/web/src/components/investigation/DocumentList.tsx     # Reuse as-is
apps/web/src/lib/api-types.generated.ts                   # No regeneration needed
```

### Previous Story Intelligence

**From Story 2.3 (CRITICAL):**
- Backend SSE endpoint, EventPublisher, and Celery task event publishing are complete and tested
- Frontend currently uses `refetchInterval: 5000` for polling — this must be replaced by SSE
- DocumentCard status styles already handle: `queued`, `extracting_text`, `complete`, `failed`
- 96 backend + 39 frontend = 135 total tests passing
- Event format confirmed: `{type, investigation_id, timestamp, payload}`
- Redis pub/sub channel: `events:{investigation_id}`

**From Story 2.2:**
- Upload endpoint returns immediately; Celery task is enqueued asynchronously
- Documents start with `status: "queued"` on creation

**From Story 1.3 (frontend patterns):**
- TanStack Query configured with: staleTime 30s, gcTime 5m, retry 1
- Test utils: `createTestQueryClient()` and `renderWithProviders()` in `src/test-utils.tsx`
- Route structure: TanStack Router with file-based routes in `src/routes/`

**Git Intelligence (last 5 commits):**
```
9147327 feat: Story 2.3 — async document processing pipeline with text extraction
31a3ee5 feat: Story 2.2 — PDF upload with immutable storage
fcf55d1 feat: Story 2.1 — investigation CRUD API & list view
9ffcec7 feat: Story 1.3 — frontend shell with system status page
77b379e feat: Story 1.2 — backend health checks & model readiness
```
Clean linear history, all tests passing, TypeScript strict mode passing.

**Current dependency versions (from package.json):**
- `react: ^19.2.4`, `react-dom: ^19.2.4`
- `@tanstack/react-query: ^5.90.21`
- `@tanstack/react-router: ^1.166.3`
- `openapi-fetch: ~0.17.0`
- `vitest: ^4.0.18`
- `tailwindcss: ^4.2.1`
- `lucide-react: ^0.577.0`

### Scope Boundaries — What This Story Does NOT Include

**Deferred to Story 2.5 (Extracted Text Viewer):**
- "View Text" link on completed documents (show disabled/placeholder in this story)
- `GET /api/v1/investigations/{id}/documents/{doc_id}/text` endpoint
- Text viewing UI component

**Deferred to Epic 3 (Entity Extraction):**
- `document.queued` SSE event type (not currently published by backend)
- `entity.discovered` SSE event handling
- Live entity counter in processing dashboard
- Additional processing phases: `extracting_entities`, `embedding`

**Deferred to Epic 5 (Q&A):**
- `query.*` SSE event types
- POST-based SSE for query streaming

**Deferred to Epic 6 (Resilience):**
- Retry button on failed documents
- `POST /api/v1/investigations/{id}/documents/{doc_id}/retry` endpoint
- Auto-retry on service recovery

**For Story 2.4, the SSE pipeline handles: `document.processing`, `document.complete`, `document.failed`.** No retry mechanism. No entity events. No query streaming. The processing dashboard shows document-level progress only.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.4: Real-Time Processing Dashboard with SSE]
- [Source: _bmad-output/planning-artifacts/architecture.md#SSE — FastAPI Direct via Redis Pub/Sub]
- [Source: _bmad-output/planning-artifacts/architecture.md#SSE — fetch-event-source + TanStack Query]
- [Source: _bmad-output/planning-artifacts/architecture.md#SSE Event Format]
- [Source: _bmad-output/planning-artifacts/architecture.md#SSE Event Types — document.processing, document.complete, document.failed]
- [Source: _bmad-output/planning-artifacts/architecture.md#Error Handling — Frontend — SSE disconnection]
- [Source: _bmad-output/planning-artifacts/architecture.md#Loading States — Processing dashboard]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Processing Dashboard]
- [Source: _bmad-output/planning-artifacts/prd.md#FR32 — Real-time progress updates during document processing]
- [Source: _bmad-output/planning-artifacts/prd.md#FR33 — Per-document processing status]
- [Source: _bmad-output/planning-artifacts/prd.md#NFR4 — Real-time updates within 1 second of state change]
- [Source: _bmad-output/implementation-artifacts/2-3-async-document-processing-pipeline-with-text-extraction.md — SSE backend implementation]
- [Source: apps/api/app/api/v1/events.py — SSE endpoint implementation]
- [Source: apps/api/app/services/events.py — EventPublisher class]
- [Source: apps/api/app/worker/tasks/process_document.py — Event publishing in Celery task]
- [Source: apps/web/src/hooks/useDocuments.ts — Current polling to be replaced]
- [Source: apps/web/src/components/investigation/DocumentCard.tsx — Existing status styles]
- [Source: apps/web/src/routes/investigations/$id.tsx — Investigation detail page]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

- Test file in `src/routes/investigations/` triggered TanStack Router route detection warning; fixed by prefixing with `-` per Router convention

### Completion Notes List

- Installed `@microsoft/fetch-event-source@2.0.1` — provides SSE client with auto-reconnect, AbortController cleanup
- Created `useSSE` hook: connects to backend SSE endpoint, parses events, updates TanStack Query cache directly for instant UI updates
- SSE events handled: `document.processing` → extracting_text status, `document.complete` → complete status, `document.failed` → failed status + error_message
- Reconnection: on `onopen`, invalidates documents query to reconcile missed events; tracks reconnect count with connectionError after 3 failures
- Connection lifecycle: enabled only when documents have non-terminal statuses; AbortController cleanup on unmount
- Removed `refetchInterval` polling from `useDocuments` — SSE fully replaces it
- Created `ProcessingDashboard` component: shows investigation name, document counts (total/complete/failed/remaining), progress bar, live indicator, and degraded-state warning banner
- Integrated into investigation detail page: ProcessingDashboard shown above document list when documents exist; useSSE wired with enabled flag
- 21 new tests (11 useSSE hook + 6 ProcessingDashboard + 4 integration); 60 total frontend tests pass, 96 backend tests pass, TypeScript strict mode clean

### File List

**Created:**
- `apps/web/src/hooks/useSSE.ts`
- `apps/web/src/hooks/useSSE.test.ts`
- `apps/web/src/components/investigation/ProcessingDashboard.tsx`
- `apps/web/src/components/investigation/ProcessingDashboard.test.tsx`
- `apps/web/src/routes/investigations/-$id.test.tsx`

**Modified:**
- `apps/web/package.json` — added @microsoft/fetch-event-source dependency
- `apps/web/src/hooks/useDocuments.ts` — removed refetchInterval polling
- `apps/web/src/routes/investigations/$id.tsx` — integrated useSSE + ProcessingDashboard
- `apps/web/src/components/investigation/DocumentCard.tsx` — added disabled "View Text" button for completed documents (AC4)
- `pnpm-lock.yaml` — lock file updated from @microsoft/fetch-event-source install
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — status updates

## Senior Developer Review (AI)

**Reviewer:** Gennadiy | **Date:** 2026-03-08 | **Outcome:** Approved after fixes

### Issues Found & Fixed

| # | Severity | Issue | Fix |
|---|----------|-------|-----|
| H1 | HIGH | `onerror` never stopped retries after MAX_RECONNECT_FAILURES — infinite failing network requests | Throw `FatalSSEError` after 3 failures to halt retry loop |
| H2 | HIGH | Missing disabled "View Text" link on completed documents (AC4 not met) | Added disabled `<Button>` with Eye icon to DocumentCard for complete status |
| M1 | MEDIUM | `onopen` didn't validate server response — 404 treated as success | Added `response.ok` check, throw `FatalSSEError` on bad status |
| M2 | MEDIUM | Integration tests tested `Array.some()` and duplicated ProcessingDashboard tests | Rewrote with meaningful SSE state combination tests |
| M3 | MEDIUM | Initially attempted to skip invalidation on first connect — reverted: first-connect invalidation is a necessary safety net against SSE connection race condition (events published before SSE connects are lost) | Kept original behavior: invalidate on every `onopen` |
| L1 | LOW | Broad catch swallowed all errors in onmessage | Narrowed try scope to `JSON.parse` only |
| L2 | LOW | `pnpm-lock.yaml` not in File List | Added to File List |

### Test Impact
- 3 new tests added (1 useSSE: response validation, 2 DocumentCard: View Text button)
- 63 total frontend tests pass (was 60), TypeScript strict clean

## Change Log

- **2026-03-08 (review):** Code review fixes — stopped infinite retries on SSE failure (throw after 3), added response validation in onopen, added disabled "View Text" button (AC4), narrowed error catch scope, rewrote integration tests, updated File List. Fixed SSE race condition: connect SSE when upload starts (isPending) so connection is established before Celery publishes events; optimistic cache update in upload onSuccess merges queued documents immediately. 63 tests pass.
- **2026-03-08:** Story 2.4 implemented — Real-time processing dashboard with SSE. Added useSSE hook consuming backend SSE events via @microsoft/fetch-event-source, updating TanStack Query cache for instant UI updates. Created ProcessingDashboard component with progress summary and connection status. Replaced polling with SSE in investigation detail page. 21 new tests added.
