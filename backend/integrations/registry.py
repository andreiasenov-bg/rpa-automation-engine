"""
External API & Integration Registry.

Central hub for managing all external connections the RPA platform uses.
Supports adding, configuring, health-checking, and monitoring APIs dynamically.

Features:
- Add any REST/GraphQL/SOAP/WebSocket API at runtime
- Automatic health checks on configurable intervals
- Connection pooling with persistent HTTP clients
- Auto-retry & reconnect on failures
- Detailed health history and uptime tracking
- Alert dispatch on failures (email, Slack, webhook)
- Credential injection from vault
- Rate limit awareness
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import httpx
import structlog

logger = structlog.get_logger(__name__)


class IntegrationType(str, Enum):
    """Supported integration types."""
    REST_API = "rest_api"
    GRAPHQL = "graphql"
    SOAP = "soap"
    WEBSOCKET = "websocket"
    DATABASE = "database"
    FTP_SFTP = "ftp_sftp"
    SMTP = "smtp"
    MQTT = "mqtt"
    CUSTOM = "custom"


class IntegrationStatus(str, Enum):
    """Health status of an integration."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"
    UNKNOWN = "unknown"
    DISABLED = "disabled"
    CHECKING = "checking"


class HealthCheckResult:
    """Result of a single health check."""

    def __init__(
        self,
        status: IntegrationStatus,
        response_time_ms: float = 0,
        status_code: Optional[int] = None,
        message: str = "",
        checked_at: Optional[datetime] = None,
    ):
        self.status = status
        self.response_time_ms = response_time_ms
        self.status_code = status_code
        self.message = message
        self.checked_at = checked_at or datetime.now(timezone.utc)

    def to_dict(self) -> dict:
        return {
            "status": self.status.value,
            "response_time_ms": round(self.response_time_ms, 2),
            "status_code": self.status_code,
            "message": self.message,
            "checked_at": self.checked_at.isoformat(),
        }


class IntegrationConfig:
    """Configuration for a single external integration."""

    def __init__(
        self,
        name: str,
        integration_type: IntegrationType,
        base_url: str,
        description: str = "",
        auth_type: str = "none",  # none, api_key, bearer, basic, oauth2, custom_header
        credential_id: Optional[str] = None,  # Reference to credential vault
        headers: Optional[Dict[str, str]] = None,
        timeout_seconds: int = 30,
        health_check_url: Optional[str] = None,  # e.g., /health, /ping, /status
        health_check_method: str = "GET",
        health_check_interval_seconds: int = 60,
        health_check_expected_status: int = 200,
        max_retries: int = 3,
        retry_delay_seconds: float = 1.0,
        rate_limit_per_minute: Optional[int] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        enabled: bool = True,
        alert_on_failure: bool = True,
        alert_channels: Optional[List[str]] = None,  # email, slack, webhook
        alert_after_n_failures: int = 3,
    ):
        self.id = str(uuid.uuid4())
        self.name = name
        self.integration_type = integration_type
        self.base_url = base_url.rstrip("/")
        self.description = description
        self.auth_type = auth_type
        self.credential_id = credential_id
        self.headers = headers or {}
        self.timeout_seconds = timeout_seconds
        self.health_check_url = health_check_url
        self.health_check_method = health_check_method
        self.health_check_interval_seconds = health_check_interval_seconds
        self.health_check_expected_status = health_check_expected_status
        self.max_retries = max_retries
        self.retry_delay_seconds = retry_delay_seconds
        self.rate_limit_per_minute = rate_limit_per_minute
        self.tags = tags or []
        self.metadata = metadata or {}
        self.enabled = enabled
        self.alert_on_failure = alert_on_failure
        self.alert_channels = alert_channels or ["email"]
        self.alert_after_n_failures = alert_after_n_failures
        self.created_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "integration_type": self.integration_type.value,
            "base_url": self.base_url,
            "description": self.description,
            "auth_type": self.auth_type,
            "credential_id": self.credential_id,
            "headers": {k: "***" if "key" in k.lower() or "token" in k.lower() else v
                       for k, v in self.headers.items()},
            "timeout_seconds": self.timeout_seconds,
            "health_check_url": self.health_check_url,
            "health_check_interval_seconds": self.health_check_interval_seconds,
            "max_retries": self.max_retries,
            "rate_limit_per_minute": self.rate_limit_per_minute,
            "tags": self.tags,
            "metadata": self.metadata,
            "enabled": self.enabled,
            "alert_on_failure": self.alert_on_failure,
            "alert_channels": self.alert_channels,
            "alert_after_n_failures": self.alert_after_n_failures,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "IntegrationConfig":
        """Restore config from DB data."""
        config = cls(
            name=data["name"],
            integration_type=IntegrationType(data["integration_type"]),
            base_url=data["base_url"],
            description=data.get("description", ""),
            auth_type=data.get("auth_type", "none"),
            credential_id=data.get("credential_id"),
            headers=data.get("headers", {}),
            timeout_seconds=data.get("timeout_seconds", 30),
            health_check_url=data.get("health_check_url"),
            health_check_method=data.get("health_check_method", "GET"),
            health_check_interval_seconds=data.get("health_check_interval_seconds", 60),
            health_check_expected_status=data.get("health_check_expected_status", 200),
            max_retries=data.get("max_retries", 3),
            retry_delay_seconds=data.get("retry_delay_seconds", 1.0),
            rate_limit_per_minute=data.get("rate_limit_per_minute"),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
            enabled=data.get("enabled", True),
            alert_on_failure=data.get("alert_on_failure", True),
            alert_channels=data.get("alert_channels", ["email"]),
            alert_after_n_failures=data.get("alert_after_n_failures", 3),
        )
        if "id" in data:
            config.id = data["id"]
        return config


