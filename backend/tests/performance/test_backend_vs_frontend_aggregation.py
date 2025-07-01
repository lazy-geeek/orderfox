"""
Performance validation tests comparing backend vs frontend aggregation
"""

import pytest
import time
import asyncio
import statistics
from typing import List, Dict, Any
from unittest.mock import Mock

from app.services.orderbook_processor import OrderBookProcessor
from app.services.delta_update_service import DeltaUpdateService
from app.services.batch_update_service import BatchUpdateService, BatchConfig
from app.services.message_serialization_service import MessageSerializationService, CompressionMethod


class PerformanceBenchmark:
    """Helper class for performance benchmarking."""
    
    def __init__(self, name: str):
        self.name = name
        self.measurements: List[float] = []
        self.start_time = None
    
    def start(self):
        """Start timing."""
        self.start_time = time.perf_counter()
    
    def stop(self):
        """Stop timing and record measurement."""
        if self.start_time is not None:
            duration = time.perf_counter() - self.start_time
            self.measurements.append(duration)
            self.start_time = None
    
    def get_stats(self) -> Dict[str, float]:
        """Get statistical summary of measurements."""
        if not self.measurements:
            return {"count": 0}
        
        return {
            "count": len(self.measurements),
            "mean": statistics.mean(self.measurements),
            "median": statistics.median(self.measurements),
            "min": min(self.measurements),
            "max": max(self.measurements),
            "std_dev": statistics.stdev(self.measurements) if len(self.measurements) > 1 else 0,
            "total": sum(self.measurements)
        }


