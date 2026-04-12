# Story 8.1: Manual Entity Creation & Editing

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an investigator,
I want to manually create new entities and edit existing ones in my knowledge graph,
So that I can add information I found through manual reading and correct extraction errors.

## Acceptance Criteria

1. **GIVEN** the investigator is viewing the graph or entity list, **WHEN** they click "Add Entity", **THEN** a form presents fields for: name, type (person/organization/location), and optional properties, **AND** the investigator can add a source annotation (free text describing where the information came from), **AND** the entity is created in Neo4j with `source="manual"` to distinguish it from LLM-extracted entities, **AND** the new entity appears in the graph immediately.

2. **GIVEN** the API receives `POST /api/v1/investigations/{id}/entities/`, **WHEN** the request contains a valid entity with name, type, and optional properties, **THEN** the entity is persisted in Neo4j with a UUID, `confidence_score=1.0` (manually created = high confidence), and `investigation_id`, **AND** if a source annotation is provided, it's stored as a property on the entity node, **AND** the response follows the existing entity schema.

3. **GIVEN** the investigator views an Entity Detail Card (from MVP), **WHEN** they click "Edit" on the entity, **THEN** they can modify the entity name and properties, **AND** changes are persisted via `PATCH /api/v1/investigations/{id}/entities/{entity_id}`, **AND** edit history is preserved (previous name stored as `aliases` property on the entity), **AND** the graph updates immediately to reflect the new name.

4. **GIVEN** the investigator edits an entity that has relationships and citations, **WHEN** the name is changed, **THEN** all existing relationships remain intact — only the entity name/properties change, **AND** source citations and provenance chains are not affected.

## Tasks / Subtasks

- [x] **Task 1: Add entity create/update schemas** (AC: 2, 3)
  - [x] 1.1: In `apps/api/app/schemas/entity.py`, add `EntityCreateRequest(BaseModel)` with fields: `name: str`, `type: str` (validated against person/organization/location), `source_annotation: str | None = None`
  - [x] 1.2: Add `EntityUpdateRequest(BaseModel)` with fields: `name: str | None = None`, `source_annotation: str | None = None` (partial update — only provided fields change)
  - [x] 1.3: Update `EntityDetailResponse` to include `source: str` (value: "manual" or "extracted"), `source_annotation: str | None`, and `aliases: list[str]` fields
  - [x] 1.4: Update `EntityListItem` to include `source: str` field so the frontend can distinguish manual vs extracted entities
  - [x] 1.5: Regenerate OpenAPI types: run `scripts/generate-api-types.sh` to update `apps/web/src/lib/api-types.generated.ts`

- [x] **Task 2: Add entity create/update methods to EntityQueryService** (AC: 2, 3, 4)
  - [x] 2.1: In `apps/api/app/services/entity_query.py`, add method `create_entity(investigation_id, name, type, source_annotation) -> EntityDetailResponse`
  - [x] 2.2: The create method must: generate UUID via `uuid.uuid4()`, determine Neo4j label from type (`person` → `Person`, `organization` → `Organization`, `location` → `Location`), run a CREATE (not MERGE) query since manual entities should always create a new node, set properties: `id`, `name`, `type`, `investigation_id`, `confidence_score=1.0`, `source="manual"`, `source_annotation`, `aliases=[]`, `created_at=datetime()`
  - [x] 2.3: Handle duplicate entity — if an entity with the same name, type, and investigation_id already exists (uniqueness constraint), catch the `ConstraintError` from Neo4j and raise a descriptive `DomainError` (409 Conflict) telling the user an entity with that name and type already exists
  - [x] 2.4: Add method `update_entity(investigation_id, entity_id, name, source_annotation) -> EntityDetailResponse`
  - [x] 2.5: The update method must: fetch the existing entity first (return None/404 if not found), if `name` is changed, append the old name to the `aliases` list property on the Neo4j node using `SET e.aliases = e.aliases + [$old_name]`, update name and/or source_annotation in a single MATCH + SET query, return updated entity detail
  - [x] 2.6: For the update query, relationships are NOT affected — only the entity node properties change. The Neo4j MATCH + SET pattern naturally preserves all relationships since we're modifying node properties, not deleting/recreating the node

