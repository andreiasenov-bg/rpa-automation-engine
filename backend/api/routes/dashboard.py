"""Dashboard stats and recent executions endpoint."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc, case, text

from core.security import TokenPayload
from app.dependencies import get_db, get_current_active_user
from db.models.workflow import Workflow
from db.models.execution import Execution

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard/stats")
async def get_dashboard_stats(
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get dashboard statistics for the current user's organization.
    """
    org_id = current_user.org_id

    # Workflow counts
    wf_total = await db.scalar(
        select(func.count(Workflow.id)).where(
            and_(Workflow.organization_id == org_id, Workflow.is_deleted == False)
        )
    ) or 0
    wf_active = await db.scalar(
        select(func.count(Workflow.id)).where(
            and_(
                Workflow.organization_id == org_id,
                Workflow.is_deleted == False,
                Workflow.status == "published",
                Workflow.is_enabled == True,
            )
        )
    ) or 0

    # Execution counts
    exec_base = and_(Execution.organization_id == org_id, Execution.is_deleted == False)

    total_exec = await db.scalar(select(func.count(Execution.id)).where(exec_base)) or 0
    running = await db.scalar(
        select(func.count(Execution.id)).where(and_(exec_base, Execution.status == "running"))
    ) or 0
    completed = await db.scalar(
        select(func.count(Execution.id)).where(and_(exec_base, Execution.status == "completed"))
    ) or 0
    failed = await db.scalar(
        select(func.count(Execution.id)).where(and_(exec_base, Execution.status == "failed"))
    ) or 0
    pending = await db.scalar(
        select(func.count(Execution.id)).where(and_(exec_base, Execution.status == "pending"))
    ) or 0

    # Average duration (completed only)
    avg_dur = await db.scalar(
        select(func.avg(Execution.duration_ms)).where(
            and_(exec_base, Execution.status == "completed", Execution.duration_ms.isnot(None))
        )
    )

    # Success rate
    finished = completed + failed
    success_rate = round((completed / finished * 100), 1) if finished > 0 else 100.0

    # Active schedules count
    schedules_active = 0
    try:
        from db.models.schedule import Schedule
        schedules_active = await db.scalar(
            select(func.count(Schedule.id)).where(
                and_(Schedule.organization_id == org_id, Schedule.is_deleted == False, Schedule.is_enabled == True)
            )
        ) or 0
    except Exception:
        pass

    return {
        "total_workflows": wf_total,
        "active_workflows": wf_active,
        "total_executions": total_exec,
        "running_executions": running,
        "completed_executions": completed,
        "failed_executions": failed,
        "pending_executions": pending,
        "avg_duration_ms": int(avg_dur) if avg_dur else 0,
        "success_rate": success_rate,
        "agents_online": 1,  # Default single local agent
        "agents_total": 1,
        "schedules_active": schedules_active,
    }


@router.get("/dashboard/recent-executions")
async def get_recent_executions(
    limit: int = Query(10, ge=1, le=50),
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get most recent executions with workflow names."""
    org_id = current_user.org_id

    query = (
        select(
            Execution.id,
            Execution.workflow_id,
            Execution.status,
            Execution.started_at,
            Execution.completed_at,
            Execution.duration_ms,
            Execution.trigger_type,
            Execution.error_message,
            Workflow.name.label("workflow_name"),
        )
        .outerjoin(Workflow, Execution.workflow_id == Workflow.id)
        .where(and_(Execution.organization_id == org_id, Execution.is_deleted == False))
        .order_by(desc(Execution.created_at))
        .limit(limit)
    )

    result = await db.execute(query)
    rows = result.all()

    executions = []
    for row in rows:
        executions.append({
            "id": row.id,
            "workflow_id": row.workflow_id,
            "workflow_name": row.workflow_name or "Unknown Workflow",
            "status": row.status,
            "started_at": row.started_at.isoformat() if row.started_at else None,
            "completed_at": row.completed_at.isoformat() if row.completed_at else None,
            "duration_ms": row.duration_ms,
            "trigger_type": row.trigger_type or "manual",
            "error_message": row.error_message,
        })

    return {"executions": executions}
