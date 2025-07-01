"""
Load tests for order book processing system
"""

import asyncio
import pytest
import time
import threading
import concurrent.futures
from unittest.mock import Mock
import gc
import psutil
import os

from app.services.orderbook_processor import OrderBookProcessor
from app.services.delta_update_service import DeltaUpdateService
from app.services.batch_update_service import BatchUpdateService, BatchConfig
from app.services.message_serialization_service import MessageSerializationService


class TestOrderBookLoadTests:
    """Load tests for order book processing components."""

    @pytest.fixture
    def sample_large_orderbook_data(self):
        """Create large order book data for load testing."""
        return {
            'bids': [[100.0 - i*0.01, 1.0 + (i % 10)*0.1] for i in range(500)],
            'asks': [[101.0 + i*0.01, 1.0 + (i % 10)*0.1] for i in range(500)],
            'symbol': 'BTCUSDT',
            'timestamp': int(time.time() * 1000)
        }

    def test_processor_high_volume_aggregation(self, sample_large_orderbook_data):
        """Test processor performance with high volume order book data."""
        processor = OrderBookProcessor()
        
        # Test multiple aggregations with different parameters
        start_time = time.time()
        
        for i in range(100):
            aggregated = processor.aggregate_order_book(
                sample_large_orderbook_data,
                rounding=0.01,
                depth=50
            )
            assert len(aggregated.bids) <= 50
            assert len(aggregated.asks) <= 50
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Should process 100 large order books in under 1 second
        assert total_time < 1.0
        print(f"Processed 100 large order books in {total_time:.3f} seconds")

    def test_processor_concurrent_aggregation(self, sample_large_orderbook_data):
        """Test processor performance under concurrent load."""
        processor = OrderBookProcessor()
        num_threads = 10
        iterations_per_thread = 50
        
        def worker():
            for i in range(iterations_per_thread):
                aggregated = processor.aggregate_order_book(
                    sample_large_orderbook_data,
                    rounding=0.01 * (i % 5 + 1),  # Vary rounding
                    depth=25
                )
                assert aggregated is not None
        
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker) for _ in range(num_threads)]
            concurrent.futures.wait(futures)
        
        end_time = time.time()
        total_time = end_time - start_time
        total_operations = num_threads * iterations_per_thread
        
        print(f"Processed {total_operations} aggregations concurrently in {total_time:.3f} seconds")
        print(f"Average: {total_operations/total_time:.1f} operations/second")
        
        # Should handle concurrent load efficiently
        assert total_time < 5.0

    def test_delta_service_many_connections(self, sample_large_orderbook_data):
        """Test delta service with many concurrent connections."""
        delta_service = DeltaUpdateService()
        processor = OrderBookProcessor()
        
        num_connections = 100
        num_updates = 50
        
        # Register many connections
        connection_ids = []
        for i in range(num_connections):
            conn_id = delta_service.register_connection(f"ws{i}", "BTCUSDT", 1.0)
            connection_ids.append(conn_id)
        
        start_time = time.time()
        
        # Send updates to all connections
        for update_num in range(num_updates):
            # Modify data slightly for each update
            modified_data = sample_large_orderbook_data.copy()
            modified_data['bids'][0][1] = 1.0 + update_num * 0.01
            
            aggregated = processor.aggregate_order_book(modified_data, rounding=1.0, depth=50)
            
            for conn_id in connection_ids:
                delta = delta_service.compute_delta(conn_id, aggregated)
                # First update will be full snapshot, subsequent will be deltas
                assert delta is not None
        
        end_time = time.time()
        total_time = end_time - start_time
        total_operations = num_connections * num_updates
        
        print(f"Processed {total_operations} delta operations in {total_time:.3f} seconds")
        print(f"Average: {total_operations/total_time:.1f} operations/second")
        
        # Verify service stats
        stats = delta_service.get_service_stats()
        assert stats['total_connections'] == num_connections
        
        # Should handle many connections efficiently
        assert total_time < 10.0

    def test_batch_service_high_throughput(self, sample_large_orderbook_data):
        """Test batch service under high throughput conditions."""
        config = BatchConfig(
            max_batch_size=10,
            max_batch_delay_ms=10.0,
            max_queue_size=200
        )
        batch_service = BatchUpdateService(config)
        
        num_connections = 50
        updates_per_connection = 100
        
        # Register connections
        for i in range(num_connections):
            batch_service.register_connection(f"conn{i}")
        
        # Mock callback to capture sent batches
        sent_batches = []
        def capture_batches(conn_id, updates):
            sent_batches.append((conn_id, len(updates)))
        
        batch_service.set_send_callback(capture_batches)
        
        start_time = time.time()
        
        # Send many updates
        for i in range(updates_per_connection):
            for j in range(num_connections):
                batch_service.add_update(f"conn{j}", sample_large_orderbook_data)
        
        # Force flush all connections
        batch_service.force_flush()
        
        end_time = time.time()
        total_time = end_time - start_time
        total_updates = num_connections * updates_per_connection
        
        print(f"Processed {total_updates} batch updates in {total_time:.3f} seconds")
        print(f"Sent {len(sent_batches)} batches")
        
        # Verify batching efficiency
        stats = batch_service.get_performance_stats()
        assert stats['total_updates_received'] == total_updates
        assert stats['batching_efficiency'] > 0.8  # Should batch efficiently
        
        # Should handle high throughput
        assert total_time < 3.0

    def test_serialization_service_performance(self, sample_large_orderbook_data):
        """Test serialization service performance with large data."""
        serialization_service = MessageSerializationService()
        processor = OrderBookProcessor()
        
        # Create large aggregated order book
        aggregated = processor.aggregate_order_book(
            sample_large_orderbook_data,
            rounding=0.01,
            depth=200
        )
        
        num_serializations = 1000
        
        start_time = time.time()
        
        for i in range(num_serializations):
            serialized, headers = serialization_service.serialize(aggregated)
            assert len(serialized) > 0
        
        end_time = time.time()
        total_time = end_time - start_time
        
        print(f"Performed {num_serializations} serializations in {total_time:.3f} seconds")
        print(f"Average: {num_serializations/total_time:.1f} serializations/second")
        
        # Should serialize efficiently
        assert total_time < 2.0

    def test_memory_usage_under_load(self, sample_large_orderbook_data):
        """Test memory usage patterns under sustained load."""
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Create services
        processor = OrderBookProcessor()
        delta_service = DeltaUpdateService()
        batch_service = BatchUpdateService()
        
        num_connections = 50
        num_iterations = 100
        
        # Register connections
        connection_ids = []
        for i in range(num_connections):
            conn_id = delta_service.register_connection(f"ws{i}", "BTCUSDT", 1.0)
            connection_ids.append(conn_id)
            batch_service.register_connection(f"ws{i}")
        
        memory_samples = []
        
        for iteration in range(num_iterations):
            # Modify data
            modified_data = sample_large_orderbook_data.copy()
            modified_data['bids'][0][1] = 1.0 + iteration * 0.01
            
            # Process through pipeline
            aggregated = processor.aggregate_order_book(modified_data, rounding=1.0, depth=50)
            
            for conn_id in connection_ids:
                delta = delta_service.compute_delta(conn_id, aggregated)
                if delta:
                    batch_service.add_update(conn_id.split(':')[0], delta)
            
            # Sample memory every 10 iterations
            if iteration % 10 == 0:
                current_memory = process.memory_info().rss
                memory_samples.append(current_memory)
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        print(f"Initial memory: {initial_memory / 1024 / 1024:.1f} MB")
        print(f"Final memory: {final_memory / 1024 / 1024:.1f} MB")
        print(f"Memory increase: {memory_increase / 1024 / 1024:.1f} MB")
        
        # Memory increase should be reasonable (less than 100MB for this load)
        assert memory_increase < 100 * 1024 * 1024

    def test_cache_performance_under_load(self):
        """Test cache performance with many different rounding values."""
        processor = OrderBookProcessor()
        
        # Enable caching
        processor.cache.clear()
        
        base_data = {
            'bids': [[100.0 - i*0.01, 1.0] for i in range(100)],
            'asks': [[101.0 + i*0.01, 1.0] for i in range(100)],
            'symbol': 'BTCUSDT',
            'timestamp': int(time.time() * 1000)
        }
        
        rounding_values = [0.01, 0.1, 1.0, 10.0, 0.05, 0.5, 5.0]
        num_iterations = 200
        
        start_time = time.time()
        
        for i in range(num_iterations):
            rounding = rounding_values[i % len(rounding_values)]
            aggregated = processor.aggregate_order_book(base_data, rounding=rounding, depth=50)
            assert aggregated is not None
        
        end_time = time.time()
        total_time = end_time - start_time
        
        cache_stats = processor.get_cache_stats()
        hit_rate = cache_stats['hit_rate']
        
        print(f"Processed {num_iterations} cached aggregations in {total_time:.3f} seconds")
        print(f"Cache hit rate: {hit_rate:.2%}")
        
        # Should achieve good cache hit rate and performance
        assert hit_rate > 0.5  # At least 50% hit rate with repeated rounding values
        assert total_time < 1.0


