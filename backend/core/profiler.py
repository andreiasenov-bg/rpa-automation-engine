"""Request profiling middleware — CPU time, memory, and duration tracking.

Stores per-request metrics in Redis for the Profiler dashboard.
Enable/disable via PROFILER_ENABLED in settings.
"""

import json
import logging
import time
import tracemalloc
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# In-memory fallback when Redis is unavailable
_inmemory_requests: list[dict[str, Any]] = []
_inmemory_endpoints: dict[str, dict[str, Any]] = {}
_profiler_enabled: bool = True
MAX_REQUESTS = 1000


def _get_redis():
    """Get Redis connection (lazy import to avoid circular deps)."""
    try:
        import redis
        from app.config import get_settings
        settings = get_settings()
        r = redis.Redis.from_url(
            settings.REDIS_URL if hasattr(settings, "REDIS_URL") else "redis://redis:6379/0",
            decode_responses=True,
        )
        r.ping()
        return r
    except Exception:
        return None


def _store_request(data: dict[str, Any]):
    """Store a single request's profiling data."""
    r = _get_redis()
    if r:
        try:
            key = f"profiler:req:{data['id']}"
            r.setex(key, 3600, json.dumps(data))  # TTL 1h
            r.lpush("profiler:requests", data["id"])
            r.ltrim("profiler:requests", 0, MAX_REQUESTS - 1)
            return
        except Exception as e:
            logger.debug(f"Redis store failed, using memory: {e}")

    _inmemory_requests.insert(0, data)
    if len(_inmemory_requests) > MAX_REQUESTS:
        _inmemory_requests.pop()


def _update_endpoint_stats(endpoint: str, method: str, duration_ms: float,
                           memory_kb: float, cpu_ms: float, status_code: int):
    """Update aggregate stats for an endpoint."""
    ep_key = f"{method} {endpoint}"
    r = _get_redis()

    if r:
        try:
            hash_key = f"profiler:ep:{ep_key}"
            pipe = r.pipeline()
            pipe.hincrby(hash_key, "count", 1)
            pipe.hincrbyfloat(hash_key, "total_duration", duration_ms)
            pipe.hincrbyfloat(hash_key, "total_memory", memory_kb)
            pipe.hincrbyfloat(hash_key, "total_cpu", cpu_ms)

            current = r.hgetall(hash_key)
            max_dur = float(current.get("max_duration", 0))
            max_mem = float(current.get("max_memory", 0))
            if duration_ms > max_dur:
                pipe.hset(hash_key, "max_duration", str(duration_ms))
            if memory_kb > max_mem:
                pipe.hset(hash_key, "max_memory", str(memory_kb))
            if status_code >= 400:
                pipe.hincrby(hash_key, "error_count", 1)

            pipe.hset(hash_key, "method", method)
            pipe.hset(hash_key, "endpoint", endpoint)
            pipe.hset(hash_key, "last_seen", datetime.now(timezone.utc).isoformat())
            pipe.expire(hash_key, 86400)  # TTL 24h
            pipe.execute()
            return
        except Exception as e:
            logger.debug(f"Redis endpoint stats failed: {e}")

    # In-memory fallback
    stats = _inmemory_endpoints.setdefault(ep_key, {
        "method": method, "endpoint": endpoint, "count": 0,
        "total_duration": 0, "total_memory": 0, "total_cpu": 0,
        "max_duration": 0, "max_memory": 0, "error_count": 0,
    })
    stats["count"] += 1
    stats["total_duration"] += duration_ms
    stats["total_memory"] += memory_kb
    stats["total_cpu"] += cpu_ms
    stats["max_duration"] = max(stats["max_duration"], duration_ms)
    stats["max_memory"] = max(stats["max_memory"], memory_kb)
    if status_code >= 400:
        stats["error_count"] += 1
    stats["last_seen"] = datetime.now(timezone.utc).isoformat()


def get_profiler_enabled() -> bool:
    global _profiler_enabled
    return _profiler_enabled


def set_profiler_enabled(enabled: bool):
    global _profiler_enabled
    _profiler_enabled = enabled


