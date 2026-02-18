"""Workflow execution history and management endpoints."""

from fastapi import APIRouter, HTTPException, status as http_status, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List
import logging

from core.security import TokenPayload
from api.schemas.execution import (
    ExecutionResponse,
    ExecutionLogResponse,
    ExecutionListResponse,
)
from api.schemas.common import PaginationParams, MessageResponse
from app.dependencies import get_db, get_current_active_user
from services.workflow_service import ExecutionService, WorkflowService
from core.utils import calculate_offset

logger = logging.getLogger(__name__)

router = APIRouter(tags=["executions"])


def _execution_to_response(ex) -> ExecutionResponse:
    """Convert an Execution ORM object to response schema."""
    return ExecutionResponse(
        id=ex.id,
        workflow_id=ex.workflow_id,
        agent_id=ex.agent_id,
        trigger_type=ex.trigger_type,
        status=ex.status,
        started_at=ex.started_at,
        completed_at=ex.completed_at,
        duration_ms=ex.duration_ms,
        error_message=ex.error_message,
        retry_count=ex.retry_count,
    )


@router.get("/", response_model=ExecutionListResponse)
async def list_executions(
    pagination: PaginationParams = Depends(),
    workflow_id: Optional[str] = Query(None, description="Filter by workflow ID"),
    exec_status: Optional[str] = Query(None, alias="status", description="Filter by execution status"),
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ExecutionListResponse:
    """
    List workflow executions (paginated, filterable).
    """
    svc = ExecutionService(db)
    offset = calculate_offset(pagination.page, pagination.per_page)

    filters = {}
    if workflow_id:
        filters["workflow_id"] = workflow_id
    if exec_status:
        filters["status"] = exec_status

    executions, total = await svc.list(
        organization_id=current_user.org_id,
        offset=offset,
        limit=pagination.per_page,
        filters=filters if filters else None,
        order_by="created_at",
        order_desc=True,
    )

    return ExecutionListResponse(
        executions=[_execution_to_response(ex) for ex in executions],
        total=total,
        page=pagination.page,
        per_page=pagination.per_page,
    )


@router.get("/{execution_id}")
async def get_execution(
    execution_id: str,
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get execution details by ID, including step progress from execution_states.
    """
    svc = ExecutionService(db)
    ex = await svc.get_by_id_and_org(execution_id, current_user.org_id)

    if not ex:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Execution not found",
        )

    resp = _execution_to_response(ex).model_dump()

    # Enrich with step data from execution_states
    try:
        from db.models.execution_state import ExecutionStateModel
        result = await db.execute(
            select(ExecutionStateModel)
            .where(ExecutionStateModel.execution_id == execution_id)
        )
        state = result.scalars().first()

        if state and state.state_data:
            data = state.state_data
            step_outputs = data.get("step_outputs", {})
            completed = set(data.get("completed_steps", []))
            failed = set(data.get("failed_steps", []))
            skipped = set(data.get("skipped_steps", []))
            error_map = {}
            for err_entry in data.get("error_log", []):
                if isinstance(err_entry, dict) and err_entry.get("step_id"):
                    error_map[err_entry["step_id"]] = err_entry.get("error")

            steps_list = []
            all_step_ids = sorted(set(step_outputs.keys()) | completed | failed | skipped)
            for step_id in all_step_ids:
                st = "completed" if step_id in completed else "failed" if step_id in failed else "skipped" if step_id in skipped else "unknown"
                steps_list.append({
                    "id": step_id,
                    "step_id": step_id,
                    "name": step_id,
                    "type": "step",
                    "status": st,
                    "output": step_outputs.get(step_id),
                    "error": error_map.get(step_id),
                })

            # Also check "steps" key (alternative engine format)
            raw_steps = data.get("steps", {})
            existing_ids = {s["id"] for s in steps_list}
            for step_id, step_data in sorted(raw_steps.items()):
                if isinstance(step_data, dict) and step_id not in existing_ids:
                    steps_list.append({
                        "id": step_id,
                        "step_id": step_id,
                        "name": step_data.get("name", step_id),
                        "type": step_data.get("type", "step"),
                        "status": step_data.get("status", "unknown"),
                        "output": step_data.get("output"),
                        "error": step_data.get("error"),
                        "duration_ms": step_data.get("duration_ms"),
                    })

            resp["steps"] = steps_list
            resp["step_results"] = steps_list
    except Exception as e:
        logger.warning(f"Failed to enrich execution with step data: {e}")
        resp["steps"] = []
        resp["step_results"] = []

    return resp


@router.get("/{execution_id}/logs", response_model=List[ExecutionLogResponse])
async def get_execution_logs(
    execution_id: str,
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> List[ExecutionLogResponse]:
    """
    Get log entries for a specific execution.
    """
    svc = ExecutionService(db)
    ex = await svc.get_by_id_and_org(execution_id, current_user.org_id)

    if not ex:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Execution not found",
        )

    from db.models.execution_log import ExecutionLog
    result = await db.execute(
        select(ExecutionLog)
        .where(ExecutionLog.execution_id == execution_id)
        .order_by(ExecutionLog.created_at.asc())
    )
    logs = result.scalars().all()

    return [
        ExecutionLogResponse(
            id=log.id,
            level=log.level,
            message=log.message,
            context=log.context,
            timestamp=log.created_at,
        )
        for log in logs
    ]


@router.get("/{execution_id}/data")
async def get_execution_data(
    execution_id: str,
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get full execution state data including step outputs.

    Returns the serialized execution context from execution_states table.
    This contains all step results, outputs (e.g. scraped products), and variables.
    """
    # Verify execution belongs to user's org
    svc = ExecutionService(db)
    ex = await svc.get_by_id_and_org(execution_id, current_user.org_id)

    if not ex:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Execution not found",
        )

    # Query execution_states for the full state_data
    from db.models.execution_state import ExecutionStateModel
    result = await db.execute(
        select(ExecutionStateModel)
        .where(ExecutionStateModel.execution_id == execution_id)
    )
    state = result.scalars().first()

    if not state or not state.state_data:
        return {"execution_id": execution_id, "steps": {}, "variables": {}}

    data = state.state_data

    # Extract step results with their outputs.
    # The checkpoint system stores outputs in "step_outputs" (key -> raw output),
    # plus metadata in "completed_steps", "failed_steps", "error_log".
    steps_out = {}

    # Primary source: "step_outputs" from CheckpointManager
    step_outputs = data.get("step_outputs", {})
    completed = set(data.get("completed_steps", []))
    failed = set(data.get("failed_steps", []))
    skipped = set(data.get("skipped_steps", []))
    error_map = {}
    for err_entry in data.get("error_log", []):
        if isinstance(err_entry, dict) and err_entry.get("step_id"):
            error_map[err_entry["step_id"]] = err_entry.get("error")

    # Build unified step info from all checkpoint sources
    all_step_ids = set(step_outputs.keys()) | completed | failed | skipped
    for step_id in all_step_ids:
        status = "completed" if step_id in completed else "failed" if step_id in failed else "skipped" if step_id in skipped else "unknown"
        output = step_outputs.get(step_id)
        steps_out[step_id] = {
            "status": status,
            "output": output,
            "error": error_map.get(step_id),
        }

    # Fallback: also check "steps" key (alternative engine format)
    raw_steps = data.get("steps", {})
    for step_id, step_data in raw_steps.items():
        if isinstance(step_data, dict) and step_id not in steps_out:
            steps_out[step_id] = {
                "status": step_data.get("status", "unknown"),
                "output": step_data.get("output"),
                "error": step_data.get("error"),
                "duration_ms": step_data.get("duration_ms"),
            }

    return {
        "execution_id": execution_id,
        "steps": steps_out,
        "variables": data.get("variables", {}),
    }


@router.post("/{execution_id}/retry", response_model=ExecutionResponse, status_code=http_status.HTTP_202_ACCEPTED)
async def retry_execution(
    execution_id: str,
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ExecutionResponse:
    """
    Retry a failed execution by creating a new execution for the same workflow.
    """
    exec_svc = ExecutionService(db)
    ex = await exec_svc.get_by_id_and_org(execution_id, current_user.org_id)

    if not ex:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Execution not found",
        )

    if ex.status not in ("failed", "cancelled"):
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot retry execution in '{ex.status}' status (must be 'failed' or 'cancelled')",
        )

    # Create a new execution for the same workflow
    wf_svc = WorkflowService(db)
    new_execution_id = await wf_svc.execute(
        workflow_id=ex.workflow_id,
        organization_id=current_user.org_id,
        trigger_type="retry",
    )

    if not new_execution_id:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Workflow not found or disabled — cannot retry",
        )

    return ExecutionResponse(
        id=new_execution_id,
        workflow_id=ex.workflow_id,
        trigger_type="retry",
        status="pending",
    )


@router.post("/{execution_id}/cancel", response_model=MessageResponse)
async def cancel_execution(
    execution_id: str,
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """
    Cancel a running or pending execution.
    """
    svc = ExecutionService(db)
    ex = await svc.get_by_id_and_org(execution_id, current_user.org_id)

    if not ex:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Execution not found",
        )

    if ex.status not in ("pending", "running"):
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel execution in '{ex.status}' status",
        )

    await svc.update_status(execution_id, "cancelled")

    return MessageResponse(message=f"Execution {execution_id} cancelled")
