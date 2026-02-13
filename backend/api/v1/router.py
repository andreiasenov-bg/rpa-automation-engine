"""API v1 aggregated router.

All v1 endpoints are registered here and mounted under /api/v1 in main.py.
This makes it trivial to add /api/v2 later without touching existing routes.
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
)
from api.routes import integrations as integrations_routes
from api.routes import triggers
from api.routes import notifications
from api.routes import task_types

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
