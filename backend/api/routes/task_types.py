"""Task Types API routes.

Exposes available task types to the frontend for workflow editor.
"""

from fastapi import APIRouter

from tasks.registry import get_task_registry

router = APIRouter()


@router.get("/", summary="List all available task types")
async def list_task_types():
    """Get all registered task types with their schemas.

    Used by the visual workflow editor to populate the step palette.
    """
    registry = get_task_registry()
    return {
        "task_types": registry.list_all(),
        "count": len(registry.available_types),
    }


@router.get("/{task_type}", summary="Get task type details")
async def get_task_type(task_type: str):
    """Get details and config schema for a specific task type."""
    registry = get_task_registry()
    task_class = registry.get(task_type)
    if not task_class:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown task type: {task_type}",
        )
    return {
        "task_type": task_class.task_type,
        "display_name": task_class.display_name,
        "description": task_class.description,
        "icon": task_class.icon,
        "config_schema": task_class.get_config_schema(),
    }
