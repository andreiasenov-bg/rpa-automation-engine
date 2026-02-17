"""Agent task assignment API routes.

Handles assigning pending executions to available agents,
tracking task progress, and agent-side result reporting.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func, and_, desc, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_active_user
from core.security import TokenPayload
from db.models.agent import Agent
from db.models.execution import Execution

router = APIRouter()


# ─── Schemas ───

class TaskClaimRequest(BaseModel):
    agent_id: str
    capabilities: Optional[dict] = None


class TaskResultRequest(BaseModel):
    status: str = Field(..., pattern=r"^(completed|failed)$")
    output: Optional[dict] = None
    error_message: Optional[str] = None
    duration_ms: Optional[int] = None


class TaskAssignment(BaseModel):
    execution_id: str
    workflow_id: str
    step_index: int = 0
    task_type: str = "workflow"
    parameters: Optional[dict] = None


# ─── Endpoints ───

@router.post("/claim")
async def claim_task(
    body: TaskClaimRequest,
    db: AsyncSession = Depends(get_db),
):
    """Agent claims the next pending task.

    The agent provides its ID and capabilities. The system finds
    the oldest pending execution that matches and assigns it.
    Returns null if no tasks are available.
    """
    # Verify agent exists and is active
    agent = (await db.execute(
        select(Agent).where(
            Agent.id == body.agent_id,
            Agent.is_deleted == False,
        )
    )).scalar_one_or_none()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Update heartbeat
    agent.last_heartbeat_at = datetime.now(timezone.utc)
    agent.status = "active"

    # Find oldest pending execution for this org
    execution = (await db.execute(
        select(Execution).where(
            and_(
                Execution.organization_id == agent.organization_id,
                Execution.status == "pending",
                Execution.agent_id.is_(None),
            )
        ).order_by(Execution.created_at.asc()).limit(1)
    )).scalar_one_or_none()

    if not execution:
        return {"task": None, "message": "No pending tasks"}

    # Assign to agent
    execution.agent_id = agent.id
    execution.status = "running"
    execution.started_at = datetime.now(timezone.utc)

    await db.flush()

    return {
        "task": {
            "execution_id": execution.id,
            "workflow_id": execution.workflow_id,
            "task_type": "workflow",
            "parameters": execution.input_data,
            "assigned_at": execution.started_at.isoformat(),
        },
    }


@router.post("/{execution_id}/result")
async def submit_result(
    execution_id: str,
    body: TaskResultRequest,
    db: AsyncSession = Depends(get_db),
):
    """Agent submits the result of a completed/failed task."""
    execution = (await db.execute(
        select(Execution).where(
            Execution.id == execution_id,
            Execution.status == "running",
        )
    )).scalar_one_or_none()

    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found or not running")

    now = datetime.now(timezone.utc)
    execution.status = body.status
    execution.completed_at = now
    execution.output_data = body.output
    execution.error_message = body.error_message

    if body.duration_ms is not None:
        execution.duration_ms = body.duration_ms
    elif execution.started_at:
        execution.duration_ms = int((now - execution.started_at).total_seconds() * 1000)

    await db.flush()

    return {
        "execution_id": execution.id,
        "status": execution.status,
        "completed_at": execution.completed_at.isoformat(),
    }


@router.get("/queue")
async def get_task_queue(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """View the pending task queue for the organization."""
    base = and_(
        Execution.organization_id == current_user.org_id,
        Execution.status == "pending",
        Execution.agent_id.is_(None),
    )

    total = (await db.execute(
        select(func.count()).select_from(Execution).where(base)
    )).scalar() or 0

    offset = (page - 1) * per_page
    rows = (await db.execute(
        select(Execution).where(base)
        .order_by(Execution.created_at.asc())
        .offset(offset).limit(per_page)
    )).scalars().all()

    return {
        "queue": [
            {
                "execution_id": ex.id,
                "workflow_id": ex.workflow_id,
                "created_at": ex.created_at.isoformat() if ex.created_at else None,
                "trigger_type": ex.trigger_type,
            }
            for ex in rows
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/assigned/{agent_id}")
async def get_agent_assigned_tasks(
    agent_id: str,
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get tasks currently assigned to a specific agent."""
    rows = (await db.execute(
        select(Execution).where(
            and_(
                Execution.organization_id == current_user.org_id,
                Execution.agent_id == agent_id,
                Execution.status == "running",
            )
        ).order_by(Execution.started_at.desc())
    )).scalars().all()

    return {
        "agent_id": agent_id,
        "assigned_tasks": [
            {
                "execution_id": ex.id,
                "workflow_id": ex.workflow_id,
                "started_at": ex.started_at.isoformat() if ex.started_at else None,
                "trigger_type": ex.trigger_type,
            }
            for ex in rows
        ],
        "count": len(rows),
    }
