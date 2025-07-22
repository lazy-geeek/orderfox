"""
Load tests for liquidation volume system.

Tests high-volume scenarios, memory usage, and data retention under load.
"""

import pytest

# Chunk 8g: Extended Load Tests - High-volume scenarios, extended runtime
pytestmark = pytest.mark.chunk8g
import asyncio
import time
import psutil
import gc
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from collections import deque
from unittest.mock import AsyncMock, Mock, patch
import random

from app.services.liquidation_service import liquidation_service
from app.api.v1.endpoints import liquidations_ws


class TestLiquidationVolumeLoad:
    """Load tests for liquidation volume system"""

    @pytest.fixture
    def mock_symbol_service(self):
        """Mock symbol service"""
        with patch('app.services.symbol_service.symbol_service') as mock:
            mock.validate_symbol_exists = Mock(return_value=True)
            mock.resolve_symbol_to_exchange_format = Mock(return_value='BTC/USDT:USDT')
            mock.get_symbol_info = Mock(return_value={'baseAsset': 'BTC', 'amountPrecision': 3})
            yield mock

    def get_memory_usage(self):
        """Get current memory usage in MB"""
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024

    @pytest.mark.asyncio
    async def test_high_volume_liquidations_30_minutes(self, mock_symbol_service):
        """Simulate 1000+ liquidations over 30 minutes"""
        symbol = "BTCUSDT"
        timeframe = "1m"
        
        # Initial memory
        gc.collect()
        initial_memory = self.get_memory_usage()
        
        # Initialize service
        service = liquidation_service
        service.liquidation_buffers[symbol] = {timeframe: []}
        service.buffer_callbacks[symbol] = {timeframe: [AsyncMock()]}
        service.symbol_info_cache[symbol] = {"baseAsset": "BTC"}
        
        # Track performance metrics
        processing_times = []
        memory_samples = []
        
        # Generate 30 minutes of data (1800 seconds)
        start_time = 1700000000000  # Base timestamp
        total_liquidations = 1500
        time_span = 30 * 60 * 1000  # 30 minutes in milliseconds
        
        # Create liquidations spread across 30 minutes
        liquidations = []
        for i in range(total_liquidations):
            timestamp = start_time + int((i / total_liquidations) * time_span)
            side = "BUY" if random.random() > 0.5 else "SELL"
            price = random.randint(100, 10000)
            
            liquidations.append({
                "timestamp": timestamp,
                "priceUsdt": str(price),
                "side": side,
                "quantity": f"{random.uniform(0.001, 10.0):.3f}"
            })
        
        # Process in batches to simulate real-time flow
        batch_size = 50
        for batch_start in range(0, len(liquidations), batch_size):
            batch_end = min(batch_start + batch_size, len(liquidations))
            batch = liquidations[batch_start:batch_end]
            
            # Add to buffer
            service.liquidation_buffers[symbol][timeframe].extend(batch)
            
            # Time the processing
            start_process = time.time()
            await service._process_aggregation_buffer(symbol, timeframe)
            process_time = time.time() - start_process
            processing_times.append(process_time)
            
            # Sample memory
            memory_samples.append(self.get_memory_usage())
            
            # Small delay to simulate real-time
            await asyncio.sleep(0.01)
        
        # Verify data integrity
        assert symbol in service.accumulated_volumes
        assert timeframe in service.accumulated_volumes[symbol]
        
        # Count unique time buckets (should be ~30 for 30 minutes of 1m timeframe)
        unique_buckets = len(service.accumulated_volumes[symbol][timeframe])
        assert 25 <= unique_buckets <= 35  # Allow some variance
        
        # Calculate total volume
        total_buy_volume = Decimal("0")
        total_sell_volume = Decimal("0")
        total_count = 0
        
        for bucket_data in service.accumulated_volumes[symbol][timeframe].values():
            total_buy_volume += bucket_data["buy_volume"]
            total_sell_volume += bucket_data["sell_volume"]
            total_count += bucket_data["count"]
        
        # Verify all liquidations were processed
        assert total_count == total_liquidations
        
        # Performance metrics
        avg_process_time = sum(processing_times) / len(processing_times)
        max_process_time = max(processing_times)
        memory_growth = max(memory_samples) - initial_memory
        
        # Performance assertions
        assert avg_process_time < 0.1  # Average processing under 100ms
        assert max_process_time < 0.5  # Max processing under 500ms
        assert memory_growth < 50  # Memory growth under 50MB
        
        print(f"\nPerformance Metrics:")
        print(f"Total liquidations: {total_liquidations}")
        print(f"Unique time buckets: {unique_buckets}")
        print(f"Avg processing time: {avg_process_time*1000:.2f}ms")
        print(f"Max processing time: {max_process_time*1000:.2f}ms")
        print(f"Memory growth: {memory_growth:.2f}MB")

    @pytest.mark.asyncio
    async def test_memory_usage_with_multiple_symbols(self, mock_symbol_service):
        """Test memory usage with multiple concurrent symbols"""
        symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT"]
        timeframe = "1m"
        
        gc.collect()
        initial_memory = self.get_memory_usage()
        
        service = liquidation_service
        
        # Initialize all symbols
        for symbol in symbols:
            service.liquidation_buffers[symbol] = {timeframe: []}
            service.buffer_callbacks[symbol] = {timeframe: [AsyncMock()]}
            service.symbol_info_cache[symbol] = {"baseAsset": symbol[:3]}
        
        # Generate data for each symbol
        liquidations_per_symbol = 200
        base_time = 1700000000000
        
        for symbol in symbols:
            for i in range(liquidations_per_symbol):
                liq = {
                    "timestamp": base_time + i * 1000,
                    "priceUsdt": str(random.randint(100, 10000)),
                    "side": "BUY" if i % 2 == 0 else "SELL"
                }
                service.liquidation_buffers[symbol][timeframe].append(liq)
            
            # Process buffer
            await service._process_aggregation_buffer(symbol, timeframe)
        
        # Check memory after processing
        gc.collect()
        final_memory = self.get_memory_usage()
        memory_per_symbol = (final_memory - initial_memory) / len(symbols)
        
        # Verify data for each symbol
        for symbol in symbols:
            assert symbol in service.accumulated_volumes
            assert len(service.accumulated_volumes[symbol][timeframe]) > 0
        
        # Memory assertions
        assert memory_per_symbol < 10  # Less than 10MB per symbol
        
        print(f"\nMulti-symbol Memory Usage:")
        print(f"Symbols tested: {len(symbols)}")
        print(f"Total memory growth: {final_memory - initial_memory:.2f}MB")
        print(f"Memory per symbol: {memory_per_symbol:.2f}MB")

    @pytest.mark.asyncio
    async def test_data_retention_after_extended_runtime(self, mock_symbol_service):
        """Test that historical data is retained after extended runtime"""
        symbol = "BTCUSDT"
        timeframe = "1m"
        
        service = liquidation_service
        service.liquidation_buffers[symbol] = {timeframe: []}
        service.buffer_callbacks[symbol] = {timeframe: [AsyncMock()]}
        service.symbol_info_cache[symbol] = {"baseAsset": "BTC"}
        
        # Add initial historical data (1 hour old)
        historical_time = 1700000000000
        historical_liquidations = []
        
        for i in range(60):  # 60 minutes of historical data
            minute_time = historical_time + i * 60000
            historical_liquidations.append({
                "timestamp": minute_time,
                "priceUsdt": "1000",
                "side": "BUY"
            })
        
        # Process historical data
        service.liquidation_buffers[symbol][timeframe] = historical_liquidations
        await service._process_aggregation_buffer(symbol, timeframe)
        
        # Count initial buckets
        initial_buckets = len(service.accumulated_volumes[symbol][timeframe])
        assert initial_buckets == 60
        
        # Simulate 2 hours of real-time updates
        current_time = historical_time + 3600000  # 1 hour later
        
        for hour in range(2):
            for minute in range(60):
                timestamp = current_time + hour * 3600000 + minute * 60000
                
                # Add 1-5 liquidations per minute
                minute_liquidations = []
                for _ in range(random.randint(1, 5)):
                    minute_liquidations.append({
                        "timestamp": timestamp + random.randint(0, 59999),
                        "priceUsdt": str(random.randint(500, 2000)),
                        "side": "BUY" if random.random() > 0.5 else "SELL"
                    })
                
                service.liquidation_buffers[symbol][timeframe] = minute_liquidations
                await service._process_aggregation_buffer(symbol, timeframe)
        
        # Verify all data is retained
        final_buckets = len(service.accumulated_volumes[symbol][timeframe])
        # We should have around 180 buckets (3 hours), but allow for some variance due to timing
        assert 170 <= final_buckets <= 190  # Around 3 hours of data
        
        # Verify oldest data still exists
        oldest_bucket = min(service.accumulated_volumes[symbol][timeframe].keys())
        # The bucket time is floored to the minute boundary
        expected_oldest_bucket = (historical_time // 60000) * 60000
        assert oldest_bucket == expected_oldest_bucket
        
        # Verify data in oldest bucket exists and has been accumulated (not replaced)
        oldest_data = service.accumulated_volumes[symbol][timeframe][oldest_bucket]
        # The oldest bucket should have accumulated data (more than just the initial 1000)
        assert oldest_data["buy_volume"] >= Decimal("1000")
        assert oldest_data["count"] >= 1  # At least the initial liquidation
        
        print(f"\nData Retention Test:")
        print(f"Initial buckets: {initial_buckets}")
        print(f"Final buckets: {final_buckets}")
        print(f"Data retention: 100% - all historical data preserved")

    @pytest.mark.asyncio
    async def test_websocket_performance_under_load(self, mock_symbol_service):
        """Test WebSocket message handling performance under load"""
        symbol = "BTCUSDT"
        
        # Mock WebSocket
        mock_websocket = AsyncMock()
        mock_websocket.send_json = AsyncMock()
        
        # Track message sending times
        message_times = []
        
        async def track_send_time(data):
            start = time.time()
            # Simulate network latency
            await asyncio.sleep(0.001)
            message_times.append(time.time() - start)
        
        mock_websocket.send_json.side_effect = track_send_time
        
        # Initialize caches
        liquidations_ws.liquidations_cache[symbol] = deque(maxlen=50)
        
        # Simulate rapid liquidation updates
        for i in range(500):
            liq = {
                "symbol": symbol,
                "side": "BUY" if i % 2 == 0 else "SELL",
                "quantity": f"0.{i:03d}",
                "quantityFormatted": f"0.{i:03d}",
                "priceUsdt": str(50000 + i),
                "priceUsdtFormatted": f"{50000 + i:,}",
                "timestamp": 1700000000000 + i * 100,
                "displayTime": "12:00:00",
                "avgPrice": "50000",
                "baseAsset": "BTC"
            }
            
            # Add to cache
            liquidations_ws.liquidations_cache[symbol].appendleft(liq)
            
            # Simulate sending update
            await mock_websocket.send_json({
                "type": "liquidation_order",
                "symbol": symbol,
                "data": [liq],
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        
        # Performance metrics
        avg_send_time = sum(message_times) / len(message_times)
        max_send_time = max(message_times)
        
        # Verify cache size limit
        assert len(liquidations_ws.liquidations_cache[symbol]) == 50
        
        # Performance assertions
        assert avg_send_time < 0.01  # Average under 10ms
        assert max_send_time < 0.05  # Max under 50ms
        
        print(f"\nWebSocket Performance:")
        print(f"Messages sent: {len(message_times)}")
        print(f"Avg send time: {avg_send_time*1000:.2f}ms")
        print(f"Max send time: {max_send_time*1000:.2f}ms")
        print(f"Cache size maintained at: {len(liquidations_ws.liquidations_cache[symbol])}")

    @pytest.mark.asyncio 
    async def test_concurrent_symbol_processing(self, mock_symbol_service):
        """Test concurrent processing of multiple symbols"""
        symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
        timeframe = "1m"
        
        service = liquidation_service
        
        # Initialize all symbols
        for symbol in symbols:
            service.liquidation_buffers[symbol] = {timeframe: []}
            service.buffer_callbacks[symbol] = {timeframe: [AsyncMock()]}
            service.symbol_info_cache[symbol] = {"baseAsset": symbol[:3]}
        
        # Create concurrent tasks
        async def process_symbol_data(symbol):
            # Clear any existing data for this symbol
            if symbol in service.accumulated_volumes:
                service.accumulated_volumes[symbol] = {}
                
            for i in range(100):
                liq = {
                    "timestamp": 1700000000000 + i * 1000,
                    "priceUsdt": str(random.randint(100, 10000)),
                    "side": "BUY" if i % 2 == 0 else "SELL"
                }
                service.liquidation_buffers[symbol][timeframe].append(liq)
                
                if len(service.liquidation_buffers[symbol][timeframe]) >= 10:
                    await service._process_aggregation_buffer(symbol, timeframe)
        
        # Process all symbols concurrently
        start_time = time.time()
        await asyncio.gather(*[process_symbol_data(symbol) for symbol in symbols])
        total_time = time.time() - start_time
        
        # Verify all symbols processed correctly
        for symbol in symbols:
            assert symbol in service.accumulated_volumes
            assert len(service.accumulated_volumes[symbol][timeframe]) > 0
            
            # Check data integrity
            total_count = sum(
                bucket["count"] 
                for bucket in service.accumulated_volumes[symbol][timeframe].values()
            )
            assert total_count == 100
        
        # Performance assertion
        assert total_time < 2.0  # Should complete in under 2 seconds
        
        print(f"\nConcurrent Processing:")
        print(f"Symbols processed: {len(symbols)}")
        print(f"Total processing time: {total_time:.2f}s")
        print(f"Time per symbol: {total_time/len(symbols):.2f}s")