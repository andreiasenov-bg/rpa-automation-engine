# RPA Automation Engine — Session Checkpoint Log

> **ИНСТРУКЦИЯ**: Дай този файл на Claude при нова сесия, за да продължи от последния checkpoint.

---

## Проект
- **Repo**: `https://github.com/andreiasenov-bg/rpa-automation-engine` (private)
- **User**: `andreiasenov-bg`
- **Stack**: Python 3.11 + FastAPI + SQLAlchemy 2.0 async + PostgreSQL 16 + Redis 7 + Celery + React 18

---

## Checkpoint #1 — Начален scaffold (Сесия 1)
**Дата**: 2025-02-13
**Commit**: `1f474c6` — Initial project scaffold
**Какво е направено**:
- 49 файла, ~3,751 реда код
- FastAPI app с lifespan, CORS, route registration
- 15+ SQLAlchemy модела: Organization, User, Role, Permission, Workflow, WorkflowStep, Execution, ExecutionLog, Agent, Credential, Schedule, AuditLog
- JWT auth (access/refresh tokens) + RBAC permission система
- AES-256 encryption (Fernet) за credential vault
- WebSocket connection manager за real-time updates
- 40+ API endpoints (health, auth, users, workflows, executions, agents, credentials, schedules, analytics)
- Docker Compose (PostgreSQL 16, Redis 7, Backend, Celery worker, Celery beat)
- Pydantic schemas за всички endpoints

## Checkpoint #2 — Claude AI Integration (Сесия 1)
**Commit**: `355361d` — Add Claude AI integration
**Какво е направено**:
- `backend/integrations/claude_client.py` — HTTP/2 connection pooling, auto-reconnect, conversation memory, token usage tracking
- 8 AI task типа: ask, analyze, decide, classify, extract, summarize, generate_code, conversation
- AI API routes: /api/ai/status, /ask, /analyze, /decide, /classify, /extract, /summarize, /usage
- `backend/tasks/implementations/ai_task.py` — AI tasks за workflow engine

## Checkpoint #3 — Checkpoint/Resume система (Сесия 1)
**Commit**: `4b3d8a4` — Add checkpoint/resume system
**Какво е направено**:
- `backend/workflow/checkpoint.py` — CheckpointType (15 типа), ExecutionState, CheckpointManager
- `backend/workflow/recovery.py` — RecoveryService (scan + auto-recover), ExecutionJournal
- 3 нови DB модела: ExecutionStateModel, ExecutionCheckpointModel, ExecutionJournalModel
- Zero data loss при crash — state се записва преди/след всяка стъпка

## Checkpoint #4 — External API Registry (Сесия 1)
**Commit**: `aaedfaa` — Add external API registry
**Какво е направено**:
- `backend/integrations/registry.py` — IntegrationRegistry с health monitoring, rate limiting, alerts
- Поддържа: REST, GraphQL, SOAP, WebSocket, Database, FTP/SFTP, SMTP, MQTT, Custom
- Background health check loop, failure tracking, dashboard
- API routes: /api/integrations/dashboard, CRUD, /health-check, /alerts/active
- Integration tasks за workflow engine

## Checkpoint #5 — ROADMAP.md (Сесия 1)
**Commit**: `e7471ec` — Add comprehensive roadmap
**Какво е направено**:
- Пълен roadmap с 4 приоритетни категории
- Архитектурни решения и конвенции

---

## Checkpoint #6 — Foundation Hardening + Engine Core (Сесия 2)
**Дата**: 2026-02-13
**Какво е направено**:

### 6a. Config.py fix
- Добавени липсващи properties: `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_POOL_TIMEOUT`
- Добавени: `ENVIRONMENT`, `API_V1_PREFIX`, `LOG_LEVEL`, `LOG_FORMAT`
- Properties: `is_development`, `is_production`, `cors_origins_list`

### 6b. API Versioning — `/api/v1/`
- `backend/api/v1/router.py` — агрегира всички routes под `/api/v1/`
- Health на `/api/` (k8s probes), всичко друго на `/api/v1/`

### 6c. Soft Delete на всички модели
- `SoftDeleteMixin` клас с `deleted_at`, `is_deleted`, `soft_delete()`, `restore()`
- `BaseModel` наследява `SoftDeleteMixin` → автоматично на ВСИЧКИ модели

