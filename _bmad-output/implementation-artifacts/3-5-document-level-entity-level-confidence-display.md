# Story 3.5: Document-Level & Entity-Level Confidence Display

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an investigator,
I want to see confidence indicators showing how well each document was processed and how reliable each entity is,
So that I know which results to trust and which documents to manually review.

## Acceptance Criteria

1. GIVEN documents have been processed with entity extraction, WHEN the investigator views the document list, THEN each document shows an extraction quality indicator (high/medium/low based on average entity confidence from its extracted entities), AND low-confidence documents are visually distinct (FR45).

2. GIVEN entities have been extracted with confidence scores, WHEN the investigator views entity information via the API, THEN each entity includes its confidence score (0.0–1.0), AND the API response from `GET /api/v1/investigations/{id}/entities/` includes `confidence_score` per entity (FR46), AND the response includes summary counts by entity type (people, organizations, locations).

3. GIVEN the processing dashboard is showing live updates, WHEN a document completes processing, THEN the confidence indicator appears on the document status card, AND the overall investigation summary updates entity counts by type (people, organizations, locations).

## Tasks / Subtasks

- [x] **Task 1: Alembic migration — add `entity_count` + `extraction_confidence` to documents** (AC: 1)
  - [x] 1.1: Create migration: `ALTER TABLE documents ADD COLUMN entity_count INTEGER NULL`
  - [x] 1.2: In same migration: `ALTER TABLE documents ADD COLUMN extraction_confidence FLOAT NULL`
  - [x] 1.3: Verify migration is reversible (`downgrade` drops both columns)

- [x] **Task 2: Update Document model + schema** (AC: 1, 3)
  - [x] 2.1: Add `entity_count: Mapped[int | None] = mapped_column(Integer, nullable=True)` to `Document` model
  - [x] 2.2: Add `extraction_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)` to `Document` model
  - [x] 2.3: Add `entity_count: int | None = None` and `extraction_confidence: float | None = None` to `DocumentResponse` schema
  - [x] 2.4: Add computed `extraction_quality: str | None` to `DocumentResponse` — a `@computed_field` or `@model_validator` that maps `extraction_confidence` to `"high"` (≥0.7), `"medium"` (≥0.4), `"low"` (<0.4), or `None` if `extraction_confidence is None`
  - [x] 2.5: Update `_to_response()` in `app/api/v1/documents.py` to pass the new fields

- [x] **Task 3: Update ExtractionSummary + extraction service** (AC: 1)
  - [x] 3.1: Add `average_confidence: float` field to `ExtractionSummary` dataclass (default `0.0`)
  - [x] 3.2: In `extract_from_chunks()`, collect each unique entity's confidence into a list; after loop, compute mean and store in `ExtractionSummary.average_confidence`

- [x] **Task 4: Store document confidence in process_document.py** (AC: 1, 3)
  - [x] 4.1: After entity extraction Stage 3 succeeds, set `document.entity_count = summary.entity_count` and `document.extraction_confidence = summary.average_confidence`
  - [x] 4.2: `session.commit()` to persist before Stage 4
  - [x] 4.3: Include `entity_count` and `extraction_confidence` in the `document.complete` SSE event payload

- [x] **Task 5: Create entity list endpoint schemas** (AC: 2)
  - [x] 5.1: Create `EntityListItem` in `app/schemas/entity.py`: `id: str`, `name: str`, `type: str`, `confidence_score: float`, `source_count: int`, `evidence_strength: str`
  - [x] 5.2: Create `EntityTypeSummary` in `app/schemas/entity.py`: `people: int`, `organizations: int`, `locations: int`, `total: int`
  - [x] 5.3: Create `EntityListResponse` in `app/schemas/entity.py`: `items: list[EntityListItem]`, `total: int`, `summary: EntityTypeSummary`

- [x] **Task 6: Add `list_entities` to EntityQueryService** (AC: 2)
  - [x] 6.1: Add `async def list_entities(self, investigation_id: uuid.UUID, entity_type: str | None = None, limit: int = 100, offset: int = 0) -> EntityListResponse`
  - [x] 6.2: Neo4j query: match all `Person|Organization|Location` nodes with `investigation_id`, return `id, name, type, confidence_score`, count MENTIONED_IN edges as `source_count`
  - [x] 6.3: Apply optional `entity_type` filter (lowercase match against label)
  - [x] 6.4: Compute `evidence_strength` per entity: `source_count >= 2` → `"corroborated"`, `== 1` → `"single_source"`, `== 0` → `"none"`
  - [x] 6.5: Compute `EntityTypeSummary` from full result set before pagination
  - [x] 6.6: Sort by `confidence_score DESC` by default, then apply `offset`/`limit`

