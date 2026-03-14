# Story 5.3: Citation Click-Through Viewer

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an investigator,
I want to click any citation in an answer and see the original document passage,
So that I can verify every fact the system presents.

## Acceptance Criteria

1. **GIVEN** an answer contains superscript citation numbers, **WHEN** the investigator clicks a citation number (superscript in answer text or numbered entry in citation footer), **THEN** a Citation Modal opens showing the original source passage with the relevant text highlighted, **AND** the modal displays: document filename, page number, and surrounding context (preceding and following text in muted color), **AND** the modal is built on Radix UI Dialog (inherits focus trap, aria-modal, Escape handling), **AND** modal enters with fade in + scale from 0.95 (150ms ease-out).

2. **GIVEN** the Citation Modal is open with a source passage, **WHEN** the investigator views the passage, **THEN** entity names within the passage are clickable (same entity link styling as Answer Panel), **AND** clicking an entity name in the passage closes the modal and centers that entity in the graph, **AND** a footer displays chunk position (e.g., "Chunk 14 of 47").

3. **GIVEN** the citation passage is being fetched, **WHEN** the modal opens, **THEN** a loading skeleton is displayed, **AND** once loaded the passage replaces the skeleton near-instantly (local storage, should be <200ms).

4. **GIVEN** an answer contains highlighted entity names, **WHEN** the investigator clicks an entity name in the answer text, **THEN** the graph panel centers on and highlights that entity node, **AND** the entity's neighborhood is expanded if not already loaded. *(Already implemented in Story 5.2 — verify it still works correctly.)*

5. **GIVEN** a citation references a specific passage, **WHEN** the citation is resolved, **THEN** the passage text matches exactly what was extracted from the document, **AND** every citation resolves to an actual document chunk (zero orphaned citations), **AND** 100% of facts in the answer are traceable to a specific source document passage (NFR21).

## Tasks / Subtasks

- [x] **Task 1: Create backend chunk-with-context endpoint** (AC: 1, 2, 3, 5)
  - [x] 1.1: Create `apps/api/app/api/v1/chunks.py` with `GET /api/v1/investigations/{investigation_id}/chunks/{chunk_id}`
  - [x] 1.2: Create `ChunkWithContextResponse` schema in `apps/api/app/schemas/chunk.py`: `{ chunk_id, document_id, document_filename, sequence_number, total_chunks, text, page_start, page_end, context_before (text of previous chunk or null), context_after (text of next chunk or null) }`
  - [x] 1.3: Implement service function in `apps/api/app/services/chunk.py`: query `DocumentChunk` by ID, fetch adjacent chunks by `document_id` + `sequence_number +/- 1`, fetch total chunk count, join document filename
  - [x] 1.4: Validate `investigation_id` matches chunk's investigation (security: prevent cross-investigation data access)
  - [x] 1.5: Register router in `apps/api/app/api/v1/router.py`
  - [x] 1.6: Return 404 with `urn:osint:error:chunk_not_found` if chunk doesn't exist
  - [x] 1.7: Write endpoint tests in `apps/api/tests/api/test_chunks.py`: happy path, 404, cross-investigation rejection
  - [x] 1.8: Write service tests in `apps/api/tests/services/test_chunks.py`: context fetching, edge cases (first chunk has no context_before, last chunk has no context_after)

- [x] **Task 2: Regenerate OpenAPI types** (AC: 1)
  - [x] 2.1: Run `cd apps/api && uv run python -m app.generate_openapi` to export updated schema
  - [x] 2.2: Run `cd apps/web && pnpm run generate-types` to regenerate `api-types.generated.ts`
  - [x] 2.3: Verify `ChunkWithContextResponse` type appears in generated types

- [x] **Task 3: Create useChunkContext hook** (AC: 1, 2, 3)
  - [x] 3.1: Create `apps/web/src/hooks/useChunkContext.ts`
  - [x] 3.2: Use `@tanstack/react-query` `useQuery` with `queryKey: ["chunk-context", investigationId, chunkId]`
  - [x] 3.3: Call `GET /api/v1/investigations/{investigation_id}/chunks/{chunk_id}` via `api` client from `api-client.ts`
  - [x] 3.4: Enable query only when `chunkId` is not null (modal is open with a valid citation)
  - [x] 3.5: Return typed `ChunkWithContextResponse` data

