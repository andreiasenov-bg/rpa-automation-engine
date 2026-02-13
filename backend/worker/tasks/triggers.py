"""Celery tasks for trigger-related operations."""

import asyncio
import logging

from worker.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="worker.tasks.triggers.execute_trigger",
    bind=True,
    max_retries=2,
    default_retry_delay=10,
    queue="triggers",
)
def execute_trigger(self, trigger_id: str):
    """Fire a trigger (called by Celery beat for scheduled triggers).

    Args:
        trigger_id: ID of the trigger to fire
    """
    logger.info(f"Executing scheduled trigger: {trigger_id}")

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(_fire_trigger(trigger_id))
            return result
        finally:
            loop.close()
    except Exception as exc:
        logger.error(f"Trigger execution failed: {trigger_id}: {exc}")
        raise self.retry(exc=exc)


async def _fire_trigger(trigger_id: str) -> dict:
    """Async trigger fire logic."""
    from triggers.manager import get_trigger_manager

    manager = get_trigger_manager()
    result = await manager.fire_trigger(trigger_id)
    return {
        "success": result.success,
        "message": result.message,
        "execution_id": result.execution_id,
    }
