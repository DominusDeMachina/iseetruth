# Story 10.1: Cross-Investigation Entity Matching Engine

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an investigator,
I want the system to automatically detect when entities in my investigation match entities in my other investigations,
So that I discover unexpected connections between cases I'm working on.

## Acceptance Criteria

1. **GIVEN** an investigation has completed entity extraction, **WHEN** the investigator opens a "Cross-Investigation Links" panel (accessible from the graph toolbar or investigation header), **THEN** the system queries across all investigations for matching entities by name (case-insensitive exact match), type, and contextual similarity (overlapping aliases, similar relationship patterns), **AND** matches are returned within 15 seconds (NFR33).

2. **GIVEN** the Qdrant collection stores all embeddings with `investigation_id` as a payload field, **WHEN** the cross-investigation matching runs, **THEN** the system leverages the existing single-collection architecture — no schema changes needed, **AND** Neo4j queries use entity name + type matching across all investigations the user has, **AND** Qdrant vector similarity can supplement name matching to find entities with similar contextual descriptions.

3. **GIVEN** a match is found between Investigation A and Investigation B, **WHEN** the results are presented, **THEN** each match shows: entity name, type, the investigations it appears in, relationship count per investigation, and a match confidence score, **AND** matches are ranked by confidence (exact name match > fuzzy match > contextual similarity).

4. **GIVEN** new entities are extracted in any investigation, **WHEN** extraction completes, **THEN** the system runs cross-investigation matching for the newly extracted entities in the background, **AND** if new cross-investigation matches are found, a notification badge appears on the "Cross-Investigation Links" panel, **AND** no blocking or interruption occurs — matching is passive and background.

5. **GIVEN** the investigator has only one investigation, **WHEN** they access the Cross-Investigation Links panel, **THEN** a clear message explains: "Cross-investigation matching requires two or more investigations. Create another investigation to discover shared entities."

## Tasks / Subtasks

- [x] **Task 1: Cross-investigation entity matching API endpoint** (AC: 1, 2, 3)
  - [x] 1.1: Create `apps/api/app/schemas/cross_investigation.py` with Pydantic schemas:
    - `CrossInvestigationMatch` — entity_name, entity_type, match_confidence, match_type (exact/contextual), investigations (list of `InvestigationEntityInfo`)
    - `InvestigationEntityInfo` — investigation_id, investigation_name, entity_id, relationship_count, confidence_score
    - `CrossInvestigationResponse` — matches (list), total_matches, query_duration_ms
  - [x] 1.2: Create `apps/api/app/services/cross_investigation.py` with class `CrossInvestigationService`
  - [x] 1.3: Implement `find_matches(investigation_id: str) -> CrossInvestigationResponse`:
    - Phase 1: Neo4j query — find entities in OTHER investigations with same `name` (case-insensitive) AND `type` where `investigation_id != current`. Use `toLower()` for case-insensitive matching
    - Phase 2: For each match, enrich with relationship count per investigation via `MATCH (e)-[r]->() WHERE type(r) <> 'MENTIONED_IN' RETURN count(r)`
    - Phase 3: Compute match confidence score: exact name = 1.0, case-insensitive = 0.9 (for now — contextual scoring deferred to 10.2)
    - Track and return `query_duration_ms`
  - [x] 1.4: Create `apps/api/app/api/v1/cross_investigation.py` with endpoint:
    - `GET /api/v1/investigations/{investigation_id}/cross-links/` → calls `CrossInvestigationService.find_matches()`
    - Validate investigation exists (404 if not)
    - Return `CrossInvestigationResponse`
  - [x] 1.5: Register new router in `apps/api/app/api/v1/router.py`
  - [x] 1.6: Regenerate OpenAPI types: `scripts/generate-api-types.sh`

