import pytest
import asyncio
import time
import statistics
from unittest.mock import AsyncMock, MagicMock, patch
from concurrent.futures import ThreadPoolExecutor
import json

from app.services.orderbook_aggregation_service import OrderBookAggregationService
from app.services.orderbook_manager import OrderBookManager
from app.api.v1.endpoints.connection_manager import ConnectionManager
from app.models.orderbook import OrderBook, OrderBookLevel


class TestOrderBookPerformance:
    """
    Load tests for orderbook performance validation.
    Tests latency, throughput, memory usage, and scalability under various loads.
    """

    @pytest.fixture
    def performance_setup(self):
        """Setup for performance tests with isolated components."""
        async def _setup():
            # Create isolated instances
            aggregation_service = OrderBookAggregationService()
            
            orderbook_manager = OrderBookManager.__new__(OrderBookManager)
            orderbook_manager._initialized = False
            orderbook_manager.__init__()
            orderbook_manager._aggregation_service = aggregation_service
            
            connection_manager = ConnectionManager()
            connection_manager.orderbook_manager = orderbook_manager
            
            return {
                'aggregation_service': aggregation_service,
                'orderbook_manager': orderbook_manager,
                'connection_manager': connection_manager
            }
        
        return _setup()

    @pytest.fixture
    def large_orderbook_data(self):
        """Generate large orderbook dataset for testing."""
        # Generate 1000 bid levels
        bids = []
        for i in range(1000):
            price = 50000.0 - i * 0.1
            amount = 1.0 + (i % 10) * 0.5
            bids.append(MagicMock(price=price, amount=amount))
        
        # Generate 1000 ask levels
        asks = []
        for i in range(1000):
            price = 50001.0 + i * 0.1
            amount = 1.0 + (i % 10) * 0.5
            asks.append(MagicMock(price=price, amount=amount))
        
        return bids, asks

    @staticmethod
    def create_mock_orderbook(symbol, bids, asks):
        """Create a mock orderbook with specified data."""
        orderbook = AsyncMock(spec=OrderBook)
        orderbook.symbol = symbol
        orderbook.timestamp = time.time() * 1000
        orderbook.latest_snapshot = True  # For cache warming
        
        mock_snapshot = MagicMock()
        mock_snapshot.bids = bids
        mock_snapshot.asks = asks
        orderbook.get_snapshot.return_value = mock_snapshot
        
        return orderbook

    class TestAggregationPerformance:
        """Test aggregation performance under various conditions."""

        @pytest.mark.asyncio
        async def test_aggregation_latency_single_request(self, performance_setup, large_orderbook_data):
            """Test aggregation latency for single requests."""
            setup = await performance_setup
            aggregation_service = setup['aggregation_service']
            bids, asks = large_orderbook_data
            
            orderbook = TestOrderBookPerformance.create_mock_orderbook("BTCUSDT", bids, asks)
            
            # Test different parameter combinations
            test_cases = [
                (10, 1.0),
                (20, 0.5),
                (50, 0.1),
                (100, 0.01)
            ]
            
            latencies = []
            
            for limit, rounding in test_cases:
                start_time = time.perf_counter()
                result = await aggregation_service.aggregate_orderbook(orderbook, limit, rounding)
                end_time = time.perf_counter()
                
                latency = (end_time - start_time) * 1000  # Convert to milliseconds
                latencies.append(latency)
                
                # Verify result structure
                assert 'bids' in result
                assert 'asks' in result
                assert len(result['bids']) <= limit
                assert len(result['asks']) <= limit
            
            # Performance requirements
            avg_latency = statistics.mean(latencies)
            max_latency = max(latencies)
            
            print(f"Aggregation latencies: {latencies}")
            print(f"Average latency: {avg_latency:.2f}ms")
            print(f"Max latency: {max_latency:.2f}ms")
            
            # Latency should be under 50ms for single requests
            assert avg_latency < 50, f"Average latency too high: {avg_latency}ms"
            assert max_latency < 100, f"Max latency too high: {max_latency}ms"

        @pytest.mark.asyncio
        async def test_aggregation_throughput(self, performance_setup, large_orderbook_data):
            """Test aggregation throughput under concurrent load."""
            setup = await performance_setup
            aggregation_service = setup['aggregation_service']
            bids, asks = large_orderbook_data
            
            orderbook = TestOrderBookPerformance.create_mock_orderbook("BTCUSDT", bids, asks)
            
            # Test concurrent requests
            num_requests = 100
            limit = 20
            rounding = 1.0
            
            async def single_aggregation():
                return await aggregation_service.aggregate_orderbook(orderbook, limit, rounding)
            
            # Measure throughput
            start_time = time.perf_counter()
            
            # Run concurrent aggregations
            tasks = [asyncio.create_task(single_aggregation()) for _ in range(num_requests)]
            results = await asyncio.gather(*tasks)
            
            end_time = time.perf_counter()
            
            total_time = end_time - start_time
            throughput = num_requests / total_time
            
            print(f"Processed {num_requests} requests in {total_time:.2f}s")
            print(f"Throughput: {throughput:.2f} requests/second")
            
            # Verify all requests succeeded
            assert len(results) == num_requests
            for result in results:
                assert result is not None
                assert 'bids' in result
                assert 'asks' in result
            
            # Throughput should be at least 100 requests/second
            assert throughput >= 100, f"Throughput too low: {throughput:.2f} req/s"

        @pytest.mark.asyncio
        async def test_cache_performance_impact(self, performance_setup, large_orderbook_data):
            """Test performance impact of caching."""
            setup = await performance_setup
            aggregation_service = setup['aggregation_service']
            bids, asks = large_orderbook_data
            
            orderbook = TestOrderBookPerformance.create_mock_orderbook("BTCUSDT", bids, asks)
            
            limit = 20
            rounding = 1.0
            
            # First request (cache miss)
            start_time = time.perf_counter()
            result1 = await aggregation_service.aggregate_orderbook(orderbook, limit, rounding)
            cache_miss_time = time.perf_counter() - start_time
            
            # Second request (cache hit)
            start_time = time.perf_counter()
            result2 = await aggregation_service.aggregate_orderbook(orderbook, limit, rounding)
            cache_hit_time = time.perf_counter() - start_time
            
            # Results should be identical
            assert result1 == result2
            
            # Cache hit should be significantly faster
            speedup = cache_miss_time / cache_hit_time
            
            print(f"Cache miss time: {cache_miss_time*1000:.2f}ms")
            print(f"Cache hit time: {cache_hit_time*1000:.2f}ms")
            print(f"Cache speedup: {speedup:.1f}x")
            
            # Cache should provide at least 10x speedup
            assert speedup >= 10, f"Cache speedup insufficient: {speedup:.1f}x"

        @pytest.mark.asyncio
        async def test_rounding_performance_scaling(self, performance_setup, large_orderbook_data):
            """Test how performance scales with different rounding values."""
            setup = await performance_setup
            aggregation_service = setup['aggregation_service']
            bids, asks = large_orderbook_data
            
            orderbook = TestOrderBookPerformance.create_mock_orderbook("BTCUSDT", bids, asks)
            
            # Test different rounding values (more aggregation = potentially better performance)
            rounding_values = [0.01, 0.1, 1.0, 10.0, 100.0]
            limit = 50
            
            performance_data = []
            
            for rounding in rounding_values:
                start_time = time.perf_counter()
                result = await aggregation_service.aggregate_orderbook(orderbook, limit, rounding)
                end_time = time.perf_counter()
                
                latency = (end_time - start_time) * 1000
                levels_returned = len(result['bids']) + len(result['asks'])
                
                performance_data.append({
                    'rounding': rounding,
                    'latency': latency,
                    'levels': levels_returned
                })
                
                print(f"Rounding {rounding}: {latency:.2f}ms, {levels_returned} levels")
            
            # All requests should complete within reasonable time
            for data in performance_data:
                assert data['latency'] < 100, f"Rounding {data['rounding']} too slow: {data['latency']}ms"

    class TestConnectionManagerPerformance:
        """Test connection manager performance."""

        @pytest.mark.asyncio
        async def test_multiple_connections_performance(self, performance_setup, large_orderbook_data):
            """Test performance with multiple concurrent connections."""
            setup = await performance_setup
            connection_manager = setup['connection_manager']
            bids, asks = large_orderbook_data
            
            symbol = "BTCUSDT"
            num_connections = 50
            
            with patch('app.services.orderbook_manager.OrderBook') as mock_orderbook_class:
                mock_orderbook = TestOrderBookPerformance.create_mock_orderbook(symbol, bids, asks)
                mock_orderbook_class.return_value = mock_orderbook
                
                # Create mock websockets
                websockets = []
                connection_ids = []
                
                for i in range(num_connections):
                    ws = AsyncMock()
                    ws.accept = AsyncMock()
                    ws.send_text = AsyncMock()
                    websockets.append(ws)
                    connection_ids.append(f"perf_conn_{i}")
                
                # Measure connection establishment time
                start_time = time.perf_counter()
                
                # Establish all connections concurrently
                connection_tasks = []
                for i in range(num_connections):
                    task = asyncio.create_task(
                        connection_manager.connect_orderbook(
                            websockets[i], connection_ids[i], symbol, 10, 1.0
                        )
                    )
                    connection_tasks.append(task)
                
                await asyncio.gather(*connection_tasks)
                
                connection_time = time.perf_counter() - start_time
                
                print(f"Established {num_connections} connections in {connection_time:.2f}s")
                print(f"Connection rate: {num_connections/connection_time:.2f} conn/s")
                
                # Test broadcast performance
                start_time = time.perf_counter()
                await connection_manager._broadcast_to_all_symbol_connections(symbol)
                broadcast_time = time.perf_counter() - start_time
                
                print(f"Broadcast to {num_connections} connections: {broadcast_time*1000:.2f}ms")
                
                # Verify all connections received data
                for ws in websockets:
                    ws.send_text.assert_called()
                
                # Performance requirements
                assert connection_time < 5.0, f"Connection establishment too slow: {connection_time}s"
                assert broadcast_time < 0.5, f"Broadcast too slow: {broadcast_time}s"

        @pytest.mark.asyncio
        async def test_parameter_update_performance(self, performance_setup, large_orderbook_data):
            """Test parameter update performance under load."""
            setup = await performance_setup
            connection_manager = setup['connection_manager']
            bids, asks = large_orderbook_data
            
            symbol = "BTCUSDT"
            connection_id = "param_perf_test"
            
            with patch('app.services.orderbook_manager.OrderBook') as mock_orderbook_class:
                mock_orderbook = TestOrderBookPerformance.create_mock_orderbook(symbol, bids, asks)
                mock_orderbook_class.return_value = mock_orderbook
                
                # Setup connection
                ws = AsyncMock()
                ws.accept = AsyncMock()
                ws.send_text = AsyncMock()
                
                await connection_manager.connect_orderbook(ws, connection_id, symbol, 10, 1.0)
                
                # Test rapid parameter updates
                num_updates = 100
                update_latencies = []
                
                for i in range(num_updates):
                    update_message = {
                        'type': 'update_params',
                        'limit': 10 + (i % 5),
                        'rounding': 1.0 + (i % 3) * 0.5
                    }
                    
                    start_time = time.perf_counter()
                    await connection_manager.handle_websocket_message(
                        ws, symbol, update_message
                    )
                    end_time = time.perf_counter()
                    
                    latency = (end_time - start_time) * 1000
                    update_latencies.append(latency)
                
                avg_latency = statistics.mean(update_latencies)
                max_latency = max(update_latencies)
                
                print(f"Parameter update - Avg: {avg_latency:.2f}ms, Max: {max_latency:.2f}ms")
                
                # Parameter updates should be fast
                assert avg_latency < 10, f"Parameter update avg latency too high: {avg_latency}ms"
                assert max_latency < 50, f"Parameter update max latency too high: {max_latency}ms"

    class TestMemoryPerformance:
        """Test memory usage and cleanup performance."""

        @pytest.mark.asyncio
        async def test_memory_scaling_with_connections(self, performance_setup, large_orderbook_data):
            """Test memory scaling with number of connections."""
            setup = await performance_setup
            orderbook_manager = setup['orderbook_manager']
            bids, asks = large_orderbook_data
            
            symbol = "BTCUSDT"
            
            with patch('app.services.orderbook_manager.OrderBook') as mock_orderbook_class:
                mock_orderbook = TestOrderBookPerformance.create_mock_orderbook(symbol, bids, asks)
                mock_orderbook_class.return_value = mock_orderbook
                
                # Test different connection counts
                connection_counts = [10, 50, 100, 200]
                memory_stats = []
                
                for count in connection_counts:
                    # Register connections
                    connection_ids = []
                    for i in range(count):
                        conn_id = f"mem_test_{count}_{i}"
                        await orderbook_manager.register_connection(conn_id, symbol, 10, 1.0)
                        connection_ids.append(conn_id)
                    
                    # Get stats
                    stats = await orderbook_manager.get_stats()
                    memory_stats.append({
                        'connections': count,
                        'memory_estimate': stats['memory_usage_estimate'],
                        'cache_size': stats['cache_size']
                    })
                    
                    # Cleanup connections
                    for conn_id in connection_ids:
                        await orderbook_manager.unregister_connection(conn_id)
                
                # Analyze memory scaling
                for i, stats in enumerate(memory_stats):
                    print(f"Connections: {stats['connections']}, "
                          f"Memory: {stats['memory_estimate']} bytes, "
                          f"Cache: {stats['cache_size']}")
                
                # Memory should scale roughly linearly
                if len(memory_stats) >= 2:
                    ratio = memory_stats[-1]['memory_estimate'] / memory_stats[0]['memory_estimate']
                    conn_ratio = memory_stats[-1]['connections'] / memory_stats[0]['connections']
                    
                    # Memory scaling should not be exponential
                    assert ratio <= conn_ratio * 2, f"Memory scaling too aggressive: {ratio}x for {conn_ratio}x connections"

        @pytest.mark.asyncio
        async def test_cache_memory_bounds(self, performance_setup, large_orderbook_data):
            """Test that cache memory usage is bounded."""
            setup = await performance_setup
            aggregation_service = setup['aggregation_service']
            bids, asks = large_orderbook_data
            
            # Create many different orderbooks to fill cache
            symbols = [f"SYMBOL{i}" for i in range(200)]
            
            for symbol in symbols:
                orderbook = TestOrderBookPerformance.create_mock_orderbook(symbol, bids, asks)
                
                # Make multiple requests to fill cache
                for limit in [10, 20, 50]:
                    for rounding in [0.1, 1.0, 10.0]:
                        await aggregation_service.aggregate_orderbook(orderbook, limit, rounding)
            
            # Check cache size
            metrics = await aggregation_service.get_cache_metrics()
            
            print(f"Cache size after heavy usage: {metrics['cache_size']}")
            print(f"Cache hit rate: {metrics['hit_rate_percent']:.1f}%")
            
            # Cache should be bounded (shouldn't exceed reasonable limits)
            assert metrics['cache_size'] <= 200, f"Cache size too large: {metrics['cache_size']}"

    class TestScalabilityLimits:
        """Test system behavior at scalability limits."""

        @pytest.mark.asyncio
        async def test_maximum_symbols_handling(self, performance_setup, large_orderbook_data):
            """Test handling maximum number of symbols."""
            setup = await performance_setup
            orderbook_manager = setup['orderbook_manager']
            bids, asks = large_orderbook_data
            
            # Test with many symbols
            num_symbols = 100
            symbols = [f"PAIR{i}USDT" for i in range(num_symbols)]
            
            with patch('app.services.orderbook_manager.OrderBook') as mock_orderbook_class:
                def create_mock_for_symbol(symbol):
                    return TestOrderBookPerformance.create_mock_orderbook(symbol, bids, asks)
                
                mock_orderbook_class.side_effect = create_mock_for_symbol
                
                # Register one connection per symbol
                start_time = time.perf_counter()
                
                for i, symbol in enumerate(symbols):
                    await orderbook_manager.register_connection(f"conn_{i}", symbol, 10, 1.0)
                
                registration_time = time.perf_counter() - start_time
                
                print(f"Registered {num_symbols} symbols in {registration_time:.2f}s")
                
                # Get final stats
                stats = await orderbook_manager.get_stats()
                print(f"Active orderbooks: {stats['active_orderbooks']}")
                print(f"Total connections: {stats['total_connections']}")
                
                # Should handle 100 symbols efficiently
                assert registration_time < 10.0, f"Symbol registration too slow: {registration_time}s"
                assert stats['active_orderbooks'] == num_symbols

        @pytest.mark.asyncio
        async def test_sustained_load_stability(self, performance_setup, large_orderbook_data):
            """Test system stability under sustained load."""
            setup = await performance_setup
            connection_manager = setup['connection_manager']
            bids, asks = large_orderbook_data
            
            symbol = "BTCUSDT"
            connection_id = "sustained_test"
            
            with patch('app.services.orderbook_manager.OrderBook') as mock_orderbook_class:
                mock_orderbook = TestOrderBookPerformance.create_mock_orderbook(symbol, bids, asks)
                mock_orderbook_class.return_value = mock_orderbook
                
                # Setup connection
                ws = AsyncMock()
                ws.accept = AsyncMock()
                ws.send_text = AsyncMock()
                
                await connection_manager.connect_orderbook(ws, connection_id, symbol, 10, 1.0)
                
                # Sustained load simulation
                duration = 5.0  # 5 seconds of sustained load
                operations_per_second = 50
                
                start_time = time.perf_counter()
                operation_count = 0
                latencies = []
                
                while time.perf_counter() - start_time < duration:
                    # Alternate between parameter updates and broadcasts
                    if operation_count % 2 == 0:
                        # Parameter update
                        update_message = {
                            'type': 'update_params',
                            'limit': 10 + (operation_count % 5),
                            'rounding': 1.0 + (operation_count % 3) * 0.5
                        }
                        
                        op_start = time.perf_counter()
                        await connection_manager.handle_websocket_message(
                            ws, symbol, update_message
                        )
                        op_end = time.perf_counter()
                    else:
                        # Broadcast
                        op_start = time.perf_counter()
                        await connection_manager._broadcast_to_all_symbol_connections(symbol)
                        op_end = time.perf_counter()
                    
                    latencies.append((op_end - op_start) * 1000)
                    operation_count += 1
                    
                    # Control rate
                    await asyncio.sleep(1.0 / operations_per_second)
                
                # Analyze sustained performance
                avg_latency = statistics.mean(latencies)
                p95_latency = statistics.quantiles(latencies, n=20)[18]  # 95th percentile
                
                print(f"Sustained load results:")
                print(f"Operations: {operation_count}")
                print(f"Average latency: {avg_latency:.2f}ms")
                print(f"95th percentile latency: {p95_latency:.2f}ms")
                
                # Performance should remain stable under sustained load
                assert avg_latency < 20, f"Sustained avg latency too high: {avg_latency}ms"
                assert p95_latency < 100, f"Sustained p95 latency too high: {p95_latency}ms"

    class TestConcurrencyPerformance:
        """Test performance under high concurrency."""

        @pytest.mark.asyncio
        async def test_high_concurrency_aggregation(self, performance_setup, large_orderbook_data):
            """Test aggregation performance under high concurrency."""
            setup = await performance_setup
            aggregation_service = setup['aggregation_service']
            bids, asks = large_orderbook_data
            
            # Create multiple orderbooks for different symbols
            symbols = ["BTCUSDT", "ETHUSDT", "ADAUSDT", "DOTUSDT", "LINKUSDT"]
            orderbooks = {}
            
            for symbol in symbols:
                orderbooks[symbol] = TestOrderBookPerformance.create_mock_orderbook(symbol, bids, asks)
            
            # High concurrency test
            num_concurrent_requests = 200
            requests_per_symbol = num_concurrent_requests // len(symbols)
            
            async def concurrent_aggregation(symbol, request_id):
                orderbook = orderbooks[symbol]
                limit = 10 + (request_id % 5)
                rounding = 1.0 + (request_id % 3) * 0.5
                
                start_time = time.perf_counter()
                result = await aggregation_service.aggregate_orderbook(orderbook, limit, rounding)
                end_time = time.perf_counter()
                
                return {
                    'symbol': symbol,
                    'request_id': request_id,
                    'latency': (end_time - start_time) * 1000,
                    'success': result is not None
                }
            
            # Create all concurrent tasks
            tasks = []
            for symbol in symbols:
                for i in range(requests_per_symbol):
                    task = asyncio.create_task(concurrent_aggregation(symbol, i))
                    tasks.append(task)
            
            # Execute all tasks concurrently
            start_time = time.perf_counter()
            results = await asyncio.gather(*tasks)
            total_time = time.perf_counter() - start_time
            
            # Analyze results
            successful_requests = sum(1 for r in results if r['success'])
            latencies = [r['latency'] for r in results if r['success']]
            
            avg_latency = statistics.mean(latencies)
            max_latency = max(latencies)
            throughput = successful_requests / total_time
            
            print(f"High concurrency results:")
            print(f"Successful requests: {successful_requests}/{len(tasks)}")
            print(f"Total time: {total_time:.2f}s")
            print(f"Throughput: {throughput:.2f} req/s")
            print(f"Average latency: {avg_latency:.2f}ms")
            print(f"Max latency: {max_latency:.2f}ms")
            
            # Performance requirements for high concurrency
            assert successful_requests == len(tasks), "Some requests failed"
            assert throughput >= 50, f"Throughput too low under concurrency: {throughput:.2f} req/s"
            assert avg_latency < 100, f"Average latency too high under concurrency: {avg_latency:.2f}ms"
            assert max_latency < 500, f"Max latency too high under concurrency: {max_latency:.2f}ms"