class ManagedIntegration:
    """
    A live managed integration with HTTP client, health state, and history.

    Each registered API gets its own:
    - Persistent HTTP client with connection pooling
    - Health check loop
    - Request counter and rate limiter
    - Failure tracking and alerting
    """

    def __init__(self, config: IntegrationConfig):
        self.config = config
        self._client: Optional[httpx.AsyncClient] = None
        self.current_status = IntegrationStatus.UNKNOWN
        self.health_history: List[HealthCheckResult] = []
        self.consecutive_failures: int = 0
        self.total_requests: int = 0
        self.total_errors: int = 0
        self.last_request_at: Optional[datetime] = None
        self.last_error: Optional[str] = None
        self.last_error_at: Optional[datetime] = None
        self.uptime_since: Optional[datetime] = None
        self._rate_limit_tokens: int = config.rate_limit_per_minute or 9999
        self._rate_limit_last_refill: float = time.monotonic()
        self._alert_sent: bool = False

    async def connect(self):
        """Create the HTTP client for this integration."""
        headers = dict(self.config.headers)

        # Inject auth headers based on type
        # (credential_id would be resolved from vault in production)
        if self.config.auth_type == "api_key" and "X-API-Key" not in headers:
            headers["X-API-Key"] = "{{resolved_from_vault}}"
        elif self.config.auth_type == "bearer" and "Authorization" not in headers:
            headers["Authorization"] = "Bearer {{resolved_from_vault}}"

        self._client = httpx.AsyncClient(
            base_url=self.config.base_url,
            headers=headers,
            timeout=httpx.Timeout(float(self.config.timeout_seconds)),
            http2=True,
            limits=httpx.Limits(
                max_connections=10,
                max_keepalive_connections=5,
                keepalive_expiry=300,
            ),
        )
        logger.info("Integration connected", name=self.config.name, url=self.config.base_url)

    async def disconnect(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def request(
        self,
        method: str,
        path: str,
        data: Optional[dict] = None,
        params: Optional[dict] = None,
        headers: Optional[dict] = None,
    ) -> Dict[str, Any]:
        """
        Make a request to this API with retry and rate limiting.

        Returns dict with status_code, body, headers, duration_ms.
        """
        if not self.config.enabled:
            raise RuntimeError(f"Integration '{self.config.name}' is disabled")

        if not self._client:
            await self.connect()

        # Rate limiting
        await self._check_rate_limit()

        self.total_requests += 1
        self.last_request_at = datetime.now(timezone.utc)

        last_error = None
        for attempt in range(self.config.max_retries):
            start = time.monotonic()
            try:
                response = await self._client.request(
                    method=method.upper(),
                    url=path,
                    json=data if method.upper() in ("POST", "PUT", "PATCH") else None,
                    params=params,
                    headers=headers,
                )
                duration = (time.monotonic() - start) * 1000

                result = {
                    "status_code": response.status_code,
                    "body": self._parse_response(response),
                    "headers": dict(response.headers),
                    "duration_ms": round(duration, 2),
                    "integration": self.config.name,
                }

                if response.is_success:
                    self.consecutive_failures = 0
                    self._alert_sent = False
                    return result
                else:
                    last_error = f"HTTP {response.status_code}: {response.text[:200]}"
                    self.total_errors += 1

            except httpx.TimeoutException:
                duration = (time.monotonic() - start) * 1000
                last_error = f"Timeout after {duration:.0f}ms"
                self.total_errors += 1

            except httpx.ConnectError as e:
                last_error = f"Connection failed: {str(e)[:200]}"
                self.total_errors += 1

            except Exception as e:
                last_error = f"Request error: {str(e)[:200]}"
                self.total_errors += 1

            # Retry delay with backoff
            if attempt < self.config.max_retries - 1:
                delay = min(2 ** attempt * self.config.retry_delay_seconds, 30)
                await asyncio.sleep(delay)

        # All retries failed
        self.consecutive_failures += 1
        self.last_error = last_error
        self.last_error_at = datetime.now(timezone.utc)

        raise RuntimeError(
            f"API '{self.config.name}' request failed after {self.config.max_retries} retries: {last_error}"
        )

    async def health_check(self) -> HealthCheckResult:
        """Run a health check against this integration."""
        if not self.config.enabled:
            return HealthCheckResult(
                status=IntegrationStatus.DISABLED,
                message="Integration is disabled",
            )

        if not self.config.health_check_url:
            return HealthCheckResult(
                status=IntegrationStatus.UNKNOWN,
                message="No health check URL configured",
            )

        if not self._client:
            await self.connect()

        start = time.monotonic()
        try:
            response = await self._client.request(
                method=self.config.health_check_method,
                url=self.config.health_check_url,
            )
            duration = (time.monotonic() - start) * 1000

            if response.status_code == self.config.health_check_expected_status:
                status = IntegrationStatus.HEALTHY
                self.consecutive_failures = 0
                self._alert_sent = False
                if not self.uptime_since:
                    self.uptime_since = datetime.now(timezone.utc)
            elif response.status_code < 500:
                status = IntegrationStatus.DEGRADED
                self.consecutive_failures += 1
            else:
                status = IntegrationStatus.DOWN
                self.consecutive_failures += 1
                self.uptime_since = None

            result = HealthCheckResult(
                status=status,
                response_time_ms=duration,
                status_code=response.status_code,
                message=f"HTTP {response.status_code}",
            )

        except Exception as e:
            duration = (time.monotonic() - start) * 1000
            self.consecutive_failures += 1
            self.uptime_since = None
            result = HealthCheckResult(
                status=IntegrationStatus.DOWN,
                response_time_ms=duration,
                message=str(e)[:200],
            )

        self.current_status = result.status
        self.health_history.append(result)
        if len(self.health_history) > 500:
            self.health_history = self.health_history[-500:]

        # Trigger alert if needed
        if (
            result.status == IntegrationStatus.DOWN
            and self.config.alert_on_failure
            and self.consecutive_failures >= self.config.alert_after_n_failures
            and not self._alert_sent
        ):
            self._alert_sent = True
            await self._send_alert(result)

        return result

    async def _send_alert(self, health_result: HealthCheckResult):
        """Send alert notification when API goes down."""
        alert_data = {
            "integration_name": self.config.name,
            "integration_url": self.config.base_url,
            "status": health_result.status.value,
            "message": health_result.message,
            "consecutive_failures": self.consecutive_failures,
            "last_healthy": self.health_history[-2].checked_at.isoformat()
            if len(self.health_history) > 1
            else "never",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        logger.error(
            "ALERT: Integration is DOWN",
            integration=self.config.name,
            failures=self.consecutive_failures,
            **alert_data,
        )

        # Alert dispatch will be handled by notification service
        # For now, log the alert for the registry to pick up
        self._pending_alert = alert_data

    async def _check_rate_limit(self):
        """Token bucket rate limiter."""
        if not self.config.rate_limit_per_minute:
            return

        now = time.monotonic()
        elapsed = now - self._rate_limit_last_refill
        refill = elapsed * (self.config.rate_limit_per_minute / 60.0)
        self._rate_limit_tokens = min(
            self.config.rate_limit_per_minute,
            self._rate_limit_tokens + refill,
        )
        self._rate_limit_last_refill = now

        if self._rate_limit_tokens < 1:
            wait_time = (1 - self._rate_limit_tokens) / (self.config.rate_limit_per_minute / 60.0)
            logger.warning(
                "Rate limit hit, waiting",
                integration=self.config.name,
                wait_seconds=round(wait_time, 2),
            )
            await asyncio.sleep(wait_time)
            self._rate_limit_tokens = 1

        self._rate_limit_tokens -= 1

    def _parse_response(self, response: httpx.Response) -> Any:
        """Parse response body."""
        content_type = response.headers.get("content-type", "")
        if "json" in content_type:
            try:
                return response.json()
            except Exception:
                return response.text
        return response.text

    def get_stats(self) -> dict:
        """Get integration statistics."""
        healthy_checks = [h for h in self.health_history if h.status == IntegrationStatus.HEALTHY]
        avg_response = (
            sum(h.response_time_ms for h in healthy_checks) / len(healthy_checks)
            if healthy_checks
            else 0
        )

        return {
            "id": self.config.id,
            "name": self.config.name,
            "type": self.config.integration_type.value,
            "base_url": self.config.base_url,
            "status": self.current_status.value,
            "enabled": self.config.enabled,
            "total_requests": self.total_requests,
            "total_errors": self.total_errors,
            "error_rate": round(
                (self.total_errors / max(self.total_requests, 1)) * 100, 2
            ),
            "consecutive_failures": self.consecutive_failures,
            "avg_response_time_ms": round(avg_response, 2),
            "last_request_at": self.last_request_at.isoformat() if self.last_request_at else None,
            "last_error": self.last_error,
            "last_error_at": self.last_error_at.isoformat() if self.last_error_at else None,
            "uptime_since": self.uptime_since.isoformat() if self.uptime_since else None,
            "health_checks_count": len(self.health_history),
            "tags": self.config.tags,
        }


class IntegrationRegistry:
    """
    Central registry for all external API integrations.

    Manages the lifecycle of external connections:
    - Registration and configuration
    - Connection pooling
    - Periodic health checking
    - Alert dispatching
    - Statistics and reporting
    """

    def __init__(self):
        self._integrations: Dict[str, ManagedIntegration] = {}
        self._health_check_task: Optional[asyncio.Task] = None
        self._alert_callbacks: List[Callable] = []
        self._running = False

    async def register(self, config: IntegrationConfig) -> ManagedIntegration:
        """Register a new external API integration."""
        if config.id in self._integrations:
            logger.warning("Integration already registered, updating", name=config.name)
            await self.unregister(config.id)

        integration = ManagedIntegration(config)
        if config.enabled:
            await integration.connect()
            # Initial health check
            await integration.health_check()

        self._integrations[config.id] = integration
        logger.info(
            "Integration registered",
            name=config.name,
            type=config.integration_type.value,
            url=config.base_url,
        )
        return integration

    async def unregister(self, integration_id: str):
        """Remove an integration."""
        integration = self._integrations.pop(integration_id, None)
        if integration:
            await integration.disconnect()
            logger.info("Integration unregistered", name=integration.config.name)

    def get(self, integration_id: str) -> Optional[ManagedIntegration]:
        """Get an integration by ID."""
        return self._integrations.get(integration_id)

    def get_by_name(self, name: str) -> Optional[ManagedIntegration]:
        """Get an integration by name."""
        for integration in self._integrations.values():
            if integration.config.name == name:
                return integration
        return None

    def list_all(self) -> List[dict]:
        """List all integrations with their stats."""
        return [i.get_stats() for i in self._integrations.values()]

    def list_by_status(self, status: IntegrationStatus) -> List[dict]:
        """List integrations filtered by status."""
        return [
            i.get_stats()
            for i in self._integrations.values()
            if i.current_status == status
        ]

    def list_by_tag(self, tag: str) -> List[dict]:
        """List integrations filtered by tag."""
        return [
            i.get_stats()
            for i in self._integrations.values()
            if tag in i.config.tags
        ]

    async def check_health_all(self) -> Dict[str, HealthCheckResult]:
        """Run health check on all enabled integrations."""
        results = {}
        for integration_id, integration in self._integrations.items():
            if integration.config.enabled and integration.config.health_check_url:
                results[integration_id] = await integration.health_check()
        return results

    async def start_health_monitor(self):
        """Start periodic health checking in background."""
        if self._running:
            return
        self._running = True
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        logger.info("Health monitor started")

    async def stop_health_monitor(self):
        """Stop periodic health checking."""
        self._running = False
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        logger.info("Health monitor stopped")

    async def _health_check_loop(self):
        """Background loop that checks integration health periodically."""
        while self._running:
            for integration in self._integrations.values():
                if not integration.config.enabled or not integration.config.health_check_url:
                    continue

                try:
                    result = await integration.health_check()
                    if result.status == IntegrationStatus.DOWN:
                        logger.warning(
                            "Integration unhealthy",
                            name=integration.config.name,
                            failures=integration.consecutive_failures,
                        )
                except Exception as e:
                    logger.error(
                        "Health check error",
                        name=integration.config.name,
                        error=str(e),
                    )

            # Wait for shortest interval among all integrations
            min_interval = min(
                (i.config.health_check_interval_seconds
                 for i in self._integrations.values()
                 if i.config.enabled and i.config.health_check_url),
                default=60,
            )
            await asyncio.sleep(min_interval)

    def get_dashboard(self) -> dict:
        """Get a summary dashboard of all integrations."""
        all_integrations = list(self._integrations.values())
        healthy = sum(1 for i in all_integrations if i.current_status == IntegrationStatus.HEALTHY)
        degraded = sum(1 for i in all_integrations if i.current_status == IntegrationStatus.DEGRADED)
        down = sum(1 for i in all_integrations if i.current_status == IntegrationStatus.DOWN)
        disabled = sum(1 for i in all_integrations if i.current_status == IntegrationStatus.DISABLED)

        total_requests = sum(i.total_requests for i in all_integrations)
        total_errors = sum(i.total_errors for i in all_integrations)

        return {
            "total_integrations": len(all_integrations),
            "healthy": healthy,
            "degraded": degraded,
            "down": down,
            "disabled": disabled,
            "overall_status": (
                "healthy" if down == 0 and degraded == 0
                else "degraded" if down == 0
                else "critical"
            ),
            "total_requests": total_requests,
            "total_errors": total_errors,
            "error_rate": round((total_errors / max(total_requests, 1)) * 100, 2),
            "integrations": [i.get_stats() for i in all_integrations],
            "alerts": [
                {
                    "integration": i.config.name,
                    "status": i.current_status.value,
                    "consecutive_failures": i.consecutive_failures,
                    "last_error": i.last_error,
                }
                for i in all_integrations
                if i.current_status == IntegrationStatus.DOWN
            ],
        }

    async def persist_all(self, db_session):
        """Save all integration configs to database."""
        if not db_session:
            return
        try:
            from sqlalchemy import text
            for integration in self._integrations.values():
                config_json = json.dumps(integration.config.to_dict())
                await db_session.execute(
                    text("""
                        INSERT INTO integration_configs (id, config_data, updated_at)
                        VALUES (:id, :config_data, :updated_at)
                        ON CONFLICT (id) DO UPDATE
                        SET config_data = :config_data, updated_at = :updated_at
                    """),
                    {
                        "id": integration.config.id,
                        "config_data": config_json,
                        "updated_at": datetime.now(timezone.utc),
                    },
                )
            await db_session.commit()
        except Exception as e:
            logger.error("Failed to persist integrations", error=str(e))

    async def load_all(self, db_session):
        """Load all integration configs from database on startup."""
        if not db_session:
            return
        try:
            from sqlalchemy import text
            result = await db_session.execute(
                text("SELECT config_data FROM integration_configs")
            )
            rows = result.fetchall()
            for row in rows:
                config_data = json.loads(row[0]) if isinstance(row[0], str) else row[0]
                config = IntegrationConfig.from_dict(config_data)
                await self.register(config)
            logger.info("Loaded integrations from DB", count=len(rows))
        except Exception as e:
            logger.error("Failed to load integrations", error=str(e))


# ─── Singleton ─────────────────────────────────────────────────────

_registry: Optional[IntegrationRegistry] = None


def get_integration_registry() -> IntegrationRegistry:
    """Get or create the singleton integration registry."""
    global _registry
    if _registry is None:
        _registry = IntegrationRegistry()
    return _registry
