# Story 1.2: Backend Health Checks & Model Readiness

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an administrator,
I want to see the health status of every service and know when LLM models are loaded,
so that I can verify the system is ready before starting an investigation.

## Acceptance Criteria

1. **AC1: Aggregate Health Endpoint**
   - Given all services are running
   - When a client sends `GET /api/v1/health/`
   - Then the response includes status for each service: postgres, neo4j, qdrant, redis, ollama
   - And each service reports "healthy", "unhealthy", or "unavailable" with a detail message
   - And Ollama status includes model readiness for qwen3.5:9b and qwen3-embedding:8b
   - And the response follows RFC 7807 format on errors

2. **AC2: Ollama Model Readiness — Models Not Downloaded**
   - Given Ollama is running but models are not yet downloaded
   - When a client sends `GET /api/v1/health/`
   - Then the Ollama status reports "unhealthy" with detail: "Models not ready: qwen3.5:9b, qwen3-embedding:8b"
   - And a `models_ready` boolean field is `false`

3. **AC3: Hardware Warnings**
   - Given the system is running on hardware below minimum spec
   - When the health endpoint detects insufficient resources
   - Then the response includes a warning with clear message about minimum requirements (16GB RAM, 8GB VRAM)

4. **AC4: Application Initialization**
   - Given the FastAPI app starts
   - When the application initializes
   - Then database connections are established to PostgreSQL (SQLAlchemy), Neo4j (driver), Qdrant (client), Redis (client)
   - And Alembic migrations run automatically on startup
   - And Loguru is configured for structured logging to stdout
   - And CORS is configured for localhost origins only (5173, 80)

## Tasks / Subtasks