- [x] **Task 7: Create entity list API endpoint** (AC: 2)
  - [x] 7.1: Add `GET /{investigation_id}/entities/` to `app/api/v1/entities.py`
  - [x] 7.2: Query params: `type: str | None = None`, `limit: int = Query(50, ge=1, le=200)`, `offset: int = Query(0, ge=0)`
  - [x] 7.3: Return `EntityListResponse`

- [x] **Task 8: Write backend tests** (AC: 1, 2)
  - [x] 8.1: `tests/api/test_entities_list.py` — test entity list endpoint returns entities with confidence_score, filtered by type, paged
  - [x] 8.2: `tests/services/test_entity_query_list.py` — test `list_entities()` with mock Neo4j: returns items with confidence, summary counts, evidence_strength, type filter, pagination
  - [x] 8.3: `tests/test_extraction_confidence.py` — test `ExtractionSummary.average_confidence` computed correctly; test with 0 entities returns 0.0
  - [x] 8.4: Add to existing document tests: verify `extraction_quality`, `entity_count`, `extraction_confidence` appear in document response

- [x] **Task 9: Regenerate OpenAPI types** (AC: 1, 2, 3)
  - [x] 9.1: Run `cd apps/api && uv run python -c "import app.main; import json; print(json.dumps(app.main.app.openapi()))" > /tmp/openapi.json` (or existing script)
  - [x] 9.2: Run `cd apps/web && pnpm openapi-typescript /tmp/openapi.json -o src/lib/api-types.generated.ts`

- [x] **Task 10: Create `useEntities` hook** (AC: 2, 3)
  - [x] 10.1: Create `apps/web/src/hooks/useEntities.ts`
  - [x] 10.2: Export types: `EntityListItem`, `EntityListResponse`, `EntityTypeSummary` from generated types
  - [x] 10.3: `useEntities(investigationId, typeFilter?)` — TanStack Query fetching `GET /api/v1/investigations/{id}/entities/`

- [x] **Task 11: Update DocumentCard with confidence indicator** (AC: 1, 3)
  - [x] 11.1: Add confidence badge next to status badge in `DocumentCard.tsx`
  - [x] 11.2: Badge renders only when `extraction_quality` is not null (document is complete with entities)
  - [x] 11.3: Styling per UX spec — high: `--status-success` border, medium: `--status-warning` dashed border, low: `--status-warning` + warning icon
  - [x] 11.4: Add entity count below file size: e.g., "12 entities"

- [x] **Task 12: Create EntitySummaryBar component** (AC: 2, 3)
  - [x] 12.1: Create `apps/web/src/components/investigation/EntitySummaryBar.tsx`
  - [x] 12.2: Shows entity type counts with colored dots: People (amber `--entity-person`), Organizations (green `--entity-org`), Locations (amber `--entity-location`)
  - [x] 12.3: Total entity count displayed

- [x] **Task 13: Update investigation page** (AC: 2, 3)
  - [x] 13.1: Import and use `useEntities` hook in `apps/web/src/routes/investigations/$id.tsx`
  - [x] 13.2: Add `EntitySummaryBar` between ProcessingDashboard and DocumentList
  - [x] 13.3: Only show EntitySummaryBar when there are completed documents

- [x] **Task 14: Update SSE handler to refresh entities** (AC: 3)
  - [x] 14.1: On `document.complete` SSE event, invalidate both `["documents", investigationId]` and `["entities", investigationId]` query caches
  - [x] 14.2: This ensures entity counts and document confidence update live

## Dev Notes

### Architecture Context

This story bridges **Epic 3** (backend extraction pipeline) and **Epic 4** (graph visualization). It surfaces confidence data that already exists in Neo4j but is not yet exposed through the document list API or entity list API.

**Pipeline completed by Story 3.4:**
```
Stage 1: extracting_text  → TextExtractionService (PyMuPDF)
Stage 2: chunking         → ChunkingService
Stage 3: extracting_entities → EntityExtractionService (Ollama qwen3.5:9b → Neo4j)
Stage 4: embedding        → EmbeddingService (Ollama qwen3-embedding:8b → Qdrant)
→ complete
```

