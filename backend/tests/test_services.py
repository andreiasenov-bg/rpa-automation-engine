"""Tests for the service layer (repository pattern)."""

import pytest
from uuid import uuid4

from services.auth_service import AuthService


@pytest.mark.integration
class TestAuthService:

    async def test_register_creates_org_and_user(self, db_session):
        svc = AuthService(db_session)
        user, org = await svc.register(
            email="newadmin@test.com",
            password="StrongPass123!",
            first_name="New",
            last_name="Admin",
            organization_name="New Org",
        )
        assert user is not None
        assert user.email == "newadmin@test.com"
        assert org is not None
        assert org.slug == "new-org"

    async def test_register_duplicate_email_fails(self, db_session, test_user):
        svc = AuthService(db_session)
        with pytest.raises(ValueError, match="already registered"):
            await svc.register(
                email=test_user.email,
                password="AnotherPass123!",
                first_name="Duplicate",
                last_name="User",
                organization_name="Dup Org",
            )

    async def test_login_success(self, db_session, test_user, test_org):
        svc = AuthService(db_session)
        result = await svc.login(
            email="test@example.com",
            password="TestPassword123!",
        )
        assert result is not None
        assert "access_token" in result
        assert result["user"]["id"] == test_user.id

    async def test_login_wrong_password_returns_none(self, db_session, test_user):
        svc = AuthService(db_session)
        result = await svc.login(
            email="test@example.com",
            password="WrongPassword",
        )
        assert result is None

    async def test_login_nonexistent_email_returns_none(self, db_session):
        svc = AuthService(db_session)
        result = await svc.login(
            email="nobody@test.com",
            password="anything",
        )
        assert result is None