- [x] Task 1: Create database connection modules (AC: #4)
  - [x] 1.1: Create `app/db/postgres.py` — async SQLAlchemy engine + session factory using `create_async_engine` with `DATABASE_URL` from settings; expose `get_db()` async generator for FastAPI dependency injection
  - [x] 1.2: Create `app/db/neo4j.py` — Neo4j async driver using `AsyncGraphDatabase.driver()` with `NEO4J_URI` and parsed `NEO4J_AUTH` from settings; expose lifespan-managed driver instance
  - [x] 1.3: Create `app/db/qdrant.py` — `QdrantClient` instance using `QDRANT_URL` from settings; expose singleton client
  - [x] 1.4: Create `app/db/redis.py` — `redis.asyncio.Redis.from_url()` using `REDIS_URL` from settings; expose singleton client

- [x] Task 2: Configure Loguru structured logging (AC: #4)
  - [x] 2.1: Add Loguru configuration in `app/main.py` — remove default handler, add stdout handler with structured format (`{time} | {level} | {message}` + extras as key-value pairs)
  - [x] 2.2: Intercept standard library logging (uvicorn, celery) into Loguru using `InterceptHandler`

- [x] Task 3: Create health check service layer (AC: #1, #2, #3)
  - [x] 3.1: Create `app/schemas/health.py` — Pydantic response models: `ServiceStatus` (name, status enum, detail, optional metadata), `OllamaStatus` (extends ServiceStatus with `models_ready` bool and `models` list), `HealthResponse` (services dict, overall_status, warnings list, timestamp)
  - [x] 3.2: Create `app/services/health.py` — `HealthService` with async methods:
    - `check_postgres()` — execute `SELECT 1` via SQLAlchemy session
    - `check_neo4j()` — call `driver.verify_connectivity()` via neo4j async driver
    - `check_qdrant()` — call `client.info()` via qdrant-client (sync, run in threadpool)
    - `check_redis()` — call `client.ping()` via redis-py async
    - `check_ollama()` — `GET /api/tags` via httpx to list downloaded models, check for `qwen3.5:9b` and `qwen3-embedding:8b` presence
    - `check_hardware()` — use `psutil` or `/proc/meminfo` to check RAM (warn if <16GB); note: VRAM detection is best-effort only
    - `get_health()` — orchestrate all checks concurrently via `asyncio.gather`, aggregate into `HealthResponse`

- [x] Task 4: Create health check API endpoint (AC: #1, #2, #3)
  - [x] 4.1: Create `app/api/v1/health.py` — `GET /api/v1/health/` route returning `HealthResponse`; overall_status is "healthy" only if ALL services are "healthy", otherwise "degraded" or "unhealthy"
  - [x] 4.2: Create `app/api/v1/router.py` — aggregate v1 router, include health router
  - [x] 4.3: Update `app/main.py` — replace inline health endpoint with v1 router; add lifespan handler for startup/shutdown of db connections

- [x] Task 5: Configure Alembic auto-migration on startup (AC: #4)
  - [x] 5.1: Add startup logic in `app/main.py` lifespan to run `alembic upgrade head` programmatically (using `alembic.command.upgrade`)
  - [x] 5.2: Update `migrations/env.py` to use async engine from `app/db/postgres.py`

- [x] Task 6: Create RFC 7807 error handling (AC: #1)
  - [x] 6.1: Create `app/exceptions.py` — domain exception classes (`ServiceUnavailableError`, `HealthCheckError`) mapping to RFC 7807 fields
  - [x] 6.2: Register exception handlers in `app/main.py` that return RFC 7807 JSON responses

- [x] Task 7: Write tests (AC: #1, #2, #3, #4)
  - [x] 7.1: Create `tests/api/test_health.py` — test health endpoint returns all 5 services; test degraded response when a service is down; test `models_ready: false` when Ollama models missing
  - [x] 7.2: Create `tests/services/test_health.py` — unit tests for each health check method with mocked clients
  - [x] 7.3: Update `tests/conftest.py` — add fixtures for mocked db clients (no real DB connections in tests)

## Dev Notes

### CRITICAL: SQLAlchemy (Not SQLModel)

Story 1.1 established that **SQLModel is incompatible** with FastAPI 0.135.x. Use `sqlalchemy[asyncio]` with `psycopg2-binary` (sync) for migrations and async engine for runtime. Pydantic v2 models serve as request/response schemas — separate from SQLAlchemy ORM models.

### Database Connection Patterns

**PostgreSQL (async):**
```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
# Use asyncpg driver: postgresql+asyncpg://...
# NOTE: pyproject.toml has psycopg2-binary (sync). You will need to add asyncpg for async.
# Alternatively, use psycopg (v3) async: postgresql+psycopg://... (psycopg[binary] supports async)
```

**Neo4j (async):**
```python
from neo4j import AsyncGraphDatabase
driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
# Health check: await driver.verify_connectivity()  -> returns None on success, raises on failure
```

**Qdrant:**
```python
from qdrant_client import QdrantClient
client = QdrantClient(url=settings.qdrant_url)
# Health check: client.info()  -> returns VersionInfo (sync only; wrap in run_in_executor for async)
```

**Redis (async):**
```python
import redis.asyncio as aioredis
client = aioredis.from_url(settings.redis_url)
# Health check: await client.ping()  -> returns True
```

### Ollama Health Check API

- **Liveness:** `GET /` returns `"Ollama is running"` (200 OK)
- **List models:** `GET /api/tags` returns `{"models": [{"name": "qwen3.5:9b", ...}, ...]}`
- **Check specific model:** `POST /api/show` with `{"model": "qwen3.5:9b"}` — 200 if exists, error if not
- **Required models:** `qwen3.5:9b` (extraction/query) and `qwen3-embedding:8b` (embeddings)
- Use `httpx.AsyncClient` for all Ollama HTTP calls

### Loguru Configuration

```python
from loguru import logger
import sys, logging

# Remove default handler
logger.remove()
# Add structured stdout handler
logger.add(sys.stdout, format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}", level="INFO")

# Intercept uvicorn/standard logging into Loguru
class InterceptHandler(logging.Handler):
    def emit(self, record):
        level = logger.level(record.levelname).name
        logger.opt(depth=6, exception=record.exc_info).log(level, record.getMessage())

logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
```

### Health Response Shape

```json
{
  "status": "healthy",
  "timestamp": "2026-03-08T14:30:00Z",
  "services": {
    "postgres": {"status": "healthy", "detail": "Connected"},
    "neo4j": {"status": "healthy", "detail": "Connected, server agent: Neo4j/5.x"},
    "qdrant": {"status": "healthy", "detail": "Connected, version: 1.17.0"},
    "redis": {"status": "healthy", "detail": "Connected"},
    "ollama": {
      "status": "healthy",
      "detail": "Running, all models ready",
      "models_ready": true,
      "models": [
        {"name": "qwen3.5:9b", "available": true},
        {"name": "qwen3-embedding:8b", "available": true}
      ]
    }
  },
  "warnings": []
}
```

When degraded:
```json
{
  "status": "degraded",
  "services": {
    "ollama": {
      "status": "unhealthy",
      "detail": "Models not ready: qwen3.5:9b, qwen3-embedding:8b",
      "models_ready": false,
      "models": [
        {"name": "qwen3.5:9b", "available": false},
        {"name": "qwen3-embedding:8b", "available": false}
      ]
    }
  },
  "warnings": ["System RAM below recommended 16GB minimum"]
}
```

### RFC 7807 Error Format

All API errors must follow this structure (already established in architecture):
```json
{
  "type": "urn:osint:error:service_unavailable",
  "title": "Service Unavailable",
  "status": 503,
  "detail": "PostgreSQL connection failed: Connection refused",
  "instance": "/api/v1/health/"
}
```

### Async Considerations

- All health checks MUST run concurrently via `asyncio.gather()` to avoid sequential latency
- Qdrant client is sync-only at the top level — wrap in `asyncio.to_thread()` or `loop.run_in_executor()`
- Set a timeout (3-5s) on each individual health check to prevent hanging
- Each check should catch exceptions and return "unavailable" status rather than propagating errors

### Dependency: asyncpg or psycopg v3

The current `pyproject.toml` only has `psycopg2-binary` (sync driver). For async PostgreSQL:
- **Option A:** Add `asyncpg` — most popular async PG driver, well-tested with SQLAlchemy async
- **Option B:** Add `psycopg[binary]>=3.2` — supports both sync and async, newer
- **Recommendation:** Use `asyncpg` — it's the most battle-tested async PG driver with SQLAlchemy

### Project Structure Notes

Files to create in this story:
```
apps/api/
├── app/
│   ├── main.py                 # MODIFY: add lifespan, v1 router, loguru, remove inline health
│   ├── exceptions.py           # NEW: domain exceptions + RFC 7807 handlers
│   ├── api/v1/
│   │   ├── router.py           # NEW: aggregate v1 router
│   │   └── health.py           # NEW: health check endpoint
│   ├── schemas/
│   │   ├── health.py           # NEW: health response models
│   │   └── error.py            # NEW: RFC 7807 error schema
│   ├── services/
│   │   └── health.py           # NEW: health check service
│   └── db/
│       ├── postgres.py         # NEW: async SQLAlchemy engine + session
│       ├── neo4j.py            # NEW: Neo4j async driver
│       ├── qdrant.py           # NEW: Qdrant client
│       └── redis.py            # NEW: async Redis client
├── migrations/
│   └── env.py                  # MODIFY: use engine from app/db/postgres.py
└── tests/
    ├── conftest.py             # MODIFY: add mock fixtures
    ├── api/
    │   └── test_health.py      # NEW: health endpoint tests
    └── services/
        └── test_health.py      # NEW: health service unit tests
```

### Naming Conventions to Follow

| Context | Convention | Example |
|---------|-----------|---------|
| Python modules/files | snake_case | `health.py`, `postgres.py` |
| Python classes | PascalCase | `HealthService`, `ServiceStatus` |
| API endpoints | kebab-case, plural | `/api/v1/health/` |
| Pydantic models | PascalCase | `HealthResponse`, `OllamaStatus` |
| Log messages | Structured key-value | `logger.info("Health check completed", status="healthy", duration_ms=42)` |

### Previous Story Intelligence

**From Story 1.1 implementation:**
- SQLModel dropped in favor of SQLAlchemy 2.0 + Pydantic v2 (separate models)
- Python 3.13-slim used (not 3.14 — not available as Docker image yet)
- shadcn/ui initialized manually (CLI failed)
- pnpm v10 blocks lifecycle scripts — `onlyBuiltDependencies` in root package.json
- CORS already configured in `app/main.py` with `cors_origins` from settings
- Health endpoint `GET /api/v1/health` exists as a placeholder returning `{"status": "ok"}`
- Test structure established: `tests/conftest.py` with `TestClient` fixture, `test_health.py`, `test_config.py`, `test_structure.py`, `test_docker_compose.py`
- Code review applied 12 fixes: lazy settings init, scoped CORS methods/headers, health checks in compose, non-root user in Dockerfile, .dockerignore

**Git Intelligence:**
- Commit `4feffbb`: feat: Story 1.1 — monorepo scaffolding & Docker Compose infrastructure
- Commit `8b59842`: Product idea
- All Story 1.1 code was reviewed and fixes applied — clean baseline to build on

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.2: Backend Health Checks & Model Readiness]
- [Source: _bmad-output/planning-artifacts/architecture.md#API Layer Architecture — GET /api/v1/health/]
- [Source: _bmad-output/planning-artifacts/architecture.md#Monorepo & Directory Structure — app/api/v1/health.py, app/services/health.py, app/db/*]
- [Source: _bmad-output/planning-artifacts/architecture.md#Infrastructure & Deployment — Logging (Loguru)]
- [Source: _bmad-output/planning-artifacts/architecture.md#Implementation Patterns — Error Handling, Logging Levels]
- [Source: _bmad-output/planning-artifacts/architecture.md#Format Patterns — RFC 7807]
- [Source: _bmad-output/planning-artifacts/prd.md#Deployment & Setup (FR41-FR44)]
- [Source: _bmad-output/planning-artifacts/prd.md#Journey 4 (Admin Setup)]
- [Source: _bmad-output/implementation-artifacts/1-1-monorepo-scaffolding-docker-compose-infrastructure.md#Dev Notes, Change Log]
- [Ollama API: GET /, GET /api/tags, POST /api/show — github.com/ollama/ollama/docs/api.md]
- [Neo4j Python driver 6.x: driver.verify_connectivity() — neo4j.com/docs/api/python-driver/current]
- [Qdrant Python client 1.17.x: client.info() — python-client.qdrant.tech]
- [Redis-py 6.x: client.ping() — redis.io/docs]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

- Old `tests/test_health.py` expected placeholder `{"status": "ok"}` — updated to match new structured response

### Completion Notes List

- Task 1: Created 4 database connection modules (postgres async via asyncpg, neo4j async, qdrant sync singleton, redis async). Added `asyncpg` and `psutil` to dependencies.
- Task 2: Configured Loguru with structured stdout handler and InterceptHandler to route stdlib logging (uvicorn, celery) through Loguru.
- Task 3: Created Pydantic schemas (`ServiceStatus`, `OllamaStatus`, `HealthResponse`, `RFC7807Error`) and `HealthService` with concurrent health checks via `asyncio.gather()`, 5s timeout per check, hardware RAM detection via psutil.
- Task 4: Created `GET /api/v1/health/` endpoint via v1 router. Replaced inline placeholder health endpoint. Overall status logic: healthy (all green), degraded (some unhealthy), unhealthy (any unavailable).
- Task 5: Added Alembic auto-migration on startup via lifespan handler. Updated `migrations/env.py` to use async engine with asyncpg.
- Task 6: Created domain exception hierarchy (`DomainError`, `ServiceUnavailableError`, `HealthCheckError`) with RFC 7807 JSON response format. Registered exception handlers in FastAPI app.
- Task 7: 20 tests covering all health check methods (healthy + failure), orchestrated health, API endpoint (all-healthy, degraded, models-not-ready, hardware-warning, trailing-slash). All mocked — no real DB connections in tests.

### Change Log

- 2026-03-08: Implemented Story 1.2 — Backend Health Checks & Model Readiness. Added aggregate health endpoint with 5 service checks (postgres, neo4j, qdrant, redis, ollama), model readiness detection, hardware warnings, Loguru logging, Alembic auto-migration, RFC 7807 error handling, and 20 tests.
- 2026-03-08: Code review applied 9 fixes: reverted Alembic env.py to sync engine (asyncio.run nested crash), robust Neo4j auth validation, robust postgres URL scheme handling, exception logging in generic error handler, RFC 7807 test coverage (2 tests), fixed overall status logic (all-unhealthy→unhealthy), removed duplicate test file, added mocks to trailing-slash test, updated File List with uv.lock.

### File List

New files:
- `apps/api/app/db/postgres.py`
- `apps/api/app/db/neo4j.py`
- `apps/api/app/db/qdrant.py`
- `apps/api/app/db/redis.py`
- `apps/api/app/schemas/health.py`
- `apps/api/app/schemas/error.py`
- `apps/api/app/services/health.py`
- `apps/api/app/api/v1/health.py`
- `apps/api/app/api/v1/router.py`
- `apps/api/app/exceptions.py`
- `apps/api/tests/api/__init__.py`
- `apps/api/tests/api/test_health.py`
- `apps/api/tests/services/__init__.py`
- `apps/api/tests/services/test_health.py`

Modified files:
- `apps/api/app/main.py` — replaced placeholder with lifespan, Loguru, v1 router, error handlers
- `apps/api/migrations/env.py` — reverted to sync engine (psycopg2) for Alembic compatibility with async lifespan
- `apps/api/pyproject.toml` — added asyncpg, psutil, pytest-asyncio
- `apps/api/tests/conftest.py` — added mock fixtures for all DB clients
- `apps/api/tests/test_health.py` — tests moved to tests/api/test_health.py
- `apps/api/uv.lock` — updated lockfile from dependency changes
