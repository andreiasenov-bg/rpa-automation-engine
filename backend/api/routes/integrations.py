"""
Integration Management API Routes.

CRUD and monitoring endpoints for external API connections.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from integrations.registry import (
    IntegrationConfig,
    IntegrationStatus,
    IntegrationType,
    get_integration_registry,
)


router = APIRouter()


# ─── Schemas ─────────────────────────────────────────────────────────

class IntegrationCreateRequest(BaseModel):
    name: str
    integration_type: str  # rest_api, graphql, soap, websocket, database, etc.
    base_url: str
    description: str = ""
    auth_type: str = "none"  # none, api_key, bearer, basic, oauth2
    credential_id: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    timeout_seconds: int = 30
    health_check_url: Optional[str] = None
    health_check_method: str = "GET"
    health_check_interval_seconds: int = 60
    health_check_expected_status: int = 200
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    rate_limit_per_minute: Optional[int] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    enabled: bool = True
    alert_on_failure: bool = True
    alert_channels: Optional[List[str]] = None
    alert_after_n_failures: int = 3


class IntegrationUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    base_url: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    timeout_seconds: Optional[int] = None
    health_check_url: Optional[str] = None
    health_check_interval_seconds: Optional[int] = None
    max_retries: Optional[int] = None
    rate_limit_per_minute: Optional[int] = None
    enabled: Optional[bool] = None
    alert_on_failure: Optional[bool] = None
    alert_after_n_failures: Optional[int] = None
    tags: Optional[List[str]] = None


class IntegrationTestRequest(BaseModel):
    method: str = "GET"
    path: str = "/"
    data: Optional[dict] = None
    params: Optional[dict] = None


# ─── Endpoints ───────────────────────────────────────────────────────

@router.get("/dashboard")
async def get_integrations_dashboard():
    """Get overview dashboard of all integrations with health status."""
    registry = get_integration_registry()
    return registry.get_dashboard()


@router.get("/")
async def list_integrations(
    status: Optional[str] = None,
    tag: Optional[str] = None,
):
    """List all registered integrations, optionally filtered."""
    registry = get_integration_registry()

    if status:
        try:
            return registry.list_by_status(IntegrationStatus(status))
        except ValueError:
            raise HTTPException(400, f"Invalid status: {status}")

    if tag:
        return registry.list_by_tag(tag)

    return registry.list_all()


@router.post("/", status_code=201)
async def register_integration(request: IntegrationCreateRequest):
    """Register a new external API integration."""
    registry = get_integration_registry()

    try:
        int_type = IntegrationType(request.integration_type)
    except ValueError:
        raise HTTPException(
            400,
            f"Invalid type: {request.integration_type}. "
            f"Valid: {[t.value for t in IntegrationType]}",
        )

    config = IntegrationConfig(
        name=request.name,
        integration_type=int_type,
        base_url=request.base_url,
        description=request.description,
        auth_type=request.auth_type,
        credential_id=request.credential_id,
        headers=request.headers,
        timeout_seconds=request.timeout_seconds,
        health_check_url=request.health_check_url,
        health_check_method=request.health_check_method,
        health_check_interval_seconds=request.health_check_interval_seconds,
        health_check_expected_status=request.health_check_expected_status,
        max_retries=request.max_retries,
        retry_delay_seconds=request.retry_delay_seconds,
        rate_limit_per_minute=request.rate_limit_per_minute,
        tags=request.tags,
        metadata=request.metadata,
        enabled=request.enabled,
        alert_on_failure=request.alert_on_failure,
        alert_channels=request.alert_channels,
        alert_after_n_failures=request.alert_after_n_failures,
    )

    integration = await registry.register(config)
    return integration.get_stats()


@router.get("/{integration_id}")
async def get_integration(integration_id: str):
    """Get integration details and stats."""
    registry = get_integration_registry()
    integration = registry.get(integration_id)
    if not integration:
        raise HTTPException(404, "Integration not found")
    return integration.get_stats()


@router.put("/{integration_id}")
async def update_integration(integration_id: str, request: IntegrationUpdateRequest):
    """Update integration configuration."""
    registry = get_integration_registry()
    integration = registry.get(integration_id)
    if not integration:
        raise HTTPException(404, "Integration not found")

    config = integration.config
    for field, value in request.dict(exclude_none=True).items():
        if hasattr(config, field):
            setattr(config, field, value)

    # Reconnect if URL changed
    if request.base_url:
        await integration.disconnect()
        await integration.connect()

    return integration.get_stats()


@router.delete("/{integration_id}")
async def remove_integration(integration_id: str):
    """Remove an integration."""
    registry = get_integration_registry()
    integration = registry.get(integration_id)
    if not integration:
        raise HTTPException(404, "Integration not found")

    await registry.unregister(integration_id)
    return {"message": f"Integration '{integration.config.name}' removed"}


@router.post("/{integration_id}/toggle")
async def toggle_integration(integration_id: str):
    """Enable or disable an integration."""
    registry = get_integration_registry()
    integration = registry.get(integration_id)
    if not integration:
        raise HTTPException(404, "Integration not found")

    integration.config.enabled = not integration.config.enabled
    status = "enabled" if integration.config.enabled else "disabled"

    if integration.config.enabled:
        await integration.connect()
        await integration.health_check()
    else:
        await integration.disconnect()
        integration.current_status = IntegrationStatus.DISABLED

    return {"message": f"Integration '{integration.config.name}' {status}", "enabled": integration.config.enabled}


@router.post("/{integration_id}/health-check")
async def run_health_check(integration_id: str):
    """Manually trigger a health check."""
    registry = get_integration_registry()
    integration = registry.get(integration_id)
    if not integration:
        raise HTTPException(404, "Integration not found")

    result = await integration.health_check()
    return result.to_dict()


@router.get("/{integration_id}/health-history")
async def get_health_history(integration_id: str, limit: int = 50):
    """Get health check history for an integration."""
    registry = get_integration_registry()
    integration = registry.get(integration_id)
    if not integration:
        raise HTTPException(404, "Integration not found")

    history = integration.health_history[-limit:]
    return [h.to_dict() for h in reversed(history)]


@router.post("/{integration_id}/test")
async def test_integration(integration_id: str, request: IntegrationTestRequest):
    """Send a test request to an integration."""
    registry = get_integration_registry()
    integration = registry.get(integration_id)
    if not integration:
        raise HTTPException(404, "Integration not found")

    try:
        result = await integration.request(
            method=request.method,
            path=request.path,
            data=request.data,
            params=request.params,
        )
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/health-check-all")
async def check_all_health():
    """Run health check on all enabled integrations."""
    registry = get_integration_registry()
    results = await registry.check_health_all()
    return {
        integration_id: result.to_dict()
        for integration_id, result in results.items()
    }


@router.get("/alerts/active")
async def get_active_alerts():
    """Get currently active alerts (integrations that are down)."""
    registry = get_integration_registry()
    dashboard = registry.get_dashboard()
    return dashboard.get("alerts", [])
