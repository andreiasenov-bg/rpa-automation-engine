"""Base CRUD service with soft-delete aware queries.

All service classes inherit from this. Provides standard
create/read/update/delete with automatic soft-delete filtering,
pagination, and organization scoping (multi-tenant).
"""

from typing import Any, Generic, Optional, Sequence, Type, TypeVar
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.base import BaseModel

ModelType = TypeVar("ModelType", bound=BaseModel)


class BaseService(Generic[ModelType]):
    """Generic CRUD service for any SQLAlchemy model.

    Usage:
        class UserService(BaseService[User]):
            def __init__(self, db: AsyncSession):
                super().__init__(User, db)
    """

    def __init__(self, model: Type[ModelType], db: AsyncSession):
        self.model = model
        self.db = db

    # ─── Read ──────────────────────────────────────────────

    async def get_by_id(
        self,
        id: str,
        include_deleted: bool = False,
    ) -> Optional[ModelType]:
        """Get a single record by ID."""
        query = select(self.model).where(self.model.id == id)
        if not include_deleted:
            query = query.where(self.model.is_deleted == False)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_id_and_org(
        self,
        id: str,
        organization_id: str,
        include_deleted: bool = False,
    ) -> Optional[ModelType]:
        """Get a single record scoped to an organization."""
        query = select(self.model).where(
            self.model.id == id,
            self.model.organization_id == organization_id,
        )
        if not include_deleted:
            query = query.where(self.model.is_deleted == False)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list(
        self,
        organization_id: Optional[str] = None,
        offset: int = 0,
        limit: int = 50,
        order_by: str = "created_at",
        order_desc: bool = True,
        include_deleted: bool = False,
        filters: dict[str, Any] = None,
    ) -> tuple[Sequence[ModelType], int]:
        """List records with pagination, filtering, and sorting.

        Returns:
            Tuple of (items, total_count)
        """
        query = select(self.model)
        count_query = select(func.count()).select_from(self.model)

        # Organization scope
        if organization_id and hasattr(self.model, "organization_id"):
            query = query.where(self.model.organization_id == organization_id)
            count_query = count_query.where(self.model.organization_id == organization_id)

        # Soft delete filter
        if not include_deleted:
            query = query.where(self.model.is_deleted == False)
            count_query = count_query.where(self.model.is_deleted == False)

        # Additional filters
        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field):
                    col = getattr(self.model, field)
                    if isinstance(value, list):
                        query = query.where(col.in_(value))
                        count_query = count_query.where(col.in_(value))
                    else:
                        query = query.where(col == value)
                        count_query = count_query.where(col == value)

        # Sorting
        if hasattr(self.model, order_by):
            col = getattr(self.model, order_by)
            query = query.order_by(col.desc() if order_desc else col.asc())

        # Pagination
        query = query.offset(offset).limit(limit)

        # Execute
        result = await self.db.execute(query)
        items = result.scalars().all()

        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        return items, total

    async def exists(self, id: str) -> bool:
        """Check if a record exists (not soft-deleted)."""
        query = select(func.count()).select_from(self.model).where(
            self.model.id == id,
            self.model.is_deleted == False,
        )
        result = await self.db.execute(query)
        return (result.scalar() or 0) > 0

    # ─── Create ────────────────────────────────────────────

    async def create(self, data: dict[str, Any]) -> ModelType:
        """Create a new record.

        Args:
            data: Dict of field values

        Returns:
            Created model instance
        """
        if "id" not in data:
            data["id"] = str(uuid4())

        instance = self.model(**data)
        self.db.add(instance)
        await self.db.flush()
        await self.db.refresh(instance)
        return instance

    # ─── Update ────────────────────────────────────────────

    async def update(
        self,
        id: str,
        data: dict[str, Any],
        organization_id: Optional[str] = None,
    ) -> Optional[ModelType]:
        """Update a record by ID.

        Args:
            id: Record UUID
            data: Dict of fields to update (None values are skipped)
            organization_id: Optional org scope

        Returns:
            Updated model instance or None if not found
        """
        # Filter out None values
        update_data = {k: v for k, v in data.items() if v is not None}
        if not update_data:
            return await self.get_by_id(id)

        if organization_id and hasattr(self.model, "organization_id"):
            instance = await self.get_by_id_and_org(id, organization_id)
        else:
            instance = await self.get_by_id(id)

        if not instance:
            return None

        for key, value in update_data.items():
            if hasattr(instance, key):
                setattr(instance, key, value)

        await self.db.flush()
        await self.db.refresh(instance)
        return instance

    # ─── Delete ────────────────────────────────────────────

    async def soft_delete(
        self,
        id: str,
        organization_id: Optional[str] = None,
    ) -> bool:
        """Soft-delete a record (set is_deleted=True).

        Returns:
            True if deleted, False if not found
        """
        if organization_id and hasattr(self.model, "organization_id"):
            instance = await self.get_by_id_and_org(id, organization_id)
        else:
            instance = await self.get_by_id(id)

        if not instance:
            return False

        instance.soft_delete()
        await self.db.flush()
        return True

    async def restore(self, id: str) -> Optional[ModelType]:
        """Restore a soft-deleted record.

        Returns:
            Restored instance or None
        """
        instance = await self.get_by_id(id, include_deleted=True)
        if not instance or not instance.is_deleted:
            return None

        instance.restore()
        await self.db.flush()
        await self.db.refresh(instance)
        return instance

    async def hard_delete(self, id: str) -> bool:
        """Permanently delete a record (use with caution).

        Returns:
            True if deleted, False if not found
        """
        instance = await self.get_by_id(id, include_deleted=True)
        if not instance:
            return False

        await self.db.delete(instance)
        await self.db.flush()
        return True
