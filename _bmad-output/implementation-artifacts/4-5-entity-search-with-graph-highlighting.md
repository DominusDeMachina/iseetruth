# Story 4.5: Entity Search with Graph Highlighting

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an investigator,
I want to search for specific entities by name and see them highlighted in the graph,
So that I can quickly locate known persons, organizations, or locations.

## Acceptance Criteria

1. **GIVEN** the graph is displayed, **WHEN** the investigator types a search query in the entity search input, **THEN** matching entities are returned from `GET /api/v1/investigations/{id}/entities/` with search parameter, **AND** results appear in <500 milliseconds, **AND** matching nodes in the graph are highlighted with a glow effect (opacity transition + subtle pulse, 600ms).

2. **GIVEN** a search result is selected, **WHEN** the investigator clicks on a search result, **THEN** the graph centers on and highlights the matching node, **AND** the node's neighborhood is expanded if not already loaded.

3. **GIVEN** the investigator clears the search, **WHEN** the search input is emptied, **THEN** all highlighting is removed and the graph returns to its default visual state.

## Tasks / Subtasks

- [x] **Task 1: Add search query parameter to backend entities API** (AC: 1)
  - [x] 1.1: Modify `apps/api/app/api/v1/entities.py` — add `search: str | None = Query(None)` parameter to `list_entities()` endpoint
  - [x] 1.2: Modify `apps/api/app/services/entity_query.py` — update `list_entities()` to accept `search: str | None` parameter and pass to `_fetch_entity_list()`
  - [x] 1.3: Modify `_fetch_entity_list()` — when `search` is provided, add `WHERE toLower(e.name) CONTAINS toLower($search)` clause to the Cypher query; combine with existing type filter using AND logic
  - [x] 1.4: Modify `_fetch_entity_list()` — when `search` is provided, apply the same filter to the count query so `total` reflects search results
  - [x] 1.5: Update OpenAPI spec: `cd apps/api && uv run python -c "from app.main import app; import json; print(json.dumps(app.openapi()))" > ../web/src/lib/openapi.json` then `cd apps/web && pnpm run generate-api-types`

- [x] **Task 2: Write backend tests for entity search** (AC: 1)
  - [x] 2.1: Extend `apps/api/tests/api/test_entities.py` — test `GET /entities/?search=john` returns only entities whose names contain "john" (case-insensitive)
  - [x] 2.2: Test `GET /entities/?search=john&type=person` — combined search + type filter (AND logic)
  - [x] 2.3: Test `GET /entities/?search=nonexistent` returns empty results with `total: 0`
  - [x] 2.4: Test `GET /entities/?search=` (empty string) — same as no search, returns all entities
  - [x] 2.5: Test `GET /entities/?search=ORG` — case-insensitive match returns entities with "org" in the name
  - [x] 2.6: Test that `type_summary` in the response reflects the search-filtered results, not all entities

- [x] **Task 3: Add `useSearchEntities` hook** (AC: 1, 3)
  - [x] 3.1: Create `apps/web/src/hooks/useSearchEntities.ts`
  - [x] 3.2: Hook signature: `useSearchEntities(investigationId: string, query: string)` — returns `{ data: EntityListItem[], isLoading: boolean }`
  - [x] 3.3: Call `GET /api/v1/investigations/{id}/entities/?search={query}&limit=20` via `api.GET(...)` (openapi-fetch)
  - [x] 3.4: TanStack Query key: `["entities", "search", investigationId, query]` — distinct from the `useEntities` key to prevent cache collision
  - [x] 3.5: Enable query only when `query.trim().length >= 2` — debounce at the component level, not the hook level
  - [x] 3.6: Set `staleTime: 30_000` (30s) to avoid refetching same search terms rapidly
  - [x] 3.7: Return `data?.items ?? []` for easy consumption

