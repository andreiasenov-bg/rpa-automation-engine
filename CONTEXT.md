# RPA Engine — Project Context (updated 2026-02-20)

## Server
- Hetzner Cloud CX22, IP: 89.167.34.21
- Domain: rpa.o-connect.com
- Server ID: 121307281
- Host path: /opt/rpa-engine
- Deployer path: /repo (maps to host /opt/rpa-engine)

## Docker Compose
- Project name: rpa-engine
- Command pattern: docker compose --project-directory /opt/rpa-engine -f /repo/docker-compose.yml --env-file /repo/.env up -d [service]
- 13 containers total

## Services (13 containers)
1. postgres (PostgreSQL)
2. redis
3. pgbouncer (connection pooling, port 6432)
4. backend (FastAPI, port 8000)
5. celery-worker
6. celery-beat
7. deployer (port 9000)
8. frontend (Next.js/Vite, port 3000)
9. flower (Celery monitor, port 5555)
10. prometheus (port 9090, localhost only)
11. grafana (port 3001, localhost only)
12. cadvisor (port 8080, localhost only)
13. node-exporter (port 9100, localhost only)

## Caddy (systemd on host)
Routes: /api/* -> backend:8000, /deploy/* -> deployer:9000, /ws -> backend:8000, default -> frontend:3000

## Completed Checkpoints (P0-P3)
- CP0: Docker restart policies
- CP1: Secrets rotation + deployer recovery
- CP2: PgBouncer connection pooling (d34d7dd)
- CP3: Redis-backed rate limiter (f914da5)
- CP4: Worker-safe DB sessions for Celery (0e7f629)
- CP5: JWT expiry reduction 24h->30min (e6d07f9)
- CP6: Flower dashboard (3372041)
- CP7: Monitoring stack - Prometheus+Grafana+cAdvisor+node-exporter (fde3bed)
- CP8: AI Creator structured JSON output via tool_use (ae020c2)
- CP9: Run button fix + RouteErrorBoundary (fbfcfa2)
- CP10: GitHub Actions CI/CD pipeline (95b52a6)
- CP11: Automated DB backups with 7-day retention (2900187)

## Key Files Modified
- docker-compose.yml (all services)
- backend/integrations/claude_client.py (ask_json method)
- backend/api/routes/ai.py (structured output for generate-workflow)
- backend/core/rate_limit.py (Redis-backed)
- backend/db/worker_session.py (per-call async engine)
- backend/app/config.py (JWT expiry)
- frontend/src/pages/WorkflowEditorPage.tsx (Run button)
- frontend/src/components/ErrorBoundary.tsx (RouteErrorBoundary)
- frontend/src/App.tsx (route-level error boundary)
- .github/workflows/ci-cd.yml (CI/CD pipeline)
- scripts/backup-db.sh (automated backups)
- monitoring/prometheus.yml (scrape configs)

## Known Issues
- Git push blocked: PAT needs 'workflow' scope to push .github/workflows/
- Celery health task: timezone naive vs aware datetime (pre-existing bug)
- All backend/celery services need PYTHONPATH='/app' in docker-compose

## Credentials
- Deploy Token: zHOOF6REZHaUMskB069Xmx5tCBog30axMrgqt39n0zE
- Web Login: andreiasenov@gmail.com / 9geOkfMTwjic8JojOORhRQ
- VNC: console.hetzner.com root/THAibx3VVikT
