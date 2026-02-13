"""Prometheus metrics for the RPA Automation Engine.

Provides:
- HTTP request metrics (count, duration, status breakdown)
- Execution metrics (total, running, completed, failed)
- WebSocket connection gauge
- System info (uptime, version)

Exposes a plain-text /metrics endpoint compatible with any Prometheus scraper.
No external dependency required — generates exposition format directly.
"""

import time
import threading
from collections import defaultdict
from typing import Optional

from fastapi import APIRouter, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# ---------------------------------------------------------------------------
# In-process metric store (lightweight, no prometheus_client dependency)
# ---------------------------------------------------------------------------

_lock = threading.Lock()

_counters: dict[str, float] = defaultdict(float)
_gauges: dict[str, float] = defaultdict(float)
_histograms: dict[str, list[float]] = defaultdict(list)
_start_time = time.time()


def inc(name: str, value: float = 1.0, labels: Optional[dict] = None) -> None:
    key = _label_key(name, labels)
    with _lock:
        _counters[key] += value


def gauge_set(name: str, value: float, labels: Optional[dict] = None) -> None:
    key = _label_key(name, labels)
    with _lock:
        _gauges[key] = value


def gauge_inc(name: str, value: float = 1.0, labels: Optional[dict] = None) -> None:
    key = _label_key(name, labels)
    with _lock:
        _gauges[key] += value


def observe(name: str, value: float, labels: Optional[dict] = None) -> None:
    key = _label_key(name, labels)
    with _lock:
        _histograms[key].append(value)
        # Keep only last 10k observations to bound memory
        if len(_histograms[key]) > 10_000:
            _histograms[key] = _histograms[key][-5_000:]


def _label_key(name: str, labels: Optional[dict] = None) -> str:
    if not labels:
        return name
    label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
    return f"{name}{{{label_str}}}"


# ---------------------------------------------------------------------------
# Exposition format generator
# ---------------------------------------------------------------------------

def generate_metrics() -> str:
    """Generate Prometheus exposition format text."""
    lines: list[str] = []

    lines.append("# HELP rpa_uptime_seconds Time since application start.")
    lines.append("# TYPE rpa_uptime_seconds gauge")
    lines.append(f"rpa_uptime_seconds {time.time() - _start_time:.1f}")
    lines.append("")

    with _lock:
        # Counters
        if _counters:
            seen_names: set[str] = set()
            for key, val in sorted(_counters.items()):
                base_name = key.split("{")[0]
                if base_name not in seen_names:
                    lines.append(f"# TYPE {base_name} counter")
                    seen_names.add(base_name)
                lines.append(f"{key} {val}")
            lines.append("")

        # Gauges
        if _gauges:
            seen_names = set()
            for key, val in sorted(_gauges.items()):
                base_name = key.split("{")[0]
                if base_name not in seen_names:
                    lines.append(f"# TYPE {base_name} gauge")
                    seen_names.add(base_name)
                lines.append(f"{key} {val}")
            lines.append("")

        # Histograms (simplified — sum and count only)
        if _histograms:
            seen_names = set()
            for key, values in sorted(_histograms.items()):
                base_name = key.split("{")[0]
                if base_name not in seen_names:
                    lines.append(f"# TYPE {base_name} summary")
                    seen_names.add(base_name)
                if values:
                    lines.append(f"{key}_count {len(values)}")
                    lines.append(f"{key}_sum {sum(values):.4f}")
            lines.append("")

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Metrics middleware
# ---------------------------------------------------------------------------

class MetricsMiddleware(BaseHTTPMiddleware):
    """Track HTTP request count and duration per method/path/status."""

    async def dispatch(self, request: Request, call_next):
        # Skip metrics endpoint itself to avoid recursion
        if request.url.path == "/metrics":
            return await call_next(request)

        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start

        # Normalize path: replace UUIDs with {id}
        path = request.url.path
        parts = path.split("/")
        normalized_parts = []
        for part in parts:
            if len(part) == 36 and part.count("-") == 4:
                normalized_parts.append("{id}")
            else:
                normalized_parts.append(part)
        normalized_path = "/".join(normalized_parts)

        labels = {
            "method": request.method,
            "path": normalized_path,
            "status": str(response.status_code),
        }

        inc("rpa_http_requests_total", labels=labels)
        observe("rpa_http_request_duration_seconds", duration, labels=labels)

        return response


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

metrics_router = APIRouter()


@metrics_router.get("/metrics")
async def prometheus_metrics():
    """Prometheus-compatible metrics endpoint."""
    return Response(
        content=generate_metrics(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
