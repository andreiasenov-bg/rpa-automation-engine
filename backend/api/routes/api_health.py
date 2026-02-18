"""API Health Monitor endpoints — check and track service health over time."""

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api-health", tags=["api-health"])


def _get_redis():
    try:
        import redis
        from app.config import get_settings
        settings = get_settings()
        url = settings.REDIS_URL if hasattr(settings, "REDIS_URL") else "redis://redis:6379/0"
        r = redis.Redis.from_url(url, decode_responses=True)
        r.ping()
        return r
    except Exception:
        return None


async def _check_database() -> dict[str, Any]:
    """Check PostgreSQL connectivity."""
    start = time.monotonic()
    try:
        from db.database import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            from sqlalchemy import text
            await session.execute(text("SELECT 1"))
        duration = round((time.monotonic() - start) * 1000, 2)
        return {"service": "PostgreSQL", "status": "ok", "response_ms": duration, "error": None}
    except Exception as e:
        duration = round((time.monotonic() - start) * 1000, 2)
        return {"service": "PostgreSQL", "status": "down", "response_ms": duration, "error": str(e)}


def _check_redis() -> dict[str, Any]:
    """Check Redis connectivity."""
    start = time.monotonic()
    try:
        r = _get_redis()
        if r is None:
            raise ConnectionError("Cannot connect to Redis")
        r.ping()
        info = r.info("memory")
        duration = round((time.monotonic() - start) * 1000, 2)
        return {
            "service": "Redis",
            "status": "ok",
            "response_ms": duration,
            "error": None,
            "details": {
                "used_memory_human": info.get("used_memory_human", "N/A"),
                "connected_clients": info.get("connected_clients", "N/A"),
            },
        }
    except Exception as e:
        duration = round((time.monotonic() - start) * 1000, 2)
        return {"service": "Redis", "status": "down", "response_ms": duration, "error": str(e)}


def _check_celery() -> dict[str, Any]:
    """Check Celery worker availability."""
    start = time.monotonic()
    try:
        from worker.celery_app import celery_app
        inspector = celery_app.control.inspect(timeout=3)
        ping = inspector.ping()
        duration = round((time.monotonic() - start) * 1000, 2)
        if ping:
            workers = list(ping.keys())
            return {
                "service": "Celery Workers",
                "status": "ok",
                "response_ms": duration,
                "error": None,
                "details": {"workers": workers, "count": len(workers)},
            }
        return {"service": "Celery Workers", "status": "down", "response_ms": duration, "error": "No workers responding"}
    except Exception as e:
        duration = round((time.monotonic() - start) * 1000, 2)
        return {"service": "Celery Workers", "status": "down", "response_ms": duration, "error": str(e)}


def _check_backend() -> dict[str, Any]:
    """Check backend API itself."""
    return {
        "service": "Backend API",
        "status": "ok",
        "response_ms": 0,
        "error": None,
        "details": {"uptime": "running"},
    }


def _store_health_result(results: list[dict[str, Any]]):
    """Store health check results in Redis for history."""
    r = _get_redis()
    if not r:
        return
    try:
        ts = datetime.now(timezone.utc).isoformat()
        entry = json.dumps({"timestamp": ts, "services": results})
        r.lpush("health:history", entry)
        r.ltrim("health:history", 0, 1439)  # Keep 24h at 1/min
        r.expire("health:history", 86400)

        # Store alerts for any failures
        for svc in results:
            if svc["status"] != "ok":
                alert = json.dumps({
                    "timestamp": ts,
                    "service": svc["service"],
                    "status": svc["status"],
                    "error": svc.get("error"),
                    "response_ms": svc.get("response_ms"),
                })
                r.lpush("health:alerts", alert)
                r.ltrim("health:alerts", 0, 99)
                r.expire("health:alerts", 86400)
    except Exception as e:
        logger.debug(f"Health history store failed: {e}")


@router.get("/status", response_model=dict[str, Any])
async def health_status():
    """Get current health status of all services."""
    db_result = await _check_database()
    redis_result = _check_redis()
    celery_result = _check_celery()
    backend_result = _check_backend()

    services = [backend_result, db_result, redis_result, celery_result]

    # Determine overall status
    statuses = [s["status"] for s in services]
    if all(s == "ok" for s in statuses):
        overall = "healthy"
    elif any(s == "down" for s in statuses):
        overall = "degraded"
    else:
        overall = "degraded"

    result = {
        "overall": overall,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": services,
    }

    # Store for history
    _store_health_result(services)

    return result


@router.get("/history", response_model=dict[str, Any])
async def health_history(limit: int = 60):
    """Get health check history (last N entries)."""
    r = _get_redis()
    history = []
    if r:
        try:
            raw_entries = r.lrange("health:history", 0, limit - 1)
            for entry in raw_entries:
                history.append(json.loads(entry))
        except Exception:
            pass

    return {"history": history, "count": len(history)}


@router.get("/alerts", response_model=dict[str, Any])
async def health_alerts(limit: int = 50):
    """Get recent health alerts (failures/degradations)."""
    r = _get_redis()
    alerts = []
    if r:
        try:
            raw = r.lrange("health:alerts", 0, limit - 1)
            for entry in raw:
                alerts.append(json.loads(entry))
        except Exception:
            pass

    return {"alerts": alerts, "count": len(alerts)}


@router.post("/check", response_model=dict[str, Any])
async def trigger_health_check():
    """Manually trigger a health check."""
    return await health_status()
