# Story 3.3: Provenance Chain & Evidence Storage

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an investigator,
I want every extracted fact to trace back to the exact document passage it came from,
So that I can verify any connection the system finds.

## Acceptance Criteria

1. GIVEN an entity is extracted and stored in Neo4j, WHEN `_store_in_neo4j` runs for a chunk, THEN a `Document` node is MERGE'd by `(id, investigation_id)`, AND a `MENTIONED_IN` edge is created from each entity node to the `Document` node with properties: `chunk_id` (str UUID), `page_start` (int), `page_end` (int), `text_excerpt` (str — first 500 chars of `chunk.text`), AND the MENTIONED_IN write is part of the same atomic transaction as entity and relationship writes.

2. GIVEN the API serves entity data, WHEN a client requests `GET /api/v1/investigations/{investigation_id}/entities/{entity_id}`, THEN the response includes entity properties (id, name, type, confidence_score, investigation_id), AND outgoing entity relationships (relation_type, target_id, target_name, target_type, confidence_score), AND a `sources` list with per-source: document_id, document_filename (from PostgreSQL), chunk_id, page_start, page_end, text_excerpt, AND a 404 is returned if the entity is not found or does not belong to the given investigation.

3. GIVEN an entity's `sources` are compiled, WHEN the API response is built, THEN `evidence_strength` is `"corroborated"` if the entity is mentioned in ≥ 2 distinct documents, AND `"single_source"` if mentioned in exactly 1 document, AND `"none"` if no sources are found.

## Tasks / Subtasks

- [x] **Task 1: Extend `_store_in_neo4j` with provenance edges** (`app/services/extraction.py`) (AC: 1)
  - [x] 1.1: Inside `_write_tx`, after all entity MERGEs, MERGE a `Document` node: `MERGE (d:Document {id: $doc_id, investigation_id: $inv_id})`
  - [x] 1.2: For each entity, MERGE a `MENTIONED_IN` edge: `MERGE (e:{label} {name: $name, investigation_id: $inv_id})-[m:MENTIONED_IN {chunk_id: $chunk_id}]->(d)` — `ON CREATE SET m.page_start = $page_start, m.page_end = $page_end, m.text_excerpt = $text_excerpt`
  - [x] 1.3: Add `Document` node uniqueness constraint to `ensure_neo4j_constraints`: `FOR (n:Document) REQUIRE (n.id, n.investigation_id) IS UNIQUE`
  - [x] 1.4: Add investigation_id index on `Document` nodes to `ensure_neo4j_constraints`
  - [x] 1.5: Add entity `id`-property index to `ensure_neo4j_constraints` for each label (`Person`, `Organization`, `Location`) — enables fast lookup by UUID in entity detail API
  - [x] 1.6: Update `tests/services/test_extraction.py` — verify `MENTIONED_IN` keyword appears in Cypher calls; verify Document node MERGE runs; verify no MENTIONED_IN written when no entities

- [x] **Task 2: Add `EntityNotFoundError` exception** (`app/exceptions.py`) (AC: 2)
  - [x] 2.1: Add `EntityNotFoundError(DomainError)` — `status_code=404`, `error_type="entity_not_found"`, default message `"No entity found with id: {entity_id}"`

- [x] **Task 3: Create Pydantic response schemas** (`app/schemas/entity.py`) (AC: 2, 3)
  - [x] 3.1: `EntityRelationship`: `relation_type: str`, `target_id: str | None`, `target_name: str | None`, `target_type: str | None`, `confidence_score: float`
  - [x] 3.2: `EntitySource`: `document_id: str`, `document_filename: str`, `chunk_id: str`, `page_start: int`, `page_end: int`, `text_excerpt: str`
  - [x] 3.3: `EntityDetailResponse`: `id: str`, `name: str`, `type: str`, `confidence_score: float`, `investigation_id: str`, `relationships: list[EntityRelationship]`, `sources: list[EntitySource]`, `evidence_strength: str`

