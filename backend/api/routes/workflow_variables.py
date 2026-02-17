"""Workflow variables API.

Manage workflow-level variables that flow between steps:
- Define input/output variable schemas per workflow
- Set default values, types, and descriptions
- Variable validation before execution
"""

import uuid
from typing import Optional, Any
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_active_user
from core.security import TokenPayload
from db.models.workflow import Workflow

router = APIRouter(tags=["workflow-variables"])


# ─── Schemas ─────────────────────────────────────────────────────────────────

class VarType(str, Enum):
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    JSON = "json"
    LIST = "list"
    SECRET = "secret"


class VariableDefinition(BaseModel):
    name: str = Field(..., min_length=1, max_length=128, pattern=r"^[a-zA-Z_][a-zA-Z0-9_]*$")
    type: VarType = VarType.STRING
    default_value: Optional[Any] = None
    description: str = ""
    required: bool = False
    scope: str = Field(default="workflow", description="workflow | step")
    sensitive: bool = False


class VariableSchemaRequest(BaseModel):
    variables: list[VariableDefinition] = Field(default_factory=list, max_length=100)


class StepMappingEntry(BaseModel):
    step_id: str
    input_mapping: dict[str, str] = Field(
        default_factory=dict,
        description="Map step input param -> variable name or expression",
    )
    output_mapping: dict[str, str] = Field(
        default_factory=dict,
        description="Map step output key -> variable name to store result",
    )


class StepMappingsRequest(BaseModel):
    mappings: list[StepMappingEntry] = Field(default_factory=list)


class ExecutionVariablesRequest(BaseModel):
    """Variables to pass when starting an execution."""
    variables: dict[str, Any] = Field(default_factory=dict)


# ─── Helpers ─────────────────────────────────────────────────────────────────

async def _get_workflow(workflow_id: str, org_id: str, db: AsyncSession) -> Workflow:
    wf = (await db.execute(
        select(Workflow).where(
            Workflow.id == workflow_id,
            Workflow.organization_id == org_id,
            Workflow.is_deleted == False,
        )
    )).scalar_one_or_none()

    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return wf


def _get_definition(wf: Workflow) -> dict:
    """Get workflow definition as dict."""
    if isinstance(wf.definition, dict):
        return wf.definition
    return {}


# ─── Get variable schema ────────────────────────────────────────────────────

@router.get("/{workflow_id}/variables")
async def get_variables(
    workflow_id: str,
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the variable schema for a workflow."""
    wf = await _get_workflow(workflow_id, current_user.org_id, db)
    definition = _get_definition(wf)

    return {
        "workflow_id": wf.id,
        "variables": definition.get("variables", []),
        "step_mappings": definition.get("step_mappings", []),
    }


# ─── Update variable schema ─────────────────────────────────────────────────

@router.put("/{workflow_id}/variables")
async def update_variables(
    workflow_id: str,
    body: VariableSchemaRequest,
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update the variable schema for a workflow."""
    wf = await _get_workflow(workflow_id, current_user.org_id, db)
    definition = _get_definition(wf)

    # Check for duplicate variable names
    names = [v.name for v in body.variables]
    if len(names) != len(set(names)):
        raise HTTPException(status_code=400, detail="Duplicate variable names")

    # Serialize
    definition["variables"] = [v.model_dump() for v in body.variables]
    wf.definition = definition
    await db.flush()

    return {
        "workflow_id": wf.id,
        "variables": definition["variables"],
        "count": len(body.variables),
    }


# ─── Update step mappings ───────────────────────────────────────────────────

@router.put("/{workflow_id}/variables/mappings")
async def update_step_mappings(
    workflow_id: str,
    body: StepMappingsRequest,
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update step input/output variable mappings."""
    wf = await _get_workflow(workflow_id, current_user.org_id, db)
    definition = _get_definition(wf)

    # Validate step IDs exist in workflow
    step_ids = {s.get("id") for s in definition.get("steps", [])}
    for mapping in body.mappings:
        if mapping.step_id not in step_ids:
            raise HTTPException(
                status_code=400,
                detail=f"Step '{mapping.step_id}' not found in workflow",
            )

    definition["step_mappings"] = [m.model_dump() for m in body.mappings]
    wf.definition = definition
    await db.flush()

    return {
        "workflow_id": wf.id,
        "step_mappings": definition["step_mappings"],
    }


# ─── Validate execution variables ───────────────────────────────────────────

@router.post("/{workflow_id}/variables/validate")
async def validate_execution_variables(
    workflow_id: str,
    body: ExecutionVariablesRequest,
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Validate variables before execution. Returns errors for missing required variables or type mismatches."""
    wf = await _get_workflow(workflow_id, current_user.org_id, db)
    definition = _get_definition(wf)
    schema = definition.get("variables", [])

    errors = []
    resolved = {}

    for var_def in schema:
        name = var_def["name"]
        var_type = var_def.get("type", "string")
        required = var_def.get("required", False)
        default = var_def.get("default_value")

        if name in body.variables:
            value = body.variables[name]
        elif default is not None:
            value = default
        elif required:
            errors.append({"variable": name, "error": "Required variable not provided"})
            continue
        else:
            value = None

        # Type validation
        if value is not None:
            type_ok = _validate_type(value, var_type)
            if not type_ok:
                errors.append({
                    "variable": name,
                    "error": f"Expected type '{var_type}', got '{type(value).__name__}'",
                })
                continue

        resolved[name] = value

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "resolved": resolved,
    }


def _validate_type(value: Any, var_type: str) -> bool:
    """Check if value matches the expected variable type."""
    if var_type == "string":
        return isinstance(value, str)
    elif var_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    elif var_type == "boolean":
        return isinstance(value, bool)
    elif var_type == "json":
        return isinstance(value, (dict, list))
    elif var_type == "list":
        return isinstance(value, list)
    elif var_type == "secret":
        return isinstance(value, str)
    return True
