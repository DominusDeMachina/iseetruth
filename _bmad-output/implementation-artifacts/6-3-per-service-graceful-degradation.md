# Story 6.3: Per-Service Graceful Degradation

Status: in-progress

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an investigator,
I want the application to keep working partially when individual services are down,
So that I can still use available features instead of facing a completely broken app.

## Acceptance Criteria

1. **GIVEN** Ollama is down, **WHEN** the investigator uses the application, **THEN** graph browsing and visualization work normally (Neo4j is independent), **AND** natural language queries return "LLM service unavailable — try again shortly", **AND** document upload still queues for later processing, **AND** the status bar shows Ollama as unavailable.

2. **GIVEN** Neo4j is down, **WHEN** the investigator uses the application, **THEN** document upload and queuing still work, **AND** graph pages show a clear error: "Graph database unavailable", **AND** Q&A queries that depend on graph return a clear error.

3. **GIVEN** Qdrant is down, **WHEN** the investigator uses the application, **THEN** graph queries work (Neo4j is independent), **AND** natural language queries fall back to graph-only results (no vector search), **AND** the status bar indicates reduced search capability.

4. **GIVEN** any service recovers, **WHEN** the health check detects the recovery, **THEN** the application restores full functionality automatically without requiring a restart (NFR27), **AND** a `service.status` SSE event notifies the frontend of the status change.

## Tasks / Subtasks

- [ ] **Task 1: Add `service.status` SSE event support to backend** (AC: 4)
  - [ ] 1.1: Create `HealthMonitorService` in `apps/api/app/services/health_monitor.py` — background task that periodically checks service health (every 15s), compares against previous state, and publishes `service.status` SSE events on state transitions
  - [ ] 1.2: Store previous health state in Redis key `health:last_status` (JSON dict of `{service_name: status_enum}`) to detect transitions
  - [ ] 1.3: Publish `service.status` SSE event via EventPublisher when any service transitions: `{service: "ollama"|"neo4j"|"qdrant"|"redis"|"postgres", status: "healthy"|"unhealthy"|"unavailable", detail: "..."}`
  - [ ] 1.4: Use a global SSE channel `events:system` (not investigation-scoped) for service status events
  - [ ] 1.5: Start health monitor as `asyncio.create_task` in FastAPI `lifespan` startup handler in `apps/api/app/main.py`
  - [ ] 1.6: Add SSE endpoint subscription to `events:system` channel in `apps/api/app/api/v1/events.py` — either a new endpoint `GET /api/v1/events/system` or multiplex into existing per-investigation SSE

- [ ] **Task 2: Wrap graph service and API with Neo4j error handling** (AC: 2)
  - [ ] 2.1: In `apps/api/app/services/graph_query.py`, wrap all Neo4j session calls in try-except catching `neo4j.exceptions.ServiceUnavailable`, `neo4j.exceptions.SessionExpired`, and `ConnectionRefusedError` → raise `GraphUnavailableError("Graph database unavailable")`
  - [ ] 2.2: In `apps/api/app/api/v1/graph.py`, add exception handler for `GraphUnavailableError` → return 503 with RFC 7807 body: `{"type": "urn:osint:error:graph_unavailable", "title": "Graph Database Unavailable", "status": 503, "detail": "Graph database unavailable — document management and uploads still work"}`
  - [ ] 2.3: Verify existing `GraphUnavailableError` in `apps/api/app/exceptions.py` has correct status code (503) and error type

- [ ] **Task 3: Add Qdrant degradation messaging to query pipeline** (AC: 3)
  - [ ] 3.1: In `apps/api/app/services/query.py`, when vector search fails (Qdrant down), yield a `query.degraded` SSE event: `{query_id, message: "Vector search unavailable — results based on graph data only", service: "qdrant"}`  before continuing with graph-only results
  - [ ] 3.2: Ensure the final `query.complete` SSE event includes a `degraded: true` flag when Qdrant was unavailable, so the frontend can show "reduced search" indicator on the answer