- [x] **Task 3: Add entity create/update API endpoints** (AC: 2, 3)
  - [x] 3.1: In `apps/api/app/api/v1/entities.py`, add `POST /{investigation_id}/entities/` endpoint that accepts `EntityCreateRequest` body, validates entity type against `ALLOWED_ENTITY_TYPES`, calls `EntityQueryService.create_entity()`, returns `EntityDetailResponse` with 201 status
  - [x] 3.2: Add `PATCH /{investigation_id}/entities/{entity_id}` endpoint that accepts `EntityUpdateRequest` body, calls `EntityQueryService.update_entity()`, returns `EntityDetailResponse` with 200 status
  - [x] 3.3: For the PATCH endpoint, if entity not found, raise `EntityNotFoundError(entity_id)` (existing exception, returns 404)
  - [x] 3.4: Add `EntityDuplicateError` to `app/exceptions.py` — `DomainError` subclass with `status_code=409`, `error_type="entity_duplicate"`, detail message like `"Entity with name '{name}' and type '{type}' already exists in this investigation"`

- [x] **Task 4: Update existing entity read queries to return new fields** (AC: 2, 3)
  - [x] 4.1: In `_fetch_entity_list()` (entity_query.py line 175), add `e.source AS source` to the RETURN clause so list items include source field
  - [x] 4.2: In `_fetch_entity()` (entity_query.py line 204), add `e.source AS source, e.source_annotation AS source_annotation, e.aliases AS aliases` to the RETURN clause
  - [x] 4.3: In `list_entities()`, pass `source` to `EntityListItem` constructor — default to `"extracted"` for entities that don't have the field (backward compat with pre-existing entities that were created before this story)
  - [x] 4.4: In `get_entity_detail()`, pass `source`, `source_annotation`, `aliases` to `EntityDetailResponse` — default `source` to `"extracted"`, `source_annotation` to `None`, `aliases` to `[]` for pre-existing entities

- [x] **Task 5: Create "Add Entity" dialog component** (AC: 1)
  - [x] 5.1: Create `apps/web/src/components/graph/AddEntityDialog.tsx` — a shadcn/ui `Dialog` component with a form containing: `name` input (required), `type` select/radio group (person/organization/location, required), `source_annotation` textarea (optional, placeholder: "Where did you find this information?")
  - [x] 5.2: Use shadcn/ui components already installed: `Dialog`, `Input`, `Label`, `Button`. For the entity type selector, use 3 radio-style toggle buttons with the entity type colored dots (reusing `ENTITY_COLORS` from `@/lib/entity-constants`)
  - [x] 5.3: Form validation: name is required and must be non-empty after trimming, type must be selected. Show inline validation errors
  - [x] 5.4: On submit, call the POST endpoint via a TanStack Query mutation. On success: close dialog, invalidate entity list and graph data queries so the new entity appears immediately, show no toast (the entity appearing in the graph IS the feedback)
  - [x] 5.5: On error, display the error detail from the API response in the dialog (e.g., "Entity with name 'X' and type 'person' already exists in this investigation")
  - [x] 5.6: Dialog follows UX modal patterns: max-width ~420px, focus trapped, close via X/Escape/backdrop, fade-in 150ms

- [x] **Task 6: Create "Edit Entity" dialog component** (AC: 3, 4)
  - [x] 6.1: Create `apps/web/src/components/graph/EditEntityDialog.tsx` — a shadcn/ui `Dialog` component pre-filled with the entity's current name and source_annotation
  - [x] 6.2: Entity type is NOT editable (changing type would require label change in Neo4j and could break existing uniqueness constraints). Display current type as read-only with colored dot
  - [x] 6.3: Show current aliases (if any) as read-only chips below the name field, labeled "Previous names"
  - [x] 6.4: On submit, call the PATCH endpoint via a TanStack Query mutation. On success: close dialog, invalidate entity detail + entity list + graph data queries so the updated name appears everywhere immediately
  - [x] 6.5: On error, display the error detail from the API response in the dialog

