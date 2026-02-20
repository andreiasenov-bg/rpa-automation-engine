"""Celery tasks for maintenance and cleanup.

Runs daily at 3 AM (configured in beat_schedule) and performs:
1. Purge execution logs older than retention period
2. Hard-delete soft-deleted records older than 30 days
3. Clean up orphaned checkpoint/journal data
4. Purge expired execution states for completed/failed runs
5. Archive old audit logs to a summary row (optional future)
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from worker.celery_app import celery_app
import sys
if "/app" not in sys.path:
    sys.path.insert(0, "/app")

logger = logging.getLogger(__name__)

# Retention settings (days)
EXECUTION_LOG_RETENTION_DAYS = 90
SOFT_DELETE_PURGE_DAYS = 30
CHECKPOINT_RETENTION_DAYS = 14
AUDIT_LOG_RETENTION_DAYS = 365


@celery_app.task(
    name="worker.tasks.maintenance.cleanup_old_data",
    queue="default",
)
def cleanup_old_data():
    """Clean up old execution logs and expired data.

    Runs daily at 3 AM (configured in beat_schedule).
    """
    logger.info("Running daily cleanup")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(_run_cleanup())
        logger.info("Daily cleanup completed: %s", result)
        return result
    except Exception as exc:
        logger.error("Daily cleanup failed: %s", exc, exc_info=True)
        return {"status": "error", "error": str(exc)}
    finally:
        loop.close()


async def _run_cleanup() -> dict:
    """Async cleanup logic with DB access."""
    from sqlalchemy import delete, select, and_
    from db.session import AsyncSessionLocal
    from db.models.execution_log import ExecutionLog
    from db.models.execution import Execution
    from db.models.execution_state import (
        ExecutionStateModel,
        ExecutionCheckpointModel,
        ExecutionJournalModel,
    )
    from db.models.audit_log import AuditLog

    now = datetime.now(timezone.utc)
    stats = {
        "execution_logs_deleted": 0,
        "soft_deleted_purged": 0,
        "checkpoints_purged": 0,
        "journal_entries_purged": 0,
        "execution_states_purged": 0,
    }

    async with AsyncSessionLocal() as session:
        try:
            # 1. Delete execution logs older than retention period
            log_cutoff = now - timedelta(days=EXECUTION_LOG_RETENTION_DAYS)
            result = await session.execute(
                delete(ExecutionLog).where(
                    ExecutionLog.timestamp < log_cutoff.replace(tzinfo=None)
                )
            )
            stats["execution_logs_deleted"] = result.rowcount
            logger.info(
                "Purged %d execution logs older than %d days",
                result.rowcount,
                EXECUTION_LOG_RETENTION_DAYS,
            )

            # 2. Hard-delete soft-deleted records older than 30 days
            purge_cutoff = now - timedelta(days=SOFT_DELETE_PURGE_DAYS)
            # Purge soft-deleted executions (cascades to logs)
            result = await session.execute(
                delete(Execution).where(
                    and_(
                        Execution.is_deleted == True,
                        Execution.deleted_at < purge_cutoff,
                    )
                )
            )
            stats["soft_deleted_purged"] += result.rowcount
            logger.info(
                "Purged %d soft-deleted executions older than %d days",
                result.rowcount,
                SOFT_DELETE_PURGE_DAYS,
            )

            # 3. Clean up orphaned checkpoint data for completed/failed executions
            checkpoint_cutoff = now - timedelta(days=CHECKPOINT_RETENTION_DAYS)

            # Find execution IDs that are terminal (completed/failed/cancelled)
            # and older than retention period
            terminal_exec_ids = await session.execute(
                select(Execution.id).where(
                    and_(
                        Execution.status.in_(["completed", "failed", "cancelled"]),
                        Execution.completed_at != None,
                        Execution.completed_at < checkpoint_cutoff.replace(tzinfo=None),
                    )
                )
            )
            old_exec_ids = [row[0] for row in terminal_exec_ids.all()]

            if old_exec_ids:
                # Delete checkpoints in batches
                for i in range(0, len(old_exec_ids), 500):
                    batch = old_exec_ids[i : i + 500]

                    result = await session.execute(
                        delete(ExecutionCheckpointModel).where(
                            ExecutionCheckpointModel.execution_id.in_(batch)
                        )
                    )
                    stats["checkpoints_purged"] += result.rowcount

                    result = await session.execute(
                        delete(ExecutionJournalModel).where(
                            ExecutionJournalModel.execution_id.in_(batch)
                        )
                    )
                    stats["journal_entries_purged"] += result.rowcount

                    result = await session.execute(
                        delete(ExecutionStateModel).where(
                            ExecutionStateModel.execution_id.in_(batch)
                        )
                    )
                    stats["execution_states_purged"] += result.rowcount

                logger.info(
                    "Purged checkpoint/journal/state data for %d terminal executions",
                    len(old_exec_ids),
                )

            await session.commit()

        except Exception:
            await session.rollback()
            raise

    stats["status"] = "completed"
    return stats
