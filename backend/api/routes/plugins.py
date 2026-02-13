"""Plugin management API endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.plugin_system import plugin_manager

router = APIRouter()


class PluginToggleRequest(BaseModel):
    enabled: bool


@router.get("/plugins")
async def list_plugins():
    """List all discovered plugins with their status."""
    return {"plugins": plugin_manager.list_plugins()}


@router.get("/plugins/{name}")
async def get_plugin(name: str):
    """Get detailed info about a specific plugin."""
    plugin = plugin_manager.get_plugin(name)
    if not plugin:
        raise HTTPException(404, "Plugin not found")
    return {
        "name": plugin.name,
        "version": plugin.version,
        "description": plugin.description,
        "author": plugin.author,
        "source": plugin.source,
        "enabled": plugin.enabled,
        "task_types": list(plugin.task_types.keys()),
        "config_schema": plugin.config_schema,
        "errors": plugin.errors,
    }


@router.put("/plugins/{name}")
async def toggle_plugin(name: str, body: PluginToggleRequest):
    """Enable or disable a plugin."""
    if body.enabled:
        ok = plugin_manager.enable_plugin(name)
    else:
        ok = plugin_manager.disable_plugin(name)

    if not ok:
        raise HTTPException(404, "Plugin not found")

    return {"name": name, "enabled": body.enabled}


@router.post("/plugins/reload")
async def reload_plugins():
    """Re-discover and reload all plugins."""
    plugins = plugin_manager.discover_and_load()
    return {
        "plugins_loaded": len(plugins),
        "task_types": len(plugin_manager.get_task_types()),
    }
