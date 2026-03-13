# Story 4.1: Graph API & Subgraph Queries

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an investigator,
I want the backend to serve graph data efficiently for visualization,
So that the frontend can load and display subgraphs on demand without fetching the entire graph.

## Acceptance Criteria

1. GIVEN an investigation has entities and relationships in Neo4j, WHEN a client sends `GET /api/v1/investigations/{id}/graph/` with pagination parameters, THEN the response returns a subgraph: nodes (entities) and edges (relationships) limited to the requested scope, AND nodes include: id, name, type, confidence_score, relationship_count (for hub detection), AND edges include: id, source, target, type, confidence_score, AND the response is structured for direct consumption by Cytoscape.js.

2. GIVEN a client requests neighborhood expansion, WHEN `GET /api/v1/investigations/{id}/graph/neighbors/{entity_id}` is called, THEN the response returns the entity's immediate neighbors and connecting edges, AND the response completes in <1 second.

3. GIVEN no entities exist yet (empty investigation or still processing), WHEN the graph endpoint is called, THEN an empty graph response is returned (empty nodes/edges arrays), AND no error is thrown.

## Tasks / Subtasks

- [x] **Task 1: Create graph response schemas** (AC: 1, 2, 3)
  - [x] 1.1: Create `apps/api/app/schemas/graph.py`
  - [x] 1.2: `GraphNode` — Cytoscape.js node element: `group: Literal["nodes"]`, `data: GraphNodeData` where `GraphNodeData` contains `id: str`, `name: str`, `type: str`, `confidence_score: float`, `relationship_count: int`
  - [x] 1.3: `GraphEdge` — Cytoscape.js edge element: `group: Literal["edges"]`, `data: GraphEdgeData` where `GraphEdgeData` contains `id: str`, `source: str`, `target: str`, `type: str`, `confidence_score: float`
  - [x] 1.4: `GraphResponse` — `nodes: list[GraphNode]`, `edges: list[GraphEdge]`, `total_nodes: int`, `total_edges: int`

- [x] **Task 2: Create GraphQueryService** (AC: 1, 2, 3)
  - [x] 2.1: Create `apps/api/app/services/graph_query.py` with class `GraphQueryService(neo4j_driver)`
  - [x] 2.2: `async def get_subgraph(investigation_id: UUID, limit: int = 50, offset: int = 0) -> GraphResponse` — returns hub nodes ordered by relationship_count DESC and all edges between them
  - [x] 2.3: `async def get_neighbors(investigation_id: UUID, entity_id: str) -> GraphResponse` — returns immediate neighbors of entity and connecting edges
  - [x] 2.4: Neo4j read transaction helpers: `_fetch_hub_nodes`, `_fetch_edges_between`, `_fetch_neighbors`, `_fetch_neighbor_edges`, `_fetch_total_counts`
  - [x] 2.5: Handle empty graph (no entities) gracefully — return empty nodes/edges arrays

- [x] **Task 3: Create graph API router** (AC: 1, 2, 3)
  - [x] 3.1: Create `apps/api/app/api/v1/graph.py` with router prefix `/investigations`, tags `["graph"]`
  - [x] 3.2: `GET /{investigation_id}/graph/` — query params: `limit: int = Query(50, ge=1, le=200)`, `offset: int = Query(0, ge=0)`. Returns `GraphResponse`.
  - [x] 3.3: `GET /{investigation_id}/graph/neighbors/{entity_id}` — returns `GraphResponse`. Raises `EntityNotFoundError` if entity not found.

- [x] **Task 4: Register graph router** (AC: 1, 2)
  - [x] 4.1: Add `from app.api.v1.graph import router as graph_router` in `app/api/v1/router.py`
  - [x] 4.2: Add `v1_router.include_router(graph_router)` after entities_router

- [x] **Task 5: Write backend tests** (AC: 1, 2, 3)
  - [x] 5.1: `tests/api/test_graph.py` — endpoint integration tests: subgraph returns nodes+edges, neighbors returns neighbors, empty graph returns empty arrays, 422 for non-UUID investigation_id, 404 for unknown entity in neighbors
  - [x] 5.2: `tests/services/test_graph_query.py` — service unit tests: hub detection ordering, edge filtering between hub nodes, neighbor expansion, empty investigation, relationship_count accuracy

