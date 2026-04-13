# OSINT API

FastAPI backend + Celery worker for the OSINT investigation platform.

## Stack

- Python 3.11, `uv` for dependency management
- FastAPI with async SQLAlchemy (PostgreSQL)
- Celery + Redis for async document processing
- Neo4j (graph), Qdrant (vectors), Ollama (local LLMs)
- Alembic for schema migrations
- Loguru for structured logging, RFC 7807 for error responses

## Running

```bash
# Install deps (creates .venv)
uv sync

# Run migrations
uv run alembic upgrade head

# Dev server
uv run fastapi dev app/main.py          # http://localhost:8000

# Worker (separate terminal)
uv run celery -A app.worker.celery_app worker --loglevel=info

# Tests
uv run pytest
uv run pytest tests/api/test_documents.py -v    # targeted
uv run pytest -k "test_merge" -v                # by name
```

## Layout

```
app/
  api/v1/            REST endpoints (documents, entities, relationships,
                     graph, query, cross_investigation, health, events)
  services/          Business logic (one module per bounded context)
    image_extraction.py   Tesseract OCR + moondream2 fallback
    vision.py             moondream2 via Ollama multimodal API
    web_capture.py        URL fetch + HTML-to-text conversion
    entity_query.py       CRUD + merge (atomic Neo4j transaction)
    cross_investigation.py  Cross-case entity matching & dismissal
    query.py              Graph-first RAG pipeline
    health.py             Per-service health + model readiness
  worker/tasks/       Celery tasks (process_document is the main pipeline)
  models/             SQLAlchemy ORM models
  schemas/            Pydantic request/response schemas
  db/                 Connection factories (postgres, neo4j, qdrant)
migrations/versions/  Alembic migrations
tests/
  api/                HTTP endpoint tests
  services/           Service-layer unit tests
  worker/             Celery task tests (many require Docker infra)
```

## Key Endpoints

| Route | Purpose |
|---|---|
| `POST /api/v1/investigations/` | Create investigation |
| `POST /api/v1/investigations/{id}/documents` | Upload PDF or image (multipart) |
| `POST /api/v1/investigations/{id}/documents/capture` | Capture URL as document |
| `POST /api/v1/investigations/{id}/entities/` | Create entity manually |
| `PATCH /api/v1/investigations/{id}/entities/{eid}` | Edit entity |
| `POST /api/v1/investigations/{id}/entities/merge/preview` | Preview merge |
| `POST /api/v1/investigations/{id}/entities/merge` | Execute atomic merge |
| `POST /api/v1/investigations/{id}/relationships/` | Create relationship manually |
| `GET  /api/v1/investigations/{id}/graph/` | Fetch graph subgraph |
| `POST /api/v1/investigations/{id}/query/` | Ask question (streams answer + citations) |
| `GET  /api/v1/investigations/{id}/cross-links/` | Per-investigation cross-links |
| `POST /api/v1/investigations/{id}/cross-links/dismiss` | Dismiss false-positive match |
| `GET  /api/v1/cross-links/entity-detail/` | Entity presence across investigations |
| `GET  /api/v1/cross-links/search/` | Cross-investigation entity search |
| `GET  /api/v1/investigations/{id}/events` | SSE stream of processing events |
| `GET  /api/v1/health/` | Service + model readiness |

Full OpenAPI at `http://localhost:8000/docs` when running.

## Document Processing Pipeline

`process_document_task` runs four stages:

1. **Text extraction** — routed by `document_type`:
   - `pdf` → PyMuPDF
   - `image` → Tesseract, with moondream2 enhancement when quality score < `OCR_QUALITY_THRESHOLD` (default 0.3). Stores `ocr_method` ("tesseract" / "tesseract+moondream2" / "moondream2") and `ocr_confidence` (0.0–1.0)
   - `web` → content already fetched at upload time by `web_capture.fetch_and_store`
2. **Chunking** — split by `--- Page N ---` markers for provenance
3. **Entity extraction** — qwen3.5:9b via Ollama; entities/relationships written to Neo4j with provenance edges to chunks
4. **Embedding** — qwen3-embedding:8b; stored in single Qdrant collection with `investigation_id` payload (enables cross-investigation similarity)

All stages publish SSE events via `EventPublisher`. Failures set `document.failed_stage` for precise retry resumption.

## Migration Chain

Migrations are strictly linear (check `down_revision` before adding):

```
001 investigations → 002 documents → 003 extracted_text → 004 chunks
  → 005 confidence → 006 failed_stage → 007 retry_count → 008 document_type
  → 009 source_url → 010 ocr_method → 011 dismissed_matches → 012 ocr_confidence
```

## Conventions

- **Service layer** — business logic lives in `app/services/`; API handlers and Celery tasks orchestrate services, not raw DB access
- **Sync vs async sessions** — API endpoints use `AsyncSession`; Celery tasks use `SyncSessionLocal()`
- **SSE publishing** — always use `_publish_safe()`; commit DB state before publishing so consumers read consistent data
- **Errors** — raise `DomainError` subclasses from services; the exception handler emits RFC 7807 JSON
- **Logging** — structured via Loguru, e.g. `logger.info("OCR completed", document_id=doc_id, chars=len(text))`
- **OpenAPI regen** — after any schema change, run `../../scripts/generate-api-types.sh` to update frontend types

## Pre-existing Test Failures (Known)

These fail without additional setup and are not caused by new work — do not treat as regressions:

- `tests/worker/test_process_document.py` — ~22 failures requiring Docker infrastructure (Qdrant, Neo4j) to be live
- `tests/docker/test_docker_compose.py` — infrastructure smoke tests
- `test_entity_discovered_sse_events_published` — mock limitation
