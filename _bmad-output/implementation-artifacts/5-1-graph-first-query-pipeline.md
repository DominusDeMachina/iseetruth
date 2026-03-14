# Story 5.1: GRAPH FIRST Query Pipeline

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an investigator,
I want to ask natural language questions and have them translated into graph and vector searches,
So that answers come from my actual documents rather than AI speculation.

## Acceptance Criteria

1. **GIVEN** an investigation has entities, relationships, and embeddings, **WHEN** the investigator submits a question via `POST /api/v1/investigations/{id}/query/`, **THEN** the LLM translates the natural language question into Cypher graph queries and vector search operations, **AND** the Cypher query executes against Neo4j to find entity paths and relationships, **AND** the vector search executes against Qdrant (filtered by investigation_id) to find semantically relevant chunks, **AND** results from both sources are merged with their provenance chains.

2. **GIVEN** the query pipeline processes results, **WHEN** grounded results with provenance are available, **THEN** the LLM formats the results as cited prose — it formats and presents, never synthesizes or infers, **AND** every fact in the answer maps to a specific source document passage, **AND** the LLM never presents speculation, inference, or "likely" connections as facts (NFR22).

3. **GIVEN** the graph cannot answer a question, **WHEN** no relevant entities, relationships, or chunks are found, **THEN** the system returns "No connection found in your documents" (FR22), **AND** the response is not a fabricated or hedged answer.

4. **GIVEN** a question is submitted, **WHEN** the pipeline executes, **THEN** SSE events are published: `query.translating` -> `query.searching` -> `query.streaming` -> `query.complete`, **AND** streaming begins within 5 seconds (NFR7).

## Tasks / Subtasks

- [x] **Task 1: Create query request/response schemas** (AC: 1, 2, 3)
  - [x] 1.1: Create `apps/api/app/schemas/query.py`
  - [x] 1.2: Define `QueryRequest` — `question: str`, `conversation_history: list[ConversationTurn] | None = None`
  - [x] 1.3: Define `ConversationTurn` — `role: Literal["user", "assistant"]`, `content: str`
  - [x] 1.4: Define `Citation` — `citation_number: int`, `document_id: str`, `document_filename: str`, `chunk_id: str`, `page_start: int`, `page_end: int`, `text_excerpt: str`
  - [x] 1.5: Define `EntityReference` — `entity_id: str`, `name: str`, `type: str`
  - [x] 1.6: Define `QueryResponse` — `query_id: str`, `answer: str`, `citations: list[Citation]`, `entities_mentioned: list[EntityReference]`, `no_results: bool = False`
  - [x] 1.7: Define `QuerySSEEvent` — `event: str` (query.translating | query.searching | query.streaming | query.complete | query.failed), `data: dict` with event-specific payload

- [x] **Task 2: Add query translation + answer formatting prompts** (AC: 1, 2, 3)
  - [x] 2.1: Add to `apps/api/app/llm/prompts.py` — `QUERY_TRANSLATION_SYSTEM_PROMPT`: instructs LLM to translate a natural language question into a structured JSON response containing a Cypher query and vector search terms, given the Neo4j schema
  - [x] 2.2: Add `QUERY_TRANSLATION_USER_PROMPT` template — includes the Neo4j schema description (node labels: Person, Organization, Location; relationship types: WORKS_FOR, KNOWS, LOCATED_AT, MENTIONED_IN; properties: name, investigation_id, confidence_score), the investigation_id, and the user's question
  - [x] 2.3: Add `ANSWER_FORMATTING_SYSTEM_PROMPT` — instructs LLM to format graph + vector results as cited prose: every fact must reference a citation number `[N]`, entity names should be wrapped in `**bold**`, the LLM must NEVER add facts not present in the provided results, must NEVER speculate or infer
  - [x] 2.4: Add `ANSWER_FORMATTING_USER_PROMPT` template — includes the original question, graph results (paths/entities with provenance), vector results (relevant chunks with source info), and a numbered citation list for the LLM to reference
  - [x] 2.5: Add `SUGGESTED_FOLLOWUPS_PROMPT` — instructs LLM to suggest 2-3 follow-up questions based on the answer entities and relationships (short, one line each)

