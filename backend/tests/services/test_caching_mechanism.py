import pytest

# Chunk 2: Core services - Symbol, exchange, formatting, caching
pytestmark = pytest.mark.chunk2
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.orderbook_aggregation_service import OrderBookAggregationService
from app.models.orderbook import OrderBook, OrderBookSnapshot, OrderBookLevel


class TestCachingMechanism:
    """
    Comprehensive unit tests for the caching mechanism in OrderBookAggregationService.
    Tests cache operations, TTL behavior, cleanup, metrics, and performance.
    """

    @pytest.fixture
    def service(self):
        """Create a fresh aggregation service for each test."""
        return OrderBookAggregationService()

    @pytest.fixture
    def mock_orderbook(self):
        """Create a mock orderbook with test data."""
        orderbook = AsyncMock(spec=OrderBook)
        orderbook.symbol = "BTCUSDT"
        orderbook.timestamp = 1640995200000  # Fixed timestamp
        
        # Mock snapshot data with enough levels to avoid retries
        mock_snapshot = MagicMock()
        # Generate 25 bids (descending prices)
        mock_snapshot.bids = [
            MagicMock(price=50000.0 - i, amount=1.0 + i * 0.1)
            for i in range(25)
        ]
        # Generate 25 asks (ascending prices)
        mock_snapshot.asks = [
            MagicMock(price=50001.0 + i, amount=1.5 + i * 0.1)
            for i in range(25)
        ]
        orderbook.get_snapshot.return_value = mock_snapshot
        
        return orderbook

    class TestCacheKeyGeneration:
        """Test cache key generation."""

        def test_cache_key_format(self, service):
            """Test cache key format is correct."""
            key = service._generate_cache_key("BTCUSDT", 10, 1.0, 1640995200.123)
            
            assert isinstance(key, str)
            assert "BTCUSDT" in key
            assert "10" in key
            assert "1.0" in key
            assert ":" in key  # Delimiter

        def test_cache_key_timestamp_rounding(self, service):
            """Test that timestamps are rounded to nearest second."""
            key1 = service._generate_cache_key("BTCUSDT", 10, 1.0, 1640995200.123)
            key2 = service._generate_cache_key("BTCUSDT", 10, 1.0, 1640995200.789)
            key3 = service._generate_cache_key("BTCUSDT", 10, 1.0, 1640995201.123)
            
            # Same second should produce same key
            assert key1 == key2
            # Different second should produce different key
            assert key1 != key3

        def test_cache_key_parameter_sensitivity(self, service):
            """Test that cache keys are sensitive to all parameters."""
            base_timestamp = 1640995200.0
            
            key_base = service._generate_cache_key("BTCUSDT", 10, 1.0, base_timestamp)
            key_diff_symbol = service._generate_cache_key("ETHUSDT", 10, 1.0, base_timestamp)
            key_diff_limit = service._generate_cache_key("BTCUSDT", 20, 1.0, base_timestamp)
            key_diff_rounding = service._generate_cache_key("BTCUSDT", 10, 0.5, base_timestamp)
            
            # All should be different
            keys = [key_base, key_diff_symbol, key_diff_limit, key_diff_rounding]
            assert len(set(keys)) == 4

    class TestCacheOperations:
        """Test basic cache operations."""

        @pytest.mark.asyncio
        async def test_cache_miss(self, service):
            """Test cache miss returns None."""
            result = await service._get_from_cache("nonexistent_key")
            assert result is None

        @pytest.mark.asyncio
        async def test_cache_set_and_get(self, service):
            """Test setting and getting cache data."""
            test_data = {"symbol": "BTCUSDT", "test": "data"}
            cache_key = "test_key"
            
            # Set cache
            await service._set_cache(cache_key, test_data)
            
            # Get from cache
            result = await service._get_from_cache(cache_key)
            assert result == test_data

        @pytest.mark.asyncio
        async def test_cache_overwrite(self, service):
            """Test overwriting existing cache data."""
            cache_key = "test_key"
            original_data = {"version": 1}
            updated_data = {"version": 2}
            
            # Set original data
            await service._set_cache(cache_key, original_data)
            result1 = await service._get_from_cache(cache_key)
            assert result1 == original_data
            
            # Overwrite with new data
            await service._set_cache(cache_key, updated_data)
            result2 = await service._get_from_cache(cache_key)
            assert result2 == updated_data

        @pytest.mark.asyncio
        async def test_cache_different_keys(self, service):
            """Test that different keys store different data."""
            data1 = {"key": "value1"}
            data2 = {"key": "value2"}
            
            await service._set_cache("key1", data1)
            await service._set_cache("key2", data2)
            
            result1 = await service._get_from_cache("key1")
            result2 = await service._get_from_cache("key2")
            
            assert result1 == data1
            assert result2 == data2

    class TestCacheTTL:
        """Test cache Time-To-Live behavior."""

        @pytest.mark.asyncio
        async def test_cache_expiry(self, service):
            """Test that cache entries expire after TTL."""
            # Set very short TTL for testing
            service._cache_ttl = 0.01  # 10ms
            
            test_data = {"expired": True}
            cache_key = "expiry_test"
            
            # Set cache
            await service._set_cache(cache_key, test_data)
            
            # Should hit immediately
            result1 = await service._get_from_cache(cache_key)
            assert result1 == test_data
            
            # Wait for expiry
            await asyncio.sleep(0.02)  # 20ms > 10ms TTL
            
            # Should miss after expiry
            result2 = await service._get_from_cache(cache_key)
            assert result2 is None

        @pytest.mark.asyncio
        async def test_cache_not_expired(self, service):
            """Test that cache entries don't expire before TTL."""
            # Set longer TTL
            service._cache_ttl = 1.0  # 1 second
            
            test_data = {"not_expired": True}
            cache_key = "no_expiry_test"
            
            # Set cache
            await service._set_cache(cache_key, test_data)
            
            # Wait less than TTL
            await asyncio.sleep(0.1)  # 100ms < 1s TTL
            
            # Should still hit
            result = await service._get_from_cache(cache_key)
            assert result == test_data

        @pytest.mark.asyncio
        async def test_expired_entry_cleanup(self, service):
            """Test that expired entries are cleaned up on access."""
            service._cache_ttl = 0.01  # 10ms
            
            test_data = {"cleanup": True}
            cache_key = "cleanup_test"
            
            # Set cache
            await service._set_cache(cache_key, test_data)
            
            # Verify entry exists in internal cache
            async with service._cache_lock:
                assert cache_key in service._cache
            
            # Wait for expiry
            await asyncio.sleep(0.02)
            
            # Access expired entry (should trigger cleanup)
            result = await service._get_from_cache(cache_key)
            assert result is None
            
            # Verify entry was removed from internal cache
            async with service._cache_lock:
                assert cache_key not in service._cache

    class TestCacheCleanup:
        """Test cache cleanup mechanisms."""

        @pytest.mark.asyncio
        async def test_cache_size_limit(self, service):
            """Test that cache size is limited."""
            # Fill cache beyond limit (100 entries)
            for i in range(105):
                await service._set_cache(f"key_{i}", {"data": i})
            
            # Cache should be cleaned up to stay within limit
            async with service._cache_lock:
                assert len(service._cache) <= 100

        @pytest.mark.asyncio
        async def test_cache_cleanup_removes_oldest(self, service):
            """Test that cleanup removes oldest entries first."""
            # Set a smaller limit for easier testing
            original_cleanup_threshold = service._cache_lock
            
            # Add entries sequentially
            test_entries = []
            for i in range(105):  # Exceed 100 limit
                key = f"key_{i}"
                data = {"data": i, "timestamp": time.time()}
                await service._set_cache(key, data)
                test_entries.append((key, data))
                
                # Small delay to ensure different timestamps
                await asyncio.sleep(0.001)
            
            # Verify cleanup occurred
            async with service._cache_lock:
                remaining_keys = set(service._cache.keys())
                
                # Some early keys should be removed
                assert len(remaining_keys) <= 100
                
                # Later keys should still exist
                for i in range(max(0, 105-100), 105):
                    assert f"key_{i}" in remaining_keys

        @pytest.mark.asyncio
        async def test_manual_cache_clear(self, service):
            """Test manual cache clearing."""
            # Add some entries
            for i in range(10):
                await service._set_cache(f"key_{i}", {"data": i})
            
            # Verify entries exist
            async with service._cache_lock:
                assert len(service._cache) == 10
            
            # Clear cache manually
            async with service._cache_lock:
                service._cache.clear()
            
            # Verify cache is empty
            async with service._cache_lock:
                assert len(service._cache) == 0

    class TestCacheMetrics:
        """Test cache metrics tracking."""

        @pytest.mark.asyncio
        async def test_metrics_initialization(self, service):
            """Test that metrics start at zero."""
            metrics = await service.get_cache_metrics()
            
            assert metrics['cache_hits'] == 0
            assert metrics['cache_misses'] == 0
            assert metrics['total_requests'] == 0
            assert metrics['hit_rate_percent'] == 0
            assert 'cache_size' in metrics

        @pytest.mark.asyncio
        async def test_cache_hit_tracking(self, service):
            """Test that cache hits are tracked correctly."""
            cache_key = "hit_test"
            test_data = {"hit": True}
            
            # Set cache
            await service._set_cache(cache_key, test_data)
            
            # Get initial metrics
            initial_metrics = await service.get_cache_metrics()
            
            # Perform cache hits
            for _ in range(3):
                result = await service._get_from_cache(cache_key)
                assert result == test_data
            
            # Check updated metrics
            final_metrics = await service.get_cache_metrics()
            
            assert final_metrics['cache_hits'] == initial_metrics['cache_hits'] + 3
            assert final_metrics['total_requests'] == initial_metrics['total_requests'] + 3

        @pytest.mark.asyncio
        async def test_cache_miss_tracking(self, service):
            """Test that cache misses are tracked correctly."""
            # Get initial metrics
            initial_metrics = await service.get_cache_metrics()
            
            # Perform cache misses
            for i in range(3):
                result = await service._get_from_cache(f"miss_key_{i}")
                assert result is None
            
            # Check updated metrics
            final_metrics = await service.get_cache_metrics()
            
            assert final_metrics['cache_misses'] == initial_metrics['cache_misses'] + 3
            assert final_metrics['total_requests'] == initial_metrics['total_requests'] + 3

        @pytest.mark.asyncio
        async def test_hit_rate_calculation(self, service):
            """Test that hit rate is calculated correctly."""
            cache_key = "rate_test"
            test_data = {"rate": True}
            
            # Set cache
            await service._set_cache(cache_key, test_data)
            
            # Perform 3 hits and 2 misses
            await service._get_from_cache(cache_key)  # Hit
            await service._get_from_cache(cache_key)  # Hit
            await service._get_from_cache(cache_key)  # Hit
            await service._get_from_cache("miss1")   # Miss
            await service._get_from_cache("miss2")   # Miss
            
            # Check hit rate (3 hits out of 5 total = 60%)
            metrics = await service.get_cache_metrics()
            expected_rate = (3 / 5) * 100
            assert abs(metrics['hit_rate_percent'] - expected_rate) < 0.01

        @pytest.mark.asyncio
        async def test_cache_size_tracking(self, service):
            """Test that cache size is tracked correctly."""
            # Add entries and check size tracking
            for i in range(5):
                await service._set_cache(f"size_key_{i}", {"data": i})
                
                metrics = await service.get_cache_metrics()
                assert metrics['cache_size'] == i + 1

    class TestCacheWarming:
        """Test cache warming functionality."""

        @pytest.mark.asyncio
        async def test_cache_warming_for_symbol(self, service, mock_orderbook):
            """Test cache warming for a symbol."""
            symbol = "BTCUSDT"
            symbol_data = {'pricePrecision': 2}
            
            # Mock to avoid actual cache warming delays
            mock_orderbook.latest_snapshot = True
            
            # Perform cache warming
            await service.warm_cache_for_symbol(symbol, mock_orderbook, symbol_data)
            
            # Verify that cache warming was attempted
            # (Cache should have some entries for common combinations)
            metrics = await service.get_cache_metrics()
            assert metrics['cache_size'] > 0

        @pytest.mark.asyncio
        async def test_cache_warming_error_handling(self, service, mock_orderbook):
            """Test that cache warming handles errors gracefully."""
            symbol = "BTCUSDT"
            
            # Make orderbook operations raise exceptions
            mock_orderbook.get_snapshot.side_effect = Exception("Test error")
            mock_orderbook.latest_snapshot = True
            
            # Cache warming should not raise exceptions
            try:
                await service.warm_cache_for_symbol(symbol, mock_orderbook, None)
            except Exception as e:
                pytest.fail(f"Cache warming should handle errors gracefully, but raised: {e}")

        @pytest.mark.asyncio
        async def test_cache_warming_with_no_snapshot(self, service, mock_orderbook):
            """Test cache warming when orderbook has no snapshot."""
            symbol = "BTCUSDT"
            
            # Set no latest snapshot
            mock_orderbook.latest_snapshot = None
            
            # Should handle gracefully
            await service.warm_cache_for_symbol(symbol, mock_orderbook, None)
            
            # Should complete without error

    class TestCacheIntegration:
        """Test cache integration with aggregation."""

        @pytest.mark.asyncio
        async def test_aggregation_uses_cache(self, service, mock_orderbook):
            """Test that aggregation uses cache when available."""
            # First call should miss cache and calculate
            result1 = await service.aggregate_orderbook(mock_orderbook, 10, 1.0)
            
            # Verify call was made to orderbook
            mock_orderbook.get_snapshot.assert_called_once()
            
            # Reset mock to track subsequent calls
            mock_orderbook.get_snapshot.reset_mock()
            
            # Second call with same parameters should use cache
            result2 = await service.aggregate_orderbook(mock_orderbook, 10, 1.0)
            
            # Should not call get_snapshot again (using cache)
            mock_orderbook.get_snapshot.assert_not_called()
            
            # Results should be identical
            assert result1 == result2

        @pytest.mark.asyncio
        async def test_aggregation_cache_miss_different_params(self, service, mock_orderbook):
            """Test that different parameters cause cache miss."""
            # First call
            result1 = await service.aggregate_orderbook(mock_orderbook, 10, 1.0)
            
            # Reset mock
            mock_orderbook.get_snapshot.reset_mock()
            
            # Second call with different parameters should miss cache
            result2 = await service.aggregate_orderbook(mock_orderbook, 20, 1.0)  # Different limit
            
            # Should call get_snapshot again (cache miss)
            mock_orderbook.get_snapshot.assert_called_once()

        @pytest.mark.asyncio
        async def test_aggregation_cache_expired(self, service, mock_orderbook):
            """Test that expired cache entries cause re-calculation."""
            # Set very short TTL
            service._cache_ttl = 0.01  # 10ms
            
            # First call
            result1 = await service.aggregate_orderbook(mock_orderbook, 10, 1.0)
            
            # Wait for cache to expire
            await asyncio.sleep(0.02)
            
            # Reset mock
            mock_orderbook.get_snapshot.reset_mock()
            
            # Second call should miss expired cache
            result2 = await service.aggregate_orderbook(mock_orderbook, 10, 1.0)
            
            # Should call get_snapshot again (expired cache)
            mock_orderbook.get_snapshot.assert_called_once()

    class TestCacheConcurrency:
        """Test cache behavior under concurrent access."""

        @pytest.mark.asyncio
        async def test_concurrent_cache_operations(self, service):
            """Test concurrent cache set/get operations."""
            async def cache_operation(i):
                key = f"concurrent_key_{i}"
                data = {"value": i}
                
                # Set and immediately get
                await service._set_cache(key, data)
                result = await service._get_from_cache(key)
                return result == data
            
            # Run multiple concurrent operations
            tasks = [asyncio.create_task(cache_operation(i)) for i in range(20)]
            results = await asyncio.gather(*tasks)
            
            # All operations should succeed
            assert all(results)

        @pytest.mark.asyncio
        async def test_concurrent_aggregation_same_params(self, service, mock_orderbook):
            """Test that concurrent aggregation calls produce consistent results."""
            # First, populate the cache with one call
            await service.aggregate_orderbook(mock_orderbook, 10, 1.0)
            initial_call_count = mock_orderbook.get_snapshot.call_count
            
            # Now make concurrent calls - these should use cache
            tasks = [
                asyncio.create_task(service.aggregate_orderbook(mock_orderbook, 10, 1.0))
                for _ in range(5)
            ]
            
            results = await asyncio.gather(*tasks)
            
            # All results should be identical
            first_result = results[0]
            assert all(result == first_result for result in results)
            
            # Should not have made additional calls due to caching
            final_call_count = mock_orderbook.get_snapshot.call_count
            assert final_call_count == initial_call_count

        @pytest.mark.asyncio
        async def test_cache_metrics_thread_safety(self, service):
            """Test that cache metrics are updated safely under concurrency."""
            async def perform_cache_operations():
                for i in range(10):
                    await service._set_cache(f"thread_key_{i}", {"data": i})
                    await service._get_from_cache(f"thread_key_{i}")  # Hit
                    await service._get_from_cache(f"miss_key_{i}")    # Miss
            
            # Run concurrent cache operations
            tasks = [asyncio.create_task(perform_cache_operations()) for _ in range(3)]
            await asyncio.gather(*tasks)
            
            # Verify metrics are consistent
            metrics = await service.get_cache_metrics()
            
            # Should have hits and misses from all tasks
            assert metrics['cache_hits'] >= 30  # 10 hits per task * 3 tasks
            assert metrics['cache_misses'] >= 30  # 10 misses per task * 3 tasks
            assert metrics['total_requests'] >= 60  # Total requests

    class TestCacheEdgeCases:
        """Test cache edge cases and error conditions."""

        @pytest.mark.asyncio
        async def test_cache_with_none_values(self, service):
            """Test caching None values."""
            cache_key = "none_test"
            
            # Set None value
            await service._set_cache(cache_key, None)
            
            # Should retrieve None (not cache miss)
            result = await service._get_from_cache(cache_key)
            assert result is None
            
            # Should count as cache hit, not miss
            metrics = await service.get_cache_metrics()
            assert metrics['cache_hits'] > 0

        @pytest.mark.asyncio
        async def test_cache_with_large_data(self, service):
            """Test caching large data structures."""
            cache_key = "large_data_test"
            
            # Create large data structure
            large_data = {
                'bids': [{'price': i, 'amount': i * 0.1} for i in range(1000)],
                'asks': [{'price': i + 50000, 'amount': i * 0.1} for i in range(1000)],
                'metadata': {'large': True}
            }
            
            # Should handle large data
            await service._set_cache(cache_key, large_data)
            result = await service._get_from_cache(cache_key)
            
            assert result == large_data

        @pytest.mark.asyncio
        async def test_cache_key_collision_resistance(self, service):
            """Test that cache keys are collision-resistant."""
            # These should produce different cache keys
            key1 = service._generate_cache_key("BTC", 10, 1.0, 1640995200.0)
            key2 = service._generate_cache_key("BTCU", 101, 0.0, 1640995200.0)  # Potential collision
            
            assert key1 != key2
            
            # Set different data for each
            await service._set_cache(key1, {"data": "btc"})
            await service._set_cache(key2, {"data": "btcu"})
            
            # Should retrieve correct data
            result1 = await service._get_from_cache(key1)
            result2 = await service._get_from_cache(key2)
            
            assert result1["data"] == "btc"
            assert result2["data"] == "btcu"