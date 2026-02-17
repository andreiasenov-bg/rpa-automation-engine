"""Rate limiting middleware for API protection.

Provides per-IP and per-user rate limiting using an in-memory sliding window.
Configurable limits per endpoint group. Adds standard rate limit headers.

Production note: Replace in-memory store with Redis for multi-instance deployments.
"""

import time
import threading
from collections import defaultdict
from typing import Optional, Tuple

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

# ─── Rate limit configuration ──────────────────────────────────────────────
# Format: { "group_name": (max_requests, window_seconds) }
RATE_LIMITS = {
    "auth": (10, 60),           # 10 req/min for auth endpoints
    "ai": (20, 60),             # 20 req/min for AI endpoints
    "write": (60, 60),          # 60 req/min for POST/PUT/DELETE
    "read": (200, 60),          # 200 req/min for GET
    "default": (120, 60),       # 120 req/min default
}


def _classify_request(method: str, path: str) -> str:
    """Classify a request into a rate limit group."""
    if "/auth/" in path:
        return "auth"
    if "/ai/" in path:
        return "ai"
    if method in ("POST", "PUT", "PATCH", "DELETE"):
        return "write"
    if method == "GET":
        return "read"
    return "default"


class SlidingWindowCounter:
    """Thread-safe sliding window rate counter.

    Uses a two-bucket sliding window algorithm for accuracy
    without per-request storage overhead.
    """

    def __init__(self):
        self._lock = threading.Lock()
        # Key: (identifier, group) -> (current_count, prev_count, current_window_start)
        self._windows: dict[Tuple[str, str], Tuple[int, int, float]] = {}
        self._max_keys = 50_000  # Bounded memory

    def check_and_increment(
        self, key: str, group: str, max_requests: int, window_seconds: int
    ) -> Tuple[bool, int, int, float]:
        """Check if request is allowed and increment counter.

        Returns:
            (allowed, current_count, limit, retry_after_seconds)
        """
        now = time.monotonic()
        bucket_key = (key, group)

        with self._lock:
            entry = self._windows.get(bucket_key)

            if entry is None:
                # First request
                self._windows[bucket_key] = (1, 0, now)
                self._maybe_cleanup()
                return (True, 1, max_requests, 0)

            current_count, prev_count, window_start = entry
            elapsed = now - window_start

            if elapsed >= window_seconds:
                # New window
                if elapsed >= window_seconds * 2:
                    # Completely new — prev window expired too
                    self._windows[bucket_key] = (1, 0, now)
                else:
                    # Roll over: current becomes prev
                    self._windows[bucket_key] = (1, current_count, now)
                return (True, 1, max_requests, 0)

            # Weighted count: prev * remaining_fraction + current
            weight = 1 - (elapsed / window_seconds)
            estimated = prev_count * weight + current_count

            if estimated >= max_requests:
                retry_after = window_seconds - elapsed
                return (False, int(estimated), max_requests, retry_after)

            # Allowed — increment
            self._windows[bucket_key] = (current_count + 1, prev_count, window_start)
            return (True, int(estimated) + 1, max_requests, 0)

    def _maybe_cleanup(self):
        """Evict oldest entries if memory bound exceeded."""
        if len(self._windows) > self._max_keys:
            # Remove oldest 20%
            to_remove = int(self._max_keys * 0.2)
            sorted_keys = sorted(
                self._windows.keys(),
                key=lambda k: self._windows[k][2],
            )
            for k in sorted_keys[:to_remove]:
                del self._windows[k]


# Singleton counter
_counter = SlidingWindowCounter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for rate limiting.

    Applies per-IP rate limits with standard headers:
    - X-RateLimit-Limit
    - X-RateLimit-Remaining
    - X-RateLimit-Reset
    - Retry-After (on 429)

    Skips rate limiting for:
    - Health check endpoints
    - Prometheus metrics endpoint
    - WebSocket connections
    """

    SKIP_PATHS = {"/api/health", "/api/v1/health", "/health", "/metrics", "/ws"}

    async def dispatch(self, request: Request, call_next):
        # Skip for non-rate-limited paths
        if request.url.path in self.SKIP_PATHS or request.url.path.startswith("/ws"):
            return await call_next(request)

        # Identify caller: prefer user ID from auth, fall back to IP
        identifier = self._get_identifier(request)
        group = _classify_request(request.method, request.url.path)
        max_req, window = RATE_LIMITS.get(group, RATE_LIMITS["default"])

        allowed, current, limit, retry_after = _counter.check_and_increment(
            identifier, group, max_req, window
        )

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded",
                    "retry_after": round(retry_after, 1),
                },
                headers={
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(retry_after)),
                    "Retry-After": str(int(retry_after)),
                },
            )

        response = await call_next(request)

        # Add rate limit headers
        remaining = max(0, limit - current)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(window)

        return response

    def _get_identifier(self, request: Request) -> str:
        """Get a unique identifier for the requestor.

        Uses direct client IP as primary source (not trusting X-Forwarded-For).
        Only falls back to X-Forwarded-For if direct client is unavailable.
        """
        # Try to get user ID from request state (set by auth middleware)
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            return f"user:{user_id}"

        # Use direct client IP (most reliable, not spoofable)
        if request.client and request.client.host:
            return f"ip:{request.client.host}"

        # Only as fallback, use first IP from X-Forwarded-For if available
        # This is less reliable but better than nothing
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return f"ip:{forwarded.split(',')[0].strip()}"

        return f"ip:unknown"
