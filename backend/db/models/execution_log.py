"""ExecutionLog model for RPA automation engine."""

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.constants import LogLevel
from db.base import BaseModel


class ExecutionLog(BaseModel):
    """ExecutionLog model for logging execution step details.

    Attributes:
        id: Unique identifier (UUID string)
        execution_id: Foreign key to Execution
        step_id: Optional foreign key to WorkflowStep
        level: Log level (debug, info, warning, error, critical)
        message: Log message
        context: JSON context data for the log entry
        timestamp: Log timestamp
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "execution_logs"

    execution_id: Mapped[str] = mapped_column(
        ForeignKey("executions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    step_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("workflow_steps.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    level: Mapped[str] = mapped_column(
        default=LogLevel.INFO.value, index=True
    )
    message: Mapped[str] = mapped_column(nullable=False)
    context: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(nullable=False, index=True)

    # Relationships
    execution: Mapped["Execution"] = relationship(
        "Execution", back_populates="logs", lazy="selectin"
    )
    step: Mapped[Optional["WorkflowStep"]] = relationship(
        "WorkflowStep", back_populates="execution_logs", lazy="selectin"
    )
