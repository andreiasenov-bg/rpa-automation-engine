"""Shared pytest fixtures for the RPA Automation Engine test suite.

Provides:
- In-memory async SQLite database (no PostgreSQL needed for tests)
- AsyncSession factory
- FastAPI test client (httpx.AsyncClient)
- Pre-seeded test data (org, user, roles)
- Auth helpers (JWT tokens)
"""

import asyncio
import os
from typing import AsyncGenerator
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Override settings BEFORE any app imports
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("ENVIRONMENT", "testing")
os.environ.setdefault("LOG_FORMAT", "colored")

from db.base import Base, BaseModel  # noqa: E402
from core.security import create_access_token  # noqa: E402


# ---------------------------------------------------------------------------
# Database fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="session")
async def db_engine():
    """Create a shared async engine for the entire test session."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    # Import all models so Base.metadata knows about them
    import db.models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide a DB session that commits (so the app can read data) and cleans up after."""
    async_session_factory = sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    async with async_session_factory() as session:
        yield session
        await session.commit()

    # Clean up all data after each test
    async with db_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())


# ---------------------------------------------------------------------------
# App / HTTP client fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def app(db_engine):
    """Create a FastAPI app instance wired to the test database."""
    # Ensure tables exist and are clean
    async with db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())

    # Patch the database module to use our test engine
    import db.database as db_mod
    original_engine = db_mod.engine
    original_session = db_mod.AsyncSessionLocal

    db_mod.engine = db_engine
    db_mod.AsyncSessionLocal = sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    # Ensure tables exist on the patched engine
    import db.models  # noqa: F401
    async with db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    from app.main import create_app
    test_app = create_app()

    yield test_app

    # Restore originals
    db_mod.engine = original_engine
    db_mod.AsyncSessionLocal = original_session


@pytest_asyncio.fixture
async def client(app) -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=True) as ac:
        yield ac


# ---------------------------------------------------------------------------
# Test data fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def test_org(db_session):
    """Create a test organization."""
    from db.models.organization import Organization

    unique_suffix = uuid4().hex[:8]
    org = Organization(
        id=str(uuid4()),
        name=f"Test Organization {unique_suffix}",
        slug=f"test-org-{unique_suffix}",
        subscription_plan="enterprise",
        settings={"timezone": "UTC"},
    )
    db_session.add(org)
    await db_session.flush()
    return org


@pytest_asyncio.fixture
async def test_user(db_session, test_org):
    """Create a test user with admin role."""
    from db.models.user import User
    from core.security import hash_password

    user = User(
        id=str(uuid4()),
        organization_id=test_org.id,
        email=f"test-{uuid4().hex[:8]}@example.com",
        password_hash=hash_password("TestPassword123!"),
        first_name="Test",
        last_name="User",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
def auth_headers(test_user, test_org) -> dict:
    """Generate Authorization headers with a valid JWT token."""
    token = create_access_token(
        user_id=test_user.id,
        email=test_user.email,
        org_id=test_org.id,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def test_workflow(db_session, test_org, test_user):
    """Create a test workflow."""
    from db.models.workflow import Workflow

    workflow = Workflow(
        id=str(uuid4()),
        organization_id=test_org.id,
        created_by_id=test_user.id,
        name="Test Workflow",
        description="A workflow for testing",
        definition={
            "steps": [
                {
                    "id": "step_1",
                    "type": "delay",
                    "config": {"seconds": 0},
                    "next": [],
                }
            ],
            "entry_point": "step_1",
        },
        version=1,
        is_enabled=True,
    )
    db_session.add(workflow)
    await db_session.flush()
    return workflow
