"""User service — CRUD and organization-scoped user management."""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.user import User
from services.base import BaseService


class UserService(BaseService[User]):
    """Service for user management within an organization."""

    def __init__(self, db: AsyncSession):
        super().__init__(User, db)

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get a user by email (cross-org)."""
        result = await self.db.execute(
            select(User).where(User.email == email, User.is_deleted == False)
        )
        return result.scalar_one_or_none()

    async def list_by_org(
        self,
        organization_id: str,
        offset: int = 0,
        limit: int = 50,
    ):
        """List users in an organization."""
        return await self.list(
            organization_id=organization_id,
            offset=offset,
            limit=limit,
        )

    async def deactivate(self, user_id: str, organization_id: str) -> bool:
        """Deactivate a user (soft-delete)."""
        return await self.soft_delete(user_id, organization_id)

    async def update_profile(
        self,
        user_id: str,
        organization_id: str,
        data: dict,
    ) -> Optional[User]:
        """Update user profile fields (only safe fields)."""
        allowed_fields = {"first_name", "last_name", "is_active"}
        safe_data = {k: v for k, v in data.items() if k in allowed_fields}
        if not safe_data:
            return await self.get_by_id_and_org(user_id, organization_id)
        return await self.update(user_id, safe_data, organization_id)
