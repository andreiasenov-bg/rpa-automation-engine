# RPA Automation Engine — Deployment Guide

## Prerequisites

- Docker 24+ and Docker Compose v2
- 4GB+ RAM (8GB recommended for production)
- PostgreSQL 16 (included in Docker stack)
- Redis 7 (included in Docker stack)

## Quick Start (Development)

```bash
git clone https://github.com/andreiasenov-bg/rpa-automation-engine.git
cd rpa-automation-engine

# Start all services
make dev
# or: docker compose up -d

# Access:
#   Frontend:  http://localhost:3000
#   Backend:   http://localhost:8000
#   API Docs:  http://localhost:8000/docs
```

Default dev credentials are configured in `docker-compose.yml`. The database is automatically migrated and seeded on first run.

## Production Deployment

### 1. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with production values:

```env
# Required — generate with: openssl rand -hex 32
SECRET_KEY=<64-char-hex>
ENCRYPTION_KEY=<64-char-hex>

# Database
DATABASE_URL=postgresql+asyncpg://rpa_user:STRONG_PASSWORD@postgres:5432/rpa_engine
DB_PASSWORD=STRONG_PASSWORD

# Redis
REDIS_URL=redis://redis:6379/0
REDIS_PASSWORD=<redis-password>

# CORS
ALLOWED_ORIGINS=https://your-domain.com

# Workers
UVICORN_WORKERS=4
CELERY_CONCURRENCY=8

# Optional
ANTHROPIC_API_KEY=<your-claude-api-key>
SLACK_WEBHOOK_URL=<webhook-url>
```

### 2. Build and Start

```bash
make prod-build
# or: docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

### 3. Verify

```bash
# Check all services are healthy
docker compose ps

# Check backend health
curl http://localhost:8000/api/health/health

# Tail logs
make prod-logs
```

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌────────────┐
│   Nginx     │────▶│   FastAPI    │────▶│ PostgreSQL │
│  (frontend) │     │  (backend)   │     │   16       │
│  port 3000  │     │  port 8000   │     │            │
└─────────────┘     └──────┬───────┘     └────────────┘
                           │
                    ┌──────┴───────┐
                    │    Redis 7   │
                    │ broker/cache │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
        ┌─────┴─────┐ ┌───┴────┐ ┌────┴─────┐
        │  Celery   │ │ Celery │ │  Flower  │
        │  Worker   │ │  Beat  │ │ (opt.)   │
        └───────────┘ └────────┘ └──────────┘
```

## Services

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| frontend | nginx:1.25-alpine | 3000→80 | React SPA + reverse proxy |
| backend | python:3.11-slim | 8000 | FastAPI REST API + WebSocket |
| postgres | postgres:16-alpine | 5432 | Primary database |
| redis | redis:7-alpine | 6379 | Task broker, cache, pub/sub |
| celery-worker | (backend image) | — | Background task processing |
| celery-beat | (backend image) | — | Scheduled task triggers |

## Resource Limits (Production)

| Service | Memory | CPU | Replicas |
|---------|--------|-----|----------|
| backend | 2 GB | 2.0 | 2 |
| celery-worker | 2 GB | 2.0 | 2 |
| celery-beat | 512 MB | 0.5 | 1 |
| frontend | 256 MB | 0.5 | 2 |
| postgres | 2 GB | 2.0 | 1 |
| redis | 1 GB | 1.0 | 1 |

## Database Migrations

```bash
# Run pending migrations
make migrate
# or: docker compose exec backend alembic upgrade head

# Create a new migration
docker compose exec backend alembic revision --autogenerate -m "description"

# Rollback one step
docker compose exec backend alembic downgrade -1
```

## Monitoring (Optional)

```bash
make monitoring

# Prometheus: http://localhost:9090
# Grafana:    http://localhost:3001 (admin/admin)
```

The monitoring stack includes Prometheus, Grafana, and exporters for Redis and PostgreSQL. Pre-built dashboards are included.

## SSL/TLS

For production, place a reverse proxy (e.g., Caddy, Traefik, or an external Nginx) in front of the stack to handle TLS termination:

```
Internet → Caddy (TLS) → Nginx (port 3000) → Backend (port 8000)
```

Example Caddyfile:
```
rpa.example.com {
    reverse_proxy localhost:3000
}
```

## Backup

### Database
```bash
# Dump
docker compose exec postgres pg_dump -U rpa_user rpa_engine > backup.sql

# Restore
docker compose exec -T postgres psql -U rpa_user rpa_engine < backup.sql
```

### Redis
Redis data is persisted to the `redis_data` / `redis_prod_data` volume. For backup, stop Redis and copy the volume.

## Scaling

To scale backend or worker instances:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --scale backend=4 --scale celery-worker=4
```

For Kubernetes deployment, manifests are available in the `k8s/` directory.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Backend won't start | Check `DATABASE_URL` and wait for PostgreSQL health |
| WebSocket disconnects | Ensure nginx proxy_read_timeout is high (86400s) |
| Celery tasks stuck | Check Redis connectivity and queue names |
| Migration fails | Run `alembic downgrade -1` then `alembic upgrade head` |
| High memory usage | Reduce `CELERY_CONCURRENCY` or add `--max-tasks-per-child` |

## Makefile Commands

```
make help          Show all available commands
make dev           Start development stack
make prod          Start production stack
make prod-build    Build and start production
make down          Stop all services
make clean         Stop and remove volumes (destroys data)
make migrate       Run database migrations
make seed          Seed database
make db-shell      Open PostgreSQL shell
make test-backend  Run backend tests
make test-frontend Run frontend E2E tests
make monitoring    Start Prometheus + Grafana
```