- [x] **Task 4: Install shadcn/ui Command component** (AC: 1, 2, 3)
  - [x] 4.1: Install cmdk dependency: `cd apps/web && pnpm add cmdk@1`
  - [x] 4.2: Create `apps/web/src/components/ui/command.tsx` — use shadcn/ui Command recipe adapted to project's CSS custom properties (dark theme, `--bg-elevated`, `--border-subtle`, `--text-primary`, `--text-muted`)
  - [x] 4.3: Verify Command component renders correctly in the project's dark theme

- [x] **Task 5: Create `EntitySearchCommand` component** (AC: 1, 2, 3)
  - [x] 5.1: Create `apps/web/src/components/graph/EntitySearchCommand.tsx`
  - [x] 5.2: Props: `investigationId: string`, `open: boolean`, `onOpenChange: (open: boolean) => void`, `onSelectEntity: (entity: EntityListItem) => void`
  - [x] 5.3: Use `CommandDialog` (cmdk) as the overlay — centers on screen with backdrop, matches project dark theme
  - [x] 5.4: Search input at top with placeholder "Search entities by name..." — debounce user input by 200ms before calling `useSearchEntities`
  - [x] 5.5: Results list grouped by entity type (People, Organizations, Locations) using `CommandGroup` — each group has a heading with entity type color dot (from `ENTITY_COLORS`)
  - [x] 5.6: Each result item shows: colored dot (entity type), entity name, confidence badge, source count — using `CommandItem`
  - [x] 5.7: Empty state: when search has results=0, show "No entities matching '{query}'" — using `CommandEmpty`
  - [x] 5.8: Initial state (no search typed): show nothing or "Type to search entities"
  - [x] 5.9: Selecting an item (click or Enter) calls `onSelectEntity(entity)` and closes the dialog
  - [x] 5.10: Escape or backdrop click closes the dialog via `onOpenChange(false)`
  - [x] 5.11: Accessibility: `CommandDialog` provides built-in keyboard navigation (arrow keys), `aria-label="Entity search"`

- [x] **Task 6: Add Cytoscape highlight styles** (AC: 1, 2, 3)
  - [x] 6.1: Modify `apps/web/src/lib/cytoscape-styles.ts` — add `.search-highlighted` node class: `border-color: #e8e0d4`, `border-width: 4`, `border-opacity: 1`, `overlay-color: #e8e0d4`, `overlay-padding: 8`, `overlay-opacity: 0.15`
  - [x] 6.2: Add `.search-dimmed` node class: `opacity: 0.3` — applied to nodes NOT matching search results when search is active (de-emphasis)
  - [x] 6.3: Add `.search-dimmed` edge class: `opacity: 0.15` — edges between non-highlighted nodes dim
  - [x] 6.4: Ensure highlight styles have higher specificity than `node:selected` to work when a highlighted node is also selected

