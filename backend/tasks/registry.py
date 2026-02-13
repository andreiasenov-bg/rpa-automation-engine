"""
Task Type Registry — Central registry for all available RPA task types.

Maintains a mapping of task_type strings to their implementations.
New task types are automatically discovered and registered.
"""

from typing import Dict, Optional, Type

from tasks.base_task import BaseTask
from tasks.implementations.ai_task import AI_TASK_TYPES
from tasks.implementations.integration_task import INTEGRATION_TASK_TYPES
from tasks.implementations.http_task import HTTP_TASK_TYPES
from tasks.implementations.script_task import SCRIPT_TASK_TYPES
from tasks.implementations.browser_task import BROWSER_TASK_TYPES


class TaskRegistry:
    """Central registry for all task type implementations."""

    def __init__(self):
        self._tasks: Dict[str, Type[BaseTask]] = {}
        self._register_builtin_tasks()

    def _register_builtin_tasks(self):
        """Register all built-in task types."""
        # AI-powered tasks
        for task_type, task_class in AI_TASK_TYPES.items():
            self.register(task_type, task_class)

        # Integration tasks (external APIs)
        for task_type, task_class in INTEGRATION_TASK_TYPES.items():
            self.register(task_type, task_class)

        # HTTP tasks
        for task_type, task_class in HTTP_TASK_TYPES.items():
            self.register(task_type, task_class)

        # Script & data tasks
        for task_type, task_class in SCRIPT_TASK_TYPES.items():
            self.register(task_type, task_class)

        # Browser automation tasks (Playwright)
        for task_type, task_class in BROWSER_TASK_TYPES.items():
            self.register(task_type, task_class)

    def register(self, task_type: str, task_class: Type[BaseTask]):
        """Register a new task type."""
        self._tasks[task_type] = task_class

    def get(self, task_type: str) -> Optional[Type[BaseTask]]:
        """Get a task class by type string."""
        return self._tasks.get(task_type)

    def create_instance(self, task_type: str) -> Optional[BaseTask]:
        """Create a new instance of a task by type."""
        task_class = self.get(task_type)
        if task_class:
            return task_class()
        return None

    def list_all(self) -> list:
        """List all registered task types with metadata."""
        return [
            {
                "task_type": task_type,
                "display_name": cls.display_name,
                "description": cls.description,
                "icon": cls.icon,
                "config_schema": cls.get_config_schema(),
            }
            for task_type, cls in self._tasks.items()
        ]

    @property
    def available_types(self) -> list:
        return list(self._tasks.keys())


# Singleton
_registry: Optional[TaskRegistry] = None


def get_task_registry() -> TaskRegistry:
    """Get or create the singleton task registry."""
    global _registry
    if _registry is None:
        _registry = TaskRegistry()
    return _registry
