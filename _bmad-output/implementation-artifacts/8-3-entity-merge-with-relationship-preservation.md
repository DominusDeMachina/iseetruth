# Story 8.3: Entity Merge with Relationship Preservation

Status: done

## Story

As an investigator,
I want to merge duplicate entities into one, keeping all relationships and citations from both,
So that "Dep. Mayor Horvat" and "Deputy Mayor Horvat" become a single node with the full picture.

## Acceptance Criteria

1. **GIVEN** the investigator identifies two entities that are the same real-world entity, **WHEN** they select "Merge" from the Entity Detail Card and choose the target entity to merge into, **THEN** a merge preview shows: both entity names, all relationships from both, all source citations from both, **AND** the investigator selects which name to keep as primary (the other becomes an alias), **AND** they confirm the merge.

2. **GIVEN** the investigator confirms a merge, **WHEN** `POST /api/v1/investigations/{id}/entities/merge` is called with `source_entity_id` and `target_entity_id`, **THEN** all relationships from the source entity are transferred to the target entity, **AND** all source citations and provenance chains (MENTIONED_IN edges) from the source entity are added to the target entity, **AND** the source entity's name is added to the target entity's `aliases` array, **AND** the source entity node is deleted from Neo4j, **AND** any Qdrant embeddings referencing the source entity are updated to reference the target entity, **AND** the operation is atomic -- all transfers complete or the entire merge is rolled back (NFR34).

3. **GIVEN** both entities have a relationship to the same third entity of the same type, **WHEN** the merge executes, **THEN** duplicate relationships are consolidated into one, combining source citations from both, **AND** the confidence score of the consolidated relationship reflects the combined evidence (max of both scores).

4. **GIVEN** the merge completes, **WHEN** the graph re-renders, **THEN** the merged entity appears as a single node with all combined relationships, **AND** the node reflects the updated relationship count, **AND** an SSE event notifies the frontend of the entity change.

## Tasks / Subtasks