- [x] **Task 7: Wire entity search into GraphCanvas** (AC: 1, 2, 3)
  - [x] 7.1: Modify `apps/web/src/components/graph/GraphCanvas.tsx`
  - [x] 7.2: Add search state: `const [searchOpen, setSearchOpen] = useState(false)`, `const [highlightedEntityIds, setHighlightedEntityIds] = useState<string[]>([])`
  - [x] 7.3: Add keyboard shortcut: `useEffect` with `keydown` listener for `Cmd/Ctrl+K` — calls `setSearchOpen(true)`, `e.preventDefault()` to prevent browser search
  - [x] 7.4: Render `<EntitySearchCommand>` with `open={searchOpen}`, `onOpenChange={setSearchOpen}`, `onSelectEntity={handleSearchSelect}`
  - [x] 7.5: Implement `handleSearchSelect(entity)`: (a) close search dialog, (b) check if entity's node exists in the current Cytoscape graph, (c) if yes → center + highlight, (d) if no → call `expandNeighbors(entity.id)` to load the node, then center + highlight after data arrives
  - [x] 7.6: Implement `centerAndHighlight(entityId)`: (a) apply `.search-highlighted` class to the node, (b) apply `.search-dimmed` class to all other nodes and edges, (c) animate `cy.center(node)` with `cy.animate({ center: { eles: node }, zoom: cy.zoom() }, { duration: reducedMotion ? 0 : 400 })`, (d) after 600ms run a pulse animation cycle (2 pulses) — scale node border width 4→6→4 via `node.animate()`
  - [x] 7.7: Implement `clearHighlights()`: remove `.search-highlighted` from all nodes, remove `.search-dimmed` from all elements, called when search dialog closes OR when user taps background
  - [x] 7.8: After `expandNeighbors` completes (if entity wasn't in graph), wait for the TanStack Query cache to update, then call `centerAndHighlight` on the next render cycle via `useEffect` watching `highlightedEntityIds` + graph data
  - [x] 7.9: Add search trigger button to `GraphFilterPanel` or alongside it — a search icon button (lucide-react `Search`) in the top-right area of the graph container, positioned `top-3 right-3` (opposite side from GraphFilterPanel which is `top-3 left-3`) with matching elevated style

- [x] **Task 8: Pass `expandNeighbors` function from `useExpandNeighbors` for search** (AC: 2)
  - [x] 8.1: The `useExpandNeighbors` hook already returns `expandNeighbors(entityId)` — ensure it's accessible from `handleSearchSelect` in GraphCanvas
  - [x] 8.2: After expand completes, the Cytoscape element sync `useEffect` will add the new nodes — chain `centerAndHighlight` after the new elements are rendered
  - [x] 8.3: Handle edge case: entity exists in the database but has no graph connections (isolated node) — the graph API won't include it in hub nodes. The neighbor expansion API will return it. Center on it after expansion.

- [x] **Task 9: Write frontend tests** (AC: 1, 2, 3)
  - [x] 9.1: Create `apps/web/src/hooks/useSearchEntities.test.ts` — test hook calls API with search param, test disabled when query < 2 chars, test returns empty array on no results, test query key includes search term
  - [x] 9.2: Create `apps/web/src/components/graph/EntitySearchCommand.test.tsx` — renders search input, typing triggers search, results grouped by entity type with colors, clicking result calls onSelectEntity, escape closes dialog, empty state shows message
  - [x] 9.3: Extend `apps/web/src/components/graph/GraphCanvas.test.tsx` — verify Cmd+K opens search dialog, verify search button opens dialog, verify handleSearchSelect applies highlight classes to Cytoscape, verify clearHighlights removes classes, verify expandNeighbors called when entity not in graph

## Dev Notes

### Architecture Context

This is the **fifth and final story in Epic 4** (Graph Visualization & Exploration). Stories 4.1–4.4 built the backend graph API, frontend graph canvas with Cytoscape.js, node/edge interaction with detail cards, and graph filtering by entity type and document. This story adds **entity search** — the investigator can search for entities by name and see them highlighted in the graph.

**Epic 5 will build on this:** Natural Language Q&A will use similar graph highlighting to show relevant entities when an answer is displayed (the "answer-to-graph bridge" described in the UX spec).

### Search Strategy: API-Driven with Neo4j CONTAINS

**Decision:** Search is performed server-side via the existing entities API endpoint with a new `search` query parameter. The backend uses Neo4j's `toLower(e.name) CONTAINS toLower($search)` for case-insensitive substring matching.

**Rationale:**
1. The entities API already handles type filtering and pagination — adding search is natural
2. Neo4j CONTAINS is sufficient for entity name search (not full-text, just substring match)
3. No need for a full-text search index at this scale (hundreds to low thousands of entities per investigation)
4. Results include type, confidence, source count — needed for search result display
5. Performance target: <500ms (NFR11) — CONTAINS on a small dataset is well within this

**Not using Neo4j full-text index:** Full-text search with scoring/ranking would be overkill. Entity names are short strings (3-50 chars). CONTAINS gives exact substring matching which is what investigators expect.

### Search UX: Command Palette (cmdk)

**Decision:** Use shadcn/ui Command component (built on cmdk library) as a centered overlay command palette.

**Rationale (from UX spec):**
- Triggered by: search icon button in graph area OR `Cmd/Ctrl+K` keyboard shortcut
- Opens as centered overlay with search input and grouped results
- Results grouped by entity type (People, Organizations, Locations) with colored badges
- Type-ahead filtering as user types (debounced 200ms)
- Select result → graph centers on entity + highlights it + expands neighborhood if needed
- Escape or backdrop click to dismiss
- Built-in keyboard navigation (arrow keys up/down, Enter to select)

**Why cmdk and not a custom search input:** The Command palette provides keyboard navigation, grouped results, empty states, and accessible search UX out of the box. Building this from scratch would be more code and less polished. cmdk has 0 dependencies and is lightweight (~4KB).

### What Already Exists (DO NOT recreate)

| Component | Location | What It Does |
|-----------|----------|-------------|
| Entities API | `apps/api/app/api/v1/entities.py` | `GET /{investigation_id}/entities/` — entity list with type filter (add search param) |
| EntityQueryService | `apps/api/app/services/entity_query.py` | `list_entities()`, `_fetch_entity_list()` — Neo4j queries to extend with search |
| Entity schemas | `apps/api/app/schemas/entity.py` | `EntityListItem`, `EntityListResponse`, `EntityTypeSummary` |
| `useEntities` hook | `apps/web/src/hooks/useEntities.ts` | Entity list hook — **reference pattern** for search hook, but don't modify (different use case) |
| `useGraphData` hook | `apps/web/src/hooks/useGraphData.ts` | Graph data fetching with filters |
| `useExpandNeighbors` | `apps/web/src/hooks/useGraphData.ts` | Double-tap node expansion — reuse for search result expansion |
| `GraphCanvas` | `apps/web/src/components/graph/GraphCanvas.tsx` | Graph rendering, click handlers, filter state — extend with search state |
| `GraphFilterPanel` | `apps/web/src/components/graph/GraphFilterPanel.tsx` | Filter controls at top-left — **positioning reference** for search button |
| `GraphControls` | `apps/web/src/components/graph/GraphControls.tsx` | Zoom/fit/relayout at bottom-right |
| `ENTITY_COLORS` | `apps/web/src/lib/entity-constants.ts` | `{ Person: "#6b9bd2", Organization: "#c4a265", Location: "#7dab8f" }` — use for search result colors |
| Cytoscape styles | `apps/web/src/lib/cytoscape-styles.ts` | Node/edge styles — add highlight classes here |
| `useCytoscape` hook | `apps/web/src/hooks/useCytoscape.ts` | Cytoscape lifecycle, `reducedMotion` flag |
| `buildFcoseOptions` | `apps/web/src/lib/cytoscape-styles.ts` | fcose layout config |
| shadcn/ui Button | `apps/web/src/components/ui/button.tsx` | Button with variants |
| shadcn/ui Badge | `apps/web/src/components/ui/badge.tsx` | Badge for confidence display |
| shadcn/ui Dialog | `apps/web/src/components/ui/dialog.tsx` | Dialog base — CommandDialog builds on this pattern |
| Lucide icons | package.json | `Search`, `X`, `User`, `Building2`, `MapPin` etc. |
| `api` client | `apps/web/src/lib/api-client.ts` | openapi-fetch client for type-safe API calls |
| Investigation workspace | `apps/web/src/routes/investigations/$id.tsx` | Contains GraphCanvas — no changes needed for search |

### Backend Implementation Details

**Current `_fetch_entity_list` Cypher (to modify):**
```cypher
MATCH (e:Person|Organization|Location {investigation_id: $investigation_id})
OPTIONAL MATCH (e)-[:MENTIONED_IN]->(d:Document)
WITH e, labels(e)[0] AS type, COUNT(DISTINCT d) AS source_count
RETURN e.id AS id, e.name AS name, type, e.confidence_score AS confidence_score, source_count
```

**With search filter:**
```cypher
MATCH (e:Person|Organization|Location {investigation_id: $investigation_id})
WHERE toLower(e.name) CONTAINS toLower($search)
OPTIONAL MATCH (e)-[:MENTIONED_IN]->(d:Document)
WITH e, labels(e)[0] AS type, COUNT(DISTINCT d) AS source_count
RETURN e.id AS id, e.name AS name, type, e.confidence_score AS confidence_score, source_count
```

**With search + type filter combined:**
```cypher
MATCH (e:Person {investigation_id: $investigation_id})
WHERE toLower(e.name) CONTAINS toLower($search)
OPTIONAL MATCH (e)-[:MENTIONED_IN]->(d:Document)
WITH e, labels(e)[0] AS type, COUNT(DISTINCT d) AS source_count
RETURN e.id AS id, e.name AS name, type, e.confidence_score AS confidence_score, source_count
```

**Important:** The `type_summary` computation in `list_entities()` currently counts types from the full result set. With search, it must count from the search-filtered results. The current code at lines 40-51 of `entity_query.py` computes summary from `all_entities` which is the result of `_fetch_entity_list()` — since `_fetch_entity_list()` will return only search-matching entities, the summary will naturally be correct.

### Frontend Search Flow

```
User presses Cmd+K or clicks search icon
  → EntitySearchCommand opens (CommandDialog overlay)
  → User types "horv" (200ms debounce)
  → useSearchEntities("horv") fires API call
  → Results displayed: [Person] Deputy Mayor Horvat (95% confidence, 5 sources)
  → User clicks result (or presses Enter)
  → onSelectEntity called with EntityListItem
  → GraphCanvas.handleSearchSelect:
    1. Close search dialog
    2. Set highlightedEntityIds = [entity.id]
    3. Check if entity.id exists in Cytoscape: cy.getElementById(entity.id).length > 0
    4a. If YES → centerAndHighlight(entity.id)
    4b. If NO → expandNeighbors(entity.id), then on data update → centerAndHighlight
  → centerAndHighlight:
    1. Add .search-highlighted to target node
    2. Add .search-dimmed to all other elements
    3. cy.animate center on node (400ms, ease-out)
    4. Run 2-cycle pulse animation on node (600ms, ease-in-out) — border width oscillation
  → User taps graph background OR presses Escape
  → clearHighlights: remove all .search-* classes
```

### Cytoscape Highlight Animation Details

**Glow effect (from UX spec: "opacity transition + subtle pulse, 600ms"):**

The highlight consists of two visual components:
1. **Static glow**: `.search-highlighted` class adds `overlay-color: #e8e0d4`, `overlay-padding: 8`, `overlay-opacity: 0.15` — creates a warm glow around the node
2. **Pulse animation**: After centering, run `node.animate()` to pulse the border width: `4 → 6 → 4` over 600ms (2 cycles of 300ms each). This creates a subtle "breathing" effect that draws attention.
3. **Dimming**: All non-highlighted elements get `.search-dimmed` (opacity 0.3 for nodes, 0.15 for edges) — creates contrast that makes the highlighted node pop.

**Reduced motion:** When `prefers-reduced-motion` is active:
- Skip pulse animation
- Skip center animation (instant pan)
- Still apply static highlight + dimming classes (these are state, not motion)

### Expand + Center Pattern for Not-Yet-Loaded Entities

When the user searches for an entity that exists in the database but isn't currently rendered in the graph (e.g., it's not a hub node and hasn't been expanded):

1. `handleSearchSelect` detects node not in Cytoscape
2. Calls `expandNeighbors(entity.id)` — this fetches the entity + its neighbors from `GET /graph/neighbors/{entity_id}`
3. TanStack Query cache updates → triggers Cytoscape element sync `useEffect`
4. New elements added to Cytoscape, layout runs
5. After layout animation completes, `centerAndHighlight(entity.id)` centers on the newly added node

**Implementation:** Watch for `highlightedEntityIds` changes + graph data changes in a `useEffect`. When `highlightedEntityIds` is non-empty and the target node exists in Cytoscape, trigger `centerAndHighlight`.

### Search Button Positioning

- **Search icon button**: Positioned at `top-3 right-3` of the graph container (opposite corner from GraphFilterPanel at `top-3 left-3`)
- Style: Same elevated panel style as GraphFilterPanel — `bg-[var(--bg-elevated)]`, `border border-[var(--border-subtle)]`, `rounded-lg`, `shadow-lg`, `p-1.5`
- Icon: lucide-react `Search` icon
- Tooltip: "Search entities (⌘K)"
- Z-index: 30 (same as GraphFilterPanel)

### Project Structure Notes

**New files:**
- `apps/web/src/components/ui/command.tsx` — shadcn/ui Command component
- `apps/web/src/hooks/useSearchEntities.ts` — Search entities hook
- `apps/web/src/hooks/useSearchEntities.test.ts` — Hook tests
- `apps/web/src/components/graph/EntitySearchCommand.tsx` — Search command palette component
- `apps/web/src/components/graph/EntitySearchCommand.test.tsx` — Component tests

**Modified files:**
- `apps/api/app/api/v1/entities.py` — Add `search` query parameter
- `apps/api/app/services/entity_query.py` — Add search filter to Neo4j queries
- `apps/api/tests/api/test_entities.py` — Add entity search tests
- `apps/web/src/lib/cytoscape-styles.ts` — Add `.search-highlighted` and `.search-dimmed` classes
- `apps/web/src/components/graph/GraphCanvas.tsx` — Add search state, keyboard shortcut, search button, highlight/dim logic
- `apps/web/src/components/graph/GraphCanvas.test.tsx` — Extend with search tests
- `apps/web/src/lib/api-types.generated.ts` — Auto-regenerated after OpenAPI update

**New dependency:**
- `cmdk@1` — Command palette library (shadcn/ui Command component)

### Testing Strategy

**Backend tests:** Mock Neo4j driver, verify Cypher queries include `CONTAINS` clause with search parameter. Test search + type filter combination. Test case-insensitivity. Test empty search returns all entities. Test no-match returns empty results with correct type_summary.

**Frontend tests:**
- Co-located test files with source (project convention)
- `useSearchEntities` hook tests: query params, disabled when query too short, stale time
- `EntitySearchCommand` tests: renders search input, debounced search, grouped results with entity type colors, selection callback, keyboard navigation (Escape closes)
- `GraphCanvas` search integration: Cmd+K opens search, search button opens search, highlight classes applied, clearHighlights on background tap, expandNeighbors called for missing nodes

**Test counts:** Current suite: ~145 frontend tests, ~258 backend tests. This story should add ~18-22 new tests: backend entity search (6), useSearchEntities hook (4), EntitySearchCommand component (5-6), GraphCanvas search integration (3-4).

### References

- [Source: _bmad-output/planning-artifacts/epics.md — Epic 4, Story 4.5 acceptance criteria and BDD scenarios]
- [Source: _bmad-output/planning-artifacts/prd.md — FR30: Entity search with graph highlighting; NFR11: Entity search <500ms]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — Entity Search (Command Palette): triggered by search icon or Cmd/Ctrl+K, Command component overlay, grouped by entity type]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — Component Strategy: Command component for entity search across investigation]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — Animation: Graph highlighting (answer entities glow) = opacity transition + subtle pulse (2 cycles), 600ms, ease-in-out]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — Search & Filtering: Entity Search Command palette with results grouped by entity type with colored badges]
- [Source: _bmad-output/planning-artifacts/architecture.md — FR23-FR30 mapping: graph.py, entities.py endpoints]
- [Source: _bmad-output/planning-artifacts/architecture.md — Cytoscape.js Custom React Wrapper: custom useCytoscape hook, imperative control for highlighting]
- [Source: apps/api/app/services/entity_query.py — Current _fetch_entity_list Cypher queries to extend with CONTAINS]
- [Source: apps/api/app/api/v1/entities.py — Current endpoint with type filter pattern to follow for search param]
- [Source: apps/web/src/hooks/useEntities.ts — Reference pattern for entity API hooks with TanStack Query]
- [Source: apps/web/src/hooks/useGraphData.ts — useExpandNeighbors cache merge pattern, GraphFilters type]
- [Source: apps/web/src/components/graph/GraphCanvas.tsx — Current state management, element sync, click handlers]
- [Source: apps/web/src/components/graph/GraphFilterPanel.tsx — Positioning and styling pattern for graph overlay controls]
- [Source: apps/web/src/lib/cytoscape-styles.ts — Current node:selected and node:active classes as highlight precedent]
- [Source: apps/web/src/lib/entity-constants.ts — ENTITY_COLORS for search result color coding]
- [Source: _bmad-output/implementation-artifacts/4-4-graph-filtering-by-entity-type-source-document.md — Previous story learnings and patterns]