class TestBackendVsFrontendAggregation:
    """Performance comparison tests between backend and frontend aggregation."""

    @pytest.fixture
    def large_orderbook_data(self):
        """Create large order book data for performance testing."""
        return {
            'bids': [[100.0 - i*0.001, 1.0 + (i % 100)*0.01] for i in range(1000)],
            'asks': [[101.0 + i*0.001, 1.0 + (i % 100)*0.01] for i in range(1000)],
            'symbol': 'BTCUSDT',
            'timestamp': int(time.time() * 1000)
        }

    @pytest.fixture
    def processor(self):
        """Create OrderBookProcessor instance."""
        return OrderBookProcessor()

    def simulate_frontend_aggregation(self, orderbook_data: Dict, rounding: float, depth: int) -> Dict:
        """
        Simulate frontend aggregation logic.
        This represents the work that would be done in the browser.
        """
        start_time = time.perf_counter()
        
        # Simulate the aggregation work (simplified version)
        bids = orderbook_data['bids'][:depth]
        asks = orderbook_data['asks'][:depth]
        
        # Simulate rounding logic
        aggregated_bids = {}
        for price, amount in bids:
            rounded_price = round(price / rounding) * rounding
            aggregated_bids[rounded_price] = aggregated_bids.get(rounded_price, 0) + amount
        
        aggregated_asks = {}
        for price, amount in asks:
            rounded_price = round(price / rounding) * rounding
            aggregated_asks[rounded_price] = aggregated_asks.get(rounded_price, 0) + amount
        
        # Convert back to list format
        result_bids = sorted(aggregated_bids.items(), reverse=True)[:depth]
        result_asks = sorted(aggregated_asks.items())[:depth]
        
        processing_time = time.perf_counter() - start_time
        
        return {
            'bids': result_bids,
            'asks': result_asks,
            'symbol': orderbook_data['symbol'],
            'processing_time': processing_time,
            'aggregated': True
        }

    def test_aggregation_performance_comparison(self, processor, large_orderbook_data):
        """Compare performance of backend vs frontend aggregation."""
        test_cases = [
            {'rounding': 0.01, 'depth': 50},
            {'rounding': 0.1, 'depth': 50},
            {'rounding': 1.0, 'depth': 50},
            {'rounding': 0.01, 'depth': 100},
            {'rounding': 0.1, 'depth': 100},
        ]
        
        iterations = 100
        results = {}
        
        for case in test_cases:
            rounding = case['rounding']
            depth = case['depth']
            case_name = f"rounding_{rounding}_depth_{depth}"
            
            # Test backend aggregation
            backend_benchmark = PerformanceBenchmark(f"backend_{case_name}")
            for _ in range(iterations):
                backend_benchmark.start()
                aggregated = processor.aggregate_order_book(
                    large_orderbook_data,
                    rounding=rounding,
                    depth=depth
                )
                backend_benchmark.stop()
                assert aggregated is not None
            
            # Test frontend aggregation simulation
            frontend_benchmark = PerformanceBenchmark(f"frontend_{case_name}")
            for _ in range(iterations):
                frontend_benchmark.start()
                aggregated = self.simulate_frontend_aggregation(
                    large_orderbook_data,
                    rounding=rounding,
                    depth=depth
                )
                frontend_benchmark.stop()
                assert aggregated is not None
            
            # Compare results
            backend_stats = backend_benchmark.get_stats()
            frontend_stats = frontend_benchmark.get_stats()
            
            speedup = frontend_stats['mean'] / backend_stats['mean']
            
            results[case_name] = {
                'backend': backend_stats,
                'frontend': frontend_stats,
                'speedup': speedup,
                'backend_faster': speedup > 1.0
            }
            
            print(f"\n{case_name}:")
            print(f"  Backend mean: {backend_stats['mean']*1000:.3f}ms")
            print(f"  Frontend mean: {frontend_stats['mean']*1000:.3f}ms")
            print(f"  Speedup: {speedup:.2f}x {'(backend faster)' if speedup > 1 else '(frontend faster)'}")
        
        # Overall analysis
        total_backend_time = sum(r['backend']['total'] for r in results.values())
        total_frontend_time = sum(r['frontend']['total'] for r in results.values())
        overall_speedup = total_frontend_time / total_backend_time
        
        print(f"\nOverall Results:")
        print(f"  Total backend time: {total_backend_time:.3f}s")
        print(f"  Total frontend time: {total_frontend_time:.3f}s")
        print(f"  Overall speedup: {overall_speedup:.2f}x")
        
        # Backend should be faster or at least competitive
        assert overall_speedup >= 0.8, "Backend aggregation is significantly slower than frontend"

    def test_bandwidth_usage_comparison(self, processor, large_orderbook_data):
        """Compare bandwidth usage between raw data and aggregated data."""
        serialization_service = MessageSerializationService()
        
        test_cases = [
            {'rounding': 0.01, 'depth': 50},
            {'rounding': 0.1, 'depth': 50},
            {'rounding': 1.0, 'depth': 50},
        ]
        
        results = {}
        
        for case in test_cases:
            rounding = case['rounding']
            depth = case['depth']
            case_name = f"rounding_{rounding}_depth_{depth}"
            
            # Serialize raw data (frontend aggregation scenario)
            raw_serialized, _ = serialization_service.serialize(large_orderbook_data)
            raw_size = len(raw_serialized)
            
            # Serialize aggregated data (backend aggregation scenario)
            aggregated = processor.aggregate_order_book(
                large_orderbook_data,
                rounding=rounding,
                depth=depth
            )
            aggregated_serialized, _ = serialization_service.serialize(aggregated)
            aggregated_size = len(aggregated_serialized)
            
            # Test with compression
            raw_compressed, _ = serialization_service.serialize(
                large_orderbook_data,
                compression=CompressionMethod.GZIP
            )
            raw_compressed_size = len(raw_compressed)
            
            aggregated_compressed, _ = serialization_service.serialize(
                aggregated,
                compression=CompressionMethod.GZIP
            )
            aggregated_compressed_size = len(aggregated_compressed)
            
            bandwidth_reduction = (raw_size - aggregated_size) / raw_size
            compressed_bandwidth_reduction = (raw_compressed_size - aggregated_compressed_size) / raw_compressed_size
            
            results[case_name] = {
                'raw_size': raw_size,
                'aggregated_size': aggregated_size,
                'raw_compressed_size': raw_compressed_size,
                'aggregated_compressed_size': aggregated_compressed_size,
                'bandwidth_reduction': bandwidth_reduction,
                'compressed_bandwidth_reduction': compressed_bandwidth_reduction
            }
            
            print(f"\n{case_name}:")
            print(f"  Raw size: {raw_size} bytes")
            print(f"  Aggregated size: {aggregated_size} bytes")
            print(f"  Bandwidth reduction: {bandwidth_reduction:.2%}")
            print(f"  Compressed raw: {raw_compressed_size} bytes")
            print(f"  Compressed aggregated: {aggregated_compressed_size} bytes")
            print(f"  Compressed bandwidth reduction: {compressed_bandwidth_reduction:.2%}")
        
        # Backend aggregation should significantly reduce bandwidth
        avg_bandwidth_reduction = statistics.mean(r['bandwidth_reduction'] for r in results.values())
        assert avg_bandwidth_reduction > 0.5, "Backend aggregation should reduce bandwidth by at least 50%"

    def test_memory_usage_comparison(self, processor, large_orderbook_data):
        """Compare memory usage patterns between backend and frontend processing."""
        import psutil
        import os
        import gc
        
        process = psutil.Process(os.getpid())
        
        # Test backend aggregation memory usage
        gc.collect()
        initial_memory = process.memory_info().rss
        
        aggregated_books = []
        for i in range(100):
            aggregated = processor.aggregate_order_book(
                large_orderbook_data,
                rounding=1.0,
                depth=50
            )
            aggregated_books.append(aggregated)
        
        backend_memory = process.memory_info().rss
        backend_memory_increase = backend_memory - initial_memory
        
        # Clean up
        aggregated_books.clear()
        gc.collect()
        
        # Test frontend simulation memory usage
        gc.collect()
        initial_memory = process.memory_info().rss
        
        frontend_results = []
        for i in range(100):
            result = self.simulate_frontend_aggregation(
                large_orderbook_data,
                rounding=1.0,
                depth=50
            )
            frontend_results.append(result)
        
        frontend_memory = process.memory_info().rss
        frontend_memory_increase = frontend_memory - initial_memory
        
        # Clean up
        frontend_results.clear()
        gc.collect()
        
        print(f"\nMemory Usage Comparison:")
        print(f"  Backend memory increase: {backend_memory_increase / 1024 / 1024:.2f} MB")
        print(f"  Frontend memory increase: {frontend_memory_increase / 1024 / 1024:.2f} MB")
        
        # Backend might use slightly more memory due to caching, but should be reasonable
        memory_ratio = backend_memory_increase / frontend_memory_increase if frontend_memory_increase > 0 else 1
        assert memory_ratio < 3.0, "Backend memory usage should not be excessively higher than frontend"

    def test_cache_effectiveness(self, processor, large_orderbook_data):
        """Test effectiveness of backend caching."""
        cache_benchmark = PerformanceBenchmark("cache_test")
        
        # Clear cache
        processor.cache.clear()
        
        # First run (cache miss)
        cache_benchmark.start()
        aggregated1 = processor.aggregate_order_book(
            large_orderbook_data,
            rounding=1.0,
            depth=50
        )
        cache_benchmark.stop()
        first_run_time = cache_benchmark.measurements[-1]
        
        # Second run (cache hit)
        cache_benchmark.start()
        aggregated2 = processor.aggregate_order_book(
            large_orderbook_data,
            rounding=1.0,
            depth=50
        )
        cache_benchmark.stop()
        second_run_time = cache_benchmark.measurements[-1]
        
        # Cache hit should be significantly faster
        speedup = first_run_time / second_run_time
        cache_stats = processor.get_cache_stats()
        
        print(f"\nCache Effectiveness:")
        print(f"  First run (miss): {first_run_time*1000:.3f}ms")
        print(f"  Second run (hit): {second_run_time*1000:.3f}ms")
        print(f"  Cache speedup: {speedup:.2f}x")
        print(f"  Cache hit rate: {cache_stats['hit_rate']:.2%}")
        
        assert speedup > 2.0, "Cache should provide at least 2x speedup"
        assert cache_stats['hit_rate'] > 0, "Should have cache hits"

    def test_delta_update_efficiency(self, large_orderbook_data):
        """Test efficiency of delta updates vs full snapshots."""
        processor = OrderBookProcessor()
        delta_service = DeltaUpdateService()
        serialization_service = MessageSerializationService()
        
        conn_id = delta_service.register_connection("test_ws", "BTCUSDT", 1.0)
        
        # Initial aggregation and delta (full snapshot)
        aggregated1 = processor.aggregate_order_book(large_orderbook_data, rounding=1.0, depth=50)
        delta1 = delta_service.compute_delta(conn_id, aggregated1)
        
        # Serialize full snapshot
        full_snapshot_size = len(serialization_service.serialize(delta1)[0])
        
        # Modify data slightly
        modified_data = large_orderbook_data.copy()
        modified_data['bids'][0][1] = modified_data['bids'][0][1] + 0.1  # Small change
        
        aggregated2 = processor.aggregate_order_book(modified_data, rounding=1.0, depth=50)
        delta2 = delta_service.compute_delta(conn_id, aggregated2)
        
        # Serialize delta update
        delta_update_size = len(serialization_service.serialize(delta2)[0])
        
        bandwidth_savings = (full_snapshot_size - delta_update_size) / full_snapshot_size
        
        print(f"\nDelta Update Efficiency:")
        print(f"  Full snapshot size: {full_snapshot_size} bytes")
        print(f"  Delta update size: {delta_update_size} bytes")
        print(f"  Bandwidth savings: {bandwidth_savings:.2%}")
        
        # Delta updates should be significantly smaller
        assert bandwidth_savings > 0.8, "Delta updates should save at least 80% bandwidth"

    def test_concurrent_processing_performance(self, processor, large_orderbook_data):
        """Test performance under concurrent processing load."""
        import concurrent.futures
        import threading
        
        def process_orderbook(thread_id: int, iterations: int):
            """Worker function for concurrent processing."""
            times = []
            for i in range(iterations):
                start_time = time.perf_counter()
                aggregated = processor.aggregate_order_book(
                    large_orderbook_data,
                    rounding=1.0 + (thread_id * 0.1),  # Different rounding per thread
                    depth=50
                )
                end_time = time.perf_counter()
                times.append(end_time - start_time)
                assert aggregated is not None
            return times
        
        num_threads = 5
        iterations_per_thread = 20
        
        # Sequential processing baseline
        sequential_times = process_orderbook(0, num_threads * iterations_per_thread)
        sequential_total_time = sum(sequential_times)
        
        # Concurrent processing
        start_time = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [
                executor.submit(process_orderbook, i, iterations_per_thread)
                for i in range(num_threads)
            ]
            concurrent_results = [future.result() for future in futures]
        concurrent_total_time = time.perf_counter() - start_time
        
        # Analyze results
        all_concurrent_times = [t for times in concurrent_results for t in times]
        
        print(f"\nConcurrent Processing Performance:")
        print(f"  Sequential total time: {sequential_total_time:.3f}s")
        print(f"  Concurrent total time: {concurrent_total_time:.3f}s")
        print(f"  Concurrency speedup: {sequential_total_time / concurrent_total_time:.2f}x")
        print(f"  Sequential avg per operation: {statistics.mean(sequential_times)*1000:.3f}ms")
        print(f"  Concurrent avg per operation: {statistics.mean(all_concurrent_times)*1000:.3f}ms")
        
        # Should show some benefit from concurrency
        assert concurrent_total_time < sequential_total_time * 0.8, "Concurrent processing should be faster"


