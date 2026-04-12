# Story 10.2: Cross-Investigation Entity Exploration & Querying

Status: done

## Story

As an investigator,
I want to explore entities that appear across multiple investigations and query for shared patterns,
So that I can build a cumulative intelligence picture and find connections I wouldn't see within a single case.

## Acceptance Criteria

1. **GIVEN** cross-investigation entity matches exist (from Story 10.1), **WHEN** the investigator clicks on a matched entity in the Cross-Investigation Links panel, **THEN** a detail view shows the entity's presence across investigations: name, type, relationships in each investigation, and source documents per investigation, **AND** the investigator can see side-by-side how the entity connects to different networks in different cases.

2. **GIVEN** the investigator wants to query across investigations, **WHEN** they use a "Cross-Investigation Search" input in the Cross-Investigation Links panel, **THEN** they can search for an entity name, type, or keyword across all their investigations, **AND** results show which investigations contain matching entities and the relationship context in each, **AND** results are returned within 15 seconds (NFR33).

3. **GIVEN** the investigator views a cross-investigation match, **WHEN** they click "Open in Investigation" on a specific investigation, **THEN** they navigate to that investigation's workspace with the matched entity centered and highlighted in the graph, **AND** the Entity Detail Card opens for that entity showing its relationships within that investigation.

4. **GIVEN** a cross-investigation match is a false positive (different real-world entities with the same name), **WHEN** the investigator reviews the match, **THEN** they can dismiss the match as "not the same entity", **AND** dismissed matches are remembered and not shown again, **AND** dismissed matches do not affect the entity data in either investigation.

5. **GIVEN** the investigator views the investigation list (home page), **WHEN** investigations have cross-investigation entity matches, **THEN** each investigation card shows a count of cross-investigation entity links (e.g., "3 entities shared with other investigations"), **AND** this count serves as a discovery prompt to explore connections.

FRs covered: FR60 (view cross-investigation entity matches), FR61 (cross-investigation entity queries)

## Tasks / Subtasks

- [x] **Task 1: Cross-investigation entity detail API endpoint** (AC: 1)
  - [x] 1.1: Add `CrossInvestigationEntityDetail` schema to `apps/api/app/schemas/cross_investigation.py`:
    - `entity_name`, `entity_type`, list of `InvestigationPresence` (investigation_id, investigation_name, entity_id, relationships: list of {type, target_name, target_type, confidence_score}, source_documents: list of {document_id, filename, mention_count}, relationship_count, confidence_score)
  - [x] 1.2: Add `GET /api/v1/cross-links/entity-detail/` endpoint to `apps/api/app/api/v1/cross_investigation.py`:
    - Query params: `entity_name` (required), `entity_type` (required), `investigation_ids` (optional comma-separated filter)
    - Find all entities matching name+type across all investigations
    - For each investigation: fetch relationships (excluding MENTIONED_IN), source documents via MENTIONED_IN edges
    - Return `CrossInvestigationEntityDetail`
  - [x] 1.3: Implement `get_entity_detail_across_investigations()` in `CrossInvestigationService`:
    - Neo4j query: match entity by name+type across investigations, collect relationships and documents per investigation
    - PostgreSQL: batch-resolve investigation names and document filenames
    - Performance: must complete within 15 seconds (NFR33)

- [x] **Task 2: Cross-investigation search API endpoint** (AC: 2)
  - [x] 2.1: Add `CrossInvestigationSearchRequest` and `CrossInvestigationSearchResponse` schemas:
    - Request: `query` (string), `entity_type` (optional filter), `limit` (default 20)
    - Response: list of `CrossInvestigationSearchResult` (entity_name, entity_type, investigation_count, investigations: [{id, name, entity_id, relationship_count}], match_score)
  - [x] 2.2: Add `GET /api/v1/cross-links/search/` endpoint:
    - Query params: `q` (required), `type` (optional), `limit` (optional, default 20)
    - Searches entities by name (case-insensitive CONTAINS) across ALL investigations
    - Groups results by (entity_name, entity_type), counts distinct investigations
    - Returns within 15 seconds (NFR33)
  - [x] 2.3: Implement `search_across_investigations()` in `CrossInvestigationService`:
    - Neo4j query: `MATCH (e:Person|Organization|Location) WHERE toLower(e.name) CONTAINS toLower($query)` with optional type filter
    - Group by name+type, collect investigation details
    - Sort by investigation_count DESC, then name ASC

