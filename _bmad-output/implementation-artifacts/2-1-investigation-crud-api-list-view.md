# Story 2.1: Investigation CRUD API & List View

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an investigator,
I want to create, view, and delete investigations,
so that I can organize my document collections into separate workspaces.

## Acceptance Criteria

1. **AC1: Create Investigation**
   - Given the investigator is on the home page
   - When they click "New Investigation" and enter a name and description
   - Then a new investigation is created with a UUID and timestamps
   - And they are redirected to the investigation workspace

2. **AC2: List Investigations**
   - Given investigations exist
   - When the investigator navigates to `/`
   - Then the investigation list displays as cards in a CSS Grid layout (auto-fill, minmax(320px, 1fr))
   - And each card shows investigation name, description, creation date, and document count
   - And data is fetched via TanStack Query from `GET /api/v1/investigations/`

3. **AC3: Delete Investigation**
   - Given an investigation exists
   - When the investigator clicks delete and confirms
   - Then the investigation and all associated data are deleted (cascading: Neo4j → Qdrant → filesystem → PostgreSQL)
   - And the investigation disappears from the list

4. **AC4: Open Investigation Workspace**
   - Given the investigator clicks on an investigation card
   - When the workspace loads at `/investigations/:id`
   - Then the investigation header shows name and description
   - And the workspace displays the document management area (upload zone + document list placeholder)

5. **AC5: Backend Investigation Persistence**
   - Given the backend receives a `POST /api/v1/investigations/`
   - When the request body contains name and optional description
   - Then the investigation is persisted in PostgreSQL via SQLAlchemy
   - And the Alembic migration has created the `investigations` table
   - And a storage directory `storage/{investigation_id}/` is created on disk

## Tasks / Subtasks

