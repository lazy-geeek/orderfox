"""
Market Data WebSocket API endpoints.

This module provides FastAPI WebSocket endpoints for real-time market data
streaming including order books, tickers, and candlestick data.
"""

import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.services.exchange_service import exchange_service
from app.services.symbol_service import symbol_service
from app.api.v1.endpoints.connection_manager import connection_manager
from app.api.v1.endpoints.trading import trading_engine_service_instance
from app.core.logging_config import get_logger

logger = get_logger("market_data_ws")

router = APIRouter()


@router.websocket("/ws/orderbook/{symbol}")
async def websocket_orderbook(
    websocket: WebSocket, 
    symbol: str, 
    limit: int = Query(default=20, ge=5, le=5000),
    rounding: float = Query(default=0.01, gt=0)
):
    """
    WebSocket endpoint for real-time aggregated order book updates.

    Args:
        websocket: WebSocket connection
        symbol: Trading symbol (e.g., 'BTCUSDT')
        limit: Number of order book levels to stream (default: 20, max: 5000)
        rounding: Price rounding value for aggregation (default: 0.01, must be > 0)

    The WebSocket will send JSON messages with the following format:
    {
        "type": "orderbook_update",
        "symbol": "BTCUSDT",
        "bids": [
            {
                "price": 50000.0, 
                "amount": 1.5, 
                "cumulative": 1.5,
                "price_formatted": "50000.00",
                "amount_formatted": "1.50000000",
                "cumulative_formatted": "1.50000000"
            }, ...
        ],
        "asks": [
            {
                "price": 50100.0, 
                "amount": 2.0, 
                "cumulative": 2.0,
                "price_formatted": "50100.00",
                "amount_formatted": "2.00000000", 
                "cumulative_formatted": "2.00000000"
            }, ...
        ],
        "timestamp": 1640995200000,
        "rounding": 0.01,
        "rounding_options": [0.01, 0.1, 1, 10, 100],
        "market_depth_info": {"actual_levels": 20, "requested_levels": 20},
        "aggregated": true
    }
    
    Note: Formatted fields (price_formatted, amount_formatted, cumulative_formatted) 
    are included when symbol precision data is available. These fields provide 
    backend-formatted strings optimized for display, eliminating frontend formatting.

    Parameter update messages can be sent:
    {
        "type": "update_params",
        "limit": 50,
        "rounding": 1.0
    }

    Error messages have the format:
    {
        "type": "error",
        "message": "Error description"
    }
    """
    logger.info(
        f"WebSocket orderbook connection attempt for {symbol} from {websocket.client}"
    )

    try:
        # Accept connection first
        await websocket.accept()
        logger.info(f"WebSocket orderbook connection accepted for {symbol}")

        # Validate and convert symbol using symbol service
        exchange_symbol = symbol_service.resolve_symbol_to_exchange_format(symbol)
        if not exchange_symbol:
            # Get suggestions for invalid symbol
            suggestions = symbol_service.get_symbol_suggestions(symbol)
            error_msg = f"Symbol {symbol} not found"
            if suggestions:
                error_msg += f". Did you mean: {', '.join(suggestions[:3])}?"

            logger.warning(f"WebSocket orderbook error: {error_msg}")
            await websocket.send_text(
                json.dumps({"type": "error", "message": error_msg})
            )
            await websocket.close(code=4000, reason=error_msg)
            return

        logger.info(
            f"Using exchange symbol: {exchange_symbol} for WebSocket symbol: {symbol}"
        )

        # Validate and clamp limit parameter (handle Query object in tests)
        limit_value = limit if isinstance(limit, int) else (limit.default if hasattr(limit, 'default') else 20)
        limit = max(5, min(limit_value, 1000))  # Ensure limit is between 5 and 1000
        
        # Validate rounding parameter (handle Query object in tests)
        rounding_value = rounding if isinstance(rounding, (int, float)) else (rounding.default if hasattr(rounding, 'default') else 0.01)
        rounding = max(0.0001, rounding_value)  # Ensure minimum rounding value
        
        # Populate symbol data for optimal aggregation
        try:
            symbol_info = symbol_service.get_symbol_info(exchange_symbol)
            if symbol_info and symbol_info.get('pricePrecision') is not None:
                # Import here to avoid circular imports
                from app.services.orderbook_manager import orderbook_manager
                
                symbol_data = {
                    'pricePrecision': symbol_info['pricePrecision'],
                    'amountPrecision': symbol_info.get('amountPrecision', 2),
                    'symbol': symbol_info['symbol'],
                    'base_asset': symbol_info.get('base_asset'),
                    'quote_asset': symbol_info.get('quote_asset')
                }
                await orderbook_manager.update_symbol_data(exchange_symbol, symbol_data)
                logger.info(f"Updated symbol data for {exchange_symbol} with pricePrecision={symbol_info['pricePrecision']}, amountPrecision={symbol_info.get('amountPrecision', 2)}")
        except Exception as e:
            logger.warning(f"Could not populate symbol data for {exchange_symbol}: {e}")
            # Continue without symbol data - fallbacks will handle this

        # Connect to the connection manager using the exchange symbol, limit, and rounding
        await connection_manager.connect_orderbook(websocket, exchange_symbol, symbol, limit, rounding)
        logger.info(
            f"WebSocket orderbook streaming started for {symbol} (exchange: {exchange_symbol})"
        )

        try:
            # Keep the connection alive
            while True:
                try:
                    # Use receive() instead of receive_text() to handle all message types
                    message = await websocket.receive()

                    # Check if it's a disconnect message
                    if message["type"] == "websocket.disconnect":
                        logger.info(
                            f"WebSocket orderbook client disconnected for {symbol}"
                        )
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
                                elif message_type == "update_params":
                                    # Handle parameter updates
                                    await connection_manager.handle_websocket_message(
                                        websocket, exchange_symbol, data
                                    )
                                else:
                                    logger.warning(
                                        f"Unknown message type '{message_type}' received from client for {symbol}"
                                    )
                            except json.JSONDecodeError:
                                logger.warning(
                                    f"Invalid JSON received from client for {symbol}"
                                )

                except WebSocketDisconnect:
                    logger.debug(f"WebSocket orderbook client disconnected for {symbol}")
                    break
                except Exception as e:
                    logger.error(
                        f"Error in WebSocket receive loop for {symbol}: {str(e)}"
                    )
                    break

        except WebSocketDisconnect:
            logger.debug(f"WebSocket orderbook client disconnected for {symbol}")
        finally:
            await connection_manager.disconnect_orderbook(websocket, exchange_symbol)
            logger.debug(f"WebSocket orderbook connection cleaned up for {symbol}")

    except Exception as e:
        logger.error(f"WebSocket orderbook error for {symbol}: {str(e)}", exc_info=True)
        try:
            if websocket.client_state.name != "DISCONNECTED":
                await websocket.send_text(
                    json.dumps(
                        {"type": "error", "message": f"Connection error: {str(e)}"}
                    )
                )
                await websocket.close(code=4000, reason=f"Connection error: {str(e)}")
        except Exception as close_error:
            logger.error(f"Error closing WebSocket for {symbol}: {str(close_error)}")


