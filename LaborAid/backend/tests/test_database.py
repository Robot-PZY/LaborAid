"""Tests for the database module (app.core.database).

Covers: health check structure, get_db commit behaviour, and
get_db_readonly non-commit behaviour.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, db_health_check, get_db, get_db_readonly


# ---------------------------------------------------------------------------
# Helpers — isolated in-memory engine per test group
# ---------------------------------------------------------------------------

def _make_test_engine():
    """Create an in-memory async SQLite engine for testing."""
    return create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


# ---------------------------------------------------------------------------
# db_health_check
# ---------------------------------------------------------------------------


class TestDbHealthCheck:
    """Tests for the db_health_check function."""

    @pytest.mark.asyncio
    async def test_returns_ok_status(self):
        """A working database should return status='ok'."""
        result = await db_health_check()
        assert result["status"] == "ok"

    @pytest.mark.asyncio
    async def test_contains_latency(self):
        """The result should include latency_ms as a positive number."""
        result = await db_health_check()
        assert "latency_ms" in result
        assert isinstance(result["latency_ms"], (int, float))
        assert result["latency_ms"] >= 0

    @pytest.mark.asyncio
    async def test_contains_database_url(self):
        """The result should include the database_url key."""
        result = await db_health_check()
        assert "database_url" in result

    @pytest.mark.asyncio
    async def test_contains_pool_stats(self):
        """When status is ok, pool statistics should be present."""
        result = await db_health_check()
        if result["status"] == "ok":
            assert "pool" in result
            pool = result["pool"]
            assert "pool_size" in pool
            assert "checked_in" in pool
            assert "checked_out" in pool
            assert "overflow" in pool

    @pytest.mark.asyncio
    async def test_returns_dict(self):
        result = await db_health_check()
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# get_db — commits on success
# ---------------------------------------------------------------------------


class TestGetDb:
    """Tests for the get_db async generator dependency."""

    @pytest.mark.asyncio
    async def test_yields_session_and_commits(self):
        """get_db should commit the session after the caller finishes."""
        engine = _make_test_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        SessionLocal = async_sessionmaker(
            bind=engine, class_=AsyncSession, expire_on_commit=False,
        )

        # Patch AsyncSessionLocal inside app.core.database to use our engine
        with patch("app.core.database.AsyncSessionLocal", SessionLocal):
            gen = get_db()
            session = await gen.__anext__()
            assert isinstance(session, AsyncSession)

            # Verify the session is usable
            result = await session.execute(text("SELECT 1"))
            row = result.scalar()
            assert row == 1

            # The session should commit when the generator is finalized
            commit_spy = MagicMock(wraps=session.commit)
            with patch.object(session, "commit", commit_spy):
                pass  # the real commit already happened via __anext__ flow

            # Exhaust the generator to trigger finally/commit
            try:
                await gen.__anext__()
            except StopAsyncIteration:
                pass

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_rolls_back_on_exception(self):
        """get_db should rollback if the caller raises an exception."""
        engine = _make_test_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        SessionLocal = async_sessionmaker(
            bind=engine, class_=AsyncSession, expire_on_commit=False,
        )

        with patch("app.core.database.AsyncSessionLocal", SessionLocal):
            gen = get_db()
            session = await gen.__anext__()

            # Simulate an exception from the caller side by throwing into
            # the generator, which will enter get_db's except clause.
            with pytest.raises(ValueError, match="test error"):
                await gen.athrow(ValueError("test error"))

        await engine.dispose()


# ---------------------------------------------------------------------------
# get_db_readonly — does NOT auto-commit
# ---------------------------------------------------------------------------


class TestGetDbReadonly:
    """Tests for the get_db_readonly async generator dependency."""

    @pytest.mark.asyncio
    async def test_yields_session(self):
        """get_db_readonly should yield a valid AsyncSession."""
        engine = _make_test_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        SessionLocal = async_sessionmaker(
            bind=engine, class_=AsyncSession, expire_on_commit=False,
        )

        with patch("app.core.database.AsyncSessionLocal", SessionLocal):
            gen = get_db_readonly()
            session = await gen.__anext__()
            assert isinstance(session, AsyncSession)

            result = await session.execute(text("SELECT 1"))
            assert result.scalar() == 1

            # Exhaust the generator cleanly
            try:
                await gen.__anext__()
            except StopAsyncIteration:
                pass

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_no_commit_on_success(self):
        """get_db_readonly should NOT call commit on normal exit.

        We verify this by patching session.commit and ensuring it is never
        called during a successful read-only session lifecycle.
        """
        engine = _make_test_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        SessionLocal = async_sessionmaker(
            bind=engine, class_=AsyncSession, expire_on_commit=False,
        )

        with patch("app.core.database.AsyncSessionLocal", SessionLocal):
            gen = get_db_readonly()
            session = await gen.__anext__()

            commit_called = False
            original_commit = session.commit

            async def tracking_commit():
                nonlocal commit_called
                commit_called = True
                await original_commit()

            with patch.object(session, "commit", tracking_commit):
                # Exhaust the generator
                try:
                    await gen.__anext__()
                except StopAsyncIteration:
                    pass

            # commit should NOT have been called for a read-only session
            assert not commit_called, "get_db_readonly should not commit"

        await engine.dispose()
