"""
Test configuration and fixtures.
"""
import asyncio
from datetime import datetime
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine, event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app


# Use SQLite for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
TEST_DATABASE_URL_SYNC = "sqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def async_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create async database session for testing."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_factory() as session:
        yield session
        await session.rollback()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def client(async_db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test client with database override."""

    async def override_get_db():
        yield async_db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def sample_user():
    """Create sample user data."""
    return {
        "id": 1,
        "name": "Test User",
        "email": "test@example.com",
        "role": "leader",
        "dept_id": 1,
    }


@pytest.fixture
def sample_department():
    """Create sample department data."""
    return {
        "id": 1,
        "name": "Test Department",
        "leader_id": 1,
    }


@pytest.fixture
def sample_task_data():
    """Create sample task data."""
    return {
        "title": "Test Task",
        "description": "Test task description",
        "lead_dept_id": 1,
        "deadline": datetime.utcnow(),
        "priority": "high",
    }


@pytest.fixture
def sample_assignment_data():
    """Create sample assignment data."""
    return {
        "dept_id": 2,
        "assigned_tasks": [{"title": "Subtask 1", "description": "Description"}],
        "deadline": datetime.utcnow(),
    }


@pytest.fixture
def sample_feedback_data():
    """Create sample feedback data."""
    return {
        "feedback_type": "agree",
        "reason": "Looks good",
        "proposed_changes": None,
    }


@pytest.fixture
def sample_conflict_data():
    """Create sample conflict data."""
    return {
        "task_id": 1,
        "conflict_summary": "Test conflict",
        "conflict_details": {"description": "Test conflict details"},
        "proposed_solutions": [{"id": 1, "description": "Solution 1"}],
        "urgency_level": "high",
    }
