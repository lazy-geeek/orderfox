"""
Message Serialization Service

This module handles optimized serialization of order book data for WebSocket transmission,
including benchmarking and compression capabilities.
"""

import json
import time
import gzip
import zlib
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

# Try to import msgpack, fall back to JSON if not available
try:
    import msgpack
    MSGPACK_AVAILABLE = True
except ImportError:
    MSGPACK_AVAILABLE = False
    msgpack = None

from .orderbook_processor import AggregatedOrderBook
from .delta_update_service import OrderBookDelta

logger = logging.getLogger(__name__)


class SerializationFormat(Enum):
    """Available serialization formats."""
    JSON = "json"
    MSGPACK = "msgpack"


class CompressionMethod(Enum):
    """Available compression methods."""
    NONE = "none"
    GZIP = "gzip"
    ZLIB = "zlib"


@dataclass
class SerializationBenchmark:
    """Results of a serialization benchmark."""
    format: SerializationFormat
    compression: CompressionMethod
    serialization_time: float
    deserialization_time: float
    size_bytes: int
    compressed_size_bytes: Optional[int] = None
    compression_ratio: Optional[float] = None


class MessageSerializationService:
    """
    Service for optimized serialization of order book messages.
    
    Provides benchmarking, compression, and format selection capabilities.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.benchmark_history: List[SerializationBenchmark] = []
        self.preferred_format = SerializationFormat.JSON
        self.preferred_compression = CompressionMethod.NONE
        
        # Check MessagePack availability
        if not MSGPACK_AVAILABLE:
            self.logger.warning("MessagePack not available, falling back to JSON only")
    
    def _serialize_json(self, data: Dict[str, Any]) -> bytes:
        """Serialize data to JSON bytes."""
        return json.dumps(data, separators=(',', ':')).encode('utf-8')
    
    def _deserialize_json(self, data: bytes) -> Dict[str, Any]:
        """Deserialize JSON bytes to data."""
        return json.loads(data.decode('utf-8'))
    
    def _serialize_msgpack(self, data: Dict[str, Any]) -> bytes:
        """Serialize data to MessagePack bytes."""
        if not MSGPACK_AVAILABLE:
            raise RuntimeError("MessagePack not available")
        return msgpack.packb(data, use_bin_type=True)
    
    def _deserialize_msgpack(self, data: bytes) -> Dict[str, Any]:
        """Deserialize MessagePack bytes to data."""
        if not MSGPACK_AVAILABLE:
            raise RuntimeError("MessagePack not available")
        return msgpack.unpackb(data, raw=False)
    
    def _compress_gzip(self, data: bytes, level: int = 6) -> bytes:
        """Compress data using gzip."""
        return gzip.compress(data, compresslevel=level)
    
    def _decompress_gzip(self, data: bytes) -> bytes:
        """Decompress gzip data."""
        return gzip.decompress(data)
    
    def _compress_zlib(self, data: bytes, level: int = 6) -> bytes:
        """Compress data using zlib."""
        return zlib.compress(data, level=level)
    
    def _decompress_zlib(self, data: bytes) -> bytes:
        """Decompress zlib data."""
        return zlib.decompress(data)
    
    def _orderbook_to_dict(self, orderbook: AggregatedOrderBook) -> Dict[str, Any]:
        """Convert AggregatedOrderBook to dictionary."""
        return {
            "type": "orderbook_update",
            "symbol": orderbook.symbol,
            "bids": [[level.price, level.amount] for level in orderbook.bids],
            "asks": [[level.price, level.amount] for level in orderbook.asks],
            "timestamp": orderbook.timestamp,
            "rounding": orderbook.rounding,
            "depth": orderbook.depth,
            "source": orderbook.source,
            "aggregated": orderbook.aggregated
        }
    
    def _delta_to_dict(self, delta: OrderBookDelta) -> Dict[str, Any]:
        """Convert OrderBookDelta to dictionary."""
        return {
            "type": "orderbook_delta" if not delta.full_snapshot else "orderbook_snapshot",
            "symbol": delta.symbol,
            "rounding": delta.rounding,
            "timestamp": delta.timestamp,
            "sequence_id": delta.sequence_id,
            "full_snapshot": delta.full_snapshot,
            "bids": [
                {
                    "price": level.price,
                    "amount": level.amount,
                    "operation": level.operation
                }
                for level in delta.bids
            ],
            "asks": [
                {
                    "price": level.price,
                    "amount": level.amount,
                    "operation": level.operation
                }
                for level in delta.asks
            ]
        }
    
    def serialize(
        self, 
        data: Any, 
        format: SerializationFormat = None, 
        compression: CompressionMethod = None
    ) -> Tuple[bytes, Dict[str, str]]:
        """
        Serialize data with specified format and compression.
        
        Args:
            data: Data to serialize (AggregatedOrderBook, OrderBookDelta, or dict)
            format: Serialization format (defaults to preferred)
            compression: Compression method (defaults to preferred)
            
        Returns:
            Tuple of (serialized_bytes, headers_dict)
        """
        if format is None:
            format = self.preferred_format
        if compression is None:
            compression = self.preferred_compression
        
        # Convert to dictionary if needed
        if hasattr(data, '__dict__'):
            if isinstance(data, AggregatedOrderBook):
                data_dict = self._orderbook_to_dict(data)
            elif isinstance(data, OrderBookDelta):
                data_dict = self._delta_to_dict(data)
            else:
                data_dict = data.__dict__
        else:
            data_dict = data
        
        # Serialize
        if format == SerializationFormat.JSON:
            serialized = self._serialize_json(data_dict)
        elif format == SerializationFormat.MSGPACK:
            serialized = self._serialize_msgpack(data_dict)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        # Compress
        if compression == CompressionMethod.GZIP:
            serialized = self._compress_gzip(serialized)
        elif compression == CompressionMethod.ZLIB:
            serialized = self._compress_zlib(serialized)
        elif compression != CompressionMethod.NONE:
            raise ValueError(f"Unsupported compression: {compression}")
        
        # Generate headers
        headers = {
            "Content-Type": f"application/{format.value}",
            "Content-Encoding": compression.value if compression != CompressionMethod.NONE else "identity"
        }
        
        return serialized, headers
    
    def deserialize(
        self, 
        data: bytes, 
        format: SerializationFormat, 
        compression: CompressionMethod = CompressionMethod.NONE
    ) -> Dict[str, Any]:
        """
        Deserialize data with specified format and compression.
        
        Args:
            data: Serialized data
            format: Serialization format
            compression: Compression method
            
        Returns:
            Deserialized data
        """
        # Decompress
        if compression == CompressionMethod.GZIP:
            data = self._decompress_gzip(data)
        elif compression == CompressionMethod.ZLIB:
            data = self._decompress_zlib(data)
        elif compression != CompressionMethod.NONE:
            raise ValueError(f"Unsupported compression: {compression}")
        
        # Deserialize
        if format == SerializationFormat.JSON:
            return self._deserialize_json(data)
        elif format == SerializationFormat.MSGPACK:
            return self._deserialize_msgpack(data)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def benchmark_serialization(
        self, 
        test_data: Any, 
        iterations: int = 1000
    ) -> List[SerializationBenchmark]:
        """
        Benchmark different serialization formats and compression methods.
        
        Args:
            test_data: Data to use for benchmarking
            iterations: Number of iterations to run
            
        Returns:
            List of benchmark results
        """
        results = []
        formats_to_test = [SerializationFormat.JSON]
        
        if MSGPACK_AVAILABLE:
            formats_to_test.append(SerializationFormat.MSGPACK)
        
        compressions_to_test = [
            CompressionMethod.NONE,
            CompressionMethod.GZIP,
            CompressionMethod.ZLIB
        ]
        
        for format in formats_to_test:
            for compression in compressions_to_test:
                try:
                    # Warm up
                    serialized, _ = self.serialize(test_data, format, compression)
                    self.deserialize(serialized, format, compression)
                    
                    # Benchmark serialization
                    start_time = time.perf_counter()
                    for _ in range(iterations):
                        serialized, _ = self.serialize(test_data, format, compression)
                    serialization_time = (time.perf_counter() - start_time) / iterations
                    
                    # Benchmark deserialization
                    start_time = time.perf_counter()
                    for _ in range(iterations):
                        self.deserialize(serialized, format, compression)
                    deserialization_time = (time.perf_counter() - start_time) / iterations
                    
                    # Calculate sizes
                    uncompressed_size = len(self.serialize(test_data, format, CompressionMethod.NONE)[0])
                    compressed_size = len(serialized) if compression != CompressionMethod.NONE else None
                    compression_ratio = (
                        uncompressed_size / compressed_size 
                        if compressed_size else None
                    )
                    
                    benchmark = SerializationBenchmark(
                        format=format,
                        compression=compression,
                        serialization_time=serialization_time,
                        deserialization_time=deserialization_time,
                        size_bytes=uncompressed_size,
                        compressed_size_bytes=compressed_size,
                        compression_ratio=compression_ratio
                    )
                    
                    results.append(benchmark)
                    self.logger.info(
                        f"Benchmark {format.value}+{compression.value}: "
                        f"ser={serialization_time*1000:.3f}ms, "
                        f"deser={deserialization_time*1000:.3f}ms, "
                        f"size={uncompressed_size}B"
                        + (f", compressed={compressed_size}B ({compression_ratio:.2f}x)" 
                           if compressed_size else "")
                    )
                    
                except Exception as e:
                    self.logger.error(f"Benchmark failed for {format.value}+{compression.value}: {e}")
        
        # Store results
        self.benchmark_history.extend(results)
        return results
    
    def auto_select_format(self, benchmark_results: List[SerializationBenchmark] = None) -> Tuple[SerializationFormat, CompressionMethod]:
        """
        Automatically select the best format and compression based on benchmarks.
        
        Args:
            benchmark_results: Results to analyze (uses latest if None)
            
        Returns:
            Tuple of (best_format, best_compression)
        """
        if benchmark_results is None:
            benchmark_results = self.benchmark_history[-len(SerializationFormat)*len(CompressionMethod):]
        
        if not benchmark_results:
            self.logger.warning("No benchmark results available, using defaults")
            return SerializationFormat.JSON, CompressionMethod.NONE
        
        # Score each result (lower is better)
        # Weight: 40% serialization time, 20% deserialization time, 40% size
        best_score = float('inf')
        best_format = SerializationFormat.JSON
        best_compression = CompressionMethod.NONE
        
        for result in benchmark_results:
            size_to_use = result.compressed_size_bytes or result.size_bytes
            total_time = result.serialization_time + result.deserialization_time
            
            # Normalize scores (smaller is better)
            time_score = total_time * 1000  # Convert to ms
            size_score = size_to_use / 1024   # Convert to KB
            
            # Weighted score
            score = (time_score * 0.6) + (size_score * 0.4)
            
            if score < best_score:
                best_score = score
                best_format = result.format
                best_compression = result.compression
        
        self.logger.info(
            f"Auto-selected format: {best_format.value} + {best_compression.value} "
            f"(score: {best_score:.3f})"
        )
        
        return best_format, best_compression
    
    def configure_preferred_format(self, format: SerializationFormat, compression: CompressionMethod):
        """
        Configure the preferred serialization format and compression.
        
        Args:
            format: Preferred serialization format
            compression: Preferred compression method
        """
        self.preferred_format = format
        self.preferred_compression = compression
        self.logger.info(f"Configured preferred format: {format.value} + {compression.value}")
    
    def get_benchmark_summary(self) -> Dict[str, Any]:
        """Get a summary of all benchmark results."""
        if not self.benchmark_history:
            return {"message": "No benchmarks run yet"}
        
        # Group by format+compression
        groups = {}
        for result in self.benchmark_history:
            key = f"{result.format.value}+{result.compression.value}"
            if key not in groups:
                groups[key] = []
            groups[key].append(result)
        
        # Calculate averages
        summary = {}
        for key, results in groups.items():
            avg_ser_time = sum(r.serialization_time for r in results) / len(results)
            avg_deser_time = sum(r.deserialization_time for r in results) / len(results)
            avg_size = sum(r.size_bytes for r in results) / len(results)
            avg_compressed_size = (
                sum(r.compressed_size_bytes for r in results if r.compressed_size_bytes) / 
                len([r for r in results if r.compressed_size_bytes])
                if any(r.compressed_size_bytes for r in results) else None
            )
            
            summary[key] = {
                "avg_serialization_time_ms": avg_ser_time * 1000,
                "avg_deserialization_time_ms": avg_deser_time * 1000,
                "avg_size_bytes": int(avg_size),
                "avg_compressed_size_bytes": int(avg_compressed_size) if avg_compressed_size else None,
                "sample_count": len(results)
            }
        
        return {
            "current_preferred": f"{self.preferred_format.value}+{self.preferred_compression.value}",
            "msgpack_available": MSGPACK_AVAILABLE,
            "benchmarks": summary
        }