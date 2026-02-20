"""Notification channel implementations.

Each channel handles delivery for one transport (email, Slack, webhook, etc.).
The NotificationManager dispatches to the appropriate channel(s).
"""

import asyncio
import logging
import smtplib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from enum import Enum
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


# ─── Data Types ────────────────────────────────────────────────

class NotificationPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationChannel(str, Enum):
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    WEBSOCKET = "websocket"
    FCM = "fcm"
    IN_APP = "in_app"


@dataclass
class Notification:
    """A notification to be delivered."""
    title: str
    message: str
    channel: NotificationChannel
    priority: NotificationPriority = NotificationPriority.NORMAL
    recipient: str = ""  # email, Slack channel, webhook URL, user_id
    metadata: dict[str, Any] = field(default_factory=dict)
    organization_id: Optional[str] = None
    user_id: Optional[str] = None
    template: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class DeliveryResult:
    """Result of a notification delivery attempt."""
    success: bool
    channel: NotificationChannel
    recipient: str
    message: str = ""
    error: Optional[str] = None
    delivered_at: Optional[str] = None


# ─── Base Channel ──────────────────────────────────────────────

class BaseChannel(ABC):
    """Abstract base for notification channels."""

    channel_type: NotificationChannel

    @abstractmethod
    async def send(self, notification: Notification) -> DeliveryResult:
        """Send a notification through this channel."""
        ...

    @abstractmethod
    async def validate_config(self, config: dict) -> tuple[bool, Optional[str]]:
        """Validate channel-specific configuration."""
        ...


# ─── Email Channel ─────────────────────────────────────────────

class EmailChannel(BaseChannel):
    """Send notifications via SMTP email.

    Config:
        smtp_host, smtp_port, smtp_user, smtp_password,
        from_address, use_tls
    """

    channel_type = NotificationChannel.EMAIL

    def __init__(self, config: dict = None):
        self.config = config or {}

    async def send(self, notification: Notification) -> DeliveryResult:
        """Send email notification."""
        try:
            smtp_host = self.config.get("smtp_host", "localhost")
            smtp_port = self.config.get("smtp_port", 587)
            smtp_user = self.config.get("smtp_user", "")
            smtp_pass = self.config.get("smtp_password", "")
            from_addr = self.config.get("from_address", "rpa@localhost")
            use_tls = self.config.get("use_tls", True)

            msg = MIMEMultipart("alternative")
            msg["Subject"] = notification.title
            msg["From"] = from_addr
            msg["To"] = notification.recipient

            # Plain text
            msg.attach(MIMEText(notification.message, "plain"))

            # HTML version
            html = f"""
            <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #333;">{notification.title}</h2>
                <div style="color: #555; line-height: 1.6;">
                    {notification.message.replace(chr(10), '<br>')}
                </div>
                <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
                <p style="color: #999; font-size: 12px;">
                    Sent by RPA Automation Engine
                </p>
            </div>
            """
            msg.attach(MIMEText(html, "html"))

            # Send via SMTP (run in executor to avoid blocking)
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self._send_smtp(smtp_host, smtp_port, smtp_user, smtp_pass, from_addr, notification.recipient, msg, use_tls),
            )

            return DeliveryResult(
                success=True,
                channel=self.channel_type,
                recipient=notification.recipient,
                message="Email sent",
                delivered_at=datetime.now(timezone.utc).isoformat(),
            )

        except Exception as e:
            logger.error(f"Email send failed: {e}")
            return DeliveryResult(
                success=False,
                channel=self.channel_type,
                recipient=notification.recipient,
                error=str(e),
            )

    def _send_smtp(self, host, port, user, password, from_addr, to_addr, msg, use_tls):
        """Synchronous SMTP send."""
        with smtplib.SMTP(host, port) as server:
            if use_tls:
                server.starttls()
            if user and password:
                server.login(user, password)
            server.sendmail(from_addr, to_addr, msg.as_string())

    async def validate_config(self, config: dict) -> tuple[bool, Optional[str]]:
        if not config.get("smtp_host"):
            return False, "Missing smtp_host"
        return True, None


# ─── Slack Channel ─────────────────────────────────────────────

