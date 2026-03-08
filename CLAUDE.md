# OSINT Project — Claude Code Context

## Dev Tooling

- **Backend (Python)**: Uses `uv` as package manager. Run commands with `uv run` from `apps/api/`.
  - Run tests: `cd apps/api && uv run pytest`
  - Python version: 3.11
- **Frontend (TypeScript/React)**: Uses `pnpm` in a monorepo with `pnpm-workspace.yaml`.
  - Run tests: `cd apps/web && pnpm test`
- **Infrastructure**: Docker Compose in `docker/` directory.
  - Dev services: `docker compose -f docker/docker-compose.dev.yml up`

## Post-Review / Post-Implementation

- After completing a code review or story implementation, always provide **manual testing instructions** — list the steps the user should follow to verify the feature end-to-end (what to start, what URLs to visit, what actions to perform, what to expect).
