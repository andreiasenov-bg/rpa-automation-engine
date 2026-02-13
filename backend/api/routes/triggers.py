"""Trigger API routes.

CRUD for trigger management + webhook endpoint + test/fire actions.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from typing import Optional

from triggers.base import TriggerTypeEnum
from triggers.manager import get_trigger_manager

router = APIRouter()


# -- Schemas --

class TriggerCreate(BaseModel):
    """Schema for creating a new trigger."""
    workflow_id: str
    name: str
    trigger_type: str  # Must be a valid TriggerTypeEnum value
    config: dict = Field(default_factory=dict)
    is_enabled: bool = True


class TriggerUpdate(BaseModel):
    """Schema for updating a trigger."""
    name: Optional[str] = None
    config: Optional[dict] = None
    is_enabled: Optional[bool] = None


class TriggerResponse(BaseModel):
    """Schema for trigger API responses."""
    id: str
    workflow_id: str
    name: str
    trigger_type: str
    config: dict
    is_enabled: bool
    trigger_count: int = 0
    last_triggered_at: Optional[str] = None
    error_message: Optional[str] = None


class TriggerTestRequest(BaseModel):
    """Schema for testing a trigger config."""
    trigger_type: str
    config: dict


class TriggerFireRequest(BaseModel):
    """Schema for manually firing a trigger."""
    payload: dict = Field(default_factory=dict)


# -- Endpoints --

@router.get("/types", summary="List supported trigger types")
async def list_trigger_types():
    """Get all supported trigger types and their descriptions."""
    manager = get_trigger_manager()
    return {
        "types": manager.get_supported_types(),
    }


@router.get("/status", summary="Get trigger manager status")
async def get_trigger_status():
    """Get the current status of the trigger manager."""
    manager = get_trigger_manager()
    return manager.get_status()


@router.post("/test", summary="Test trigger configuration")
async def test_trigger(request: TriggerTestRequest):
    """Validate a trigger configuration without creating it."""
    manager = get_trigger_manager()
    result = await manager.test_trigger(request.trigger_type, request.config)
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.error or result.message,
        )
    return {"message": result.message, "valid": True}


@router.post("/{trigger_id}/fire", summary="Manually fire a trigger")
async def fire_trigger(trigger_id: str, request: TriggerFireRequest):
    """Manually fire a trigger to start a workflow execution."""
    manager = get_trigger_manager()
    result = await manager.fire_trigger(trigger_id, payload=request.payload)
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.error or result.message,
        )
    return {
        "message": result.message,
        "execution_id": result.execution_id,
    }


@router.post("/{trigger_id}/start", summary="Start a trigger")
async def start_trigger(trigger_id: str):
    """Start listening for trigger events (re-enable a stopped trigger)."""
    manager = get_trigger_manager()
    # TODO: Load trigger from DB by trigger_id, then call manager.start_trigger()
    return {"message": "Trigger start endpoint ready", "trigger_id": trigger_id}


@router.post("/{trigger_id}/stop", summary="Stop a trigger")
async def stop_trigger(trigger_id: str):
    """Stop listening for trigger events."""
    manager = get_trigger_manager()
    result = await manager.stop_trigger(trigger_id)
    return {"message": result.message, "success": result.success}


# -- Webhook Receiver --

@router.post("/webhooks/{path:path}", summary="Receive webhook")
async def receive_webhook(path: str, request: Request):
    """Universal webhook receiver endpoint.

    External systems POST here to trigger workflows.
    The path is matched against registered webhook triggers.
    """
    manager = get_trigger_manager()
    webhook_handler = manager._handlers.get("webhook")

    if not webhook_handler:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Webhook handler not available",
        )

    # Look up trigger by path
    full_path = f"/{path}" if not path.startswith("/") else path
    trigger_id = webhook_handler.get_trigger_for_path(full_path)

    if not trigger_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No webhook registered for path: {full_path}",
        )

    # Verify signature if configured
    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")
    if not webhook_handler.verify_signature(trigger_id, body, signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )

    # Parse payload
    try:
        payload = await request.json()
    except Exception:
        payload = {"raw_body": body.decode("utf-8", errors="replace")}

    payload["_headers"] = dict(request.headers)
    payload["_method"] = request.method
    payload["_path"] = full_path

    # Fire the trigger
    result = await manager.fire_trigger(trigger_id, payload=payload)
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.error or "Trigger execution failed",
        )

    return {
        "accepted": True,
        "execution_id": result.execution_id,
    }
