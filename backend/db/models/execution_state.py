"""
Execution State & Checkpoint persistence models.

These tables are the backbone of the resume-from-crash capability:
- execution_states: Full serialized execution state (one per execution)
- execution_checkpoints: Individual checkpoint records (many per execution)
- execution_journal: Detailed event log for every execution action
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text, JSON
from sqlalchemy.dialects.postgresql import UUID

from db.base import BaseModel


class ExecutionStateModel(BaseModel):
    """
    Persisted execution state.

    Stores the full serialized state of a running execution.
    Updated on every checkpoint. Used for recovery after crash/restart.
    """

    __tablename__ = "execution_states"

    execution_id = Column(String(36), unique=True, nullable=False, index=True)
    state_data = Column(JSON, nullable=False, default=dict)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index("ix_execution_states_status", "state_data", postgresql_using="gin"),
    )


class ExecutionCheckpointModel(BaseModel):
    """
    Individual checkpoint record.

    Every step transition creates a checkpoint. Used for:
    - Determining exact resume point after crash
    - Audit trail of execution progress
    - Debugging failed executions
    """

    __tablename__ = "execution_checkpoints"

    execution_id = Column(String(36), nullable=False, index=True)
    checkpoint_type = Column(String(50), nullable=False, index=True)
    step_id = Column(String(36), nullable=True)
    step_index = Column(Integer, nullable=True)
    data = Column(JSON, nullable=True, default=dict)
    context_snapshot = Column(JSON, nullable=True, default=dict)

    __table_args__ = (
        Index("ix_checkpoints_exec_type", "execution_id", "checkpoint_type"),
    )


class ExecutionJournalModel(BaseModel):
    """
    Detailed event journal for executions.

    Records every meaningful event during execution:
    - Step transitions
    - Variable updates
    - AI interactions
    - Retry attempts
    - Recovery events
    - Errors and warnings

    Provides complete audit trail for compliance and debugging.
    """

    __tablename__ = "execution_journal"

    execution_id = Column(String(36), nullable=False, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    message = Column(Text, nullable=False)
    details = Column(JSON, nullable=True, default=dict)
    step_id = Column(String(36), nullable=True)
    step_index = Column(Integer, nullable=True)
    severity = Column(String(20), nullable=False, default="info", index=True)

    __table_args__ = (
        Index("ix_journal_exec_time", "execution_id", "created_at"),
        Index("ix_journal_severity", "severity", "created_at"),
    )