- [x] **Task 3: Add query translation response schema to LLM schemas** (AC: 1)
  - [x] 3.1: Add to `apps/api/app/llm/schemas.py` — `QueryTranslation` Pydantic model: `cypher_queries: list[str]` (one or more Cypher queries to execute), `search_terms: list[str]` (terms for Qdrant vector search), `entity_names: list[str]` (entity names mentioned in the question, for graph lookup fallback)
  - [x] 3.2: Cypher queries should use parameterized `$investigation_id` — never hardcode investigation IDs in Cypher

- [x] **Task 4: Create GRAPH FIRST query service** (AC: 1, 2, 3, 4)
  - [x] 4.1: Create `apps/api/app/services/query.py` — module-level async functions (follow existing service pattern from `entity_query.py`, `graph_query.py`)
  - [x] 4.2: Implement `async def execute_query(investigation_id: str, question: str, conversation_history: list | None, neo4j_driver, qdrant_client, ollama_client, embedding_client, event_publisher) -> QueryResponse`
  - [x] 4.3: **Step 1 — Translate** (publish `query.translating` SSE event): Call OllamaClient.chat() with QUERY_TRANSLATION prompts, parse response as QueryTranslation JSON. If LLM returns invalid JSON, fall back to entity name extraction + generic path query.
  - [x] 4.4: **Step 2 — Search graph** (publish `query.searching` SSE event): Execute each Cypher query from Step 1 against Neo4j using async read transaction. For each result, resolve MENTIONED_IN edges to get provenance (chunk_id, document_id, page_start, page_end, text_excerpt). Collect all paths, entities, relationships with their provenance.
  - [x] 4.5: **Step 2b — Search vectors**: Embed the question using OllamaEmbeddingClient. Search Qdrant `document_chunks` collection with `investigation_id` filter, `limit=10`. Each result has chunk_id, document_id, page_start, page_end, text_excerpt in payload.
  - [x] 4.6: **Step 3 — Merge results**: Combine graph results (entity paths + provenance) and vector results (relevant chunks). Deduplicate by chunk_id. Build a numbered citation list: each unique (document_id, chunk_id) pair gets a citation number. Resolve document filenames from PostgreSQL `documents` table.
  - [x] 4.7: **Step 4 — Check for empty results**: If zero graph results AND zero vector results, return `QueryResponse(no_results=True, answer="No connection found in your documents.", citations=[], entities_mentioned=[])`. Publish `query.complete`. Do NOT call the LLM for formatting.
  - [x] 4.8: **Step 5 — Format answer** (publish `query.streaming` SSE event): Call OllamaClient.chat() with ANSWER_FORMATTING prompts, passing merged results + citation list. Stream the response — publish each chunk as a `query.streaming` SSE event with `{"chunk": "..."}` data.
  - [x] 4.9: **Step 6 — Generate follow-ups**: Call OllamaClient.chat() with SUGGESTED_FOLLOWUPS_PROMPT. Parse as list of strings.
  - [x] 4.10: **Step 7 — Complete** (publish `query.complete` SSE event): Return `QueryResponse` with full answer, citations, entities_mentioned, follow-up suggestions. SSE data includes `{"answer": "...", "citations": [...], "entities_mentioned": [...], "suggested_followups": [...]}`.
  - [x] 4.11: **Error handling**: Wrap entire pipeline in try/except. On failure, publish `query.failed` SSE event with `{"error": "..."}`. If Ollama is unavailable, return RFC 7807 error with `type: "urn:osint:error:llm_unavailable"`.

