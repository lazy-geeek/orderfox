import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.orderbook_manager import OrderBookManager, orderbook_manager
from app.models.orderbook import OrderBook


class TestOrderBookManager:
    """
    Comprehensive unit tests for OrderBookManager.
    Tests singleton pattern, connection lifecycle, and memory management.
    """

    @pytest.fixture
    async def manager(self):
        """Create a fresh manager instance for each test."""
        # Create a new instance for testing (bypass singleton for testing)
        manager = OrderBookManager.__new__(OrderBookManager)
        manager._initialized = False
        manager.__init__()
        yield manager
        # Cleanup after test
        await manager.shutdown()

    @pytest.fixture
    def mock_orderbook(self):
        """Create a mock orderbook."""
        orderbook = AsyncMock(spec=OrderBook)
        orderbook.symbol = "BTCUSDT"
        orderbook.get_levels_count.return_value = (100, 100)  # bid_count, ask_count
        return orderbook

    class TestSingletonPattern:
        """Test the singleton pattern implementation."""

        def test_singleton_behavior(self):
            """Test that only one instance is created."""
            # The global orderbook_manager should be the same instance
            manager1 = OrderBookManager()
            manager2 = OrderBookManager()
            
            assert manager1 is manager2
            assert manager1 is orderbook_manager

        def test_initialization_once(self):
            """Test that initialization only happens once."""
            manager1 = OrderBookManager()
            initial_orderbooks = manager1._orderbooks
            
            manager2 = OrderBookManager()
            
            # Should be the same object reference
            assert manager2._orderbooks is initial_orderbooks

    class TestConnectionRegistration:
        """Test connection registration and management."""

        @pytest.mark.asyncio
        async def test_register_new_connection(self, manager):
            """Test registering a new connection."""
            connection_id = "conn_1"
            symbol = "BTCUSDT"
            limit = 10
            rounding = 1.0
            
            # Mock OrderBook creation
            with patch('app.services.orderbook_manager.OrderBook') as mock_orderbook_class:
                mock_orderbook = AsyncMock(spec=OrderBook)
                mock_orderbook_class.return_value = mock_orderbook
                
                # Register connection
                orderbook = await manager.register_connection(connection_id, symbol, limit, rounding)
                
                # Verify connection is registered
                assert connection_id in manager._connection_params
                assert manager._connection_params[connection_id]['symbol'] == symbol
                assert manager._connection_params[connection_id]['limit'] == limit
                assert manager._connection_params[connection_id]['rounding'] == rounding
                assert 'connected_at' in manager._connection_params[connection_id]
                
                # Verify symbol tracking
                assert symbol in manager._connections
                assert connection_id in manager._connections[symbol]
                
                # Verify orderbook creation
                assert symbol in manager._orderbooks
                assert orderbook is not None

        @pytest.mark.asyncio
        async def test_register_multiple_connections_same_symbol(self, manager):
            """Test registering multiple connections for the same symbol."""
            symbol = "BTCUSDT"
            
            with patch('app.services.orderbook_manager.OrderBook') as mock_orderbook_class:
                mock_orderbook = AsyncMock(spec=OrderBook)
                mock_orderbook_class.return_value = mock_orderbook
                
                # Register first connection
                orderbook1 = await manager.register_connection("conn_1", symbol, 10, 1.0)
                
                # Register second connection for same symbol
                orderbook2 = await manager.register_connection("conn_2", symbol, 20, 0.5)
                
                # Should reuse the same orderbook
                assert orderbook1 is orderbook2
                assert len(manager._connections[symbol]) == 2
                assert "conn_1" in manager._connections[symbol]
                assert "conn_2" in manager._connections[symbol]
                
                # Should only create one orderbook
                mock_orderbook_class.assert_called_once()

        @pytest.mark.asyncio
        async def test_register_connections_different_symbols(self, manager):
            """Test registering connections for different symbols."""
            with patch('app.services.orderbook_manager.OrderBook') as mock_orderbook_class:
                mock_orderbook = AsyncMock(spec=OrderBook)
                mock_orderbook_class.return_value = mock_orderbook
                
                # Register connections for different symbols
                await manager.register_connection("conn_1", "BTCUSDT", 10, 1.0)
                await manager.register_connection("conn_2", "ETHUSDT", 10, 0.1)
                
                # Should create separate orderbooks
                assert "BTCUSDT" in manager._orderbooks
                assert "ETHUSDT" in manager._orderbooks
                assert len(manager._orderbooks) == 2
                assert mock_orderbook_class.call_count == 2

    class TestConnectionUnregistration:
        """Test connection unregistration and cleanup."""

        @pytest.mark.asyncio
        async def test_unregister_connection(self, manager):
            """Test unregistering a connection."""
            connection_id = "conn_1"
            symbol = "BTCUSDT"
            
            with patch('app.services.orderbook_manager.OrderBook') as mock_orderbook_class:
                mock_orderbook = AsyncMock(spec=OrderBook)
                mock_orderbook_class.return_value = mock_orderbook
                
                # Register and then unregister
                await manager.register_connection(connection_id, symbol, 10, 1.0)
                await manager.unregister_connection(connection_id)
                
                # Verify cleanup
                assert connection_id not in manager._connection_params
                assert connection_id not in manager._connections[symbol]

        @pytest.mark.asyncio
        async def test_unregister_last_connection_removes_orderbook(self, manager):
            """Test that removing the last connection removes the orderbook."""
            connection_id = "conn_1"
            symbol = "BTCUSDT"
            
            with patch('app.services.orderbook_manager.OrderBook') as mock_orderbook_class:
                mock_orderbook = AsyncMock(spec=OrderBook)
                mock_orderbook_class.return_value = mock_orderbook
                
                # Register and then unregister last connection
                await manager.register_connection(connection_id, symbol, 10, 1.0)
                await manager.unregister_connection(connection_id)
                
                # Orderbook should be removed in non-persistent mode
                assert symbol not in manager._orderbooks
                assert symbol not in manager._connections

        @pytest.mark.asyncio
        async def test_unregister_with_remaining_connections(self, manager):
            """Test unregistering when other connections remain."""
            symbol = "BTCUSDT"
            
            with patch('app.services.orderbook_manager.OrderBook') as mock_orderbook_class:
                mock_orderbook = AsyncMock(spec=OrderBook)
                mock_orderbook_class.return_value = mock_orderbook
                
                # Register multiple connections
                await manager.register_connection("conn_1", symbol, 10, 1.0)
                await manager.register_connection("conn_2", symbol, 20, 0.5)
                
                # Unregister one connection
                await manager.unregister_connection("conn_1")
                
                # Orderbook should remain as other connection exists
                assert symbol in manager._orderbooks
                assert "conn_2" in manager._connections[symbol]
                assert "conn_1" not in manager._connections[symbol]

        @pytest.mark.asyncio
        async def test_unregister_nonexistent_connection(self, manager):
            """Test unregistering a non-existent connection."""
            # Should not raise an error
            await manager.unregister_connection("nonexistent")
            
            # Should be no-op
            assert len(manager._connection_params) == 0

    class TestPersistentMode:
        """Test persistent mode functionality."""

        @pytest.mark.asyncio
        async def test_persistent_mode_setting(self, manager):
            """Test setting persistent mode."""
            assert manager._persistent_mode is False
            
            await manager.set_persistent_mode(True)
            assert manager._persistent_mode is True
            
            await manager.set_persistent_mode(False)
            assert manager._persistent_mode is False

        @pytest.mark.asyncio
        async def test_persistent_mode_preserves_orderbooks(self, manager):
            """Test that persistent mode preserves orderbooks after last connection."""
            connection_id = "conn_1"
            symbol = "BTCUSDT"
            
            with patch('app.services.orderbook_manager.OrderBook') as mock_orderbook_class:
                mock_orderbook = AsyncMock(spec=OrderBook)
                mock_orderbook_class.return_value = mock_orderbook
                
                # Enable persistent mode
                await manager.set_persistent_mode(True)
                
                # Register and unregister connection
                await manager.register_connection(connection_id, symbol, 10, 1.0)
                await manager.unregister_connection(connection_id)
                
                # Orderbook should remain in persistent mode
                assert symbol in manager._orderbooks

    class TestParameterUpdates:
        """Test connection parameter updates."""

        @pytest.mark.asyncio
        async def test_update_connection_params(self, manager):
            """Test updating connection parameters."""
            connection_id = "conn_1"
            symbol = "BTCUSDT"
            
            with patch('app.services.orderbook_manager.OrderBook') as mock_orderbook_class:
                mock_orderbook = AsyncMock(spec=OrderBook)
                mock_orderbook_class.return_value = mock_orderbook
                
                # Register connection
                await manager.register_connection(connection_id, symbol, 10, 1.0)
                
                # Update parameters
                result = await manager.update_connection_params(connection_id, limit=20, rounding=0.5)
                
                assert result is True
                assert manager._connection_params[connection_id]['limit'] == 20
                assert manager._connection_params[connection_id]['rounding'] == 0.5
                assert 'updated_at' in manager._connection_params[connection_id]

        @pytest.mark.asyncio
        async def test_update_nonexistent_connection_params(self, manager):
            """Test updating parameters for non-existent connection."""
            result = await manager.update_connection_params("nonexistent", limit=20)
            assert result is False

        @pytest.mark.asyncio
        async def test_partial_parameter_update(self, manager):
            """Test updating only some parameters."""
            connection_id = "conn_1"
            symbol = "BTCUSDT"
            
            with patch('app.services.orderbook_manager.OrderBook') as mock_orderbook_class:
                mock_orderbook = AsyncMock(spec=OrderBook)
                mock_orderbook_class.return_value = mock_orderbook
                
                # Register connection
                await manager.register_connection(connection_id, symbol, 10, 1.0)
                
                # Update only limit
                await manager.update_connection_params(connection_id, limit=20)
                
                assert manager._connection_params[connection_id]['limit'] == 20
                assert manager._connection_params[connection_id]['rounding'] == 1.0  # Unchanged

    class TestDataRetrieval:
        """Test data retrieval methods."""

        @pytest.mark.asyncio
        async def test_get_orderbook(self, manager):
            """Test getting orderbook by symbol."""
            symbol = "BTCUSDT"
            
            with patch('app.services.orderbook_manager.OrderBook') as mock_orderbook_class:
                mock_orderbook = AsyncMock(spec=OrderBook)
                mock_orderbook_class.return_value = mock_orderbook
                
                # No orderbook initially
                orderbook = await manager.get_orderbook(symbol)
                assert orderbook is None
                
                # Register connection to create orderbook
                await manager.register_connection("conn_1", symbol, 10, 1.0)
                
                # Should now return orderbook
                orderbook = await manager.get_orderbook(symbol)
                assert orderbook is mock_orderbook

        @pytest.mark.asyncio
        async def test_get_connections_for_symbol(self, manager):
            """Test getting connections for a symbol."""
            symbol = "BTCUSDT"
            
            with patch('app.services.orderbook_manager.OrderBook') as mock_orderbook_class:
                mock_orderbook = AsyncMock(spec=OrderBook)
                mock_orderbook_class.return_value = mock_orderbook
                
                # No connections initially
                connections = await manager.get_connections_for_symbol(symbol)
                assert connections == []
                
                # Register connections
                await manager.register_connection("conn_1", symbol, 10, 1.0)
                await manager.register_connection("conn_2", symbol, 20, 0.5)
                
                # Should return all connections
                connections = await manager.get_connections_for_symbol(symbol)
                assert len(connections) == 2
                assert "conn_1" in connections
                assert "conn_2" in connections

        @pytest.mark.asyncio
        async def test_get_connection_params(self, manager):
            """Test getting connection parameters."""
            connection_id = "conn_1"
            symbol = "BTCUSDT"
            
            with patch('app.services.orderbook_manager.OrderBook') as mock_orderbook_class:
                mock_orderbook = AsyncMock(spec=OrderBook)
                mock_orderbook_class.return_value = mock_orderbook
                
                # No params initially
                params = await manager.get_connection_params(connection_id)
                assert params is None
                
                # Register connection
                await manager.register_connection(connection_id, symbol, 10, 1.0)
                
                # Should return params
                params = await manager.get_connection_params(connection_id)
                assert params is not None
                assert params['symbol'] == symbol
                assert params['limit'] == 10
                assert params['rounding'] == 1.0

    class TestAggregation:
        """Test aggregation functionality."""

        @pytest.mark.asyncio
        async def test_get_aggregated_orderbook(self, manager):
            """Test getting aggregated orderbook data."""
            connection_id = "conn_1"
            symbol = "BTCUSDT"
            
            with patch('app.services.orderbook_manager.OrderBook') as mock_orderbook_class:
                mock_orderbook = AsyncMock(spec=OrderBook)
                mock_orderbook_class.return_value = mock_orderbook
                
                # Mock aggregation service
                mock_aggregated_data = {
                    'symbol': symbol,
                    'bids': [{'price': 50000.0, 'amount': 1.0, 'cumulative': 1.0}],
                    'asks': [{'price': 50001.0, 'amount': 1.0, 'cumulative': 1.0}]
                }
                manager._aggregation_service.aggregate_orderbook = AsyncMock(return_value=mock_aggregated_data)
                
                # Register connection
                await manager.register_connection(connection_id, symbol, 10, 1.0)
                
                # Get aggregated data
                result = await manager.get_aggregated_orderbook(connection_id)
                
                assert result == mock_aggregated_data
                manager._aggregation_service.aggregate_orderbook.assert_called_once()

        @pytest.mark.asyncio
        async def test_get_aggregated_orderbook_nonexistent_connection(self, manager):
            """Test getting aggregated data for non-existent connection."""
            result = await manager.get_aggregated_orderbook("nonexistent")
            assert result is None

    class TestSymbolData:
        """Test symbol data management."""

        @pytest.mark.asyncio
        async def test_update_symbol_data(self, manager):
            """Test updating symbol metadata."""
            symbol = "BTCUSDT"
            symbol_data = {'pricePrecision': 2, 'quantityPrecision': 6}
            
            await manager.update_symbol_data(symbol, symbol_data)
            
            assert symbol in manager._symbol_data
            assert manager._symbol_data[symbol] == symbol_data

    class TestMemoryManagement:
        """Test memory management and cleanup."""

        @pytest.mark.asyncio
        async def test_memory_cleanup_triggers(self, manager):
            """Test that memory cleanup triggers at threshold."""
            # Set low limits for testing
            manager._max_orderbooks = 5
            manager._cleanup_threshold = 0.6  # 60% = 3 orderbooks
            
            with patch('app.services.orderbook_manager.OrderBook') as mock_orderbook_class:
                mock_orderbook = AsyncMock(spec=OrderBook)
                mock_orderbook_class.return_value = mock_orderbook
                
                # Register connections to trigger cleanup
                for i in range(4):  # Exceeds 3 (60% of 5)
                    await manager.register_connection(f"conn_{i}", f"SYMBOL{i}", 10, 1.0)
                
                # Should trigger memory check
                assert len(manager._orderbooks) <= manager._max_orderbooks

        @pytest.mark.asyncio
        async def test_cleanup_old_orderbooks(self, manager):
            """Test cleanup of orderbooks with no connections."""
            with patch('app.services.orderbook_manager.OrderBook') as mock_orderbook_class:
                mock_orderbook = AsyncMock(spec=OrderBook)
                mock_orderbook_class.return_value = mock_orderbook
                
                # Register and unregister to create orphaned orderbook
                await manager.register_connection("conn_1", "BTCUSDT", 10, 1.0)
                await manager.unregister_connection("conn_1")
                
                # Manually add an orderbook without connections
                manager._orderbooks["ORPHANED"] = mock_orderbook
                
                # Run cleanup
                await manager._cleanup_old_orderbooks()
                
                # Orphaned orderbook should be removed
                assert "ORPHANED" not in manager._orderbooks

        @pytest.mark.asyncio
        async def test_no_cleanup_in_persistent_mode(self, manager):
            """Test that cleanup doesn't happen in persistent mode."""
            await manager.set_persistent_mode(True)
            
            with patch('app.services.orderbook_manager.OrderBook') as mock_orderbook_class:
                mock_orderbook = AsyncMock(spec=OrderBook)
                mock_orderbook_class.return_value = mock_orderbook
                
                # Add orderbook without connections
                manager._orderbooks["PERSISTENT"] = mock_orderbook
                
                # Run cleanup
                await manager._cleanup_old_orderbooks()
                
                # Should not be removed in persistent mode
                assert "PERSISTENT" in manager._orderbooks

    class TestCacheWarming:
        """Test cache warming functionality."""

        @pytest.mark.asyncio
        async def test_warm_cache_for_symbol(self, manager):
            """Test cache warming for a symbol."""
            symbol = "BTCUSDT"
            
            with patch('app.services.orderbook_manager.OrderBook') as mock_orderbook_class:
                mock_orderbook = AsyncMock(spec=OrderBook)
                mock_orderbook_class.return_value = mock_orderbook
                
                # Mock aggregation service
                manager._aggregation_service.warm_cache_for_symbol = AsyncMock()
                
                # Register connection (should trigger cache warming)
                await manager.register_connection("conn_1", symbol, 10, 1.0)
                
                # Allow async task to run
                await asyncio.sleep(0.01)
                
                # Should have called cache warming
                assert manager._aggregation_service.warm_cache_for_symbol.called

    class TestStatistics:
        """Test statistics and monitoring."""

        @pytest.mark.asyncio
        async def test_get_stats(self, manager):
            """Test getting manager statistics."""
            with patch('app.services.orderbook_manager.OrderBook') as mock_orderbook_class:
                mock_orderbook = AsyncMock(spec=OrderBook)
                mock_orderbook.get_levels_count.return_value = (100, 100)
                mock_orderbook_class.return_value = mock_orderbook
                
                # Mock cache metrics
                manager._aggregation_service.get_cache_metrics = AsyncMock(return_value={
                    'cache_hits': 10,
                    'cache_misses': 5,
                    'hit_rate_percent': 66.67
                })
                
                # Register some connections
                await manager.register_connection("conn_1", "BTCUSDT", 10, 1.0)
                await manager.register_connection("conn_2", "ETHUSDT", 20, 0.5)
                
                # Get stats
                stats = await manager.get_stats()
                
                assert 'total_connections' in stats
                assert 'active_orderbooks' in stats
                assert 'symbols' in stats
                assert 'persistent_mode' in stats
                assert 'memory_usage_estimate' in stats
                assert 'cache_metrics' in stats
                
                assert stats['total_connections'] == 2
                assert stats['active_orderbooks'] == 2
                assert len(stats['symbols']) == 2

    class TestShutdown:
        """Test shutdown functionality."""

        @pytest.mark.asyncio
        async def test_shutdown(self, manager):
            """Test manager shutdown."""
            with patch('app.services.orderbook_manager.OrderBook') as mock_orderbook_class:
                mock_orderbook = AsyncMock(spec=OrderBook)
                mock_orderbook_class.return_value = mock_orderbook
                
                # Register some connections
                await manager.register_connection("conn_1", "BTCUSDT", 10, 1.0)
                await manager.update_symbol_data("BTCUSDT", {'pricePrecision': 2})
                
                # Verify data exists
                assert len(manager._orderbooks) > 0
                assert len(manager._connections) > 0
                assert len(manager._connection_params) > 0
                assert len(manager._symbol_data) > 0
                
                # Shutdown
                await manager.shutdown()
                
                # All data should be cleared
                assert len(manager._orderbooks) == 0
                assert len(manager._connections) == 0
                assert len(manager._connection_params) == 0
                assert len(manager._symbol_data) == 0

    class TestConcurrency:
        """Test concurrent access handling."""

        @pytest.mark.asyncio
        async def test_concurrent_registration(self, manager):
            """Test concurrent connection registration."""
            with patch('app.services.orderbook_manager.OrderBook') as mock_orderbook_class:
                mock_orderbook = AsyncMock(spec=OrderBook)
                mock_orderbook_class.return_value = mock_orderbook
                
                # Register multiple connections concurrently
                tasks = []
                for i in range(10):
                    task = asyncio.create_task(
                        manager.register_connection(f"conn_{i}", "BTCUSDT", 10, 1.0)
                    )
                    tasks.append(task)
                
                # Wait for all to complete
                await asyncio.gather(*tasks)
                
                # Should have 10 connections for the same symbol
                assert len(manager._connections["BTCUSDT"]) == 10
                assert len(manager._connection_params) == 10
                # Should only create one orderbook
                assert len(manager._orderbooks) == 1

        @pytest.mark.asyncio
        async def test_concurrent_parameter_updates(self, manager):
            """Test concurrent parameter updates."""
            connection_id = "conn_1"
            symbol = "BTCUSDT"
            
            with patch('app.services.orderbook_manager.OrderBook') as mock_orderbook_class:
                mock_orderbook = AsyncMock(spec=OrderBook)
                mock_orderbook_class.return_value = mock_orderbook
                
                # Register connection
                await manager.register_connection(connection_id, symbol, 10, 1.0)
                
                # Update parameters concurrently
                tasks = [
                    asyncio.create_task(manager.update_connection_params(connection_id, limit=20)),
                    asyncio.create_task(manager.update_connection_params(connection_id, rounding=0.5)),
                    asyncio.create_task(manager.update_connection_params(connection_id, limit=30, rounding=2.0))
                ]
                
                results = await asyncio.gather(*tasks)
                
                # All updates should succeed
                assert all(results)
                
                # Final state should be consistent
                params = await manager.get_connection_params(connection_id)
                assert params is not None