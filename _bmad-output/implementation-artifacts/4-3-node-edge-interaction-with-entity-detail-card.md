# Story 4.3: Node & Edge Interaction with Entity Detail Card

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an investigator,
I want to click on entities and relationships in the graph to see their details and evidence,
So that I can inspect the facts behind any connection.

## Acceptance Criteria

1. **GIVEN** the graph is displayed with entities, **WHEN** the investigator clicks a node, **THEN** an Entity Detail Card appears showing: name, type badge (colored dot + label), confidence score, relationships list (type → target entity with citation superscript, truncated at 5 with "show more"), and source documents list, **AND** the card is a non-focus-trapping dialog (`role="dialog"`, `aria-label="Details for [entity name]"`), **AND** the card's floating position adapts to available graph canvas space (positioned near the clicked node, auto-repositioned to stay within viewport), **AND** the card includes an "Ask about this entity" action button that pre-fills Q&A input.

2. **GIVEN** the graph shows relationships between entities, **WHEN** the investigator clicks an edge, **THEN** relationship details appear in a compact popover: relationship type, confidence score, source and target entity names, and source citation(s) with document filename and passage text excerpt, **AND** clicking a source citation opens the document text viewer.

3. **GIVEN** an entity node is displayed, **WHEN** the investigator double-clicks it, **THEN** the node's neighborhood is loaded via `GET /api/v1/investigations/{id}/graph/neighbors/{entity_id}`, **AND** new neighbor nodes animate in (400ms ease-out, respecting `prefers-reduced-motion`) and the layout stabilizes via fcose, **AND** expansion completes in <1 second.

4. **GIVEN** an Entity Detail Card is open, **WHEN** the investigator clicks a target entity name in the relationships list, **THEN** the current card closes, the graph centers on the target entity, and a new Entity Detail Card opens for that entity.

5. **GIVEN** an Entity Detail Card is open, **WHEN** the investigator clicks elsewhere on the graph, presses Escape, or clicks the ╳ button, **THEN** the card closes, **AND** clicking another node replaces the card (never stacks modals).

## Tasks / Subtasks

- [x] **Task 1: Create `useEntityDetail` hook** (AC: 1)
  - [x]1.1: Create `apps/web/src/hooks/useEntityDetail.ts`
  - [x]1.2: Hook signature: `useEntityDetail(investigationId: string, entityId: string | null)` — wraps TanStack Query for `GET /api/v1/investigations/{investigation_id}/entities/{entity_id}`
  - [x]1.3: Query key: `["entity-detail", investigationId, entityId]`
  - [x]1.4: Use `api.GET("/api/v1/investigations/{investigation_id}/entities/{entity_id}", { params: { path: { investigation_id: investigationId, entity_id: entityId } } })` via openapi-fetch
  - [x]1.5: Return `{ data: EntityDetailResponse | undefined, isLoading, isError, error }`
  - [x]1.6: `enabled: !!investigationId && !!entityId` — only fetch when both IDs are present (card is open)
  - [x]1.7: `staleTime: 30_000` — entity details are relatively stable, avoid refetching on every click

