# Story 4.2: Interactive Graph Canvas with Cytoscape.js

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an investigator,
I want to see an interactive graph of entities and relationships when I open my investigation,
So that I can visually explore the connections the system found in my documents.

## Acceptance Criteria

1. **GIVEN** an investigation has processed entities, **WHEN** the investigator opens the investigation workspace, **THEN** the graph canvas renders using Cytoscape.js via a custom `useCytoscape` hook, **AND** the Graph-First Landing shows top hub entities (most connected nodes) with a clean force-directed layout, **AND** entity types are color-coded: Person (soft blue `#6b9bd2`), Organization (warm amber `#c4a265`), Location (muted green `#7dab8f`), **AND** node border thickness reflects confidence score, **AND** the graph renders up to 500 visible nodes in <2 seconds.

2. **GIVEN** the workspace uses the Answer-to-Graph Bridge layout, **WHEN** the investigator views the investigation, **THEN** the workspace splits into Q&A panel (left, 40%) and graph panel (right, 60%), **AND** the split divider is resizable with minimum 25% per panel, **AND** the graph canvas fills 100% of its panel at any size.

3. **GIVEN** the graph contains more entities than can fit in the viewport, **WHEN** the graph loads initially, **THEN** only hub nodes and their immediate connections are loaded (viewport-based loading), **AND** no artificial upper limit is imposed on graph size, **AND** additional nodes are fetched on demand as the user explores.

4. **GIVEN** `prefers-reduced-motion` is enabled, **WHEN** graph layout changes occur, **THEN** all animations are reduced to instant state changes.

## Tasks / Subtasks

- [x] **Task 1: Install Cytoscape.js dependencies** (AC: 1)
  - [x] 1.1: `cd apps/web && pnpm add cytoscape cytoscape-fcose`
  - [x] 1.2: `cd apps/web && pnpm add -D @types/cytoscape`
  - [x] 1.3: Verify Cytoscape.js v3.x and cytoscape-fcose v2.x installed
  - [x] 1.4: Register fcose layout extension: `import fcose from 'cytoscape-fcose'; cytoscape.use(fcose);` — must run once at module scope (not inside component)

- [x] **Task 2: Create `useCytoscape` hook** (AC: 1, 3, 4)
  - [x] 2.1: Create `apps/web/src/hooks/useCytoscape.ts`
  - [x] 2.2: Hook signature: `useCytoscape(containerRef: RefObject<HTMLDivElement | null>, options?: { reducedMotion?: boolean })` → returns `{ cy: Core | null, isReady: boolean }`
  - [x] 2.3: Instance lifecycle: create Cytoscape instance in `useEffect`, attach to `containerRef.current`, destroy on cleanup via `cy.destroy()`
  - [x] 2.4: `useRef<Core | null>` to hold instance (imperative — not state-driven re-renders)
  - [x] 2.5: `isReady` state set to true after `cy.ready()` callback fires
  - [x] 2.6: Detect `prefers-reduced-motion` via `window.matchMedia('(prefers-reduced-motion: reduce)')` — pass to layout config
  - [x] 2.7: Configure `userZoomingEnabled: true`, `userPanningEnabled: true`, `boxSelectionEnabled: false`, `minZoom: 0.1`, `maxZoom: 3`
  - [x] 2.8: Error handling: wrap Cytoscape initialization in try/catch, return `{ cy: null, isReady: false, error }` on failure — never crash the workspace

