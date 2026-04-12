# Story 8.2: Manual Relationship Creation

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an investigator,
I want to manually draw connections between entities I know are related,
So that I can capture relationships I discovered through my own analysis that the system didn't detect.

## Acceptance Criteria

1. **GIVEN** the investigator is viewing the graph with two or more entities visible, **WHEN** they initiate "Add Relationship" (via Entity Detail Card action or graph toolbar), **THEN** they can select a source entity, target entity, and relationship type (WORKS_FOR, KNOWS, LOCATED_AT, MENTIONED_IN, or custom), **AND** they can add a source annotation describing the evidence for this relationship, **AND** the relationship is created in Neo4j with `source="manual"` and `confidence_score=1.0`.

2. **GIVEN** the API receives `POST /api/v1/investigations/{id}/relationships/`, **WHEN** the request contains source_entity_id, target_entity_id, type, and optional annotation, **THEN** the relationship is persisted in Neo4j connecting the two entity nodes, **AND** the response includes the relationship ID, type, and connected entity names.

3. **GIVEN** a manual relationship is created, **WHEN** the graph renders, **THEN** the new edge appears with the same visual styling as LLM-extracted relationships, **AND** the edge is distinguishable as manually created via a subtle indicator (e.g., "manual" badge on edge detail), **AND** clicking the edge shows the source annotation instead of a document citation.

4. **GIVEN** the investigator tries to create a duplicate relationship (same source, target, and type), **WHEN** the API validates the request, **THEN** the existing relationship is returned with a note that it already exists, **AND** no duplicate edge is created.

## Tasks / Subtasks

- [x] **Task 1: Add relationship schemas** (AC: 2)
  - [x] 1.1: In `apps/api/app/schemas/relationship.py` (new file), add `RelationshipCreateRequest(BaseModel)` with fields: `source_entity_id: str`, `target_entity_id: str`, `type: str` (validated against ALLOWED_RELATIONSHIP_TYPES), `source_annotation: str | None = None`
  - [x] 1.2: Add `RelationshipResponse(BaseModel)` with fields: `id: str`, `source_entity_id: str`, `target_entity_id: str`, `source_entity_name: str`, `target_entity_name: str`, `type: str`, `confidence_score: float`, `source: str`, `source_annotation: str | None`, `already_existed: bool = False`
  - [x] 1.3: Define `ALLOWED_RELATIONSHIP_TYPES = {"WORKS_FOR", "KNOWS", "LOCATED_AT", "MENTIONED_IN"}` in the schema file. Additionally accept custom types that match pattern `^[A-Z][A-Z0-9_]*$` (UPPER_SNAKE_CASE)
  - [x] 1.4: Regenerate OpenAPI types: run `scripts/generate-api-types.sh` to update `apps/web/src/lib/api-types.generated.ts`

- [x] **Task 2: Add relationship creation method to EntityQueryService** (AC: 2, 4)
  - [x] 2.1: In `apps/api/app/services/entity_query.py`, add method `create_relationship(investigation_id, source_entity_id, target_entity_id, rel_type, source_annotation) -> RelationshipResponse`
  - [x] 2.2: The method must first verify both source and target entities exist in the investigation (return 404 if either is missing)
  - [x] 2.3: Check for existing duplicate relationship (same source, target, type) using MATCH query. If found, return it with `already_existed=True`
  - [x] 2.4: If no duplicate, CREATE the relationship with properties: `id` (UUID), `confidence_score=1.0`, `source="manual"`, `source_annotation`, `created_at=datetime()`
  - [x] 2.5: Return `RelationshipResponse` including both entity names (fetched from the MATCH)

- [x] **Task 3: Add relationship creation API endpoint** (AC: 2)
  - [x] 3.1: In `apps/api/app/api/v1/relationships.py` (new file), add `POST /{investigation_id}/relationships/` endpoint that accepts `RelationshipCreateRequest` body, validates relationship type, calls service method, returns `RelationshipResponse` with 201 status (or 200 if already existed)
  - [x] 3.2: Add the router to `apps/api/app/api/v1/router.py`
  - [x] 3.3: If either entity not found, raise `EntityNotFoundError`
  - [x] 3.4: Validate relationship type: must be in ALLOWED_RELATIONSHIP_TYPES or match UPPER_SNAKE_CASE pattern

