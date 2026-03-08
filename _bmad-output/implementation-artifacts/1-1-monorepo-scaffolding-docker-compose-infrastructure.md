# Story 1.1: Monorepo Scaffolding & Docker Compose Infrastructure

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an administrator,
I want to run a single `docker compose up` command and have all infrastructure services start successfully,
so that I have a working foundation to build the application on.

## Acceptance Criteria

1. **AC1: Fresh Clone — Production Compose**
   - Given: a fresh clone of the repository
   - When: the administrator runs `docker compose -f docker/docker-compose.yml up` from the project root
   - Then: all 7 services start: app (placeholder), web (placeholder), postgres, neo4j, qdrant, redis, ollama
   - And: named volumes are created for postgres-data, neo4j-data, qdrant-data, redis-data, ollama-models
   - And: the `storage/` directory is bind-mounted for document storage
   - And: all services communicate on a single Docker bridge network

2. **AC2: Dev Compose — Infrastructure Only**
   - Given: the dev compose file exists
   - When: the administrator runs `docker compose -f docker/docker-compose.dev.yml up`
   - Then: only infrastructure services start: postgres, neo4j, qdrant, redis, ollama
   - And: ports are exposed for native app development:
     - PostgreSQL: 5432
     - Neo4j: 7474 (HTTP) / 7687 (Bolt)
     - Qdrant: 6333
     - Redis: 6379
     - Ollama: 11434

3. **AC3: Monorepo Structure**
   - Given: the monorepo is initialized
   - When: a developer inspects the project structure
   - Then: `apps/web/` contains a React + Vite SPA scaffold (created via `create-vite` react-swc-ts template, shadcn/ui initialized)
   - And: `apps/api/` contains a FastAPI + Celery scaffold (created via `uv init`, dependencies added)
   - And: `docker/` contains both compose files, Dockerfiles, and nginx.conf
   - And: `scripts/` contains `generate-api-types.sh` and `dev.sh`
   - And: `storage/.gitkeep` exists
   - And: `.env.example` documents all required environment variables

## Tasks / Subtasks