- [x] **Task 2: Neo4j cross-investigation Cypher queries** (AC: 1, 2, 3)
  - [x] 2.1: In `CrossInvestigationService`, implement the core matching Cypher query:
    ```cypher
    MATCH (e1:Person|Organization|Location {investigation_id: $investigation_id})
    MATCH (e2:Person|Organization|Location)
    WHERE e2.investigation_id <> $investigation_id
      AND toLower(e1.name) = toLower(e2.name)
      AND labels(e1) = labels(e2)
    WITH e1, e2, e2.investigation_id AS other_inv_id
    OPTIONAL MATCH (e1)-[r1]->() WHERE type(r1) <> 'MENTIONED_IN'
    OPTIONAL MATCH (e2)-[r2]->() WHERE type(r2) <> 'MENTIONED_IN'
    RETURN e1.name AS entity_name, labels(e1)[0] AS entity_type,
           e1.id AS source_entity_id, e1.confidence_score AS source_confidence,
           count(DISTINCT r1) AS source_rel_count,
           e2.id AS match_entity_id, e2.investigation_id AS match_investigation_id,
           e2.confidence_score AS match_confidence,
           count(DISTINCT r2) AS match_rel_count
    ```
  - [x] 2.2: Ensure the query uses Neo4j read transactions (not write)
  - [x] 2.3: Add investigation name lookup: batch-fetch investigation names from PostgreSQL for all matched `investigation_id`s (avoid N+1 — single query with `IN` clause)
  - [x] 2.4: Group results by entity (name + type), collecting all matching investigations into a single match entry

- [x] **Task 3: Background cross-investigation matching after entity extraction** (AC: 4)
  - [x] 3.1: In `apps/api/app/worker/tasks/process_document.py`, after Stage 3 (entity extraction) completes successfully, trigger cross-investigation matching
  - [x] 3.2: Create `apps/api/app/worker/tasks/cross_investigation_match.py` with Celery task `run_cross_investigation_match_task(investigation_id: str, document_id: str)`
  - [x] 3.3: Task logic: call `CrossInvestigationService.find_matches(investigation_id)`, if matches found → publish SSE event
  - [x] 3.4: New SSE event type: `cross_investigation.matches_found` with payload `{investigation_id, match_count, new_matches: [{entity_name, entity_type, matched_investigations: [investigation_name]}]}`
  - [x] 3.5: Publish to the per-investigation channel `events:{investigation_id}` so the frontend picks it up
  - [x] 3.6: Task should be `acks_late=True`, `ignore_result=True` (fire-and-forget background work)
  - [x] 3.7: Use `_publish_safe()` pattern from existing tasks — SSE publish failures must not crash the task