- [x] **Task 4: Create CitationModal component** (AC: 1, 2, 3)
  - [x] 4.1: Create `apps/web/src/components/qa/CitationModal.tsx`
  - [x] 4.2: Build on shadcn/ui `Dialog` with `max-w-2xl` (640px per UX spec)
  - [x] 4.3: **Header:** Close button (x), "Citation — {document_filename}", "Page {page_start}" (or "Pages {page_start}-{page_end}" if multi-page)
  - [x] 4.4: **Body — context before:** Render `context_before` text in `--text-muted` color with Source Serif 4 font. Separated by subtle border from highlighted passage.
  - [x] 4.5: **Body — highlighted passage:** Render chunk `text` with `<mark>` element, background `--bg-hover`, text `--text-primary`, Source Serif 4 at `--text-base` (15px) with 1.8 line height. Within the passage, parse and highlight entity names using the same `**Entity Name**` → clickable link pattern from AnswerPanel.
  - [x] 4.6: **Body — context after:** Render `context_after` text in `--text-muted` color. Separated by subtle border from highlighted passage.
  - [x] 4.7: **Footer:** "Chunk {sequence_number} of {total_chunks}" in `--text-secondary`
  - [x] 4.8: **Loading state:** Skeleton placeholder matching modal anatomy while chunk data loads
  - [x] 4.9: **Error state:** "Failed to load source passage. Please try again." with retry button
  - [x] 4.10: Accept props: `citation: Citation | null`, `investigationId: string`, `open: boolean`, `onOpenChange: (open: boolean) => void`, `onEntityClick: (entityName: string) => void`
  - [x] 4.11: Entity names in passage — match against `entities_mentioned` from the conversation entry if available, or render as generic styled links
  - [x] 4.12: Close via x button, Escape key, or clicking backdrop (all provided by Radix Dialog)
  - [x] 4.13: Add `aria-label="Source citation from {filename}, page {page}"` on the Dialog

- [x] **Task 5: Wire CitationModal into investigation detail page** (AC: 1, 4)
  - [x] 5.1: In `apps/web/src/routes/investigations/$id.tsx`, add state: `const [activeCitation, setActiveCitation] = useState<Citation | null>(null)`
  - [x] 5.2: Update `handleCitationClick` to resolve citation: if `number` is passed (superscript click), look up full `Citation` object from the current conversation's citations array; if `Citation` object is passed (footer click), use directly
  - [x] 5.3: Set `activeCitation` to open the modal, set to `null` to close
  - [x] 5.4: Render `<CitationModal citation={activeCitation} investigationId={investigationId} open={!!activeCitation} onOpenChange={(open) => !open && setActiveCitation(null)} onEntityClick={handleEntityClick} />`
  - [x] 5.5: Pass conversation entries (or at minimum `entities_mentioned` from the latest complete entry) to CitationModal for entity type resolution
  - [x] 5.6: Wire `onEntityClick` from CitationModal — close modal first, then dispatch entity click to GraphCanvas (center + highlight)

- [x] **Task 6: Resolve citation number to Citation object** (AC: 1)
  - [x] 6.1: Track citations from completed conversation entries in QAPanel or investigation page state
  - [x] 6.2: When superscript citation `[N]` is clicked (passes `number`), find the matching `Citation` object from the most recent conversation entry's `citations[]` where `citation.citation_number === N`
  - [x] 6.3: If citation lookup fails (edge case), show error toast or fallback message in modal

- [x] **Task 7: Write tests for CitationModal component** (AC: 1, 2, 3)
  - [x] 7.1: Create `apps/web/src/components/qa/CitationModal.test.tsx`
  - [x] 7.2: Test modal opens when `open={true}` and citation is provided
  - [x] 7.3: Test header displays filename and page number from citation
  - [x] 7.4: Test highlighted passage rendered with `<mark>` element
  - [x] 7.5: Test context_before and context_after rendered in muted color
  - [x] 7.6: Test chunk position footer ("Chunk X of Y")
  - [x] 7.7: Test loading state shows skeleton
  - [x] 7.8: Test error state shows error message with retry
  - [x] 7.9: Test entity names in passage are clickable and dispatch onEntityClick
  - [x] 7.10: Test modal closes on Escape key
  - [x] 7.11: Test aria-label set correctly

