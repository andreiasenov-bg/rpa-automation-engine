"""Workflow service — CRUD + execution dispatch."""

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from db.models.workflow import Workflow
from db.models.execution import Execution
from services.base import BaseService

logger = logging.getLogger(__name__)


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
        mode: str = "auto",
    ) -> Optional[str]:
        """Dispatch a workflow execution.

        Creates an Execution record and runs it.

        Args:
            workflow_id: Workflow to execute
            organization_id: Owning org
            trigger_type: How execution was triggered
            variables: Initial variables
            mode: "celery" (async via worker), "sync" (in-process background),
                  "auto" (try celery, fall back to sync)

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

        definition = wf.definition or {}

        # Determine execution mode
        use_celery = False
        if mode in ("celery", "auto"):
            try:
                from worker.celery_app import celery_app
                # Check if any workers are actually running
                inspector = celery_app.control.inspect(timeout=2.0)
                active_workers = inspector.ping()
                if active_workers:
                    from worker.tasks.workflow import execute_workflow
                    execute_workflow.delay(
                        execution_id=execution_id,
                        workflow_id=workflow_id,
                        organization_id=organization_id,
                        definition=definition,
                        variables=variables or {},
                    )
                    use_celery = True
                    logger.info(f"Execution {execution_id} dispatched to Celery ({len(active_workers)} workers)")
                else:
                    logger.info("No Celery workers found, falling back to sync")
            except Exception as e:
                logger.warning(f"Celery check/dispatch failed: {e}")

        # Fall back to in-process execution if no workers or sync mode requested
        if not use_celery:
            logger.info(f"Execution {execution_id} running in-process (sync mode)")
            asyncio.create_task(
                _run_workflow_in_process(
                    execution_id=execution_id,
                    workflow_id=workflow_id,
                    organization_id=organization_id,
                    definition=definition,
                    variables=variables or {},
                )
            )

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
        data: dict[str, Any] = {"status": status}
        if error_message:
            data["error_message"] = error_message
        if duration_ms is not None:
            data["duration_ms"] = duration_ms
        if status in ("completed", "failed", "cancelled"):
            data["completed_at"] = datetime.utcnow()
        if status == "running":
            data["started_at"] = datetime.utcnow()
        return await self.update(execution_id, data)


# ─── In-process workflow execution (no Celery needed) ──────────

async def _run_workflow_in_process(
    execution_id: str,
    workflow_id: str,
    organization_id: str,
    definition: dict,
    variables: dict,
):
    """Run workflow directly in the API process as a background task.

    Uses the same engine as the Celery worker but runs in the current
    event loop. Updates the database directly via async session.
    """
    from db.session import AsyncSessionLocal
    from db.models.execution import Execution
    from sqlalchemy import update as sa_update

    start_time = time.time()

    async def update_status(status, error_message=None, duration_ms=None):
        values = {"status": status}
        if error_message:
            values["error_message"] = error_message
        if duration_ms is not None:
            values["duration_ms"] = duration_ms
        if status == "running":
            values["started_at"] = datetime.utcnow()
        if status in ("completed", "failed", "cancelled"):
            values["completed_at"] = datetime.utcnow()
        try:
            async with AsyncSessionLocal() as session:
                await session.execute(
                    sa_update(Execution)
                    .where(Execution.id == execution_id)
                    .values(**values)
                )
                await session.commit()
        except Exception as e:
            logger.error(f"Failed to update execution {execution_id}: {e}")

    try:
        # Mark as running
        await update_status("running")
        logger.info(f"Workflow {execution_id} starting in-process")

        # Import and run engine
        from workflow.engine import WorkflowEngine
        from workflow.checkpoint import CheckpointManager
        from tasks.registry import get_task_registry

        task_registry = get_task_registry()
        checkpoint_mgr = CheckpointManager()

        async def on_step_complete(context, step_result):
            step_id = getattr(step_result, 'step_id', 'unknown')
            step_status = getattr(step_result, 'status', 'unknown')
            logger.info(f"Step {step_id} → {step_status} (execution: {execution_id})")

        engine = WorkflowEngine(
            task_registry=task_registry,
            checkpoint_manager=checkpoint_mgr,
            on_step_complete=on_step_complete,
        )

        context = await engine.execute(
            execution_id=execution_id,
            workflow_id=workflow_id,
            organization_id=organization_id,
            definition=definition,
            variables=variables,
        )

        duration_ms = int((time.time() - start_time) * 1000)

        # Check if any steps failed
        has_failures = any(
            hasattr(r, 'status') and str(r.status) == 'failed'
            for r in context.steps.values()
        )

        if has_failures:
            failed_steps = [
                sid for sid, r in context.steps.items()
                if hasattr(r, 'status') and str(r.status) == 'failed'
            ]
            await update_status(
                "failed",
                error_message=f"Steps failed: {', '.join(failed_steps)}",
                duration_ms=duration_ms,
            )
        else:
            await update_status("completed", duration_ms=duration_ms)

        logger.info(f"Workflow {execution_id} finished in {duration_ms}ms")

    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        error_msg = str(e)
        logger.error(f"Workflow {execution_id} failed: {error_msg}", exc_info=True)
        await update_status("failed", error_message=error_msg, duration_ms=duration_ms)
