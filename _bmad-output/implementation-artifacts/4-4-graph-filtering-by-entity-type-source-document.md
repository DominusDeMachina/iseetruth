# Story 4.4: Graph Filtering by Entity Type & Source Document

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an investigator,
I want to filter the graph to show only specific entity types or entities from specific documents,
So that I can focus on the connections most relevant to my current line of inquiry.

## Acceptance Criteria

1. **GIVEN** the graph displays entities of multiple types, **WHEN** the investigator toggles entity type filters (people, organizations, locations), **THEN** non-matching nodes and their edges are hidden with a smooth opacity + scale animation (200ms), **AND** the graph layout adjusts to the remaining visible nodes, **AND** filter state persists within the session.

2. **GIVEN** the investigation has multiple source documents, **WHEN** the investigator selects a document filter, **THEN** only entities and relationships sourced from the selected document(s) are shown, **AND** entities from other documents are hidden.

3. **GIVEN** multiple filters are active (type + document), **WHEN** the investigator views the graph, **THEN** both filters apply simultaneously (AND logic), **AND** clearing all filters restores the full graph view.

## Tasks / Subtasks

- [x] **Task 1: Add entity type and document filter params to backend graph API** (AC: 1, 2)
  - [x] 1.1: Modify `apps/api/app/api/v1/graph.py` — add `entity_types: str | None = Query(None)` and `document_id: str | None = Query(None)` to `get_subgraph()` endpoint
  - [x] 1.2: Modify `apps/api/app/services/graph_query.py` — update `get_subgraph()` signature to accept `entity_types: list[str] | None` and `document_id: str | None`
  - [x] 1.3: Modify `_fetch_hub_nodes()` — when `entity_types` is provided, dynamically build Cypher label filter (e.g., `(e:Person|Organization)`) instead of `(e:Person|Organization|Location)`; when `document_id` is provided, add `MATCH (e)-[:MENTIONED_IN]->(d:Document {id: $document_id})` join
  - [x] 1.4: Modify `_fetch_edges_between()` — no changes needed (already filters to given `node_ids`)
  - [x] 1.5: Modify `_fetch_total_counts()` — apply same filters so `total_nodes`/`total_edges` reflect filtered counts
  - [x] 1.6: Parse `entity_types` query param: comma-separated string → list, validate each against `ALLOWED_ENTITY_TYPES = {"person", "organization", "location"}`, return 422 for invalid types
  - [x] 1.7: Validate `document_id` is a valid UUID format if provided
  - [x] 1.8: Regenerate OpenAPI spec: `cd apps/api && uv run python -c "from app.main import app; import json; print(json.dumps(app.openapi()))" > ../web/src/lib/openapi.json` then `cd apps/web && pnpm run generate-api-types`

- [x] **Task 2: Write backend tests for graph filtering** (AC: 1, 2, 3)
  - [x] 2.1: Create/extend `apps/api/tests/api/test_graph.py` — test `GET /graph/?entity_types=person` returns only Person nodes
  - [x] 2.2: Test `GET /graph/?entity_types=person,organization` returns Person+Organization nodes, excludes Location
  - [x] 2.3: Test `GET /graph/?document_id=<uuid>` returns only entities MENTIONED_IN that document
  - [x] 2.4: Test `GET /graph/?entity_types=person&document_id=<uuid>` — combined filter (AND logic)
  - [x] 2.5: Test `GET /graph/` with no filter params — unchanged behavior (all types, all documents)
  - [x] 2.6: Test `GET /graph/?entity_types=invalid` returns 422
  - [x] 2.7: Test total_nodes/total_edges reflect filtered counts

