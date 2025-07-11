"""
Liquidation Service for Binance Futures Liquidation Streams

This service handles direct WebSocket connections to Binance futures liquidation streams
since CCXT Pro doesn't support liquidation order streams.
"""

import asyncio
import json
import websockets
import aiohttp
from typing import Optional, Dict, List, Callable, Any
from datetime import datetime
import logging
from decimal import Decimal
from app.services.formatting_service import formatting_service
from app.core.config import settings

logger = logging.getLogger(__name__)

class LiquidationService:
    """Service for connecting to Binance liquidation streams"""
    
    def __init__(self):
        self.base_url = settings.BINANCE_WS_BASE_URL
        self.active_connections: Dict[str, asyncio.Task] = {}
        self.data_callbacks: Dict[str, List[Callable]] = {}
        self.running_streams: Dict[str, bool] = {}
        self.retry_delays = [1, 2, 5, 10, 30]  # Exponential backoff
        self.symbol_info_cache: Dict[str, Optional[Dict]] = {}  # Store symbol info per symbol
        self._http_session: Optional[aiohttp.ClientSession] = None
        
    async def connect_to_liquidation_stream(self, symbol: str, callback: Callable[[Dict], Any], symbol_info: Optional[Dict] = None):
        """
        Connect to Binance liquidation stream for a specific symbol
        
        Args:
            symbol: Trading symbol (e.g., 'BTCUSDT')
            callback: Callback function to handle liquidation data
            symbol_info: Optional symbol information for formatting
        """
        # Convert symbol to lowercase for Binance
        stream_symbol = symbol.lower()
        stream_url = f"{self.base_url}/ws/{stream_symbol}@forceOrder"
        
        # Register callback
        if symbol not in self.data_callbacks:
            self.data_callbacks[symbol] = []
        self.data_callbacks[symbol].append(callback)
        
        # Store symbol info
        self.symbol_info_cache[symbol] = symbol_info
        
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
                            symbol_info = self.symbol_info_cache.get(symbol)
                            formatted_data = self.format_liquidation_data(data, symbol, symbol_info)
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
            
    def format_liquidation_data(self, raw_data: Dict, display_symbol: str, symbol_info: Optional[Dict] = None) -> Dict:
        """
        Format liquidation data for frontend display
        
        Expected output format:
        {
            "symbol": "BTCUSDT",
            "side": "SELL",
            "quantity": "0.014",
            "quantityFormatted": "0.014000",
            "priceUsdt": "138.74",
            "priceUsdtFormatted": "138",
            "timestamp": 1568014460893,
            "displayTime": "14:27:40",
            "avgPrice": "9910",
            "baseAsset": "BTC"
        }
        
        Args:
            raw_data: Raw liquidation message from Binance
            display_symbol: Symbol for display purposes
            symbol_info: Optional symbol information for formatting
            
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
        if symbol_info:
            quantity_formatted = formatting_service.format_amount(float(quantity), symbol_info)
        else:
            # Fallback to existing logic if no symbol info
            if quantity >= 1:
                quantity_formatted = f"{quantity:.3f}"
            else:
                quantity_formatted = f"{quantity:.6f}"
            
        # Format price to whole USDT with thousand separators
        price_formatted = f"{int(round(float(price_usdt))):,}"
        
        return {
            "symbol": display_symbol,
            "side": side,
            "quantity": str(quantity),
            "quantityFormatted": quantity_formatted,
            "priceUsdt": str(price_usdt),
            "priceUsdtFormatted": price_formatted,
            "timestamp": timestamp,
            "displayTime": display_time,
            "avgPrice": str(avg_price),
            "baseAsset": symbol_info.get('baseAsset', '') if symbol_info else ''
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
    
    async def _get_http_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session for API calls"""
        if not self._http_session:
            self._http_session = aiohttp.ClientSession()
        return self._http_session
    
    async def fetch_historical_liquidations(self, symbol: str, limit: int = 50) -> List[Dict]:
        """
        Fetch historical liquidations from external API
        
        Args:
            symbol: Trading symbol (e.g., 'BTCUSDT')
            limit: Maximum number of liquidations to fetch
            
        Returns:
            List of formatted liquidation data dictionaries
        """
        if not settings.LIQUIDATION_API_BASE_URL:
            logger.warning("LIQUIDATION_API_BASE_URL not configured, returning empty list")
            return []
        
        try:
            session = await self._get_http_session()
            url = f"{settings.LIQUIDATION_API_BASE_URL}/liquidation-orders"
            params = {"symbol": symbol.upper(), "limit": limit}
            
            async with session.get(url, params=params, timeout=15) as response:
                if response.status != 200:
                    logger.warning(f"Liquidation API returned status {response.status} for {symbol}")
                    return []
                
                data = await response.json()
                
                # Get symbol info for formatting
                symbol_info = self.symbol_info_cache.get(symbol)
                
                # Convert API format to our WebSocket format
                return [self._convert_api_to_ws_format(item, symbol, symbol_info) for item in data]
                
        except asyncio.TimeoutError:
            logger.error(f"Timeout fetching historical liquidations for {symbol}")
            return []
        except Exception as e:
            logger.error(f"Failed to fetch historical liquidations for {symbol}: {e}")
            return []
    
    def _convert_api_to_ws_format(self, api_data: Dict, display_symbol: str, symbol_info: Optional[Dict] = None) -> Dict:
        """
        Convert API response format to match WebSocket format
        
        Args:
            api_data: Liquidation data from API
            display_symbol: Symbol for display
            symbol_info: Optional symbol information for formatting
            
        Returns:
            Formatted liquidation data matching WebSocket format
        """
        # Calculate USDT value using filled quantity
        quantity = Decimal(api_data.get("order_filled_accumulated_quantity", "0"))
        avg_price = Decimal(api_data.get("average_price", "0"))
        amount_usdt = quantity * avg_price
        
        # Convert timestamp
        timestamp = api_data.get("order_trade_time", 0)
        dt = datetime.fromtimestamp(timestamp / 1000)
        display_time = dt.strftime('%H:%M:%S')
        
        # Format quantity
        if symbol_info:
            quantity_formatted = formatting_service.format_amount(float(quantity), symbol_info)
        else:
            # Fallback formatting
            if quantity >= 1:
                quantity_formatted = f"{quantity:.3f}"
            else:
                quantity_formatted = f"{quantity:.6f}"
        
        # Format price to whole USDT with thousand separators
        price_formatted = f"{int(round(float(amount_usdt))):,}"
        
        return {
            "symbol": display_symbol,
            "side": api_data.get("side", "").upper(),  # API returns lowercase
            "quantity": str(quantity),
            "quantityFormatted": quantity_formatted,
            "priceUsdt": str(amount_usdt),
            "priceUsdtFormatted": price_formatted,
            "timestamp": timestamp,
            "displayTime": display_time,
            "avgPrice": str(avg_price),
            "baseAsset": symbol_info.get('baseAsset', '') if symbol_info else ''
        }
                
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
            
        # Clear symbol info cache
        if symbol in self.symbol_info_cache:
            del self.symbol_info_cache[symbol]
            
    async def disconnect_all(self):
        """Disconnect all active streams"""
        symbols = list(self.active_connections.keys())
        for symbol in symbols:
            await self.disconnect_stream(symbol)
        
        # Close HTTP session if it exists
        if self._http_session:
            await self._http_session.close()
            self._http_session = None

# Singleton instance
liquidation_service = LiquidationService()