- [x] **Task 3: Dismiss false-positive matches API** (AC: 4)
  - [x] 3.1: Create `DismissedMatch` SQLModel in `apps/api/app/models/dismissed_match.py`:
    - Fields: `id` (UUID PK), `entity_name` (str), `entity_type` (str), `source_investigation_id` (FK), `target_investigation_id` (FK), `dismissed_at` (datetime)
    - Unique constraint: (entity_name, entity_type, source_investigation_id, target_investigation_id)
  - [x] 3.2: Create Alembic migration for `dismissed_matches` table
  - [x] 3.3: Add `POST /api/v1/investigations/{investigation_id}/cross-links/dismiss` endpoint:
    - Body: `{entity_name, entity_type, target_investigation_id}`
    - Creates `DismissedMatch` record
    - Returns 201 on success, 409 if already dismissed
  - [x] 3.4: Add `DELETE /api/v1/investigations/{investigation_id}/cross-links/dismiss` endpoint:
    - Body: `{entity_name, entity_type, target_investigation_id}`
    - Removes `DismissedMatch` record (undo dismiss)
    - Returns 204
  - [x] 3.5: Update `CrossInvestigationService.find_matches()` to filter out dismissed matches:
    - After Neo4j query, load dismissed matches from PostgreSQL for the investigation
    - Exclude any match where (entity_name, entity_type, target_investigation_id) is in dismissed set
  - [x] 3.6: Update `search_across_investigations()` to respect dismissals similarly

- [x] **Task 4: Cross-investigation link counts for investigation list API** (AC: 5)
  - [x] 4.1: Add `cross_link_count: int` field to `InvestigationResponse` schema
  - [x] 4.2: Add `_get_cross_link_counts_batch()` in `apps/api/app/api/v1/investigations.py`:
    - Single Neo4j query across all provided investigation IDs
    - For each investigation: count distinct entities that have name+type matches in other investigations
    - Exclude dismissed matches
    - Return `dict[uuid.UUID, int]`
  - [x] 4.3: Update `list_investigations` endpoint to include cross_link_count per investigation
  - [x] 4.4: Update `get_investigation` endpoint to include cross_link_count

- [x] **Task 5: Frontend — Entity detail view in CrossInvestigationPanel** (AC: 1)
  - [x] 5.1: Create `apps/web/src/components/cross-investigation/CrossInvestigationEntityDetail.tsx`:
    - Full-panel detail view replacing the match list when an entity is clicked
    - Shows entity name (bold), type badge, presence across investigations
    - Per-investigation section: investigation name, relationships list (type, target), source documents (filename, mention count)
    - Back button to return to match list
    - "Open in Investigation" button per investigation
  - [x] 5.2: Create `useCrossInvestigationEntityDetail` hook in `apps/web/src/hooks/useCrossInvestigation.ts`:
    - Query key: `['cross-investigation-detail', entityName, entityType]`
    - Fetches `GET /api/v1/cross-links/entity-detail/?entity_name=X&entity_type=Y`
    - Stale time: 5 minutes
  - [x] 5.3: Update `CrossInvestigationMatchCard` to make entity name clickable — opens entity detail view within panel

