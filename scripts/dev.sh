#!/bin/bash
set -e

echo "Starting infrastructure services..."
docker compose -f docker/docker-compose.dev.yml up -d

echo "Waiting for services to be ready..."
sleep 3

echo "Starting FastAPI dev server..."
cd apps/api && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
API_PID=$!

echo "Starting Vite dev server..."
cd apps/web && pnpm dev &
VITE_PID=$!

cleanup() {
    echo "Shutting down..."
    kill $API_PID $VITE_PID 2>/dev/null
    docker compose -f docker/docker-compose.dev.yml down
}

trap cleanup EXIT INT TERM

wait
