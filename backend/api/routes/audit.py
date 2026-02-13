"""Audit Log API routes.

Provides read-only access to the organization's audit trail.
Supports filtering by resource_type, action, user, date range, and search.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, desc, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_active_user
from core.security import TokenPayload
from db.models.audit_log import AuditLog
from db.models.user import User

router = APIRouter()


@router.get("")
async def list_audit_logs(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    resource_type: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    resource_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None, description="ISO date: 2026-01-01"),
    date_to: Optional[str] = Query(None, description="ISO date: 2026-12-31"),
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List audit logs with filtering and pagination."""
    conditions = [
        AuditLog.organization_id == current_user.org,
        AuditLog.is_deleted == False,
    ]

    if resource_type:
        conditions.append(AuditLog.resource_type == resource_type)
    if action:
        conditions.append(AuditLog.action == action)
    if user_id:
        conditions.append(AuditLog.user_id == user_id)
    if resource_id:
        conditions.append(AuditLog.resource_id == resource_id)
    if search:
        search_pattern = f"%{search}%"
        conditions.append(
            or_(
                AuditLog.resource_type.ilike(search_pattern),
                AuditLog.resource_id.ilike(search_pattern),
                AuditLog.action.ilike(search_pattern),
            )
        )
    if date_from:
        try:
            dt = datetime.fromisoformat(date_from)
            conditions.append(AuditLog.created_at >= dt)
        except ValueError:
            pass
    if date_to:
        try:
            dt = datetime.fromisoformat(date_to)
            conditions.append(AuditLog.created_at <= dt)
        except ValueError:
            pass

    where_clause = and_(*conditions)

    # Count
    count_q = select(func.count()).select_from(AuditLog).where(where_clause)
    total = (await db.execute(count_q)).scalar() or 0

    # Fetch with user join
    offset = (page - 1) * per_page
    query = (
        select(AuditLog, User.email)
        .outerjoin(User, AuditLog.user_id == User.id)
        .where(where_clause)
        .order_by(desc(AuditLog.created_at))
        .offset(offset)
        .limit(per_page)
    )
    rows = (await db.execute(query)).all()

    logs = []
    for row in rows:
        log = row[0]
        user_email = row[1]
        logs.append({
            "id": log.id,
            "user_id": log.user_id,
            "user_email": user_email,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "action": log.action,
            "old_values": log.old_values,
            "new_values": log.new_values,
            "ip_address": log.ip_address,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        })

    return {"audit_logs": logs, "total": total, "page": page, "per_page": per_page}


@router.get("/stats")
async def audit_stats(
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get audit log statistics (action breakdown, resource type breakdown)."""
    base = and_(
        AuditLog.organization_id == current_user.org,
        AuditLog.is_deleted == False,
    )

    # By action
    action_q = (
        select(AuditLog.action, func.count())
        .where(base)
        .group_by(AuditLog.action)
    )
    action_rows = (await db.execute(action_q)).all()
    by_action = {row[0]: row[1] for row in action_rows}

    # By resource type
    resource_q = (
        select(AuditLog.resource_type, func.count())
        .where(base)
        .group_by(AuditLog.resource_type)
    )
    resource_rows = (await db.execute(resource_q)).all()
    by_resource = {row[0]: row[1] for row in resource_rows}

    # Total
    total = sum(by_action.values())

    return {
        "total": total,
        "by_action": by_action,
        "by_resource_type": by_resource,
    }


@router.get("/resource-types")
async def audit_resource_types(
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get distinct resource types for filter dropdown."""
    q = (
        select(AuditLog.resource_type)
        .where(
            AuditLog.organization_id == current_user.org,
            AuditLog.is_deleted == False,
        )
        .distinct()
    )
    rows = (await db.execute(q)).all()
    return {"resource_types": [r[0] for r in rows]}


@router.get("/actions")
async def audit_actions(
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get distinct actions for filter dropdown."""
    q = (
        select(AuditLog.action)
        .where(
            AuditLog.organization_id == current_user.org,
            AuditLog.is_deleted == False,
        )
        .distinct()
    )
    rows = (await db.execute(q)).all()
    return {"actions": [r[0] for r in rows]}