- [x] **Task 4: Update graph edge data to include source field** (AC: 3)
  - [x] 4.1: In `apps/api/app/schemas/graph.py`, add `source: str = "extracted"` and `source_annotation: str | None = None` to `GraphEdgeData`
  - [x] 4.2: In `apps/api/app/services/graph_query.py`, update `_fetch_edges_between` and `_fetch_neighbors` Cypher queries to RETURN `r.source AS source` and `r.source_annotation AS source_annotation`
  - [x] 4.3: Pass `source` and `source_annotation` when constructing `GraphEdgeData` objects in `get_subgraph()` and `get_neighbors()`, defaulting to `"extracted"` for edges without the property

- [x] **Task 5: Update EdgeDetailPopover for manual relationship indicator** (AC: 3)
  - [x] 5.1: In `apps/web/src/components/graph/EdgeDetailPopover.tsx`, accept `source` and `source_annotation` in the `EdgeData` interface
  - [x] 5.2: When `source === "manual"`, show a "Manual" badge next to the relationship type
  - [x] 5.3: When `source_annotation` is present, show it in the evidence section instead of "View source entities for evidence"
  - [x] 5.4: Update the `GraphCanvas.tsx` edge tap handler to pass `source` and `source_annotation` from edge data

- [x] **Task 6: Create "Add Relationship" dialog component** (AC: 1)
  - [x] 6.1: Create `apps/web/src/components/graph/AddRelationshipDialog.tsx` — a shadcn/ui `Dialog` with: source entity selector (searchable dropdown), target entity selector (searchable dropdown), relationship type selector (predefined types + custom input), source_annotation textarea (optional)
  - [x] 6.2: Entity selectors should use the existing entities list endpoint. Pre-populate source entity if opened from Entity Detail Card
  - [x] 6.3: Relationship type selector: radio-style buttons for WORKS_FOR, KNOWS, LOCATED_AT, MENTIONED_IN, plus a text input for custom types
  - [x] 6.4: Form validation: source and target must be different entities, relationship type is required, custom type must be UPPER_SNAKE_CASE
  - [x] 6.5: On submit, call POST endpoint via TanStack Query mutation. On success: close dialog, invalidate graph data queries. If already_existed=true, show info message that the relationship already exists
  - [x] 6.6: On error, display the error detail from the API response in the dialog

- [x] **Task 7: Add TanStack Query mutation for relationship creation** (AC: 1)
  - [x] 7.1: In `apps/web/src/hooks/useEntityMutations.ts`, add `useCreateRelationship(investigationId)` mutation hook — calls `POST /api/v1/investigations/{investigationId}/relationships/`, on success invalidates query keys: `["graph", investigationId]` and `["entity-detail"]`

- [x] **Task 8: Add "Add Relationship" action to Entity Detail Card** (AC: 1)
  - [x] 8.1: In `apps/web/src/components/graph/EntityDetailCard.tsx`, add a "Link" (lucide-react) icon button in the action area
  - [x] 8.2: Clicking it opens the `AddRelationshipDialog` with the current entity pre-selected as source
  - [x] 8.3: Manage dialog state with `useState` for `addRelationshipDialogOpen`

- [x] **Task 9: Add "Add Relationship" button to graph toolbar** (AC: 1)
  - [x] 9.1: In `apps/web/src/components/graph/GraphCanvas.tsx`, add a `GitBranch` (lucide-react) icon button next to the existing "Add Entity" button
  - [x] 9.2: Clicking the button opens the `AddRelationshipDialog` without pre-selected entities
  - [x] 9.3: Manage dialog open state — add `useState` for `addRelationshipOpen`

- [x] **Task 10: Backend tests** (AC: 1, 2, 3, 4)
  - [x] 10.1: In `apps/api/tests/api/test_relationships.py` (new file), add test: `POST /investigations/{id}/relationships/` with valid body -> 201, response has `source="manual"`, `confidence_score=1.0`, correct type and entity names
  - [x] 10.2: Add test: POST with missing source_entity_id -> 422
  - [x] 10.3: Add test: POST with nonexistent source entity -> 404
  - [x] 10.4: Add test: POST with nonexistent target entity -> 404
  - [x] 10.5: Add test: POST duplicate relationship -> 200, response has `already_existed=True`
  - [x] 10.6: Add test: POST with same source and target entity -> 422
  - [x] 10.7: Add test: POST with invalid type (lowercase) -> 422
  - [x] 10.8: Add test: POST with valid custom UPPER_SNAKE_CASE type -> 201
  - [x] 10.9: Add test: graph edges include `source` field after relationship creation

