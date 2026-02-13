"""Trigger model for RPA automation engine.

Triggers are the entry points that start workflow executions.
Supports: webhook, schedule, file watcher, email, database change,
API polling, event bus, and manual triggers.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import BaseModel


class Trigger(BaseModel):
    """Trigger model — defines how a workflow gets started.

    Attributes:
        id: UUID primary key
        organization_id: FK → Organization (multi-tenant)
        workflow_id: FK → Workflow to execute when triggered
        name: Human-readable trigger name
        trigger_type: One of the TriggerType enum values
        is_enabled: Whether this trigger is active
        config: JSON config specific to trigger type (see below)
        last_triggered_at: When this trigger last fired
        trigger_count: How many times this trigger has fired
        error_message: Last error if trigger failed
        created_by_id: FK → User who created the trigger

    Config schemas by type:
        webhook:   { "path": "/hooks/my-hook", "secret": "...", "methods": ["POST"] }
        schedule:  { "cron": "0 9 * * MON", "timezone": "Europe/Sofia" }
        file_watch:{ "path": "/data/inbox", "patterns": ["*.csv"], "events": ["created"] }
        email:     { "mailbox": "imap://...", "folder": "INBOX", "filter": {"from": "..."} }
        db_change: { "connection_id": "...", "table": "orders", "events": ["INSERT","UPDATE"] }
        api_poll:  { "integration_id": "...", "endpoint": "/status", "interval_sec": 60 }
        event_bus: { "channel": "orders.created", "filter": {"amount_gt": 100} }
        manual:    {}
    """

    __tablename__ = "triggers"

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
    created_by_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    name: Mapped[str] = mapped_column(nullable=False, index=True)
    trigger_type: Mapped[str] = mapped_column(nullable=False, index=True)
    is_enabled: Mapped[bool] = mapped_column(default=True, index=True)
    config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    last_triggered_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    trigger_count: Mapped[int] = mapped_column(default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="triggers", lazy="selectin"
    )
    workflow: Mapped["Workflow"] = relationship(
        "Workflow", back_populates="triggers", lazy="selectin"
    )
    created_by: Mapped[Optional["User"]] = relationship(
        "User", lazy="selectin"
    )
