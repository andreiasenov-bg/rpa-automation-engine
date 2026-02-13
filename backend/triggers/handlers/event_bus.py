"""Event bus trigger handler.

Subscribes to Redis pub/sub channels. Internal services and
external systems can publish events that trigger workflows.
"""

from typing import Optional

from triggers.base import BaseTriggerHandler, TriggerResult, TriggerTypeEnum


class EventBusTriggerHandler(BaseTriggerHandler):
    """Handler for event-bus (Redis pub/sub) triggers.

    Config schema:
        {
            "channel": "orders.created",      # Redis pub/sub channel pattern
            "filter": {                        # optional payload filter (JSONPath)
                "amount_gt": 100,
                "status": "paid"
            }
        }
    """

    trigger_type = TriggerTypeEnum.EVENT_BUS

    def __init__(self):
        self._active: dict[str, dict] = {}
        self._subscriptions: dict[str, list[str]] = {}  # channel -> [trigger_ids]

    async def start(self, trigger_id: str, config: dict) -> TriggerResult:
        """Subscribe to a Redis pub/sub channel."""
        is_valid, error = self.validate_config(config)
        if not is_valid:
            return TriggerResult(
                success=False,
                message=f"Invalid config: {error}",
                trigger_id=trigger_id,
                error=error,
            )

        channel = config["channel"]
        self._active[trigger_id] = config

        if channel not in self._subscriptions:
            self._subscriptions[channel] = []
        self._subscriptions[channel].append(trigger_id)

        # TODO: Start Redis subscriber for this channel
        # await redis.subscribe(channel, callback=self._on_message)

        return TriggerResult(
            success=True,
            message=f"Subscribed to event channel: {channel}",
            trigger_id=trigger_id,
        )

    async def stop(self, trigger_id: str) -> TriggerResult:
        """Unsubscribe from Redis pub/sub channel."""
        config = self._active.pop(trigger_id, None)
        if config:
            channel = config.get("channel")
            if channel and channel in self._subscriptions:
                self._subscriptions[channel] = [
                    t for t in self._subscriptions[channel] if t != trigger_id
                ]
                if not self._subscriptions[channel]:
                    del self._subscriptions[channel]
                    # TODO: Unsubscribe from Redis if no more listeners

        return TriggerResult(
            success=True,
            message="Unsubscribed from event channel",
            trigger_id=trigger_id,
        )

    async def test(self, config: dict) -> TriggerResult:
        """Validate event bus configuration."""
        is_valid, error = self.validate_config(config)
        if not is_valid:
            return TriggerResult(
                success=False,
                message=f"Invalid config: {error}",
                trigger_id="test",
                error=error,
            )
        return TriggerResult(
            success=True,
            message=f"Event channel '{config['channel']}' config is valid",
            trigger_id="test",
        )

    def validate_config(self, config: dict) -> tuple[bool, Optional[str]]:
        """Validate event bus config."""
        if not isinstance(config, dict):
            return False, "Config must be a dict"
        if not config.get("channel"):
            return False, "Missing required field: channel"
        return True, None

    def get_triggers_for_channel(self, channel: str) -> list[str]:
        """Get all trigger IDs subscribed to a channel."""
        return list(self._subscriptions.get(channel, []))
