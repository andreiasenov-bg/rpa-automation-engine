"""API Key management endpoints.

Create, list, revoke API keys for programmatic access.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_active_user, get_db
from core.api_keys import generate_api_key, mask_api_key
from db.models.api_key import APIKey

router = APIRouter()


class CreateAPIKeyRequest(BaseModel):
    name: str
    permissions: list[str] = ["*"]
    expires_in_days: Optional[int] = None


class APIKeyResponse(BaseModel):
    id: str
    name: str
    prefix: str
    permissions: list[str]
    is_active: bool
    usage_count: int
    last_used_at: Optional[str] = None
    created_at: str


@router.get("/", summary="List API keys")
async def list_api_keys(
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List all API keys for the current organization."""
    result = await db.execute(
        select(APIKey)
        .where(
            APIKey.organization_id == current_user.organization_id,
            APIKey.is_deleted == False,
        )
        .order_by(APIKey.created_at.desc())
    )
    keys = result.scalars().all()

    return [
        {
            "id": k.id,
            "name": k.name,
            "prefix": k.prefix,
            "permissions": k.permissions or [],
            "is_active": k.is_active,
            "usage_count": k.usage_count,
            "last_used_at": str(k.last_used_at) if k.last_used_at else None,
            "created_at": str(k.created_at),
        }
        for k in keys
    ]


@router.post("/", status_code=status.HTTP_201_CREATED, summary="Create API key")
async def create_api_key(
    request: CreateAPIKeyRequest,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new API key. The raw key is shown ONCE — save it immediately."""
    from datetime import datetime, timedelta, timezone

    raw_key, key_hash = generate_api_key()

    expires_at = None
    if request.expires_in_days:
        expires_at = datetime.now(timezone.utc) + timedelta(days=request.expires_in_days)

    api_key = APIKey(
        organization_id=current_user.organization_id,
        name=request.name,
        key_hash=key_hash,
        prefix=raw_key[:11],
        permissions=request.permissions,
        expires_at=expires_at,
        created_by_id=current_user.id,
    )
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)

    return {
        "id": api_key.id,
        "name": api_key.name,
        "raw_key": raw_key,  # Shown ONCE
        "prefix": api_key.prefix,
        "permissions": api_key.permissions,
        "expires_at": str(expires_at) if expires_at else None,
        "message": "Save this key now — it will not be shown again.",
    }


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Revoke API key")
async def revoke_api_key(
    key_id: str,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke (soft-delete) an API key."""
    result = await db.execute(
        select(APIKey).where(
            APIKey.id == key_id,
            APIKey.organization_id == current_user.organization_id,
        )
    )
    api_key = result.scalar_one_or_none()

    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    api_key.is_active = False
    api_key.soft_delete()
    await db.commit()