- [x] **Task 5: Implement graph result provenance resolution** (AC: 1, 2)
  - [x] 5.1: Add helper `async def _resolve_provenance(entity_ids: list[str], neo4j_driver) -> dict[str, list[ProvenanceRecord]]` — for each entity, query MENTIONED_IN edges to get source documents + chunks
  - [x] 5.2: Cypher for provenance: `MATCH (e)-[m:MENTIONED_IN]->(d:Document) WHERE e.id IN $entity_ids RETURN e.id, m.chunk_id, m.page_start, m.page_end, m.text_excerpt, d.id AS document_id`
  - [x] 5.3: Add helper `async def _resolve_document_filenames(document_ids: list[str], db_session) -> dict[str, str]` — query PostgreSQL documents table for filenames by ID

- [x] **Task 6: Create query API endpoint** (AC: 1, 4)
  - [x] 6.1: Create `apps/api/app/api/v1/query.py`
  - [x] 6.2: Implement `POST /investigations/{investigation_id}/query/` — accepts `QueryRequest` body, returns `StreamingResponse` with SSE content type
  - [x] 6.3: Validate investigation exists in PostgreSQL (404 if not found)
  - [x] 6.4: Generate `query_id` (UUID v4) for SSE event correlation
  - [x] 6.5: Use `sse-starlette` `EventSourceResponse` for streaming — yield SSE events as query pipeline executes
  - [x] 6.6: Also publish events to Redis channel `events:{investigation_id}` via EventPublisher so other frontend components (graph canvas) can react to query events
  - [x] 6.7: After streaming completes, return final `QueryResponse` as the last SSE event (`query.complete`) with full payload

- [x] **Task 7: Register query router** (AC: 1)
  - [x] 7.1: Modify `apps/api/app/api/v1/router.py` — import query router and include with `prefix="/investigations/{investigation_id}"` and `tags=["query"]`

- [x] **Task 8: Write backend tests for query endpoint** (AC: 1, 2, 3, 4)
  - [x] 8.1: Create `apps/api/tests/api/test_query.py`
  - [x] 8.2: Test `POST /query/` with valid question — returns SSE stream with correct event sequence (translating → searching → streaming → complete)
  - [x] 8.3: Test `POST /query/` when no results — returns `no_results: true` with "No connection found" message
  - [x] 8.4: Test `POST /query/` with nonexistent investigation — returns 404
  - [x] 8.5: Test `POST /query/` when Ollama unavailable — returns appropriate error
  - [x] 8.6: Test all citations in response map to real document passages (no orphaned citations)
  - [x] 8.7: Test conversation_history is passed through to query translation prompt

- [x] **Task 9: Write backend tests for query service** (AC: 1, 2, 3)
  - [x] 9.1: Create `apps/api/tests/services/test_query.py`
  - [x] 9.2: Test translate step — LLM response parsed into Cypher queries + search terms
  - [x] 9.3: Test translate fallback — invalid LLM JSON falls back to entity name lookup
  - [x] 9.4: Test graph search — Cypher executes against Neo4j, provenance resolved
  - [x] 9.5: Test vector search — question embedded, Qdrant searched with investigation filter
  - [x] 9.6: Test result merge — deduplication by chunk_id, citation numbering
  - [x] 9.7: Test empty results — no_results response without LLM formatting call
  - [x] 9.8: Test answer formatting — LLM called with merged results, citations in output match citation list
  - [x] 9.9: Test SSE events published in correct order

- [x] **Task 10: Update OpenAPI spec and regenerate frontend types** (AC: 1)
  - [x] 10.1: Run `cd apps/api && uv run python -c "from app.main import app; import json; print(json.dumps(app.openapi()))" > ../web/src/lib/openapi.json`
  - [x] 10.2: Run `cd apps/web && pnpm run generate-api-types`

## Dev Notes

### Architecture Context

This is the **first story in Epic 5** (Natural Language Q&A with Source Citations). Epic 4 (Graph Visualization) is complete. This story builds the **backend query pipeline only** — the frontend Q&A panel is Story 5.2, citation click-through is Story 5.3.

The GRAPH FIRST pipeline is the architectural centerpiece of OSINT. It is fundamentally different from standard RAG:
```
Question → LLM translates to Cypher + vector search → Execute against Neo4j/Qdrant
→ Retrieve grounded results with provenance → LLM formats as cited prose
→ Stream answer via SSE
```

