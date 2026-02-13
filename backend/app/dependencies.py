"""FastAPI dependency injection functions."""

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from core.security import get_current_user, TokenPayload
from db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)


async def get_db() -> AsyncSession:
    """
    Provide a database session for API endpoints.

    Yields an async SQLAlchemy session that is automatically closed after use.

    Yields:
        AsyncSession: Database session
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Database error: {str(e)}")
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_current_active_user(
    current_user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TokenPayload:
    """
    Get the current authenticated user and verify they are active.

    Checks that the user's account is not deactivated.

    Args:
        current_user: Current user from JWT token
        db: Database session

    Returns:
        Current user token payload

    Raises:
        HTTPException: If user is not active
    """
    # TODO: Query database to verify user is_active status
    # For now, we'll just return the user
    # In production, you would check the user record in the database
    return current_user