- [x] **Task 7: Add "Edit" button to Entity Detail Card** (AC: 3)
  - [x] 7.1: In `apps/web/src/components/graph/EntityDetailCard.tsx`, add a `Pencil` (lucide-react) icon button in the header next to the close button
  - [x] 7.2: Clicking "Edit" opens the `EditEntityDialog` with the current entity data pre-populated
  - [x] 7.3: The EntityDetailCard needs to manage the edit dialog open state — add `useState` for `editDialogOpen`
  - [x] 7.4: Pass an `onEntityUpdated` callback prop (or rely on query invalidation) to refresh the card data after edit

- [x] **Task 8: Add "Add Entity" button to graph toolbar** (AC: 1)
  - [x] 8.1: In `apps/web/src/components/graph/GraphCanvas.tsx`, add a `Plus` (lucide-react) icon button next to the existing search button (top-right area, line ~608-617)
  - [x] 8.2: Clicking the button opens the `AddEntityDialog`
  - [x] 8.3: Manage dialog open state in GraphCanvas — add `useState` for `addEntityOpen`
  - [x] 8.4: The "Add Entity" button should only show when the graph is loaded (same condition as search button: `cy && !overlay`)

- [x] **Task 9: Add TanStack Query mutations** (AC: 1, 3)
  - [x] 9.1: Create `apps/web/src/hooks/useEntityMutations.ts` with `useCreateEntity(investigationId)` mutation hook — calls `POST /api/v1/investigations/{investigationId}/entities/`, on success invalidates query keys: `["entities", investigationId]` and `["graph", investigationId]`
  - [x] 9.2: Add `useUpdateEntity(investigationId)` mutation hook — calls `PATCH /api/v1/investigations/{investigationId}/entities/{entityId}`, on success invalidates query keys: `["entities", investigationId]`, `["entity", investigationId, entityId]`, and `["graph", investigationId]`
  - [x] 9.3: Use `openapi-fetch` client (`apiClient`) for both mutations to maintain type safety with generated types

- [x] **Task 10: Backend tests** (AC: 1, 2, 3, 4)
  - [x] 10.1: In `apps/api/tests/api/test_entities.py`, add test: `POST /investigations/{id}/entities/` with valid body → 201, response has `source="manual"`, `confidence_score=1.0`, correct name/type
  - [x] 10.2: Add test: POST with missing `name` → 422 validation error
  - [x] 10.3: Add test: POST with invalid `type` (e.g., "vehicle") → 422
  - [x] 10.4: Add test: POST with duplicate name+type → 409 with descriptive error
  - [x] 10.5: Add test: `PATCH /investigations/{id}/entities/{entity_id}` with new name → 200, old name in `aliases` array, relationships preserved
  - [x] 10.6: Add test: PATCH with non-existent entity_id → 404
  - [x] 10.7: Add test: PATCH with only `source_annotation` change → 200, name unchanged, aliases unchanged
  - [x] 10.8: Add test: GET entity list includes `source` field for both manual and extracted entities
  - [x] 10.9: Add test: GET entity detail includes `source`, `source_annotation`, `aliases` fields

- [x] **Task 11: Frontend tests** (AC: 1, 3)
  - [x] 11.1: Create `apps/web/src/components/graph/AddEntityDialog.test.tsx` — test: form renders with name, type, annotation fields
  - [x] 11.2: Add test: submit button disabled when name empty
  - [x] 11.3: Add test: successful submission closes dialog
  - [x] 11.4: Create `apps/web/src/components/graph/EditEntityDialog.test.tsx` — test: form pre-populated with entity data
  - [x] 11.5: Add test: entity type field is read-only
  - [x] 11.6: In `EntityDetailCard.test.tsx`, add test: edit button present and opens edit dialog

## Dev Notes

### Architecture Context

This is **Story 8.1** — the first story in Epic 8 (Manual Entity Curation & Disambiguation). This story adds manual entity creation and editing to the existing graph, giving investigators direct control over the knowledge graph. All MVP infrastructure (Epics 1-6) is complete. Epic 7 (Image OCR) is in progress.