- [x] **Task 4: Create `EntityQueryService`** (`app/services/entity_query.py`) (AC: 2, 3)
  - [x] 4.1: `EntityQueryService.__init__(self, neo4j_driver, db: AsyncSession)`
  - [x] 4.2: Implement `get_entity_detail(investigation_id: uuid.UUID, entity_id: str) -> EntityDetailResponse | None` — returns `None` if entity not found or investigation mismatch
  - [x] 4.3: Three-query Neo4j fetch via `session.execute_read`: (a) entity node by `id` + `investigation_id`, (b) outgoing WORKS_FOR/KNOWS/LOCATED_AT edges to `target` nodes, (c) MENTIONED_IN edges to Document nodes
  - [x] 4.4: Enrich sources with `document_filename` via single batch PostgreSQL SELECT: `SELECT id, filename FROM documents WHERE id IN [doc_ids]`
  - [x] 4.5: Compute `evidence_strength` from distinct `document_id` count in sources
  - [x] 4.6: Write unit tests `tests/services/test_entity_query.py` (see Testing Strategy section)

- [x] **Task 5: Create entities API router** (`app/api/v1/entities.py`) (AC: 2, 3)
  - [x] 5.1: Router with `prefix="/investigations"`, `tags=["entities"]`
  - [x] 5.2: `GET /{investigation_id}/entities/{entity_id}` — use `driver` from `app/db/neo4j.py` and `Depends(get_db)` for PostgreSQL; raise `EntityNotFoundError` if service returns `None`; return `EntityDetailResponse`
  - [x] 5.3: Write API tests `tests/api/test_entities.py`

- [x] **Task 6: Register entities router** (`app/api/v1/router.py`) (AC: 2)
  - [x] 6.1: Import `entities_router` from `app/api/v1/entities.py` and include in `v1_router`

## Dev Notes

### Provenance Data Model

**Neo4j graph after Story 3.3:**
```
(Person {id, name, type, confidence_score, investigation_id, created_at})
  -[:MENTIONED_IN {chunk_id, page_start, page_end, text_excerpt}]->
(Document {id, investigation_id})

(Person {name: "John Smith"})-[:WORKS_FOR {confidence_score, source_chunk_id}]->(Organization {name: "Acme Corp"})
```

`Document` nodes in Neo4j are lightweight provenance anchors — they hold only `id` and `investigation_id`. Full document metadata (filename, size, status) stays in PostgreSQL. The API joins the two.

**`DocumentChunk` fields available in `_store_in_neo4j`:**
- `chunk.id` → `chunk_id` on MENTIONED_IN edge
- `chunk.document_id` → Document node `id`
- `chunk.page_start` / `chunk.page_end` → stored on MENTIONED_IN edge
- `chunk.text[:500]` → `text_excerpt` on MENTIONED_IN edge
- `chunk.investigation_id` → not needed (investigation_id passed as parameter)

### Extending `_store_in_neo4j` (extraction.py)

The current `_write_tx` runs inside `session.execute_write(_write_tx)`. Extend it to add Document + MENTIONED_IN writes **after** entity MERGEs, **before** relationship MERGEs (entities must exist before MENTIONED_IN edges):

```python
def _write_tx(tx):
    # --- Existing: entity MERGEs ---
    for entity in entities:
        label = entity.type.value.capitalize()
        tx.run(f"MERGE (e:{label} {{...}}) ...", ...)

    # --- NEW: Document node + MENTIONED_IN edges ---
    tx.run(
        "MERGE (d:Document {id: $doc_id, investigation_id: $inv_id})",
        doc_id=str(chunk.document_id),
        inv_id=str(investigation_id),
    )
    for entity in entities:
        label = entity.type.value.capitalize()
        tx.run(
            f"MATCH (e:{label} {{name: $name, investigation_id: $inv_id}}) "
            "MATCH (d:Document {id: $doc_id, investigation_id: $inv_id}) "
            "MERGE (e)-[m:MENTIONED_IN {chunk_id: $chunk_id}]->(d) "
            "ON CREATE SET m.page_start = $page_start, m.page_end = $page_end, "
            "m.text_excerpt = $text_excerpt",
            name=entity.name,
            inv_id=str(investigation_id),
            doc_id=str(chunk.document_id),
            chunk_id=str(chunk.id),
            page_start=chunk.page_start,
            page_end=chunk.page_end,
            text_excerpt=chunk.text[:500],
        )

    # --- Existing: relationship MERGEs ---
    for rel in relationships:
        ...
```

