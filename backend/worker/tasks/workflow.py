"""Celery tasks for workflow execution.

These tasks bridge the Celery worker with the WorkflowEngine.
When a trigger fires or a user clicks "Execute", a Celery task
is dispatched to run the workflow asynchronously.
"""

import asyncio
import logging
from uuid import uuid4

from worker.celery_app import celery_app

logger = logging.getLogger(__name__)


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

    try:
        # Run async engine in sync Celery context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
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
            return result
        finally:
            loop.close()

    except Exception as exc:
        logger.error(f"Workflow execution failed: {execution_id}: {exc}")
        raise self.retry(exc=exc)


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

    engine = WorkflowEngine(
        task_registry=task_registry,
        checkpoint_manager=checkpoint_mgr,
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

    # TODO: Load workflow definition from DB using resume_context.workflow_id
    definition = {}  # Placeholder

    context = await engine.execute(
        execution_id=execution_id,
        workflow_id=resume_context.workflow_id,
        organization_id=resume_context.organization_id,
        definition=definition,
        resume_context=resume_context,
    )

    return context.to_dict()
