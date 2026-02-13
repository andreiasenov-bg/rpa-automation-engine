"""
Execution Recovery Service.

Automatically detects and resumes interrupted workflow executions
after server crashes, restarts, or unexpected shutdowns.

Recovery flow:
1. On startup, scan DB for executions with status "running" or "paused"
2. Load their checkpoint state
3. Determine resume point (last completed step + 1)
4. Re-queue them for execution from that point
5. Notify via WebSocket that execution was recovered

This ensures zero data loss and seamless continuation.
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

import structlog

from workflow.checkpoint import CheckpointManager, CheckpointType, ExecutionState

logger = structlog.get_logger(__name__)


class RecoveryResult:
    """Result of a recovery attempt for a single execution."""

    def __init__(self, execution_id: str):
        self.execution_id = execution_id
        self.recovered: bool = False
        self.resume_from_step: int = 0
        self.completed_steps_count: int = 0
        self.total_steps: int = 0
        self.error: Optional[str] = None
        self.timestamp = datetime.now(timezone.utc)

    def to_dict(self) -> dict:
        return {
            "execution_id": self.execution_id,
            "recovered": self.recovered,
            "resume_from_step": self.resume_from_step,
            "completed_steps_count": self.completed_steps_count,
            "total_steps": self.total_steps,
            "error": self.error,
            "timestamp": self.timestamp.isoformat(),
        }


class RecoveryService:
    """
    Handles recovery of interrupted executions on startup.

    Integrates with CheckpointManager to restore state
    and with the execution engine to resume workflows.
    """

    def __init__(self, checkpoint_manager: CheckpointManager, db_session=None):
        self.checkpoint_manager = checkpoint_manager
        self.db_session = db_session
        self._recovery_log: List[RecoveryResult] = []

    async def scan_interrupted_executions(self) -> List[str]:
        """
        Scan database for executions that were interrupted.

        Looks for executions with status 'running' or 'retrying'
        that haven't been updated in the last 5 minutes (stale).
        """
        if not self.db_session:
            logger.warning("No DB session for recovery scan")
            return []

        try:
            from sqlalchemy import text
            stale_threshold = datetime.now(timezone.utc) - timedelta(minutes=5)

            result = await self.db_session.execute(
                text("""
                    SELECT execution_id
                    FROM execution_states
                    WHERE state_data::jsonb->>'status' IN ('running', 'retrying', 'paused')
                    AND updated_at < :threshold
                    ORDER BY updated_at ASC
                """),
                {"threshold": stale_threshold},
            )
            rows = result.fetchall()
            execution_ids = [row[0] for row in rows]

            if execution_ids:
                logger.info(
                    "Found interrupted executions",
                    count=len(execution_ids),
                    execution_ids=execution_ids[:10],
                )

            return execution_ids

        except Exception as e:
            logger.error("Recovery scan failed", error=str(e))
            return []

    async def recover_execution(self, execution_id: str) -> RecoveryResult:
        """
        Attempt to recover a single interrupted execution.

        Steps:
        1. Load checkpoint state from DB
        2. Validate state is recoverable
        3. Mark as "resuming"
        4. Return recovery info for the execution engine
        """
        result = RecoveryResult(execution_id)

        try:
            # Load persisted state
            state = await self.checkpoint_manager.load_state(execution_id)
            if not state:
                result.error = "No checkpoint state found"
                logger.warning("No state found for recovery", execution_id=execution_id)
                self._recovery_log.append(result)
                return result

            if not state.can_resume:
                result.error = f"Execution in non-resumable state: {state.status}"
                logger.info("Execution cannot be resumed", execution_id=execution_id, status=state.status)
                self._recovery_log.append(result)
                return result

            # Calculate resume point
            result.resume_from_step = state.next_step_index
            result.completed_steps_count = len(state.completed_steps)
            result.total_steps = state.total_steps
            result.recovered = True

            # Save recovery checkpoint
            await self.checkpoint_manager.save_checkpoint(
                execution_id=execution_id,
                checkpoint_type=CheckpointType.EXECUTION_RESUMED,
                step_index=state.next_step_index,
                data={
                    "recovered_at": datetime.now(timezone.utc).isoformat(),
                    "resume_from_step": state.next_step_index,
                    "completed_steps": state.completed_steps,
                    "reason": "automatic_recovery_after_interruption",
                },
            )

            logger.info(
                "Execution recovered successfully",
                execution_id=execution_id,
                resume_from=state.next_step_index,
                completed=len(state.completed_steps),
                total=state.total_steps,
                progress=f"{state.progress_percent}%",
            )

        except Exception as e:
            result.error = str(e)
            logger.error("Recovery failed", execution_id=execution_id, error=str(e))

        self._recovery_log.append(result)
        return result

    async def recover_all(self) -> List[RecoveryResult]:
        """
        Scan and recover all interrupted executions.

        Called on application startup.
        Returns list of recovery results.
        """
        logger.info("Starting execution recovery scan...")

        interrupted_ids = await self.scan_interrupted_executions()
        if not interrupted_ids:
            logger.info("No interrupted executions found")
            return []

        results = []
        for execution_id in interrupted_ids:
            result = await self.recover_execution(execution_id)
            results.append(result)

            # Small delay between recoveries to not overwhelm the system
            await asyncio.sleep(0.1)

        recovered_count = sum(1 for r in results if r.recovered)
        failed_count = sum(1 for r in results if not r.recovered)

        logger.info(
            "Recovery scan complete",
            total=len(results),
            recovered=recovered_count,
            failed=failed_count,
        )

        return results

    def get_recovery_log(self) -> List[dict]:
        """Get the recovery log for admin dashboard."""
        return [r.to_dict() for r in self._recovery_log]


class ExecutionJournal:
    """
    Persistent journal of all execution events.

    Every meaningful event during an execution is recorded here:
    - Start, pause, resume, complete, fail
    - Each step start/end with timing
    - Variable changes
    - AI conversation turns
    - Retry attempts
    - Recovery events

    This provides a complete audit trail and debugging history.
    """

    def __init__(self, db_session=None):
        self.db_session = db_session

    async def record_event(
        self,
        execution_id: str,
        event_type: str,
        message: str,
        details: Optional[dict] = None,
        step_id: Optional[str] = None,
        step_index: Optional[int] = None,
        severity: str = "info",
    ):
        """Record an event in the execution journal."""
        event = {
            "execution_id": execution_id,
            "event_type": event_type,
            "message": message,
            "details": details or {},
            "step_id": step_id,
            "step_index": step_index,
            "severity": severity,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        logger.log(
            severity,
            message,
            execution_id=execution_id,
            event_type=event_type,
            step_id=step_id,
        )

        if self.db_session:
            try:
                import json
                from sqlalchemy import text
                await self.db_session.execute(
                    text("""
                        INSERT INTO execution_journal
                        (execution_id, event_type, message, details, step_id, step_index, severity, created_at)
                        VALUES (:execution_id, :event_type, :message, :details, :step_id, :step_index, :severity, :created_at)
                    """),
                    {
                        "execution_id": execution_id,
                        "event_type": event_type,
                        "message": message,
                        "details": json.dumps(details or {}),
                        "step_id": step_id,
                        "step_index": step_index,
                        "severity": severity,
                        "created_at": datetime.now(timezone.utc),
                    },
                )
                await self.db_session.commit()
            except Exception as e:
                logger.error("Failed to record journal event", error=str(e))

    async def get_journal(
        self,
        execution_id: str,
        event_type: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 100,
    ) -> List[dict]:
        """Retrieve journal entries for an execution."""
        if not self.db_session:
            return []

        try:
            from sqlalchemy import text
            query = "SELECT * FROM execution_journal WHERE execution_id = :execution_id"
            params = {"execution_id": execution_id}

            if event_type:
                query += " AND event_type = :event_type"
                params["event_type"] = event_type
            if severity:
                query += " AND severity = :severity"
                params["severity"] = severity

            query += " ORDER BY created_at DESC LIMIT :limit"
            params["limit"] = limit

            result = await self.db_session.execute(text(query), params)
            rows = result.fetchall()
            return [dict(row._mapping) for row in rows]

        except Exception as e:
            logger.error("Failed to get journal", error=str(e))
            return []