**This story adds:** confidence metrics surfaced from Stage 3 to the API and frontend.

### What Already Exists (DO NOT recreate)

| Component | Location | What It Does |
|-----------|----------|-------------|
| Entity confidence generation | `app/llm/prompts.py` | LLM prompts explicitly request `confidence: float[0-1]` |
| Entity confidence storage | `app/services/extraction.py` `_store_in_neo4j()` | MERGE with max-boosting: `ON MATCH SET e.confidence_score = CASE WHEN $confidence > e.confidence_score THEN $confidence ELSE e.confidence_score END` |
| Entity detail endpoint | `app/api/v1/entities.py` | `GET /{investigation_id}/entities/{entity_id}` → `EntityDetailResponse` with `confidence_score` |
| Entity query service | `app/services/entity_query.py` | `get_entity_detail()` fetches confidence from Neo4j, computes `evidence_strength` |
| Entity schemas | `app/schemas/entity.py` | `EntityDetailResponse`, `EntityRelationship`, `EntitySource` — all have `confidence_score` |
| LLM extraction schemas | `app/llm/schemas.py` | `ExtractedEntity(confidence: float)`, `ExtractedRelationship(confidence: float)` |
| Extraction summary | `app/services/extraction.py` | `ExtractionSummary(entity_count, relationship_count, chunk_count)` |

### Document Confidence Computation Strategy

**Approach:** Compute and store at extraction time (not at query time).

After `EntityExtractionService.extract_from_chunks()` completes for a document, the `ExtractionSummary` will include `average_confidence`. The `process_document.py` task stores this on the `Document` row alongside `entity_count`.

**Quality tier mapping** (per UX spec confidence indicators):
| Threshold | Tier | Visual |
|-----------|------|--------|
| ≥ 0.7 | `"high"` | Solid `--status-success` border (default — no special marking) |
| ≥ 0.4, < 0.7 | `"medium"` | Dashed `--status-warning` border |
| < 0.4 | `"low"` | Dotted `--status-warning` border + warning icon |
| `None` | Not yet processed | No indicator |

**Why store, not compute:** Querying Neo4j for avg confidence per document on every document list request adds latency and cross-DB joins. The stored value reflects the document's own extraction quality at processing time — this is correct even as entity confidence evolves across documents (max-boosting reflects the entity's best evidence, not the document's extraction quality).

### Entity List Neo4j Query

```cypher
// Count + list entities for investigation
MATCH (e:Person|Organization|Location {investigation_id: $inv_id})
OPTIONAL MATCH (e)-[m:MENTIONED_IN]->(d:Document)
WITH e, labels(e)[0] AS type, e.confidence_score AS confidence_score,
     COUNT(DISTINCT d) AS source_count
RETURN e.id AS id, e.name AS name, type, confidence_score, source_count
ORDER BY confidence_score DESC
SKIP $offset LIMIT $limit
```

For the summary counts (separate query or pre-pagination aggregation):
```cypher
MATCH (e:Person|Organization|Location {investigation_id: $inv_id})
RETURN labels(e)[0] AS type, COUNT(e) AS count
```

### ExtractionSummary Enhancement

Current `ExtractionSummary`:
```python
@dataclass
class ExtractionSummary:
    entity_count: int
    relationship_count: int
    chunk_count: int
```

Add `average_confidence: float = 0.0`. In `extract_from_chunks()`, collect entity confidence values:
```python
# Track confidence for unique entities
entity_confidences: dict[tuple[str, str], float] = {}
for entity in entities:
    key = (entity.name, entity.type.value)
    existing = entity_confidences.get(key, 0.0)
    entity_confidences[key] = max(existing, entity.confidence)

avg_confidence = (sum(entity_confidences.values()) / len(entity_confidences)) if entity_confidences else 0.0
```

### process_document.py Stage 3 Update

After `extraction_service.extract_from_chunks()` succeeds, add:
```python
document.entity_count = summary.entity_count
document.extraction_confidence = summary.average_confidence
session.commit()
```

Also add `entity_count` and `extraction_confidence` to the `document.complete` event payload:
```python
_publish_safe(
    "document.complete",
    {
        "document_id": document_id,
        "entity_count": summary.entity_count,
        "relationship_count": summary.relationship_count,
        "embedded_count": emb_summary.embedded_count,
        "extraction_confidence": summary.average_confidence,
    },
)
```