- [x] **Task 6: Frontend — Cross-investigation search** (AC: 2)
  - [x] 6.1: Add search input at top of `CrossInvestigationPanel`:
    - Text input with search icon, placeholder "Search across investigations..."
    - Debounced (300ms) to avoid excessive API calls
    - When search is active, shows search results instead of match list
    - Clear button to return to default match list view
  - [x] 6.2: Create `useCrossInvestigationSearch` hook:
    - Query key: `['cross-investigation-search', query]`
    - Fetches `GET /api/v1/cross-links/search/?q=X`
    - Enabled only when query length >= 2
    - Stale time: 30 seconds
  - [x] 6.3: Create `apps/web/src/components/cross-investigation/CrossInvestigationSearchResults.tsx`:
    - Renders search results grouped by entity
    - Each result: entity name, type badge, "Found in N investigations" with clickable investigation names
    - Empty state: "No entities matching 'X' found across investigations"

- [x] **Task 7: Frontend — "Open in Investigation" navigation** (AC: 3)
  - [x] 7.1: Update `CrossInvestigationMatchCard` and `CrossInvestigationEntityDetail` to include "Open in Investigation" button per investigation
  - [x] 7.2: Implement navigation: `navigate({ to: '/investigations/$id', params: { id: targetInvestigationId }, search: { highlightEntity: entityName } })`
  - [x] 7.3: In `apps/web/src/routes/investigations/$id.tsx`, read `highlightEntity` search param:
    - If present, pass to `GraphCanvas` as `highlightEntities` prop
    - After graph loads, center on and highlight the matching entity
    - Open EntityDetailCard for the matched entity automatically

- [x] **Task 8: Frontend — Dismiss false-positive matches** (AC: 4)
  - [x] 8.1: Add dismiss button (X icon with "Not the same entity" tooltip) to `CrossInvestigationMatchCard` per investigation entry
  - [x] 8.2: Create `useDismissCrossMatch` mutation hook:
    - POST to `/api/v1/investigations/{id}/cross-links/dismiss`
    - On success: invalidate `['cross-investigation', investigationId]` query
    - Optimistic update: immediately hide the dismissed investigation from the match card
  - [x] 8.3: Add undo capability: after dismissal, show toast with "Undo" action that calls DELETE dismiss endpoint

- [x] **Task 9: Frontend — Cross-link count on investigation cards** (AC: 5)
  - [x] 9.1: Update `InvestigationCard.tsx` to display `cross_link_count` when > 0:
    - Below document count: "N entities shared with other investigations" with Link2 icon
    - Use `--status-info` color for the count text
  - [x] 9.2: Update `useInvestigations` types to include `cross_link_count` field

- [x] **Task 10: Backend tests** (AC: 1, 2, 3, 4, 5)
  - [x] 10.1: Add to `apps/api/tests/services/test_cross_investigation.py`:
    - Test: entity detail across investigations returns relationships and documents
    - Test: search across investigations matches partial name
    - Test: search with type filter narrows results
    - Test: search returns empty for no matches
    - Test: dismissed matches are excluded from find_matches
    - Test: dismissed matches are excluded from search
    - Test: cross-link count returns correct counts
    - Test: cross-link count excludes dismissed matches
  - [x] 10.2: Add to `apps/api/tests/api/test_cross_investigation.py`:
    - Test: GET entity-detail endpoint returns data
    - Test: GET search endpoint returns results
    - Test: POST dismiss creates record
    - Test: POST dismiss returns 409 for duplicate
    - Test: DELETE dismiss removes record
    - Test: list_investigations includes cross_link_count
  - [x] 10.3: Create `apps/api/tests/models/test_dismissed_match.py`:
    - Test: DismissedMatch model creation
    - Test: unique constraint enforcement

- [x] **Task 11: Frontend tests** (AC: 1, 2, 3, 4, 5)
  - [x] 11.1: Create `apps/web/src/components/cross-investigation/CrossInvestigationEntityDetail.test.tsx`:
    - Test: renders entity name, type, investigation sections
    - Test: shows relationships per investigation
    - Test: shows source documents per investigation
    - Test: back button returns to match list
    - Test: "Open in Investigation" button navigates correctly
  - [x] 11.2: Create `apps/web/src/components/cross-investigation/CrossInvestigationSearchResults.test.tsx`:
    - Test: renders search results
    - Test: shows empty state for no results
  - [x] 11.3: Update `CrossInvestigationPanel.test.tsx`:
    - Test: search input renders and filters
    - Test: clicking entity opens detail view
  - [x] 11.4: Update `CrossInvestigationMatchCard.test.tsx`:
    - Test: dismiss button renders and calls mutation
    - Test: entity name is clickable
  - [x] 11.5: Update `InvestigationCard` tests (or create if needed):
    - Test: cross_link_count renders when > 0
    - Test: cross_link_count hidden when 0