**FRs covered:** FR52 (manual entity creation with source annotation), FR53 (entity name/property editing)
**NFRs relevant:** NFR34 (atomic operations — entity updates must be complete or rolled back), all existing MVP NFRs for data integrity and provenance

### What Already Exists — DO NOT RECREATE

| Component | Location | What It Does |
|---|---|---|
| Entity read endpoints | `app/api/v1/entities.py` | GET list + GET detail (no POST/PATCH yet) |
| Entity schemas | `app/schemas/entity.py` | EntityListItem, EntityDetailResponse, EntityRelationship, EntitySource |
| Entity query service | `app/services/entity_query.py` | list_entities(), get_entity_detail() with Neo4j async reads |
| Entity extraction service | `app/services/extraction.py` | LLM-based extraction → Neo4j storage (MERGE pattern) |
| Neo4j constraints | `app/services/extraction.py:233-267` | Uniqueness: (name, type, investigation_id), indexes on id and investigation_id |
| EntityDetailCard | `components/graph/EntityDetailCard.tsx` | Floating card with entity name, type, confidence, relationships, sources, "Ask about" action |
| GraphCanvas | `components/graph/GraphCanvas.tsx` | Graph visualization with search button, filter panel, entity/edge detail cards |
| Entity search | `components/graph/EntitySearchCommand.tsx` | Command palette search for entities |
| Entity hooks | `hooks/useEntities.ts`, `hooks/useEntityDetail.ts` | TanStack Query hooks for entity list and detail |
| Graph hooks | `hooks/useGraphData.ts` | TanStack Query hooks for graph data and neighbor expansion |
| DomainError + handler | `app/exceptions.py` | Base exception with RFC 7807 formatting, EntityNotFoundError already exists |
| shadcn/ui Dialog | `components/ui/dialog.tsx` | Dialog component already installed and available |
| shadcn/ui Input/Label/Button | `components/ui/input.tsx`, `label.tsx`, `button.tsx` | Form components already installed |
| Entity colors | `lib/entity-constants.ts` | ENTITY_COLORS map: person=#6b9bd2, organization=#c4a265, location=#7dab8f |
| OpenAPI type gen script | `scripts/generate-api-types.sh` | Generates TypeScript types from FastAPI OpenAPI spec |
| API client | `lib/api-client.ts` | openapi-fetch configured instance |

### Critical Implementation Details

#### Neo4j Entity Node Structure

**Current node properties (LLM-extracted entities):**
```
(:Person|Organization|Location {
  id: "uuid",
  name: "Deputy Mayor Horvat",
  type: "person",
  investigation_id: "uuid",
  confidence_score: 0.85,
  created_at: datetime()
})
```

**New node properties (manual entities — Story 8.1 additions):**
```
(:Person|Organization|Location {
  id: "uuid",
  name: "Deputy Mayor Horvat",
  type: "person",
  investigation_id: "uuid",
  confidence_score: 1.0,          // Always 1.0 for manual
  source: "manual",               // NEW — "manual" or absent (= "extracted")
  source_annotation: "Found in...",// NEW — optional free text
  aliases: ["Dep. Mayor Horvat"], // NEW — previous names from edits
  created_at: datetime()
})
```

**Backward compatibility:** Pre-existing LLM-extracted entities do NOT have `source`, `source_annotation`, or `aliases` properties. The read queries must handle missing properties gracefully by defaulting: `source` → `"extracted"`, `source_annotation` → `null`, `aliases` → `[]`.

In Neo4j, accessing a missing property returns `null`, so use `COALESCE(e.source, "extracted")` in Cypher, or handle at the Python layer with `.get("source") or "extracted"`.

#### Entity Creation — CREATE vs MERGE

The extraction service uses `MERGE` to avoid duplicates when the same entity appears in multiple chunks. For manual creation, use `CREATE` because:
1. If the name+type+investigation combo already exists (uniqueness constraint), we WANT it to fail with a clear error — the user should be told the entity exists, not silently merged
2. The Neo4j uniqueness constraint `(name, type, investigation_id) IS UNIQUE` will throw a `ConstraintError` on duplicate — catch this and convert to a 409 Conflict response

