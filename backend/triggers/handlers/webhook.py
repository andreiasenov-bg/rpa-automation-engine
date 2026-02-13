"""Webhook trigger handler.

Registers webhook routes dynamically in FastAPI so external
systems can POST to /api/v1/webhooks/<path> to trigger workflows.
"""

import hashlib
import hmac
import secrets
from typing import Optional

from triggers.base import BaseTriggerHandler, TriggerEvent, TriggerResult, TriggerTypeEnum


class WebhookTriggerHandler(BaseTriggerHandler):
    """Handler for webhook-based triggers.

    Config schema:
        {
            "path": "/hooks/my-hook",        # webhook path (auto-prefixed)
            "secret": "...",                  # optional HMAC secret for signature verification
            "methods": ["POST"],              # allowed HTTP methods
            "headers_filter": {},             # optional headers that must be present
            "payload_filter": {}              # optional JSONPath filter on body
        }
    """

    trigger_type = TriggerTypeEnum.WEBHOOK

    def __init__(self):
        # Active webhooks: trigger_id -> config
        self._active: dict[str, dict] = {}
        # Path -> trigger_id mapping for routing
        self._path_map: dict[str, str] = {}

    async def start(self, trigger_id: str, config: dict) -> TriggerResult:
        """Register a webhook endpoint."""
        path = config.get("path", f"/hooks/{trigger_id}")
        if not path.startswith("/"):
            path = f"/{path}"

        # Generate secret if not provided
        if "secret" not in config or not config["secret"]:
            config["secret"] = secrets.token_urlsafe(32)

        self._active[trigger_id] = config
        self._path_map[path] = trigger_id

        return TriggerResult(
            success=True,
            message=f"Webhook registered at {path}",
            trigger_id=trigger_id,
        )

    async def stop(self, trigger_id: str) -> TriggerResult:
        """Unregister a webhook endpoint."""
        config = self._active.pop(trigger_id, None)
        if config:
            path = config.get("path", f"/hooks/{trigger_id}")
            self._path_map.pop(path, None)

        return TriggerResult(
            success=True,
            message="Webhook unregistered",
            trigger_id=trigger_id,
        )

    async def test(self, config: dict) -> TriggerResult:
        """Validate webhook configuration."""
        is_valid, error = self.validate_config(config)
        if not is_valid:
            return TriggerResult(
                success=False,
                message=f"Invalid config: {error}",
                trigger_id="test",
            )
        return TriggerResult(
            success=True,
            message="Webhook configuration is valid",
            trigger_id="test",
        )

    def validate_config(self, config: dict) -> tuple[bool, Optional[str]]:
        """Validate webhook config."""
        if not isinstance(config, dict):
            return False, "Config must be a dict"
        methods = config.get("methods", ["POST"])
        valid_methods = {"GET", "POST", "PUT", "PATCH", "DELETE"}
        for m in methods:
            if m.upper() not in valid_methods:
                return False, f"Invalid HTTP method: {m}"
        return True, None

    def verify_signature(self, trigger_id: str, body: bytes, signature: str) -> bool:
        """Verify HMAC signature for a webhook payload."""
        config = self._active.get(trigger_id)
        if not config or not config.get("secret"):
            return True  # No secret configured, skip verification

        expected = hmac.new(
            config["secret"].encode(),
            body,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(f"sha256={expected}", signature)

    def get_trigger_for_path(self, path: str) -> Optional[str]:
        """Look up trigger_id by webhook path."""
        return self._path_map.get(path)

    def list_active(self) -> dict[str, dict]:
        """Return all active webhooks."""
        return dict(self._active)
