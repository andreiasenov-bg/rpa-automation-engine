"""Base trigger classes and trigger type registry."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class TriggerTypeEnum(str, Enum):
    """All supported trigger types."""

    WEBHOOK = "webhook"
    SCHEDULE = "schedule"
    FILE_WATCH = "file_watch"
    EMAIL = "email"
    DB_CHANGE = "db_change"
    API_POLL = "api_poll"
    EVENT_BUS = "event_bus"
    MANUAL = "manual"


@dataclass
class TriggerEvent:
    """Represents a single trigger firing event.

    This is the payload that gets passed from a trigger
    to the workflow execution engine.
    """

    trigger_id: str
    trigger_type: str
    workflow_id: str
    organization_id: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    payload: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    correlation_id: Optional[str] = None


@dataclass
class TriggerResult:
    """Result of a trigger operation (start/stop/test)."""

    success: bool
    message: str
    trigger_id: str
    execution_id: Optional[str] = None
    error: Optional[str] = None


class BaseTriggerHandler(ABC):
    """Abstract base class for all trigger type handlers.

    Each trigger type (webhook, schedule, file_watch, etc.)
    implements this interface. The TriggerManager uses these
    handlers to start/stop/test triggers.
    """

    trigger_type: TriggerTypeEnum

    @abstractmethod
    async def start(self, trigger_id: str, config: dict) -> TriggerResult:
        """Start listening for this trigger.

        Args:
            trigger_id: ID of the trigger record in DB
            config: Type-specific configuration from trigger.config

        Returns:
            TriggerResult indicating success/failure
        """
        ...

    @abstractmethod
    async def stop(self, trigger_id: str) -> TriggerResult:
        """Stop listening for this trigger.

        Args:
            trigger_id: ID of the trigger to stop

        Returns:
            TriggerResult indicating success/failure
        """
        ...

    @abstractmethod
    async def test(self, config: dict) -> TriggerResult:
        """Test trigger configuration without starting it.

        Args:
            config: Type-specific configuration to validate

        Returns:
            TriggerResult with validation details
        """
        ...

    def validate_config(self, config: dict) -> tuple[bool, Optional[str]]:
        """Validate trigger configuration.

        Args:
            config: Configuration dict to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        return True, None