- [x] **Task 3: Update `useGraphData` hook with filter params** (AC: 1, 2, 3)
  - [x] 3.1: Modify `apps/web/src/hooks/useGraphData.ts` — change `useGraphData(investigationId: string)` to `useGraphData(investigationId: string, filters?: GraphFilters)` where `GraphFilters = { entityTypes?: string[]; documentId?: string }`
  - [x] 3.2: Include filters in query key: `["graph", investigationId, filters?.entityTypes, filters?.documentId]` — TanStack Query auto-refetches when filters change
  - [x] 3.3: Pass filter params to API: `query: { limit: 50, ...(filters?.entityTypes?.length ? { entity_types: filters.entityTypes.join(",") } : {}), ...(filters?.documentId ? { document_id: filters.documentId } : {}) }`
  - [x] 3.4: Update `useExpandNeighbors` — keep using the unfiltered query key `["graph", investigationId]` for cache merge? **No** — the expand merges into whatever the current graph cache is. Pass the same `filters` to `useExpandNeighbors` so `setQueryData` targets the correct cache key: `["graph", investigationId, filters?.entityTypes, filters?.documentId]`. The neighbor API itself is NOT filtered (we always fetch full neighborhood), but the cache merge key must match.
  - [x] 3.5: Export `GraphFilters` type for consumer components

- [x] **Task 4: Create `GraphFilterPanel` component** (AC: 1, 2, 3)
  - [x] 4.1: Create `apps/web/src/components/graph/GraphFilterPanel.tsx`
  - [x] 4.2: Props: `entityTypes: string[]`, `onEntityTypesChange: (types: string[]) => void`, `documentId: string | undefined`, `onDocumentIdChange: (id: string | undefined) => void`, `documents: DocumentResponse[]`, `isCollapsed: boolean`, `onToggleCollapse: () => void`
  - [x] 4.3: **Entity type toggle chips**: Three buttons for Person, Organization, Location. Each shows colored dot (using `ENTITY_COLORS` from `entity-constants.ts`) + label. Active = filled background with entity color at 20% opacity + colored border. Inactive = outline only, muted text. All active by default (empty `entityTypes` array means "show all"). Clicking toggles that type in/out of the array. Clicking the last active type does nothing (at least one type must remain — OR re-enables all types).
  - [x] 4.4: **Document filter dropdown**: Native `<select>` element (no shadcn/ui Select installed) or custom dropdown using Button + absolute-positioned list. Options: "All documents" (value="") + each document from `documents` prop with `filename`. Selecting a document sets `documentId`; selecting "All documents" clears it.
  - [x] 4.5: **Active filter indicator**: When any filter is non-default, show a small badge with count of active filters (e.g., "2 filters active") and a "Clear all" button (lucide-react `X` icon)
  - [x] 4.6: **Collapsed state**: Single row showing active filter summary text (e.g., "Person, Org · contract.pdf") + expand chevron (lucide-react `ChevronDown`/`ChevronUp`). Expand chevron toggles panel open/closed
  - [x] 4.7: **Expanded state**: Full panel with entity type chips row + document dropdown row + clear button
  - [x] 4.8: **Positioning**: Absolute positioned at top-left of graph container (`top-3 left-3`), matching GraphControls elevated style: `bg-[var(--bg-elevated)]`, `border border-[var(--border-subtle)]`, `rounded-lg`, `shadow-lg`, `p-2`
  - [x] 4.9: **Accessibility**: `role="toolbar"`, `aria-label="Graph filters"`. Each entity type chip: `role="checkbox"`, `aria-checked`. Document dropdown: standard `<select>` or `role="listbox"`. Clear button: `aria-label="Clear all filters"`

- [x] **Task 5: Wire filters into GraphCanvas** (AC: 1, 2, 3)
  - [x] 5.1: Modify `apps/web/src/components/graph/GraphCanvas.tsx`
  - [x] 5.2: Add filter state: `const [entityTypes, setEntityTypes] = useState<string[]>([])` (empty = all types shown), `const [documentId, setDocumentId] = useState<string | undefined>()`
  - [x] 5.3: Add collapsed state: `const [filtersCollapsed, setFiltersCollapsed] = useState(true)` — collapsed by default
  - [x] 5.4: Pass filters to `useGraphData`: `useGraphData(investigationId, { entityTypes, documentId })`
  - [x] 5.5: Pass filters to `useExpandNeighbors`: update hook call to use filtered cache key
  - [x] 5.6: Accept `documents` prop from parent: `GraphCanvasProps` gets `documents?: DocumentResponse[]` — passed from investigation workspace where `useDocuments` already runs
  - [x] 5.7: Render `<GraphFilterPanel>` inside the graph container div, above/alongside GraphControls
  - [x] 5.8: **Filter transition animation**: When filters change and new graph data arrives, add new Cytoscape elements and remove old ones. Use batch operation: `cy.startBatch()` → remove elements not in new data → add new elements → `cy.endBatch()`. Then run fcose layout with `animate: !reducedMotion, animationDuration: 200` for smooth transition. This replaces element-level opacity animation with a data-driven approach (API returns only filtered data).
  - [x] 5.9: **Close detail card on filter change**: If `selectedNodeId` refers to a node that was filtered out, clear selection (`setSelectedNodeId(null)`)

