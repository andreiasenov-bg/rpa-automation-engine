"""Credential vault management endpoints.

Full CRUD with AES-256 encryption/decryption via CredentialVault.
Credential *values* are never returned unless explicitly requested
via GET /{credential_id} (which is audit-logged).
"""

from typing import Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, status, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from core.security import TokenPayload, vault
from core.constants import CredentialType
from app.dependencies import get_db, get_current_active_user
from db.models.credential import Credential
from db.models.audit_log import AuditLog

logger = logging.getLogger(__name__)

router = APIRouter(tags=["credentials"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class CredentialCreateRequest(BaseModel):
    """Request body to create a credential."""
    name: str = Field(..., min_length=1, max_length=255)
    credential_type: str = Field(
        default=CredentialType.API_KEY.value,
        description="One of: api_key, oauth2, basic_auth, database, private_key, custom",
    )
    value: str = Field(..., min_length=1, description="Plain-text credential value (will be encrypted)")
    extra_data: Optional[dict] = Field(default=None, description="Optional JSON metadata")


class CredentialUpdateRequest(BaseModel):
    """Request body to update a credential."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    credential_type: Optional[str] = None
    value: Optional[str] = Field(default=None, min_length=1, description="New plain-text value (re-encrypted)")
    extra_data: Optional[dict] = None


class CredentialResponse(BaseModel):
    """Public representation of a credential (value excluded by default)."""
    id: str
    name: str
    credential_type: str
    extra_data: Optional[dict] = None
    created_by_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CredentialDetailResponse(CredentialResponse):
    """Credential with decrypted value (only returned on GET /{id})."""
    value: Optional[str] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_response(cred: Credential, *, include_value: bool = False) -> dict:
    """Convert a Credential ORM instance to a response dict."""
    data = {
        "id": cred.id,
        "name": cred.name,
        "credential_type": cred.credential_type,
        "extra_data": cred.extra_data,
        "created_by_id": cred.created_by_id,
        "created_at": cred.created_at.isoformat() if cred.created_at else None,
        "updated_at": cred.updated_at.isoformat() if cred.updated_at else None,
    }
    if include_value:
        try:
            data["value"] = vault.decrypt(cred.encrypted_value)
        except Exception:
            data["value"] = None  # decryption key rotated / corrupted
    return data


async def _audit(
    db: AsyncSession,
    *,
    user_id: str,
    org_id: str,
    action: str,
    resource_type: str = "credential",
    resource_id: str,
    details: Optional[dict] = None,
) -> None:
    """Write an audit-log entry."""
    try:
        entry = AuditLog(
            organization_id=org_id,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
        )
        db.add(entry)
        # commit handled by the dependency's context manager
    except Exception as exc:
        logger.warning(f"Audit log write failed: {exc}")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/")
async def list_credentials(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None, description="Filter by name (case-insensitive)"),
    credential_type: Optional[str] = Query(None, description="Filter by credential type"),
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List credentials in the organisation (values excluded)."""
    org_id = current_user.org_id
    base = and_(
        Credential.organization_id == org_id,
        Credential.is_deleted == False,
    )

    # Optional filters
    filters = [base]
    if search:
        filters.append(Credential.name.ilike(f"%{search}%"))
    if credential_type:
        filters.append(Credential.credential_type == credential_type)

    where = and_(*filters)

    total = await db.scalar(select(func.count(Credential.id)).where(where)) or 0

    stmt = (
        select(Credential)
        .where(where)
        .order_by(Credential.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await db.execute(stmt)
    rows = result.scalars().all()

    return {
        "items": [_to_response(c) for c in rows],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page if per_page else 0,
    }


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_credential(
    request: CredentialCreateRequest,
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create a new credential (value is encrypted before storage)."""
    org_id = current_user.org_id

    # Validate credential type
    valid_types = {t.value for t in CredentialType}
    if request.credential_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid credential_type. Must be one of: {', '.join(sorted(valid_types))}",
        )

    # Check for duplicate name in org
    existing = await db.scalar(
        select(func.count(Credential.id)).where(
            and_(
                Credential.organization_id == org_id,
                Credential.name == request.name,
                Credential.is_deleted == False,
            )
        )
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Credential with name '{request.name}' already exists",
        )

    encrypted_value = vault.encrypt(request.value)

    credential = Credential(
        organization_id=org_id,
        created_by_id=current_user.sub,
        name=request.name,
        credential_type=request.credential_type,
        encrypted_value=encrypted_value,
        extra_data=request.extra_data,
    )
    db.add(credential)
    await db.flush()  # populate .id

    await _audit(
        db,
        user_id=current_user.sub,
        org_id=org_id,
        action="create",
        resource_id=credential.id,
        details={"name": request.name, "type": request.credential_type},
    )

    return _to_response(credential)


@router.get("/{credential_id}")
async def get_credential(
    credential_id: str,
    include_value: bool = Query(False, description="Include decrypted value (audit-logged)"),
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get credential details. When include_value=true the decrypted value is returned and the access is audit-logged."""
    org_id = current_user.org_id

    result = await db.execute(
        select(Credential).where(
            and_(
                Credential.id == credential_id,
                Credential.organization_id == org_id,
                Credential.is_deleted == False,
            )
        )
    )
    credential = result.scalar_one_or_none()
    if not credential:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credential not found")

    if include_value:
        await _audit(
            db,
            user_id=current_user.sub,
            org_id=org_id,
            action="read",
            resource_id=credential_id,
            details={"decrypted": True},
        )

    return _to_response(credential, include_value=include_value)


@router.put("/{credential_id}")
async def update_credential(
    credential_id: str,
    request: CredentialUpdateRequest,
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Update a credential. If value is provided it is re-encrypted."""
    org_id = current_user.org_id

    result = await db.execute(
        select(Credential).where(
            and_(
                Credential.id == credential_id,
                Credential.organization_id == org_id,
                Credential.is_deleted == False,
            )
        )
    )
    credential = result.scalar_one_or_none()
    if not credential:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credential not found")

    changes: dict = {}
    if request.name is not None and request.name != credential.name:
        # Check duplicate
        dup = await db.scalar(
            select(func.count(Credential.id)).where(
                and_(
                    Credential.organization_id == org_id,
                    Credential.name == request.name,
                    Credential.id != credential_id,
                    Credential.is_deleted == False,
                )
            )
        )
        if dup:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Credential with name '{request.name}' already exists",
            )
        credential.name = request.name
        changes["name"] = request.name

    if request.credential_type is not None:
        valid_types = {t.value for t in CredentialType}
        if request.credential_type not in valid_types:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid credential_type. Must be one of: {', '.join(sorted(valid_types))}",
            )
        credential.credential_type = request.credential_type
        changes["credential_type"] = request.credential_type

    if request.value is not None:
        credential.encrypted_value = vault.encrypt(request.value)
        changes["value_rotated"] = True

    if request.extra_data is not None:
        credential.extra_data = request.extra_data
        changes["extra_data_updated"] = True

    await db.flush()

    await _audit(
        db,
        user_id=current_user.sub,
        org_id=org_id,
        action="update",
        resource_id=credential_id,
        details=changes,
    )

    return _to_response(credential)


@router.delete("/{credential_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_credential(
    credential_id: str,
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft-delete a credential."""
    org_id = current_user.org_id

    result = await db.execute(
        select(Credential).where(
            and_(
                Credential.id == credential_id,
                Credential.organization_id == org_id,
                Credential.is_deleted == False,
            )
        )
    )
    credential = result.scalar_one_or_none()
    if not credential:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credential not found")

    credential.is_deleted = True

    await _audit(
        db,
        user_id=current_user.sub,
        org_id=org_id,
        action="delete",
        resource_id=credential_id,
        details={"name": credential.name},
    )
