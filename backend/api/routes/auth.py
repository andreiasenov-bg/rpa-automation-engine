"""Authentication endpoints — register, login, refresh, me."""

from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from core.security import (
    create_access_token,
    create_refresh_token,
    verify_token,
    TokenPayload,
)
from api.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    RefreshRequest,
    UserResponse,
)
from app.dependencies import get_db, get_current_active_user
from services.auth_service import AuthService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["authentication"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    Register a new user and create an organization.

    Returns access and refresh tokens for the newly created user.
    """
    auth_svc = AuthService(db)

    try:
        user, org = await auth_svc.register(
            email=request.email,
            password=request.password,
            first_name=request.first_name,
            last_name=request.last_name,
            organization_name=request.org_name,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )

    access_token = create_access_token(
        user_id=user.id,
        email=user.email,
        org_id=org.id,
    )
    refresh_token = create_refresh_token(
        user_id=user.id,
        email=user.email,
        org_id=org.id,
    )

    logger.info(f"New user registered: {user.email} (org: {org.slug})")

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    Authenticate user with email and password.

    Returns access and refresh tokens on success.
    """
    auth_svc = AuthService(db)
    result = await auth_svc.login(email=request.email, password=request.password)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return TokenResponse(
        access_token=result["access_token"],
        refresh_token=result["refresh_token"],
        token_type=result["token_type"],
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    Refresh access token using a valid refresh token.
    """
    try:
        token_payload = verify_token(request.refresh_token)

        if token_payload.type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type — expected refresh token",
            )

        # Verify user still exists and is active
        auth_svc = AuthService(db)
        user = await auth_svc.get_user_by_id(token_payload.sub)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or deactivated",
            )

        access_token = create_access_token(
            user_id=token_payload.sub,
            email=token_payload.email,
            org_id=token_payload.org_id,
        )
        new_refresh = create_refresh_token(
            user_id=token_payload.sub,
            email=token_payload.email,
            org_id=token_payload.org_id,
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh,
            token_type="bearer",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token refresh failed",
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """
    Get current authenticated user's full profile.
    """
    auth_svc = AuthService(db)
    user = await auth_svc.get_user_by_id(current_user.sub)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return UserResponse(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        org_id=user.organization_id,
        is_active=user.is_active,
        roles=[r.name for r in user.roles] if user.roles else [],
        created_at=user.created_at,
    )
