"""AuditLog model for RPA automation engine."""

from typing import Optional

from sqlalchemy import JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.constants import AuditAction
from db.base import BaseModel


class AuditLog(BaseModel):
    """AuditLog model for tracking changes and user actions.

    Attributes:
        id: Unique identifier (UUID string)
        organization_id: Foreign key to Organization
        user_id: Foreign key to User who performed the action
        resource_type: Type of resource affected (e.g., 'workflow', 'user', 'credential')
        resource_id: ID of the resource affected
        action: Action performed (create, read, update, delete, execute, login, logout, export, import)
        old_values: JSON object with previous values
        new_values: JSON object with new values
        ip_address: IP address from which action was performed
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "audit_logs"

    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    resource_type: Mapped[str] = mapped_column(nullable=False, index=True)
    resource_id: Mapped[str] = mapped_column(nullable=False, index=True)
    action: Mapped[str] = mapped_column(
        default=AuditAction.READ.value, index=True
    )
    old_values: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    new_values: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(nullable=True)

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="audit_logs", lazy="selectin"
    )
    user: Mapped[Optional["User"]] = relationship(
        "User", back_populates="audit_logs", lazy="selectin"
    )
