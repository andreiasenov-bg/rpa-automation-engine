"""Bulk operations API endpoints.

Supports batch operations on workflows and executions:
- Bulk execute, publish, archive, delete workflows
- Bulk cancel, retry executions
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, update, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_active_user
from core.rbac import require_permission
from db.models.workflow import Workflow
from db.models.execution import Execution

router = APIRouter()


class BulkIdsRequest(BaseModel):
    ids: list[str] = Field(..., min_length=1, max_length=100)


class BulkResult(BaseModel):
    success: int
    failed: int
    errors: list[dict] = []


# ─── Workflow Bulk Operations ───

@router.post(
    "/bulk/workflows/publish",
    response_model=BulkResult,
    dependencies=[Depends(require_permission("workflows.write"))],
)
async def bulk_publish_workflows(
    body: BulkIdsRequest,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Publish multiple workflows at once."""
    success = 0
    errors = []

    for wf_id in body.ids:
        try:
            result = await db.execute(
                select(Workflow).where(
                    and_(
                        Workflow.id == wf_id,
                        Workflow.organization_id == current_user.organization_id,
                        Workflow.deleted_at.is_(None),
                    )
                )
            )
            wf = result.scalar_one_or_none()
            if not wf:
                errors.append({"id": wf_id, "error": "Not found"})
                continue
            wf.status = "published"
            wf.is_enabled = True
            success += 1
        except Exception as e:
            errors.append({"id": wf_id, "error": str(e)})

    await db.commit()
    return BulkResult(success=success, failed=len(errors), errors=errors)


@router.post(
    "/bulk/workflows/archive",
    response_model=BulkResult,
    dependencies=[Depends(require_permission("workflows.write"))],
)
async def bulk_archive_workflows(
    body: BulkIdsRequest,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Archive multiple workflows at once."""
    success = 0
    errors = []

    for wf_id in body.ids:
        try:
            result = await db.execute(
                select(Workflow).where(
                    and_(
                        Workflow.id == wf_id,
                        Workflow.organization_id == current_user.organization_id,
                        Workflow.deleted_at.is_(None),
                    )
                )
            )
            wf = result.scalar_one_or_none()
            if not wf:
                errors.append({"id": wf_id, "error": "Not found"})
                continue
            wf.status = "archived"
            wf.is_enabled = False
            success += 1
        except Exception as e:
            errors.append({"id": wf_id, "error": str(e)})

    await db.commit()
    return BulkResult(success=success, failed=len(errors), errors=errors)


@router.post(
    "/bulk/workflows/delete",
    response_model=BulkResult,
    dependencies=[Depends(require_permission("workflows.delete"))],
)
async def bulk_delete_workflows(
    body: BulkIdsRequest,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete multiple workflows at once."""
    from datetime import datetime, timezone

    success = 0
    errors = []
    now = datetime.now(timezone.utc)

    for wf_id in body.ids:
        try:
            result = await db.execute(
                select(Workflow).where(
                    and_(
                        Workflow.id == wf_id,
                        Workflow.organization_id == current_user.organization_id,
                        Workflow.deleted_at.is_(None),
                    )
                )
            )
            wf = result.scalar_one_or_none()
            if not wf:
                errors.append({"id": wf_id, "error": "Not found"})
                continue
            wf.deleted_at = now
            wf.is_enabled = False
            success += 1
        except Exception as e:
            errors.append({"id": wf_id, "error": str(e)})

    await db.commit()
    return BulkResult(success=success, failed=len(errors), errors=errors)


# ─── Execution Bulk Operations ───

@router.post(
    "/bulk/executions/cancel",
    response_model=BulkResult,
    dependencies=[Depends(require_permission("executions.cancel"))],
)
async def bulk_cancel_executions(
    body: BulkIdsRequest,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel multiple running/pending executions at once."""
    success = 0
    errors = []

    for ex_id in body.ids:
        try:
            result = await db.execute(
                select(Execution).where(
                    and_(
                        Execution.id == ex_id,
                        Execution.organization_id == current_user.organization_id,
                        Execution.status.in_(["pending", "running"]),
                    )
                )
            )
            ex = result.scalar_one_or_none()
            if not ex:
                errors.append({"id": ex_id, "error": "Not found or not cancellable"})
                continue
            ex.status = "cancelled"
            success += 1
        except Exception as e:
            errors.append({"id": ex_id, "error": str(e)})

    await db.commit()
    return BulkResult(success=success, failed=len(errors), errors=errors)


@router.post(
    "/bulk/executions/retry",
    response_model=BulkResult,
    dependencies=[Depends(require_permission("executions.write"))],
)
async def bulk_retry_executions(
    body: BulkIdsRequest,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Retry multiple failed/cancelled executions at once."""
    import uuid
    from datetime import datetime, timezone

    success = 0
    errors = []

    for ex_id in body.ids:
        try:
            result = await db.execute(
                select(Execution).where(
                    and_(
                        Execution.id == ex_id,
                        Execution.organization_id == current_user.organization_id,
                        Execution.status.in_(["failed", "cancelled"]),
                    )
                )
            )
            ex = result.scalar_one_or_none()
            if not ex:
                errors.append({"id": ex_id, "error": "Not found or not retryable"})
                continue

            new_execution = Execution(
                id=str(uuid.uuid4()),
                workflow_id=ex.workflow_id,
                organization_id=ex.organization_id,
                status="pending",
                trigger_type="manual",
                created_at=datetime.now(timezone.utc),
            )
            db.add(new_execution)
            success += 1
        except Exception as e:
            errors.append({"id": ex_id, "error": str(e)})

    await db.commit()
    return BulkResult(success=success, failed=len(errors), errors=errors)