### DocumentResponse Schema Enhancement

Add computed `extraction_quality` via Pydantic:
```python
from pydantic import computed_field

class DocumentResponse(BaseModel):
    # ... existing fields ...
    entity_count: int | None = None
    extraction_confidence: float | None = None

    @computed_field
    @property
    def extraction_quality(self) -> str | None:
        if self.extraction_confidence is None:
            return None
        if self.extraction_confidence >= 0.7:
            return "high"
        if self.extraction_confidence >= 0.4:
            return "medium"
        return "low"
```

Update `_to_response()` in `documents.py`:
```python
def _to_response(document, include_text: bool = False) -> DocumentResponse:
    return DocumentResponse(
        # ... existing fields ...
        entity_count=document.entity_count,
        extraction_confidence=document.extraction_confidence,
    )
```

### Frontend Confidence Badge Implementation

In `DocumentCard.tsx`, add after the status Badge:
```tsx
{document.extraction_quality && (
  <Badge
    variant="outline"
    className={qualityStyles[document.extraction_quality]}
  >
    {document.extraction_quality === "low" && <AlertTriangle className="size-3 mr-1" />}
    {document.extraction_quality.charAt(0).toUpperCase() + document.extraction_quality.slice(1)} confidence
  </Badge>
)}
```

Quality styles:
```typescript
const qualityStyles: Record<string, string> = {
  high: "bg-[var(--status-success)]/15 text-[var(--status-success)] border-[var(--status-success)]/30",
  medium: "bg-[var(--status-warning)]/15 text-[var(--status-warning)] border-[var(--status-warning)]/30 border-dashed",
  low: "bg-[var(--status-warning)]/15 text-[var(--status-warning)] border-[var(--status-warning)]/30 border-dotted",
};
```

### EntitySummaryBar Component

A compact horizontal bar showing entity type counts:
```tsx
// EntitySummaryBar.tsx
<div className="flex items-center gap-4 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-4 py-2">
  <span className="text-sm font-medium text-[var(--text-primary)]">
    {summary.total} entities
  </span>
  <div className="flex items-center gap-3 text-xs text-[var(--text-muted)]">
    <span className="flex items-center gap-1">
      <span className="size-2 rounded-full bg-[var(--entity-person)]" />
      {summary.people} people
    </span>
    <span className="flex items-center gap-1">
      <span className="size-2 rounded-full bg-[var(--entity-org)]" />
      {summary.organizations} orgs
    </span>
    <span className="flex items-center gap-1">
      <span className="size-2 rounded-full bg-[var(--entity-location)]" />
      {summary.locations} locations
    </span>
  </div>
</div>
```

### SSE Event Cache Invalidation

In `useSSE.ts` (or wherever SSE events are handled), on `document.complete`:
```typescript
queryClient.invalidateQueries({ queryKey: ["documents", investigationId] });
queryClient.invalidateQueries({ queryKey: ["entities", investigationId] });
```

### Testing Strategy

**Backend tests (pytest, mocked Neo4j/DB):**
1. Entity list endpoint: mock Neo4j returns entities, verify response shape, confidence scores, type filter, pagination, summary counts
2. ExtractionSummary: verify `average_confidence` computed from entity confidences across chunks
3. DocumentResponse: verify `extraction_quality` computed field returns correct tier for each threshold

**Frontend tests (Vitest):**
1. DocumentCard: renders confidence badge for each quality tier, no badge when null
2. EntitySummaryBar: renders correct counts per type
3. useEntities hook: mocked fetch returns expected data

### Project Structure Notes

**New files:**
- `apps/api/alembic/versions/XXXX_add_document_confidence.py` — migration
- `apps/api/tests/api/test_entities_list.py` — endpoint tests
- `apps/api/tests/services/test_entity_query_list.py` — service tests
- `apps/web/src/hooks/useEntities.ts` — TanStack Query hook
- `apps/web/src/components/investigation/EntitySummaryBar.tsx` — entity counts display