- [x] **Task 6: Pass documents to GraphCanvas from investigation workspace** (AC: 2)
  - [x] 6.1: Modify `apps/web/src/routes/investigations/$id.tsx`
  - [x] 6.2: Pass `documents={documentsData?.items}` prop to `<GraphCanvas>`
  - [x] 6.3: Only pass completed documents (status === "completed") — documents still processing have no entities yet

- [x] **Task 7: Write frontend tests** (AC: 1, 2, 3)
  - [x] 7.1: `apps/web/src/hooks/useGraphData.test.ts` — extend: test that filters are included in query key, test that API call includes entity_types and document_id params when provided, test that omitting filters sends no filter params
  - [x] 7.2: `apps/web/src/components/graph/GraphFilterPanel.test.tsx` — renders three entity type chips with correct colors, toggling a chip calls `onEntityTypesChange`, document dropdown shows document list, selecting a document calls `onDocumentIdChange`, clear button resets all filters, collapsed mode shows summary, expand/collapse toggle works
  - [x] 7.3: `apps/web/src/components/graph/GraphCanvas.test.tsx` — extend: verify GraphFilterPanel is rendered, verify filter state changes trigger useGraphData with new params, verify detail card clears when filtered node disappears

## Dev Notes

### Architecture Context

This is the **fourth story in Epic 4** (Graph Visualization & Exploration). Stories 4.1–4.3 created the backend graph API, frontend graph canvas with Cytoscape.js, and node/edge interaction with detail cards. This story adds **filtering** — the investigator can narrow the graph to specific entity types and/or specific source documents.

**Story 4.5 will build on this:** Entity search with graph highlighting (uses the filtered graph canvas for centering/highlighting results).

### Filtering Strategy: Server-Side (API-Driven)

**Decision:** Filters are applied server-side. The graph API receives filter params and returns only matching nodes/edges. This is preferred over client-side filtering because:
1. The graph API uses pagination (`limit=50` hub nodes) — client-side filtering would only filter the currently loaded subset, missing entities that aren't loaded yet
2. Neo4j can efficiently filter by label and traverse MENTIONED_IN relationships
3. `total_nodes`/`total_edges` in the response accurately reflect filtered counts
4. Consistent with the existing `useEntities` hook pattern (server-side type filter)

**Implication:** When filters change, TanStack Query refetches from the API (new cache key). The Cytoscape instance receives a new set of elements. Transition animation happens during element sync.

### What Already Exists (DO NOT recreate)