Use `MATCH` (not `MERGE`) for entities in the MENTIONED_IN step because they were already `MERGE`'d earlier in the same transaction.

### `ensure_neo4j_constraints` Updates

Add to the loop in `ensure_neo4j_constraints`:
```python
# Document node constraint (new for Story 3.3)
session.run(
    "CREATE CONSTRAINT document_unique IF NOT EXISTS "
    "FOR (n:Document) REQUIRE (n.id, n.investigation_id) IS UNIQUE"
)
session.run(
    "CREATE INDEX document_investigation_idx IF NOT EXISTS "
    "FOR (n:Document) ON (n.investigation_id)"
)

# Entity id index for fast API lookup (new for Story 3.3)
for label in ("Person", "Organization", "Location"):
    session.run(
        f"CREATE INDEX entity_id_idx_{label.lower()} IF NOT EXISTS "
        f"FOR (n:{label}) ON (n.id)"
    )
```

`ensure_neo4j_constraints` run count will increase: +2 (Document) + 3 (entity id indexes) = 5 more calls (11 total). Update the test `test_constraints_created_for_all_labels` assertion: `assert mock_session.run.call_count == 11`.

### Neo4j Async Query Pattern (entity_query.py)

FastAPI routes are async → use `AsyncGraphDatabase.driver` from `app/db/neo4j.py`. Pattern:

```python
from app.db.neo4j import driver as neo4j_driver  # imported in router, injected into service

async with neo4j_driver.session() as session:
    record = await session.execute_read(_query_entity_fn, str(entity_id), str(investigation_id))
```

Three-query approach (simpler than one complex query with multiple OPTIONAL MATCH):
```python
async def _fetch_entity(tx, entity_id: str, investigation_id: str):
    result = await tx.run(
        "MATCH (e {id: $entity_id, investigation_id: $investigation_id}) "
        "RETURN e.id AS id, e.name AS name, labels(e)[0] AS type, "
        "e.confidence_score AS confidence_score",
        entity_id=entity_id, investigation_id=investigation_id,
    )
    return await result.single()

async def _fetch_relationships(tx, entity_id: str, investigation_id: str):
    result = await tx.run(
        "MATCH (e {id: $entity_id, investigation_id: $inv_id})"
        "-[r:WORKS_FOR|KNOWS|LOCATED_AT]->(t {investigation_id: $inv_id}) "
        "RETURN type(r) AS relation_type, t.id AS target_id, t.name AS target_name, "
        "labels(t)[0] AS target_type, r.confidence_score AS confidence_score",
        entity_id=entity_id, inv_id=investigation_id,
    )
    return await result.data()

async def _fetch_sources(tx, entity_id: str, investigation_id: str):
    result = await tx.run(
        "MATCH (e {id: $entity_id, investigation_id: $inv_id})"
        "-[m:MENTIONED_IN]->(d:Document {investigation_id: $inv_id}) "
        "RETURN d.id AS document_id, m.chunk_id AS chunk_id, "
        "m.page_start AS page_start, m.page_end AS page_end, m.text_excerpt AS text_excerpt",
        entity_id=entity_id, inv_id=investigation_id,
    )
    return await result.data()
```

Run all three inside a single `execute_read` transaction for consistency, or sequentially in three separate `execute_read` calls (either is fine since these are reads).

### PostgreSQL Batch Filename Lookup

```python
from sqlalchemy import select
from app.models.document import Document

doc_ids = list({s["document_id"] for s in sources_data})
result = await db.execute(
    select(Document.id, Document.filename).where(
        Document.id.in_([uuid.UUID(d) for d in doc_ids])
    )
)
filename_map: dict[str, str] = {str(row.id): row.filename for row in result}
```

### API Router Pattern

Follow existing `investigations.py` / `documents.py` conventions:

