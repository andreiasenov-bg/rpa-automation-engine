"""
Integration Task — Call any registered external API from a workflow.

Uses the Integration Registry to make requests to registered APIs,
with automatic auth injection, rate limiting, and failure reporting.
"""

from typing import Any, Dict, Optional

from tasks.base_task import BaseTask, TaskResult
from integrations.registry import get_integration_registry


class IntegrationRequestTask(BaseTask):
    """Make a request to a registered external API."""

    task_type = "integration_request"
    display_name = "API Request (Registered)"
    description = "Call a registered external API integration with health tracking and auto-retry"
    icon = "🔌"

    async def execute(self, config: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> TaskResult:
        registry = get_integration_registry()

        integration_name = config.get("integration_name") or config.get("integration_id")
        if not integration_name:
            return TaskResult(success=False, error="integration_name or integration_id is required")

        # Find integration by name or ID
        integration = registry.get(integration_name) or registry.get_by_name(integration_name)
        if not integration:
            available = [i["name"] for i in registry.list_all()]
            return TaskResult(
                success=False,
                error=f"Integration '{integration_name}' not found. Available: {available}",
            )

        method = config.get("method", "GET")
        path = config.get("path", "/")
        data = config.get("data")
        params = config.get("params")
        headers = config.get("headers")

        # Resolve variables from context
        if context:
            path = self._resolve_vars(path, context)
            if isinstance(data, dict):
                data = {k: self._resolve_vars(str(v), context) if isinstance(v, str) else v
                       for k, v in data.items()}
            if isinstance(params, dict):
                params = {k: self._resolve_vars(str(v), context) if isinstance(v, str) else v
                         for k, v in params.items()}

        try:
            result = await integration.request(
                method=method,
                path=path,
                data=data,
                params=params,
                headers=headers,
            )
            return TaskResult(
                success=True,
                output=result.get("body"),
                metadata={
                    "status_code": result.get("status_code"),
                    "duration_ms": result.get("duration_ms"),
                    "integration": integration.config.name,
                },
            )
        except Exception as e:
            return TaskResult(
                success=False,
                error=str(e),
                metadata={
                    "integration": integration.config.name,
                    "status": integration.current_status.value,
                    "consecutive_failures": integration.consecutive_failures,
                },
            )

    def _resolve_vars(self, text: str, context: Dict[str, Any]) -> str:
        for key, value in context.items():
            text = text.replace(f"{{{{{key}}}}}", str(value))
        return text

    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "integration_name": {"type": "string", "description": "Registered integration name or ID"},
                "method": {"type": "string", "enum": ["GET", "POST", "PUT", "PATCH", "DELETE"], "description": "HTTP method"},
                "path": {"type": "string", "description": "API path (e.g., /api/orders)"},
                "data": {"type": "object", "description": "Request body (for POST/PUT/PATCH)"},
                "params": {"type": "object", "description": "Query parameters"},
                "headers": {"type": "object", "description": "Additional headers"},
            },
            "required": ["integration_name"],
        }


class IntegrationHealthTask(BaseTask):
    """Check health of a registered integration."""

    task_type = "integration_health_check"
    display_name = "API Health Check"
    description = "Check if a registered API is healthy and report status"
    icon = "🏥"

    async def execute(self, config: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> TaskResult:
        registry = get_integration_registry()

        integration_name = config.get("integration_name")
        check_all = config.get("check_all", False)

        if check_all:
            results = await registry.check_health_all()
            dashboard = registry.get_dashboard()
            return TaskResult(
                success=dashboard["overall_status"] != "critical",
                output=dashboard,
                metadata={"total": dashboard["total_integrations"], "down": dashboard["down"]},
            )

        if not integration_name:
            return TaskResult(success=False, error="integration_name is required (or set check_all=true)")

        integration = registry.get_by_name(integration_name) or registry.get(integration_name)
        if not integration:
            return TaskResult(success=False, error=f"Integration '{integration_name}' not found")

        result = await integration.health_check()
        return TaskResult(
            success=result.status.value in ("healthy", "degraded"),
            output=result.to_dict(),
            metadata={
                "integration": integration.config.name,
                "consecutive_failures": integration.consecutive_failures,
            },
        )

    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "integration_name": {"type": "string", "description": "Integration to check"},
                "check_all": {"type": "boolean", "description": "Check all integrations"},
            },
        }


INTEGRATION_TASK_TYPES = {
    "integration_request": IntegrationRequestTask,
    "integration_health_check": IntegrationHealthTask,
}
