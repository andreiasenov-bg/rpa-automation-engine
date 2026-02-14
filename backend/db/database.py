"""SQLAlchemy async database setup and engine configuration."""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.config import get_settings

settings = get_settings()


def create_db_engine():
    """Create and configure async SQLAlchemy engine.

    Returns:
        Async SQLAlchemy engine instance.
    """
    is_sqlite = settings.DATABASE_URL.startswith("sqlite")
    kwargs = dict(echo=settings.DEBUG)
    if not is_sqlite:
        kwargs.update(
            pool_pre_ping=True,
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
        )
    return create_async_engine(settings.DATABASE_URL, **kwargs)


def create_session_factory(engine):
    """Create async session factory.

    Args:
        engine: SQLAlchemy async engine instance.

    Returns:
        Async sessionmaker instance.
    """
    return sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )


# Global engine and session factory instances
engine = create_db_engine()
AsyncSessionLocal = create_session_factory(engine)


async def init_db():
    """Initialize database (create tables and run migrations).

    This should be called once at application startup.
    """
    from db.base import Base

    async with engine.begin() as conn:
        from sqlalchemy import text
        is_pg = settings.DATABASE_URL.startswith("postgresql")
        if is_pg:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS btree_gin"))
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Close database connections.

    This should be called at application shutdown.
    """
    await engine.dispose()