- [x] **Task 2: Create `EntityDetailCard` component** (AC: 1, 4, 5)
  - [x]2.1: Create `apps/web/src/components/graph/EntityDetailCard.tsx`
  - [x]2.2: Props: `entityId: string`, `investigationId: string`, `position: { x: number, y: number }`, `onClose: () => void`, `onNavigateToEntity: (entityId: string) => void`, `onAskAboutEntity: (entityName: string) => void`
  - [x]2.3: Use `useEntityDetail(investigationId, entityId)` for data fetching
  - [x]2.4: **Header section**: Entity name (bold), type badge with colored dot (Person=`#6b9bd2`, Org=`#c4a265`, Location=`#7dab8f`), confidence indicator (e.g., "High confidence" / "Medium confidence" / "Low confidence" based on thresholds: >=0.8 high, >=0.5 medium, <0.5 low), close button (╳) using lucide-react `X` icon
  - [x]2.5: **Relationships section**: Header "Relationships (N)", list of `type → target_name` items with confidence as subtle indicator. Truncate at 5 items, show "Show N more" button to expand. Each target entity name is clickable → calls `onNavigateToEntity(target_id)`
  - [x]2.6: **Source Documents section**: Header "Source Documents (N)", list of `document_filename` items. Each clickable (defer to Story 5 citation modal — for now log or no-op)
  - [x]2.7: **Action button**: "Ask about this entity" — calls `onAskAboutEntity(entityName)` (defer actual Q&A pre-fill to Epic 5 — for now log to console)
  - [x]2.8: **Loading state**: Skeleton matching card anatomy (3 sections with shimmer lines)
  - [x]2.9: **Error state**: "Failed to load entity details" with retry via React Query refetch
  - [x]2.10: Floating card positioning: Use `position: absolute` within the graph panel container. Calculate position from Cytoscape node rendered position (`cy.getElementById(entityId).renderedPosition()`). Auto-reposition if card overflows viewport (flip left/right/top/bottom). Card min-width `280px`, max-width `360px`, max-height `400px` with internal scroll for overflow
  - [x]2.11: **Accessibility**: `role="dialog"`, `aria-label="Details for {entity name}"`, NOT focus-trapping (user may interact with Q&A panel), close on Escape via `useEffect` keydown listener, relationships list items are focusable
  - [x]2.12: **Animation**: Entry — scale from 0.95 + fade in 150ms. Exit — fade out 100ms. Respect `prefers-reduced-motion` (instant transitions)
  - [x]2.13: **Styling**: Use `bg-[var(--bg-elevated)]` background, `border border-[var(--border-subtle)]` outline, `rounded-lg`, `shadow-lg` for floating effect. Font: Inter (matches graph UI density). Compact spacing (efficient density per UX spec)

- [x] **Task 3: Create `EdgeDetailPopover` component** (AC: 2)
  - [x]3.1: Create `apps/web/src/components/graph/EdgeDetailPopover.tsx`
  - [x]3.2: Props: `edgeData: { id: string, source: string, target: string, type: string, confidence_score: number }`, `sourceEntityName: string`, `targetEntityName: string`, `position: { x: number, y: number }`, `onClose: () => void`
  - [x]3.3: Compact popover showing: relationship type badge (e.g., "WORKS_FOR"), confidence score, source entity → target entity display, evidence summary text ("From N documents")
  - [x]3.4: Positioning: Same viewport-aware floating logic as EntityDetailCard, but smaller (max-width `260px`)
  - [x]3.5: Close on click elsewhere, Escape, or ╳ button
  - [x]3.6: **Note on source citations**: The current `GraphEdge` schema returns `type` and `confidence_score` but not source document citations. For full edge evidence, the dev should check if the backend has an edge detail endpoint or if citations are available via entity detail relationships. If no edge-level citation endpoint exists, show "View source entities for evidence" with links to the source and target entity cards. This is acceptable for MVP — detailed edge provenance can be enhanced later.
  - [x]3.7: Styling: Same floating card pattern as EntityDetailCard — `bg-[var(--bg-elevated)]`, border, rounded, shadow

