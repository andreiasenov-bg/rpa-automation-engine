"""API v1 aggregated router.

All v1 endpoints are registered here and mounted under /api/v1 in main.py.
This makes it trivial to add /api/v2 later without touching existing routes.

Includes: Storage routes for workflow file management (results, icons, docs).
"""

from fastapi import APIRouter

from api.routes import (
    health,
    auth,
    users,
    workflows,
    executions,
    agents,
    credentials,
    schedules,
    analytics,
    ai,
    dashboard,
)
from api.routes import admin
from api.routes import audit
from api.routes import templates
from api.routes import plugins
from api.routes import export
from api.routes import bulk
from api.routes import agent_tasks
from api.routes import activity
from api.routes import user_roles
from api.routes import workflow_variables
from api.routes import chat
from api.routes import storage
from api.routes import integrations as integrations_routes
from api.routes import triggers
from api.routes import notifications
from api.routes import task_types
from api.routes import system_check

api_v1_router = APIRouter()

# Health (no auth required)
api_v1_router.include_router(
    health.router,
    tags=["Health"],
)

# Authentication
api_v1_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentication"],
)

# Users
api_v1_router.include_router(
    users.router,
    prefix="/users",
    tags=["Users"],
)

# Workflows
api_v1_router.include_router(
    workflows.router,
    prefix="/workflows",
    tags=["Workflows"],
)

# Executions
api_v1_router.include_router(
    executions.router,
    prefix="/executions",
    tags=["Executions"],
)

# Agents
api_v1_router.include_router(
    agents.router,
    prefix="/agents",
    tags=["Agents"],
)

# Credentials vault
api_v1_router.include_router(
    credentials.router,
    prefix="/credentials",
    tags=["Credentials"],
)

# Schedules
api_v1_router.include_router(
    schedules.router,
    prefix="/schedules",
    tags=["Schedules"],
)

# Analytics
api_v1_router.include_router(
    analytics.router,
    prefix="/analytics",
    tags=["Analytics"],
)

# Dashboard
api_v1_router.include_router(
    dashboard.router,
    tags=["Dashboard"],
)

# AI — Claude Integration
api_v1_router.include_router(
    ai.router,
    prefix="/ai",
    tags=["AI - Claude Integration"],
)

# External Integrations
api_v1_router.include_router(
    integrations_routes.router,
    prefix="/integrations",
    tags=["External Integrations"],
)

# Triggers
api_v1_router.include_router(
    triggers.router,
    prefix="/triggers",
    tags=["Triggers"],
)

# Notifications
api_v1_router.include_router(
    notifications.router,
    prefix="/notifications",
    tags=["Notifications"],
)

# Task Types (for workflow editor)
api_v1_router.include_router(
    task_types.router,
    prefix="/task-types",
    tags=["Task Types"],
)

# Audit Logs
api_v1_router.include_router(
    audit.router,
    prefix="/audit-logs",
    tags=["Audit Logs"],
)

# Workflow Templates
api_v1_router.include_router(
    templates.router,
    prefix="/templates",
    tags=["Workflow Templates"],
)

# Admin Panel
api_v1_router.include_router(
    admin.router,
    prefix="/admin",
    tags=["Admin Panel"],
)

# Plugins
api_v1_router.include_router(
    plugins.router,
    prefix="/plugins",
    tags=["Plugins"],
)

# Data Export
api_v1_router.include_router(
    export.router,
    tags=["Data Export"],
)

# Bulk Operations
api_v1_router.include_router(
    bulk.router,
    tags=["Bulk Operations"],
)

# Agent Task Assignment
api_v1_router.include_router(
    agent_tasks.router,
    prefix="/agent-tasks",
    tags=["Agent Tasks"],
)

# Activity Timeline
api_v1_router.include_router(
    activity.router,
    prefix="/activity",
    tags=["Activity Timeline"],
)

# User-Role Assignment
api_v1_router.include_router(
    user_roles.router,
    prefix="/user-roles",
    tags=["User Roles"],
)

# Workflow Variables
api_v1_router.include_router(
    workflow_variables.router,
    prefix="/workflow-variables",
    tags=["Workflow Variables"],
)

# Chat Assistant
api_v1_router.include_router(
    chat.router,
    prefix="/chat",
    tags=["Chat Assistant"],
)

# Workflow Storage (files, results, icons)
api_v1_router.include_router(
    storage.router,
    prefix="/storage",
    tags=["Workflow Storage"],
)

# System Health Check (post-deploy + daily)
api_v1_router.include_router(system_check.router)
