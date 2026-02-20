"""Workflow model for RPA automation engine."""

from typing import Optional

from sqlalchemy import JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.constants import WorkflowStatus
from db.base import BaseModel


class Workflow(BaseModel):
    """Workflow model representing an automation workflow.

    Attributes:
        id: Unique identifier (UUID string)
        organization_id: Foreign key to Organization
        name: Workflow name
        description: Workflow description
        definition: JSON definition of workflow structure
        version: Workflow version number
        is_enabled: Whether workflow can be executed
        status: Current workflow status (draft, published, deprecated, archived)
        created_by_id: Foreign key to User who created the workflow
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "workflows"

    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(nullable=False, index=True)
    description: Mapped[str] = mapped_column(nullable=False, default="")
    definition: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    version: Mapped[int] = mapped_column(default=1)
    is_enabled: Mapped[bool] = mapped_column(default=True, index=True)
    status: Mapped[str] = mapped_column(
        default=WorkflowStatus.DRAFT.value, index=True
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="workflows", lazy="noload"
    )
    created_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[created_by_id],
        back_populates="created_workflows",
        lazy="noload",
    )
    steps: Mapped[list["WorkflowStep"]] = relationship(
        "WorkflowStep",
        back_populates="workflow",
        cascade="all, delete-orphan",
        lazy="noload",
    )
    executions: Mapped[list["Execution"]] = relationship(
        "Execution",
        back_populates="workflow",
        cascade="all, delete-orphan",
        lazy="noload",
    )
    schedules: Mapped[list["Schedule"]] = relationship(
        "Schedule",
        back_populates="workflow",
        cascade="all, delete-orphan",
        lazy="noload",
    )
    triggers: Mapped[list["Trigger"]] = relationship(
        "Trigger",
        back_populates="workflow",
        cascade="all, delete-orphan",
        lazy="noload",
    )