- [x] **Task 4: Wire graph click handlers in `GraphCanvas`** (AC: 1, 2, 3, 4, 5)
  - [x]4.1: Modify `apps/web/src/components/graph/GraphCanvas.tsx`
  - [x]4.2: Add state: `selectedNodeId: string | null`, `selectedEdgeId: string | null`, `cardPosition: { x: number, y: number } | null`
  - [x]4.3: Register Cytoscape event handlers after `cy.ready()`:
    - `cy.on('tap', 'node', (evt) => { ... })` — set selectedNodeId to `evt.target.data('id')`, compute rendered position, clear selectedEdgeId
    - `cy.on('tap', 'edge', (evt) => { ... })` — set selectedEdgeId to `evt.target.data('id')`, compute edge midpoint rendered position, clear selectedNodeId
    - `cy.on('tap', (evt) => { if (evt.target === cy) { clearSelection() } })` — click on background clears both selections
    - `cy.on('dbltap', 'node', (evt) => { ... })` — trigger neighbor expansion via `expandNeighbors(entityId)` from `useExpandNeighbors`
  - [x]4.4: **Position calculation**: Use `evt.target.renderedPosition()` for nodes. For edges, use midpoint of source/target rendered positions. Convert to graph panel-relative coordinates for absolute positioning of the floating card
  - [x]4.5: **Prevent double-click selecting node**: On `dbltap` handler, also call `expandNeighbors` AND keep existing card open (if any) — card stays, neighbors animate in
  - [x]4.6: **Neighbor expansion animation**: After `expandNeighbors` resolves and new elements are added to Cytoscape, run fcose layout with `animate: !reducedMotion, animationDuration: 400`. Use the existing `buildFcoseOptions` helper from `cytoscape-styles.ts`
  - [x]4.7: Pass `onNavigateToEntity` callback to EntityDetailCard: when called, `cy.getElementById(targetId).select()`, `cy.animate({ center: { eles: cy.getElementById(targetId) }, duration: 300 })`, then set `selectedNodeId = targetId`
  - [x]4.8: Render `EntityDetailCard` when `selectedNodeId` is set, render `EdgeDetailPopover` when `selectedEdgeId` is set. Both positioned absolutely within the graph container
  - [x]4.9: **Cleanup**: Remove event handlers on component unmount via `cy.removeListener()`

- [x] **Task 5: Add node hover tooltip** (AC: 1)
  - [x]5.1: Register `cy.on('mouseover', 'node', ...)` and `cy.on('mouseout', 'node', ...)` handlers
  - [x]5.2: Show a lightweight CSS tooltip (not a React component) near the hovered node with: entity name, type, connection count
  - [x]5.3: Use a simple `<div>` element managed via DOM manipulation (ref-based, outside React render cycle) for performance — graph hover events fire rapidly
  - [x]5.4: Hide tooltip when node is clicked (card replaces tooltip) or when mouse leaves node
  - [x]5.5: Styling: Small, dark tooltip with `bg-[var(--bg-elevated)]`, `text-[var(--text-primary)]`, `text-xs`, `rounded`, `px-2 py-1`, `shadow`

- [x] **Task 6: Update investigation workspace integration** (AC: 1)
  - [x]6.1: Modify `apps/web/src/routes/investigations/$id.tsx` if needed to pass additional props or callbacks to `GraphCanvas`
  - [x]6.2: The "Ask about this entity" callback should be a no-op or console.log for now — Q&A panel integration is Epic 5. Add a `// TODO: Epic 5 — wire to Q&A input` comment
  - [x]6.3: Ensure the graph panel container has `position: relative` so that absolute-positioned EntityDetailCard and EdgeDetailPopover are positioned correctly within the graph panel

- [x] **Task 7: Write frontend tests** (AC: 1, 2, 3, 4, 5)
  - [x]7.1: `apps/web/src/hooks/useEntityDetail.test.ts` — hook fetches entity detail, handles null entityId (disabled query), handles error response
  - [x]7.2: `apps/web/src/components/graph/EntityDetailCard.test.tsx` — renders entity name/type/confidence, shows relationships truncated at 5 with "show more", calls onNavigateToEntity on target click, calls onClose on ╳ click, shows loading skeleton, shows error state
  - [x]7.3: `apps/web/src/components/graph/EdgeDetailPopover.test.tsx` — renders edge type and confidence, shows source/target entity names, calls onClose
  - [x]7.4: `apps/web/src/components/graph/GraphCanvas.test.tsx` — extend existing tests to verify: node click registers tap handler, edge click registers tap handler, double-click triggers expand neighbors, background click clears selection
  - [x]7.5: Mock `useEntityDetail` in EntityDetailCard tests: `vi.mock('@/hooks/useEntityDetail', () => ({ useEntityDetail: vi.fn() }))`
  - [x]7.6: Mock Cytoscape event registration in GraphCanvas tests: verify `cy.on('tap', 'node', ...)`, `cy.on('tap', 'edge', ...)`, `cy.on('dbltap', 'node', ...)` are called

