"""Execution model for RPA automation engine."""

from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.constants import ExecutionStatus, TriggerType
from db.base import BaseModel


class Execution(BaseModel):
    """Execution model representing a workflow execution instance.

    Attributes:
        id: Unique identifier (UUID string)
        organization_id: Foreign key to Organization
        workflow_id: Foreign key to Workflow
        agent_id: Optional foreign key to Agent that executed the workflow
        trigger_type: Type of trigger (manual, scheduled, webhook, api, event)
        status: Current execution status (pending, running, completed, failed, cancelled, paused)
        started_at: Execution start timestamp
        completed_at: Execution completion timestamp
        duration_ms: Execution duration in milliseconds
        error_message: Error message if execution failed
        retry_count: Number of retries performed
        max_retries: Maximum number of retries allowed
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "executions"

    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workflow_id: Mapped[str] = mapped_column(
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    agent_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("agents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    trigger_type: Mapped[str] = mapped_column(
        default=TriggerType.MANUAL.value, index=True
    )
    status: Mapped[str] = mapped_column(
        default=ExecutionStatus.PENDING.value, index=True
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(nullable=True)
    retry_count: Mapped[int] = mapped_column(default=0)
    max_retries: Mapped[int] = mapped_column(default=3)

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="executions", lazy="select"
    )
    workflow: Mapped["Workflow"] = relationship(
        "Workflow", back_populates="executions", lazy="selectin"
    )
    agent: Mapped[Optional["Agent"]] = relationship(
        "Agent", back_populates="executions", lazy="select"
    )
    logs: Mapped[list["ExecutionLog"]] = relationship(
        "ExecutionLog",
        back_populates="execution",
        cascade="all, delete-orphan",
        lazy="noload",
    )
