"""Database engine and session management.

Supports both SQLite and Postgres with proper pool settings, lifecycle
logging, health-check, and graceful shutdown.
"""

import logging
import time
from collections.abc import AsyncGenerator

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# ── Engine creation ─────────────────────────────────────────────────────────
connect_args = {}
engine_kwargs: dict = {"echo": settings.APP_DEBUG}

if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False
    # SQLite pool settings — use StaticPool for single-connection scenario
    # or set pool_size for WAL mode concurrent reads
    engine_kwargs["pool_size"] = 5
    engine_kwargs["pool_recycle"] = 1800  # 30 min
    engine_kwargs["pool_pre_ping"] = True
    # Enable WAL journal mode for better concurrent read performance
    connect_args["timeout"] = 30  # seconds to wait for lock
else:
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20
    engine_kwargs["pool_recycle"] = 1800
    engine_kwargs["pool_pre_ping"] = True

engine = create_async_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    **engine_kwargs,
)

logger.debug(
    "Database engine created: url=%s pool_size=%s",
    settings.DATABASE_URL.split("@")[-1] if "@" in settings.DATABASE_URL else "sqlite",
    engine_kwargs.get("pool_size", "default"),
)

# ── Connection pool event listeners ─────────────────────────────────────────

pool = engine.pool


@event.listens_for(pool, "checkout")
def _on_checkout(dbapi_conn, connection_record, proxy):
    logger.debug(
        "Pool checkout: dbapi_conn=%s connection_record=%s",
        id(dbapi_conn),
        id(connection_record),
    )


@event.listens_for(pool, "checkin")
def _on_checkin(dbapi_conn, connection_record):
    logger.debug(
        "Pool checkin: dbapi_conn=%s connection_record=%s",
        id(dbapi_conn),
        id(connection_record),
    )

# ── Session factory ─────────────────────────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async_session = AsyncSessionLocal


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — yields a database session with lifecycle logging.

    Includes slow-query detection: queries taking longer than 2 seconds
    are logged as warnings.

    Optimization notes for common query patterns:
    - Case listing: filtered by owner_id + status + case_type with pagination.
      EXPLAIN ANALYZE hint: ensure ix_cases_owner_status and ix_cases_owner_type
      composite indexes are used; verify with EXPLAIN on:
        SELECT * FROM cases WHERE owner_id = ? AND status = ? ORDER BY updated_at DESC LIMIT ? OFFSET ?
    - Document listing: filtered by owner_id + case_id with content truncation.
      EXPLAIN ANALYZE hint: ix_documents_owner_case composite index covers:
        SELECT * FROM documents WHERE owner_id = ? AND case_id = ? ORDER BY updated_at DESC
    - Evidence chain analysis: ordered by case_id + sort_order.
      EXPLAIN ANALYZE hint: ix_evidences_case_sort covers:
        SELECT * FROM evidences WHERE case_id = ? ORDER BY sort_order, created_at DESC
    - Knowledge duplicate detection: lookup by owner_id + title.
      EXPLAIN ANALYZE hint: ix_knowledge_items_owner_title covers:
        SELECT * FROM knowledge_items WHERE owner_id = ? AND title = ?
    """
    session_id = id(object())  # lightweight unique-ish id for log correlation
    logger.debug("DB session opened: sid=%s", session_id)
    start = time.monotonic()
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
            elapsed = time.monotonic() - start
            if elapsed > 2.0:
                logger.warning(
                    "Slow DB session: sid=%s elapsed=%.3fs",
                    session_id, elapsed,
                )
            else:
                logger.debug(
                    "DB session committed: sid=%s elapsed=%.3fs",
                    session_id, elapsed,
                )
        except Exception:
            await session.rollback()
            elapsed = time.monotonic() - start
            logger.debug(
                "DB session rolled back: sid=%s elapsed=%.3fs",
                session_id, elapsed,
            )
            raise
        finally:
            logger.debug("DB session closed: sid=%s", session_id)


async def get_db_readonly() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — yields a read-only database session (no auto-commit).

    Use this for endpoints that only read data. Skipping the commit avoids
    an unnecessary round-trip and reduces write-load on the database.
    """
    session_id = id(object())
    logger.debug("DB readonly session opened: sid=%s", session_id)
    start = time.monotonic()
    async with AsyncSessionLocal() as session:
        try:
            yield session
            elapsed = time.monotonic() - start
            if elapsed > 2.0:
                logger.warning(
                    "Slow DB readonly session: sid=%s elapsed=%.3fs",
                    session_id, elapsed,
                )
            else:
                logger.debug(
                    "DB readonly session closed: sid=%s elapsed=%.3fs",
                    session_id, elapsed,
                )
        except Exception:
            await session.rollback()
            elapsed = time.monotonic() - start
            logger.debug(
                "DB readonly session rolled back: sid=%s elapsed=%.3fs",
                session_id, elapsed,
            )
            raise
        finally:
            logger.debug("DB readonly session finalized: sid=%s", session_id)


# ── Health check ────────────────────────────────────────────────────────────

async def db_health_check() -> dict:
    """Return a health status dict for monitoring / readiness probes."""
    start = time.monotonic()
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        latency_ms = (time.monotonic() - start) * 1000
        pool = engine.pool
        pool_stats = {
            "pool_size": getattr(pool, "size", lambda: None)(),
            "checked_in": getattr(pool, "checkedin", lambda: None)(),
            "checked_out": getattr(pool, "checkedout", lambda: None)(),
            "overflow": getattr(pool, "overflow", lambda: None)(),
        }
        return {
            "status": "ok",
            "latency_ms": round(latency_ms, 2),
            "database_url": (
                settings.DATABASE_URL.split("@")[-1]
                if "@" in settings.DATABASE_URL
                else "sqlite"
            ),
            "pool": pool_stats,
        }
    except Exception as exc:
        latency_ms = (time.monotonic() - start) * 1000
        logger.error("DB health check failed: %s", exc)
        return {
            "status": "error",
            "latency_ms": round(latency_ms, 2),
            "error": str(exc),
        }


# ── Graceful shutdown ───────────────────────────────────────────────────────

async def dispose_engine() -> None:
    """Dispose of the engine connection pool.  Call on app shutdown."""
    logger.info("Disposing database engine connection pool...")
    await engine.dispose()
    logger.info("Database engine disposed.")
