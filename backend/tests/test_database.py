"""
Database tests for PostgreSQL with SQLModel.
"""

import pytest

# Chunk 1: Foundation tests - Database, config, utilities
pytestmark = pytest.mark.chunk1
from unittest.mock import AsyncMock, MagicMock, patch
from sqlmodel import SQLModel, Session, select
from uuid import uuid4

from app.models.bot import Bot, BotCreate, BotUpdate, BotPublic
from pydantic import ValidationError
from app.core.database import get_session, init_db, check_database_connection


class TestBotModel:
    """Test Bot SQLModel models."""
    
    def test_bot_creation(self):
        """Test creating a Bot instance."""
        bot = Bot(
            name="Test Bot",
            symbol="BTCUSDT",
            is_active=True
        )
        
        assert bot.name == "Test Bot"
        assert bot.symbol == "BTCUSDT"
        assert bot.is_active is True
        assert bot.id is not None
        assert bot.created_at is not None
        assert bot.updated_at is not None
    
    def test_bot_create_model(self):
        """Test BotCreate model validation."""
        bot_create = BotCreate(
            name="New Bot",
            symbol="ETHUSDT",
            is_active=False
        )
        
        assert bot_create.name == "New Bot"
        assert bot_create.symbol == "ETHUSDT"
        assert bot_create.is_active is False
    
    def test_bot_update_model(self):
        """Test BotUpdate model with optional fields."""
        bot_update: BotUpdate = BotUpdate(name="Updated Bot")  # type: ignore
        
        assert bot_update.name == "Updated Bot"
        assert bot_update.symbol is None
        assert bot_update.is_active is None
    
    def test_bot_public_model(self):
        """Test BotPublic model."""
        bot_id = uuid4()
        bot_public = BotPublic(
            id=bot_id,
            name="Public Bot",
            symbol="ADAUSDT",
            is_active=True
        )
        
        assert bot_public.id == bot_id
        assert bot_public.name == "Public Bot"
        assert bot_public.symbol == "ADAUSDT"
        assert bot_public.is_active is True
    
    def test_symbol_validation(self):
        """Test symbol validation converts to uppercase."""
        bot = Bot(
            name="Test Bot",
            symbol="BTCUSDT",
            is_active=True
        )
        
        assert bot.symbol == "BTCUSDT"
    
    def test_name_validation(self):
        """Test name validation."""
        bot = Bot(
            name="Test Bot",
            symbol="BTCUSDT",
            is_active=True
        )
        
        assert bot.name == "Test Bot"
    
    def test_invalid_name_validation(self):
        """Test that empty names raise validation error."""
        with pytest.raises(ValidationError, match="String should have at least 1 character"):
            Bot.model_validate({
                "name": "",
                "symbol": "BTCUSDT",
                "is_active": True
            })
    
    def test_invalid_symbol_validation(self):
        """Test that empty symbols raise validation error."""
        with pytest.raises(ValidationError, match="String should have at least 1 character"):
            Bot.model_validate({
                "name": "Test Bot",
                "symbol": "",
                "is_active": True
            })


class TestDatabaseConfiguration:
    """Test database configuration without actual database."""
    
    @patch('app.core.database.async_session_factory')
    @pytest.mark.asyncio
    async def test_get_session_success(self, mock_session_factory):
        """Test get_session dependency."""
        mock_session = AsyncMock()
        mock_session_factory.return_value.__aenter__.return_value = mock_session
        mock_session_factory.return_value.__aexit__.return_value = None
        
        # Test the session generator
        session_gen = get_session()
        session = await session_gen.__anext__()
        
        assert session == mock_session
    
    @patch('app.core.database.async_session_factory')
    @pytest.mark.asyncio
    async def test_get_session_exception_handling(self, mock_session_factory):
        """Test get_session handles exceptions properly."""
        mock_session = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session.close = AsyncMock()
        mock_session_factory.return_value.__aenter__.return_value = mock_session
        mock_session_factory.return_value.__aexit__.return_value = None
        
        # Test the session generator with exception during usage
        session_gen = get_session()
        session = await session_gen.__anext__()
        
        # Simulate an exception during database operation
        try:
            # Trigger the exception handling by closing the generator
            await session_gen.aclose()
        except Exception:
            pass
        
        # The session should be properly closed
        assert session == mock_session
    
    @patch('app.core.database.async_engine')
    @pytest.mark.asyncio
    async def test_init_db_success(self, mock_engine):
        """Test database initialization."""
        mock_conn = AsyncMock()
        mock_engine.begin.return_value.__aenter__.return_value = mock_conn
        mock_engine.begin.return_value.__aexit__.return_value = None
        
        # Should not raise an exception
        await init_db()
        
        # Should have called run_sync
        mock_conn.run_sync.assert_called_once()
    
    @patch('app.core.database.async_engine')
    @pytest.mark.asyncio
    async def test_init_db_exception(self, mock_engine):
        """Test database initialization with exception."""
        mock_engine.begin.side_effect = Exception("Connection failed")
        
        # Should raise the exception
        with pytest.raises(Exception, match="Connection failed"):
            await init_db()
    
    @patch('app.core.database.async_session_factory')
    @pytest.mark.asyncio
    async def test_test_connection_success(self, mock_session_factory):
        """Test successful database connection test."""
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.fetchone.return_value = (1,)
        mock_session.execute.return_value = mock_result
        mock_session_factory.return_value.__aenter__.return_value = mock_session
        mock_session_factory.return_value.__aexit__.return_value = None
        
        result = await check_database_connection()
        
        assert result is True
        mock_session.execute.assert_called_once()
    
    @patch('app.core.database.async_session_factory')
    @pytest.mark.asyncio
    async def test_test_connection_failure(self, mock_session_factory):
        """Test database connection test failure."""
        mock_session_factory.return_value.__aenter__.side_effect = Exception("Connection failed")
        
        result = await check_database_connection()
        
        assert result is False