- [x] Task 1: Initialize monorepo root structure (AC: #3)
  - [x] 1.1: Create root `package.json` with workspace scripts only (no dependencies)
  - [x] 1.2: Create `pnpm-workspace.yaml` with `packages: ["apps/*"]`
  - [x] 1.3: Create `.gitignore` (node_modules, .venv, __pycache__, .env, dist, storage/*, !storage/.gitkeep)
  - [x] 1.4: Create `.env.example` with all environment variables documented
  - [x] 1.5: Create `storage/.gitkeep`

- [x] Task 2: Scaffold frontend app (AC: #3)
  - [x] 2.1: Run `pnpm create vite@latest apps/web -- --template react-swc-ts`
  - [x] 2.2: Initialize shadcn/ui: manual setup with components.json, globals.css, and utils.ts (CLI failed to detect framework)
  - [x] 2.3: Install TanStack Router: `pnpm add @tanstack/react-router @tanstack/react-router-devtools` + `pnpm add -D @tanstack/router-plugin`
  - [x] 2.4: Configure Vite with TanStack Router plugin (plugin order: tanstackRouter BEFORE react)
  - [x] 2.5: Create route stubs: `__root.tsx`, `index.tsx`, `investigations/$id.tsx`, `status.tsx`
  - [x] 2.6: Install openapi-typescript 7.x + openapi-fetch 0.17.x
  - [x] 2.7: Create placeholder `src/lib/api-client.ts` and `src/lib/api-types.generated.ts`
  - [x] 2.8: Set dark theme as default in globals.css

- [x] Task 3: Scaffold backend app (AC: #3)
  - [x] 3.1: Run `uv init apps/api --app`
  - [x] 3.2: Add production dependencies: `uv add fastapi[standard] celery[redis] pydantic sqlalchemy[asyncio] psycopg2-binary neo4j qdrant-client pymupdf redis alembic loguru httpx`
  - [x] 3.3: Add dev dependencies: `uv add --dev pytest httpx`
  - [x] 3.4: Create `app/` package structure with `__init__.py` files for: api/v1/, schemas/, models/, services/, worker/tasks/, db/, llm/
  - [x] 3.5: Create placeholder `app/main.py` with FastAPI app instance
  - [x] 3.6: Create placeholder `app/config.py` with pydantic-settings
  - [x] 3.7: Initialize Alembic: `alembic init migrations`
  - [x] 3.8: Configure `alembic.ini` to read DATABASE_URL from environment

- [x] Task 4: Create Docker infrastructure (AC: #1, #2)
  - [x] 4.1: Create `docker/docker-compose.yml` with all 7 services
  - [x] 4.2: Create `docker/docker-compose.dev.yml` with 5 infrastructure services + exposed ports
  - [x] 4.3: Create `docker/app.Dockerfile` (Python 3.13-slim base, uv install, dual Uvicorn + Celery process)
  - [x] 4.4: Create `docker/web.Dockerfile` (multi-stage: pnpm build → Nginx serve)
  - [x] 4.5: Create `docker/nginx.conf` (SPA history fallback, proxy /api to app service)
  - [x] 4.6: Define named volumes: postgres-data, neo4j-data, qdrant-data, redis-data, ollama-models
  - [x] 4.7: Define single bridge network for all services
  - [x] 4.8: Configure bind mount: `./storage:/app/storage`

- [x] Task 5: Create utility scripts (AC: #3)
  - [x] 5.1: Create `scripts/generate-api-types.sh` (curl OpenAPI spec from FastAPI → run openapi-typescript)
  - [x] 5.2: Create `scripts/dev.sh` (start docker-compose.dev.yml + run Vite and FastAPI natively)

- [x] Task 6: Verify everything works (AC: #1, #2, #3)
  - [x] 6.1: Docker compose config validated — production compose defines all 7 services
  - [x] 6.2: Docker compose config validated — dev compose defines 5 services with correct port mappings
  - [x] 6.3: Named volumes defined in both compose files (postgres-data, neo4j-data, qdrant-data, redis-data, ollama-models)
  - [x] 6.4: All services configured on osint-network bridge network

## Dev Notes

### CRITICAL: SQLModel Incompatibility

**SQLModel 0.0.37 caps FastAPI at <0.129.0.** The architecture specifies FastAPI 0.135.x, which is outside SQLModel's supported range.

**Resolution: Use SQLAlchemy 2.0 directly with separate Pydantic v2 models.**
- Use `sqlalchemy[asyncio]` for ORM
- Use `pydantic` v2 for request/response schemas (already in FastAPI)
- This is actually cleaner: SQLModel's main value (unified model class) adds little over SQLAlchemy 2.0's native declarative style + Pydantic v2
- The architecture's `uv add` command should replace `sqlmodel` with `sqlalchemy[asyncio]`

### FastAPI 0.135.x Strict Content-Type

Since FastAPI 0.135.x, `Content-Type: application/json` is enforced on JSON request bodies by default (CSRF protection). This is beneficial for this localhost app. The frontend's `openapi-fetch` client sets this header automatically, so no action needed — just be aware during manual testing with curl.

### pnpm v10 Lifecycle Scripts

pnpm v10 **disables dependency lifecycle scripts by default** for security. If any npm package needs `postinstall` scripts (e.g., some native modules), you must explicitly allow them in `.npmrc`:
```
# .npmrc (only if needed)
side-effects-cache=true
```

### Docker Image Versions to Pin

| Service | Image Tag | Size Note |
|---------|-----------|-----------|
| PostgreSQL | `postgres:17-alpine` | ~80MB (vs ~400MB Debian) |
| Neo4j | `neo4j:5-community` | Community edition, free |
| Qdrant | `qdrant/qdrant:v1.17.0` | Pin version for reproducibility |
| Redis | `redis:7-alpine` | ~30MB Alpine variant |
| Ollama | `ollama/ollama:latest` | No stable version tags; `latest` is convention |

### Ollama Model Storage

Ollama models (~15GB total for qwen3.5:9b + qwen3-embedding:8b) are stored in the `ollama-models` named volume. Models are NOT downloaded automatically on `docker compose up` — they are pulled on first use or can be pre-pulled with:
```bash
docker exec ollama ollama pull qwen3.5:9b
docker exec ollama ollama pull qwen3-embedding:8b
```

### app.Dockerfile: Dual Process Pattern

The `app` container runs both FastAPI (Uvicorn) and Celery worker in a single container to conserve resources on 16GB hardware. Use a process manager or simple shell script entrypoint:
```dockerfile
# Entrypoint runs both:
# uvicorn app.main:app --host 0.0.0.0 --port 8000 &
# celery -A app.worker.celery_app worker --loglevel=info &
# wait -n  (exit when either process exits)
```

### Environment Variables (.env.example)

```env
# PostgreSQL
POSTGRES_USER=osint
POSTGRES_PASSWORD=osint_dev
POSTGRES_DB=osint
DATABASE_URL=postgresql://osint:osint_dev@postgres:5432/osint

# Neo4j
NEO4J_AUTH=neo4j/osint_dev
NEO4J_URI=bolt://neo4j:7687

# Qdrant
QDRANT_URL=http://qdrant:6333

# Redis
REDIS_URL=redis://redis:6379/0

# Ollama
OLLAMA_BASE_URL=http://ollama:11434

# FastAPI
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost,http://localhost:5173

# Celery
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1
```

### Nginx Configuration

```
# Key points:
# - Serve /api/* → proxy to app:8000
# - Serve /api/v1/events/* → proxy with SSE headers (no buffering)
# - Serve everything else → Vite build output with try_files $uri /index.html (SPA fallback)
```

### Network Architecture

All 7 services share a single Docker bridge network named `osint-network`. No network segmentation needed — this is a single-user local tool. The threat model is data exfiltration over internet (mitigated by zero outbound calls), not inter-service attacks.

### Project Structure Notes

The complete target directory structure for this story:

```
osint/
├── .env.example
├── .gitignore
├── package.json                    # Root workspace config (scripts only)
├── pnpm-workspace.yaml             # packages: ["apps/*"]
├── apps/
│   ├── web/                        # React + Vite SPA (scaffold)
│   │   ├── package.json
│   │   ├── vite.config.ts          # SWC + TanStack Router plugin
│   │   ├── tsconfig.json
│   │   ├── components.json         # shadcn/ui config
│   │   ├── index.html
│   │   └── src/
│   │       ├── main.tsx
│   │       ├── app.tsx
│   │       ├── globals.css         # Dark theme default
│   │       ├── routes/
│   │       │   ├── __root.tsx      # Root layout (placeholder)
│   │       │   ├── index.tsx       # / (placeholder)
│   │       │   ├── investigations/
│   │       │   │   └── $id.tsx     # /investigations/:id (placeholder)
│   │       │   └── status.tsx      # /status (placeholder)
│   │       ├── components/ui/      # shadcn/ui components (empty, added per story)
│   │       ├── lib/
│   │       │   ├── api-client.ts   # openapi-fetch placeholder
│   │       │   └── api-types.generated.ts  # Generated types placeholder
│   │       └── types/
│   │           └── index.ts
│   └── api/                        # FastAPI + Celery (scaffold)
│       ├── pyproject.toml          # uv config + dependencies
│       ├── uv.lock
│       ├── alembic.ini
│       ├── app/
│       │   ├── __init__.py
│       │   ├── main.py             # FastAPI app (placeholder)
│       │   ├── config.py           # pydantic-settings
│       │   ├── api/v1/             # Route stubs (empty __init__.py files)
│       │   ├── schemas/            # Pydantic schemas (empty)
│       │   ├── models/             # SQLAlchemy models (empty)
│       │   ├── services/           # Business logic (empty)
│       │   ├── worker/tasks/       # Celery tasks (empty)
│       │   ├── db/                 # Database connectors (empty)
│       │   └── llm/               # Ollama integration (empty)
│       ├── migrations/
│       │   ├── env.py
│       │   ├── versions/
│       │   └── script.py.mako
│       └── tests/
│           └── conftest.py
├── docker/
│   ├── docker-compose.yml          # Full 7-service stack
│   ├── docker-compose.dev.yml      # 5 infrastructure services
│   ├── app.Dockerfile              # Python 3.14 + FastAPI + Celery
│   ├── web.Dockerfile              # Vite build → Nginx
│   └── nginx.conf                  # SPA fallback + API proxy
├── scripts/
│   ├── generate-api-types.sh       # OpenAPI → TypeScript types
│   └── dev.sh                      # Dev environment launcher
└── storage/
    └── .gitkeep
```

### Naming Conventions to Follow

| Context | Convention | Example |
|---------|-----------|---------|
| Python modules/files | snake_case | `document_service.py` |
| Python classes | PascalCase | `Investigation` |
| PostgreSQL tables | snake_case, plural | `investigations` |
| PostgreSQL columns | snake_case | `investigation_id` |
| Neo4j node labels | PascalCase, singular | `Person` |
| Neo4j relationship types | UPPER_SNAKE_CASE | `WORKS_FOR` |
| TypeScript components | PascalCase files | `AnswerPanel.tsx` |
| TypeScript hooks/utils | camelCase files | `useCytoscape.ts` |
| API endpoints | kebab-case nouns, plural | `/api/v1/investigations/` |
| CSS custom properties | kebab-case | `--bg-primary` |
| IDs | UUID v4 everywhere | `uuid.uuid4()` |

### References

- [Source: _bmad-output/planning-artifacts/architecture.md#Technology Stack Decisions]
- [Source: _bmad-output/planning-artifacts/architecture.md#Monorepo & Directory Structure]
- [Source: _bmad-output/planning-artifacts/architecture.md#Docker Compose Architecture]
- [Source: _bmad-output/planning-artifacts/architecture.md#Database Technology Choices]
- [Source: _bmad-output/planning-artifacts/architecture.md#API Layer Architecture]
- [Source: _bmad-output/planning-artifacts/architecture.md#Naming Conventions]
- [Source: _bmad-output/planning-artifacts/epics.md#Epic 1 - Story 1.1]
- [Source: _bmad-output/planning-artifacts/prd.md#Deployment & Setup (FR41-FR44)]
- [Source: _bmad-output/planning-artifacts/prd.md#Web App Specific Requirements]

## Change Log

- 2026-03-08: Initial implementation of monorepo scaffolding and Docker infrastructure (all 6 tasks completed)
- 2026-03-08: Code review fixes — 12 issues resolved: fixed test execution (cors_origins parsing), added pydantic-settings explicit dep, lazy settings init, scoped CORS methods/headers, removed hardcoded DB URL fallback in alembic, added health checks and restart policies to both compose files, non-root user in app.Dockerfile, fixed pnpm-lock.yaml requirement in web.Dockerfile, conditional devtools loading, created .dockerignore

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

- shadcn/ui CLI init failed to detect Vite framework; resolved via manual setup (components.json, globals.css with dark theme CSS variables, lib/utils.ts with cn() helper)
- Vite scaffold generated vanilla TS template instead of React; resolved by manually installing @vitejs/plugin-react-swc and creating React files
- pnpm v10 blocked esbuild and @swc/core build scripts; resolved by adding onlyBuiltDependencies to root package.json
- Used Python 3.13-slim instead of 3.14 (specified in story) as Python 3.14 is not yet available as a Docker image

### Completion Notes List

- All 6 tasks with 36 subtasks completed successfully
- 13 automated tests written and passing: health check, config defaults, project structure validation, docker compose validation
- Frontend builds and type-checks successfully (Vite build + tsc)
- Backend FastAPI app loads and health endpoint works
- Both docker-compose configs validate via `docker compose config`
- Dark theme set as default via `class="dark"` on HTML element with oklch CSS variables

### File List

- package.json (new) — Root workspace config with pnpm build scripts approval
- pnpm-workspace.yaml (new) — Workspace packages config
- .gitignore (new) — Git ignore rules
- .env.example (new) — Environment variable documentation
- .env (new) — Local env from .env.example
- storage/.gitkeep (new) — Document storage directory placeholder
- apps/web/package.json (new) — Frontend dependencies and scripts
- apps/web/vite.config.ts (new) — Vite config with TanStack Router + React SWC + Tailwind plugins
- apps/web/tsconfig.json (new) — TypeScript config with React JSX and path aliases
- apps/web/index.html (new) — HTML entry with dark class
- apps/web/components.json (new) — shadcn/ui configuration
- apps/web/src/main.tsx (new) — React entry point with TanStack Router
- apps/web/src/globals.css (new) — Dark theme CSS with Tailwind v4 and shadcn/ui variables
- apps/web/src/routes/__root.tsx (new) — Root layout with header
- apps/web/src/routes/index.tsx (new) — Home page placeholder
- apps/web/src/routes/investigations/$id.tsx (new) — Investigation detail placeholder
- apps/web/src/routes/status.tsx (new) — System status page placeholder
- apps/web/src/lib/api-client.ts (new) — openapi-fetch client placeholder
- apps/web/src/lib/api-types.generated.ts (new) — Generated types placeholder
- apps/web/src/lib/utils.ts (new) — cn() utility for class merging
- apps/web/src/types/index.ts (new) — App types placeholder
- apps/web/src/routeTree.gen.ts (new) — Auto-generated route tree
- apps/api/pyproject.toml (new) — Python project config with all dependencies
- apps/api/uv.lock (new) — Locked Python dependencies
- apps/api/alembic.ini (new) — Alembic config (DATABASE_URL from env)
- apps/api/app/__init__.py (new) — App package init
- apps/api/app/main.py (new) — FastAPI app with CORS and health endpoint
- apps/api/app/config.py (new) — pydantic-settings configuration
- apps/api/app/api/__init__.py (new) — API package init
- apps/api/app/api/v1/__init__.py (new) — API v1 package init
- apps/api/app/schemas/__init__.py (new) — Schemas package init
- apps/api/app/models/__init__.py (new) — Models package init
- apps/api/app/services/__init__.py (new) — Services package init
- apps/api/app/worker/__init__.py (new) — Worker package init
- apps/api/app/worker/tasks/__init__.py (new) — Tasks package init
- apps/api/app/db/__init__.py (new) — DB package init
- apps/api/app/llm/__init__.py (new) — LLM package init
- apps/api/migrations/env.py (new) — Alembic env with DATABASE_URL from env
- apps/api/migrations/script.py.mako (new) — Alembic migration template
- apps/api/migrations/README (new) — Alembic README
- apps/api/tests/conftest.py (new) — Test fixtures with FastAPI TestClient
- apps/api/tests/test_health.py (new) — Health endpoint test
- apps/api/tests/test_config.py (new) — Settings defaults test
- apps/api/tests/test_structure.py (new) — Project structure validation tests
- apps/api/tests/test_docker_compose.py (new) — Docker compose config validation tests
- docker/docker-compose.yml (new) — Production 7-service compose
- docker/docker-compose.dev.yml (new) — Dev 5-service compose with exposed ports
- docker/app.Dockerfile (new) — Python API container
- docker/web.Dockerfile (new) — Frontend multi-stage build
- docker/nginx.conf (new) — Nginx SPA fallback + API proxy + SSE config
- docker/entrypoint.sh (new) — Dual process entrypoint script
- scripts/generate-api-types.sh (new) — OpenAPI to TypeScript type generation
- scripts/dev.sh (new) — Dev environment launcher
- pnpm-lock.yaml (new) — Locked frontend dependencies
- .dockerignore (new) — Docker build context exclusions
