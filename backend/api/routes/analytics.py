"""Analytics and reporting endpoints."""

from fastapi import APIRouter, HTTPException, status, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc, case
from typing import Optional
from datetime import datetime, timedelta
import logging

from core.security import TokenPayload
from app.dependencies import get_db, get_current_active_user
from core.utils import utc_now
from db.models.execution import Execution
from db.models.workflow import Workflow

logger = logging.getLogger(__name__)

router = APIRouter(tags=["analytics"])


@router.get("/overview", response_model=dict)
async def get_execution_overview(
    days: int = Query(7, ge=1, le=90, description="Number of past days to analyze"),
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get execution statistics overview.

    Returns aggregated metrics for workflow executions within the specified time period.

    Args:
        days: Number of past days to include in analysis (default 7)
        current_user: Current authenticated user
        db: Database session

    Returns:
        Execution stats including:
        - total_executions: Total number of executions
        - successful_executions: Number of successful executions
        - failed_executions: Number of failed executions
        - average_duration_ms: Average execution duration
        - success_rate: Percentage of successful executions
    """
    org_id = current_user.org_id
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    # Base where clause for organization and time period
    base_where = and_(
        Execution.organization_id == org_id,
        Execution.is_deleted == False,
        Execution.created_at >= cutoff_date,
    )

    # Total executions
    total_exec = await db.scalar(
        select(func.count(Execution.id)).where(base_where)
    ) or 0

    # Completed executions
    completed_exec = await db.scalar(
        select(func.count(Execution.id)).where(
            and_(base_where, Execution.status == "completed")
        )
    ) or 0

    # Failed executions
    failed_exec = await db.scalar(
        select(func.count(Execution.id)).where(
            and_(base_where, Execution.status == "failed")
        )
    ) or 0

    # Average duration
    avg_duration = await db.scalar(
        select(func.avg(Execution.duration_ms)).where(base_where)
    )

    # Calculate success rate
    success_rate = 0.0
    if total_exec > 0:
        success_rate = (completed_exec / total_exec) * 100

    return {
        "total_executions": total_exec,
        "successful_executions": completed_exec,
        "failed_executions": failed_exec,
        "average_duration_ms": float(avg_duration) if avg_duration else 0.0,
        "success_rate": round(success_rate, 2),
        "period_days": days,
    }


@router.get("/executions/timeline", response_model=dict)
async def get_execution_timeline(
    days: int = Query(7, ge=1, le=90, description="Number of past days to analyze"),
    interval: str = Query("day", regex="^(hour|day|week)$", description="Time interval for grouping"),
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get execution timeline data.

    Returns execution counts grouped by time interval.

    Args:
        days: Number of past days to include
        interval: Time interval for grouping (hour, day, week)
        current_user: Current authenticated user
        db: Database session

    Returns:
        Timeline data with timestamps and execution counts
    """
    org_id = current_user.org_id
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    # Determine grouping function based on interval
    if interval == "hour":
        from sqlalchemy import func as sql_func
        group_expr = sql_func.date_trunc('hour', Execution.created_at)
    elif interval == "week":
        from sqlalchemy import func as sql_func
        group_expr = sql_func.date_trunc('week', Execution.created_at)
    else:  # day
        from sqlalchemy import func as sql_func
        group_expr = sql_func.date_trunc('day', Execution.created_at)

    base_where = and_(
        Execution.organization_id == org_id,
        Execution.is_deleted == False,
        Execution.created_at >= cutoff_date,
    )

    # Query execution counts grouped by time interval
    stmt = select(
        group_expr.label("timestamp"),
        func.count(Execution.id).label("count"),
    ).where(base_where).group_by(group_expr).order_by(group_expr)

    results = await db.execute(stmt)
    rows = results.all()

    timeline = [
        {
            "timestamp": row[0].isoformat() if row[0] else None,
            "count": row[1],
        }
        for row in rows
    ]

    return {
        "interval": interval,
        "period_days": days,
        "timeline": timeline,
    }


@router.get("/workflows/performance", response_model=dict)
async def get_workflow_performance(
    days: int = Query(7, ge=1, le=90, description="Number of past days to analyze"),
    limit: int = Query(10, ge=1, le=50, description="Maximum workflows to return"),
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get per-workflow performance metrics.

    Returns performance statistics for each workflow.

    Args:
        days: Number of past days to include
        limit: Maximum number of workflows to return
        current_user: Current authenticated user
        db: Database session

    Returns:
        List of workflows with performance metrics:
        - workflow_id, workflow_name
        - execution_count: Total executions
        - success_count: Successful executions
        - failure_count: Failed executions
        - average_duration_ms: Average execution time
        - success_rate: Success percentage
        - last_execution: Timestamp of most recent execution
    """
    org_id = current_user.org_id
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    base_where = and_(
        Execution.organization_id == org_id,
        Execution.is_deleted == False,
        Execution.created_at >= cutoff_date,
    )

    # Get all workflows that have executions in the period
    stmt = select(
        Workflow.id.label("workflow_id"),
        Workflow.name.label("workflow_name"),
        func.count(Execution.id).label("execution_count"),
        func.sum(
            case(
                (Execution.status == "completed", 1),
                else_=0,
            )
        ).label("success_count"),
        func.sum(
            case(
                (Execution.status == "failed", 1),
                else_=0,
            )
        ).label("failure_count"),
        func.avg(Execution.duration_ms).label("avg_duration_ms"),
        func.max(Execution.created_at).label("last_execution"),
    ).select_from(Workflow).join(
        Execution,
        Execution.workflow_id == Workflow.id,
    ).where(base_where).group_by(
        Workflow.id,
        Workflow.name,
    ).order_by(
        desc(func.count(Execution.id))
    ).limit(limit)

    results = await db.execute(stmt)
    rows = results.all()

    workflows = []
    for row in rows:
        execution_count = row[2] or 0
        success_count = row[3] or 0
        failure_count = row[4] or 0

        success_rate = 0.0
        if execution_count > 0:
            success_rate = (success_count / execution_count) * 100

        workflows.append({
            "workflow_id": row[0],
            "workflow_name": row[1],
            "execution_count": execution_count,
            "success_count": success_count,
            "failure_count": failure_count,
            "average_duration_ms": float(row[5]) if row[5] else 0.0,
            "success_rate": round(success_rate, 2),
            "last_execution": row[6].isoformat() if row[6] else None,
        })

    return {
        "period_days": days,
        "limit": limit,
        "workflows": workflows,
    }
