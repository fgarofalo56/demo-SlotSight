"""Async database engine, session factory, and FastAPI dependency."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from slotsight.config import get_settings
from slotsight.models import Base

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Lazily create the process-wide async engine."""
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.sqlalchemy_url,
            echo=settings.log_level == "debug",
            pool_pre_ping=True,  # survive Postgres idle-connection reaping
            pool_size=5,
            max_overflow=10,
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(), expire_on_commit=False, class_=AsyncSession
        )
    return _session_factory


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding a request-scoped session."""
    async with get_session_factory()() as session:
        yield session


@asynccontextmanager
async def session_scope() -> AsyncGenerator[AsyncSession, None]:
    """Session context manager for scripts and the MCP server.

    Commits on clean exit, rolls back on exception.
    """
    async with get_session_factory()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def create_all() -> None:
    """Create tables if absent.

    Deliberately not Alembic. This is a demo whose database is regenerated from
    a deterministic seed on every run, so migrations would be ceremony with no
    payoff. A production build of this app should use Alembic — that trade-off
    is documented in docs/architecture.md rather than hidden.
    """
    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_all() -> None:
    """Drop every table. Used by the seeder's --reset and by tests."""
    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def dispose_engine() -> None:
    """Close the pool on shutdown."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
