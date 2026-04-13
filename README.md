# OSINT

A local-first investigation platform for journalists and OSINT researchers. Ingests documents (PDFs, images, web pages), extracts entities and relationships with local LLMs, and answers natural-language questions with full source citations — all without data ever leaving the machine.

## Features

### Document Ingestion
- **PDFs** — text extraction via PyMuPDF with page-level provenance
- **Images** (JPEG, PNG, TIFF) — Tesseract OCR with automatic moondream2 vision-AI fallback for low-quality scans
- **Web pages** — URL-based capture, HTML → text conversion, stored immutably; outbound calls are opt-in per action
- **Processing dashboard** — real-time SSE progress through extract → chunk → entities → embed stages with per-service status

### Knowledge Graph
- Entities (person / organization / location) and typed relationships extracted via `qwen3.5:9b` (Ollama)
- Confidence scores at document and entity level, surfaced via solid/dashed/dotted badge borders
- **Interactive graph canvas** (Cytoscape.js) with type/source filtering, search highlighting, entity detail card
- **Provenance chains** — every entity and relationship traces back to the source document chunk

### Manual Curation (Epic 8)
- Create entities and relationships by hand with source annotations (`source="manual"`)
- Edit entity names and properties; previous names preserved as aliases
- **Atomic entity merge** — combine duplicates across Neo4j in a single write transaction, consolidating duplicate relationships, citations, and aliases
- Duplicate detection with fuzzy + contextual matching and approve/reject review panel

### Natural-Language Q&A
- Graph-first pipeline: relevant subgraph → LLM → answer with inline citations
- Streaming responses, click-through citation modal, web citations link back to source URL
- Full text viewer with OCR source banner indicating Tesseract vs. moondream2 provenance

### Cross-Investigation Intelligence (Epic 10)
- Automatic detection of entities shared across investigations (name + type + contextual similarity)
- Cross-investigation search panel with detail view per investigation
- Dismissed-match memory avoids re-surfacing false positives
- Investigation cards on the home page show shared-entity counts

### Resilience (Epic 6)
- Per-service health checks (Postgres, Neo4j, Qdrant, Redis, Ollama) with graceful degradation
- Auto-retry on service recovery; manual retry for failed documents; RFC 7807 error responses throughout

## Architecture

- **Backend** — FastAPI + SQLAlchemy (async) + Alembic migrations
- **Worker** — Celery + Redis for async document processing
- **Storage** — PostgreSQL (metadata) · Neo4j (graph) · Qdrant (embeddings, single collection with `investigation_id` payload filter) · Filesystem (immutable document storage with SHA-256 checksums)
- **LLM** — Ollama (local): `qwen3.5:9b` (entities) · `qwen3-embedding:8b` (vectors) · `moondream2` (vision/OCR enhancement)
- **Frontend** — React 19 + TanStack Router/Query + Tailwind + shadcn/ui + Cytoscape.js
- **Transport** — SSE for real-time processing events

## Running Locally

### Prerequisites

- Docker & Docker Compose
- Python 3.11 with [`uv`](https://github.com/astral-sh/uv)
- Node.js 20+ with `pnpm`
- Tesseract OCR (installed automatically in the Docker image; for local dev outside Docker, install via `brew install tesseract` / `apt-get install tesseract-ocr`)
- [Ollama](https://ollama.com) with the following models pulled:
  ```bash
  ollama pull qwen3.5:9b        # entity extraction
  ollama pull qwen3-embedding:8b # vector embeddings
  ollama pull moondream2         # vision-AI OCR fallback (Story 7.2)
  ```

### 1. Infrastructure (Docker) — start first

```bash
# From project root
docker compose -f docker/docker-compose.dev.yml up -d
```

Starts: **PostgreSQL** (5432), **Neo4j** (7474/7687), **Qdrant** (6333), **Redis** (6379)

Optional — Ollama in Docker (if not running on host):

```bash
docker compose -f docker/docker-compose.dev.yml --profile ollama up -d
```

### 2. DB Migrations (run once / on schema changes)

```bash
cd apps/api
uv run alembic upgrade head
```

### 3. Backend API (FastAPI)

```bash
cd apps/api
uv run fastapi dev app/main.py
```

Runs at: `http://localhost:8000` | Docs: `http://localhost:8000/docs`

### 4. Celery Worker

```bash
cd apps/api
uv run celery -A app.worker.celery_app worker --loglevel=info
```

### 5. Frontend (React/Vite)

```bash
cd apps/web
pnpm install   # first time only
pnpm dev
```

Runs at: `http://localhost:5173`

### Recommended startup order

1. Docker services
2. Alembic migrations
3. FastAPI (BE)
4. Celery worker
5. Frontend

## Dev Tooling

- **Backend (Python)**: `uv` — run commands with `uv run` from `apps/api/`
  - Tests: `cd apps/api && uv run pytest`
  - Lint: `cd apps/api && uv run ruff check .`
  - Python version: 3.11
- **Frontend (TypeScript/React)**: `pnpm` monorepo (see `pnpm-workspace.yaml`)
  - Tests: `cd apps/web && pnpm test`
  - Lint: `cd apps/web && pnpm lint`
- **OpenAPI types** — regenerate after backend schema changes (backend must be running):
  ```bash
  ./scripts/generate-api-types.sh
  ```

## Project Layout

```
apps/
  api/              # FastAPI backend
    app/
      api/v1/       # REST endpoints
      services/     # Business logic
      worker/       # Celery tasks
      models/       # SQLAlchemy models
      schemas/      # Pydantic schemas
    migrations/     # Alembic migrations
    tests/
  web/              # React frontend
    src/
      components/   # UI components (graph, investigation, qa, cross-investigation)
      routes/       # TanStack Router pages
      hooks/        # React Query hooks
docker/             # Docker Compose + Dockerfiles
scripts/            # Dev utilities (OpenAPI type generation, etc.)
_bmad-output/
  planning-artifacts/    # PRD, architecture, epics, UX spec
  implementation-artifacts/  # Per-story specs and sprint status
```

## Privacy Model

All processing is local. The only outbound network calls are **web page captures**, which occur only when a user explicitly submits a URL — no automatic or background outbound traffic. See `NFR14` in the PRD.
