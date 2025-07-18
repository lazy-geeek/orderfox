"""
Tests for the Bot Service.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID
from datetime import datetime

from app.services.bot_service import BotService
from app.models.bot import Bot, BotCreate, BotUpdate, BotPublic


@pytest.mark.database
@pytest.mark.docker
class TestBotService:
    """Test BotService with real database."""
    
    @pytest_asyncio.fixture
    async def bot_service(self):
        """Create a bot service instance."""
        return BotService()
    
    async def test_create_bot(self, bot_service: BotService, test_session):
        """Test creating a bot."""
        bot_data = BotCreate(
            name="Test Bot",
            symbol="BTCUSDT",
            is_active=True
        )
        
        result = await bot_service.create_bot(bot_data, test_session)
        
        assert isinstance(result, BotPublic)
        assert result.name == "Test Bot"
        assert result.symbol == "BTCUSDT"
        assert result.is_active is True
        assert result.id is not None
        assert result.created_at is not None
        assert result.updated_at is not None
    
    async def test_get_all_bots_empty(self, bot_service: BotService, test_session):
        """Test getting all bots when database is empty."""
        result = await bot_service.get_all_bots(test_session)
        
        assert result.bots == []
        assert result.total == 0
        assert result.page == 1
        assert result.page_size == 50
    
    async def test_get_all_bots_with_data(self, bot_service: BotService, test_session, multiple_bots):
        """Test getting all bots with data."""
        result = await bot_service.get_all_bots(test_session)
        
        assert len(result.bots) == 4
        assert result.total == 4
        assert result.page == 1
        assert result.page_size == 50
        
        # Check that bots are sorted by created_at desc
        created_times = [bot.created_at for bot in result.bots]
        assert created_times == sorted(created_times, reverse=True)
    
    async def test_get_all_bots_pagination(self, bot_service: BotService, test_session, multiple_bots):
        """Test bot pagination."""
        # Get first page with 2 bots per page
        result = await bot_service.get_all_bots(test_session, page=1, page_size=2)
        
        assert len(result.bots) == 2
        assert result.total == 4
        assert result.page == 1
        assert result.page_size == 2
        
        # Get second page
        result2 = await bot_service.get_all_bots(test_session, page=2, page_size=2)
        
        assert len(result2.bots) == 2
        assert result2.total == 4
        assert result2.page == 2
        assert result2.page_size == 2
        
        # Ensure different bots on different pages
        page1_ids = {bot.id for bot in result.bots}
        page2_ids = {bot.id for bot in result2.bots}
        assert page1_ids.isdisjoint(page2_ids)
    
    async def test_get_bot_existing(self, bot_service: BotService, test_session, sample_bot):
        """Test getting an existing bot."""
        result = await bot_service.get_bot(sample_bot.id, test_session)
        
        assert result is not None
        assert result.id == sample_bot.id
        assert result.name == sample_bot.name
        assert result.symbol == sample_bot.symbol
        assert result.is_active == sample_bot.is_active
    
    async def test_get_bot_nonexistent(self, bot_service: BotService, test_session):
        """Test getting a non-existent bot."""
        fake_id = uuid4()
        result = await bot_service.get_bot(fake_id, test_session)
        
        assert result is None
    
    async def test_update_bot_existing(self, bot_service: BotService, test_session, sample_bot):
        """Test updating an existing bot."""
        update_data = BotUpdate(
            name="Updated Bot",
            is_active=False
        )
        
        result = await bot_service.update_bot(sample_bot.id, update_data, test_session)
        
        assert result is not None
        assert result.id == sample_bot.id
        assert result.name == "Updated Bot"
        assert result.symbol == sample_bot.symbol  # Unchanged
        assert result.is_active is False
        assert result.updated_at >= sample_bot.updated_at
    
    async def test_update_bot_nonexistent(self, bot_service: BotService, test_session):
        """Test updating a non-existent bot."""
        fake_id = uuid4()
        update_data = BotUpdate(name="Updated Bot")
        
        result = await bot_service.update_bot(fake_id, update_data, test_session)
        
        assert result is None
    
    async def test_delete_bot_existing(self, bot_service: BotService, test_session, sample_bot):
        """Test deleting an existing bot."""
        bot_id = sample_bot.id
        
        result = await bot_service.delete_bot(bot_id, test_session)
        
        assert result is True
        
        # Verify bot is deleted
        deleted_bot = await bot_service.get_bot(bot_id, test_session)
        assert deleted_bot is None
    
    async def test_delete_bot_nonexistent(self, bot_service: BotService, test_session):
        """Test deleting a non-existent bot."""
        fake_id = uuid4()
        
        result = await bot_service.delete_bot(fake_id, test_session)
        
        assert result is False
    
    async def test_get_active_symbols_empty(self, bot_service: BotService, test_session):
        """Test getting active symbols when no bots exist."""
        result = await bot_service.get_active_symbols(test_session)
        
        assert result == []
    
    async def test_get_active_symbols_with_data(self, bot_service: BotService, test_session, multiple_bots):
        """Test getting active symbols with data."""
        result = await bot_service.get_active_symbols(test_session)
        
        # Should have 2 active symbols: BTCUSDT and ETHUSDT
        assert len(result) == 2
        assert "BTCUSDT" in result
        assert "ETHUSDT" in result
        assert "ADAUSDT" not in result  # This one is inactive
    
    async def test_get_bot_stats_by_symbol(self, bot_service: BotService, test_session, multiple_bots):
        """Test getting bot statistics by symbol."""
        result = await bot_service.get_bot_stats_by_symbol(test_session)
        
        # Should have stats for 3 symbols
        assert len(result) == 3
        
        # Find stats for each symbol
        btc_stats = next(s for s in result if s.symbol == "BTCUSDT")
        eth_stats = next(s for s in result if s.symbol == "ETHUSDT")
        ada_stats = next(s for s in result if s.symbol == "ADAUSDT")
        
        assert btc_stats.total_count == 2  # Bot 1 (active) + Bot 4 (inactive)
        assert btc_stats.active_count == 1
        
        assert eth_stats.total_count == 1  # Bot 2 (active)
        assert eth_stats.active_count == 1
        
        assert ada_stats.total_count == 1  # Bot 3 (inactive)
        assert ada_stats.active_count == 0
    
    async def test_get_bots_by_symbol(self, bot_service: BotService, test_session, multiple_bots):
        """Test getting bots by symbol."""
        # Get all BTCUSDT bots
        result = await bot_service.get_bots_by_symbol("BTCUSDT", test_session)
        
        assert len(result) == 2
        for bot in result:
            assert bot.symbol == "BTCUSDT"
        
        # Get only active BTCUSDT bots
        active_result = await bot_service.get_bots_by_symbol("BTCUSDT", test_session, active_only=True)
        
        assert len(active_result) == 1
        assert active_result[0].symbol == "BTCUSDT"
        assert active_result[0].is_active is True
    
    async def test_set_bot_active_status(self, bot_service: BotService, test_session, sample_bot):
        """Test setting bot active status."""
        # Deactivate bot
        result = await bot_service.set_bot_active_status(sample_bot.id, False, test_session)
        
        assert result is not None
        assert result.id == sample_bot.id
        assert result.is_active is False
        assert result.updated_at >= sample_bot.updated_at
        
        # Activate bot
        result2 = await bot_service.set_bot_active_status(sample_bot.id, True, test_session)
        
        assert result2 is not None
        assert result2.id == sample_bot.id
        assert result2.is_active is True
        assert result2.updated_at >= result.updated_at
    
    async def test_set_bot_active_status_nonexistent(self, bot_service: BotService, test_session):
        """Test setting active status for non-existent bot."""
        fake_id = uuid4()
        
        result = await bot_service.set_bot_active_status(fake_id, True, test_session)
        
        assert result is None
    
    async def test_caching_behavior(self, bot_service: BotService, test_session, sample_bot):
        """Test that caching works correctly."""
        # Clear cache first
        bot_service._clear_caches()
        
        # First call should hit database
        result1 = await bot_service.get_bot(sample_bot.id, test_session)
        
        # Second call should hit cache
        result2 = await bot_service.get_bot(sample_bot.id, test_session)
        
        assert result1 == result2
        
        # Check cache stats
        stats = bot_service.get_cache_stats()
        assert stats["bot_cache_size"] > 0
        assert stats["bot_cache_ttl"] == 300
    
    async def test_cache_clearing_on_update(self, bot_service: BotService, test_session, sample_bot):
        """Test that cache is cleared when bot is updated."""
        # Populate cache
        await bot_service.get_bot(sample_bot.id, test_session)
        await bot_service.get_all_bots(test_session)
        
        # Verify cache has data
        stats_before = bot_service.get_cache_stats()
        assert stats_before["bot_cache_size"] > 0
        
        # Update bot (should clear cache)
        update_data = BotUpdate(name="Updated Bot")
        await bot_service.update_bot(sample_bot.id, update_data, test_session)
        
        # Verify cache is cleared
        stats_after = bot_service.get_cache_stats()
        assert stats_after["bot_cache_size"] == 0
    
    async def test_error_handling_on_create(self, bot_service: BotService, test_session):
        """Test error handling during bot creation."""
        # Test with invalid data that should cause a database error
        bot_data = BotCreate(
            name="Test Bot",
            symbol="BTCUSDT",
            is_active=True
        )
        
        # Mock session to raise an exception
        with patch.object(test_session, 'commit', side_effect=Exception("Database error")):
            with pytest.raises(Exception, match="Database error"):
                await bot_service.create_bot(bot_data, test_session)
    
    async def test_error_handling_on_update(self, bot_service: BotService, test_session, sample_bot):
        """Test error handling during bot update."""
        update_data = BotUpdate(name="Updated Bot")
        
        # Mock session to raise an exception
        with patch.object(test_session, 'commit', side_effect=Exception("Database error")):
            with pytest.raises(Exception, match="Database error"):
                await bot_service.update_bot(sample_bot.id, update_data, test_session)
    
    async def test_partial_update(self, bot_service: BotService, test_session, sample_bot):
        """Test partial updates work correctly."""
        original_name = sample_bot.name
        original_symbol = sample_bot.symbol
        original_active = sample_bot.is_active
        
        # Update only the name
        update_data = BotUpdate(name="New Name Only")
        
        result = await bot_service.update_bot(sample_bot.id, update_data, test_session)
        
        assert result is not None
        assert result.name == "New Name Only"
        assert result.symbol == original_symbol  # Unchanged
        assert result.is_active == original_active  # Unchanged
        
        # Update only the active status
        update_data2 = BotUpdate(is_active=False)
        
        result2 = await bot_service.update_bot(sample_bot.id, update_data2, test_session)
        
        assert result2 is not None
        assert result2.name == "New Name Only"  # Previous update preserved
        assert result2.symbol == original_symbol  # Still unchanged
        assert result2.is_active is False  # Now changed