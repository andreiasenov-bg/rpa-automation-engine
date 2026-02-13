"""FastAPI dependency injection functions."""

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from core.security import get_current_user, TokenPayload
from db.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


async def get_db() -> AsyncSession:
    """
    Provide a database session for API endpoints.

    Yields an async SQLAlchemy session that is automatically
    committed on success or rolled back on error.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
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
    Get the current authenticated user and verify they are active in the DB.

    Checks that the user's account exists and is not deactivated.

    Returns:
        Current user token payload (with verified active status)

    Raises:
        HTTPException: If user is not found or not active
    """
    from db.models.user import User

    result = await db.execute(
        select(User.is_active).where(
            User.id == current_user.sub,
            User.is_deleted == False,
        )
    )
    row = result.first()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if not row[0]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    return current_user
