"""API Key model for external integrations.

Each API key is scoped to an organization, has a SHA-256 hash stored in DB,
and can carry specific permission codes (same format as RBAC permissions).
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import BaseModel


class APIKey(BaseModel):
    """Persisted API key for programmatic access.

    Attributes:
        id: UUID primary key
        organization_id: Owning organization
        name: Human-readable name (e.g. "CI Pipeline Key")
        key_hash: SHA-256 hash of the raw key (raw key shown once at creation)
        prefix: First 7 chars of the raw key for identification (e.g. "rpa_abc")
        permissions: List of permission codes (e.g. ["workflows.read", "executions.*"])
        is_active: Whether key is active
        expires_at: Optional expiration datetime
        last_used_at: Timestamp of last successful use
        usage_count: Total number of successful uses
        created_by_id: User who created the key
        rate_limit_group: Rate limit tier ("default", "high", "unlimited")
    """

    __tablename__ = "api_keys"

    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(nullable=False)
    key_hash: Mapped[str] = mapped_column(nullable=False, unique=True, index=True)
    prefix: Mapped[str] = mapped_column(nullable=False, default="rpa_???")
    permissions: Mapped[Optional[list]] = mapped_column(JSON, nullable=True, default=list)
    is_active: Mapped[bool] = mapped_column(default=True, index=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    usage_count: Mapped[int] = mapped_column(default=0)
    created_by_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    rate_limit_group: Mapped[str] = mapped_column(default="default")

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization", lazy="selectin"
    )