- [x] **Task 8: Write tests for useChunkContext hook** (AC: 3)
  - [x] 8.1: Create `apps/web/src/hooks/useChunkContext.test.ts`
  - [x] 8.2: Mock API client, test successful data fetch
  - [x] 8.3: Test query disabled when chunkId is null
  - [x] 8.4: Test error handling

- [x] **Task 9: Write integration test for citation click-through flow** (AC: 1, 2, 4)
  - [x] 9.1: Update `apps/web/src/routes/investigations/-$id.test.tsx`
  - [x] 9.2: Test that clicking a citation superscript in the answer opens the CitationModal
  - [x] 9.3: Test that clicking a citation in the footer opens the CitationModal
  - [x] 9.4: Test that clicking an entity name in the passage closes modal and triggers graph navigation
  - [x] 9.5: Test that closing the modal returns focus to the Q&A panel

## Dev Notes

### Architecture Context

This is **Story 5.3** in Epic 5 (Natural Language Q&A with Source Citations). Stories 5.1 (GRAPH FIRST Query Pipeline) and 5.2 (Answer Streaming & Q&A Panel) are **done**. The entire backend query pipeline and frontend Q&A panel are complete.

**This story has a small backend component** (chunk-with-context endpoint) and a larger frontend component (Citation Modal + wiring).

Story 5.3 is the **trust mechanism** of the entire product. The UX spec explicitly states: "Product credibility depends entirely on the citation click-through experience. Investigators must be able to quickly verify any fact against its original document passage to trust the system enough to publish or prosecute." This is the highest-priority custom component alongside the Answer Panel.

### Backend: Chunk-with-Context Endpoint

**Why a new endpoint is needed:**
The Citation object from `query.complete` SSE events contains: `citation_number`, `document_id`, `document_filename`, `chunk_id`, `page_start`, `page_end`, `text_excerpt`. The `text_excerpt` is the cited passage itself — but the UX spec requires **surrounding context** (preceding and following paragraphs in muted text) and **chunk position** ("Chunk 14 of 47"). This data isn't available without querying the `document_chunks` table.

**Existing infrastructure:**
- `DocumentChunk` model (`apps/api/app/models/chunk.py`): `id`, `document_id`, `investigation_id`, `sequence_number`, `text`, `page_start`, `page_end`, `char_offset_start`, `char_offset_end`, `token_count`
- Chunks are indexed on `(document_id, sequence_number)` — efficient adjacent chunk lookup
- No existing chunk API endpoint — all chunk access is currently internal (processing pipeline, query service)

**Endpoint design:**
```
GET /api/v1/investigations/{investigation_id}/chunks/{chunk_id}
Response: ChunkWithContextResponse {
  chunk_id: UUID
  document_id: UUID
  document_filename: str
  sequence_number: int
  total_chunks: int
  text: str
  page_start: int
  page_end: int
  context_before: str | None  # Previous chunk's text, null if first chunk
  context_after: str | None   # Next chunk's text, null if last chunk
}
```

**Security:** Validate that the chunk belongs to the specified `investigation_id`. The `DocumentChunk` model has `investigation_id` field — use it to prevent cross-investigation data access.

**Service implementation pattern** — follow the existing pattern in `apps/api/app/services/`:
```python
async def get_chunk_with_context(db: AsyncSession, investigation_id: UUID, chunk_id: UUID) -> ChunkWithContextResponse:
    # 1. Fetch the target chunk, verify investigation_id
    # 2. Count total chunks for this document
    # 3. Fetch adjacent chunks (sequence_number +/- 1) for context
    # 4. Join document table for filename
    # 5. Return composed response
```

### Frontend: Citation Modal Component