- [x] **Task 3: Create `cytoscape-styles.ts` style config** (AC: 1)
  - [x] 3.1: Create `apps/web/src/lib/cytoscape-styles.ts`
  - [x] 3.2: Node styles using CSS variable values (must read computed CSS vars at runtime or hardcode matching values):
    - Person: background `#6b9bd2`, shape `ellipse` (circle)
    - Organization: background `#c4a265`, shape `diamond`
    - Location: background `#7dab8f`, shape `triangle`
  - [x] 3.3: Node label: `data(name)`, font `Inter`, font-size 11px, color `#e8e0d4`, text wrap `ellipsis`, text-max-width `80px`
  - [x] 3.4: Node border: width mapped from `data(confidence_score)` → range `1px` (score 0) to `4px` (score 1.0), border-color same as background but 30% darker
  - [x] 3.5: Node size: base `40px` width/height, or mapped from `data(relationship_count)` for hub emphasis (range 35–60px)
  - [x] 3.6: Edge styles: line-color `#5c5548`, width `1.5px`, curve-style `bezier`, target-arrow-shape `triangle`, target-arrow-color `#5c5548`, opacity `0.6`
  - [x] 3.7: Edge label: `data(type)` displayed on hover only (via `:active` or event-based class toggle), font-size 10px
  - [x] 3.8: Selection/hover: `:selected` → border-color `#e8e0d4`, border-width `3px`; node `:active` → opacity `1`, scale `1.05`
  - [x] 3.9: Export as `cytoscapeStylesheet: cytoscape.Stylesheet[]`

- [x] **Task 4: Create `useGraphData` hook** (AC: 1, 3)
  - [x] 4.1: Create `apps/web/src/hooks/useGraphData.ts`
  - [x] 4.2: `useGraphData(investigationId: string)` — wraps TanStack Query for `GET /api/v1/investigations/{id}/graph/`
  - [x] 4.3: Query key: `["graph", investigationId]`
  - [x] 4.4: Use `api.GET("/api/v1/investigations/{investigation_id}/graph/", { params: { path: { investigation_id: investigationId }, query: { limit: 50 } } })` via openapi-fetch
  - [x] 4.5: Return `{ data: GraphResponse | undefined, isLoading, isError, error }`
  - [x] 4.6: `useExpandNeighbors(investigationId: string)` — returns a mutation-like function: `expandNeighbors(entityId: string)` that calls `GET /api/v1/investigations/{id}/graph/neighbors/{entity_id}` and merges results into the graph
  - [x] 4.7: On expand success: merge new nodes/edges into cached graph data (use `queryClient.setQueryData` to append without duplicates — deduplicate by node/edge `data.id`)

- [x] **Task 5: Create `GraphCanvas` component** (AC: 1, 2, 3, 4)
  - [x] 5.1: Create `apps/web/src/components/graph/GraphCanvas.tsx`
  - [x] 5.2: Props: `investigationId: string`
  - [x] 5.3: Render a full-size `<div ref={containerRef}>` — must have explicit height (use `h-full` with parent providing height via flex or grid)
  - [x] 5.4: Use `useCytoscape(containerRef)` for instance, `useGraphData(investigationId)` for data
  - [x] 5.5: On data change: `cy.json({ elements: [...data.nodes, ...data.edges] })` or `cy.add()` for incremental updates. Use `cy.elements().diff()` to avoid re-adding existing elements.
  - [x] 5.6: Run fcose layout after adding elements: `cy.layout({ name: 'fcose', animate: !reducedMotion, animationDuration: 400, quality: 'default', randomize: false, nodeSeparation: 75 }).run()`
  - [x] 5.7: Loading state: show skeleton/spinner while `isLoading`, centered in the panel
  - [x] 5.8: Empty state: "No entities found. Upload and process documents to populate the graph." centered message
  - [x] 5.9: Error state: "Failed to load graph data." with retry button

- [x] **Task 6: Create `GraphControls` component** (AC: 1)
  - [x] 6.1: Create `apps/web/src/components/graph/GraphControls.tsx`
  - [x] 6.2: Zoom controls: zoom in (`cy.zoom(cy.zoom() * 1.2)`), zoom out, fit (`cy.fit(undefined, 50)`)
  - [x] 6.3: Re-layout button: re-run fcose layout on current elements
  - [x] 6.4: Position: absolute bottom-right of graph panel, small floating toolbar with icon buttons
  - [x] 6.5: Use `lucide-react` icons: `ZoomIn`, `ZoomOut`, `Maximize2` (fit), `RefreshCw` (re-layout)