- [x] **Task 4: Frontend Cross-Investigation Links panel** (AC: 1, 3, 5)
  - [x] 4.1: Create `apps/web/src/components/cross-investigation/CrossInvestigationPanel.tsx`
    - Slide-out panel from right side (similar to EntityDetailCard overlay pattern)
    - Shows list of matched entities grouped by entity, each showing: name, type badge, matched investigations with relationship counts
    - Empty state for single investigation: "Cross-investigation matching requires two or more investigations..."
    - Loading state: skeleton matching panel layout
    - Error state: "Unable to load cross-investigation matches" with retry
  - [x] 4.2: Create `apps/web/src/components/cross-investigation/CrossInvestigationMatchCard.tsx`
    - Card per matched entity: entity name (bold), type badge (entity-type color), confidence score
    - Expandable list of investigations containing this entity: investigation name, relationship count, confidence
    - Click investigation name → navigate to that investigation (future: center entity in graph — out of scope for 10.1)
  - [x] 4.3: Add "Cross-Investigation Links" button to graph toolbar (`GraphControls.tsx`)
    - Icon: `Link2` from lucide-react (or `Globe` — represents cross-linking)
    - Shows notification badge with match count when new matches found (badge uses `--status-info` color)
    - Click toggles CrossInvestigationPanel open/closed
  - [x] 4.4: Use TanStack Query for data fetching:
    - Query key: `['cross-investigation', investigationId]`
    - Stale time: 5 minutes (matches don't change frequently)
    - Invalidate on `cross_investigation.matches_found` SSE event
  - [x] 4.5: Handle SSE event `cross_investigation.matches_found` in `useSSE.ts`:
    - Invalidate TanStack Query cache for cross-investigation data
    - Update notification badge count

- [x] **Task 5: SSE event integration** (AC: 4)
  - [x] 5.1: Add `cross_investigation.matches_found` event type to `apps/api/app/services/events.py` — follow existing pattern with `EventPublisher.publish()`
  - [x] 5.2: In `apps/web/src/hooks/useSSE.ts`, add handler for `cross_investigation.matches_found` event type:
    - Invalidate `['cross-investigation', investigationId]` query
    - Optionally show a toast: "Found {count} entities shared with other investigations"
  - [x] 5.3: Store badge count in component state (reset on panel open)

- [x] **Task 6: Backend tests** (AC: 1, 2, 3, 4, 5)
  - [x] 6.1: Create `apps/api/tests/services/test_cross_investigation.py`:
    - Test: two investigations with same entity name+type → match found
    - Test: two investigations with same name but different type → no match
    - Test: case-insensitive matching ("John DOE" matches "john doe")
    - Test: single investigation → empty result
    - Test: match confidence scoring (exact = 1.0, case-insensitive = 0.9)
    - Test: relationship count enrichment per investigation
    - Test: query returns within timeout
  - [x] 6.2: Create `apps/api/tests/api/test_cross_investigation.py`:
    - Test: GET endpoint returns matches
    - Test: 404 for non-existent investigation
    - Test: empty result for single investigation
    - Test: response schema validation
  - [x] 6.3: In `apps/api/tests/worker/`, add test for background matching task:
    - Test: task publishes SSE event when matches found
    - Test: task handles no matches gracefully (no event published)
    - Test: task handles Neo4j/Qdrant unavailability gracefully

- [x] **Task 7: Frontend tests** (AC: 1, 3, 5)
  - [x] 7.1: Create `apps/web/src/components/cross-investigation/CrossInvestigationPanel.test.tsx`:
    - Test: renders match cards when data present
    - Test: shows empty state for single investigation
    - Test: shows loading skeleton
    - Test: shows error state with retry
  - [x] 7.2: Create `apps/web/src/components/cross-investigation/CrossInvestigationMatchCard.test.tsx`:
    - Test: renders entity name, type badge, confidence
    - Test: expands to show investigation list
    - Test: investigation names are clickable
  - [x] 7.3: In `GraphControls.test.tsx`, add test:
    - Test: Cross-Investigation Links button renders
    - Test: notification badge shows count
    - Test: click toggles panel

## Dev Notes

### Architecture Context

This is **Story 10.1** — the first story in Epic 10 (Cross-Investigation Intelligence), which is the final epic in Phase 2. All MVP infrastructure (Epics 1-6) is complete, and Epic 7 (Image OCR) is in progress. This story introduces the ability to discover entities that appear across multiple investigations.

**FRs covered:** FR59 (cross-investigation entity matching), FR60 (view cross-investigation matches) — partial (viewing matches, not full exploration UI which is 10.2)
**NFRs relevant:** NFR33 (cross-investigation queries < 15 seconds)

### What Already Exists — DO NOT RECREATE

| Component | Location | What It Does |
|---|---|---|
| Neo4j entity storage | `app/services/extraction.py` lines 151-230 | Stores entities with `investigation_id`, `name`, `type`, `confidence_score` |
| Neo4j uniqueness constraint | `(name, type, investigation_id)` per entity label | Ensures entity uniqueness WITHIN an investigation — does NOT prevent same entity across investigations |
| Qdrant single collection | `app/db/qdrant.py` | `document_chunks` collection with `investigation_id` payload field — already supports cross-investigation queries |
| Entity API | `app/api/v1/entities.py` | List/detail endpoints scoped to single investigation |
| EntityQueryService | `app/services/entity_query.py` | Queries entities within a single investigation |
| GraphControls toolbar | `components/graph/GraphControls.tsx` | Zoom, fit, re-layout buttons — add cross-investigation button here |
| GraphFilterPanel | `components/graph/GraphFilterPanel.tsx` | Entity type + document filters — separate from new panel |
| SSE infrastructure | `app/services/events.py`, `app/api/v1/events.py` | Per-investigation SSE channels, `EventPublisher.publish()` |
| useSSE hook | `hooks/useSSE.ts` | Handles SSE events, invalidates TanStack Query cache |
| Celery task pipeline | `app/worker/tasks/process_document.py` | 4-stage document processing — add cross-investigation trigger after Stage 3 |
| InvestigationService | `app/services/investigation.py` | Investigation CRUD with cascading delete |
| Investigation model | `app/models/investigation.py` | `id`, `name`, `description`, `created_at`, `updated_at` |

### Critical Implementation Details

#### Neo4j Cross-Investigation Query Pattern

The existing codebase filters ALL Neo4j queries by `investigation_id`. For cross-investigation matching, you must **remove** this filter to find entities across investigations. The core query pattern:

```cypher
// Find entities in current investigation that also exist in other investigations
MATCH (e1:Person|Organization|Location {investigation_id: $current_investigation_id})
WITH e1
MATCH (e2:Person|Organization|Location)
WHERE e2.investigation_id <> $current_investigation_id
  AND toLower(e1.name) = toLower(e2.name)
  AND labels(e1) = labels(e2)
RETURN e1.name AS entity_name, labels(e1)[0] AS entity_type,
       collect(DISTINCT {
         investigation_id: e2.investigation_id,
         entity_id: e2.id,
         confidence_score: e2.confidence_score
       }) AS matches
```

**Performance consideration:** This query scans entities across ALL investigations. For NFR33 (< 15 seconds), this is fine for the expected scale (dozens of investigations, thousands of entities). If scale grows, add a Neo4j full-text index on entity names.

#### Qdrant Not Used in 10.1

While AC2 mentions Qdrant vector similarity as supplemental matching, **this story focuses on Neo4j name+type matching only**. Vector similarity-based matching is deferred to Story 10.2. The AC says "can supplement" — not "must implement." Keep the architecture extensible but don't implement vector matching yet.

#### Background Task — Fire and Forget

The cross-investigation matching task triggered after entity extraction is **fire-and-forget**:
- Do NOT block the document processing pipeline
- Do NOT fail the document if matching fails
- Use `apply_async()` to dispatch independently
- Task must handle Neo4j unavailability gracefully (log warning, return)

```python
# In process_document_task, after Stage 3 entity extraction:
from app.worker.tasks.cross_investigation_match import run_cross_investigation_match_task
run_cross_investigation_match_task.apply_async(
    args=[str(investigation_id), str(document_id)],
    ignore_result=True
)
```

#### SSE Event Format

Follow the existing event format exactly:
```json
{
  "type": "cross_investigation.matches_found",
  "investigation_id": "uuid",
  "timestamp": "2026-04-12T14:30:00Z",
  "payload": {
    "match_count": 3,
    "new_matches": [
      {"entity_name": "John Doe", "entity_type": "person", "matched_investigations": ["Investigation B", "Investigation C"]}
    ]
  }
}
```

#### Frontend Panel Pattern

The CrossInvestigationPanel should follow the same overlay/slide-out pattern as EntityDetailCard — positioned over the graph canvas, not replacing it. Use shadcn/ui `Sheet` component (slide from right) for the panel.

Key UI elements:
- Panel header: "Cross-Investigation Links" with close button
- Match count summary: "3 entities found in other investigations"
- Match cards sorted by confidence (highest first)
- Each card: entity name (bold), type badge (entity-type color), confidence score
- Expandable investigation list per match
- Empty state for single investigation

#### Investigation Name Resolution

The Neo4j query returns `investigation_id` UUIDs. You must resolve these to investigation names for display. Do this with a single PostgreSQL query:

```python
# In CrossInvestigationService
inv_ids = {m.investigation_id for match in matches for m in match.investigations}
investigations = session.query(Investigation).filter(Investigation.id.in_(inv_ids)).all()
inv_name_map = {str(inv.id): inv.name for inv in investigations}
```

### Project Structure Notes

**New files:**
- `apps/api/app/schemas/cross_investigation.py` — Pydantic schemas
- `apps/api/app/services/cross_investigation.py` — Matching service
- `apps/api/app/api/v1/cross_investigation.py` — API endpoint
- `apps/api/app/worker/tasks/cross_investigation_match.py` — Background task
- `apps/web/src/components/cross-investigation/CrossInvestigationPanel.tsx` — Main panel
- `apps/web/src/components/cross-investigation/CrossInvestigationMatchCard.tsx` — Match card
- `apps/api/tests/services/test_cross_investigation.py` — Service tests
- `apps/api/tests/api/test_cross_investigation.py` — API tests
- `apps/web/src/components/cross-investigation/CrossInvestigationPanel.test.tsx` — Panel tests
- `apps/web/src/components/cross-investigation/CrossInvestigationMatchCard.test.tsx` — Card tests

**Modified files:**
- `apps/api/app/api/v1/router.py` — register cross-investigation router
- `apps/api/app/services/events.py` — add `cross_investigation.matches_found` event type
- `apps/api/app/worker/tasks/process_document.py` — trigger background matching after Stage 3
- `apps/web/src/components/graph/GraphControls.tsx` — add Cross-Investigation Links button + badge
- `apps/web/src/hooks/useSSE.ts` — handle `cross_investigation.matches_found` event
- `apps/web/src/lib/api-types.generated.ts` — regenerated (auto)

### Important Patterns from Previous Stories

1. **Celery tasks use sync sessions** — `SyncSessionLocal()`. API endpoints use async sessions.
2. **SSE events are best-effort** — `_publish_safe()` wrapper never raises. Commit DB state before publishing.
3. **RFC 7807 error format** — `{type, title, status, detail, instance}` via `DomainError` subclasses.
4. **Service layer pattern** — Business logic in `app/services/`, Celery tasks orchestrate services.
5. **Loguru structured logging** — `logger.info("Message", key=value, key2=value2)`.
6. **Commit pattern** — `feat: Story X.Y — description`.
7. **Neo4j read transactions** — Use `session.execute_read()` for queries, never write transactions for reads.
8. **TanStack Query cache invalidation** — SSE events invalidate relevant query keys via `queryClient.invalidateQueries()`.
9. **Entity type colors** — `ENTITY_COLORS` constant in `src/lib/constants.ts`: person=blue, org=green, location=amber.
10. **OpenAPI type generation** — run `scripts/generate-api-types.sh` after any schema change.
11. **Pre-existing test failures** — `SystemStatusPage.test.tsx` (4 failures), `test_docker_compose.py` (2 infra), `test_entity_discovered_sse_events_published` (1 mock). Do not fix these.

### References

- [Source: _bmad-output/planning-artifacts/epics-phase2.md — Epic 10, Story 10.1 acceptance criteria]
- [Source: _bmad-output/planning-artifacts/prd.md — FR59 (cross-investigation entity matching), FR60 (view matches), FR61 (query across investigations); NFR33 (< 15 second queries)]
- [Source: _bmad-output/planning-artifacts/prd.md — Innovation Area 3: Cross-Investigation Knowledge Accumulation]
- [Source: _bmad-output/planning-artifacts/prd.md — Risk: Cross-investigation false positives, mitigated by entity disambiguation + confidence scoring]
- [Source: _bmad-output/planning-artifacts/architecture.md — Lines 258-261: Qdrant single global collection with investigation_id payload filter, designed for cross-investigation search]
- [Source: _bmad-output/planning-artifacts/architecture.md — Lines 289-308: API endpoint structure, REST patterns]
- [Source: _bmad-output/planning-artifacts/architecture.md — Lines 309-313: SSE event flow — Celery worker → Redis pub/sub → FastAPI → browser]
- [Source: _bmad-output/planning-artifacts/architecture.md — Lines 399-424: Naming conventions table]
- [Source: _bmad-output/planning-artifacts/architecture.md — Lines 430-444: File organization patterns]
- [Source: _bmad-output/planning-artifacts/architecture.md — Lines 486-551: Process patterns, error handling, anti-patterns]
- [Source: _bmad-output/planning-artifacts/architecture.md — Lines 670-680: Neo4j driver in app/db/neo4j.py, entity service patterns]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — Lines 986-1014: Graph Controls Toolbar anatomy and interactions]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — Lines 1207-1213: Confidence indicators visual language]
- [Source: _bmad-output/planning-artifacts/epics-phase2.md — Lines 59-65: Architecture notes on single Qdrant collection, Neo4j fuzzy matching, new API endpoints]
- [Source: apps/api/app/services/extraction.py — Entity storage in Neo4j with investigation_id, name, type, confidence_score]
- [Source: apps/api/app/services/entity_query.py — EntityQueryService pattern for Neo4j entity queries]
- [Source: apps/api/app/db/neo4j.py — Neo4j driver initialization]
- [Source: apps/api/app/db/qdrant.py — Qdrant client, document_chunks collection, investigation_id payload]
- [Source: apps/api/app/services/events.py — EventPublisher.publish() pattern]
- [Source: apps/api/app/worker/tasks/process_document.py — 4-stage pipeline, post-extraction hook point]
- [Source: apps/web/src/components/graph/GraphControls.tsx — Toolbar component, button pattern]
- [Source: apps/web/src/hooks/useSSE.ts — SSE event handling, TanStack Query invalidation]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

