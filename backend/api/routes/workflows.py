"""Workflow CRUD endpoints — list, create, get, update, delete, execute, publish, archive, version history."""

import copy
from typing import Optional

from fastapi import APIRouter, HTTPException, status, Depends, Query
from sqlalchemy import select, desc, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from core.security import TokenPayload
from api.schemas.workflow import (
    WorkflowCreate,
    WorkflowUpdate,
    WorkflowResponse,
    WorkflowListResponse,
)
from api.schemas.execution import ExecutionResponse
from api.schemas.common import PaginationParams
from app.dependencies import get_db, get_current_active_user
from services.workflow_service import WorkflowService
from core.utils import calculate_offset
from db.models.audit_log import AuditLog

logger = logging.getLogger(__name__)

router = APIRouter(tags=["workflows"])


def _workflow_to_response(wf) -> WorkflowResponse:
    """Convert a Workflow ORM object to response schema."""
    return WorkflowResponse(
        id=wf.id,
        name=wf.name,
        description=wf.description or "",
        definition=wf.definition or {},
        version=wf.version,
        is_enabled=wf.is_enabled,
        status=wf.status,
        created_by=wf.created_by_id or "",
        created_at=wf.created_at,
        updated_at=wf.updated_at,
    )


@router.get("/", response_model=WorkflowListResponse)
async def list_workflows(
    pagination: PaginationParams = Depends(),
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> WorkflowListResponse:
    """
    List workflows in the current organization (paginated).
    """
    svc = WorkflowService(db)
    offset = calculate_offset(pagination.page, pagination.per_page)

    workflows, total = await svc.list(
        organization_id=current_user.org_id,
        offset=offset,
        limit=pagination.per_page,
    )

    return WorkflowListResponse(
        workflows=[_workflow_to_response(wf) for wf in workflows],
        total=total,
        page=pagination.page,
        per_page=pagination.per_page,
    )


@router.post("/", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    request: WorkflowCreate,
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> WorkflowResponse:
    """
    Create a new workflow in the current organization.
    """
    svc = WorkflowService(db)
    wf = await svc.create_workflow(
        organization_id=current_user.org_id,
        name=request.name,
        description=request.description or "",
        definition=request.definition,
        created_by_id=current_user.sub,
    )
    return _workflow_to_response(wf)


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: str,
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> WorkflowResponse:
    """
    Get workflow details by ID (org-scoped).
    """
    svc = WorkflowService(db)
    wf = await svc.get_by_id_and_org(workflow_id, current_user.org_id)

    if not wf:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )

    return _workflow_to_response(wf)


@router.put("/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(
    workflow_id: str,
    request: WorkflowUpdate,
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> WorkflowResponse:
    """
    Update workflow fields. Definition changes bump the version automatically.
    """
    svc = WorkflowService(db)

    # If definition is being updated, use the version-bumping method
    if request.definition is not None:
        wf = await svc.update_definition(
            workflow_id=workflow_id,
            organization_id=current_user.org_id,
            definition=request.definition,
        )
    else:
        update_data = request.model_dump(exclude_unset=True, exclude={"definition"})
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update",
            )
        wf = await svc.update(workflow_id, update_data, current_user.org_id)

    if not wf:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )

    return _workflow_to_response(wf)


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(
    workflow_id: str,
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Soft-delete a workflow.
    """
    svc = WorkflowService(db)
    deleted = await svc.soft_delete(workflow_id, current_user.org_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )


@router.post("/{workflow_id}/publish", response_model=WorkflowResponse)
async def publish_workflow(
    workflow_id: str,
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> WorkflowResponse:
    """
    Publish a workflow (make it executable).
    """
    svc = WorkflowService(db)
    wf = await svc.publish(workflow_id, current_user.org_id)

    if not wf:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )

    return _workflow_to_response(wf)


@router.post("/{workflow_id}/archive", response_model=WorkflowResponse)
async def archive_workflow(
    workflow_id: str,
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> WorkflowResponse:
    """
    Archive a workflow (disable and mark as archived).
    """
    svc = WorkflowService(db)
    wf = await svc.archive(workflow_id, current_user.org_id)

    if not wf:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )

    return _workflow_to_response(wf)


@router.post("/{workflow_id}/execute", status_code=status.HTTP_202_ACCEPTED)
async def trigger_workflow_execution(
    workflow_id: str,
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger manual execution of a workflow.
    Runs the engine directly in-process and updates DB status.
    """
    import time
    from datetime import datetime, timezone
    from uuid import uuid4
    from db.session import AsyncSessionLocal
    from db.models.execution import Execution as ExecModel
    from sqlalchemy import update as sa_update

    svc = WorkflowService(db)
    wf = await svc.get_by_id_and_org(workflow_id, current_user.org_id)
    if not wf or not wf.is_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found or disabled",
        )

    execution_id = str(uuid4())
    definition = wf.definition or {}

    # Create execution record
    execution = ExecModel(
        id=execution_id,
        organization_id=current_user.org_id,
        workflow_id=workflow_id,
        trigger_type="manual",
        status="running",
        started_at=datetime.now(timezone.utc),
    )
    db.add(execution)
    await db.commit()

    # Run engine directly (proven to work via execute-test)
    try:
        from workflow.engine import WorkflowEngine
        from workflow.checkpoint import CheckpointManager
        from tasks.registry import get_task_registry

        start = time.time()
        engine = WorkflowEngine(
            task_registry=get_task_registry(),
            checkpoint_manager=CheckpointManager(),
        )

        context = await engine.execute(
            execution_id=execution_id,
            workflow_id=workflow_id,
            organization_id=current_user.org_id,
            definition=definition,
            variables={},
        )
        duration_ms = int((time.time() - start) * 1000)

        # Check for failures
        failed_steps = [
            sid for sid, r in context.steps.items()
            if hasattr(r, 'status') and str(r.status) == 'failed'
        ]

        final_status = "failed" if failed_steps else "completed"
        error_msg = f"Steps failed: {', '.join(failed_steps)}" if failed_steps else None

        # Update DB directly
        async with AsyncSessionLocal() as session:
            await session.execute(
                sa_update(ExecModel)
                .where(ExecModel.id == execution_id)
                .values(
                    status=final_status,
                    duration_ms=duration_ms,
                    completed_at=datetime.now(timezone.utc),
                    error_message=error_msg,
                )
            )
            await session.commit()

        return {
            "id": execution_id,
            "workflow_id": workflow_id,
            "trigger_type": "manual",
            "status": final_status,
            "duration_ms": duration_ms,
            "error_message": error_msg,
            "steps_completed": len(context.steps) - len(failed_steps),
            "steps_failed": len(failed_steps),
        }

    except Exception as e:
        logger.error(f"Execution {execution_id} failed: {e}", exc_info=True)
        async with AsyncSessionLocal() as session:
            await session.execute(
                sa_update(ExecModel)
                .where(ExecModel.id == execution_id)
                .values(
                    status="failed",
                    completed_at=datetime.now(timezone.utc),
                    error_message=str(e),
                )
            )
            await session.commit()

        return {
            "id": execution_id,
            "workflow_id": workflow_id,
            "trigger_type": "manual",
            "status": "failed",
            "error_message": str(e),
        }


