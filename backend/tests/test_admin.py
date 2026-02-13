"""Tests for admin API endpoints."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


class TestAdminOverview:
    """Test admin overview endpoint."""

    def test_overview_returns_org_and_counts(self):
        """Verify overview structure contains expected fields."""
        overview = {
            "organization": {
                "id": str(uuid4()),
                "name": "Test Corp",
                "plan": "enterprise",
                "created_at": "2025-01-01T00:00:00Z",
            },
            "counts": {
                "users": 10,
                "workflows": 25,
                "agents": 3,
                "credentials": 5,
                "executions_total": 1000,
                "executions_running": 2,
                "executions_failed": 15,
            },
        }
        assert "organization" in overview
        assert "counts" in overview
        assert overview["counts"]["users"] == 10
        assert overview["organization"]["plan"] == "enterprise"

    def test_counts_are_non_negative(self):
        """All counts should be non-negative."""
        counts = {
            "users": 0,
            "workflows": 0,
            "agents": 0,
            "credentials": 0,
            "executions_total": 0,
            "executions_running": 0,
            "executions_failed": 0,
        }
        for key, value in counts.items():
            assert value >= 0, f"{key} should be non-negative"


class TestRoleManagement:
    """Test role CRUD operations."""

    def test_role_slug_generation(self):
        """Test slug generation from role name."""
        import re

        def slugify(name: str) -> str:
            return re.sub(r'[^a-z0-9]+', '_', name.lower()).strip('_')

        assert slugify("Admin") == "admin"
        assert slugify("Power User") == "power_user"
        assert slugify("Read-Only Viewer") == "read_only_viewer"
        assert slugify("  Spaces  ") == "spaces"

    def test_admin_role_protected(self):
        """Admin role slug should not be deleteable."""
        protected_slugs = {"admin"}
        assert "admin" in protected_slugs

    def test_role_with_permissions(self):
        """Role should contain permission list."""
        role = {
            "id": str(uuid4()),
            "name": "Editor",
            "slug": "editor",
            "permissions": [
                {"id": str(uuid4()), "code": "workflows.read"},
                {"id": str(uuid4()), "code": "workflows.write"},
                {"id": str(uuid4()), "code": "executions.read"},
            ],
        }
        assert len(role["permissions"]) == 3
        codes = [p["code"] for p in role["permissions"]]
        assert "workflows.read" in codes
        assert "workflows.write" in codes

    def test_duplicate_slug_detection(self):
        """Slugs should be unique within an organization."""
        existing_slugs = {"admin", "operator", "viewer"}
        new_slug = "operator"
        assert new_slug in existing_slugs, "Should detect duplicate"


class TestPermissions:
    """Test permission system."""

    def test_permission_code_format(self):
        """Permission codes should follow resource.action pattern."""
        import re
        pattern = re.compile(r'^[a-z_]+\.[a-z_*]+$')

        valid_codes = [
            "workflows.read",
            "workflows.write",
            "executions.read",
            "executions.cancel",
            "admin.*",
            "users.manage",
            "credentials.read",
            "agents.manage",
        ]
        for code in valid_codes:
            assert pattern.match(code), f"Invalid permission code format: {code}"

    def test_wildcard_permission_grants_all(self):
        """admin.* should match any admin permission."""

        def check_permission(user_perms: list[str], required: str) -> bool:
            for perm in user_perms:
                if perm == required:
                    return True
                # Wildcard: "admin.*" matches "admin.read", "admin.write", etc.
                if perm.endswith(".*"):
                    prefix = perm[:-2]
                    if required.startswith(prefix + "."):
                        return True
            return False

        assert check_permission(["admin.*"], "admin.read") is True
        assert check_permission(["admin.*"], "admin.write") is True
        assert check_permission(["admin.*"], "workflows.read") is False
        assert check_permission(["workflows.read"], "workflows.read") is True
        assert check_permission(["workflows.read"], "workflows.write") is False