- [x] **Task 11: Frontend tests** (AC: 1, 3)
  - [x] 11.1: Create `apps/web/src/components/graph/AddRelationshipDialog.test.tsx` — test: form renders with source entity, target entity, type, annotation fields
  - [x] 11.2: Add test: submit button disabled when required fields empty
  - [x] 11.3: Add test: successful submission closes dialog
  - [x] 11.4: In `EdgeDetailPopover.test.tsx`, add test: manual badge shown when source="manual"
  - [x] 11.5: In `EdgeDetailPopover.test.tsx`, add test: source annotation displayed when present

## Dev Notes

### Architecture Context

This is **Story 8.2** — the second story in Epic 8 (Manual Entity Curation & Disambiguation). Story 8.1 (Manual Entity Creation & Editing) is complete and established the patterns for manual data creation in Neo4j. This story extends that capability to relationships, giving investigators control over the graph structure.

**FRs covered:** FR55 (manual relationship creation)
**NFRs relevant:** NFR25 (atomic operations), NFR34 (atomic operations for relationships), all existing MVP NFRs for data integrity and provenance

### What Already Exists -- DO NOT RECREATE

| Component | Location | What It Does |
|---|---|---|
| Entity read/create/update endpoints | `app/api/v1/entities.py` | GET list + GET detail + POST create + PATCH update |
| Entity schemas | `app/schemas/entity.py` | EntityCreateRequest, EntityUpdateRequest, EntityListItem, EntityDetailResponse, EntityRelationship, EntitySource |
| Entity query service | `app/services/entity_query.py` | list_entities(), get_entity_detail(), create_entity(), update_entity() with Neo4j async reads/writes |
| Entity extraction service | `app/services/extraction.py` | LLM-based extraction -> Neo4j storage (MERGE pattern for entities AND relationships) |
| Graph query service | `app/services/graph_query.py` | get_subgraph(), get_neighbors() - returns hub nodes and edges |
| Graph schemas | `app/schemas/graph.py` | GraphNodeData, GraphEdgeData, GraphNode, GraphEdge, GraphResponse |
| Graph API endpoints | `app/api/v1/graph.py` | GET subgraph + GET neighbors |
| EntityDetailCard | `components/graph/EntityDetailCard.tsx` | Floating card with entity name, type, confidence, relationships, sources, edit button, "Ask about" action |
| EdgeDetailPopover | `components/graph/EdgeDetailPopover.tsx` | Edge detail popover showing type, confidence, source/target names, evidence links |
| GraphCanvas | `components/graph/GraphCanvas.tsx` | Graph visualization with search, filter, add entity buttons, entity/edge detail cards |
| AddEntityDialog | `components/graph/AddEntityDialog.tsx` | Add entity form dialog pattern (follow this for AddRelationshipDialog) |
| EditEntityDialog | `components/graph/EditEntityDialog.tsx` | Edit entity form dialog |
| Entity mutations hook | `hooks/useEntityMutations.ts` | useCreateEntity, useUpdateEntity TanStack Query mutations |
| Graph data hook | `hooks/useGraphData.ts` | useGraphData, useExpandNeighbors TanStack Query hooks |
| Entities hook | `hooks/useEntities.ts` | Entity list TanStack Query hook |
| DomainError + handler | `app/exceptions.py` | Base exception with RFC 7807 formatting, EntityNotFoundError, EntityDuplicateError |
| shadcn/ui Dialog/Input/Button/Textarea | `components/ui/*.tsx` | Form components already installed |
| Entity colors | `lib/entity-constants.ts` | ENTITY_COLORS map |
| OpenAPI type gen script | `scripts/generate-api-types.sh` | Generates TypeScript types from FastAPI OpenAPI spec |
| API client | `lib/api-client.ts` | openapi-fetch configured instance |
| Neo4j constraints | `app/services/extraction.py:233-267` | Uniqueness: (name, type, investigation_id) for entities |

### Critical Implementation Details

#### Neo4j Relationship Structure

**Current relationship properties (LLM-extracted relationships):**
```
(src)-[:WORKS_FOR {
  confidence_score: 0.85,
  source_chunk_id: "uuid"
}]->(tgt)
```

