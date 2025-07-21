"""
Tests for the Data Stream Manager service.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.services.data_stream_manager import DataStreamManager, data_stream_manager
from app.models.bot import Bot


@pytest.mark.database
@pytest.mark.docker
class TestDataStreamManager:
    """Test DataStreamManager with real database."""
    
    @pytest_asyncio.fixture
    async def stream_manager(self):
        """Create a fresh data stream manager instance for testing."""
        manager = DataStreamManager()
        # Clear any existing cache
        manager.clear_cache()
        return manager
    
    async def test_get_required_symbols_empty(self, stream_manager: DataStreamManager, test_session):
        """Test getting required symbols when no bots exist."""
        result = await stream_manager.get_required_symbols(test_session)
        
        assert result == set()
    
    async def test_get_required_symbols_with_active_bots(self, stream_manager: DataStreamManager, test_session, multiple_bots):
        """Test getting required symbols with active bots."""
        result = await stream_manager.get_required_symbols(test_session)
        
        # Should have 2 active symbols: BTCUSDT and ETHUSDT
        assert len(result) == 2
        assert "BTCUSDT" in result
        assert "ETHUSDT" in result
        assert "ADAUSDT" not in result  # This one is inactive
    
    async def test_get_required_symbols_caching(self, stream_manager: DataStreamManager, test_session, multiple_bots):
        """Test that required symbols are cached properly."""
        # First call should hit database
        result1 = await stream_manager.get_required_symbols(test_session)
        
        # Second call should hit cache
        result2 = await stream_manager.get_required_symbols(test_session)
        
        assert result1 == result2
        assert len(result1) == 2
    
    async def test_should_stream_symbol_true(self, stream_manager: DataStreamManager, test_session, multiple_bots):
        """Test should_stream_symbol returns True for active symbols."""
        result = await stream_manager.should_stream_symbol("BTCUSDT", test_session)
        assert result is True
        
        result = await stream_manager.should_stream_symbol("ETHUSDT", test_session)
        assert result is True
    
    async def test_should_stream_symbol_false(self, stream_manager: DataStreamManager, test_session, multiple_bots):
        """Test should_stream_symbol returns False for inactive symbols."""
        result = await stream_manager.should_stream_symbol("ADAUSDT", test_session)
        assert result is False
        
        result = await stream_manager.should_stream_symbol("NONEXISTENT", test_session)
        assert result is False
    
    async def test_update_active_streams_initial(self, stream_manager: DataStreamManager, test_session, multiple_bots):
        """Test updating active streams from initial empty state."""
        result = await stream_manager.update_active_streams(test_session)
        
        assert len(result['start']) == 2
        assert "BTCUSDT" in result['start']
        assert "ETHUSDT" in result['start']
        assert len(result['stop']) == 0
        
        # Check internal state
        active_streams = await stream_manager.get_active_streams()
        assert len(active_streams) == 2
        assert "BTCUSDT" in active_streams
        assert "ETHUSDT" in active_streams
    
    async def test_update_active_streams_no_changes(self, stream_manager: DataStreamManager, test_session, multiple_bots):
        """Test updating active streams when no changes are needed."""
        # Initial update
        await stream_manager.update_active_streams(test_session)
        
        # Second update should show no changes
        result = await stream_manager.update_active_streams(test_session)
        
        assert len(result['start']) == 0
        assert len(result['stop']) == 0
    
    async def test_update_active_streams_with_changes(self, stream_manager: DataStreamManager, test_session, multiple_bots):
        """Test updating active streams when bots change."""
        # Initial update
        await stream_manager.update_active_streams(test_session)
        
        # Deactivate one bot
        from app.services.bot_service import bot_service
        btc_bot = next(bot for bot in multiple_bots if bot.symbol == "BTCUSDT" and bot.is_active)
        await bot_service.set_bot_active_status(btc_bot.id, False, test_session)
        
        # Clear cache to force re-read
        stream_manager.clear_cache()
        
        # Update streams
        result = await stream_manager.update_active_streams(test_session)
        
        # Should only have ETHUSDT active now
        assert len(result['start']) == 0
        assert len(result['stop']) == 1
        assert "BTCUSDT" in result['stop']
    
    async def test_stream_reference_management(self, stream_manager: DataStreamManager):
        """Test stream reference counting."""
        # Add first reference
        is_first = await stream_manager.add_stream_reference("BTCUSDT")
        assert is_first is True
        
        # Add second reference
        is_first = await stream_manager.add_stream_reference("BTCUSDT")
        assert is_first is False
        
        # Check reference count
        count = await stream_manager.get_stream_reference_count("BTCUSDT")
        assert count == 2
        
        # Remove one reference
        is_last = await stream_manager.remove_stream_reference("BTCUSDT")
        assert is_last is False
        
        # Remove last reference
        is_last = await stream_manager.remove_stream_reference("BTCUSDT")
        assert is_last is True
        
        # Check reference count is zero
        count = await stream_manager.get_stream_reference_count("BTCUSDT")
        assert count == 0
    
    async def test_remove_nonexistent_reference(self, stream_manager: DataStreamManager):
        """Test removing reference for non-existent symbol."""
        is_last = await stream_manager.remove_stream_reference("NONEXISTENT")
        assert is_last is False
    
    async def test_get_active_streams(self, stream_manager: DataStreamManager):
        """Test getting active streams."""
        # Initially empty
        streams = await stream_manager.get_active_streams()
        assert len(streams) == 0
        
        # Add some references
        await stream_manager.add_stream_reference("BTCUSDT")
        await stream_manager.add_stream_reference("ETHUSDT")
        
        # Check active streams
        streams = await stream_manager.get_active_streams()
        assert len(streams) == 2
        assert "BTCUSDT" in streams
        assert "ETHUSDT" in streams
    
    async def test_get_stream_statistics(self, stream_manager: DataStreamManager):
        """Test getting stream statistics."""
        # Add some references
        await stream_manager.add_stream_reference("BTCUSDT")
        await stream_manager.add_stream_reference("BTCUSDT")
        await stream_manager.add_stream_reference("ETHUSDT")
        
        stats = await stream_manager.get_stream_statistics()
        
        assert stats['active_streams'] == 2
        assert stats['total_references'] == 3
        assert stats['symbols_with_references'] == 2
    
    async def test_optimize_streams(self, stream_manager: DataStreamManager, test_session, multiple_bots):
        """Test stream optimization."""
        # Update streams first
        await stream_manager.update_active_streams(test_session)
        
        # Get optimization metrics
        result = await stream_manager.optimize_streams(test_session)
        
        assert 'total_bots' in result
        assert 'active_bots' in result
        assert 'required_streams' in result
        assert 'active_streams' in result
        assert 'stream_efficiency' in result
        assert 'bot_to_stream_ratio' in result
        
        # Check specific values
        assert result['total_bots'] == 4  # From multiple_bots fixture
        assert result['active_bots'] == 2  # Two active bots
        assert result['required_streams'] == 2  # BTCUSDT and ETHUSDT
        assert result['active_streams'] == 2  # Should match required
        assert result['stream_efficiency'] == 1.0  # Perfect efficiency
        assert result['bot_to_stream_ratio'] == 1.0  # 2 bots / 2 streams
    
    async def test_clear_cache(self, stream_manager: DataStreamManager, test_session, multiple_bots):
        """Test cache clearing."""
        # Populate cache
        await stream_manager.get_required_symbols(test_session)
        assert len(stream_manager._active_symbols_cache) > 0
        
        # Clear cache
        stream_manager.clear_cache()
        assert len(stream_manager._active_symbols_cache) == 0
    
    async def test_health_check(self, stream_manager: DataStreamManager):
        """Test health check functionality."""
        # Add some references
        await stream_manager.add_stream_reference("BTCUSDT")
        
        health = await stream_manager.health_check()
        
        assert health['status'] == 'healthy'
        assert 'cache_size' in health
        assert 'cache_maxsize' in health
        assert 'cache_ttl' in health
        assert 'active_streams' in health
        assert 'total_references' in health
        assert 'timestamp' in health
        
        # Check specific values
        assert health['cache_maxsize'] == 10
        assert health['cache_ttl'] == 120
        assert health['active_streams'] == 1
        assert health['total_references'] == 1
    
    async def test_concurrent_access(self, stream_manager: DataStreamManager):
        """Test concurrent access to stream manager."""
        import asyncio
        
        async def add_references(symbol: str, count: int):
            for _ in range(count):
                await stream_manager.add_stream_reference(symbol)
        
        # Add references concurrently
        await asyncio.gather(
            add_references("BTCUSDT", 5),
            add_references("ETHUSDT", 3),
            add_references("ADAUSDT", 2)
        )
        
        stats = await stream_manager.get_stream_statistics()
        
        assert stats['active_streams'] == 3
        assert stats['total_references'] == 10
        assert stats['symbols_with_references'] == 3
    
    async def test_error_handling_get_required_symbols(self, stream_manager: DataStreamManager, test_session):
        """Test error handling in get_required_symbols."""
        # Mock bot_service to raise an exception
        with patch('app.services.data_stream_manager.bot_service') as mock_bot_service:
            mock_bot_service.get_active_symbols.side_effect = Exception("Database error")
            
            result = await stream_manager.get_required_symbols(test_session)
            
            # Should return empty set on error
            assert result == set()
    
    async def test_error_handling_update_active_streams(self, stream_manager: DataStreamManager, test_session):
        """Test error handling in update_active_streams."""
        # Mock get_required_symbols to raise an exception
        with patch.object(stream_manager, 'get_required_symbols', side_effect=Exception("Error")):
            result = await stream_manager.update_active_streams(test_session)
            
            # Should return empty lists on error
            assert result == {'start': [], 'stop': []}
    
    async def test_error_handling_should_stream_symbol(self, stream_manager: DataStreamManager, test_session):
        """Test error handling in should_stream_symbol."""
        # Mock get_required_symbols to raise an exception
        with patch.object(stream_manager, 'get_required_symbols', side_effect=Exception("Error")):
            result = await stream_manager.should_stream_symbol("BTCUSDT", test_session)
            
            # Should return False on error
            assert result is False
    
    async def test_error_handling_optimize_streams(self, stream_manager: DataStreamManager, test_session):
        """Test error handling in optimize_streams."""
        # Mock bot_service to raise an exception
        with patch('app.services.data_stream_manager.bot_service') as mock_bot_service:
            mock_bot_service.get_bot_stats_by_symbol.side_effect = Exception("Database error")
            
            result = await stream_manager.optimize_streams(test_session)
            
            # Should return error information
            assert 'error' in result
            assert result['error'] == "Database error"
    
    async def test_error_handling_health_check(self, stream_manager: DataStreamManager):
        """Test error handling in health_check."""
        # Mock get_stream_statistics to raise an exception
        with patch.object(stream_manager, 'get_stream_statistics', side_effect=Exception("Internal error")):
            result = await stream_manager.health_check()
            
            # Should return unhealthy status
            assert result['status'] == 'unhealthy'
            assert 'error' in result
            assert result['error'] == "Internal error"


@pytest.mark.asyncio
class TestDataStreamManagerUnit:
    """Unit tests for DataStreamManager without database."""
    
    async def test_global_instance_creation(self):
        """Test that global data_stream_manager instance is created."""
        assert data_stream_manager is not None
        assert isinstance(data_stream_manager, DataStreamManager)
    
    async def test_initialization(self):
        """Test DataStreamManager initialization."""
        manager = DataStreamManager()
        
        assert manager._active_symbols_cache.maxsize == 10
        assert manager._active_symbols_cache.ttl == 120
        assert len(manager._active_streams) == 0
        assert len(manager._stream_references) == 0
    
    async def test_cache_configuration(self):
        """Test cache configuration."""
        manager = DataStreamManager()
        
        # Test cache properties
        assert manager._active_symbols_cache.maxsize == 10
        assert manager._active_symbols_cache.ttl == 120
        
        # Test cache operations
        manager._active_symbols_cache['test'] = {'data'}
        assert len(manager._active_symbols_cache) == 1
        
        manager.clear_cache()
        assert len(manager._active_symbols_cache) == 0