**Modified files:**
- `apps/api/app/models/document.py` — add `entity_count`, `extraction_confidence` columns
- `apps/api/app/schemas/document.py` — add fields + computed `extraction_quality`
- `apps/api/app/schemas/entity.py` — add `EntityListItem`, `EntityTypeSummary`, `EntityListResponse`
- `apps/api/app/api/v1/entities.py` — add list endpoint
- `apps/api/app/api/v1/documents.py` — update `_to_response()` to include new fields
- `apps/api/app/services/entity_query.py` — add `list_entities()` method
- `apps/api/app/services/extraction.py` — add `average_confidence` to `ExtractionSummary`, compute in `extract_from_chunks()`
- `apps/api/app/worker/tasks/process_document.py` — store entity_count + extraction_confidence after Stage 3
- `apps/web/src/components/investigation/DocumentCard.tsx` — add confidence badge + entity count
- `apps/web/src/components/investigation/ProcessingDashboard.tsx` — optionally add entity summary
- `apps/web/src/routes/investigations/$id.tsx` — add EntitySummaryBar, useEntities
- `apps/web/src/hooks/useSSE.ts` — invalidate entities cache on document.complete
- `apps/web/src/lib/api-types.generated.ts` — regenerated

**No new Python packages needed.** All dependencies (SQLAlchemy Float, Pydantic computed_field) are already available.

### References

- [Source: _bmad-output/planning-artifacts/epics.md — Epic 3, Story 3.5 acceptance criteria: document confidence indicators, entity confidence API, live processing updates]
- [Source: _bmad-output/planning-artifacts/architecture.md — FR45-FR47 mapping: confidence computed in extraction.py, stored in Neo4j, exposed via entity/graph schemas, frontend in EntityDetailCard.tsx]
- [Source: _bmad-output/planning-artifacts/architecture.md — API endpoints: GET /api/v1/investigations/{id}/entities/ for entity list, GET /api/v1/investigations/{id}/entities/{entity_id} for detail]
- [Source: _bmad-output/planning-artifacts/architecture.md — Naming conventions: Neo4j properties = snake_case (confidence_score), PostgreSQL columns = snake_case]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — Confidence indicators: high (solid/success), medium (dashed/warning), low (dotted/warning+icon); entity type colors: person=#d4956a, org=#7dab8f, location=#c4a265]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — Entity Detail Card anatomy: name, type badge, confidence indicator, relationships, sources]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — Processing Dashboard: per-document status cards with confidence after processing]
- [Source: apps/api/app/services/extraction.py — ExtractionSummary dataclass, extract_from_chunks() with seen_entities tracking, _store_in_neo4j() max-boosting confidence logic]
- [Source: apps/api/app/schemas/entity.py — EntityDetailResponse already includes confidence_score field]
- [Source: apps/api/app/services/entity_query.py — _fetch_entity returns confidence_score, _fetch_relationships returns confidence_score, evidence_strength computation logic]
- [Source: apps/api/app/models/document.py — Document model: status String(20), no confidence fields yet; uses SQLAlchemy mapped_column pattern]
- [Source: apps/api/app/api/v1/documents.py — _to_response() helper maps Document model to DocumentResponse]
- [Source: apps/web/src/components/investigation/DocumentCard.tsx — status badge pattern with statusStyles/statusLabels maps; Badge component from shadcn/ui]
- [Source: apps/web/src/hooks/useDocuments.ts — TanStack Query pattern: useQuery with queryKey, queryFn using openapi-fetch api.GET]
- [Source: apps/web/src/lib/api-client.ts — openapi-fetch createClient with generated types]

### Previous Story Intelligence (Story 3.4 Learnings)

1. **Class-based services with injected dependencies** — `EntityQueryService(neo4j_driver, db)` pattern. New `list_entities()` follows the same pattern.

2. **Celery uses sync drivers** — `process_document.py` uses sync Neo4j and sync SQLAlchemy sessions. Document model updates (`entity_count`, `extraction_confidence`) use `session.commit()` directly (no async).

3. **ExtractionSummary is a dataclass** — Add `average_confidence: float = 0.0` as a new field with a default to preserve backward compatibility with any callers.

4. **Tests at 200 after Story 3.4** — All must continue to pass.

5. **Document status `String(20)`** — No status change needed; confidence is stored in separate columns.

6. **Alembic migration pattern** — Previous migrations exist in `apps/api/alembic/versions/`. Follow the auto-generated pattern with explicit `op.add_column` / `op.drop_column`.