class SlackChannel(BaseChannel):
    """Send notifications to Slack via webhook or API.

    Config:
        webhook_url (for simple webhook) OR
        bot_token (for Slack API)
    """

    channel_type = NotificationChannel.SLACK

    def __init__(self, config: dict = None):
        self.config = config or {}

    async def send(self, notification: Notification) -> DeliveryResult:
        """Send Slack notification."""
        try:
            webhook_url = self.config.get("webhook_url")
            if not webhook_url:
                return DeliveryResult(
                    success=False,
                    channel=self.channel_type,
                    recipient=notification.recipient,
                    error="No Slack webhook URL configured",
                )

            # Build Slack message payload
            priority_emoji = {
                NotificationPriority.LOW: "",
                NotificationPriority.NORMAL: "",
                NotificationPriority.HIGH: ":warning:",
                NotificationPriority.CRITICAL: ":rotating_light:",
            }
            emoji = priority_emoji.get(notification.priority, "")

            payload = {
                "channel": notification.recipient or "#rpa-notifications",
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f"{emoji} {notification.title}".strip(),
                        },
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": notification.message,
                        },
                    },
                ],
            }

            # Add metadata fields if present
            if notification.metadata:
                fields = []
                for key, value in list(notification.metadata.items())[:10]:
                    fields.append({
                        "type": "mrkdwn",
                        "text": f"*{key}:*\n{value}",
                    })
                if fields:
                    payload["blocks"].append({
                        "type": "section",
                        "fields": fields[:10],
                    })

            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(webhook_url, json=payload)
                response.raise_for_status()

            return DeliveryResult(
                success=True,
                channel=self.channel_type,
                recipient=notification.recipient or "#rpa-notifications",
                message="Slack message sent",
                delivered_at=datetime.now(timezone.utc).isoformat(),
            )

        except Exception as e:
            logger.error(f"Slack send failed: {e}")
            return DeliveryResult(
                success=False,
                channel=self.channel_type,
                recipient=notification.recipient,
                error=str(e),
            )

    async def validate_config(self, config: dict) -> tuple[bool, Optional[str]]:
        if not config.get("webhook_url") and not config.get("bot_token"):
            return False, "Need either webhook_url or bot_token"
        return True, None


# ─── Webhook Channel ──────────────────────────────────────────

class WebhookChannel(BaseChannel):
    """Send notifications to arbitrary HTTP endpoints.

    Config:
        url: Target URL
        method: HTTP method (default POST)
        headers: Additional headers
        auth: Optional auth config
    """

    channel_type = NotificationChannel.WEBHOOK

    def __init__(self, config: dict = None):
        self.config = config or {}

    async def send(self, notification: Notification) -> DeliveryResult:
        """Send webhook notification."""
        try:
            url = notification.recipient or self.config.get("url")
            if not url:
                return DeliveryResult(
                    success=False,
                    channel=self.channel_type,
                    recipient="",
                    error="No webhook URL",
                )

            method = self.config.get("method", "POST").upper()
            headers = {
                "Content-Type": "application/json",
                "X-RPA-Event": "notification",
                **self.config.get("headers", {}),
            }

            payload = {
                "title": notification.title,
                "message": notification.message,
                "priority": notification.priority.value,
                "channel": notification.channel.value,
                "metadata": notification.metadata,
                "timestamp": notification.created_at,
            }

            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.request(method, url, json=payload, headers=headers)
                response.raise_for_status()

            return DeliveryResult(
                success=True,
                channel=self.channel_type,
                recipient=url,
                message=f"Webhook delivered (HTTP {response.status_code})",
                delivered_at=datetime.now(timezone.utc).isoformat(),
            )

        except Exception as e:
            logger.error(f"Webhook send failed: {e}")
            return DeliveryResult(
                success=False,
                channel=self.channel_type,
                recipient=notification.recipient,
                error=str(e),
            )

    async def validate_config(self, config: dict) -> tuple[bool, Optional[str]]:
        if not config.get("url"):
            return False, "Missing url"
        return True, None


# ─── WebSocket Channel (in-app real-time) ─────────────────────

class WebSocketChannel(BaseChannel):
    """Deliver real-time notifications via WebSocket.

    Uses the existing ConnectionManager to push to connected clients.
    """

    channel_type = NotificationChannel.WEBSOCKET

    def __init__(self, connection_manager=None):
        self._manager = connection_manager

    async def send(self, notification: Notification) -> DeliveryResult:
        """Push notification via WebSocket."""
        if not self._manager:
            return DeliveryResult(
                success=False,
                channel=self.channel_type,
                recipient=notification.recipient,
                error="WebSocket manager not available",
            )

        try:
            payload = {
                "type": "notification",
                "title": notification.title,
                "message": notification.message,
                "priority": notification.priority.value,
                "metadata": notification.metadata,
                "timestamp": notification.created_at,
            }

            if notification.user_id:
                await self._manager.send_to_user(notification.user_id, payload)
            elif notification.organization_id:
                await self._manager.send_to_org(notification.organization_id, payload)
            else:
                await self._manager.broadcast(payload)

            return DeliveryResult(
                success=True,
                channel=self.channel_type,
                recipient=notification.user_id or notification.organization_id or "broadcast",
                message="WebSocket notification pushed",
                delivered_at=datetime.now(timezone.utc).isoformat(),
            )

        except Exception as e:
            logger.error(f"WebSocket send failed: {e}")
            return DeliveryResult(
                success=False,
                channel=self.channel_type,
                recipient=notification.recipient,
                error=str(e),
            )

    async def validate_config(self, config: dict) -> tuple[bool, Optional[str]]:
        return True, None