@router.post("/{workflow_id}/execute-test")
async def test_workflow_execution(
    workflow_id: str,
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Debug endpoint: runs workflow synchronously and returns full result/error.
    """
    import traceback
    import time
    from datetime import datetime, timezone

    svc = WorkflowService(db)
    wf = await svc.get_by_id_and_org(workflow_id, current_user.org_id)
    if not wf:
        return {"error": "Workflow not found"}

    definition = wf.definition or {}
    steps = definition.get("steps", [])

    result = {
        "workflow_id": workflow_id,
        "workflow_name": wf.name,
        "step_count": len(steps),
        "step_types": [s.get("type", "unknown") for s in steps],
        "stages": [],
    }

    # Stage 1: Check imports
    try:
        from workflow.engine import WorkflowEngine
        from workflow.checkpoint import CheckpointManager
        from tasks.registry import get_task_registry
        result["stages"].append({"stage": "imports", "status": "ok"})
    except Exception as e:
        result["stages"].append({"stage": "imports", "status": "failed", "error": traceback.format_exc()})
        return result

    # Stage 2: Check task registry
    try:
        registry = get_task_registry()
        available = registry.available_types
        result["stages"].append({
            "stage": "registry",
            "status": "ok",
            "available_types": available,
            "needed_types": list(set(s.get("type", "unknown") for s in steps)),
        })
    except Exception as e:
        result["stages"].append({"stage": "registry", "status": "failed", "error": traceback.format_exc()})
        return result

    # Stage 3: Check DB update
    try:
        from db.session import AsyncSessionLocal
        from db.models.execution import Execution
        from sqlalchemy import update as sa_update
        async with AsyncSessionLocal() as session:
            # Just test that we can query
            r = await session.execute(
                sa_update(Execution)
                .where(Execution.id == "test-nonexistent")
                .values(status="test")
            )
            await session.rollback()
        result["stages"].append({"stage": "db_update", "status": "ok"})
    except Exception as e:
        result["stages"].append({"stage": "db_update", "status": "failed", "error": traceback.format_exc()})
        return result

    # Stage 4: Actually run the engine
    try:
        engine = WorkflowEngine(
            task_registry=registry,
            checkpoint_manager=CheckpointManager(),
        )

        start = time.time()
        context = await engine.execute(
            execution_id=f"test-{int(time.time())}",
            workflow_id=workflow_id,
            organization_id=current_user.org_id,
            definition=definition,
            variables={},
        )
        duration = int((time.time() - start) * 1000)

        step_results = {}
        for sid, sr in context.steps.items():
            step_results[sid] = {
                "status": str(sr.status.value if hasattr(sr.status, 'value') else sr.status),
                "error": sr.error,
                "duration_ms": sr.duration_ms,
                "has_output": sr.output is not None,
            }

        result["stages"].append({
            "stage": "engine_run",
            "status": "ok",
            "duration_ms": duration,
            "step_results": step_results,
        })

    except Exception as e:
        result["stages"].append({
            "stage": "engine_run",
            "status": "failed",
            "error": traceback.format_exc(),
        })

    return result


@router.get("/{workflow_id}/history")
async def get_workflow_history(
    workflow_id: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get audit history for a workflow (version changes, publishes, etc.).
    """
    conditions = and_(
        AuditLog.organization_id == current_user.org,
        AuditLog.resource_type == "workflow",
        AuditLog.resource_id == workflow_id,
        AuditLog.is_deleted == False,
    )

    total = (await db.execute(
        select(func.count()).select_from(AuditLog).where(conditions)
    )).scalar() or 0

    offset = (page - 1) * per_page
    from db.models.user import User
    query = (
        select(AuditLog, User.email)
        .outerjoin(User, AuditLog.user_id == User.id)
        .where(conditions)
        .order_by(desc(AuditLog.created_at))
        .offset(offset)
        .limit(per_page)
    )
    rows = (await db.execute(query)).all()

    history = []
    for row in rows:
        log = row[0]
        user_email = row[1]
        history.append({
            "id": log.id,
            "action": log.action,
            "user_email": user_email,
            "old_values": log.old_values,
            "new_values": log.new_values,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        })

    return {"history": history, "total": total, "page": page, "per_page": per_page}


@router.post("/{workflow_id}/clone", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def clone_workflow(
    workflow_id: str,
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> WorkflowResponse:
    """
    Clone a workflow (create a copy with version 1).
    """
    svc = WorkflowService(db)
    original = await svc.get_by_id_and_org(workflow_id, current_user.org_id)

    if not original:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )

    cloned = await svc.create_workflow(
        organization_id=current_user.org_id,
        name=f"{original.name} (Copy)",
        description=original.description,
        definition=copy.deepcopy(original.definition) if original.definition else {},
        created_by_id=current_user.sub,
    )

    return _workflow_to_response(cloned)