Cypher for creation:
```cypher
CREATE (e:Person {
  id: $id,
  name: $name,
  type: $type,
  investigation_id: $investigation_id,
  confidence_score: 1.0,
  source: "manual",
  source_annotation: $source_annotation,
  aliases: [],
  created_at: datetime()
})
RETURN e.id AS id, e.name AS name, labels(e)[0] AS type,
       e.confidence_score AS confidence_score, e.source AS source,
       e.source_annotation AS source_annotation, e.aliases AS aliases
```

#### Entity Update — Name Change with Alias Tracking

When the name changes, append the old name to `aliases` before updating:

```cypher
MATCH (e:Person|Organization|Location {id: $entity_id, investigation_id: $investigation_id})
SET e.name = $new_name,
    e.aliases = COALESCE(e.aliases, []) + [$old_name],
    e.source_annotation = CASE WHEN $source_annotation IS NOT NULL
                           THEN $source_annotation
                           ELSE e.source_annotation END
RETURN e.id AS id, e.name AS name, labels(e)[0] AS type,
       e.confidence_score AS confidence_score, e.source AS source,
       e.source_annotation AS source_annotation, e.aliases AS aliases
```

**Important:** The MATCH uses `id` + `investigation_id`, NOT `name`, so relationships (which connect by node identity, not name) are unaffected by the name change. Neo4j relationships connect to nodes, not to property values.

**Type is NOT editable.** Changing entity type would require changing the Neo4j node label (Person → Organization), which is a complex operation that could break the uniqueness constraint. Defer type change to a future story if needed.

#### Uniqueness Constraint Handling

The existing constraint `(name, type, investigation_id) IS UNIQUE` means:
- Creating "Deputy Mayor Horvat" / person / investigation-123 → succeeds
- Creating "Deputy Mayor Horvat" / person / investigation-123 again → fails
- Creating "Deputy Mayor Horvat" / organization / investigation-123 → succeeds (different type)
- Creating "Deputy Mayor Horvat" / person / investigation-456 → succeeds (different investigation)

When a name is updated and the new name conflicts with an existing entity of the same type in the same investigation, Neo4j will throw a ConstraintError. Catch this the same way as create — return 409.

#### Frontend Dialog Patterns

Per UX spec (lines 1254-1296):
- Full modal centered with backdrop dimming (`rgba(0,0,0,0.6)`)
- Max-width: 420px for form dialogs
- Focus trapped inside (shadcn/ui Dialog handles this natively with Radix UI)
- Close via: X button, Escape key, backdrop click
- Body scroll locked
- Entrance: fade in 150ms. Exit: fade out 100ms.
- Never stack modals — one at a time

The "Add Entity" and "Edit Entity" dialogs should follow the same pattern as `CreateInvestigationDialog.tsx` in `components/investigation/`.

#### Graph Refresh After Entity Changes

After creating or editing an entity, invalidate these TanStack Query keys:
- `["entities", investigationId]` — refreshes entity list (used by entity search, GraphFilterPanel)
- `["entity", investigationId, entityId]` — refreshes entity detail card (for edits)
- `["graph", investigationId]` — refreshes graph data (so new entity appears as a node)

TanStack Query invalidation triggers automatic refetch. The Cytoscape graph will re-render when `useGraphData` returns updated data.

#### SSE Event for Entity Changes (optional optimization)

The story does not explicitly require SSE events for entity changes, but publishing an `entity.created` or `entity.updated` SSE event would allow other open tabs or future features to react. This is a nice-to-have, not required for AC compliance. Skip for now to reduce scope.

### Project Structure Notes

**New files:**
- `apps/api/app/services/entity_mutation.py` — Entity create/update service (separate from entity_query.py to maintain read/write separation)
- `apps/web/src/components/graph/AddEntityDialog.tsx` — Add entity form dialog
- `apps/web/src/components/graph/EditEntityDialog.tsx` — Edit entity form dialog
- `apps/web/src/hooks/useEntityMutations.ts` — TanStack Query mutation hooks for create/update

