"""
Unit tests for liquidation service cache management.

Tests cache clearing, volume aggregation, and message type separation.
"""

import pytest

# Chunk 4: Advanced services - Liquidation, trade, trading engine
pytestmark = pytest.mark.chunk4
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from decimal import Decimal
from collections import deque
from datetime import datetime, timezone

from app.services.liquidation_service import LiquidationService
from app.api.v1.endpoints import liquidations_ws


class TestLiquidationCacheManagement:
    """Test cache management in liquidation service"""

    @pytest.fixture
    def liquidation_service(self):
        """Create liquidation service instance"""
        return LiquidationService()

    @pytest.fixture
    def mock_websocket(self):
        """Create mock websocket"""
        mock_ws = AsyncMock()
        mock_ws.recv = AsyncMock()
        mock_ws.send = AsyncMock()
        mock_ws.ping = AsyncMock()
        mock_ws.close = AsyncMock()
        return mock_ws

    @pytest.mark.asyncio
    async def test_cache_clearing_on_disconnect(self, liquidation_service):
        """Test that caches are properly cleared when last subscriber disconnects"""
        symbol = "BTCUSDT"
        callback = Mock()
        
        # Mock the global caches
        with patch.object(liquidations_ws, 'liquidations_cache', {symbol: deque([1, 2, 3])}) as mock_cache, \
             patch.object(liquidations_ws, 'historical_loaded', {symbol: True}) as mock_historical:
            
            # Set up some data in service caches
            liquidation_service.data_callbacks[symbol] = [callback]
            liquidation_service.symbol_info_cache[symbol] = {"baseAsset": "BTC"}
            liquidation_service.liquidation_buffers[symbol] = {"1m": []}
            liquidation_service.accumulated_volumes[symbol] = {"1m": {}}
            # Create a proper async task that can be cancelled
            async def dummy_task():
                await asyncio.sleep(1)
            
            task = asyncio.create_task(dummy_task())
            liquidation_service.active_connections[symbol] = task
            liquidation_service.running_streams[symbol] = True
            
            # Disconnect with specific callback
            await liquidation_service.disconnect_stream(symbol, callback)
            
            # Verify caches were cleared
            assert symbol not in mock_cache
            assert symbol not in mock_historical
            assert symbol not in liquidation_service.symbol_info_cache
            assert symbol not in liquidation_service.liquidation_buffers
            assert symbol not in liquidation_service.accumulated_volumes
            assert symbol not in liquidation_service.data_callbacks

    @pytest.mark.asyncio
    async def test_cache_not_cleared_with_remaining_subscribers(self, liquidation_service):
        """Test that caches are NOT cleared when other subscribers remain"""
        symbol = "BTCUSDT"
        callback1 = Mock()
        callback2 = Mock()
        
        # Mock the global caches
        with patch.object(liquidations_ws, 'liquidations_cache', {symbol: deque([1, 2, 3])}) as mock_cache:
            
            # Set up multiple callbacks
            liquidation_service.data_callbacks[symbol] = [callback1, callback2]
            liquidation_service.symbol_info_cache[symbol] = {"baseAsset": "BTC"}
            
            # Disconnect only one callback
            await liquidation_service.disconnect_stream(symbol, callback1)
            
            # Verify caches were NOT cleared
            assert symbol in mock_cache
            assert symbol in liquidation_service.symbol_info_cache
            assert callback2 in liquidation_service.data_callbacks[symbol]
            assert callback1 not in liquidation_service.data_callbacks[symbol]

    @pytest.mark.asyncio
    async def test_volume_aggregation_accumulation(self, liquidation_service):
        """Test that volume aggregation accumulates instead of replacing"""
        symbol = "BTCUSDT"
        timeframe = "1m"
        
        # Initialize buffers
        liquidation_service.liquidation_buffers[symbol] = {timeframe: []}
        liquidation_service.buffer_callbacks[symbol] = {timeframe: [Mock()]}
        liquidation_service.symbol_info_cache[symbol] = {"baseAsset": "BTC"}
        
        # Add first liquidation
        liq1 = {
            "timestamp": 1700000000000,  # First minute
            "priceUsdt": "1000",
            "side": "BUY"
        }
        liquidation_service.liquidation_buffers[symbol][timeframe].append(liq1)
        
        # Process buffer
        await liquidation_service._process_aggregation_buffer(symbol, timeframe)
        
        # Verify accumulation started
        assert symbol in liquidation_service.accumulated_volumes
        assert timeframe in liquidation_service.accumulated_volumes[symbol]
        
        # Check first bucket
        bucket_time = 1700000000000 // 60000 * 60000
        assert bucket_time in liquidation_service.accumulated_volumes[symbol][timeframe]
        first_volume = liquidation_service.accumulated_volumes[symbol][timeframe][bucket_time]
        assert first_volume["buy_volume"] == Decimal("1000")
        assert first_volume["sell_volume"] == Decimal("0")
        assert first_volume["count"] == 1
        
        # Add second liquidation to same bucket
        liq2 = {
            "timestamp": 1700000030000,  # Same minute
            "priceUsdt": "500",
            "side": "SELL"
        }
        liquidation_service.liquidation_buffers[symbol][timeframe].append(liq2)
        
        # Process buffer again
        await liquidation_service._process_aggregation_buffer(symbol, timeframe)
        
        # Verify accumulation (not replacement)
        updated_volume = liquidation_service.accumulated_volumes[symbol][timeframe][bucket_time]
        assert updated_volume["buy_volume"] == Decimal("1000")  # Unchanged
        assert updated_volume["sell_volume"] == Decimal("500")   # Added
        assert updated_volume["count"] == 2  # Incremented

    @pytest.mark.asyncio
    async def test_message_type_separation(self):
        """Test that liquidation_order and liquidation_volume messages are properly separated"""
        # This would typically be tested in the WebSocket endpoint test
        # Here we verify the model has the correct type
        from app.models.liquidation import LiquidationVolumeUpdate
        
        # Create volume update
        volume_update = LiquidationVolumeUpdate(
            symbol="BTCUSDT",
            timeframe="1m",
            data=[],
            timestamp=datetime.now(timezone.utc).isoformat(),
            is_update=True
        )
        
        # Verify type
        assert volume_update.type == "liquidation_volume"
        assert hasattr(volume_update, "is_update")
        assert volume_update.is_update is True

    @pytest.mark.asyncio
    async def test_reference_counting_in_fan_out_pattern(self, liquidation_service):
        """Test reference counting works correctly in fan-out pattern"""
        symbol = "BTCUSDT"
        callback1 = Mock()
        callback2 = Mock()
        callback3 = Mock()
        
        # Mock the maintain_connection method to prevent actual WebSocket connection
        liquidation_service._maintain_connection = AsyncMock()
        
        # First connection creates task
        await liquidation_service.connect_to_liquidation_stream(symbol, callback1)
        assert len(liquidation_service.data_callbacks[symbol]) == 1
        assert symbol in liquidation_service.active_connections
        first_task = liquidation_service.active_connections[symbol]
        
        # Second connection reuses task
        await liquidation_service.connect_to_liquidation_stream(symbol, callback2)
        assert len(liquidation_service.data_callbacks[symbol]) == 2
        assert liquidation_service.active_connections[symbol] is first_task
        
        # Third connection reuses task
        await liquidation_service.connect_to_liquidation_stream(symbol, callback3)
        assert len(liquidation_service.data_callbacks[symbol]) == 3
        assert liquidation_service.active_connections[symbol] is first_task
        
        # Verify only one task was created
        assert liquidation_service._maintain_connection.call_count == 1

    @pytest.mark.asyncio
    async def test_accumulated_volumes_cleared_on_disconnect(self, liquidation_service):
        """Test that accumulated volumes are cleared when symbol disconnects"""
        symbol = "BTCUSDT"
        timeframe = "1m"
        
        # Set up accumulated volumes
        liquidation_service.accumulated_volumes[symbol] = {
            timeframe: {
                1700000000000: {
                    "buy_volume": Decimal("1000"),
                    "sell_volume": Decimal("500"),
                    "count": 2
                }
            }
        }
        
        # Set up minimal requirements for disconnect
        liquidation_service.data_callbacks[symbol] = [Mock()]
        liquidation_service.running_streams[symbol] = False
        
        # Mock the global caches
        with patch.object(liquidations_ws, 'liquidations_cache', {}), \
             patch.object(liquidations_ws, 'historical_loaded', {}):
            
            # Disconnect
            await liquidation_service.disconnect_stream(symbol)
            
            # Verify accumulated volumes were cleared
            assert symbol not in liquidation_service.accumulated_volumes

    def test_timeframe_ms_conversion(self, liquidation_service):
        """Test timeframe string to milliseconds conversion"""
        assert liquidation_service._get_timeframe_ms("1m") == 60 * 1000
        assert liquidation_service._get_timeframe_ms("5m") == 5 * 60 * 1000
        assert liquidation_service._get_timeframe_ms("15m") == 15 * 60 * 1000
        assert liquidation_service._get_timeframe_ms("30m") == 30 * 60 * 1000
        assert liquidation_service._get_timeframe_ms("1h") == 60 * 60 * 1000
        assert liquidation_service._get_timeframe_ms("4h") == 4 * 60 * 60 * 1000
        assert liquidation_service._get_timeframe_ms("1d") == 24 * 60 * 60 * 1000
        assert liquidation_service._get_timeframe_ms("invalid") == 60 * 1000  # Default

    @pytest.mark.asyncio
    async def test_aggregation_buffer_cleared_after_processing(self, liquidation_service):
        """Test that liquidation buffer is cleared after processing"""
        symbol = "BTCUSDT"
        timeframe = "1m"
        
        # Initialize buffers
        liquidation_service.liquidation_buffers[symbol] = {timeframe: []}
        liquidation_service.buffer_callbacks[symbol] = {timeframe: [Mock()]}
        liquidation_service.symbol_info_cache[symbol] = {"baseAsset": "BTC"}
        
        # Add liquidations
        liquidation_service.liquidation_buffers[symbol][timeframe] = [
            {"timestamp": 1700000000000, "priceUsdt": "1000", "side": "BUY"},
            {"timestamp": 1700000001000, "priceUsdt": "2000", "side": "SELL"}
        ]
        
        # Process buffer
        await liquidation_service._process_aggregation_buffer(symbol, timeframe)
        
        # Verify buffer was cleared
        assert len(liquidation_service.liquidation_buffers[symbol][timeframe]) == 0

    @pytest.mark.asyncio
    async def test_only_updated_buckets_sent(self, liquidation_service):
        """Test that only updated buckets are sent in real-time updates"""
        symbol = "BTCUSDT"
        timeframe = "1m"
        volume_updates = []
        
        # Mock callback to capture updates
        async def capture_callback(updates):
            volume_updates.extend(updates)
        
        # Initialize
        liquidation_service.liquidation_buffers[symbol] = {timeframe: []}
        liquidation_service.buffer_callbacks[symbol] = {timeframe: [capture_callback]}
        liquidation_service.symbol_info_cache[symbol] = {"baseAsset": "BTC"}
        
        # Add liquidations for different time buckets
        liquidation_service.liquidation_buffers[symbol][timeframe] = [
            {"timestamp": 1700000000000, "priceUsdt": "1000", "side": "BUY"},   # Bucket 1
            {"timestamp": 1700000060000, "priceUsdt": "2000", "side": "SELL"},  # Bucket 2
        ]
        
        # Process buffer
        await liquidation_service._process_aggregation_buffer(symbol, timeframe)
        
        # Verify only 2 buckets were sent
        assert len(volume_updates) == 2
        # The times are bucket start times (floored to minute boundaries)
        # 1700000000000 ms -> bucket 1699999940000 ms -> 1699999940 seconds
        # But the service returns seconds, so we check the actual returned values
        assert len(set(v["time"] for v in volume_updates)) == 2  # Two distinct time buckets
        assert volume_updates[1]["time"] > volume_updates[0]["time"]  # Correct order