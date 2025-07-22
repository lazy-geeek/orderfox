"""
End-to-end integration test for order book formatting data flow.

This test validates the complete pipeline from WebSocket connection through
to formatted order book data being sent to clients, ensuring all formatting
logic works correctly in integration.
"""

import pytest

# Chunk 7b: Data Flow Integration tests - E2E formatting, liquidation volume flows
pytestmark = pytest.mark.chunk7b
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from app.api.v1.endpoints.connection_manager import ConnectionManager
from app.services.orderbook_aggregation_service import OrderBookAggregationService
from app.services.formatting_service import FormattingService
from app.services.orderbook_manager import OrderBookManager
from app.models.orderbook import OrderBook, OrderBookSnapshot, OrderBookLevel


class TestOrderBookE2EFormatting:
    """Test end-to-end order book formatting data flow."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.connection_manager = ConnectionManager()
        self.aggregation_service = OrderBookAggregationService()
        self.formatting_service = FormattingService()
    
    @pytest.mark.asyncio
    async def test_complete_orderbook_formatting_pipeline(self):
        """Test the complete order book formatting pipeline from raw data to WebSocket output."""
        # Test setup
        symbol = "BTCUSDT"
        connection_id = f"{symbol}:e2e_test"
        
        # Mock WebSocket
        mock_websocket = AsyncMock()
        mock_websocket.send_text = AsyncMock()
        
        # Set up connection metadata
        self.connection_manager._connection_metadata = {
            connection_id: {
                'websocket': mock_websocket,
                'symbol': symbol,
                'display_symbol': symbol,
                'limit': 5,
                'rounding': 0.1
            }
        }
        
        # Raw order book data (simulating exchange data)
        raw_bids = [
            OrderBookLevel(price=50000.12, amount=0.001234),
            OrderBookLevel(price=50000.06, amount=0.002500),
            OrderBookLevel(price=49999.98, amount=0.000456),
            OrderBookLevel(price=49999.87, amount=0.003200),
            OrderBookLevel(price=49999.73, amount=0.001800),
        ]
        
        raw_asks = [
            OrderBookLevel(price=50000.23, amount=0.003456),
            OrderBookLevel(price=50000.31, amount=0.001000),
            OrderBookLevel(price=50000.47, amount=0.002300),
            OrderBookLevel(price=50000.58, amount=0.001500),
            OrderBookLevel(price=50000.69, amount=0.003100),
        ]
        
        # Symbol data with precision information
        symbol_data = {
            'symbol': symbol,
            'pricePrecision': 2,
            'amountPrecision': 8,
            'base_asset': 'BTC',
            'quote_asset': 'USDT'
        }
        
        # Create OrderBookSnapshot
        snapshot = OrderBookSnapshot(
            symbol=symbol,
            bids=raw_bids,
            asks=raw_asks,
            timestamp=1640995200000
        )
        
        # Mock OrderBook
        mock_orderbook = AsyncMock(spec=OrderBook)
        mock_orderbook.symbol = symbol
        mock_orderbook.timestamp = 1640995200000
        mock_orderbook.get_snapshot.return_value = snapshot
        
        # Test the aggregation service with formatting
        aggregated_result = await self.aggregation_service.aggregate_orderbook(
            mock_orderbook,
            limit=5,
            rounding=0.1,
            symbol_data=symbol_data
        )
        
        # Verify aggregation includes formatted fields
        assert 'bids' in aggregated_result
        assert 'asks' in aggregated_result
        assert len(aggregated_result['bids']) > 0
        assert len(aggregated_result['asks']) > 0
        
        # Verify each bid/ask has formatted fields
        for bid in aggregated_result['bids']:
            assert 'price' in bid
            assert 'amount' in bid
            assert 'cumulative' in bid
            assert 'price_formatted' in bid
            assert 'amount_formatted' in bid
            assert 'cumulative_formatted' in bid
            
            # Verify formatting quality
            assert isinstance(bid['price_formatted'], str)
            assert isinstance(bid['amount_formatted'], str)
            assert isinstance(bid['cumulative_formatted'], str)
            
            # Small amounts should not display as "0.00"
            if bid['amount'] < 0.01:
                assert bid['amount_formatted'] != "0.00"
                assert len(bid['amount_formatted'].split('.')[1]) > 2
        
        for ask in aggregated_result['asks']:
            assert 'price' in ask
            assert 'amount' in ask
            assert 'cumulative' in ask
            assert 'price_formatted' in ask
            assert 'amount_formatted' in ask
            assert 'cumulative_formatted' in ask
            
            # Verify formatting quality
            assert isinstance(ask['price_formatted'], str)
            assert isinstance(ask['amount_formatted'], str)
            assert isinstance(ask['cumulative_formatted'], str)
            
            # Small amounts should not display as "0.00"
            if ask['amount'] < 0.01:
                assert ask['amount_formatted'] != "0.00"
                assert len(ask['amount_formatted'].split('.')[1]) > 2
        
        # Test connection manager broadcast with the aggregated data
        with patch('app.api.v1.endpoints.connection_manager.orderbook_manager') as mock_orderbook_manager:
            mock_orderbook_manager.get_aggregated_orderbook = AsyncMock(return_value=aggregated_result)
            
            # Broadcast the data
            await self.connection_manager._broadcast_aggregated_orderbook(connection_id)
            
            # Verify WebSocket received the data
            mock_websocket.send_text.assert_called_once()
            sent_message = mock_websocket.send_text.call_args[0][0]
            sent_data = json.loads(sent_message)
            
            # Verify WebSocket message structure
            assert sent_data['type'] == 'orderbook_update'
            assert sent_data['symbol'] == symbol
            assert 'bids' in sent_data
            assert 'asks' in sent_data
            assert 'timestamp' in sent_data
            assert 'rounding' in sent_data
            
            # Verify formatted fields are preserved in WebSocket output
            for bid in sent_data['bids']:
                assert 'price_formatted' in bid
                assert 'amount_formatted' in bid
                assert 'cumulative_formatted' in bid
                
                # Verify formatting quality is maintained
                assert isinstance(bid['price_formatted'], str)
                assert isinstance(bid['amount_formatted'], str)
                assert isinstance(bid['cumulative_formatted'], str)
            
            for ask in sent_data['asks']:
                assert 'price_formatted' in ask
                assert 'amount_formatted' in ask
                assert 'cumulative_formatted' in ask
                
                # Verify formatting quality is maintained
                assert isinstance(ask['price_formatted'], str)
                assert isinstance(ask['amount_formatted'], str)
                assert isinstance(ask['cumulative_formatted'], str)
    
    @pytest.mark.asyncio
    async def test_formatting_consistency_across_pipeline(self):
        """Test that formatting is consistent throughout the entire pipeline."""
        # Test data with very specific values to verify precision handling
        test_amounts = [0.00123456, 0.00000789, 1.23456789, 1234.567890]
        test_prices = [50000.12, 0.000012, 3456.78, 123456.78]
        
        symbol_data = {
            'symbol': 'TESTUSDT',
            'pricePrecision': 2,
            'amountPrecision': 8
        }
        
        # Test each amount with the formatting service directly
        direct_formatting_results = {}
        for i, amount in enumerate(test_amounts):
            price = test_prices[i]
            cumulative = amount * 2  # Simple cumulative calculation
            
            price_formatted = self.formatting_service.format_price(price, symbol_data)
            amount_formatted = self.formatting_service.format_amount(amount, symbol_data)
            cumulative_formatted = self.formatting_service.format_total(cumulative, symbol_data)
            
            direct_formatting_results[i] = {
                'price_formatted': price_formatted,
                'amount_formatted': amount_formatted,
                'cumulative_formatted': cumulative_formatted
            }
        
        # Now test the same values through the aggregation pipeline
        raw_bids = [
            OrderBookLevel(price=test_prices[i], amount=test_amounts[i])
            for i in range(len(test_amounts))
        ]
        raw_asks = [
            OrderBookLevel(price=test_prices[i] + 0.01, amount=test_amounts[i])
            for i in range(len(test_amounts))
        ]
        
        snapshot = OrderBookSnapshot(
            symbol='TESTUSDT',
            bids=raw_bids,
            asks=raw_asks,
            timestamp=1640995200000
        )
        
        mock_orderbook = AsyncMock(spec=OrderBook)
        mock_orderbook.symbol = 'TESTUSDT'
        mock_orderbook.timestamp = 1640995200000
        mock_orderbook.get_snapshot.return_value = snapshot
        
        # Aggregate with formatting
        aggregated_result = await self.aggregation_service.aggregate_orderbook(
            mock_orderbook,
            limit=len(test_amounts),
            rounding=0.01,  # Small rounding to preserve original values
            symbol_data=symbol_data
        )
        
        # Verify that aggregation produces the same formatting as direct service calls
        for i, bid in enumerate(aggregated_result['bids']):
            # The aggregation might change order due to sorting, so find matching price
            original_price = test_prices[i]
            matching_bid = None
            for b in aggregated_result['bids']:
                if abs(b['price'] - original_price) < 0.001:  # Allow small floating point differences
                    matching_bid = b
                    break
            
            if matching_bid:
                # Compare formatting - should be identical or very close
                direct_price = direct_formatting_results[i]['price_formatted']
                direct_amount = direct_formatting_results[i]['amount_formatted']
                
                # Prices should match exactly
                assert matching_bid['price_formatted'] == direct_price or \
                       abs(float(matching_bid['price_formatted']) - float(direct_price)) < 0.01
                
                # Amounts should match exactly
                assert matching_bid['amount_formatted'] == direct_amount
    
    @pytest.mark.asyncio
    async def test_error_handling_in_formatting_pipeline(self):
        """Test error handling when formatting fails in the pipeline."""
        symbol = "ERRORTEST"
        connection_id = f"{symbol}:error_test"
        
        # Mock WebSocket
        mock_websocket = AsyncMock()
        mock_websocket.send_text = AsyncMock()
        
        # Set up connection metadata
        self.connection_manager._connection_metadata = {
            connection_id: {
                'websocket': mock_websocket,
                'symbol': symbol,
                'display_symbol': symbol
            }
        }
        
        # Test with invalid symbol data that might cause formatting issues
        invalid_symbol_data = {
            'symbol': symbol,
            'pricePrecision': None,  # Invalid precision
            'amountPrecision': 'invalid'  # Invalid type
        }
        
        # Raw data with edge case values (use valid prices since OrderBookLevel validates)
        raw_bids = [
            OrderBookLevel(price=50000, amount=0.001),  # Normal data
            OrderBookLevel(price=49999, amount=0.002),  # Normal data
        ]
        raw_asks = [
            OrderBookLevel(price=50001, amount=0.001),  # Normal data
        ]
        
        snapshot = OrderBookSnapshot(
            symbol=symbol,
            bids=raw_bids,
            asks=raw_asks,
            timestamp=1640995200000
        )
        
        mock_orderbook = AsyncMock(spec=OrderBook)
        mock_orderbook.symbol = symbol
        mock_orderbook.timestamp = 1640995200000
        mock_orderbook.get_snapshot.return_value = snapshot
        
        # Test aggregation with invalid data - should not crash
        try:
            aggregated_result = await self.aggregation_service.aggregate_orderbook(
                mock_orderbook,
                limit=5,
                rounding=0.1,
                symbol_data=invalid_symbol_data
            )
            
            # Should filter out invalid data and continue
            assert 'bids' in aggregated_result
            assert 'asks' in aggregated_result
            
            # Should have at least the valid ask
            assert len(aggregated_result['asks']) > 0
            
            # Any remaining data should have formatted fields (even if basic)
            for ask in aggregated_result['asks']:
                assert 'price_formatted' in ask
                assert 'amount_formatted' in ask
                assert 'cumulative_formatted' in ask
                
        except Exception as e:
            # If it does raise an exception, it should be a known, handled exception
            # not an unhandled crash
            assert "formatting" in str(e).lower() or "invalid" in str(e).lower()
    
    @pytest.mark.asyncio
    async def test_performance_of_formatting_pipeline(self):
        """Test that the formatting pipeline performs well with large datasets."""
        symbol = "PERFTEST"
        
        # Create large dataset
        large_bid_data = [
            OrderBookLevel(price=50000 - i * 0.01, amount=0.001 + i * 0.0001)
            for i in range(1000)  # 1000 bid levels
        ]
        large_ask_data = [
            OrderBookLevel(price=50001 + i * 0.01, amount=0.001 + i * 0.0001)
            for i in range(1000)  # 1000 ask levels
        ]
        
        snapshot = OrderBookSnapshot(
            symbol=symbol,
            bids=large_bid_data,
            asks=large_ask_data,
            timestamp=1640995200000
        )
        
        mock_orderbook = AsyncMock(spec=OrderBook)
        mock_orderbook.symbol = symbol
        mock_orderbook.timestamp = 1640995200000
        mock_orderbook.get_snapshot.return_value = snapshot
        
        symbol_data = {
            'symbol': symbol,
            'pricePrecision': 2,
            'amountPrecision': 8
        }
        
        # Time the aggregation with formatting
        import time
        start_time = time.time()
        
        aggregated_result = await self.aggregation_service.aggregate_orderbook(
            mock_orderbook,
            limit=100,  # Request 100 levels
            rounding=0.1,
            symbol_data=symbol_data
        )
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Should complete in reasonable time (under 500ms for 1000 raw levels -> 100 aggregated)
        assert processing_time < 0.5, f"Processing took too long: {processing_time:.3f}s"
        
        # Should have formatted all requested levels
        assert len(aggregated_result['bids']) <= 100
        assert len(aggregated_result['asks']) <= 100
        
        # All levels should have formatted fields
        for bid in aggregated_result['bids']:
            assert 'price_formatted' in bid
            assert 'amount_formatted' in bid
            assert 'cumulative_formatted' in bid
        
        for ask in aggregated_result['asks']:
            assert 'price_formatted' in ask
            assert 'amount_formatted' in ask
            assert 'cumulative_formatted' in ask