| Component | Location | What It Does |
|-----------|----------|-------------|
| Graph API (subgraph) | `apps/api/app/api/v1/graph.py` | `GET /{investigation_id}/graph/` — paginated hub-ordered graph (currently no filters) |
| Graph API (neighbors) | `apps/api/app/api/v1/graph.py` | `GET /{investigation_id}/graph/neighbors/{entity_id}` — neighbor expansion |
| GraphQueryService | `apps/api/app/services/graph_query.py` | `_fetch_hub_nodes()`, `_fetch_edges_between()`, `_fetch_total_counts()` — Neo4j queries to extend |
| Entity type validation | `apps/api/app/api/v1/entities.py` | `ALLOWED_ENTITY_TYPES = {"person", "organization", "location"}` — reuse same constant or import |
| MENTIONED_IN relationship | `apps/api/app/services/extraction.py` | Entity→Document edges in Neo4j with chunk_id, page_start, page_end |
| `useGraphData` hook | `apps/web/src/hooks/useGraphData.ts` | Graph data fetching — extend with filter params |
| `useExpandNeighbors` | `apps/web/src/hooks/useGraphData.ts` | Neighbor expansion with cache merge — update cache key to include filters |
| `GraphCanvas` component | `apps/web/src/components/graph/GraphCanvas.tsx` | Graph rendering, click handlers, detail cards — extend with filter state + panel |
| `GraphControls` component | `apps/web/src/components/graph/GraphControls.tsx` | Zoom, fit, relayout floating toolbar (bottom-right) |
| `useDocuments` hook | `apps/web/src/hooks/useDocuments.ts` | `useDocuments(investigationId)` → `DocumentListResponse` with `items: DocumentResponse[]` — use for document dropdown population |
| `DocumentResponse` type | `apps/web/src/hooks/useDocuments.ts` | Has `id`, `filename`, `status` fields — filter to `status === "completed"` for dropdown |
| `ENTITY_COLORS` | `apps/web/src/lib/entity-constants.ts` | `{ Person: "#6b9bd2", Organization: "#c4a265", Location: "#7dab8f" }` — use for chip colors |
| Entity colors CSS vars | `apps/web/src/globals.css` | `--entity-person`, `--entity-org`, `--entity-location` |
| `useCytoscape` hook | `apps/web/src/hooks/useCytoscape.ts` | Cytoscape lifecycle, `reducedMotion` flag |
| `buildFcoseOptions` | `apps/web/src/lib/cytoscape-styles.ts` | fcose layout config — use for relayout after filter change |
| shadcn/ui Button | `apps/web/src/components/ui/button.tsx` | Button with variants and `icon-xs` size |
| shadcn/ui Badge | `apps/web/src/components/ui/badge.tsx` | Badge for filter count |
| Lucide icons | package.json | `Filter`, `X`, `ChevronDown`, `ChevronUp`, `FileText` etc. |
| `useEntities` hook | `apps/web/src/hooks/useEntities.ts` | **Reference pattern** — already has `typeFilter` param, includes filter in queryKey |
| Investigation workspace | `apps/web/src/routes/investigations/$id.tsx` | SplitView with `useDocuments(id)` already called — pass documents to GraphCanvas |

### Backend Implementation Details

**Current `_fetch_hub_nodes` Cypher (to modify):**
```cypher
MATCH (e:Person|Organization|Location {investigation_id: $investigation_id})
OPTIONAL MATCH (e)-[r:WORKS_FOR|KNOWS|LOCATED_AT]-({investigation_id: $investigation_id})
WITH e, labels(e)[0] AS type, COUNT(r) AS relationship_count
ORDER BY relationship_count DESC
SKIP $offset LIMIT $limit
RETURN e.id AS id, e.name AS name, type, e.confidence_score AS confidence_score, relationship_count
```

**With entity_types filter** (e.g., `entity_types=["person", "organization"]`):
- Build label expression dynamically: `Person|Organization` from validated types
- Replace `Person|Organization|Location` with dynamic label string
- **Python pattern:** Use string formatting for label expression since Neo4j doesn't support parameterized labels: `f"MATCH (e:{label_expr} {{investigation_id: $investigation_id}})"`

**With document_id filter:**
```cypher
MATCH (e:Person|Organization|Location {investigation_id: $investigation_id})
  -[:MENTIONED_IN]->(d:Document {id: $document_id, investigation_id: $investigation_id})
WITH DISTINCT e
OPTIONAL MATCH (e)-[r:WORKS_FOR|KNOWS|LOCATED_AT]-({investigation_id: $investigation_id})
WITH e, labels(e)[0] AS type, COUNT(r) AS relationship_count
ORDER BY relationship_count DESC
SKIP $offset LIMIT $limit
RETURN e.id AS id, e.name AS name, type, e.confidence_score AS confidence_score, relationship_count
```

**Combined filter (entity_types + document_id):**
```cypher
MATCH (e:Person|Organization {investigation_id: $investigation_id})
  -[:MENTIONED_IN]->(d:Document {id: $document_id, investigation_id: $investigation_id})
WITH DISTINCT e
OPTIONAL MATCH (e)-[r:WORKS_FOR|KNOWS|LOCATED_AT]-({investigation_id: $investigation_id})
WITH e, labels(e)[0] AS type, COUNT(r) AS relationship_count
ORDER BY relationship_count DESC
SKIP $offset LIMIT $limit
RETURN e.id AS id, e.name AS name, type, e.confidence_score AS confidence_score, relationship_count
```

**`_fetch_total_counts` must also apply the same filters** so the response `total_nodes`/`total_edges` match the filtered dataset.

