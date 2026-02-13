# RPA Automation Engine — API Reference

Base URL: `/api/v1`
Authentication: JWT Bearer token (`Authorization: Bearer <token>`)
Content-Type: `application/json`

## Authentication

| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/register` | Register user + organization |
| POST | `/auth/login` | Login, returns access + refresh tokens |
| POST | `/auth/refresh` | Refresh access token |
| GET | `/auth/me` | Current user profile |

### Login Example
```bash
curl -X POST /api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "secret"}'
```
Response:
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

## Workflows

| Method | Path | Description |
|--------|------|-------------|
| GET | `/workflows/` | List workflows (paginated) |
| POST | `/workflows/` | Create workflow |
| GET | `/workflows/{id}` | Get workflow details |
| PUT | `/workflows/{id}` | Update workflow |
| DELETE | `/workflows/{id}` | Soft-delete workflow |
| POST | `/workflows/{id}/publish` | Publish (make executable) |
| POST | `/workflows/{id}/archive` | Archive (disable) |
| POST | `/workflows/{id}/execute` | Trigger execution (202) |
| GET | `/workflows/{id}/history` | Audit history |
| POST | `/workflows/{id}/clone` | Clone workflow |

## Executions

| Method | Path | Description |
|--------|------|-------------|
| GET | `/executions/` | List executions (paginated, filterable) |
| GET | `/executions/{id}` | Execution details |
| GET | `/executions/{id}/logs` | Execution log entries |
| POST | `/executions/{id}/retry` | Retry failed execution (202) |
| POST | `/executions/{id}/cancel` | Cancel running execution |

## Agents

| Method | Path | Description |
|--------|------|-------------|
| GET | `/agents` | List agents |
| POST | `/agents` | Register new agent |
| GET | `/agents/stats` | Agent statistics |
| GET | `/agents/{id}` | Agent details |
| PUT | `/agents/{id}` | Update agent |
| DELETE | `/agents/{id}` | Soft-delete agent |
| POST | `/agents/{id}/heartbeat` | Update heartbeat |
| POST | `/agents/{id}/rotate-token` | Rotate auth token |

## Credentials

| Method | Path | Description |
|--------|------|-------------|
| GET | `/credentials/` | List credentials (values excluded) |
| POST | `/credentials/` | Create credential (AES-256 encrypted) |
| GET | `/credentials/{id}` | Get credential (optional decrypted value) |
| PUT | `/credentials/{id}` | Update credential |
| DELETE | `/credentials/{id}` | Soft-delete credential |

## Schedules

| Method | Path | Description |
|--------|------|-------------|
| GET | `/schedules/` | List schedules |
| POST | `/schedules/` | Create schedule (cron expression) |
| GET | `/schedules/{id}` | Schedule details |
| PUT | `/schedules/{id}` | Update schedule |
| DELETE | `/schedules/{id}` | Soft-delete schedule |
| POST | `/schedules/{id}/toggle` | Enable/disable |

## Analytics

| Method | Path | Description |
|--------|------|-------------|
| GET | `/analytics/overview` | Execution statistics overview |
| GET | `/analytics/executions/timeline` | Execution counts by time interval |
| GET | `/analytics/workflows/performance` | Per-workflow performance metrics |

## Dashboard

| Method | Path | Description |
|--------|------|-------------|
| GET | `/dashboard/stats` | Dashboard statistics |

## AI (Claude Integration)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/ai/status` | AI connection status |
| GET | `/ai/task-types` | Available AI task types |
| POST | `/ai/ask` | Send prompt to Claude |
| POST | `/ai/analyze` | Analyze data |
| POST | `/ai/decide` | Decision based on context |
| POST | `/ai/classify` | Text classification |
| POST | `/ai/extract` | Structured data extraction |
| POST | `/ai/summarize` | Text summarization |
| POST | `/ai/conversation/{id}/clear` | Clear conversation |
| GET | `/ai/usage` | Token usage statistics |

## Integrations

| Method | Path | Description |
|--------|------|-------------|
| GET | `/integrations/dashboard` | All integrations health overview |
| GET | `/integrations/` | List integrations |
| POST | `/integrations/` | Register integration |
| GET | `/integrations/{id}` | Integration details |
| PUT | `/integrations/{id}` | Update integration |
| DELETE | `/integrations/{id}` | Remove integration |
| POST | `/integrations/{id}/toggle` | Enable/disable |
| POST | `/integrations/{id}/health-check` | Manual health check |
| GET | `/integrations/{id}/health-history` | Health check history |
| POST | `/integrations/{id}/test` | Test request |
| POST | `/integrations/health-check-all` | Check all integrations |
| GET | `/integrations/alerts/active` | Active alerts |