**Modal anatomy** (per UX spec):
```
+-------------------------------------------+
|  x  Citation -- contract-award-089.pdf    |
|      Page 3                               |
+-------------------------------------------+
|                                           |
|  ...preceding context in muted text...    |
|                                           |
|  +- Highlighted Passage ----------------+ |
|  | "Deputy Mayor Horvat signed the      | |
|  |  contract award #2024-089 granting   | |
|  |  the municipal construction tender   | |
|  |  to GreenBuild LLC on March 15."     | |
|  +--------------------------------------+ |
|                                           |
|  ...following context in muted text...    |
|                                           |
|  [Entity Name] [Entity Name] clickable    |
+-------------------------------------------+
|  Chunk 14 of 47                           |
+-------------------------------------------+
```

**Styling tokens:**
- Modal background: `--bg-elevated` (#2d2a23)
- Max-width: 640px (`max-w-2xl`)
- Passage font: Source Serif 4 (`var(--font-serif)`) at 15px with 1.8 line height
- Highlighted passage background: `--bg-hover` (#38342b)
- Context text color: `--text-muted` (#7a7168)
- Passage text color: `--text-primary` (#e8e0d4)
- Chunk position text: `--text-secondary` (#a89f90)
- Entity link colors: `--entity-person` (#6b9bd2), `--entity-org` (#c4a265), `--entity-location` (#7dab8f)
- Citation link color from UX spec: `--citation-link` (#9b8ec4) — **NOTE:** this token is defined in UX spec but may need to be added to `globals.css` if not present (Story 5.2 used `--status-info` for citations instead)

### Citation Number Resolution

**Current click handler** (`apps/web/src/routes/investigations/$id.tsx:66-69`):
```typescript
const handleCitationClick = useCallback((citation: Citation | number) => {
  console.log("Citation clicked:", citation);
}, []);
```

**The handler receives two types:**
1. **`number`** — from superscript `[N]` clicks in answer text (AnswerPanel line 58: `onCitationClick(seg.num)`)
2. **`Citation` object** — from citation footer clicks (AnswerPanel line 182: `onCitationClick(cit)`)

**Resolution strategy:**
- When a `number` is received, look up the full `Citation` object from the conversation entries. The `ConversationEntry` in QAPanel stores `citations: Citation[]` for each completed answer.
- Need to expose citations from QAPanel to the investigation page, or track them in the page state via a callback.
- Simplest approach: add an `onConversationUpdate` callback from QAPanel, or lift citation tracking to the investigation page via a ref or state.

### Entity Parsing in Passage Text

The passage text from the chunk may contain entity names that should be clickable. Two approaches:

1. **Use `entities_mentioned` from the conversation entry** — match entity names against the passage text using the same `**Entity Name**` regex from AnswerPanel
2. **Simpler: don't parse entities in the raw chunk text** — the chunk text is raw extracted text, NOT LLM-formatted with `**bold**` markers. Only the LLM answer has bold entity names.

**Decision: Parse entity names from `entities_mentioned` list by doing a case-insensitive text search** in the passage. For each entity in `entities_mentioned`, find occurrences in the chunk text and make them clickable. This is more robust than regex since chunk text doesn't have markdown formatting.

### What Already Exists (DO NOT recreate)

| Component | Location | What It Does |
|-----------|----------|-------------|
| Citation type | `apps/web/src/components/qa/types.ts` | `Citation { citation_number, document_id, document_filename, chunk_id, page_start, page_end, text_excerpt }` |
| AnswerPanel | `apps/web/src/components/qa/AnswerPanel.tsx` | Already renders citations as superscripts and footer. `onCitationClick` wired. |
| QAPanel | `apps/web/src/components/qa/QAPanel.tsx` | Container with conversation state. Has `onCitationClick` prop. |
| Investigation page | `apps/web/src/routes/investigations/$id.tsx` | Has `handleCitationClick` (currently logs). Wires QAPanel props. |
| Dialog | `apps/web/src/components/ui/dialog.tsx` | shadcn/ui Dialog with all Radix primitives (DialogContent, DialogHeader, DialogTitle, etc.) |
| DocumentTextViewer | `apps/web/src/components/investigation/DocumentTextViewer.tsx` | Reference implementation: Dialog-based document text display with page parsing. Reuse pattern, NOT the component itself. |
| useDocumentText | `apps/web/src/hooks/useDocuments.ts` | Fetches full document text. NOT needed for this story (using chunk endpoint instead). |
| DocumentChunk model | `apps/api/app/models/chunk.py` | SQLAlchemy model with `id`, `document_id`, `investigation_id`, `sequence_number`, `text`, `page_start`, `page_end` |
| GraphCanvas | `apps/web/src/components/graph/GraphCanvas.tsx` | Has entity navigation. `onEntityClick` callback already wired from Story 5.2. |
| globals.css | `apps/web/src/globals.css` | All theme tokens. |
| api client | `apps/web/src/lib/api-client.ts` | `openapi-fetch` client for typed API calls. |

### Key Design Tokens for Citation Modal

```css
/* Modal surface */
--bg-elevated: #2d2a23;       /* Modal background per UX spec */

/* Text */
--text-primary: #e8e0d4;       /* Highlighted passage text */
--text-secondary: #a89f90;     /* Chunk position, metadata */
--text-muted: #7a7168;         /* Surrounding context text */

/* Highlighted passage */
--bg-hover: #38342b;           /* Passage highlight background */

/* Entity type colors (for entity links in passage) */
--entity-person: #6b9bd2;
--entity-org: #c4a265;
--entity-location: #7dab8f;

/* Borders */
--border-subtle: #3d3830;      /* Separator between context and passage */

/* Typography */
font-family: var(--font-serif); /* Source Serif 4 for passage text */
font-size: 15px;                /* --text-base */
line-height: 1.8;              /* Editorial reading line height */
```

### Testing Patterns (from existing frontend tests)

**Test setup pattern:**
```typescript
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

function renderWithProviders(ui: React.ReactElement) {
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
  );
}
```

**Mock patterns:**
- Mock `useChunkContext` hook when testing CitationModal — provide controlled chunk data
- Mock `api.GET` when testing the hook itself
- Use `userEvent` for interaction testing (click, keyboard)
- Use `screen.getByText`, `screen.getByRole`, `screen.getByLabelText` for queries

**Backend test patterns:**
```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_get_chunk_with_context(client: AsyncClient, ...):
    response = await client.get(f"/api/v1/investigations/{inv_id}/chunks/{chunk_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["chunk_id"] == str(chunk_id)
    assert data["context_before"] is not None  # not first chunk
```

### Project Structure Notes

**New files:**
- `apps/api/app/api/v1/chunks.py` — Chunk API endpoint
- `apps/api/app/schemas/chunk.py` — ChunkWithContextResponse schema
- `apps/api/app/services/chunk.py` — Chunk service with context fetching
- `apps/api/tests/api/test_chunks.py` — Endpoint tests
- `apps/api/tests/services/test_chunks.py` — Service tests
- `apps/web/src/hooks/useChunkContext.ts` — Chunk context fetch hook
- `apps/web/src/hooks/useChunkContext.test.ts` — Hook tests
- `apps/web/src/components/qa/CitationModal.tsx` — Citation Modal component
- `apps/web/src/components/qa/CitationModal.test.tsx` — Modal tests

**Modified files:**
- `apps/api/app/api/v1/router.py` — Register chunks router
- `apps/web/src/routes/investigations/$id.tsx` — Add CitationModal state, update handleCitationClick, render CitationModal
- `apps/web/src/routes/investigations/-$id.test.tsx` — Add citation click-through integration tests
- `apps/web/src/lib/api-types.generated.ts` — Regenerated with chunk endpoint types
- `apps/web/src/lib/openapi.json` — Updated OpenAPI spec

**No new dependencies required.** All libraries are already installed.

### Performance Considerations

- **Chunk fetch is fast:** Single database query with indexed lookup. Local storage — should be <200ms.
- **Cache chunks:** TanStack Query caches by `[chunk-context, investigationId, chunkId]`. Same citation clicked twice won't refetch.
- **Modal animation:** Use CSS transitions (fade + scale), not JS animation. Keep it lightweight.
- **Entity name matching:** Simple string search in passage text, not regex. O(n*m) where n=passage length, m=entity count — trivial for typical passages.

### References

- [Source: _bmad-output/planning-artifacts/epics.md — Epic 5, Story 5.3 acceptance criteria and BDD scenarios]
- [Source: _bmad-output/planning-artifacts/prd.md — FR20: Source citations in answers, FR21: Citation click-through to source passage]
- [Source: _bmad-output/planning-artifacts/prd.md — NFR21: 100% fact traceability, NFR22: zero hallucinated facts]
- [Source: _bmad-output/planning-artifacts/prd.md — "Evidence Integrity: Every fact in an answer links to a specific source passage. Zero orphaned citations."]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — Citation Modal anatomy, styling, interactions, accessibility]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — "Citation viewer slides out from right edge over the graph panel" / "Centered overlay with backdrop dimming, max-width 640px"]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — Modal hierarchy: "Full Modal (Citation Modal, Confirmation Dialogs)" with backdrop, focus trap, Escape close]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — Font pairing: "Source Serif 4 only in reading contexts: answer panel, citation viewer, document text"]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — Citation link color: --citation-link (#9b8ec4)]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — "Built on shadcn/ui Dialog (Radix UI) -- focus trap, Escape close, aria-modal=true"]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — Highlighted passage: mark element, aria-label="Source citation from [filename], page [n]"]
- [Source: _bmad-output/planning-artifacts/architecture.md — Naming: CitationModal.tsx (PascalCase), chunk service (snake_case)]
- [Source: _bmad-output/planning-artifacts/architecture.md — API endpoints: kebab-case nouns, plural: /api/v1/investigations/{id}/chunks/{chunk_id}]
- [Source: apps/api/app/models/chunk.py — DocumentChunk model with sequence_number, text, page_start, page_end, investigation_id]
- [Source: apps/api/app/schemas/query.py — Citation schema: citation_number, document_id, document_filename, chunk_id, page_start, page_end, text_excerpt]
- [Source: apps/web/src/components/qa/types.ts — Frontend Citation interface]
- [Source: apps/web/src/components/qa/AnswerPanel.tsx — Citation click handlers: superscript passes number, footer passes Citation object]
- [Source: apps/web/src/routes/investigations/$id.tsx:66-69 — handleCitationClick currently logs, awaiting modal implementation]
- [Source: apps/web/src/components/ui/dialog.tsx — shadcn/ui Dialog primitives ready for use]
- [Source: apps/web/src/components/investigation/DocumentTextViewer.tsx — Reference pattern for Dialog-based document text display]
- [Source: apps/web/src/hooks/useDocuments.ts — useDocumentText hook pattern (for reference)]
- [Source: apps/web/src/globals.css — Theme tokens]

### Previous Story Intelligence (Story 5.2 Learnings)

1. **Entity type names are PascalCase** — `Person`, `Organization`, `Location` in `entities_mentioned[].type`. Map to CSS variables: `Person` -> `--entity-person`, `Organization` -> `--entity-org`, `Location` -> `--entity-location`.

2. **Citation data arrives with `query.complete` event** — The `citations[]` array in the complete payload has all data needed: `citation_number`, `document_id`, `document_filename`, `chunk_id`, `page_start`, `page_end`, `text_excerpt`. The `chunk_id` is the key for fetching context.

3. **AnswerPanel sends two click types** — Superscript clicks pass `number`, footer clicks pass full `Citation` object. The investigation page handler must normalize this.

4. **ConversationEntry tracks citations** — Each completed conversation entry stores `citations: Citation[]`. This is the lookup source for resolving citation numbers to full objects.

5. **SSE response types are manually defined** — Citation, EntityReference types are in `apps/web/src/components/qa/types.ts`, NOT in generated types (because the endpoint returns StreamingResponse).

6. **Entity highlighting works via className** — GraphCanvas uses `addClass('highlighted')` / `removeClass('highlighted')` on Cytoscape nodes. The `onEntityClick` from QAPanel already triggers center + highlight.

7. **Dialog component is already used** — Story 5.2 added a Dialog for document management in the investigation page (line 213-223 of $id.tsx). Follow the same pattern for CitationModal.

8. **Test count baseline:** ~295 backend tests, ~198 frontend tests. This story should add ~8-10 backend tests (endpoint + service) and ~15-20 frontend tests (modal + hook + integration).

### Git Intelligence

Recent commits (for pattern continuity):
- `b3326fd` — feat: improve query pipeline -- multilingual support, Cypher validation & result quality
- `58916bb` — feat: Story 5.2 -- answer streaming QA panel + UI layout cleanup
- `bf2d2c6` — feat: Story 5.1 -- graph-first natural language query pipeline

**Commit message format:** `feat: Story 5.3 -- citation click-through viewer`

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

No debug issues encountered.

### Completion Notes List

- Implemented chunk-with-context backend endpoint (`GET /api/v1/investigations/{investigation_id}/chunks/{chunk_id}`) with schema, service, and security validation (cross-investigation access prevention)
- Added `ChunkNotFoundError` domain exception returning `urn:osint:error:chunk_not_found` (404)
- Regenerated OpenAPI spec and TypeScript types — `ChunkWithContextResponse` available in generated types
- Created `useChunkContext` React Query hook with conditional fetching (disabled when chunkId is null)
- Built `CitationModal` component using shadcn/ui Dialog with: header (filename + page), context before/after (muted), highlighted passage (`<mark>` element), entity name highlighting from `entities_mentioned`, chunk position footer, loading skeleton, error state with retry, aria-label accessibility
- Wired CitationModal into investigation detail page: added `activeCitation` state, citation number resolution from conversation entries via `onConversationUpdate` callback from QAPanel, entity click from modal closes modal and highlights entity in graph
- Added 9 backend tests (4 endpoint + 5 service) covering happy path, 404, cross-investigation rejection, first/last chunk edge cases
- Added 14 frontend unit tests (10 CitationModal + 4 useChunkContext hook)
- Added 4 integration tests covering citation superscript click, footer click, entity click in passage, and modal close
- All 304 backend tests pass, all 216 frontend tests pass — zero regressions

**Code Review Fixes (2026-03-14):**
- Fixed citation number resolution fallback: now shows user-visible error notification instead of silent console.warn (H1)
- Fixed entity highlighting in multi-turn conversations: entities now come from the specific conversation entry containing the clicked citation, not always the latest entry (M1)
- Fixed chunk position footer: displays 1-based sequence number (was showing 0-based, e.g. "Chunk 0 of 20" for first chunk) (M2)
- Fixed entity link accessibility: added Space key activation alongside Enter for role="button" elements per WCAG 2.1 (M3)
- Added `staleTime: Infinity` to useChunkContext query (chunk data is immutable) (L3)
- Added Space key activation test for entity links in CitationModal (+1 test, 217 frontend tests total)

### Change Log

- 2026-03-14: Story 5.3 implementation complete — citation click-through viewer with full backend + frontend
- 2026-03-14: Code review fixes — 5 issues fixed (H1, M1, M2, M3, L3), 1 test added

### File List

**New files:**
- `apps/api/app/api/v1/chunks.py` — Chunk API endpoint
- `apps/api/app/schemas/chunk.py` — ChunkWithContextResponse schema
- `apps/api/app/services/chunk.py` — Chunk service with context fetching
- `apps/api/tests/api/test_chunks.py` — Endpoint tests (4 tests)
- `apps/api/tests/services/test_chunks.py` — Service tests (5 tests)
- `apps/web/src/hooks/useChunkContext.ts` — Chunk context fetch hook
- `apps/web/src/hooks/useChunkContext.test.ts` — Hook tests (4 tests)
- `apps/web/src/components/qa/CitationModal.tsx` — Citation Modal component
- `apps/web/src/components/qa/CitationModal.test.tsx` — Modal tests (11 tests)

**Modified files:**
- `apps/api/app/api/v1/router.py` — Registered chunks router
- `apps/api/app/exceptions.py` — Added ChunkNotFoundError
- `apps/api/tests/conftest.py` — Added chunk fixtures
- `apps/web/src/lib/openapi.json` — Updated OpenAPI spec
- `apps/web/src/lib/api-types.generated.ts` — Regenerated with chunk endpoint types
- `apps/web/src/components/qa/QAPanel.tsx` — Added onConversationUpdate callback
- `apps/web/src/routes/investigations/$id.tsx` — Added CitationModal state, citation resolution, entity click wiring
- `apps/web/src/routes/investigations/-$id.test.tsx` — Added citation click-through integration tests (4 tests)