- [x] **Task 7: Create `SplitView` layout component** (AC: 2)
  - [x] 7.1: Create `apps/web/src/components/layout/SplitView.tsx`
  - [x] 7.2: Props: `left: ReactNode`, `right: ReactNode`, `defaultLeftPercent?: number` (default 40), `minPercent?: number` (default 25)
  - [x] 7.3: CSS grid with `grid-template-columns: ${leftPercent}% 4px 1fr` — middle column is the drag handle
  - [x] 7.4: Drag handle: 4px wide, `cursor-col-resize`, subtle visual indicator on hover (`bg-[var(--border-strong)]`)
  - [x] 7.5: Drag logic: `onPointerDown` on handle → track `pointermove` on `document` → calculate new leftPercent from clientX, clamp to [minPercent, 100-minPercent] → set state → `onPointerUp` removes listeners
  - [x] 7.6: Both panels must have `overflow: hidden` and children handle their own scrolling
  - [x] 7.7: Full height: parent must provide height context (use `flex-1` or explicit height)

- [x] **Task 8: Update investigation workspace route** (AC: 1, 2, 3)
  - [x] 8.1: Modify `apps/web/src/routes/investigations/$id.tsx`
  - [x] 8.2: When investigation has completed entities: render `SplitView` with left=Q&A placeholder panel (for now: document list + upload zone + processing dashboard), right=`GraphCanvas`
  - [x] 8.3: When no entities yet: keep current full-width layout (upload + processing + document list)
  - [x] 8.4: The graph panel parent must have a defined height — use `flex-1 min-h-0` in a `flex flex-col h-full` container
  - [x] 8.5: Import GraphCanvas and SplitView lazily if needed to avoid loading Cytoscape until needed

- [x] **Task 9: Write frontend tests** (AC: 1, 2, 3, 4)
  - [x] 9.1: `apps/web/src/hooks/useCytoscape.test.ts` — hook creates/destroys instance, handles missing container, respects reduced motion
  - [x] 9.2: `apps/web/src/hooks/useGraphData.test.ts` — fetches graph data, handles empty response, expand neighbors deduplicates
  - [x] 9.3: `apps/web/src/components/graph/GraphCanvas.test.tsx` — renders container div, shows loading state, shows empty state, shows error state
  - [x] 9.4: `apps/web/src/components/layout/SplitView.test.tsx` — renders left and right panels, respects default split percentage
  - [x] 9.5: Mock Cytoscape in tests: `vi.mock('cytoscape', () => ({ default: vi.fn(() => mockCyInstance) }))` where `mockCyInstance` has `add`, `layout`, `destroy`, `on`, `ready`, `fit`, `zoom`, `json`, `elements` stubs

## Dev Notes

### Architecture Context

This is the **second story in Epic 4** (Graph Visualization & Exploration). Story 4.1 created the backend graph API (`GET /graph/` and `GET /graph/neighbors/{entity_id}`). This story creates the frontend graph canvas that consumes those endpoints.

**Stories 4.3–4.5 will build on top of this story:**
- 4.3: Entity detail card on node click, edge click for relationship evidence, double-click to expand neighbors
- 4.4: Graph filtering by entity type and source document
- 4.5: Entity search with graph highlighting

**This story must establish the foundational graph infrastructure** that those stories extend. The `useCytoscape` hook, `GraphCanvas` component, and `useGraphData` hook are all extension points.

### What Already Exists (DO NOT recreate)