def get_endpoint_stats() -> list[dict[str, Any]]:
    """Return aggregate stats for all endpoints."""
    r = _get_redis()
    results = []

    if r:
        try:
            keys = r.keys("profiler:ep:*")
            for k in keys:
                data = r.hgetall(k)
                count = int(data.get("count", 0))
                if count == 0:
                    continue
                results.append({
                    "endpoint": data.get("endpoint", ""),
                    "method": data.get("method", ""),
                    "count": count,
                    "avg_duration": round(float(data.get("total_duration", 0)) / count, 2),
                    "max_duration": round(float(data.get("max_duration", 0)), 2),
                    "avg_memory": round(float(data.get("total_memory", 0)) / count, 2),
                    "max_memory": round(float(data.get("max_memory", 0)), 2),
                    "avg_cpu": round(float(data.get("total_cpu", 0)) / count, 2),
                    "error_count": int(data.get("error_count", 0)),
                    "error_rate": round(int(data.get("error_count", 0)) / count * 100, 1),
                    "last_seen": data.get("last_seen", ""),
                })
            return sorted(results, key=lambda x: x["avg_duration"], reverse=True)
        except Exception:
            pass

    # In-memory fallback
    for ep_key, stats in _inmemory_endpoints.items():
        count = stats["count"]
        if count == 0:
            continue
        results.append({
            "endpoint": stats["endpoint"],
            "method": stats["method"],
            "count": count,
            "avg_duration": round(stats["total_duration"] / count, 2),
            "max_duration": round(stats["max_duration"], 2),
            "avg_memory": round(stats["total_memory"] / count, 2),
            "max_memory": round(stats["max_memory"], 2),
            "avg_cpu": round(stats["total_cpu"] / count, 2),
            "error_count": stats["error_count"],
            "error_rate": round(stats["error_count"] / count * 100, 1),
            "last_seen": stats.get("last_seen", ""),
        })
    return sorted(results, key=lambda x: x["avg_duration"], reverse=True)


def get_recent_requests(limit: int = 50) -> list[dict[str, Any]]:
    """Return the most recent profiled requests."""
    r = _get_redis()
    results = []

    if r:
        try:
            req_ids = r.lrange("profiler:requests", 0, limit - 1)
            for rid in req_ids:
                raw = r.get(f"profiler:req:{rid}")
                if raw:
                    results.append(json.loads(raw))
            return results
        except Exception:
            pass

    return _inmemory_requests[:limit]


def reset_profiler_data():
    """Clear all profiling data."""
    global _inmemory_requests, _inmemory_endpoints
    r = _get_redis()

    if r:
        try:
            keys = r.keys("profiler:*")
            if keys:
                r.delete(*keys)
        except Exception:
            pass

    _inmemory_requests = []
    _inmemory_endpoints = {}


class ProfilerMiddleware(BaseHTTPMiddleware):
    """Middleware that profiles each request for CPU time, memory, and duration."""

    SKIP_PREFIXES = ("/docs", "/openapi.json", "/redoc", "/favicon")

    async def dispatch(self, request: Request, call_next):
        if not _profiler_enabled:
            return await call_next(request)

        path = request.url.path
        if any(path.startswith(p) for p in self.SKIP_PREFIXES):
            return await call_next(request)

        method = request.method
        request_id = getattr(request.state, "request_id", str(uuid4()))

        # Start measurements
        if not tracemalloc.is_tracing():
            tracemalloc.start()

        snapshot_before = tracemalloc.take_snapshot()
        cpu_start = time.process_time()
        wall_start = time.monotonic()

        # Process request
        status_code = 500
        try:
            response: Response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception as exc:
            status_code = 500
            raise
        finally:
            wall_end = time.monotonic()
            cpu_end = time.process_time()

            duration_ms = round((wall_end - wall_start) * 1000, 2)
            cpu_ms = round((cpu_end - cpu_start) * 1000, 2)

            # Memory delta
            memory_kb = 0.0
            try:
                snapshot_after = tracemalloc.take_snapshot()
                stats = snapshot_after.compare_to(snapshot_before, "lineno")
                memory_kb = round(sum(s.size_diff for s in stats[:50]) / 1024, 2)
            except Exception:
                pass

            data = {
                "id": request_id,
                "method": method,
                "path": path,
                "status_code": status_code,
                "duration_ms": duration_ms,
                "cpu_ms": cpu_ms,
                "memory_kb": abs(memory_kb),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            try:
                _store_request(data)
                _update_endpoint_stats(path, method, duration_ms, abs(memory_kb), cpu_ms, status_code)
            except Exception as e:
                logger.debug(f"Profiler store error: {e}")
