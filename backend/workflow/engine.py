"""Workflow Execution Engine — DAG-based workflow runner.

This is the core of the RPA platform. It takes a workflow definition
(a DAG of steps) and executes them in order, handling:

- Sequential and parallel execution
- Conditional branching (if/else/switch)
- Loops (for-each, while, repeat)
- Error handling (try/catch/finally per step)
- Retry with exponential backoff
- Timeout per step and per workflow
- Variable passing between steps (context)
- Checkpoint/resume after crash
- Real-time progress via WebSocket

Workflow Definition Schema (stored in Workflow.definition JSON):
{
    "version": "1.0",
    "variables": { "input_file": "", "output_dir": "" },
    "steps": [
        {
            "id": "step_1",
            "type": "http_request",
            "name": "Fetch data",
            "config": { "url": "...", "method": "GET" },
            "next": ["step_2"],
            "on_error": "step_error_handler",
            "timeout": 30,
            "retry": { "max_attempts": 3, "backoff": "exponential" }
        },
        {
            "id": "step_2",
            "type": "condition",
            "name": "Check response",
            "config": { "expression": "{{ steps.step_1.status_code == 200 }}" },
            "branches": {
                "true": ["step_3"],
                "false": ["step_error_handler"]
            }
        },
        {
            "id": "step_3",
            "type": "foreach",
            "name": "Process items",
            "config": { "collection": "{{ steps.step_1.data.items }}" },
            "body": ["step_3a", "step_3b"],
            "next": ["step_4"]
        },
        ...
    ]
}
"""

import asyncio
import logging
import sys

sys.setrecursionlimit(5000)
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


# ─── Step Status ──────────────────────────────────────────────