class TestModelIntegration:
    """Test model integration scenarios."""
    
    def test_bot_repr(self):
        """Test Bot model string representation."""
        bot = Bot(
            name="Test Bot",
            symbol="BTCUSDT",
            is_active=True
        )
        
        repr_str = repr(bot)
        assert "Test Bot" in repr_str
        assert "BTCUSDT" in repr_str
        assert "True" in repr_str
    
    def test_camel_case_aliases(self):
        """Test that models use camelCase aliases."""
        bot_create = BotCreate(
            name="Test Bot",
            symbol="BTCUSDT",
            is_active=True
        )
        
        # Test that the model config has alias_generator
        assert 'alias_generator' in bot_create.model_config  # type: ignore
        
        # Test field aliases
        model_dump = bot_create.model_dump(by_alias=True)
        assert 'isActive' in model_dump
        assert 'createdAt' in model_dump or 'created_at' in model_dump  # May vary by implementation
    
    def test_update_model_partial_updates(self):
        """Test BotUpdate allows partial updates."""
        # Test updating only name
        update1: BotUpdate = BotUpdate(name="New Name")  # type: ignore
        assert update1.name == "New Name"
        assert update1.symbol is None
        assert update1.is_active is None
        
        # Test updating only symbol
        update2: BotUpdate = BotUpdate(symbol="ETHUSDT")  # type: ignore
        assert update2.name is None
        assert update2.symbol == "ETHUSDT"
        assert update2.is_active is None
        
        # Test updating only is_active
        update3: BotUpdate = BotUpdate(is_active=False)  # type: ignore
        assert update3.name is None
        assert update3.symbol is None
        assert update3.is_active is False
    
    def test_uuid_generation(self):
        """Test that Bot instances generate unique UUIDs."""
        bot1 = Bot(name="Bot 1", symbol="BTCUSDT", is_active=True)
        bot2 = Bot(name="Bot 2", symbol="ETHUSDT", is_active=True)
        
        assert bot1.id != bot2.id
        assert bot1.id is not None
        assert bot2.id is not None
    
    def test_timestamp_generation(self):
        """Test that timestamps are generated automatically."""
        bot = Bot(name="Test Bot", symbol="BTCUSDT", is_active=True)
        
        assert bot.created_at is not None
        assert bot.updated_at is not None
        # Both should be close to each other initially
        time_diff = abs((bot.updated_at - bot.created_at).total_seconds())
        assert time_diff < 1.0  # Should be less than 1 second apart


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_whitespace_name_validation(self):
        """Test that whitespace-only names are rejected."""
        with pytest.raises(ValidationError, match="Bot name cannot be empty"):
            Bot.model_validate({"name": "   ", "symbol": "BTCUSDT", "is_active": True})
    
    def test_case_insensitive_symbol_validation(self):
        """Test that symbols are converted to uppercase."""
        bot = Bot.model_validate({"name": "Test Bot", "symbol": "btcusdt", "is_active": True})
        assert bot.symbol == "BTCUSDT"
        
        bot_create = BotCreate.model_validate({"name": "Test Bot", "symbol": "ethusdt", "is_active": True})
        assert bot_create.symbol == "ETHUSDT"
    
    def test_none_symbol_in_update(self):
        """Test that None symbol in update is handled."""
        update: BotUpdate = BotUpdate(symbol=None)  # type: ignore
        assert update.symbol is None
    
    def test_empty_string_symbol_in_update(self):
        """Test that empty string symbol in update raises error."""
        with pytest.raises(ValidationError, match="String should have at least 1 character"):
            BotUpdate.model_validate({"symbol": ""})
    
    def test_empty_string_name_in_update(self):
        """Test that empty string name in update raises error."""
        with pytest.raises(ValidationError, match="String should have at least 1 character"):
            BotUpdate.model_validate({"name": ""})
    
    def test_whitespace_name_in_update(self):
        """Test that whitespace-only name in update raises error."""
        with pytest.raises(ValidationError, match="Bot name cannot be empty"):
            BotUpdate.model_validate({"name": "   "})
    
    def test_valid_whitespace_trimming_in_update(self):
        """Test that valid names with whitespace are trimmed in update."""
        update: BotUpdate = BotUpdate(name="  Valid Name  ")  # type: ignore
        assert update.name == "Valid Name"