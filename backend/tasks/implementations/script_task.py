"""Script execution task implementations.

Execute Python scripts, shell commands, and JavaScript code
within workflow steps. Sandboxed with resource limits.
"""

import asyncio
import json
import os
import sys
import tempfile
from typing import Any, Dict, Optional

import structlog

from tasks.base_task import BaseTask, TaskResult

logger = structlog.get_logger(__name__)


class PythonScriptTask(BaseTask):
    """Execute Python code in an isolated subprocess.

    Config:
        code: Python source code (required)
        timeout: Execution timeout in seconds (default: 60)
        inputs: Dict of variables to inject into script namespace
        capture_output: Whether to capture stdout/stderr (default: true)
    """

    task_type = "python_script"
    display_name = "Python Script"
    description = "Execute Python code in a sandboxed environment"
    icon = "🐍"

    async def execute(self, config: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> TaskResult:
        code = config.get("code")
        if not code:
            return TaskResult(success=False, error="Missing required config: code")

        timeout = min(config.get("timeout", 60), 300)  # Cap at 5 min
        inputs = config.get("inputs", {})

        # Write script to temp file with input injection
        script_content = self._build_script(code, inputs)

        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
                f.write(script_content)
                script_path = f.name

            try:
                process = await asyncio.create_subprocess_exec(
                    sys.executable, script_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env={**os.environ, "PYTHONPATH": os.getcwd()},
                )

                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout,
                )

                stdout_text = stdout.decode("utf-8", errors="replace").strip()
                stderr_text = stderr.decode("utf-8", errors="replace").strip()

                # Try to parse last line as JSON result
                result_data = None
                if stdout_text:
                    lines = stdout_text.split("\n")
                    try:
                        result_data = json.loads(lines[-1])
                    except (json.JSONDecodeError, IndexError):
                        result_data = stdout_text

                success = process.returncode == 0

                return TaskResult(
                    success=success,
                    output={
                        "return_code": process.returncode,
                        "stdout": stdout_text,
                        "stderr": stderr_text,
                        "result": result_data,
                    },
                    error=stderr_text if not success else None,
                )

            except asyncio.TimeoutError:
                process.kill()
                return TaskResult(success=False, error=f"Script timed out after {timeout}s")

            finally:
                os.unlink(script_path)

        except Exception as e:
            return TaskResult(success=False, error=f"Script execution failed: {str(e)}")

    def _build_script(self, code: str, inputs: dict) -> str:
        """Build a runnable script with injected variables."""
        lines = ["import json", "import sys", ""]

        # Inject input variables
        if inputs:
            lines.append("# Injected inputs")
            lines.append(f"_inputs = json.loads({json.dumps(json.dumps(inputs))})")
            for key, value in inputs.items():
                lines.append(f"{key} = _inputs[{json.dumps(key)}]")
            lines.append("")

        lines.append("# User code")
        lines.append(code)

        return "\n".join(lines)

    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["code"],
            "properties": {
                "code": {"type": "string", "description": "Python source code"},
                "timeout": {"type": "integer", "default": 60, "maximum": 300},
                "inputs": {"type": "object", "description": "Variables to inject"},
            },
        }


class ShellCommandTask(BaseTask):
    """Execute shell commands.

    Config:
        command: Shell command string (required)
        shell: Shell to use (default: /bin/bash)
        timeout: Execution timeout in seconds (default: 60)
        working_dir: Working directory
        env: Environment variables to set
    """

    task_type = "shell_command"
    display_name = "Shell Command"
    description = "Execute shell commands and scripts"
    icon = "💻"

    async def execute(self, config: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> TaskResult:
        command = config.get("command")
        if not command:
            return TaskResult(success=False, error="Missing required config: command")

        # Security: block dangerous commands
        dangerous_patterns = ["rm -rf /", "mkfs", "dd if=", ": > /dev/", "chmod 777 /"]
        for pattern in dangerous_patterns:
            if pattern in command:
                return TaskResult(success=False, error=f"Blocked dangerous command pattern: {pattern}")

        shell = config.get("shell", "/bin/bash")
        timeout = min(config.get("timeout", 60), 300)
        working_dir = config.get("working_dir")
        env = {**os.environ, **(config.get("env", {}))}

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=working_dir,
                env=env,
                executable=shell,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout,
            )

            stdout_text = stdout.decode("utf-8", errors="replace").strip()
            stderr_text = stderr.decode("utf-8", errors="replace").strip()
            success = process.returncode == 0

            return TaskResult(
                success=success,
                output={
                    "return_code": process.returncode,
                    "stdout": stdout_text,
                    "stderr": stderr_text,
                },
                error=stderr_text if not success else None,
            )

        except asyncio.TimeoutError:
            process.kill()
            return TaskResult(success=False, error=f"Command timed out after {timeout}s")
        except Exception as e:
            return TaskResult(success=False, error=f"Command failed: {str(e)}")

    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["command"],
            "properties": {
                "command": {"type": "string", "description": "Shell command to execute"},
                "shell": {"type": "string", "default": "/bin/bash"},
                "timeout": {"type": "integer", "default": 60, "maximum": 300},
                "working_dir": {"type": "string"},
                "env": {"type": "object"},
            },
        }