### Previous Story Intelligence (Story 4.4 Learnings)

1. **`ENTITY_COLORS` shared constant** — Use for search result type indicators. Maps `Person → "#6b9bd2"`, `Organization → "#c4a265"`, `Location → "#7dab8f"`. Do NOT hardcode colors.

2. **Entity type field is PascalCase in API responses** — `"Person"`, `"Organization"`, `"Location"`. The search results will use these. Display as human-readable labels ("People", "Orgs", "Locations") in Command groups.

3. **GraphCanvas container has `position: relative`** — Already set for absolute-positioned overlays (EntityDetailCard, EdgeDetailPopover, GraphFilterPanel). Search button can also use absolute positioning.

4. **200ms tap delay for single-click vs double-click** — Search highlight clearing on background tap should work through the existing `cy.on('tap')` handler, not conflict with it.

5. **Cytoscape element sync in `useEffect`** — Story 4.4 updated this to handle element removal for filtering. The search feature adds elements via `expandNeighbors` which follows the existing cache merge pattern — element sync will add them automatically.

6. **`buildFcoseOptions(reducedMotion)` helper** — Use for relayout after expand-then-center. Centering uses `cy.animate()` which is separate from layout.

7. **Test patterns** — Co-located `.test.tsx` files, mock Cytoscape with `vi.mock()`, mock hooks with `vi.mock('@/hooks/...')`, TanStack QueryClientProvider wrapper.