- [x] **Task 6: Regenerate OpenAPI types** (AC: 1, 2)
  - [x] 6.1: Run `cd apps/api && uv run python -c "import app.main; import json; print(json.dumps(app.main.app.openapi()))" > /tmp/openapi.json`
  - [x] 6.2: Run `cd apps/web && pnpm openapi-typescript /tmp/openapi.json -o src/lib/api-types.generated.ts`

## Dev Notes

### Architecture Context

This is the **first story in Epic 4** (Graph Visualization & Exploration). It creates the backend API that Stories 4.2–4.5 will consume for the Cytoscape.js graph canvas, entity detail cards, filtering, and search highlighting.

**Existing entity pipeline (completed in Epics 2–3):**
```
PDF upload → text extraction → chunking → entity extraction (Ollama → Neo4j) → embedding (Qdrant)
```

**Neo4j graph state after processing:**
- **Entity nodes**: `Person`, `Organization`, `Location` — each with `id` (UUID), `name`, `type`, `confidence_score`, `investigation_id`, `created_at`
- **Entity-to-entity relationships**: `WORKS_FOR`, `KNOWS`, `LOCATED_AT` — each with `confidence_score`, `source_chunk_id`
- **Provenance edges**: `MENTIONED_IN` (entity → Document) — with `chunk_id`, `page_start`, `page_end`, `text_excerpt`
- **Document nodes**: `Document` — with `id`, `investigation_id`

This story adds **graph subgraph** and **neighbor expansion** endpoints that return data in Cytoscape.js element format.

### What Already Exists (DO NOT recreate)

| Component | Location | What It Does |
|-----------|----------|-------------|
| Entity list endpoint | `app/api/v1/entities.py` | `GET /{investigation_id}/entities/` — paginated entities with confidence |
| Entity detail endpoint | `app/api/v1/entities.py` | `GET /{investigation_id}/entities/{entity_id}` — full detail with relationships + sources |
| EntityQueryService | `app/services/entity_query.py` | Neo4j queries for entity list/detail (async read transactions) |
| Entity schemas | `app/schemas/entity.py` | `EntityListItem`, `EntityDetailResponse`, `EntityRelationship`, `EntitySource` |
| Neo4j async driver | `app/db/neo4j.py` | Module-level `driver` singleton (`AsyncGraphDatabase.driver`) |
| EntityNotFoundError | `app/exceptions.py` | 404 domain error — reuse for neighbors endpoint |
| Router registration | `app/api/v1/router.py` | `v1_router = APIRouter(prefix="/api/v1")` with `include_router()` pattern |

### Cytoscape.js Response Format

The API **MUST** return elements in Cytoscape.js compatible format. Each node/edge is an object with `group` and `data`:

```json
{
  "nodes": [
    {
      "group": "nodes",
      "data": {
        "id": "uuid-1",
        "name": "Deputy Mayor Horvat",
        "type": "Person",
        "confidence_score": 0.92,
        "relationship_count": 7
      }
    }
  ],
  "edges": [
    {
      "group": "edges",
      "data": {
        "id": "uuid-1-WORKS_FOR-uuid-2",
        "source": "uuid-1",
        "target": "uuid-2",
        "type": "WORKS_FOR",
        "confidence_score": 0.85
      }
    }
  ],
  "total_nodes": 150,
  "total_edges": 300
}
```

Frontend will pass `[...response.nodes, ...response.edges]` directly to `cy.add()` — zero transformation needed.

**Edge ID strategy:** Composite `{source_id}-{type}-{target_id}`. This is deterministic and unique per directed relationship. Do NOT use Neo4j internal element IDs (not stable across restarts).

**Node type field:** Return PascalCase as stored in Neo4j labels (`Person`, `Organization`, `Location`) — the frontend maps these to styles.

### Neo4j Query Design

**Query 1: Hub nodes (for `get_subgraph`)**

```cypher
MATCH (e:Person|Organization|Location {investigation_id: $investigation_id})
OPTIONAL MATCH (e)-[r:WORKS_FOR|KNOWS|LOCATED_AT]-({investigation_id: $investigation_id})
WITH e, labels(e)[0] AS type, COUNT(r) AS relationship_count
ORDER BY relationship_count DESC
SKIP $offset LIMIT $limit
RETURN e.id AS id, e.name AS name, type,
       e.confidence_score AS confidence_score, relationship_count
```

**Query 2: Edges between hub nodes (for `get_subgraph`)**

