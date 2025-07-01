"""
Unit tests for OrderBookProcessor

Tests the server-side order book aggregation and processing logic.
"""

import pytest
import math
from unittest.mock import Mock, patch

from app.services.orderbook_processor import (
    OrderBookProcessor, 
    OrderBookLevel, 
    AggregatedOrderBook
)


class TestOrderBookLevel:
    """Test the OrderBookLevel dataclass."""
    
    def test_orderbook_level_creation(self):
        level = OrderBookLevel(price=100.0, amount=1.5)
        assert level.price == 100.0
        assert level.amount == 1.5
    
    def test_orderbook_level_equality(self):
        level1 = OrderBookLevel(price=100.0, amount=1.5)
        level2 = OrderBookLevel(price=100.0, amount=1.5)
        level3 = OrderBookLevel(price=101.0, amount=1.5)
        
        assert level1 == level2
        assert level1 != level3


class TestAggregatedOrderBook:
    """Test the AggregatedOrderBook dataclass and validation."""
    
    def test_aggregated_orderbook_creation(self):
        bids = [OrderBookLevel(100.0, 1.5), OrderBookLevel(99.0, 2.0)]
        asks = [OrderBookLevel(101.0, 1.0), OrderBookLevel(102.0, 1.5)]
        
        book = AggregatedOrderBook(
            bids=bids,
            asks=asks,
            symbol="BTCUSDT",
            rounding=0.01,
            depth=20,
            source="test"
        )
        
        assert book.symbol == "BTCUSDT"
        assert book.rounding == 0.01
        assert book.depth == 20
        assert book.source == "test"
        assert book.aggregated is True
    
    def test_valid_orderbook_validation(self):
        """Test validation of a properly structured order book."""
        # Bids sorted descending (highest first)
        bids = [
            OrderBookLevel(100.0, 1.5),
            OrderBookLevel(99.5, 2.0),
            OrderBookLevel(99.0, 1.0)
        ]
        
        # Asks sorted ascending (lowest first)
        asks = [
            OrderBookLevel(101.0, 1.0),
            OrderBookLevel(101.5, 1.5),
            OrderBookLevel(102.0, 2.0)
        ]
        
        book = AggregatedOrderBook(
            bids=bids,
            asks=asks,
            symbol="BTCUSDT",
            rounding=0.5,
            depth=3,
            source="test"
        )
        
        assert book.validate() is True
    
    def test_invalid_bid_sorting(self):
        """Test validation fails for improperly sorted bids."""
        # Bids NOT sorted descending (should be highest first)
        bids = [
            OrderBookLevel(99.0, 1.0),   # Wrong order!
            OrderBookLevel(100.0, 1.5),
        ]
        
        asks = [OrderBookLevel(101.0, 1.0)]
        
        book = AggregatedOrderBook(
            bids=bids,
            asks=asks,
            symbol="BTCUSDT",
            rounding=0.5,
            depth=2,
            source="test"
        )
        
        assert book.validate() is False
    
    def test_invalid_ask_sorting(self):
        """Test validation fails for improperly sorted asks."""
        bids = [OrderBookLevel(100.0, 1.5)]
        
        # Asks NOT sorted ascending (should be lowest first)
        asks = [
            OrderBookLevel(102.0, 2.0),  # Wrong order!
            OrderBookLevel(101.0, 1.0),
        ]
        
        book = AggregatedOrderBook(
            bids=bids,
            asks=asks,
            symbol="BTCUSDT",
            rounding=0.5,
            depth=2,
            source="test"
        )
        
        assert book.validate() is False
    
    def test_invalid_negative_amounts(self):
        """Test validation fails for negative amounts."""
        bids = [OrderBookLevel(100.0, -1.5)]  # Negative amount
        asks = [OrderBookLevel(101.0, 1.0)]
        
        book = AggregatedOrderBook(
            bids=bids,
            asks=asks,
            symbol="BTCUSDT",
            rounding=0.5,
            depth=2,
            source="test"
        )
        
        assert book.validate() is False


