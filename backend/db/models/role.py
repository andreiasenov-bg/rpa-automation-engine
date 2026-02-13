"""Role model and user_roles association table."""

from sqlalchemy import ForeignKey, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base, BaseModel

# Association table for many-to-many relationship between User and Role
user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)


class Role(BaseModel):
    """Role model for role-based access control (RBAC).

    Attributes:
        id: Unique identifier (UUID string)
        organization_id: Foreign key to Organization
        name: Role name
        description: Role description
        is_system_role: Whether this is a system role (cannot be deleted)
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "roles"

    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(nullable=False, index=True)
    slug: Mapped[str] = mapped_column(nullable=False, index=True)
    description: Mapped[str] = mapped_column(nullable=False, default="")
    is_system_role: Mapped[bool] = mapped_column(default=False)

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="roles", lazy="selectin"
    )
    users: Mapped[list["User"]] = relationship(
        "User",
        secondary=user_roles,
        back_populates="roles",
        lazy="selectin",
    )
    permissions: Mapped[list["Permission"]] = relationship(
        "Permission",
        secondary="role_permissions",
        back_populates="roles",
        lazy="selectin",
    )
