# RPA Automation Engine

Enterprise-grade, self-hosted Robotic Process Automation platform with visual workflow editor, multi-tenant support, and autonomous operation.

## Features

- **Visual Workflow Editor** — Drag-and-drop workflow builder with React Flow
- **13+ Task Types** — Web scraping, form filling, API calls, document processing, email, database, file operations, AI (Claude), and more
- **Distributed Agents** — Deploy RPA agents anywhere with auto-reconnect and heartbeat monitoring
- **Multi-Tenant** — Organization-level isolation with RBAC (roles & permissions)
- **Credential Vault** — AES-256 encrypted storage for API keys, passwords, and certificates
- **Scheduling** — Cron-based scheduling with timezone support
- **Real-Time Monitoring** — WebSocket-powered live execution tracking
- **Analytics & Reports** — Execution metrics, performance dashboards, export to CSV/JSON
- **Notifications** — Email, Slack, webhooks, in-app alerts
- **Audit Trail** — Complete history of all user actions for compliance
- **Auto-Retry** — Exponential backoff with configurable retry strategies
- **Claude AI Integration** — Text analysis, classification, extraction, summarization

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | Python 3.11 + FastAPI + SQLAlchemy 2.0 async |
| Task Queue | Celery + Redis 7 |
| Database | PostgreSQL 16 |
| Cache/PubSub | Redis 7 |
| Frontend | React 18 + TypeScript + Vite |
| Workflow Editor | React Flow 11 |
| UI Components | Tailwind CSS + Lucide Icons |
| Auth | JWT (access 30min / refresh 7d) + RBAC |
| Containerization | Docker + Docker Compose |
| Monitoring | Prometheus + Grafana |

## Quick Start

```bash
git clone https://github.com/andreiasenov-bg/rpa-automation-engine.git
cd rpa-automation-engine

# Start all services (Docker)
make dev

# Or without Make:
docker compose up -d

# Frontend:  http://localhost:3000
# Backend:   http://localhost:8000
# API Docs:  http://localhost:8000/docs
```

For frontend development without Docker:
```bash
cd frontend
npm install
npm run dev    # http://localhost:5173
```

## Project Structure

```
rpa-automation-engine/
├── backend/                 # FastAPI backend (127 API endpoints)
│   ├── app/                 # Application config & entry point
│   ├── api/                 # REST API routes & schemas
│   ├── core/                # Security, constants, utilities
│   ├── db/                  # Database models & migrations
│   ├── services/            # Business logic layer
│   ├── tasks/               # Task type implementations
│   ├── workflow/            # Execution engine & scheduler
│   ├── queue/               # Celery configuration
│   ├── integrations/        # External service connectors
│   ├── notifications/       # Email, Slack, webhook alerts
│   ├── triggers/            # Event triggers & webhooks
│   └── Dockerfile           # Multi-stage build
├── frontend/                # React SPA (16 pages, code-split)
│   ├── src/pages/           # Page components
│   ├── src/components/      # Shared UI components
│   ├── src/api/             # API client (Axios)
│   ├── src/stores/          # Zustand state management
│   ├── e2e/                 # Playwright E2E tests (51 tests)
│   ├── Dockerfile           # Multi-stage (Node → Nginx)
│   └── nginx.conf           # Reverse proxy + security headers
├── agent-service/           # Standalone RPA agent
├── monitoring/              # Prometheus + Grafana stack
├── k8s/                     # Kubernetes manifests
├── docs/                    # Documentation
│   ├── API.md               # Complete API reference
│   ├── DEPLOYMENT.md        # Deployment & operations guide
│   └── USER_GUIDE.md        # End-user guide
├── docker-compose.yml       # Development environment
├── docker-compose.prod.yml  # Production overlay
├── Makefile                 # Common commands
└── .env.example             # Environment template
```

## Documentation

- [API Reference](docs/API.md) — All 127 endpoints
- [Deployment Guide](docs/DEPLOYMENT.md) — Docker setup, production config, scaling, backup
- [User Guide](docs/USER_GUIDE.md) — How to use the platform

Interactive API docs (Swagger UI) available at `/docs` when the backend is running.

## Makefile Commands

```
make dev           Start development stack
make prod          Start production stack
make prod-build    Build and start production
make down          Stop all services
make migrate       Run database migrations
make seed          Seed database with sample data
make db-shell      Open PostgreSQL shell
make test-backend  Run backend pytest suite
make test-frontend Run Playwright E2E tests
make monitoring    Start Prometheus + Grafana
make clean         Stop and remove volumes (destroys data)
```

## License

MIT
