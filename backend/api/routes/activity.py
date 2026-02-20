"""User activity timeline API.

Aggregates recent actions across the platform into a unified timeline:
- Workflow created/published/archived/deleted
- Execution started/completed/failed
- Agent connected/disconnected
- User login/register
- Credential created/updated
- Schedule created/modified
"""

from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_active_user
from core.security import TokenPayload
from db.models.audit_log import AuditLog

router = APIRouter()


@router.get("")
async def get_activity_timeline(
    days: int = Query(7, ge=1, le=90),
    limit: int = Query(50, ge=1, le=200),
    actor_id: Optional[str] = Query(None),
    action_type: Optional[str] = Query(None),
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a unified activity timeline for the organization.

    Pulls from the audit_logs table, which records all significant actions.
    Supports filtering by actor and action type.
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)

    conditions = [
        AuditLog.organization_id == current_user.org_id,
        AuditLog.created_at >= since,
    ]

    if actor_id:
        conditions.append(AuditLog.user_id == actor_id)
    if action_type:
        conditions.append(AuditLog.action == action_type)

    query = (
        select(AuditLog)
        .where(and_(*conditions))
        .order_by(desc(AuditLog.created_at))
        .limit(limit)
    )

    rows = (await db.execute(query)).scalars().all()

    # Map actions to user-friendly timeline entries
    activities = []
    for log in rows:
        activities.append({
            "id": log.id,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "actor_id": log.user_id,
            "actor_name": _get_actor_display(log),
            "description": _format_description(log),
            "icon": _action_icon(log.action),
            "color": _action_color(log.action),
            "timestamp": log.created_at.isoformat() if log.created_at else None,
            "metadata": log.details if hasattr(log, 'details') else None,
        })

    # Group by date for frontend rendering
    grouped: dict[str, list] = {}
    for activity in activities:
        if activity["timestamp"]:
            date_key = activity["timestamp"][:10]  # YYYY-MM-DD
        else:
            date_key = "unknown"
        grouped.setdefault(date_key, []).append(activity)

    return {
        "activities": activities,
        "grouped": grouped,
        "total": len(activities),
        "period_days": days,
    }


@router.get("/summary")
async def get_activity_summary(
    days: int = Query(7, ge=1, le=90),
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a summary of activity counts by action type."""
    since = datetime.now(timezone.utc) - timedelta(days=days)

    from sqlalchemy import func

    query = (
        select(AuditLog.action, func.count().label("count"))
        .where(
            and_(
                AuditLog.organization_id == current_user.org_id,
                AuditLog.created_at >= since,
            )
        )
        .group_by(AuditLog.action)
        .order_by(desc("count"))
    )

    rows = (await db.execute(query)).all()

    return {
        "summary": [{"action": r[0], "count": r[1]} for r in rows],
        "period_days": days,
        "total": sum(r[1] for r in rows),
    }


# ─── Helpers ───

def _get_actor_display(log: AuditLog) -> str:
    """Get display name for the actor."""
    if hasattr(log, 'details') and log.details and isinstance(log.details, dict):
        return log.details.get('actor_name', log.user_id or 'System')
    return log.user_id or 'System'


def _format_description(log: AuditLog) -> str:
    """Generate a human-readable description of the action."""
    action_descriptions = {
        'workflow.created': 'Created a new workflow',
        'workflow.updated': 'Updated workflow',
        'workflow.published': 'Published workflow',
        'workflow.archived': 'Archived workflow',
        'workflow.deleted': 'Deleted workflow',
        'execution.started': 'Started execution',
        'execution.completed': 'Execution completed',
        'execution.failed': 'Execution failed',
        'execution.cancelled': 'Cancelled execution',
        'agent.registered': 'Registered a new agent',
        'agent.connected': 'Agent connected',
        'agent.disconnected': 'Agent disconnected',
        'user.login': 'Logged in',
        'user.register': 'Registered a new account',
        'credential.created': 'Created a new credential',
        'credential.updated': 'Updated credential',
        'schedule.created': 'Created a new schedule',
        'schedule.updated': 'Updated schedule',
        'role.created': 'Created a new role',
        'role.deleted': 'Deleted role',
    }
    return action_descriptions.get(log.action, log.action)


def _action_icon(action: str) -> str:
    """Map action to a Lucide icon name for frontend rendering."""
    icons = {
        'workflow.created': 'GitBranch',
        'workflow.updated': 'Edit3',
        'workflow.published': 'Globe',
        'workflow.archived': 'Archive',
        'workflow.deleted': 'Trash2',
        'execution.started': 'Play',
        'execution.completed': 'CheckCircle2',
        'execution.failed': 'XCircle',
        'execution.cancelled': 'Ban',
        'agent.registered': 'Server',
        'agent.connected': 'Wifi',
        'agent.disconnected': 'WifiOff',
        'user.login': 'LogIn',
        'user.register': 'UserPlus',
        'credential.created': 'Key',
        'schedule.created': 'CalendarClock',
    }
    return icons.get(action, 'Activity')


def _action_color(action: str) -> str:
    """Map action to a color class for frontend styling."""
    if 'completed' in action or 'published' in action or 'connected' in action:
        return 'emerald'
    if 'failed' in action or 'deleted' in action or 'disconnected' in action:
        return 'red'
    if 'started' in action or 'created' in action or 'registered' in action:
        return 'blue'
    if 'cancelled' in action or 'archived' in action:
        return 'amber'
    return 'slate'