## Dev Notes

### Architecture Context

This is the **third story in Epic 4** (Graph Visualization & Exploration). Story 4.1 created the backend graph API. Story 4.2 created the frontend graph canvas with Cytoscape.js, the `useCytoscape` hook, `useGraphData` hook, `GraphCanvas` component, `GraphControls` toolbar, and `SplitView` layout. This story adds **interactivity** — clicking nodes/edges to inspect details, and double-clicking to expand neighborhoods.

**Stories 4.4–4.5 will build on top of this story:**
- 4.4: Graph filtering by entity type and source document (uses the graph canvas and node visibility)
- 4.5: Entity search with graph highlighting (uses the graph canvas and node centering)

**This story's components are extension points for later stories:**
- `EntityDetailCard` will be reused when entity search (4.5) selects a result
- Node centering/highlighting patterns established here will be reused by answer-to-graph bridge (Epic 5)
- The "Ask about this entity" button is a placeholder for Epic 5 Q&A integration

### What Already Exists (DO NOT recreate)

| Component | Location | What It Does |
|-----------|----------|-------------|
| Graph API (subgraph) | `apps/api/app/api/v1/graph.py` | `GET /{investigation_id}/graph/` — paginated Cytoscape.js-format graph data |
| Graph API (neighbors) | `apps/api/app/api/v1/graph.py` | `GET /{investigation_id}/graph/neighbors/{entity_id}` — neighbor expansion |
| Entity detail API | `apps/api/app/api/v1/entities.py` | `GET /{investigation_id}/entities/{entity_id}` — entity with relationships & sources |
| Entity detail schema | `apps/api/app/schemas/entity.py` | `EntityDetailResponse` with `EntityRelationship[]` and `EntitySource[]` |
| Graph schemas | `apps/api/app/schemas/graph.py` | `GraphNode`, `GraphEdge`, `GraphResponse` — Cytoscape.js format |
| GraphQueryService | `apps/api/app/services/graph_query.py` | Neo4j hub-ordered subgraph + neighbor queries |
| EntityQueryService | `apps/api/app/services/entity_query.py` | `get_entity_detail()` — fetches entity, relationships, sources from Neo4j + PostgreSQL |
| TypeScript API types | `src/lib/api-types.generated.ts` | `EntityDetailResponse`, `EntityRelationship`, `EntitySource`, `GraphResponse` — already generated |
| openapi-fetch client | `src/lib/api-client.ts` | `api.GET(...)` pattern — use for entity detail fetching |
| `useCytoscape` hook | `src/hooks/useCytoscape.ts` | Cytoscape instance lifecycle, reduced motion detection, error handling |
| `useGraphData` hook | `src/hooks/useGraphData.ts` | Graph data fetching + `useExpandNeighbors` for neighbor expansion with deduplication |
| `GraphCanvas` component | `src/components/graph/GraphCanvas.tsx` | Graph rendering, element syncing, edge hover labels, loading/empty/error states |
| `GraphControls` component | `src/components/graph/GraphControls.tsx` | Zoom in/out, fit-to-view, re-layout floating toolbar |
| `cytoscape-styles.ts` | `src/lib/cytoscape-styles.ts` | Entity type colors/shapes, confidence→border mapping, node sizing, edge styles, `buildFcoseOptions()` |
| `SplitView` layout | `src/components/layout/SplitView.tsx` | Resizable 40/60 split with drag handle |
| `useEntities` hook | `src/hooks/useEntities.ts` | Entity list with type filter (for reference pattern) |
| Entity colors CSS vars | `src/globals.css` | `--entity-person: #6b9bd2`, `--entity-org: #c4a265`, `--entity-location: #7dab8f` |
| shadcn/ui Card | `src/components/ui/card.tsx` | Card, CardHeader, CardTitle, CardContent, CardFooter |
| shadcn/ui Badge | `src/components/ui/badge.tsx` | Badge with variants |
| shadcn/ui Button | `src/components/ui/button.tsx` | Button with variants and icon sizes |
| shadcn/ui Separator | `src/components/ui/separator.tsx` | Visual separator |
| Lucide icons | package.json | Already installed — `X`, `ChevronDown`, `ChevronUp`, `MessageSquare`, `FileText` etc. |
| Investigation workspace | `src/routes/investigations/$id.tsx` | SplitView layout with left=document management, right=GraphCanvas |