class TestRoundingFunctions:
    """Test the rounding utility functions."""
    
    def test_round_down_basic(self):
        processor = OrderBookProcessor()
        
        # Basic rounding down
        assert processor.round_down(100.57, 0.1) == 100.5
        assert processor.round_down(100.51, 0.1) == 100.5
        assert processor.round_down(100.59, 0.1) == 100.5
    
    def test_round_down_edge_cases(self):
        processor = OrderBookProcessor()
        
        # Edge cases
        assert processor.round_down(100.0, 0.1) == 100.0  # Exact multiple
        assert processor.round_down(0.0, 0.1) == 0.0      # Zero value
        assert processor.round_down(100.5, 0) == 100.5    # Zero multiple
        assert processor.round_down(100.5, -0.1) == 100.5 # Negative multiple
    
    def test_round_down_precision(self):
        processor = OrderBookProcessor()
        
        # Test floating-point precision handling
        assert processor.round_down(0.3, 0.1) == 0.3
        assert processor.round_down(0.31, 0.1) == 0.3
        assert processor.round_down(0.39, 0.1) == 0.3
        
        # Test with different multiples
        assert processor.round_down(1.25, 0.25) == 1.25
        assert processor.round_down(1.24, 0.25) == 1.0
        assert processor.round_down(1.49, 0.25) == 1.25
    
    def test_round_up_basic(self):
        processor = OrderBookProcessor()
        
        # Basic rounding up
        assert processor.round_up(100.51, 0.1) == 100.6
        assert processor.round_up(100.50, 0.1) == 100.5  # Exact multiple
        assert processor.round_up(100.41, 0.1) == 100.5
    
    def test_round_up_edge_cases(self):
        processor = OrderBookProcessor()
        
        # Edge cases
        assert processor.round_up(100.0, 0.1) == 100.0   # Exact multiple
        assert processor.round_up(0.0, 0.1) == 0.0       # Zero value
        assert processor.round_up(100.5, 0) == 100.5     # Zero multiple
        assert processor.round_up(100.5, -0.1) == 100.5  # Negative multiple
    
    def test_round_up_precision(self):
        processor = OrderBookProcessor()
        
        # Test floating-point precision handling
        assert processor.round_up(0.3, 0.1) == 0.3
        assert processor.round_up(0.31, 0.1) == 0.4
        assert processor.round_up(0.39, 0.1) == 0.4
        
        # Test with different multiples
        assert processor.round_up(1.25, 0.25) == 1.25
        assert processor.round_up(1.24, 0.25) == 1.25
        assert processor.round_up(1.01, 0.25) == 1.25


class TestAggregateLevels:
    """Test the aggregate_levels method."""
    
    def test_aggregate_bids_basic(self):
        """Test basic bid aggregation (round down, sort descending)."""
        processor = OrderBookProcessor()
        
        # Raw bid data: [price, amount]
        raw_bids = [
            [100.57, 1.0],  # Should round down to 100.5
            [100.51, 2.0],  # Should round down to 100.5 (aggregate)
            [99.82, 1.5],   # Should round down to 99.8
            [99.33, 0.5],   # Should round down to 99.3
        ]
        
        result = processor.aggregate_levels(
            raw_data=raw_bids,
            rounding=0.1,
            depth=10,
            is_ask=False  # Bids
        )
        
        # Should have 3 levels: 100.5 (3.0), 99.8 (1.5), 99.3 (0.5)
        assert len(result) == 3
        
        # Should be sorted descending (highest price first)
        assert result[0].price == 100.5
        assert result[0].amount == 3.0  # 1.0 + 2.0 aggregated
        
        assert result[1].price == 99.8
        assert result[1].amount == 1.5
        
        assert result[2].price == 99.3
        assert result[2].amount == 0.5
    
    def test_aggregate_asks_basic(self):
        """Test basic ask aggregation (round up, sort ascending)."""
        processor = OrderBookProcessor()
        
        # Raw ask data: [price, amount]
        raw_asks = [
            [101.42, 1.0],  # Should round up to 101.5
            [101.51, 2.0],  # Should round up to 101.6
            [101.48, 1.5],  # Should round up to 101.5 (aggregate)
            [102.13, 0.5],  # Should round up to 102.2
        ]
        
        result = processor.aggregate_levels(
            raw_data=raw_asks,
            rounding=0.1,
            depth=10,
            is_ask=True  # Asks
        )
        
        # Should have 3 levels: 101.5 (2.5), 101.6 (2.0), 102.2 (0.5)
        assert len(result) == 3
        
        # Should be sorted ascending (lowest price first)
        assert result[0].price == 101.5
        assert result[0].amount == 2.5  # 1.0 + 1.5 aggregated
        
        assert result[1].price == 101.6
        assert result[1].amount == 2.0
        
        assert result[2].price == 102.2
        assert result[2].amount == 0.5
    
    def test_depth_limiting(self):
        """Test that depth parameter limits results."""
        processor = OrderBookProcessor()
        
        # Generate many levels
        raw_bids = [[100.0 - i * 0.1, 1.0] for i in range(10)]
        
        result = processor.aggregate_levels(
            raw_data=raw_bids,
            rounding=0.1,
            depth=3,  # Limit to 3 levels
            is_ask=False
        )
        
        assert len(result) == 3
        # Should get the top 3 prices: 100.0, 99.9, 99.8
        assert result[0].price == 100.0
        assert result[1].price == 99.9
        assert result[2].price == 99.8
    
    def test_zero_amount_filtering(self):
        """Test that zero amounts are filtered out."""
        processor = OrderBookProcessor()
        
        raw_bids = [
            [100.0, 1.0],
            [99.0, 0.0],   # Zero amount - should be filtered
            [98.0, 2.0],
        ]
        
        result = processor.aggregate_levels(
            raw_data=raw_bids,
            rounding=0.1,
            depth=10,
            is_ask=False
        )
        
        # Should only have 2 levels (zero amount filtered)
        assert len(result) == 2
        assert result[0].price == 100.0
        assert result[1].price == 98.0
    
    def test_invalid_data_handling(self):
        """Test handling of malformed raw data."""
        processor = OrderBookProcessor()
        
        raw_bids = [
            [100.0, 1.0],     # Valid
            [99.0],           # Missing amount - should be skipped
            [98.0, 2.0],      # Valid
            [],               # Empty - should be skipped
        ]
        
        result = processor.aggregate_levels(
            raw_data=raw_bids,
            rounding=0.1,
            depth=10,
            is_ask=False
        )
        
        # Should only have 2 valid levels
        assert len(result) == 2
        assert result[0].price == 100.0
        assert result[1].price == 98.0


