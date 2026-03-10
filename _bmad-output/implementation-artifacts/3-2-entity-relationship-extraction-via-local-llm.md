# Story 3.2: Entity & Relationship Extraction via Local LLM

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an investigator,
I want the system to automatically find people, organizations, and locations in my documents and detect how they're connected,
So that I don't have to manually read every document to map relationships.

## Acceptance Criteria

1. GIVEN document chunks exist from Story 3.1, WHEN the Celery worker runs entity extraction on each chunk, THEN people, organizations, and locations are extracted using Ollama qwen3.5:9b, AND relationships are detected between co-occurring entities (WORKS_FOR, KNOWS, LOCATED_AT), AND each entity and relationship is assigned a confidence score (0.0–1.0), AND the document status transitions through an `extracting_entities` stage, AND `entity.discovered` SSE events are published as new entities are found.

2. GIVEN entities are extracted from a chunk, WHEN they are stored in Neo4j, THEN nodes are created with labels: Person, Organization, Location (PascalCase), AND relationship edges use types: WORKS_FOR, KNOWS, LOCATED_AT (UPPER_SNAKE_CASE), AND all node and relationship properties use snake_case, AND each entity node stores: id (UUID), name, type, confidence_score, investigation_id, AND each relationship stores: confidence_score, source_chunk_id, AND all Neo4j writes are atomic per chunk — no partially-written entities.

3. GIVEN the same entity name+type appears across multiple chunks or documents in the same investigation, WHEN the extraction pipeline encounters the entity again, THEN the existing Neo4j node is reused via MERGE on (name, type, investigation_id), AND the entity's confidence_score is updated to the higher of the existing vs. new score, AND no duplicate nodes are created.

4. GIVEN extraction produces results, WHEN processing completes, THEN the `document.complete` SSE event includes entity_count and relationship_count, AND entities are surfaced in real-time via `entity.discovered` events as each chunk is processed (FR34).

## Tasks / Subtasks

- [x] **Task 1: Add relationship extraction schemas** (`app/llm/schemas.py`) (AC: 1)
  - [x] 1.1: Add `RelationType` enum: WORKS_FOR, KNOWS, LOCATED_AT
  - [x] 1.2: Add `ExtractedRelationship` model: `source_entity_name` (str), `target_entity_name` (str), `relation_type` (RelationType), `confidence` (float, ge=0.0, le=1.0)
  - [x] 1.3: Add `RelationshipExtractionResponse` model: `relationships: list[ExtractedRelationship]`
  - [x] 1.4: Extend tests in `tests/llm/test_prompts.py` to validate new schemas

- [x] **Task 2: Add relationship extraction prompts** (`app/llm/prompts.py`) (AC: 1)
  - [x] 2.1: Add `RELATIONSHIP_EXTRACTION_SYSTEM_PROMPT` — instructs LLM to detect relationships between provided named entities, returning only WORKS_FOR, KNOWS, or LOCATED_AT types with confidence scores
  - [x] 2.2: Add `RELATIONSHIP_EXTRACTION_USER_PROMPT_TEMPLATE` — template accepting `{chunk_text}` and `{entities_json}` (JSON array of entity objects with name+type), returns `{"relationships": [...]}`
  - [x] 2.3: Add tests to `tests/llm/test_prompts.py`: prompt templates non-empty, `{chunk_text}` and `{entities_json}` variables present, `RelationshipExtractionResponse` validates correct JSON, rejects malformed JSON

- [x] **Task 3: Create sync Neo4j driver** (`app/db/sync_neo4j.py`) (AC: 2)
  - [x] 3.1: Create `app/db/sync_neo4j.py` using `neo4j.GraphDatabase.driver()` (sync, NOT `AsyncGraphDatabase`) — mirrors `sync_postgres.py` pattern for Celery task use
  - [x] 3.2: Export `sync_neo4j_driver` using same `settings.neo4j_uri` and parsed `settings.neo4j_auth` as the async driver in `app/db/neo4j.py`

