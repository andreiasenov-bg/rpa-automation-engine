"""Data export endpoints for executions and analytics.

Supports CSV and JSON export formats with streaming responses
for large datasets.
"""

import csv
import io
import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_active_user, get_db
from db.models.execution import Execution
from db.models.workflow import Workflow
from db.models.audit_log import AuditLog
from db.models.user import User

router = APIRouter()


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


# ─── Execution Export ───

@router.get("/export/executions")
async def export_executions(
    format: str = Query("csv", regex="^(csv|json)$"),
    workflow_id: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = Query(10000, le=50000),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    """Export execution history as CSV or JSON."""
    query = (
        select(
            Execution.id,
            Execution.workflow_id,
            Workflow.name.label("workflow_name"),
            Execution.status,
            Execution.started_at,
            Execution.completed_at,
            Execution.error_message,
            Execution.created_at,
        )
        .join(Workflow, Execution.workflow_id == Workflow.id, isouter=True)
        .where(Execution.organization_id == current_user.org_id)
        .where(Execution.deleted_at.is_(None))
        .order_by(desc(Execution.created_at))
        .limit(limit)
    )

    if workflow_id:
        query = query.where(Execution.workflow_id == workflow_id)
    if status:
        query = query.where(Execution.status == status)
    if date_from:
        query = query.where(Execution.created_at >= date_from)
    if date_to:
        query = query.where(Execution.created_at <= date_to)

    result = await db.execute(query)
    rows = result.all()

    if format == "json":
        data = [
            {
                "id": r.id,
                "workflow_id": r.workflow_id,
                "workflow_name": r.workflow_name,
                "status": r.status,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                "error_message": r.error_message,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
        content = json.dumps({"executions": data, "total": len(data)}, indent=2)
        return StreamingResponse(
            iter([content]),
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="executions_{_timestamp()}.json"'
            },
        )

    # CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "Workflow ID", "Workflow Name", "Status",
        "Started At", "Completed At", "Error", "Created At",
    ])
    for r in rows:
        writer.writerow([
            r.id,
            r.workflow_id,
            r.workflow_name,
            r.status,
            r.started_at.isoformat() if r.started_at else "",
            r.completed_at.isoformat() if r.completed_at else "",
            r.error_message or "",
            r.created_at.isoformat() if r.created_at else "",
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="executions_{_timestamp()}.csv"'
        },
    )


# ─── Audit Log Export ───

@router.get("/export/audit-logs")
async def export_audit_logs(
    format: str = Query("csv", regex="^(csv|json)$"),
    resource_type: Optional[str] = None,
    action: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = Query(10000, le=50000),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    """Export audit logs as CSV or JSON."""
    query = (
        select(
            AuditLog.id,
            AuditLog.action,
            AuditLog.resource_type,
            AuditLog.resource_id,
            AuditLog.user_id,
            User.email.label("user_email"),
            AuditLog.ip_address,
            AuditLog.created_at,
        )
        .join(User, AuditLog.user_id == User.id, isouter=True)
        .where(AuditLog.organization_id == current_user.org_id)
        .order_by(desc(AuditLog.created_at))
        .limit(limit)
    )

    if resource_type:
        query = query.where(AuditLog.resource_type == resource_type)
    if action:
        query = query.where(AuditLog.action == action)
    if date_from:
        query = query.where(AuditLog.created_at >= date_from)
    if date_to:
        query = query.where(AuditLog.created_at <= date_to)

    result = await db.execute(query)
    rows = result.all()

    if format == "json":
        data = [
            {
                "id": r.id,
                "action": r.action,
                "resource_type": r.resource_type,
                "resource_id": r.resource_id,
                "user_id": r.user_id,
                "user_email": r.user_email,
                "ip_address": r.ip_address,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
        content = json.dumps({"audit_logs": data, "total": len(data)}, indent=2)
        return StreamingResponse(
            iter([content]),
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="audit_logs_{_timestamp()}.json"'
            },
        )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "Action", "Resource Type", "Resource ID",
        "User ID", "User Email", "IP Address", "Created At",
    ])
    for r in rows:
        writer.writerow([
            r.id, r.action, r.resource_type, r.resource_id,
            r.user_id, r.user_email or "", r.ip_address or "",
            r.created_at.isoformat() if r.created_at else "",
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="audit_logs_{_timestamp()}.csv"'
        },
    )


# ─── Analytics Export ───

@router.get("/export/analytics")
async def export_analytics(
    format: str = Query("csv", regex="^(csv|json)$"),
    period_days: int = Query(30, le=365),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    """Export analytics summary as CSV or JSON."""
    from sqlalchemy import case

    # Workflow performance metrics
    query = (
        select(
            Workflow.id,
            Workflow.name,
            Workflow.status,
            func.count(Execution.id).label("total_executions"),
            func.sum(case((Execution.status == "completed", 1), else_=0)).label("completed"),
            func.sum(case((Execution.status == "failed", 1), else_=0)).label("failed"),
            func.sum(case((Execution.status == "running", 1), else_=0)).label("running"),
        )
        .join(Execution, Workflow.id == Execution.workflow_id, isouter=True)
        .where(Workflow.organization_id == current_user.org_id)
        .where(Workflow.deleted_at.is_(None))
        .group_by(Workflow.id, Workflow.name, Workflow.status)
        .order_by(desc(func.count(Execution.id)))
    )

    result = await db.execute(query)
    rows = result.all()

    if format == "json":
        data = [
            {
                "workflow_id": r.id,
                "workflow_name": r.name,
                "workflow_status": r.status,
                "total_executions": r.total_executions,
                "completed": r.completed,
                "failed": r.failed,
                "running": r.running,
                "success_rate": round(r.completed / r.total_executions * 100, 1) if r.total_executions else 0,
            }
            for r in rows
        ]
        content = json.dumps({
            "analytics": data,
            "total_workflows": len(data),
            "period_days": period_days,
        }, indent=2)
        return StreamingResponse(
            iter([content]),
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="analytics_{_timestamp()}.json"'
            },
        )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Workflow ID", "Workflow Name", "Status",
        "Total Executions", "Completed", "Failed", "Running", "Success Rate %",
    ])
    for r in rows:
        rate = round(r.completed / r.total_executions * 100, 1) if r.total_executions else 0
        writer.writerow([
            r.id, r.name, r.status,
            r.total_executions, r.completed, r.failed, r.running, rate,
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="analytics_{_timestamp()}.csv"'
        },
    )
