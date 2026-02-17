"""Event bus trigger handler.

Subscribes to Redis pub/sub channels. Internal services and
external systems can publish events that trigger workflows.
"""

import asyncio
import json
import logging
from typing import Optional

from triggers.base import BaseTriggerHandler, TriggerResult, TriggerTypeEnum

logger = logging.getLogger(__name__)


class EventBusTriggerHandler(BaseTriggerHandler):
    """Handler for event-bus (Redis pub/sub) triggers.

    Config schema:
        {
            "channel": "orders.created",      # Redis pub/sub channel pattern
            "filter": {                        # optional payload filter (key-value match)
                "amount_gt": 100,
                "status": "paid"
            }
        }
    """

    trigger_type = TriggerTypeEnum.EVENT_BUS

    def __init__(self):
        self._active: dict[str, dict] = {}
        self._subscriptions: dict[str, list[str]] = {}  # channel -> [trigger_ids]
        self._listener_tasks: dict[str, asyncio.Task] = {}  # channel -> listener task
        self._fire_callback = None  # Set by TriggerManager

    def set_fire_callback(self, callback):
        """Set the callback used when an event matches a trigger.

        Args:
            callback: Async callable(trigger_id, payload) that fires a trigger
        """
        self._fire_callback = callback

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

        # Start a Redis subscriber for this channel if not already running
        if channel not in self._listener_tasks:
            try:
                task = asyncio.create_task(self._listen_channel(channel))
                self._listener_tasks[channel] = task
                logger.info("Started Redis subscriber for channel: %s", channel)
            except Exception as exc:
                logger.error(
                    "Failed to start Redis subscriber for %s: %s", channel, exc
                )
                return TriggerResult(
                    success=False,
                    message=f"Failed to subscribe: {exc}",
                    trigger_id=trigger_id,
                    error=str(exc),
                )

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
                    # Cancel the listener task if no more subscribers
                    task = self._listener_tasks.pop(channel, None)
                    if task and not task.done():
                        task.cancel()
                        logger.info(
                            "Stopped Redis subscriber for channel: %s", channel
                        )

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

    async def _listen_channel(self, channel: str):
        """Background task that listens to a Redis pub/sub channel.

        On receiving a message, checks filter conditions and fires matching triggers.
        """
        try:
            import redis.asyncio as aioredis
            from app.config import get_settings

            settings = get_settings()
            redis_client = aioredis.from_url(settings.REDIS_URL)
            pubsub = redis_client.pubsub()
            await pubsub.subscribe(channel)

            logger.info("Listening on Redis channel: %s", channel)

            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue

                try:
                    raw_data = message["data"]
                    if isinstance(raw_data, bytes):
                        raw_data = raw_data.decode("utf-8")
                    payload = json.loads(raw_data) if raw_data else {}
                except (json.JSONDecodeError, UnicodeDecodeError):
                    payload = {"raw": str(message["data"])}

                # Fire all triggers subscribed to this channel
                trigger_ids = self._subscriptions.get(channel, [])
                for trigger_id in trigger_ids:
                    config = self._active.get(trigger_id, {})
                    filter_rules = config.get("filter", {})

                    # Apply simple key-value filter
                    if filter_rules and not self._matches_filter(payload, filter_rules):
                        logger.debug(
                            "Event on %s filtered out for trigger %s",
                            channel,
                            trigger_id,
                        )
                        continue

                    # Fire the trigger via callback
                    if self._fire_callback:
                        try:
                            await self._fire_callback(trigger_id, payload)
                            logger.info(
                                "Event bus fired trigger %s from channel %s",
                                trigger_id,
                                channel,
                            )
                        except Exception as exc:
                            logger.error(
                                "Failed to fire trigger %s: %s", trigger_id, exc
                            )

        except asyncio.CancelledError:
            logger.info("Redis listener cancelled for channel: %s", channel)
        except Exception as exc:
            logger.error(
                "Redis listener error for channel %s: %s", channel, exc, exc_info=True
            )

    @staticmethod
    def _matches_filter(payload: dict, filter_rules: dict) -> bool:
        """Check if a payload matches filter rules.

        Supports:
        - Exact match: {"status": "paid"} → payload["status"] == "paid"
        - Greater than: {"amount_gt": 100} → payload["amount"] > 100
        - Less than: {"amount_lt": 50} → payload["amount"] < 50
        - Contains: {"tags_contains": "urgent"} → "urgent" in payload["tags"]
        """
        for key, expected in filter_rules.items():
            if key.endswith("_gt"):
                field = key[:-3]
                if field not in payload or payload[field] <= expected:
                    return False
            elif key.endswith("_lt"):
                field = key[:-3]
                if field not in payload or payload[field] >= expected:
                    return False
            elif key.endswith("_contains"):
                field = key[:-9]
                if field not in payload or expected not in payload[field]:
                    return False
            else:
                if key not in payload or payload[key] != expected:
                    return False
        return True
