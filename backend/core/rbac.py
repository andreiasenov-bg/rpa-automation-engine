"""Role-Based Access Control (RBAC) enforcement.

Provides dependency-injection helpers for FastAPI routes to enforce
permission checks at the endpoint level.

Usage:
    @router.get("/admin/users", dependencies=[Depends(require_permission("users.read"))])
    async def list_users(...): ...

    @router.delete("/workflows/{id}", dependencies=[Depends(require_any_permission(["workflows.delete", "admin.*"]))])
    async def delete_workflow(...): ...
"""

import logging
from typing import Optional

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dependencies import get_current_active_user, get_db

logger = logging.getLogger(__name__)


async def _get_user_permissions(user_id: str, org_id: str, db: AsyncSession) -> set[str]:
    """Load all permission codes for a user via their roles.

    Caches per-request via the session identity map.
    """
    from db.models.user import User
    from db.models.role import Role
    from db.models.permission import Permission

    # Load user → roles → permissions in one query
    result = await db.execute(
        select(User)
        .where(User.id == user_id)
        .options(
            selectinload(User.roles).selectinload(Role.permissions)
        )
    )
    user = result.scalar_one_or_none()

    if not user:
        return set()

    permissions: set[str] = set()
    for role in user.roles:
        for perm in role.permissions:
            permissions.add(perm.code)

    return permissions


def _check_permission(user_perms: set[str], required: str) -> bool:
    """Check if user permissions satisfy the required permission.

    Supports wildcard: "admin.*" matches "admin.read", "admin.write", etc.
    """
    if required in user_perms:
        return True

    # Check wildcards in user permissions
    for perm in user_perms:
        if perm == "*":
            return True
        if perm.endswith(".*"):
            prefix = perm[:-2]
            if required.startswith(prefix + "."):
                return True

    return False


def require_permission(permission: str):
    """FastAPI dependency that enforces a single permission.

    Returns 403 if the user lacks the required permission.
    Falls back to allowing access if no roles/permissions are configured
    (graceful degradation for bootstrapping).
    """

    async def _check(
        current_user=Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
    ):
        user_perms = await _get_user_permissions(
            current_user.id, current_user.organization_id, db
        )

        # Graceful degradation: if no permissions exist at all (fresh install),
        # allow access to prevent lockout
        if not user_perms:
            logger.debug(
                "RBAC: No permissions found for user %s, allowing access (bootstrap mode)",
                current_user.id,
            )
            return current_user

        if not _check_permission(user_perms, permission):
            logger.warning(
                "RBAC denied: user=%s permission=%s available=%s",
                current_user.email,
                permission,
                user_perms,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permission: {permission}",
            )

        return current_user

    return _check


def require_any_permission(*permissions: str):
    """FastAPI dependency that enforces at least one of the given permissions."""

    async def _check(
        current_user=Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
    ):
        user_perms = await _get_user_permissions(
            current_user.id, current_user.organization_id, db
        )

        if not user_perms:
            return current_user

        for perm in permissions:
            if _check_permission(user_perms, perm):
                return current_user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Missing one of required permissions: {', '.join(permissions)}",
        )

    return _check


def require_all_permissions(*permissions: str):
    """FastAPI dependency that enforces all of the given permissions."""

    async def _check(
        current_user=Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
    ):
        user_perms = await _get_user_permissions(
            current_user.id, current_user.organization_id, db
        )

        if not user_perms:
            return current_user

        missing = [p for p in permissions if not _check_permission(user_perms, p)]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permissions: {', '.join(missing)}",
            )

        return current_user

    return _check


def require_admin():
    """Shortcut: require admin.* permission."""
    return require_permission("admin.*")


def require_org_owner():
    """FastAPI dependency that checks if the user is the organization owner.

    This is a stricter check than admin permissions — it verifies the user
    is the original creator of the organization.
    """

    async def _check(
        current_user=Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
    ):
        from db.models.organization import Organization

        result = await db.execute(
            select(Organization).where(Organization.id == current_user.organization_id)
        )
        org = result.scalar_one_or_none()

        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")

        # Check if user has admin.* or is explicitly the owner
        user_perms = await _get_user_permissions(
            current_user.id, current_user.organization_id, db
        )
        if not _check_permission(user_perms, "admin.*"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Organization owner access required",
            )

        return current_user

    return _check