class TestStressTests:
    """Stress tests for system limits and error handling."""

    def test_maximum_connections_limit(self):
        """Test behavior at maximum connection limits."""
        delta_service = DeltaUpdateService()
        
        # Try to create many connections
        max_connections = 1000
        connection_ids = []
        
        start_time = time.time()
        
        for i in range(max_connections):
            try:
                conn_id = delta_service.register_connection(f"ws{i}", "BTCUSDT", 1.0)
                connection_ids.append(conn_id)
            except Exception as e:
                print(f"Failed to create connection {i}: {e}")
                break
        
        end_time = time.time()
        
        print(f"Created {len(connection_ids)} connections in {end_time - start_time:.3f} seconds")
        
        # Should handle reasonable number of connections
        assert len(connection_ids) >= 500

    def test_extreme_order_book_sizes(self):
        """Test with extremely large order books."""
        processor = OrderBookProcessor()
        
        # Create extremely large order book
        huge_data = {
            'bids': [[100.0 - i*0.001, 1.0] for i in range(5000)],
            'asks': [[101.0 + i*0.001, 1.0] for i in range(5000)],
            'symbol': 'BTCUSDT',
            'timestamp': int(time.time() * 1000)
        }
        
        start_time = time.time()
        
        try:
            aggregated = processor.aggregate_order_book(huge_data, rounding=0.01, depth=100)
            assert aggregated is not None
            assert len(aggregated.bids) <= 100
            assert len(aggregated.asks) <= 100
        except Exception as e:
            pytest.fail(f"Failed to process huge order book: {e}")
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        print(f"Processed huge order book (10000 levels) in {processing_time:.3f} seconds")
        
        # Should complete within reasonable time
        assert processing_time < 5.0

    def test_memory_pressure_handling(self, sample_large_orderbook_data):
        """Test behavior under memory pressure."""
        # This test creates many objects to simulate memory pressure
        objects = []
        
        try:
            processor = OrderBookProcessor()
            
            # Create memory pressure
            for i in range(1000):
                # Create large objects
                large_object = [sample_large_orderbook_data.copy() for _ in range(100)]
                objects.append(large_object)
                
                # Still try to process order books
                if i % 100 == 0:
                    aggregated = processor.aggregate_order_book(
                        sample_large_orderbook_data,
                        rounding=1.0,
                        depth=50
                    )
                    assert aggregated is not None
        
        except MemoryError:
            print("Hit memory limit as expected")
        finally:
            # Clean up
            objects.clear()
            gc.collect()

    def test_rapid_connection_churn(self):
        """Test rapid connection creation and destruction."""
        delta_service = DeltaUpdateService()
        batch_service = BatchUpdateService()
        
        num_cycles = 500
        connections_per_cycle = 10
        
        start_time = time.time()
        
        for cycle in range(num_cycles):
            # Create connections
            conn_ids = []
            for i in range(connections_per_cycle):
                conn_id = delta_service.register_connection(f"ws{cycle}_{i}", "BTCUSDT", 1.0)
                conn_ids.append(conn_id)
                batch_service.register_connection(f"ws{cycle}_{i}")
            
            # Immediately destroy them
            for conn_id in conn_ids:
                delta_service.unregister_connection(conn_id)
                batch_service.unregister_connection(f"ws{cycle}_{i}")
        
        end_time = time.time()
        total_time = end_time - start_time
        total_operations = num_cycles * connections_per_cycle * 2  # Create + destroy
        
        print(f"Performed {total_operations} connection operations in {total_time:.3f} seconds")
        
        # Should handle rapid churn
        assert total_time < 10.0
        
        # Services should be clean
        assert delta_service.get_service_stats()['total_connections'] == 0

    def test_error_recovery(self, sample_large_orderbook_data):
        """Test system recovery from various error conditions."""
        processor = OrderBookProcessor()
        delta_service = DeltaUpdateService()
        
        # Test with malformed data
        malformed_data = {
            'bids': "not_a_list",
            'asks': None,
            'symbol': 'BTCUSDT'
        }
        
        # Should handle errors gracefully
        try:
            processor.aggregate_order_book(malformed_data, rounding=1.0, depth=10)
            pytest.fail("Should have raised an exception")
        except Exception:
            pass  # Expected
        
        # Should still work with good data after error
        aggregated = processor.aggregate_order_book(sample_large_orderbook_data, rounding=1.0, depth=10)
        assert aggregated is not None