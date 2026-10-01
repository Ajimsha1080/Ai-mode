#!/bin/sh
set -e

# Run Alembic migrations if DATABASE_URL is configured
if [ -n "$DATABASE_URL" ]; then
    echo "Running database migrations via Alembic..."
    alembic upgrade head || {
        echo "CRITICAL: Alembic database migration failed! Aborting startup."
        exit 1
    }
fi

echo "Starting ShopMate Python FastAPI backend on port ${PORT:-8000}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