Pass the collected hub node IDs as `$node_ids` parameter:

```cypher
MATCH (src {investigation_id: $investigation_id})
      -[r:WORKS_FOR|KNOWS|LOCATED_AT]->
      (tgt {investigation_id: $investigation_id})
WHERE src.id IN $node_ids AND tgt.id IN $node_ids
RETURN src.id AS source, tgt.id AS target,
       type(r) AS type, r.confidence_score AS confidence_score
```

**Query 3: Total counts (for metadata)**

```cypher
MATCH (e:Person|Organization|Location {investigation_id: $investigation_id})
OPTIONAL MATCH (e)-[r:WORKS_FOR|KNOWS|LOCATED_AT]-({investigation_id: $investigation_id})
RETURN COUNT(DISTINCT e) AS total_nodes, COUNT(DISTINCT r) AS total_edges
```

Note: `total_edges` counts each relationship once (edges are directed). Using `COUNT(DISTINCT r)` to avoid double-counting from the undirected `OPTIONAL MATCH`.

**Query 4: Neighbors (for `get_neighbors`)**

Traverse both directions — entity could be source or target:

```cypher
MATCH (e {id: $entity_id, investigation_id: $investigation_id})
      -[r:WORKS_FOR|KNOWS|LOCATED_AT]-
      (neighbor {investigation_id: $investigation_id})
WITH neighbor, r, labels(neighbor)[0] AS type
OPTIONAL MATCH (neighbor)-[r2:WORKS_FOR|KNOWS|LOCATED_AT]-({investigation_id: $investigation_id})
RETURN neighbor.id AS id, neighbor.name AS name, type,
       neighbor.confidence_score AS confidence_score,
       COUNT(r2) AS relationship_count,
       startNode(r).id AS rel_source, endNode(r).id AS rel_target,
       type(r) AS rel_type, r.confidence_score AS rel_confidence
```

This returns each neighbor with its relationship_count AND the connecting edge data in one query. The service splits this into GraphNode + GraphEdge lists.

**Important:** Use undirected match `-[r:...]-` for neighbors (not `->`) so both incoming and outgoing relationships are included. The edge `source`/`target` in the response must reflect the actual direction stored in Neo4j (use `startNode(r)` and `endNode(r)`).

### Service Architecture

```python
class GraphQueryService:
    def __init__(self, neo4j_driver):
        self.neo4j_driver = neo4j_driver

    async def get_subgraph(self, investigation_id: UUID, limit: int, offset: int) -> GraphResponse:
        # 1. Fetch hub nodes (ordered by relationship_count DESC)
        # 2. If no nodes → return empty GraphResponse
        # 3. Collect node IDs
        # 4. Fetch edges between those node IDs
        # 5. Fetch total counts for metadata
        # 6. Build and return GraphResponse

    async def get_neighbors(self, investigation_id: UUID, entity_id: str) -> GraphResponse:
        # 1. Verify entity exists (return None if not found)
        # 2. Fetch neighbors + connecting edges
        # 3. Build GraphResponse (include the expanded entity itself as a node)
        # 4. Return
```

**Key difference from EntityQueryService:** No PostgreSQL dependency. GraphQueryService only needs `neo4j_driver` (no `db: AsyncSession`). All data comes from Neo4j.

### API Router Pattern

Follow the exact pattern from `entities.py`:

```python
import uuid
from fastapi import APIRouter, Query
from app.db.neo4j import driver as neo4j_driver
from app.exceptions import EntityNotFoundError
from app.schemas.graph import GraphResponse
from app.services.graph_query import GraphQueryService

router = APIRouter(prefix="/investigations", tags=["graph"])

@router.get("/{investigation_id}/graph/", response_model=GraphResponse)
async def get_subgraph(
    investigation_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    service = GraphQueryService(neo4j_driver)
    return await service.get_subgraph(investigation_id, limit=limit, offset=offset)

@router.get(
    "/{investigation_id}/graph/neighbors/{entity_id}",
    response_model=GraphResponse,
)
async def get_neighbors(
    investigation_id: uuid.UUID,
    entity_id: str,
):
    service = GraphQueryService(neo4j_driver)
    result = await service.get_neighbors(investigation_id, entity_id)
    if result is None:
        raise EntityNotFoundError(entity_id)
    return result
```

### Testing Strategy

