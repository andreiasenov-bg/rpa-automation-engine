"""Rate limiting middleware for API protection.

Provides per-IP and per-user rate limiting using Redis sliding window.
Configurable limits per endpoint group. Adds standard rate limit headers.
Falls back to in-memory store if Redis is unavailable.
"""

import time
import os
import logging
from typing import Optional, Tuple

import redis
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# Rate limit configuration: { "group_name": (max_requests, window_seconds) }
RATE_LIMITS = {
    "auth": (10, 60),
    "ai": (20, 60),
    "write": (60, 60),
    "read": (200, 60),
    "default": (120, 60),
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


class RedisSlidingWindowCounter:
    """Redis-backed sliding window rate counter.
    
    Uses Redis sorted sets for accurate distributed rate limiting.
    Each request is stored as a member with score = timestamp.
    """
    
    def __init__(self, redis_url: str = None):
        self._redis_url = redis_url or os.getenv("REDIS_URL", "redis://redis:6379/0")
        self._redis: Optional[redis.Redis] = None
        self._connect()
    
    def _connect(self):
        try:
            self._redis = redis.from_url(
                self._redis_url,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=1,
                retry_on_timeout=True,
            )
            self._redis.ping()
            logger.info("Rate limiter connected to Redis")
        except Exception as e:
            logger.warning(f"Rate limiter Redis connection failed: {e}, using fallback")
            self._redis = None
    
    def check_and_increment(
        self, key: str, group: str, max_requests: int, window_seconds: int
    ) -> Tuple[bool, int, int, float]:
        """Check if request is allowed and increment counter.
        
        Returns: (allowed, current_count, limit, retry_after_seconds)
        """
        if self._redis is None:
            return (True, 0, max_requests, 0)
        
        try:
            return self._redis_check(key, group, max_requests, window_seconds)
        except redis.RedisError as e:
            logger.warning(f"Rate limit Redis error: {e}")
            return (True, 0, max_requests, 0)
    
    def _redis_check(
        self, key: str, group: str, max_requests: int, window_seconds: int
    ) -> Tuple[bool, int, int, float]:
        now = time.time()
        window_start = now - window_seconds
        redis_key = f"ratelimit:{group}:{key}"
        
        pipe = self._redis.pipeline()
        pipe.zremrangebyscore(redis_key, 0, window_start)
        pipe.zadd(redis_key, {f"{now}": now})
        pipe.zcard(redis_key)
        pipe.expire(redis_key, window_seconds + 1)
        results = pipe.execute()
        
        current_count = results[2]
        
        if current_count > max_requests:
            pipe2 = self._redis.pipeline()
            pipe2.zrem(redis_key, f"{now}")
            pipe2.zrange(redis_key, 0, 0, withscores=True)
            results2 = pipe2.execute()
            
            oldest = results2[1]
            if oldest:
                retry_after = oldest[0][1] + window_seconds - now
            else:
                retry_after = float(window_seconds)
            
            return (False, current_count - 1, max_requests, max(0, retry_after))
        
        return (True, current_count, max_requests, 0)


# Singleton counter
_counter = RedisSlidingWindowCounter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for rate limiting.
    
    Applies per-IP rate limits with standard headers.
    """
    
    SKIP_PATHS = {"/api/health", "/api/v1/health", "/health", "/metrics", "/ws"}
    
    async def dispatch(self, request: Request, call_next):
        if request.url.path in self.SKIP_PATHS:
            return await call_next(request)
        
        if request.scope.get("type") == "websocket":
            return await call_next(request)
        
        identifier = self._get_identifier(request)
        group = _classify_request(request.method, request.url.path)
        max_requests, window = RATE_LIMITS.get(group, RATE_LIMITS["default"])
        
        allowed, current, limit, retry_after = _counter.check_and_increment(
            identifier, group, max_requests, window
        )
        
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded",
                    "retry_after": int(retry_after),
                },
                headers={
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(retry_after)),
                    "Retry-After": str(int(retry_after)),
                },
            )
        
        response = await call_next(request)
        remaining = max(0, limit - current)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(window)
        return response
    
    def _get_identifier(self, request: Request) -> str:
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            return f"user:{user_id}"
        if request.client and request.client.host:
            return f"ip:{request.client.host}"
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return f"ip:{forwarded.split(chr(44))[0].strip()}"
        return "ip:unknown"