- [x] **Task 4: Create `EntityExtractionService`** (`app/services/extraction.py`) (AC: 1, 2, 3, 4)
  - [x] 4.1: Create `ExtractionSummary` dataclass: `entity_count: int`, `relationship_count: int`, `chunk_count: int`
  - [x] 4.2: Create `EntityExtractionService.__init__(self, ollama_client: OllamaClient, neo4j_driver)`
  - [x] 4.3: Implement `extract_from_chunks(chunks: list[DocumentChunk], investigation_id: UUID, on_entity_discovered: Callable | None = None) -> ExtractionSummary`
  - [x] 4.4: Implement `_extract_entities(chunk: DocumentChunk) -> list[ExtractedEntity]`
  - [x] 4.5: Implement `_extract_relationships(chunk: DocumentChunk, entities: list[ExtractedEntity]) -> list[ExtractedRelationship]`
  - [x] 4.6: Implement `_store_in_neo4j(chunk, entities, relationships, investigation_id) -> None`
  - [x] 4.7: Implement module-level `ensure_neo4j_constraints(driver) -> None`
  - [x] 4.8: Write unit tests `tests/services/test_extraction.py` (21 tests covering all scenarios)

- [x] **Task 5: Add `EntityExtractionError` exception** (`app/exceptions.py`) (AC: 1)
  - [x] 5.1: Add `EntityExtractionError(DomainError)` — `status_code=422`, `error_type="entity_extraction_failed"`

- [x] **Task 6: Add Neo4j constraint setup to FastAPI startup** (`app/main.py`) (AC: 2)
  - [x] 6.1: Import `ensure_neo4j_constraints` from `app/services/extraction.py` and `sync_neo4j_driver` from `app/db/sync_neo4j.py`
  - [x] 6.2: In the `lifespan` startup block (after Alembic migrations): call `await asyncio.to_thread(ensure_neo4j_constraints, sync_neo4j_driver)` and log completion

- [x] **Task 7: Integrate extraction into `process_document_task`** (`app/worker/tasks/process_document.py`) (AC: 1, 4)
  - [x] 7.1: Import `EntityExtractionService`, `sync_neo4j_driver` from their new modules
  - [x] 7.2: Remove the early `document.complete` event at the end of the chunking stage
  - [x] 7.3: After chunking succeeds: set `document.status = "extracting_entities"`, commit, publish `document.processing` with `{stage: "extracting_entities", chunk_count, progress: 0.0}`
  - [x] 7.4: Create `EntityExtractionService(ollama_client, sync_neo4j_driver)` and define `on_entity_discovered` callback that publishes `entity.discovered` SSE event
  - [x] 7.5: Call `service.extract_from_chunks(...)` wrapped in try/except, on failure set status to `failed` and publish `document.failed`
  - [x] 7.6: On success: set `document.status = "complete"`, commit, publish `document.complete` with `{document_id, entity_count, relationship_count}`
  - [x] 7.7: Update integration tests in `tests/worker/test_process_document.py` (all 4 new tests added)

## Dev Notes

### Pipeline Stage Update

This story extends the document processing pipeline. Current state after Story 3.1:
```
queued → extracting_text → chunking → complete (or failed)
```

After this story:
```
queued → extracting_text → chunking → extracting_entities → complete (or failed)
```

Story 3.4 will extend further:
```
queued → extracting_text → chunking → extracting_entities → embedding → complete
```