```python
# app/api/v1/entities.py
import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.neo4j import driver as neo4j_driver
from app.db.postgres import get_db
from app.exceptions import EntityNotFoundError
from app.schemas.entity import EntityDetailResponse
from app.services.entity_query import EntityQueryService

router = APIRouter(prefix="/investigations", tags=["entities"])

@router.get("/{investigation_id}/entities/{entity_id}", response_model=EntityDetailResponse)
async def get_entity_detail(
    investigation_id: uuid.UUID,
    entity_id: str,
    db: AsyncSession = Depends(get_db),
):
    service = EntityQueryService(neo4j_driver, db)
    result = await service.get_entity_detail(investigation_id, entity_id)
    if result is None:
        raise EntityNotFoundError(entity_id)
    return result
```

### Testing Strategy

**`tests/services/test_extraction.py` additions (Task 1.6):**
```python
def test_mentioned_in_edge_created_for_entity(mock_ollama, mock_neo4j_driver, sample_chunk, person_entity, investigation_id):
    """MENTIONED_IN edge is written for each entity stored in Neo4j."""
    service = EntityExtractionService(mock_ollama, mock_neo4j_driver)
    service._store_in_neo4j(sample_chunk, [person_entity], [], investigation_id)

    write_fn = mock_session.execute_write.call_args[0][0]
    mock_tx = MagicMock()
    write_fn(mock_tx)
    all_cypher = " ".join(call[0][0] for call in mock_tx.run.call_args_list)
    assert "MENTIONED_IN" in all_cypher
    assert "Document" in all_cypher

def test_document_node_merged(mock_ollama, mock_neo4j_driver, sample_chunk, person_entity, investigation_id):
    """Document node MERGE runs before MENTIONED_IN edge."""
    ...  # Verify "MERGE (d:Document" in cypher calls

def test_no_mentioned_in_when_no_entities(mock_ollama, mock_neo4j_driver, sample_chunk, investigation_id):
    """No Neo4j writes when no entities (including MENTIONED_IN)."""
    service = EntityExtractionService(mock_ollama, mock_neo4j_driver)
    service._store_in_neo4j(sample_chunk, [], [], investigation_id)
    mock_neo4j_driver.session.assert_not_called()
```

**`tests/services/test_entity_query.py` (Task 4.6) — mock both Neo4j and PostgreSQL:**
```python
@pytest.fixture
def mock_neo4j_driver():
    driver = MagicMock()
    mock_session = AsyncMock()
    driver.session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    driver.session.return_value.__aexit__ = AsyncMock(return_value=False)
    return driver, mock_session

def test_get_entity_detail_success(mock_neo4j_driver, mock_db):
    """Returns EntityDetailResponse when entity found."""
    ...

def test_get_entity_detail_not_found_returns_none(mock_neo4j_driver, mock_db):
    """Returns None when entity not found in Neo4j."""
    ...

def test_evidence_strength_corroborated(mock_neo4j_driver, mock_db):
    """2+ distinct documents → evidence_strength = 'corroborated'."""
    ...

def test_evidence_strength_single_source(mock_neo4j_driver, mock_db):
    """1 document → evidence_strength = 'single_source'."""
    ...

def test_evidence_strength_none_when_no_sources(mock_neo4j_driver, mock_db):
    """No MENTIONED_IN edges → evidence_strength = 'none'."""
    ...
```

**`tests/api/v1/test_entities.py` (Task 5.3):**
```python
def test_get_entity_detail_returns_200(mock_entity_query_svc):
    """GET /investigations/{id}/entities/{entity_id} returns 200 with payload."""
    ...

def test_get_entity_detail_not_found_returns_404(mock_entity_query_svc):
    """EntityNotFoundError → 404 response."""
    ...
```

Use `unittest.mock.AsyncMock` for all async Neo4j driver methods.

### Project Structure Notes

**New files:**
- `apps/api/app/schemas/entity.py` — Pydantic response schemas for entity detail
- `apps/api/app/services/entity_query.py` — EntityQueryService (async Neo4j + PostgreSQL)
- `apps/api/app/api/v1/entities.py` — API router for entity detail endpoint
- `apps/api/tests/services/test_entity_query.py` — unit tests for EntityQueryService
- `apps/api/tests/api/v1/test_entities.py` — API-level tests for entity endpoint

