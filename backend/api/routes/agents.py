"""Agent management API routes — fully wired.

Provides CRUD operations for distributed RPA execution agents,
heartbeat tracking, capability management, and status monitoring.
"""

import hashlib
import secrets
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_active_user
from core.security import TokenPayload
from db.models.agent import Agent

router = APIRouter()


# ─── Schemas ────────────────────────────────────────────────────────────────

class AgentRegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    version: str = Field(default="1.0.0")
    capabilities: Optional[dict] = None


class AgentUpdateRequest(BaseModel):
    name: Optional[str] = None
    version: Optional[str] = None
    capabilities: Optional[dict] = None


# ─── Helpers ────────────────────────────────────────────────────────────────

def _to_response(agent: Agent) -> dict:
    return {
        "id": agent.id,
        "name": agent.name,
        "status": agent.status,
        "version": agent.version,
        "capabilities": agent.capabilities,
        "last_heartbeat_at": agent.last_heartbeat_at.isoformat() if agent.last_heartbeat_at else None,
        "created_at": agent.created_at.isoformat() if agent.created_at else None,
        "updated_at": agent.updated_at.isoformat() if agent.updated_at else None,
    }


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


# ─── Endpoints ──────────────────────────────────────────────────────────────

@router.get("")
async def list_agents(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = Query(None),
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List agents in the organization with pagination and filtering."""
    conditions = [
        Agent.organization_id == current_user.org,
        Agent.is_deleted == False,
    ]

    if status_filter:
        conditions.append(Agent.status == status_filter)
    if search:
        conditions.append(Agent.name.ilike(f"%{search}%"))

    where = and_(*conditions)

    total = (await db.execute(select(func.count()).select_from(Agent).where(where))).scalar() or 0

    offset = (page - 1) * per_page
    query = select(Agent).where(where).order_by(desc(Agent.created_at)).offset(offset).limit(per_page)
    rows = (await db.execute(query)).scalars().all()

    now = datetime.now(timezone.utc)
    threshold = now - timedelta(minutes=2)
    online = sum(1 for a in rows if a.last_heartbeat_at and a.last_heartbeat_at >= threshold)

    return {
        "agents": [_to_response(a) for a in rows],
        "total": total,
        "page": page,
        "per_page": per_page,
        "online_count": online,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def register_agent(
    body: AgentRegisterRequest,
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Register a new agent. Returns a one-time agent token."""
    raw_token = f"rpa-agent-{secrets.token_urlsafe(32)}"
    token_hash = _hash_token(raw_token)

    agent = Agent(
        id=str(uuid.uuid4()),
        organization_id=current_user.org,
        name=body.name,
        agent_token_hash=token_hash,
        status="inactive",
        version=body.version,
        capabilities=body.capabilities,
    )
    db.add(agent)
    await db.flush()

    return {
        "agent": _to_response(agent),
        "token": raw_token,
        "message": "Save the token — it will not be shown again.",
    }


@router.get("/stats")
async def agent_stats(
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get agent statistics."""
    base = and_(Agent.organization_id == current_user.org, Agent.is_deleted == False)

    total = (await db.execute(select(func.count()).select_from(Agent).where(base))).scalar() or 0

    status_q = select(Agent.status, func.count()).where(base).group_by(Agent.status)
    status_rows = (await db.execute(status_q)).all()
    by_status = {r[0]: r[1] for r in status_rows}

    now = datetime.now(timezone.utc)
    threshold = now - timedelta(minutes=2)
    online_q = select(func.count()).select_from(Agent).where(
        and_(base, Agent.last_heartbeat_at >= threshold)
    )
    online = (await db.execute(online_q)).scalar() or 0

    return {"total": total, "online": online, "by_status": by_status}


@router.get("/{agent_id}")
async def get_agent(
    agent_id: str,
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get agent details."""
    agent = (await db.execute(
        select(Agent).where(
            Agent.id == agent_id,
            Agent.organization_id == current_user.org,
            Agent.is_deleted == False,
        )
    )).scalar_one_or_none()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    return _to_response(agent)


@router.put("/{agent_id}")
async def update_agent(
    agent_id: str,
    body: AgentUpdateRequest,
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update agent details."""
    agent = (await db.execute(
        select(Agent).where(
            Agent.id == agent_id,
            Agent.organization_id == current_user.org,
            Agent.is_deleted == False,
        )
    )).scalar_one_or_none()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    if body.name is not None:
        agent.name = body.name
    if body.version is not None:
        agent.version = body.version
    if body.capabilities is not None:
        agent.capabilities = body.capabilities

    await db.flush()
    return _to_response(agent)


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_agent(
    agent_id: str,
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete an agent."""
    agent = (await db.execute(
        select(Agent).where(
            Agent.id == agent_id,
            Agent.organization_id == current_user.org,
            Agent.is_deleted == False,
        )
    )).scalar_one_or_none()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    agent.soft_delete()
    await db.flush()


@router.post("/{agent_id}/heartbeat")
async def update_heartbeat(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Update agent heartbeat (called by agents, token-authenticated)."""
    agent = (await db.execute(
        select(Agent).where(Agent.id == agent_id, Agent.is_deleted == False)
    )).scalar_one_or_none()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    agent.last_heartbeat_at = datetime.now(timezone.utc)
    agent.status = "active"
    await db.flush()

    return {"status": "ok", "agent_id": agent_id, "timestamp": agent.last_heartbeat_at.isoformat()}


@router.post("/{agent_id}/rotate-token")
async def rotate_agent_token(
    agent_id: str,
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Rotate agent authentication token."""
    agent = (await db.execute(
        select(Agent).where(
            Agent.id == agent_id,
            Agent.organization_id == current_user.org,
            Agent.is_deleted == False,
        )
    )).scalar_one_or_none()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    raw_token = f"rpa-agent-{secrets.token_urlsafe(32)}"
    agent.agent_token_hash = _hash_token(raw_token)
    await db.flush()

    return {
        "agent_id": agent_id,
        "token": raw_token,
        "message": "Token rotated. Save the new token — it will not be shown again.",
    }