## Triggers

| Method | Path | Description |
|--------|------|-------------|
| GET | `/triggers/` | List triggers |
| POST | `/triggers/` | Create trigger |
| GET | `/triggers/{id}` | Trigger details |
| PUT | `/triggers/{id}` | Update trigger |
| DELETE | `/triggers/{id}` | Delete trigger |
| POST | `/triggers/{id}/toggle` | Toggle enabled |
| GET | `/triggers/types` | Supported trigger types |
| GET | `/triggers/manager/status` | Trigger manager status |
| POST | `/triggers/test` | Test trigger config |
| POST | `/triggers/{id}/fire` | Manually fire trigger |
| POST | `/triggers/webhooks/{path}` | Receive webhook (no auth) |

## Admin

| Method | Path | Description |
|--------|------|-------------|
| GET | `/admin/overview` | Organization overview |
| PUT | `/admin/organization` | Update organization settings |
| GET | `/admin/roles` | List roles |
| POST | `/admin/roles` | Create role |
| PUT | `/admin/roles/{id}` | Update role |
| DELETE | `/admin/roles/{id}` | Delete role |
| GET | `/admin/permissions` | List permissions |

## Templates

| Method | Path | Description |
|--------|------|-------------|
| GET | `/templates` | List templates |
| GET | `/templates/categories` | Template categories |
| GET | `/templates/{id}` | Template details |
| POST | `/templates/{id}/instantiate` | Create workflow from template |

## Bulk Operations

| Method | Path | Description |
|--------|------|-------------|
| POST | `/bulk/workflows/publish` | Publish multiple workflows |
| POST | `/bulk/workflows/archive` | Archive multiple workflows |
| POST | `/bulk/workflows/delete` | Delete multiple workflows |
| POST | `/bulk/executions/cancel` | Cancel multiple executions |
| POST | `/bulk/executions/retry` | Retry multiple executions |

## Data Export

| Method | Path | Description |
|--------|------|-------------|
| GET | `/export/executions` | Export execution history (CSV/JSON) |
| GET | `/export/audit-logs` | Export audit logs (CSV/JSON) |
| GET | `/export/analytics` | Export analytics summary (CSV/JSON) |

## Other Endpoints

### Notifications
`GET /notifications/status`, `POST /notifications/send`, `POST /notifications/channels/configure`, `POST /notifications/test`

### Audit Logs
`GET /audit-logs`, `GET /audit-logs/stats`, `GET /audit-logs/resource-types`, `GET /audit-logs/actions`

### Task Types
`GET /task-types/`, `GET /task-types/{type}`

### Plugins
`GET /plugins`, `GET /plugins/{name}`, `PUT /plugins/{name}`, `POST /plugins/reload`

### Activity Timeline
`GET /activity`, `GET /activity/summary`

### User Roles
`GET /user-roles/{user_id}/roles`, `POST /user-roles/{user_id}/roles`, `DELETE /user-roles/{user_id}/roles/{role_id}`, `POST /user-roles/bulk-assign`, `GET /user-roles/by-role/{role_id}`

### Workflow Variables
`GET /workflow-variables/{id}/variables`, `PUT /workflow-variables/{id}/variables`, `PUT /workflow-variables/{id}/variables/mappings`, `POST /workflow-variables/{id}/variables/validate`

### Agent Tasks
`POST /agent-tasks/claim`, `POST /agent-tasks/{execution_id}/result`, `GET /agent-tasks/queue`, `GET /agent-tasks/assigned/{agent_id}`

## WebSocket

Connect to `ws://host/ws?token=<jwt>` for real-time events:

| Event | Description |
|-------|-------------|
| `execution.status_changed` | Execution status update |
| `execution.log` | New log entry |
| `notification` | System notification |
| `trigger.fired` | Trigger activated |

## Health & Metrics

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/health/` | No | API info |
| GET | `/api/health/health` | No | Health check |
| GET | `/api/health/status` | No | Detailed system status |
| GET | `/metrics` | No | Prometheus metrics |

**Total: 127 HTTP endpoints + 1 WebSocket**

Interactive docs available at `GET /docs` (Swagger UI) and `GET /redoc` (ReDoc).
