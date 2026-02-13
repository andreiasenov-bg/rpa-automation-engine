"""Tests for RBAC permission checking logic."""

import pytest
from core.rbac import _check_permission


class TestCheckPermission:
    """Test permission matching including wildcards."""

    def test_exact_match(self):
        perms = {"workflows.read", "workflows.write"}
        assert _check_permission(perms, "workflows.read") is True
        assert _check_permission(perms, "workflows.write") is True

    def test_no_match(self):
        perms = {"workflows.read"}
        assert _check_permission(perms, "workflows.write") is False
        assert _check_permission(perms, "executions.read") is False

    def test_wildcard_match(self):
        perms = {"admin.*"}
        assert _check_permission(perms, "admin.read") is True
        assert _check_permission(perms, "admin.write") is True
        assert _check_permission(perms, "admin.delete") is True

    def test_wildcard_no_cross_resource(self):
        perms = {"admin.*"}
        assert _check_permission(perms, "workflows.read") is False
        assert _check_permission(perms, "users.manage") is False

    def test_global_wildcard(self):
        perms = {"*"}
        assert _check_permission(perms, "workflows.read") is True
        assert _check_permission(perms, "admin.delete") is True
        assert _check_permission(perms, "anything.anything") is True

    def test_empty_permissions(self):
        perms: set[str] = set()
        assert _check_permission(perms, "workflows.read") is False

    def test_multiple_wildcards(self):
        perms = {"workflows.*", "executions.*"}
        assert _check_permission(perms, "workflows.read") is True
        assert _check_permission(perms, "executions.cancel") is True
        assert _check_permission(perms, "admin.manage") is False

    def test_mixed_exact_and_wildcard(self):
        perms = {"workflows.read", "admin.*"}
        assert _check_permission(perms, "workflows.read") is True
        assert _check_permission(perms, "workflows.write") is False
        assert _check_permission(perms, "admin.anything") is True
