#!/bin/bash
set -e

echo "=== RPA Automation Engine — Starting ==="

# Wait for PostgreSQL
echo "[entrypoint] Waiting for PostgreSQL..."
until pg_isready -h "${DB_HOST:-postgres}" -p "${DB_PORT:-5432}" -U "${DB_USER:-rpa}" -q 2>/dev/null; do
    echo "[entrypoint] PostgreSQL not ready, retrying in 2s..."
    sleep 2
done
echo "[entrypoint] PostgreSQL is ready"

# Wait for Redis
echo "[entrypoint] Waiting for Redis..."
until redis-cli -h "${REDIS_HOST:-redis}" -p "${REDIS_PORT:-6379}" ping 2>/dev/null | grep -q PONG; do
    echo "[entrypoint] Redis not ready, retrying in 2s..."
    sleep 2
done
echo "[entrypoint] Redis is ready"

# Run Alembic migrations
echo "[entrypoint] Running database migrations..."
cd /app
alembic upgrade head 2>&1 || {
    echo "[entrypoint] WARNING: Migrations failed (may be first run). Initializing DB via app..."
}

# Seed database (idempotent — skips if data exists)
echo "[entrypoint] Seeding database..."
python -m scripts.seed 2>&1 || {
    echo "[entrypoint] WARNING: Seed script failed (may already be seeded)"
}

# Start application based on role
ROLE="${APP_ROLE:-api}"

case "$ROLE" in
    api)
        echo "[entrypoint] Starting FastAPI server..."
        exec uvicorn app.main:app \
            --host 0.0.0.0 \
            --port "${APP_PORT:-8000}" \
            --workers "${UVICORN_WORKERS:-2}" \
            --log-level "${LOG_LEVEL:-info}" \
            --access-log \
            --proxy-headers \
            --forwarded-allow-ips="*"
        ;;
    worker)
        echo "[entrypoint] Starting Celery worker..."
        exec celery -A worker.celery_app worker \
            --loglevel="${LOG_LEVEL:-info}" \
            --concurrency="${CELERY_CONCURRENCY:-4}" \
            --queues="${CELERY_QUEUES:-default,workflows,triggers,notifications,health}" \
            --hostname="worker@%h" \
            --max-tasks-per-child=1000 \
            --without-gossip \
            --without-mingle
        ;;
    beat)
        echo "[entrypoint] Starting Celery Beat scheduler..."
        exec celery -A worker.celery_app beat \
            --loglevel="${LOG_LEVEL:-info}" \
            --scheduler=celery.beat:PersistentScheduler \
            --schedule=/tmp/celerybeat-schedule
        ;;
    flower)
        echo "[entrypoint] Starting Flower (Celery monitor)..."
        exec celery -A worker.celery_app flower \
            --port="${FLOWER_PORT:-5555}" \
            --broker_api="${CELERY_BROKER_URL:-redis://redis:6379/0}"
        ;;
    *)
        echo "[entrypoint] Unknown role: $ROLE"
        echo "Valid roles: api, worker, beat, flower"
        exit 1
        ;;
esac
