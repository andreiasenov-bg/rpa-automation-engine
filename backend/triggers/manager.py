"""Trigger Manager — central orchestrator for all trigger types.

The TriggerManager is a singleton that:
1. Registers trigger handlers for each trigger type
2. Loads enabled triggers from DB on startup
3. Routes incoming trigger events to the workflow execution engine
4. Manages trigger lifecycle (create, enable, disable, delete, test)
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from triggers.base import (
    BaseTriggerHandler,
    TriggerEvent,
    TriggerResult,
    TriggerTypeEnum,
)
from triggers.handlers.webhook import WebhookTriggerHandler
from triggers.handlers.schedule import ScheduleTriggerHandler
from triggers.handlers.event_bus import EventBusTriggerHandler

logger = logging.getLogger(__name__)


class TriggerManager:
    """Central manager for all workflow triggers.

    Singleton pattern — use get_trigger_manager() to access.
    """

    def __init__(self):
        self._handlers: dict[str, BaseTriggerHandler] = {}
        self._active_triggers: dict[str, dict] = {}  # trigger_id -> {type, config, workflow_id, org_id}
        self._event_callback = None  # Callback to workflow engine
        self._initialized = False

        # Register built-in handlers
        self._register_builtin_handlers()

    def _register_builtin_handlers(self):
        """Register all built-in trigger type handlers."""
        self.register_handler(WebhookTriggerHandler())
        self.register_handler(ScheduleTriggerHandler())
        self.register_handler(EventBusTriggerHandler())
        # Future: FileWatchTriggerHandler, EmailTriggerHandler,
        #         DbChangeTriggerHandler, ApiPollTriggerHandler

    def register_handler(self, handler: BaseTriggerHandler) -> None:
        """Register a trigger type handler.

        Args:
            handler: Instance of BaseTriggerHandler to register
        """
        self._handlers[handler.trigger_type.value] = handler
        logger.info(f"Registered trigger handler: {handler.trigger_type.value}")

    def set_event_callback(self, callback) -> None:
        """Set the callback function for trigger events.

        The callback should accept a TriggerEvent and return an execution_id.
        Typically this is the workflow engine's execute_workflow method.

        Args:
            callback: Async callable(TriggerEvent) -> str
        """
        self._event_callback = callback

    async def load_from_db(self, db_session=None) -> int:
        """Load and start all enabled triggers from the database.

        Called at application startup.

        Args:
            db_session: Optional SQLAlchemy async session

        Returns:
            Number of triggers loaded
        """
        if db_session is None:
            logger.info("No DB session provided, skipping trigger load")
            self._initialized = True
            return 0

        from sqlalchemy import select
        from db.models.trigger import Trigger

        try:
            result = await db_session.execute(
                select(Trigger).where(
                    Trigger.is_enabled == True,
                    Trigger.is_deleted == False,
                )
            )
            triggers = result.scalars().all()

            loaded = 0
            for trigger in triggers:
                tr_result = await self.start_trigger(
                    trigger_id=trigger.id,
                    trigger_type=trigger.trigger_type,
                    config=trigger.config or {},
                    workflow_id=trigger.workflow_id,
                    organization_id=trigger.organization_id,
                )
                if tr_result.success:
                    loaded += 1
                else:
                    logger.warning(
                        "Failed to start trigger %s: %s",
                        trigger.id,
                        tr_result.message,
                    )

            logger.info(
                "Trigger manager initialized: %d/%d triggers loaded",
                loaded,
                len(triggers),
            )
        except Exception as exc:
            logger.error("Failed to load triggers from DB: %s", exc, exc_info=True)

        self._initialized = True
        return len(self._active_triggers)

    async def start_trigger(
        self,
        trigger_id: str,
        trigger_type: str,
        config: dict,
        workflow_id: str,
        organization_id: str,
    ) -> TriggerResult:
        """Start a trigger — begin listening for events.

        Args:
            trigger_id: UUID of the trigger record
            trigger_type: Type string (must match a registered handler)
            config: Type-specific configuration
            workflow_id: Workflow to execute when triggered
            organization_id: Owning organization

        Returns:
            TriggerResult
        """
        handler = self._handlers.get(trigger_type)
        if not handler:
            return TriggerResult(
                success=False,
                message=f"Unknown trigger type: {trigger_type}",
                trigger_id=trigger_id,
                error=f"No handler registered for type '{trigger_type}'",
            )

        # Validate config
        is_valid, error = handler.validate_config(config)
        if not is_valid:
            return TriggerResult(
                success=False,
                message=f"Invalid configuration: {error}",
                trigger_id=trigger_id,
                error=error,
            )

        # Start the handler
        result = await handler.start(trigger_id, config)

        if result.success:
            self._active_triggers[trigger_id] = {
                "type": trigger_type,
                "config": config,
                "workflow_id": workflow_id,
                "organization_id": organization_id,
                "started_at": datetime.now(timezone.utc).isoformat(),
            }
            logger.info(f"Trigger started: {trigger_id} ({trigger_type})")

        return result

    async def stop_trigger(self, trigger_id: str) -> TriggerResult:
        """Stop a trigger — stop listening for events.

        Args:
            trigger_id: UUID of the trigger to stop

        Returns:
            TriggerResult
        """
        info = self._active_triggers.get(trigger_id)
        if not info:
            return TriggerResult(
                success=False,
                message="Trigger not active",
                trigger_id=trigger_id,
            )

        handler = self._handlers.get(info["type"])
        if handler:
            result = await handler.stop(trigger_id)
        else:
            result = TriggerResult(
                success=True,
                message="Handler not found, removed from active list",
                trigger_id=trigger_id,
            )

        self._active_triggers.pop(trigger_id, None)
        logger.info(f"Trigger stopped: {trigger_id}")
        return result

    async def test_trigger(self, trigger_type: str, config: dict) -> TriggerResult:
        """Test a trigger configuration without starting it.

        Args:
            trigger_type: Type of trigger to test
            config: Configuration to validate

        Returns:
            TriggerResult with validation details
        """
        handler = self._handlers.get(trigger_type)
        if not handler:
            return TriggerResult(
                success=False,
                message=f"Unknown trigger type: {trigger_type}",
                trigger_id="test",
            )
        return await handler.test(config)

    async def fire_trigger(self, trigger_id: str, payload: dict = None) -> TriggerResult:
        """Fire a trigger — create a TriggerEvent and execute the workflow.

        This is called when a trigger condition is met (webhook received,
        cron fires, file detected, etc.).

        Args:
            trigger_id: UUID of the trigger that fired
            payload: Event-specific data

        Returns:
            TriggerResult with execution_id if successful
        """
        info = self._active_triggers.get(trigger_id)
        if not info:
            return TriggerResult(
                success=False,
                message="Trigger not active",
                trigger_id=trigger_id,
            )

        event = TriggerEvent(
            trigger_id=trigger_id,
            trigger_type=info["type"],
            workflow_id=info["workflow_id"],
            organization_id=info["organization_id"],
            payload=payload or {},
        )

        # Dispatch to workflow engine
        execution_id = None
        if self._event_callback:
            try:
                execution_id = await self._event_callback(event)
                logger.info(
                    f"Trigger fired: {trigger_id} -> execution {execution_id}"
                )
            except Exception as e:
                logger.error(f"Trigger fire failed: {trigger_id}: {e}")
                return TriggerResult(
                    success=False,
                    message=f"Workflow execution failed: {str(e)}",
                    trigger_id=trigger_id,
                    error=str(e),
                )
        else:
            logger.warning(
                f"Trigger fired but no event callback set: {trigger_id}"
            )

        return TriggerResult(
            success=True,
            message="Trigger fired successfully",
            trigger_id=trigger_id,
            execution_id=execution_id,
        )

    def get_status(self) -> dict[str, Any]:
        """Get trigger manager status."""
        return {
            "initialized": self._initialized,
            "registered_handlers": list(self._handlers.keys()),
            "active_triggers": len(self._active_triggers),
            "triggers": {
                tid: {
                    "type": info["type"],
                    "workflow_id": info["workflow_id"],
                    "started_at": info["started_at"],
                }
                for tid, info in self._active_triggers.items()
            },
        }

    def get_supported_types(self) -> list[dict[str, str]]:
        """Get list of supported trigger types."""
        return [
            {"type": t.value, "name": t.name.replace("_", " ").title()}
            for t in TriggerTypeEnum
        ]


# -- Singleton --

_trigger_manager: Optional[TriggerManager] = None


def get_trigger_manager() -> TriggerManager:
    """Get or create the singleton TriggerManager."""
    global _trigger_manager
    if _trigger_manager is None:
        _trigger_manager = TriggerManager()
    return _trigger_manager
