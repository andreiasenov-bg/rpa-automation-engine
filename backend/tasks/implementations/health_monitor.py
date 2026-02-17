"""Health Monitor periodic task — runs every 60 seconds to check service health."""

import json
import logging
import time
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


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


def check_database_sync() -> dict:
    """Synchronous DB health check for Celery task."""
    start = time.monotonic()
    try:
        from sqlalchemy import create_engine, text
        from app.config import get_settings
        settings = get_settings()
        db_url = str(settings.DATABASE_URL).replace("+asyncpg", "+psycopg2").replace("postgresql+asyncpg", "postgresql")
        if "asyncpg" in db_url:
            db_url = db_url.replace("asyncpg", "psycopg2")
        engine = create_engine(db_url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        duration = round((time.monotonic() - start) * 1000, 2)
        engine.dispose()
        return {"service": "PostgreSQL", "status": "ok", "response_ms": duration, "error": None}
    except Exception as e:
        duration = round((time.monotonic() - start) * 1000, 2)
        return {"service": "PostgreSQL", "status": "down", "response_ms": duration, "error": str(e)}


def check_redis_sync() -> dict:
    """Synchronous Redis health check."""
    start = time.monotonic()
    try:
        r = _get_redis()
        if not r:
            raise ConnectionError("Cannot connect to Redis")
        r.ping()
        duration = round((time.monotonic() - start) * 1000, 2)
        return {"service": "Redis", "status": "ok", "response_ms": duration, "error": None}
    except Exception as e:
        duration = round((time.monotonic() - start) * 1000, 2)
        return {"service": "Redis", "status": "down", "response_ms": duration, "error": str(e)}


def check_celery_sync() -> dict:
    """Check Celery workers."""
    start = time.monotonic()
    try:
        from tasks import celery_app
        inspector = celery_app.control.inspect(timeout=3)
        ping = inspector.ping()
        duration = round((time.monotonic() - start) * 1000, 2)
        if ping:
            return {"service": "Celery Workers", "status": "ok", "response_ms": duration, "error": None}
        return {"service": "Celery Workers", "status": "down", "response_ms": duration, "error": "No workers"}
    except Exception as e:
        duration = round((time.monotonic() - start) * 1000, 2)
        return {"service": "Celery Workers", "status": "down", "response_ms": duration, "error": str(e)}


def run_health_monitor():
    """Main health monitor function — called by Celery periodic task or in-process poller."""
    results = [
        {"service": "Backend API", "status": "ok", "response_ms": 0, "error": None},
        check_database_sync(),
        check_redis_sync(),
        check_celery_sync(),
    ]

    ts = datetime.now(timezone.utc).isoformat()
    r = _get_redis()
    if r:
        try:
            entry = json.dumps({"timestamp": ts, "services": results})
            r.lpush("health:history", entry)
            r.ltrim("health:history", 0, 1439)
            r.expire("health:history", 86400)

            for svc in results:
                if svc["status"] != "ok":
                    alert = json.dumps({
                        "timestamp": ts,
                        "service": svc["service"],
                        "status": svc["status"],
                        "error": svc.get("error"),
                    })
                    r.lpush("health:alerts", alert)
                    r.ltrim("health:alerts", 0, 99)
                    r.expire("health:alerts", 86400)
        except Exception as e:
            logger.warning(f"Health monitor store failed: {e}")

    ok_count = sum(1 for s in results if s["status"] == "ok")
    logger.info(f"Health monitor: {ok_count}/{len(results)} services healthy")
    return results