### 6d. Alembic Migrations
- Async migration environment за PostgreSQL + SQLite

### 6e. Triggers система
- Trigger модел (8 типа: webhook, schedule, file_watch, email, db_change, api_poll, event_bus, manual)
- TriggerManager singleton + 3 handlers (webhook, schedule, event_bus)

### 6f. Workflow Execution Engine (DAG core)
- `backend/workflow/engine.py` (~500 реда)
- ExpressionEvaluator: `{{ steps.step_1.output.name }}`
- StepExecutor: timeout, retry (exponential/linear), вградени типове (condition, foreach, parallel, delay)
- WorkflowEngine: DAG traversal, branching, error handlers, checkpoint integration

---

## Checkpoint #7 — Celery + Notifications + Tasks + Logging (Сесия 2)
**Дата**: 2026-02-13
**Какво е направено**:

### 7a. Celery Worker Setup
- `backend/worker/celery_app.py` — 5 queues, beat schedule
- Worker tasks: workflow, triggers, health, maintenance, notifications

### 7b. Notification System
- 4 канала: Email (SMTP), Slack (webhook), Webhook (HTTP), WebSocket (real-time)
- NotificationManager с convenience methods

### 7c. Task Implementations
- HTTP tasks: HttpRequestTask, HttpDownloadTask
- Script tasks: PythonScriptTask, ShellCommandTask, DataTransformTask
- Task Registry: 15+ типа общо

### 7d. Structured Logging
- structlog с JSON (prod) / colored console (dev)

### 7e. Trigger→Engine Wiring
- `_handle_trigger_event`: Load workflow → Create Execution → Dispatch to Celery

---

## Checkpoint #8 — Service Layer + Docker + Tests (Сесия 3)
**Дата**: 2026-02-13
**Какво е направено**:

### 8a. CRUD Service Layer (Repository Pattern)
- **Нов файл**: `backend/services/base.py` — Generic BaseService[ModelType]:
  - `get_by_id()`, `get_by_id_and_org()`, `list()` (с pagination, ordering, soft-delete filtering)
  - `create()`, `update()`, `soft_delete()`, `restore()`, `hard_delete()`, `exists()`
  - Всички queries са org-scoped и soft-delete aware
- **Нов файл**: `backend/services/auth_service.py` — AuthService:
  - `register()` — Създава Organization + User, проверява за дублиран email
  - `login()` — Верифицира парола, обновява last_login_at, генерира JWT
  - `get_user_by_id()`, `get_user_by_email()`
- **Нов файл**: `backend/services/workflow_service.py` — WorkflowService + ExecutionService:
  - `create_workflow()`, `publish()`, `archive()`, `update_definition()` (bumps version)
  - `execute()` — Creates Execution + dispatches to Celery
  - ExecutionService: `get_by_workflow()`, `update_status()`
- **Нов файл**: `backend/services/trigger_service.py` — TriggerService:
  - `create_trigger()` с auto_start, `toggle()`, `delete_trigger()` (stop + soft delete)

### 8b. DB Seed Script
- **Нов файл**: `backend/scripts/seed.py`
  - Default org (RPA Engine) с enterprise plan
  - 25 permissions (workflows:read, workflows:write, executions:read, etc.)
  - 4 roles: admin (всички permissions), developer, operator, viewer
  - Admin user: admin@rpa-engine.local / admin123!
  - Idempotent — safe to run multiple times

### 8c. DB Model Updates
- **Permission model** обновен: `resource` + `action` полета заменени с `code` (unique, indexed) + добавен `organization_id` FK
- **Role model** обновен: добавено `slug` поле (indexed)

### 8d. Request Middleware
- **Нов файл**: `backend/core/middleware.py` — RequestTrackingMiddleware:
  - X-Request-ID генериране/propagation
  - X-Process-Time header
  - Structured logging per request (skip health endpoints)
  - Global exception handlers: NotFoundError→404, UnauthorizedError→401, ForbiddenError→403, ValidationError→422, ConflictError→409, ValueError→400
- Интегриран в `main.py` (`create_app()`)

### 8e. Docker Entrypoint
- **Нов файл**: `backend/scripts/entrypoint.sh`
  - Wait for PostgreSQL + Redis
  - Run Alembic migrations
  - Run seed script (idempotent)
  - Multi-role: api, worker, beat, flower (via APP_ROLE env)
