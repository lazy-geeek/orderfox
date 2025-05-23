"""
WebSocket Connection Manager for real-time data streaming.

This module provides the ConnectionManager class that handles WebSocket connections
for real-time market data streaming including order books, tickers, and candles.
"""

from typing import List, Dict, Any
import asyncio
import json
from fastapi import WebSocket, WebSocketDisconnect
from app.services.exchange_service import exchange_service


class ConnectionManager:
    """Manages WebSocket connections for real-time data streaming."""

    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.streaming_tasks: Dict[str, asyncio.Task] = {}

    async def connect(
        self, websocket: WebSocket, stream_key: str, stream_type: str = "orderbook"
    ):
        """Accept a new WebSocket connection for a stream."""
        await websocket.accept()

        if stream_key not in self.active_connections:
            self.active_connections[stream_key] = []

        self.active_connections[stream_key].append(websocket)

        # Start streaming task if this is the first connection for this stream
        if len(self.active_connections[stream_key]) == 1:
            await self._start_streaming(stream_key, stream_type)

    def disconnect(self, websocket: WebSocket, stream_key: str):
        """Remove a WebSocket connection."""
        if stream_key in self.active_connections:
            if websocket in self.active_connections[stream_key]:
                self.active_connections[stream_key].remove(websocket)

            # Stop streaming if no more connections for this stream
            if not self.active_connections[stream_key]:
                self._stop_streaming(stream_key)
                del self.active_connections[stream_key]

    async def broadcast_to_stream(self, stream_key: str, data: dict):
        """Broadcast data to all connections for a specific stream."""
        if stream_key in self.active_connections:
            disconnected = []
            for connection in self.active_connections[stream_key]:
                try:
                    await connection.send_text(json.dumps(data))
                except Exception:
                    # Connection is broken, mark for removal
                    disconnected.append(connection)

            # Remove disconnected connections
            for connection in disconnected:
                self.disconnect(connection, stream_key)

    async def _start_streaming(self, stream_key: str, stream_type: str):
        """Start streaming data for a stream key."""
        if stream_type == "orderbook":
            task = asyncio.create_task(self._stream_orderbook(stream_key))
        elif stream_type == "ticker":
            task = asyncio.create_task(self._stream_ticker(stream_key))
        elif stream_type == "candles":
            # Extract symbol and timeframe from stream_key (format: "symbol:timeframe")
            symbol, timeframe = stream_key.split(":")
            task = asyncio.create_task(
                self._stream_candles(symbol, timeframe, stream_key)
            )
        else:
            raise ValueError(f"Unknown stream type: {stream_type}")

        self.streaming_tasks[stream_key] = task

    def _stop_streaming(self, stream_key: str):
        """Stop streaming data for a stream key."""
        if stream_key in self.streaming_tasks:
            self.streaming_tasks[stream_key].cancel()
            del self.streaming_tasks[stream_key]

    # Keep backward compatibility for existing orderbook methods
    async def connect_orderbook(self, websocket: WebSocket, symbol: str):
        """Accept a new WebSocket connection for orderbook (backward compatibility)."""
        await self.connect(websocket, symbol, "orderbook")

    def disconnect_orderbook(self, websocket: WebSocket, symbol: str):
        """Remove a WebSocket connection for orderbook (backward compatibility)."""
        self.disconnect(websocket, symbol)

    async def broadcast_to_symbol(self, symbol: str, data: dict):
        """Broadcast data to all connections for a symbol (backward compatibility)."""
        await self.broadcast_to_stream(symbol, data)

    async def _stream_orderbook(self, symbol: str):
        """Stream order book updates using ccxtpro."""
        exchange_pro = None
        try:
            exchange_pro = exchange_service.get_exchange_pro()

            while symbol in self.active_connections and self.active_connections[symbol]:
                try:
                    # Watch order book updates
                    order_book_data = await exchange_pro.watch_order_book(symbol)

                    # Convert to our schema format
                    bids = [
                        {"price": float(bid[0]), "amount": float(bid[1])}
                        for bid in order_book_data["bids"][:20]  # Top 20 levels
                    ]

                    asks = [
                        {"price": float(ask[0]), "amount": float(ask[1])}
                        for ask in order_book_data["asks"][:20]  # Top 20 levels
                    ]

                    formatted_data = {
                        "type": "orderbook_update",
                        "symbol": symbol,
                        "bids": bids,
                        "asks": asks,
                        "timestamp": order_book_data["timestamp"],
                    }

                    # Broadcast to all connected clients for this symbol
                    await self.broadcast_to_symbol(symbol, formatted_data)

                except Exception as e:
                    error_data = {
                        "type": "error",
                        "message": f"Error streaming order book for {symbol}: {str(e)}",
                    }
                    await self.broadcast_to_symbol(symbol, error_data)
                    await asyncio.sleep(5)  # Wait before retrying

        except Exception as e:
            error_data = {
                "type": "error",
                "message": f"Failed to initialize streaming for {symbol}: {str(e)}",
            }
            await self.broadcast_to_symbol(symbol, error_data)
        finally:
            if exchange_pro:
                try:
                    await exchange_pro.close()
                except Exception:
                    pass

    async def _stream_ticker(self, symbol: str):
        """Stream ticker updates using ccxtpro."""
        exchange_pro = None
        try:
            exchange_pro = exchange_service.get_exchange_pro()

            while symbol in self.active_connections and self.active_connections[symbol]:
                try:
                    # Watch ticker updates
                    ticker_data = await exchange_pro.watch_ticker(symbol)

                    # Convert to our schema format
                    formatted_data = {
                        "type": "ticker_update",
                        "symbol": symbol,
                        "last": (
                            float(ticker_data.get("last", 0))
                            if ticker_data.get("last")
                            else None
                        ),
                        "bid": (
                            float(ticker_data.get("bid", 0))
                            if ticker_data.get("bid")
                            else None
                        ),
                        "ask": (
                            float(ticker_data.get("ask", 0))
                            if ticker_data.get("ask")
                            else None
                        ),
                        "high": (
                            float(ticker_data.get("high", 0))
                            if ticker_data.get("high")
                            else None
                        ),
                        "low": (
                            float(ticker_data.get("low", 0))
                            if ticker_data.get("low")
                            else None
                        ),
                        "open": (
                            float(ticker_data.get("open", 0))
                            if ticker_data.get("open")
                            else None
                        ),
                        "close": (
                            float(ticker_data.get("close", 0))
                            if ticker_data.get("close")
                            else None
                        ),
                        "change": (
                            float(ticker_data.get("change", 0))
                            if ticker_data.get("change")
                            else None
                        ),
                        "percentage": (
                            float(ticker_data.get("percentage", 0))
                            if ticker_data.get("percentage")
                            else None
                        ),
                        "volume": (
                            float(ticker_data.get("baseVolume", 0))
                            if ticker_data.get("baseVolume")
                            else None
                        ),
                        "quote_volume": (
                            float(ticker_data.get("quoteVolume", 0))
                            if ticker_data.get("quoteVolume")
                            else None
                        ),
                        "timestamp": ticker_data.get("timestamp"),
                    }

                    # Broadcast to all connected clients for this symbol
                    await self.broadcast_to_stream(symbol, formatted_data)

                except Exception as e:
                    error_data = {
                        "type": "error",
                        "message": f"Error streaming ticker for {symbol}: {str(e)}",
                    }
                    await self.broadcast_to_stream(symbol, error_data)
                    await asyncio.sleep(5)  # Wait before retrying

        except Exception as e:
            error_data = {
                "type": "error",
                "message": f"Failed to initialize ticker streaming for {symbol}: {str(e)}",
            }
            await self.broadcast_to_stream(symbol, error_data)
        finally:
            if exchange_pro:
                try:
                    await exchange_pro.close()
                except Exception:
                    pass

    async def _stream_candles(self, symbol: str, timeframe: str, stream_key: str):
        """Stream candle/OHLCV updates using ccxtpro."""
        exchange_pro = None
        try:
            exchange_pro = exchange_service.get_exchange_pro()

            while (
                stream_key in self.active_connections
                and self.active_connections[stream_key]
            ):
                try:
                    # Watch OHLCV updates
                    ohlcv_data = await exchange_pro.watch_ohlcv(symbol, timeframe)

                    # Convert to our schema format - get the latest candle
                    if ohlcv_data and len(ohlcv_data) > 0:
                        latest_candle = ohlcv_data[-1]  # Get the most recent candle

                        formatted_data = {
                            "type": "candle_update",
                            "symbol": symbol,
                            "timeframe": timeframe,
                            "timestamp": latest_candle[0],
                            "open": float(latest_candle[1]),
                            "high": float(latest_candle[2]),
                            "low": float(latest_candle[3]),
                            "close": float(latest_candle[4]),
                            "volume": float(latest_candle[5]),
                        }

                        # Broadcast to all connected clients for this stream
                        await self.broadcast_to_stream(stream_key, formatted_data)

                except Exception as e:
                    error_data = {
                        "type": "error",
                        "message": f"Error streaming candles for {symbol} {timeframe}: {str(e)}",
                    }
                    await self.broadcast_to_stream(stream_key, error_data)
                    await asyncio.sleep(5)  # Wait before retrying

        except Exception as e:
            error_data = {
                "type": "error",
                "message": f"Failed to initialize candle streaming for {symbol} {timeframe}: {str(e)}",
            }
            await self.broadcast_to_stream(stream_key, error_data)
        finally:
            if exchange_pro:
                try:
                    await exchange_pro.close()
                except Exception:
                    pass


# Global connection manager instance
connection_manager = ConnectionManager()