| Component | Location | What It Does |
|-----------|----------|-------------|
| Graph API (subgraph) | `app/api/v1/graph.py` | `GET /{investigation_id}/graph/` — paginated Cytoscape.js-format graph data |
| Graph API (neighbors) | `app/api/v1/graph.py` | `GET /{investigation_id}/graph/neighbors/{entity_id}` — neighbor expansion |
| Graph schemas | `app/schemas/graph.py` | `GraphNode`, `GraphEdge`, `GraphResponse` — Cytoscape.js format |
| GraphQueryService | `app/services/graph_query.py` | Neo4j hub-ordered subgraph + neighbor queries |
| TypeScript graph types | `src/lib/api-types.generated.ts` | `GraphResponse`, `GraphNode`, `GraphEdge` — already generated |
| openapi-fetch client | `src/lib/api-client.ts` | `api.GET(...)` pattern — use for graph data fetching |
| Entity colors CSS vars | `src/globals.css` | `--entity-person: #6b9bd2`, `--entity-org: #c4a265`, `--entity-location: #7dab8f` |
| Entity summary bar | `src/components/investigation/EntitySummaryBar.tsx` | Shows entity type counts with colored dots |
| useEntities hook | `src/hooks/useEntities.ts` | Entity list with type filter — reuse query key pattern |
| useSSE hook | `src/hooks/useSSE.ts` | SSE infrastructure — graph can listen for entity updates later |
| shadcn/ui components | `src/components/ui/` | `button.tsx`, `dialog.tsx`, `badge.tsx`, `card.tsx` etc. |
| Lucide icons | package.json | Already installed — use for graph controls |
| Investigation workspace | `src/routes/investigations/$id.tsx` | Current full-width layout — must be refactored to split view |

### Cytoscape.js Integration Pattern

**Architecture decision:** Custom `useCytoscape` hook — NOT `react-cytoscapejs` wrapper library. Direct imperative control over the Cytoscape API is necessary for viewport-based loading, answer-entity highlighting (Story 5.2), neighborhood expansion (Story 4.3), and synchronized panel updates.

**Package versions:**
- `cytoscape` — v3.33.1 (latest stable)
- `cytoscape-fcose` — v2.2.0 (fCoSE layout — fast compound spring embedder)
- `@types/cytoscape` — latest (TypeScript definitions)

**fcose layout** is the chosen force-directed algorithm. It combines spectral layout speed with force-directed aesthetics. It runs up to 2x faster than cose while producing similar quality layouts. Must register once at module level:

```typescript
import cytoscape from 'cytoscape';
import fcose from 'cytoscape-fcose';
cytoscape.use(fcose);
```

**Graph data format from API** (Cytoscape.js compatible — zero transformation):
```json
{
  "nodes": [{ "group": "nodes", "data": { "id": "uuid", "name": "Name", "type": "Person", "confidence_score": 0.92, "relationship_count": 7 } }],
  "edges": [{ "group": "edges", "data": { "id": "uuid1-WORKS_FOR-uuid2", "source": "uuid1", "target": "uuid2", "type": "WORKS_FOR", "confidence_score": 0.85 } }],
  "total_nodes": 150,
  "total_edges": 300
}
```

To add to Cytoscape: `cy.add([...response.nodes, ...response.edges])` — the `group` and `data` fields are exactly what Cytoscape expects.

### Node Visual Design (from UX Spec)

| Entity Type | Color | Shape | CSS Variable |
|-------------|-------|-------|-------------|
| Person | Soft blue `#6b9bd2` | Circle (ellipse) | `--entity-person` |
| Organization | Warm amber `#c4a265` | Diamond | `--entity-org` |
| Location | Muted green `#7dab8f` | Triangle | `--entity-location` |

**Node labels:** Inter font, 11px, `#e8e0d4` (text-primary). Truncate with ellipsis at 80px.

**Confidence → border thickness:** Linear mapping from `confidence_score` (0–1) to border-width (1–4px). Higher confidence = thicker border.

**Node size:** Base 40px. Scale by `relationship_count` for hub emphasis (range 35–60px). Hubs should be visually larger.

**Edge styling:** `#5c5548` (border-subtle), 1.5px width, bezier curves, directed arrows. Edge type labels on hover/interaction only (not default — too noisy).

### SplitView Layout Design

```
┌──────────────────────────────────────────────────────┐
│  Investigation Header (back link, title, description) │
├──────────────────┬───┬───────────────────────────────┤
│                  │ ║ │                                 │
│  Left Panel      │ ║ │   Right Panel (Graph)           │
│  (40%)           │ ║ │   (60%)                         │
│                  │ ║ │                                 │
│  Upload Zone     │ ║ │   GraphCanvas                   │
│  Processing      │ ║ │   (Cytoscape.js)               │
│  Entity Summary  │ ║ │                                 │
│  Document List   │ ║ │           GraphControls          │
│                  │ ║ │           (bottom-right)         │
├──────────────────┴───┴───────────────────────────────┤
│  Status Bar                                           │
└──────────────────────────────────────────────────────┘
```

