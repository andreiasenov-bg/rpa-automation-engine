"""Common schemas used across the API."""

from pydantic import BaseModel, Field
from typing import Optional


class PaginationParams(BaseModel):
    """Pagination parameters for list endpoints."""

    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    per_page: int = Field(
        default=20, ge=1, le=100, description="Items per page (max 100)"
    )


class MessageResponse(BaseModel):
    """Simple message response."""

    message: str


class ErrorResponse(BaseModel):
    """Standard error response."""

    detail: str = Field(description="Human-readable error message")
    error_code: str = Field(description="Machine-readable error code")