class TestSystemScalability:
    """Tests for system scalability under various loads."""

    def test_connection_scaling(self):
        """Test system behavior as number of connections scales."""
        delta_service = DeltaUpdateService()
        batch_service = BatchUpdateService(BatchConfig(max_batch_size=10))
        
        connection_counts = [10, 50, 100, 200]
        results = {}
        
        for count in connection_counts:
            # Register connections
            start_time = time.perf_counter()
            conn_ids = []
            for i in range(count):
                conn_id = delta_service.register_connection(f"ws{i}", "BTCUSDT", 1.0)
                conn_ids.append(conn_id)
                batch_service.register_connection(f"ws{i}")
            registration_time = time.perf_counter() - start_time
            
            # Test cleanup
            start_time = time.perf_counter()
            for conn_id in conn_ids:
                delta_service.unregister_connection(conn_id)
                batch_service.unregister_connection(conn_id.split(':')[0])
            cleanup_time = time.perf_counter() - start_time
            
            results[count] = {
                'registration_time': registration_time,
                'cleanup_time': cleanup_time,
                'reg_time_per_conn': registration_time / count,
                'cleanup_time_per_conn': cleanup_time / count
            }
            
            print(f"\nConnections: {count}")
            print(f"  Registration time: {registration_time:.3f}s ({registration_time/count*1000:.3f}ms per conn)")
            print(f"  Cleanup time: {cleanup_time:.3f}s ({cleanup_time/count*1000:.3f}ms per conn)")
        
        # Performance should scale reasonably
        max_reg_time_per_conn = max(r['reg_time_per_conn'] for r in results.values())
        min_reg_time_per_conn = min(r['reg_time_per_conn'] for r in results.values())
        
        # Time per connection shouldn't increase dramatically
        assert max_reg_time_per_conn / min_reg_time_per_conn < 3.0, "Connection registration should scale reasonably"

    def test_message_throughput_scaling(self):
        """Test message throughput as volume scales."""
        serialization_service = MessageSerializationService()
        
        # Test data of various sizes
        small_data = {"type": "test", "data": list(range(10))}
        medium_data = {"type": "test", "data": list(range(100))}
        large_data = {"type": "test", "data": list(range(1000))}
        
        message_counts = [100, 500, 1000, 2000]
        data_sizes = {"small": small_data, "medium": medium_data, "large": large_data}
        
        for size_name, test_data in data_sizes.items():
            print(f"\n{size_name.title()} message throughput:")
            
            for count in message_counts:
                start_time = time.perf_counter()
                
                for _ in range(count):
                    serialized, headers = serialization_service.serialize(test_data)
                    assert len(serialized) > 0
                
                end_time = time.perf_counter()
                total_time = end_time - start_time
                throughput = count / total_time
                
                print(f"  {count} messages: {throughput:.1f} msg/s ({total_time:.3f}s total)")
            
        # Should maintain reasonable throughput
        # This is mainly for monitoring - actual assertions would depend on requirements