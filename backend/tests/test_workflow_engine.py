"""Tests for the workflow execution engine."""

import pytest
from workflow.engine import ExpressionEvaluator, ExecutionContext


@pytest.mark.unit
class TestExpressionEvaluator:
    """Test template expression resolution."""

    def test_simple_variable(self):
        ctx = ExecutionContext(
            execution_id="ex-1",
            workflow_id="wf-1",
            organization_id="org-1",
        )
        ctx.variables["greeting"] = "hello"
        result = ExpressionEvaluator.evaluate("{{ variables.greeting }}", ctx)
        assert result == "hello"

    def test_step_output(self):
        ctx = ExecutionContext(
            execution_id="ex-1",
            workflow_id="wf-1",
            organization_id="org-1",
        )
        ctx.step_results["step_1"] = {"output": {"name": "Alice"}}
        result = ExpressionEvaluator.evaluate(
            "{{ steps.step_1.output.name }}", ctx
        )
        assert result == "Alice"

    def test_no_expression_passthrough(self):
        ctx = ExecutionContext(
            execution_id="ex-1",
            workflow_id="wf-1",
            organization_id="org-1",
        )
        result = ExpressionEvaluator.evaluate("plain text", ctx)
        assert result == "plain text"


@pytest.mark.unit
class TestExecutionContext:
    """Test context serialization."""

    def test_to_dict_and_back(self):
        ctx = ExecutionContext(
            execution_id="ex-1",
            workflow_id="wf-1",
            organization_id="org-1",
        )
        ctx.variables["key"] = "value"
        ctx.step_results["s1"] = {"output": 42}

        data = ctx.to_dict()
        restored = ExecutionContext.from_dict(data)

        assert restored.execution_id == "ex-1"
        assert restored.variables["key"] == "value"
        assert restored.step_results["s1"]["output"] == 42
