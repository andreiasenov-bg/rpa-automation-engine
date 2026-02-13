"""HTTP Request task implementation.

Makes HTTP requests to external APIs/services.
Supports all methods, custom headers, auth, timeouts,
response parsing, and response validation.
"""

import json
from typing import Any, Dict, Optional

import httpx
import structlog

from tasks.base_task import BaseTask, TaskResult

logger = structlog.get_logger(__name__)


class HttpRequestTask(BaseTask):
    """Execute HTTP requests to external services.

    Config:
        url: Target URL (required)
        method: HTTP method — GET, POST, PUT, PATCH, DELETE (default: GET)
        headers: Dict of HTTP headers
        params: URL query parameters
        body: Request body (for POST/PUT/PATCH)
        body_type: "json" | "form" | "text" (default: json)
        auth: Auth config { "type": "bearer|basic|api_key", "token|username|key": "..." }
        timeout: Request timeout in seconds (default: 30)
        follow_redirects: Whether to follow redirects (default: true)
        validate: Response validation rules
            {
                "status_code": [200, 201],
                "json_path": "$.data",
                "contains": "success"
            }
        extract: What to extract from response
            {
                "json_path": "$.data.items",
                "headers": ["X-Request-Id"],
            }
    """

    task_type = "http_request"
    display_name = "HTTP Request"
    description = "Make HTTP requests to APIs and web services"
    icon = "🌐"

    async def execute(self, config: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> TaskResult:
        url = config.get("url")
        if not url:
            return TaskResult(success=False, error="Missing required config: url")

        method = config.get("method", "GET").upper()
        headers = config.get("headers", {})
        params = config.get("params", {})
        body = config.get("body")
        body_type = config.get("body_type", "json")
        timeout = config.get("timeout", 30)
        follow_redirects = config.get("follow_redirects", True)

        # Apply authentication
        auth_config = config.get("auth", {})
        if auth_config:
            auth_type = auth_config.get("type", "")
            if auth_type == "bearer":
                headers["Authorization"] = f"Bearer {auth_config['token']}"
            elif auth_type == "basic":
                import base64
                creds = base64.b64encode(
                    f"{auth_config['username']}:{auth_config['password']}".encode()
                ).decode()
                headers["Authorization"] = f"Basic {creds}"
            elif auth_type == "api_key":
                header_name = auth_config.get("header", "X-API-Key")
                headers[header_name] = auth_config["key"]

        # Build request kwargs
        kwargs: Dict[str, Any] = {
            "method": method,
            "url": url,
            "headers": headers,
            "params": params,
            "timeout": timeout,
            "follow_redirects": follow_redirects,
        }

        if body and method in ("POST", "PUT", "PATCH"):
            if body_type == "json":
                kwargs["json"] = body if isinstance(body, dict) else json.loads(body)
            elif body_type == "form":
                kwargs["data"] = body
            else:
                kwargs["content"] = str(body)

        try:
            async with httpx.AsyncClient() as client:
                response = await client.request(**kwargs)

            # Parse response
            try:
                response_data = response.json()
            except Exception:
                response_data = response.text

            output = {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "data": response_data,
                "url": str(response.url),
                "elapsed_ms": response.elapsed.total_seconds() * 1000 if response.elapsed else 0,
            }

            # Validate response if rules provided
            validate = config.get("validate", {})
            if validate:
                valid_codes = validate.get("status_code", [])
                if valid_codes and response.status_code not in valid_codes:
                    return TaskResult(
                        success=False,
                        output=output,
                        error=f"Unexpected status code: {response.status_code} (expected {valid_codes})",
                    )

            # Extract specific data if configured
            extract = config.get("extract", {})
            if extract:
                extracted = {}
                if "headers" in extract:
                    extracted["headers"] = {
                        h: response.headers.get(h) for h in extract["headers"]
                    }
                if "json_path" in extract and isinstance(response_data, dict):
                    extracted["data"] = self._extract_json_path(
                        response_data, extract["json_path"]
                    )
                output["extracted"] = extracted

            # Determine success based on status code
            success = 200 <= response.status_code < 400

            return TaskResult(
                success=success,
                output=output,
                error=None if success else f"HTTP {response.status_code}",
            )

        except httpx.TimeoutException:
            return TaskResult(success=False, error=f"Request timed out after {timeout}s")
        except httpx.ConnectError as e:
            return TaskResult(success=False, error=f"Connection failed: {str(e)}")
        except Exception as e:
            return TaskResult(success=False, error=f"HTTP request failed: {str(e)}")

    def _extract_json_path(self, data: Any, path: str) -> Any:
        """Simple dot-notation JSON path extraction (e.g. 'data.items')."""
        parts = path.lstrip("$.").split(".")
        current = data
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list):
                try:
                    current = current[int(part)]
                except (ValueError, IndexError):
                    return None
            else:
                return None
        return current

    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["url"],
            "properties": {
                "url": {"type": "string", "description": "Target URL"},
                "method": {"type": "string", "enum": ["GET", "POST", "PUT", "PATCH", "DELETE"]},
                "headers": {"type": "object"},
                "params": {"type": "object"},
                "body": {"description": "Request body"},
                "body_type": {"type": "string", "enum": ["json", "form", "text"]},
                "auth": {"type": "object"},
                "timeout": {"type": "integer", "default": 30},
                "validate": {"type": "object"},
                "extract": {"type": "object"},
            },
        }


class HttpDownloadTask(BaseTask):
    """Download a file from a URL."""

    task_type = "http_download"
    display_name = "HTTP Download"
    description = "Download files from URLs"
    icon = "📥"

    async def execute(self, config: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> TaskResult:
        url = config.get("url")
        if not url:
            return TaskResult(success=False, error="Missing required config: url")

        save_path = config.get("save_path", "/tmp/download")
        timeout = config.get("timeout", 120)

        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
                response = await client.get(url)
                response.raise_for_status()

                with open(save_path, "wb") as f:
                    f.write(response.content)

            return TaskResult(
                success=True,
                output={
                    "path": save_path,
                    "size_bytes": len(response.content),
                    "content_type": response.headers.get("content-type"),
                    "status_code": response.status_code,
                },
            )
        except Exception as e:
            return TaskResult(success=False, error=f"Download failed: {str(e)}")


# Export for task registry
HTTP_TASK_TYPES = {
    "http_request": HttpRequestTask,
    "http_download": HttpDownloadTask,
}