### Backend API Response Shapes (for frontend reference)

**`GET /api/v1/investigations/{id}/entities/{entity_id}` → `EntityDetailResponse`:**
```json
{
  "id": "uuid-string",
  "name": "Deputy Mayor Horvat",
  "type": "Person",
  "confidence_score": 0.92,
  "investigation_id": "uuid-string",
  "relationships": [
    {
      "relation_type": "WORKS_FOR",
      "target_id": "uuid-target",
      "target_name": "City Council",
      "target_type": "Organization",
      "confidence_score": 0.88
    }
  ],
  "sources": [
    {
      "document_id": "uuid-doc",
      "document_filename": "contract-award-089.pdf",
      "chunk_id": "uuid-chunk",
      "page_start": 3,
      "page_end": 3,
      "text_excerpt": "Deputy Mayor Horvat signed the contract..."
    }
  ],
  "evidence_strength": "corroborated"
}
```

**Evidence strength values:** `"corroborated"` (2+ source documents), `"single_source"` (1 document), `"none"` (0 documents)

**`GraphEdge` data shape (already in Cytoscape):**
```json
{
  "group": "edges",
  "data": {
    "id": "uuid1-WORKS_FOR-uuid2",
    "source": "uuid1",
    "target": "uuid2",
    "type": "WORKS_FOR",
    "confidence_score": 0.85
  }
}
```

**Note:** The graph edge schema does NOT include source documents/citations directly. Edge evidence is accessed through the entity detail endpoint's `relationships` and `sources` fields. For the EdgeDetailPopover, display available edge data (type, confidence, source/target names) and link to entity detail cards for full evidence chain.

### Cytoscape Event Handling Patterns

**Tap vs Click:** Cytoscape uses `tap` (not `click`) for cross-device compatibility (touch + mouse). Always use `cy.on('tap', ...)`.

**Double-tap:** Use `cy.on('dbltap', 'node', ...)` for expand-neighbors. Note: `dbltap` fires AFTER two `tap` events. To prevent the first tap from opening the entity card during a double-click, use a small delay (200ms) on the single-tap handler and cancel it if a dbltap fires within that window.

**Rendered position:** `evt.target.renderedPosition()` returns `{ x, y }` in screen pixels relative to the Cytoscape container. Use this directly for absolute positioning of floating cards within the graph panel.

**Edge midpoint:** For edge click positioning, compute midpoint of source and target rendered positions:
```typescript
const sourcePos = cy.getElementById(edgeData.source).renderedPosition();
const targetPos = cy.getElementById(edgeData.target).renderedPosition();
const midpoint = { x: (sourcePos.x + targetPos.x) / 2, y: (sourcePos.y + targetPos.y) / 2 };
```

**Event cleanup:** Always remove listeners on unmount: `cy.removeListener('tap')`, or more precisely `cy.off('tap', 'node', handler)`.

### Entity Detail Card Floating Position Logic

The card must stay within the graph panel viewport. Algorithm:

1. Get node rendered position `{ x, y }` from Cytoscape
2. Get graph container `getBoundingClientRect()` for panel bounds
3. Default: position card to the right of the node (+20px offset)
4. If card would overflow right edge → position to the left of the node
5. If card would overflow bottom → shift upward
6. If card would overflow top → shift downward
7. Clamp all positions to stay within container bounds with 8px padding