**New relationship properties (manual relationships -- Story 8.2 additions):**
```
(src)-[:WORKS_FOR {
  id: "uuid",                      // NEW -- unique ID for API reference
  confidence_score: 1.0,           // Always 1.0 for manual
  source: "manual",                // NEW -- "manual" or absent (= "extracted")
  source_annotation: "Found in...",// NEW -- optional free text evidence
  created_at: datetime()           // NEW -- creation timestamp
}]->(tgt)
```

**Backward compatibility:** Pre-existing LLM-extracted relationships do NOT have `id`, `source`, `source_annotation`, or `created_at` properties. The graph read queries must handle missing properties gracefully by defaulting: `source` -> `"extracted"`, `source_annotation` -> `null`. The edge ID in graph responses is currently computed as `{source_id}-{type}-{target_id}` -- this should continue to work since relationship `id` is an internal property, not the graph response edge ID.

#### Relationship Creation -- MERGE with duplicate detection

Unlike entity creation (which uses CREATE to fail on duplicates), relationship creation should use a two-step approach:
1. MATCH for existing relationship between the same source, target, and type
2. If found, return it with `already_existed=True`
3. If not found, CREATE with all manual properties

This is because Neo4j relationships don't have uniqueness constraints. Two relationships of the same type between the same nodes would create duplicates silently. We must detect duplicates at the application level.

**Cypher for duplicate check:**
```cypher
MATCH (src {id: $source_entity_id, investigation_id: $investigation_id})
-[r:WORKS_FOR]->
(tgt {id: $target_entity_id, investigation_id: $investigation_id})
RETURN r, src.name AS source_name, tgt.name AS target_name
```

**Cypher for creation (dynamic relationship type):**
```cypher
MATCH (src:Person|Organization|Location {id: $source_entity_id, investigation_id: $investigation_id})
MATCH (tgt:Person|Organization|Location {id: $target_entity_id, investigation_id: $investigation_id})
CREATE (src)-[r:WORKS_FOR {
  id: $id,
  confidence_score: 1.0,
  source: 'manual',
  source_annotation: $source_annotation,
  created_at: datetime()
}]->(tgt)
RETURN r.id AS id, type(r) AS type, src.name AS source_name, tgt.name AS target_name,
       r.confidence_score AS confidence_score, r.source AS source,
       r.source_annotation AS source_annotation
```

**IMPORTANT:** Since Neo4j Cypher does not allow parameterized relationship types, the relationship type must be interpolated into the query string. This is safe because we validate the type against UPPER_SNAKE_CASE pattern before building the query.

#### Relationship Type Validation

Predefined types: `WORKS_FOR`, `KNOWS`, `LOCATED_AT`, `MENTIONED_IN`
Custom types: Must match `^[A-Z][A-Z0-9_]*$` (UPPER_SNAKE_CASE, no leading underscores)

The validation should NOT be restrictive -- investigators may need custom relationship types like `OWNS`, `FUNDS`, `RELATED_TO`. The predefined types are suggestions in the UI, not hard limits.

The custom type must not be `MENTIONED_IN` when used between entity nodes (MENTIONED_IN is reserved for entity-to-Document provenance edges). Actually, upon re-reading the AC, MENTIONED_IN IS listed as an allowed type. We should allow it but note that it creates entity-to-entity relationships (different from provenance edges which connect to Document nodes).

#### Graph Edge Source Field

Currently `GraphEdgeData` has: id, source, target, type, confidence_score.
We need to add: `source` (rename to avoid collision with the "source" entity ID field).

**Naming conflict:** `GraphEdgeData` already has a `source` field meaning the source entity ID. The new "source" field means "manual" or "extracted". To avoid conflict, name the new field `edge_source` or just add it only to the edge detail popover data (not the graph schema). Actually, the simplest approach: add `origin: str = "extracted"` and `source_annotation: str | None = None` to `GraphEdgeData`. Use `origin` instead of `source` to avoid the naming collision.

#### Frontend Dialog Pattern

Follow the exact same patterns as `AddEntityDialog.tsx`:
- shadcn/ui `Dialog` with max-width ~480px (slightly wider to fit two entity selectors)
- Focus trapped inside (Radix UI handles this)
- Close via: X button, Escape key, backdrop click
- useState-controlled form fields (no form library)
- TanStack Query mutation for submission
- Query invalidation on success

The entity selectors should be simple dropdown/selects that fetch from the entities list endpoint. Since the entity list is already available via TanStack Query, we can use the existing `useEntities` hook.

#### Graph Refresh After Relationship Creation