**`_fetch_edges_between` needs no changes** — it already takes the `node_ids` list from `_fetch_hub_nodes` and only returns edges between them.

### Frontend Filter Panel UX (from UX Spec)

**Entity type chips layout:**
```
┌────────────────────────────────────────┐
│ ▾ Filters                              │
│  [● People] [◆ Orgs] [▲ Locations]    │
│  [📄 All documents ▼]                  │
└────────────────────────────────────────┘
```

**Chip states:**
- **Active (default)**: Colored background at 20% opacity, colored border, colored dot, regular text. E.g., People chip: `bg-[#6b9bd2]/20 border-[#6b9bd2] text-[var(--text-primary)]`
- **Inactive**: `bg-transparent border-[var(--border-subtle)] text-[var(--text-muted)]`, muted dot

**Filter behavior (from UX spec):**
- Filters apply **instantly** — no "Apply" button. Graph animates on filter change.
- Filters are **additive** — entity type + document combine with AND logic.
- **Default state**: All entity types active, "All documents" selected.
- Collapsed toolbar shows badge with count of active filters when non-default.

**Animation (from UX spec):**
- Filter toggle (graph nodes show/hide): opacity + scale, 200ms, ease-out
- Respect `prefers-reduced-motion` — instant state changes when enabled
- Since we use server-side filtering, the animation happens via Cytoscape element add/remove during data sync, not CSS transitions on individual nodes

**No shadcn/ui Select or ToggleGroup installed.** Build chips with Button variants and native `<select>` for document dropdown, or create a custom dropdown with Button + absolute-positioned menu. Keep it simple — avoid adding new dependencies for a dropdown.

### Cytoscape Element Sync on Filter Change

When TanStack Query returns new filtered data, the existing `useEffect` in GraphCanvas syncs elements into Cytoscape. The current sync logic adds new elements and updates existing ones but does **not remove** elements that are no longer in the data. **This must be updated for filtering:**

1. On data change: diff current Cytoscape elements against new data
2. **Remove** Cytoscape elements whose IDs are not in the new dataset
3. **Add** elements that are new
4. Run `cy.layout(buildFcoseOptions(reducedMotion)).run()` to relayout with animation
5. Wrap in `cy.startBatch()` / `cy.endBatch()` for performance

**Important:** The fcose layout animation duration should be 200ms for filter transitions (faster than the 400ms used for neighbor expansion) per UX spec.

### Expand Neighbors + Active Filters

