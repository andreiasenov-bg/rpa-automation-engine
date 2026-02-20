"""Base model class for all SQLAlchemy models."""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import func, Boolean, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base model class with common fields for all models."""

    pass


class SoftDeleteMixin:
    """Mixin that adds soft delete capability to any model.

    Adds `deleted_at` and `is_deleted` columns. When an entity is
    "deleted", `deleted_at` is set to the current timestamp and
    `is_deleted` is flipped to True. The row remains in the DB and
    can be restored later.

    Usage in queries:
        # Get only non-deleted records (default for most queries)
        query.where(Model.is_deleted == False)

        # Get including deleted (admin / audit)
        query  # no filter
    """

    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None, index=True
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, default=False, index=True
    )

    def soft_delete(self) -> None:
        """Mark this record as deleted."""
        self.is_deleted = True
        self.deleted_at = func.now()

    def restore(self) -> None:
        """Restore a soft-deleted record."""
        self.is_deleted = False
        self.deleted_at = None


class BaseModel(SoftDeleteMixin, Base):
    """Abstract base model with common timestamp fields and soft delete.

    All domain models inherit from this. Provides:
    - id: UUID primary key
    - created_at / updated_at: automatic timestamps
    - is_deleted / deleted_at: soft delete support
    """

    __abstract__ = True

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now()
    )
