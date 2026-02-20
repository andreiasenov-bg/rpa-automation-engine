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

    # Single optimized query with conditional aggregation
    result = await db.execute(
        select(
            func.count(Execution.id).label("total"),
            func.count(case((Execution.status == "completed", 1))).label("completed"),
            func.count(case((Execution.status == "failed", 1))).label("failed"),
            func.avg(Execution.duration_ms).label("avg_duration"),
        ).where(base_where)
    )
    row = result.one()
    total_exec = row.total or 0
    completed_exec = row.completed or 0
    failed_exec = row.failed or 0
    avg_duration = row.avg_duration

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


# ─── Export & Looker Studio Integration ─── #

from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import csv
import io


class SheetsSyncRequest(BaseModel):
    spreadsheet_id: str
    sheet_name: str = "RPA Analytics"


@router.get("/export/executions")
async def export_executions(
    days: int = Query(30, ge=1, le=365),
    format: str = Query("json", regex="^(json|csv)$"),
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Export flat execution data for Looker Studio / Google Sheets."""
    org_id = current_user.org_id
    cutoff = datetime.utcnow() - timedelta(days=days)

    stmt = (
        select(
            Execution.id,
            Workflow.name.label("workflow_name"),
            Execution.status,
            Execution.started_at,
            Execution.completed_at,
            Execution.duration_ms,
            Execution.trigger_type,
            Execution.error_message,
        )
        .select_from(Execution)
        .outerjoin(Workflow, Execution.workflow_id == Workflow.id)
        .where(
            and_(
                Execution.organization_id == org_id,
                Execution.is_deleted == False,
                Execution.created_at >= cutoff,
            )
        )
        .order_by(desc(Execution.created_at))
    )

    result = await db.execute(stmt)
    rows = result.all()

    columns = [
        "id", "workflow_name", "status", "started_at",
        "completed_at", "duration_ms", "trigger_type", "error_message",
    ]

    data = []
    for row in rows:
        data.append({
            "id": str(row[0]),
            "workflow_name": row[1] or "Unknown",
            "status": row[2] or "",
            "started_at": row[3].isoformat() if row[3] else "",
            "completed_at": row[4].isoformat() if row[4] else "",
            "duration_ms": row[5] or 0,
            "trigger_type": row[6] or "",
            "error_message": row[7] or "",
        })

    if format == "csv":
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=columns)
        writer.writeheader()
        writer.writerows(data)
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=executions_{days}d.csv"},
        )

    return {"columns": columns, "rows": data, "total": len(data), "period_days": days}


@router.get("/export/summary")
async def export_daily_summary(
    days: int = Query(30, ge=1, le=365),
    format: str = Query("json", regex="^(json|csv)$"),
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Export daily aggregated summary — ideal for Looker Studio data source."""
    org_id = current_user.org_id
    cutoff = datetime.utcnow() - timedelta(days=days)

    from sqlalchemy import func as sql_func, cast, Date

    day_expr = sql_func.date_trunc("day", Execution.created_at)

    stmt = (
        select(
            day_expr.label("date"),
            func.count(Execution.id).label("total"),
            func.sum(case((Execution.status == "completed", 1), else_=0)).label("completed"),
            func.sum(case((Execution.status == "failed", 1), else_=0)).label("failed"),
            func.sum(case((Execution.status == "running", 1), else_=0)).label("running"),
            func.avg(Execution.duration_ms).label("avg_duration_ms"),
        )
        .where(
            and_(
                Execution.organization_id == org_id,
                Execution.is_deleted == False,
                Execution.created_at >= cutoff,
            )
        )
        .group_by(day_expr)
        .order_by(day_expr)
    )

    result = await db.execute(stmt)
    rows = result.all()

    columns = ["date", "total", "completed", "failed", "running", "avg_duration_ms", "success_rate"]
    data = []
    for row in rows:
        total = row[1] or 0
        completed = row[2] or 0
        failed = row[3] or 0
        running = row[4] or 0
        avg_dur = float(row[5]) if row[5] else 0.0
        rate = round((completed / total) * 100, 2) if total > 0 else 0.0
        data.append({
            "date": row[0].strftime("%Y-%m-%d") if row[0] else "",
            "total": total,
            "completed": completed,
            "failed": failed,
            "running": running,
            "avg_duration_ms": round(avg_dur, 1),
            "success_rate": rate,
        })

    if format == "csv":
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=columns)
        writer.writeheader()
        writer.writerows(data)
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=summary_{days}d.csv"},
        )

    return {"columns": columns, "rows": data, "total": len(data), "period_days": days}


