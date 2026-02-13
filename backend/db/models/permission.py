"""Permission model and role_permissions association table."""

from sqlalchemy import ForeignKey, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base, BaseModel

# Association table for many-to-many relationship between Role and Permission
role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column(
        "permission_id", ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True
    ),
)


class Permission(BaseModel):
    """Permission model for fine-grained access control.

    Attributes:
        id: Unique identifier (UUID string)
        resource: Resource type (e.g., 'workflow', 'user', 'organization')
        action: Action type (e.g., 'create', 'read', 'update', 'delete')
        description: Permission description
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "permissions"

    resource: Mapped[str] = mapped_column(nullable=False, index=True)
    action: Mapped[str] = mapped_column(nullable=False, index=True)
    description: Mapped[str] = mapped_column(nullable=False, default="")

    # Relationships
    roles: Mapped[list["Role"]] = relationship(
        "Role",
        secondary=role_permissions,
        back_populates="permissions",
        lazy="selectin",
    )
