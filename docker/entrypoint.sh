#!/bin/sh
set -e

# Start Celery worker in background
uv run celery -A app.worker.celery_app worker -B --loglevel=info &

# Start FastAPI with Uvicorn
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 &

# Wait for either process to exit
wait -n

# Exit with the status of the first process to exit
exit $?