Card dimensions for calculation: width ~320px, height ~380px (estimate, use ref measurement for accuracy).

### UX Design Specifications

**Entity Detail Card anatomy (from UX spec):**
```
┌──────────────────────────────┐
│ ● Deputy Mayor Horvat   ╳   │
│   Person · High confidence   │
├──────────────────────────────┤
│ Relationships (7)            │
│  → WORKS_FOR City Council    │
│  → SIGNED contract #089      │
│  → KNOWS Marko Petrovic      │
│  ... show more               │
├──────────────────────────────┤
│ Source Documents (4)         │
│  📄 contract-award-089.pdf   │
│  📄 council-minutes.pdf      │
│  📄 company-reg-2021.pdf     │
│  📄 ownership-filing.pdf     │
├──────────────────────────────┤
│ [Ask about this entity]      │
└──────────────────────────────┘
```

**Floating card behavior (from UX spec):**
- No backdrop dimming — graph remains visible and partially interactive (pan/zoom still work)
- Close via: ╳ button, Escape key, clicking elsewhere on graph, clicking another node (replaces card)
- Does NOT trap focus — user can still interact with Q&A panel
- Entry animation: scale up from 0.95 + fade in 150ms. Exit: fade out 100ms
- Never stack modals — one detail card at a time. Opening a Citation Modal from within an Entity Detail Card closes the card first

**Density:** Efficient density for the card (tighter spacing, compact layout per UX spec investigation data panels)

**Color mapping for type badges:**
| Entity Type | Color | CSS Variable |
|-------------|-------|-------------|
| Person | `#6b9bd2` | `--entity-person` |
| Organization | `#c4a265` | `--entity-org` |
| Location | `#7dab8f` | `--entity-location` |

**Confidence display thresholds:**
| Score Range | Label | Visual |
|-------------|-------|--------|
| >= 0.8 | High confidence | Strong border (from cytoscape-styles) |
| >= 0.5 | Medium confidence | Medium border |
| < 0.5 | Low confidence | Thin border |

### Project Structure Notes

**New files:**
- `apps/web/src/hooks/useEntityDetail.ts` — Entity detail data fetching hook
- `apps/web/src/hooks/useEntityDetail.test.ts` — Hook tests
- `apps/web/src/components/graph/EntityDetailCard.tsx` — Floating entity detail card
- `apps/web/src/components/graph/EntityDetailCard.test.tsx` — Card tests
- `apps/web/src/components/graph/EdgeDetailPopover.tsx` — Edge click popover
- `apps/web/src/components/graph/EdgeDetailPopover.test.tsx` — Popover tests

**Modified files:**
- `apps/web/src/components/graph/GraphCanvas.tsx` — Add click handlers, state for selected node/edge, render detail card/popover
- `apps/web/src/components/graph/GraphCanvas.test.tsx` — Extend with interaction tests

**No backend changes.** This is a frontend-only story. All required API endpoints already exist.

**No new dependencies.** All required packages (cytoscape, tanstack-query, lucide-react, shadcn/ui) are already installed.

### Testing Strategy

**Test patterns (follow Story 4.2 conventions):**
- Co-located test files with source
- Mock Cytoscape in all graph tests (same mock from Story 4.2)
- Mock `useEntityDetail` in EntityDetailCard tests
- Use `@testing-library/react` for component tests
- Use `renderHook` from `@testing-library/react` for hook tests
- TanStack Query wrapper for hooks that use queries

**Test counts:** Frontend currently has ~95+ tests. This story should add ~15-20 new tests across 4 test files (useEntityDetail: 3-4, EntityDetailCard: 5-6, EdgeDetailPopover: 3-4, GraphCanvas extensions: 4-5).

### References