**Resizable divider:** 4px drag handle between panels. Min 25% per panel. Default 40/60.

**Height:** The workspace must fill available viewport height. Use `flex flex-col h-[calc(100vh-<header+statusbar>)]` or flex-1 with `min-h-0` to allow the graph panel to fill remaining space. The Cytoscape container **requires** a non-zero height to render.

**Transition logic in `$id.tsx`:**
- If `hasCompleted` entities → show SplitView (left=document management, right=GraphCanvas)
- If no entities → keep current full-width layout (upload + processing + documents)

### TanStack Query Patterns (follow existing hooks)

```typescript
// useGraphData.ts — follow useEntities.ts pattern
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";

export function useGraphData(investigationId: string) {
  return useQuery({
    queryKey: ["graph", investigationId],
    queryFn: async () => {
      const { data, error } = await api.GET(
        "/api/v1/investigations/{investigation_id}/graph/",
        { params: { path: { investigation_id: investigationId }, query: { limit: 50 } } }
      );
      if (error) throw error;
      return data;
    },
    enabled: !!investigationId,
  });
}
```

**Neighbor expansion pattern:** Use `queryClient.setQueryData(["graph", investigationId], ...)` to merge new nodes/edges into the cached graph. Deduplicate by `data.id`.

### Testing Strategy

**Cytoscape mocking in Vitest:**
```typescript
// Mock cytoscape module
vi.mock('cytoscape', () => {
  const mockCy = {
    add: vi.fn(),
    remove: vi.fn(),
    layout: vi.fn(() => ({ run: vi.fn() })),
    destroy: vi.fn(),
    on: vi.fn(),
    ready: vi.fn((cb: () => void) => cb()),
    fit: vi.fn(),
    zoom: vi.fn(() => 1),
    json: vi.fn(),
    elements: vi.fn(() => ({ diff: vi.fn(() => ({ left: [], right: [], both: [] })) })),
    mount: vi.fn(),
  };
  return { default: vi.fn(() => mockCy) };
});
```

**Test files — co-located with source (frontend pattern):**
- `src/hooks/useCytoscape.test.ts`
- `src/hooks/useGraphData.test.ts`
- `src/components/graph/GraphCanvas.test.tsx`
- `src/components/layout/SplitView.test.tsx`

**Test counts to verify:** Backend: 251 tests (no changes). Frontend: 85 → should grow to ~95+ with new graph tests.

### Project Structure Notes

**New files:**
- `apps/web/src/hooks/useCytoscape.ts` — Cytoscape.js instance lifecycle hook
- `apps/web/src/hooks/useGraphData.ts` — Graph data fetching + neighbor expansion hook
- `apps/web/src/lib/cytoscape-styles.ts` — Cytoscape stylesheet config
- `apps/web/src/components/graph/GraphCanvas.tsx` — Main graph canvas component
- `apps/web/src/components/graph/GraphCanvas.test.tsx` — Canvas tests
- `apps/web/src/components/graph/GraphControls.tsx` — Zoom/layout floating toolbar
- `apps/web/src/components/layout/SplitView.tsx` — Resizable split panel layout
- `apps/web/src/components/layout/SplitView.test.tsx` — Split view tests
- `apps/web/src/hooks/useCytoscape.test.ts` — Hook tests
- `apps/web/src/hooks/useGraphData.test.ts` — Data hook tests

**Modified files:**
- `apps/web/src/routes/investigations/$id.tsx` — Refactored to use SplitView when entities exist
- `apps/web/package.json` — New dependencies: cytoscape, cytoscape-fcose, @types/cytoscape

**No backend changes.** This is a frontend-only story.

**No new shadcn/ui components needed.** Use existing `button.tsx` for GraphControls.

### References