- [ ] **Task 4: Handle Ollama unavailability in query endpoint** (AC: 1)
  - [ ] 4.1: In `apps/api/app/services/query.py`, the `OllamaUnavailableError` is already caught and yields `query.failed` with the error message — verify it produces: `"LLM service unavailable — try again shortly. Graph exploration still works."`
  - [ ] 4.2: In `apps/api/app/api/v1/query.py`, verify the 503 error response for Ollama unavailable includes the message from AC#1

- [ ] **Task 5: Handle Ollama down during document processing — queue for later** (AC: 1)
  - [ ] 5.1: In `apps/api/app/worker/tasks/process_document.py`, when the pre-flight Ollama check fails, instead of immediately marking as "failed", set status to "queued" with `error_message = "Waiting for LLM service"` and `failed_stage = "preflight"`
  - [ ] 5.2: Do NOT re-enqueue a Celery task (avoids infinite retry loop) — rely on Story 6.2's auto-retry mechanism (future) or manual retry (Story 6.1, already done) to re-process when Ollama recovers
  - [ ] 5.3: Publish a `document.failed` SSE event with `{document_id, stage: "preflight", error: "LLM service unavailable — document will be retried when service recovers"}` so the frontend shows a clear message

- [ ] **Task 6: Handle Neo4j down in query pipeline** (AC: 2)
  - [ ] 6.1: In `apps/api/app/services/query.py`, the `GraphUnavailableError` is already caught — verify the error message matches: `"Graph database unavailable — unable to answer questions. Document upload and processing still work."`
  - [ ] 6.2: Ensure graph-dependent queries fail fast with a clear SSE `query.failed` event rather than timing out

- [ ] **Task 7: Frontend — handle `service.status` SSE events** (AC: 4)
  - [ ] 7.1: Create a new `useSystemSSE` hook in `apps/web/src/hooks/useSystemSSE.ts` that subscribes to `GET /api/v1/events/system`
  - [ ] 7.2: On `service.status` event, invalidate the `useHealthStatus` TanStack Query cache (forces StatusBar and SystemStatusPage to re-fetch)
  - [ ] 7.3: Show a toast notification on service recovery: `"[Service] is back online"` (green left border, auto-dismiss 5s)
  - [ ] 7.4: Show a toast notification on service failure: `"[Service] is unavailable — some features are limited"` (amber left border, persists until dismissed)
  - [ ] 7.5: Mount the `useSystemSSE` hook in the root layout (`apps/web/src/routes/__root.tsx`) so it runs globally

- [ ] **Task 8: Frontend — graph panel degradation UX** (AC: 2)
  - [ ] 8.1: In `apps/web/src/components/graph/GraphCanvas.tsx`, check health status from `useHealthStatus` hook — if Neo4j is unavailable, render an error state: centered message "Graph database unavailable" with `AlertTriangle` icon, styled in `--status-warning`
  - [ ] 8.2: Wrap Cytoscape rendering in a try-catch (already exists in `useCytoscape` hook) — on Neo4j API 503, show the unavailable state instead of crashing
  - [ ] 8.3: When Ollama is down but Neo4j is up, show a small badge in the graph header: "Q&A unavailable" (per UX spec line 971: `Degraded — When Ollama is down: graph fully interactive, badge indicating "Q&A unavailable"`)

- [ ] **Task 9: Frontend — Q&A panel degradation UX** (AC: 1, 3)
  - [ ] 9.1: In `apps/web/src/components/qa/AnswerPanel.tsx` or `QueryInput.tsx`, check health status — if Ollama is unavailable, disable the query input and show: "LLM service unavailable — try again shortly. Graph exploration still works." (per UX spec line 787)
  - [ ] 9.2: Handle `query.degraded` SSE event in `useQueryStream.ts` — show an inline notice in the answer: "Results based on graph data only — vector search unavailable" (amber text)
  - [ ] 9.3: When the `query.complete` event has `degraded: true`, append a small indicator to the answer footer

- [ ] **Task 10: Frontend — StatusBar real-time updates** (AC: 1, 2, 3, 4)
  - [ ] 10.1: In `apps/web/src/components/layout/StatusBar.tsx`, the `useHealthStatus` hook already powers the display — SSE-driven cache invalidation (Task 7.2) will cause automatic re-render on service state changes
  - [ ] 10.2: For Qdrant down specifically, update the StatusBar tooltip to show "Reduced search capability" alongside the degraded status

