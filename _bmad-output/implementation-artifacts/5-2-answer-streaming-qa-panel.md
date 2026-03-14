# Story 5.2: Answer Streaming & Q&A Panel

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an investigator,
I want to see answers stream in progressively with citations I can click,
So that I get results quickly and can immediately verify any fact.

## Acceptance Criteria

1. **GIVEN** a query is processing, **WHEN** the answer begins streaming, **THEN** the Q&A panel (left side of split view) displays answer text progressively via SSE `query.streaming` events, **AND** answer text uses Perplexity-style cited prose: entity names are highlighted and clickable, citations appear as superscript numbers, **AND** query status updates show in the panel: translating → searching → streaming answer.

2. **GIVEN** answer streaming completes, **WHEN** the `query.complete` SSE event arrives, **THEN** the complete answer is displayed with all citations and entity highlights, **AND** suggested follow-up questions appear below the answer, **AND** the total time from question to answer is <30 seconds on minimum hardware.

3. **GIVEN** the query fails, **WHEN** a `query.failed` SSE event arrives, **THEN** a clear error message is displayed in the Q&A panel, **AND** the investigator can retry or ask a different question.

4. **GIVEN** the investigator has asked previous questions, **WHEN** they ask a follow-up question, **THEN** the conversation history is maintained within the session, **AND** the LLM uses prior conversation context for query translation (conversational investigation).

## Tasks / Subtasks

- [x] **Task 1: Create useQueryStream hook for POST+SSE query streaming** (AC: 1, 2, 3, 4)
  - [x]1.1: Create `apps/web/src/hooks/useQueryStream.ts`
  - [x]1.2: Implement the hook with state machine: `idle` → `translating` → `searching` → `streaming` → `complete` | `error`
  - [x]1.3: Use `@microsoft/fetch-event-source` to POST to `/api/v1/investigations/{investigation_id}/query/` with `QueryRequest` body (question + conversation_history)
  - [x]1.4: Handle `query.translating` SSE event — set status to `translating`
  - [x]1.5: Handle `query.searching` SSE event — set status to `searching`
  - [x]1.6: Handle `query.streaming` SSE event — append `chunk` to accumulated answer text, set status to `streaming`
  - [x]1.7: Handle `query.complete` SSE event — parse full payload: `answer`, `citations[]`, `entities_mentioned[]`, `suggested_followups[]`, `no_results`, set status to `complete`
  - [x]1.8: Handle `query.failed` SSE event — extract error message, set status to `error`
  - [x]1.9: Maintain `conversationHistory: ConversationTurn[]` in React state — append user question + assistant answer after each complete query
  - [x]1.10: Pass full `conversation_history` to every query request for conversational context
  - [x]1.11: Provide `submitQuery(question: string)` function and `resetConversation()` function
  - [x]1.12: On SSE connection error or abort, set status to `error` with user-friendly message

- [x] **Task 2: Create QueryInput component** (AC: 1, 4)
  - [x]2.1: Create `apps/web/src/components/qa/QueryInput.tsx`
  - [x]2.2: Render a `<textarea>` with Source Serif 4 font for input (matching UX spec for Q&A input), auto-resize on content
  - [x]2.3: Submit on Enter (without Shift), Shift+Enter for newline
  - [x]2.4: Submit button using existing `Button` component (shadcn/ui) with send icon (lucide `Send`)
  - [x]2.5: Disable input and button while query is in-flight (status is not `idle` and not `complete` and not `error`)
  - [x]2.6: Accept `onSubmit: (question: string) => void` prop and optional `prefillQuestion: string` prop
  - [x]2.7: When `prefillQuestion` changes (from "Ask about entity" action), populate input and optionally auto-submit
  - [x]2.8: Clear input after successful submission
  - [x]2.9: Add `aria-label="Ask a question about your investigation"` for accessibility

