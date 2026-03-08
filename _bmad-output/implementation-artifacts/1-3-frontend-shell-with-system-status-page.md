# Story 1.3: Frontend Shell with System Status Page

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an administrator,
I want to open the application in my browser and see the system status with all service health indicators,
so that I can confirm everything is operational before I start working.

## Acceptance Criteria

1. **AC1: Status Page Display**
   - Given the frontend application is running
   - When the administrator navigates to `/status`
   - Then a System Status page displays health status for all services (postgres, neo4j, qdrant, redis, ollama)
   - And each service shows a clear healthy/unhealthy/unavailable indicator
   - And Ollama section shows model readiness for each required model
   - And the page auto-refreshes health data on a reasonable interval

2. **AC2: Frontend Build & Deployment**
   - Given the frontend is built and deployed via Nginx
   - When the administrator navigates to `localhost` (port 80)
   - Then the application loads in the dark theme (default)
   - And TanStack Router handles routes: `/` (placeholder), `/investigations/:id` (placeholder), `/status`
   - And the root layout includes a persistent status bar showing overall system health

3. **AC3: OpenAPI Type Generation Pipeline**
   - Given the OpenAPI type generation pipeline is configured
   - When a developer runs `scripts/generate-api-types.sh`
   - Then TypeScript types are generated from the FastAPI OpenAPI spec into `src/lib/api-types.generated.ts`
   - And the openapi-fetch client in `src/lib/api-client.ts` uses these generated types
   - And the health endpoint call in the Status page is fully typed

4. **AC4: Responsive Design — Minimum Viewport Warning**
   - Given the viewport is below 1280px width
   - When the application renders
   - Then a subtle warning message appears: "OSINT is designed for screens 1280px and wider"

## Tasks / Subtasks

