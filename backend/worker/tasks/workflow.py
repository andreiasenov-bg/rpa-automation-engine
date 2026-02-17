"""Celery tasks for workflow execution.

These tasks bridge the Celery worker with the WorkflowEngine.
When a trigger fires or a user clicks "Execute", a Celery task
is dispatched to run the workflow asynchronously.

Status updates are written directly to the database so the frontend
can track progress in real time.
"""

import asyncio
import logging
import time
from datetime import datetime, timezone
from uuid import uuid4

from worker.celery_app import celery_app

logger = logging.getLogger(__name__)


# ─── Database helpers (run inside the worker's event loop) ───────

async def _update_execution_status(
    execution_id: str,
    status: str,
    error_message: str = None,
    duration_ms: int = None,
):
    """Update execution record directly via async session."""
    from db.session import AsyncSessionLocal
    from db.models.execution import Execution
    from sqlalchemy import update

    values: dict = {"status": status}
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
                update(Execution)
                .where(Execution.id == execution_id)
                .values(**values)
            )
            await session.commit()
        logger.info(f"Execution {execution_id} → {status}")
    except Exception as e:
        logger.error(f"Failed to update execution {execution_id} to {status}: {e}")


# ─── Main execution task ─────────────────────────────────────────

@celery_app.task(
    name="worker.tasks.workflow.execute_workflow",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    acks_late=True,
    queue="workflows",
)
def execute_workflow(
    self,
    execution_id: str,
    workflow_id: str,
    organization_id: str,
    definition: dict,
    variables: dict = None,
    trigger_payload: dict = None,
):
    """Execute a workflow in the background.

    Args:
        execution_id: Pre-generated execution UUID
        workflow_id: Workflow to execute
        organization_id: Owning org
        definition: Workflow definition (steps DAG)
        variables: Initial variables
        trigger_payload: Data from trigger
    """
    logger.info(f"Starting workflow execution: {execution_id} (workflow: {workflow_id})")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    start_time = time.time()

    try:
        # Mark as running
        loop.run_until_complete(
            _update_execution_status(execution_id, "running")
        )

        # Execute
        result = loop.run_until_complete(
            _run_workflow(
                execution_id=execution_id,
                workflow_id=workflow_id,
                organization_id=organization_id,
                definition=definition,
                variables=variables or {},
                trigger_payload=trigger_payload or {},
            )
        )

        duration_ms = int((time.time() - start_time) * 1000)

        # Mark as completed
        loop.run_until_complete(
            _update_execution_status(
                execution_id,
                "completed",
                duration_ms=duration_ms,
            )
        )

        logger.info(f"Workflow {execution_id} completed in {duration_ms}ms")
        return result

    except Exception as exc:
        duration_ms = int((time.time() - start_time) * 1000)
        error_msg = str(exc)
        logger.error(f"Workflow execution failed: {execution_id}: {error_msg}")

        # Mark as failed in DB
        try:
            loop.run_until_complete(
                _update_execution_status(
                    execution_id,
                    "failed",
                    error_message=error_msg,
                    duration_ms=duration_ms,
                )
            )
        except Exception:
            logger.error(f"Could not update failed status for {execution_id}")

        # Only retry on transient errors, not on workflow logic errors
        if self.request.retries < self.max_retries and _is_transient_error(exc):
            raise self.retry(exc=exc)
        # Don't retry workflow logic errors — they'll just fail again
        return {"error": error_msg, "status": "failed"}

    finally:
        loop.close()


def _is_transient_error(exc: Exception) -> bool:
    """Check if an error is transient (worth retrying)."""
    transient_types = (ConnectionError, TimeoutError, OSError)
    error_msg = str(exc).lower()
    transient_keywords = ["connection", "timeout", "unavailable", "reset"]
    return isinstance(exc, transient_types) or any(kw in error_msg for kw in transient_keywords)


# ─── Async workflow runner ──────────────────────────────────────

async def _run_workflow(
    execution_id: str,
    workflow_id: str,
    organization_id: str,
    definition: dict,
    variables: dict,
    trigger_payload: dict,
) -> dict:
    """Async workflow execution logic."""
    from workflow.engine import WorkflowEngine
    from workflow.checkpoint import CheckpointManager
    from tasks.registry import get_task_registry

    task_registry = get_task_registry()
    checkpoint_mgr = CheckpointManager()

    # Step progress callback — updates DB per step
    async def on_step_complete(context, step_result):
        """Callback fired after each step completes."""
        step_id = getattr(step_result, 'step_id', None) or 'unknown'
        status = getattr(step_result, 'status', 'unknown')
        logger.info(f"Step {step_id} → {status} (execution: {execution_id})")

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
        trigger_payload=trigger_payload,
    )

    return context.to_dict()


# ─── Resume task ─────────────────────────────────────────────────

@celery_app.task(
    name="worker.tasks.workflow.resume_workflow",
    bind=True,
    max_retries=1,
    queue="workflows",
)
def resume_workflow(self, execution_id: str, saved_state: dict):
    """Resume a workflow from a saved checkpoint.

    Args:
        execution_id: Execution to resume
        saved_state: Serialized ExecutionContext dict
    """
    logger.info(f"Resuming workflow execution: {execution_id}")

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(
                _resume_workflow(execution_id, saved_state)
            )
            return result
        finally:
            loop.close()

    except Exception as exc:
        logger.error(f"Workflow resume failed: {execution_id}: {exc}")
        raise self.retry(exc=exc)


async def _resume_workflow(execution_id: str, saved_state: dict) -> dict:
    """Async workflow resume logic."""
    from sqlalchemy import select
    from db.session import AsyncSessionLocal
    from db.models.workflow import Workflow
    from workflow.engine import WorkflowEngine, ExecutionContext
    from workflow.checkpoint import CheckpointManager
    from tasks.registry import get_task_registry

    task_registry = get_task_registry()
    checkpoint_mgr = CheckpointManager()

    engine = WorkflowEngine(
        task_registry=task_registry,
        checkpoint_manager=checkpoint_mgr,
    )

    resume_context = ExecutionContext.from_dict(saved_state)

    # Load workflow definition from DB
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Workflow).where(Workflow.id == resume_context.workflow_id)
        )
        workflow = result.scalar_one_or_none()

    if not workflow:
        raise RuntimeError(
            f"Cannot resume: workflow {resume_context.workflow_id} not found in DB"
        )

    definition = workflow.definition or {}

    context = await engine.execute(
        execution_id=execution_id,
        workflow_id=resume_context.workflow_id,
        organization_id=resume_context.organization_id,
        definition=definition,
        resume_context=resume_context,
    )

    return context.to_dict()