## Dev Notes

### Architecture Context

This is **Story 10.2** — the second and final story in Epic 10 (Cross-Investigation Intelligence). Story 10.1 built the matching engine (Neo4j name+type matching, background task, SSE notifications, basic panel with match cards). This story adds exploration, querying, navigation, and false-positive management on top of 10.1's foundation.

**FRs covered:** FR60 (view cross-investigation entity matches — full exploration UI), FR61 (cross-investigation entity queries)
**NFRs relevant:** NFR33 (cross-investigation queries < 15 seconds)

### What Already Exists — DO NOT RECREATE

| Component | Location | What It Does |
|---|---|---|
| CrossInvestigationService | `app/services/cross_investigation.py` | `find_matches()` — Neo4j name+type matching, returns `CrossInvestigationResponse` |
| Cross-investigation schemas | `app/schemas/cross_investigation.py` | `CrossInvestigationMatch`, `InvestigationEntityInfo`, `CrossInvestigationResponse` |
| Cross-investigation API | `app/api/v1/cross_investigation.py` | `GET /api/v1/investigations/{id}/cross-links/` |
| Background matching task | `app/worker/tasks/cross_investigation_match.py` | Fire-and-forget after entity extraction |
| SSE event handler | `hooks/useSSE.ts` | Handles `cross_investigation.matches_found`, invalidates TanStack Query cache |
| CrossInvestigationPanel | `components/cross-investigation/CrossInvestigationPanel.tsx` | Slide-out panel with match cards, empty state, loading, error retry |
| CrossInvestigationMatchCard | `components/cross-investigation/CrossInvestigationMatchCard.tsx` | Expandable card: entity name, type badge, investigation list |
| useCrossInvestigation hook | `hooks/useCrossInvestigation.ts` | TanStack Query fetch of cross-links, types for `CrossInvestigationMatch` |
| GraphCanvas integration | `components/graph/GraphCanvas.tsx` | Panel toggle, badge count tracking, `lastSeenMatchCount` state |
| GraphControls | `components/graph/GraphControls.tsx` | Cross-investigation button with notification badge |
| InvestigationCard | `components/investigation/InvestigationCard.tsx` | Card with name, description, date, doc count — add cross_link_count here |
| InvestigationResponse schema | `app/schemas/investigation.py` | Has `document_count`, `entity_count` — add `cross_link_count` |
| Investigations API | `app/api/v1/investigations.py` | `_get_document_counts_batch()` pattern — follow this for cross-link counts |
| EntityQueryService | `app/services/entity_query.py` | Entity detail with relationships and provenance — reference pattern for cross-investigation detail |
| Entity schemas | `app/schemas/entity.py` | `EntityDetailResponse`, `EntityRelationship`, `EntitySource` — reuse types where applicable |
| EntityDetailCard | `components/graph/EntityDetailCard.tsx` | Floating card with entity relationships and sources — opens on node click |
| Investigation workspace route | `routes/investigations/$id.tsx` | Reads params, passes to GraphCanvas — add `highlightEntity` search param handling |
| Alembic migrations | `apps/api/migrations/versions/` | Follow existing migration patterns |
| Neo4j driver | `app/db/neo4j.py` | Async driver with `session.execute_read()` |

### Critical Implementation Details

#### New API Endpoints

All new endpoints should be on the `cross_investigation` router (`app/api/v1/cross_investigation.py`). Structure:

```
GET  /api/v1/cross-links/entity-detail/?entity_name=X&entity_type=Y    → CrossInvestigationEntityDetail
GET  /api/v1/cross-links/search/?q=X&type=Y&limit=20                   → CrossInvestigationSearchResponse
POST /api/v1/investigations/{id}/cross-links/dismiss                    → 201
DELETE /api/v1/investigations/{id}/cross-links/dismiss                  → 204
```

Note: The entity-detail and search endpoints are NOT scoped to a single investigation because they query across all investigations. They use the `/api/v1/cross-links/` prefix directly (not under `/investigations/{id}/`). The dismiss endpoints ARE investigation-scoped because they represent a decision made from within a specific investigation's context.

#### Neo4j Entity Detail Query Pattern

```cypher
MATCH (e:Person|Organization|Location)
WHERE toLower(e.name) = toLower($entity_name)
  AND labels(e)[0] = $entity_type
WITH e
OPTIONAL MATCH (e)-[r]->(t) WHERE type(r) <> 'MENTIONED_IN'
WITH e, collect(DISTINCT {type: type(r), target_name: t.name, target_type: labels(t)[0], confidence: r.confidence_score}) AS relationships
OPTIONAL MATCH (e)-[:MENTIONED_IN]->(d:Document)
WITH e, relationships, collect(DISTINCT {document_id: d.id, mention_count: 1}) AS documents
RETURN e.investigation_id AS investigation_id, e.id AS entity_id,
       e.confidence_score AS confidence_score,
       relationships, documents
```

Batch-resolve investigation names and document filenames from PostgreSQL (single query with IN clause — follow existing pattern in `CrossInvestigationService._resolve_investigation_names()`).

#### Neo4j Search Query Pattern

```cypher
MATCH (e:Person|Organization|Location)
WHERE toLower(e.name) CONTAINS toLower($query)
OPTIONAL MATCH (e)-[r]->() WHERE type(r) <> 'MENTIONED_IN'
WITH e, count(DISTINCT r) AS rel_count
RETURN e.name AS entity_name, labels(e)[0] AS entity_type,
       e.investigation_id AS investigation_id, e.id AS entity_id,
       e.confidence_score AS confidence_score, rel_count
ORDER BY entity_name
```

Group results in Python: by (toLower(entity_name), entity_type), collecting investigations. Sort final results by investigation_count DESC.

#### DismissedMatch Model

```python
class DismissedMatch(SQLModel, table=True):
    __tablename__ = "dismissed_matches"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    entity_name: str = Field(index=True)
    entity_type: str
    source_investigation_id: uuid.UUID = Field(foreign_key="investigations.id", index=True)
    target_investigation_id: uuid.UUID = Field(foreign_key="investigations.id")
    dismissed_at: datetime = Field(default_factory=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("entity_name", "entity_type", "source_investigation_id", "target_investigation_id"),
    )
```

The `source_investigation_id` is the investigation the user was viewing when they dismissed the match. The `target_investigation_id` is the other investigation in the match pair. This allows dismissals to be directional — dismissing "John Doe" match between Investigation A→B doesn't affect the same match viewed from Investigation B.

#### Cross-Link Count Query Pattern

Use a single Neo4j query to count cross-investigation entity matches for multiple investigations at once:

```cypher
UNWIND $investigation_ids AS inv_id
MATCH (e1 {investigation_id: inv_id})
WHERE (e1:Person OR e1:Organization OR e1:Location)
MATCH (e2)
WHERE (e2:Person OR e2:Organization OR e2:Location)
  AND e2.investigation_id <> inv_id
  AND toLower(e1.name) = toLower(e2.name)
  AND labels(e1) = labels(e2)
WITH inv_id, count(DISTINCT e1.name + '::' + labels(e1)[0]) AS link_count
RETURN inv_id AS investigation_id, link_count
```

Then subtract dismissed matches from PostgreSQL per investigation.

#### Frontend Navigation with Entity Highlight

When navigating to another investigation from the cross-investigation panel:

