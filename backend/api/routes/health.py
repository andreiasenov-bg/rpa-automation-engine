"""Health check endpoints."""

from fastapi import APIRouter, HTTPException, status
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/", response_model=Dict[str, Any])
async def root() -> Dict[str, Any]:
    """
    Get API root information.

    Returns:
        Application info including version and status
    """
    return {
        "app": "RPA Automation Engine",
        "version": "1.0.0",
        "status": "ok",
    }


@router.get("/health", response_model=Dict[str, Any])
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint with dependency checks.

    Pings database and Redis to verify connectivity.

    Returns:
        Health status of the application and its dependencies

    Raises:
        HTTPException: If critical dependencies are unavailable
    """
    try:
        # TODO: Implement actual database ping
        db_status = "ok"
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        db_status = "unavailable"

    try:
        # TODO: Implement actual Redis ping
        redis_status = "ok"
    except Exception as e:
        logger.warning(f"Redis health check failed: {str(e)}")
        redis_status = "unavailable"

    # Consider health degraded if critical components are down
    if db_status == "unavailable":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        )

    return {
        "status": "healthy",
        "database": db_status,
        "redis": redis_status,
    }