class StepStatus(str, Enum):
    """Status of a single workflow step execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"
    WAITING = "waiting"  # Waiting for parallel branches


# ─── Execution Context ────────────────────────────────────────

@dataclass
class StepResult:
    """Result of executing a single step."""
    step_id: str
    status: StepStatus
    output: Any = None
    error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_ms: int = 0
    retry_count: int = 0


@dataclass
class ExecutionContext:
    """Shared context passed through the entire workflow execution.

    Holds variables, step results, and execution metadata.
    All steps can read/write to this context.
    """

    execution_id: str
    workflow_id: str
    organization_id: str
    variables: dict[str, Any] = field(default_factory=dict)
    steps: dict[str, StepResult] = field(default_factory=dict)
    trigger_payload: dict[str, Any] = field(default_factory=dict)
    current_step_id: Optional[str] = None
    parent_step_id: Optional[str] = None  # For nested loops
    loop_index: int = 0
    loop_item: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def set_variable(self, key: str, value: Any) -> None:
        """Set a workflow variable."""
        self.variables[key] = value

    def get_variable(self, key: str, default: Any = None) -> Any:
        """Get a workflow variable."""
        return self.variables.get(key, default)

    def get_step_output(self, step_id: str) -> Any:
        """Get the output of a previously executed step."""
        result = self.steps.get(step_id)
        return result.output if result else None

    def to_dict(self) -> dict:
        """Serialize context for checkpoint persistence."""
        return {
            "execution_id": self.execution_id,
            "workflow_id": self.workflow_id,
            "organization_id": self.organization_id,
            "variables": self.variables,
            "steps": {
                sid: {
                    "step_id": r.step_id,
                    "status": r.status.value,
                    "output": r.output,
                    "error": r.error,
                    "started_at": r.started_at,
                    "completed_at": r.completed_at,
                    "duration_ms": r.duration_ms,
                    "retry_count": r.retry_count,
                }
                for sid, r in self.steps.items()
            },
            "trigger_payload": self.trigger_payload,
            "current_step_id": self.current_step_id,
            "loop_index": self.loop_index,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ExecutionContext":
        """Restore context from checkpoint."""
        ctx = cls(
            execution_id=data["execution_id"],
            workflow_id=data["workflow_id"],
            organization_id=data["organization_id"],
            variables=data.get("variables", {}),
            trigger_payload=data.get("trigger_payload", {}),
            current_step_id=data.get("current_step_id"),
            loop_index=data.get("loop_index", 0),
        )
        for sid, sdata in data.get("steps", {}).items():
            ctx.steps[sid] = StepResult(
                step_id=sdata["step_id"],
                status=StepStatus(sdata["status"]),
                output=sdata.get("output"),
                error=sdata.get("error"),
                started_at=sdata.get("started_at"),
                completed_at=sdata.get("completed_at"),
                duration_ms=sdata.get("duration_ms", 0),
                retry_count=sdata.get("retry_count", 0),
            )
        return ctx


# ─── Expression Evaluator ─────────────────────────────────────

class _DotDict(dict):
    """Dict that supports attribute-style access for eval expressions.
    Handles step ID mismatches: step-1 vs step_1."""
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            alt = name.replace('_', '-')
            if alt in self:
                return self[alt]
            raise AttributeError(f"No key '{name}' or '{alt}'")

    def __setattr__(self, name, value):
        self[name] = value


def _make_dot_dict(obj, _depth=0, _max_depth=50):
    """Recursively convert dicts to _DotDict for eval-friendly access."""
    if _depth >= _max_depth:
        return obj
    if isinstance(obj, dict) and not isinstance(obj, _DotDict):
        return _DotDict({k: _make_dot_dict(v, _depth + 1, _max_depth) for k, v in obj.items()})
    elif isinstance(obj, list):
        return [_make_dot_dict(item, _depth + 1, _max_depth) for item in obj]
    return obj


class ExpressionEvaluator:
    """Evaluates template expressions like {{ steps.step_1.output.name }}.

    Supports:
    - Variable references: {{ variables.input_file }}
    - Step output references: {{ steps.step_1.categories }}
    - Trigger data: {{ trigger.payload.order_id }}
    - Loop data: {{ loop.index }}, {{ loop.item }}
    - Comparisons: {{ steps.step_1.status_code == 200 }}
    - List slicing: {{ steps.step_1.categories[0:5] }}
    - Builtins: not, len, True, False, None
    """

    @staticmethod
    def evaluate(expression: str, context: ExecutionContext) -> Any:
        """Evaluate a template expression against the execution context."""
        if not isinstance(expression, str):
            return expression

        # Strip {{ }} markers
        expr = expression.strip()
        if expr.startswith("{{") and expr.endswith("}}"):
            expr = expr[2:-2].strip()
        elif "{{" not in expr:
            return expression  # Not a template expression

        # Build evaluation namespace with DotDict for attribute access
        steps_ns = _DotDict()
        for sid, result in context.steps.items():
            step_data = _DotDict({
                "output": _make_dot_dict(result.output) if result.output else None,
                "status": result.status.value if hasattr(result.status, 'value') else str(result.status),
                "error": result.error,
                "duration_ms": result.duration_ms,
            })
            # Flatten output fields to step level for convenience:
            # steps.step_1.categories instead of steps.step_1.output.categories
            if isinstance(result.output, dict):
                for k, v in result.output.items():
                    if k not in step_data:
                        step_data[k] = _make_dot_dict(v)
            steps_ns[sid] = step_data

        namespace = _DotDict({
            "variables": _make_dot_dict(context.variables),
            "steps": steps_ns,
            "trigger": _DotDict({"payload": _make_dot_dict(context.trigger_payload)}),
            "loop": _DotDict({
                "index": context.loop_index,
                "item": _make_dot_dict(context.loop_item) if isinstance(context.loop_item, dict) else context.loop_item,
            }),
            "item": _make_dot_dict(context.loop_item) if isinstance(context.loop_item, dict) else context.loop_item,
        })

        # Try simple dot-notation path first (fast path)
        try:
            return ExpressionEvaluator._resolve_path(expr, namespace)
        except Exception:
            pass

        # Fall back to Python eval with safe builtins
        safe_builtins = {
            "True": True, "False": False, "None": None,
            "not": lambda x: not x, "len": len,
            "int": int, "float": float, "str": str,
            "bool": bool, "list": list, "abs": abs,
            "min": min, "max": max, "range": range,
        }
        try:
            # Strip non-ASCII characters (emojis) that break eval/compile
            clean_expr = ''.join(c if ord(c) < 128 else ' ' for c in expr)
            return eval(clean_expr, {"__builtins__": safe_builtins}, namespace)
        except Exception as e:
            logger.warning(f"Expression eval failed: {repr(expr)} -> {e}")
            return expression

    @staticmethod
    def _resolve_path(path: str, namespace: dict) -> Any:
        """Resolve a dot-notation path like 'steps.step_1.output.name'."""
        # Can't resolve paths with brackets, comparisons, or function calls
        if any(c in path for c in "[]()!=<>+-*/"):
            raise ValueError("Not a simple dot path")

        parts = path.split(".")
        current = namespace

        for part in parts:
            if isinstance(current, dict):
                if part in current:
                    current = current[part]
                else:
                    alt = part.replace('_', '-') if '_' in part else part.replace('-', '_')
                    if alt in current:
                        current = current[alt]
                    else:
                        raise KeyError(f"Cannot resolve '{part}' in path '{path}'")
            elif isinstance(current, list):
                current = current[int(part)]
            elif hasattr(current, part):
                current = getattr(current, part)
            else:
                raise KeyError(f"Cannot resolve '{part}' in path '{path}'")

        return current

    @staticmethod
    def resolve_config(config: dict, context: ExecutionContext) -> dict:
        """Recursively resolve all template expressions in a config dict."""
        resolved = {}
        for key, value in config.items():
            if isinstance(value, str):
                resolved[key] = ExpressionEvaluator.evaluate(value, context)
            elif isinstance(value, dict):
                resolved[key] = ExpressionEvaluator.resolve_config(value, context)
            elif isinstance(value, list):
                resolved[key] = [
                    ExpressionEvaluator.evaluate(v, context) if isinstance(v, str)
                    else ExpressionEvaluator.resolve_config(v, context) if isinstance(v, dict)
                    else v
                    for v in value
                ]
            else:
                resolved[key] = value
        return resolved


# ─── Step Executor ─────────────────────────────────────────────

class StepExecutor:
    """Executes individual workflow steps by delegating to task implementations.

    Uses the TaskRegistry to find the right handler for each step type.
    """

    def __init__(self, task_registry=None):
        self._task_registry = task_registry
        self._evaluator = ExpressionEvaluator()

    async def execute_step(
        self,
        step_def: dict,
        context: ExecutionContext,
    ) -> StepResult:
        """Execute a single workflow step.

        Args:
            step_def: Step definition from the workflow
            context: Shared execution context

        Returns:
            StepResult with output or error
        """
        step_id = step_def["id"]
        step_type = step_def.get("type", "unknown")
        step_name = step_def.get("name", step_id)
        timeout = step_def.get("timeout", 300)  # Default 5 min
        retry_config = step_def.get("retry", {})
        max_retries = retry_config.get("max_attempts", 0)

        context.current_step_id = step_id
        started_at = datetime.now(timezone.utc)

        result = StepResult(
            step_id=step_id,
            status=StepStatus.RUNNING,
            started_at=started_at.isoformat(),
        )

        # Resolve template expressions in config
        raw_config = step_def.get("config", {})
        try:
            resolved_config = self._evaluator.resolve_config(raw_config, context)
        except Exception as e:
            result.status = StepStatus.FAILED
            result.error = f"Config resolution failed: {str(e)}"
            result.completed_at = datetime.now(timezone.utc).isoformat()
            return result

        # Handle built-in step types
        if step_type == "condition":
            return await self._execute_condition(step_def, resolved_config, context, result)
        elif step_type == "foreach":
            return await self._execute_foreach(step_def, resolved_config, context, result)
        elif step_type == "parallel":
            return await self._execute_parallel(step_def, resolved_config, context, result)
        elif step_type == "delay":
            return await self._execute_delay(step_def, resolved_config, context, result)
        elif step_type == "set_variable":
            return await self._execute_set_variable(step_def, resolved_config, context, result)
        elif step_type == "log":
            return await self._execute_log(step_def, resolved_config, context, result)
        elif step_type == "loop":
            return await self._execute_loop(step_def, resolved_config, context, result)

        # Delegate to task registry for custom step types
        attempt = 0
        last_error = None

        while attempt <= max_retries:
            try:
                output = await asyncio.wait_for(
                    self._run_task(step_type, resolved_config, context),
                    timeout=timeout,
                )
                completed_at = datetime.now(timezone.utc)
                result.status = StepStatus.COMPLETED
                result.output = output
                result.completed_at = completed_at.isoformat()
                result.duration_ms = int((completed_at - started_at).total_seconds() * 1000)
                result.retry_count = attempt
                return result

            except asyncio.TimeoutError:
                last_error = f"Step timed out after {timeout}s"
                attempt += 1
            except Exception as e:
                last_error = str(e)
                attempt += 1
                if attempt <= max_retries:
                    backoff = retry_config.get("backoff", "exponential")
                    delay = self._calculate_backoff(attempt, backoff)
                    logger.info(f"Step {step_id} retry {attempt}/{max_retries} in {delay}s")
                    await asyncio.sleep(delay)

        # All retries exhausted
        completed_at = datetime.now(timezone.utc)
        result.status = StepStatus.FAILED
        result.error = last_error
        result.completed_at = completed_at.isoformat()
        result.duration_ms = int((completed_at - started_at).total_seconds() * 1000)
        result.retry_count = attempt - 1
        return result

    async def _run_task(self, task_type: str, config: dict, context: ExecutionContext) -> Any:
        """Run a task from the task registry."""
        if self._task_registry is None:
            # Fallback: return config as output (useful for testing)
            logger.warning(f"No task registry — returning config for type '{task_type}'")
            return {"task_type": task_type, "config": config, "status": "mock"}

        task_class = self._task_registry.get(task_type)
        if task_class is None:
            raise ValueError(f"Unknown task type: {task_type}")

        task_instance = task_class()

        # Build context dict for tasks that need step results / variables
        context_dict = {
            "steps": {
                sid: {"output": sr.output, "status": sr.status.value if hasattr(sr.status, 'value') else sr.status}
                for sid, sr in context.steps.items()
            },
            "variables": context.variables,
            "loop_item": context.loop_item,
            "workflow_id": context.workflow_id,
        }

        result = await task_instance.run(config, context_dict)

        # Propagate task-level failures so execute_step marks the step as FAILED
        if hasattr(result, "success") and not result.success:
            raise RuntimeError(result.error or f"Task '{task_type}' returned success=False")

        return result.output if hasattr(result, "output") else result

    async def _execute_condition(
        self, step_def: dict, config: dict, context: ExecutionContext, result: StepResult
    ) -> StepResult:
        """Execute a conditional branch step."""
        # Support both "expression" and "condition" keys (template compatibility)
        expression = config.get("expression") or config.get("condition", "false")
        evaluated = self._evaluator.evaluate(expression, context)

        branch_key = "true" if evaluated else "false"
        # Store on_true/on_false for the engine to determine next steps
        result.status = StepStatus.COMPLETED
        result.output = {
            "branch": branch_key,
            "evaluated": evaluated,
            "on_true": config.get("on_true"),
            "on_false": config.get("on_false"),
        }
        result.completed_at = datetime.now(timezone.utc).isoformat()
        return result

    def _resolve_items_expression(self, items_expr, context: ExecutionContext):
        """Resolve a loop items/collection expression to an iterable.

        Handles both {{ expr }} and bare dot-notation like 'steps.step_5.data'.
        Returns a list — empty list if resolution fails or result is not iterable.
        """
        if isinstance(items_expr, (list, tuple)):
            return list(items_expr)

        if isinstance(items_expr, str):
            expr = items_expr.strip()
            # If bare expression (no {{ }}), wrap it for evaluator
            if expr and "{{" not in expr:
                expr = "{{ " + expr + " }}"
            resolved = self._evaluator.evaluate(expr, context)
            if isinstance(resolved, (list, tuple)):
                return list(resolved)
            # If still a string (unresolved), try JSON parse
            if isinstance(resolved, str):
                try:
                    import json
                    parsed = json.loads(resolved)
                    if isinstance(parsed, list):
                        return parsed
                except (json.JSONDecodeError, ValueError):
                    pass
            # None or non-iterable → empty list with warning
            if resolved is None or resolved == items_expr:
                logger.warning("Loop items expression resolved to empty",
                               expression=items_expr, resolved_type=type(resolved).__name__)
                return []
            # Single dict → wrap in list
            if isinstance(resolved, dict):
                return [resolved]
            return []

        if items_expr is None:
            return []

        # Already a list or other iterable
        try:
            return list(items_expr)
        except (TypeError, ValueError):
            return []

    async def _execute_foreach(
        self, step_def: dict, config: dict, context: ExecutionContext, result: StepResult
    ) -> StepResult:
        """Execute a for-each loop step — iterate and run body steps."""
        collection = self._resolve_items_expression(config.get("collection", []), context)

        if not collection:
            logger.warning("foreach collection is empty, skipping loop",
                           step=step_def.get("id"))
            result.status = StepStatus.COMPLETED
            result.output = {"collection_size": 0, "iterations_completed": 0, "results": [], "skipped": True}
            result.completed_at = datetime.now(timezone.utc).isoformat()
            return result

        body_step_ids = config.get("body", [])
        iteration_results = []
        errors = []

        for i, item in enumerate(collection):
            context.loop_item = item
            context.set_variable("_loop_index", i)

            for body_step_id in body_step_ids:
                # Find step definition in workflow
                body_step = None
                for s in context.workflow_steps if hasattr(context, 'workflow_steps') else []:
                    if s.get("id") == body_step_id:
                        body_step = s
                        break
                if body_step:
                    try:
                        body_result = await self.execute_step(body_step, context)
                        iteration_results.append(body_result.output)
                    except Exception as e:
                        errors.append(f"Iteration {i}: {str(e)}")

        context.loop_item = None
        result.status = StepStatus.COMPLETED
        result.output = {
            "collection_size": len(collection),
            "iterations_completed": len(collection) - len(errors),
            "results": iteration_results,
            "errors": errors,
        }
        result.completed_at = datetime.now(timezone.utc).isoformat()
        return result

    async def _execute_loop(
        self, step_def: dict, config: dict, context: ExecutionContext, result: StepResult
    ) -> StepResult:
        """Execute a loop step — iterates items and runs embedded step template."""
        items = self._resolve_items_expression(config.get("items", []), context)

        if not items:
            logger.warning("loop items is empty, skipping loop", step=step_def.get("id"))
            result.status = StepStatus.COMPLETED
            result.output = {"iterations_completed": 0, "results": [], "errors": [], "skipped": True}
            result.completed_at = datetime.now(timezone.utc).isoformat()
            return result

        # Embedded step template to run per item
        inner_step = config.get("step", step_def.get("step", {}))
        max_parallel = config.get("max_parallel", 1)
        delay_config = config.get("delay_between", {})
        on_error = config.get("on_error", "stop")

        iteration_results = []
        errors = []

        for i, item in enumerate(items):
            # Set loop context
            context.loop_item = item
            context.set_variable("_loop_index", i)
            context.set_variable("_loop_total", len(items))

            # Build a temporary step definition from the embedded step template
            temp_step_def = {
                "id": f"{step_def['id']}_iter_{i}",
                "type": inner_step.get("type", "custom_script"),
                "name": f"{step_def.get('name', 'loop')} [{i+1}/{len(items)}]",
                "config": inner_step.get("config", {}),
                "timeout": inner_step.get("timeout", step_def.get("timeout", 300)),
            }

            try:
                iter_result = await self.execute_step(temp_step_def, context)
                iteration_results.append(iter_result.output)

                if iter_result.status == StepStatus.FAILED and on_error == "stop":
                    errors.append(f"Iteration {i}: {iter_result.error}")
                    break
                elif iter_result.status == StepStatus.FAILED:
                    errors.append(f"Iteration {i}: {iter_result.error}")

            except Exception as e:
                errors.append(f"Iteration {i}: {str(e)}")
                if on_error == "stop":
                    break

            # Delay between iterations
            if delay_config and i < len(items) - 1:
                import random as rng
                min_delay = delay_config.get("min", 1)
                max_delay = delay_config.get("max", min_delay)
                unit = delay_config.get("unit", "seconds")
                wait = rng.uniform(min_delay, max_delay)
                if unit == "milliseconds":
                    wait /= 1000
                await asyncio.sleep(wait)

        context.loop_item = None
        result.status = StepStatus.COMPLETED
        result.output = {
            "total_items": len(items),
            "iterations_completed": len(iteration_results),
            "results": iteration_results,
            "errors": errors,
        }
        result.completed_at = datetime.now(timezone.utc).isoformat()
        return result

    async def _execute_parallel(
        self, step_def: dict, config: dict, context: ExecutionContext, result: StepResult
    ) -> StepResult:
        """Execute parallel branches."""
        branches = step_def.get("branches", {})
        result.status = StepStatus.COMPLETED
        result.output = {"branches": list(branches.keys())}
        result.completed_at = datetime.now(timezone.utc).isoformat()
        return result

    async def _execute_delay(
        self, step_def: dict, config: dict, context: ExecutionContext, result: StepResult
    ) -> StepResult:
        """Execute a delay/wait step."""
        seconds = config.get("seconds", 1)
        await asyncio.sleep(min(seconds, 300))  # Cap at 5 min
        result.status = StepStatus.COMPLETED
        result.output = {"waited_seconds": seconds}
        result.completed_at = datetime.now(timezone.utc).isoformat()
        return result

    async def _execute_set_variable(
        self, step_def: dict, config: dict, context: ExecutionContext, result: StepResult
    ) -> StepResult:
        """Set workflow variables."""
        for key, value in config.items():
            if key != "type":
                context.set_variable(key, value)
        result.status = StepStatus.COMPLETED
        result.output = {"variables_set": list(config.keys())}
        result.completed_at = datetime.now(timezone.utc).isoformat()
        return result

    async def _execute_log(
        self, step_def: dict, config: dict, context: ExecutionContext, result: StepResult
    ) -> StepResult:
        """Log a message (useful for debugging workflows)."""
        message = config.get("message", "")
        level = config.get("level", "info")
        getattr(logger, level, logger.info)(f"[Workflow {context.workflow_id}] {message}")
        result.status = StepStatus.COMPLETED
        result.output = {"message": message, "level": level}
        result.completed_at = datetime.now(timezone.utc).isoformat()
        return result

    @staticmethod
    def _calculate_backoff(attempt: int, strategy: str) -> float:
        """Calculate retry backoff delay."""
        if strategy == "exponential":
            return min(2 ** attempt, 60)
        elif strategy == "linear":
            return min(attempt * 2, 60)
        else:
            return 1  # Fixed 1 second


# ─── Workflow Engine ───────────────────────────────────────────

class WorkflowEngine:
    """Main workflow execution engine.

    Executes a complete workflow DAG from start to finish,
    handling step ordering, branching, loops, error handling,
    and checkpoint persistence.

    Architecture (v2 — iterative queue):
    - Uses an asyncio.Queue instead of recursive _execute_steps calls
    - asyncio.Semaphore controls max parallel step concurrency
    - Prevents stack overflow on deeply nested / long workflows
    - Supports graceful cancellation via context.metadata["cancelled"]
    """

    # Default max parallel steps running at once (per execution)
    DEFAULT_MAX_CONCURRENCY = 5

    def __init__(
        self,
        task_registry=None,
        checkpoint_manager=None,
        on_step_complete: Optional[Callable] = None,
        on_execution_complete: Optional[Callable] = None,
        max_concurrency: int = DEFAULT_MAX_CONCURRENCY,
    ):
        self._step_executor = StepExecutor(task_registry=task_registry)
        self._checkpoint_manager = checkpoint_manager
        self._on_step_complete = on_step_complete
        self._on_execution_complete = on_execution_complete
        self._running_executions: dict[str, ExecutionContext] = {}
        self._max_concurrency = max_concurrency

    async def execute(
        self,
        execution_id: str,
        workflow_id: str,
        organization_id: str,
        definition: dict,
        variables: dict = None,
        trigger_payload: dict = None,
        resume_context: ExecutionContext = None,
    ) -> ExecutionContext:
        """Execute a workflow from its definition.

        Args:
            execution_id: Unique ID for this execution
            workflow_id: ID of the workflow being executed
            organization_id: Owning organization
            definition: Workflow definition dict with steps
            variables: Initial workflow variables
            trigger_payload: Data from the trigger that started this
            resume_context: If resuming from crash, the saved context

        Returns:
            Final ExecutionContext with all step results
        """
        # Create or resume context
        if resume_context:
            context = resume_context
            logger.info(f"Resuming execution {execution_id} from step {context.current_step_id}")
        else:
            context = ExecutionContext(
                execution_id=execution_id,
                workflow_id=workflow_id,
                organization_id=organization_id,
                variables={**(definition.get("variables", {})), **(variables or {})},
                trigger_payload=trigger_payload or {},
            )

        self._running_executions[execution_id] = context

        try:
            steps = definition.get("steps", [])
            if not steps:
                logger.warning(f"Workflow {workflow_id} has no steps")
                return context

            # Convert depends_on to next pointers if needed
            # Templates use depends_on (backward), engine uses next (forward)
            has_next = any(s.get("next") for s in steps)
            has_depends = any(s.get("depends_on") for s in steps)
            if has_depends and not has_next:
                for step in steps:
                    for dep_id in step.get("depends_on", []):
                        # Find the dependency step and add this step to its next list
                        for dep_step in steps:
                            if dep_step["id"] == dep_id:
                                if "next" not in dep_step:
                                    dep_step["next"] = []
                                if step["id"] not in dep_step["next"]:
                                    dep_step["next"].append(step["id"])

            # Build step index for quick lookup
            step_index = {s["id"]: s for s in steps}

            # Find starting step(s) — steps with no incoming edges
            # or resume from the last incomplete step
            if resume_context and context.current_step_id:
                start_steps = [context.current_step_id]
            else:
                # Find entry points: first step or steps not referenced as "next" by others
                all_next_ids = set()
                for s in steps:
                    all_next_ids.update(s.get("next", []))
                    for branch_steps in s.get("branches", {}).values():
                        all_next_ids.update(branch_steps)
                    all_next_ids.update(s.get("body", []))

                entry_steps = [s["id"] for s in steps if s["id"] not in all_next_ids]
                start_steps = entry_steps if entry_steps else [steps[0]["id"]]

            # Execute DAG starting from entry steps
            await self._execute_steps(start_steps, step_index, context)

        except asyncio.CancelledError:
            logger.info(f"Execution {execution_id} cancelled")
        except Exception as e:
            logger.error(f"Execution {execution_id} failed: {e}", exc_info=True)
            context.metadata["error"] = str(e)
        finally:
            self._running_executions.pop(execution_id, None)

            if self._on_execution_complete:
                try:
                    await self._on_execution_complete(context)
                except Exception as e:
                    logger.error(f"on_execution_complete callback failed: {e}")

        return context

    async def _execute_steps(
        self,
        step_ids: list[str],
        step_index: dict[str, dict],
        context: ExecutionContext,
    ) -> None:
        """Execute steps using an iterative queue (no recursion).

        Uses asyncio.Queue + Semaphore for controlled parallelism.
        This prevents stack overflow on deeply nested workflows and
        allows concurrent step execution where the DAG allows it.

        Args:
            step_ids: Initial step IDs to start with
            step_index: Dict mapping step_id -> step definition
            context: Shared execution context
        """
        queue: asyncio.Queue[str] = asyncio.Queue()
        semaphore = asyncio.Semaphore(self._max_concurrency)
        visited: set[str] = set()  # Prevent infinite loops
        failed_fatally = False  # Stops the queue on unhandled errors

        # Seed the queue
        for sid in step_ids:
            queue.put_nowait(sid)

        async def _process_step(step_id: str) -> None:
            """Process a single step from the queue (runs under semaphore)."""
            nonlocal failed_fatally

            if failed_fatally:
                return

            # Check cancellation
            if context.metadata.get("cancelled"):
                logger.info(f"Execution cancelled, skipping step {step_id}")
                return

            # Skip already completed (resuming) or already visited
            existing = context.steps.get(step_id)
            if existing and existing.status == StepStatus.COMPLETED:
                logger.info(f"Skipping already completed step: {step_id}")
                # Still enqueue next steps so DAG continues
                self._enqueue_next(step_id, step_index, context, queue, visited)
                return

            step_def = step_index.get(step_id)
            if not step_def:
                logger.error(f"Step not found in definition: {step_id}")
                return

            # Checkpoint before step
            if self._checkpoint_manager:
                try:
                    from workflow.checkpoint import CheckpointType
                    await self._checkpoint_manager.save_checkpoint(
                        execution_id=context.execution_id,
                        checkpoint_type=CheckpointType.STEP_STARTING,
                        step_id=step_id,
                    )
                except Exception as e:
                    logger.warning(f"Checkpoint save failed: {e}")

            # Execute the step
            async with semaphore:
                result = await self._step_executor.execute_step(step_def, context)

            context.steps[step_id] = result

            # Checkpoint after step
            if self._checkpoint_manager:
                try:
                    from workflow.checkpoint import CheckpointType
                    cp_type = (
                        CheckpointType.STEP_COMPLETED
                        if result.status == StepStatus.COMPLETED
                        else CheckpointType.STEP_FAILED
                    )
                    await self._checkpoint_manager.save_checkpoint(
                        execution_id=context.execution_id,
                        checkpoint_type=cp_type,
                        step_id=step_id,
                        data={"output": result.output, "error": result.error},
                    )
                except Exception as e:
                    logger.warning(f"Checkpoint save failed: {e}")

            # Notify step completion
            if self._on_step_complete:
                try:
                    await self._on_step_complete(context, result)
                except Exception as e:
                    logger.warning(f"on_step_complete callback failed: {e}")

            # Handle step failure
            if result.status == StepStatus.FAILED:
                error_handler_id = step_def.get("on_error")
                if error_handler_id and error_handler_id in step_index:
                    logger.info(f"Step {step_id} failed, running error handler: {error_handler_id}")
                    if error_handler_id not in visited:
                        visited.add(error_handler_id)
                        queue.put_nowait(error_handler_id)
                else:
                    logger.error(f"Step {step_id} failed with no error handler: {result.error}")
                    failed_fatally = True
                    return

            # Enqueue next steps based on step type
            self._enqueue_next(step_id, step_index, context, queue, visited)

        # Main loop: drain the queue iteratively
        while not queue.empty() and not failed_fatally:
            # Grab a batch of ready steps (up to concurrency limit)
            batch: list[str] = []
            while not queue.empty() and len(batch) < self._max_concurrency:
                try:
                    batch.append(queue.get_nowait())
                except asyncio.QueueEmpty:
                    break

            if not batch:
                break

            if len(batch) == 1:
                # Single step — run directly (common case, avoids gather overhead)
                await _process_step(batch[0])
            else:
                # Multiple steps — run in parallel with semaphore control
                await asyncio.gather(*[_process_step(sid) for sid in batch])

    def _enqueue_next(
        self,
        step_id: str,
        step_index: dict[str, dict],
        context: ExecutionContext,
        queue: asyncio.Queue,
        visited: set[str],
    ) -> None:
        """Determine and enqueue next steps based on the completed step's type."""
        step_def = step_index.get(step_id, {})
        result = context.steps.get(step_id)
        step_type = step_def.get("type", "")

        next_ids: list[str] = []

        if step_type == "condition" and result and result.output:
            branch = result.output.get("branch", "false")
            # Support branches: {"true": [...], "false": [...]}
            branches = step_def.get("branches", {})
            next_ids = branches.get(branch, [])
            # Also support config-style on_true / on_false
            if not next_ids and result.output:
                target = result.output.get(f"on_{branch}")
                if target:
                    next_ids = [target] if isinstance(target, str) else target

        elif step_type == "foreach" and result and result.status == StepStatus.COMPLETED:
            # foreach body is already executed inside StepExecutor._execute_foreach
            # Enqueue next pointers after loop
            next_ids = step_def.get("next", [])

        elif step_type == "loop" and result and result.status == StepStatus.COMPLETED:
            # Loop body already executed in StepExecutor._execute_loop
            next_ids = step_def.get("next", []) or step_def.get("depends_on_next", [])

        else:
            # Regular step — follow next pointers
            next_ids = step_def.get("next", [])

        for nid in next_ids:
            if nid not in visited:
                visited.add(nid)
                queue.put_nowait(nid)

    async def cancel_execution(self, execution_id: str) -> bool:
        """Cancel a running execution.

        Args:
            execution_id: ID of the execution to cancel

        Returns:
            True if cancelled, False if not found
        """
        context = self._running_executions.get(execution_id)
        if context:
            context.metadata["cancelled"] = True
            logger.info(f"Execution {execution_id} marked for cancellation")
            return True
        return False

    def get_running_executions(self) -> dict[str, dict]:
        """Get status of all running executions."""
        return {
            eid: {
                "workflow_id": ctx.workflow_id,
                "current_step": ctx.current_step_id,
                "steps_completed": sum(
                    1 for r in ctx.steps.values()
                    if r.status == StepStatus.COMPLETED
                ),
                "steps_failed": sum(
                    1 for r in ctx.steps.values()
                    if r.status == StepStatus.FAILED
                ),
            }
            for eid, ctx in self._running_executions.items()
        }


# ─── Singleton ─────────────────────────────────────────────────

_engine: Optional[WorkflowEngine] = None


def get_workflow_engine() -> WorkflowEngine:
    """Get or create the singleton WorkflowEngine."""
    global _engine
    if _engine is None:
        _engine = WorkflowEngine()
    return _engine