- **Обновен**: `backend/Dockerfile` — +postgresql-client +redis-tools, entrypoint
- **Обновен**: `docker-compose.yml` — YAML anchors (&backend-common), proper env vars, Celery queues

### 8f. Pytest Test Suite Foundation
- **Нов файл**: `backend/pytest.ini` — config с markers (unit, integration, slow, e2e)
- **Нов файл**: `backend/tests/conftest.py` — shared fixtures:
  - In-memory SQLite async DB (no PostgreSQL needed)
  - AsyncSession factory с rollback per test
  - FastAPI test client (httpx AsyncClient)
  - Pre-seeded: test_org, test_user, test_workflow, auth_headers
- **Тестове**:
  - `test_health.py` — Health endpoints, X-Request-ID propagation
  - `test_auth.py` — Password hashing, JWT creation/decoding
  - `test_models.py` — Model creation, soft delete
  - `test_workflow_engine.py` — ExpressionEvaluator, ExecutionContext serialization
  - `test_services.py` — AuthService register/login/duplicate checks

---

## Файлова структура (текущо състояние)
```
rpa-automation-engine/
├── SESSION_LOG.md, README.md, ROADMAP.md
├── docker-compose.yml (YAML anchors, multi-service)
├── .gitignore
├── backend/
│   ├── Dockerfile (multi-role entrypoint)
│   ├── requirements.txt
│   ├── pytest.ini
│   ├── .env.example
│   ├── alembic.ini, alembic/
│   ├── app/
│   │   ├── config.py, main.py (middleware integrated), dependencies.py
│   ├── api/
│   │   ├── v1/router.py (15 route groups)
│   │   ├── routes/ (health, auth, users, workflows, executions, agents,
│   │   │           credentials, schedules, analytics, ai, integrations,
│   │   │           triggers, notifications, task_types)
│   │   ├── schemas/, websockets/
│   ├── core/
│   │   ├── constants, exceptions, security, utils
│   │   ├── logging_config, middleware (RequestTracking + exception handlers)
│   ├── db/
│   │   ├── base.py (BaseModel + SoftDeleteMixin)
│   │   ├── database.py, session.py
│   │   └── models/ (17+ models)
│   ├── integrations/ (claude_client, registry)
│   ├── notifications/ (channels × 4, manager)
│   ├── services/                       ← NEW
│   │   ├── base.py (BaseService generic CRUD)
│   │   ├── auth_service.py
│   │   ├── workflow_service.py
│   │   └── trigger_service.py
│   ├── scripts/
│   │   ├── seed.py                     ← NEW
│   │   └── entrypoint.sh              ← NEW
│   ├── tasks/
│   │   ├── base_task, registry (15+ types)
│   │   └── implementations/ (ai, integration, http, script)
│   ├── triggers/ (base, manager, handlers × 3)
│   ├── worker/ (celery_app, tasks × 5)
│   ├── workflow/ (checkpoint, recovery, engine)
│   └── tests/                          ← NEW
│       ├── conftest.py (async fixtures, in-memory DB)
│       ├── test_health.py
│       ├── test_auth.py
│       ├── test_models.py
│       ├── test_workflow_engine.py
│       └── test_services.py
```

## Технически бележки
- **Git**: `git push` директно с token в URL (не `gh` CLI — blocked by proxy)
- **Git credentials**: `~/.git-credentials` с token `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`
- **DB**: SQLite + aiosqlite (dev/test), PostgreSQL + asyncpg (prod)
- **Всички модели**: BaseModel → SoftDeleteMixin (id, created/updated/deleted_at, is_deleted)
- **API**: `/api/v1/` prefix, 15 route groups, 60+ endpoints
- **Task types**: 15+ (8 AI, 2 integration, 2 HTTP, 3 script/data)
- **Celery**: 5 queues (workflows, triggers, notifications, health, default)
- **Notifications**: 4 канала (email, slack, webhook, websocket)
- **Services**: BaseService generic CRUD, AuthService, WorkflowService, ExecutionService, TriggerService
- **Tests**: pytest + pytest-asyncio, in-memory SQLite, rollback per test

## Checkpoint #9 — Wire Services into API Routes (Сесия 3)
**Дата**: 2026-02-13
**Какво е направено**:

