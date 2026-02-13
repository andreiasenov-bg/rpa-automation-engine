"""Agent model for RPA automation engine."""

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.constants import AgentStatus
from db.base import BaseModel


class Agent(BaseModel):
    """Agent model representing an RPA execution agent.

    Attributes:
        id: Unique identifier (UUID string)
        organization_id: Foreign key to Organization
        name: Agent name
        agent_token_hash: Hashed authentication token for the agent
        status: Agent status (active, inactive, disconnected, error)
        last_heartbeat_at: Timestamp of last heartbeat
        version: Agent version
        capabilities: JSON object with agent capabilities
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "agents"

    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(nullable=False, index=True)
    agent_token_hash: Mapped[str] = mapped_column(nullable=False, unique=True)
    status: Mapped[str] = mapped_column(
        default=AgentStatus.INACTIVE.value, index=True
    )
    last_heartbeat_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    version: Mapped[str] = mapped_column(nullable=False, default="1.0.0")
    capabilities: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="agents", lazy="selectin"
    )
    executions: Mapped[list["Execution"]] = relationship(
        "Execution",
        back_populates="agent",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