class TestProcessOrderbook:
    """Test the main process_orderbook method."""
    
    def test_process_basic_orderbook(self):
        """Test processing a basic order book."""
        processor = OrderBookProcessor()
        
        raw_orderbook = {
            'bids': [
                [100.57, 1.0],
                [100.51, 2.0],
                [99.82, 1.5],
            ],
            'asks': [
                [101.42, 1.0],
                [101.48, 1.5],
                [102.13, 0.5],
            ],
            'timestamp': 1234567890
        }
        
        result = processor.process_orderbook(
            raw_orderbook=raw_orderbook,
            symbol="BTCUSDT",
            rounding=0.1,
            depth=10,
            source="test"
        )
        
        # Check structure
        assert isinstance(result, AggregatedOrderBook)
        assert result.symbol == "BTCUSDT"
        assert result.rounding == 0.1
        assert result.depth == 10
        assert result.source == "test"
        assert result.timestamp == 1234567890
        assert result.aggregated is True
        
        # Check bids (rounded down, sorted descending)
        assert len(result.bids) == 2  # 100.5 aggregated, 99.8 separate
        assert result.bids[0].price == 100.5
        assert result.bids[0].amount == 3.0  # Aggregated
        assert result.bids[1].price == 99.8
        assert result.bids[1].amount == 1.5
        
        # Check asks (rounded up, sorted ascending)
        assert len(result.asks) == 2  # 101.5 aggregated, 102.2 separate
        assert result.asks[0].price == 101.5
        assert result.asks[0].amount == 2.5  # Aggregated
        assert result.asks[1].price == 102.2
        assert result.asks[1].amount == 0.5
        
        # Validation should pass
        assert result.validate() is True
    
    def test_insufficient_data_warning(self):
        """Test warning for insufficient market depth."""
        processor = OrderBookProcessor()
        
        # Small dataset
        raw_orderbook = {
            'bids': [[100.0, 1.0]],  # Only 1 bid
            'asks': [[101.0, 1.0]],  # Only 1 ask
        }
        
        # Patch the instance logger
        with patch.object(processor, 'logger') as mock_logger:
            result = processor.process_orderbook(
                raw_orderbook=raw_orderbook,
                symbol="BTCUSDT",
                rounding=0.1,
                depth=20,  # Requesting 20 levels
                source="test"
            )
            
            # Should log warning about insufficient data
            mock_logger.warning.assert_called()
            warning_call = mock_logger.warning.call_args[0][0]
            assert "Limited market depth" in warning_call
            assert "BTCUSDT" in warning_call
    
    def test_market_depth_limited_info(self):
        """Test info logging for limited market depth."""
        processor = OrderBookProcessor()
        
        # Data that will result in fewer levels than requested
        raw_orderbook = {
            'bids': [[100.0, 1.0], [99.0, 1.0]],
            'asks': [[101.0, 1.0], [102.0, 1.0]],
        }
        
        # Patch the instance logger
        with patch.object(processor, 'logger') as mock_logger:
            result = processor.process_orderbook(
                raw_orderbook=raw_orderbook,
                symbol="BTCUSDT",
                rounding=0.1,
                depth=10,  # Requesting more than available
                source="test"
            )
            
            # Should log info about market depth limitation
            mock_logger.info.assert_called()
    
    def test_error_handling(self):
        """Test error handling for malformed data."""
        processor = OrderBookProcessor()
        
        # Invalid data structure - None instead of dict
        invalid_orderbook = None
        
        with pytest.raises((TypeError, AttributeError)):
            processor.process_orderbook(
                raw_orderbook=invalid_orderbook,
                symbol="BTCUSDT",
                rounding=0.1,
                depth=10,
                source="test"
            )
        
        # Test with malformed bids/asks that will cause aggregation issues
        invalid_orderbook2 = {
            'bids': [["invalid", "data"]],  # Non-numeric data
            'asks': [["invalid", "data"]],
        }
        
        with pytest.raises((ValueError, TypeError)):
            processor.process_orderbook(
                raw_orderbook=invalid_orderbook2,
                symbol="BTCUSDT",
                rounding=0.1,
                depth=10,
                source="test"
            )


