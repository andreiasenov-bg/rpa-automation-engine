"""Celery tasks for workflow execution.

These tasks bridge the Celery worker with the WorkflowEngine.
When a trigger fires or a user clicks "Execute", a Celery task
is dispatched to run the workflow asynchronously.

Status updates are written directly to the database so the frontend
can track progress in real time.
"""

import asyncio
import json as _json
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

        # Send failure notification (async, non-blocking)
        try:
            loop.run_until_complete(
                _send_fail_notification(
                    execution_id=execution_id,
                    workflow_id=workflow_id,
                    organization_id=organization_id,
                    error_message=error_msg,
                )
            )
        except Exception as notify_exc:
            logger.warning(f"Failed to send failure notification: {notify_exc}")

        # ── AI Auto-Diagnosis (non-blocking) ──
        # Analyze the error with Claude and store diagnosis.
        # If the error is auto-fixable (e.g. transient), retry automatically.
        try:
            loop.run_until_complete(
                _ai_diagnose_and_maybe_fix(
                    execution_id=execution_id,
                    workflow_id=workflow_id,
                    organization_id=organization_id,
                    error_message=error_msg,
                    definition=definition,
                )
            )
        except Exception as ai_exc:
            logger.warning(f"AI diagnosis failed (non-critical): {ai_exc}")

        # Only retry on transient errors, not on workflow logic errors
        if self.request.retries < self.max_retries and _is_transient_error(exc):
            raise self.retry(exc=exc)
        # Don't retry workflow logic errors — they'll just fail again
        return {"error": error_msg, "status": "failed"}

    finally:
        loop.close()


async def _send_fail_notification(
    execution_id: str,
    workflow_id: str,
    organization_id: str,
    error_message: str,
) -> None:
    """Send notification to all configured channels when a workflow fails."""
    from sqlalchemy import select
    from db.session import AsyncSessionLocal
    from db.models.workflow import Workflow
    from notifications.manager import get_notification_manager

    # Get workflow name
    workflow_name = workflow_id[:8]
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Workflow.name).where(Workflow.id == workflow_id)
            )
            row = result.scalar_one_or_none()
            if row:
                workflow_name = row
    except Exception:
        pass

    manager = get_notification_manager()
    await manager.notify_workflow_failed(
        workflow_name=workflow_name,
        execution_id=execution_id,
        error=error_message[:500],
        organization_id=organization_id,
    )


async def _ai_diagnose_and_maybe_fix(
    execution_id: str,
    workflow_id: str,
    organization_id: str,
    error_message: str,
    definition: dict,
) -> None:
    """
    AI-powered error diagnosis.

    1. Calls ClaudeClient.analyze() to understand the failure
    2. Stores diagnosis in execution_journals table
    3. If auto-fixable (e.g. transient/rate-limit), triggers retry

    This runs in the worker after failure and is non-blocking.
    """
    from sqlalchemy import text as sa_text
    from db.session import AsyncSessionLocal

    # Get workflow name
    workflow_name = workflow_id[:8]
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(sa_text(
                "SELECT name FROM workflows WHERE id = :wid"
            ), {"wid": workflow_id})
            row = result.fetchone()
            if row:
                workflow_name = row[0]
    except Exception:
        pass

    # Get step-level errors from execution_states
    step_errors = []
    try:
        async with AsyncSessionLocal() as session:
            state_row = (await session.execute(sa_text(
                "SELECT state_data FROM execution_states WHERE execution_id = :eid LIMIT 1"
            ), {"eid": execution_id})).fetchone()
            if state_row and state_row[0]:
                sd = state_row[0] if isinstance(state_row[0], dict) else _json.loads(state_row[0])
                steps = sd.get("steps", {})
                for sid, si in (steps.items() if isinstance(steps, dict) else []):
                    if isinstance(si, dict) and si.get("error"):
                        step_errors.append({
                            "step": sid,
                            "error": str(si["error"])[:300],
                            "status": si.get("status", "unknown"),
                        })
    except Exception:
        pass

    # Build prompt for AI
    prompt = f"""You are an RPA workflow diagnostic AI. Analyze this execution failure.

WORKFLOW: {workflow_name}
EXECUTION ID: {execution_id}
MAIN ERROR: {error_message[:500]}

STEP-LEVEL ERRORS:
{_json.dumps(step_errors, indent=2) if step_errors else "None captured."}

WORKFLOW STEPS (first 5):
{_json.dumps(definition.get('steps', [])[:5], indent=2, default=str)[:1500]}

Provide diagnosis as JSON:
{{
  "diagnosis": "What went wrong and why (1-2 sentences)",
  "root_cause": "connection_error|auth_error|data_error|config_error|rate_limit|site_changed|timeout|unknown",
  "severity": "low|medium|high|critical",
  "fix_suggestion": "Actionable fix (1 sentence)",
  "auto_fixable": true/false,
  "auto_fix_action": "retry|update_config|null",
  "confidence": 0.0-1.0
}}"""

    # Call ClaudeClient
    diagnosis = None
    try:
        from integrations.claude_client import get_claude_client
        ai = get_claude_client()
        raw = await ai.analyze(prompt, output_format="json")
        if isinstance(raw, str):
            diagnosis = ai.safe_extract_json(raw)
        elif isinstance(raw, dict):
            diagnosis = raw
    except Exception as ai_err:
        logger.warning(f"ClaudeClient unavailable for diagnosis: {ai_err}")
        # Fallback: rule-based diagnosis
        diagnosis = _rule_based_diagnosis(error_message)

    if not diagnosis:
        diagnosis = _rule_based_diagnosis(error_message)

    # Store diagnosis in execution_journals
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(sa_text("""
                INSERT INTO execution_journals
                (id, execution_id, event_type, severity, details, created_at)
                VALUES (gen_random_uuid(), :eid, 'ai_diagnosis', :severity,
                        CAST(:details AS jsonb), NOW())
            """), {
                "eid": execution_id,
                "severity": diagnosis.get("severity", "medium"),
                "details": _json.dumps(diagnosis),
            })
            await session.commit()
        logger.info(f"AI diagnosis stored for execution {execution_id}: {diagnosis.get('root_cause', 'unknown')}")
    except Exception as db_err:
        logger.warning(f"Could not store AI diagnosis: {db_err}")

    # Auto-fix: if transient and auto-fixable, trigger retry
    if diagnosis.get("auto_fixable") and diagnosis.get("auto_fix_action") == "retry":
        try:
            new_exec_id = str(uuid4())
            async with AsyncSessionLocal() as session:
                await session.execute(sa_text("""
                    INSERT INTO executions
                    (id, workflow_id, status, trigger_type, created_at)
                    VALUES (:eid, :wid, 'pending', 'ai_retry', NOW())
                """), {"eid": new_exec_id, "wid": workflow_id})
                await session.commit()

            # Dispatch new execution
            execute_workflow.delay(
                execution_id=new_exec_id,
                workflow_id=workflow_id,
                organization_id=organization_id,
                definition=definition,
            )

            # Log auto-fix
            async with AsyncSessionLocal() as session:
                await session.execute(sa_text("""
                    INSERT INTO execution_journals
                    (id, execution_id, event_type, severity, details, created_at)
                    VALUES (gen_random_uuid(), :eid, 'ai_auto_fix', 'info',
                            CAST(:details AS jsonb), NOW())
                """), {
                    "eid": execution_id,
                    "details": _json.dumps({
                        "action": "retry",
                        "new_execution_id": new_exec_id,
                        "reason": diagnosis.get("diagnosis", "Auto-retry after AI analysis"),
                    }),
                })
                await session.commit()

            logger.info(f"AI auto-retry: new execution {new_exec_id} from failed {execution_id}")

        except Exception as retry_err:
            logger.warning(f"AI auto-retry failed: {retry_err}")