**The LLM has two strictly defined roles:**
1. **Query translation** — NL → Cypher + vector search terms
2. **Result formatting** — graph/vector results → cited prose with `[N]` references

**The LLM NEVER:** synthesizes, infers, speculates, fills gaps, or presents "likely" connections. If the graph has no answer, the system says "No connection found in your documents" — period.

### GRAPH FIRST Pipeline Design

**Phase 1 — Query Translation:**
The LLM receives the Neo4j schema description and the user's question. It outputs structured JSON:
```json
{
  "cypher_queries": [
    "MATCH p = shortestPath((a)-[*..5]-(b)) WHERE a.investigation_id = $investigation_id AND toLower(a.name) CONTAINS 'horvat' AND toLower(b.name) CONTAINS 'greenbuild' RETURN p"
  ],
  "search_terms": ["Horvat GreenBuild connection"],
  "entity_names": ["Horvat", "GreenBuild"]
}
```

**Cypher generation guardrails:**
- Always include `investigation_id = $investigation_id` filter (multi-investigation isolation)
- Use `toLower(name) CONTAINS toLower(...)` for fuzzy matching (same pattern as entity search — Story 4.5)
- Limit path length to `*..5` hops to prevent runaway queries
- Use `shortestPath` for connection queries, `MATCH` patterns for attribute queries
- Use parameterized queries (`$investigation_id`) — never interpolate values into Cypher strings

**Fallback strategy:** If the LLM returns invalid JSON or garbled Cypher, fall back to:
1. Extract entity names from the question using simple heuristics (capitalized words, quoted strings)
2. Query Neo4j for entities with matching names
3. Find shortest paths between matched entities
4. Continue with vector search as normal

**Phase 2 — Graph Search + Vector Search (parallel):**
Execute Cypher queries against Neo4j and embed question for Qdrant search simultaneously (asyncio.gather). For graph results, resolve MENTIONED_IN provenance edges to get source chunk context.

**Phase 3 — Result Merge:**
Combine graph results (entity paths with provenance) and vector results (semantically relevant chunks). Deduplicate overlapping chunks. Build numbered citation list where each unique (document_id, chunk_id) pair = one citation number.

**Phase 4 — Answer Formatting (streaming):**
LLM receives merged results + citation list. Formats as prose with `[N]` citation references and `**entity names**` in bold. Streams response token by token — each chunk published as SSE event.

**Phase 5 — Follow-up suggestions:**
Quick LLM call to suggest 2-3 follow-up questions based on answer entities/relationships. Short, one line each.

### SSE Streaming Strategy

**Endpoint returns SSE directly:** `POST /query/` returns `EventSourceResponse` (sse-starlette). The frontend uses `@microsoft/fetch-event-source` which supports POST with body.

**Event sequence:**
```
event: query.translating
data: {"query_id": "uuid", "message": "Translating your question..."}

event: query.searching
data: {"query_id": "uuid", "message": "Searching knowledge graph and documents..."}

event: query.streaming
data: {"query_id": "uuid", "chunk": "Deputy Mayor Horvat"}

event: query.streaming
data: {"query_id": "uuid", "chunk": " is connected to GreenBuild LLC through"}

... (more streaming chunks)

event: query.complete
data: {"query_id": "uuid", "answer": "full answer text", "citations": [...], "entities_mentioned": [...], "suggested_followups": [...], "no_results": false}
```

**Dual publishing:** Events are also published to Redis channel `events:{investigation_id}` via existing EventPublisher so the graph canvas (Story 5.2/5.3) can react to `query.complete` events and highlight relevant entities.

**Error event:**
```
event: query.failed
data: {"query_id": "uuid", "error": "LLM service unavailable"}
```

### What Already Exists (DO NOT recreate)

