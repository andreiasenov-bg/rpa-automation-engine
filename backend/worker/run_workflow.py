"""Shared helper to execute a workflow directly (no Celery dispatch).

Both the API manual-execute endpoint and the schedule poller need to run
the WorkflowEngine.  This module provides a single entry point that:

1. Creates a **fresh** SQLAlchemy engine / session (safe for bg threads)
2. Runs the engine
3. Persists results (status, duration, state_data) back to the DB
4. Cleans up resources

Usage from a synchronous context (thread / celery task)::

    from worker.run_workflow import run_workflow_sync
    run_workflow_sync(execution_id, workflow_id, org_id, definition)

Usage from an async context::

    from worker.run_workflow import run_workflow_async
    await run_workflow_async(execution_id, workflow_id, org_id, definition)
"""

import asyncio
import json as _json
import logging
import time
import threading
import traceback as tb_mod

logger = logging.getLogger(__name__)


# ── Serialization helper ────────────────────────────────────────

def _safe_serialize(obj, depth=0):
    """Recursively ensure all values are JSON-serializable."""
    if depth > 10:
        return str(obj)
    if obj is None or isinstance(obj, (bool, int, float)):
        return obj
    if isinstance(obj, str):
        return obj[:10000] if len(obj) > 10000 else obj
    if isinstance(obj, dict):
        return {str(k): _safe_serialize(v, depth + 1) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_safe_serialize(v, depth + 1) for v in obj]
    return str(obj)


# ── Core async runner ───────────────────────────────────────────

