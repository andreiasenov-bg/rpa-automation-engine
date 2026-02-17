"""Schedule model for RPA automation engine."""

from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import BaseModel


class Schedule(BaseModel):
    """Schedule model for workflow scheduling.

    Attributes:
        id: Unique identifier (UUID string)
        organization_id: Foreign key to Organization
        workflow_id: Foreign key to Workflow
        name: Schedule name
        cron_expression: Cron expression for schedule
        timezone: Timezone for schedule
        is_enabled: Whether schedule is active
        next_run_at: Timestamp of next scheduled run
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "schedules"

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
    name: Mapped[str] = mapped_column(nullable=False, index=True)
    cron_expression: Mapped[str] = mapped_column(nullable=False)
    timezone: Mapped[str] = mapped_column(nullable=False, default="UTC")
    is_enabled: Mapped[bool] = mapped_column(default=True, index=True)
    next_run_at: Mapped[Optional[datetime]] = mapped_column(nullable=True, index=True)

    # Relationships — use "noload" to avoid greenlet_spawn errors in async
    # sessions.  Endpoints that need related data do explicit JOINs.
    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="schedules", lazy="noload"
    )
    workflow: Mapped["Workflow"] = relationship(
        "Workflow", back_populates="schedules", lazy="noload"
    )