**Modified files:**
- `apps/api/app/schemas/entity.py` — Add EntityCreateRequest, EntityUpdateRequest, extend responses
- `apps/api/app/api/v1/entities.py` — Add POST and PATCH endpoints
- `apps/api/app/exceptions.py` — Add EntityDuplicateError
- `apps/api/app/services/entity_query.py` — Update read queries to return source/aliases fields
- `apps/web/src/components/graph/EntityDetailCard.tsx` — Add "Edit" button
- `apps/web/src/components/graph/GraphCanvas.tsx` — Add "Add Entity" button
- `apps/web/src/lib/api-types.generated.ts` — Regenerated (auto)
- `apps/api/tests/api/test_entities.py` — New entity creation/update tests
- `apps/web/src/components/graph/AddEntityDialog.test.tsx` — New
- `apps/web/src/components/graph/EditEntityDialog.test.tsx` — New
- `apps/web/src/components/graph/EntityDetailCard.test.tsx` — Updated with edit button test

### Important Patterns from Previous Stories

1. **Neo4j async for reads, sync for writes in worker** — For API-driven writes (this story), use `async with self.neo4j_driver.session() as session:` and `await session.execute_write(tx_function, ...)`. The extraction service uses sync sessions because it runs inside Celery workers — this story's write operations run inside FastAPI async endpoints.
2. **SSE events are best-effort** — `_publish_safe()` wrapper never raises. If adding SSE events for entity changes, use this pattern.
3. **RFC 7807 error format** — `{type, title, status, detail, instance}` via `DomainError` subclasses. The new `EntityDuplicateError` follows this pattern exactly.
4. **Service layer pattern** — Business logic in `app/services/`, API routes orchestrate services. Do NOT put Neo4j Cypher queries directly in route handlers.
5. **Loguru structured logging** — `logger.info("Message", key=value, key2=value2)`.
6. **Commit pattern** — `feat: Story X.Y — description`.
7. **Backend test baselines** — ~316+ backend tests, ~225+ frontend tests.
8. **Pre-existing test failures** — `SystemStatusPage.test.tsx` (4 failures), `test_docker_compose.py` (2 infra), `test_entity_discovered_sse_events_published` (1 mock). Do not fix these.
9. **OpenAPI type generation** — run `scripts/generate-api-types.sh` after any schema change.
10. **TanStack Query invalidation** — Use `queryClient.invalidateQueries({ queryKey: [...] })` in mutation `onSuccess` callbacks.
11. **Entity type colors** — `ENTITY_COLORS` in `lib/entity-constants.ts`: person=#6b9bd2, organization=#c4a265, location=#7dab8f.
12. **Forms** — Per architecture decision, MVP uses `useState` + controlled inputs. No form library. Same pattern should be followed here.
13. **shadcn/ui Dialog** — Already installed. Import from `@/components/ui/dialog`. Uses Radix UI under the hood with focus trapping and backdrop close.

### References

- [Source: _bmad-output/planning-artifacts/epics-phase2.md — Epic 8, Story 8.1 acceptance criteria]
- [Source: _bmad-output/planning-artifacts/epics-phase2.md — FR52 (manual entity creation), FR53 (entity editing)]
- [Source: _bmad-output/planning-artifacts/architecture.md — Lines 66-77: Tech stack, Neo4j, FastAPI]
- [Source: _bmad-output/planning-artifacts/architecture.md — Lines 288-306: API endpoint structure — entity endpoints at /investigations/{id}/entities/]
- [Source: _bmad-output/planning-artifacts/architecture.md — Lines 399-424: Naming conventions — Neo4j labels PascalCase, types UPPER_SNAKE_CASE, properties snake_case]
- [Source: _bmad-output/planning-artifacts/architecture.md — Lines 486-496: Error handling patterns — DomainError subclasses, RFC 7807]
- [Source: _bmad-output/planning-artifacts/architecture.md — Lines 315-326: SSE event format and types]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — Lines 851-899: Entity Detail Card anatomy and interactions]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — Lines 1248-1296: Modal & Overlay patterns — centered dialog, focus trap, close behaviors]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — Lines 1204-1217: Confidence indicators — High/Medium/Low visual language]
- [Source: apps/api/app/schemas/entity.py — Current entity schemas: EntityListItem, EntityDetailResponse]
- [Source: apps/api/app/api/v1/entities.py — Current GET-only endpoints, ALLOWED_ENTITY_TYPES set]
- [Source: apps/api/app/services/entity_query.py — Neo4j read queries, async session pattern]
- [Source: apps/api/app/services/extraction.py:150-228 — Neo4j MERGE pattern for entity storage]
- [Source: apps/api/app/services/extraction.py:233-267 — Neo4j constraints: uniqueness on (name, type, investigation_id)]
- [Source: apps/api/app/exceptions.py — DomainError base, EntityNotFoundError pattern]
- [Source: apps/web/src/components/graph/EntityDetailCard.tsx — Full component with header, relationships, sources, actions]
- [Source: apps/web/src/components/graph/GraphCanvas.tsx:580-659 — Graph render with toolbar buttons and entity detail card]
- [Source: apps/web/src/hooks/useEntities.ts — Entity list TanStack Query hook]
- [Source: apps/web/src/hooks/useEntityDetail.ts — Entity detail TanStack Query hook]
- [Source: apps/web/src/hooks/useGraphData.ts — Graph data + expand neighbors hooks]
- [Source: _bmad-output/implementation-artifacts/7-1-image-upload-tesseract-ocr-text-extraction.md — Previous story patterns and conventions]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