- [x] **Task 3: Create AnswerPanel component** (AC: 1, 2, 3)
  - [x]3.1: Create `apps/web/src/components/qa/AnswerPanel.tsx`
  - [x]3.2: Render conversation as a scrollable vertical list of question/answer pairs
  - [x]3.3: Each user question displayed in a message bubble with slightly different background (`--bg-hover`)
  - [x]3.4: Each answer displayed with Source Serif 4 typography at `15px` with `1.8` line height (per UX spec `--text-base`)
  - [x]3.5: **Parse answer text for citations:** Replace `[N]` patterns with clickable superscript `<sup>` elements styled with `--status-info` color. Each superscript is an `<a>` with `aria-label="Source: [filename], page [n]"`
  - [x]3.6: **Parse answer text for entity names:** Replace `**Entity Name**` (bold markdown) with clickable entity links styled with entity-type color underline (person=`--entity-person`, org=`--entity-org`, location=`--entity-location`). Each link has `aria-label="Explore [entity name] in graph"`
  - [x]3.7: Entity type for styling — match entity name against `entities_mentioned[]` from the `query.complete` payload to get the type
  - [x]3.8: **Streaming state:** Display accumulated text progressively as chunks arrive. Show a blinking cursor at end while streaming.
  - [x]3.9: **Query status indicator:** Show inline status text below the question during processing: "Translating your question..." → "Searching knowledge graph and documents..." → "Streaming answer..." (matches SSE event phases per UX spec)
  - [x]3.10: **No results state:** When `no_results: true`, display "No connection found in your documents." with suggestion to rephrase or explore graph manually
  - [x]3.11: **Error state:** Display error message with `--status-error` color and a "Try again" button that resubmits the same question
  - [x]3.12: **Citation footer:** Below each answer, render numbered citation list: `[N] filename, page X` — each clickable (dispatches `onCitationClick(citation)`)
  - [x]3.13: Auto-scroll to bottom when new answer starts streaming, but respect manual scroll-up (stop auto-scroll if user scrolls up)
  - [x]3.14: Accept props: `conversation: ConversationEntry[]`, `streamingText: string`, `status: QueryStatus`, `onCitationClick: (citation) => void`, `onEntityClick: (entityName: string) => void`
  - [x]3.15: Use `aria-live="polite"` region for streaming state announcements

- [x] **Task 4: Create SuggestedQuestions component** (AC: 2)
  - [x]4.1: Create `apps/web/src/components/qa/SuggestedQuestions.tsx`
  - [x]4.2: Render 2-4 follow-up questions as clickable cards/buttons below each completed answer
  - [x]4.3: Each question shows bold question text — styled with `--text-primary`
  - [x]4.4: Hover state with `--bg-hover` background
  - [x]4.5: Click dispatches `onQuestionClick(question: string)` which submits as a new query
  - [x]4.6: **Loading state:** Show skeleton placeholder while answer is still streaming (follow-ups arrive with `query.complete`)
  - [x]4.7: **Empty state:** Hidden when `no_results` is true or no follow-ups provided
  - [x]4.8: Focusable list items, Enter to submit (keyboard accessibility)

- [x] **Task 5: Create QAPanel container component** (AC: 1, 2, 3, 4)
  - [x]5.1: Create `apps/web/src/components/qa/QAPanel.tsx`
  - [x]5.2: Compose `AnswerPanel` + `SuggestedQuestions` + `QueryInput` into a single vertical layout
  - [x]5.3: Layout: scrollable conversation area (flex-1) at top, fixed QueryInput at bottom
  - [x]5.4: Initialize `useQueryStream` hook and wire all child components
  - [x]5.5: **Initial state (no questions yet):** Show suggested starting questions like "How are the entities in your documents connected?" or entity-based suggestions if entity data is available
  - [x]5.6: Accept props: `investigationId: string`, `onEntityClick: (entityName: string) => void`, `onCitationClick: (citation: Citation) => void`, `prefillQuestion?: string`
  - [x]5.7: Background color: `--bg-secondary` (matches UX spec for Q&A panel/sidebars)

- [x] **Task 6: Restructure investigation detail page layout** (AC: 1)
  - [x]6.1: Modify `apps/web/src/routes/investigations/$id.tsx`
  - [x]6.2: When `hasEntities` is true, change the split view: **left panel = QAPanel** (40%), **right panel = GraphCanvas** (60%)
  - [x]6.3: Move document management (DocumentUploadZone, DocumentList, ProcessingDashboard) to a collapsible overlay or a small toggle button that opens a slide-over panel — documents are accessible but not the primary left-panel content when entities exist
  - [x]6.4: Pass `investigationId` and callback props to QAPanel
  - [x]6.5: Wire `onEntityClick` from QAPanel to GraphCanvas — clicking an entity name in the answer should center+highlight that entity in the graph
  - [x]6.6: Wire `onAskAboutEntity` from GraphCanvas (the existing TODO at line 327-329) to QAPanel's `prefillQuestion` prop — clicking "Ask about this entity" in EntityDetailCard pre-fills the Q&A input with "What connections does [entity name] have?"
  - [x]6.7: Wire `onCitationClick` — for now, log citation data (Story 5.3 will implement the Citation Modal)