8. **`tw-animate-css` installed** — Available for Command dialog enter/exit animations if needed.

9. **GraphFilterPanel z-index: 30** — The search button should use the same z-index. EntityDetailCard and EdgeDetailPopover use z-index 20 — search overlay (CommandDialog) should be above all of these (z-index 50 or use dialog default).

10. **Filter-aware query keys** — `useGraphData` uses `["graph", investigationId, filters.entityTypes, filters.documentId]`. The `useSearchEntities` hook should use a completely separate key prefix `["entities", "search", ...]` to avoid any cache interference.

11. **`expandNeighbors` returns a promise** — The `mutateAsync` from TanStack Query mutation can be awaited. Use this to chain `centerAndHighlight` after expansion completes.

12. **Memoized `filters` object** — Story 4.4 code review fixed a bug where unmemoized filters caused Cytoscape re-registration. Apply same `useMemo` discipline to any objects passed to hooks or effects.

### Git Intelligence

Recent commits (for pattern continuity):
- `e4f2070` — feat: Story 4.4 — graph filtering by entity type & source document
- `a6260c1` — feat: Story 4.3 — node & edge interaction with entity detail card
- `d62f758` — feat: Story 4.2 — interactive graph canvas with Cytoscape.js
- `9c599c0` — feat: Story 4.1 — graph API subgraph queries