@router.websocket("/ws/ticker/{symbol}")
async def websocket_ticker(websocket: WebSocket, symbol: str):
    """
    WebSocket endpoint for real-time ticker updates.

    Args:
        websocket: WebSocket connection
        symbol: Trading symbol (e.g., 'BTCUSDT')

    The WebSocket will send JSON messages with the following format:
    {
        "type": "ticker_update",
        "symbol": "BTCUSDT",
        "last": 50000.0,
        "bid": 49999.5,
        "ask": 50000.5,
        "high": 51000.0,
        "low": 49000.0,
        "open": 49500.0,
        "close": 50000.0,
        "change": 500.0,
        "percentage": 1.01,
        "volume": 1250.75,
        "quote_volume": 62537500.0,
        "timestamp": 1640995200000
    }

    Error messages have the format:
    {
        "type": "error",
        "message": "Error description"
    }
    """
    logger.info(
        f"WebSocket ticker connection attempt for {symbol} from {websocket.client}"
    )

    try:
        # Accept connection first
        await websocket.accept()
        logger.info(f"WebSocket ticker connection accepted for {symbol}")

        # Validate and convert symbol using symbol service
        exchange_symbol = symbol_service.resolve_symbol_to_exchange_format(symbol)
        if not exchange_symbol:
            # Get suggestions for invalid symbol
            suggestions = symbol_service.get_symbol_suggestions(symbol)
            error_msg = f"Symbol {symbol} not found"
            if suggestions:
                error_msg += f". Did you mean: {', '.join(suggestions[:3])}?"

            logger.warning(f"WebSocket ticker error: {error_msg}")
            await websocket.send_text(
                json.dumps({"type": "error", "message": error_msg})
            )
            await websocket.close(code=4000, reason=error_msg)
            return

        # Connect to the connection manager using unique ticker stream key
        ticker_stream_key = f"{exchange_symbol}:ticker"
        await connection_manager.connect(websocket, ticker_stream_key, "ticker", symbol)
        logger.info(
            f"WebSocket ticker streaming started for {symbol} (exchange: {exchange_symbol})"
        )

        try:
            # Keep the connection alive
            while True:
                try:
                    # Use receive() instead of receive_text() to handle all message types
                    message = await websocket.receive()

                    # Check if it's a disconnect message
                    if message["type"] == "websocket.disconnect":
                        logger.info(
                            f"WebSocket ticker client disconnected for {symbol}"
                        )
                        break

                    # Handle text messages
                    elif message["type"] == "websocket.receive":
                        if "text" in message:
                            try:
                                data = json.loads(message["text"])
                                if data.get("type") == "ping":
                                    await websocket.send_text(
                                        json.dumps({"type": "pong"})
                                    )
                            except json.JSONDecodeError:
                                logger.warning(
                                    f"Invalid JSON received from client for {symbol}"
                                )

                except WebSocketDisconnect:
                    logger.info(f"WebSocket ticker client disconnected for {symbol}")
                    break
                except Exception as e:
                    logger.error(
                        f"Error in WebSocket receive loop for {symbol}: {str(e)}"
                    )
                    break

        except WebSocketDisconnect:
            logger.info(f"WebSocket ticker client disconnected for {symbol}")
        finally:
            connection_manager.disconnect(websocket, exchange_symbol)
            logger.info(f"WebSocket ticker connection cleaned up for {symbol}")

    except Exception as e:
        logger.error(f"WebSocket ticker error for {symbol}: {str(e)}", exc_info=True)
        try:
            if websocket.client_state.name != "DISCONNECTED":
                await websocket.send_text(
                    json.dumps(
                        {"type": "error", "message": f"Connection error: {str(e)}"}
                    )
                )
                await websocket.close(code=4000, reason=f"Connection error: {str(e)}")
        except Exception as close_error:
            logger.error(f"Error closing WebSocket for {symbol}: {str(close_error)}")