**Modified files:**
- `apps/api/app/services/extraction.py` — `_store_in_neo4j` extended + `ensure_neo4j_constraints` updated
- `apps/api/app/exceptions.py` — `EntityNotFoundError` added
- `apps/api/app/api/v1/router.py` — entities router registered
- `apps/api/tests/services/test_extraction.py` — 3 new tests; `test_constraints_created_for_all_labels` updated (count: 6 → 11)

**No new Alembic migration** — all schema changes are Neo4j Cypher constraints.
**No new Python packages** — `neo4j>=6.1.0` (async driver already used in Story 3.2); `sqlalchemy` async already in use.

**No chunk storage in Neo4j** — chunks remain PostgreSQL-only. The MENTIONED_IN edge carries the text excerpt inline to avoid cross-DB joins at query time.

### Alignment with Architecture

- Neo4j node labels: PascalCase (`Document`) ✓
- Neo4j relationship types: UPPER_SNAKE_CASE (`MENTIONED_IN`) ✓
- Neo4j properties: snake_case (`chunk_id`, `page_start`, `page_end`, `text_excerpt`) ✓
- API prefix: `/api/v1/investigations/{id}/entities/{entity_id}` ✓ per architecture spec
- Async Neo4j driver for FastAPI routes (`app/db/neo4j.py`) ✓
- Sync Neo4j driver only for Celery tasks (`app/db/sync_neo4j.py`) ✓
- Services: class-based, dependencies injected via `__init__` ✓

### References

- [Source: _bmad-output/planning-artifacts/epics.md — Epic 3, Story 3.3 acceptance criteria and user story]
- [Source: _bmad-output/planning-artifacts/architecture.md — Neo4j naming conventions: PascalCase labels, UPPER_SNAKE_CASE rel types, snake_case properties]
- [Source: _bmad-output/planning-artifacts/architecture.md — API spec: GET /api/v1/investigations/{id}/entities/{entity_id}]
- [Source: _bmad-output/planning-artifacts/architecture.md — MENTIONED_IN relationship type listed in Neo4j conventions]
- [Source: apps/api/app/services/extraction.py — _store_in_neo4j, _write_tx pattern, ensure_neo4j_constraints]
- [Source: apps/api/app/db/neo4j.py — AsyncGraphDatabase.driver for FastAPI async routes]
- [Source: apps/api/app/db/sync_neo4j.py — sync driver for Celery tasks only]
- [Source: apps/api/app/models/chunk.py — DocumentChunk fields: id, document_id, investigation_id, sequence_number, text, page_start, page_end]
- [Source: apps/api/app/models/document.py — Document fields: id, investigation_id, filename]
- [Source: apps/api/app/db/postgres.py — get_db() async dependency pattern]
- [Source: apps/api/app/api/v1/investigations.py — router prefix, Depends(get_db), service instantiation pattern]
- [Source: apps/api/app/exceptions.py — DomainError base class; DocumentNotFoundError as 404 pattern]
- [Source: _bmad-output/implementation-artifacts/3-2-entity-relationship-extraction-via-local-llm.md — ensure_neo4j_constraints pattern; session.execute_write(_write_tx) pattern; MERGE deduplication; mock_neo4j_driver fixture pattern]

### Previous Story Intelligence (Story 3.2 Learnings)

1. **`session.execute_write(_write_tx)` pattern** — all Neo4j writes for a chunk go in one transaction. Story 3.3 extends `_write_tx` to include Document MERGEs and MENTIONED_IN edges. Order matters: MERGE entities → MERGE Document → MERGE MENTIONED_IN edges → MERGE relationships.

2. **`entity_type_map`** already built in `_store_in_neo4j` as `{e.name: e.type.value.capitalize() for e in entities}`. Reuse this for the label in MENTIONED_IN MATCH clauses.

3. **`ensure_neo4j_constraints` run count** — current test asserts `call_count == 6` (3 constraints + 3 indexes). Story 3.3 adds 5 more calls (Document constraint, Document index, 3 entity-id indexes) → update assertion to `call_count == 11`. The idempotency test (`call_count == 12` per call) also needs updating → `call_count == 22`.

