"""
Liquidations WebSocket API endpoints.

This module provides FastAPI WebSocket endpoints for real-time liquidation data
streaming from Binance futures liquidation orders.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.api.v1.endpoints.connection_manager import connection_manager as manager
from app.services.symbol_service import symbol_service
from app.services.liquidation_service import liquidation_service
from typing import List, Dict
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
async def liquidation_stream(websocket: WebSocket, display_symbol: str):
    """WebSocket endpoint for liquidation data streaming"""
    
    await websocket.accept()
    logger.info(f"Liquidations WebSocket connected for {display_symbol}")
    
    liquidation_queue = asyncio.Queue()
    
    async def liquidation_callback(data: Dict):
        """Callback for liquidation data"""
        await liquidation_queue.put(data)
        
        # Store in liquidations cache (prepend to keep newest first)
        if display_symbol not in liquidations_cache:
            liquidations_cache[display_symbol] = deque(maxlen=MAX_LIQUIDATIONS)
        liquidations_cache[display_symbol].appendleft(data)
    
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
        
        # Stream liquidation data
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
        # Disconnect liquidation stream for this symbol
        try:
            await liquidation_service.disconnect_stream(display_symbol)
        except Exception as e:
            logger.error(f"Error disconnecting liquidation stream: {e}")
        pass