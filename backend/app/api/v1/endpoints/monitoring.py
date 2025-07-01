"""
Monitoring endpoints for system health and metrics
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import PlainTextResponse
import time
import logging

from app.services.monitoring_service import get_monitoring_service, SystemMetrics
from app.services.orderbook_processor import OrderBookProcessor
from app.services.delta_update_service import DeltaUpdateService
from app.services.batch_update_service import BatchUpdateService

logger = logging.getLogger(__name__)

router = APIRouter()
monitoring_service = get_monitoring_service()


@router.get("/health", response_model=Dict[str, Any])
async def health_check():
    """
    Basic health check endpoint.
    Returns system status and basic metrics.
    """
    try:
        current_time = time.time()
        metrics_summary = monitoring_service.get_metrics_summary()
        
        # Check if system is healthy based on recent metrics
        is_healthy = True
        health_issues = []
        
        if "current" in metrics_summary:
            current = metrics_summary["current"]
            
            # Check memory usage
            if current.get("memory_usage_mb", 0) > 1000:
                is_healthy = False
                health_issues.append("High memory usage")
            
            # Check error rate
            if current.get("error_rate", 0) > 0.1:
                is_healthy = False
                health_issues.append("High error rate")
            
            # Check CPU usage
            if current.get("cpu_usage_percent", 0) > 90:
                is_healthy = False
                health_issues.append("High CPU usage")
        
        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "timestamp": current_time,
            "issues": health_issues,
            "uptime_seconds": current_time - (metrics_summary.get("current", {}).get("timestamp", current_time)),
            "version": "1.0.0"
        }
    
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail="Health check failed")


@router.get("/metrics", response_model=Dict[str, Any])
async def get_metrics(
    format: Optional[str] = Query(None, description="Output format: json or prometheus"),
    include_history: bool = Query(False, description="Include historical data")
):
    """
    Get comprehensive system metrics.
    Supports both JSON and Prometheus output formats.
    """
    try:
        if format == "prometheus":
            prometheus_data = monitoring_service.export_metrics_prometheus()
            return PlainTextResponse(
                content=prometheus_data,
                media_type="text/plain"
            )
        
        # Default JSON format
        if include_history:
            return {
                "timestamp": time.time(),
                "summary": monitoring_service.get_metrics_summary(),
                "history": [
                    {
                        "timestamp": m.timestamp,
                        "memory_mb": m.memory_usage_mb,
                        "cpu_percent": m.cpu_usage_percent,
                        "active_connections": m.active_connections,
                        "cache_hit_rate": m.cache_hit_rate,
                        "processing_latency_ms": m.processing_latency_ms,
                        "error_rate": m.error_rate
                    }
                    for m in monitoring_service.get_system_metrics(50)
                ],
                "all_metrics": monitoring_service.collector.get_all_metrics()
            }
        else:
            return {
                "timestamp": time.time(),
                "summary": monitoring_service.get_metrics_summary(),
                "all_metrics": monitoring_service.collector.get_all_metrics()
            }
    
    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve metrics")


@router.get("/metrics/prometheus")
async def get_prometheus_metrics():
    """
    Get metrics in Prometheus format.
    This endpoint is specifically for Prometheus scraping.
    """
    try:
        prometheus_data = monitoring_service.export_metrics_prometheus()
        return PlainTextResponse(
            content=prometheus_data,
            media_type="text/plain; version=0.0.4; charset=utf-8"
        )
    except Exception as e:
        logger.error(f"Failed to export Prometheus metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to export metrics")


@router.get("/stats/orderbook", response_model=Dict[str, Any])
async def get_orderbook_stats():
    """
    Get detailed order book processing statistics.
    """
    try:
        # This would need to be injected or imported from a global instance
        # For now, we'll return placeholder data
        return {
            "timestamp": time.time(),
            "cache_stats": {
                "hit_rate": 0.85,
                "total_hits": 1000,
                "total_misses": 150,
                "cache_size": 50
            },
            "processing_stats": {
                "total_processed": 5000,
                "avg_processing_time_ms": 2.5,
                "max_processing_time_ms": 15.0,
                "min_processing_time_ms": 0.5
            },
            "aggregation_stats": {
                "total_aggregations": 3000,
                "avg_aggregation_time_ms": 1.2,
                "rounding_distribution": {
                    "0.01": 500,
                    "0.1": 800,
                    "1.0": 1200,
                    "10.0": 500
                }
            }
        }
    
    except Exception as e:
        logger.error(f"Failed to get order book stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve order book stats")


@router.get("/stats/connections", response_model=Dict[str, Any])
async def get_connection_stats():
    """
    Get WebSocket connection statistics.
    """
    try:
        # This would integrate with the actual connection manager
        return {
            "timestamp": time.time(),
            "total_connections": 25,
            "active_connections": 23,
            "connections_by_symbol": {
                "BTCUSDT": 8,
                "ETHUSDT": 6,
                "BNBUSDT": 4,
                "SOLUSDT": 3,
                "ADAUSDT": 2
            },
            "connections_by_rounding": {
                "0.01": 5,
                "0.1": 8,
                "1.0": 10,
                "10.0": 2
            },
            "avg_connection_duration_seconds": 1200,
            "total_messages_sent": 50000,
            "avg_messages_per_connection": 2100
        }
    
    except Exception as e:
        logger.error(f"Failed to get connection stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve connection stats")


@router.get("/stats/performance", response_model=Dict[str, Any])
async def get_performance_stats():
    """
    Get system performance statistics.
    """
    try:
        recent_metrics = monitoring_service.get_system_metrics(30)
        
        if not recent_metrics:
            return {"message": "No performance data available"}
        
        # Calculate performance statistics
        memory_values = [m.memory_usage_mb for m in recent_metrics]
        cpu_values = [m.cpu_usage_percent for m in recent_metrics]
        latency_values = [m.processing_latency_ms for m in recent_metrics]
        
        import statistics
        
        return {
            "timestamp": time.time(),
            "sample_count": len(recent_metrics),
            "time_range_seconds": recent_metrics[-1].timestamp - recent_metrics[0].timestamp if len(recent_metrics) > 1 else 0,
            "memory": {
                "current_mb": recent_metrics[-1].memory_usage_mb,
                "avg_mb": statistics.mean(memory_values),
                "max_mb": max(memory_values),
                "min_mb": min(memory_values),
                "trend": "increasing" if memory_values[-1] > memory_values[0] else "decreasing"
            },
            "cpu": {
                "current_percent": recent_metrics[-1].cpu_usage_percent,
                "avg_percent": statistics.mean(cpu_values),
                "max_percent": max(cpu_values),
                "min_percent": min(cpu_values)
            },
            "latency": {
                "current_ms": recent_metrics[-1].processing_latency_ms,
                "avg_ms": statistics.mean(latency_values),
                "max_ms": max(latency_values),
                "min_ms": min(latency_values),
                "p95_ms": statistics.quantiles(latency_values, n=20)[18] if len(latency_values) > 20 else max(latency_values)
            },
            "throughput": {
                "bandwidth_bytes_per_second": recent_metrics[-1].bandwidth_bytes_per_second,
                "error_rate": recent_metrics[-1].error_rate,
                "cache_hit_rate": recent_metrics[-1].cache_hit_rate
            }
        }
    
    except Exception as e:
        logger.error(f"Failed to get performance stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve performance stats")


@router.post("/monitoring/start")
async def start_monitoring():
    """
    Start continuous monitoring if not already running.
    """
    try:
        if not monitoring_service.is_monitoring:
            monitoring_service.start_monitoring()
            return {"message": "Monitoring started", "status": "success"}
        else:
            return {"message": "Monitoring already running", "status": "already_running"}
    
    except Exception as e:
        logger.error(f"Failed to start monitoring: {e}")
        raise HTTPException(status_code=500, detail="Failed to start monitoring")


@router.post("/monitoring/stop")
async def stop_monitoring():
    """
    Stop continuous monitoring.
    """
    try:
        if monitoring_service.is_monitoring:
            monitoring_service.stop_monitoring()
            return {"message": "Monitoring stopped", "status": "success"}
        else:
            return {"message": "Monitoring not running", "status": "not_running"}
    
    except Exception as e:
        logger.error(f"Failed to stop monitoring: {e}")
        raise HTTPException(status_code=500, detail="Failed to stop monitoring")


@router.post("/metrics/reset")
async def reset_metrics():
    """
    Reset all collected metrics.
    WARNING: This will clear all historical data.
    """
    try:
        monitoring_service.collector.reset_metrics()
        return {"message": "All metrics reset", "status": "success", "timestamp": time.time()}
    
    except Exception as e:
        logger.error(f"Failed to reset metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to reset metrics")


@router.get("/debug/memory")
async def get_memory_debug():
    """
    Get detailed memory usage information for debugging.
    """
    try:
        import psutil
        import os
        import gc
        
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        
        # Trigger garbage collection and get stats
        gc.collect()
        gc_stats = gc.get_stats()
        
        return {
            "timestamp": time.time(),
            "process_memory": {
                "rss_mb": memory_info.rss / 1024 / 1024,
                "vms_mb": memory_info.vms / 1024 / 1024,
                "percent": process.memory_percent(),
                "available_mb": psutil.virtual_memory().available / 1024 / 1024,
                "total_mb": psutil.virtual_memory().total / 1024 / 1024
            },
            "garbage_collection": {
                "collections": gc_stats,
                "garbage_objects": len(gc.garbage),
                "reference_cycles": sum(stat['collections'] for stat in gc_stats)
            },
            "system_memory": {
                "total_mb": psutil.virtual_memory().total / 1024 / 1024,
                "available_mb": psutil.virtual_memory().available / 1024 / 1024,
                "percent_used": psutil.virtual_memory().percent,
                "swap_total_mb": psutil.swap_memory().total / 1024 / 1024,
                "swap_used_mb": psutil.swap_memory().used / 1024 / 1024
            }
        }
    
    except Exception as e:
        logger.error(f"Failed to get memory debug info: {e}")
        raise HTTPException(status_code=500, detail="Failed to get memory debug info")