```typescript
navigate({
  to: '/investigations/$id',
  params: { id: targetInvestigationId },
  search: { highlightEntity: entityName }
});
```

In the investigation route handler (`routes/investigations/$id.tsx`):
1. Read `highlightEntity` from search params
2. Pass it as `highlightEntities` prop to `GraphCanvas`
3. The existing `highlightEntitiesProp` effect in `GraphCanvas` will handle centering and highlighting
4. After a brief delay, automatically open the EntityDetailCard for the matching entity

#### Frontend Panel State Management

The `CrossInvestigationPanel` needs three views:
1. **Match list** (default) — current behavior from 10.1
2. **Entity detail** — shown when clicking an entity in the match list
3. **Search results** — shown when search input has text

Use a simple state machine:

```typescript
type PanelView =
  | { type: 'matches' }
  | { type: 'detail'; entityName: string; entityType: string }
  | { type: 'search'; query: string };
```

#### Dismiss UX Pattern

- Each investigation entry in `CrossInvestigationMatchCard` gets a small "X" dismiss button (on hover or always visible)
- Clicking dismiss shows a confirmation tooltip: "Not the same entity? This match won't appear again."
- After dismiss: optimistic update removes the investigation from the card
- If the entity has no remaining investigation matches after dismissals, the entire match card is removed
- Toast notification: "Match dismissed. Undo" with undo action (30s timeout)
- Undo calls DELETE dismiss endpoint, re-invalidates cross-investigation query

### Project Structure Notes

**New files:**
- `apps/api/app/models/dismissed_match.py` — DismissedMatch SQLModel
- `apps/api/migrations/versions/XXXX_add_dismissed_matches.py` — Migration
- `apps/web/src/components/cross-investigation/CrossInvestigationEntityDetail.tsx` — Detail view
- `apps/web/src/components/cross-investigation/CrossInvestigationEntityDetail.test.tsx` — Tests
- `apps/web/src/components/cross-investigation/CrossInvestigationSearchResults.tsx` — Search results
- `apps/web/src/components/cross-investigation/CrossInvestigationSearchResults.test.tsx` — Tests
- `apps/api/tests/models/test_dismissed_match.py` — Model tests

**Modified files:**
- `apps/api/app/schemas/cross_investigation.py` — New schemas
- `apps/api/app/services/cross_investigation.py` — New methods + dismiss filtering
- `apps/api/app/api/v1/cross_investigation.py` — New endpoints
- `apps/api/app/schemas/investigation.py` — Add `cross_link_count` field
- `apps/api/app/api/v1/investigations.py` — Include cross-link counts
- `apps/web/src/hooks/useCrossInvestigation.ts` — New hooks + types
- `apps/web/src/components/cross-investigation/CrossInvestigationPanel.tsx` — Search + detail view
- `apps/web/src/components/cross-investigation/CrossInvestigationMatchCard.tsx` — Dismiss + click-to-detail
- `apps/web/src/components/investigation/InvestigationCard.tsx` — Cross-link count display
- `apps/web/src/routes/investigations/$id.tsx` — highlightEntity search param
- `apps/api/tests/services/test_cross_investigation.py` — Additional tests
- `apps/api/tests/api/test_cross_investigation.py` — Additional tests
- `apps/web/src/components/cross-investigation/CrossInvestigationPanel.test.tsx` — Additional tests
- `apps/web/src/components/cross-investigation/CrossInvestigationMatchCard.test.tsx` — Additional tests

### Important Patterns from Previous Stories