### 9a. Auth Routes — Fully Wired
- `POST /auth/register` → AuthService.register() → създава Org + User → връща JWT tokens
- `POST /auth/login` → AuthService.login() → верифицира парола → обновява last_login → JWT
- `POST /auth/refresh` → верифицира refresh token + проверява user в DB → нови tokens
- `GET /auth/me` → get_current_active_user (DB проверка) → връща пълен профил с roles

### 9b. Workflow Routes — Fully Wired
- `GET /workflows/` → WorkflowService.list() с pagination, org scope
- `POST /workflows/` → WorkflowService.create_workflow()
- `GET /workflows/{id}` → WorkflowService.get_by_id_and_org()
- `PUT /workflows/{id}` → update_definition() (version bump) или update()
- `DELETE /workflows/{id}` → soft_delete()
- `POST /workflows/{id}/publish` → publish (status→published, is_enabled→true)
- `POST /workflows/{id}/archive` → archive (status→archived, is_enabled→false)
- `POST /workflows/{id}/execute` → execute() → Celery dispatch → 202 Accepted

### 9c. Execution Routes — Fully Wired
- `GET /executions/` → ExecutionService.list() с filters (workflow_id, status)
- `GET /executions/{id}` → get_by_id_and_org()
- `GET /executions/{id}/logs` → ExecutionLog query
- `POST /executions/{id}/retry` → creates new execution за failed/cancelled
- `POST /executions/{id}/cancel` → update_status("cancelled")

### 9d. Trigger Routes — Fully Wired with CRUD
- `GET /triggers/` → TriggerService.list() с optional workflow_id filter
- `POST /triggers/` → create_trigger() с auto_start
- `GET /triggers/{id}` → get_by_id_and_org()
- `PUT /triggers/{id}` → update name/config
- `DELETE /triggers/{id}` → delete_trigger() (stop + soft-delete)
- `POST /triggers/{id}/toggle` → toggle() (enable/disable + start/stop manager)
- `POST /triggers/{id}/fire` → manual fire (auth required)
- Webhook receiver остава unauthenticated (за external systems)

### 9e. User Routes — Fully Wired
- `GET /users/` → UserService.list_by_org() с pagination
- `GET /users/{id}` → get_by_id_and_org()
- `PUT /users/{id}` → update_profile() (safe fields only)
- `DELETE /users/{id}` → deactivate (soft-delete, cannot deactivate self)

### 9f. Infrastructure Improvements
- **Нов файл**: `backend/services/user_service.py` — UserService with org-scoped queries
- **decode_access_token()** добавена в security.py (за tests)
- **get_current_active_user** вече проверява user в DB (is_active + is_deleted)
- **get_db** вече auto-commits on success, rollback on error
- **DB import consistency**: всички файлове ползват `db.database`, не `db.session`
- **Test fixtures фиксирани**: password_hash (не hashed_password), subscription_plan (не plan)
- **Test assertions фиксирани**: match actual AuthService return types

---

## Файлова структура (текущо състояние)
```
rpa-automation-engine/
├── SESSION_LOG.md, README.md, ROADMAP.md
├── docker-compose.yml (YAML anchors, multi-service)
├── backend/
│   ├── Dockerfile, requirements.txt, pytest.ini
│   ├── alembic.ini, alembic/
│   ├── app/
│   │   ├── config.py, main.py (middleware), dependencies.py (DB-verified auth)
│   ├── api/
│   │   ├── v1/router.py (15 route groups)
│   │   ├── routes/ — ALL WIRED TO SERVICES:
│   │   │   ├── auth.py (register/login/refresh/me)
│   │   │   ├── users.py (CRUD + deactivate)
│   │   │   ├── workflows.py (CRUD + publish/archive/execute)
│   │   │   ├── executions.py (list/get/logs/retry/cancel)
│   │   │   ├── triggers.py (CRUD + toggle/fire + webhook)
│   │   │   ├── agents, credentials, schedules, analytics, ai
│   │   │   ├── integrations, notifications, task_types
│   │   ├── schemas/, websockets/
│   ├── core/
│   │   ├── constants, exceptions, security (+decode_access_token)
│   │   ├── utils, logging_config, middleware
│   ├── db/
│   │   ├── base.py, database.py, session.py
│   │   └── models/ (17+ models)
│   ├── integrations/ (claude_client, registry)
│   ├── notifications/ (channels × 4, manager)
│   ├── services/
│   │   ├── base.py (BaseService generic CRUD)
│   │   ├── auth_service.py, user_service.py (NEW)
│   │   ├── workflow_service.py, trigger_service.py
│   ├── scripts/ (seed.py, entrypoint.sh)
│   ├── tasks/ (15+ types)
│   ├── triggers/ (base, manager, handlers × 3)
│   ├── worker/ (celery_app, tasks × 5)
│   ├── workflow/ (checkpoint, recovery, engine)
│   └── tests/ (conftest, 5 test modules)
```

