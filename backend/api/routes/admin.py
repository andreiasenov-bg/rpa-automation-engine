"""Admin panel API routes.

Organization-level admin operations:
- Organization settings and stats
- Role management (list, create, update, delete)
- Permission management
- System health overview
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_active_user
from core.rbac import require_permission
from core.security import TokenPayload
from db.models.user import User
from db.models.workflow import Workflow
from db.models.execution import Execution
from db.models.agent import Agent
from db.models.credential import Credential
from db.models.role import Role
from db.models.permission import Permission
from db.models.organization import Organization

router = APIRouter()


# ─── Schemas ────────────────────────────────────────────────────────────────

class RoleCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    slug: str = Field(..., min_length=1, max_length=64)
    description: Optional[str] = None
    permission_ids: list[str] = Field(default_factory=list)


class RoleUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    permission_ids: Optional[list[str]] = None


class OrgSettingsUpdate(BaseModel):
    name: Optional[str] = None
    plan: Optional[str] = None


# ─── Organization Overview ──────────────────────────────────────────────────

@router.get("/overview", dependencies=[Depends(require_permission("admin.*"))])
async def admin_overview(
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get organization overview with resource counts."""
    org_id = current_user.org
    base = lambda Model: and_(Model.organization_id == org_id, Model.is_deleted == False)

    users_count = (await db.execute(select(func.count()).select_from(User).where(base(User)))).scalar() or 0
    workflows_count = (await db.execute(select(func.count()).select_from(Workflow).where(base(Workflow)))).scalar() or 0
    agents_count = (await db.execute(select(func.count()).select_from(Agent).where(base(Agent)))).scalar() or 0
    credentials_count = (await db.execute(select(func.count()).select_from(Credential).where(base(Credential)))).scalar() or 0

    # Execution stats
    exec_total = (await db.execute(
        select(func.count()).select_from(Execution).where(base(Execution))
    )).scalar() or 0
    exec_running = (await db.execute(
        select(func.count()).select_from(Execution).where(
            and_(base(Execution), Execution.status == "running")
        )
    )).scalar() or 0
    exec_failed = (await db.execute(
        select(func.count()).select_from(Execution).where(
            and_(base(Execution), Execution.status == "failed")
        )
    )).scalar() or 0

    # Org details
    org = (await db.execute(
        select(Organization).where(Organization.id == org_id)
    )).scalar_one_or_none()

    return {
        "organization": {
            "id": org.id if org else org_id,
            "name": org.name if org else "Unknown",
            "plan": org.plan if org else "free",
            "created_at": org.created_at.isoformat() if org and org.created_at else None,
        },
        "counts": {
            "users": users_count,
            "workflows": workflows_count,
            "agents": agents_count,
            "credentials": credentials_count,
            "executions_total": exec_total,
            "executions_running": exec_running,
            "executions_failed": exec_failed,
        },
    }


@router.put("/organization", dependencies=[Depends(require_permission("admin.*"))])
async def update_org_settings(
    body: OrgSettingsUpdate,
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update organization settings (admin only)."""
    org = (await db.execute(
        select(Organization).where(Organization.id == current_user.org)
    )).scalar_one_or_none()

    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    if body.name is not None:
        org.name = body.name
    if body.plan is not None:
        org.plan = body.plan

    await db.flush()
    return {
        "id": org.id,
        "name": org.name,
        "plan": org.plan,
    }


# ─── Role Management ───────────────────────────────────────────────────────

@router.get("/roles", dependencies=[Depends(require_permission("admin.*"))])
async def list_roles(
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List all roles in the organization."""
    query = (
        select(Role)
        .where(
            Role.organization_id == current_user.org,
            Role.is_deleted == False,
        )
        .order_by(Role.name)
    )
    roles = (await db.execute(query)).scalars().all()

    result = []
    for role in roles:
        perms = []
        if hasattr(role, 'permissions') and role.permissions:
            perms = [{"id": p.id, "code": p.code, "name": p.name} for p in role.permissions]

        result.append({
            "id": role.id,
            "name": role.name,
            "slug": role.slug,
            "description": getattr(role, 'description', None),
            "permissions": perms,
            "created_at": role.created_at.isoformat() if role.created_at else None,
        })

    return {"roles": result, "total": len(result)}


@router.post("/roles", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("admin.*"))])
async def create_role(
    body: RoleCreateRequest,
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new role."""
    # Check for duplicate slug
    existing = (await db.execute(
        select(Role).where(
            Role.organization_id == current_user.org,
            Role.slug == body.slug,
            Role.is_deleted == False,
        )
    )).scalar_one_or_none()

    if existing:
        raise HTTPException(status_code=409, detail=f"Role with slug '{body.slug}' already exists")

    role = Role(
        id=str(uuid.uuid4()),
        organization_id=current_user.org,
        name=body.name,
        slug=body.slug,
    )
    db.add(role)
    await db.flush()

    return {"id": role.id, "name": role.name, "slug": role.slug, "message": "Role created"}


@router.put("/roles/{role_id}", dependencies=[Depends(require_permission("admin.*"))])
async def update_role(
    role_id: str,
    body: RoleUpdateRequest,
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a role."""
    role = (await db.execute(
        select(Role).where(
            Role.id == role_id,
            Role.organization_id == current_user.org,
            Role.is_deleted == False,
        )
    )).scalar_one_or_none()

    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    if body.name is not None:
        role.name = body.name
    if body.description is not None:
        role.description = body.description

    await db.flush()
    return {"id": role.id, "name": role.name, "message": "Role updated"}


@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_permission("admin.*"))])
async def delete_role(
    role_id: str,
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a role."""
    role = (await db.execute(
        select(Role).where(
            Role.id == role_id,
            Role.organization_id == current_user.org,
            Role.is_deleted == False,
        )
    )).scalar_one_or_none()

    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    # Prevent deleting built-in admin role
    if role.slug == "admin":
        raise HTTPException(status_code=400, detail="Cannot delete the admin role")

    role.soft_delete()
    await db.flush()


# ─── Permissions ────────────────────────────────────────────────────────────

@router.get("/permissions", dependencies=[Depends(require_permission("admin.*"))])
async def list_permissions(
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List all available permissions."""
    query = (
        select(Permission)
        .where(
            Permission.organization_id == current_user.org,
            Permission.is_deleted == False,
        )
        .order_by(Permission.code)
    )
    perms = (await db.execute(query)).scalars().all()

    return {
        "permissions": [
            {
                "id": p.id,
                "code": p.code,
                "name": p.name,
                "description": getattr(p, 'description', None),
            }
            for p in perms
        ],
    }