@router.post("/sheets-sync")
async def sync_to_google_sheets(
    request: SheetsSyncRequest,
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Push analytics summary data to a Google Sheet for Looker Studio.
    
    Writes daily summary + workflow performance to the specified spreadsheet.
    The sheet then serves as a Looker Studio data source via native Google Sheets connector.
    """
    org_id = current_user.org_id
    cutoff = datetime.utcnow() - timedelta(days=90)

    from sqlalchemy import func as sql_func

    # ── Daily summary data ──
    day_expr = sql_func.date_trunc("day", Execution.created_at)
    stmt = (
        select(
            day_expr.label("date"),
            func.count(Execution.id).label("total"),
            func.sum(case((Execution.status == "completed", 1), else_=0)).label("completed"),
            func.sum(case((Execution.status == "failed", 1), else_=0)).label("failed"),
            func.avg(Execution.duration_ms).label("avg_duration_ms"),
        )
        .where(
            and_(
                Execution.organization_id == org_id,
                Execution.is_deleted == False,
                Execution.created_at >= cutoff,
            )
        )
        .group_by(day_expr)
        .order_by(day_expr)
    )
    result = await db.execute(stmt)
    summary_rows = result.all()

    # ── Write to Google Sheets ──
    try:
        from integrations.google_sheets import GoogleSheetsClient
        sheets = GoogleSheetsClient()

        # Header row
        header = ["Date", "Total Executions", "Completed", "Failed", "Avg Duration (ms)", "Success Rate %"]
        values = [header]
        for row in summary_rows:
            total = row[1] or 0
            completed = row[2] or 0
            rate = round((completed / total) * 100, 1) if total > 0 else 0
            values.append([
                row[0].strftime("%Y-%m-%d") if row[0] else "",
                total,
                completed,
                row[3] or 0,
                round(float(row[4]), 1) if row[4] else 0,
                rate,
            ])

        await sheets.write_range(
            spreadsheet_id=request.spreadsheet_id,
            range_str=f"A1:{chr(64 + len(header))}{len(values)}",
            values=values,
            sheet_name=request.sheet_name,
        )

        return {
            "ok": True,
            "rows_written": len(values) - 1,
            "sheet_name": request.sheet_name,
            "spreadsheet_id": request.spreadsheet_id,
            "message": f"Synced {len(values) - 1} days of analytics data",
        }

    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google Sheets integration not configured. Install google-auth and google-api-python-client.",
        )
    except Exception as e:
        logger.error(f"Sheets sync failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync: {str(e)}",
        )


# ─── Performance Alerts ─────────────────────────────────────

@router.get("/alerts", summary="Get workflow performance alerts")
async def get_performance_alerts(
    threshold: float = Query(50.0, ge=0, le=100, description="Success rate threshold (%)"),
    days: int = Query(7, ge=1, le=90, description="Analysis period"),
    min_runs: int = Query(3, ge=1, description="Minimum runs to trigger alert"),
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get alerts for workflows whose success rate drops below threshold.

    Returns a list of workflows that have failed more than expected,
    with their stats and recommended actions.
    """
    cutoff = utc_now() - timedelta(days=days)

    # Get per-workflow stats
    stmt = (
        select(
            Execution.workflow_id,
            func.count(Execution.id).label("total"),
            func.sum(case((Execution.status == "completed", 1), else_=0)).label("ok"),
            func.sum(case((Execution.status == "failed", 1), else_=0)).label("failed"),
            func.max(Execution.created_at).label("last_run"),
        )
        .where(
            Execution.organization_id == current_user.org_id,
            Execution.created_at >= cutoff,
            Execution.is_deleted == False,
        )
        .group_by(Execution.workflow_id)
    )
    result = await db.execute(stmt)
    rows = result.all()

    alerts = []
    for row in rows:
        total = row.total
        ok = row.ok or 0
        failed = row.failed or 0
        rate = (ok / total * 100) if total > 0 else 0

        if total >= min_runs and rate < threshold:
            # Get workflow name
            wf_result = await db.execute(
                select(Workflow.name).where(Workflow.id == row.workflow_id)
            )
            wf_name = wf_result.scalar_one_or_none() or row.workflow_id[:8]

            severity = "critical" if rate < 20 else "warning" if rate < threshold else "info"

            alerts.append({
                "workflow_id": row.workflow_id,
                "workflow_name": wf_name,
                "total_runs": total,
                "successful": ok,
                "failed": failed,
                "success_rate": round(rate, 1),
                "threshold": threshold,
                "severity": severity,
                "last_run": str(row.last_run) if row.last_run else None,
                "message": f"{wf_name}: {rate:.0f}% success rate ({failed} failures in {days}d)",
            })

    # Sort by severity (critical first)
    severity_order = {"critical": 0, "warning": 1, "info": 2}
    alerts.sort(key=lambda a: (severity_order.get(a["severity"], 9), a["success_rate"]))

    return {
        "alerts": alerts,
        "count": len(alerts),
        "threshold": threshold,
        "period_days": days,
    }