# ─── Firebase Cloud Messaging (FCM) Channel ──────────────────

class FCMChannel(BaseChannel):
    """Send push notifications via Firebase Cloud Messaging (FCM v1 HTTP API).

    Config:
        service_account_json: Path to Firebase service account JSON file
        project_id: Firebase project ID

    Device tokens are stored per-user and passed via notification.recipient
    or notification.metadata["device_tokens"].
    """

    channel_type = NotificationChannel.FCM

    def __init__(self, config: dict = None):
        self.config = config or {}
        self._access_token: Optional[str] = None
        self._token_expiry: float = 0

    async def _get_access_token(self) -> str:
        """Get a valid OAuth2 access token for FCM v1 API.

        Uses the service account credentials to generate a short-lived token.
        Caches the token until it expires.
        """
        import time

        if self._access_token and time.time() < self._token_expiry - 60:
            return self._access_token

        try:
            from google.oauth2 import service_account
            from google.auth.transport.requests import Request

            sa_path = self.config.get("service_account_json", "")
            credentials = service_account.Credentials.from_service_account_file(
                sa_path,
                scopes=["https://www.googleapis.com/auth/firebase.messaging"],
            )
            credentials.refresh(Request())
            self._access_token = credentials.token
            self._token_expiry = credentials.expiry.timestamp() if credentials.expiry else time.time() + 3500
            return self._access_token
        except Exception as exc:
            logger.error("FCM token refresh failed: %s", exc)
            raise

    async def send(self, notification: Notification) -> DeliveryResult:
        """Send push notification via FCM v1 HTTP API."""
        try:
            project_id = self.config.get("project_id")
            if not project_id:
                return DeliveryResult(
                    success=False,
                    channel=self.channel_type,
                    recipient=notification.recipient,
                    error="FCM project_id not configured",
                )

            # Device tokens: from recipient (single) or metadata (multiple)
            tokens = []
            if notification.recipient:
                tokens.append(notification.recipient)
            if notification.metadata.get("device_tokens"):
                tokens.extend(notification.metadata["device_tokens"])

            if not tokens:
                return DeliveryResult(
                    success=False,
                    channel=self.channel_type,
                    recipient="",
                    error="No device tokens provided",
                )

            access_token = await self._get_access_token()
            url = f"https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"

            # Priority mapping
            android_priority = "high" if notification.priority in (
                NotificationPriority.HIGH, NotificationPriority.CRITICAL
            ) else "normal"

            sent = 0
            errors = []

            async with httpx.AsyncClient(timeout=10) as client:
                for token in tokens:
                    payload = {
                        "message": {
                            "token": token,
                            "notification": {
                                "title": notification.title,
                                "body": notification.message,
                            },
                            "data": {
                                k: str(v) for k, v in (notification.metadata or {}).items()
                                if k != "device_tokens"
                            },
                            "android": {
                                "priority": android_priority,
                                "notification": {
                                    "click_action": "OPEN_DASHBOARD",
                                    "channel_id": "rpa_alerts",
                                },
                            },
                            "webpush": {
                                "headers": {"Urgency": android_priority},
                                "notification": {
                                    "icon": "/icons/rpa-icon-192.png",
                                    "badge": "/icons/rpa-badge-72.png",
                                    "requireInteraction": notification.priority in (
                                        NotificationPriority.HIGH, NotificationPriority.CRITICAL
                                    ),
                                },
                            },
                        }
                    }

                    response = await client.post(
                        url,
                        json=payload,
                        headers={
                            "Authorization": f"Bearer {access_token}",
                            "Content-Type": "application/json",
                        },
                    )

                    if response.status_code == 200:
                        sent += 1
                    else:
                        errors.append(f"{token[:20]}...: HTTP {response.status_code}")
                        logger.warning(
                            "FCM send failed for token %s...: %s",
                            token[:20],
                            response.text,
                        )

            if sent > 0:
                return DeliveryResult(
                    success=True,
                    channel=self.channel_type,
                    recipient=f"{sent}/{len(tokens)} devices",
                    message=f"FCM push sent to {sent} device(s)",
                    delivered_at=datetime.now(timezone.utc).isoformat(),
                )
            else:
                return DeliveryResult(
                    success=False,
                    channel=self.channel_type,
                    recipient=f"0/{len(tokens)} devices",
                    error="; ".join(errors[:3]),
                )

        except Exception as e:
            logger.error("FCM send failed: %s", e)
            return DeliveryResult(
                success=False,
                channel=self.channel_type,
                recipient=notification.recipient,
                error=str(e),
            )

    async def validate_config(self, config: dict) -> tuple[bool, Optional[str]]:
        if not config.get("project_id"):
            return False, "Missing project_id"
        if not config.get("service_account_json"):
            return False, "Missing service_account_json path"
        return True, None