- [x] **Task 1: Add merge request/response schemas** (AC: 1, 2)
  - [x] 1.1: In `apps/api/app/schemas/entity.py`, add `EntityMergeRequest(BaseModel)` with fields: `source_entity_id: str`, `target_entity_id: str`, `primary_name: str | None = None` (optional -- if provided, this is the name to keep; otherwise target entity's name is kept)
  - [x] 1.2: Add `EntityMergePreview(BaseModel)` with fields: `source_entity: EntityDetailResponse`, `target_entity: EntityDetailResponse`, `duplicate_relationships: list[str]` (relationship types that exist on both entities to the same third party), `total_relationships_after: int`, `total_sources_after: int`
  - [x] 1.3: Add `EntityMergeResponse(BaseModel)` with fields: `merged_entity: EntityDetailResponse`, `relationships_transferred: int`, `citations_transferred: int`, `aliases_added: list[str]`, `duplicate_relationships_consolidated: int`
  - [x] 1.4: Regenerate OpenAPI types: run `scripts/generate-api-types.sh`

- [x] **Task 2: Add merge preview endpoint** (AC: 1)
  - [x] 2.1: In `apps/api/app/api/v1/entities.py`, add `POST /{investigation_id}/entities/merge/preview` endpoint that accepts `EntityMergeRequest` body, calls `EntityQueryService.preview_merge()`, returns `EntityMergePreview` with 200 status
  - [x] 2.2: Validate both entities exist and belong to same investigation. If source == target, return 422 "Cannot merge entity with itself". If either entity not found, return 404.
  - [x] 2.3: Validate both entities are the same type. If types differ, return 422 "Cannot merge entities of different types" (merging a Person into an Organization makes no sense)

- [x] **Task 3: Add merge execution endpoint** (AC: 2, 3, 4)
  - [x] 3.1: In `apps/api/app/api/v1/entities.py`, add `POST /{investigation_id}/entities/merge` endpoint that accepts `EntityMergeRequest` body, calls `EntityQueryService.merge_entities()`, returns `EntityMergeResponse` with 200 status
  - [x] 3.2: Same validation as preview endpoint (entities exist, same investigation, same type, not self-merge)
  - [x] 3.3: On successful merge, publish `entity.merged` SSE event via EventPublisher with payload: `{source_entity_id, target_entity_id, merged_entity_name}`

- [x] **Task 4: Implement merge preview in EntityQueryService** (AC: 1)
  - [x] 4.1: In `apps/api/app/services/entity_query.py`, add method `preview_merge(investigation_id, source_entity_id, target_entity_id) -> EntityMergePreview | None`
  - [x] 4.2: Fetch both entity details using existing `get_entity_detail()` method
  - [x] 4.3: Run a Neo4j read query to find duplicate relationships (same type + same third-party entity on both source and target)
  - [x] 4.4: Calculate totals: total unique relationships after merge, total unique source citations after merge

- [x] **Task 5: Implement atomic merge in EntityQueryService** (AC: 2, 3)
  - [x] 5.1: In `apps/api/app/services/entity_query.py`, add method `merge_entities(investigation_id, source_entity_id, target_entity_id, primary_name) -> EntityMergeResponse`
  - [x] 5.2: Execute the following steps in a **single Neo4j write transaction** for atomicity:
    - Step A: Transfer all entity-to-entity relationships FROM the source entity to the target entity. For each outgoing relationship `(source)-[r:TYPE]->(other)`, create `(target)-[r:TYPE]->(other)` with same properties, unless it already exists (duplicate consolidation per AC3). For incoming relationships `(other)-[r:TYPE]->(source)`, create `(other)-[r:TYPE]->(target)`.
    - Step B: For duplicate relationships (same type to same third entity), keep the one with higher confidence_score. If source has properties like source_chunk_id, merge them.
    - Step C: Transfer all MENTIONED_IN provenance edges: `(source)-[m:MENTIONED_IN]->(doc)` becomes `(target)-[m:MENTIONED_IN]->(doc)` with same chunk_id, page_start, page_end, text_excerpt properties. If target already has a MENTIONED_IN edge to the same doc with the same chunk_id, skip (dedup).
    - Step D: Add source entity's name to target entity's aliases array (avoid duplicates in aliases list). If primary_name is provided and differs from target's current name, swap: set target name = primary_name, add old target name to aliases too.
    - Step E: Update target's confidence_score to max(source.confidence_score, target.confidence_score).
    - Step F: Delete the source entity node and all its remaining relationships from Neo4j.
  - [x] 5.3: After Neo4j transaction succeeds, update Qdrant embeddings: scroll through all points in `document_chunks` collection where payload contains references to the source entity and update them. NOTE: Current Qdrant embeddings are indexed by chunk_id, not entity_id -- entities are NOT stored in Qdrant. Qdrant stores document chunk embeddings. Entity references live only in Neo4j. **Therefore, no Qdrant updates are needed for entity merge.** The AC mentions Qdrant but in practice, entity data is exclusively in Neo4j. Log this architectural decision.
  - [x] 5.4: Return `EntityMergeResponse` with counts of transferred relationships, citations, and consolidated duplicates

- [x] **Task 6: Add merge error types** (AC: 2)
  - [x] 6.1: In `apps/api/app/exceptions.py`, add `EntityMergeError(DomainError)` with `status_code=422`, `error_type="entity_merge_failed"`
  - [x] 6.2: Add `EntityTypeMismatchError(DomainError)` with `status_code=422`, `error_type="entity_type_mismatch"`
  - [x] 6.3: Add `EntitySelfMergeError(DomainError)` with `status_code=422`, `error_type="entity_self_merge"`

- [x] **Task 7: Create MergeEntityDialog component** (AC: 1)
  - [x] 7.1: Create `apps/web/src/components/graph/MergeEntityDialog.tsx` -- a shadcn/ui `Dialog` component that shows the merge preview and confirmation
  - [x] 7.2: Dialog flow: Step 1 -- entity search/select for the merge target (reuse EntitySearchCommand pattern), Step 2 -- preview showing both entities side by side with combined relationships/citations, Step 3 -- name selection (radio: keep source name or target name as primary), Step 4 -- confirm button
  - [x] 7.3: Preview fetched via POST to merge/preview endpoint. Show: source entity name+type, target entity name+type, relationship count from each, duplicate relationships that will be consolidated, total relationships/sources after merge
  - [x] 7.4: Confirm button calls POST merge endpoint via TanStack Query mutation. On success: close dialog, invalidate entity list + entity detail + graph data queries, show no toast (the graph update IS the feedback)
  - [x] 7.5: On error, display the error detail from the API response in the dialog
  - [x] 7.6: Dialog pattern: max-width ~520px, focus trapped, close via X/Escape/backdrop, fade-in 150ms

- [x] **Task 8: Add "Merge" button to EntityDetailCard** (AC: 1)
  - [x] 8.1: In `apps/web/src/components/graph/EntityDetailCard.tsx`, add a `Merge` (lucide-react) icon button in the header, next to the Edit (Pencil) and Close (X) buttons
  - [x] 8.2: Clicking "Merge" opens the `MergeEntityDialog` with the current entity as the source entity
  - [x] 8.3: Add `useState` for `mergeDialogOpen` in EntityDetailCard

- [x] **Task 9: Add TanStack Query mutations for merge** (AC: 1, 2)
  - [x] 9.1: In `apps/web/src/hooks/useEntityMutations.ts`, add `useMergeEntitiesPreview(investigationId)` query hook -- calls `POST /api/v1/investigations/{investigationId}/entities/merge/preview`
  - [x] 9.2: Add `useMergeEntities(investigationId)` mutation hook -- calls `POST /api/v1/investigations/{investigationId}/entities/merge`, on success invalidates query keys: `["entities", investigationId]`, `["entity-detail", investigationId]` (broad), and `["graph", investigationId]`

- [x] **Task 10: Backend tests** (AC: 1, 2, 3, 4)
  - [x] 10.1: In `apps/api/tests/api/test_entities.py`, add test class `TestMergePreview`:
    - Test: preview returns 200 with both entities and duplicate relationship info
    - Test: preview with non-existent source entity returns 404
    - Test: preview with self-merge returns 422
    - Test: preview with type mismatch returns 422
  - [x] 10.2: Add test class `TestMergeEntities`:
    - Test: merge returns 200 with transferred counts
    - Test: merge transfers relationships and citations
    - Test: merge adds source name to target aliases
    - Test: merge with primary_name swaps names correctly
    - Test: merge consolidates duplicate relationships (AC3)
    - Test: merge returns 404 for non-existent entity
    - Test: merge returns 422 for self-merge
    - Test: merge returns 422 for type mismatch

- [x] **Task 11: Frontend tests** (AC: 1)
  - [x] 11.1: Create `apps/web/src/components/graph/MergeEntityDialog.test.tsx` -- test: dialog renders with entity search, test: preview step shows both entities
  - [x] 11.2: In `EntityDetailCard.test.tsx`, add test: merge button present and opens merge dialog

## Dev Notes

### Architecture Context

This is **Story 8.3** -- the third story in Epic 8 (Manual Entity Curation & Disambiguation). Story 8.1 added manual entity creation and editing (POST/PATCH /entities/). Story 8.2 (manual relationship creation) is still in backlog but its patterns are described in the epics file. This story adds entity merge capability to combine duplicate entities while preserving all relationships and provenance.

**FRs covered:** FR54 (entity merge preserving relationships + citations)
**NFRs relevant:** NFR34 (atomic merge -- all transfers complete or entire merge is rolled back), NFR25 (database transactions are atomic)

### What Already Exists -- DO NOT RECREATE

| Component | Location | What It Does |
|---|---|---|
| Entity CRUD endpoints | `app/api/v1/entities.py` | GET list, GET detail, POST create, PATCH update |
| Entity schemas | `app/schemas/entity.py` | EntityCreateRequest, EntityUpdateRequest, EntityListItem, EntityDetailResponse, EntityRelationship, EntitySource |
| Entity query service | `app/services/entity_query.py` | list_entities(), get_entity_detail(), create_entity(), update_entity() with Neo4j async read/write |
| Entity extraction service | `app/services/extraction.py` | LLM-based extraction with MERGE pattern, Neo4j constraints |
| Neo4j constraints | `app/services/extraction.py:233-267` | Uniqueness: (name, type, investigation_id), indexes on id and investigation_id |
| EntityDetailCard | `components/graph/EntityDetailCard.tsx` | Floating card with entity name, type, confidence, relationships, sources, Edit button, "Ask about" action |
| EditEntityDialog | `components/graph/EditEntityDialog.tsx` | Edit entity name/annotation dialog |
| AddEntityDialog | `components/graph/AddEntityDialog.tsx` | Add new entity dialog |
| GraphCanvas | `components/graph/GraphCanvas.tsx` | Graph visualization with search, filter panel, entity/edge detail cards |
| Entity search | `components/graph/EntitySearchCommand.tsx` | Command palette search for entities -- REUSE this pattern for merge target selection |
| Entity hooks | `hooks/useEntities.ts`, `hooks/useEntityDetail.ts` | TanStack Query hooks for entity list and detail |
| Entity mutations | `hooks/useEntityMutations.ts` | useCreateEntity, useUpdateEntity TanStack Query mutations |
| Graph hooks | `hooks/useGraphData.ts` | TanStack Query hooks for graph data and neighbor expansion |
| Event publisher | `app/services/events.py` | EventPublisher with Redis pub/sub, `publish(investigation_id, event_type, payload)` |
| DomainError + handler | `app/exceptions.py` | Base exception with RFC 7807 formatting, EntityNotFoundError, EntityDuplicateError |
| Qdrant client | `app/db/qdrant.py` | Lazy singleton QdrantClient, COLLECTION_NAME="document_chunks" |
| Neo4j driver | `app/db/neo4j.py` | AsyncGraphDatabase driver singleton |
| API client | `lib/api-client.ts` | openapi-fetch configured instance |
| Entity colors | `lib/entity-constants.ts` | ENTITY_COLORS map |
| shadcn/ui Dialog | `components/ui/dialog.tsx` | Dialog component already installed |

### Critical Implementation Details

#### Neo4j Merge Transaction -- Atomic All-or-Nothing

The merge MUST execute in a single Neo4j write transaction. If any step fails, the entire operation rolls back. This is achieved by using `session.execute_write()` with all steps inside a single transaction function.

**Cypher for relationship transfer (inside single transaction):**
```cypher
// Step A: Transfer outgoing relationships from source to target
MATCH (source {id: $source_id, investigation_id: $inv_id})-[r]->(other)
WHERE type(r) <> 'MENTIONED_IN' AND other.id <> $target_id
WITH source, r, other, type(r) AS rel_type
OPTIONAL MATCH (target {id: $target_id})-[existing:rel_type]->(other)
// ... complex merge logic - see implementation
```

The actual implementation should use multiple Cypher statements within a single transaction function, not try to do everything in one query. Pattern from extraction.py `_write_tx` function:

```python
async def _merge_entities_tx(tx, source_id, target_id, inv_id, primary_name):
    # Step A: Get source's outgoing relationships
    result = await tx.run(
        "MATCH (s {id: $sid, investigation_id: $inv})-[r]->(o) "
        "WHERE type(r) <> 'MENTIONED_IN' "
        "RETURN type(r) AS rtype, o.id AS other_id, r.confidence_score AS conf, "
        "r.source_chunk_id AS chunk_id",
        sid=source_id, inv=inv_id,
    )
    outgoing = await result.data()

    # For each outgoing, create on target if not exists
    for rel in outgoing:
        # Check if target already has this relationship to the same node
        existing = await tx.run(
            "MATCH (t {id: $tid})-[r:" + rel["rtype"] + "]->(o {id: $oid}) "
            "RETURN r.confidence_score AS conf",
            tid=target_id, oid=rel["other_id"],
        )
        existing_data = await existing.single()
        if existing_data:
            # Duplicate consolidation - keep higher confidence
            if rel["conf"] and (not existing_data["conf"] or rel["conf"] > existing_data["conf"]):
                await tx.run(
                    "MATCH (t {id: $tid})-[r:" + rel["rtype"] + "]->(o {id: $oid}) "
                    "SET r.confidence_score = $conf",
                    tid=target_id, oid=rel["other_id"], conf=rel["conf"],
                )
        else:
            # Create new relationship on target
            await tx.run(
                "MATCH (t {id: $tid, investigation_id: $inv}), (o {id: $oid}) "
                "CREATE (t)-[r:" + rel["rtype"] + " {confidence_score: $conf, source_chunk_id: $chunk_id}]->(o)",
                tid=target_id, inv=inv_id, oid=rel["other_id"],
                conf=rel["conf"], chunk_id=rel.get("chunk_id"),
            )
    # ... repeat for incoming, MENTIONED_IN, aliases, delete source
```

**IMPORTANT:** The extraction service uses **sync** `self.neo4j_driver.session()` because it runs in Celery workers. The entity merge runs in FastAPI async endpoints, so use **async** `self.neo4j_driver.session()` with `await session.execute_write(...)`. See Story 8.1 patterns.

#### Qdrant Considerations -- NO UPDATE NEEDED

The acceptance criteria mention "Any Qdrant embeddings referencing the source entity are updated to reference the target entity." However, examining the actual Qdrant data model:

- Qdrant stores **document chunk embeddings** in the `document_chunks` collection
- Each point has payload: `{chunk_id, document_id, investigation_id, page_start, page_end, text_excerpt}`
- **Entities are NOT stored in Qdrant.** Entity data lives exclusively in Neo4j.
- The link between chunks and entities is through Neo4j MENTIONED_IN edges, not Qdrant payloads.

**Therefore, no Qdrant updates are needed for entity merge.** Log this architectural decision in the merge service.

#### SSE Event for Merge

Publish an `entity.merged` event after successful merge:
```python
event_publisher.publish(
    investigation_id=str(investigation_id),
    event_type="entity.merged",
    payload={
        "source_entity_id": source_entity_id,
        "target_entity_id": target_entity_id,
        "merged_entity_name": result.merged_entity.name,
    },
)
```

Use the existing `EventPublisher` from `app/services/events.py`. The publisher uses sync Redis (not async), so it can be called directly. Use `_publish_safe()` pattern if creating a wrapper -- SSE events are best-effort and should never raise.

To get EventPublisher in the API endpoint, create it with the Redis URL from settings:
```python
from app.config import get_settings
from app.services.events import EventPublisher

settings = get_settings()
publisher = EventPublisher(settings.redis_url)
publisher.publish(...)
publisher.close()
```

#### Merge Target Entity Selection UI

The merge dialog needs an entity search/select step. Reuse the pattern from `EntitySearchCommand.tsx`:
- Use the existing `useEntities` hook to fetch the entity list
- Filter out the source entity from the list
- Allow searching by name
- Show entity type colored dots for each option
- On select, fetch the merge preview

#### Frontend Dialog Pattern

Per UX spec and existing patterns (AddEntityDialog, EditEntityDialog):
- Full modal centered with backdrop dimming
- Max-width: ~520px for merge dialog (wider than edit/add because it shows side-by-side comparison)
- Focus trapped inside (shadcn/ui Dialog handles this)
- Close via: X button, Escape key, backdrop click
- Entrance: fade in 150ms
- Multi-step flow: target selection -> preview -> confirm

#### Graph Refresh After Merge

After merge, invalidate these TanStack Query keys:
- `["entities", investigationId]` -- refreshes entity list (merged entity gone, target updated)
- `["entity-detail", investigationId]` -- broadly invalidate all entity details (source entity deleted, target changed)
- `["graph", investigationId]` -- refreshes graph (source node removed, target node has new edges)

### Project Structure Notes

**New files:**
- `apps/web/src/components/graph/MergeEntityDialog.tsx` -- Merge entity dialog with search, preview, and confirm
- `apps/web/src/components/graph/MergeEntityDialog.test.tsx` -- Frontend tests

**Modified files:**
- `apps/api/app/schemas/entity.py` -- Add EntityMergeRequest, EntityMergePreview, EntityMergeResponse
- `apps/api/app/api/v1/entities.py` -- Add POST merge/preview and POST merge endpoints
- `apps/api/app/exceptions.py` -- Add EntityMergeError, EntityTypeMismatchError, EntitySelfMergeError
- `apps/api/app/services/entity_query.py` -- Add preview_merge(), merge_entities() methods with Neo4j transaction helpers
- `apps/web/src/components/graph/EntityDetailCard.tsx` -- Add "Merge" button in header
- `apps/web/src/hooks/useEntityMutations.ts` -- Add useMergeEntitiesPreview, useMergeEntities hooks
- `apps/web/src/lib/api-types.generated.ts` -- Regenerated (auto)
- `apps/api/tests/api/test_entities.py` -- Add merge preview and merge execution tests
- `apps/web/src/components/graph/EntityDetailCard.test.tsx` -- Add merge button test

### Important Patterns from Previous Stories

1. **Neo4j async for API-driven writes** -- Use `async with self.neo4j_driver.session() as session:` and `await session.execute_write(tx_function, ...)`. Extraction service uses sync sessions for Celery workers only.
2. **SSE events are best-effort** -- `_publish_safe()` wrapper never raises. If SSE publish fails, log warning and continue.
3. **RFC 7807 error format** -- `{type, title, status, detail, instance}` via DomainError subclasses.
4. **Service layer pattern** -- Business logic in `app/services/`, API routes orchestrate. No Cypher in route handlers.
5. **Loguru structured logging** -- `logger.info("Message", key=value)`.
6. **OpenAPI type generation** -- run `scripts/generate-api-types.sh` after any schema change.
7. **TanStack Query invalidation** -- Use `queryClient.invalidateQueries({ queryKey: [...] })` in mutation `onSuccess` callbacks.
8. **Entity type colors** -- `ENTITY_COLORS` in `lib/entity-constants.ts`: person=#6b9bd2, organization=#c4a265, location=#7dab8f.
9. **Forms** -- `useState` + controlled inputs. No form library.
10. **shadcn/ui Dialog** -- Import from `@/components/ui/dialog`. Radix UI under the hood.
11. **Commit pattern** -- `feat: Story X.Y -- description`.
12. **Pre-existing test failures to IGNORE** -- SystemStatusPage.test.tsx (4 failures), test_process_document.py (22 worker/infra failures).

### References

- [Source: _bmad-output/planning-artifacts/epics.md -- Epic 8, Story 8.3 acceptance criteria]
- [Source: _bmad-output/planning-artifacts/architecture.md -- Lines 66-77: Tech stack]
- [Source: _bmad-output/planning-artifacts/architecture.md -- Lines 288-306: API endpoint structure]
- [Source: _bmad-output/planning-artifacts/architecture.md -- Lines 399-424: Naming conventions]
- [Source: _bmad-output/planning-artifacts/architecture.md -- Lines 486-496: Error handling patterns]
- [Source: _bmad-output/planning-artifacts/architecture.md -- Lines 309-314: SSE event format]
- [Source: _bmad-output/planning-artifacts/prd.md -- FR54: Entity merge with relationship preservation]
- [Source: apps/api/app/services/entity_query.py -- Entity CRUD service with Neo4j async patterns]
- [Source: apps/api/app/services/extraction.py -- Neo4j write transaction pattern in _write_tx]
- [Source: apps/api/app/services/extraction.py:233-267 -- Neo4j constraints]
- [Source: apps/api/app/services/embedding.py -- Qdrant storage model (chunk-based, not entity-based)]
- [Source: apps/api/app/db/qdrant.py -- COLLECTION_NAME="document_chunks", no entity references]
- [Source: apps/api/app/services/events.py -- EventPublisher with Redis pub/sub]
- [Source: apps/api/app/exceptions.py -- DomainError base, EntityNotFoundError, EntityDuplicateError patterns]
- [Source: apps/web/src/components/graph/EntityDetailCard.tsx -- Full component with header buttons]
- [Source: apps/web/src/hooks/useEntityMutations.ts -- Mutation hook patterns]
- [Source: apps/web/src/components/graph/EntitySearchCommand.tsx -- Entity search pattern to reuse for merge target selection]
- [Source: _bmad-output/implementation-artifacts/8-1-manual-entity-creation-editing.md -- Previous story patterns]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

- Backend tests: 375 passed (excluding 2 pre-existing docker_compose failures)
- Entity tests: 31 passed (20 existing + 11 new merge tests)
- Frontend tests: 267 passed (excluding 4 pre-existing SystemStatusPage failures)
- New frontend tests: MergeEntityDialog (3), EntityDetailCard merge button (1)
- Code review: 3 HIGH + 2 MEDIUM issues found and fixed (2026-04-12)

### Code Review Findings (2026-04-12)

1. **HIGH — Cypher injection risk:** Dynamic relationship type names from Neo4j were interpolated directly into Cypher f-strings without validation. Fixed by adding `_validate_rel_type()` that enforces alphanumeric + underscore pattern.
2. **HIGH — Missing source_annotation merge:** Source entity's `source_annotation` was lost during merge. Fixed: annotations are now merged (target's annotation preserved, source's appended with `[Merged]` prefix).
3. **MEDIUM — Duplicate log messages:** Two "Entity merge completed" log lines with redundant info. Fixed: changed Qdrant skip message to `logger.debug`.
4. **MEDIUM — Incomplete duplicate detection in preview:** `_fetch_duplicate_relationships` only checked outgoing relationships. Fixed: now checks both outgoing and incoming relationship directions.
5. **MEDIUM — TOCTOU race in validation:** Validation fetches entities separately from the service method. Accepted risk: the atomic transaction will fail gracefully if entities are deleted between validation and execution, raising EntityMergeError.

### Completion Notes List

- Implemented entity merge backend: EntityMergeRequest/EntityMergePreview/EntityMergeResponse schemas, POST merge/preview and POST merge endpoints, preview_merge()/merge_entities() service methods with atomic Neo4j write transactions
- Added EntityMergeError, EntityTypeMismatchError, EntitySelfMergeError exception types
- Merge transaction handles: outgoing relationship transfer, incoming relationship transfer, duplicate relationship consolidation (max confidence wins), MENTIONED_IN provenance edge transfer with dedup, alias merging (source name + source aliases into target), primary_name swap, source_annotation merge, confidence score max, source entity DETACH DELETE
- Documented Qdrant non-requirement: entities live exclusively in Neo4j, Qdrant stores chunk embeddings only
- Published entity.merged SSE event via EventPublisher (best-effort)
- Created MergeEntityDialog with multi-step flow: target search/select -> preview comparison -> name selection -> confirm
- Added Merge icon button to EntityDetailCard header next to Edit and Close
- Created useMergeEntitiesPreview and useMergeEntities TanStack Query mutation hooks with proper cache invalidation
- OpenAPI TypeScript types manually updated for new schemas (generate-api-types.sh requires running backend)

### File List

**New files:**
- apps/web/src/components/graph/MergeEntityDialog.tsx
- apps/web/src/components/graph/MergeEntityDialog.test.tsx

**Modified files:**
- apps/api/app/schemas/entity.py -- Added EntityMergeRequest, EntityMergePreview, EntityMergeResponse
- apps/api/app/api/v1/entities.py -- Added POST merge/preview and POST merge endpoints, _validate_merge_request helper
- apps/api/app/exceptions.py -- Added EntityMergeError, EntityTypeMismatchError, EntitySelfMergeError
- apps/api/app/services/entity_query.py -- Added preview_merge(), merge_entities(), _fetch_duplicate_relationships, _merge_entities_tx, _validate_rel_type helpers
- apps/web/src/components/graph/EntityDetailCard.tsx -- Added Merge button and MergeEntityDialog integration
- apps/web/src/components/graph/EntityDetailCard.test.tsx -- Added merge button test
- apps/web/src/hooks/useEntityMutations.ts -- Added useMergeEntitiesPreview, useMergeEntities hooks
- apps/web/src/lib/api-types.generated.ts -- Added EntityMergeRequest, EntityMergePreview, EntityMergeResponse schemas and merge endpoint operations
- apps/api/tests/api/test_entities.py -- Added 11 new tests for merge preview and merge execution