- [Source: _bmad-output/planning-artifacts/epics.md — Epic 4, Story 4.2: Interactive Graph Canvas with Cytoscape.js acceptance criteria]
- [Source: _bmad-output/planning-artifacts/architecture.md — Frontend Architecture: Custom useCytoscape hook, no community wrapper library]
- [Source: _bmad-output/planning-artifacts/architecture.md — File structure: src/components/graph/GraphCanvas.tsx, src/hooks/useCytoscape.ts, src/lib/cytoscape-styles.ts]
- [Source: _bmad-output/planning-artifacts/architecture.md — Error handling: Cytoscape errors caught in useCytoscape hook, fallback to empty graph]
- [Source: _bmad-output/planning-artifacts/architecture.md — Loading states: Cytoscape shows existing graph while loading neighbors, new nodes animate in]
- [Source: _bmad-output/planning-artifacts/architecture.md — TanStack Query for all server state, no useState for API data]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — Direction B: Prose-Forward 40/60 split, resizable divider, min 25% per panel]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — Entity colors: Person=#6b9bd2, Org=#c4a265, Location=#7dab8f; shapes: circle/diamond/triangle]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — Node border thickness = confidence; Graph-First Landing with hub entities]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — Warm dark theme: bg-primary=#1a1816, text-primary=#e8e0d4, border-subtle=#5c5548]
- [Source: _bmad-output/planning-artifacts/prd.md — NFR9: Graph render up to 500 nodes in <2s; NFR10: Node expansion <1s]
- [Source: _bmad-output/implementation-artifacts/4-1-graph-api-subgraph-queries.md — Cytoscape.js response format, edge ID strategy, API patterns]
- [Source: apps/web/src/globals.css — CSS custom properties for entity colors and theme tokens]
- [Source: apps/web/src/lib/api-client.ts — openapi-fetch configured instance for type-safe API calls]
- [Source: apps/web/src/hooks/useEntities.ts — TanStack Query hook pattern to follow]

### Previous Story Intelligence (Story 4.1 Learnings)

1. **Cytoscape.js response format already established** — API returns `{ group: "nodes"/"edges", data: {...} }` format. Frontend can pass directly to `cy.add()` — zero transformation.

2. **Edge ID strategy is composite** — `{source_id}-{type}-{target_id}`. Deterministic and unique. Use for deduplication when merging neighbor expansions.

3. **Node type field is PascalCase** — `Person`, `Organization`, `Location` as stored in Neo4j. Map to Cytoscape styles using these exact strings.

4. **Hub nodes ordered by relationship_count DESC** — Initial subgraph shows most-connected entities first. The `relationship_count` field can drive node sizing.

5. **Empty graph returns empty arrays (not error)** — Handle empty `nodes`/`edges` arrays as a valid empty state, not an error.

6. **22 backend graph tests exist** — No backend changes in this story, but run full suite to verify no regressions.

7. **OpenAPI types already include graph endpoints** — `api-types.generated.ts` has `GraphResponse`, `GraphNode`, `GraphEdge`. Do NOT regenerate — use as-is.

