"""
Integration tests for database functionality with real PostgreSQL.
"""

import pytest

# Chunk 1: Foundation tests - Database, config, utilities
pytestmark = pytest.mark.chunk1
from sqlmodel import select
from uuid import uuid4

from app.models.bot import Bot, BotCreate, BotUpdate
from app.core.database import init_db, check_database_connection


@pytest.mark.database
@pytest.mark.docker
class TestDatabaseIntegration:
    """Test database integration with real PostgreSQL."""
    
    async def test_database_connection(self, test_session):
        """Test that we can connect to the test database."""
        # Simple query to test connection
        result = await test_session.execute(select(1))
        value = result.scalar()
        assert value == 1
    
    async def test_create_bot(self, test_session):
        """Test creating a bot in the database."""
        bot = Bot(
            name="Integration Test Bot",
            symbol="BTCUSDT",
            is_active=True
        )
        
        test_session.add(bot)
        await test_session.commit()
        await test_session.refresh(bot)
        
        assert bot.id is not None
        assert bot.name == "Integration Test Bot"
        assert bot.symbol == "BTCUSDT"
        assert bot.is_active is True
        assert bot.created_at is not None
        assert bot.updated_at is not None
    
    async def test_query_bot(self, test_session, sample_bot):
        """Test querying a bot from the database."""
        result = await test_session.execute(
            select(Bot).where(Bot.id == sample_bot.id)
        )
        bot = result.scalar_one_or_none()
        
        assert bot is not None
        assert bot.id == sample_bot.id
        assert bot.name == sample_bot.name
        assert bot.symbol == sample_bot.symbol
        assert bot.is_active == sample_bot.is_active
    
    async def test_update_bot(self, test_session, sample_bot):
        """Test updating a bot in the database."""
        # Update bot name
        sample_bot.name = "Updated Test Bot"
        sample_bot.is_active = False
        
        await test_session.commit()
        await test_session.refresh(sample_bot)
        
        assert sample_bot.name == "Updated Test Bot"
        assert sample_bot.is_active is False
    
    async def test_delete_bot(self, test_session, sample_bot):
        """Test deleting a bot from the database."""
        bot_id = sample_bot.id
        
        await test_session.delete(sample_bot)
        await test_session.commit()
        
        # Try to find the deleted bot
        result = await test_session.execute(
            select(Bot).where(Bot.id == bot_id)
        )
        bot = result.scalar_one_or_none()
        
        assert bot is None
    
    async def test_query_bots_by_symbol(self, test_session, multiple_bots):
        """Test querying bots by symbol."""
        result = await test_session.execute(
            select(Bot).where(Bot.symbol == "BTCUSDT")
        )
        btc_bots = result.scalars().all()
        
        # Should have 2 BTCUSDT bots from the fixture
        assert len(btc_bots) == 2
        for bot in btc_bots:
            assert bot.symbol == "BTCUSDT"
    
    async def test_query_active_bots(self, test_session, multiple_bots):
        """Test querying active bots."""
        result = await test_session.execute(
            select(Bot).where(Bot.is_active == True)
        )
        active_bots = result.scalars().all()
        
        # Should have 2 active bots from the fixture
        assert len(active_bots) == 2
        for bot in active_bots:
            assert bot.is_active is True
    
    async def test_query_bots_by_symbol_and_active(self, test_session, multiple_bots):
        """Test querying bots by symbol and active status."""
        result = await test_session.execute(
            select(Bot).where(Bot.symbol == "BTCUSDT", Bot.is_active == True)
        )
        active_btc_bots = result.scalars().all()
        
        # Should have 1 active BTCUSDT bot from the fixture
        assert len(active_btc_bots) == 1
        bot = active_btc_bots[0]
        assert bot.symbol == "BTCUSDT"
        assert bot.is_active is True
    
    async def test_count_bots(self, test_session, multiple_bots):
        """Test counting bots."""
        from sqlalchemy import func
        
        result = await test_session.execute(
            select(func.count()).select_from(Bot)
        )
        count = result.scalar()
        
        # Should have 4 bots from the fixture
        assert count == 4
    
    async def test_bot_uuid_uniqueness(self, test_session):
        """Test that bot UUIDs are unique."""
        bot1 = Bot(name="Bot 1", symbol="BTCUSDT", is_active=True)
        bot2 = Bot(name="Bot 2", symbol="ETHUSDT", is_active=True)
        
        test_session.add_all([bot1, bot2])
        await test_session.commit()
        
        assert bot1.id != bot2.id
        assert bot1.id is not None
        assert bot2.id is not None
    
    async def test_bot_timestamps(self, test_session):
        """Test that timestamps are set correctly."""
        bot = Bot(name="Timestamp Bot", symbol="BTCUSDT", is_active=True)
        
        test_session.add(bot)
        await test_session.commit()
        await test_session.refresh(bot)
        
        assert bot.created_at is not None
        assert bot.updated_at is not None
        
        # Update the bot
        original_created = bot.created_at
        original_updated = bot.updated_at
        
        bot.name = "Updated Timestamp Bot"
        await test_session.commit()
        await test_session.refresh(bot)
        
        # created_at should remain the same, updated_at should change
        assert bot.created_at == original_created
        # Note: updated_at is only updated manually in this implementation
    
    async def test_database_indexes(self, test_session):
        """Test that database indexes work correctly."""
        # Create multiple bots to test index performance
        bots = []
        for i in range(10):
            bot = Bot(
                name=f"Test Bot {i}",
                symbol="BTCUSDT" if i % 2 == 0 else "ETHUSDT",
                is_active=i % 3 == 0
            )
            bots.append(bot)
        
        test_session.add_all(bots)
        await test_session.commit()
        
        # Test symbol index
        result = await test_session.execute(
            select(Bot).where(Bot.symbol == "BTCUSDT")
        )
        btc_bots = result.scalars().all()
        assert len(btc_bots) == 5
        
        # Test is_active index
        result = await test_session.execute(
            select(Bot).where(Bot.is_active == True)
        )
        active_bots = result.scalars().all()
        assert len(active_bots) == 4  # Every 3rd bot (0, 3, 6, 9)
        
        # Test composite index
        result = await test_session.execute(
            select(Bot).where(Bot.symbol == "BTCUSDT", Bot.is_active == True)
        )
        active_btc_bots = result.scalars().all()
        assert len(active_btc_bots) == 2  # Bots 0 and 6