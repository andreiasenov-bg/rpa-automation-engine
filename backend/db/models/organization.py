"""Organization model for RPA automation engine."""

from typing import Optional

from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import BaseModel


class Organization(BaseModel):
    """Organization model representing a tenant in the system.

    Attributes:
        id: Unique identifier (UUID string)
        name: Organization name
        slug: URL-friendly identifier
        subscription_plan: Subscription tier (e.g., 'free', 'pro', 'enterprise')
        is_active: Whether organization is active
        settings: JSON configuration object for organization-specific settings
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(nullable=False, index=True)
    slug: Mapped[str] = mapped_column(nullable=False, unique=True, index=True)
    subscription_plan: Mapped[str] = mapped_column(nullable=False, default="free")
    is_active: Mapped[bool] = mapped_column(default=True, index=True)
    settings: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Relationships
    users: Mapped[list["User"]] = relationship(
        "User",
        back_populates="organization",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    roles: Mapped[list["Role"]] = relationship(
        "Role",
        back_populates="organization",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    workflows: Mapped[list["Workflow"]] = relationship(
        "Workflow",
        back_populates="organization",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    executions: Mapped[list["Execution"]] = relationship(
        "Execution",
        back_populates="organization",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    agents: Mapped[list["Agent"]] = relationship(
        "Agent",
        back_populates="organization",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    credentials: Mapped[list["Credential"]] = relationship(
        "Credential",
        back_populates="organization",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    schedules: Mapped[list["Schedule"]] = relationship(
        "Schedule",
        back_populates="organization",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(
        "AuditLog",
        back_populates="organization",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