async def run_workflow_async(
    execution_id: str,
    workflow_id: str,
    organization_id: str,
    definition: dict,
    variables: dict | None = None,
    trigger_payload: dict | None = None,
):
    """Run a workflow with a fresh DB engine (safe for background threads).

    Updates the execution record to ``running`` → ``completed``/``failed``
    and persists step outputs into ``execution_states``.
    """
    from sqlalchemy.ext.asyncio import (
        create_async_engine,
        async_sessionmaker,
        AsyncSession as _AsyncSession,
    )
    from app.config import get_settings

    _settings = get_settings()
    _bg_engine = create_async_engine(
        _settings.DATABASE_URL, echo=False, future=True,
    )
    _BGSession = async_sessionmaker(
        _bg_engine, class_=_AsyncSession, expire_on_commit=False,
    )

    start = time.time()
    logger.info(f"[run-workflow] Starting {execution_id}")

    try:
        # Mark as running
        from sqlalchemy import text as sa_text

        async with _BGSession() as sess:
            await sess.execute(
                sa_text(
                    "UPDATE executions SET status='running', started_at=now() "
                    "WHERE id=:id"
                ),
                {"id": execution_id},
            )
            await sess.commit()

        # Run engine
        from workflow.engine import WorkflowEngine
        from workflow.checkpoint import CheckpointManager
        from tasks.registry import get_task_registry

        engine = WorkflowEngine(
            task_registry=get_task_registry(),
            checkpoint_manager=CheckpointManager(),
        )
        context = await engine.execute(
            execution_id=execution_id,
            workflow_id=workflow_id,
            organization_id=organization_id,
            definition=definition,
            variables=variables or {},
        )
        duration_ms = int((time.time() - start) * 1000)

        # Determine final status
        failed = [
            s
            for s, r in context.steps.items()
            if hasattr(r, "status")
            and (
                r.status.value == "failed"
                if hasattr(r.status, "value")
                else str(r.status) == "failed"
            )
        ]
        final_status = "failed" if failed else "completed"
        error_msg = f"Steps failed: {', '.join(failed)}" if failed else None

        # Serialize state
        state_data = {}
        try:
            steps_dict = {}
            for step_id, step_result in context.steps.items():
                sr = step_result
                raw_output = sr.output if hasattr(sr, "output") else None
                steps_dict[step_id] = {
                    "status": (
                        sr.status.value
                        if hasattr(sr.status, "value")
                        else str(sr.status)
                    ),
                    "output": _safe_serialize(raw_output),
                    "error": sr.error if hasattr(sr, "error") else None,
                    "duration_ms": (
                        sr.duration_ms if hasattr(sr, "duration_ms") else None
                    ),
                }
            state_data = {
                "steps": steps_dict,
                "variables": _safe_serialize(
                    dict(context.variables)
                    if hasattr(context, "variables")
                    else {}
                ),
            }
        except Exception as ser_err:
            logger.warning(f"[run-workflow] Serialize error: {ser_err}")
            state_data = {
                "steps": {},
                "variables": {},
                "serialization_error": str(ser_err),
            }

        # Persist results
        async with _BGSession() as sess:
            await sess.execute(
                sa_text(
                    "UPDATE executions "
                    "SET status=:s, duration_ms=:d, completed_at=now(), error_message=:e "
                    "WHERE id=:id"
                ),
                {
                    "s": final_status,
                    "d": duration_ms,
                    "e": error_msg,
                    "id": execution_id,
                },
            )
            await sess.execute(
                sa_text(
                    "INSERT INTO execution_states "
                    "(id, execution_id, state_data, updated_at, created_at, is_deleted) "
                    "VALUES (gen_random_uuid(), :exec_id, CAST(:state_data AS jsonb), now(), now(), false) "
                    "ON CONFLICT (execution_id) DO UPDATE "
                    "SET state_data = CAST(:state_data AS jsonb), updated_at = now()"
                ),
                {
                    "exec_id": execution_id,
                    "state_data": _json.dumps(state_data),
                },
            )
            await sess.commit()

        logger.info(
            f"[run-workflow] {execution_id}: {final_status} in {duration_ms}ms"
        )

        # Auto-save results to storage
        try:
            from services.storage_service import get_storage_service

            _storage = get_storage_service()
            _storage.save_execution_result(
                workflow_id, execution_id, state_data, format="json"
            )
        except Exception as store_err:
            logger.warning(f"[run-workflow] Storage save failed: {store_err}")

        # Cleanup browser sessions
        try:
            from tasks.implementations.browser_task import BrowserSessionManager

            await BrowserSessionManager.cleanup_all()
        except Exception:
            pass

    except Exception as e:
        duration_ms = int((time.time() - start) * 1000)
        logger.error(
            f"[run-workflow] {execution_id} crashed: {e}\n{tb_mod.format_exc()}"
        )
        try:
            async with _BGSession() as sess:
                await sess.execute(
                    sa_text(
                        "UPDATE executions "
                        "SET status='failed', duration_ms=:d, completed_at=now(), "
                        "error_message=:e WHERE id=:id"
                    ),
                    {"d": duration_ms, "e": str(e)[:500], "id": execution_id},
                )
                await sess.commit()
        except Exception as db_err:
            logger.error(f"[run-workflow] DB update also failed: {db_err}")

    finally:
        await _bg_engine.dispose()


# ── Sync wrappers ───────────────────────────────────────────────

def run_workflow_sync(
    execution_id: str,
    workflow_id: str,
    organization_id: str,
    definition: dict,
    variables: dict | None = None,
    trigger_payload: dict | None = None,
):
    """Run a workflow synchronously (blocks until done).

    Creates its own event loop — safe for threads or Celery tasks.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(
            run_workflow_async(
                execution_id=execution_id,
                workflow_id=workflow_id,
                organization_id=organization_id,
                definition=definition,
                variables=variables,
                trigger_payload=trigger_payload,
            )
        )
    except Exception as e:
        logger.error(f"[run-workflow] sync wrapper error: {e}\n{tb_mod.format_exc()}")
    finally:
        loop.close()


def launch_workflow_thread(
    execution_id: str,
    workflow_id: str,
    organization_id: str,
    definition: dict,
    variables: dict | None = None,
    trigger_payload: dict | None = None,
) -> threading.Thread:
    """Launch workflow in a background daemon thread.

    Returns the thread object (already started).
    """
    t = threading.Thread(
        target=run_workflow_sync,
        args=(execution_id, workflow_id, organization_id, definition),
        kwargs={"variables": variables, "trigger_payload": trigger_payload},
        daemon=True,
        name=f"wf-{execution_id[:8]}",
    )
    t.start()
    logger.info(f"[run-workflow] Launched thread {t.name} for {execution_id}")
    return t
