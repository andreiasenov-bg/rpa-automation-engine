"""
Execution Checkpoint & Resume System.

Ensures RPA workflows survive crashes, restarts, and network failures.
Every step is checkpointed to the database so execution can resume
from the exact point of interruption.

Architecture:
- Before each step: save "step_starting" checkpoint
- After each step: save "step_completed" checkpoint with output
- On crash/restart: recovery service finds interrupted executions
  and resumes from the last completed checkpoint
- Full execution journal preserved for audit trail
"""

import json
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger(__name__)


class CheckpointType(str, Enum):
    """Types of execution checkpoints."""
    EXECUTION_STARTED = "execution_started"
    STEP_QUEUED = "step_queued"
    STEP_STARTING = "step_starting"
    STEP_COMPLETED = "step_completed"
    STEP_FAILED = "step_failed"
    STEP_RETRYING = "step_retrying"
    STEP_SKIPPED = "step_skipped"
    EXECUTION_PAUSED = "execution_paused"
    EXECUTION_RESUMED = "execution_resumed"
    EXECUTION_COMPLETED = "execution_completed"
    EXECUTION_FAILED = "execution_failed"
    EXECUTION_CANCELLED = "execution_cancelled"
    VARIABLE_UPDATED = "variable_updated"
    AI_CONVERSATION_STATE = "ai_conversation_state"


class Checkpoint:
    """A single checkpoint record."""

    def __init__(
        self,
        execution_id: str,
        checkpoint_type: CheckpointType,
        step_id: Optional[str] = None,
        step_index: Optional[int] = None,
        data: Optional[Dict[str, Any]] = None,
        context_snapshot: Optional[Dict[str, Any]] = None,
    ):
        self.id = str(uuid.uuid4())
        self.execution_id = execution_id
        self.checkpoint_type = checkpoint_type
        self.step_id = step_id
        self.step_index = step_index
        self.data = data or {}
        self.context_snapshot = context_snapshot or {}
        self.created_at = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "execution_id": self.execution_id,
            "checkpoint_type": self.checkpoint_type.value,
            "step_id": self.step_id,
            "step_index": self.step_index,
            "data": self.data,
            "context_snapshot": self.context_snapshot,
            "created_at": self.created_at.isoformat(),
        }