- [x] **Task 7: Wire graph-QA entity highlighting** (AC: 2)
  - [x]7.1: When `query.complete` arrives with `entities_mentioned[]`, pass entity IDs/names to GraphCanvas
  - [x]7.2: GraphCanvas should highlight (glow/pulse briefly, then elevated opacity) matching entity nodes while dimming non-relevant nodes
  - [x]7.3: Add a `highlightEntities: string[]` prop to GraphCanvas (or pass via callback)
  - [x]7.4: Clear highlighting when a new query starts or when the user interacts with the graph
  - [x]7.5: Use existing Cytoscape.js `addClass`/`removeClass` pattern for highlighting (reference existing filter highlighting in GraphCanvas)

- [x] **Task 8: Write tests for useQueryStream hook** (AC: 1, 2, 3, 4)
  - [x]8.1: Create `apps/web/src/hooks/useQueryStream.test.ts`
  - [x]8.2: Mock `fetchEventSource` from `@microsoft/fetch-event-source`
  - [x]8.3: Test status transitions: idle → translating → searching → streaming → complete
  - [x]8.4: Test streaming chunk accumulation — multiple `query.streaming` events concatenate into full answer
  - [x]8.5: Test `query.complete` event parsing — citations, entities_mentioned, suggested_followups populated
  - [x]8.6: Test `query.failed` event — status set to error with message
  - [x]8.7: Test conversation history — after complete, conversationHistory contains the turn
  - [x]8.8: Test conversation history passed to subsequent queries
  - [x]8.9: Test `no_results` flag handling

- [x] **Task 9: Write tests for QA components** (AC: 1, 2, 3)
  - [x]9.1: Create `apps/web/src/components/qa/QueryInput.test.tsx`
  - [x]9.2: Test submit on Enter, no submit on Shift+Enter
  - [x]9.3: Test input disabled during query processing
  - [x]9.4: Test prefillQuestion populates input
  - [x]9.5: Create `apps/web/src/components/qa/AnswerPanel.test.tsx`
  - [x]9.6: Test citation parsing — `[1]` rendered as clickable superscript
  - [x]9.7: Test entity name parsing — `**Horvat**` rendered as clickable link
  - [x]9.8: Test streaming state — text appears progressively with cursor
  - [x]9.9: Test no-results state — "No connection found" message displayed
  - [x]9.10: Test error state — error message with retry button
  - [x]9.11: Create `apps/web/src/components/qa/SuggestedQuestions.test.tsx`
  - [x]9.12: Test questions render and are clickable
  - [x]9.13: Test loading skeleton shown during streaming
  - [x]9.14: Test hidden when no_results

- [x] **Task 10: Write integration test for investigation page with Q&A** (AC: 1, 4)
  - [x]10.1: Update `apps/web/src/routes/investigations/-$id.test.tsx` (or create new test)
  - [x]10.2: Test that QAPanel renders in left panel when entities exist
  - [x]10.3: Test that document management is still accessible
  - [x]10.4: Test entity click from answer → graph highlight
  - [x]10.5: Test "Ask about this entity" from graph → Q&A input prefilled

## Dev Notes

### Architecture Context

This is **Story 5.2** in Epic 5 (Natural Language Q&A with Source Citations). Story 5.1 (GRAPH FIRST Query Pipeline) is **done** — the entire backend is complete including:
- `POST /api/v1/investigations/{id}/query/` endpoint returning SSE stream
- Query service with translate → graph search + vector search → merge → format → stream pipeline
- All schemas: QueryRequest, QueryResponse, Citation, EntityReference, QuerySSEEvent
- 25 backend tests (7 endpoint + 18 service)

**This story is 100% frontend.** No backend changes needed. The backend SSE stream is ready.