def _rule_based_diagnosis(error_message: str) -> dict:
    """Fallback rule-based diagnosis when AI is unavailable."""
    error_lower = error_message.lower()

    if any(kw in error_lower for kw in ["timeout", "timed out"]):
        return {
            "diagnosis": "The execution timed out, likely due to slow response from target service.",
            "root_cause": "timeout",
            "severity": "medium",
            "fix_suggestion": "Increase timeout settings or check if target service is responding slowly.",
            "auto_fixable": True,
            "auto_fix_action": "retry",
            "confidence": 0.8,
        }
    elif any(kw in error_lower for kw in ["connection", "connect", "refused", "reset"]):
        return {
            "diagnosis": "Connection error — target service may be down or network issue.",
            "root_cause": "connection_error",
            "severity": "high",
            "fix_suggestion": "Check network connectivity and target service availability.",
            "auto_fixable": True,
            "auto_fix_action": "retry",
            "confidence": 0.7,
        }
    elif any(kw in error_lower for kw in ["401", "403", "unauthorized", "forbidden", "auth"]):
        return {
            "diagnosis": "Authentication/authorization failure — credentials may be expired or invalid.",
            "root_cause": "auth_error",
            "severity": "high",
            "fix_suggestion": "Check and refresh API credentials in the Credentials page.",
            "auto_fixable": False,
            "auto_fix_action": None,
            "confidence": 0.85,
        }
    elif any(kw in error_lower for kw in ["429", "rate limit", "too many requests", "throttl"]):
        return {
            "diagnosis": "Rate limited by the target API — too many requests in short time.",
            "root_cause": "rate_limit",
            "severity": "medium",
            "fix_suggestion": "Wait a few minutes and retry. Consider adding delays between requests.",
            "auto_fixable": True,
            "auto_fix_action": "retry",
            "confidence": 0.9,
        }
    elif any(kw in error_lower for kw in ["selector", "element not found", "no such element", "css"]):
        return {
            "diagnosis": "Web scraping selector failed — the target website structure may have changed.",
            "root_cause": "site_changed",
            "severity": "high",
            "fix_suggestion": "Update CSS selectors to match the current site structure.",
            "auto_fixable": False,
            "auto_fix_action": None,
            "confidence": 0.75,
        }
    elif any(kw in error_lower for kw in ["404", "not found"]):
        return {
            "diagnosis": "Target resource not found (404) — URL may have changed.",
            "root_cause": "config_error",
            "severity": "high",
            "fix_suggestion": "Verify the target URL is still valid and update if needed.",
            "auto_fixable": False,
            "auto_fix_action": None,
            "confidence": 0.8,
        }
    elif any(kw in error_lower for kw in ["500", "internal server error", "502", "503"]):
        return {
            "diagnosis": "Target server error — the remote service is experiencing issues.",
            "root_cause": "connection_error",
            "severity": "medium",
            "fix_suggestion": "The target service has issues. Retry later.",
            "auto_fixable": True,
            "auto_fix_action": "retry",
            "confidence": 0.7,
        }
    else:
        return {
            "diagnosis": f"Execution failed with error: {error_message[:150]}",
            "root_cause": "unknown",
            "severity": "medium",
            "fix_suggestion": "Check the execution logs for detailed error information.",
            "auto_fixable": False,
            "auto_fix_action": None,
            "confidence": 0.3,
        }


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