- [Source: _bmad-output/planning-artifacts/epics.md — Epic 4, Story 4.3: Node & Edge Interaction with Entity Detail Card acceptance criteria]
- [Source: _bmad-output/planning-artifacts/architecture.md — API endpoints: GET /entities/{entity_id} for entity detail with relationships]
- [Source: _bmad-output/planning-artifacts/architecture.md — File structure: src/components/graph/EntityDetailCard.tsx]
- [Source: _bmad-output/planning-artifacts/architecture.md — Naming: EntityDetailCard PascalCase component, useEntityDetail camelCase hook]
- [Source: _bmad-output/planning-artifacts/architecture.md — Custom useCytoscape hook, direct imperative Cytoscape API control]
- [Source: _bmad-output/planning-artifacts/architecture.md — Confidence: node border thickness in cytoscape-styles.ts, badges in EntityDetailCard.tsx]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — Entity Detail Card anatomy, states, interactions, accessibility]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — Floating Card positioning: near node, auto-reposition within viewport, no backdrop]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — Graph interactions: click node → detail card, double-click → expand, click edge → relationship detail]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — Modal rules: never stack, non-focus-trapping for entity card, close on Escape]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — Animation: scale 0.95→1 + fade 150ms entry, fade 100ms exit]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — Efficient density for graph workspace and entity cards]
- [Source: _bmad-output/planning-artifacts/prd.md — FR25: Entity detail card on node click; FR26: Relationship details on edge click; FR27: Neighborhood expansion]
- [Source: _bmad-output/planning-artifacts/prd.md — NFR10: Node expansion <1s]
- [Source: apps/api/app/schemas/entity.py — EntityDetailResponse, EntityRelationship, EntitySource shapes]
- [Source: apps/api/app/schemas/graph.py — GraphEdge data shape (type + confidence_score, no source citations)]
- [Source: apps/web/src/hooks/useGraphData.ts — useExpandNeighbors already implemented for neighbor expansion]
- [Source: apps/web/src/lib/cytoscape-styles.ts — buildFcoseOptions helper, entity color/shape mapping]
- [Source: apps/web/src/components/graph/GraphCanvas.tsx — Current implementation to extend with click handlers]
- [Source: _bmad-output/implementation-artifacts/4-2-interactive-graph-canvas-with-cytoscape-js.md — Previous story learnings and patterns]

### Previous Story Intelligence (Story 4.2 Learnings)

1. **`useExpandNeighbors` is implemented but NOT wired to UI** — The hook exists in `useGraphData.ts` and is tested, but was intentionally deferred from Story 4.2 to this story. Wire it to the `dbltap` node handler.

2. **Edge hover labels use class-based toggle** — `cy.on('mouseover', 'edge', ...)` adds `show-label` class, `mouseout` removes it. This pattern works. Node tooltips should use a similar approach but with a DOM element (not Cytoscape class) for richer content.

3. **fcose layout only runs when new elements are added** — Story 4.2 code review fixed a bug where layout re-ran on every TanStack Query refetch. The fix checks if new elements were actually added before running layout. Follow the same pattern after neighbor expansion.

4. **`buildFcoseOptions(reducedMotion)` helper exists** — Centralized fcose layout config. Use it for neighbor expansion layout too. Options include `animate: !reducedMotion`, `animationDuration: 400`, `quality: 'default'`, `randomize: false`, `nodeSeparation: 75`.

5. **Cytoscape mount pattern** — The hook creates the Cytoscape instance with `container` ref. The instance is held in `useRef<Core | null>`, not state. Event handlers should be added after `cy.ready()` callback fires.

6. **TypeScript: cytoscape-fcose ambient module** — Already declared in `vite-env.d.ts`. No additional type declarations needed for this story.

