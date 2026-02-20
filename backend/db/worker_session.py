"""Worker-safe database session for Celery tasks.

Creates a fresh async engine per call to avoid the 'Future attached
to a different loop' error when asyncpg connections are shared
across event loops in forked Celery workers.
"""

from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.config import get_settings


@asynccontextmanager
async def worker_session():
    """Provide a transactional async session safe for Celery workers.
    
    Usage:
        async with worker_session() as session:
            result = await session.execute(...)
    """
    settings = get_settings()
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        future=True,
        pool_size=5,
        max_overflow=5,
        pool_recycle=300,
    )
    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False,
    )
    async with session_factory() as session:
        try:
            yield session
        finally:
            await session.close()
    await engine.dispose()

