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

logger = logging.getLogger(__name__)
router = APIRouter()

# Store recent liquidations per symbol
recent_liquidations: Dict[str, List[Dict]] = {}
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
        
        # Store in recent liquidations
        if display_symbol not in recent_liquidations:
            recent_liquidations[display_symbol] = []
        recent_liquidations[display_symbol].insert(0, data)
        recent_liquidations[display_symbol] = recent_liquidations[display_symbol][:MAX_LIQUIDATIONS]
    
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
        
        # Send initial data with recent liquidations
        initial_data = {
            "type": "liquidations",
            "symbol": display_symbol,
            "data": recent_liquidations.get(display_symbol, []),
            "initial": True,
            "timestamp": datetime.utcnow().isoformat()
        }
        await websocket.send_json(initial_data)
        
        # Connect to liquidation stream
        await liquidation_service.connect_to_liquidation_stream(display_symbol, liquidation_callback)
        
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