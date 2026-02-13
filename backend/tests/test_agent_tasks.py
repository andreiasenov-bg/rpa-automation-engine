"""Tests for agent task assignment API."""

import pytest


class TestTaskClaim:
    """Tests for POST /agent-tasks/claim."""

    def test_claim_requires_agent_id(self):
        """Body must include agent_id."""
        from api.routes.agent_tasks import TaskClaimRequest
        with pytest.raises(Exception):
            TaskClaimRequest()

    def test_claim_request_valid(self):
        from api.routes.agent_tasks import TaskClaimRequest
        req = TaskClaimRequest(agent_id="agent-123", capabilities={"browser": True})
        assert req.agent_id == "agent-123"
        assert req.capabilities == {"browser": True}


class TestTaskResult:
    """Tests for POST /agent-tasks/{execution_id}/result."""

    def test_result_requires_status(self):
        from api.routes.agent_tasks import TaskResultRequest
        with pytest.raises(Exception):
            TaskResultRequest()

    def test_result_valid_completed(self):
        from api.routes.agent_tasks import TaskResultRequest
        req = TaskResultRequest(
            status="completed",
            output={"data": 42},
            duration_ms=1500,
        )
        assert req.status == "completed"
        assert req.output == {"data": 42}

    def test_result_valid_failed(self):
        from api.routes.agent_tasks import TaskResultRequest
        req = TaskResultRequest(
            status="failed",
            error_message="Timeout after 30s",
        )
        assert req.status == "failed"
        assert req.error_message == "Timeout after 30s"

    def test_result_invalid_status(self):
        from api.routes.agent_tasks import TaskResultRequest
        with pytest.raises(Exception):
            TaskResultRequest(status="invalid")


class TestTaskSchemas:
    """Tests for task assignment schemas."""

    def test_task_assignment_schema(self):
        from api.routes.agent_tasks import TaskAssignment
        task = TaskAssignment(
            execution_id="ex-1",
            workflow_id="wf-1",
            step_index=0,
            task_type="workflow",
        )
        assert task.execution_id == "ex-1"
        assert task.workflow_id == "wf-1"
        assert task.step_index == 0