| Component | Location | What It Does |
|-----------|----------|-------------|
| OllamaClient | `apps/api/app/llm/client.py` | Chat & generate endpoints with timeout handling. Model: `qwen3.5:9b`. Use for query translation + answer formatting. |
| OllamaEmbeddingClient | `apps/api/app/llm/embeddings.py` | Embedding generation via `qwen3-embedding:8b` (4096 dims). Use to embed the question for Qdrant search. |
| Extraction prompts | `apps/api/app/llm/prompts.py` | Entity/relationship extraction prompts — **reference pattern** for query prompts. Add new prompts here. |
| LLM schemas | `apps/api/app/llm/schemas.py` | Pydantic models for LLM responses. Add QueryTranslation schema here. |
| Neo4j driver | `apps/api/app/db/neo4j.py` | Async Neo4j driver (`GraphDatabase.driver`). Use for Cypher execution. |
| Qdrant client | `apps/api/app/db/qdrant.py` | Qdrant async client with `document_chunks` collection (4096 dims). Use for vector search. |
| Redis client | `apps/api/app/db/redis.py` | Async Redis client for pub/sub. |
| EventPublisher | `apps/api/app/services/events.py` | Publishes SSE events to Redis channel `events:{investigation_id}`. Use for dual-publishing query events. |
| SSE endpoint | `apps/api/app/api/v1/events.py` | `GET /events/{investigation_id}` — subscribes to Redis and streams to browser. Already handles query event types when published. |
| GraphQueryService | `apps/api/app/services/graph_query.py` | Subgraph queries, neighbor expansion, hub detection. **Reference for Neo4j async read transaction patterns.** |
| EntityQueryService | `apps/api/app/services/entity_query.py` | Entity list with search, entity detail with relationships. **Reference for Neo4j Cypher patterns.** |
| Entity schemas | `apps/api/app/schemas/entity.py` | EntityListItem, EntityDetail — reference for entity-related fields. |
| Graph schemas | `apps/api/app/schemas/graph.py` | GraphNode, GraphEdge, GraphResponse — reference for graph data structures. |
| Document model | `apps/api/app/models/document.py` | Document ORM with filename, investigation_id — query this for filename resolution. |
| Chunk model | `apps/api/app/models/chunk.py` | DocumentChunk ORM with text, page_start, page_end — reference for chunk data. |
| API router | `apps/api/app/api/v1/router.py` | Aggregates all v1 routes — add query router here. |
| Config | `apps/api/app/config.py` | All service URLs, model names, timeouts. |
| Exceptions | `apps/api/app/exceptions.py` | DomainError base + specific error types. Add query-specific errors here. |
| sse-starlette | `pyproject.toml` | Already installed — use `EventSourceResponse` for streaming POST response. |

### Neo4j Schema (for Cypher generation)

**Node labels and properties:**
```
(:Person {id, name, investigation_id, confidence_score, created_at})
(:Organization {id, name, investigation_id, confidence_score, created_at})
(:Location {id, name, investigation_id, confidence_score, created_at})
(:Document {id, investigation_id})
```

**Relationship types:**
```
(:Person)-[:WORKS_FOR {confidence_score}]->(:Organization)
(:Person)-[:KNOWS {confidence_score}]->(:Person)
(:Person|Organization)-[:LOCATED_AT {confidence_score}]->(:Location)
(:Person|Organization|Location)-[:MENTIONED_IN {chunk_id, page_start, page_end, text_excerpt}]->(:Document)
```

**Critical:** MENTIONED_IN edges are the provenance chain. Every entity links to its source document via MENTIONED_IN with chunk-level detail. This is what makes citations possible.

### Qdrant Schema (for vector search)

**Collection:** `document_chunks`
**Vector:** 4096 dimensions (qwen3-embedding:8b)
**Payload fields:** `chunk_id`, `document_id`, `investigation_id`, `page_start`, `page_end`, `text_excerpt`
**Filter:** Always filter by `investigation_id` using Qdrant's `Filter(must=[FieldCondition(key="investigation_id", match=MatchValue(value=investigation_id))])`

### Performance Requirements