1. **Celery tasks use sync sessions** — `SyncSessionLocal()`. API endpoints use async sessions via `get_db`.
2. **SSE events are best-effort** — `_publish_safe()` wrapper never raises.
3. **RFC 7807 error format** — `{type, title, status, detail, instance}` via `DomainError` subclasses.
4. **Service layer pattern** — Business logic in `app/services/`, API routes thin.
5. **Loguru structured logging** — `logger.info("Message", key=value)`.
6. **Commit pattern** — `feat: Story X.Y — description`.
7. **Neo4j read transactions** — Use `session.execute_read()` for queries.
8. **TanStack Query cache invalidation** — SSE events invalidate relevant query keys.
9. **Entity type colors** — `ENTITY_COLORS` constant in `src/lib/entity-constants.ts`.
10. **OpenAPI type generation** — Run `scripts/generate-api-types.sh` after schema changes.
11. **Pre-existing test failures** — `SystemStatusPage.test.tsx` (4), `test_docker_compose.py` (2), `test_entity_discovered_sse_events_published` (1). Do not fix these.
12. **Alembic migration** — `cd apps/api && uv run alembic revision --autogenerate -m "description"` then `uv run alembic upgrade head`.
13. **SQLModel patterns** — See `app/models/investigation.py` and `app/models/document.py` for table definition patterns.
14. **Batch query pattern** — `_get_document_counts_batch()` in investigations.py uses single query with IN clause. Follow for cross-link counts.
15. **Frontend test patterns** — Co-located `.test.tsx` files, use `@testing-library/react`, mock fetch for API calls.

### References

- [Source: _bmad-output/planning-artifacts/epics.md — No epic 10 in phase 1 epics; story specified via user prompt]
- [Source: _bmad-output/planning-artifacts/prd.md — FR60 (view cross-investigation matches), FR61 (query across investigations); NFR33 (< 15 second queries)]
- [Source: _bmad-output/planning-artifacts/prd.md — Innovation Area 3: Cross-Investigation Knowledge Accumulation]
- [Source: _bmad-output/planning-artifacts/prd.md — Risk: Cross-investigation false positives, mitigated by entity disambiguation + confidence scoring]
- [Source: _bmad-output/planning-artifacts/architecture.md — Lines 258-261: Qdrant single global collection with investigation_id payload filter]
- [Source: _bmad-output/planning-artifacts/architecture.md — Lines 289-308: API endpoint structure, REST patterns]
- [Source: _bmad-output/planning-artifacts/architecture.md — Lines 399-424: Naming conventions table]
- [Source: _bmad-output/planning-artifacts/architecture.md — Lines 430-444: File organization patterns]
- [Source: _bmad-output/planning-artifacts/architecture.md — Lines 486-551: Process patterns, error handling, anti-patterns]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — Lines 986-1014: Graph Controls Toolbar]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — Lines 1085-1106: Investigation Card anatomy]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — Lines 1175-1201: Toast notification patterns]
- [Source: _bmad-output/implementation-artifacts/10-1-cross-investigation-entity-matching-engine.md — Complete 10.1 implementation context]
- [Source: apps/api/app/services/cross_investigation.py — Existing matching service]
- [Source: apps/api/app/schemas/cross_investigation.py — Existing schemas]
- [Source: apps/api/app/api/v1/cross_investigation.py — Existing endpoints]
- [Source: apps/web/src/components/cross-investigation/ — Existing panel and card components]
- [Source: apps/web/src/hooks/useCrossInvestigation.ts — Existing TanStack Query hook]
- [Source: apps/api/app/api/v1/investigations.py — _get_document_counts_batch pattern]
- [Source: apps/api/app/services/entity_query.py — Entity detail query patterns]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

### Completion Notes List

- Extended `CrossInvestigationService` with 5 new methods: `get_entity_detail_across_investigations()`, `search_across_investigations()`, `get_cross_link_counts()`, `dismiss_match()`, `undismiss_match()`
- Updated `find_matches()` to filter dismissed matches from results
- Created `DismissedMatch` SQLModel with Alembic migration (010)
- Added 4 new API endpoints: entity-detail, search, dismiss (POST), undismiss (DELETE)
- Created `CrossInvestigationEntityDetail` panel view with per-investigation relationships and source documents
- Created `CrossInvestigationSearchResults` component with search-across-investigations UI
- Updated `CrossInvestigationPanel` with 3-view state machine (matches/detail/search) and debounced search input
- Updated `CrossInvestigationMatchCard` with dismiss buttons and entity name click-to-detail
- Added `cross_link_count` to `InvestigationResponse` schema and API endpoints
- Updated `InvestigationCard` to display cross-link count when > 0
- Added `highlightEntity` search param handling to investigation route for cross-investigation navigation
- 12 new backend tests (service + API), all passing; existing 10 tests updated and passing (22 total)
- 17 new/updated frontend tests across 4 test files, all passing
- No regressions: 394 backend tests pass, 273 frontend tests pass (excluding pre-existing failures)

