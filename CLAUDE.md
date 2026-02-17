# RPA Automation Engine — Project Context

## Quick Reference
- **App**: http://localhost:3000 (frontend) / http://localhost:8000 (backend API)
- **Deployer**: http://localhost:9000 (POST /deploy, GET /status, POST /health-check)
- **Auth**: admin@rpa-engine.com / admin123!
- **Language**: User speaks Bulgarian, code/docs in English
- **Stack**: React + Vite + Tailwind v4 + Zustand | FastAPI + SQLAlchemy async + PostgreSQL + Redis + Celery

## Deployment Flow
1. `git push origin main`
2. `POST http://localhost:9000/deploy` → git pull → uvicorn reload → health check
3. Frontend auto-reloads via Vite dev server (volume mount)

## Code Review Rules (hardcoded)
- **BIG CHANGE** (4 issues/section) vs **SMALL CHANGE** (1/section)
- Sections: Architecture → Code Quality → Tests → Performance
- Format: describe → options → recommend → ask approval
- Principles: DRY, well-tested, engineered enough, edge cases, explicit > clever

---

## Frontend Architecture

### Responsive Design System

**Breakpoint**: `lg` (1024px) is the primary mobile/desktop split.

| Viewport  | Width         | Sidebar        | Hamburger | Padding  |
|-----------|---------------|----------------|-----------|----------|
| Mobile    | < 768px       | Hidden (drawer)| Visible   | p-3      |
| Tablet    | 768–1023px    | Hidden (drawer)| Visible   | p-4      |
| Desktop   | ≥ 1024px      | Inline         | Hidden    | p-6      |

**Key files:**
- `src/hooks/useBreakpoint.ts` — `useBreakpoint()` hook: `{ isMobile, isTablet, isDesktop, breakpoint, width }`
- `src/stores/layoutStore.ts` — Zustand store: `sidebarOpen`, `searchOpen` + actions
- `src/lib/responsive.ts` — Shared constants: `CARD_GRID`, `PAGE_HEADER`, `CONTENT_PADDING`, etc.
- `src/components/layout/AppLayout.tsx` — Root layout, reads from layoutStore
- `src/components/layout/Sidebar.tsx` — Navigation drawer, reads from layoutStore
- `src/components/layout/TopBar.tsx` — Header with hamburger, reads from layoutStore

**When adding a new page:**
1. Import responsive constants from `@/lib/responsive`
2. Use `PAGE_HEADER` for the header section
3. Use `CARD_GRID` or `STAT_GRID` for card layouts
4. Use `INFO_GRID_2` / `INFO_GRID_3` for detail panels
5. If you need JS-level breakpoint detection, use `useBreakpoint()` from `@/hooks/useBreakpoint`
6. For sidebar/search state, use `useLayoutStore()` — never pass as props

**Responsive class patterns (Tailwind):**
```
Headers:     flex flex-col sm:flex-row sm:items-center justify-between gap-3
Grids:       grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4
Padding:     p-3 sm:p-4 md:p-6
Text sizes:  text-xl sm:text-2xl
Buttons:     px-3 sm:px-4 py-2 sm:py-2.5
Hide mobile: hidden sm:block  (or  hidden lg:block for sidebar-related)
Meta rows:   flex flex-wrap items-center gap-x-4 gap-y-1
```

### State Management (Zustand stores)
- `authStore` — user, login/logout, tokens
- `layoutStore` — sidebar drawer, search overlay
- `themeStore` — light/dark/system theme
- `toastStore` — notification toasts
- `chatStore` — AI chat assistant state
- `helpStore` — onboarding tour state

### Routing (React Router v7)
- Public: `/login`, `/register`
- Protected: 20 routes wrapped in `ProtectedRoute` + `AppLayout`
- Heavy pages use `React.lazy()` for code splitting

### Styling
- **Tailwind CSS v4** — pure utility classes, no CSS modules/styled-components
- **Dark mode**: `.dark` class on `<html>` via themeStore
- **Icons**: `lucide-react`
- **Charts**: `recharts`
- **Flow editor**: `reactflow`

---

## Backend Architecture

### Key patterns
- **Async SQLAlchemy** — always `await db.refresh(obj)` after `db.flush()` (prevents greenlet_spawn errors)
- **Naive UTC datetimes** — `.replace(tzinfo=None)` after timezone conversion for PostgreSQL TIMESTAMP columns
- **Relationships**: `lazy="noload"` on Schedule model to prevent async IO issues

### Integrations Infrastructure
- `IntegrationRegistry` — connection pooling (httpx HTTP/2), health monitoring, rate limiting
- `CredentialVault` — AES-256 encrypted credential storage
- 8 integration types: REST, GraphQL, SOAP, WebSocket, gRPC, Database, FileSystem, MessageQueue
- 2 existing adapters: Claude AI + Google Sheets
- Trigger types: webhook, schedule, manual, event, api

### System Health Check
- `GET /api/v1/system-check/` — 7 checks (DB, Redis, imports, schedules, executions, Celery, data integrity)
- `GET /api/v1/system-check/quick` — unauthenticated ping
- Daily scheduled check at 06:00 UTC with retry-on-failure