- [ ] **Task 11: Regenerate OpenAPI types** (AC: all)
  - [ ] 11.1: Run `cd apps/api && uv run python -m app.generate_openapi` to export updated schema
  - [ ] 11.2: Run `cd apps/web && pnpm run generate-types` to regenerate `api-types.generated.ts`
  - [ ] 11.3: Verify new SSE event types and any new response fields are reflected

- [ ] **Task 12: Backend tests** (AC: 1, 2, 3, 4)
  - [ ] 12.1: Test `HealthMonitorService` — mock health checks, verify `service.status` SSE events are published on state transitions and NOT on no-change polls
  - [ ] 12.2: Test graph API endpoint returns 503 with RFC 7807 body when Neo4j is down (mock Neo4j driver to raise `ServiceUnavailable`)
  - [ ] 12.3: Test query pipeline with Qdrant down — verify `query.degraded` event is emitted and answer still returns with graph-only data
  - [ ] 12.4: Test query pipeline with Ollama down — verify `query.failed` event with correct error message
  - [ ] 12.5: Test query pipeline with Neo4j down — verify `query.failed` event with correct error message
  - [ ] 12.6: Test document processing pre-flight with Ollama down — verify document status remains "queued" (not "failed"), error message set, SSE event published
  - [ ] 12.7: Add tests in existing test files: `tests/api/test_graph.py`, `tests/api/test_query.py`, `tests/worker/test_process_document.py`, and new `tests/services/test_health_monitor.py`

- [ ] **Task 13: Frontend tests** (AC: 1, 2, 3, 4)
  - [ ] 13.1: Test GraphCanvas renders "Graph database unavailable" when health status shows Neo4j down
  - [ ] 13.2: Test GraphCanvas shows "Q&A unavailable" badge when Ollama is down but Neo4j is up
  - [ ] 13.3: Test AnswerPanel/QueryInput disables input when Ollama is unavailable
  - [ ] 13.4: Test `useSystemSSE` hook fires cache invalidation on `service.status` events
  - [ ] 13.5: Test toast notifications appear on service recovery and failure events
  - [ ] 13.6: Test `query.degraded` event handler shows inline "graph-only results" notice

## Dev Notes

### Architecture Context

This is **Story 6.3** in Epic 6 (System Resilience & Error Recovery). Story 6.1 (failed document detection & manual retry) is **done** — it established `failed_stage` tracking, the retry endpoint, and stage-aware resume. Story 6.2 (auto-retry on service recovery) is still **backlog** — it will build on the health monitoring infrastructure created here.

**FRs covered:** FR38 (data preservation on partial failure), FR39 (degraded mode — graph works without LLM), FR40 (service status display)