4. **AsyncMock for Neo4j async driver** — tests for `entity_query.py` require `AsyncMock` (not plain `MagicMock`) for coroutine methods. Use `from unittest.mock import AsyncMock`.

5. **Session rollback before failure commit** — if `_store_in_neo4j` raises (Neo4j down), the exception propagates to `process_document_task` which does `session.rollback()` before setting `document.status = "failed"`. No changes needed here — Story 3.2 already handles this correctly.

6. **Full test suite was 180 tests after Story 3.2 code review** — all must continue to pass.

### Git Intelligence

Recent commits:
- `2e3c3b0` — fix: increase Ollama inference timeout to 300s
- `bdcd567` — feat: Story 3.2 — entity & relationship extraction via local LLM
- `c587e45` — Add README.md
- `18279df` — feat: Story 3.1 — document chunking & LLM integration layer with code review fixes

**Patterns to continue:**
- Services: `class-based`, `__init__` takes dependencies (no global state)
- Tests: `tests/{category}/test_{module}.py` mirrors `app/{category}/{module}.py`
- Exceptions: all in `app/exceptions.py`, inherit from `DomainError`
- API schemas: separate `app/schemas/{resource}.py`, plain Pydantic `BaseModel`
- Routers: `prefix="/investigations"` (scoped under investigation for all entity/document endpoints)

## Dev Agent Record

### Agent Model Used

Claude Sonnet 4.6

### Debug Log References

None — implementation proceeded cleanly without debugging sessions.

### Completion Notes List

- Extended `_store_in_neo4j` with three-phase write transaction: (1) entity MERGEs, (2) Document node MERGE + MENTIONED_IN edge MERGEs, (3) relationship MERGEs. All within a single `session.execute_write` for atomicity per chunk.
- MENTIONED_IN edge keyed on `chunk_id` to allow multiple distinct chunks per entity-document pair. Stores `page_start`, `page_end`, `text_excerpt` (first 500 chars) inline on the edge.
- `ensure_neo4j_constraints` updated: +3 entity `id`-property indexes (fast API lookup) + Document uniqueness constraint + Document investigation_id index = 11 total calls (was 6).
- `EntityQueryService` uses three sequential `execute_read` calls (entity, relationships, sources) on async Neo4j driver + batch PostgreSQL `SELECT id, filename` for document enrichment.
- `evidence_strength` computed from distinct `document_id` count in MENTIONED_IN sources: "corroborated" (≥2), "single_source" (1), "none" (0).
- `GET /api/v1/investigations/{id}/entities/{entity_id}` returns 200 with `EntityDetailResponse` or 404 via `EntityNotFoundError`.
- Full test suite: 194 tests, 0 failures, 0 regressions. 14 new tests added (3 extraction + 7 entity_query + 4 entities API).

### File List

apps/api/app/services/extraction.py
apps/api/app/services/entity_query.py
apps/api/app/schemas/entity.py
apps/api/app/exceptions.py
apps/api/app/api/v1/entities.py
apps/api/app/api/v1/router.py
apps/api/tests/services/test_extraction.py
apps/api/tests/services/test_entity_query.py
apps/api/tests/api/test_entities.py
_bmad-output/implementation-artifacts/sprint-status.yaml

## Change Log

- 2026-03-10: Story 3.3 implementation complete — provenance chain via MENTIONED_IN edges (Entity → Document) written atomically per chunk; GET /api/v1/investigations/{id}/entities/{entity_id} endpoint with relationship + source enrichment and evidence_strength indicator. 14 new tests; 194 total, 0 regressions.
- 2026-03-11: Code review fixes — (H1) `_fetch_entity` changed to labeled MATCH `Person|Organization|Location` so entity id indexes are actually used and Document nodes can't be matched; (H2) `sample_chunk` fixture given explicit `document_id`/`page_start`/`page_end` values and `test_mentioned_in_edge_written_for_entity` now asserts AC1 parameter values on the MENTIONED_IN edge; (M3) duplicate 404 test replaced with 422 test for non-UUID `investigation_id`; (M4) Phase 2 Document MERGE guarded with `if entities:` to prevent orphan Document nodes; (M2) `sprint-status.yaml` added to File List. 194 tests, 0 failures.
