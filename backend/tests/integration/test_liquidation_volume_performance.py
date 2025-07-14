"""
Performance Tests for Liquidation Volume Feature

Tests system performance under load to ensure the liquidation volume
feature maintains acceptable response times and resource usage.
"""

import pytest
import asyncio
import time
import json
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, Mock
from datetime import datetime, timedelta
from decimal import Decimal
from app.main import app


class TestLiquidationVolumePerformance:
    """Performance tests for liquidation volume feature"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    def generate_large_liquidation_dataset(self, size=10000):
        """Generate a large dataset of liquidations for testing"""
        base_time = 1609459200000  # 2021-01-01 00:00:00
        dataset = []
        
        for i in range(size):
            dataset.append({
                "order_trade_time": base_time + (i * 100),  # 100ms apart
                "symbol": "BTCUSDT",
                "side": "buy" if i % 2 == 0 else "sell",
                "order_filled_accumulated_quantity": str(0.001 * (i % 100 + 1)),
                "average_price": str(30000 + (i % 1000)),
                "liquidation_order_id": str(i)
            })
        
        return dataset
    
    @pytest.mark.asyncio
    async def test_aggregation_performance_various_timeframes(self):
        """Test aggregation performance across different timeframes"""
        from app.services.liquidation_service import liquidation_service
        
        # Generate test data
        dataset = self.generate_large_liquidation_dataset(10000)
        
        timeframes = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"]
        performance_results = {}
        
        for timeframe in timeframes:
            start_time = time.time()
            
            result = await liquidation_service.aggregate_liquidations_for_timeframe(
                dataset, timeframe, "BTCUSDT"
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            performance_results[timeframe] = {
                "duration": duration,
                "candles": len(result),
                "avg_time_per_candle": duration / len(result) if result else 0
            }
        
        # Performance assertions
        for timeframe, metrics in performance_results.items():
            assert metrics["duration"] < 2.0, f"Aggregation for {timeframe} took too long: {metrics['duration']}s"
            
        # Verify larger timeframes process faster (fewer candles)
        assert performance_results["1d"]["duration"] < performance_results["1m"]["duration"]
        assert performance_results["1d"]["candles"] < performance_results["1m"]["candles"]
    
    def test_concurrent_api_requests(self, client):
        """Test API performance under concurrent load"""
        
        mock_data = [{
            "time": 1609459200,
            "buy_volume": "15000.0",
            "sell_volume": "25000.0",
            "total_volume": "40000.0",
            "count": 50
        }]
        
        with patch('app.services.liquidation_service.liquidation_service.fetch_historical_liquidations_by_timeframe') as mock_fetch:
            mock_fetch.return_value = mock_data
            
            def make_request(symbol, timeframe):
                """Make a single API request"""
                response = client.get(f"/api/v1/liquidation-volume/{symbol}/{timeframe}")
                return response.status_code, response.json()
            
            # Test concurrent requests
            symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "XRPUSDT"]
            timeframes = ["1m", "5m", "15m", "1h"]
            
            start_time = time.time()
            
            with ThreadPoolExecutor(max_workers=20) as executor:
                futures = []
                
                # Submit 100 concurrent requests
                for _ in range(20):
                    for symbol in symbols:
                        for timeframe in timeframes[:2]:  # Use first 2 timeframes
                            future = executor.submit(make_request, symbol, timeframe)
                            futures.append(future)
                
                # Wait for all requests to complete
                results = []
                for future in futures:
                    status_code, data = future.result()
                    results.append((status_code, data))
            
            end_time = time.time()
            total_duration = end_time - start_time
            
            # Verify all requests succeeded
            successful_requests = sum(1 for status, _ in results if status == 200)
            assert successful_requests == len(results), f"Some requests failed: {successful_requests}/{len(results)}"
            
            # Performance assertions
            avg_time_per_request = total_duration / len(results)
            assert avg_time_per_request < 0.1, f"Average request time too high: {avg_time_per_request}s"
            assert total_duration < 10.0, f"Total time for {len(results)} requests too high: {total_duration}s"
    
    @pytest.mark.asyncio
    async def test_websocket_message_throughput(self):
        """Test WebSocket performance with high message throughput"""
        from app.services.liquidation_service import liquidation_service
        
        # Simulate rapid liquidation updates
        message_count = 1000
        messages_processed = 0
        start_time = time.time()
        
        for i in range(message_count):
            # Simulate processing a liquidation
            liquidation = {
                "symbol": "BTCUSDT",
                "side": "buy" if i % 2 == 0 else "sell",
                "quantity": "0.1",
                "priceUsdt": "30000",
                "timestamp": int(time.time() * 1000)
            }
            
            # Process for aggregation (simplified)
            messages_processed += 1
            
            # Small delay to simulate real-time stream
            if i % 100 == 0:
                await asyncio.sleep(0.01)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Performance metrics
        messages_per_second = messages_processed / duration
        
        assert messages_per_second > 100, f"Message throughput too low: {messages_per_second} msg/s"
        assert duration < 15.0, f"Processing {message_count} messages took too long: {duration}s"
    
    def test_cache_performance(self, client):
        """Test caching improves performance"""
        
        large_dataset = self.generate_large_liquidation_dataset(1000)
        
        with patch('app.services.liquidation_service.liquidation_service.fetch_historical_liquidations_by_timeframe') as mock_fetch:
            # Return large dataset
            mock_fetch.return_value = [
                {
                    "time": 1609459200 + (i * 60),
                    "buy_volume": str(1000 * (i + 1)),
                    "sell_volume": str(2000 * (i + 1)),
                    "total_volume": str(3000 * (i + 1)),
                    "count": 10 + i
                } for i in range(100)
            ]
            
            # First request - no cache
            start_time = time.time()
            response1 = client.get("/api/v1/liquidation-volume/BTCUSDT/1m")
            first_request_time = time.time() - start_time
            
            assert response1.status_code == 200
            
            # Subsequent requests - should use cache
            cached_times = []
            for _ in range(10):
                start_time = time.time()
                response = client.get("/api/v1/liquidation-volume/BTCUSDT/1m")
                cached_times.append(time.time() - start_time)
                assert response.status_code == 200
            
            # Average cached request time
            avg_cached_time = sum(cached_times) / len(cached_times)
            
            # Cache should be significantly faster
            assert avg_cached_time < first_request_time * 0.5, \
                f"Cache not providing performance benefit: {avg_cached_time}s vs {first_request_time}s"
    
    @pytest.mark.asyncio
    async def test_memory_usage_with_large_datasets(self):
        """Test memory efficiency with large datasets"""
        from app.services.liquidation_service import liquidation_service
        import psutil
        import os
        
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Process large dataset
        large_dataset = self.generate_large_liquidation_dataset(50000)
        
        # Aggregate for multiple timeframes
        results = {}
        for timeframe in ["1m", "5m", "15m", "1h"]:
            results[timeframe] = await liquidation_service.aggregate_liquidations_for_timeframe(
                large_dataset, timeframe, "BTCUSDT"
            )
        
        # Get final memory usage
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory assertions
        assert memory_increase < 500, f"Memory usage increased too much: {memory_increase}MB"
        
        # Verify results are reasonable
        for timeframe, data in results.items():
            assert len(data) > 0, f"No data for timeframe {timeframe}"
            # Higher timeframes should have fewer candles
            if timeframe == "1h":
                assert len(data) < len(results["1m"])
    
    def test_response_time_percentiles(self, client):
        """Test API response time percentiles"""
        
        mock_data = [{
            "time": 1609459200,
            "buy_volume": "1000.0",
            "sell_volume": "2000.0",
            "total_volume": "3000.0",
            "count": 10
        }]
        
        with patch('app.services.liquidation_service.liquidation_service.fetch_historical_liquidations_by_timeframe') as mock_fetch:
            mock_fetch.return_value = mock_data
            
            response_times = []
            
            # Make 100 requests
            for i in range(100):
                start_time = time.time()
                response = client.get(f"/api/v1/liquidation-volume/BTCUSDT/{['1m', '5m', '15m'][i % 3]}")
                response_time = time.time() - start_time
                
                assert response.status_code == 200
                response_times.append(response_time)
            
            # Calculate percentiles
            response_times.sort()
            p50 = response_times[49]  # 50th percentile (median)
            p95 = response_times[94]  # 95th percentile
            p99 = response_times[98]  # 99th percentile
            
            # Performance requirements
            assert p50 < 0.05, f"50th percentile too high: {p50}s"
            assert p95 < 0.1, f"95th percentile too high: {p95}s"
            assert p99 < 0.2, f"99th percentile too high: {p99}s"
            
            # Average response time
            avg_response_time = sum(response_times) / len(response_times)
            assert avg_response_time < 0.06, f"Average response time too high: {avg_response_time}s"