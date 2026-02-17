"""Celery task to poll schedules and trigger workflow executions.

This task runs every minute via Celery Beat, checks for enabled schedules
whose next_run_at <= now(), and dispatches workflow executions for them.
After dispatching, it updates next_run_at to the next occurrence.

Important: All datetime comparisons use NAIVE UTC to match the database
column type (TIMESTAMP WITHOUT TIME ZONE).  ``_compute_next_run`` also
returns naive UTC datetimes.
"""

import asyncio
import logging
from datetime import datetime, timezone
from uuid import uuid4

from worker.celery_app import celery_app

logger = logging.getLogger(__name__)


def _utcnow_naive() -> datetime:
    """Return the current UTC time as a **naive** datetime.

    PostgreSQL ``TIMESTAMP WITHOUT TIME ZONE`` columns store naive
    timestamps, so all comparisons must also be naive-UTC.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


@celery_app.task(
    name="worker.tasks.schedule_poller.poll_schedules",
    bind=True,
    max_retries=2,
    default_retry_delay=15,
    queue="triggers",
)
def poll_schedules(self):
    """Check for due schedules and trigger workflow executions."""
    logger.info("[schedule-poller] Polling schedules for due executions...")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(_poll_and_dispatch())
        logger.info(f"[schedule-poller] Done — {result}")
        return result
    except Exception as exc:
        logger.error(f"[schedule-poller] Polling failed: {exc}", exc_info=True)
        raise self.retry(exc=exc)
    finally:
        loop.close()


async def _poll_and_dispatch() -> dict:
    """Find due schedules and dispatch workflow executions."""
    from sqlalchemy import select
    from db.session import AsyncSessionLocal
    from db.models.schedule import Schedule
    from db.models.workflow import Workflow
    from db.models.execution import Execution

    now = _utcnow_naive()
    dispatched = 0
    errors = 0

    logger.info(f"[schedule-poller] Current UTC (naive): {now.isoformat()}")

    async with AsyncSessionLocal() as session:
        # Find all enabled, non-deleted schedules where next_run_at <= now
        stmt = (
            select(Schedule)
            .where(Schedule.is_enabled == True)       # noqa: E712
            .where(Schedule.is_deleted == False)       # noqa: E712
            .where(Schedule.next_run_at != None)       # noqa: E711
            .where(Schedule.next_run_at <= now)
        )
        result = await session.execute(stmt)
        due_schedules = result.scalars().all()

        if not due_schedules:
            logger.debug("[schedule-poller] No due schedules found.")
            return {"dispatched": 0, "errors": 0}

        logger.info(
            f"[schedule-poller] Found {len(due_schedules)} due schedule(s): "
            + ", ".join(
                f"'{s.name}' (next_run_at={s.next_run_at})" for s in due_schedules
            )
        )

        for schedule in due_schedules:
            try:
                # Get the workflow
                wf_stmt = select(Workflow).where(Workflow.id == schedule.workflow_id)
                wf_result = await session.execute(wf_stmt)
                workflow = wf_result.scalar_one_or_none()

                if not workflow or not workflow.is_enabled:
                    logger.warning(
                        f"[schedule-poller] Skipping schedule {schedule.id}: "
                        f"workflow {schedule.workflow_id} not found or disabled"
                    )
                    continue

                # Create execution record
                execution_id = str(uuid4())
                execution = Execution(
                    id=execution_id,
                    organization_id=schedule.organization_id,
                    workflow_id=schedule.workflow_id,
                    trigger_type="schedule",
                    status="pending",
                )
                session.add(execution)

                # Compute next_run_at — if it fails, keep the OLD value
                # (prevents schedule from being lost forever)
                next_run = _compute_next_run(
                    schedule.cron_expression, schedule.timezone
                )
                if next_run is not None:
                    schedule.next_run_at = next_run
                else:
                    # Fallback: add 60 seconds so poller retries next minute
                    logger.warning(
                        f"[schedule-poller] _compute_next_run returned None "
                        f"for schedule '{schedule.name}' — setting retry in 60s"
                    )
                    from datetime import timedelta
                    schedule.next_run_at = now + timedelta(seconds=60)

                await session.commit()

                # Run workflow directly (same process, new event loop
                # in a background thread) — avoids Celery dispatch issues
                from worker.run_workflow import launch_workflow_thread

                launch_workflow_thread(
                    execution_id=execution_id,
                    workflow_id=str(schedule.workflow_id),
                    organization_id=str(schedule.organization_id),
                    definition=workflow.definition or {},
                    variables={},
                    trigger_payload={"schedule_id": str(schedule.id)},
                )

                dispatched += 1
                logger.info(
                    f"[schedule-poller] Dispatched execution {execution_id} "
                    f"for schedule '{schedule.name}' "
                    f"(workflow: {workflow.name}). Next run: {next_run}"
                )

            except Exception as e:
                errors += 1
                logger.error(
                    f"[schedule-poller] Error dispatching schedule "
                    f"{schedule.id}: {e}",
                    exc_info=True,
                )
                await session.rollback()

    return {"dispatched": dispatched, "errors": errors}


def _compute_next_run(cron_expression: str, tz: str = "UTC"):
    """Compute the next run time from a cron expression.

    Returns a **naive UTC** datetime suitable for storing in a
    ``TIMESTAMP WITHOUT TIME ZONE`` column.
    """
    try:
        from croniter import croniter
        from zoneinfo import ZoneInfo

        tz_obj = ZoneInfo(tz)
        now_local = datetime.now(tz_obj)
        cron = croniter(cron_expression, now_local)
        next_local = cron.get_next(datetime)
        # Convert to UTC and strip tzinfo → naive UTC
        next_utc = next_local.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
        logger.debug(
            f"[schedule-poller] Next run for '{cron_expression}' "
            f"tz={tz}: {next_utc} UTC"
        )
        return next_utc
    except ImportError as exc:
        logger.error(f"[schedule-poller] croniter/zoneinfo not available: {exc}")
        return None
    except Exception as e:
        logger.error(f"[schedule-poller] Failed to compute next run: {e}")
        return None
