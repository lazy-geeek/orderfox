"""
Monitoring Service

This module provides comprehensive monitoring and metrics collection for the order book system.
"""

import time
import logging
import threading
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field, asdict
from collections import defaultdict, deque
from enum import Enum
import json
import statistics

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics that can be collected."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class MetricValue:
    """Represents a metric value with metadata."""
    value: float
    timestamp: float
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class HistogramData:
    """Histogram metric data."""
    buckets: Dict[float, int] = field(default_factory=dict)
    sum: float = 0.0
    count: int = 0
    
    def add_value(self, value: float):
        """Add a value to the histogram."""
        self.sum += value
        self.count += 1
        
        # Add to appropriate buckets (simplified bucketing)
        bucket_boundaries = [0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0, float('inf')]
        for boundary in bucket_boundaries:
            if value <= boundary:
                self.buckets[boundary] = self.buckets.get(boundary, 0) + 1


@dataclass
class SystemMetrics:
    """System-wide metrics snapshot."""
    timestamp: float
    active_connections: int
    total_orderbooks: int
    cache_hit_rate: float
    memory_usage_mb: float
    cpu_usage_percent: float
    processing_latency_ms: float
    bandwidth_bytes_per_second: float
    error_rate: float


class MetricsCollector:
    """Collects and stores metrics data."""
    
    def __init__(self, max_history: int = 1000):
        """
        Initialize metrics collector.
        
        Args:
            max_history: Maximum number of metric values to keep in history
        """
        self.max_history = max_history
        self.lock = threading.RLock()
        
        # Metric storage
        self.counters: Dict[str, float] = defaultdict(float)
        self.gauges: Dict[str, MetricValue] = {}
        self.histograms: Dict[str, HistogramData] = defaultdict(HistogramData)
        self.timers: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_history))
        
        # Metric metadata
        self.metric_labels: Dict[str, Dict[str, str]] = {}
        self.metric_help: Dict[str, str] = {}
        
        logger.info("MetricsCollector initialized")
    
    def increment_counter(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None):
        """Increment a counter metric."""
        with self.lock:
            full_name = self._build_metric_name(name, labels)
            self.counters[full_name] += value
    
    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Set a gauge metric value."""
        with self.lock:
            full_name = self._build_metric_name(name, labels)
            self.gauges[full_name] = MetricValue(
                value=value,
                timestamp=time.time(),
                labels=labels or {}
            )
    
    def record_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Record a value in a histogram metric."""
        with self.lock:
            full_name = self._build_metric_name(name, labels)
            self.histograms[full_name].add_value(value)
    
    def record_timer(self, name: str, duration: float, labels: Optional[Dict[str, str]] = None):
        """Record a timer measurement."""
        with self.lock:
            full_name = self._build_metric_name(name, labels)
            self.timers[full_name].append(MetricValue(
                value=duration,
                timestamp=time.time(),
                labels=labels or {}
            ))
    
    def _build_metric_name(self, name: str, labels: Optional[Dict[str, str]] = None) -> str:
        """Build a full metric name including labels."""
        if not labels:
            return name
        
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"
    
    def get_metric_value(self, name: str, metric_type: MetricType, labels: Optional[Dict[str, str]] = None) -> Any:
        """Get current value of a metric."""
        with self.lock:
            full_name = self._build_metric_name(name, labels)
            
            if metric_type == MetricType.COUNTER:
                return self.counters.get(full_name, 0.0)
            elif metric_type == MetricType.GAUGE:
                metric = self.gauges.get(full_name)
                return metric.value if metric else None
            elif metric_type == MetricType.HISTOGRAM:
                return asdict(self.histograms.get(full_name, HistogramData()))
            elif metric_type == MetricType.TIMER:
                timer_values = self.timers.get(full_name, deque())
                return [asdict(v) for v in timer_values]
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all collected metrics."""
        with self.lock:
            return {
                "counters": dict(self.counters),
                "gauges": {k: asdict(v) for k, v in self.gauges.items()},
                "histograms": {k: asdict(v) for k, v in self.histograms.items()},
                "timers": {k: [asdict(v) for v in values] for k, values in self.timers.items()}
            }
    
    def reset_metrics(self):
        """Reset all metrics."""
        with self.lock:
            self.counters.clear()
            self.gauges.clear()
            self.histograms.clear()
            self.timers.clear()
            logger.info("All metrics reset")


class Timer:
    """Context manager for timing operations."""
    
    def __init__(self, collector: MetricsCollector, metric_name: str, labels: Optional[Dict[str, str]] = None):
        self.collector = collector
        self.metric_name = metric_name
        self.labels = labels
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time is not None:
            duration = (time.perf_counter() - self.start_time) * 1000  # Convert to milliseconds
            self.collector.record_timer(self.metric_name, duration, self.labels)


class MonitoringService:
    """
    Main monitoring service for the order book system.
    
    Provides high-level monitoring capabilities and integrates with all system components.
    """
    
    def __init__(self):
        self.collector = MetricsCollector()
        self.system_metrics_history = deque(maxlen=100)
        self.alert_callbacks: List[Callable[[str, Dict], None]] = []
        self.is_monitoring = False
        self.monitoring_thread = None
        
        # Thresholds for alerts
        self.alert_thresholds = {
            'memory_usage_mb': 1000,  # Alert if over 1GB
            'cpu_usage_percent': 80,   # Alert if over 80%
            'error_rate': 0.05,        # Alert if error rate over 5%
            'processing_latency_ms': 1000  # Alert if latency over 1 second
        }
        
        logger.info("MonitoringService initialized")
    
    def start_monitoring(self, interval: float = 30.0):
        """
        Start continuous monitoring.
        
        Args:
            interval: Monitoring interval in seconds
        """
        if self.is_monitoring:
            logger.warning("Monitoring already started")
            return
        
        self.is_monitoring = True
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            args=(interval,),
            daemon=True
        )
        self.monitoring_thread.start()
        logger.info(f"Started monitoring with {interval}s interval")
    
    def stop_monitoring(self):
        """Stop continuous monitoring."""
        self.is_monitoring = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5.0)
        logger.info("Stopped monitoring")
    
    def _monitoring_loop(self, interval: float):
        """Main monitoring loop."""
        while self.is_monitoring:
            try:
                self._collect_system_metrics()
                time.sleep(interval)
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(interval)
    
    def _collect_system_metrics(self):
        """Collect system-wide metrics."""
        try:
            import psutil
            import os
            
            process = psutil.Process(os.getpid())
            
            # Memory usage
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            
            # CPU usage
            cpu_percent = process.cpu_percent()
            
            # Get application-specific metrics
            active_connections = self.collector.get_metric_value(
                "active_connections", MetricType.GAUGE
            ) or 0
            
            total_orderbooks = self.collector.get_metric_value(
                "total_orderbooks", MetricType.GAUGE
            ) or 0
            
            # Calculate cache hit rate
            cache_hits = self.collector.get_metric_value("cache_hits", MetricType.COUNTER) or 0
            cache_misses = self.collector.get_metric_value("cache_misses", MetricType.COUNTER) or 0
            cache_hit_rate = cache_hits / (cache_hits + cache_misses) if (cache_hits + cache_misses) > 0 else 0
            
            # Calculate processing latency
            processing_times = self.collector.get_metric_value("processing_time", MetricType.TIMER) or []
            avg_latency = statistics.mean([t['value'] for t in processing_times[-100:]]) if processing_times else 0
            
            # Calculate bandwidth
            bytes_sent = self.collector.get_metric_value("bytes_sent", MetricType.COUNTER) or 0
            bandwidth = bytes_sent / 60  # Rough estimate per second over last minute
            
            # Calculate error rate
            total_requests = self.collector.get_metric_value("total_requests", MetricType.COUNTER) or 0
            total_errors = self.collector.get_metric_value("total_errors", MetricType.COUNTER) or 0
            error_rate = total_errors / total_requests if total_requests > 0 else 0
            
            # Create system metrics snapshot
            metrics = SystemMetrics(
                timestamp=time.time(),
                active_connections=int(active_connections),
                total_orderbooks=int(total_orderbooks),
                cache_hit_rate=cache_hit_rate,
                memory_usage_mb=memory_mb,
                cpu_usage_percent=cpu_percent,
                processing_latency_ms=avg_latency,
                bandwidth_bytes_per_second=bandwidth,
                error_rate=error_rate
            )
            
            self.system_metrics_history.append(metrics)
            
            # Update gauge metrics
            self.collector.set_gauge("system_memory_mb", memory_mb)
            self.collector.set_gauge("system_cpu_percent", cpu_percent)
            self.collector.set_gauge("system_cache_hit_rate", cache_hit_rate)
            self.collector.set_gauge("system_error_rate", error_rate)
            
            # Check for alerts
            self._check_alerts(metrics)
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
    
    def _check_alerts(self, metrics: SystemMetrics):
        """Check if any metrics exceed alert thresholds."""
        alerts = []
        
        if metrics.memory_usage_mb > self.alert_thresholds['memory_usage_mb']:
            alerts.append({
                'type': 'high_memory_usage',
                'value': metrics.memory_usage_mb,
                'threshold': self.alert_thresholds['memory_usage_mb'],
                'message': f"Memory usage {metrics.memory_usage_mb:.1f}MB exceeds threshold"
            })
        
        if metrics.cpu_usage_percent > self.alert_thresholds['cpu_usage_percent']:
            alerts.append({
                'type': 'high_cpu_usage',
                'value': metrics.cpu_usage_percent,
                'threshold': self.alert_thresholds['cpu_usage_percent'],
                'message': f"CPU usage {metrics.cpu_usage_percent:.1f}% exceeds threshold"
            })
        
        if metrics.error_rate > self.alert_thresholds['error_rate']:
            alerts.append({
                'type': 'high_error_rate',
                'value': metrics.error_rate,
                'threshold': self.alert_thresholds['error_rate'],
                'message': f"Error rate {metrics.error_rate:.2%} exceeds threshold"
            })
        
        if metrics.processing_latency_ms > self.alert_thresholds['processing_latency_ms']:
            alerts.append({
                'type': 'high_latency',
                'value': metrics.processing_latency_ms,
                'threshold': self.alert_thresholds['processing_latency_ms'],
                'message': f"Processing latency {metrics.processing_latency_ms:.1f}ms exceeds threshold"
            })
        
        # Send alerts
        for alert in alerts:
            self._send_alert(alert['type'], alert)
    
    def _send_alert(self, alert_type: str, alert_data: Dict):
        """Send alert to registered callbacks."""
        logger.warning(f"ALERT: {alert_type} - {alert_data['message']}")
        
        for callback in self.alert_callbacks:
            try:
                callback(alert_type, alert_data)
            except Exception as e:
                logger.error(f"Error in alert callback: {e}")
    
    def register_alert_callback(self, callback: Callable[[str, Dict], None]):
        """Register a callback for alerts."""
        self.alert_callbacks.append(callback)
        logger.info("Registered alert callback")
    
    def get_system_metrics(self, count: int = 10) -> List[SystemMetrics]:
        """Get recent system metrics."""
        return list(self.system_metrics_history)[-count:]
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get comprehensive metrics summary."""
        recent_metrics = list(self.system_metrics_history)[-10:]
        
        if not recent_metrics:
            return {"message": "No metrics available"}
        
        latest = recent_metrics[-1]
        
        # Calculate trends
        if len(recent_metrics) >= 2:
            memory_trend = recent_metrics[-1].memory_usage_mb - recent_metrics[0].memory_usage_mb
            latency_trend = recent_metrics[-1].processing_latency_ms - recent_metrics[0].processing_latency_ms
        else:
            memory_trend = 0
            latency_trend = 0
        
        return {
            "current": asdict(latest),
            "trends": {
                "memory_mb_change": memory_trend,
                "latency_ms_change": latency_trend
            },
            "aggregates": {
                "avg_memory_mb": statistics.mean([m.memory_usage_mb for m in recent_metrics]),
                "avg_cpu_percent": statistics.mean([m.cpu_usage_percent for m in recent_metrics]),
                "avg_latency_ms": statistics.mean([m.processing_latency_ms for m in recent_metrics]),
                "avg_error_rate": statistics.mean([m.error_rate for m in recent_metrics])
            },
            "total_metrics": len(self.collector.get_all_metrics())
        }
    
    def timer(self, metric_name: str, labels: Optional[Dict[str, str]] = None) -> Timer:
        """Create a timer context manager."""
        return Timer(self.collector, metric_name, labels)
    
    def increment(self, metric_name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None):
        """Increment a counter metric."""
        self.collector.increment_counter(metric_name, value, labels)
    
    def gauge(self, metric_name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Set a gauge metric."""
        self.collector.set_gauge(metric_name, value, labels)
    
    def histogram(self, metric_name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Record a histogram value."""
        self.collector.record_histogram(metric_name, value, labels)
    
    def export_metrics_prometheus(self) -> str:
        """Export metrics in Prometheus format."""
        lines = []
        all_metrics = self.collector.get_all_metrics()
        
        # Export counters
        for name, value in all_metrics["counters"].items():
            lines.append(f"# TYPE {name} counter")
            lines.append(f"{name} {value}")
        
        # Export gauges
        for name, metric in all_metrics["gauges"].items():
            lines.append(f"# TYPE {name} gauge")
            lines.append(f"{name} {metric['value']}")
        
        # Export histograms
        for name, hist in all_metrics["histograms"].items():
            lines.append(f"# TYPE {name} histogram")
            for bucket, count in hist["buckets"].items():
                lines.append(f"{name}_bucket{{le=\"{bucket}\"}} {count}")
            lines.append(f"{name}_sum {hist['sum']}")
            lines.append(f"{name}_count {hist['count']}")
        
        return "\n".join(lines)
    
    def export_metrics_json(self) -> str:
        """Export metrics in JSON format."""
        return json.dumps({
            "timestamp": time.time(),
            "system_metrics": [asdict(m) for m in self.system_metrics_history],
            "application_metrics": self.collector.get_all_metrics()
        }, indent=2)


# Global monitoring service instance
monitoring_service = MonitoringService()


def get_monitoring_service() -> MonitoringService:
    """Get the global monitoring service instance."""
    return monitoring_service