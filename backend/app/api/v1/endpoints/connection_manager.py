"""
WebSocket Connection Manager for real-time data streaming.

This module provides the ConnectionManager class that handles WebSocket connections
for real-time market data streaming including order books, tickers, and candles.
"""

from typing import List, Dict
import asyncio
import json
from fastapi import WebSocket, WebSocketDisconnect
from app.services.exchange_service import exchange_service
from app.services.chart_data_service import chart_data_service
from app.services.orderbook_manager import orderbook_manager
from app.models.orderbook import OrderBookSnapshot, OrderBookLevel
from app.core.logging_config import get_logger

logger = get_logger("connection_manager")


class ConnectionManager:
    """Manages WebSocket connections for real-time data streaming."""

    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.streaming_tasks: Dict[str, asyncio.Task] = {}
        # Tracks active stream types per symbol (e.g., {"BTCUSDT":
        # {"orderbook", "candles:1m"}})
        self.symbol_active_streams: Dict[str, set[str]] = {}
        # Stores the type of each stream_key
        self.stream_key_types: Dict[str, str] = {}

    async def connect(
        self,
        websocket: WebSocket,
        stream_key: str,
        stream_type: str = "orderbook",
        display_symbol: str = None,
    ):
        """Accept a new WebSocket connection for a stream."""
        logger.info(
            f"Connecting WebSocket for stream {stream_key} (type: {stream_type})")

        # Store display symbol for response formatting
        if display_symbol and stream_key not in getattr(
                self, "_display_symbols", {}):
            if not hasattr(self, "_display_symbols"):
                self._display_symbols = {}
            self._display_symbols[stream_key] = display_symbol

        # Note: WebSocket should already be accepted by the endpoint
        if stream_key not in self.active_connections:
            self.active_connections[stream_key] = []

        self.active_connections[stream_key].append(websocket)
        self.stream_key_types[stream_key] = stream_type  # Store stream type
        logger.info(
            f"WebSocket connected to stream {stream_key}. Total connections: {
                len(
                    self.active_connections[stream_key])}")

        # Extract base symbol from stream_key for symbol_active_streams
        # tracking
        base_symbol = self._get_base_symbol_from_stream_key(
            stream_key, stream_type)
        if base_symbol:
            if base_symbol not in self.symbol_active_streams:
                self.symbol_active_streams[base_symbol] = set()
            self.symbol_active_streams[base_symbol].add(stream_key)
            logger.debug(
                f"Active streams for {base_symbol}: {
                    self.symbol_active_streams[base_symbol]}")

        # Start streaming task if this is the first connection for this stream
        if len(self.active_connections[stream_key]) == 1:
            logger.info(f"Starting streaming task for {stream_key}")
            await self._start_streaming(stream_key, stream_type)

    def disconnect(self, websocket: WebSocket, stream_key: str):
        """Remove a WebSocket connection."""
        if stream_key in self.active_connections:
            if websocket in self.active_connections[stream_key]:
                self.active_connections[stream_key].remove(websocket)
                logger.debug(
                    f"WebSocket disconnected from stream {stream_key}. Remaining connections: {
                        len(
                            self.active_connections[stream_key])}")

            # Check if there are any remaining connections for this specific
            # stream_key
            if not self.active_connections[stream_key]:
                logger.debug(
                    f"No more connections for stream_key: {stream_key}. Stopping its specific streaming task.")
                self._stop_streaming(
                    stream_key
                )  # Cancels task and removes from self.streaming_tasks

                retrieved_stream_type = self.stream_key_types.get(stream_key)
                del self.active_connections[stream_key]
                # Do NOT delete from self.stream_key_types[stream_key] here yet.
                # It's needed for the "stop all tasks for base_symbol" logic
                # below.

                base_symbol = None
                if retrieved_stream_type:
                    base_symbol = self._get_base_symbol_from_stream_key(
                        stream_key, retrieved_stream_type
                    )
                else:
                    logger.warning(
                        f"Could not retrieve stored stream_type for stream_key: {stream_key} upon disconnect. "
                        f"This might affect comprehensive cleanup if it's the last stream for its base symbol."
                    )

                if base_symbol and base_symbol in self.symbol_active_streams:
                    self.symbol_active_streams[base_symbol].discard(stream_key)
                    logger.debug(
                        f"Updated active streams for {base_symbol}: {
                            self.symbol_active_streams[base_symbol]}")

                    if not self.symbol_active_streams[base_symbol]:
                        logger.info(
                            f"No more active specific streams for base_symbol {base_symbol}. "
                            f"Ensuring all related streaming tasks are stopped and cleaning up types."
                        )
                        # Iterate over a copy of streaming_tasks keys, as
                        # _stop_streaming modifies the dict
                        tasks_to_check_for_stop = list(
                            self.streaming_tasks.keys())
                        stopped_task_keys_for_base_symbol = []

                        for task_key_iter in tasks_to_check_for_stop:
                            # We need the type of task_key_iter to determine
                            # its base_symbol
                            iter_task_type = self.stream_key_types.get(
                                task_key_iter)
                            if iter_task_type:
                                iter_base_symbol = (
                                    self._get_base_symbol_from_stream_key(
                                        task_key_iter, iter_task_type
                                    )
                                )
                                if iter_base_symbol == base_symbol:
                                    logger.debug(
                                        f"Stopping task {task_key_iter} as part of {base_symbol} cleanup.")
                                    # Ensures it's cancelled and removed from
                                    # streaming_tasks
                                    self._stop_streaming(task_key_iter)
                                    stopped_task_keys_for_base_symbol.append(
                                        task_key_iter
                                    )
                            else:
                                logger.warning(
                                    f"No type found for active task {task_key_iter} during {base_symbol} cleanup. Skipping.")

                        # Now, clean up stream_key_types for all stream_keys associated with this base_symbol.
                        # This includes the original stream_key and any others
                        # that were part of its group.
                        logger.debug(
                            f"Cleaning up stream_key_types for base_symbol: {base_symbol}")
                        related_stream_keys_for_type_cleanup = [
                            s_key
                            for s_key, s_type in list(
                                self.stream_key_types.items()
                            )  # Iterate over a copy
                            if self._get_base_symbol_from_stream_key(s_key, s_type)
                            == base_symbol
                        ]
                        for key_to_delete_type in related_stream_keys_for_type_cleanup:
                            if key_to_delete_type in self.stream_key_types:
                                logger.debug(
                                    f"Deleting {key_to_delete_type} from stream_key_types.")
                                del self.stream_key_types[key_to_delete_type]

                        if (
                            base_symbol in self.symbol_active_streams
                        ):  # Check before deleting
                            del self.symbol_active_streams[base_symbol]
                        else:  # Should not happen if logic is correct, but good to log
                            logger.warning(
                                f"Attempted to delete {base_symbol} from symbol_active_streams, but it was already removed or not found.")
                elif (
                    base_symbol
                ):  # base_symbol was determined, but not in symbol_active_streams
                    logger.warning(
                        f"Base symbol {base_symbol} (from stream_key {stream_key}) not found in symbol_active_streams for cleanup.")
                # else: base_symbol could not be determined, already logged.

            else:  # Still active connections for this specific stream_key
                logger.debug(
                    f"Stream {stream_key} still has {
                        len(
                            self.active_connections[stream_key])} active connections.")
        else:  # stream_key not in self.active_connections
            logger.warning(
                f"Attempted to disconnect from non-existent or already cleaned stream: {stream_key}")

    def _get_base_symbol_from_stream_key(
        self, stream_key: str, stream_type: str | None  # Added | None
    ) -> str | None:
        """Helper to extract the base symbol from a stream_key."""
        if not stream_type:  # Handle if stream_type is None
            logger.debug(
                f"Cannot determine base symbol for {stream_key} without stream_type.")
            return None
        if stream_type == "candles":
            parts = stream_key.split(":")
            if len(parts) >= 2:
                return ":".join(parts[:-1])
        elif stream_type == "orderbook" or stream_type == "ticker":
            return stream_key
        logger.warning(
            f"Unknown stream_type '{stream_type}' for stream_key '{stream_key}' in _get_base_symbol_from_stream_key."
        )
        return None  # Default for unknown types or if logic above fails

    async def broadcast_to_stream(self, stream_key: str, data: dict):
        """Broadcast data to all connections for a specific stream."""
        if stream_key in self.active_connections:
            disconnected = []
            # Iterate over a copy of the list of connections, as
            # self.disconnect can modify it
            for connection in list(self.active_connections[stream_key]):
                try:
                    await connection.send_text(json.dumps(data))
                except WebSocketDisconnect:
                    logger.info(
                        f"WebSocketDisconnect detected for a connection on stream {stream_key}. Marking for removal.")
                    disconnected.append(connection)
                except Exception as e:
                    logger.error(
                        f"Error sending to a connection on stream {stream_key}: {e}. Marking for removal.")
                    disconnected.append(connection)

            # Remove disconnected connections
            for connection in disconnected:
                # Check if connection is still in the list before attempting to remove,
                # as multiple errors or rapid disconnects could lead to it
                # being already handled.
                if (
                    stream_key in self.active_connections
                    and connection in self.active_connections[stream_key]
                ):
                    self.disconnect(connection, stream_key)
                else:
                    logger.debug(
                        f"Connection for stream {stream_key} already removed, skipping redundant disconnect call.")

    async def _start_streaming(self, stream_key: str, stream_type: str):
        """Start streaming data for a stream key."""
        if stream_key in self.streaming_tasks:  # Prevent duplicate tasks
            logger.warning(
                f"Streaming task for {stream_key} already exists. Not starting a new one.")
            return

        if stream_type == "orderbook":
            task = asyncio.create_task(self._stream_orderbook(stream_key))
        elif stream_type == "ticker":
            # For ticker streams, extract symbol from stream_key (format:
            # "SYMBOL:ticker" -> "SYMBOL")
            symbol = stream_key.replace(
                ":ticker", "") if stream_key.endswith(":ticker") else stream_key
            task = asyncio.create_task(self._stream_ticker(symbol))
        elif stream_type == "candles":
            parts = stream_key.split(":")
            if len(parts) >= 2:
                symbol = ":".join(parts[:-1])
                timeframe = parts[-1]
            else:
                logger.error(
                    f"Invalid stream key format for candles: {stream_key}")
                return  # Do not create task for invalid format
            task = asyncio.create_task(
                self._stream_candles(symbol, timeframe, stream_key)
            )
        else:
            logger.error(
                f"Unknown stream type: {stream_type} for stream_key: {stream_key}")
            return  # Do not create task for unknown type

        self.streaming_tasks[stream_key] = task
        logger.info(
            f"Successfully started streaming task for {stream_key} (type: {stream_type})")

    def _stop_streaming(self, stream_key: str):
        """Stop streaming data for a stream key. Cancels the task and removes it from tracking."""
        if stream_key in self.streaming_tasks:
            logger.debug(
                f"Cancelling and removing streaming task for {stream_key}")
            try:
                # CRITICAL: Cancel task immediately to prevent race conditions
                task = self.streaming_tasks[stream_key]
                if not task.cancelled():
                    task.cancel()
                    logger.debug(f"Task for {stream_key} cancelled successfully")
            except Exception as e:  # Catch potential errors during cancellation
                logger.error(f"Error cancelling task for {stream_key}: {e}")
            del self.streaming_tasks[stream_key]
            
            # CRITICAL: Immediately remove from active_connections to prevent new broadcasts
            if stream_key in self.active_connections:
                logger.debug(f"Clearing active connections for {stream_key} during stream stop")
                # Don't delete the key yet, just clear the connections list
                # The disconnect method will handle full cleanup
                self.active_connections[stream_key] = []
        else:
            # This might be normal if a task was already stopped by another
            # path (e.g. base_symbol cleanup)
            logger.debug(
                f"Attempted to stop streaming task for {stream_key}, but it was not found in streaming_tasks (possibly already stopped).")

    # Enhanced orderbook connection with aggregation support
    async def connect_orderbook(
        self, websocket: WebSocket, symbol: str, display_symbol: str = None,
        limit: int = 20, rounding: float = 0.01
    ):
        """Accept a new WebSocket connection for orderbook with aggregation parameters."""
        # Generate unique connection ID
        connection_id = f"{symbol}:{id(websocket)}"

        # Register connection with OrderBook Manager
        try:
            await orderbook_manager.register_connection(
                connection_id, symbol, limit, rounding
            )
            logger.info(
                f"Registered orderbook connection {connection_id} with limit={limit}, rounding={rounding}")
        except Exception as e:
            logger.error(
                f"Failed to register orderbook connection {connection_id}: {e}")
            await websocket.close(code=1011, reason="Failed to initialize orderbook")
            return

        # Store connection metadata for message handling
        if not hasattr(self, '_connection_metadata'):
            self._connection_metadata = {}

        self._connection_metadata[connection_id] = {
            'websocket': websocket,
            'symbol': symbol,
            'display_symbol': display_symbol,
            'limit': limit,
            'rounding': rounding,
            'type': 'orderbook'
        }

        await self.connect(websocket, symbol, "orderbook", display_symbol)

    async def disconnect_orderbook(self, websocket: WebSocket, symbol: str):
        """Remove a WebSocket connection for orderbook with proper cleanup."""
        # Find and cleanup connection metadata
        connection_id = f"{symbol}:{id(websocket)}"

        if hasattr(
                self,
                '_connection_metadata') and connection_id in self._connection_metadata:
            del self._connection_metadata[connection_id]

        # Unregister from OrderBook Manager
        try:
            await orderbook_manager.unregister_connection(connection_id)
            logger.info(f"Unregistered orderbook connection {connection_id}")
        except Exception as e:
            logger.error(
                f"Failed to unregister orderbook connection {connection_id}: {e}")

        # Standard disconnect
        self.disconnect(websocket, symbol)

    async def broadcast_to_symbol(self, symbol: str, data: dict):
        """Broadcast data to all connections for a symbol (backward compatibility)."""
        await self.broadcast_to_stream(symbol, data)

    async def handle_websocket_message(
            self,
            websocket: WebSocket,
            symbol: str,
            message: dict):
        """Handle incoming WebSocket messages for parameter updates."""
        try:
            message_type = message.get("type")

            if message_type == "update_params":
                connection_id = f"{symbol}:{id(websocket)}"
                limit = message.get("limit")
                rounding = message.get("rounding")

                logger.info(
                    f"Received parameter update for {connection_id}: limit={limit}, rounding={rounding}")

                # Update OrderBook Manager
                success = await orderbook_manager.update_connection_params(
                    connection_id, limit, rounding
                )

                if success:
                    # Update local metadata
                    if hasattr(
                            self,
                            '_connection_metadata') and connection_id in self._connection_metadata:
                        if limit is not None:
                            self._connection_metadata[connection_id]['limit'] = limit
                        if rounding is not None:
                            self._connection_metadata[connection_id]['rounding'] = rounding

                    # Send acknowledgment and updated data
                    ack_message = {
                        "type": "params_updated",
                        "limit": limit,
                        "rounding": rounding,
                        "success": True
                    }
                    await websocket.send_text(json.dumps(ack_message))

                    # Broadcast updated aggregated data
                    await self._broadcast_aggregated_orderbook(connection_id)

                else:
                    error_message = {
                        "type": "error",
                        "message": f"Failed to update parameters for connection {connection_id}"}
                    await websocket.send_text(json.dumps(error_message))
            else:
                logger.warning(
                    f"Unknown message type received: {message_type}")

        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")
            error_message = {
                "type": "error",
                "message": f"Error processing message: {str(e)}"
            }
            await websocket.send_text(json.dumps(error_message))

    async def _broadcast_aggregated_orderbook(self, connection_id: str):
        """Broadcast aggregated orderbook data to a specific connection."""
        try:
            # Get aggregated data from OrderBook Manager
            aggregated_data = await orderbook_manager.get_aggregated_orderbook(connection_id)

            if aggregated_data:
                # Get connection metadata for display symbol
                metadata = getattr(
                    self, '_connection_metadata', {}).get(
                    connection_id, {})
                display_symbol = metadata.get('display_symbol')
                aggregated_symbol = aggregated_data.get('symbol', '')

                # Use display_symbol if it's non-empty, otherwise use the
                # aggregated data symbol
                symbol_to_send = display_symbol if display_symbol else aggregated_symbol

                # Ensure we always have a symbol to send
                if not symbol_to_send:
                    logger.warning(
                        f"No symbol available for connection {connection_id}, using connection metadata")
                    # Extract symbol from connection_id as fallback
                    symbol_to_send = connection_id.split(
                        ':')[0] if ':' in connection_id else 'UNKNOWN'

                websocket = metadata.get('websocket')

                if websocket:
                    # Only send data if we have at least some levels
                    # Don't send empty orderbooks during initial loading
                    bids = aggregated_data.get('bids', [])
                    asks = aggregated_data.get('asks', [])

                    if len(bids) > 0 and len(asks) > 0:
                        # Format for frontend
                        formatted_data = {
                            "type": "orderbook_update",
                            "symbol": symbol_to_send,
                            "bids": bids,
                            "asks": asks,
                            "timestamp": aggregated_data['timestamp'],
                            "rounding": aggregated_data['rounding'],
                            "rounding_options": aggregated_data.get('rounding_options', []),
                            "market_depth_info": aggregated_data.get('market_depth_info', {}),
                            "aggregated": True  # Indicate this is pre-aggregated data
                        }

                        await websocket.send_text(json.dumps(formatted_data))
                    else:
                        # Log once that we're waiting for data
                        logger.debug(
                            f"Waiting for orderbook data for {connection_id} (bids={
                                len(bids)}, asks={
                                len(asks)})")

        except Exception as e:
            logger.error(
                f"Error broadcasting aggregated orderbook for {connection_id}: {e}")

    async def _stream_orderbook(self, symbol: str):
        """Stream order book updates through OrderBook Manager with aggregation."""
        exchange_pro = None
        try:
            logger.info(
                f"Initializing aggregated orderbook stream for {symbol}")
            exchange_pro = exchange_service.get_exchange_pro()

            # Get OrderBook instance from manager
            orderbook = await orderbook_manager.get_orderbook(symbol)
            if not orderbook:
                logger.error(f"No OrderBook instance found for {symbol}")
                return

            # Test connection before starting stream
            if exchange_pro is None:
                logger.warning(
                    f"CCXT Pro not available for {symbol}, using mock data")
                await self._stream_mock_orderbook_aggregated(symbol)
                return

            try:
                # Fetch initial orderbook data with large limit for aggregation
                logger.info(f"Fetching initial orderbook data for {symbol}")
                initial_orderbook_data = await exchange_pro.fetch_order_book(symbol, limit=1000)

                # Convert to OrderBook model format
                bid_levels = [
                    OrderBookLevel(price=float(bid[0]), amount=float(bid[1]))
                    for bid in initial_orderbook_data["bids"]
                    if float(bid[1]) > 0  # Filter zero amounts
                ]

                ask_levels = [
                    OrderBookLevel(price=float(ask[0]), amount=float(ask[1]))
                    for ask in initial_orderbook_data["asks"]
                    if float(ask[1]) > 0  # Filter zero amounts
                ]

                # Create initial snapshot
                import time
                initial_snapshot = OrderBookSnapshot(
                    symbol=symbol,
                    bids=bid_levels,
                    asks=ask_levels,
                    timestamp=initial_orderbook_data.get("timestamp", int(time.time() * 1000))
                )

                # Update orderbook with initial data
                await orderbook.update_snapshot(initial_snapshot)

                # Immediately broadcast aggregated initial data to all connections
                # This will apply each connection's specific limit and rounding
                # parameters
                await self._broadcast_to_all_symbol_connections(symbol)
                logger.info(
                    f"Initial orderbook populated and sent for {symbol} with {
                        len(bid_levels)} bids and {
                        len(ask_levels)} asks")

            except Exception as e:
                logger.error(
                    f"Failed to fetch initial orderbook for {symbol}: {
                        str(e)}")
                logger.info(
                    f"Falling back to mock orderbook data for {symbol}")
                await self._stream_mock_orderbook_aggregated(symbol)
                return

            while symbol in self.active_connections and self.active_connections[symbol]:
                try:
                    # Watch order book updates with large limit for aggregation
                    order_book_data = await exchange_pro.watch_order_book(symbol)

                    # Convert to OrderBook model format
                    bid_levels = [
                        OrderBookLevel(
                            price=float(
                                bid[0]), amount=float(
                                bid[1]))
                        for bid in order_book_data["bids"]
                        if float(bid[1]) > 0  # Filter zero amounts
                    ]

                    ask_levels = [
                        OrderBookLevel(
                            price=float(
                                ask[0]), amount=float(
                                ask[1]))
                        for ask in order_book_data["asks"]
                        if float(ask[1]) > 0  # Filter zero amounts
                    ]

                    # Create snapshot and update OrderBook
                    snapshot = OrderBookSnapshot(
                        symbol=symbol,
                        bids=bid_levels,
                        asks=ask_levels,
                        timestamp=order_book_data["timestamp"]
                    )

                    await orderbook.update_snapshot(snapshot)

                    # Broadcast aggregated data to all connections for this
                    # symbol
                    await self._broadcast_to_all_symbol_connections(symbol)

                    # Pass order book update to trading engine service
                    try:
                        from app.api.v1.endpoints.trading import trading_engine_service_instance
                        await trading_engine_service_instance.process_order_book_update(
                            symbol, order_book_data
                        )
                    except Exception as e:
                        logger.warning(
                            f"Error processing order book update in trading engine for {symbol}: {
                                str(e)}")

                except Exception as e:
                    error_data = {
                        "type": "error",
                        "message": f"Error streaming order book for {symbol}: {
                            str(e)}",
                    }
                    await self.broadcast_to_symbol(symbol, error_data)
                    await asyncio.sleep(5)  # Wait before retrying

        except Exception as e:
            error_data = {
                "type": "error",
                "message": f"Failed to initialize streaming for {symbol}: {
                    str(e)}",
            }
            await self.broadcast_to_symbol(symbol, error_data)
        finally:
            # Do NOT close exchange_pro here. It should be managed globally.
            pass

    async def _broadcast_to_all_symbol_connections(self, symbol: str):
        """Broadcast aggregated orderbook data to all connections for a symbol."""
        try:
            # Get all connection IDs for this symbol
            connection_ids = await orderbook_manager.get_connections_for_symbol(symbol)

            # Broadcast to each connection with their specific aggregation
            # parameters
            for connection_id in connection_ids:
                await self._broadcast_aggregated_orderbook(connection_id)

        except Exception as e:
            logger.error(
                f"Error broadcasting to all connections for {symbol}: {e}")

    async def _stream_mock_orderbook_aggregated(self, symbol: str):
        """Stream mock order book data through OrderBook Manager when CCXT Pro is not available."""
        logger.info(f"Starting mock aggregated orderbook stream for {symbol}")
        import random
        import time

        base_price = 50000.0  # Base price for mock data

        # Get OrderBook instance from manager
        orderbook = await orderbook_manager.get_orderbook(symbol)
        if not orderbook:
            logger.error(
                f"No OrderBook instance found for {symbol} in mock stream")
            return

        while symbol in self.active_connections and self.active_connections[symbol]:
            try:
                # Generate mock orderbook data
                current_time = int(time.time() * 1000)
                price_variation = random.uniform(-0.01, 0.01)  # ±1% variation
                current_price = base_price * (1 + price_variation)

                # Generate comprehensive mock data for aggregation
                bid_levels = []
                ask_levels = []

                for i in range(100):  # Generate 100 levels for aggregation
                    bid_price = current_price - \
                        (i + 1) * random.uniform(0.1, 2.0)
                    ask_price = current_price + \
                        (i + 1) * random.uniform(0.1, 2.0)
                    bid_amount = random.uniform(0.1, 5.0)
                    ask_amount = random.uniform(0.1, 5.0)

                    bid_levels.append(
                        OrderBookLevel(
                            price=bid_price,
                            amount=bid_amount))
                    ask_levels.append(
                        OrderBookLevel(
                            price=ask_price,
                            amount=ask_amount))

                # Create snapshot and update OrderBook
                snapshot = OrderBookSnapshot(
                    symbol=symbol,
                    bids=bid_levels,
                    asks=ask_levels,
                    timestamp=current_time
                )

                await orderbook.update_snapshot(snapshot)

                # Broadcast aggregated data to all connections for this symbol
                await self._broadcast_to_all_symbol_connections(symbol)

                # Wait before next update (simulate real-time updates)
                await asyncio.sleep(1.0)

            except Exception as e:
                logger.error(
                    f"Error in mock aggregated orderbook stream for {symbol}: {
                        str(e)}")
                await asyncio.sleep(5)  # Wait before retrying

        logger.info(f"Mock aggregated orderbook stream ended for {symbol}")

    async def _stream_ticker(self, symbol: str):
        """Stream ticker updates using ccxtpro."""
        exchange_pro = None
        try:
            logger.info(f"Initializing ticker stream for {symbol}")
            exchange_pro = exchange_service.get_exchange_pro()

            # Test connection before starting stream
            if exchange_pro is None:
                logger.warning(
                    f"CCXT Pro not available for {symbol}, using mock data")
                await self._stream_mock_ticker(symbol)
                return

            try:
                await exchange_pro.fetch_ticker(symbol)
                logger.info(
                    f"Exchange connection test successful for ticker {symbol}")
            except Exception as e:
                logger.error(
                    f"Exchange connection test failed for ticker {symbol}: {
                        str(e)}")
                logger.info(f"Falling back to mock ticker data for {symbol}")
                await self._stream_mock_ticker(symbol)
                return

            while symbol in self.active_connections and self.active_connections[symbol]:
                try:
                    # Watch ticker updates
                    ticker_data = await exchange_pro.watch_ticker(symbol)

                    # Use display symbol if available, otherwise use the stream
                    # symbol
                    display_symbol = getattr(self, "_display_symbols", {}).get(
                        symbol, symbol
                    )
                    # Convert to our schema format
                    formatted_data = {
                        "type": "ticker_update",
                        "symbol": display_symbol,
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
                        "message": f"Error streaming ticker for {symbol}: {
                            str(e)}",
                    }
                    await self.broadcast_to_stream(symbol, error_data)
                    await asyncio.sleep(5)  # Wait before retrying

        except Exception as e:
            error_data = {
                "type": "error",
                "message": f"Failed to initialize ticker streaming for {symbol}: {
                    str(e)}",
            }
            await self.broadcast_to_stream(symbol, error_data)
        finally:
            # Do NOT close exchange_pro here. It should be managed globally.
            pass

    async def _stream_candles(
            self,
            symbol: str,
            timeframe: str,
            stream_key: str):
        """Stream candle/OHLCV updates using ccxtpro."""
        exchange_pro = None
        try:
            logger.info(
                f"Initializing candles stream for {symbol}/{timeframe}")
            exchange_pro = exchange_service.get_exchange_pro()

            # Test connection before starting stream
            if exchange_pro is None:
                logger.warning(
                    f"CCXT Pro not available for {symbol}/{timeframe}, using mock data")
                await self._stream_mock_candles(symbol, timeframe, stream_key)
                return

            try:
                await exchange_pro.fetch_ohlcv(
                    symbol, timeframe, limit=1
                )
                logger.info(
                    f"Exchange connection test successful for {symbol}/{timeframe}")
            except Exception as e:
                logger.error(
                    f"Exchange connection test failed for {symbol}/{timeframe}: {str(e)}"
                )
                logger.info(
                    f"Falling back to mock candles data for {symbol}/{timeframe}")
                await self._stream_mock_candles(symbol, timeframe, stream_key)
                return

            while (
                stream_key in self.active_connections
                and self.active_connections[stream_key]
            ):
                try:
                    # CRITICAL: Validate stream is still active before processing
                    if stream_key not in self.active_connections:
                        logger.debug(f"Stream {stream_key} no longer active, stopping candles broadcast")
                        break

                    # Watch OHLCV updates
                    ohlcv_data = await exchange_pro.watch_ohlcv(symbol, timeframe)

                    # CRITICAL: Double-check stream is still active after async operation
                    if stream_key not in self.active_connections:
                        logger.debug(f"Stream {stream_key} disconnected during watch_ohlcv, stopping candles broadcast")
                        break

                    # Convert to our schema format - get the latest candle
                    if ohlcv_data and len(ohlcv_data) > 0:
                        # Get the most recent candle
                        latest_candle = ohlcv_data[-1]

                        # Use display symbol if available, otherwise use the
                        # stream symbol
                        display_symbol = getattr(
                            self, "_display_symbols", {}).get(
                            stream_key, symbol)

                        # Use chart data service for consistent formatting
                        formatted_data = await chart_data_service.prepare_websocket_message(
                            display_symbol, timeframe, latest_candle
                        )

                        if not formatted_data:
                            logger.warning(
                                f"Invalid candle data for {symbol} {timeframe}: {latest_candle}")
                            continue

                        # CRITICAL: Final validation before broadcast - ensure stream still exists
                        if stream_key in self.active_connections and self.active_connections[stream_key]:
                            # Add stream creation timestamp to help frontend filter stale messages
                            import time
                            formatted_data['stream_timestamp'] = int(time.time() * 1000)
                            
                            # Broadcast to all connected clients for this stream
                            await self.broadcast_to_stream(stream_key, formatted_data)
                        else:
                            logger.debug(f"Stream {stream_key} disconnected before broadcast, skipping candle update")

                except Exception as e:
                    error_data = {
                        "type": "error",
                        "message": f"Error streaming candles for {symbol} {timeframe}: {
                            str(e)}",
                    }
                    await self.broadcast_to_stream(stream_key, error_data)
                    await asyncio.sleep(5)  # Wait before retrying

        except Exception as e:
            error_data = {
                "type": "error",
                "message": f"Failed to initialize candle streaming for {symbol} {timeframe}: {
                    str(e)}",
            }
            await self.broadcast_to_stream(stream_key, error_data)
        finally:
            # Do NOT close exchange_pro here. It should be managed globally.
            pass

    async def _stream_mock_candles(
            self,
            symbol: str,
            timeframe: str,
            stream_key: str):
        """Stream mock candle data when CCXT Pro is not available."""
        logger.info(f"Starting mock candles stream for {symbol}/{timeframe}")
        import random
        import time

        base_price = 50000.0
        current_price = base_price

        while (
            stream_key in self.active_connections
            and self.active_connections[stream_key]
        ):
            try:
                # Generate mock candle data
                current_time = int(time.time() * 1000)

                # Simulate price movement
                price_change = random.uniform(-0.005, 0.005)  # ±0.5% change
                current_price *= 1 + price_change

                # Generate OHLCV data
                open_price = current_price
                high_price = current_price * random.uniform(1.0, 1.002)
                low_price = current_price * random.uniform(0.998, 1.0)
                close_price = current_price * random.uniform(0.999, 1.001)
                volume = random.uniform(10.0, 100.0)

                # CRITICAL: Validate stream is still active before broadcast
                if stream_key not in self.active_connections or not self.active_connections[stream_key]:
                    logger.debug(f"Mock candles stream {stream_key} no longer active, stopping")
                    break

                # Use display symbol if available, otherwise use the stream
                # symbol
                display_symbol = getattr(self, "_display_symbols", {}).get(
                    stream_key, symbol
                )
                formatted_data = {
                    "type": "candle_update",
                    "symbol": display_symbol,
                    "timeframe": timeframe,
                    "timestamp": current_time,
                    "open": round(open_price, 2),
                    "high": round(high_price, 2),
                    "low": round(low_price, 2),
                    "close": round(close_price, 2),
                    "volume": round(volume, 4),
                    "mock": True,  # Indicate this is mock data
                    "stream_timestamp": current_time,  # Add stream timestamp for filtering
                }

                # Broadcast to all connected clients for this stream
                await self.broadcast_to_stream(stream_key, formatted_data)

                # Wait before next update
                await asyncio.sleep(2.0)

            except Exception as e:
                logger.error(
                    f"Error in mock candles stream for {symbol}/{timeframe}: {str(e)}"
                )
                await asyncio.sleep(5)  # Wait before retrying

        logger.info(f"Mock candles stream ended for {symbol}/{timeframe}")

    async def _stream_mock_ticker(self, symbol: str):
        """Stream mock ticker data when CCXT Pro is not available."""
        logger.info(f"Starting mock ticker stream for {symbol}")
        import random
        import time

        base_price = 50000.0  # Base price for mock data
        current_price = base_price

        while symbol in self.active_connections and self.active_connections[symbol]:
            try:
                # Generate mock ticker data
                current_time = int(time.time() * 1000)

                # Simulate price movement
                price_change = random.uniform(-0.005, 0.005)  # ±0.5% change
                current_price *= 1 + price_change

                # Generate ticker data
                last_price = current_price
                bid_price = current_price * random.uniform(0.9995, 0.9999)
                ask_price = current_price * random.uniform(1.0001, 1.0005)
                high_price = current_price * random.uniform(1.0, 1.02)
                low_price = current_price * random.uniform(0.98, 1.0)
                open_price = current_price * random.uniform(0.99, 1.01)
                close_price = current_price
                change = close_price - open_price
                percentage = (change / open_price) * \
                    100 if open_price > 0 else 0
                volume = random.uniform(100.0, 1000.0)
                quote_volume = volume * current_price

                # Use display symbol if available, otherwise use the stream
                # symbol
                display_symbol = getattr(self, "_display_symbols", {}).get(
                    symbol, symbol
                )
                formatted_data = {
                    "type": "ticker_update",
                    "symbol": display_symbol,
                    "last": round(last_price, 2),
                    "bid": round(bid_price, 2),
                    "ask": round(ask_price, 2),
                    "high": round(high_price, 2),
                    "low": round(low_price, 2),
                    "open": round(open_price, 2),
                    "close": round(close_price, 2),
                    "change": round(change, 2),
                    "percentage": round(percentage, 4),
                    "volume": round(volume, 4),
                    "quote_volume": round(quote_volume, 2),
                    "timestamp": current_time,
                    "mock": True,  # Indicate this is mock data
                }

                # Broadcast to all connected clients for this symbol
                await self.broadcast_to_stream(symbol, formatted_data)

                # Wait before next update (simulate real-time updates)
                await asyncio.sleep(1.5)

            except Exception as e:
                logger.error(
                    f"Error in mock ticker stream for {symbol}: {
                        str(e)}")
                await asyncio.sleep(5)  # Wait before retrying

        logger.info(f"Mock ticker stream ended for {symbol}")

    async def _restart_orderbook_stream(self, symbol: str):
        """Restart orderbook stream with updated limit."""
        logger.info(f"Restarting orderbook stream for {symbol} with new limit")

        # Stop the current streaming task if it exists
        if symbol in self.streaming_tasks:
            logger.info(f"Stopping existing orderbook task for {symbol}")
            self._stop_streaming(symbol)

        # Start new streaming task with updated limit
        if symbol in self.active_connections and self.active_connections[symbol]:
            logger.info(f"Starting new orderbook task for {symbol}")
            await self._start_streaming(symbol, "orderbook")


# Global connection manager instance
connection_manager = ConnectionManager()