**NFRs relevant:** NFR26 (individual service failure doesn't crash app), NFR27 (auto-recover when services come back online)

**Dependency note:** Story 6.4 (Service Status Display & Error Boundaries) depends on this story's `service.status` SSE events and degradation states.

### Current Codebase State — What Already Works

| Component | Location | Current Behavior | Gap |
|---|---|---|---|
| Health service | `app/services/health.py` | Checks all 5 services in parallel with 5s timeout, returns `healthy`/`degraded`/`unhealthy` | No state-change detection, no SSE events |
| Health API | `app/api/v1/health.py` | Single GET endpoint returns `HealthResponse` | No streaming, no push notifications |
| Query service | `app/services/query.py` | Qdrant failure → silently continues graph-only; Ollama/Neo4j → raises error with SSE `query.failed` | No `query.degraded` event for Qdrant; error messages need alignment with UX spec |
| Graph service | `app/services/graph_query.py` | Zero try-catch — Neo4j exceptions propagate as unhandled 500s | Needs `GraphUnavailableError` wrapping |
| Graph API | `app/api/v1/graph.py` | No error handling | Needs 503 with RFC 7807 for Neo4j down |
| Events service | `app/services/events.py` | Publishes document + query events on investigation channels | No `service.status` event, no system channel |
| StatusBar | `components/layout/StatusBar.tsx` | Shows overall health, polls every 30s, links to `/status` | Polling only — no SSE-driven real-time updates |
| useSSE hook | `hooks/useSSE.ts` | Handles `document.*` and `entity.discovered` events | No `service.status` handler |
| Document task | `worker/tasks/process_document.py` | Ollama preflight fail → immediate "failed" status | Should queue for later instead of failing |
| Exceptions | `app/exceptions.py` | Has `OllamaUnavailableError`, `GraphUnavailableError`, `ServiceUnavailableError` (all 503) | Foundation exists, ready to use |

### Health Monitor Design

**New component:** `HealthMonitorService` — a background async loop that:
1. Runs `get_health()` every 15 seconds
2. Compares result against last-known state stored in Redis (`health:last_status`)
3. On state transition → publishes `service.status` SSE event
4. Only fires events on **changes**, not on every poll

**Redis state key:** `health:last_status` — JSON dict:
```json
{"postgres": "healthy", "neo4j": "healthy", "qdrant": "healthy", "redis": "healthy", "ollama": "healthy"}
```

**SSE channel:** `events:system` — global channel, not investigation-scoped. The existing `EventPublisher.publish()` uses `events:{investigation_id}` channels. For system events, pass `investigation_id="system"` or add a `publish_system()` method.

**Lifespan integration:**
```python
# In app/main.py lifespan handler
@asynccontextmanager
async def lifespan(app: FastAPI):
    monitor = HealthMonitorService()
    task = asyncio.create_task(monitor.run())
    yield
    task.cancel()
```

### SSE Architecture for System Events

The existing SSE endpoint at `GET /api/v1/events/{investigation_id}` subscribes to `events:{investigation_id}` Redis channel. For system events:

**Option A (recommended):** Add `GET /api/v1/events/system` endpoint that subscribes to `events:system` channel. Frontend mounts `useSystemSSE` hook globally in `__root.tsx`.

**Option B:** Multiplex system events into all investigation channels. Simpler for frontend but noisier.

**Choose Option A** — it's cleaner and avoids polluting investigation-specific streams with system events.

### Per-Service Degradation Matrix

| Service Down | Graph Browsing | Q&A Queries | Document Upload | Document Processing | Status Bar |
|---|---|---|---|---|---|
| **Ollama** | Works normally | "LLM unavailable — try shortly" | Queues normally | Stays "queued" (won't fail) | Shows Ollama unavailable |
| **Neo4j** | "Graph database unavailable" | "Graph unavailable" error | Queues normally | Entity extraction fails → document fails | Shows Neo4j unavailable |
| **Qdrant** | Works normally | Falls back to graph-only results | Queues normally | Embedding fails → document completes without embeddings | Shows reduced search |
| **Redis** | Works normally | Fails (no SSE/queue) | Fails (no queue) | Fails (no queue) | Shows Redis unavailable |
| **Postgres** | Works normally | Fails (no document metadata) | Fails (no DB) | Fails (no DB) | Shows Postgres unavailable |

**Scope for this story:** Focus on Ollama, Neo4j, Qdrant degradation (the 3 ACs). Redis and Postgres failures are too fundamental — the app can't meaningfully degrade without them (they're core infrastructure).

### Document Processing: Ollama Down Behavior Change

**Current (Story 6.1):** Pre-flight check fails → `status = "failed"`, `failed_stage = "preflight"`, `error_message = "Ollama LLM service is unavailable..."`

**New (Story 6.3):** Pre-flight check fails → keep `status = "queued"` (or use a new status like `"waiting"`). The document stays in the queue. When Ollama recovers, manual retry (6.1) or auto-retry (6.2, future) will pick it up.

**IMPORTANT DESIGN DECISION:** Don't change the document status to "failed" when Ollama is down at pre-flight. Instead:
- Set `status = "queued"`, `failed_stage = "preflight"`, `error_message = "Waiting for LLM service"`
- The document appears as "Queued" in the UI with a note about waiting for LLM
- The retry mechanism from Story 6.1 already works — user can click retry when Ollama is back
- Story 6.2 (future) will auto-retry these documents on Ollama recovery

**Alternative considered:** A dedicated `"waiting"` status. Rejected — it would require frontend status label/style additions and doesn't add value over "queued" with an informative message. The existing `failed_stage = "preflight"` flag already distinguishes "waiting for Ollama" from "genuinely queued."

### Query Pipeline: Qdrant Down Fallback

**Current code** (in `query.py`, `execute_query()`):
```python
graph_results, vector_results = await asyncio.gather(graph_task, vector_task, return_exceptions=True)
if isinstance(vector_results, Exception):
    logger.warning("Vector search failed, continuing with graph-only results")
    vector_results = []
```

**Add:** Before continuing, yield a `query.degraded` SSE event so the frontend knows results are partial. Also set a `degraded` flag on the `query.complete` event payload.

### Frontend Toast System

The project already uses a toast notification system (shadcn/ui `sonner` or similar). Check `apps/web/src/components/ui/` for the toast component.

**Service recovery toast:** Green left border, "Ollama is back online", auto-dismiss 5s
**Service failure toast:** Amber left border, "Ollama is unavailable — some features are limited", persists until dismissed

**UX spec reference (line 713):** "Honest failure with recovery — Every error state includes: what happened, what's affected, and what to do about it."

### Important Patterns from Story 6.1

1. **Celery tasks use sync sessions** — `SyncSessionLocal()` from `app/db/sync_postgres.py`. API endpoints use async sessions.
2. **SSE events are best-effort** — `_publish_safe()` wrapper never raises. Commit DB state before publishing.
3. **Fork-safe client creation** — Neo4j, Qdrant, Redis clients created per-task inside the task function.
4. **RFC 7807 error format** — All API errors: `{type, title, status, detail, instance}`.
5. **OpenAPI type generation** — Backend exports JSON → frontend regenerates types. Both must run after schema changes.
6. **TanStack Query cache invalidation** — Use `queryClient.invalidateQueries({queryKey: ["health"]})` to force StatusBar re-render.
7. **Test baselines** — ~316 backend tests, ~225 frontend tests. Add ~10-12 backend + ~8-10 frontend tests.

### Project Structure Notes

- **New files:**
  - `apps/api/app/services/health_monitor.py` — HealthMonitorService (background health polling + SSE)
  - `apps/web/src/hooks/useSystemSSE.ts` — global SSE hook for system events
  - `apps/api/tests/services/test_health_monitor.py` — health monitor tests
- **Modified files:**
  - `apps/api/app/main.py` — start health monitor in lifespan
  - `apps/api/app/services/events.py` — add `publish_system()` or handle `investigation_id="system"`
  - `apps/api/app/services/graph_query.py` — add Neo4j error handling
  - `apps/api/app/services/query.py` — add `query.degraded` event, align error messages
  - `apps/api/app/api/v1/graph.py` — add 503 error handling
  - `apps/api/app/api/v1/events.py` — add system SSE endpoint
  - `apps/api/app/worker/tasks/process_document.py` — change preflight fail behavior
  - `apps/web/src/hooks/useQueryStream.ts` — handle `query.degraded` event
  - `apps/web/src/components/graph/GraphCanvas.tsx` — add degradation states
  - `apps/web/src/components/qa/AnswerPanel.tsx` or `QueryInput.tsx` — add Ollama unavailable state
  - `apps/web/src/components/layout/StatusBar.tsx` — add Qdrant-specific tooltip
  - `apps/web/src/routes/__root.tsx` — mount `useSystemSSE` hook

### UX Specifications

- **Graph degraded state** (UX spec line 971): "When Ollama is down: graph fully interactive, badge indicating 'Q&A unavailable'"
- **Q&A error state** (UX spec line 787): "LLM service unavailable — try again shortly. Graph exploration still works."
- **Graph unavailable** (UX spec line 1198): "Service degradation badge appears in graph header"
- **Status colors** (UX spec line 353-354): Warning `#c4a265` (`--status-warning`), Error `#c47070` (`--status-error`)
- **Error messaging principle** (UX spec line 713): "Honest failure with recovery — Every error state includes: what happened, what's affected, and what to do about it."

### Performance Considerations

- Health monitor polls every 15s — negligible overhead (5 lightweight checks, each with 5s timeout)
- Redis state comparison is O(1) — compare 5 string values
- SSE system channel is lightweight — only fires on state transitions (rare events)
- No performance regression on happy path — degradation code only activates on service failure

### References

- [Source: _bmad-output/planning-artifacts/epics.md — Epic 6, Story 6.3 acceptance criteria]
- [Source: _bmad-output/planning-artifacts/prd.md — FR38, FR39, FR40; NFR26, NFR27]
- [Source: _bmad-output/planning-artifacts/architecture.md — Lines 287-307: API endpoints including events endpoint]
- [Source: _bmad-output/planning-artifacts/architecture.md — Lines 309-313: SSE via Redis pub/sub, per-investigation channels]
- [Source: _bmad-output/planning-artifacts/architecture.md — Lines 460-483: SSE event format and types including service.status]
- [Source: _bmad-output/planning-artifacts/architecture.md — Lines 487-503: Error handling patterns — backend and frontend]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — Line 713: Honest failure with recovery messaging]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — Line 787: Q&A error state message]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — Line 971: Graph degraded state with Q&A unavailable badge]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — Line 1198: Service degradation badge in graph header]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — Lines 353-354: Status warning/error colors]
- [Source: apps/api/app/services/health.py — HealthService with parallel checks, StatusEnum, 5s timeouts]
- [Source: apps/api/app/services/query.py — execute_query with asyncio.gather, Qdrant silent fallback, OllamaUnavailableError/GraphUnavailableError handlers]
- [Source: apps/api/app/services/graph_query.py — GraphQueryService with no error handling, Neo4j sessions propagate exceptions]
- [Source: apps/api/app/services/events.py — EventPublisher with Redis pub/sub, _publish_safe wrapper]
- [Source: apps/api/app/api/v1/graph.py — Graph endpoints with no try-catch]
- [Source: apps/api/app/api/v1/events.py — SSE endpoint subscribing to events:{investigation_id}]
- [Source: apps/api/app/worker/tasks/process_document.py — Pre-flight Ollama check, immediate failure on unavailable]
- [Source: apps/api/app/exceptions.py — OllamaUnavailableError, GraphUnavailableError, ServiceUnavailableError (all 503)]
- [Source: apps/web/src/hooks/useSSE.ts — document/entity event handlers, no service.status handler]
- [Source: apps/web/src/hooks/useQueryStream.ts — query event handlers, query.failed error display]
- [Source: apps/web/src/components/layout/StatusBar.tsx — useHealthStatus polling, 30s refresh]
- [Source: apps/web/src/components/graph/GraphCanvas.tsx — Cytoscape rendering, no degradation state]
- [Source: apps/web/src/components/qa/AnswerPanel.tsx — Error display with retry button]