**Endpoint tests (`tests/api/test_graph.py`):**
- Mock `GraphQueryService` at `app.api.v1.graph.GraphQueryService` (same pattern as `test_entities.py`)
- Test subgraph: returns 200 with nodes+edges, verify Cytoscape format (group field present)
- Test neighbors: returns 200, verify node + edge structure
- Test empty graph: returns 200 with empty arrays
- Test neighbors 404: entity not found
- Test 422: non-UUID investigation_id

**Service tests (`tests/services/test_graph_query.py`):**
- Mock Neo4j driver + session + `execute_read`
- Test hub detection: verify nodes sorted by relationship_count DESC
- Test edge filtering: only edges between requested hub nodes
- Test neighbor expansion: includes connecting edges with correct direction
- Test empty investigation: returns empty GraphResponse
- Test `get_neighbors` returns None for non-existent entity

**Test client fixture pattern** (reuse from `test_entities.py`):
```python
@pytest.fixture
def graph_client():
    from app.main import app
    yield TestClient(app)
```

No `get_db` override needed — GraphQueryService does not use PostgreSQL.

### Project Structure Notes

**New files:**
- `apps/api/app/schemas/graph.py` — GraphNode, GraphEdge, GraphResponse
- `apps/api/app/services/graph_query.py` — GraphQueryService
- `apps/api/app/api/v1/graph.py` — graph API router
- `apps/api/tests/api/test_graph.py` — endpoint tests
- `apps/api/tests/services/test_graph_query.py` — service tests

**Modified files:**
- `apps/api/app/api/v1/router.py` — add graph router import + include
- `apps/web/src/lib/api-types.generated.ts` — regenerated (new graph endpoints + schemas)

**No new Python packages needed.** All dependencies (FastAPI, Pydantic, neo4j async driver) are already available.

**No database migrations needed.** No PostgreSQL schema changes — this story only reads from Neo4j.

### References

