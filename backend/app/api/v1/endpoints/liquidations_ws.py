"""
Liquidations WebSocket API endpoints.

This module provides FastAPI WebSocket endpoints for real-time liquidation data
streaming from Binance futures liquidation orders.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.api.v1.endpoints.connection_manager import connection_manager as manager
from app.services.symbol_service import symbol_service
from app.services.liquidation_service import liquidation_service
from app.models.liquidation import LiquidationVolumeUpdate
from typing import List, Dict, Optional
import asyncio
import logging
from datetime import datetime
from collections import deque

logger = logging.getLogger(__name__)
router = APIRouter()

# Store recent liquidations per symbol using deque for FIFO behavior
liquidations_cache: Dict[str, deque] = {}
MAX_LIQUIDATIONS = 50

@router.websocket("/ws/liquidations/{display_symbol}")
async def liquidation_stream(
    websocket: WebSocket, 
    display_symbol: str,
    timeframe: Optional[str] = Query(None, description="Timeframe for volume aggregation (1m, 5m, 15m, 1h, 4h, 1d)")
):
    """
    WebSocket endpoint for liquidation data streaming
    
    Args:
        display_symbol: Trading symbol (e.g., BTCUSDT)
        timeframe: Optional timeframe for volume aggregation
    """
    
    await websocket.accept()
    logger.info(f"Liquidations WebSocket connected for {display_symbol} (timeframe: {timeframe})")
    
    liquidation_queue = asyncio.Queue()
    volume_queue = asyncio.Queue() if timeframe else None
    tasks = []  # Initialize tasks list
    
    async def liquidation_callback(data: Dict):
        """Callback for liquidation data"""
        await liquidation_queue.put(data)
        
        # Store in liquidations cache (prepend to keep newest first)
        if display_symbol not in liquidations_cache:
            liquidations_cache[display_symbol] = deque(maxlen=MAX_LIQUIDATIONS)
        liquidations_cache[display_symbol].appendleft(data)
    
    async def volume_callback(volume_data: List[Dict]):
        """Callback for aggregated volume data"""
        if volume_queue:
            await volume_queue.put(volume_data)
    
    try:
        # Validate symbol
        if not symbol_service.validate_symbol_exists(display_symbol):
            error_msg = {
                "type": "error",
                "message": f"Invalid symbol: {display_symbol}",
                "timestamp": datetime.utcnow().isoformat()
            }
            await websocket.send_json(error_msg)
            return
            
        # Convert to exchange format
        exchange_symbol = symbol_service.resolve_symbol_to_exchange_format(display_symbol)
        
        # Get symbol info for formatting
        symbol_info = symbol_service.get_symbol_info(display_symbol)
        
        # Initialize cache with historical data (only once per symbol)
        if display_symbol not in liquidations_cache:
            liquidations_cache[display_symbol] = deque(maxlen=MAX_LIQUIDATIONS)
            
            # Fetch historical liquidations
            logger.info(f"Fetching historical liquidations for {display_symbol}")
            historical = await liquidation_service.fetch_historical_liquidations(
                display_symbol, limit=MAX_LIQUIDATIONS
            )
            
            # Add to cache (newest first - sort by timestamp descending)
            # Sort historical data by timestamp (newest first)
            historical_sorted = sorted(historical, key=lambda x: x.get('timestamp', 0), reverse=True)
            for liquidation in historical_sorted:
                liquidations_cache[display_symbol].append(liquidation)
            
            if historical:
                logger.info(f"Loaded {len(historical)} historical liquidations for {display_symbol}")
        
        # Send initial data with cached liquidations
        initial_data = {
            "type": "liquidations",
            "symbol": display_symbol,
            "data": list(liquidations_cache[display_symbol]),
            "initial": True,
            "timestamp": datetime.utcnow().isoformat()
        }
        await websocket.send_json(initial_data)
        
        # Connect to liquidation stream with symbol info
        await liquidation_service.connect_to_liquidation_stream(display_symbol, liquidation_callback, symbol_info)
        
        # If timeframe is specified, register for volume updates and send historical volume data
        if timeframe:
            # Validate timeframe
            valid_timeframes = ['1m', '5m', '15m', '30m', '1h', '4h', '1d']
            if timeframe not in valid_timeframes:
                error_msg = {
                    "type": "error",
                    "message": f"Invalid timeframe. Must be one of: {', '.join(valid_timeframes)}",
                    "timestamp": datetime.utcnow().isoformat()
                }
                await websocket.send_json(error_msg)
                return
            
            # Register for volume updates
            await liquidation_service.register_volume_callback(display_symbol, timeframe, volume_callback)
            
            # Send historical volume data
            try:
                # Get last 24 hours of volume data
                end_time = int(datetime.now().timestamp() * 1000)
                start_time = end_time - (24 * 60 * 60 * 1000)
                
                historical_volume = await liquidation_service.fetch_historical_liquidations_by_timeframe(
                    display_symbol, timeframe, start_time, end_time
                )
                
                if historical_volume:
                    volume_update = LiquidationVolumeUpdate(
                        symbol=display_symbol,
                        timeframe=timeframe,
                        data=historical_volume,
                        timestamp=datetime.utcnow().isoformat()
                    )
                    await websocket.send_json(volume_update.dict())
                    logger.info(f"Sent {len(historical_volume)} historical volume records for {display_symbol}/{timeframe}")
            except Exception as e:
                logger.error(f"Error fetching historical volume data: {e}")
        
        # Create tasks for handling different data streams
        tasks = []
        
        # Task for liquidation data
        async def handle_liquidations():
            while True:
                try:
                    # Wait for new liquidation with timeout
                    liquidation = await asyncio.wait_for(liquidation_queue.get(), timeout=30)
                    
                    # Send update
                    update = {
                        "type": "liquidation",
                        "symbol": display_symbol,
                        "data": liquidation,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    await websocket.send_json(update)
                    
                except asyncio.TimeoutError:
                    # Send heartbeat
                    heartbeat = {
                        "type": "heartbeat",
                        "symbol": display_symbol,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    await websocket.send_json(heartbeat)
        
        # Task for volume data (if timeframe specified)
        async def handle_volume():
            if not volume_queue:
                return
                
            while True:
                try:
                    # Wait for volume update
                    volume_data = await volume_queue.get()
                    
                    # Send volume update
                    volume_update = LiquidationVolumeUpdate(
                        symbol=display_symbol,
                        timeframe=timeframe,
                        data=volume_data,
                        timestamp=datetime.utcnow().isoformat()
                    )
                    await websocket.send_json(volume_update.dict())
                    
                except Exception as e:
                    logger.error(f"Error sending volume update: {e}")
        
        # Start tasks
        tasks.append(asyncio.create_task(handle_liquidations()))
        if timeframe:
            tasks.append(asyncio.create_task(handle_volume()))
        
        # Run until disconnected
        await asyncio.gather(*tasks)
                
    except WebSocketDisconnect:
        logger.info(f"Liquidations WebSocket disconnected for {display_symbol}")
    except Exception as e:
        logger.error(f"Error in liquidations WebSocket for {display_symbol}: {e}")
        error_msg = {
            "type": "error",
            "message": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
        try:
            await websocket.send_json(error_msg)
        except:
            pass
    finally:
        # Cancel tasks
        for task in tasks:
            task.cancel()
        
        # Disconnect liquidation stream for this symbol
        try:
            await liquidation_service.disconnect_stream(display_symbol)
        except Exception as e:
            logger.error(f"Error disconnecting liquidation stream: {e}")
        
        # Unregister volume callback if timeframe was specified
        if timeframe:
            try:
                await liquidation_service.unregister_volume_callback(display_symbol, timeframe, volume_callback)
            except Exception as e:
                logger.error(f"Error unregistering volume callback: {e}")