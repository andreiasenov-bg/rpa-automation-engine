"""Execution and workflow run schemas."""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional


class ExecutionCreate(BaseModel):
    """Request to create/trigger a workflow execution."""

    workflow_id: str = Field(description="ID of the workflow to execute")


class ExecutionResponse(BaseModel):
    """Execution run information response."""

    id: str = Field(description="Execution ID")
    workflow_id: str = Field(description="Workflow ID")
    agent_id: Optional[str] = Field(default=None, description="Agent ID that executed the workflow")
    trigger_type: str = Field(description="How execution was triggered (manual, schedule, webhook)")
    status: str = Field(description="Execution status (pending, running, success, failed, cancelled)")
    started_at: Optional[datetime] = Field(default=None, description="Execution start timestamp")
    completed_at: Optional[datetime] = Field(default=None, description="Execution completion timestamp")
    duration_ms: Optional[int] = Field(default=None, description="Execution duration in milliseconds")
    error_message: Optional[str] = Field(default=None, description="Error message if execution failed")
    retry_count: int = Field(default=0, description="Number of retry attempts")

    class Config:
        from_attributes = True


class ExecutionLogResponse(BaseModel):
    """Execution log entry response."""

    id: str = Field(description="Log entry ID")
    level: str = Field(description="Log level (debug, info, warning, error)")
    message: str = Field(description="Log message")
    context: Optional[dict] = Field(default=None, description="Additional context data")
    timestamp: datetime = Field(description="Log timestamp")

    class Config:
        from_attributes = True


class ExecutionListResponse(BaseModel):
    """Paginated list of executions."""

    executions: List[ExecutionResponse] = Field(description="List of executions")
    total: int = Field(description="Total number of executions")
    page: int = Field(description="Current page number")
    per_page: int = Field(description="Items per page")
