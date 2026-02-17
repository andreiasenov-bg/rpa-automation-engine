"""Celery task to poll schedules and trigger workflow executions.

This task runs every minute via Celery Beat, checks for enabled schedules
whose next_run_at <= now(), and dispatches workflow executions for them.
After dispatching, it updates next_run_at to the next occurrence.
"""

import asyncio
import logging
from datetime import datetime, timezone
from uuid import uuid4

from worker.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="worker.tasks.schedule_poller.poll_schedules",
    bind=True,
    max_retries=1,
    default_retry_delay=30,
    queue="triggers",
)
def poll_schedules(self):
    """Check for due schedules and trigger workflow executions."""
    logger.info("Polling schedules for due executions...")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(_poll_and_dispatch())
        return result
    except Exception as exc:
        logger.error(f"Schedule polling failed: {exc}")
        raise self.retry(exc=exc)
    finally:
        loop.close()


async def _poll_and_dispatch() -> dict:
    """Find due schedules and dispatch workflow executions."""
    from sqlalchemy import select, update
    from db.session import AsyncSessionLocal
    from db.models.schedule import Schedule
    from db.models.workflow import Workflow
    from db.models.execution import Execution

    now = datetime.now(timezone.utc)
    dispatched = 0
    errors = 0

    async with AsyncSessionLocal() as session:
        # Find all enabled schedules where next_run_at <= now
        stmt = (
            select(Schedule)
            .where(Schedule.is_enabled == True)
            .where(Schedule.next_run_at != None)
            .where(Schedule.next_run_at <= now)
        )
        result = await session.execute(stmt)
        due_schedules = result.scalars().all()

        if not due_schedules:
            logger.info("No due schedules found.")
            return {"dispatched": 0, "errors": 0}

        logger.info(f"Found {len(due_schedules)} due schedule(s)")

        for schedule in due_schedules:
            try:
                # Get the workflow
                wf_stmt = select(Workflow).where(Workflow.id == schedule.workflow_id)
                wf_result = await session.execute(wf_stmt)
                workflow = wf_result.scalar_one_or_none()

                if not workflow or not workflow.is_enabled:
                    logger.warning(
                        f"Skipping schedule {schedule.id}: workflow "
                        f"{schedule.workflow_id} not found or disabled"
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

                # Compute next_run_at
                next_run = _compute_next_run(
                    schedule.cron_expression, schedule.timezone
                )
                schedule.next_run_at = next_run

                await session.commit()

                # Dispatch to Celery worker
                from worker.tasks.workflow import execute_workflow

                execute_workflow.delay(
                    execution_id=execution_id,
                    workflow_id=str(schedule.workflow_id),
                    organization_id=str(schedule.organization_id),
                    definition=workflow.definition or {},
                    variables={},
                    trigger_payload={"schedule_id": str(schedule.id)},
                )

                dispatched += 1
                logger.info(
                    f"Dispatched execution {execution_id} for schedule "
                    f"'{schedule.name}' (workflow: {workflow.name}). "
                    f"Next run: {next_run}"
                )

            except Exception as e:
                errors += 1
                logger.error(
                    f"Error dispatching schedule {schedule.id}: {e}",
                    exc_info=True,
                )
                await session.rollback()

    return {"dispatched": dispatched, "errors": errors}


def _compute_next_run(cron_expression: str, tz: str = "UTC"):
    """Compute the next run time from a cron expression."""
    try:
        from croniter import croniter
        import pytz

        tz_obj = pytz.timezone(tz)
        now = datetime.now(tz_obj)
        cron = croniter(cron_expression, now)
        return cron.get_next(datetime).astimezone(pytz.utc)
    except ImportError:
        logger.warning("croniter not installed — cannot compute next_run_at")
        return None
    except Exception as e:
        logger.error(f"Failed to compute next run: {e}")
        return None