8. **Entity colors in epics file are WRONG** — Epics say "Person (amber), Org (blue)" but actual CSS vars (and UX spec) say Person=blue (#6b9bd2), Org=amber (#c4a265). Follow the CSS vars and UX spec.

### Git Intelligence

Recent commits:
- `9c599c0` — feat: Story 4.1 — graph API subgraph queries (JUST COMMITTED)
- `3ad8318` — feat: Story 3.5 — document-level & entity-level confidence display
- `ba02706` — fix: make Qdrant/Neo4j clients fork-safe for Celery prefork workers

**Patterns to continue:**
- Frontend tests co-located with source files
- TanStack Query hooks in `src/hooks/`
- Feature-grouped components in `src/components/{feature}/`
- openapi-fetch for type-safe API calls
- CSS custom properties for theming
- Commit message: `feat: Story 4.2 — interactive graph canvas with Cytoscape.js`

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

- Fixed `window.matchMedia` not available in jsdom test environment — added `typeof window.matchMedia === "function"` guard in useCytoscape hook
- Fixed TypeScript: `cytoscape-fcose` has no type declarations — added ambient module declaration in `vite-env.d.ts`
- Fixed TypeScript: `cytoscape.Stylesheet` type doesn't exist in v3.33.1 — used `StylesheetCSS | StylesheetStyle` union instead

### Completion Notes List

- **Task 1:** Installed cytoscape 3.33.1, cytoscape-fcose 2.2.0, @types/cytoscape 3.31.0. fcose registered at module scope in useCytoscape.ts.
- **Task 2:** Created `useCytoscape` hook with full lifecycle management, error handling, reduced motion detection, and configurable zoom/pan settings. Returns `{ cy, isReady, error, reducedMotion }`.
- **Task 3:** Created `cytoscape-styles.ts` with color-coded entity types (Person=blue/ellipse, Organization=amber/diamond, Location=green/triangle), confidence→border-width mapping, relationship_count→node-size mapping, edge styles with hover labels via class toggle, and selection styles.
- **Task 4:** Created `useGraphData` hook wrapping TanStack Query for graph API, and `useExpandNeighbors` for neighbor expansion with deduplication via `queryClient.setQueryData`.
- **Task 5:** Created `GraphCanvas` component with loading/empty/error states, incremental element syncing with diff-based deduplication, fcose layout, and edge hover label toggle.
- **Task 6:** Created `GraphControls` floating toolbar with zoom in/out, fit-to-view, and re-layout buttons using lucide-react icons and existing shadcn Button component.
- **Task 7:** Created `SplitView` layout component with CSS grid, 4px draggable handle via pointer events, configurable default split (40/60) and minimum (25%) constraints.
- **Task 8:** Refactored investigation workspace route to show SplitView when entities exist (left=document management, right=GraphCanvas), keeping full-width layout when no entities. GraphCanvas loaded lazily via `React.lazy`.
- **Task 9:** Wrote 19 new tests across 4 test files: useCytoscape (6 tests), useGraphData (5 tests), GraphCanvas (4 tests), SplitView (4 tests). All mock Cytoscape appropriately.

### Change Log

- 2026-03-13: Implemented Story 4.2 — Interactive Graph Canvas with Cytoscape.js. Added graph visualization infrastructure: useCytoscape hook, useGraphData hook, GraphCanvas component, GraphControls toolbar, SplitView layout, cytoscape-styles config. Refactored investigation workspace to split view when entities exist.
- 2026-03-13: Code review fixes — (H1) Fixed fcose layout re-running on every TanStack Query refetch even when no new elements were added; layout now only runs when new elements are actually added to the graph. (M1) Extracted duplicate fcose layout config into `buildFcoseOptions` helper. (M2) Added width/height increase on `:active` node style to simulate scale(1.05) per Task 3.8. (M3) Fixed lockfile path in File List from `apps/web/pnpm-lock.yaml` to `pnpm-lock.yaml` (monorepo root). (H2-noted) AC3 on-demand expansion: `useExpandNeighbors` hook is implemented and tested but not wired to UI interaction — intentionally deferred to Story 4.3 (double-click to expand neighbors).

### File List

**New files:**
- `apps/web/src/hooks/useCytoscape.ts`
- `apps/web/src/hooks/useCytoscape.test.ts`
- `apps/web/src/hooks/useGraphData.ts`
- `apps/web/src/hooks/useGraphData.test.ts`
- `apps/web/src/lib/cytoscape-styles.ts`
- `apps/web/src/components/graph/GraphCanvas.tsx`
- `apps/web/src/components/graph/GraphCanvas.test.tsx`
- `apps/web/src/components/graph/GraphControls.tsx`
- `apps/web/src/components/layout/SplitView.tsx`
- `apps/web/src/components/layout/SplitView.test.tsx`

**Modified files:**
- `apps/web/src/routes/investigations/$id.tsx` — Refactored to use SplitView when entities exist
- `apps/web/src/vite-env.d.ts` — Added cytoscape-fcose ambient module declaration
- `apps/web/package.json` — Added cytoscape, cytoscape-fcose, @types/cytoscape
- `pnpm-lock.yaml` — Updated lockfile (monorepo root)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — Story status updated