- Backend tests: 363 passed (excluding pre-existing docker_compose and process_document failures)
- Entity tests: 20 passed (10 existing + 10 new)
- Frontend tests: 263 passed (excluding 4 pre-existing SystemStatusPage failures)
- New frontend tests: AddEntityDialog (3), EditEntityDialog (3), EntityDetailCard edit button (1)
- Code review: 3 HIGH + 4 MEDIUM issues found and fixed (2026-04-12)

### Completion Notes List

- Implemented full entity CRUD backend: EntityCreateRequest/EntityUpdateRequest schemas with Pydantic validators, POST/PATCH endpoints, create_entity/update_entity service methods with Neo4j async write transactions
- Added EntityDuplicateError (409) for uniqueness constraint violations
- Added backward-compatible source/source_annotation/aliases fields to entity read queries — pre-existing entities default to source="extracted"
- Created AddEntityDialog with entity type radio buttons (colored dots), name input, source annotation textarea, inline validation, error display from API
- Created EditEntityDialog with pre-populated fields, read-only entity type, alias chips display
- Added Pencil edit button to EntityDetailCard header
- Added Plus "Add Entity" button to GraphCanvas toolbar next to search
- Created useEntityMutations hook with useCreateEntity/useUpdateEntity TanStack Query mutations with proper cache invalidation
- OpenAPI TypeScript types regenerated

### File List

**New files:**
- apps/api/app/services/entity_query.py (write transaction helpers added)
- apps/web/src/components/graph/AddEntityDialog.tsx
- apps/web/src/components/graph/AddEntityDialog.test.tsx
- apps/web/src/components/graph/EditEntityDialog.tsx
- apps/web/src/components/graph/EditEntityDialog.test.tsx
- apps/web/src/hooks/useEntityMutations.ts

**Modified files:**
- apps/api/app/schemas/entity.py — Added EntityCreateRequest, EntityUpdateRequest, extended EntityDetailResponse and EntityListItem with source/aliases fields
- apps/api/app/api/v1/entities.py — Added POST and PATCH endpoints
- apps/api/app/exceptions.py — Added EntityDuplicateError
- apps/api/app/services/entity_query.py — Added create_entity, update_entity methods; updated read queries to return source/aliases fields; added _create_entity and _update_entity write transaction helpers
- apps/web/src/components/graph/EntityDetailCard.tsx — Added Pencil edit button and EditEntityDialog integration
- apps/web/src/components/graph/EntityDetailCard.test.tsx — Added edit button test
- apps/web/src/components/graph/GraphCanvas.tsx — Added Plus add entity button and AddEntityDialog integration
- apps/web/src/lib/api-types.generated.ts — Regenerated with new entity schemas
- apps/api/tests/api/test_entities.py — Added 10 new tests for create, update, duplicate, field validation
