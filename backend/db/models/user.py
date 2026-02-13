"""User model for RPA automation engine."""

from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import BaseModel


class User(BaseModel):
    """User model representing a system user.

    Attributes:
        id: Unique identifier (UUID string)
        organization_id: Foreign key to Organization
        email: User email address (unique)
        password_hash: Bcrypt hashed password
        first_name: User's first name
        last_name: User's last name
        is_active: Whether user account is active
        is_superadmin: Whether user has superadmin privileges
        last_login_at: Timestamp of last login
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "users"

    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(nullable=False)
    first_name: Mapped[str] = mapped_column(nullable=False)
    last_name: Mapped[str] = mapped_column(nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, index=True)
    is_superadmin: Mapped[bool] = mapped_column(default=False)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="users", lazy="selectin"
    )
    roles: Mapped[list["Role"]] = relationship(
        "Role",
        secondary="user_roles",
        back_populates="users",
        lazy="selectin",
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(
        "AuditLog",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    created_workflows: Mapped[list["Workflow"]] = relationship(
        "Workflow",
        foreign_keys="Workflow.created_by_id",
        back_populates="created_by",
        lazy="selectin",
    )
    created_credentials: Mapped[list["Credential"]] = relationship(
        "Credential",
        foreign_keys="Credential.created_by_id",
        back_populates="created_by",
        lazy="selectin",
    )