When the user double-clicks to expand a node's neighborhood:
- The `useExpandNeighbors` API call does **not** pass filters — we always fetch the full neighborhood from the API (the user explicitly asked to see this node's connections)
- However, the cache merge key **must include filters** so `setQueryData` updates the correct cache entry: `["graph", investigationId, filters?.entityTypes, filters?.documentId]`
- Expanded neighbor nodes appear in the graph even if their type is currently filtered out — this is intentional (explicit user action overrides passive filters)
- **Alternative approach:** Filter expanded neighbors too. Decision: Show all neighbors (matches UX principle of user-driven exploration).

### Project Structure Notes

**New files:**
- `apps/web/src/components/graph/GraphFilterPanel.tsx` — Filter control component
- `apps/web/src/components/graph/GraphFilterPanel.test.tsx` — Filter panel tests

**Modified files:**
- `apps/api/app/api/v1/graph.py` — Add filter query params
- `apps/api/app/services/graph_query.py` — Extend Neo4j queries with filter logic
- `apps/web/src/hooks/useGraphData.ts` — Add filter params to hook and query key
- `apps/web/src/hooks/useGraphData.test.ts` — Extend with filter tests
- `apps/web/src/components/graph/GraphCanvas.tsx` — Add filter state, render GraphFilterPanel, update element sync
- `apps/web/src/components/graph/GraphCanvas.test.tsx` — Extend with filter integration tests
- `apps/web/src/routes/investigations/$id.tsx` — Pass documents prop to GraphCanvas
- `apps/web/src/lib/api-types.generated.ts` — Auto-regenerated after OpenAPI update

**No new dependencies.** All required packages are already installed.

### Testing Strategy

**Backend tests:** Mock Neo4j driver, verify Cypher queries include correct label expressions and MENTIONED_IN joins based on filter params. Test the API endpoint returns 422 for invalid entity types. Test empty results when filter matches nothing.

**Frontend tests:**
- Co-located test files with source (project convention)
- Mock `useGraphData` in GraphCanvas tests to verify filter params passed
- Mock `useDocuments` data for GraphFilterPanel document dropdown
- Use `@testing-library/react` for component tests
- TanStack Query wrapper for hook tests

**Test counts:** Current suite: 126 tests. This story should add ~15-20 new tests: backend API tests (5-7), GraphFilterPanel (5-6), useGraphData filter extensions (3-4), GraphCanvas filter integration (2-3).

### References

- [Source: _bmad-output/planning-artifacts/epics.md — Epic 4, Story 4.4 acceptance criteria and BDD scenarios]
- [Source: _bmad-output/planning-artifacts/prd.md — FR28: Filter by entity type; FR29: Filter by source document]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — Graph Controls Toolbar anatomy with filter chips and document dropdown]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — Filter animation: opacity + scale 200ms ease-out]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — Filter rules: instant apply, additive, active filter badge]
- [Source: _bmad-output/planning-artifacts/architecture.md — MENTIONED_IN relationship: entity→document provenance edges in Neo4j]
- [Source: _bmad-output/planning-artifacts/architecture.md — API: GET /investigations/{id}/graph/ hub-ordered subgraph]
- [Source: apps/api/app/services/graph_query.py — Current _fetch_hub_nodes, _fetch_edges_between, _fetch_total_counts Cypher queries]
- [Source: apps/api/app/services/extraction.py — MENTIONED_IN edge creation: MERGE (e)-[m:MENTIONED_IN {chunk_id: $chunk_id}]->(d)]
- [Source: apps/api/app/api/v1/entities.py — ALLOWED_ENTITY_TYPES validation pattern]
- [Source: apps/web/src/hooks/useGraphData.ts — Current hook signature and useExpandNeighbors cache merge pattern]
- [Source: apps/web/src/hooks/useEntities.ts — Reference pattern for filter param in query key and API call]
- [Source: apps/web/src/hooks/useDocuments.ts — useDocuments hook and DocumentResponse type for document dropdown]
- [Source: apps/web/src/components/graph/GraphCanvas.tsx — Current element sync logic to extend with removal]
- [Source: apps/web/src/components/graph/GraphControls.tsx — Floating toolbar pattern (bottom-right positioning)]
- [Source: apps/web/src/lib/entity-constants.ts — ENTITY_COLORS constant for chip colors]
- [Source: _bmad-output/implementation-artifacts/4-3-node-edge-interaction-with-entity-detail-card.md — Previous story learnings]

### Previous Story Intelligence (Story 4.3 Learnings)

1. **`ENTITY_COLORS` shared constant exists** — Extracted in 4.3 code review to `apps/web/src/lib/entity-constants.ts`. Maps `Person → "#6b9bd2"`, `Organization → "#c4a265"`, `Location → "#7dab8f"`. Use this for filter chip colors — do NOT hardcode colors.

2. **Entity type field is PascalCase** — `"Person"`, `"Organization"`, `"Location"` in API responses and Cytoscape node data. The filter chips should display human-readable labels ("People", "Orgs", "Locations") but use PascalCase values for API params (lowercase: `person`, `organization`, `location` — the backend `ALLOWED_ENTITY_TYPES` uses lowercase).

3. **GraphCanvas container has `position: relative`** — Already set for absolute-positioned EntityDetailCard and EdgeDetailPopover. The GraphFilterPanel can also use absolute positioning within this container.

4. **200ms tap delay for single-click vs double-click** — Story 4.3 added a 200ms delay on single-tap to distinguish from double-tap. Filter changes should not interfere with this — filters are in a separate UI panel, not on graph elements.

5. **Cytoscape element sync in `useEffect`** — Current code adds elements and updates styles but does NOT remove elements. For filtering, the sync must also remove elements whose IDs are no longer in the data. Use `cy.remove(eles)` for elements not in the new dataset.

6. **`buildFcoseOptions(reducedMotion)` helper** — Use for relayout after filter changes. May want to pass a shorter animation duration (200ms vs default 400ms) for filter transitions — or create a variant like `buildFcoseOptions(reducedMotion, { animationDuration: 200 })`.

