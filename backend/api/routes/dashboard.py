"""Dashboard stats endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

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

    Returns:
        Dashboard stats including:
        - total_workflows: Total number of workflows in organization
        - active_workflows: Number of enabled, published workflows
        - total_executions: Total number of execution instances
        - running_executions: Number of currently running executions
        - completed_executions: Number of completed executions
        - failed_executions: Number of failed executions
    """
    org_id = current_user.org_id

    # Workflow counts
    wf_total = await db.scalar(
        select(func.count(Workflow.id)).where(
            and_(Workflow.organization_id == org_id, Workflow.is_deleted == False)
        )
    )
    wf_active = await db.scalar(
        select(func.count(Workflow.id)).where(
            and_(
                Workflow.organization_id == org_id,
                Workflow.is_deleted == False,
                Workflow.status == "published",
                Workflow.is_enabled == True,
            )
        )
    )

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

    return {
        "total_workflows": wf_total or 0,
        "active_workflows": wf_active or 0,
        "total_executions": total_exec,
        "running_executions": running,
        "completed_executions": completed,
        "failed_executions": failed,
    }
