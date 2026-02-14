"""Workflow Templates API routes.

Provides a library of pre-built workflow templates that users can browse,
preview, and instantiate as new workflows.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, func, desc, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_active_user
from core.security import TokenPayload
from db.models.workflow import Workflow

router = APIRouter()


# ─── Import comprehensive template library (25+ templates) ────────────────

from api.routes.template_library import BUILTIN_TEMPLATES


# ─── Endpoints ──────────────────────────────────────────────────────────────

class TemplateInstantiateRequest(BaseModel):
    template_id: str
    name: str
    description: Optional[str] = None


@router.get("")
async def list_templates(
    category: Optional[str] = Query(None),
    difficulty: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    current_user: TokenPayload = Depends(get_current_active_user),
):
    """List all available workflow templates."""
    templates = BUILTIN_TEMPLATES

    if category:
        templates = [t for t in templates if t["category"] == category]
    if difficulty:
        templates = [t for t in templates if t["difficulty"] == difficulty]
    if search:
        q = search.lower()
        templates = [
            t for t in templates
            if q in t["name"].lower()
            or q in t["description"].lower()
            or any(q in tag for tag in t.get("tags", []))
        ]

    # Return without step details for list view
    result = []
    for t in templates:
        result.append({
            "id": t["id"],
            "name": t["name"],
            "description": t["description"],
            "category": t["category"],
            "icon": t["icon"],
            "tags": t["tags"],
            "difficulty": t["difficulty"],
            "estimated_duration": t["estimated_duration"],
            "step_count": len(t["steps"]),
        })

    return {"templates": result, "total": len(result)}


@router.get("/categories")
async def list_categories(
    current_user: TokenPayload = Depends(get_current_active_user),
):
    """Get distinct template categories."""
    cats = sorted(set(t["category"] for t in BUILTIN_TEMPLATES))
    return {"categories": cats}


@router.get("/{template_id}")
async def get_template(
    template_id: str,
    current_user: TokenPayload = Depends(get_current_active_user),
):
    """Get a single template with full step details."""
    for t in BUILTIN_TEMPLATES:
        if t["id"] == template_id:
            return t
    raise HTTPException(status_code=404, detail="Template not found")


@router.post("/{template_id}/instantiate")
async def instantiate_template(
    template_id: str,
    body: TemplateInstantiateRequest,
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new workflow from a template."""
    template = None
    for t in BUILTIN_TEMPLATES:
        if t["id"] == template_id:
            template = t
            break

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    import uuid

    workflow = Workflow(
        id=str(uuid.uuid4()),
        organization_id=current_user.org_id,
        created_by_id=current_user.sub,
        name=body.name,
        description=body.description or template["description"],
        definition={
            "steps": template["steps"],
            "source_template": template_id,
        },
        version=1,
        status="draft",
    )

    db.add(workflow)
    await db.flush()

    return {
        "workflow_id": workflow.id,
        "name": workflow.name,
        "template_id": template_id,
        "template_name": template["name"],
        "status": "draft",
        "message": f"Workflow created from template '{template['name']}'",
    }