### Previous Story Intelligence (Story 6.1 Learnings)

1. **RFC 7807 error pattern** — `DomainError(detail, status_code, error_type)` constructor. `GraphUnavailableError` already exists and follows this pattern.
2. **Stage-aware processing** — `failed_stage` column and `resume_from_stage` parameter are established. Preflight failure currently sets `failed_stage = "preflight"` — this story changes the behavior (keep queued instead of failing).
3. **SSE event payload convention** — Events are `{type, investigation_id, timestamp, payload: {...}}`. The `service.status` event should follow this format but use `investigation_id: "system"`.
4. **Frontend optimistic updates** — TanStack Query cache is updated optimistically on mutations, then invalidated. For service status, invalidation on SSE event is the right pattern (not optimistic).
5. **Test patterns** — Backend: `pytest` + `httpx.AsyncClient`, fixtures in `conftest.py`. Frontend: Vitest + Testing Library + React Query wrapper.
6. **Pre-existing test failures** — `TestEntityExtractionStage::test_entity_discovered_sse_events_published` (mock issue), `test_docker_compose.py` (2 infra failures), `SystemStatusPage.test.tsx` (4 TanStack Router context failures). Do not fix these — they are pre-existing.

### Git Intelligence

Recent commits:
- `762b9a0` — feat: Story 6.1 — failed document detection and manual retry with code review fixes
- `55ea6f2` — feat: real-time document processing progress & native Ollama for Metal GPU
- `e0931c0` — feat: graph-first query pipeline, dynamic relationships, Dockerized dev stack
- `fc6ab6a` — feat: Story 5.3 — citation click-through viewer with code review fixes

**Commit pattern:** `feat: Story X.Y — description`

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
