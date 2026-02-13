"""
Base task interface for all RPA task implementations.

Every task type (web scraping, AI analysis, form filling, etc.)
must inherit from BaseTask and implement the execute() method.
"""

import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import structlog

logger = structlog.get_logger(__name__)


class TaskResult:
    """Standardized result from task execution."""

    def __init__(
        self,
        success: bool,
        output: Any = None,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        duration_ms: float = 0,
    ):
        self.success = success
        self.output = output
        self.error = error
        self.metadata = metadata or {}
        self.duration_ms = duration_ms
        self.timestamp = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "metadata": self.metadata,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp.isoformat(),
        }


class BaseTask(ABC):
    """
    Abstract base class for all RPA task implementations.

    Subclasses must implement:
    - execute(config, context) -> TaskResult
    - task_type (class property)
    - display_name (class property)
    """

    task_type: str = "base"
    display_name: str = "Base Task"
    description: str = "Abstract base task"
    icon: str = "⚙️"

    @abstractmethod
    async def execute(
        self,
        config: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> TaskResult:
        """
        Execute the task with given configuration.

        Args:
            config: Task-specific configuration (from workflow step)
            context: Execution context (variables from previous steps, credentials, etc.)

        Returns:
            TaskResult with output or error
        """
        pass

    async def run(
        self,
        config: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> TaskResult:
        """
        Run the task with timing and error handling.

        This is the main entry point called by the workflow engine.
        """
        start = time.monotonic()
        try:
            logger.info(
                "Task starting",
                task_type=self.task_type,
                task_name=self.display_name,
            )
            result = await self.execute(config, context or {})
            result.duration_ms = (time.monotonic() - start) * 1000

            logger.info(
                "Task completed",
                task_type=self.task_type,
                success=result.success,
                duration_ms=round(result.duration_ms, 2),
            )
            return result

        except Exception as e:
            duration_ms = (time.monotonic() - start) * 1000
            logger.error(
                "Task failed",
                task_type=self.task_type,
                error=str(e),
                duration_ms=round(duration_ms, 2),
            )
            return TaskResult(
                success=False,
                error=str(e),
                duration_ms=duration_ms,
            )

    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """
        Return JSON schema for task configuration.

        Override in subclasses to define expected config shape.
        """
        return {"type": "object", "properties": {}}