class ExecutionState:
    """
    Full execution state that can be serialized, persisted, and restored.

    This is the core of the resume capability — everything needed
    to continue an execution from where it stopped.
    """

    def __init__(self, execution_id: str, workflow_id: str):
        self.execution_id = execution_id
        self.workflow_id = workflow_id
        self.status: str = "pending"
        self.current_step_index: int = 0
        self.completed_steps: List[str] = []
        self.failed_steps: List[str] = []
        self.skipped_steps: List[str] = []
        self.step_outputs: Dict[str, Any] = {}
        self.variables: Dict[str, Any] = {}
        self.retry_counts: Dict[str, int] = {}
        self.error_log: List[Dict[str, Any]] = []
        self.checkpoints: List[Checkpoint] = []
        self.started_at: Optional[datetime] = None
        self.last_checkpoint_at: Optional[datetime] = None
        self.total_steps: int = 0

        # AI conversation states (for multi-turn AI tasks)
        self.ai_conversations: Dict[str, List[Dict[str, str]]] = {}

    def to_dict(self) -> Dict[str, Any]:
        """Serialize full state for DB persistence."""
        return {
            "execution_id": self.execution_id,
            "workflow_id": self.workflow_id,
            "status": self.status,
            "current_step_index": self.current_step_index,
            "completed_steps": self.completed_steps,
            "failed_steps": self.failed_steps,
            "skipped_steps": self.skipped_steps,
            "step_outputs": self._serialize_outputs(self.step_outputs),
            "variables": self._serialize_outputs(self.variables),
            "retry_counts": self.retry_counts,
            "error_log": self.error_log,
            "ai_conversations": self.ai_conversations,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "last_checkpoint_at": self.last_checkpoint_at.isoformat() if self.last_checkpoint_at else None,
            "total_steps": self.total_steps,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExecutionState":
        """Restore state from DB data."""
        state = cls(
            execution_id=data["execution_id"],
            workflow_id=data["workflow_id"],
        )
        state.status = data.get("status", "pending")
        state.current_step_index = data.get("current_step_index", 0)
        state.completed_steps = data.get("completed_steps", [])
        state.failed_steps = data.get("failed_steps", [])
        state.skipped_steps = data.get("skipped_steps", [])
        state.step_outputs = data.get("step_outputs", {})
        state.variables = data.get("variables", {})
        state.retry_counts = data.get("retry_counts", {})
        state.error_log = data.get("error_log", [])
        state.ai_conversations = data.get("ai_conversations", {})
        state.total_steps = data.get("total_steps", 0)

        if data.get("started_at"):
            state.started_at = datetime.fromisoformat(data["started_at"])
        if data.get("last_checkpoint_at"):
            state.last_checkpoint_at = datetime.fromisoformat(data["last_checkpoint_at"])

        return state

    def _serialize_outputs(self, data: Dict) -> Dict:
        """Ensure all values are JSON-serializable."""
        result = {}
        for key, value in data.items():
            try:
                json.dumps(value)
                result[key] = value
            except (TypeError, ValueError):
                result[key] = str(value)
        return result

    @property
    def can_resume(self) -> bool:
        """Check if this execution can be resumed."""
        return self.status in ("running", "paused", "retrying")

    @property
    def next_step_index(self) -> int:
        """Get the index of the next step to execute."""
        return self.current_step_index

    @property
    def progress_percent(self) -> float:
        """Calculate execution progress percentage."""
        if self.total_steps == 0:
            return 0.0
        completed = len(self.completed_steps) + len(self.skipped_steps)
        return round((completed / self.total_steps) * 100, 1)


class CheckpointManager:
    """
    Manages checkpoint creation, persistence, and recovery.

    Works with the database to persist execution state and
    provides recovery capabilities after crashes or restarts.
    """

    def __init__(self, db_session=None):
        self.db_session = db_session
        self._states: Dict[str, ExecutionState] = {}  # In-memory cache

    def get_state(self, execution_id: str) -> Optional[ExecutionState]:
        """Get execution state from cache."""
        return self._states.get(execution_id)

    def create_state(self, execution_id: str, workflow_id: str, total_steps: int) -> ExecutionState:
        """Create a new execution state."""
        state = ExecutionState(execution_id, workflow_id)
        state.total_steps = total_steps
        state.started_at = datetime.now(timezone.utc)
        state.status = "running"
        self._states[execution_id] = state
        return state

    async def save_checkpoint(
        self,
        execution_id: str,
        checkpoint_type: CheckpointType,
        step_id: Optional[str] = None,
        step_index: Optional[int] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> Checkpoint:
        """
        Save a checkpoint to the database.

        This is called before and after every step to ensure
        we can resume from the last known good state.
        """
        state = self._states.get(execution_id)
        if not state:
            logger.warning("No state found for execution", execution_id=execution_id)
            return None

        checkpoint = Checkpoint(
            execution_id=execution_id,
            checkpoint_type=checkpoint_type,
            step_id=step_id,
            step_index=step_index,
            data=data,
            context_snapshot={
                "variables": state.variables.copy(),
                "completed_steps": state.completed_steps.copy(),
                "current_step_index": state.current_step_index,
            },
        )

        state.checkpoints.append(checkpoint)
        state.last_checkpoint_at = checkpoint.created_at

        # Update state based on checkpoint type
        if checkpoint_type == CheckpointType.STEP_COMPLETED:
            if step_id and step_id not in state.completed_steps:
                state.completed_steps.append(step_id)
            if data and "output" in data:
                state.step_outputs[step_id or f"step_{step_index}"] = data["output"]
            state.current_step_index = (step_index or state.current_step_index) + 1

        elif checkpoint_type == CheckpointType.STEP_FAILED:
            if step_id and step_id not in state.failed_steps:
                state.failed_steps.append(step_id)
            if data and "error" in data:
                state.error_log.append({
                    "step_id": step_id,
                    "step_index": step_index,
                    "error": data["error"],
                    "timestamp": checkpoint.created_at.isoformat(),
                })

        elif checkpoint_type == CheckpointType.STEP_SKIPPED:
            if step_id and step_id not in state.skipped_steps:
                state.skipped_steps.append(step_id)
            state.current_step_index = (step_index or state.current_step_index) + 1

        elif checkpoint_type == CheckpointType.EXECUTION_COMPLETED:
            state.status = "completed"

        elif checkpoint_type == CheckpointType.EXECUTION_FAILED:
            state.status = "failed"

        elif checkpoint_type == CheckpointType.EXECUTION_PAUSED:
            state.status = "paused"

        elif checkpoint_type == CheckpointType.EXECUTION_RESUMED:
            state.status = "running"

        elif checkpoint_type == CheckpointType.VARIABLE_UPDATED:
            if data and "variables" in data:
                state.variables.update(data["variables"])

        elif checkpoint_type == CheckpointType.AI_CONVERSATION_STATE:
            if data and "conversation_id" in data:
                state.ai_conversations[data["conversation_id"]] = data.get("messages", [])

        # Persist to database
        await self._persist_state(state)
        await self._persist_checkpoint(checkpoint)

        logger.debug(
            "Checkpoint saved",
            execution_id=execution_id,
            type=checkpoint_type.value,
            step_id=step_id,
            progress=f"{state.progress_percent}%",
        )

        return checkpoint

    async def _persist_state(self, state: ExecutionState):
        """Save execution state to database."""
        if not self.db_session:
            return

        try:
            from sqlalchemy import text
            state_json = json.dumps(state.to_dict())
            await self.db_session.execute(
                text("""
                    INSERT INTO execution_states (execution_id, state_data, updated_at)
                    VALUES (:execution_id, :state_data, :updated_at)
                    ON CONFLICT (execution_id) DO UPDATE
                    SET state_data = :state_data, updated_at = :updated_at
                """),
                {
                    "execution_id": state.execution_id,
                    "state_data": state_json,
                    "updated_at": datetime.now(timezone.utc),
                },
            )
            await self.db_session.commit()
        except Exception as e:
            logger.error("Failed to persist state", error=str(e), execution_id=state.execution_id)

    async def _persist_checkpoint(self, checkpoint: Checkpoint):
        """Save individual checkpoint to database."""
        if not self.db_session:
            return

        try:
            from sqlalchemy import text
            await self.db_session.execute(
                text("""
                    INSERT INTO execution_checkpoints
                    (id, execution_id, checkpoint_type, step_id, step_index, data, context_snapshot, created_at)
                    VALUES (:id, :execution_id, :checkpoint_type, :step_id, :step_index, :data, :context_snapshot, :created_at)
                """),
                {
                    "id": checkpoint.id,
                    "execution_id": checkpoint.execution_id,
                    "checkpoint_type": checkpoint.checkpoint_type.value,
                    "step_id": checkpoint.step_id,
                    "step_index": checkpoint.step_index,
                    "data": json.dumps(checkpoint.data),
                    "context_snapshot": json.dumps(checkpoint.context_snapshot),
                    "created_at": checkpoint.created_at,
                },
            )
            await self.db_session.commit()
        except Exception as e:
            logger.error("Failed to persist checkpoint", error=str(e))

    async def load_state(self, execution_id: str) -> Optional[ExecutionState]:
        """Load execution state from database for recovery."""
        if not self.db_session:
            return self._states.get(execution_id)

        try:
            from sqlalchemy import text
            result = await self.db_session.execute(
                text("SELECT state_data FROM execution_states WHERE execution_id = :execution_id"),
                {"execution_id": execution_id},
            )
            row = result.fetchone()
            if row:
                state_data = json.loads(row[0])
                state = ExecutionState.from_dict(state_data)
                self._states[execution_id] = state
                logger.info(
                    "Execution state loaded",
                    execution_id=execution_id,
                    status=state.status,
                    progress=f"{state.progress_percent}%",
                    last_step=state.current_step_index,
                )
                return state
        except Exception as e:
            logger.error("Failed to load state", error=str(e), execution_id=execution_id)

        return None

    def cleanup(self, execution_id: str):
        """Remove completed execution state from memory cache."""
        self._states.pop(execution_id, None)
