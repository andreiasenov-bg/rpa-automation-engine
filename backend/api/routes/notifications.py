"""Notification API routes.

Manage notification channels, send test notifications, view status.
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional

from notifications.channels import NotificationChannel, NotificationPriority
from notifications.manager import get_notification_manager

router = APIRouter()


# -- Schemas --

class NotificationSendRequest(BaseModel):
    """Schema for sending a notification."""
    title: str
    message: str
    channel: str  # email, slack, webhook, websocket
    recipient: str = ""
    priority: str = "normal"
    metadata: dict = Field(default_factory=dict)


class ChannelConfigRequest(BaseModel):
    """Schema for configuring a notification channel."""
    channel: str
    config: dict


# -- Endpoints --

@router.get("/status", summary="Get notification manager status")
async def get_notification_status():
    """Get the current status of the notification system."""
    manager = get_notification_manager()
    return manager.get_status()


@router.post("/send", summary="Send a notification")
async def send_notification(request: NotificationSendRequest):
    """Send a notification through the specified channel."""
    from notifications.channels import Notification

    manager = get_notification_manager()

    try:
        channel = NotificationChannel(request.channel)
        priority = NotificationPriority(request.priority)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    notification = Notification(
        title=request.title,
        message=request.message,
        channel=channel,
        priority=priority,
        recipient=request.recipient,
        metadata=request.metadata,
    )

    result = await manager.send(notification)

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=result.error or "Delivery failed",
        )

    return {
        "success": True,
        "channel": result.channel.value,
        "recipient": result.recipient,
        "delivered_at": result.delivered_at,
    }


@router.post("/channels/configure", summary="Configure a notification channel")
async def configure_channel(request: ChannelConfigRequest):
    """Configure a notification channel (email, slack, webhook)."""
    manager = get_notification_manager()
    manager.configure_channels({request.channel: request.config})
    return {"message": f"Channel '{request.channel}' configured", "success": True}


@router.post("/test", summary="Send a test notification")
async def send_test_notification(channel: str = "websocket"):
    """Send a test notification to verify channel configuration."""
    manager = get_notification_manager()

    from notifications.channels import Notification
    try:
        ch = NotificationChannel(channel)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown channel: {channel}",
        )

    notification = Notification(
        title="Test Notification",
        message="This is a test notification from the RPA Automation Engine.",
        channel=ch,
        priority=NotificationPriority.NORMAL,
        metadata={"test": True},
    )

    result = await manager.send(notification)
    return {
        "success": result.success,
        "channel": channel,
        "error": result.error,
    }
