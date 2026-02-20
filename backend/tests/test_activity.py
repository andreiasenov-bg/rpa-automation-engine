"""Tests for activity timeline helpers."""

from api.routes.activity import (
    _format_description,
    _action_icon,
    _action_color,
)


class MockLog:
    """Minimal mock for AuditLog."""
    def __init__(self, action, user_id=None, details=None, resource_type=None, resource_id=None):
        self.action = action
        self.user_id = user_id
        self.details = details
        self.resource_type = resource_type
        self.resource_id = resource_id


class TestFormatDescription:
    def test_known_action(self):
        log = MockLog(action="workflow.created")
        assert _format_description(log) == "Created a new workflow"

    def test_execution_completed(self):
        log = MockLog(action="execution.completed")
        assert _format_description(log) == "Execution completed"

    def test_unknown_action_returns_raw(self):
        log = MockLog(action="custom.action")
        assert _format_description(log) == "custom.action"

    def test_all_known_actions_have_descriptions(self):
        known_actions = [
            'workflow.created', 'workflow.updated', 'workflow.published',
            'workflow.archived', 'workflow.deleted',
            'execution.started', 'execution.completed', 'execution.failed',
            'execution.cancelled',
            'agent.registered', 'agent.connected', 'agent.disconnected',
            'user.login', 'user.register',
            'credential.created', 'credential.updated',
            'schedule.created', 'schedule.updated',
            'role.created', 'role.deleted',
        ]
        for action in known_actions:
            log = MockLog(action=action)
            desc = _format_description(log)
            assert desc != action, f"Action {action} should have a human-readable description"


class TestActionIcon:
    def test_workflow_created(self):
        assert _action_icon("workflow.created") == "GitBranch"

    def test_execution_completed(self):
        assert _action_icon("execution.completed") == "CheckCircle2"

    def test_agent_connected(self):
        assert _action_icon("agent.connected") == "Wifi"

    def test_unknown_returns_activity(self):
        assert _action_icon("something.unknown") == "Activity"


class TestActionColor:
    def test_completed_is_emerald(self):
        assert _action_color("execution.completed") == "emerald"

    def test_failed_is_red(self):
        assert _action_color("execution.failed") == "red"

    def test_started_is_blue(self):
        assert _action_color("execution.started") == "blue"

    def test_cancelled_is_amber(self):
        assert _action_color("execution.cancelled") == "amber"

    def test_unknown_is_slate(self):
        assert _action_color("something.other") == "slate"

    def test_published_is_emerald(self):
        assert _action_color("workflow.published") == "emerald"

    def test_deleted_is_red(self):
        assert _action_color("workflow.deleted") == "red"
