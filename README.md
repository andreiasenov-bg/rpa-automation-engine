# RPA Automation Engine

Enterprise-grade, self-hosted Robotic Process Automation platform with visual workflow editor, multi-tenant support, and autonomous operation.

## Features

- **Visual Workflow Editor** — Drag-and-drop workflow builder with React Flow
- **12+ Task Types** — Web scraping, form filling, API calls, document processing, email, database, file operations, and more
- **Distributed Agents** — Deploy RPA agents anywhere with auto-reconnect and heartbeat monitoring
- **Multi-Tenant** — Organization-level isolation with RBAC (roles & permissions)
- **Credential Vault** — AES-256 encrypted storage for API keys, passwords, and certificates
- **Scheduling** — Cron-based scheduling with timezone support
- **Real-Time Monitoring** — WebSocket-powered live execution tracking
- **Analytics & Reports** — Execution metrics, performance dashboards, export to CSV/PDF
- **Notifications** — Email, Slack, webhooks, PagerDuty alerts
- **Audit Trail** — Complete history of all user actions for compliance
- **Auto-Retry** — Exponential backoff with configurable retry strategies

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | Python 3.11 + FastAPI |
| Task Queue | Celery + Redis |
| Database | PostgreSQL 16 |
| Cache/PubSub | Redis 7 |
| Frontend | React 18 + TypeScript + Vite |
| Workflow Editor | React Flow |
| UI | shadcn/ui + Tailwind CSS |
| Containerization | Docker + Docker Compose |

## Quick Start

```bash
# Clone the repository
git clone https://github.com/andreiasenov-bg/rpa-automation-engine.git
cd rpa-automation-engine

# Start all services
docker-compose up -d

# Backend API: http://localhost:8000
# API Docs:    http://localhost:8000/docs
# Frontend:    http://localhost:3000
```

## Project Structure

```
rpa-automation-engine/
├── backend/                 # FastAPI backend
│   ├── app/                 # Application config & entry point
│   ├── api/                 # REST API routes & schemas
│   ├── core/                # Security, constants, utilities
│   ├── db/                  # Database models & migrations
│   ├── services/            # Business logic layer
│   ├── tasks/               # Task type implementations
│   ├── workflow/            # Execution engine & scheduler
│   ├── queue/               # Celery configuration
│   └── integrations/        # External service connectors
├── frontend/                # React SPA
├── agent-service/           # Standalone RPA agent
├── docker-compose.yml       # Development environment
├── k8s/                     # Kubernetes manifests
└── docs/                    # Documentation
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /api/auth/login` | Authenticate user |
| `POST /api/auth/register` | Register organization + user |
| `GET /api/workflows` | List workflows |
| `POST /api/workflows` | Create workflow |
| `POST /api/workflows/{id}/execute` | Trigger execution |
| `GET /api/executions` | Execution history |
| `GET /api/executions/{id}/logs` | Execution logs |
| `GET /api/agents` | List agents |
| `POST /api/agents/register` | Register agent |
| `GET /api/credentials` | List credentials |
| `GET /api/schedules` | List schedules |
| `GET /api/analytics/overview` | Execution statistics |

Full API documentation available at `/docs` (Swagger UI).

## License

MIT