Story 5.3 (Citation Click-Through Viewer) is next — it will implement the Citation Modal. In this story, citation clicks should dispatch an event/callback but the modal itself is deferred to 5.3.

### SSE Streaming Architecture — CRITICAL DIFFERENCE from existing useSSE

**The existing `useSSE.ts` hook** (`apps/web/src/hooks/useSSE.ts`) connects to `GET /api/v1/investigations/{id}/events` for document processing events. It uses React Query cache updates.

**The query SSE stream is fundamentally different:**
- It uses **POST** (not GET) — sends `QueryRequest` body with the question
- It's a **per-query stream** that opens, streams events, and closes (not a persistent connection)
- It returns query-specific events: `query.translating`, `query.searching`, `query.streaming`, `query.complete`, `query.failed`
- The `query.streaming` events contain `{chunk}` data that must be accumulated into a growing answer string
- The `query.complete` event contains the full payload: `{answer, citations[], entities_mentioned[], suggested_followups[], no_results}`

**DO NOT reuse or extend the existing `useSSE.ts` hook.** Create a new `useQueryStream.ts` hook specifically for query streaming. The patterns are different enough to warrant a separate hook.

**`@microsoft/fetch-event-source` supports POST** — this is why it was chosen over native EventSource (which only supports GET). Already installed: `@microsoft/fetch-event-source@2.0.1`.

### SSE Event Payloads (from backend `apps/api/app/schemas/query.py`)

```typescript
// query.translating
{ query_id: string, message: "Translating your question..." }

// query.searching
{ query_id: string, message: "Searching knowledge graph and documents..." }

// query.streaming
{ query_id: string, chunk: string }  // Accumulated text chunks

// query.complete
{
  query_id: string,
  answer: string,           // Full answer text
  citations: Citation[],     // { citation_number, document_id, document_filename, chunk_id, page_start, page_end, text_excerpt }
  entities_mentioned: EntityReference[],  // { entity_id, name, type }
  suggested_followups: string[],
  no_results: boolean
}

// query.failed
{ query_id: string, error: string }
```

### Answer Text Parsing Rules

The backend LLM formats answers with:
1. **Citation references** as `[N]` — e.g., `"Deputy Mayor Horvat signed contract #2024-089 [1]"`
2. **Entity names** in `**bold**` — e.g., `"**Deputy Mayor Horvat** is connected to **GreenBuild LLC**"`

The AnswerPanel must parse these into React elements:
- `[N]` → `<sup><a href="#citation-N" onClick={onCitationClick}>N</a></sup>` styled with `--status-info` color
- `**Entity Name**` → `<a onClick={onEntityClick(name)}>Entity Name</a>` styled with entity-type color underline

**Entity type resolution:** Match the entity name against `entities_mentioned[]` from `query.complete` to determine type for color styling. During streaming (before `query.complete`), render bold text as generic styled links (use `--text-primary`), then re-render with correct entity type colors once `query.complete` arrives.

**Regex patterns for parsing:**
```typescript
// Citations: [1], [2], etc.
const CITATION_REGEX = /\[(\d+)\]/g;

// Bold entity names: **Name**
const ENTITY_REGEX = /\*\*([^*]+)\*\*/g;
```

### Layout Restructuring Details

**Current layout** (when entities exist):
```
┌────────────────────────────────────────┐
│ Header (back link, name, description)  │
├──────────────┬─────────────────────────┤
│ Left (40%)   │ Right (60%)             │
│ - Upload     │ - GraphCanvas           │
│ - Processing │   (with EntityDetail,   │
│ - EntityBar  │    Search, Filters)     │
│ - DocList    │                         │
└──────────────┴─────────────────────────┘
```

**New layout** (when entities exist):
```
┌────────────────────────────────────────┐
│ Header (back link, name, desc) [📄]    │  ← [📄] icon button to toggle document panel
├──────────────┬─────────────────────────┤
│ Left (40%)   │ Right (60%)             │
│ Q&A Panel:   │ GraphCanvas             │
│ - Answers    │   (with EntityDetail,   │
│ - Follow-ups │    Search, Filters,     │
│ - Input      │    entity highlighting) │
└──────────────┴─────────────────────────┘
```

