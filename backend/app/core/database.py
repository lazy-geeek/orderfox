"""
Database configuration for PostgreSQL with SQLModel.
"""

from typing import AsyncGenerator, Optional
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel, Session, select
from sqlalchemy.pool import StaticPool
from contextlib import asynccontextmanager
import asyncpg
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# Database configuration from settings
DATABASE_URL = settings.DATABASE_URL
ASYNC_DATABASE_URL = settings.ASYNC_DATABASE_URL

# Create async engine
async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=True,
    pool_recycle=300,
)

# Create async session factory
async_session_factory = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Synchronous engine for migrations and initial setup
sync_engine = create_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=True,
    pool_recycle=300,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency to get database session.
    
    Yields:
        AsyncSession: Database session
    """
    async with async_session_factory() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    Initialize database tables.
    Creates all tables defined in SQLModel metadata.
    """
    try:
        # Import models to register them with SQLModel
        from app.models.bot import Bot
        
        # Create tables
        async with async_engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
        
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


async def test_connection() -> bool:
    """
    Test database connection.
    
    Returns:
        bool: True if connection successful, False otherwise
    """
    try:
        async with async_session_factory() as session:
            # Simple query to test connection
            result = await session.execute(select(1))
            await result.fetchone()
            logger.info("Database connection test successful")
            return True
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False


@asynccontextmanager
async def get_db_session():
    """
    Context manager for database sessions.
    
    Yields:
        AsyncSession: Database session
    """
    async with async_session_factory() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()


async def close_db():
    """
    Close database connections.
    """
    try:
        await async_engine.dispose()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database connections: {e}")
        raise


def get_sync_session() -> Session:
    """
    Get synchronous database session for migrations.
    
    Returns:
        Session: Synchronous database session
    """
    return Session(sync_engine)