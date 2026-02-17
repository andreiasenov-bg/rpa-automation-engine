"""Workflow Templates API routes.

Provides a library of pre-built workflow templates that users can browse,
preview, and instantiate as new workflows. Includes parameter validation
to ensure templates work before creating workflows.
"""

import re
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, func, desc, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_active_user
from core.security import TokenPayload
from db.models.workflow import Workflow

router = APIRouter()


# ━━━ Import comprehensive template library (25+ templates) ━━━━━━━━━━━━━━━━

from api.routes.template_library import BUILTIN_TEMPLATES
from api.routes.template_parameters import TEMPLATE_PARAMETERS, get_template_parameters


# ━━━ Helpers ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _enrich_template(t: dict, include_steps: bool = False) -> dict:
    """Add required_parameters to template data."""
    result = {
        "id": t["id"],
        "name": t["name"],
        "description": t["description"],
        "category": t["category"],
        "icon": t["icon"],
        "tags": t["tags"],
        "difficulty": t["difficulty"],
        "estimated_duration": t["estimated_duration"],
        "step_count": len(t["steps"]),
        "required_parameters": get_template_parameters(t["id"]),
    }
    if include_steps:
        result["steps"] = t["steps"]
    return result


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
URL_RE = re.compile(r"^https?://\S+$")


def _validate_param_value(param: dict, value) -> Optional[str]:
    """Validate a single parameter value. Returns error message or None."""
    ptype = param.get("type", "string")
    key = param["key"]
    label = param.get("label", key)

    if value is None or (isinstance(value, str) and not value.strip()):
        if param.get("required", False):
            return f"{label} is required"
        return None

    val = str(value).strip()

    if ptype == "url":
        if not URL_RE.match(val):
            return f"{label} must be a valid URL (starting with http:// or https://)"

    elif ptype == "email":
        if not EMAIL_RE.match(val):
            return f"{label} must be a valid email address"

    elif ptype == "number":
        try:
            float(val)
        except (ValueError, TypeError):
            return f"{label} must be a number"

    return None


def _set_nested_value(obj, path: str, value):
    """Set a value in a nested dict using dot notation path like 'steps.0.config.url'."""
    parts = path.split(".")
    current = obj
    for i, part in enumerate(parts[:-1]):
        if part.isdigit():
            idx = int(part)
            if isinstance(current, list) and idx < len(current):
                current = current[idx]
            else:
                return
        else:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return
    last = parts[-1]
    if last.isdigit():
        idx = int(last)
        if isinstance(current, list) and idx < len(current):
            current[idx] = value
    elif isinstance(current, dict):
        current[last] = value


def _merge_parameters_into_steps(steps: list, params: dict, param_defs: list) -> list:
    """Merge user-provided parameters into template step configs using maps_to paths."""
    import copy
    merged = copy.deepcopy(steps)
    for pdef in param_defs:
        maps_to = pdef.get("maps_to")
        key = pdef["key"]
        if maps_to and key in params and params[key]:
            _set_nested_value({"steps": merged}, maps_to if maps_to.startswith("steps") else f"steps.{maps_to}", params[key])
    return merged


# ━━━ Request / Response models ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TemplateInstantiateRequest(BaseModel):
    template_id: str
    name: str
    description: Optional[str] = None
    parameters: Optional[dict] = None


class TemplateValidateRequest(BaseModel):
    parameters: dict = {}


# ━━━ Endpoints ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

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

    result = [_enrich_template(t) for t in templates]
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
    """Get a single template with full step details and required parameters."""
    for t in BUILTIN_TEMPLATES:
        if t["id"] == template_id:
            return _enrich_template(t, include_steps=True)
    raise HTTPException(status_code=404, detail="Template not found")


@router.post("/{template_id}/validate")
async def validate_template_params(
    template_id: str,
    body: TemplateValidateRequest,
    current_user: TokenPayload = Depends(get_current_active_user),
):
    """Validate template parameters before instantiation.

    Checks required fields, type formats (URL, email, number), and returns
    per-field validation results.
    """
    template = None
    for t in BUILTIN_TEMPLATES:
        if t["id"] == template_id:
            template = t
            break
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    param_defs = get_template_parameters(template_id)
    if not param_defs:
        return {"valid": True, "errors": [], "warnings": [], "fields": {}}

    errors = []
    warnings = []
    fields = {}

    for pdef in param_defs:
        key = pdef["key"]
        value = body.parameters.get(key)
        error = _validate_param_value(pdef, value)

        if error:
            errors.append({"key": key, "message": error})
            fields[key] = {"status": "error", "message": error}
        elif value and str(value).strip():
            fields[key] = {"status": "ok", "message": "Valid"}
        elif not pdef.get("required", False):
            fields[key] = {"status": "ok", "message": "Optional — skipped"}

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "fields": fields,
    }


@router.post("/{template_id}/instantiate")
async def instantiate_template(
    template_id: str,
    body: TemplateInstantiateRequest,
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new workflow from a template with user-provided parameters."""
    template = None
    for t in BUILTIN_TEMPLATES:
        if t["id"] == template_id:
            template = t
            break
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Validate required parameters if template has them
    param_defs = get_template_parameters(template_id)
    steps = template["steps"]

    if param_defs and body.parameters:
        # Validate before creating
        for pdef in param_defs:
            key = pdef["key"]
            value = body.parameters.get(key)
            error = _validate_param_value(pdef, value)
            if error and pdef.get("required", False):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Parameter validation failed: {error}",
                )
        # Merge parameters into step configs
        steps = _merge_parameters_into_steps(steps, body.parameters, param_defs)
    elif param_defs:
        # Template has required params but none provided — check if any are required
        required_missing = [p for p in param_defs if p.get("required", False)]
        if required_missing:
            labels = ", ".join(p.get("label", p["key"]) for p in required_missing)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Missing required parameters: {labels}",
            )

    workflow = Workflow(
        id=str(uuid.uuid4()),
        organization_id=current_user.org_id,
        created_by_id=current_user.sub,
        name=body.name,
        description=body.description or template["description"],
        definition={
            "steps": steps,
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
