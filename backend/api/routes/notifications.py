"""Notification API routes.

Manage notification channels, send test notifications, view status.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional

from app.dependencies import get_current_active_user

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


# ─── FCM Device Token Management ────────────────────────────

class FCMTokenRequest(BaseModel):
    """Register a device token for push notifications."""
    token: str
    device_name: str = "Unknown"
    platform: str = "web"  # web, android, ios


# In-memory token store (per-org). In production, persist to DB.
_device_tokens: dict[str, list[dict]] = {}


@router.post("/fcm/register", summary="Register FCM device token")
async def register_fcm_token(
    request: FCMTokenRequest,
    current_user=Depends(get_current_active_user),
):
    """Register a device token for push notifications."""
    org_id = current_user.org_id
    user_id = current_user.sub

    if org_id not in _device_tokens:
        _device_tokens[org_id] = []

    # Remove existing entry for same token
    _device_tokens[org_id] = [
        t for t in _device_tokens[org_id] if t["token"] != request.token
    ]

    _device_tokens[org_id].append({
        "token": request.token,
        "user_id": user_id,
        "device_name": request.device_name,
        "platform": request.platform,
    })

    return {"success": True, "message": "Device registered for push notifications"}


@router.delete("/fcm/unregister", summary="Unregister FCM device token")
async def unregister_fcm_token(
    token: str,
    current_user=Depends(get_current_active_user),
):
    """Remove a device token."""
    org_id = current_user.org_id
    if org_id in _device_tokens:
        _device_tokens[org_id] = [
            t for t in _device_tokens[org_id] if t["token"] != token
        ]
    return {"success": True}


@router.get("/fcm/tokens", summary="List registered FCM tokens")
async def list_fcm_tokens(
    current_user=Depends(get_current_active_user),
):
    """List registered device tokens for the current organization."""
    org_id = current_user.org_id
    tokens = _device_tokens.get(org_id, [])
    return {
        "tokens": [
            {"device_name": t["device_name"], "platform": t["platform"]}
            for t in tokens
        ],
        "count": len(tokens),
    }