- [Source: _bmad-output/planning-artifacts/epics.md — Epic 4, Story 4.1: Graph API & Subgraph Queries acceptance criteria]
- [Source: _bmad-output/planning-artifacts/architecture.md — API endpoints: GET /api/v1/investigations/{id}/graph/ for subgraph, GET /api/v1/investigations/{id}/graph/neighbors/{entity_id} for expansion]
- [Source: _bmad-output/planning-artifacts/architecture.md — FR23-FR30 mapping: graph visualization via Cytoscape.js, dynamic loading, no upper limit, viewport-based fetching]
- [Source: _bmad-output/planning-artifacts/architecture.md — Neo4j naming: node labels PascalCase (Person, Organization, Location), relationship types UPPER_SNAKE_CASE (WORKS_FOR, KNOWS, LOCATED_AT), properties snake_case]
- [Source: _bmad-output/planning-artifacts/architecture.md — Frontend architecture: custom useCytoscape hook, Cytoscape.js data format with group/data structure]
- [Source: _bmad-output/planning-artifacts/architecture.md — GraphQueryService in app/services/graph_query.py, GraphCanvas.tsx in src/components/graph/]
- [Source: _bmad-output/planning-artifacts/prd.md — NFR9: Graph render up to 500 nodes in <2s; NFR10: Node expansion <1s; NFR11: Entity search <500ms]
- [Source: _bmad-output/planning-artifacts/prd.md — FR23: interactive graph; FR24: dynamic loading no upper limit; FR25: entity detail card; FR27: expand neighborhood]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — Graph Canvas: entity type colors (Person=#6b9bd2, Org=#7dab8f, Location=#c4a265); node shapes (circle/diamond/triangle); border thickness = confidence]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — Split view: Q&A 40% left, Graph 60% right; Graph-First Landing with hub entities]
- [Source: apps/api/app/services/entity_query.py — Async Neo4j read transaction pattern: async with driver.session() as session → session.execute_read(tx_fn, params)]
- [Source: apps/api/app/api/v1/entities.py — Router pattern: APIRouter(prefix="/investigations", tags=[...]), service instantiation with neo4j_driver]
- [Source: apps/api/app/exceptions.py — EntityNotFoundError(entity_id) for 404 responses, DomainError base with RFC 7807 format]
- [Source: apps/api/app/api/v1/router.py — Router aggregation: v1_router.include_router(router) pattern]
- [Source: apps/api/tests/api/test_entities.py — Test pattern: patch service class at module path, AsyncMock service methods, TestClient]

### Previous Story Intelligence (Story 3.5 Learnings)

1. **Class-based services with injected dependencies** — Follow `EntityQueryService(neo4j_driver, db)` pattern. `GraphQueryService` only needs `neo4j_driver` (no db).

2. **Async Neo4j read transactions** — Use `session.execute_read(tx_fn, ...)` pattern where `tx_fn` is an async function that receives `tx` and runs queries via `await tx.run(query, **params)`.

3. **Neo4j result handling** — `await result.data()` returns list of dicts. `await result.single()` returns one dict or None.

4. **Entity type whitelist validation** — Story 3.5 added `ALLOWED_ENTITY_TYPES` validation in entities.py to prevent Cypher injection. Apply same discipline in graph queries — never interpolate user input into Cypher strings. Use parameterized queries only.

5. **Test pattern** — Patch the service class at the API module path: `patch("app.api.v1.graph.GraphQueryService")`. Return `AsyncMock()` with methods returning schema instances.

6. **Tests at 229 backend, 85 frontend after Story 3.5** — All must continue to pass.

7. **Frontend type regeneration** — After backend changes, run `pnpm openapi-typescript` to regenerate `api-types.generated.ts`. Story 4.2 will consume the new graph types.

8. **RFC 7807 error format** — All errors use `DomainError` → `domain_error_handler` returning `{type, title, status, detail, instance}`. EntityNotFoundError already implements this.

### Git Intelligence

Recent commits:
- `3ad8318` — feat: Story 3.5 — document-level & entity-level confidence display with code review fixes
- `ba02706` — fix: make Qdrant/Neo4j clients fork-safe for Celery prefork workers
- `c9cbaf2` — chore: add dev data reset script
- `1e10443` — feat: Story 3.4 — vector embedding generation & storage with code review fixes
- `56f8359` — feat: Story 3.3 — provenance chain evidence storage with code review fixes

**Patterns to continue:**
- Services: class-based with injected deps, async methods
- Tests: mirror source paths (`tests/services/test_graph_query.py` ↔ `app/services/graph_query.py`)
- Schemas: Pydantic BaseModel with explicit field types
- API router: prefix pattern from existing routers, Query() for pagination params
- Commit message: `feat: Story 4.1 — graph API & subgraph queries`

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

None — clean implementation with no blockers.

### Completion Notes List

- Created Cytoscape.js-compatible Pydantic schemas (`GraphNode`, `GraphEdge`, `GraphResponse`) with `group`/`data` structure for zero-transformation frontend consumption.
- Implemented `GraphQueryService` with `get_subgraph()` (hub-first pagination ordered by relationship_count DESC) and `get_neighbors()` (entity expansion with bidirectional traversal).
- Neo4j read transaction helpers use parameterized queries only (no Cypher injection risk). Edge IDs use deterministic `{source}-{type}-{target}` composite keys.
- Empty graph cases return empty arrays with 200 status (no errors thrown).
- `get_neighbors()` returns `None` for non-existent entities, triggering `EntityNotFoundError` (404) at the router level.
- Null confidence scores from Neo4j default to `0.0`.
- 22 backend tests (10 API integration + 12 service unit), all passing. Full suite: 251 backend + 85 frontend = 336 total, zero regressions.
- OpenAPI TypeScript types regenerated for frontend consumption in Story 4.2.

### Change Log

- 2026-03-13: Story 4.1 implementation — graph API subgraph & neighbor expansion endpoints
- 2026-03-13: Code review fixes — added entity label filters to Neo4j queries, limit param to neighbors endpoint, consistent total_nodes/total_edges semantics, 3 new tests

### File List

**New files:**
- `apps/api/app/schemas/graph.py` — GraphNode, GraphEdge, GraphResponse Pydantic schemas
- `apps/api/app/services/graph_query.py` — GraphQueryService with Neo4j read transaction helpers
- `apps/api/app/api/v1/graph.py` — Graph API router (subgraph + neighbors endpoints)
- `apps/api/tests/api/test_graph.py` — 10 endpoint integration tests
- `apps/api/tests/services/test_graph_query.py` — 12 service unit tests

**Modified files:**
- `apps/api/app/api/v1/router.py` — Added graph router import + include_router
- `apps/web/src/lib/api-types.generated.ts` — Regenerated with new graph endpoints/schemas
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — Story status updated