7. **Test patterns** — Co-located `.test.tsx` files, mock Cytoscape with `vi.mock()`, mock hooks with `vi.mock('@/hooks/...')`, TanStack QueryClientProvider wrapper. Follow exact same patterns from Story 4.3 tests.

8. **`tw-animate-css` installed** — Story 4.3 added this for entry animations. Available for filter panel entry/exit if needed.

### Git Intelligence

Recent commits (for pattern continuity):
- `a6260c1` — feat: Story 4.3 — node & edge interaction with entity detail card
- `d62f758` — feat: Story 4.2 — interactive graph canvas with Cytoscape.js
- `9c599c0` — feat: Story 4.1 — graph API subgraph queries

**Commit message format:** `feat: Story 4.4 — graph filtering by entity type & source document`

**Patterns to continue:**
- Frontend tests co-located with source files
- TanStack Query hooks in `src/hooks/`
- Feature-grouped components in `src/components/graph/`
- openapi-fetch for type-safe API calls via `api.GET(...)`
- CSS custom properties for theming
- Backend: FastAPI Query params with validation, Neo4j read transaction helpers as module-level functions

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

- Fixed Cytoscape mock in GraphCanvas.test.tsx: added `startBatch`/`endBatch` and array-like `elements().filter()` to support new batch element sync logic.
- Updated `useExpandNeighbors` test cache key to include filter slots `[..., undefined, undefined]` after adding filter-aware query keys.

### Completion Notes List

- **Backend**: Added `entity_types` (comma-separated) and `document_id` (UUID) query params to `GET /{investigation_id}/graph/`. Invalid types return 422. Filters apply to both `_fetch_hub_nodes` and `_fetch_total_counts` via dynamic Cypher label expressions and MENTIONED_IN joins. `_fetch_edges_between` unchanged (already scoped to node_ids).
- **Frontend**: Created `GraphFilterPanel` component with entity type toggle chips (colored using `ENTITY_COLORS`), document dropdown (native `<select>`), active filter badge, and collapsed/expanded states. Wired into `GraphCanvas` with filter state management. Cytoscape element sync now diffs incoming data against existing elements, removing filtered-out nodes/edges via batch operations with 200ms animated relayout. Detail card auto-closes when selected node is filtered out.
- **Hook updates**: `useGraphData` and `useExpandNeighbors` accept optional `GraphFilters` param, included in query key for cache separation. Neighbor API is unfiltered but cache merge targets the correct filter-aware key.
- **Test results**: 258 backend tests pass, 145 frontend tests pass (19 new: 13 GraphFilterPanel + 4 useGraphData filter + 2 GraphCanvas filter).

### Change Log

- 2026-03-14: Implemented Story 4.4 — graph filtering by entity type and source document. Added server-side filter params to graph API, created GraphFilterPanel component, wired filter state into GraphCanvas with animated element sync, passed documents from investigation workspace. Added 26 new tests (7 backend, 19 frontend).
- 2026-03-14: Code review fixes — (H1) memoized `filters` object with `useMemo` to prevent Cytoscape event handler re-registration every render; (H2) fixed edge detail card not clearing when filter change removes selected edge; (H3) deduplicated `ALLOWED_ENTITY_TYPES` — now imported from `entities.py`; (M1) normalized entity types to lowercase at API validation boundary; (M2) added 6 unit tests for `_build_label_expr`; (M3) fixed inconsistent document status check (`"completed"` → `"complete"`); (M4) added `sprint-status.yaml` to File List.

### File List

**New files:**
- `apps/web/src/components/graph/GraphFilterPanel.tsx`
- `apps/web/src/components/graph/GraphFilterPanel.test.tsx`

**Modified files:**
- `apps/api/app/api/v1/graph.py`
- `apps/api/app/services/graph_query.py`
- `apps/api/tests/api/test_graph.py`
- `apps/web/src/hooks/useGraphData.ts`
- `apps/web/src/hooks/useGraphData.test.ts`
- `apps/web/src/components/graph/GraphCanvas.tsx`
- `apps/web/src/components/graph/GraphCanvas.test.tsx`
- `apps/web/src/routes/investigations/$id.tsx`
- `apps/web/src/lib/api-types.generated.ts`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
