"""Authentication endpoints."""

from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token,
    get_current_user,
    TokenPayload,
)
from api.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    RefreshRequest,
    UserResponse,
)
from app.dependencies import get_db
from core.utils import utc_now

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    Authenticate user with email and password.

    Args:
        request: Login credentials (email, password)
        db: Database session

    Returns:
        Access and refresh tokens

    Raises:
        HTTPException: If credentials are invalid
    """
    # TODO: Implement actual user lookup from database
    # This is a placeholder implementation
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials",
    )


@router.post("/register", response_model=TokenResponse)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    Register a new user and create organization.

    Creates a new organization and user, returns authentication tokens.

    Args:
        request: Registration details (email, password, name, org_name)
        db: Database session

    Returns:
        Access and refresh tokens

    Raises:
        HTTPException: If email already exists or validation fails
    """
    # TODO: Implement actual user and organization creation
    # This is a placeholder implementation
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Registration not yet implemented",
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    Refresh access token using refresh token.

    Args:
        request: Refresh token
        db: Database session

    Returns:
        New access and refresh tokens

    Raises:
        HTTPException: If refresh token is invalid or expired
    """
    try:
        token_payload = verify_token(request.refresh_token)

        if token_payload.type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )

        # TODO: Verify refresh token has not been revoked
        # Generate new tokens
        access_token = create_access_token(
            user_id=token_payload.sub,
            email=token_payload.email,
            org_id=token_payload.org_id,
        )
        refresh_token_new = create_refresh_token(
            user_id=token_payload.sub,
            email=token_payload.email,
            org_id=token_payload.org_id,
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token_new,
            token_type="bearer",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token refresh failed",
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """
    Get current authenticated user information.

    Args:
        current_user: Current user from JWT token
        db: Database session

    Returns:
        Current user information

    Raises:
        HTTPException: If user not found
    """
    # TODO: Fetch full user details from database
    # This is a placeholder implementation
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User not found",
    )