The `document.complete` SSE event currently fires at the end of chunking (from Story 3.1's task 5). **Remove that early `document.complete` event** and move it to after extraction completes. The updated event payload must include `entity_count` and `relationship_count` per the architecture spec.

### Two-Phase LLM Extraction Per Chunk

Each chunk requires two Ollama calls:
1. **Entity extraction** (existing prompts): extract Person/Organization/Location entities
2. **Relationship extraction** (new prompts): given the entity list, detect relationships

The second call is conditioned on `len(entities) >= 2` — no entities or a single entity cannot form a relationship. This avoids an unnecessary LLM call for sparse chunks.

```python
# Phase 1 — Entity extraction
entities = service._extract_entities(chunk)

# Phase 2 — Relationship extraction (only if 2+ entities found)
relationships = service._extract_relationships(chunk, entities) if len(entities) >= 2 else []
```

### Sync Neo4j Driver for Celery Tasks

The existing `app/db/neo4j.py` uses `AsyncGraphDatabase.driver` (for FastAPI async routes). Celery tasks are **synchronous** (using `SyncSessionLocal` for PostgreSQL). Create a dedicated `app/db/sync_neo4j.py`:

```python
# app/db/sync_neo4j.py
from neo4j import GraphDatabase  # Sync driver — NOT AsyncGraphDatabase
from app.config import get_settings

settings = get_settings()
_auth_parts = settings.neo4j_auth.split("/", 1)
_user, _password = _auth_parts

sync_neo4j_driver = GraphDatabase.driver(
    settings.neo4j_uri,
    auth=(_user, _password),
)
```

Use `with sync_neo4j_driver.session() as session:` in Celery tasks — synchronous, no asyncio required.

### Neo4j MERGE Pattern for Deduplication

Entities are deduplicated by `(name, type, investigation_id)`. The MERGE pattern handles both create and update atomically:

```cypher
MERGE (e:Person {name: $name, type: $type, investigation_id: $investigation_id})
ON CREATE SET
  e.id = $id,
  e.confidence_score = $confidence,
  e.created_at = datetime()
ON MATCH SET
  e.confidence_score = CASE
    WHEN $confidence > e.confidence_score THEN $confidence
    ELSE e.confidence_score
  END
```

For relationships between entities:
```cypher
MATCH (src:Person {name: $src_name, investigation_id: $inv_id})
MATCH (tgt:Organization {name: $tgt_name, investigation_id: $inv_id})
MERGE (src)-[r:WORKS_FOR]->(tgt)
ON CREATE SET r.confidence_score = $confidence, r.source_chunk_id = $chunk_id
ON MATCH SET
  r.confidence_score = CASE
    WHEN $confidence > r.confidence_score THEN $confidence
    ELSE r.confidence_score
  END
```

**Dynamic labels are safe** because they come from the validated `EntityType` and `RelationType` enums — never from raw user input. Use Python string formatting for label names in Cypher (labels cannot be parameterized in Cypher).

### Neo4j Uniqueness Constraints (Story-Level Schema)

The architecture defers Neo4j schema constraints to this story. Create per-label uniqueness constraints:
```cypher
CREATE CONSTRAINT person_unique IF NOT EXISTS
  FOR (n:Person) REQUIRE (n.name, n.type, n.investigation_id) IS UNIQUE

CREATE CONSTRAINT organization_unique IF NOT EXISTS
  FOR (n:Organization) REQUIRE (n.name, n.type, n.investigation_id) IS UNIQUE

CREATE CONSTRAINT location_unique IF NOT EXISTS
  FOR (n:Location) REQUIRE (n.name, n.type, n.investigation_id) IS UNIQUE
```

Plus investigation_id indexes for fast per-investigation entity queries:
```cypher
CREATE INDEX entity_investigation_idx IF NOT EXISTS FOR (n:Person) ON (n.investigation_id)
-- same for Organization, Location
```

These are created via `ensure_neo4j_constraints(sync_neo4j_driver)` called once at FastAPI startup in `app/main.py` (after Alembic migrations). They are idempotent — safe to run on every deploy.

### Relationship Prompt Design

The relationship extraction prompt receives the **already-extracted entity list** from phase 1. This constrains the LLM to only create relationships between known entities (prevents hallucinated entity names):

```python
RELATIONSHIP_EXTRACTION_SYSTEM_PROMPT = """\
You are a relationship extraction system for OSINT analysis.

Given a text passage and a list of named entities already extracted from it, identify
relationships ONLY between the provided entities. Do not introduce new entity names.

Relationship types to detect:
- WORKS_FOR: A person works for, is employed by, or is affiliated with an organization
- KNOWS: Two people know each other, have met, or have a personal/professional connection
- LOCATED_AT: A person or organization is located at, based in, or associated with a location

Rules:
- Only create relationships between entities listed in the provided entity list
- Use the exact entity names from the provided list as source_entity_name and target_entity_name
- Assign a confidence score (0.0–1.0) based on how explicitly the text states the relationship
- Do not infer relationships that are not stated in the text
- Return valid JSON matching the schema

Respond ONLY with a JSON object containing a "relationships" array.\
"""

RELATIONSHIP_EXTRACTION_USER_PROMPT_TEMPLATE = """\
Text passage:
---
{chunk_text}
---

Entities found in this passage:
{entities_json}

Identify relationships between these entities. Return a JSON object with a "relationships" array.
Each relationship must have: "source_entity_name", "target_entity_name", "relation_type", "confidence".\
"""
```

### SSE Events for Entity Extraction

Reuse existing `EventPublisher` from `app/services/events.py`. New events:

```python
# Stage transition
publisher.publish(investigation_id, "document.processing", {
    "document_id": document_id,
    "stage": "extracting_entities",
    "chunk_count": len(chunks),
    "progress": 0.0,
})

# Per-entity discovery (via callback in extraction service)
publisher.publish(investigation_id, "entity.discovered", {
    "document_id": document_id,
    "entity_type": "person",      # one of: person, organization, location
    "entity_name": "John Smith",
})

# Completion
publisher.publish(investigation_id, "document.complete", {
    "document_id": document_id,
    "entity_count": 15,
    "relationship_count": 6,
})
```

The `on_entity_discovered` callback in `EntityExtractionService.extract_from_chunks()` should only fire for **new entities** (not already seen in a previous chunk). Use a `set[tuple[str, str]]` of `(name, type)` to track what has been discovered across chunks in this document run.

Note: The architecture requires real-time entity appearance (FR34). Deduplicate only within a single document run — the same entity name may appear in a previous document (different run, already in Neo4j) and still fire `entity.discovered` for the current document context.

### LLM Response Parsing — Resilience

The LLM can occasionally return malformed JSON. Handle gracefully:

```python
try:
    raw_content = response["message"]["content"]
    data = json.loads(raw_content)
    result = EntityExtractionResponse.model_validate(data)
    return result.entities
except (KeyError, json.JSONDecodeError, ValidationError) as exc:
    logger.warning(
        "LLM response parse failed for entity extraction",
        chunk_id=str(chunk.id),
        error=str(exc),
    )
    return []  # Soft failure — this chunk yields no entities
```

A chunk yielding no entities is acceptable — it just means that chunk produced no OSINT value. The document continues processing. Only `OllamaUnavailableError` (network failure) causes the document to fail.

### Processing Pipeline — Important Change

The current `process_document_task` ends with:
```python
# All stages complete
document.status = "complete"
session.commit()
_publish_safe("document.complete", {"document_id": document_id})
```

**This early `document.complete` must be replaced** by the new extraction stage. The final `document.complete` fires after extraction with entity/relationship counts. Story 3.4 will then insert `embedding` before `complete`.

### ExtractionSummary

```python
from dataclasses import dataclass

@dataclass
class ExtractionSummary:
    entity_count: int     # Total unique entities stored (new + updated)
    relationship_count: int  # Total relationships stored
    chunk_count: int      # Number of chunks processed
```

Entity count tracks unique entities **stored** (deduplicated across chunks within this document's processing run). Use a `set` of entity names seen in this run to count uniquely.

### Project Structure Notes

**New files:**
- `apps/api/app/db/sync_neo4j.py` — Sync Neo4j driver for Celery tasks
- `apps/api/app/services/extraction.py` — EntityExtractionService
- `apps/api/tests/services/test_extraction.py` — Unit tests for extraction service

**Modified files:**
- `apps/api/app/llm/schemas.py` — Add RelationType, ExtractedRelationship, RelationshipExtractionResponse
- `apps/api/app/llm/prompts.py` — Add RELATIONSHIP_EXTRACTION_SYSTEM_PROMPT and RELATIONSHIP_EXTRACTION_USER_PROMPT_TEMPLATE
- `apps/api/app/exceptions.py` — Add EntityExtractionError
- `apps/api/app/main.py` — Add ensure_neo4j_constraints call at startup
- `apps/api/app/worker/tasks/process_document.py` — Add extracting_entities stage, update document.complete event
- `apps/api/tests/llm/test_prompts.py` — Add relationship schema/prompt tests
- `apps/api/tests/worker/test_process_document.py` — Add extraction stage integration tests

**No new Alembic migration needed** — all Neo4j schema changes are handled via Cypher constraints, not PostgreSQL.

**No new Python packages** — `neo4j>=6.1.0` is already installed and supports sync `GraphDatabase.driver()`.

### Alignment with Unified Project Structure

- `app/db/sync_neo4j.py` mirrors the existing `app/db/sync_postgres.py` pattern exactly
- `app/services/extraction.py` follows the same class-based service pattern as `app/services/chunking.py`
- All Neo4j property names use `snake_case` per architecture convention
- All Neo4j node labels use `PascalCase` per architecture convention
- All Neo4j relationship types use `UPPER_SNAKE_CASE` per architecture convention

### Existing Code to Reuse (DO NOT REINVENT)

| What | Where | How to Reuse |
|------|-------|--------------|
| `OllamaClient.chat()` | `app/llm/client.py` | Two-phase LLM calls (entity + relationship extraction) |
| `DEFAULT_MODEL` constant | `app/llm/client.py` | Import and use for all Ollama calls |
| `EntityExtractionResponse` + `ExtractedEntity` | `app/llm/schemas.py` | Phase 1 entity parsing (extend, don't rewrite) |
| `ENTITY_EXTRACTION_SYSTEM_PROMPT` | `app/llm/prompts.py` | Phase 1 system prompt (extend, don't rewrite) |
| `ENTITY_EXTRACTION_USER_PROMPT_TEMPLATE` | `app/llm/prompts.py` | Phase 1 user prompt (extend, don't rewrite) |
| `EventPublisher` | `app/services/events.py` | Publish entity.discovered and document.complete events |
| `SyncSessionLocal` | `app/db/sync_postgres.py` | Pattern reference for sync_neo4j.py |
| `_publish_safe` helper | `app/worker/tasks/process_document.py` | Reuse existing best-effort publisher wrapper |
| `DomainError` | `app/exceptions.py` | Inherit for EntityExtractionError |
| `conftest.py` fixtures | `tests/conftest.py` | Reuse mock_postgres, sample_document fixtures |
| Loguru structured logging | Used throughout | `logger.info(...)` with keyword args for structured context |

### Anti-Patterns to Avoid

- **DO NOT** hardcode entity type labels as strings — derive from `EntityType` enum (`.value.capitalize()`)
- **DO NOT** use `CREATE` instead of `MERGE` for entities — must handle duplicates atomically
- **DO NOT** fail the entire document if a single chunk yields no entities — soft failures per chunk
- **DO NOT** fire `entity.discovered` for every entity occurrence — only fire for first discovery per entity per document run
- **DO NOT** call relationship extraction when fewer than 2 entities were extracted — skip early
- **DO NOT** include relationships with entity names not in the extracted list — validate referential integrity
- **DO NOT** use the async Neo4j driver in Celery tasks — use `sync_neo4j_driver` from `sync_neo4j.py`
- **DO NOT** store chunks in Neo4j — chunks stay in PostgreSQL; provenance linking (MENTIONED_IN edges from Entity to Chunk) is Story 3.3's work. Story 3.2 stores only `source_chunk_id` as a scalar property on relationship edges.
- **DO NOT** implement embedding generation — that is Story 3.4
- **DO NOT** implement entity search or graph query APIs — that is Epic 4
- **DO NOT** implement the provenance chain API (`GET /api/v1/investigations/{id}/entities/{id}`) — that is Story 3.3
- **DO NOT** add new Python packages — all needed packages already installed (`neo4j>=6.1.0`, `httpx`, `pydantic`)
- **DO NOT** use `print()` — use Loguru `logger` for all output
- **DO NOT** use async Neo4j session in Celery tasks — always sync

### Testing Strategy

**Unit tests** (`tests/services/test_extraction.py`):
```python
from unittest.mock import MagicMock, patch, call
from app.services.extraction import EntityExtractionService, ExtractionSummary

def test_extract_entities_success(mock_ollama, sample_chunk):
    """Phase 1: successful entity extraction from chunk."""
    mock_ollama.chat.return_value = {
        "message": {"content": '{"entities": [{"name": "John Smith", "type": "person", "confidence": 0.9}]}'}
    }
    service = EntityExtractionService(mock_ollama, MagicMock())
    entities = service._extract_entities(sample_chunk)
    assert len(entities) == 1
    assert entities[0].name == "John Smith"

def test_extract_entities_parse_failure_returns_empty(mock_ollama, sample_chunk):
    """LLM returns malformed JSON — soft failure, return empty list."""
    mock_ollama.chat.return_value = {"message": {"content": "sorry, i cannot"}}
    service = EntityExtractionService(mock_ollama, MagicMock())
    entities = service._extract_entities(sample_chunk)
    assert entities == []  # No exception raised

def test_relationship_extraction_skipped_if_less_than_2_entities(mock_ollama, sample_chunk):
    """Skip relationship LLM call when fewer than 2 entities extracted."""
    service = EntityExtractionService(mock_ollama, MagicMock())
    rels = service._extract_relationships(sample_chunk, [one_entity])
    assert rels == []
    mock_ollama.chat.assert_not_called()  # No LLM call made

def test_entity_deduplication_fires_callback_once(mock_ollama, mock_neo4j, two_chunks):
    """entity.discovered callback fires only for first occurrence."""
    discovered = []
    service = EntityExtractionService(mock_ollama, mock_neo4j)
    service.extract_from_chunks(two_chunks, investigation_id, on_entity_discovered=discovered.append)
    # Same entity in both chunks → callback fires only once
    entity_names = [e.name for e in discovered]
    assert entity_names.count("John Smith") == 1
```

**Integration tests** (`tests/worker/test_process_document.py` extensions):
```python
@patch("app.worker.tasks.process_document.EntityExtractionService")
def test_extracting_entities_stage_runs(mock_service_cls, ...):
    """Pipeline runs extracting_entities stage after chunking."""
    mock_service_cls.return_value.extract_from_chunks.return_value = ExtractionSummary(3, 1, 2)
    process_document_task(document_id, investigation_id)
    # Verify status transition
    assert document.status == "complete"
    # Verify document.complete event has entity/relationship counts
    published_events = [e for e in published if e["type"] == "document.complete"]
    assert published_events[0]["payload"]["entity_count"] == 3

@patch("app.worker.tasks.process_document.EntityExtractionService")
def test_extraction_failure_marks_document_failed(mock_service_cls, ...):
    """Extraction failure → document.status = failed, document.failed SSE published."""
    mock_service_cls.return_value.extract_from_chunks.side_effect = EntityExtractionError("neo4j down")
    process_document_task(document_id, investigation_id)
    assert document.status == "failed"
```

### Previous Story Intelligence (Story 3.1 Learnings)

From Story 3.1 dev notes and completion record:

1. **httpx.Response mock requires `request` attribute for `raise_for_status()`** — use `MagicMock`-based responses when mocking httpx in tests (not bare `httpx.Response` constructors). Pattern: `mock.post.return_value = MagicMock(status_code=200, json=lambda: {...})` rather than `httpx.Response(200, ...)`.

2. **Composite index on `__table_args__`** was added as a code review fix — SQLModel models need `__table_args__` for composite constraints. Not directly relevant for this story (no new PostgreSQL tables), but applies to Neo4j constraints similarly.

3. **Session rollback before failure commit** — Story 3.1 code review required `session.rollback()` before setting `document.status = "failed"` when an earlier operation may have left the session dirty. Apply same pattern in extraction failure handler in `process_document.py`.

4. **`OllamaClient` is sync + uses context manager for `httpx.Client`** — each call creates and closes its own `httpx.Client` via `with httpx.Client(...) as http:`. This is deliberate for Celery (no shared state). Do not attempt to share or reuse the httpx client.

5. **Entity extraction prompts already defined** — `ENTITY_EXTRACTION_SYSTEM_PROMPT` and `ENTITY_EXTRACTION_USER_PROMPT_TEMPLATE` are in `app/llm/prompts.py`. `EntityExtractionResponse` and `ExtractedEntity` are in `app/llm/schemas.py`. Import and reuse; do not duplicate.

6. **Full test suite had 137 tests passing** after Story 3.1 — all existing tests must continue to pass.

### Git Intelligence (Recent Commits)

- `c587e45` — Add README.md
- `18279df` — Story 3.1: document chunking, Ollama LLM client, prompt templates, pipeline integration
  - Created: `app/models/chunk.py`, `app/services/chunking.py`, `app/llm/client.py`, `app/llm/prompts.py`, `app/llm/schemas.py`, `migrations/004_create_document_chunks_table.py`
  - Modified: `app/models/__init__.py`, `app/exceptions.py`, `app/worker/tasks/process_document.py`
  - Test files: `tests/services/test_chunking.py`, `tests/llm/test_client.py`, `tests/llm/test_prompts.py`, `tests/worker/test_process_document.py`

**Convention patterns from recent commits:**
- Services: class-based, `__init__` takes dependencies (no global state)
- Tests: `tests/{category}/test_{module}.py` — mirrors `app/{category}/{module}.py`
- Exceptions: all in `app/exceptions.py`, inherit from `DomainError`
- Celery tasks: sync session (`SyncSessionLocal`), explicit commit/rollback, `_publish_safe` wrapper

### References

- [Source: _bmad-output/planning-artifacts/epics.md — Epic 3, Story 3.2 acceptance criteria]
- [Source: _bmad-output/planning-artifacts/architecture.md — Neo4j node labels: PascalCase; relationship types: UPPER_SNAKE_CASE; properties: snake_case]
- [Source: _bmad-output/planning-artifacts/architecture.md — SSE event types: entity.discovered payload {document_id, entity_type, entity_name}]
- [Source: _bmad-output/planning-artifacts/architecture.md — document.complete payload {document_id, entity_count, relationship_count}]
- [Source: _bmad-output/planning-artifacts/architecture.md — Entity extraction service location: app/services/extraction.py]
- [Source: _bmad-output/planning-artifacts/architecture.md — FR11-FR16: Entity extraction requirements]
- [Source: _bmad-output/planning-artifacts/architecture.md — FR34: entities appear in real-time via SSE]
- [Source: _bmad-output/planning-artifacts/architecture.md — NFR1: 100-page PDF processed in <15 min]
- [Source: _bmad-output/planning-artifacts/architecture.md — Neo4j constraints deferred to story-level]
- [Source: _bmad-output/planning-artifacts/architecture.md — Data boundary: Neo4j accessed via neo4j Python driver]
- [Source: apps/api/app/llm/client.py — OllamaClient.chat(), DEFAULT_MODEL = "qwen3.5:9b"]
- [Source: apps/api/app/llm/prompts.py — Existing entity extraction prompts to extend]
- [Source: apps/api/app/llm/schemas.py — EntityExtractionResponse, ExtractedEntity, EntityType]
- [Source: apps/api/app/db/sync_postgres.py — Pattern for sync Neo4j driver creation]
- [Source: apps/api/app/db/neo4j.py — Async driver config for reference (uri, auth parsing)]
- [Source: apps/api/app/services/events.py — EventPublisher for Redis pub/sub SSE]
- [Source: apps/api/app/worker/tasks/process_document.py — Current pipeline; _publish_safe pattern]
- [Source: apps/api/app/exceptions.py — DomainError base class pattern]
- [Source: apps/api/app/config.py — settings.neo4j_uri, settings.neo4j_auth]
- [Source: apps/api/app/main.py — lifespan startup block for Neo4j constraint setup]
- [Source: _bmad-output/implementation-artifacts/3-1-document-chunking-llm-integration-layer.md — httpx mock pattern; session.rollback() before failure commit; soft failure per chunk approach]

## Dev Agent Record

### Agent Model Used

Claude Sonnet 4.6

### Debug Log References

None — implementation proceeded cleanly without debugging sessions.

### Completion Notes List

- Implemented two-phase LLM extraction per chunk: Phase 1 entity extraction (reusing existing prompts/schemas), Phase 2 relationship extraction (new prompts/schemas). Phase 2 skipped when fewer than 2 entities extracted.
- Created sync Neo4j driver (`app/db/sync_neo4j.py`) mirroring `sync_postgres.py` pattern exactly — uses `neo4j.GraphDatabase.driver()` for Celery task use.
- `EntityExtractionService` uses MERGE (not CREATE) for deduplication — entities identified by `(name, type, investigation_id)`, confidence_score updated to max of existing vs. new.
- Referential integrity enforced: relationships filtered to only those where both `source_entity_name` and `target_entity_name` appear in the extracted entity list for that chunk.
- Soft failure pattern: LLM parse failures (ValidationError, JSONDecodeError, KeyError) return empty list per chunk — processing continues. Only Neo4j errors re-raise.
- `entity.discovered` callback fires only for first occurrence of each entity (tracked by `(name, type)` set) per document run.
- `document.complete` SSE event now includes `entity_count` and `relationship_count` (breaking change from Story 3.1 which sent only `document_id`).
- Neo4j uniqueness constraints and investigation_id indexes created at FastAPI startup via `ensure_neo4j_constraints` — idempotent, run via `asyncio.to_thread`.
- Session rollback applied before failure commit in extraction stage (consistent with chunking stage pattern from Story 3.1 code review).
- Full test suite: 180 tests, 0 failures, 0 regressions. (43 new tests added across 3 files: 21 in test_extraction.py, 14 in test_prompts.py, 8 in test_process_document.py.)

### File List

apps/api/app/llm/schemas.py
apps/api/app/llm/prompts.py
apps/api/app/db/sync_neo4j.py
apps/api/app/services/extraction.py
apps/api/app/exceptions.py
apps/api/app/main.py
apps/api/app/worker/tasks/process_document.py
apps/api/migrations/env.py
apps/api/tests/llm/test_prompts.py
apps/api/tests/services/test_extraction.py
apps/api/tests/worker/test_process_document.py

## Change Log

- 2026-03-10: Story 3.2 implementation complete — added two-phase entity/relationship extraction via Ollama, sync Neo4j driver for Celery, EntityExtractionService with MERGE deduplication, Neo4j schema constraints at startup, extracting_entities pipeline stage with entity.discovered SSE events, updated document.complete payload to include entity/relationship counts. 42 new tests added; 179 total, 0 regressions.
- 2026-03-10: Code review complete (adversarial) — 0 High, 5 Medium fixed, 4 Low noted. Fixes: sync_neo4j_driver.close() added to lifespan shutdown; trivially-passing MERGE test assertion corrected; unreachable test code in test_malformed_json_raises split into two meaningful tests; story File List updated to include migrations/env.py; false "45 tests" claim corrected to 21. 1 additional test added; 180 total, 0 regressions.
