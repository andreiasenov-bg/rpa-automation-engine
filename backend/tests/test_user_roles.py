"""Tests for user-role assignment schemas and validation."""

import pytest
from pydantic import ValidationError
from api.routes.user_roles import AssignRoleRequest, BulkAssignRequest


class TestAssignRoleRequest:
    def test_valid(self):
        req = AssignRoleRequest(role_id="abc-123")
        assert req.role_id == "abc-123"

    def test_missing_role_id(self):
        with pytest.raises(ValidationError):
            AssignRoleRequest()


class TestBulkAssignRequest:
    def test_valid(self):
        req = BulkAssignRequest(user_ids=["u1", "u2"], role_id="r1")
        assert len(req.user_ids) == 2
        assert req.role_id == "r1"

    def test_empty_user_ids(self):
        with pytest.raises(ValidationError):
            BulkAssignRequest(user_ids=[], role_id="r1")

    def test_too_many_user_ids(self):
        with pytest.raises(ValidationError):
            BulkAssignRequest(user_ids=[f"u{i}" for i in range(51)], role_id="r1")

    def test_missing_role_id(self):
        with pytest.raises(ValidationError):
            BulkAssignRequest(user_ids=["u1"])
