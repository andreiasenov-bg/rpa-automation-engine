"""User-role assignment endpoints.

Assign and remove roles to/from users within the same organization.
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, and_, delete, insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dependencies import get_db, get_current_active_user
from core.rbac import require_permission
from core.security import TokenPayload
from db.models.user import User
from db.models.role import Role, user_roles

router = APIRouter(tags=["user-roles"])


# ─── Schemas ─────────────────────────────────────────────────────────────────

class AssignRoleRequest(BaseModel):
    role_id: str = Field(..., description="Role ID to assign")


class BulkAssignRequest(BaseModel):
    user_ids: list[str] = Field(..., min_length=1, max_length=50)
    role_id: str


# ─── Get user's roles ────────────────────────────────────────────────────────

@router.get(
    "/{user_id}/roles",
    dependencies=[Depends(require_permission("admin.*"))],
)
async def get_user_roles(
    user_id: str,
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all roles assigned to a user."""
    user = (await db.execute(
        select(User)
        .options(selectinload(User.roles))
        .where(
            User.id == user_id,
            User.organization_id == current_user.org_id,
            User.is_deleted == False,
        )
    )).scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "user_id": user.id,
        "email": user.email,
        "roles": [
            {
                "id": r.id,
                "name": r.name,
                "slug": r.slug,
                "description": getattr(r, "description", ""),
            }
            for r in (user.roles or [])
            if not getattr(r, "is_deleted", False)
        ],
    }


# ─── Assign role ─────────────────────────────────────────────────────────────

@router.post(
    "/{user_id}/roles",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("admin.*"))],
)
async def assign_role(
    user_id: str,
    body: AssignRoleRequest,
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Assign a role to a user."""
    # Verify user exists in same org
    user = (await db.execute(
        select(User).where(
            User.id == user_id,
            User.organization_id == current_user.org_id,
            User.is_deleted == False,
        )
    )).scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Verify role exists in same org
    role = (await db.execute(
        select(Role).where(
            Role.id == body.role_id,
            Role.organization_id == current_user.org_id,
            Role.is_deleted == False,
        )
    )).scalar_one_or_none()

    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    # Check if already assigned
    existing = (await db.execute(
        select(user_roles).where(
            user_roles.c.user_id == user_id,
            user_roles.c.role_id == body.role_id,
        )
    )).first()

    if existing:
        raise HTTPException(status_code=409, detail="Role already assigned")

    await db.execute(
        insert(user_roles).values(user_id=user_id, role_id=body.role_id)
    )
    await db.flush()

    return {"message": f"Role '{role.name}' assigned to user", "role_id": role.id}


# ─── Remove role ─────────────────────────────────────────────────────────────

@router.delete(
    "/{user_id}/roles/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("admin.*"))],
)
async def remove_role(
    user_id: str,
    role_id: str,
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a role from a user."""
    # Verify user exists
    user = (await db.execute(
        select(User).where(
            User.id == user_id,
            User.organization_id == current_user.org_id,
            User.is_deleted == False,
        )
    )).scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Perform deletion
    result = await db.execute(
        delete(user_roles).where(
            user_roles.c.user_id == user_id,
            user_roles.c.role_id == role_id,
        )
    )

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Role assignment not found")

    await db.flush()


# ─── Bulk assign ──────────────────────────────────────────────────────────────

@router.post(
    "/bulk-assign",
    dependencies=[Depends(require_permission("admin.*"))],
)
async def bulk_assign_role(
    body: BulkAssignRequest,
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Assign a role to multiple users at once."""
    # Verify role
    role = (await db.execute(
        select(Role).where(
            Role.id == body.role_id,
            Role.organization_id == current_user.org_id,
            Role.is_deleted == False,
        )
    )).scalar_one_or_none()

    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    # Verify all users are in same org
    users = (await db.execute(
        select(User.id).where(
            User.id.in_(body.user_ids),
            User.organization_id == current_user.org_id,
            User.is_deleted == False,
        )
    )).scalars().all()

    valid_user_ids = set(users)
    success = 0
    skipped = 0
    errors = []

    for uid in body.user_ids:
        if uid not in valid_user_ids:
            errors.append({"user_id": uid, "error": "User not found"})
            continue

        # Check existing
        existing = (await db.execute(
            select(user_roles).where(
                user_roles.c.user_id == uid,
                user_roles.c.role_id == body.role_id,
            )
        )).first()

        if existing:
            skipped += 1
            continue

        await db.execute(
            insert(user_roles).values(user_id=uid, role_id=body.role_id)
        )
        success += 1

    await db.flush()

    return {
        "success": success,
        "skipped": skipped,
        "errors": errors,
        "role": {"id": role.id, "name": role.name},
    }


# ─── Users by role ──────────────────────────────────────────────────────────

@router.get(
    "/by-role/{role_id}",
    dependencies=[Depends(require_permission("admin.*"))],
)
async def users_by_role(
    role_id: str,
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List all users assigned to a specific role."""
    role = (await db.execute(
        select(Role)
        .options(selectinload(Role.users))
        .where(
            Role.id == role_id,
            Role.organization_id == current_user.org_id,
            Role.is_deleted == False,
        )
    )).scalar_one_or_none()

    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    return {
        "role": {"id": role.id, "name": role.name, "slug": role.slug},
        "users": [
            {
                "id": u.id,
                "email": u.email,
                "first_name": u.first_name,
                "last_name": u.last_name,
                "is_active": u.is_active,
            }
            for u in (role.users or [])
            if not getattr(u, "is_deleted", False)
        ],
    }
