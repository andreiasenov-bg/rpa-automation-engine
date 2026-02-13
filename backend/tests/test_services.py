"""Tests for the service layer (repository pattern)."""

import pytest
from uuid import uuid4

from services.auth_service import AuthService


@pytest.mark.integration
class TestAuthService:

    async def test_register_creates_org_and_user(self, db_session):
        svc = AuthService(db_session)
        result = await svc.register(
            email="newadmin@test.com",
            password="StrongPass123!",
            full_name="New Admin",
            org_name="New Org",
        )
        assert "access_token" in result
        assert "user" in result
        assert result["user"]["email"] == "newadmin@test.com"

    async def test_register_duplicate_email_fails(self, db_session, test_user):
        svc = AuthService(db_session)
        with pytest.raises(Exception):
            await svc.register(
                email=test_user.email,
                password="AnotherPass123!",
                full_name="Duplicate",
                org_name="Dup Org",
            )

    async def test_login_success(self, db_session, test_user, test_org):
        svc = AuthService(db_session)
        result = await svc.login(
            email="test@example.com",
            password="TestPassword123!",
        )
        assert "access_token" in result
        assert result["user"]["id"] == test_user.id

    async def test_login_wrong_password(self, db_session, test_user):
        svc = AuthService(db_session)
        with pytest.raises(Exception):
            await svc.login(
                email="test@example.com",
                password="WrongPassword",
            )
