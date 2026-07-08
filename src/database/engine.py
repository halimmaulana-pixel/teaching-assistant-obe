"""Database engine and session management — Singleton pattern."""

import logging
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.orm import DeclarativeBase

from ..config import get_settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


_engine = None
_session_factory = None


def get_engine():
    """Get or create singleton database engine."""
    global _engine
    if _engine is None:
        settings = get_settings()
        # Use async database URL (converts postgresql:// to postgresql+asyncpg://)
        db_url = settings.get_async_database_url()
        _engine = create_async_engine(
            db_url,
            echo=settings.database_echo,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
        )
        logger.info("Database engine created (singleton)")
    return _engine


def get_session_factory():
    """Get or create singleton session factory."""
    global _session_factory
    if _session_factory is None:
        engine = get_engine()
        _session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        logger.info("Session factory created (singleton)")
    return _session_factory


async def init_db() -> None:
    """Initialize database — create all tables."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created")


@asynccontextmanager
async def get_db():
    """Get database session (context manager)."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def close_db() -> None:
    """Close database engine — call on shutdown."""
    global _engine, _session_factory
    if _engine:
        await _engine.dispose()
        _engine = None
        _session_factory = None
        logger.info("Database engine closed")
