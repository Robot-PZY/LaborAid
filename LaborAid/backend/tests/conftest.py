"""Shared pytest fixtures for LaborAid backend tests.

Provides an isolated in-memory SQLite database per test, a test client
with authentication helpers, and commonly reused async utilities.
"""

import asyncio
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.pool import StaticPool
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.core.database import Base, get_db
from app.core.security import hash_password, create_access_token
from app.models.user import User


# ---------------------------------------------------------------------------
# Event-loop configuration
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def event_loop():
    """Provide a session-scoped asyncio event loop so async fixtures share it."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ---------------------------------------------------------------------------
# Per-test database engine (fresh in-memory DB each test)
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def test_engine():
    """Create a fresh async SQLAlchemy engine per test with a clean in-memory DB."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    # Clean up
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


# ---------------------------------------------------------------------------
# Per-test database session
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide a database session for the current test.

    Since the engine is fresh per test, no transaction tricks are needed.
    """
    TestSession = async_sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False,
    )
    async with TestSession() as session:
        yield session


# ---------------------------------------------------------------------------
# FastAPI test client with DB dependency override
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def client(db_session: AsyncSession, test_engine) -> AsyncGenerator[AsyncClient, None]:
    """Provide an httpx AsyncClient wired to the FastAPI app with the test DB."""
    from app.main import create_app

    app = create_app()

    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Test user helpers
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create and return a test user in the database."""
    user = User(
        name="测试用户",
        email="test@example.com",
        password_hash=hash_password("Test1234"),
        role="lawyer",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    # Refresh to get auto-generated fields (id, created_at, etc.)
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_admin(db_session: AsyncSession) -> User:
    """Create and return a test admin user in the database."""
    user = User(
        name="管理员",
        email="admin@example.com",
        password_hash=hash_password("Admin1234"),
        role="admin",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def auth_token(test_user: User) -> str:
    """Return a valid JWT access token for the test user."""
    return create_access_token({"sub": str(test_user.id), "email": test_user.email})


@pytest_asyncio.fixture
def auth_headers(auth_token: str) -> dict:
    """Return authorization headers for the test user."""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest_asyncio.fixture
async def admin_auth_token(test_admin: User) -> str:
    """Return a valid JWT access token for the test admin."""
    return create_access_token({"sub": str(test_admin.id), "email": test_admin.email})


@pytest_asyncio.fixture
def admin_auth_headers(admin_auth_token: str) -> dict:
    """Return authorization headers for the test admin."""
    return {"Authorization": f"Bearer {admin_auth_token}"}
