"""API Key authentication for external integrations.

Supports two authentication methods:
1. Header-based: X-API-Key: <key>
2. Query parameter: ?api_key=<key>

API keys are stored as SHA-256 hashes in the database.
Each key is scoped to an organization and can have specific permissions.
"""

import hashlib
import secrets
from datetime import datetime, timezone
from typing import Optional

from fastapi import Request, HTTPException, Security
from fastapi.security import APIKeyHeader, APIKeyQuery

# Security schemes
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
api_key_query = APIKeyQuery(name="api_key", auto_error=False)


def generate_api_key(prefix: str = "rpa") -> tuple[str, str]:
    """Generate a new API key and its hash.

    Returns:
        (raw_key, key_hash) - raw_key is shown once to user, key_hash stored in DB
    """
    raw_token = secrets.token_urlsafe(32)
    raw_key = f"{prefix}_{raw_token}"
    key_hash = hash_api_key(raw_key)
    return raw_key, key_hash


def hash_api_key(key: str) -> str:
    """Hash an API key for storage."""
    return hashlib.sha256(key.encode()).hexdigest()


def mask_api_key(key: str) -> str:
    """Mask an API key for display.

    Example: rpa_abc...xyz
    """
    if len(key) <= 10:
        return key[:4] + "..." + key[-3:]
    return key[:7] + "..." + key[-4:]


class APIKeyInfo:
    """Resolved API key information."""

    def __init__(
        self,
        key_id: str,
        organization_id: str,
        name: str,
        permissions: list[str],
        rate_limit_group: str = "default",
    ):
        self.key_id = key_id
        self.organization_id = organization_id
        self.name = name
        self.permissions = permissions
        self.rate_limit_group = rate_limit_group

    def has_permission(self, required: str) -> bool:
        """Check if this key has the required permission."""
        for perm in self.permissions:
            if perm == required:
                return True
            # Wildcard support: "workflows.*" matches "workflows.read"
            if perm.endswith(".*"):
                prefix = perm[:-2]
                if required.startswith(prefix + "."):
                    return True
            # Full wildcard
            if perm == "*":
                return True
        return False


async def resolve_api_key(
    header_key: Optional[str] = Security(api_key_header),
    query_key: Optional[str] = Security(api_key_query),
) -> Optional[APIKeyInfo]:
    """Extract and validate API key from request.

    Checks header first, then query parameter.
    Returns None if no key provided (falls through to JWT auth).
    Raises 401 if key is invalid.
    """
    raw_key = header_key or query_key

    if not raw_key:
        return None

    key_hash = hash_api_key(raw_key)

    # In production, this queries the database
    # For now, return None to fall through to JWT auth
    # TODO: Implement DB lookup when api_keys table is added
    #
    # Example DB query:
    # async with get_session() as session:
    #     result = await session.execute(
    #         select(APIKeyModel)
    #         .where(APIKeyModel.key_hash == key_hash)
    #         .where(APIKeyModel.is_active == True)
    #         .where(or_(APIKeyModel.expires_at.is_(None), APIKeyModel.expires_at > func.now()))
    #     )
    #     db_key = result.scalar_one_or_none()
    #     if db_key:
    #         await session.execute(
    #             update(APIKeyModel)
    #             .where(APIKeyModel.id == db_key.id)
    #             .values(last_used_at=func.now(), usage_count=APIKeyModel.usage_count + 1)
    #         )
    #         return APIKeyInfo(
    #             key_id=str(db_key.id),
    #             organization_id=str(db_key.organization_id),
    #             name=db_key.name,
    #             permissions=db_key.permissions or [],
    #         )

    return None


def require_api_permission(permission: str):
    """Dependency that checks API key has required permission.

    Usage:
        @router.get("/data", dependencies=[Depends(require_api_permission("data.read"))])
        async def get_data(): ...
    """

    async def _check(
        api_key: Optional[APIKeyInfo] = Security(resolve_api_key),
    ):
        if api_key is None:
            # No API key — fall through to regular JWT auth
            return None
        if not api_key.has_permission(permission):
            raise HTTPException(
                status_code=403,
                detail=f"API key lacks required permission: {permission}",
            )
        return api_key

    return _check
