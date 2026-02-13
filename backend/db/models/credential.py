"""Credential model for RPA automation engine."""

from typing import Optional

from sqlalchemy import JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.constants import CredentialType
from db.base import BaseModel


class Credential(BaseModel):
    """Credential model for managing encrypted credentials.

    Attributes:
        id: Unique identifier (UUID string)
        organization_id: Foreign key to Organization
        name: Credential name
        credential_type: Type of credential (api_key, oauth2, basic_auth, database, private_key, custom)
        encrypted_value: Encrypted credential value
        metadata: JSON metadata for the credential
        created_by_id: Foreign key to User who created the credential
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "credentials"

    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(nullable=False, index=True)
    credential_type: Mapped[str] = mapped_column(
        default=CredentialType.API_KEY.value, index=True
    )
    encrypted_value: Mapped[str] = mapped_column(nullable=False)
    metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="credentials", lazy="selectin"
    )
    created_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[created_by_id],
        back_populates="created_credentials",
        lazy="selectin",
    )
