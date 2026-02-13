"""User management endpoints — list, get, update, deactivate."""

from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional
import logging

from core.security import TokenPayload
from api.schemas.auth import UserResponse
from api.schemas.common import PaginationParams
from app.dependencies import get_db, get_current_active_user
from services.user_service import UserService
from core.utils import calculate_offset

logger = logging.getLogger(__name__)

router = APIRouter(tags=["users"])


class UserUpdateRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: Optional[bool] = None


def _user_to_response(user) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        org_id=user.organization_id,
        is_active=user.is_active,
        roles=[r.name for r in user.roles] if user.roles else [],
        created_at=user.created_at,
    )


@router.get("/", response_model=dict)
async def list_users(
    pagination: PaginationParams = Depends(),
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List users in the current organization (paginated)."""
    svc = UserService(db)
    offset = calculate_offset(pagination.page, pagination.per_page)

    users, total = await svc.list_by_org(
        organization_id=current_user.org_id,
        offset=offset,
        limit=pagination.per_page,
    )

    return {
        "users": [_user_to_response(u) for u in users],
        "total": total,
        "page": pagination.page,
        "per_page": pagination.per_page,
    }


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Get user details by ID (same org only)."""
    svc = UserService(db)
    user = await svc.get_by_id_and_org(user_id, current_user.org_id)

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return _user_to_response(user)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    request: UserUpdateRequest,
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Update user profile fields."""
    svc = UserService(db)
    data = request.model_dump(exclude_unset=True)

    user = await svc.update_profile(user_id, current_user.org_id, data)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return _user_to_response(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_user(
    user_id: str,
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Deactivate (soft-delete) a user."""
    if user_id == current_user.sub:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account",
        )

    svc = UserService(db)
    deleted = await svc.deactivate(user_id, current_user.org_id)

    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
