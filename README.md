# OSINT

## Running Locally

### 1. Infrastructure (Docker) — start first

```bash
# From project root
docker compose -f docker/docker-compose.dev.yml up -d
```

Starts: **PostgreSQL** (5432), **Neo4j** (7474/7687), **Qdrant** (6333), **Redis** (6379)

Optional — Ollama for local LLM:

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

---

### Recommended startup order

1. Docker services
2. Alembic migrations
3. FastAPI (BE)
4. Celery worker
5. Frontend

## Dev Tooling

- **Backend (Python)**: `uv` — run commands with `uv run` from `apps/api/`
  - Tests: `cd apps/api && uv run pytest`
  - Python version: 3.11
- **Frontend (TypeScript/React)**: `pnpm` monorepo
  - Tests: `cd apps/web && pnpm test`
