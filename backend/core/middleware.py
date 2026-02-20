"""FastAPI middleware for request tracking, timing, and error handling.

Adds:
- X-Request-ID header (generated if not provided)
- X-Process-Time header (request duration)
- Structured logging per request
- Global exception handler
"""

import logging
import time
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings

logger = logging.getLogger(__name__)


class RequestTrackingMiddleware(BaseHTTPMiddleware):
    """Add request ID and timing to every request/response."""

    async def dispatch(self, request: Request, call_next):
        # Generate or extract request ID
        request_id = request.headers.get("X-Request-ID", str(uuid4()))

        # Attach to request state for downstream access
        request.state.request_id = request_id

        # Start timing
        start_time = time.monotonic()

        # Process request
        try:
            response = await call_next(request)
        except Exception as exc:
            # Catch unhandled exceptions
            duration_ms = (time.monotonic() - start_time) * 1000
            settings = get_settings()
            logger.error(
                "Unhandled exception",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": round(duration_ms, 2),
                    "error": str(exc),
                },
                exc_info=True,
            )
            # In production, don't expose error details to client
            if settings.is_production:
                error_detail = "Internal server error"
            else:
                error_detail = str(exc) or "Internal server error"

            return JSONResponse(
                status_code=500,
                content={
                    "detail": error_detail,
                    "request_id": request_id,
                },
                headers={"X-Request-ID": request_id},
            )

        # Calculate duration
        duration_ms = (time.monotonic() - start_time) * 1000

        # Add headers to response
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = f"{duration_ms:.2f}ms"

        # Log request
        log_level = logging.WARNING if response.status_code >= 400 else logging.INFO
        if request.url.path not in ("/api/health", "/api/v1/health", "/health"):
            logger.log(
                log_level,
                f"{request.method} {request.url.path} -> {response.status_code} ({duration_ms:.0f}ms)",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": round(duration_ms, 2),
                    "client_ip": request.client.host if request.client else None,
                },
            )

        return response


def setup_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers."""

    from core.exceptions import (
        NotFoundError,
        UnauthorizedError,
        ForbiddenError,
        ValidationError,
        ConflictError,
    )

    @app.exception_handler(NotFoundError)
    async def not_found_handler(request: Request, exc: NotFoundError):
        return JSONResponse(
            status_code=404,
            content={"detail": str(exc), "request_id": getattr(request.state, "request_id", None)},
        )

    @app.exception_handler(UnauthorizedError)
    async def unauthorized_handler(request: Request, exc: UnauthorizedError):
        return JSONResponse(
            status_code=401,
            content={"detail": str(exc), "request_id": getattr(request.state, "request_id", None)},
        )

    @app.exception_handler(ForbiddenError)
    async def forbidden_handler(request: Request, exc: ForbiddenError):
        return JSONResponse(
            status_code=403,
            content={"detail": str(exc), "request_id": getattr(request.state, "request_id", None)},
        )

    @app.exception_handler(ValidationError)
    async def validation_handler(request: Request, exc: ValidationError):
        return JSONResponse(
            status_code=422,
            content={"detail": str(exc), "request_id": getattr(request.state, "request_id", None)},
        )

    @app.exception_handler(ConflictError)
    async def conflict_handler(request: Request, exc: ConflictError):
        return JSONResponse(
            status_code=409,
            content={"detail": str(exc), "request_id": getattr(request.state, "request_id", None)},
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        return JSONResponse(
            status_code=400,
            content={"detail": str(exc), "request_id": getattr(request.state, "request_id", None)},
        )