| Metric | Target | Source |
|--------|--------|--------|
| Question → answer with citations | <30 seconds | NFR5 |
| Graph path queries | <10 seconds | NFR6 |
| Streaming begins | within 5 seconds | NFR7 |
| Hardware baseline | 16GB RAM, 8GB VRAM | NFR12 |

**Optimization notes:**
- Run Neo4j Cypher + Qdrant vector search in parallel using `asyncio.gather()`
- Stream answer tokens as they arrive from Ollama (don't buffer the full response)
- Limit Qdrant results to top 10 (higher k wastes tokens in formatting prompt)
- Limit Cypher path length to 5 hops max
- Embed question and Cypher translation can run in parallel (both use Ollama but different models — embedding uses qwen3-embedding:8b, translation uses qwen3.5:9b)

### Error Handling

| Error | Response | SSE Event |
|-------|----------|-----------|
| Ollama unavailable | RFC 7807: `urn:osint:error:llm_unavailable`, 503 | `query.failed` |
| Neo4j unavailable | RFC 7807: `urn:osint:error:graph_unavailable`, 503 | `query.failed` |
| Qdrant unavailable | Degrade: skip vector search, graph-only results | `query.searching` with warning |
| Invalid Cypher from LLM | Fall back to entity name lookup + shortestPath | None (internal recovery) |
| Investigation not found | RFC 7807: `urn:osint:error:investigation_not_found`, 404 | None |
| Empty question | 422 validation error (Pydantic) | None |

**Qdrant degradation:** If Qdrant is unavailable, the pipeline should still work with graph-only results. Vector search is supplementary to the graph — not required. Log a warning and continue.

### Testing Strategy

**Backend tests (pytest + httpx):**

`tests/api/test_query.py` — Endpoint tests:
- Mock OllamaClient, Neo4j driver, Qdrant client
- Test SSE event sequence (translating → searching → streaming → complete)
- Test no-results response
- Test 404 for nonexistent investigation
- Test error response when Ollama is unavailable
- Test conversation_history passthrough

`tests/services/test_query.py` — Service tests:
- Mock all external dependencies
- Test each pipeline phase independently
- Test Cypher fallback on invalid LLM output
- Test provenance resolution
- Test result merge and deduplication
- Test citation numbering consistency
- Test empty results short-circuit (no formatting LLM call)

**Test patterns from previous stories:**
- Mock Neo4j driver with `AsyncMock` returning configured results
- Mock Qdrant client with `MagicMock` for search results
- Mock OllamaClient.chat() returning JSON strings for translation, prose for formatting
- Use `httpx.AsyncClient` for endpoint tests (FastAPI test client)
- Co-located test files in `tests/` mirroring source structure

### Project Structure Notes

**New files:**
- `apps/api/app/api/v1/query.py` — Query endpoint
- `apps/api/app/services/query.py` — GRAPH FIRST query pipeline service
- `apps/api/app/schemas/query.py` — Query request/response schemas
- `apps/api/tests/api/test_query.py` — Endpoint tests
- `apps/api/tests/services/test_query.py` — Service tests

**Modified files:**
- `apps/api/app/api/v1/router.py` — Register query router
- `apps/api/app/llm/prompts.py` — Add query translation + answer formatting prompts
- `apps/api/app/llm/schemas.py` — Add QueryTranslation schema
- `apps/api/app/exceptions.py` — Add query-specific error types (if needed)
- `apps/web/src/lib/openapi.json` — Regenerated after OpenAPI update
- `apps/web/src/lib/api-types.generated.ts` — Regenerated

**No new dependencies required.** All libraries needed (sse-starlette, neo4j, qdrant-client, httpx) are already installed.

### References

- [Source: _bmad-output/planning-artifacts/epics.md — Epic 5, Story 5.1 acceptance criteria and BDD scenarios]
- [Source: _bmad-output/planning-artifacts/prd.md — FR17-FR22: Natural language Q&A with GRAPH FIRST grounding]
- [Source: _bmad-output/planning-artifacts/prd.md — NFR5: <30s answer, NFR6: <10s graph paths, NFR7: streaming within 5s, NFR21: 100% fact traceability, NFR22: zero hallucinated facts]
- [Source: _bmad-output/planning-artifacts/architecture.md — GRAPH FIRST Query Architecture: NL → Cypher + vector → execute → provenance → cited prose]
- [Source: _bmad-output/planning-artifacts/architecture.md — API endpoint: POST /api/v1/investigations/{id}/query/]
- [Source: _bmad-output/planning-artifacts/architecture.md — File mapping: app/api/v1/query.py, app/services/query.py, app/schemas/query.py, app/llm/prompts.py]
- [Source: _bmad-output/planning-artifacts/architecture.md — SSE: Per-query channels (query:{query_id}), fetch-event-source supports POST]
- [Source: _bmad-output/planning-artifacts/architecture.md — Data flow: Question → POST /query/ → Translate → Execute graph+vector → Merge with provenance → Format → Stream via SSE]
- [Source: _bmad-output/planning-artifacts/architecture.md — Error handling: RFC 7807 Problem Details, per-service degradation matrix]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — Answer-to-Graph Bridge: Q&A panel + graph canvas synchronized in split view]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — Q&A Panel: Perplexity-style cited prose, superscript citation numbers, bold entity names, suggested follow-ups]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — SSE channels: per-query for answer streaming, per-investigation for status updates]
- [Source: apps/api/app/llm/client.py — OllamaClient with chat/generate, DEFAULT_MODEL qwen3.5:9b]
- [Source: apps/api/app/llm/embeddings.py — OllamaEmbeddingClient with qwen3-embedding:8b, 4096 dimensions]
- [Source: apps/api/app/llm/prompts.py — Existing extraction prompts as pattern reference]
- [Source: apps/api/app/services/graph_query.py — Neo4j async read transaction patterns]
- [Source: apps/api/app/services/entity_query.py — Entity Cypher query patterns, MENTIONED_IN provenance]
- [Source: apps/api/app/services/events.py — EventPublisher Redis pub/sub pattern]
- [Source: apps/api/app/db/qdrant.py — Qdrant client with collection config, filter patterns]
- [Source: apps/api/app/schemas/entity.py — Entity schema patterns to follow]

