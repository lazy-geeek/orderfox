"""
Trades WebSocket API endpoints.

This module provides FastAPI WebSocket endpoints for real-time trade data
streaming including recent trades and live trade updates.
"""

import json
import time
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.services.symbol_service import symbol_service
from app.services.trade_service import trade_service
from app.api.v1.endpoints.connection_manager import connection_manager
from app.core.logging_config import get_logger

logger = get_logger("trades_ws")

router = APIRouter()


@router.websocket("/ws/trades/{symbol}")
async def websocket_trades(websocket: WebSocket, symbol: str):
    """
    WebSocket endpoint for real-time trades updates.

    Args:
        websocket: WebSocket connection
        symbol: Trading symbol (e.g., 'BTCUSDT')

    The WebSocket will send JSON messages with the following format:
    {
        "type": "trades_update",
        "symbol": "BTCUSDT",
        "trades": [
            {
                "id": "12345",
                "price": 50000.0,
                "amount": 1.5,
                "side": "buy",
                "timestamp": 1640995200000,
                "price_formatted": "50,000.00",
                "amount_formatted": "1.50000000",
                "time_formatted": "12:30:45"
            }, ...
        ],
        "initial": true,  // Only true for first message with historical data
        "timestamp": 1640995200000
    }

    Error messages have the format:
    {
        "type": "error",
        "message": "Error description"
    }
    """
    logger.info(
        f"WebSocket trades connection attempt for {symbol} from {websocket.client}")

    try:
        # Accept connection first
        await websocket.accept()
        logger.info(f"WebSocket trades connection accepted for {symbol}")

        # Validate and convert symbol using symbol service
        exchange_symbol = symbol_service.resolve_symbol_to_exchange_format(symbol)
        if not exchange_symbol:
            # Get suggestions for invalid symbol
            suggestions = symbol_service.get_symbol_suggestions(symbol)
            error_msg = f"Symbol {symbol} not found"
            if suggestions:
                error_msg += f". Did you mean: {', '.join(suggestions[:3])}?"

            logger.warning(f"WebSocket trades error: {error_msg}")
            await websocket.send_text(
                json.dumps({"type": "error", "message": error_msg})
            )
            await websocket.close(code=4000, reason=error_msg)
            return

        logger.info(
            f"Using exchange symbol: {exchange_symbol} for WebSocket symbol: {symbol}")

        # Fetch initial trades data
        try:
            logger.info(f"Fetching initial trades data for {symbol}")
            initial_trades = await trade_service.fetch_trades_with_fallback(
                exchange_symbol, limit=100
            )

            # Send initial batch with 'initial': true
            initial_message = {
                "type": "trades_update",
                "symbol": symbol,  # Use frontend symbol format
                "trades": initial_trades,
                "initial": True,
                "timestamp": int(time.time() * 1000)
            }

            await websocket.send_text(json.dumps(initial_message))
            logger.info(
                f"Sent initial trades data for {symbol}: {len(initial_trades)} trades")

        except Exception as e:
            logger.error(f"Failed to fetch initial trades for {symbol}: {e}")
            error_msg = f"Failed to load initial trades: {str(e)}"
            await websocket.send_text(
                json.dumps({"type": "error", "message": error_msg})
            )
            # Continue with real-time stream even if initial data fails

        # Connect to the connection manager using unique trades stream key
        trades_stream_key = f"{exchange_symbol}:trades"
        await connection_manager.connect(websocket, trades_stream_key, "trades", symbol)
        logger.info(
            f"WebSocket trades streaming started for {symbol} (exchange: {exchange_symbol})"
        )

        try:
            # Keep the connection alive and handle incoming messages
            while True:
                try:
                    # Use receive() instead of receive_text() to handle all message types
                    message = await websocket.receive()

                    # Check if it's a disconnect message
                    if message["type"] == "websocket.disconnect":
                        logger.info(
                            f"WebSocket trades client disconnected for {symbol}")
                        break

                    # Handle text messages
                    elif message["type"] == "websocket.receive":
                        if "text" in message:
                            try:
                                data = json.loads(message["text"])
                                message_type = data.get("type")

                                if message_type == "ping":
                                    await websocket.send_text(
                                        json.dumps({"type": "pong"})
                                    )
                                else:
                                    logger.warning(
                                        f"Unknown message type '{message_type}' received from client for {symbol}")
                            except json.JSONDecodeError:
                                logger.warning(
                                    f"Invalid JSON received from client for {symbol}")

                except WebSocketDisconnect:
                    logger.debug(
                        f"WebSocket trades client disconnected for {symbol}")
                    break
                except Exception as e:
                    logger.error(
                        f"Error in WebSocket receive loop for {symbol}: {str(e)}")
                    break

        except WebSocketDisconnect:
            logger.debug(f"WebSocket trades client disconnected for {symbol}")
        finally:
            connection_manager.disconnect(websocket, trades_stream_key)
            logger.debug(f"WebSocket trades connection cleaned up for {symbol}")

    except Exception as e:
        logger.error(
            f"WebSocket trades error for {symbol}: {str(e)}", exc_info=True)
        try:
            if websocket.client_state.name != "DISCONNECTED":
                await websocket.send_text(
                    json.dumps(
                        {"type": "error", "message": f"Connection error: {str(e)}"}
                    )
                )
                await websocket.close(code=4000, reason=f"Connection error: {str(e)}")
        except Exception as close_error:
            logger.error(
                f"Error closing WebSocket for {symbol}: {str(close_error)}")