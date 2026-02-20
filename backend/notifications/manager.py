"""Notification Manager — central dispatcher for all notification channels.

Routes notifications to the appropriate channel(s) based on
organization preferences and notification rules.
"""

import logging
from typing import Optional

from notifications.channels import (
    BaseChannel,
    DeliveryResult,
    EmailChannel,
    FCMChannel,
    Notification,
    NotificationChannel,
    NotificationPriority,
    SlackChannel,
    WebhookChannel,
    WebSocketChannel,
)

logger = logging.getLogger(__name__)


class NotificationManager:
    """Central notification dispatcher.

    Manages channel registration, notification routing,
    and delivery tracking. Singleton — use get_notification_manager().
    """

    def __init__(self):
        self._channels: dict[NotificationChannel, BaseChannel] = {}
        self._rules: list[dict] = []  # Routing rules
        self._initialized = False

    def register_channel(self, channel: BaseChannel) -> None:
        """Register a notification channel."""
        self._channels[channel.channel_type] = channel
        logger.info(f"Notification channel registered: {channel.channel_type.value}")

    def configure_channels(self, config: dict) -> None:
        """Configure all channels from app settings.

        Args:
            config: Dict with channel configs:
                {
                    "email": {"smtp_host": ..., "smtp_port": ...},
                    "slack": {"webhook_url": ...},
                    "webhook": {"url": ...},
                }
        """
        if "email" in config:
            self.register_channel(EmailChannel(config["email"]))

        if "slack" in config:
            self.register_channel(SlackChannel(config["slack"]))

        if "webhook" in config:
            self.register_channel(WebhookChannel(config["webhook"]))

        if "fcm" in config:
            self.register_channel(FCMChannel(config["fcm"]))

        # WebSocket is registered separately with a connection manager
        self._initialized = True

    def set_websocket_manager(self, connection_manager) -> None:
        """Set the WebSocket connection manager for real-time notifications."""
        self.register_channel(WebSocketChannel(connection_manager=connection_manager))

    async def send(self, notification: Notification) -> DeliveryResult:
        """Send a notification through the specified channel.

        Args:
            notification: Notification to send

        Returns:
            DeliveryResult
        """
        channel = self._channels.get(notification.channel)
        if not channel:
            return DeliveryResult(
                success=False,
                channel=notification.channel,
                recipient=notification.recipient,
                error=f"Channel not configured: {notification.channel.value}",
            )

        result = await channel.send(notification)

        if result.success:
            logger.info(
                f"Notification sent via {notification.channel.value} to {notification.recipient}"
            )
        else:
            logger.warning(
                f"Notification failed via {notification.channel.value}: {result.error}"
            )

        return result

    async def send_multi(
        self,
        title: str,
        message: str,
        channels: list[NotificationChannel],
        recipients: dict[NotificationChannel, str] = None,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        metadata: dict = None,
        organization_id: str = None,
        user_id: str = None,
    ) -> list[DeliveryResult]:
        """Send a notification to multiple channels at once.

        Args:
            title: Notification title
            message: Notification body
            channels: List of channels to send to
            recipients: Channel -> recipient mapping
            priority: Notification priority
            metadata: Additional data
            organization_id: Target organization
            user_id: Target user

        Returns:
            List of DeliveryResults, one per channel
        """
        recipients = recipients or {}
        results = []

        for ch in channels:
            notification = Notification(
                title=title,
                message=message,
                channel=ch,
                priority=priority,
                recipient=recipients.get(ch, ""),
                metadata=metadata or {},
                organization_id=organization_id,
                user_id=user_id,
            )
            result = await self.send(notification)
            results.append(result)

        return results

    # ─── Convenience methods for common events ─────────────────

    async def notify_workflow_completed(
        self,
        workflow_name: str,
        execution_id: str,
        organization_id: str,
        duration_ms: int = 0,
        channels: list[NotificationChannel] = None,
    ) -> list[DeliveryResult]:
        """Send notification when a workflow completes."""
        channels = channels or [NotificationChannel.WEBSOCKET]
        return await self.send_multi(
            title=f"Workflow completed: {workflow_name}",
            message=f"Execution {execution_id[:8]} finished successfully in {duration_ms/1000:.1f}s.",
            channels=channels,
            priority=NotificationPriority.NORMAL,
            metadata={"execution_id": execution_id, "duration_ms": duration_ms},
            organization_id=organization_id,
        )

    async def notify_workflow_failed(
        self,
        workflow_name: str,
        execution_id: str,
        error: str,
        organization_id: str,
        channels: list[NotificationChannel] = None,
    ) -> list[DeliveryResult]:
        """Send notification when a workflow fails.

        Dispatches to WebSocket (real-time), Slack, and FCM (push) by default.
        """
        default_channels = [NotificationChannel.WEBSOCKET, NotificationChannel.SLACK]
        # Add FCM if configured
        if NotificationChannel.FCM in self._channels:
            default_channels.append(NotificationChannel.FCM)
        # Add Email if configured
        if NotificationChannel.EMAIL in self._channels:
            default_channels.append(NotificationChannel.EMAIL)

        channels = channels or default_channels
        return await self.send_multi(
            title=f"Workflow FAILED: {workflow_name}",
            message=f"Execution {execution_id[:8]} failed: {error}",
            channels=channels,
            priority=NotificationPriority.HIGH,
            metadata={
                "execution_id": execution_id,
                "error": error,
                "type": "execution_failed",
            },
            organization_id=organization_id,
        )

    async def notify_integration_down(
        self,
        integration_name: str,
        error: str,
        organization_id: str = None,
        channels: list[NotificationChannel] = None,
    ) -> list[DeliveryResult]:
        """Send notification when an external integration is down."""
        channels = channels or [NotificationChannel.WEBSOCKET, NotificationChannel.SLACK]
        return await self.send_multi(
            title=f"Integration DOWN: {integration_name}",
            message=f"Health check failed: {error}",
            channels=channels,
            priority=NotificationPriority.CRITICAL,
            metadata={"integration": integration_name, "error": error},
            organization_id=organization_id,
        )

    async def notify_agent_disconnected(
        self,
        agent_name: str,
        organization_id: str,
        channels: list[NotificationChannel] = None,
    ) -> list[DeliveryResult]:
        """Send notification when an agent goes offline."""
        channels = channels or [NotificationChannel.WEBSOCKET]
        return await self.send_multi(
            title=f"Agent disconnected: {agent_name}",
            message=f"Agent '{agent_name}' has stopped sending heartbeats.",
            channels=channels,
            priority=NotificationPriority.HIGH,
            organization_id=organization_id,
        )

    def get_status(self) -> dict:
        """Get notification manager status."""
        return {
            "initialized": self._initialized,
            "channels": [ch.value for ch in self._channels.keys()],
            "rules_count": len(self._rules),
        }


# ─── Singleton ─────────────────────────────────────────────────

_manager: Optional[NotificationManager] = None


def get_notification_manager() -> NotificationManager:
    """Get or create the singleton NotificationManager."""
    global _manager
    if _manager is None:
        _manager = NotificationManager()
    return _manager