**Document management access:** Add a small icon button (e.g., `FileText` from lucide) in the header that opens a slide-over or dialog containing the document management UI (upload, list, processing dashboard). This keeps documents accessible without cluttering the Q&A workspace.

### What Already Exists (DO NOT recreate)

| Component | Location | What It Does |
|-----------|----------|-------------|
| SplitView | `apps/web/src/components/layout/SplitView.tsx` | Draggable two-panel split layout, default 40/60. Reuse as-is. |
| GraphCanvas | `apps/web/src/components/graph/GraphCanvas.tsx` | Full interactive graph. Has `handleAskAboutEntity` TODO at line 327-329 to wire. |
| EntityDetailCard | `apps/web/src/components/graph/EntityDetailCard.tsx` | Shows entity details with "Ask about this entity" button (already calls `onAskAboutEntity`). |
| useSSE | `apps/web/src/hooks/useSSE.ts` | Document processing SSE hook. **Do NOT modify** — create new `useQueryStream` instead. |
| api client | `apps/web/src/lib/api-client.ts` | `openapi-fetch` client. Use for non-SSE API calls if needed. |
| API types | `apps/web/src/lib/api-types.generated.ts` | `QueryRequest`, `ConversationTurn` types already generated. |
| Button | `apps/web/src/components/ui/button.tsx` | shadcn/ui Button with variants (default, ghost, outline, etc.) and sizes (xs, sm, default, lg, icon). |
| Dialog | `apps/web/src/components/ui/dialog.tsx` | shadcn/ui Dialog (Radix). Use for document management slide-over if needed. |
| globals.css | `apps/web/src/globals.css` | All theme tokens: `--bg-secondary`, `--entity-person`, `--status-info`, etc. |
| Package deps | `package.json` | `@microsoft/fetch-event-source@2.0.1`, `@tanstack/react-query@5.90.21`, `lucide-react@0.577.0` — all installed. |
| Fonts | `globals.css` | `--font-serif: "Source Serif 4 Variable"` for Q&A prose, `--font-sans: "Inter Variable"` for UI. |

### Key Design Tokens for Q&A Panel

```css
/* Panel background */
--bg-secondary: #232019;       /* Q&A panel background per UX spec */

/* Text */
--text-primary: #e8e0d4;       /* Answer prose text */
--text-secondary: #a89f90;     /* Status messages, descriptions */
--text-muted: #7a7168;         /* Placeholder text */

/* Entity type colors (for entity links in answer) */
--entity-person: #6b9bd2;      /* Blue */
--entity-org: #c4a265;         /* Warm gold (UX spec says "green" but tokens use gold) */
--entity-location: #7dab8f;    /* Green */

/* Citations */
--status-info: #6b9bd2;        /* Citation link color */

/* States */
--status-error: #c47070;       /* Error messages */
--bg-hover: #38342b;           /* User message bubble, hover states */
--bg-elevated: #2d2a23;        /* Cards, elevated surfaces */

/* Typography */
font-family: var(--font-serif); /* Source Serif 4 for answer prose */
font-size: 15px;                /* --text-base per UX spec */
line-height: 1.8;              /* UX spec: editorial reading line height */
max-width: 65ch;               /* Prose container max-width per UX spec */
```

### Graph-QA Synchronization Pattern

1. **Answer → Graph highlighting:** When `query.complete` arrives with `entities_mentioned`, pass entity names to GraphCanvas. GraphCanvas should:
   - Find matching nodes by name (case-insensitive, same as entity search)
   - Add a `highlighted` CSS class that applies glow/pulse animation
   - Dim non-highlighted nodes (reduce opacity)
   - Clear highlights on new query start or user graph interaction

2. **Answer entity click → Graph navigation:** When user clicks entity name in answer text, call GraphCanvas's existing `handleNavigateToEntity` pattern:
   - Center graph on the entity node
   - Expand neighborhood if not loaded
   - Open EntityDetailCard

3. **Graph "Ask about" → Q&A input:** GraphCanvas already has `handleAskAboutEntity(entityName: string)` (line 327). Wire this to set QAPanel's `prefillQuestion` to `"What connections does {entityName} have?"`.

### Conversation History State Design