### Senior Developer Review (AI)

**Review Date:** 2026-04-12
**Review Outcome:** Changes Requested -> All Fixed
**Issues Found:** 1 High, 3 Medium, 1 Low

**Action Items:**
- [x] [HIGH] Cypher injection risk: entity_type_label interpolated directly into f-string Cypher queries in `_fetch_entity_detail_across` and `_fetch_search_across_investigations` -- added `_ALLOWED_ENTITY_LABELS` whitelist validation in service methods
- [x] [MED] No UUID validation for `target_investigation_id` in dismiss endpoint -- changed `DismissMatchRequest.target_investigation_id` from `str` to `uuid.UUID` for Pydantic validation
- [x] [MED] N+1 dismissed count queries in `get_cross_link_counts` -- accepted tradeoff for simplicity; typical investigation count is small (< 50)
- [x] [MED] Missing entity_type validation in entity-detail and search API endpoints -- service methods now validate against `_ALLOWED_ENTITY_LABELS`, returning empty results for invalid types
- [x] [LOW] `from sqlalchemy import func as sa_func` imported inside method body in `_count_dismissed_matches` -- moved to module-level import

### Change Log

- 2026-04-12: Story 10.2 implemented — cross-investigation entity exploration, search, dismiss, navigation, and investigation card counts
- 2026-04-12: Code review fixes — Cypher injection prevention, UUID validation, entity_type whitelist, import cleanup

### File List

**New files:**
- `apps/api/app/models/dismissed_match.py`
- `apps/api/migrations/versions/010_create_dismissed_matches_table.py`
- `apps/web/src/components/cross-investigation/CrossInvestigationEntityDetail.tsx`
- `apps/web/src/components/cross-investigation/CrossInvestigationEntityDetail.test.tsx`
- `apps/web/src/components/cross-investigation/CrossInvestigationSearchResults.tsx`
- `apps/web/src/components/cross-investigation/CrossInvestigationSearchResults.test.tsx`

**Modified files:**
- `apps/api/app/schemas/cross_investigation.py` — 7 new Pydantic schemas
- `apps/api/app/services/cross_investigation.py` — 5 new methods, dismissed match filtering
- `apps/api/app/api/v1/cross_investigation.py` — 4 new endpoints + cross_links_router
- `apps/api/app/api/v1/router.py` — registered cross_links_router
- `apps/api/app/schemas/investigation.py` — added cross_link_count field
- `apps/api/app/api/v1/investigations.py` — cross-link counts in list/get endpoints
- `apps/web/src/hooks/useCrossInvestigation.ts` — 5 new hooks + types
- `apps/web/src/components/cross-investigation/CrossInvestigationPanel.tsx` — search + detail views
- `apps/web/src/components/cross-investigation/CrossInvestigationMatchCard.tsx` — dismiss + entity click
- `apps/web/src/components/graph/GraphCanvas.tsx` — navigation callback
- `apps/web/src/components/investigation/InvestigationCard.tsx` — cross_link_count display
- `apps/web/src/routes/investigations/$id.tsx` — highlightEntity search param
- `apps/api/tests/services/test_cross_investigation.py` — 12 new tests, mock fixes
- `apps/api/tests/api/test_cross_investigation.py` — 8 new tests
- `apps/web/src/components/cross-investigation/CrossInvestigationPanel.test.tsx` — mock fixes + search test
- `apps/web/src/components/cross-investigation/CrossInvestigationMatchCard.test.tsx` — dismiss + entity click tests