class TestFormatSupport:
    """Test format detection and support methods."""
    
    def test_ccxtpro_format_support_valid(self):
        """Test detection of valid ccxtpro format."""
        processor = OrderBookProcessor()
        
        valid_orderbook = {
            'bids': [[100.0, 1.0]],
            'asks': [[101.0, 1.0]],
            'timestamp': 1234567890
        }
        
        assert processor.supports_ccxtpro_format(valid_orderbook) is True
    
    def test_ccxtpro_format_support_invalid(self):
        """Test detection of invalid ccxtpro format."""
        processor = OrderBookProcessor()
        
        # Missing keys
        assert processor.supports_ccxtpro_format({}) is False
        assert processor.supports_ccxtpro_format({'bids': []}) is False
        
        # Wrong types
        invalid_orderbook = {
            'bids': "not a list",
            'asks': []
        }
        assert processor.supports_ccxtpro_format(invalid_orderbook) is False
    
    def test_depth_cache_format_support(self):
        """Test detection of DepthCacheManager format."""
        processor = OrderBookProcessor()
        
        # Mock DepthCacheManager object
        mock_depth_cache = Mock()
        mock_depth_cache.get_bids = Mock()
        mock_depth_cache.get_asks = Mock()
        
        assert processor.supports_depth_cache_format(mock_depth_cache) is True
        
        # Regular dict should not be detected as DepthCacheManager
        regular_dict = {'bids': [], 'asks': []}
        assert processor.supports_depth_cache_format(regular_dict) is False
    
    def test_process_depth_cache(self):
        """Test processing DepthCacheManager data."""
        processor = OrderBookProcessor()
        
        # Mock DepthCacheManager
        mock_depth_cache = Mock()
        mock_depth_cache.get_bids.return_value = {
            100.5: 1.0,
            100.0: 2.0,
            99.5: 1.5
        }
        mock_depth_cache.get_asks.return_value = {
            101.0: 1.0,
            101.5: 1.5,
            102.0: 2.0
        }
        
        result = processor.process_depth_cache(
            depth_cache=mock_depth_cache,
            symbol="BTCUSDT",
            rounding=0.1,
            depth=10
        )
        
        # Check structure
        assert isinstance(result, AggregatedOrderBook)
        assert result.symbol == "BTCUSDT"
        assert result.source == "depth_cache"
        
        # Check that methods were called
        mock_depth_cache.get_bids.assert_called_once()
        mock_depth_cache.get_asks.assert_called_once()
        
        # Validation should pass
        assert result.validate() is True