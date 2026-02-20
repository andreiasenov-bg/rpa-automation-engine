"""Schedule management endpoints.

Full CRUD for workflow schedules with cron-expression validation,
timezone support, enable/disable toggle, and next-run computation.
"""

from typing import Optional
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from core.security import TokenPayload
from app.dependencies import get_db, get_current_active_user
from db.models.schedule import Schedule
from db.models.workflow import Workflow

logger = logging.getLogger(__name__)

router = APIRouter(tags=["schedules"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class ScheduleCreateRequest(BaseModel):
    """Request body to create a schedule."""
    workflow_id: str = Field(..., description="ID of the workflow to schedule")
    name: str = Field(..., min_length=1, max_length=255)
    cron_expression: str = Field(
        ...,
        min_length=5,
        description="Standard cron expression (5 fields: min hour dom mon dow)",
    )
    timezone: str = Field(default="UTC", max_length=64)
    is_enabled: bool = Field(default=True)


class ScheduleUpdateRequest(BaseModel):
    """Request body to update a schedule."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    cron_expression: Optional[str] = Field(default=None, min_length=5)
    timezone: Optional[str] = Field(default=None, max_length=64)
    is_enabled: Optional[bool] = None


class ScheduleResponse(BaseModel):
    """Public representation of a schedule."""
    id: str
    workflow_id: str
    workflow_name: Optional[str] = None
    name: str
    cron_expression: str
    timezone: str
    is_enabled: bool
    next_run_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _compute_next_run(cron_expression: str, tz: str = "UTC") -> Optional[datetime]:
    """Compute the next run timestamp from a cron expression.

    Returns a **naive UTC** datetime for TIMESTAMP WITHOUT TIME ZONE columns.
    """
    try:
        from croniter import croniter
        from zoneinfo import ZoneInfo

        tz_obj = ZoneInfo(tz)
        now_local = datetime.now(tz_obj)
        cron = croniter(cron_expression, now_local)
        next_local = cron.get_next(datetime)
        # Convert to UTC and strip tzinfo → naive UTC
        return next_local.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
    except ImportError:
        logger.warning("croniter not installed — cannot compute next_run_at")
        return None
    except Exception as e:
        logger.error(f"Failed to compute next run: {e}")
        return None


def _validate_cron(cron_expression: str) -> bool:
    """Return True if the cron expression is syntactically valid."""
    try:
        from croniter import croniter
        return croniter.is_valid(cron_expression)
    except ImportError:
        # Lightweight fallback: accept any 5-field string
        parts = cron_expression.strip().split()
        return len(parts) == 5
    except Exception:
        return False


def _to_response(sched: Schedule, workflow_name: Optional[str] = None) -> dict:
    """Convert a Schedule ORM instance to a response dict."""
    return {
        "id": sched.id,
        "workflow_id": sched.workflow_id,
        "workflow_name": workflow_name,
        "name": sched.name,
        "cron_expression": sched.cron_expression,
        "timezone": sched.timezone,
        "is_enabled": sched.is_enabled,
        "next_run_at": sched.next_run_at.isoformat() if sched.next_run_at else None,
        "created_at": sched.created_at.isoformat() if sched.created_at else None,
        "updated_at": sched.updated_at.isoformat() if sched.updated_at else None,
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/")
async def list_schedules(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    workflow_id: Optional[str] = Query(None, description="Filter by workflow"),
    is_enabled: Optional[bool] = Query(None, description="Filter by enabled status"),
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List workflow schedules for the organisation."""
    org_id = current_user.org_id
    base = and_(
        Schedule.organization_id == org_id,
        Schedule.is_deleted == False,
    )

    filters = [base]
    if workflow_id:
        filters.append(Schedule.workflow_id == workflow_id)
    if is_enabled is not None:
        filters.append(Schedule.is_enabled == is_enabled)

    where = and_(*filters)

    total = await db.scalar(select(func.count(Schedule.id)).where(where)) or 0

    # Join with Workflow to include workflow_name
    stmt = (
        select(Schedule, Workflow.name.label("workflow_name"))
        .outerjoin(Workflow, Workflow.id == Schedule.workflow_id)
        .where(where)
        .order_by(Schedule.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await db.execute(stmt)
    rows = result.all()

    return {
        "items": [_to_response(row[0], workflow_name=row[1]) for row in rows],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page if per_page else 0,
    }


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_schedule(
    request: ScheduleCreateRequest,
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create a new schedule for a workflow."""
    org_id = current_user.org_id

    # Validate cron
    if not _validate_cron(request.cron_expression):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid cron expression: '{request.cron_expression}'",
        )

    # Verify workflow belongs to org
    wf = await db.execute(
        select(Workflow).where(
            and_(
                Workflow.id == request.workflow_id,
                Workflow.organization_id == org_id,
                Workflow.is_deleted == False,
            )
        )
    )
    workflow = wf.scalar_one_or_none()
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )

    next_run = _compute_next_run(request.cron_expression, request.timezone)

    schedule = Schedule(
        organization_id=org_id,
        workflow_id=request.workflow_id,
        name=request.name,
        cron_expression=request.cron_expression,
        timezone=request.timezone,
        is_enabled=request.is_enabled,
        next_run_at=next_run,
    )
    db.add(schedule)
    await db.flush()
    await db.refresh(schedule)

    return _to_response(schedule, workflow_name=workflow.name)


@router.get("/{schedule_id}")
async def get_schedule(
    schedule_id: str,
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get schedule details."""
    org_id = current_user.org_id

    result = await db.execute(
        select(Schedule, Workflow.name.label("workflow_name"))
        .outerjoin(Workflow, Workflow.id == Schedule.workflow_id)
        .where(
            and_(
                Schedule.id == schedule_id,
                Schedule.organization_id == org_id,
                Schedule.is_deleted == False,
            )
        )
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found")

    return _to_response(row[0], workflow_name=row[1])


@router.put("/{schedule_id}")
async def update_schedule(
    schedule_id: str,
    request: ScheduleUpdateRequest,
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Update a schedule."""
    org_id = current_user.org_id

    result = await db.execute(
        select(Schedule).where(
            and_(
                Schedule.id == schedule_id,
                Schedule.organization_id == org_id,
                Schedule.is_deleted == False,
            )
        )
    )
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found")

    recalc_next = False

    if request.name is not None:
        schedule.name = request.name

    if request.cron_expression is not None:
        if not _validate_cron(request.cron_expression):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid cron expression: '{request.cron_expression}'",
            )
        schedule.cron_expression = request.cron_expression
        recalc_next = True

    if request.timezone is not None:
        schedule.timezone = request.timezone
        recalc_next = True

    if request.is_enabled is not None:
        schedule.is_enabled = request.is_enabled
        if request.is_enabled:
            recalc_next = True

    if recalc_next and schedule.is_enabled:
        schedule.next_run_at = _compute_next_run(schedule.cron_expression, schedule.timezone)
    elif not schedule.is_enabled:
        schedule.next_run_at = None

    await db.flush()
    await db.refresh(schedule)

    # Fetch workflow name
    wf_result = await db.execute(
        select(Workflow.name).where(Workflow.id == schedule.workflow_id)
    )
    wf_name = wf_result.scalar_one_or_none()

    return _to_response(schedule, workflow_name=wf_name)


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule(
    schedule_id: str,
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft-delete a schedule."""
    org_id = current_user.org_id

    result = await db.execute(
        select(Schedule).where(
            and_(
                Schedule.id == schedule_id,
                Schedule.organization_id == org_id,
                Schedule.is_deleted == False,
            )
        )
    )
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found")

    schedule.is_deleted = True


@router.post("/{schedule_id}/toggle")
async def toggle_schedule(
    schedule_id: str,
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Enable or disable a schedule."""
    org_id = current_user.org_id

    result = await db.execute(
        select(Schedule).where(
            and_(
                Schedule.id == schedule_id,
                Schedule.organization_id == org_id,
                Schedule.is_deleted == False,
            )
        )
    )
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found")

    schedule.is_enabled = not schedule.is_enabled

    if schedule.is_enabled:
        schedule.next_run_at = _compute_next_run(schedule.cron_expression, schedule.timezone)
    else:
        schedule.next_run_at = None

    await db.flush()
    await db.refresh(schedule)

    wf_result = await db.execute(
        select(Workflow.name).where(Workflow.id == schedule.workflow_id)
    )
    wf_name = wf_result.scalar_one_or_none()

    return _to_response(schedule, workflow_name=wf_name)


@router.post("/recalculate-all")
async def recalculate_all_schedules(
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Recalculate next_run_at for all enabled schedules.

    Useful after installing croniter or fixing schedule computation.
    """
    org_id = current_user.org_id

    result = await db.execute(
        select(Schedule).where(
            and_(
                Schedule.organization_id == org_id,
                Schedule.is_enabled == True,
                Schedule.is_deleted == False,
            )
        )
    )
    schedules = result.scalars().all()

    updated = 0
    for schedule in schedules:
        next_run = _compute_next_run(schedule.cron_expression, schedule.timezone)
        if next_run:
            schedule.next_run_at = next_run
            updated += 1
            logger.info(f"Schedule '{schedule.name}' next_run_at: {next_run}")

    await db.flush()
    # No refresh needed — response doesn't access ORM attributes

    return {"updated": updated, "total": len(schedules)}


@router.post("/poll-now")
async def poll_schedules_now(
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Manually trigger the schedule poller for the current org.

    Useful for debugging — shows which schedules are due and dispatches them
    immediately without waiting for Celery Beat.
    """
    from datetime import timedelta
    from uuid import uuid4
    from db.models.workflow import Workflow
    from db.models.execution import Execution

    org_id = current_user.org_id
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # Show debug info about all schedules for this org
    all_result = await db.execute(
        select(Schedule).where(
            and_(
                Schedule.organization_id == org_id,
                Schedule.is_deleted == False,
            )
        )
    )
    all_schedules = all_result.scalars().all()

    debug_info = []
    for s in all_schedules:
        is_due = (
            s.is_enabled
            and s.next_run_at is not None
            and s.next_run_at <= now
        )
        debug_info.append({
            "id": s.id,
            "name": s.name,
            "cron": s.cron_expression,
            "timezone": s.timezone,
            "is_enabled": s.is_enabled,
            "next_run_at": s.next_run_at.isoformat() if s.next_run_at else None,
            "now_utc": now.isoformat(),
            "is_due": is_due,
        })

    # Find due schedules
    due_result = await db.execute(
        select(Schedule).where(
            and_(
                Schedule.organization_id == org_id,
                Schedule.is_enabled == True,
                Schedule.is_deleted == False,
                Schedule.next_run_at is not None,
                Schedule.next_run_at <= now,
            )
        )
    )
    due_schedules = due_result.scalars().all()

    dispatched = []
    for schedule in due_schedules:
        wf_result = await db.execute(
            select(Workflow).where(Workflow.id == schedule.workflow_id)
        )
        workflow = wf_result.scalar_one_or_none()
        if not workflow or not workflow.is_enabled:
            continue

        execution_id = str(uuid4())
        execution = Execution(
            id=execution_id,
            organization_id=org_id,
            workflow_id=schedule.workflow_id,
            trigger_type="schedule",
            status="pending",
        )
        db.add(execution)

        next_run = _compute_next_run(schedule.cron_expression, schedule.timezone)
        schedule.next_run_at = next_run if next_run else now + timedelta(seconds=60)

        await db.flush()

        # Run directly in background thread (bypasses Celery for reliability)
        try:
            from worker.run_workflow import launch_workflow_thread
            launch_workflow_thread(
                execution_id=execution_id,
                workflow_id=str(schedule.workflow_id),
                organization_id=str(org_id),
                definition=workflow.definition or {},
                variables={},
                trigger_payload={"schedule_id": str(schedule.id)},
            )
        except Exception as e:
            logger.error(f"Failed to launch execution: {e}")

        dispatched.append({
            "execution_id": execution_id,
            "schedule_name": schedule.name,
            "workflow_name": workflow.name,
            "next_run_at": schedule.next_run_at.isoformat() if schedule.next_run_at else None,
        })

    return {
        "now_utc": now.isoformat(),
        "all_schedules": debug_info,
        "due_count": len(due_schedules),
        "dispatched": dispatched,
    }