```typescript
interface ConversationEntry {
  id: string;           // UUID for React keys
  question: string;
  answer: string | null;       // null while streaming
  citations: Citation[];
  entitiesMentioned: EntityReference[];
  suggestedFollowups: string[];
  noResults: boolean;
  status: 'streaming' | 'complete' | 'error';
  error?: string;
}

// The hook maintains:
// 1. conversationEntries: ConversationEntry[] — full conversation
// 2. currentStreamingText: string — accumulated text for current streaming answer
// 3. queryStatus: 'idle' | 'translating' | 'searching' | 'streaming' | 'complete' | 'error'

// On submitQuery(question):
// - Create new ConversationEntry with question, answer=null, status='streaming'
// - Send POST with { question, conversation_history: previousTurns }
// - As query.streaming events arrive, update currentStreamingText
// - On query.complete, finalize the entry with answer, citations, etc.

// conversation_history for API:
// Map conversationEntries to ConversationTurn[]:
//   { role: "user", content: entry.question }
//   { role: "assistant", content: entry.answer }
```

### Testing Patterns (from existing frontend tests)

**Test setup pattern:**
```typescript
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
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
- Mock `@microsoft/fetch-event-source` — control `onopen`, `onmessage`, `onerror` callbacks
- Mock `useQueryStream` hook when testing components — provide controlled state
- Use `userEvent` for interaction testing (click, type, keyboard)
- Use `screen.getByText`, `screen.getByRole`, `screen.getByLabelText` for queries

**Test file locations:** Co-located with source (same directory).

### Performance Considerations

- **Streaming rendering:** Don't re-render the entire conversation on each chunk. Only update the current streaming entry. Use `React.memo` for completed conversation entries.
- **Answer parsing:** Parse citations and entity names only on complete answers, not on every streaming chunk. During streaming, render raw text. After `query.complete`, re-render with parsed elements.
- **Auto-scroll:** Use `scrollIntoView({ behavior: 'smooth' })` on a sentinel div at the bottom. Detect manual scroll-up to pause auto-scroll (compare `scrollTop + clientHeight` to `scrollHeight`).
- **Prose container:** Apply `max-width: 65ch` to answer text to maintain readability per UX spec.

### Project Structure Notes

**New files:**
- `apps/web/src/hooks/useQueryStream.ts` — Query SSE streaming hook
- `apps/web/src/hooks/useQueryStream.test.ts` — Hook tests
- `apps/web/src/components/qa/QueryInput.tsx` — Question input component
- `apps/web/src/components/qa/QueryInput.test.tsx` — Input tests
- `apps/web/src/components/qa/AnswerPanel.tsx` — Answer display with citations/entities
- `apps/web/src/components/qa/AnswerPanel.test.tsx` — Answer panel tests
- `apps/web/src/components/qa/SuggestedQuestions.tsx` — Follow-up questions
- `apps/web/src/components/qa/SuggestedQuestions.test.tsx` — Suggested questions tests
- `apps/web/src/components/qa/QAPanel.tsx` — Container component
- `apps/web/src/components/qa/types.ts` — Shared Q&A types (ConversationEntry, QueryStatus, Citation frontend type)

**Modified files:**
- `apps/web/src/routes/investigations/$id.tsx` — Layout restructuring: Q&A panel replaces document list as left panel
- `apps/web/src/components/graph/GraphCanvas.tsx` — Wire `handleAskAboutEntity` (remove TODO), add `highlightEntities` prop, add/clear highlight CSS classes on Cytoscape nodes
- `apps/web/src/routes/investigations/-$id.test.tsx` — Update tests for new layout

**No new dependencies required.** All libraries (`@microsoft/fetch-event-source`, `@tanstack/react-query`, `lucide-react`, shadcn/ui) are already installed.

### References

- [Source: _bmad-output/planning-artifacts/epics.md — Epic 5, Story 5.2 acceptance criteria and BDD scenarios]
- [Source: _bmad-output/planning-artifacts/prd.md — FR17: Natural language questions, FR18: Graph+vector search translation, FR19: GRAPH FIRST grounding, FR20: Source citations, FR21: Citation click-through, FR22: "No connection found"]
- [Source: _bmad-output/planning-artifacts/prd.md — NFR5: <30s answer, NFR7: streaming within 5s, NFR21: 100% fact traceability, NFR22: zero hallucinated facts]
- [Source: _bmad-output/planning-artifacts/architecture.md — SSE: @microsoft/fetch-event-source for POST+SSE, piped into TanStack Query cache]
- [Source: _bmad-output/planning-artifacts/architecture.md — Frontend file structure: src/components/qa/AnswerPanel.tsx, QueryInput.tsx, SuggestedQuestions.tsx]
- [Source: _bmad-output/planning-artifacts/architecture.md — SSE channel strategy: per-query channels (query:{query_id}) for answer streaming]
- [Source: _bmad-output/planning-artifacts/architecture.md — Error boundaries: Wrap Q&A panel and graph canvas independently]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — Answer Panel: Perplexity-style cited prose, Source Serif 4 at 15px/1.8, entity links with type colors, superscript citations]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — Layout: 40% Q&A / 60% Graph, prose container max-width 65ch]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — Suggested Questions List: 2-4 follow-ups, bold question + muted description, click to submit]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — Streaming state: progressive text, skeleton for follow-ups, blinking cursor]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — Accessibility: aria-live="polite" for streaming, aria-labels on citations and entity links]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — Q&A Panel background: --bg-secondary, Input: Source Serif 4, Citations: --status-info]
- [Source: apps/api/app/schemas/query.py — QueryRequest, QueryResponse, Citation, EntityReference, QuerySSEEvent backend schemas]
- [Source: apps/api/app/api/v1/query.py — POST /investigations/{id}/query/ endpoint with EventSourceResponse]
- [Source: apps/web/src/hooks/useSSE.ts — Existing SSE hook pattern (for reference, NOT reuse)]
- [Source: apps/web/src/components/graph/GraphCanvas.tsx:327 — handleAskAboutEntity TODO to wire]
- [Source: apps/web/src/components/graph/EntityDetailCard.tsx:273 — "Ask about this entity" button already connected]
- [Source: apps/web/src/routes/investigations/$id.tsx — Current investigation detail page layout to restructure]
- [Source: apps/web/src/components/layout/SplitView.tsx — Existing draggable split view to reuse]
- [Source: apps/web/src/globals.css — Theme tokens and font declarations]
- [Source: apps/web/src/lib/api-types.generated.ts — QueryRequest, ConversationTurn TypeScript types already generated]

### Previous Story Intelligence (Story 5.1 Learnings)

1. **SSE event format:** Events are published using `sse-starlette` `EventSourceResponse`. The event name is in the `event` field, data is JSON in the `data` field. The `fetchEventSource` `onmessage` callback receives `{ event: string, data: string }` — parse `data` with `JSON.parse()`.

2. **query.streaming events contain the full answer text as a single chunk** — after the code review fix in Story 5.1, the backend yields the full answer honestly (not fake 50-char chunks). The answer arrives as one `query.streaming` event followed by `query.complete`. However, the hook should still handle multiple streaming chunks for future extensibility.

3. **query.complete contains the complete payload** — `answer`, `citations[]`, `entities_mentioned[]`, `suggested_followups[]`, `no_results`. This is the authoritative data. Use this to finalize the conversation entry, not the accumulated streaming text.

4. **Cypher injection fix applied** — The backend now uses parameterized queries. No frontend concern, but good to know the backend is secure.

5. **GraphUnavailableError added** — The backend returns RFC 7807 `urn:osint:error:graph_unavailable` when Neo4j is down. The frontend should show a user-friendly message for this error type.

6. **Entity type names are PascalCase** — `Person`, `Organization`, `Location` in `entities_mentioned[].type`. Map these to CSS variables: `Person` → `--entity-person`, `Organization` → `--entity-org`, `Location` → `--entity-location`.

7. **OpenAPI types already generated** — `QueryRequest` and `ConversationTurn` types are in `api-types.generated.ts`. However, the SSE response types (Citation, EntityReference, QueryResponse) are NOT in the generated types because the endpoint returns `StreamingResponse` (not a typed JSON response). Define these types manually in `apps/web/src/components/qa/types.ts`.

8. **Commit message format:** `feat: Story 5.2 — answer streaming & Q&A panel`

### Git Intelligence

Recent commits (for pattern continuity):
- `bf2d2c6` — feat: Story 5.1 — graph-first natural language query pipeline
- `20200f5` — feat: Story 4.5 — entity search with graph highlighting with code review fixes
- `e4f2070` — feat: Story 4.4 — graph filtering by entity type & source document
- `a6260c1` — feat: Story 4.3 — node & edge interaction with entity detail card
- `d62f758` — feat: Story 4.2 — interactive graph canvas with Cytoscape.js

**Test counts:** Current suite: ~295 backend tests, ~160 frontend tests. This story should add ~20-25 new frontend tests (hook: 9, components: 14+, integration: 5). No backend tests in this story.

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

No blocking issues encountered.

### Completion Notes List

- Implemented `useQueryStream` hook with POST+SSE using `@microsoft/fetch-event-source`, full state machine (idle→translating→searching→streaming→complete|error), conversation history management, and abort cleanup
- Created `QueryInput` component with textarea auto-resize, Enter to submit, Shift+Enter for newline, disabled state during processing, prefill support
- Created `AnswerPanel` component with Perplexity-style cited prose: `[N]` citations rendered as clickable superscripts, `**Entity Name**` rendered as colored entity links matching entity type, streaming cursor, auto-scroll with manual scroll-up detection, error/no-results states
- Created `SuggestedQuestions` component with clickable follow-up cards, skeleton loading state, hidden when no results
- Created `QAPanel` container composing AnswerPanel + SuggestedQuestions + QueryInput with initial state starter questions
- Restructured investigation detail page: QAPanel replaces document list as left panel (40%) when entities exist; document management moved to a Dialog accessible via FileText icon button in header
- Wired graph-QA entity highlighting: `highlightEntities` prop on GraphCanvas, CSS class-based highlight/dim with center animation; clears on graph tap
- Wired "Ask about this entity" from GraphCanvas EntityDetailCard → QAPanel prefillQuestion
- Citation clicks dispatch callbacks (logged for now; Story 5.3 will implement Citation Modal)
- 38 new tests: 12 hook tests, 9 QueryInput tests, 8 AnswerPanel tests, 4 SuggestedQuestions tests, 5 integration tests
- All 198 frontend tests pass with 0 regressions

### Change Log

- 2026-03-14: Story 5.2 implemented — answer streaming & Q&A panel with full graph-QA synchronization
- 2026-03-14: Code review fixes applied:
  - CRITICAL: Added "Try again" retry button to AnswerPanel error state (AC 3, Task 3.11)
  - HIGH: Added useEffect cleanup in useQueryStream to abort SSE on component unmount
  - HIGH: Wired onQueryStart callback to clear graph entity highlights when new query starts (Task 7.4)
  - MEDIUM: Fixed citation aria-label to include filename and page per spec (Task 3.5)
  - MEDIUM: Refactored parseAnswerText to two-pass parsing (citations first, then entities) to handle nested edge cases
  - MEDIUM: Improved document dialog integration test to verify click interaction
  - MEDIUM: Fixed test count in completion notes (was 25, actually 38)

### File List

**New files:**
- `apps/web/src/components/qa/types.ts` — Shared Q&A types (QueryStatus, Citation, EntityReference, ConversationEntry)
- `apps/web/src/hooks/useQueryStream.ts` — POST+SSE query streaming hook
- `apps/web/src/hooks/useQueryStream.test.ts` — Hook tests (11 tests)
- `apps/web/src/components/qa/QueryInput.tsx` — Question input component
- `apps/web/src/components/qa/QueryInput.test.tsx` — Input tests (9 tests)
- `apps/web/src/components/qa/AnswerPanel.tsx` — Answer display with citations and entity links
- `apps/web/src/components/qa/AnswerPanel.test.tsx` — AnswerPanel tests (7 tests)
- `apps/web/src/components/qa/SuggestedQuestions.tsx` — Follow-up question cards
- `apps/web/src/components/qa/SuggestedQuestions.test.tsx` — SuggestedQuestions tests (4 tests)
- `apps/web/src/components/qa/QAPanel.tsx` — Container component

**Modified files:**
- `apps/web/src/routes/investigations/$id.tsx` — Layout restructured: QAPanel as left panel, document management in dialog
- `apps/web/src/components/graph/GraphCanvas.tsx` — Added `onAskAboutEntity`, `highlightEntities`, `onHighlightClear` props; wired entity highlighting; removed TODO
- `apps/web/src/routes/investigations/-$id.test.tsx` — Added 5 Q&A integration tests