After creating a relationship, invalidate these TanStack Query keys:
- `["graph", investigationId]` -- refreshes graph data (new edge appears)
- `["entity-detail", investigationId, sourceEntityId]` -- refreshes entity detail (relationships list)
- `["entity-detail", investigationId, targetEntityId]` -- refreshes target entity detail too

### Project Structure Notes

**New files:**
- `apps/api/app/schemas/relationship.py` -- Relationship create request + response schemas
- `apps/api/app/api/v1/relationships.py` -- POST relationship endpoint
- `apps/web/src/components/graph/AddRelationshipDialog.tsx` -- Add relationship form dialog
- `apps/web/src/components/graph/AddRelationshipDialog.test.tsx` -- Frontend tests
- `apps/api/tests/api/test_relationships.py` -- Backend tests

**Modified files:**
- `apps/api/app/api/v1/router.py` -- Register relationships router
- `apps/api/app/services/entity_query.py` -- Add create_relationship() method
- `apps/api/app/schemas/graph.py` -- Add origin/source_annotation to GraphEdgeData
- `apps/api/app/services/graph_query.py` -- Update edge queries to return source/source_annotation
- `apps/web/src/components/graph/EdgeDetailPopover.tsx` -- Manual badge and annotation display
- `apps/web/src/components/graph/EdgeDetailPopover.test.tsx` -- New tests for manual badge
- `apps/web/src/components/graph/EntityDetailCard.tsx` -- Add "Add Relationship" button
- `apps/web/src/components/graph/GraphCanvas.tsx` -- Add relationship toolbar button + dialog
- `apps/web/src/hooks/useEntityMutations.ts` -- Add useCreateRelationship hook
- `apps/web/src/lib/api-types.generated.ts` -- Regenerated (auto)

### Important Patterns from Previous Stories (Story 8.1)

1. **Neo4j async for reads, sync for writes in worker** -- For API-driven writes (this story), use `async with self.neo4j_driver.session() as session:` and `await session.execute_write(tx_function, ...)`. Same pattern as create_entity/update_entity.
2. **RFC 7807 error format** -- `{type, title, status, detail, instance}` via `DomainError` subclasses.
3. **Service layer pattern** -- Business logic in `app/services/`, API routes orchestrate services. Do NOT put Neo4j Cypher queries directly in route handlers.
4. **Loguru structured logging** -- `logger.info("Message", key=value, key2=value2)`.
5. **Commit pattern** -- `feat: Story X.Y -- description`.
6. **Backend test baselines** -- ~363+ backend tests, ~263+ frontend tests.
7. **Pre-existing test failures** -- `SystemStatusPage.test.tsx` (4 failures), `test_docker_compose.py` (2 infra), `test_entity_discovered_sse_events_published` (1 mock). Do not fix these.
8. **OpenAPI type generation** -- run `scripts/generate-api-types.sh` after any schema change.
9. **TanStack Query invalidation** -- Use `queryClient.invalidateQueries({ queryKey: [...] })` in mutation `onSuccess` callbacks.
10. **Forms** -- Per architecture decision, MVP uses `useState` + controlled inputs. No form library.
11. **shadcn/ui Dialog** -- Already installed. Import from `@/components/ui/dialog`. Uses Radix UI.
12. **Edge ID computation** -- `f"{source_id}-{type}-{target_id}"` in graph_query.py. Manual relationships use the same pattern.
13. **Dynamic Cypher relationship types** -- The extraction service already does this (line 219 in extraction.py: `f"MERGE (src)-[r:{rel_type}]->(tgt)"`). Follow the same pattern but with CREATE instead of MERGE.

### References

- [Source: _bmad-output/planning-artifacts/epics-phase2.md -- Epic 8, Story 8.2 acceptance criteria]
- [Source: _bmad-output/planning-artifacts/epics-phase2.md -- FR55 (manual relationship creation)]
- [Source: _bmad-output/planning-artifacts/architecture.md -- Lines 414: Neo4j relationship types UPPER_SNAKE_CASE]
- [Source: _bmad-output/planning-artifacts/architecture.md -- Lines 288-306: API endpoint structure]
- [Source: _bmad-output/planning-artifacts/architecture.md -- Lines 486-496: Error handling patterns]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md -- Lines 851-899: Entity Detail Card anatomy]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md -- Lines 1248-1296: Modal & Overlay patterns]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md -- Lines 963-976: Edge labels and click behavior]
- [Source: apps/api/app/services/extraction.py:209-228 -- Neo4j relationship MERGE pattern with dynamic type]
- [Source: apps/api/app/services/graph_query.py -- Edge queries and ID computation pattern]
- [Source: apps/api/app/services/entity_query.py -- create_entity/update_entity async write patterns]
- [Source: apps/api/app/schemas/graph.py -- Current GraphEdgeData schema]
- [Source: apps/web/src/components/graph/EdgeDetailPopover.tsx -- Current edge detail UI]
- [Source: apps/web/src/components/graph/AddEntityDialog.tsx -- Dialog form pattern to follow]
- [Source: apps/web/src/hooks/useEntityMutations.ts -- TanStack Query mutation pattern]
- [Source: _bmad-output/implementation-artifacts/8-1-manual-entity-creation-editing.md -- Previous story patterns and learnings]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