### Previous Story Intelligence (Story 4.5 Learnings)

1. **Module-level async functions** — The project uses module-level functions (not classes) for services. `entity_query.py` and `graph_query.py` both use `async def function_name(driver, ...)` pattern. Follow this for `query.py`.

2. **Neo4j async read transactions** — Use `async with driver.session() as session: result = await session.execute_read(tx_func)` pattern. The `tx_func` receives a `tx` (AsyncManagedTransaction) and runs `await tx.run(cypher, params)`.

3. **OpenAPI spec regeneration** — After adding the query endpoint, run the spec export + type generation command to keep frontend types in sync.

4. **RFC 7807 error format** — All errors follow Problem Details format. Use existing `DomainError` base from `app/exceptions.py`.

5. **SSE with sse-starlette** — Already installed and used in `events.py`. Use `EventSourceResponse` for the streaming POST endpoint.

6. **Test patterns** — `conftest.py` has fixtures for mock DB sessions, mock Neo4j driver, mock HTTP clients. Follow existing test structure in `tests/api/` and `tests/services/`.

7. **Entity type names are PascalCase** — `Person`, `Organization`, `Location` in Neo4j and API responses. Use PascalCase in Cypher queries and schema descriptions.

8. **`MENTIONED_IN` provenance pattern** — Already established in extraction pipeline. Each entity has MENTIONED_IN edges to Document nodes with `chunk_id`, `page_start`, `page_end`, `text_excerpt` properties. Query these for citation data.

9. **Qdrant filter pattern** — Use `Filter(must=[FieldCondition(key="investigation_id", match=MatchValue(value=investigation_id))])` for investigation-scoped vector search.