## Технически бележки
- **Git**: `git push` директно с token в URL
- **Git credentials**: `~/.git-credentials` с token `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`
- **DB**: SQLite + aiosqlite (dev/test), PostgreSQL + asyncpg (prod)
- **API**: `/api/v1/` prefix, 15 route groups, 70+ endpoints (5 core groups now fully wired)
- **Services**: BaseService, AuthService, UserService, WorkflowService, ExecutionService, TriggerService
- **Auth flow**: JWT (access 30min + refresh 7d), get_current_active_user verifies DB
- **All routes**: use get_current_active_user (DB-verified) instead of raw get_current_user

## Checkpoint #10 — React Frontend SPA (Сесия 4)
**Дата**: 2026-02-13
**Какво е направено**:

### 10a. Project Setup
- **Vite 7 + React 19 + TypeScript** scaffold (replaced old empty skeleton)
- **Dependencies**: react-router-dom 7, @tanstack/react-query 5, axios, zustand 5, reactflow 11, lucide-react, tailwindcss 4, clsx
- **vite.config.ts**: Tailwind CSS 4 plugin, `@/` path alias, proxy `/api` → `http://localhost:8000`
- **tsconfig.app.json**: path aliases, strict mode, bundler moduleResolution

### 10b. API Layer
- **`api/client.ts`** — Axios HTTP client with JWT interceptors:
  - Request: attaches `Authorization: Bearer` header from localStorage
  - Response: 401 → auto-refresh access token via refresh token; failed queue mechanism; redirect to /login on refresh failure
- **`api/auth.ts`** — login, register, me, refresh
- **`api/workflows.ts`** — list, get, create, update, delete, publish, archive, execute
- **`api/executions.ts`** — list, get, logs, retry, cancel

### 10c. State Management
- **`stores/authStore.ts`** — Zustand store:
  - State: user, isAuthenticated, isLoading, error
  - Actions: login, register, logout, loadUser, clearError
  - Persists JWT tokens in localStorage

### 10d. Layout Components
- **`components/layout/Sidebar.tsx`** — Navigation sidebar with NavLink active state, lucide-react icons, user email, logout button
- **`components/layout/AppLayout.tsx`** — Sidebar + `<Outlet />` (React Router nested routes)
- **`components/layout/ProtectedRoute.tsx`** — Redirects to /login if not authenticated

### 10e. Pages
- **`pages/LoginPage.tsx`** — Email/password form, error display, loading spinner, link to register
- **`pages/RegisterPage.tsx`** — Full registration: first/last name, org name, email, password + confirm, client-side validation (min 8 chars, match passwords)
- **`pages/DashboardPage.tsx`** — Stats grid (6 cards: workflows, active, runs, running, completed, failed) + recent executions list with status badges, durations, relative timestamps
- **`pages/WorkflowListPage.tsx`** — Paginated table with search, status badges, action menu (edit, execute, publish, archive, delete), "New Workflow" creates and navigates to editor
- **`pages/WorkflowEditorPage.tsx`** — Visual DAG editor with React Flow:
  - 10 task types in palette (web scraping, API request, form fill, email, database, file ops, script, condition, loop, delay)
  - Custom StepNode component with icon + color coding
  - Add/delete/connect steps, drag-drop positioning
  - Save, publish, execute toolbar
  - Dirty state indicator, step count, MiniMap, Background grid, Controls
  - Bidirectional conversion: backend WorkflowStep[] ↔ React Flow Node[]/Edge[]
