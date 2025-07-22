"""
Integration test for bot paper trading flow.
Tests the complete CRUD flow with paper trading field.
"""

import pytest

# Chunk 7a: Bot Integration tests - Bot paper trading flows
pytestmark = pytest.mark.chunk7a
import pytest_asyncio
from uuid import uuid4
from app.models.bot import BotCreate, BotUpdate
from app.services.bot_service import BotService


@pytest.mark.database
@pytest.mark.docker
class TestBotPaperTradingFlow:
    """Test bot paper trading flow with real database."""
    
    @pytest_asyncio.fixture
    async def bot_service(self):
        """Create a bot service instance."""
        return BotService()
    
    async def test_bot_paper_trading_complete_flow(self, bot_service: BotService, test_session):
        """Test complete bot flow with paper trading field."""
        # Test 1: Create bot with paper trading enabled (default)
        bot_data = BotCreate(
            name="Paper Trading Bot",
            symbol="BTCUSDT",
            is_active=True
            # Note: is_paper_trading not specified, should default to True
        )
        
        created_bot = await bot_service.create_bot(bot_data, test_session)
        
        assert created_bot is not None
        assert created_bot.name == "Paper Trading Bot"
        assert created_bot.symbol == "BTCUSDT"
        assert created_bot.is_active is True
        assert created_bot.is_paper_trading is True  # Default value
        
        bot_id = created_bot.id
        
        # Test 2: Create bot with paper trading explicitly disabled
        bot_data_live = BotCreate(
            name="Live Trading Bot",
            symbol="ETHUSDT",
            is_active=True,
            is_paper_trading=False
        )
        
        live_bot = await bot_service.create_bot(bot_data_live, test_session)
        
        assert live_bot is not None
        assert live_bot.name == "Live Trading Bot"
        assert live_bot.symbol == "ETHUSDT"
        assert live_bot.is_active is True
        assert live_bot.is_paper_trading is False
        
        # Test 3: Update bot to toggle paper trading mode
        update_data = BotUpdate(
            name="Paper Trading Bot",  # Required field
            symbol="BTCUSDT",  # Required field
            is_active=True,  # Required field
            is_paper_trading=False  # Switch to live trading
        )
        
        updated_bot = await bot_service.update_bot(bot_id, update_data, test_session)
        
        assert updated_bot is not None
        assert updated_bot.id == bot_id
        assert updated_bot.is_paper_trading is False
        assert updated_bot.name == "Paper Trading Bot"  # Unchanged
        assert updated_bot.symbol == "BTCUSDT"  # Unchanged
        
        # Test 4: Toggle back to paper trading
        update_data2 = BotUpdate(
            name="Paper Trading Bot",  # Required field
            symbol="BTCUSDT",  # Required field
            is_active=True,  # Required field
            is_paper_trading=True  # Switch back to paper trading
        )
        
        updated_bot2 = await bot_service.update_bot(bot_id, update_data2, test_session)
        
        assert updated_bot2 is not None
        assert updated_bot2.id == bot_id
        assert updated_bot2.is_paper_trading is True
        
        # Test 5: Verify field persists across bot updates
        update_data3 = BotUpdate(
            name="Updated Bot Name",
            symbol="BTCUSDT",  # Required field
            is_active=False,
            is_paper_trading=True  # Keep previous value
        )
        
        updated_bot3 = await bot_service.update_bot(bot_id, update_data3, test_session)
        
        assert updated_bot3 is not None
        assert updated_bot3.id == bot_id
        assert updated_bot3.name == "Updated Bot Name"
        assert updated_bot3.is_active is False
        assert updated_bot3.is_paper_trading is True  # Should remain unchanged
        
        # Test 6: Get all bots and verify paper trading field is included
        all_bots = await bot_service.get_all_bots(test_session)
        
        assert all_bots.total >= 2  # At least the two we created
        
        # Find our bots
        paper_bot = next((b for b in all_bots.bots if b.id == bot_id), None)
        live_bot_found = next((b for b in all_bots.bots if b.id == live_bot.id), None)
        
        assert paper_bot is not None
        assert paper_bot.is_paper_trading is True
        
        assert live_bot_found is not None
        assert live_bot_found.is_paper_trading is False
    
    async def test_bot_paper_trading_edge_cases(self, bot_service: BotService, test_session):
        """Test edge cases for paper trading field."""
        # Test 1: Update only paper trading field
        bot_data = BotCreate(
            name="Edge Case Bot",
            symbol="ADAUSDT",
            is_active=True,
            is_paper_trading=True
        )
        
        bot = await bot_service.create_bot(bot_data, test_session)
        
        # Update only the paper trading field
        update_data = BotUpdate(
            name="Edge Case Bot",  # Required field
            symbol="ADAUSDT",  # Required field
            is_active=True,  # Required field
            is_paper_trading=False
        )
        
        updated_bot = await bot_service.update_bot(bot.id, update_data, test_session)
        
        # All other fields should remain unchanged
        assert updated_bot is not None
        assert updated_bot.name == bot.name
        assert updated_bot.symbol == bot.symbol
        assert updated_bot.is_active == bot.is_active
        assert updated_bot.is_paper_trading is False
        
        # Test 2: Create multiple bots with different paper trading states
        bots_to_create = [
            ("Bot 1", "BTCUSDT", True),
            ("Bot 2", "ETHUSDT", False),
            ("Bot 3", "ADAUSDT", True),
            ("Bot 4", "DOGEUSDT", False),
        ]
        
        created_bots = []
        for name, symbol, is_paper in bots_to_create:
            bot_data = BotCreate(
                name=name,
                symbol=symbol,
                is_active=True,
                is_paper_trading=is_paper
            )
            created_bot = await bot_service.create_bot(bot_data, test_session)
            created_bots.append(created_bot)
        
        # Verify all bots have correct paper trading state
        for i, bot in enumerate(created_bots):
            expected_is_paper = bots_to_create[i][2]
            assert bot.is_paper_trading == expected_is_paper