7. **Entity colors follow UX spec, NOT epics** — Person=blue (#6b9bd2), Org=amber (#c4a265), Location=green (#7dab8f). The entity type field is PascalCase: `"Person"`, `"Organization"`, `"Location"`.

8. **window.matchMedia guard** — `useCytoscape` has a `typeof window.matchMedia === "function"` guard for jsdom. Follow same pattern if using `matchMedia` in new components.

### Git Intelligence

Recent commits:
- `d62f758` — feat: Story 4.2 — interactive graph canvas with Cytoscape.js (LATEST)
- `9c599c0` — feat: Story 4.1 — graph API subgraph queries
- `3ad8318` — feat: Story 3.5 — document-level & entity-level confidence display with code review fixes

**Patterns to continue:**
- Frontend tests co-located with source files
- TanStack Query hooks in `src/hooks/`
- Feature-grouped components in `src/components/graph/`
- openapi-fetch for type-safe API calls via `api.GET(...)`
- CSS custom properties for theming — use `var(--entity-person)` etc.
- Commit message format: `feat: Story 4.3 — node & edge interaction with entity detail card`

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

No issues encountered during implementation.

### Completion Notes List

- **Task 1**: Created `useEntityDetail` hook wrapping TanStack Query for entity detail API. Uses `enabled` guard to only fetch when both IDs are present, with 30s staleTime. 3 tests.
- **Task 2**: Created `EntityDetailCard` component with header (name, type badge with color dot, confidence label), relationships section (truncated at 5 with "show more"), source documents section, and "Ask about this entity" action button. Floating card with viewport-aware positioning, loading skeleton, error state with retry, Escape-to-close, and `role="dialog"` accessibility. 9 tests.
- **Task 3**: Created `EdgeDetailPopover` with relationship type badge, confidence %, source→target entity display, and clickable entity links for evidence navigation (MVP — no edge-level citation endpoint). Compact floating popover with same positioning logic as EntityDetailCard. 5 tests.
- **Task 4**: Wired Cytoscape event handlers in GraphCanvas — `tap node` (opens EntityDetailCard with 200ms delay to distinguish from double-click), `tap edge` (opens EdgeDetailPopover at edge midpoint), `tap background` (clears selection), `dbltap node` (expands neighbors via `useExpandNeighbors`). Navigate-to-entity animates graph center and opens new card. All handlers cleaned up on unmount.
- **Task 5**: Added DOM-based node hover tooltip (outside React render cycle for performance) showing `name · type · N connections`. Hidden when card opens or mouse leaves.
- **Task 6**: GraphCanvas container already has `position: relative` for absolute card positioning. "Ask about this entity" is console.log with TODO comment for Epic 5. No changes needed to investigation workspace.
- **Task 7**: All tests written co-located with source files following project conventions. 22 new tests across 4 files (useEntityDetail: 3, EntityDetailCard: 9, EdgeDetailPopover: 5, GraphCanvas: 5 new / 9 total). Full suite: 126 tests, 0 regressions.

### Change Log

- 2026-03-13: Implemented Story 4.3 — Node & Edge Interaction with Entity Detail Card. Added entity detail hook, floating EntityDetailCard, EdgeDetailPopover, Cytoscape click/double-click/hover handlers, and 22 new frontend tests.
- 2026-03-13: Code review fixes — extracted shared ENTITY_COLORS constant, fixed React key collision in sources list (document_id → chunk_id), removed dead code in dbltap handler, added clickable entity links to EdgeDetailPopover, installed tw-animate-css for entry animations, added Escape key and "Ask about entity" tests. Suite: 126 tests, 0 regressions.

### File List

**New files:**
- `apps/web/src/hooks/useEntityDetail.ts`
- `apps/web/src/hooks/useEntityDetail.test.ts`
- `apps/web/src/components/graph/EntityDetailCard.tsx`
- `apps/web/src/components/graph/EntityDetailCard.test.tsx`
- `apps/web/src/components/graph/EdgeDetailPopover.tsx`
- `apps/web/src/components/graph/EdgeDetailPopover.test.tsx`
- `apps/web/src/lib/entity-constants.ts`

**Modified files:**
- `apps/web/src/components/graph/GraphCanvas.tsx`
- `apps/web/src/components/graph/GraphCanvas.test.tsx`
- `apps/web/src/lib/cytoscape-styles.ts`
- `apps/web/src/globals.css`
- `apps/web/package.json`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/4-3-node-edge-interaction-with-entity-detail-card.md`
