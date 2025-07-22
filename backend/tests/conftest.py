"""
Test configuration and fixtures for the OrderFox backend.
"""

import pytest
import pytest_asyncio
import asyncio
import os
from typing import AsyncGenerator
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel, Session

from app.core.database import get_session
from app.models.bot import Bot

# Test database configuration - use environment variable or default
TEST_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://orderfox_test_user:orderfox_test_password@localhost:5433/orderfox_test_db"
)
TEST_ASYNC_DATABASE_URL = TEST_DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """Create a test database engine."""
    engine = create_async_engine(
        TEST_ASYNC_DATABASE_URL,
        echo=False,
        future=True,
        pool_pre_ping=True,
    )
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    
    yield engine
    
    # Cleanup
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")  
async def test_session_factory(test_engine):
    """Create a test session factory."""
    return async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


@pytest_asyncio.fixture
async def test_session(test_session_factory) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async with test_session_factory() as session:
        # Clear bot service cache before each test to prevent cache pollution
        from app.services.bot_service import bot_service
        bot_service._clear_caches()
        
        yield session
        # Clean up all bots after each test
        await session.execute(text("DELETE FROM bots"))
        await session.commit()


@pytest.fixture
def override_get_session(test_session):
    """Override the get_session dependency for testing."""
    async def _get_session():
        yield test_session
    return _get_session


@pytest_asyncio.fixture
async def sample_bot(test_session: AsyncSession) -> Bot:
    """Create a sample bot for testing."""
    bot = Bot(
        name="Test Bot",
        symbol="BTCUSDT",
        is_active=True
    )
    
    test_session.add(bot)
    await test_session.commit()
    await test_session.refresh(bot)
    
    return bot


@pytest_asyncio.fixture
async def inactive_bot(test_session: AsyncSession) -> Bot:
    """Create an inactive bot for testing."""
    bot = Bot(
        name="Inactive Bot",
        symbol="ETHUSDT",
        is_active=False
    )
    
    test_session.add(bot)
    await test_session.commit()
    await test_session.refresh(bot)
    
    return bot


@pytest_asyncio.fixture
async def multiple_bots(test_session: AsyncSession) -> list[Bot]:
    """Create multiple bots for testing."""
    # Clean up any existing bots first to ensure consistent state
    await test_session.execute(text("DELETE FROM bots"))
    await test_session.commit()
    
    bots = [
        Bot(name="Bot 1", symbol="BTCUSDT", is_active=True),
        Bot(name="Bot 2", symbol="ETHUSDT", is_active=True),
        Bot(name="Bot 3", symbol="ADAUSDT", is_active=False),
        Bot(name="Bot 4", symbol="BTCUSDT", is_active=False),  # Same symbol as Bot 1
    ]
    
    for bot in bots:
        test_session.add(bot)
    
    await test_session.commit()
    
    for bot in bots:
        await test_session.refresh(bot)
    
    # Verify bots were created
    result = await test_session.execute(text("SELECT COUNT(*) FROM bots"))
    count = result.scalar()
    assert count == 4, f"Expected 4 bots, but found {count} in database"
    
    return bots


# Marker for tests that require database
pytest.mark.database = pytest.mark.asyncio


# Marker for tests that require Docker (PostgreSQL)
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "database: mark test as requiring database connection"
    )
    config.addinivalue_line(
        "markers", "docker: mark test as requiring Docker services"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers."""
    for item in items:
        # Add database marker to tests that use database fixtures
        if any(fixture_name in item.fixturenames for fixture_name in [
            'test_session', 'sample_bot', 'inactive_bot', 'multiple_bots'
        ]):
            item.add_marker(pytest.mark.database)
            item.add_marker(pytest.mark.docker)