"""
Liquidation Service for Binance Futures Liquidation Streams

This service handles direct WebSocket connections to Binance futures liquidation streams
since CCXT Pro doesn't support liquidation order streams.
"""

import asyncio
import json
import websockets
from typing import Optional, Dict, List, Callable, Any
from datetime import datetime
import logging
from decimal import Decimal

logger = logging.getLogger(__name__)

class LiquidationService:
    """Service for connecting to Binance liquidation streams"""
    
    def __init__(self):
        self.base_url = "wss://fstream.binance.com"
        self.active_connections: Dict[str, asyncio.Task] = {}
        self.data_callbacks: Dict[str, List[Callable]] = {}
        self.running_streams: Dict[str, bool] = {}
        self.retry_delays = [1, 2, 5, 10, 30]  # Exponential backoff
        
    async def connect_to_liquidation_stream(self, symbol: str, callback: Callable[[Dict], Any]):
        """
        Connect to Binance liquidation stream for a specific symbol
        
        Args:
            symbol: Trading symbol (e.g., 'BTCUSDT')
            callback: Callback function to handle liquidation data
        """
        # Convert symbol to lowercase for Binance
        stream_symbol = symbol.lower()
        stream_url = f"{self.base_url}/ws/{stream_symbol}@forceOrder"
        
        # Register callback
        if symbol not in self.data_callbacks:
            self.data_callbacks[symbol] = []
        self.data_callbacks[symbol].append(callback)
        
        # If already connected, just add callback
        if symbol in self.active_connections:
            logger.info(f"Already connected to {symbol} liquidation stream")
            return
            
        # Start new connection
        self.running_streams[symbol] = True
        task = asyncio.create_task(self._maintain_connection(symbol, stream_url))
        self.active_connections[symbol] = task
        
    async def _maintain_connection(self, symbol: str, stream_url: str):
        """Maintain WebSocket connection with reconnection logic"""
        retry_count = 0
        
        while self.running_streams.get(symbol, False):
            try:
                await self._connect_and_listen(symbol, stream_url)
                retry_count = 0  # Reset on successful connection
                
            except Exception as e:
                logger.error(f"Liquidation stream error for {symbol}: {e}")
                
                if not self.running_streams.get(symbol, False):
                    break
                    
                # Exponential backoff
                delay = self.retry_delays[min(retry_count, len(self.retry_delays) - 1)]
                logger.info(f"Reconnecting {symbol} liquidation stream in {delay}s...")
                await asyncio.sleep(delay)
                retry_count += 1
                
    async def _connect_and_listen(self, symbol: str, stream_url: str):
        """Connect to WebSocket and listen for messages"""
        logger.info(f"Connecting to liquidation stream: {stream_url}")
        
        async with websockets.connect(stream_url) as websocket:
            logger.info(f"Connected to {symbol} liquidation stream")
            
            # Create ping task
            ping_task = asyncio.create_task(self._send_pings(websocket))
            
            try:
                while self.running_streams.get(symbol, False):
                    try:
                        # Wait for message with timeout
                        message = await asyncio.wait_for(websocket.recv(), timeout=30)
                        data = json.loads(message)
                        
                        # Process liquidation data
                        if data.get('e') == 'forceOrder':
                            formatted_data = self.format_liquidation_data(data, symbol)
                            await self._notify_callbacks(symbol, formatted_data)
                            
                    except asyncio.TimeoutError:
                        # No message in 30 seconds, continue
                        continue
                        
                    except websockets.ConnectionClosed:
                        logger.warning(f"WebSocket connection closed for {symbol}")
                        break
                        
            finally:
                ping_task.cancel()
                try:
                    await ping_task
                except asyncio.CancelledError:
                    pass
                    
    async def _send_pings(self, websocket):
        """Send periodic pings to keep connection alive"""
        try:
            while True:
                await asyncio.sleep(180)  # 3 minutes
                await websocket.ping()
                logger.debug("Sent ping to keep connection alive")
        except asyncio.CancelledError:
            pass
            
    def format_liquidation_data(self, raw_data: Dict, display_symbol: str) -> Dict:
        """
        Format liquidation data for frontend display
        
        Expected output format:
        {
            "symbol": "BTCUSDT",
            "side": "SELL",
            "quantity": "0.014",
            "quantityFormatted": "0.014000",
            "priceUsdt": "138.74",
            "priceUsdtFormatted": "138.74",
            "timestamp": 1568014460893,
            "displayTime": "14:27:40",
            "avgPrice": "9910"
        }
        
        Args:
            raw_data: Raw liquidation message from Binance
            display_symbol: Symbol for display purposes
            
        Returns:
            Formatted liquidation data for frontend
        """
        order = raw_data.get('o', {})
        
        # Extract data
        side = order.get('S', 'UNKNOWN')
        quantity = Decimal(order.get('z', '0'))  # Filled Accumulated Quantity
        avg_price = Decimal(order.get('ap', '0'))  # Average Price
        timestamp = raw_data.get('E', 0)
        
        # Calculate total value in USDT
        price_usdt = quantity * avg_price
        
        # Format timestamp
        dt = datetime.fromtimestamp(timestamp / 1000)
        display_time = dt.strftime('%H:%M:%S')
        
        # Format numbers
        if quantity >= 1:
            quantity_formatted = f"{quantity:.3f}"
        else:
            quantity_formatted = f"{quantity:.6f}"
            
        if price_usdt >= 1000:
            price_formatted = f"{price_usdt:,.2f}"
        else:
            price_formatted = f"{price_usdt:.2f}"
        
        return {
            "symbol": display_symbol,
            "side": side,
            "quantity": str(quantity),
            "quantityFormatted": quantity_formatted,
            "priceUsdt": str(price_usdt),
            "priceUsdtFormatted": price_formatted,
            "timestamp": timestamp,
            "displayTime": display_time,
            "avgPrice": str(avg_price)
        }
        
    async def _notify_callbacks(self, symbol: str, data: Dict):
        """Notify all registered callbacks with new data"""
        callbacks = self.data_callbacks.get(symbol, [])
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data)
                else:
                    callback(data)
            except Exception as e:
                logger.error(f"Error in liquidation callback: {e}")
                
    async def disconnect_stream(self, symbol: str):
        """
        Disconnect from liquidation stream
        
        Args:
            symbol: Trading symbol to disconnect
        """
        logger.info(f"Disconnecting liquidation stream for {symbol}")
        
        # Stop the stream
        self.running_streams[symbol] = False
        
        # Cancel the connection task
        if symbol in self.active_connections:
            task = self.active_connections[symbol]
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            del self.active_connections[symbol]
            
        # Clear callbacks
        if symbol in self.data_callbacks:
            del self.data_callbacks[symbol]
            
    async def disconnect_all(self):
        """Disconnect all active streams"""
        symbols = list(self.active_connections.keys())
        for symbol in symbols:
            await self.disconnect_stream(symbol)

# Singleton instance
liquidation_service = LiquidationService()