@router.websocket("/ws/candles/{symbol}/{timeframe}")
async def websocket_candles(websocket: WebSocket, symbol: str, timeframe: str):
    """
    WebSocket endpoint for real-time candle/OHLCV updates.

    Args:
        websocket: WebSocket connection
        symbol: Trading symbol (e.g., 'BTCUSDT')
        timeframe: Timeframe for candles (e.g., '1m', '5m', '1h', '1d')

    The WebSocket will send JSON messages with the following format:
    {
        "type": "candle_update",
        "symbol": "BTCUSDT",
        "timeframe": "1m",
        "timestamp": 1640995200000,
        "open": 49500.0,
        "high": 50100.0,
        "low": 49400.0,
        "close": 50000.0,
        "volume": 125.75
    }

    Error messages have the format:
    {
        "type": "error",
        "message": "Error description"
    }
    """
    # Validate timeframe first
    valid_timeframes = [
        "1m",
        "3m",
        "5m",
        "15m",
        "30m",
        "1h",
        "2h",
        "4h",
        "6h",
        "8h",
        "12h",
        "1d",
        "3d",
        "1w",
        "1M",
    ]
    if timeframe not in valid_timeframes:
        logger.warning(f"WebSocket candles invalid timeframe: {timeframe}")
        await websocket.accept()
        error_msg = f"Invalid timeframe. Valid options: {', '.join(valid_timeframes)}"
        await websocket.send_text(json.dumps({"type": "error", "message": error_msg}))
        await websocket.close(code=4000, reason=error_msg)
        return

    logger.info(
        f"WebSocket candles connection attempt for {symbol}/{timeframe} from {websocket.client}"
    )

    try:
        # Accept connection first
        await websocket.accept()
        logger.info(f"WebSocket candles connection accepted for {symbol}/{timeframe}")

        # Validate and convert symbol using symbol service
        exchange_symbol = symbol_service.resolve_symbol_to_exchange_format(symbol)
        if not exchange_symbol:
            # Get suggestions for invalid symbol
            suggestions = symbol_service.get_symbol_suggestions(symbol)
            error_msg = f"Symbol {symbol} not found"
            if suggestions:
                error_msg += f". Did you mean: {', '.join(suggestions[:3])}?"

            logger.warning(f"WebSocket candles error: {error_msg}")
            await websocket.send_text(
                json.dumps({"type": "error", "message": error_msg})
            )
            await websocket.close(code=4000, reason=error_msg)
            return

        # Create stream key for this symbol:timeframe combination using exchange symbol
        stream_key = f"{exchange_symbol}:{timeframe}"

        # Connect to the connection manager
        await connection_manager.connect(websocket, stream_key, "candles", symbol)
        logger.info(
            f"WebSocket candles streaming started for {symbol}/{timeframe} (exchange: {exchange_symbol})"
        )

        try:
            # Keep the connection alive
            while True:
                try:
                    # Use receive() instead of receive_text() to handle all message types
                    message = await websocket.receive()

                    # Check if it's a disconnect message
                    if message["type"] == "websocket.disconnect":
                        logger.info(
                            f"WebSocket candles client disconnected for {symbol}/{timeframe}"
                        )
                        break

                    # Handle text messages
                    elif message["type"] == "websocket.receive":
                        if "text" in message:
                            try:
                                data = json.loads(message["text"])
                                if data.get("type") == "ping":
                                    await websocket.send_text(
                                        json.dumps({"type": "pong"})
                                    )
                            except json.JSONDecodeError:
                                logger.warning(
                                    f"Invalid JSON received from client for {symbol}/{timeframe}"
                                )

                except WebSocketDisconnect:
                    logger.info(
                        f"WebSocket candles client disconnected for {symbol}/{timeframe}"
                    )
                    break
                except Exception as e:
                    logger.error(
                        f"Error in WebSocket receive loop for {symbol}/{timeframe}: {str(e)}"
                    )
                    break

        except WebSocketDisconnect:
            logger.info(
                f"WebSocket candles client disconnected for {symbol}/{timeframe}"
            )
        finally:
            connection_manager.disconnect(websocket, stream_key)
            logger.info(
                f"WebSocket candles connection cleaned up for {symbol}/{timeframe}"
            )

    except Exception as e:
        logger.error(
            f"WebSocket candles error for {symbol}/{timeframe}: {str(e)}", exc_info=True
        )
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
                f"Error closing WebSocket for {symbol}/{timeframe}: {str(close_error)}"
            )