**Commit message format:** `feat: Story 4.5 — entity search with graph highlighting`

**Patterns to continue:**
- Frontend tests co-located with source files
- TanStack Query hooks in `src/hooks/`
- Feature-grouped components in `src/components/graph/`
- openapi-fetch for type-safe API calls via `api.GET(...)`
- CSS custom properties for theming
- Backend: FastAPI Query params with validation, Neo4j read transaction helpers as module-level functions
- shadcn/ui components in `src/components/ui/`

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

- cmdk library requires `ResizeObserver` and `Element.scrollIntoView` polyfills in jsdom test environment — added to `test-setup.ts`
- cmdk's built-in client-side filtering conflicts with server-side search — disabled with `shouldFilter={false}` on CommandDialog

### Completion Notes List

- Backend: Added `search` query parameter to `GET /entities/` endpoint, modifying `entities.py`, `entity_query.py`, and `_fetch_entity_list()` to support case-insensitive substring matching via Neo4j `CONTAINS`
- Frontend: Created `useSearchEntities` hook with TanStack Query, 30s staleTime, enabled only when query >= 2 chars
- Frontend: Created `EntitySearchCommand` component using cmdk CommandDialog with debounced search, grouped results by entity type, and colored type indicators
- Frontend: Added `.search-highlighted` and `.search-dimmed` Cytoscape styles for glow effect and de-emphasis
- Frontend: Wired search into GraphCanvas with Cmd/Ctrl+K shortcut, search button, centerAndHighlight with pulse animation, and expand-then-center for entities not in graph
- Tests: 6 backend search tests, 4 hook tests, 5 component tests, 5 GraphCanvas search integration tests — all passing
- All 270 backend tests pass, all 160 frontend tests pass — zero regressions

