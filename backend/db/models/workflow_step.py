"""WorkflowStep model for RPA automation engine."""

from typing import Optional

from sqlalchemy import JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import BaseModel


class WorkflowStep(BaseModel):
    """WorkflowStep model representing a single step in a workflow.

    Attributes:
        id: Unique identifier (UUID string)
        workflow_id: Foreign key to Workflow
        step_order: Order of execution in the workflow
        task_type: Type of task (e.g., 'http', 'script', 'wait', 'condition')
        name: Step name
        config: JSON configuration for the step
        error_handler_step_id: Optional foreign key to error handler step
        timeout_seconds: Timeout for step execution in seconds
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "workflow_steps"

    workflow_id: Mapped[str] = mapped_column(
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    error_handler_step_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("workflow_steps.id", ondelete="SET NULL"),
        nullable=True,
    )
    step_order: Mapped[int] = mapped_column(nullable=False)
    task_type: Mapped[str] = mapped_column(nullable=False, index=True)
    name: Mapped[str] = mapped_column(nullable=False)
    config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    timeout_seconds: Mapped[Optional[int]] = mapped_column(nullable=True)

    # Relationships
    workflow: Mapped["Workflow"] = relationship(
        "Workflow", back_populates="steps", lazy="selectin"
    )
    error_handler_step: Mapped[Optional["WorkflowStep"]] = relationship(
        "WorkflowStep",
        remote_side="WorkflowStep.id",
        foreign_keys=[error_handler_step_id],
        backref="handled_by",
        lazy="selectin",
    )
    execution_logs: Mapped[list["ExecutionLog"]] = relationship(
        "ExecutionLog",
        back_populates="step",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