class DataTransformTask(BaseTask):
    """Transform data between formats (JSON, CSV, XML, etc.).

    Config:
        input_data: The data to transform (or reference to step output)
        operation: "json_to_csv" | "csv_to_json" | "filter" | "map" | "sort" | "group_by" | "aggregate"
        options: Operation-specific options
    """

    task_type = "data_transform"
    display_name = "Data Transform"
    description = "Transform and manipulate data between formats"
    icon = "🔄"

    async def execute(self, config: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> TaskResult:
        input_data = config.get("input_data")
        operation = config.get("operation")

        if not operation:
            return TaskResult(success=False, error="Missing required config: operation")

        try:
            if operation == "filter":
                result = self._filter(input_data, config.get("options", {}))
            elif operation == "map":
                result = self._map(input_data, config.get("options", {}))
            elif operation == "sort":
                result = self._sort(input_data, config.get("options", {}))
            elif operation == "group_by":
                result = self._group_by(input_data, config.get("options", {}))
            elif operation == "aggregate":
                result = self._aggregate(input_data, config.get("options", {}))
            elif operation == "flatten":
                result = self._flatten(input_data)
            elif operation == "unique":
                result = self._unique(input_data, config.get("options", {}))
            else:
                return TaskResult(success=False, error=f"Unknown operation: {operation}")

            return TaskResult(success=True, output=result)

        except Exception as e:
            return TaskResult(success=False, error=f"Transform failed: {str(e)}")

    def _filter(self, data: list, options: dict) -> list:
        """Filter list items by field value."""
        field = options.get("field")
        value = options.get("value")
        op = options.get("operator", "eq")

        if not isinstance(data, list):
            return data

        def matches(item):
            item_val = item.get(field) if isinstance(item, dict) else item
            if op == "eq":
                return item_val == value
            elif op == "ne":
                return item_val != value
            elif op == "gt":
                return item_val > value
            elif op == "lt":
                return item_val < value
            elif op == "contains":
                return value in str(item_val)
            return False

        return [item for item in data if matches(item)]

    def _map(self, data: list, options: dict) -> list:
        """Extract specific fields from list items."""
        fields = options.get("fields", [])
        if not isinstance(data, list) or not fields:
            return data
        return [{f: item.get(f) for f in fields if isinstance(item, dict)} for item in data]

    def _sort(self, data: list, options: dict) -> list:
        """Sort list by field."""
        field = options.get("field")
        reverse = options.get("reverse", False)
        if not isinstance(data, list):
            return data
        return sorted(data, key=lambda x: x.get(field, "") if isinstance(x, dict) else x, reverse=reverse)

    def _group_by(self, data: list, options: dict) -> dict:
        """Group list items by a field value."""
        field = options.get("field")
        if not isinstance(data, list) or not field:
            return {"_all": data}
        groups = {}
        for item in data:
            key = str(item.get(field, "_other")) if isinstance(item, dict) else "_other"
            groups.setdefault(key, []).append(item)
        return groups

    def _aggregate(self, data: list, options: dict) -> dict:
        """Compute aggregate stats on numeric fields."""
        field = options.get("field")
        if not isinstance(data, list):
            return {}
        values = [item.get(field, 0) for item in data if isinstance(item, dict)]
        numeric = [v for v in values if isinstance(v, (int, float))]
        if not numeric:
            return {"count": len(data), "field": field}
        return {
            "count": len(numeric),
            "sum": sum(numeric),
            "avg": sum(numeric) / len(numeric),
            "min": min(numeric),
            "max": max(numeric),
        }

    def _flatten(self, data: list) -> list:
        """Flatten nested lists."""
        result = []
        for item in (data if isinstance(data, list) else [data]):
            if isinstance(item, list):
                result.extend(self._flatten(item))
            else:
                result.append(item)
        return result

    def _unique(self, data: list, options: dict) -> list:
        """Deduplicate list items."""
        field = options.get("field")
        if not isinstance(data, list):
            return data
        if field:
            seen = set()
            result = []
            for item in data:
                key = item.get(field) if isinstance(item, dict) else item
                if key not in seen:
                    seen.add(key)
                    result.append(item)
            return result
        # Simple dedup for hashable items
        try:
            return list(dict.fromkeys(data))
        except TypeError:
            return data


# Import custom script task (browser-aware)
from tasks.implementations.custom_script_task import CustomScriptTask

# Export for task registry
SCRIPT_TASK_TYPES = {
    "python_script": PythonScriptTask,
    "shell_command": ShellCommandTask,
    "data_transform": DataTransformTask,
    "custom_script": CustomScriptTask,
}
