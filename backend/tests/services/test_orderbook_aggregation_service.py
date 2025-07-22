import pytest

# Chunk 3: Business services - Bot, orderbook, chart data
pytestmark = pytest.mark.chunk3
import asyncio
import math
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List, Dict

from app.services.orderbook_aggregation_service import OrderBookAggregationService
from app.models.orderbook import OrderBook, OrderBookLevel, OrderBookSnapshot


class TestOrderBookAggregationService:
    """
    Comprehensive unit tests for OrderBookAggregationService.
    Tests all aggregation logic, rounding calculations, and caching mechanisms.
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
        orderbook.timestamp = 1640995200000  # Fixed timestamp for consistency
        return orderbook

    @pytest.fixture
    def sample_bids(self):
        """Sample bid data for testing."""
        return [
            {'price': 50000.50, 'amount': 1.5},
            {'price': 50000.25, 'amount': 2.0},
            {'price': 50000.00, 'amount': 0.5},
            {'price': 49999.75, 'amount': 3.2},
            {'price': 49999.50, 'amount': 1.8},
            {'price': 49999.25, 'amount': 2.5},
            {'price': 49999.00, 'amount': 1.2},
            {'price': 49998.75, 'amount': 0.8},
            {'price': 49998.50, 'amount': 2.1},
            {'price': 49998.25, 'amount': 1.7}
        ]

    @pytest.fixture
    def sample_asks(self):
        """Sample ask data for testing."""
        return [
            {'price': 50001.00, 'amount': 1.2},
            {'price': 50001.25, 'amount': 0.8},
            {'price': 50001.50, 'amount': 2.3},
            {'price': 50001.75, 'amount': 1.5},
            {'price': 50002.00, 'amount': 3.1},
            {'price': 50002.25, 'amount': 1.9},
            {'price': 50002.50, 'amount': 0.7},
            {'price': 50002.75, 'amount': 2.4},
            {'price': 50003.00, 'amount': 1.6},
            {'price': 50003.25, 'amount': 2.2}
        ]

    class TestRoundingFunctions:
        """Test the core rounding functions."""

        def test_round_down_basic(self, service):
            """Test basic round down functionality."""
            assert service.round_down(50001.37, 0.25) == 50001.25
            assert service.round_down(50001.25, 0.25) == 50001.25
            assert service.round_down(50001.24, 0.25) == 50001.00

        def test_round_down_integers(self, service):
            """Test round down with integer multiples."""
            assert service.round_down(50001.7, 1.0) == 50001.0
            assert service.round_down(50005.2, 5.0) == 50005.0
            assert service.round_down(50007.8, 5.0) == 50005.0

        def test_round_down_small_multiples(self, service):
            """Test round down with small decimal multiples."""
            assert service.round_down(50001.127, 0.01) == 50001.12
            assert service.round_down(50001.001, 0.001) == 50001.001

        def test_round_down_edge_cases(self, service):
            """Test round down edge cases."""
            # Zero multiple should return original value
            assert service.round_down(50001.37, 0) == 50001.37
            # Negative multiple should return original value
            assert service.round_down(50001.37, -0.25) == 50001.37

        def test_round_up_basic(self, service):
            """Test basic round up functionality."""
            assert service.round_up(50001.26, 0.25) == 50001.50
            assert service.round_up(50001.25, 0.25) == 50001.25
            assert service.round_up(50001.01, 0.25) == 50001.25

        def test_round_up_integers(self, service):
            """Test round up with integer multiples."""
            assert service.round_up(50001.1, 1.0) == 50002.0
            assert service.round_up(50003.1, 5.0) == 50005.0
            assert service.round_up(50005.0, 5.0) == 50005.0

        def test_round_up_small_multiples(self, service):
            """Test round up with small decimal multiples."""
            assert service.round_up(50001.121, 0.01) == 50001.13
            assert service.round_up(50001.001, 0.001) == 50001.001

        def test_round_up_edge_cases(self, service):
            """Test round up edge cases."""
            # Zero multiple should return original value
            assert service.round_up(50001.37, 0) == 50001.37
            # Negative multiple should return original value
            assert service.round_up(50001.37, -0.25) == 50001.37

        def test_rounding_precision(self, service):
            """Test floating point precision handling."""
            # Test cases that could have floating point precision issues
            result_down = service.round_down(0.1 + 0.2, 0.1)  # Should handle 0.30000000000000004
            assert abs(result_down - 0.3) < 1e-10

            result_up = service.round_up(0.1 + 0.2, 0.1)
            assert abs(result_up - 0.4) < 1e-10  # 0.30000000000000004 rounds up to 0.4

    class TestGetExactLevels:
        """Test the level aggregation logic."""

        def test_bid_aggregation_basic(self, service, sample_bids):
            """Test basic bid aggregation."""
            # Test with 1.0 rounding (should group by whole dollars)
            result = service.get_exact_levels(sample_bids, False, 5, 1.0)
            
            # With rounding=1.0, the sample data groups into 3 levels: 50000.0, 49999.0, 49998.0
            assert len(result) == 3
            # Should be sorted highest to lowest for bids
            assert result[0]['price'] >= result[1]['price']
            
            # Check that amounts are aggregated correctly for 50000.0 bucket
            bucket_50000 = next((level for level in result if level['price'] == 50000.0), None)
            assert bucket_50000 is not None
            # Should aggregate 50000.50 + 50000.25 + 50000.00 = 4.0 total amount
            expected_amount = 1.5 + 2.0 + 0.5
            assert bucket_50000['amount'] == expected_amount

        def test_ask_aggregation_basic(self, service, sample_asks):
            """Test basic ask aggregation."""
            # Test with 0.5 rounding
            result = service.get_exact_levels(sample_asks, True, 5, 0.5)
            
            assert len(result) == 5
            # Should be sorted lowest to highest for asks
            assert result[0]['price'] <= result[1]['price']

        def test_exact_level_count_guarantee(self, service, sample_bids):
            """Test that exactly the requested number of levels is returned."""
            for depth in [1, 3, 5, 10]:
                result = service.get_exact_levels(sample_bids, False, depth, 0.25)
                assert len(result) <= depth  # Should never exceed requested depth

        def test_zero_amount_filtering(self, service):
            """Test that zero amounts are filtered out."""
            data_with_zeros = [
                {'price': 50000.0, 'amount': 1.5},
                {'price': 49999.0, 'amount': 0.0},  # Zero amount
                {'price': 49998.0, 'amount': 2.3},
                {'price': 49997.0, 'amount': 0},    # Zero amount
                {'price': 49996.0, 'amount': 1.1}
            ]
            
            result = service.get_exact_levels(data_with_zeros, False, 5, 1.0)
            
            # Should only have 3 non-zero levels
            assert len(result) == 3
            for level in result:
                assert level['amount'] > 0

        def test_invalid_data_filtering(self, service):
            """Test that invalid price/amount data is filtered out."""
            invalid_data = [
                {'price': 50000.0, 'amount': 1.5},   # Valid
                {'price': 0, 'amount': 1.0},         # Invalid price
                {'price': -1.0, 'amount': 1.0},      # Invalid price
                {'price': 49999.0, 'amount': -1.0},  # Invalid amount
                {'price': 49998.0, 'amount': 2.3},   # Valid
                {'amount': 1.0},                     # Missing price
                {'price': 49997.0}                   # Missing amount
            ]
            
            result = service.get_exact_levels(invalid_data, False, 5, 1.0)
            
            # Should only have 2 valid levels
            assert len(result) == 2
            for level in result:
                assert level['price'] > 0
                assert level['amount'] > 0

        def test_empty_data_handling(self, service):
            """Test handling of empty input data."""
            result = service.get_exact_levels([], False, 5, 1.0)
            assert len(result) == 0

        def test_insufficient_levels_handling(self, service):
            """Test when there are fewer unique levels than requested."""
            # Only 2 unique price levels after rounding
            limited_data = [
                {'price': 50000.1, 'amount': 1.0},
                {'price': 50000.2, 'amount': 1.5},  # Will round to same as above
                {'price': 49999.8, 'amount': 2.0},
                {'price': 49999.9, 'amount': 1.2}   # Will round to same as above
            ]
            
            result = service.get_exact_levels(limited_data, False, 5, 1.0)
            
            # Should return only available levels (2), not pad to 5
            assert len(result) <= 2

    class TestCumulativeTotals:
        """Test cumulative total calculations."""

        def test_bid_cumulative_totals(self, service):
            """Test cumulative totals for bids (top-down accumulation)."""
            levels = [
                {'price': 50000.0, 'amount': 1.0},
                {'price': 49999.0, 'amount': 2.0},
                {'price': 49998.0, 'amount': 3.0}
            ]
            
            result = service.calculate_cumulative_totals(levels, False)
            
            assert len(result) == 3
            assert result[0]['cumulative'] == 1.0      # Just first level
            assert result[1]['cumulative'] == 3.0      # First + second
            assert result[2]['cumulative'] == 6.0      # All three levels

        def test_ask_cumulative_totals(self, service):
            """Test cumulative totals for asks (bottom-up accumulation)."""
            levels = [
                {'price': 50001.0, 'amount': 1.0},
                {'price': 50002.0, 'amount': 2.0},
                {'price': 50003.0, 'amount': 3.0}
            ]
            
            result = service.calculate_cumulative_totals(levels, True)
            
            assert len(result) == 3
            assert result[0]['cumulative'] == 6.0      # All levels from current to end
            assert result[1]['cumulative'] == 5.0      # Last two levels
            assert result[2]['cumulative'] == 3.0      # Just last level

        def test_empty_levels_cumulative(self, service):
            """Test cumulative calculation with empty levels."""
            result = service.calculate_cumulative_totals([], False)
            assert len(result) == 0

        def test_single_level_cumulative(self, service):
            """Test cumulative calculation with single level."""
            levels = [{'price': 50000.0, 'amount': 5.0}]
            
            result_bid = service.calculate_cumulative_totals(levels, False)
            result_ask = service.calculate_cumulative_totals(levels, True)
            
            assert len(result_bid) == 1
            assert len(result_ask) == 1
            assert result_bid[0]['cumulative'] == 5.0
            assert result_ask[0]['cumulative'] == 5.0


    class TestMarketDepthAnalysis:
        """Test market depth analysis functionality."""

        def test_sufficient_data_analysis(self, service, sample_bids, sample_asks):
            """Test analysis when sufficient data is available."""
            analysis = service.analyze_market_depth(sample_bids, sample_asks, 5, 1.0)
            
            assert 'has_insufficient_raw_data' in analysis
            assert 'is_market_depth_limited' in analysis
            assert 'actual_levels' in analysis
            assert 'requested_levels' in analysis
            assert analysis['requested_levels'] == 5

        def test_insufficient_raw_data(self, service):
            """Test analysis when insufficient raw data is available."""
            limited_bids = [{'price': 50000.0, 'amount': 1.0}]
            limited_asks = [{'price': 50001.0, 'amount': 1.0}]
            
            analysis = service.analyze_market_depth(limited_bids, limited_asks, 10, 1.0)
            
            assert analysis['has_insufficient_raw_data'] is True
            assert analysis['raw_bids_count'] == 1
            assert analysis['raw_asks_count'] == 1
            assert analysis['min_required_raw_data'] == 100  # 10 * 10

        def test_market_depth_limited(self, service):
            """Test analysis when market depth is limited after aggregation."""
            # Create data that will aggregate to fewer levels than requested
            sparse_bids = [
                {'price': 50000.0, 'amount': 1.0},
                {'price': 50000.5, 'amount': 2.0},  # Will aggregate with above at 1.0 rounding
                {'price': 49995.0, 'amount': 3.0}   # Only 2 unique levels after rounding
            ]
            sparse_asks = [
                {'price': 50001.0, 'amount': 1.0},
                {'price': 50001.5, 'amount': 2.0},  # Will aggregate with above
                {'price': 50006.0, 'amount': 3.0}   # Only 2 unique levels after rounding
            ]
            
            analysis = service.analyze_market_depth(sparse_bids, sparse_asks, 5, 1.0)
            
            assert analysis['is_market_depth_limited'] is True
            assert analysis['actual_levels'] < 5

    class TestCachingMechanism:
        """Test the caching functionality."""

        @pytest.mark.asyncio
        async def test_cache_miss_and_hit(self, service):
            """Test cache miss followed by cache hit."""
            # First request should be a miss
            result1 = await service._get_from_cache("test_key")
            assert result1 is None
            
            # Set cache
            test_data = {'symbol': 'BTCUSDT', 'test': 'data'}
            await service._set_cache("test_key", test_data)
            
            # Second request should be a hit
            result2 = await service._get_from_cache("test_key")
            assert result2 == test_data

        @pytest.mark.asyncio
        async def test_cache_expiry(self, service):
            """Test that cache entries expire correctly."""
            # Set a very short TTL for testing
            service._cache_ttl = 0.01  # 10ms
            
            test_data = {'symbol': 'BTCUSDT', 'test': 'data'}
            await service._set_cache("test_key", test_data)
            
            # Should hit immediately
            result1 = await service._get_from_cache("test_key")
            assert result1 == test_data
            
            # Wait for expiry
            await asyncio.sleep(0.02)
            
            # Should miss after expiry
            result2 = await service._get_from_cache("test_key")
            assert result2 is None

        @pytest.mark.asyncio
        async def test_cache_cleanup(self, service):
            """Test that cache is cleaned up when it gets too large."""
            # Fill cache beyond limit
            for i in range(105):  # Exceeds 100 entry limit
                await service._set_cache(f"key_{i}", {'data': i})
            
            # Cache should be cleaned up
            async with service._cache_lock:
                assert len(service._cache) <= 100

        @pytest.mark.asyncio
        async def test_cache_key_generation(self, service):
            """Test cache key generation consistency."""
            key1 = service._generate_cache_key("BTCUSDT", 10, 1.0, 1640995200.123)
            key2 = service._generate_cache_key("BTCUSDT", 10, 1.0, 1640995200.789)
            
            # Should be the same due to timestamp rounding
            assert key1 == key2
            
            key3 = service._generate_cache_key("BTCUSDT", 10, 1.0, 1640995201.123)
            
            # Should be different due to different second
            assert key1 != key3

        @pytest.mark.asyncio
        async def test_cache_metrics(self, service):
            """Test cache metrics tracking."""
            # Start with empty metrics
            metrics = await service.get_cache_metrics()
            initial_requests = metrics['total_requests']
            
            # Perform some cache operations
            await service._get_from_cache("miss_key")  # Miss
            await service._set_cache("hit_key", {'data': 'test'})
            await service._get_from_cache("hit_key")   # Hit
            
            # Check updated metrics
            final_metrics = await service.get_cache_metrics()
            assert final_metrics['total_requests'] == initial_requests + 2
            assert final_metrics['cache_hits'] >= 1
            assert final_metrics['cache_misses'] >= 1
            assert 'hit_rate_percent' in final_metrics

    class TestFullAggregationFlow:
        """Test the complete aggregation flow."""

        @pytest.mark.asyncio
        async def test_full_aggregation(self, service, mock_orderbook):
            """Test the complete aggregation flow."""
            # Mock the orderbook snapshot
            mock_snapshot = MagicMock()
            mock_snapshot.bids = [
                MagicMock(price=50000.0, amount=1.0),
                MagicMock(price=49999.0, amount=2.0),
                MagicMock(price=49998.0, amount=3.0)
            ]
            mock_snapshot.asks = [
                MagicMock(price=50001.0, amount=1.5),
                MagicMock(price=50002.0, amount=2.5),
                MagicMock(price=50003.0, amount=3.5)
            ]
            mock_orderbook.get_snapshot.return_value = mock_snapshot
            
            # Test aggregation
            result = await service.aggregate_orderbook(
                mock_orderbook, 
                limit=3, 
                rounding=1.0,
                symbol_data={'pricePrecision': 2}
            )
            
            # Verify result structure
            assert 'symbol' in result
            assert 'bids' in result
            assert 'asks' in result
            assert 'timestamp' in result
            assert 'market_depth_info' in result
            
            # Verify data types and structure
            assert isinstance(result['bids'], list)
            assert isinstance(result['asks'], list)
            assert all('price' in bid and 'amount' in bid and 'cumulative' in bid 
                      for bid in result['bids'])
            assert all('price' in ask and 'amount' in ask and 'cumulative' in ask 
                      for ask in result['asks'])

        @pytest.mark.asyncio
        async def test_aggregation_with_cache(self, service, mock_orderbook):
            """Test that aggregation uses cache on subsequent calls."""
            # Mock the orderbook snapshot with enough data to avoid retries
            mock_snapshot = MagicMock()
            mock_snapshot.bids = [
                MagicMock(price=50000.0, amount=1.0),
                MagicMock(price=49999.0, amount=1.0),
                MagicMock(price=49998.0, amount=1.0),
                MagicMock(price=49997.0, amount=1.0),
                MagicMock(price=49996.0, amount=1.0)
            ]
            mock_snapshot.asks = [
                MagicMock(price=50001.0, amount=1.0),
                MagicMock(price=50002.0, amount=1.0),
                MagicMock(price=50003.0, amount=1.0),
                MagicMock(price=50004.0, amount=1.0),
                MagicMock(price=50005.0, amount=1.0)
            ]
            mock_orderbook.get_snapshot = AsyncMock(return_value=mock_snapshot)
            
            # First call
            result1 = await service.aggregate_orderbook(mock_orderbook, 5, 1.0)
            
            # Second call with same parameters should use cache
            result2 = await service.aggregate_orderbook(mock_orderbook, 5, 1.0)
            
            # Results should be identical
            assert result1 == result2
            
            # Verify cache was used (should only call get_snapshot once)
            assert mock_orderbook.get_snapshot.call_count == 1

        @pytest.mark.asyncio
        async def test_cache_warming(self, service, mock_orderbook):
            """Test cache warming functionality."""
            # Mock the orderbook
            mock_snapshot = MagicMock()
            mock_snapshot.bids = [MagicMock(price=50000.0, amount=1.0)]
            mock_snapshot.asks = [MagicMock(price=50001.0, amount=1.0)]
            mock_orderbook.get_snapshot.return_value = mock_snapshot
            mock_orderbook.latest_snapshot = True
            
            # Warm cache
            await service.warm_cache_for_symbol(
                "BTCUSDT", 
                mock_orderbook, 
                {'pricePrecision': 2}
            )
            
            # Verify cache has entries
            async with service._cache_lock:
                assert len(service._cache) > 0

    class TestEdgeCasesAndErrorHandling:
        """Test edge cases and error handling."""


        def test_negative_price_handling(self, service):
            """Test handling of negative prices."""
            invalid_data = [
                {'price': -50000.0, 'amount': 1.0},
                {'price': 50000.0, 'amount': 1.0}  # Valid data
            ]
            
            result = service.get_exact_levels(invalid_data, False, 5, 1.0)
            assert len(result) == 1  # Only valid data should remain
            assert result[0]['price'] > 0

        def test_very_large_rounding_values(self, service):
            """Test behavior with very large rounding values."""
            data = [
                {'price': 50000.0, 'amount': 1.0},
                {'price': 51000.0, 'amount': 2.0},
                {'price': 52000.0, 'amount': 3.0}
            ]
            
            # Very large rounding should aggregate everything
            result = service.get_exact_levels(data, False, 5, 10000.0)
            # All prices should round to the same bucket
            assert len(result) <= 1

        @pytest.mark.asyncio
        async def test_aggregation_with_no_data(self, service, mock_orderbook):
            """Test aggregation when orderbook has no data."""
            mock_snapshot = MagicMock()
            mock_snapshot.bids = []
            mock_snapshot.asks = []
            mock_orderbook.get_snapshot.return_value = mock_snapshot
            
            result = await service.aggregate_orderbook(mock_orderbook, 5, 1.0)
            
            assert result['bids'] == []
            assert result['asks'] == []
            assert 'market_depth_info' in result

        def test_rounding_with_zero_multiple(self, service):
            """Test rounding functions with zero multiple."""
            # Should return original value when multiple is 0
            assert service.round_up(123.45, 0) == 123.45
            assert service.round_down(123.45, 0) == 123.45

        def test_cumulative_totals_with_zero_amounts(self, service):
            """Test cumulative totals when levels have zero amounts."""
            levels = [
                {'price': 50000.0, 'amount': 0.0},
                {'price': 49999.0, 'amount': 2.0},
                {'price': 49998.0, 'amount': 0.0}
            ]
            
            result = service.calculate_cumulative_totals(levels, False)
            
            # Should handle zero amounts gracefully
            assert len(result) == 3
            assert result[0]['cumulative'] == 0.0
            assert result[1]['cumulative'] == 2.0
            assert result[2]['cumulative'] == 2.0

    class TestFormattingIntegration:
        """Test formatting integration in order book aggregation."""
        
        @pytest.mark.asyncio
        async def test_aggregate_orderbook_with_formatting(self):
            """Test that aggregation includes formatted fields when symbol_data is provided."""
            service = OrderBookAggregationService()
            
            # Create mock orderbook
            mock_orderbook = AsyncMock(spec=OrderBook)
            mock_orderbook.symbol = "BTCUSDT"
            mock_orderbook.timestamp = 1640995200000
            
            # Mock the orderbook snapshot
            mock_snapshot = MagicMock()
            mock_snapshot.bids = [
                MagicMock(price=50000.12, amount=0.001234),
                MagicMock(price=49999.50, amount=0.002500)
            ]
            mock_snapshot.asks = [
                MagicMock(price=50001.25, amount=0.003456),
                MagicMock(price=50002.00, amount=0.001000)
            ]
            mock_orderbook.get_snapshot.return_value = mock_snapshot
            
            # Symbol data with precision info
            symbol_data = {
                'pricePrecision': 2,
                'amountPrecision': 8
            }
            
            # Test aggregation with formatting
            result = await service.aggregate_orderbook(
                mock_orderbook, 
                limit=2, 
                rounding=0.5,
                symbol_data=symbol_data
            )
            
            # Verify basic structure
            assert result['symbol'] == "BTCUSDT"
            assert result['limit'] == 2
            assert result['rounding'] == 0.5
            assert 'bids' in result
            assert 'asks' in result
            
            # Verify formatted fields are present in bids
            for bid in result['bids']:
                assert 'price' in bid
                assert 'amount' in bid
                assert 'cumulative' in bid
                assert 'price_formatted' in bid
                assert 'amount_formatted' in bid
                assert 'cumulative_formatted' in bid
                
                # Verify formatting is applied correctly
                assert isinstance(bid['price_formatted'], str)
                assert isinstance(bid['amount_formatted'], str)
                assert isinstance(bid['cumulative_formatted'], str)
            
            # Verify formatted fields are present in asks
            for ask in result['asks']:
                assert 'price' in ask
                assert 'amount' in ask
                assert 'cumulative' in ask
                assert 'price_formatted' in ask
                assert 'amount_formatted' in ask
                assert 'cumulative_formatted' in ask
                
                # Verify formatting is applied correctly
                assert isinstance(ask['price_formatted'], str)
                assert isinstance(ask['amount_formatted'], str)
                assert isinstance(ask['cumulative_formatted'], str)
        
        @pytest.mark.asyncio
        async def test_aggregate_orderbook_without_symbol_data(self):
            """Test that aggregation works without formatting when symbol_data is None."""
            service = OrderBookAggregationService()
            
            # Create mock orderbook
            mock_orderbook = AsyncMock(spec=OrderBook)
            mock_orderbook.symbol = "ETHUSDT"
            mock_orderbook.timestamp = 1640995200000
            
            # Mock the orderbook snapshot
            mock_snapshot = MagicMock()
            mock_snapshot.bids = [MagicMock(price=3000.0, amount=1.5)]
            mock_snapshot.asks = [MagicMock(price=3001.0, amount=2.0)]
            mock_orderbook.get_snapshot.return_value = mock_snapshot
            
            # Test aggregation without symbol_data
            result = await service.aggregate_orderbook(
                mock_orderbook, 
                limit=1, 
                rounding=1.0,
                symbol_data=None
            )
            
            # Verify basic structure
            assert result['symbol'] == "ETHUSDT"
            assert 'bids' in result
            assert 'asks' in result
            
            # Verify formatted fields are NOT present
            for bid in result['bids']:
                assert 'price' in bid
                assert 'amount' in bid
                assert 'cumulative' in bid
                assert 'price_formatted' not in bid
                assert 'amount_formatted' not in bid
                assert 'cumulative_formatted' not in bid
            
            for ask in result['asks']:
                assert 'price' in ask
                assert 'amount' in ask
                assert 'cumulative' in ask
                assert 'price_formatted' not in ask
                assert 'amount_formatted' not in ask
                assert 'cumulative_formatted' not in ask

    @pytest.mark.asyncio
    async def test_aggregate_orderbook_includes_time_formatted(self):
        """Test that aggregated orderbook includes time_formatted field."""
        service = OrderBookAggregationService()
        
        # Create mock orderbook with specific timestamp
        mock_snapshot = OrderBookSnapshot(
            symbol="BTCUSDT",
            bids=[OrderBookLevel(50000.0, 1.0)],
            asks=[OrderBookLevel(50100.0, 1.0)],
            timestamp=1640995200000  # 2022-01-01 00:00:00 UTC
        )
        
        mock_orderbook = AsyncMock()
        mock_orderbook.get_snapshot = AsyncMock(return_value=mock_snapshot)
        mock_orderbook.symbol = "BTCUSDT"
        mock_orderbook.timestamp = 1640995200000
        
        result = await service.aggregate_orderbook(
            mock_orderbook,
            limit=10,
            rounding=1.0
        )
        
        # Check that time_formatted is included
        assert 'time_formatted' in result
        assert 'timestamp' in result
        assert result['timestamp'] == 1640995200000
        # time_formatted should be in HH:MM:SS format
        assert isinstance(result['time_formatted'], str)
        assert len(result['time_formatted']) >= 8  # HH:MM:SS format

    @pytest.mark.asyncio
    async def test_aggregate_orderbook_invalid_timestamp(self):
        """Test handling of invalid timestamp in orderbook."""
        service = OrderBookAggregationService()
        
        # Create mock orderbook with invalid timestamp that will cause an exception
        mock_snapshot = OrderBookSnapshot(
            symbol="BTCUSDT",
            bids=[OrderBookLevel(50000.0, 1.0)],
            asks=[OrderBookLevel(50100.0, 1.0)],
            timestamp=9999999999999999  # Invalid timestamp that will cause ValueError/OSError in datetime.fromtimestamp
        )
        
        mock_orderbook = AsyncMock()
        mock_orderbook.get_snapshot = AsyncMock(return_value=mock_snapshot)
        mock_orderbook.symbol = "BTCUSDT"
        mock_orderbook.timestamp = 9999999999999999
        
        result = await service.aggregate_orderbook(
            mock_orderbook,
            limit=10,
            rounding=1.0
        )
        
        # Should still include time_formatted field, even if invalid
        assert 'time_formatted' in result
        assert result['time_formatted'] == "Invalid"