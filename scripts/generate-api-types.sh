#!/usr/bin/env bash
# Requires: backend running at localhost:8000
set -euo pipefail

API_URL="${API_URL:-http://localhost:8000}"

echo "Generating TypeScript types from FastAPI OpenAPI spec..."
pnpm -C apps/web exec openapi-typescript "${API_URL}/openapi.json" \
  -o src/lib/api-types.generated.ts

echo "Types generated at apps/web/src/lib/api-types.generated.ts"
