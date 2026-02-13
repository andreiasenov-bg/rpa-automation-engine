"""Celery tasks for async notification delivery."""

import asyncio
import logging

from worker.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="worker.tasks.notifications.send_notification",
    bind=True,
    max_retries=3,
    default_retry_delay=5,
    queue="notifications",
)
def send_notification(self, title: str, message: str, channel: str, recipient: str, priority: str = "normal", metadata: dict = None):
    """Send a notification asynchronously via Celery.

    Args:
        title: Notification title
        message: Notification body
        channel: Channel type (email, slack, webhook, websocket)
        recipient: Target recipient
        priority: Priority level
        metadata: Additional data
    """
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                _send(title, message, channel, recipient, priority, metadata or {})
            )
            return result
        finally:
            loop.close()
    except Exception as exc:
        logger.error(f"Notification send failed: {exc}")
        raise self.retry(exc=exc)


async def _send(title, message, channel, recipient, priority, metadata):
    from notifications.channels import Notification, NotificationChannel, NotificationPriority
    from notifications.manager import get_notification_manager

    manager = get_notification_manager()
    notification = Notification(
        title=title,
        message=message,
        channel=NotificationChannel(channel),
        priority=NotificationPriority(priority),
        recipient=recipient,
        metadata=metadata,
    )
    result = await manager.send(notification)
    return {"success": result.success, "error": result.error}
