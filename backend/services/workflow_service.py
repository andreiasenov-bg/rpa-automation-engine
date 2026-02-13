"""Workflow service — CRUD + execution dispatch."""

from typing import Any, Optional
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from db.models.workflow import Workflow
from db.models.execution import Execution
from services.base import BaseService


class WorkflowService(BaseService[Workflow]):
    """Service for workflow management and execution."""

    def __init__(self, db: AsyncSession):
        super().__init__(Workflow, db)

    async def create_workflow(
        self,
        organization_id: str,
        name: str,
        description: str = "",
        definition: dict = None,
        created_by_id: str = None,
    ) -> Workflow:
        """Create a new workflow."""
        return await self.create({
            "organization_id": organization_id,
            "name": name,
            "description": description,
            "definition": definition or {"version": "1.0", "variables": {}, "steps": []},
            "created_by_id": created_by_id,
            "status": "draft",
            "version": 1,
        })

    async def publish(self, workflow_id: str, organization_id: str) -> Optional[Workflow]:
        """Publish a workflow (make it executable)."""
        return await self.update(workflow_id, {"status": "published", "is_enabled": True}, organization_id)

    async def archive(self, workflow_id: str, organization_id: str) -> Optional[Workflow]:
        """Archive a workflow."""
        return await self.update(workflow_id, {"status": "archived", "is_enabled": False}, organization_id)

    async def update_definition(
        self,
        workflow_id: str,
        organization_id: str,
        definition: dict,
    ) -> Optional[Workflow]:
        """Update workflow definition and bump version."""
        wf = await self.get_by_id_and_org(workflow_id, organization_id)
        if not wf:
            return None
        return await self.update(workflow_id, {
            "definition": definition,
            "version": wf.version + 1,
        }, organization_id)

    async def execute(
        self,
        workflow_id: str,
        organization_id: str,
        trigger_type: str = "manual",
        variables: dict = None,
    ) -> Optional[str]:
        """Dispatch a workflow execution.

        Creates an Execution record and sends to Celery.

        Returns:
            execution_id or None if workflow not found/disabled
        """
        wf = await self.get_by_id_and_org(workflow_id, organization_id)
        if not wf or not wf.is_enabled:
            return None

        execution_id = str(uuid4())

        execution = Execution(
            id=execution_id,
            organization_id=organization_id,
            workflow_id=workflow_id,
            trigger_type=trigger_type,
            status="pending",
        )
        self.db.add(execution)
        await self.db.flush()

        # Dispatch to Celery
        try:
            from worker.tasks.workflow import execute_workflow
            execute_workflow.delay(
                execution_id=execution_id,
                workflow_id=workflow_id,
                organization_id=organization_id,
                definition=wf.definition or {},
                variables=variables or {},
            )
        except Exception:
            # If Celery is not available, mark as failed
            execution.status = "failed"
            execution.error_message = "Task queue unavailable"
            await self.db.flush()

        return execution_id


class ExecutionService(BaseService[Execution]):
    """Service for execution management."""

    def __init__(self, db: AsyncSession):
        super().__init__(Execution, db)

    async def get_by_workflow(
        self,
        workflow_id: str,
        organization_id: str,
        offset: int = 0,
        limit: int = 20,
    ):
        """Get executions for a specific workflow."""
        return await self.list(
            organization_id=organization_id,
            offset=offset,
            limit=limit,
            filters={"workflow_id": workflow_id},
        )

    async def update_status(
        self,
        execution_id: str,
        status: str,
        error_message: str = None,
        duration_ms: int = None,
    ) -> Optional[Execution]:
        """Update execution status."""
        from datetime import datetime, timezone
        data: dict[str, Any] = {"status": status}
        if error_message:
            data["error_message"] = error_message
        if duration_ms is not None:
            data["duration_ms"] = duration_ms
        if status in ("completed", "failed", "cancelled"):
            data["completed_at"] = datetime.now(timezone.utc)
        if status == "running":
            data["started_at"] = datetime.now(timezone.utc)
        return await self.update(execution_id, data)