- Backend tests: 392 passed (excluding pre-existing docker_compose and process_document failures)
- Relationship tests: 10 passed (all new)
- Frontend tests: 269 passed (excluding 4 pre-existing SystemStatusPage failures)
- New frontend tests: AddRelationshipDialog (3), EdgeDetailPopover manual badge/annotation (3)

### Completion Notes List

- Implemented full relationship creation backend: RelationshipCreateRequest/RelationshipResponse schemas with Pydantic validators, POST endpoint at /investigations/{id}/relationships/, create_relationship service method with Neo4j async write transactions
- Duplicate relationship detection: MATCH query checks for existing relationship before CREATE, returns already_existed=True if found
- Entity existence validation: Both source and target entities verified before relationship creation, 404 if either missing
- Self-referencing prevented: Pydantic model_post_init rejects same source and target entity IDs
- Relationship types: WORKS_FOR, KNOWS, LOCATED_AT, MENTIONED_IN predefined + custom UPPER_SNAKE_CASE types validated via regex
- Graph edge data extended: Added origin and source_annotation fields to GraphEdgeData schema, updated graph_query.py Cypher queries (both _fetch_edges_between and _fetch_neighbors) to return r.source and r.source_annotation
- EdgeDetailPopover updated: "Manual" badge shown when origin="manual", source_annotation displayed in evidence section when present
- Created AddRelationshipDialog: entity selectors (native select from entity list), relationship type radio buttons + custom input, source annotation textarea, proper form validation, TanStack Query mutation with cache invalidation
- Added useCreateRelationship mutation hook to useEntityMutations.ts
- Added Link icon button to EntityDetailCard header (pre-selects current entity as source)
- Added GitBranch icon button to GraphCanvas toolbar (opens AddRelationshipDialog without pre-selection)
- OpenAPI TypeScript types updated with RelationshipCreateRequest, RelationshipResponse schemas and /relationships/ path

### File List

**New files:**
- apps/api/app/schemas/relationship.py
- apps/api/app/api/v1/relationships.py
- apps/api/tests/api/test_relationships.py
- apps/web/src/components/graph/AddRelationshipDialog.tsx
- apps/web/src/components/graph/AddRelationshipDialog.test.tsx

**Modified files:**
- apps/api/app/api/v1/router.py -- Registered relationships router
- apps/api/app/services/entity_query.py -- Added create_relationship method, _fetch_existing_relationship and _create_relationship transaction helpers
- apps/api/app/schemas/graph.py -- Added origin and source_annotation to GraphEdgeData
- apps/api/app/services/graph_query.py -- Updated edge Cypher queries to return source/source_annotation fields
- apps/web/src/components/graph/EdgeDetailPopover.tsx -- Manual badge, source annotation display
- apps/web/src/components/graph/EdgeDetailPopover.test.tsx -- Added 3 tests for manual badge and source annotation
- apps/web/src/components/graph/EntityDetailCard.tsx -- Added Link button and AddRelationshipDialog integration
- apps/web/src/components/graph/GraphCanvas.tsx -- Added GitBranch button and AddRelationshipDialog
- apps/web/src/hooks/useEntityMutations.ts -- Added useCreateRelationship mutation hook
- apps/web/src/lib/api-types.generated.ts -- Added relationship schemas and path

### Change Log

- 2026-04-12: Story 8.2 implementation complete — manual relationship creation with full backend, frontend, and tests
- 2026-04-12: Code review — 2 MEDIUM + 1 LOW issues found and fixed: added source_annotation max length validation (2000 chars) on backend schema, fixed React anti-pattern (useState-as-derived replaced with useEffect), added backend test for annotation length
