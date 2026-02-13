"""Plugin system for extensible task types and integrations.

Allows loading custom task types from:
1. Built-in tasks (tasks/implementations/)
2. Python packages with entry points (rpa_engine.tasks)
3. Local plugin directories (plugins/)

Plugins must implement the BaseTask interface and register via entry points
or by placing a module in the plugins/ directory.

Example plugin (as a package):
    # setup.py or pyproject.toml
    [project.entry-points."rpa_engine.tasks"]
    my_custom_task = "my_package.tasks:MyCustomTask"

Example plugin (local):
    # plugins/my_plugin/tasks.py
    from tasks.base_task import BaseTask
    class MyCustomTask(BaseTask):
        type_name = "my_custom_task"
        ...
    TASK_TYPES = {"my_custom_task": MyCustomTask}
"""

import importlib
import importlib.metadata
import logging
import os
import sys
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Plugin registry
_plugins: dict[str, "PluginInfo"] = {}
_hooks: dict[str, list[callable]] = {}


class PluginInfo:
    """Metadata for a loaded plugin."""

    def __init__(
        self,
        name: str,
        version: str = "0.0.0",
        description: str = "",
        author: str = "",
        source: str = "unknown",
        task_types: Optional[dict] = None,
        hooks: Optional[dict[str, callable]] = None,
        config_schema: Optional[dict] = None,
    ):
        self.name = name
        self.version = version
        self.description = description
        self.author = author
        self.source = source  # "builtin", "entrypoint", "local"
        self.task_types = task_types or {}
        self.hooks = hooks or {}
        self.config_schema = config_schema
        self.enabled = True
        self.errors: list[str] = []


