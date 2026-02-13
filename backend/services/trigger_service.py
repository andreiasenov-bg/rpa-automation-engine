"""Trigger service — CRUD for triggers with manager integration."""

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from db.models.trigger import Trigger
from services.base import BaseService
from triggers.manager import get_trigger_manager


class TriggerService(BaseService[Trigger]):
    """Service for trigger management."""

    def __init__(self, db: AsyncSession):
        super().__init__(Trigger, db)

    async def create_trigger(
        self,
        organization_id: str,
        workflow_id: str,
        name: str,
        trigger_type: str,
        config: dict = None,
        created_by_id: str = None,
        auto_start: bool = True,
    ) -> Trigger:
        """Create a new trigger and optionally start it."""
        trigger = await self.create({
            "organization_id": organization_id,
            "workflow_id": workflow_id,
            "name": name,
            "trigger_type": trigger_type,
            "config": config or {},
            "created_by_id": created_by_id,
            "is_enabled": True,
        })

        if auto_start:
            manager = get_trigger_manager()
            await manager.start_trigger(
                trigger_id=trigger.id,
                trigger_type=trigger_type,
                config=config or {},
                workflow_id=workflow_id,
                organization_id=organization_id,
            )

        return trigger

    async def toggle(self, trigger_id: str, organization_id: str) -> Optional[Trigger]:
        """Toggle a trigger on/off."""
        trigger = await self.get_by_id_and_org(trigger_id, organization_id)
        if not trigger:
            return None

        manager = get_trigger_manager()

        if trigger.is_enabled:
            await manager.stop_trigger(trigger_id)
            trigger.is_enabled = False
        else:
            await manager.start_trigger(
                trigger_id=trigger.id,
                trigger_type=trigger.trigger_type,
                config=trigger.config or {},
                workflow_id=trigger.workflow_id,
                organization_id=trigger.organization_id,
            )
            trigger.is_enabled = True

        await self.db.flush()
        await self.db.refresh(trigger)
        return trigger

    async def delete_trigger(self, trigger_id: str, organization_id: str) -> bool:
        """Soft-delete a trigger and stop it."""
        manager = get_trigger_manager()
        await manager.stop_trigger(trigger_id)
        return await self.soft_delete(trigger_id, organization_id)
