"""Workflow schemas."""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional, Dict, Any


class WorkflowStepCreate(BaseModel):
    """Request to create a workflow step."""

    step_order: int = Field(ge=0, description="Step execution order")
    task_type: str = Field(min_length=1, description="Type of task (e.g., 'click', 'type', 'wait')")
    name: str = Field(min_length=1, description="Human-readable step name")
    config: Dict[str, Any] = Field(default={}, description="Step-specific configuration")
    timeout_seconds: Optional[int] = Field(default=None, ge=1, description="Step timeout in seconds")


class WorkflowCreate(BaseModel):
    """Request to create a workflow."""

    name: str = Field(min_length=1, description="Workflow name")
    description: Optional[str] = Field(default="", description="Workflow description")
    definition: Dict[str, Any] = Field(description="Workflow definition/configuration")


class WorkflowUpdate(BaseModel):
    """Request to update a workflow."""

    name: Optional[str] = Field(default=None, min_length=1, description="Workflow name")
    description: Optional[str] = Field(default=None, description="Workflow description")
    definition: Optional[Dict[str, Any]] = Field(default=None, description="Workflow definition")
    is_enabled: Optional[bool] = Field(default=None, description="Whether workflow is enabled")


class WorkflowResponse(BaseModel):
    """Workflow information response."""

    id: str = Field(description="Workflow ID")
    name: str = Field(description="Workflow name")
    description: str = Field(description="Workflow description")
    definition: Dict[str, Any] = Field(description="Workflow definition/configuration")
    version: int = Field(description="Workflow version number")
    is_enabled: bool = Field(description="Whether workflow is enabled")
    status: str = Field(description="Current workflow status (draft, published, archived)")
    created_by: str = Field(description="User ID who created the workflow")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")

    class Config:
        from_attributes = True


class WorkflowListResponse(BaseModel):
    """Paginated list of workflows."""

    workflows: List[WorkflowResponse] = Field(description="List of workflows")
    total: int = Field(description="Total number of workflows")
    page: int = Field(description="Current page number")
    per_page: int = Field(description="Items per page")