### Change Log

- 2026-03-14: Story 4.5 implementation complete — entity search with graph highlighting
- 2026-03-14: Code review fixes applied (5 issues fixed):
  - [H1] Fixed `centerAndHighlight` not clearing previous highlight classes before applying new ones (GraphCanvas.tsx)
  - [H2] Fixed tautological assertion in `test_search_returns_matching_entities` that could pass incorrectly (test_entities.py)
  - [M1] Added visually hidden `DialogTitle` to CommandDialog for screen reader accessibility (command.tsx)
  - [M2] Added loading indicator ("Searching…") during active search in EntitySearchCommand (EntitySearchCommand.tsx)
  - [M3] Added 3 missing GraphCanvas search integration tests: highlight classes, clearHighlights on background tap, expandNeighbors for missing nodes (GraphCanvas.test.tsx)

### File List

**New files:**
- `apps/web/src/components/ui/command.tsx`
- `apps/web/src/hooks/useSearchEntities.ts`
- `apps/web/src/hooks/useSearchEntities.test.ts`
- `apps/web/src/components/graph/EntitySearchCommand.tsx`
- `apps/web/src/components/graph/EntitySearchCommand.test.tsx`

**Modified files:**
- `apps/api/app/api/v1/entities.py`
- `apps/api/app/services/entity_query.py`
- `apps/api/tests/api/test_entities.py`
- `apps/web/src/lib/cytoscape-styles.ts`
- `apps/web/src/components/graph/GraphCanvas.tsx`
- `apps/web/src/components/graph/GraphCanvas.test.tsx`
- `apps/web/src/lib/openapi.json`
- `apps/web/src/lib/api-types.generated.ts`
- `apps/web/src/test-setup.ts`
- `apps/web/package.json`
- `pnpm-lock.yaml`