class PluginManager:
    """Manages plugin lifecycle: discovery, loading, registration."""

    ENTRY_POINT_GROUP = "rpa_engine.tasks"
    LOCAL_PLUGIN_DIR = "plugins"

    def __init__(self):
        self.plugins: dict[str, PluginInfo] = {}
        self._task_types: dict[str, Any] = {}

    def discover_and_load(self) -> dict[str, PluginInfo]:
        """Discover and load all plugins from all sources."""
        logger.info("Discovering plugins...")

        # 1. Load from entry points (installed packages)
        self._load_entrypoint_plugins()

        # 2. Load from local plugins directory
        self._load_local_plugins()

        logger.info(
            "Plugin discovery complete: %d plugins loaded, %d task types registered",
            len(self.plugins),
            len(self._task_types),
        )
        return self.plugins

    def _load_entrypoint_plugins(self):
        """Load plugins registered via Python entry points."""
        try:
            entry_points = importlib.metadata.entry_points()
            # Python 3.12+ returns a SelectableGroups
            if hasattr(entry_points, "select"):
                eps = entry_points.select(group=self.ENTRY_POINT_GROUP)
            else:
                eps = entry_points.get(self.ENTRY_POINT_GROUP, [])

            for ep in eps:
                try:
                    task_class = ep.load()
                    plugin_name = f"ep:{ep.name}"

                    plugin_info = PluginInfo(
                        name=ep.name,
                        source="entrypoint",
                        task_types={ep.name: task_class},
                    )

                    # Try to get version from package
                    if ep.dist:
                        plugin_info.version = ep.dist.version

                    self.plugins[plugin_name] = plugin_info
                    self._task_types[ep.name] = task_class
                    logger.info("Loaded entry point plugin: %s", ep.name)

                except Exception as e:
                    logger.warning("Failed to load entry point %s: %s", ep.name, e)
                    self.plugins[f"ep:{ep.name}"] = PluginInfo(
                        name=ep.name,
                        source="entrypoint",
                        errors=[str(e)],
                    )

        except Exception as e:
            logger.warning("Entry point discovery failed: %s", e)

    def _load_local_plugins(self):
        """Load plugins from the local plugins/ directory."""
        plugin_dir = Path(self.LOCAL_PLUGIN_DIR)
        if not plugin_dir.exists():
            return

        # Add plugins dir to sys.path if not already
        plugins_path = str(plugin_dir.absolute())
        if plugins_path not in sys.path:
            sys.path.insert(0, plugins_path)

        for subdir in plugin_dir.iterdir():
            if not subdir.is_dir() or subdir.name.startswith(("_", ".")):
                continue

            plugin_name = f"local:{subdir.name}"
            try:
                # Look for tasks.py or __init__.py with TASK_TYPES
                module_name = None
                if (subdir / "tasks.py").exists():
                    module_name = f"{subdir.name}.tasks"
                elif (subdir / "__init__.py").exists():
                    module_name = subdir.name

                if not module_name:
                    continue

                module = importlib.import_module(module_name)

                task_types = getattr(module, "TASK_TYPES", {})
                plugin_meta = getattr(module, "PLUGIN_META", {})

                info = PluginInfo(
                    name=plugin_meta.get("name", subdir.name),
                    version=plugin_meta.get("version", "0.0.0"),
                    description=plugin_meta.get("description", ""),
                    author=plugin_meta.get("author", ""),
                    source="local",
                    task_types=task_types,
                    hooks=getattr(module, "HOOKS", {}),
                    config_schema=getattr(module, "CONFIG_SCHEMA", None),
                )

                self.plugins[plugin_name] = info
                self._task_types.update(task_types)
                logger.info(
                    "Loaded local plugin: %s (%d task types)",
                    subdir.name,
                    len(task_types),
                )

            except Exception as e:
                logger.warning("Failed to load local plugin %s: %s", subdir.name, e)
                self.plugins[plugin_name] = PluginInfo(
                    name=subdir.name,
                    source="local",
                    errors=[str(e)],
                )

    def get_task_types(self) -> dict[str, Any]:
        """Get all registered task types from plugins."""
        return dict(self._task_types)

    def get_plugin(self, name: str) -> Optional[PluginInfo]:
        """Get plugin info by name."""
        return self.plugins.get(name)

    def list_plugins(self) -> list[dict]:
        """List all discovered plugins with status."""
        return [
            {
                "name": info.name,
                "version": info.version,
                "description": info.description,
                "author": info.author,
                "source": info.source,
                "enabled": info.enabled,
                "task_types": list(info.task_types.keys()),
                "errors": info.errors,
            }
            for info in self.plugins.values()
        ]

    def enable_plugin(self, name: str) -> bool:
        """Enable a plugin."""
        plugin = self.plugins.get(name)
        if plugin:
            plugin.enabled = True
            self._task_types.update(plugin.task_types)
            return True
        return False

    def disable_plugin(self, name: str) -> bool:
        """Disable a plugin (removes its task types from registry)."""
        plugin = self.plugins.get(name)
        if plugin:
            plugin.enabled = False
            for task_name in plugin.task_types:
                self._task_types.pop(task_name, None)
            return True
        return False


# ─── Hook system ───

def register_hook(event: str, handler: callable):
    """Register a hook handler for an event."""
    if event not in _hooks:
        _hooks[event] = []
    _hooks[event].append(handler)


async def emit_hook(event: str, **kwargs):
    """Emit a hook event, calling all registered handlers."""
    handlers = _hooks.get(event, [])
    for handler in handlers:
        try:
            import asyncio
            if asyncio.iscoroutinefunction(handler):
                await handler(**kwargs)
            else:
                handler(**kwargs)
        except Exception as e:
            logger.error("Hook handler error for %s: %s", event, e)


# Hook event constants
HOOK_WORKFLOW_STARTED = "workflow.started"
HOOK_WORKFLOW_COMPLETED = "workflow.completed"
HOOK_WORKFLOW_FAILED = "workflow.failed"
HOOK_STEP_STARTED = "step.started"
HOOK_STEP_COMPLETED = "step.completed"
HOOK_STEP_FAILED = "step.failed"
HOOK_AGENT_CONNECTED = "agent.connected"
HOOK_AGENT_DISCONNECTED = "agent.disconnected"


# Singleton
plugin_manager = PluginManager()
