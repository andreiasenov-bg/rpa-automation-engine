"""Tests for database models — basic creation and relationships."""

import pytest
from uuid import uuid4


@pytest.mark.integration
class TestOrganizationModel:

    async def test_create_organization(self, db_session):
        from db.models.organization import Organization

        org = Organization(
            id=str(uuid4()),
            name="Acme Corp",
            slug="acme-corp",
            subscription_plan="enterprise",
        )
        db_session.add(org)
        await db_session.flush()
        assert org.id is not None
        assert org.created_at is not None

    async def test_soft_delete(self, db_session, test_org):
        """SoftDeleteMixin should set is_deleted and deleted_at."""
        assert test_org.is_deleted is False
        test_org.soft_delete()
        assert test_org.is_deleted is True
        assert test_org.deleted_at is not None


@pytest.mark.integration
class TestUserModel:

    async def test_create_user(self, db_session, test_org):
        from db.models.user import User
        from core.security import hash_password

        user = User(
            id=str(uuid4()),
            organization_id=test_org.id,
            email="newuser@test.com",
            password_hash=hash_password("Pass123!"),
            first_name="New",
            last_name="User",
        )
        db_session.add(user)
        await db_session.flush()
        assert user.id is not None


@pytest.mark.integration
class TestWorkflowModel:

    async def test_create_workflow(self, db_session, test_org, test_user):
        from db.models.workflow import Workflow

        wf = Workflow(
            id=str(uuid4()),
            organization_id=test_org.id,
            created_by_id=test_user.id,
            name="My Workflow",
            definition={"steps": [], "entry_point": "start"},
            version=1,
        )
        db_session.add(wf)
        await db_session.flush()
        assert wf.version == 1
