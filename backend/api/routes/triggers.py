"""Trigger API routes — CRUD + webhook receiver + test/fire actions."""

from fastapi import APIRouter, Depends, HTTPException, Request, status as http_status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from typing import Optional, List

from core.security import TokenPayload
from app.dependencies import get_db, get_current_active_user
from services.trigger_service import TriggerService
from triggers.manager import get_trigger_manager

router = APIRouter()


# -- Schemas --

class TriggerCreate(BaseModel):
    workflow_id: str
    name: str
    trigger_type: str
    config: dict = Field(default_factory=dict)
    is_enabled: bool = True


class TriggerUpdate(BaseModel):
    name: Optional[str] = None
    config: Optional[dict] = None


class TriggerResponse(BaseModel):
    id: str
    workflow_id: str
    name: str
    trigger_type: str
    config: dict
    is_enabled: bool
    trigger_count: int = 0
    last_triggered_at: Optional[str] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class TriggerTestRequest(BaseModel):
    trigger_type: str
    config: dict


class TriggerFireRequest(BaseModel):
    payload: dict = Field(default_factory=dict)


def _trigger_to_response(t) -> TriggerResponse:
    return TriggerResponse(
        id=t.id,
        workflow_id=t.workflow_id,
        name=t.name,
        trigger_type=t.trigger_type,
        config=t.config or {},
        is_enabled=t.is_enabled,
        trigger_count=t.trigger_count or 0,
        last_triggered_at=str(t.last_triggered_at) if t.last_triggered_at else None,
        error_message=t.error_message,
    )


# -- CRUD --

@router.get("/", response_model=List[TriggerResponse], summary="List triggers")
async def list_triggers(
    workflow_id: Optional[str] = None,
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    svc = TriggerService(db)
    filters = {"workflow_id": workflow_id} if workflow_id else None
    triggers, _ = await svc.list(organization_id=current_user.org_id, limit=200, filters=filters)
    return [_trigger_to_response(t) for t in triggers]


@router.post("/", response_model=TriggerResponse, status_code=http_status.HTTP_201_CREATED, summary="Create trigger")
async def create_trigger(
    request: TriggerCreate,
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    svc = TriggerService(db)
    trigger = await svc.create_trigger(
        organization_id=current_user.org_id,
        workflow_id=request.workflow_id,
        name=request.name,
        trigger_type=request.trigger_type,
        config=request.config,
        created_by_id=current_user.sub,
        auto_start=request.is_enabled,
    )
    return _trigger_to_response(trigger)


@router.get("/{trigger_id}", response_model=TriggerResponse, summary="Get trigger")
async def get_trigger(
    trigger_id: str,
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    svc = TriggerService(db)
    trigger = await svc.get_by_id_and_org(trigger_id, current_user.org_id)
    if not trigger:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Trigger not found")
    return _trigger_to_response(trigger)


@router.put("/{trigger_id}", response_model=TriggerResponse, summary="Update trigger")
async def update_trigger(
    trigger_id: str,
    request: TriggerUpdate,
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    svc = TriggerService(db)
    data = request.model_dump(exclude_unset=True)
    trigger = await svc.update(trigger_id, data, current_user.org_id)
    if not trigger:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Trigger not found")
    return _trigger_to_response(trigger)


@router.delete("/{trigger_id}", status_code=http_status.HTTP_204_NO_CONTENT, summary="Delete trigger")
async def delete_trigger(
    trigger_id: str,
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    svc = TriggerService(db)
    deleted = await svc.delete_trigger(trigger_id, current_user.org_id)
    if not deleted:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Trigger not found")


@router.post("/{trigger_id}/toggle", response_model=TriggerResponse, summary="Toggle trigger")
async def toggle_trigger(
    trigger_id: str,
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    svc = TriggerService(db)
    trigger = await svc.toggle(trigger_id, current_user.org_id)
    if not trigger:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Trigger not found")
    return _trigger_to_response(trigger)


# -- Action Endpoints --

@router.get("/types", summary="List supported trigger types")
async def list_trigger_types():
    manager = get_trigger_manager()
    return {"types": manager.get_supported_types()}


@router.get("/manager/status", summary="Trigger manager status")
async def get_trigger_manager_status():
    manager = get_trigger_manager()
    return manager.get_status()


@router.post("/test", summary="Test trigger config")
async def test_trigger(request: TriggerTestRequest):
    manager = get_trigger_manager()
    result = await manager.test_trigger(request.trigger_type, request.config)
    if not result.success:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=result.error or result.message)
    return {"message": result.message, "valid": True}


@router.post("/{trigger_id}/fire", summary="Manually fire a trigger")
async def fire_trigger(
    trigger_id: str,
    request: TriggerFireRequest,
    current_user: TokenPayload = Depends(get_current_active_user),
):
    manager = get_trigger_manager()
    result = await manager.fire_trigger(trigger_id, payload=request.payload)
    if not result.success:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=result.error or result.message)
    return {"message": result.message, "execution_id": result.execution_id}


# -- Webhook Receiver (unauthenticated) --

@router.post("/webhooks/{path:path}", summary="Receive webhook")
async def receive_webhook(path: str, request: Request):
    manager = get_trigger_manager()
    webhook_handler = manager._handlers.get("webhook")

    if not webhook_handler:
        raise HTTPException(status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE, detail="Webhook handler not available")

    full_path = f"/{path}" if not path.startswith("/") else path
    trigger_id = webhook_handler.get_trigger_for_path(full_path)

    if not trigger_id:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=f"No webhook for path: {full_path}")

    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")
    if not webhook_handler.verify_signature(trigger_id, body, signature):
        raise HTTPException(status_code=http_status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature")

    try:
        payload = await request.json()
    except Exception:
        payload = {"raw_body": body.decode("utf-8", errors="replace")}

    payload["_headers"] = dict(request.headers)
    payload["_method"] = request.method
    payload["_path"] = full_path

    result = await manager.fire_trigger(trigger_id, payload=payload)
    if not result.success:
        raise HTTPException(status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, detail=result.error or "Failed")

    return {"accepted": True, "execution_id": result.execution_id}
