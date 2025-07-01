"""
Unit tests for MessageSerializationService
"""

import pytest
import json
import time
from unittest.mock import patch

from app.services.message_serialization_service import (
    MessageSerializationService,
    SerializationFormat,
    CompressionMethod,
    SerializationBenchmark
)
from app.services.orderbook_processor import AggregatedOrderBook, OrderBookLevel
from app.services.delta_update_service import OrderBookDelta, DeltaLevel


class TestMessageSerializationService:
    """Test cases for MessageSerializationService."""

    @pytest.fixture
    def serialization_service(self):
        """Create MessageSerializationService instance."""
        return MessageSerializationService()

    @pytest.fixture
    def sample_orderbook(self):
        """Create sample aggregated order book."""
        return AggregatedOrderBook(
            bids=[
                OrderBookLevel(price=100.0, amount=1.5),
                OrderBookLevel(price=99.0, amount=2.0)
            ],
            asks=[
                OrderBookLevel(price=101.0, amount=1.0),
                OrderBookLevel(price=102.0, amount=1.5)
            ],
            symbol="BTCUSDT",
            rounding=1.0,
            timestamp=int(time.time() * 1000),
            source="test",
            aggregated=True,
            depth=10
        )

    @pytest.fixture
    def sample_delta(self):
        """Create sample order book delta."""
        return OrderBookDelta(
            bids=[DeltaLevel(price=100.0, amount=2.0, operation="update")],
            asks=[DeltaLevel(price=101.0, amount=0.0, operation="remove")],
            symbol="BTCUSDT",
            rounding=1.0,
            timestamp=int(time.time() * 1000),
            sequence_id=1,
            full_snapshot=False
        )

    @pytest.fixture
    def sample_dict(self):
        """Create sample dictionary data."""
        return {
            "type": "test",
            "symbol": "BTCUSDT",
            "data": [1, 2, 3],
            "nested": {"key": "value"}
        }

    def test_initialization(self, serialization_service):
        """Test service initialization."""
        assert len(serialization_service.benchmark_history) == 0
        assert serialization_service.preferred_format == SerializationFormat.JSON
        assert serialization_service.preferred_compression == CompressionMethod.NONE

    def test_json_serialization_deserialization(self, serialization_service, sample_dict):
        """Test JSON serialization and deserialization."""
        serialized = serialization_service._serialize_json(sample_dict)
        deserialized = serialization_service._deserialize_json(serialized)
        
        assert isinstance(serialized, bytes)
        assert deserialized == sample_dict

    @patch('app.services.message_serialization_service.MSGPACK_AVAILABLE', True)
    @patch('app.services.message_serialization_service.msgpack')
    def test_msgpack_serialization_deserialization(self, mock_msgpack, serialization_service, sample_dict):
        """Test MessagePack serialization and deserialization."""
        mock_msgpack.packb.return_value = b'mock_packed_data'
        mock_msgpack.unpackb.return_value = sample_dict
        
        serialized = serialization_service._serialize_msgpack(sample_dict)
        deserialized = serialization_service._deserialize_msgpack(serialized)
        
        assert isinstance(serialized, bytes)
        assert deserialized == sample_dict
        mock_msgpack.packb.assert_called_once_with(sample_dict, use_bin_type=True)
        mock_msgpack.unpackb.assert_called_once_with(serialized, raw=False)

    def test_msgpack_unavailable_error(self, serialization_service, sample_dict):
        """Test error when MessagePack is unavailable."""
        with patch('app.services.message_serialization_service.MSGPACK_AVAILABLE', False):
            with pytest.raises(RuntimeError, match="MessagePack not available"):
                serialization_service._serialize_msgpack(sample_dict)
            
            with pytest.raises(RuntimeError, match="MessagePack not available"):
                serialization_service._deserialize_msgpack(b'data')

    def test_gzip_compression_decompression(self, serialization_service):
        """Test GZIP compression and decompression."""
        test_data = b"This is test data for compression testing."
        
        compressed = serialization_service._compress_gzip(test_data)
        decompressed = serialization_service._decompress_gzip(compressed)
        
        assert len(compressed) < len(test_data)  # Should be smaller
        assert decompressed == test_data

    def test_zlib_compression_decompression(self, serialization_service):
        """Test ZLIB compression and decompression."""
        test_data = b"This is test data for compression testing."
        
        compressed = serialization_service._compress_zlib(test_data)
        decompressed = serialization_service._decompress_zlib(compressed)
        
        assert len(compressed) < len(test_data)  # Should be smaller
        assert decompressed == test_data

    def test_orderbook_to_dict_conversion(self, serialization_service, sample_orderbook):
        """Test conversion of AggregatedOrderBook to dictionary."""
        result = serialization_service._orderbook_to_dict(sample_orderbook)
        
        assert result["type"] == "orderbook_update"
        assert result["symbol"] == "BTCUSDT"
        assert result["rounding"] == 1.0
        assert result["aggregated"] is True
        assert len(result["bids"]) == 2
        assert len(result["asks"]) == 2
        
        # Check bid/ask structure
        assert result["bids"][0] == [100.0, 1.5]
        assert result["asks"][0] == [101.0, 1.0]

    def test_delta_to_dict_conversion(self, serialization_service, sample_delta):
        """Test conversion of OrderBookDelta to dictionary."""
        result = serialization_service._delta_to_dict(sample_delta)
        
        assert result["type"] == "orderbook_delta"
        assert result["symbol"] == "BTCUSDT"
        assert result["rounding"] == 1.0
        assert result["full_snapshot"] is False
        assert result["sequence_id"] == 1
        
        # Check delta level structure
        assert len(result["bids"]) == 1
        assert result["bids"][0]["price"] == 100.0
        assert result["bids"][0]["amount"] == 2.0
        assert result["bids"][0]["operation"] == "update"

    def test_serialize_orderbook_json_no_compression(self, serialization_service, sample_orderbook):
        """Test serializing orderbook with JSON and no compression."""
        serialized, headers = serialization_service.serialize(
            sample_orderbook,
            SerializationFormat.JSON,
            CompressionMethod.NONE
        )
        
        assert isinstance(serialized, bytes)
        assert headers["Content-Type"] == "application/json"
        assert headers["Content-Encoding"] == "identity"
        
        # Verify can deserialize
        deserialized = serialization_service.deserialize(
            serialized,
            SerializationFormat.JSON,
            CompressionMethod.NONE
        )
        assert deserialized["type"] == "orderbook_update"
        assert deserialized["symbol"] == "BTCUSDT"

    def test_serialize_orderbook_json_gzip(self, serialization_service, sample_orderbook):
        """Test serializing orderbook with JSON and GZIP compression."""
        serialized, headers = serialization_service.serialize(
            sample_orderbook,
            SerializationFormat.JSON,
            CompressionMethod.GZIP
        )
        
        assert isinstance(serialized, bytes)
        assert headers["Content-Type"] == "application/json"
        assert headers["Content-Encoding"] == "gzip"
        
        # Verify can deserialize
        deserialized = serialization_service.deserialize(
            serialized,
            SerializationFormat.JSON,
            CompressionMethod.GZIP
        )
        assert deserialized["type"] == "orderbook_update"

    def test_serialize_delta_object(self, serialization_service, sample_delta):
        """Test serializing delta object."""
        serialized, headers = serialization_service.serialize(sample_delta)
        
        deserialized = serialization_service.deserialize(
            serialized,
            SerializationFormat.JSON,
            CompressionMethod.NONE
        )
        
        assert deserialized["type"] == "orderbook_delta"
        assert deserialized["sequence_id"] == 1

    def test_serialize_dict_object(self, serialization_service, sample_dict):
        """Test serializing dictionary object."""
        serialized, headers = serialization_service.serialize(sample_dict)
        
        deserialized = serialization_service.deserialize(
            serialized,
            SerializationFormat.JSON,
            CompressionMethod.NONE
        )
        
        assert deserialized == sample_dict

    def test_serialize_unsupported_format(self, serialization_service, sample_dict):
        """Test error with unsupported format."""
        with pytest.raises(ValueError, match="Unsupported format"):
            serialization_service.serialize(sample_dict, "unsupported_format")

    def test_serialize_unsupported_compression(self, serialization_service, sample_dict):
        """Test error with unsupported compression."""
        with pytest.raises(ValueError, match="Unsupported compression"):
            serialization_service.serialize(sample_dict, SerializationFormat.JSON, "unsupported_compression")

    def test_deserialize_unsupported_format(self, serialization_service):
        """Test error when deserializing unsupported format."""
        with pytest.raises(ValueError, match="Unsupported format"):
            serialization_service.deserialize(b'data', "unsupported_format")

    def test_deserialize_unsupported_compression(self, serialization_service):
        """Test error when deserializing unsupported compression."""
        with pytest.raises(ValueError, match="Unsupported compression"):
            serialization_service.deserialize(b'data', SerializationFormat.JSON, "unsupported_compression")

    def test_benchmark_serialization_json_only(self, serialization_service, sample_orderbook):
        """Test benchmarking with JSON only."""
        with patch('app.services.message_serialization_service.MSGPACK_AVAILABLE', False):
            results = serialization_service.benchmark_serialization(sample_orderbook, iterations=10)
        
        # Should have 3 results (JSON + 3 compression methods)
        assert len(results) == 3
        
        for result in results:
            assert result.format == SerializationFormat.JSON
            assert result.serialization_time > 0
            assert result.deserialization_time > 0
            assert result.size_bytes > 0

    def test_benchmark_serialization_with_msgpack(self, serialization_service, sample_orderbook):
        """Test benchmarking with MessagePack available."""
        with patch('app.services.message_serialization_service.MSGPACK_AVAILABLE', True):
            with patch('app.services.message_serialization_service.msgpack') as mock_msgpack:
                mock_msgpack.packb.return_value = b'mock_data'
                mock_msgpack.unpackb.return_value = {"test": "data"}
                
                results = serialization_service.benchmark_serialization(sample_orderbook, iterations=10)
        
        # Should have 6 results (2 formats × 3 compression methods)
        assert len(results) == 6
        
        formats = {result.format for result in results}
        assert SerializationFormat.JSON in formats
        assert SerializationFormat.MSGPACK in formats

    def test_auto_select_format_no_benchmarks(self, serialization_service):
        """Test auto format selection with no benchmarks."""
        format, compression = serialization_service.auto_select_format()
        
        assert format == SerializationFormat.JSON
        assert compression == CompressionMethod.NONE

    def test_auto_select_format_with_benchmarks(self, serialization_service):
        """Test auto format selection with benchmark results."""
        # Create mock benchmark results
        fast_result = SerializationBenchmark(
            format=SerializationFormat.JSON,
            compression=CompressionMethod.GZIP,
            serialization_time=0.001,
            deserialization_time=0.001,
            size_bytes=1000,
            compressed_size_bytes=500,
            compression_ratio=2.0
        )
        
        slow_result = SerializationBenchmark(
            format=SerializationFormat.JSON,
            compression=CompressionMethod.NONE,
            serialization_time=0.005,
            deserialization_time=0.005,
            size_bytes=2000,
            compressed_size_bytes=None,
            compression_ratio=None
        )
        
        format, compression = serialization_service.auto_select_format([fast_result, slow_result])
        
        # Should select the faster, more compressed option
        assert format == SerializationFormat.JSON
        assert compression == CompressionMethod.GZIP

    def test_configure_preferred_format(self, serialization_service):
        """Test configuring preferred format and compression."""
        serialization_service.configure_preferred_format(
            SerializationFormat.JSON,
            CompressionMethod.GZIP
        )
        
        assert serialization_service.preferred_format == SerializationFormat.JSON
        assert serialization_service.preferred_compression == CompressionMethod.GZIP

    def test_get_benchmark_summary_no_benchmarks(self, serialization_service):
        """Test getting benchmark summary with no benchmarks."""
        summary = serialization_service.get_benchmark_summary()
        
        assert "message" in summary
        assert "No benchmarks run yet" in summary["message"]

    def test_get_benchmark_summary_with_benchmarks(self, serialization_service):
        """Test getting benchmark summary with benchmarks."""
        # Add mock benchmark results
        benchmark = SerializationBenchmark(
            format=SerializationFormat.JSON,
            compression=CompressionMethod.NONE,
            serialization_time=0.001,
            deserialization_time=0.002,
            size_bytes=1000
        )
        
        serialization_service.benchmark_history.append(benchmark)
        summary = serialization_service.get_benchmark_summary()
        
        assert "current_preferred" in summary
        assert "msgpack_available" in summary
        assert "benchmarks" in summary
        
        key = "json+none"
        assert key in summary["benchmarks"]
        assert summary["benchmarks"][key]["avg_serialization_time_ms"] == 1.0
        assert summary["benchmarks"][key]["avg_deserialization_time_ms"] == 2.0
        assert summary["benchmarks"][key]["avg_size_bytes"] == 1000

    def test_serialize_with_defaults(self, serialization_service, sample_orderbook):
        """Test serialization using default format and compression."""
        serialized, headers = serialization_service.serialize(sample_orderbook)
        
        assert headers["Content-Type"] == "application/json"
        assert headers["Content-Encoding"] == "identity"

    def test_compression_effectiveness(self, serialization_service):
        """Test that compression actually reduces size for large data."""
        # Create large data structure
        large_data = {
            "type": "test",
            "data": ["repeated_string"] * 1000,
            "numbers": list(range(1000))
        }
        
        uncompressed, _ = serialization_service.serialize(
            large_data,
            SerializationFormat.JSON,
            CompressionMethod.NONE
        )
        
        compressed, _ = serialization_service.serialize(
            large_data,
            SerializationFormat.JSON,
            CompressionMethod.GZIP
        )
        
        # Compressed should be significantly smaller
        assert len(compressed) < len(uncompressed) * 0.5