- [x] Task 1: Create Investigation database model and Alembic migration (AC: #5)
  - [x] 1.1: Create `app/models/investigation.py` with SQLAlchemy model — `Investigation` table with id (UUID), name (str), description (str|None), created_at (datetime), updated_at (datetime)
  - [x] 1.2: Generate Alembic migration: `alembic revision --autogenerate -m "create_investigations_table"`
  - [x] 1.3: Verify migration applies cleanly on fresh database

- [x] Task 2: Create Investigation Pydantic schemas (AC: #5)
  - [x] 2.1: Create `app/schemas/investigation.py` with `InvestigationCreate` (name: str, description: str|None), `InvestigationResponse` (id, name, description, created_at, updated_at, document_count, entity_count), `InvestigationListResponse` (items: list, total: int)

- [x] Task 3: Create Investigation service layer (AC: #1, #3, #5)
  - [x] 3.1: Create `app/services/investigation.py` with `InvestigationService` class
  - [x] 3.2: Implement `create_investigation(data)` — persist to PostgreSQL, create `storage/{id}/` directory, return investigation
  - [x] 3.3: Implement `list_investigations(limit, offset)` — query with document_count annotation, return paginated list
  - [x] 3.4: Implement `get_investigation(id)` — fetch single investigation or raise 404
  - [x] 3.5: Implement `delete_investigation(id)` — cascading delete: Neo4j entities → Qdrant embeddings → filesystem `storage/{id}/` → PostgreSQL record. For Story 2.1, Neo4j and Qdrant steps are no-ops (no data yet), but the delete order and try/except structure MUST be in place.

- [x] Task 4: Create Investigation API endpoints (AC: #1, #2, #3, #5)
  - [x] 4.1: Create `app/api/v1/investigations.py` with FastAPI router
  - [x] 4.2: `POST /api/v1/investigations/` → 201 Created, returns InvestigationResponse
  - [x] 4.3: `GET /api/v1/investigations/` → 200 OK, returns InvestigationListResponse with pagination (limit/offset query params)
  - [x] 4.4: `GET /api/v1/investigations/{id}` → 200 OK, returns InvestigationResponse
  - [x] 4.5: `DELETE /api/v1/investigations/{id}` → 204 No Content
  - [x] 4.6: Register investigations router in `app/api/v1/router.py`

- [x] Task 5: Write backend tests (AC: #1, #2, #3, #5)
  - [x] 5.1: Create `tests/api/test_investigations.py` — test create (201), list (200 with items/total), get (200), get not found (404), delete (204), delete not found (404)
  - [x] 5.2: Create `tests/conftest.py` investigation fixtures — test database session, investigation factory
  - [x] 5.3: Verify all RFC 7807 error responses for invalid inputs

- [x] Task 6: Install shadcn/ui dialog and input components (AC: #1)
  - [x] 6.1: Install shadcn/ui components: `pnpm dlx shadcn@latest add dialog input label textarea` in `apps/web/`

- [x] Task 7: Create Investigation frontend components (AC: #1, #2, #3, #4)
  - [x] 7.1: Create `src/components/investigation/InvestigationCard.tsx` — card showing name, description (truncated), created_at, document_count; clickable to navigate; delete button with confirmation
  - [x] 7.2: Create `src/components/investigation/CreateInvestigationDialog.tsx` — dialog with name input (required) and description textarea (optional); submit creates investigation via mutation; on success invalidates query cache and navigates to workspace
  - [x] 7.3: Create `src/components/investigation/InvestigationList.tsx` — CSS Grid layout (auto-fill, minmax(320px, 1fr)); renders InvestigationCards; shows empty state with "New Investigation" CTA; loading skeleton cards
  - [x] 7.4: Create `src/components/investigation/DeleteConfirmationDialog.tsx` — confirmation dialog showing investigation name and data counts; Cancel (default focus) and Delete (destructive style) buttons

- [x] Task 8: Create Investigation hooks (AC: #1, #2, #3)
  - [x] 8.1: Create `src/hooks/useInvestigations.ts` — `useInvestigations()` query hook for list, `useInvestigation(id)` for single, `useCreateInvestigation()` mutation, `useDeleteInvestigation()` mutation
  - [x] 8.2: All hooks use openapi-fetch typed client (`api.GET`, `api.POST`, `api.DELETE`)
  - [x] 8.3: Mutations invalidate `['investigations']` query key on success

- [x] Task 9: Update routes to render investigation views (AC: #2, #4)
  - [x] 9.1: Update `src/routes/index.tsx` — render InvestigationList with CreateInvestigationDialog trigger
  - [x] 9.2: Update `src/routes/investigations/$id.tsx` — fetch investigation by ID, render workspace header with name/description, placeholder for document management area (Epic 2 Stories 2.2-2.5)

- [x] Task 10: Regenerate OpenAPI types (AC: #2)
  - [x] 10.1: Run `scripts/generate-api-types.sh` against running backend to generate TypeScript types for investigation endpoints
  - [x] 10.2: Verify generated types match InvestigationResponse and InvestigationListResponse schemas

- [x] Task 11: Write frontend tests (AC: #1, #2, #3, #4)
  - [x] 11.1: Create `src/components/investigation/InvestigationList.test.tsx` — test: renders investigation cards; test: shows empty state; test: loading skeleton; test: error state
  - [x] 11.2: Create `src/components/investigation/CreateInvestigationDialog.test.tsx` — test: renders form; test: validates required name; test: submits successfully
  - [x] 11.3: Create `src/components/investigation/InvestigationCard.test.tsx` — test: renders card data; test: delete confirmation flow

## Dev Notes

### CRITICAL: Backend Architecture Patterns (MUST follow)

**ORM: SQLAlchemy 2.0 + Pydantic v2 (NOT SQLModel)**
Story 1.1 dropped SQLModel in favor of separate SQLAlchemy models + Pydantic schemas. The architecture doc mentions SQLModel, but the actual codebase uses SQLAlchemy 2.0 async with separate Pydantic v2 schemas. Follow the established pattern:
- Database models: `app/models/` using SQLAlchemy `DeclarativeBase`
- API schemas: `app/schemas/` using Pydantic `BaseModel`
- [Source: _bmad-output/implementation-artifacts/1-1-monorepo-scaffolding-docker-compose-infrastructure.md — "SQLModel dropped for SQLAlchemy 2.0 + Pydantic v2"]

**Database Session Pattern:**
```python
# app/db/postgres.py already provides:
# - async_engine (create_async_engine)
# - AsyncSessionLocal (async_sessionmaker)
# Use as FastAPI dependency:
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
```

**API Response Format — NO wrapper:**
- Success: Direct response body (NOT `{data: ...}`)
- List: `{ "items": [...], "total": 42 }`
- Error: RFC 7807 Problem Details
- [Source: _bmad-output/planning-artifacts/architecture.md#API Response Format]

**RFC 7807 Error Responses:**
```json
{
  "type": "urn:osint:error:investigation_not_found",
  "title": "Investigation Not Found",
  "status": 404,
  "detail": "No investigation found with id: {id}",
  "instance": "/api/v1/investigations/{id}"
}
```

**Cascading Delete Order (CRITICAL):**
1. Neo4j (entities/relationships scoped to investigation_id) — no-op in Story 2.1
2. Qdrant (embeddings filtered by investigation_id) — no-op in Story 2.1
3. Filesystem (`storage/{investigation_id}/` directory)
4. PostgreSQL (investigation record + related documents/jobs)
- Delete PostgreSQL LAST to ensure consistency point
- Wrap each step in try/except with logging — partial failure should not prevent remaining steps
- [Source: _bmad-output/planning-artifacts/architecture.md#Multi-Database Cascading Delete]

**Logging: Loguru (NOT print/logging)**
```python
from loguru import logger
logger.info("Investigation created", investigation_id=str(id), name=name)
logger.error("Investigation delete partially failed", investigation_id=str(id), failed_step="neo4j")
```

**UUID v4 for all IDs (NOT auto-increment)**
```python
import uuid
id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
```

**Alembic auto-migration runs on startup** (established in Story 1.2 lifespan):
```python
# app/main.py lifespan already runs:
# alembic.command.upgrade(alembic_cfg, "head")
```

### CRITICAL: Frontend Architecture Patterns (MUST follow)

**API Client: openapi-fetch (NOT raw fetch, NOT axios)**
```typescript
// Already configured in src/lib/api-client.ts
import createClient from "openapi-fetch";
import type { paths } from "./api-types.generated";
export const api = createClient<paths>({ baseUrl: "" });
```
- baseUrl is empty string (NOT `/api/v1`) — Nginx proxies `/api/*` to backend
- [Source: _bmad-output/implementation-artifacts/1-3-frontend-shell-with-system-status-page.md — "fixed baseUrl to empty string"]

**TanStack Query for ALL server state:**
```typescript
// Query keys: hierarchical arrays
['investigations']           // list
['investigations', id]       // single
['health']                   // health (existing)

// Mutations invalidate on success:
queryClient.invalidateQueries({ queryKey: ['investigations'] });
```

**TanStack Router navigation:**
```typescript
import { useNavigate, Link } from '@tanstack/react-router';
const navigate = useNavigate();
navigate({ to: '/investigations/$id', params: { id } });
```

**Component placement:**
- Investigation components: `src/components/investigation/`
- Hooks: `src/hooks/`
- Tests: co-located (`.test.tsx` next to source)
- Route files: `src/routes/` (file-based routing, auto-generated route tree)

**Design tokens (already in globals.css):**
```css
--bg-primary: oklch(...)   /* page background */
--bg-elevated: oklch(...)  /* cards, dialogs */
--bg-hover: oklch(...)     /* hover states */
--text-primary: oklch(...) /* body text */
--text-secondary: oklch(...)/* labels, metadata */
--status-error: oklch(...) /* destructive actions */
```

**Existing shadcn/ui components available:** button, badge, card, separator
**Need to install:** dialog, input, label, textarea

### UX Design Requirements

**Investigation List (home page `/`):**
- CSS Grid: `grid-template-columns: repeat(auto-fill, minmax(320px, 1fr))`
- Card content: name (bold, `--text-lg`), description (truncated, `--text-secondary`), created date (`--text-sm`, `--text-muted`), document count
- Empty state: "Create your first investigation to get started" with "New Investigation" button
- Loading state: skeleton cards matching card anatomy
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Investigation List]

**Create Investigation Dialog:**
- Modal with max-width ~420px, backdrop `rgba(0,0,0,0.6)`
- Fields: name (required, `min_length=1`, `max_length=255`), description (optional, `max_length=2000`)
- Close: X button, Escape, backdrop click
- After creation: navigate to `/investigations/:id`

**Delete Confirmation Dialog:**
```
"Delete Investigation?"
"{name}" and all its data will be permanently deleted.
[Cancel]  [Delete]
```
- Cancel button: default focus (safe option), secondary style
- Delete button: destructive style (`--status-error` text, solid fill on hover)
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Confirmation Dialogs]

**Investigation Workspace (`/investigations/:id`):**
- Header: investigation name (`--text-xl`, weight 600), description
- Placeholder body: "Upload documents to begin your investigation" (Story 2.2 builds on this)
- Back navigation: via header breadcrumb or browser back

### File Storage

**Storage path pattern:** `storage/{investigation_id}/`
- Bind-mounted: `./storage:/app/storage` (Docker)
- Development: `./storage/` relative to project root
- Created on investigation creation
- Deleted recursively on investigation deletion
- [Source: _bmad-output/planning-artifacts/architecture.md#Document Storage]

### Project Structure Notes

**Files to CREATE:**
```
apps/api/
├── app/
│   ├── models/investigation.py          # SQLAlchemy model
│   ├── schemas/investigation.py         # Pydantic request/response schemas
│   ├── services/investigation.py        # CRUD + cascading delete service
│   └── api/v1/investigations.py         # FastAPI router with CRUD endpoints
├── migrations/versions/
│   └── xxxx_create_investigations.py    # Alembic migration
└── tests/
    └── api/test_investigations.py       # API endpoint tests

apps/web/src/
├── components/
│   ├── ui/dialog.tsx                    # shadcn (via CLI)
│   ├── ui/input.tsx                     # shadcn (via CLI)
│   ├── ui/label.tsx                     # shadcn (via CLI)
│   ├── ui/textarea.tsx                  # shadcn (via CLI)
│   └── investigation/
│       ├── InvestigationCard.tsx
│       ├── InvestigationCard.test.tsx
│       ├── InvestigationList.tsx
│       ├── InvestigationList.test.tsx
│       ├── CreateInvestigationDialog.tsx
│       ├── CreateInvestigationDialog.test.tsx
│       └── DeleteConfirmationDialog.tsx
├── hooks/
│   └── useInvestigations.ts
└── lib/
    └── api-types.generated.ts           # Regenerated with investigation types
```

**Files to MODIFY:**
```
apps/api/app/api/v1/router.py           # Register investigations router
apps/api/tests/conftest.py              # Add investigation test fixtures
apps/web/src/routes/index.tsx            # Render InvestigationList
apps/web/src/routes/investigations/$id.tsx  # Render investigation workspace
```

### Naming Conventions

| Context | Convention | Example |
|---------|-----------|---------|
| Python files | snake_case | `investigation.py` |
| Python classes | PascalCase | `Investigation`, `InvestigationService` |
| Python functions | snake_case | `create_investigation()` |
| PostgreSQL tables | snake_case, plural | `investigations` |
| PostgreSQL columns | snake_case | `investigation_id`, `created_at` |
| React components | PascalCase files | `InvestigationCard.tsx` |
| React hooks | camelCase with `use` prefix | `useInvestigations.ts` |
| Test files | co-located `.test.tsx` | `InvestigationList.test.tsx` |
| API endpoints | plural nouns | `/api/v1/investigations/` |
| Query keys | hierarchical arrays | `['investigations']`, `['investigations', id]` |

### Previous Story Intelligence

**From Story 1.1:**
- SQLModel dropped for SQLAlchemy 2.0 + Pydantic v2 (separate models) — DO NOT use SQLModel
- Python 3.13-slim in Docker (not 3.14)
- shadcn/ui CLI works now (Story 1.3 confirmed) — use `pnpm dlx shadcn@latest add`
- pnpm v10 blocks lifecycle scripts — `onlyBuiltDependencies` in root package.json handles this
- CORS configured for localhost:5173 and localhost:80

**From Story 1.2:**
- Health endpoint pattern: service class → router → registered in v1 router
- Test pattern: mock external services in conftest.py fixtures, use httpx TestClient
- RFC 7807 error format established
- Alembic auto-migration on startup via lifespan
- Loguru structured logging configured

**From Story 1.3:**
- TanStack Query configured with defaults (staleTime: 30s, gcTime: 5m, retry: 1)
- openapi-fetch client at `src/lib/api-client.ts` with baseUrl="" (empty string)
- Vitest + Testing Library configured and working
- Design tokens in globals.css (warm dark theme)
- CSS Grid root layout: `grid-rows-[auto_1fr_auto]` (header/content/statusbar)
- Test pattern: `createTestQueryClient()` + `renderWithProviders()` helper
- shadcn/ui CLI v4 works — no need for manual copy

**Git Intelligence:**
- 3 commits: Story 1.1 → 1.2 → 1.3 (clean linear history)
- Code review fixes applied after each story
- TypeScript strict mode passing
- All tests passing

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic 2: Investigation & Document Management]
- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.1: Investigation CRUD API & List View]
- [Source: _bmad-output/planning-artifacts/architecture.md#API Endpoints — Investigation CRUD]
- [Source: _bmad-output/planning-artifacts/architecture.md#PostgreSQL Schema — investigations table]
- [Source: _bmad-output/planning-artifacts/architecture.md#Multi-Database Cascading Delete Strategy]
- [Source: _bmad-output/planning-artifacts/architecture.md#API Response Format — RFC 7807, list format]
- [Source: _bmad-output/planning-artifacts/architecture.md#Frontend Architecture — React + Vite SPA]
- [Source: _bmad-output/planning-artifacts/architecture.md#Frontend Data Layer — TanStack Query, openapi-fetch]
- [Source: _bmad-output/planning-artifacts/architecture.md#Monorepo & Directory Structure]
- [Source: _bmad-output/planning-artifacts/architecture.md#Naming Conventions]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Investigation List — CSS Grid Card Layout]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Create Investigation Dialog]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Delete Confirmation Dialog]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Color Palette — Dark Theme Tokens]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Typography — Inter for UI]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Empty States, Loading States, Error States]
- [Source: _bmad-output/planning-artifacts/prd.md#FR1-FR4 Investigation Management]
- [Source: _bmad-output/planning-artifacts/prd.md#NFR18-NFR20 Document Integrity]
- [Source: _bmad-output/implementation-artifacts/1-1-monorepo-scaffolding-docker-compose-infrastructure.md#Dev Notes]
- [Source: _bmad-output/implementation-artifacts/1-2-backend-health-checks-model-readiness.md#Dev Notes]
- [Source: _bmad-output/implementation-artifacts/1-3-frontend-shell-with-system-status-page.md#Dev Notes]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

- No blocking issues encountered during implementation.

### Completion Notes List

- **Backend (Tasks 1-5):** Implemented Investigation CRUD with SQLAlchemy 2.0 model, Pydantic v2 schemas, service layer with cascading delete order (Neo4j→Qdrant→filesystem→PostgreSQL), FastAPI router with all CRUD endpoints, Alembic migration. 10 API tests pass.
- **Frontend (Tasks 6-11):** Installed shadcn/ui dialog/input/label/textarea. Created InvestigationList (CSS Grid layout with empty/loading/error states), InvestigationCard (clickable with delete), CreateInvestigationDialog (name required, description optional), DeleteConfirmationDialog (Cancel focused by default). TanStack Query hooks with proper openapi-fetch typed client. Updated routes for home page list and workspace detail. 11 component tests pass.
- **OpenAPI types regenerated** from running backend — hooks use fully typed paths.
- **All 80 tests pass** (55 backend + 25 frontend), zero regressions.

### Code Review Fixes (2026-03-08)

- **[H1] Added service-layer unit tests** — 10 new tests in `tests/services/test_investigation_service.py` covering create (DB persist + storage dir), list (pagination + count), get (found + not found), delete (cascading order, missing dir, not found, filesystem error resilience)
- **[M1] Fixed CreateInvestigationDialog accessibility** — added `DialogDescription` to eliminate screen reader warning
- **[M2] Made STORAGE_ROOT configurable** — reads from `STORAGE_ROOT` env var with fallback to `"storage"`
- **[M3] Added database-level updated_at trigger** — PostgreSQL `BEFORE UPDATE` trigger in migration ensures `updated_at` is set even for non-ORM updates
- **[M4] Extracted shared test-utils** — created `src/test-utils.tsx` with `createTestQueryClient()` and `renderWithProviders()`, removed duplication from 5 test files

### File List

**New files:**
- apps/api/app/models/base.py
- apps/api/app/models/investigation.py
- apps/api/app/schemas/investigation.py
- apps/api/app/services/investigation.py
- apps/api/app/api/v1/investigations.py
- apps/api/migrations/versions/001_create_investigations_table.py
- apps/api/tests/api/test_investigations.py
- apps/api/tests/services/test_investigation_service.py (code review)
- apps/web/src/components/ui/dialog.tsx (shadcn)
- apps/web/src/components/ui/input.tsx (shadcn)
- apps/web/src/components/ui/label.tsx (shadcn)
- apps/web/src/components/ui/textarea.tsx (shadcn)
- apps/web/src/components/investigation/InvestigationCard.tsx
- apps/web/src/components/investigation/InvestigationCard.test.tsx
- apps/web/src/components/investigation/InvestigationList.tsx
- apps/web/src/components/investigation/InvestigationList.test.tsx
- apps/web/src/components/investigation/CreateInvestigationDialog.tsx
- apps/web/src/components/investigation/CreateInvestigationDialog.test.tsx
- apps/web/src/components/investigation/DeleteConfirmationDialog.tsx
- apps/web/src/hooks/useInvestigations.ts
- apps/web/src/test-utils.tsx (code review)
- CLAUDE.md

**Modified files:**
- apps/api/app/models/__init__.py (exports Base + Investigation)
- apps/api/app/api/v1/router.py (registered investigations router)
- apps/api/migrations/env.py (target_metadata = Base.metadata)
- apps/api/tests/conftest.py (added investigation fixtures)
- apps/web/src/lib/api-types.generated.ts (regenerated with investigation types)
- apps/web/src/routes/index.tsx (renders InvestigationList)
- apps/web/src/routes/investigations/$id.tsx (renders workspace with investigation data)
- apps/web/src/components/layout/StatusBar.test.tsx (code review: shared test-utils)
- apps/web/src/components/status/SystemStatusPage.test.tsx (code review: shared test-utils)

## Change Log

- 2026-03-08: Story 2.1 implemented — Investigation CRUD API (create/list/get/delete) with cascading delete, frontend list view with CSS Grid cards, create/delete dialogs, TanStack Query hooks, OpenAPI typed client, full test coverage (70 tests pass).
- 2026-03-08: Code review fixes — added 10 service-layer unit tests, fixed CreateInvestigationDialog accessibility, made STORAGE_ROOT configurable via env var, added DB-level updated_at trigger, extracted shared frontend test-utils (80 tests pass).