- **`pages/ExecutionsPage.tsx`** — Expandable execution rows with:
  - Status filter tabs (All/pending/running/completed/failed/cancelled)
  - Auto-refresh every 5s when running/pending executions exist
  - Log viewer per execution (monospace terminal-style, color-coded levels)
  - Retry/cancel actions
  - Pagination

### 10f. Routing
- **`App.tsx`** — React Router v7 with:
  - Public: /login, /register (redirect to / if authenticated)
  - Protected (nested under AppLayout): /, /workflows, /workflows/:id/edit, /executions, /triggers, /users, /settings
  - Placeholder pages for triggers, users, settings
  - QueryClientProvider (React Query)
- **`main.tsx`** — StrictMode + createRoot entry

### 10g. Build Verification
- `tsc -b` — zero errors
- `vite build` — production bundle: 485 KB JS (156 KB gzip) + 30 KB CSS (6.6 KB gzip)

---

## Файлова структура (текущо състояние)
```
rpa-automation-engine/
├── SESSION_LOG.md, README.md, ROADMAP.md
├── docker-compose.yml (YAML anchors, multi-service)
├── backend/
│   ├── Dockerfile, requirements.txt, pytest.ini
│   ├── alembic.ini, alembic/
│   ├── app/ (main.py, config.py, dependencies.py)
│   ├── api/
│   │   ├── v1/router.py (15 route groups)
│   │   ├── routes/ — ALL CORE ROUTES WIRED TO SERVICES
│   │   ├── schemas/, websockets/
│   ├── core/ (security, middleware, logging, exceptions)
│   ├── db/ (base.py, database.py, models/ 17+)
│   ├── integrations/ (claude_client, registry)
│   ├── notifications/ (channels × 4, manager)
│   ├── services/ (base, auth, user, workflow, trigger)
│   ├── scripts/ (seed.py, entrypoint.sh)
│   ├── tasks/ (15+ types)
│   ├── triggers/ (base, manager, handlers × 3)
│   ├── worker/ (celery_app, tasks × 5)
│   ├── workflow/ (checkpoint, recovery, engine)
│   └── tests/ (conftest, 5 test modules)
├── frontend/                              ← NEW (Checkpoint #10)
│   ├── package.json, vite.config.ts
│   ├── tsconfig.json, tsconfig.app.json, tsconfig.node.json
│   ├── index.html
│   └── src/
│       ├── main.tsx, App.tsx, index.css
│       ├── api/
│       │   ├── client.ts (JWT interceptors, auto-refresh)
│       │   ├── auth.ts, workflows.ts, executions.ts
│       ├── stores/
│       │   └── authStore.ts (Zustand)
│       ├── types/
│       │   └── index.ts (User, Workflow, Execution, Trigger, etc.)
│       ├── components/layout/
│       │   ├── Sidebar.tsx, AppLayout.tsx, ProtectedRoute.tsx
│       └── pages/
│           ├── LoginPage.tsx, RegisterPage.tsx
│           ├── DashboardPage.tsx
│           ├── WorkflowListPage.tsx
│           ├── WorkflowEditorPage.tsx (React Flow DAG editor)
│           └── ExecutionsPage.tsx
```

## Технически бележки
- **Git**: `git push` директно с token в URL
- **Git credentials**: `~/.git-credentials` с token `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`
- **DB**: SQLite + aiosqlite (dev/test), PostgreSQL + asyncpg (prod)
- **API**: `/api/v1/` prefix, 15 route groups, 70+ endpoints (5 core groups fully wired)
- **Frontend**: React 19 + TypeScript + Vite 7 + Tailwind CSS 4 + React Flow 11 + Zustand 5
- **Services**: BaseService, AuthService, UserService, WorkflowService, ExecutionService, TriggerService
- **Auth flow**: JWT (access 30min + refresh 7d), DB-verified, auto-refresh in frontend

## Какво следва (приоритет)
1. **WebSocket real-time updates** — Live execution status in frontend
2. **Alembic initial migration** — Generate from current models
3. **Wire remaining backend routes** — agents, credentials, schedules, analytics
4. **Triggers/Users/Settings pages** — Complete remaining frontend pages
5. **Prometheus metrics** — /metrics endpoint за monitoring
6. **Browser automation tasks** — Playwright-based web scraping/form filling
7. **Docker frontend** — Add frontend to docker-compose (nginx or Vite preview)
