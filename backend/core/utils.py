"""
Utility functions for the RPA automation engine.

Includes:
- Slug generation
- Agent token generation
- Pagination helpers
- UTC datetime helpers
"""

import re
import secrets
from datetime import datetime, timezone
from typing import TypeVar, Generic, List, Any
from urllib.parse import quote

from pydantic import BaseModel

T = TypeVar("T")


def generate_slug(name: str) -> str:
    """
    Generate a URL-friendly slug from a string.

    Converts to lowercase, replaces spaces with hyphens, removes special characters.

    Args:
        name: String to convert to slug

    Returns:
        URL-friendly slug
    """
    # Convert to lowercase
    slug = name.lower()

    # Replace spaces with hyphens
    slug = re.sub(r"\s+", "-", slug)

    # Remove special characters, keep only alphanumeric and hyphens
    slug = re.sub(r"[^a-z0-9\-]", "", slug)

    # Remove multiple consecutive hyphens
    slug = re.sub(r"-+", "-", slug)

    # Remove leading/trailing hyphens
    slug = slug.strip("-")

    return slug


def generate_agent_token() -> str:
    """
    Generate a secure random token for agent authentication.

    Returns a 32-byte random hex string.

    Returns:
        32-character hex token
    """
    return secrets.token_hex(32)


def utc_now() -> datetime:
    """
    Get the current UTC datetime.

    Returns:
        Current datetime in UTC timezone
    """
    return datetime.now(timezone.utc)


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Generic paginated response wrapper.

    Args:
        items: List of items
        total: Total number of items
        page: Current page number
        per_page: Items per page
    """

    items: List[T]
    total: int
    page: int
    per_page: int

    @property
    def total_pages(self) -> int:
        """Calculate total number of pages."""
        return (self.total + self.per_page - 1) // self.per_page

    @property
    def has_next(self) -> bool:
        """Check if there's a next page."""
        return self.page < self.total_pages

    @property
    def has_prev(self) -> bool:
        """Check if there's a previous page."""
        return self.page > 1


def paginate(
    items: List[T],
    total: int,
    page: int = 1,
    per_page: int = 20,
) -> dict:
    """
    Helper to create paginated response.

    Args:
        items: List of items for current page
        total: Total number of items across all pages
        page: Current page number (1-indexed)
        per_page: Number of items per page

    Returns:
        Dictionary with pagination metadata
    """
    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page,
        "has_next": page < ((total + per_page - 1) // per_page),
        "has_prev": page > 1,
    }


def calculate_offset(page: int = 1, per_page: int = 20) -> int:
    """
    Calculate database offset from page and per_page values.

    Args:
        page: Page number (1-indexed)
        per_page: Items per page

    Returns:
        Offset for database queries
    """
    return (page - 1) * per_page
