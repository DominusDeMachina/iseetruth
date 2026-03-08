#!/bin/bash
set -e

API_URL="${API_URL:-http://localhost:8000}"
OUTPUT_FILE="apps/web/src/lib/api-types.generated.ts"

echo "Fetching OpenAPI spec from ${API_URL}/openapi.json..."
curl -s "${API_URL}/openapi.json" | npx openapi-typescript /dev/stdin -o "${OUTPUT_FILE}"

echo "Types generated at ${OUTPUT_FILE}"