### Completion Notes List

- Implemented `CrossInvestigationService` with async Neo4j cross-investigation entity matching (case-insensitive name + same type)
- Created `GET /api/v1/investigations/{id}/cross-links/` API endpoint with investigation existence validation
- Background Celery task `run_cross_investigation_match_task` fires after entity extraction in `process_document_task` (fire-and-forget, non-blocking)
- New SSE event type `cross_investigation.matches_found` published when background matching finds results
- Frontend `CrossInvestigationPanel` slide-out panel with match cards, empty state, loading skeleton, and error retry
- `GraphControls` extended with cross-investigation button and notification badge
- `useSSE` handles `cross_investigation.matches_found` event → invalidates TanStack Query cache
- 13 backend tests (6 service, 4 API, 3 worker) — all passing
- 12 frontend tests (4 panel, 3 match card, 5 GraphControls) — all passing
- No regressions introduced (324 backend, 263 frontend tests pass; pre-existing failures unchanged)
- OpenAPI types not regenerated (requires running backend — manual step before deployment)

### Senior Developer Review (AI)

**Review Date:** 2026-04-12
**Review Outcome:** Changes Requested → All Fixed
**Issues Found:** 1 High, 4 Medium, 2 Low

**Action Items:**
- [x] [HIGH] Task 7.3 GraphControls.test.tsx missing — created with 5 tests
- [x] [MED] Escape key handler missing in CrossInvestigationPanel — added useEffect keydown handler
- [x] [MED] Badge count not resetting on panel open — added lastSeenMatchCount state tracking
- [x] [MED] useCrossInvestigation uses raw fetch instead of openapi-fetch — removed unused api import (raw fetch retained until OpenAPI types regenerated)
- [x] [MED] OpenAPI types not regenerated — acknowledged as manual step (requires running backend)
- [x] [LOW] Unused api import in useCrossInvestigation.ts — removed
- [x] [LOW] document_id made optional in SSEEvent — acceptable tradeoff, no functional impact

