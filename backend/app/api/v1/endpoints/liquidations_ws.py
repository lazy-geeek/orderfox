"""
Liquidations WebSocket API endpoints.

This module provides FastAPI WebSocket endpoints for real-time liquidation data
streaming from Binance futures liquidation orders.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.api.v1.endpoints.connection_manager import connection_manager as manager
from app.services.symbol_service import symbol_service
from app.services.liquidation_service import liquidation_service
from app.models.liquidation import LiquidationVolumeUpdate, LiquidationVolume
from typing import List, Dict, Optional
import asyncio
import logging
from datetime import datetime
from collections import deque

logger = logging.getLogger(__name__)
router = APIRouter()

# Store recent liquidations per symbol using deque for FIFO behavior
# Global cache shared across all WebSocket connections for the same symbol
liquidations_cache: Dict[str, deque] = {}
MAX_LIQUIDATIONS = 50
# Track if historical data has been loaded for each symbol
historical_loaded: Dict[str, bool] = {}

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
        """Callback for liquidation data with deduplication"""
        # Initialize cache if needed
        if display_symbol not in liquidations_cache:
            liquidations_cache[display_symbol] = deque(maxlen=MAX_LIQUIDATIONS)
        
        # Check for duplicates using timestamp + amount + side as unique key
        new_key = f"{data.get('timestamp', 0)}_{data.get('priceUsdt', '')}_{data.get('side', '')}"
        
        # Check if this liquidation already exists in cache
        for existing in liquidations_cache[display_symbol]:
            existing_key = f"{existing.get('timestamp', 0)}_{existing.get('priceUsdt', '')}_{existing.get('side', '')}"
            if existing_key == new_key:
                # Duplicate found - skip adding to queue and cache
                return
        
        # Add to queue for this WebSocket connection
        await liquidation_queue.put(data)
        
        # Store in global cache (prepend to keep newest first)
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
        
        # Initialize cache and load historical data (only once per symbol globally)
        if display_symbol not in liquidations_cache:
            liquidations_cache[display_symbol] = deque(maxlen=MAX_LIQUIDATIONS)
        
        # Load historical data only once per symbol (shared across all WebSocket connections)
        if display_symbol not in historical_loaded:
            historical_loaded[display_symbol] = True
            
            # Fetch historical liquidations
            logger.info(f"Fetching historical liquidations for {display_symbol} (shared across all connections)")
            historical = await liquidation_service.fetch_historical_liquidations(
                display_symbol, limit=MAX_LIQUIDATIONS, symbol_info=symbol_info
            )
            
            # Add to cache (newest first - sort by timestamp descending)
            # Sort historical data by timestamp (newest first)
            historical_sorted = sorted(historical, key=lambda x: x.get('timestamp', 0), reverse=True)
            for liquidation in historical_sorted:
                liquidations_cache[display_symbol].append(liquidation)
            
            if historical:
                logger.info(f"Loaded {len(historical)} historical liquidations for {display_symbol}")
        else:
            logger.info(f"Using existing historical liquidations for {display_symbol}")
        
        # Send initial data with cached liquidations
        initial_data = {
            "type": "liquidation_order",  # Changed from "liquidations" for clarity
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
            # Create a task to send volume data once candle time range is available
            async def send_volume_when_ready():
                try:
                    from app.services.chart_data_service import chart_data_service
                    
                    # Convert display symbol to exchange format for cache lookup
                    exchange_symbol = symbol_service.resolve_symbol_to_exchange_format(display_symbol)
                    cache_key = f"{exchange_symbol}:{timeframe}"
                    
                    # Wait for candle time range to be cached (with timeout)
                    max_wait = 10  # seconds
                    wait_interval = 0.1  # 100ms
                    waited = 0
                    
                    while waited < max_wait:
                        time_range = chart_data_service.time_range_cache.get(cache_key)
                        if time_range:
                            break
                        await asyncio.sleep(wait_interval)
                        waited += wait_interval
                    
                    if time_range:
                        # Use the exact same time range as the candles
                        start_time = time_range['start_ms']
                        end_time = time_range['end_ms']
                        logger.info(f"Using cached candle time range for {display_symbol}/{timeframe}: {start_time} to {end_time}")
                    else:
                        # Fallback to last 24 hours if no cached range after waiting
                        logger.warning(f"No cached time range for {cache_key} after {max_wait}s, using default 24h range")
                        end_time = int(datetime.now().timestamp() * 1000)
                        start_time = end_time - (24 * 60 * 60 * 1000)
                    
                    historical_volume = await liquidation_service.fetch_historical_liquidations_by_timeframe(
                        display_symbol, timeframe, start_time, end_time
                    )
                
                    if historical_volume:
                        # Check if WebSocket is still connected before sending
                        if websocket.client_state.name == "CONNECTED":
                            # Convert dict objects to LiquidationVolume models
                            volume_data = [LiquidationVolume(**vol) for vol in historical_volume]
                            
                            volume_update = LiquidationVolumeUpdate(
                                symbol=display_symbol,
                                timeframe=timeframe,
                                data=volume_data,
                                timestamp=datetime.utcnow().isoformat(),
                                is_update=False  # Historical data, not real-time update
                            )
                            await websocket.send_json(volume_update.dict())
                            logger.info(f"Sent {len(historical_volume)} historical volume records for {display_symbol}/{timeframe}")
                        else:
                            logger.debug(f"WebSocket disconnected for {display_symbol}, skipping historical volume send")
                except Exception as e:
                    logger.error(f"Error fetching historical volume data: {e}")
            
            # Add the volume task to run concurrently
            volume_task = asyncio.create_task(send_volume_when_ready())
            tasks.append(volume_task)
        
        # Create tasks for handling different data streams
        
        # Task for liquidation data
        async def handle_liquidations():
            while True:
                try:
                    # Wait for new liquidation with timeout
                    liquidation = await asyncio.wait_for(liquidation_queue.get(), timeout=30)
                    
                    # Check if WebSocket is still connected before sending
                    if websocket.client_state.name != "CONNECTED":
                        logger.debug(f"WebSocket disconnected for {display_symbol}, stopping liquidation updates")
                        break
                    
                    # Send update
                    update = {
                        "type": "liquidation_order",  # Changed from "liquidation" for clarity
                        "symbol": display_symbol,
                        "data": liquidation,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    await websocket.send_json(update)
                    
                except asyncio.TimeoutError:
                    # Check if WebSocket is still connected before sending heartbeat
                    if websocket.client_state.name != "CONNECTED":
                        logger.debug(f"WebSocket disconnected for {display_symbol}, stopping heartbeats")
                        break
                        
                    # Send heartbeat
                    heartbeat = {
                        "type": "heartbeat",
                        "symbol": display_symbol,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    await websocket.send_json(heartbeat)
                except Exception as e:
                    logger.error(f"Error in handle_liquidations: {e}")
                    break
        
        # Task for volume data (if timeframe specified)
        async def handle_volume():
            if not volume_queue:
                return
                
            while True:
                try:
                    # Wait for volume update with timeout
                    volume_data = await asyncio.wait_for(volume_queue.get(), timeout=5.0)
                    
                    # Check if WebSocket is still connected before sending
                    if websocket.client_state.name != "CONNECTED":
                        logger.debug(f"WebSocket disconnected for {display_symbol}, stopping volume updates")
                        break
                    
                    # Send volume update
                    # Determine if this is a real-time update (single data point) or historical batch
                    is_realtime_update = len(volume_data) == 1
                    
                    # Type check - timeframe is guaranteed to be not None in this function
                    assert timeframe is not None
                    
                    volume_update = LiquidationVolumeUpdate(
                        symbol=display_symbol,
                        timeframe=timeframe,
                        data=volume_data,
                        timestamp=datetime.utcnow().isoformat(),
                        is_update=is_realtime_update  # True for real-time, False for historical batches
                    )
                    await websocket.send_json(volume_update.dict())
                    
                except asyncio.TimeoutError:
                    # Check connection state on timeout
                    if websocket.client_state.name != "CONNECTED":
                        logger.debug(f"WebSocket disconnected for {display_symbol}, stopping volume updates")
                        break
                    # Continue waiting if still connected
                    continue
                except Exception as e:
                    logger.error(f"Error sending volume update: {e}")
                    # If we can't send, the connection is likely closed
                    break
        
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
        
        # Disconnect liquidation stream for this callback only (reference counting)
        try:
            await liquidation_service.disconnect_stream(display_symbol, liquidation_callback)
        except Exception as e:
            logger.error(f"Error disconnecting liquidation stream: {e}")
        
        # Unregister volume callback if timeframe was specified
        if timeframe:
            try:
                await liquidation_service.unregister_volume_callback(display_symbol, timeframe, volume_callback)
            except Exception as e:
                logger.error(f"Error unregistering volume callback: {e}")