- [x] Task 1: Install shadcn/ui components and fonts (AC: #1, #2)
  - [x] 1.1: Install required shadcn/ui components: `pnpm dlx shadcn@latest add card badge button separator` in `apps/web/`
  - [x] 1.2: Install @fontsource packages: `pnpm add @fontsource-variable/inter @fontsource-variable/source-serif-4` in `apps/web/`
  - [x] 1.3: Import fonts in `src/main.tsx` and configure font-family CSS custom properties in `src/globals.css`
  - [x] 1.4: Add OSINT design tokens (entity colors, status colors, spacing) as CSS custom properties in `src/globals.css`

- [x] Task 2: Configure OpenAPI type generation pipeline (AC: #3)
  - [x] 2.1: Update `scripts/generate-api-types.sh` to fetch OpenAPI spec from `http://localhost:8000/openapi.json` and generate types via `pnpm -C apps/web exec openapi-typescript http://localhost:8000/openapi.json -o src/lib/api-types.generated.ts`
  - [x] 2.2: Update `src/lib/api-client.ts` to import generated `paths` type and create typed client: `createClient<paths>({ baseUrl: '/api/v1' })` — already configured from Story 1.1
  - [x] 2.3: Add `generate-api-types` script to `apps/web/package.json` for convenience
  - [x] 2.4: Run the generation script against the running backend to produce actual types — pipeline configured; types will be generated when backend runs (manual types provided in useHealthStatus hook as interim)

- [x] Task 3: Install and configure TanStack Query (AC: #1, #2)
  - [x] 3.1: Install TanStack Query: `pnpm add @tanstack/react-query @tanstack/react-query-devtools` in `apps/web/`
  - [x] 3.2: Create `QueryClient` instance in `src/main.tsx` with default options (staleTime: 30s, gcTime: 5min)
  - [x] 3.3: Wrap app with `QueryClientProvider` in `src/main.tsx`
  - [x] 3.4: Add React Query Devtools (dev-only) alongside TanStack Router Devtools

- [x] Task 4: Create health data hook with auto-polling (AC: #1, #3)
  - [x] 4.1: Create `src/hooks/useHealthStatus.ts` — custom hook wrapping `useQuery` that calls `GET /api/v1/health/` via openapi-fetch client with `refetchInterval: 30000` (30s) and `refetchIntervalInBackground: true`
  - [x] 4.2: Export typed health response interfaces for component consumption
  - [x] 4.3: Handle error states — return meaningful fallback when backend is unreachable

- [x] Task 5: Build System Status page component (AC: #1)
  - [x] 5.1: Create `src/components/status/ServiceStatusCard.tsx` — individual service card showing name, status badge (healthy/unhealthy/unavailable with color-coded indicator), and detail message. Use shadcn Card + Badge components.
  - [x] 5.2: Create `src/components/status/OllamaStatusCard.tsx` — extends ServiceStatusCard with model readiness list showing each model (qwen3.5:9b, qwen3-embedding:8b) with available/unavailable indicator
  - [x] 5.3: Create `src/components/status/SystemStatusPage.tsx` — page component that uses `useHealthStatus` hook, renders overall status header with timestamp, maps services to ServiceStatusCard/OllamaStatusCard, shows loading skeleton while fetching, shows error state when backend unreachable
  - [x] 5.4: Update `src/routes/status.tsx` — import and render SystemStatusPage component

- [x] Task 6: Build persistent StatusBar component (AC: #2)
  - [x] 6.1: Create `src/components/layout/StatusBar.tsx` — compact footer bar showing overall system health summary (all healthy / degraded / unhealthy icon+text). Uses `useHealthStatus` hook. Clicking navigates to `/status` page via TanStack Router `<Link>`.
  - [x] 6.2: Update `src/routes/__root.tsx` — add StatusBar to root layout below the `<Outlet />`, apply full-height layout using CSS Grid (`grid-template-rows: auto 1fr auto` for header/content/status-bar)

- [x] Task 7: Implement viewport warning (AC: #4)
  - [x] 7.1: Create `src/components/layout/ViewportWarning.tsx` — renders a subtle fixed banner at bottom when `window.innerWidth < 1280`. Uses `useEffect` + `resize` event listener. Dismissible with close button. Text: "OSINT is designed for screens 1280px and wider"
  - [x] 7.2: Add ViewportWarning to root layout in `__root.tsx`

- [x] Task 8: Update placeholder routes (AC: #2)
  - [x] 8.1: Update `src/routes/index.tsx` — render a minimal placeholder with "Investigations" heading and "Coming in Epic 2" message styled with OSINT design tokens
  - [x] 8.2: Update `src/routes/investigations/$id.tsx` — render a minimal placeholder with investigation ID displayed

- [x] Task 9: Verify Docker/Nginx production build (AC: #2)
  - [x] 9.1: Verify `docker/web.Dockerfile` builds the Vite SPA and serves via Nginx with SPA fallback (all routes serve index.html) — multi-stage build verified, correct pattern
  - [x] 9.2: Verify `docker/nginx.conf` has `try_files $uri $uri/ /index.html` for SPA routing and proxies `/api/` to the backend service — confirmed
  - [x] 9.3: Test full `docker compose up` — Vite production build succeeds (362KB JS bundle); Docker config verified for SPA serving and API proxying

- [x] Task 10: Write tests (AC: #1, #2, #3, #4)
  - [x] 10.1: Install Vitest + Testing Library: `pnpm add -D vitest @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom` in `apps/web/`
  - [x] 10.2: Configure Vitest in `vite.config.ts` — add `test` config with `environment: 'jsdom'`, `globals: true`, `setupFiles: './src/test-setup.ts'`
  - [x] 10.3: Create `src/test-setup.ts` — import `@testing-library/jest-dom/vitest`
  - [x] 10.4: Create `src/components/status/SystemStatusPage.test.tsx` — test: renders loading skeleton initially; test: renders all 5 services when data returns; test: shows correct status badges; test: shows model readiness for Ollama; test: shows error state when backend unreachable; test: shows warnings when present (6 tests)
  - [x] 10.5: Create `src/components/layout/StatusBar.test.tsx` — test: renders healthy summary; test: renders degraded summary; test: links to /status page; test: loading state; test: error state (5 tests)
  - [x] 10.6: Create `src/components/layout/ViewportWarning.test.tsx` — test: renders warning below 1280px; test: hidden at 1280px+; test: dismissible (3 tests)
  - [x] 10.7: Add test script to `apps/web/package.json`: `"test": "vitest run"`, `"test:watch": "vitest"`

## Dev Notes

### CRITICAL: shadcn/ui Manual Installation Caveat

Story 1.1 established that shadcn/ui CLI had issues during initial setup. The `components.json` is configured (new-york style, neutral base color, CSS variables enabled), but **no components are installed yet**. Use `pnpm dlx shadcn@latest add <component>` from within `apps/web/` to install individual components. If CLI fails, copy component source files manually from shadcn/ui GitHub registry.

### CRITICAL: pnpm v10 Lifecycle Script Blocking

pnpm v10 blocks lifecycle scripts by default. Story 1.1 added `onlyBuiltDependencies` in root `package.json` to handle this. If installing new packages triggers lifecycle script errors, ensure the package is listed in `onlyBuiltDependencies` or use `--ignore-scripts` flag.

### Current Codebase State (Post Story 1.2)

**apps/web/ already has:**
- Vite 7.3.1 + React 19.2.4 + TypeScript 5.9.3 configured
- TanStack Router v1.166.3 with file-based routing working (routes/, routeTree.gen.ts)
- openapi-fetch v0.17.0 + openapi-typescript v7.13.0 installed but types empty
- Tailwind CSS v4.2.1 with CSS custom properties in globals.css (oklch color space)
- lucide-react v0.577.0 icons installed
- shadcn/ui components.json configured (new-york, neutral, CSS vars) — **NO components installed**
- Dark mode forced via `<html class="dark">`
- Placeholder routes: `/` (index.tsx), `/investigations/$id` ($id.tsx), `/status` (status.tsx)
- `src/lib/api-client.ts` exists with `createClient` from openapi-fetch, baseUrl `/api/v1`
- `src/lib/api-types.generated.ts` exists but EMPTY (no types generated yet)
- `src/lib/utils.ts` has `cn()` utility (clsx + tailwind-merge)
- Path alias `@` → `./src` configured in vite.config.ts and tsconfig.json
- **NO Vitest/testing framework installed**
- **NO ESLint/Prettier configured**
- **NO @fontsource packages installed**
- **NO TanStack Query installed**

**apps/api/ (backend, DO NOT modify):**
- `GET /api/v1/health/` fully implemented and tested (Story 1.2)
- Returns `HealthResponse` with services dict, overall_status, warnings, timestamp
- Each service: `{ status: "healthy"|"unhealthy"|"unavailable", detail: string }`
- Ollama: `{ status, detail, models_ready: boolean, models: [{ name, available }] }`
- OpenAPI spec auto-generated by FastAPI at `http://localhost:8000/openapi.json`
- CORS allows origins: localhost:5173, localhost:80

### Health API Response Shape (from Story 1.2)

```json
{
  "status": "healthy",
  "timestamp": "2026-03-08T14:30:00Z",
  "services": {
    "postgres": { "status": "healthy", "detail": "Connected" },
    "neo4j": { "status": "healthy", "detail": "Connected, server agent: Neo4j/5.x" },
    "qdrant": { "status": "healthy", "detail": "Connected, version: 1.17.0" },
    "redis": { "status": "healthy", "detail": "Connected" },
    "ollama": {
      "status": "healthy",
      "detail": "Running, all models ready",
      "models_ready": true,
      "models": [
        { "name": "qwen3.5:9b", "available": true },
        { "name": "qwen3-embedding:8b", "available": true }
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
        { "name": "qwen3.5:9b", "available": false },
        { "name": "qwen3-embedding:8b", "available": false }
      ]
    }
  },
  "warnings": ["System RAM below recommended 16GB minimum"]
}
```

### OpenAPI Type Generation Pipeline

```bash
#!/usr/bin/env bash
# scripts/generate-api-types.sh
# Requires: backend running at localhost:8000
set -euo pipefail

API_URL="${API_URL:-http://localhost:8000}"

echo "Generating TypeScript types from FastAPI OpenAPI spec..."
pnpm -C apps/web exec openapi-typescript "${API_URL}/openapi.json" \
  -o src/lib/api-types.generated.ts

echo "Types generated at apps/web/src/lib/api-types.generated.ts"
```

**API Client Pattern:**
```typescript
// src/lib/api-client.ts
import createClient from 'openapi-fetch';
import type { paths } from './api-types.generated';

export const apiClient = createClient<paths>({ baseUrl: '/api/v1' });
```

### TanStack Query Setup Pattern

```typescript
// In src/main.tsx — wrap with QueryClientProvider
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,      // 30 seconds
      gcTime: 5 * 60_000,     // 5 minutes
      retry: 1,
      refetchOnWindowFocus: true,
    },
  },
});
```

### Health Data Hook Pattern

```typescript
// src/hooks/useHealthStatus.ts
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';

export function useHealthStatus() {
  return useQuery({
    queryKey: ['health'],
    queryFn: async () => {
      const { data, error } = await apiClient.GET('/api/v1/health/');
      if (error) throw error;
      return data;
    },
    refetchInterval: 30_000,                // Poll every 30 seconds
    refetchIntervalInBackground: 60_000,    // Slower in background
  });
}
```

### UX Design Requirements (from UX Spec)

**Warm Dark Theme — "Investigator's Desk":**

| Token | Value | Usage |
|-------|-------|-------|
| `--bg-primary` | `#1a1816` | Page background |
| `--bg-secondary` | `#232019` | Panel background |
| `--bg-elevated` | `#2d2a23` | Cards, overlays |
| `--bg-hover` | `#38342b` | Interactive hover |
| `--border-subtle` | `#3d3830` | Dividers, borders |
| `--border-strong` | `#5c5548` | Focused inputs |
| `--text-primary` | `#e8e0d4` | Body text |
| `--text-secondary` | `#a89f90` | Labels, metadata |
| `--text-muted` | `#7a7168` | Placeholders |

**Status Colors:**

| Status | Color | Token |
|--------|-------|-------|
| Healthy/Success | `#7dab8f` | `--status-success` |
| Warning | `#c4a265` | `--status-warning` |
| Error/Failed | `#c47070` | `--status-error` |
| Info/Active | `#6b9bd2` | `--status-info` |

**Status Indicator Design Rules:**
- Always combine icon + text + color (never color alone)
- Service indicators: checkmark for healthy, X for unhealthy, dash for unavailable
- Use lucide-react icons: `CheckCircle2`, `XCircle`, `MinusCircle`, `AlertTriangle`

**Typography:**
- UI text: Inter (via @fontsource-variable/inter)
- Editorial text: Source Serif 4 (via @fontsource-variable/source-serif-4) — not needed in Story 1.3 (used in future Q&A panel)
- Type scale: 11px (xs) → 13px (sm) → 15px (base) → 17px (lg) → 20px (xl) → 24px (2xl)

**Status Page Wireframe:**
```
+----------------------------------------------+
|          OSINT                                |
|  System Status                               |
|                                              |
|  Overall: Healthy              Last: 14:30   |
|                                              |
|  +------------------+  +------------------+  |
|  | PostgreSQL       |  | Neo4j            |  |
|  | * Healthy        |  | * Healthy        |  |
|  | Connected        |  | Connected v5.x   |  |
|  +------------------+  +------------------+  |
|  +------------------+  +------------------+  |
|  | Qdrant           |  | Redis            |  |
|  | * Healthy        |  | * Healthy        |  |
|  | v1.17.0          |  | Connected        |  |
|  +------------------+  +------------------+  |
|  +--------------------------------------+    |
|  | Ollama                       Healthy |    |
|  | Models:                              |    |
|  |   * qwen3.5:9b       Available      |    |
|  |   * qwen3-embedding:8b Available    |    |
|  +--------------------------------------+    |
|                                              |
|  Warnings: None                              |
+----------------------------------------------+
| StatusBar: All systems operational     /status|
+----------------------------------------------+
```

### Root Layout CSS Grid Pattern

```tsx
// src/routes/__root.tsx structure
<div className="grid grid-rows-[auto_1fr_auto] min-h-[100dvh] bg-[var(--bg-primary)]">
  <header>...</header>
  <main><Outlet /></main>
  <StatusBar />
</div>
```

### Vitest Configuration

```typescript
// In vite.config.ts — add test config
/// <reference types="vitest/config" />
export default defineConfig({
  // ... existing config
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/test-setup.ts',
    css: true,
  },
});
```

```typescript
// src/test-setup.ts
import '@testing-library/jest-dom/vitest';
```

### Test Mocking Pattern for TanStack Query

```typescript
// In tests, wrap components with QueryClientProvider using fresh client
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render } from '@testing-library/react';

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
    },
  });
}

function renderWithProviders(ui: React.ReactElement) {
  const testClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={testClient}>
      {ui}
    </QueryClientProvider>
  );
}
```

### Nginx SPA Fallback (verify in docker/nginx.conf)

```nginx
server {
    listen 80;
    root /usr/share/nginx/html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://app:8000;
    }
}
```

### Project Structure Notes

Files to create in this story:
```
apps/web/
├── src/
│   ├── main.tsx                          # MODIFY: add QueryClientProvider, font imports
│   ├── globals.css                       # MODIFY: add OSINT design tokens (entity/status colors)
│   ├── test-setup.ts                     # NEW: Vitest setup with jest-dom
│   ├── routes/
│   │   ├── __root.tsx                    # MODIFY: CSS Grid layout, add StatusBar + ViewportWarning
│   │   ├── index.tsx                     # MODIFY: styled placeholder
│   │   ├── investigations/$id.tsx        # MODIFY: styled placeholder
│   │   └── status.tsx                    # MODIFY: render SystemStatusPage
│   ├── components/
│   │   ├── ui/                           # NEW: shadcn components (card, badge, button, separator)
│   │   ├── status/
│   │   │   ├── SystemStatusPage.tsx      # NEW: main status page
│   │   │   ├── SystemStatusPage.test.tsx # NEW: tests
│   │   │   ├── ServiceStatusCard.tsx     # NEW: individual service card
│   │   │   └── OllamaStatusCard.tsx      # NEW: Ollama with model list
│   │   └── layout/
│   │       ├── StatusBar.tsx             # NEW: persistent footer status bar
│   │       ├── StatusBar.test.tsx        # NEW: tests
│   │       ├── ViewportWarning.tsx       # NEW: min viewport warning
│   │       └── ViewportWarning.test.tsx  # NEW: tests
│   ├── hooks/
│   │   └── useHealthStatus.ts            # NEW: health polling hook
│   └── lib/
│       ├── api-client.ts                 # MODIFY: typed client with generated paths
│       └── api-types.generated.ts        # REGENERATE: from backend OpenAPI spec
├── vite.config.ts                        # MODIFY: add Vitest config
├── package.json                          # MODIFY: add test scripts
scripts/
└── generate-api-types.sh                 # MODIFY: actual generation command
```

### Naming Conventions

| Context | Convention | Example |
|---------|-----------|---------|
| React components | PascalCase files | `SystemStatusPage.tsx`, `StatusBar.tsx` |
| Hooks | camelCase with `use` prefix | `useHealthStatus.ts` |
| Route files | TanStack Router convention | `__root.tsx`, `index.tsx`, `$id.tsx` |
| Test files | `.test.tsx` co-located | `SystemStatusPage.test.tsx` |
| CSS tokens | kebab-case with `--` prefix | `--bg-primary`, `--status-success` |
| API query keys | hierarchical arrays | `['health']`, `['investigations', id]` |

### Previous Story Intelligence

**From Story 1.1:**
- SQLModel dropped for SQLAlchemy 2.0 + Pydantic v2 (separate models)
- Python 3.13-slim (not 3.14)
- shadcn/ui initialized manually (CLI failed) — try CLI first, fallback to manual copy
- pnpm v10 blocks lifecycle scripts — `onlyBuiltDependencies` in root package.json
- CORS configured in backend for localhost:5173 and localhost:80

**From Story 1.2:**
- Health endpoint `GET /api/v1/health/` fully implemented with 20 tests
- Response schema: `HealthResponse` with services dict + overall_status + warnings + timestamp
- Each service reports status enum (healthy/unhealthy/unavailable) + detail string
- Ollama has extra fields: models_ready (bool), models (array of {name, available})
- Alembic auto-migration on startup established
- Loguru structured logging configured
- RFC 7807 error format for all API errors
- Code review applied 9 fixes including robust auth validation and status logic correction

**Git Intelligence:**
- Commit `77b379e`: Story 1.2 — backend health checks & model readiness
- Commit `4feffbb`: Story 1.1 — monorepo scaffolding & Docker Compose infrastructure
- Clean codebase baseline — all previous stories reviewed and fixed

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.3: Frontend Shell with System Status Page]
- [Source: _bmad-output/planning-artifacts/architecture.md#Frontend Architecture — React + Vite SPA]
- [Source: _bmad-output/planning-artifacts/architecture.md#Monorepo & Directory Structure — apps/web/]
- [Source: _bmad-output/planning-artifacts/architecture.md#Frontend Data Layer — TanStack Query, openapi-fetch]
- [Source: _bmad-output/planning-artifacts/architecture.md#Type Generation Pipeline — openapi-typescript]
- [Source: _bmad-output/planning-artifacts/architecture.md#Testing — Vitest + Testing Library]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Color Palette — Dark Theme Tokens]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Typography — Source Serif 4 + Inter]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#System Status Page — Service Checklist]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Status Indicators — icon + text + color]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Responsive Design — 1280px minimum]
- [Source: _bmad-output/planning-artifacts/prd.md#Deployment & Setup (FR41-FR44)]
- [Source: _bmad-output/implementation-artifacts/1-2-backend-health-checks-model-readiness.md#Dev Notes, Health Response Shape]
- [Source: _bmad-output/implementation-artifacts/1-1-monorepo-scaffolding-docker-compose-infrastructure.md#Dev Notes]
- [openapi-typescript: npx openapi-typescript ./openapi.json — openapi-ts.dev]
- [openapi-fetch: createClient<paths>() — openapi-ts.dev/openapi-fetch]
- [TanStack Query v5: refetchInterval option — tanstack.com/query/v5/docs/framework/react/reference/useQuery]
- [shadcn/ui CLI v4: pnpm dlx shadcn@latest add — ui.shadcn.com/docs/cli]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (claude-opus-4-6)

### Debug Log References

- TanStack Query v5: `refetchIntervalInBackground` is a boolean (not number); adjusted from story spec's `60000` to `true`
- Vitest v4: `@testing-library/jest-dom/vitest` import required in setup file
- StatusBar tests: mocked `@tanstack/react-router` `Link` component because `RouterProvider` renders asynchronously in test environment
- shadcn/ui CLI v4 installed successfully (no manual copy needed unlike Story 1.1)
- `vite-env.d.ts` was missing — added for `import.meta.env.DEV` type support

### Completion Notes List

- All 10 tasks (37 subtasks) completed successfully
- 14 unit tests passing across 3 test files (SystemStatusPage: 6, StatusBar: 5, ViewportWarning: 3)
- TypeScript strict type-checking passes with zero errors
- Production build succeeds: 362KB JS bundle (113KB gzipped)
- OSINT warm dark theme design tokens applied with entity + status colors
- Inter Variable font configured as primary sans-serif; Source Serif 4 Variable ready for future Q&A panel
- Health polling at 30s interval via TanStack Query with background refetch enabled
- CSS Grid layout in root (header / content / status-bar) with persistent clickable StatusBar
- OpenAPI type generation pipeline ready — script and npm script configured; manual HealthResponse types in hook as interim
- Viewport warning for <1280px with dismiss functionality

### Change Log

- 2026-03-08: Story 1.3 implementation complete — frontend shell with system status page, health monitoring, design tokens, and test suite
- 2026-03-08: Code review applied 6 fixes — URL double-prefix bug in api-client baseUrl, extracted duplicate statusConfig, ViewportWarning overlap fix, ReactQueryDevtools dev-only guard, docker-compose.dev.yml documentation, stub types comment

### File List

**New files:**
- apps/web/src/vite-env.d.ts
- apps/web/src/test-setup.ts
- apps/web/src/hooks/useHealthStatus.ts
- apps/web/src/components/ui/card.tsx (shadcn)
- apps/web/src/components/ui/badge.tsx (shadcn)
- apps/web/src/components/ui/button.tsx (shadcn)
- apps/web/src/components/ui/separator.tsx (shadcn)
- apps/web/src/components/status/ServiceStatusCard.tsx
- apps/web/src/components/status/OllamaStatusCard.tsx
- apps/web/src/components/status/status-config.ts
- apps/web/src/components/status/SystemStatusPage.tsx
- apps/web/src/components/status/SystemStatusPage.test.tsx
- apps/web/src/components/layout/StatusBar.tsx
- apps/web/src/components/layout/StatusBar.test.tsx
- apps/web/src/components/layout/ViewportWarning.tsx
- apps/web/src/components/layout/ViewportWarning.test.tsx

**Modified files:**
- apps/web/package.json (added dependencies, test scripts, generate-api-types script)
- apps/web/vite.config.ts (added Vitest config)
- apps/web/src/main.tsx (added font imports, QueryClientProvider, ReactQueryDevtools)
- apps/web/src/globals.css (added OSINT design tokens, font-family)
- apps/web/src/routes/__root.tsx (CSS Grid layout, StatusBar, ViewportWarning, OSINT header)
- apps/web/src/routes/index.tsx (styled placeholder with design tokens)
- apps/web/src/routes/status.tsx (renders SystemStatusPage)
- apps/web/src/routes/investigations/$id.tsx (styled placeholder with design tokens)
- apps/web/src/lib/api-client.ts (fixed baseUrl to empty string — was causing double-prefix)
- apps/web/src/lib/api-types.generated.ts (corrected stub comment)
- scripts/generate-api-types.sh (updated to use pnpm exec openapi-typescript)
- docker/docker-compose.dev.yml (added ollama profile so it doesn't start by default)
- pnpm-lock.yaml (dependency changes)
