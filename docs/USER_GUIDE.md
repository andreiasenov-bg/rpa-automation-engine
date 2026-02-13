# RPA Automation Engine — User Guide

## Getting Started

### First Login

1. Open the application at `http://localhost:3000` (or your production URL)
2. Register a new account with your email, name, and organization name
3. Login with your credentials

The first registered user automatically gets the **Admin** role with full access.

### Dashboard

The dashboard shows an overview of your RPA platform:

- **Stat Cards** — Total workflows, executions, completed, and failed counts
- **Quick Actions** — Shortcuts to create workflows, view executions, and manage resources
- **Success Rate Ring** — Visual indicator of execution success rate
- **System Health** — WebSocket connection, agent status, queue depth, active schedules
- **Recent Executions** — Latest execution results with status indicators
- **Analytics** — Execution timeline chart and workflow performance

## Workflows

### Creating a Workflow

1. Navigate to **Workflows** in the sidebar
2. Click **+ New Workflow**
3. Enter a name and description
4. You'll be taken to the visual workflow editor

### Workflow Editor

The editor provides a drag-and-drop canvas powered by React Flow:

- **Step Palette** — Click "Add Step" to open the palette. Available step types include Web Scraping, API Request, Database, Email, File Operations, Custom Script, Form Fill, PDF Processing, Data Transform, Conditional, Loop, and Delay.
- **Adding Steps** — Drag a step type from the palette onto the canvas, or click to add at default position
- **Connecting Steps** — Drag from an output handle to an input handle to create execution flow
- **Configuring Steps** — Click a step node to configure its parameters
- **Variables** — Click "Variables" to define workflow input/output variables

### Publishing

Workflows must be published before they can be executed:

1. Build your workflow in the editor
2. Click **Save** to save your draft
3. Click **Publish** to make it executable

### Executing a Workflow

- **Manual**: Go to the workflow detail page and click **Execute** (or use the API)
- **Scheduled**: Create a schedule with a cron expression
- **Triggered**: Set up triggers (webhook, file watch, etc.)

## Executions

### Execution List

Navigate to **Executions** to see all workflow runs:

- Filter by status: pending, running, completed, failed, cancelled
- Each row shows the execution ID, trigger type, duration, retry count, and status
- Click the detail icon to view full execution details

### Execution Detail

The detail page shows:

- **Status Badge** — Current execution state
- **Step Timeline** — Each step's status with timing information
- **Live Logs** — Real-time log viewer (via WebSocket when running)
- **Metadata** — Execution ID, trigger type, agent, timestamps

### Retry and Cancel

- **Retry** — Available for failed or cancelled executions. Creates a new execution with the same parameters.
- **Cancel** — Available for running or pending executions. Sends a cancellation signal to the agent.

## Agents

Agents are distributed workers that execute workflow steps:

- **Register** — Create agents from the Agents page
- **Status** — Active, Idle, Error, or Offline
- **Heartbeat** — Agents send periodic heartbeats. Agents without recent heartbeats are marked offline.
- **Token Rotation** — Rotate an agent's authentication token for security

## Credentials

The credential vault stores sensitive data (API keys, passwords, certificates) with AES-256 encryption:

1. Navigate to **Credentials**
2. Click **+ Add Credential**
3. Enter a name, type (api_key, password, oauth, certificate), and the secret value
4. The value is encrypted at rest and only decrypted when used by a workflow step

## Schedules

Create cron-based schedules to run workflows automatically:

1. Navigate to **Schedules**
2. Click **+ New Schedule**
3. Select a workflow, enter a cron expression (e.g. `0 9 * * 1-5` for weekdays at 9am)
4. Optionally set a timezone
5. Toggle enable/disable as needed

## Templates

Pre-built workflow templates are available to get started quickly:

1. Navigate to **Templates**
2. Browse by category or search
3. Click **Use Template** to create a workflow from the template
4. Customize the generated workflow as needed

## Admin Panel

Available to users with the Admin role:

### Overview
Organization stats: user count, workflows, agents, credentials, execution metrics.

### Roles
- View, create, and manage roles
- Assign permissions to roles
- The built-in **Admin** role cannot be deleted

### Permissions
Permission matrix showing which roles have which capabilities.

### Users
Manage organization users, assign/remove roles.

## Settings

Personal settings available to all users:

- **Profile** — Update name and email
- **Password** — Change password
- **Theme** — Toggle dark/light mode
- **Language** — Switch between English and Bulgarian
- **Notifications** — Configure notification preferences

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+K` / `Cmd+K` | Open global search |
| `Ctrl+S` / `Cmd+S` | Save workflow (in editor) |

## Task Types Reference

| Type | Description |
|------|-------------|
| Web Scraping | Extract data from websites using CSS selectors |
| API Request | Make HTTP requests to external APIs |
| Database | Execute SQL queries (PostgreSQL, MySQL, SQLite) |
| Email | Send/receive emails via SMTP/IMAP |
| File Operations | Read, write, copy, move files |
| Custom Script | Run Python/JavaScript code |
| Form Fill | Fill web forms via Selenium |
| PDF Processing | Extract text, merge, split PDFs |
| Data Transform | Map, filter, transform data structures |
| Conditional | Branch execution based on conditions |
| Loop | Iterate over collections |
| Delay | Wait for a specified duration |
| AI (Claude) | Use Claude AI for text analysis and generation |

## Notifications

Configure alerts for important events:

- **Email** — SMTP-based email notifications
- **Slack** — Webhook or bot token integration
- **Webhook** — Send HTTP POST to any endpoint
- **In-App** — Bell icon notifications in the header

Notification rules can be set for: execution failures, agent disconnects, schedule misfires, and security events.