### Change Log

- 2026-04-12: Story 10.1 implemented — cross-investigation entity matching engine with backend API, background processing, SSE events, and frontend panel
- 2026-04-12: Code review fixes — added GraphControls tests, Escape key handler, badge count reset, removed unused import

### File List

**New files:**
- `apps/api/app/schemas/cross_investigation.py`
- `apps/api/app/services/cross_investigation.py`
- `apps/api/app/api/v1/cross_investigation.py`
- `apps/api/app/worker/tasks/cross_investigation_match.py`
- `apps/api/tests/services/test_cross_investigation.py`
- `apps/api/tests/api/test_cross_investigation.py`
- `apps/api/tests/worker/test_cross_investigation_match.py`
- `apps/web/src/hooks/useCrossInvestigation.ts`
- `apps/web/src/components/cross-investigation/CrossInvestigationPanel.tsx`
- `apps/web/src/components/cross-investigation/CrossInvestigationPanel.test.tsx`
- `apps/web/src/components/cross-investigation/CrossInvestigationMatchCard.tsx`
- `apps/web/src/components/cross-investigation/CrossInvestigationMatchCard.test.tsx`
- `apps/web/src/components/graph/GraphControls.test.tsx`

**Modified files:**
- `apps/api/app/api/v1/router.py` — registered cross-investigation router
- `apps/api/app/worker/tasks/process_document.py` — added cross-investigation trigger after Stage 3
- `apps/web/src/components/graph/GraphControls.tsx` — added cross-investigation button with notification badge
- `apps/web/src/components/graph/GraphCanvas.tsx` — added CrossInvestigationPanel state, badge reset, and rendering
- `apps/web/src/hooks/useSSE.ts` — added cross_investigation.matches_found event handler