7. **Frontend type regeneration** — After backend schema changes, run `pnpm openapi-typescript` to regenerate `api-types.generated.ts`. The `useDocuments` hook reads types from `components["schemas"]["DocumentResponse"]` — new fields appear automatically after regeneration.

8. **SSE cache invalidation** — Story 2.4 established the SSE → TanStack Query invalidation pattern in `useSSE.ts`. Add `entities` invalidation alongside existing `documents` invalidation on `document.complete` event.

### Git Intelligence

Recent commits:
- `ba02706` — fix: make Qdrant/Neo4j clients fork-safe for Celery prefork workers
- `c9cbaf2` — chore: add dev data reset script
- `1e10443` — feat: Story 3.4 — vector embedding generation & storage
- `56f8359` — feat: Story 3.3 — provenance chain evidence storage

**Patterns to continue:**
- Services: class-based with injected deps
- Tests mirror source paths: `tests/services/test_entity_query_list.py` ↔ `app/services/entity_query.py`
- Schemas: Pydantic BaseModel, `from_attributes = True` for ORM models
- API router: prefix pattern from existing entities.py and documents.py
- Frontend: TanStack Query hooks with `queryKey` array pattern, shadcn/ui Badge component

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

None — clean implementation with no blocking issues.

### Completion Notes List

- Alembic migration 005 adds `entity_count` (Integer, nullable) and `extraction_confidence` (Float, nullable) to documents table; verified reversible.
- Document model and schema updated with new columns + computed `extraction_quality` field (high/medium/low/null).
- ExtractionSummary enhanced with `average_confidence` field; computed using max confidence per unique entity across chunks.
- process_document.py persists entity_count and extraction_confidence on the Document row after Stage 3, and includes extraction_confidence in document.complete SSE event.
- New entity list schemas: EntityListItem, EntityTypeSummary, EntityListResponse.
- EntityQueryService.list_entities() queries Neo4j for entities with source counts, computes evidence_strength, returns paginated results sorted by confidence DESC with type summary.
- New GET /{investigation_id}/entities/ endpoint with type filter and pagination.
- 26 new backend tests (226 total, all pass). 76 frontend tests all pass. Post-review: 229 backend, 85 frontend.
- OpenAPI types regenerated. useEntities hook created with TanStack Query.
- DocumentCard shows confidence badge (high/medium/low styling) and entity count.
- EntitySummaryBar shows entity type breakdown with colored dots.
- Investigation page includes EntitySummaryBar between ProcessingDashboard and DocumentList.
- SSE handler invalidates both documents and entities caches on document.complete.

### Change Log

- 2026-03-12: Story 3.5 implemented — document-level & entity-level confidence display (all 14 tasks, all 3 ACs)
- 2026-03-12: Code review fixes — [H1] Cypher injection: added entity type whitelist validation in entities.py, [H2] added 7 DocumentCard confidence badge tests, [M1] added useSSE entities cache invalidation test, [M2] added EntitySummaryBar integration tests, [M3] fixed SSEEvent TypeScript interface to include entity.discovered and full payload types, [L2] fixed blank line in document schema

### File List

**New files:**
- apps/api/migrations/versions/005_add_document_confidence_columns.py
- apps/api/tests/api/test_entities_list.py
- apps/api/tests/services/test_entity_query_list.py
- apps/api/tests/test_extraction_confidence.py
- apps/web/src/hooks/useEntities.ts
- apps/web/src/components/investigation/EntitySummaryBar.tsx

**Modified files:**
- apps/api/app/models/document.py
- apps/api/app/schemas/document.py
- apps/api/app/schemas/entity.py
- apps/api/app/api/v1/documents.py
- apps/api/app/api/v1/entities.py
- apps/api/app/services/extraction.py
- apps/api/app/services/entity_query.py
- apps/api/app/worker/tasks/process_document.py
- apps/api/tests/conftest.py
- apps/web/src/components/investigation/DocumentCard.tsx
- apps/web/src/components/investigation/DocumentCard.test.tsx
- apps/web/src/components/investigation/DocumentList.test.tsx
- apps/web/src/components/investigation/ProcessingDashboard.test.tsx
- apps/web/src/hooks/useSSE.ts
- apps/web/src/hooks/useSSE.test.ts
- apps/web/src/routes/investigations/$id.tsx
- apps/web/src/routes/investigations/-$id.test.tsx
- apps/web/src/lib/api-types.generated.ts