10. **Commit message format:** `feat: Story 5.1 — GRAPH FIRST query pipeline`

### Git Intelligence

Recent commits (for pattern continuity):
- `20200f5` — feat: Story 4.5 — entity search with graph highlighting with code review fixes
- `e4f2070` — feat: Story 4.4 — graph filtering by entity type & source document
- `a6260c1` — feat: Story 4.3 — node & edge interaction with entity detail card
- `d62f758` — feat: Story 4.2 — interactive graph canvas with Cytoscape.js
- `9c599c0` — feat: Story 4.1 — graph API subgraph queries

**Test counts:** Current suite: ~270 backend tests, ~160 frontend tests. This story should add ~16-20 new backend tests (endpoint: 7, service: 9+). No frontend tests in this story (frontend is Story 5.2).

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

- Fixed fallback entity extraction regex to capture camelCase names (e.g., "GreenBuild")
- Fixed Neo4j driver mock pattern in tests (session() returns sync context manager, not async)

### Completion Notes List

- **Task 1:** Created `apps/api/app/schemas/query.py` with QueryRequest, QueryResponse, ConversationTurn, Citation, EntityReference, QuerySSEEvent schemas
- **Task 2:** Added QUERY_TRANSLATION_SYSTEM_PROMPT, QUERY_TRANSLATION_USER_PROMPT_TEMPLATE, ANSWER_FORMATTING_SYSTEM_PROMPT, ANSWER_FORMATTING_USER_PROMPT_TEMPLATE, SUGGESTED_FOLLOWUPS_PROMPT to prompts.py
- **Task 3:** Added QueryTranslation Pydantic model to schemas.py with cypher_queries, search_terms, entity_names
- **Task 4:** Created `apps/api/app/services/query.py` with full GRAPH FIRST pipeline: translate → graph search + vector search (parallel) → merge → empty check → format → follow-ups → complete
- **Task 5:** Implemented _resolve_provenance and _resolve_document_filenames helpers for MENTIONED_IN edge traversal
- **Task 6:** Created `apps/api/app/api/v1/query.py` with POST /investigations/{id}/query/ SSE endpoint, investigation validation, EventSourceResponse streaming
- **Task 7:** Registered query router in router.py
- **Task 8:** Created 7 endpoint tests covering SSE event sequence, no-results, 404, Ollama unavailable, citation validation, conversation history passthrough, empty question validation
- **Task 9:** Created 18 service tests covering translation, fallback, graph search, vector search, result merge, deduplication, citation numbering, empty results, answer formatting, SSE event order, follow-up suggestions
- **Task 10:** Exported OpenAPI spec and regenerated frontend TypeScript types

### Change Log

- 2026-03-14: Story 5.1 — GRAPH FIRST query pipeline implementation complete. Added backend query pipeline with LLM-powered Cypher/vector translation, dual-source search, provenance-based citations, and SSE streaming. 25 new backend tests (7 endpoint + 18 service).
- 2026-03-14: Code review — Fixed 4 issues: (1) HIGH: Cypher injection in fallback translation and entity name lookup — now uses parameterized queries; (2) MEDIUM: Removed fake 50-char streaming chunking — yields full answer honestly; (3) MEDIUM: Unified query_id — endpoint passes its query_id to service, removed duplicate error handling; (4) MEDIUM: Added GraphUnavailableError for RFC 7807 compliance on Neo4j failures. All 295 backend tests pass.

### File List

**New files:**
- apps/api/app/schemas/query.py
- apps/api/app/services/query.py
- apps/api/app/api/v1/query.py
- apps/api/tests/api/test_query.py
- apps/api/tests/services/test_query.py

**Modified files:**
- apps/api/app/api/v1/router.py
- apps/api/app/llm/prompts.py
- apps/api/app/llm/schemas.py
- apps/api/app/exceptions.py (added GraphUnavailableError)
- apps/web/src/lib/openapi.json
- apps/web/src/lib/api-types.generated.ts
- _bmad-output/implementation-artifacts/sprint-status.yaml
