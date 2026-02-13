"""Health check endpoints.

Provides:
- Basic liveness probe (/health/)
- Deep dependency check (/health/health)
- Detailed system status (/health/status)
"""

import platform
import sys
import time
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, status
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["health"])

_start_time = time.monotonic()
_start_datetime = datetime.now(timezone.utc).isoformat()


@router.get("/", response_model=dict[str, Any])
async def root() -> dict[str, Any]:
    """
    Get API root information and version.
    Used as a simple liveness probe.
    """
    return {
        "app": "RPA Automation Engine",
        "version": "1.0.0",
        "status": "ok",
    }


@router.get("/health", response_model=dict[str, Any])
async def health_check() -> dict[str, Any]:
    """
    Health check with dependency verification.
    Pings database and Redis to verify connectivity.
    Returns 503 if critical dependencies are down.
    """
    checks: dict[str, str] = {}

    # Database check
    try:
        from db.session import async_engine
        from sqlalchemy import text

        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        logger.error("Database health check failed: %s", e)
        checks["database"] = "unavailable"

    # Redis check via TCP socket
    try:
        import asyncio
        import socket
        from core.config import settings

        redis_url = settings.REDIS_URL
        # Parse host:port from redis://host:port/db
        parts = redis_url.replace("redis://", "").split("/")[0]
        host_port = parts.split("@")[-1] if "@" in parts else parts
        redis_host, redis_port = host_port.split(":") if ":" in host_port else (host_port, "6379")

        # Async TCP connect with 2s timeout
        loop = asyncio.get_event_loop()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2.0)
        try:
            await loop.run_in_executor(None, sock.connect, (redis_host, int(redis_port)))
            # Send Redis PING command
            await loop.run_in_executor(None, sock.send, b"*1\r\n$4\r\nPING\r\n")
            response = await loop.run_in_executor(None, sock.recv, 64)
            if b"PONG" in response:
                checks["redis"] = "ok"
            else:
                checks["redis"] = "degraded"
        finally:
            sock.close()
    except Exception as e:
        logger.warning("Redis health check failed: %s", e)
        checks["redis"] = "unavailable"

    overall = "healthy"
    status_code = 200

    if checks["database"] == "unavailable":
        overall = "unhealthy"
        status_code = 503

    if status_code == 503:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": overall, "checks": checks},
        )

    return {"status": overall, **checks}


@router.get("/status", response_model=dict[str, Any])
async def system_status() -> dict[str, Any]:
    """
    Detailed system status including uptime, versions, and component health.
    Intended for admin dashboards and monitoring.
    """
    import os

    uptime_seconds = time.monotonic() - _start_time
    hours, remainder = divmod(int(uptime_seconds), 3600)
    minutes, seconds = divmod(remainder, 60)

    return {
        "app": "RPA Automation Engine",
        "version": "1.0.0",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "started_at": _start_datetime,
        "uptime": f"{hours}h {minutes}m {seconds}s",
        "uptime_seconds": round(uptime_seconds, 1),
        "python": {
            "version": sys.version,
            "platform": platform.platform(),
        },
        "components": {
            "api": "running",
            "database": "configured",
            "redis": "configured",
            "celery": "configured",
            "websocket": "configured",
        },
    }
