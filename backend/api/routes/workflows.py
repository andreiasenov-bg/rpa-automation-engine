"""Workflow CRUD endpoints — list, create, get, update, delete, execute, publish, archive."""

from fastapi import APIRouter, HTTPException, status, Depends
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

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workflows", tags=["workflows"])


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


@router.post("/{workflow_id}/execute", response_model=ExecutionResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_workflow_execution(
    workflow_id: str,
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ExecutionResponse:
    """
    Trigger manual execution of a workflow.
    Returns 202 Accepted with the execution record.
    """
    svc = WorkflowService(db)
    execution_id = await svc.execute(
        workflow_id=workflow_id,
        organization_id=current_user.org_id,
        trigger_type="manual",
    )

    if not execution_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found or disabled",
        )

    return ExecutionResponse(
        id=execution_id,
        workflow_id=workflow_id,
        trigger_type="manual",
        status="pending",
    )
