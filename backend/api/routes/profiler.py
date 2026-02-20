"""Profiler API endpoints — view CPU, memory, and timing data per endpoint."""

from typing import Any

from fastapi import APIRouter

from core.profiler import (
    get_endpoint_stats,
    get_profiler_enabled,
    get_recent_requests,
    reset_profiler_data,
    set_profiler_enabled,
)

router = APIRouter(prefix="/profiler", tags=["profiler"])


@router.get("/summary", response_model=dict[str, Any])
async def profiler_summary():
    """Get aggregate profiling stats for all endpoints."""
    endpoints = get_endpoint_stats()
    total_requests = sum(ep["count"] for ep in endpoints)
    total_errors = sum(ep["error_count"] for ep in endpoints)
    avg_duration = (
        round(sum(ep["avg_duration"] * ep["count"] for ep in endpoints) / total_requests, 2)
        if total_requests > 0
        else 0
    )
    max_memory = max((ep["max_memory"] for ep in endpoints), default=0)

    return {
        "enabled": get_profiler_enabled(),
        "total_requests": total_requests,
        "total_errors": total_errors,
        "error_rate": round(total_errors / total_requests * 100, 1) if total_requests > 0 else 0,
        "avg_duration_ms": avg_duration,
        "peak_memory_kb": max_memory,
        "endpoints": endpoints,
    }


@router.get("/requests", response_model=dict[str, Any])
async def profiler_requests(limit: int = 50, offset: int = 0):
    """Get recent profiled requests."""
    requests = get_recent_requests(limit=limit + offset)
    return {
        "requests": requests[offset : offset + limit],
        "total": len(requests),
    }


@router.get("/config", response_model=dict[str, Any])
async def profiler_config():
    """Get current profiler configuration."""
    return {"enabled": get_profiler_enabled()}


@router.post("/config", response_model=dict[str, Any])
async def update_profiler_config(enabled: bool = True):
    """Toggle profiler on/off."""
    set_profiler_enabled(enabled)
    return {"enabled": get_profiler_enabled(), "message": f"Profiler {'enabled' if enabled else 'disabled'}"}


@router.post("/reset", response_model=dict[str, Any])
async def reset_profiler():
    """Clear all profiling data."""
    reset_profiler_data()
    return {"ok": True, "message": "Profiler data cleared"}
