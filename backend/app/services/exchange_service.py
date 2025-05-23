import ccxt
import ccxtpro
from typing import Optional, Dict, Any
from backend.app.core.config import settings

class ExchangeService:
    """Service for managing CCXT exchange connections and operations."""
    
    def __init__(self):
        self.exchange: Optional[ccxt.binance] = None
        self.exchange_pro: Optional[ccxtpro.binance] = None
    
    def initialize_exchange(self) -> ccxt.binance:
        """
        Initialize the CCXT Binance exchange instance for REST API calls.
        
        Returns:
            ccxt.binance: Initialized Binance exchange instance
            
        Raises:
            Exception: If API keys are missing or initialization fails
        """
        try:
            if not settings.BINANCE_API_KEY or not settings.BINANCE_SECRET_KEY:
                raise ValueError("Binance API keys are required but not found in environment variables")
            
            self.exchange = ccxt.binance({
                'apiKey': settings.BINANCE_API_KEY,
                'secret': settings.BINANCE_SECRET_KEY,
                'sandbox': settings.DEBUG,  # Use sandbox in debug mode
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'future',  # Use futures by default
                }
            })
            
            print(f"CCXT Binance exchange initialized successfully (sandbox: {settings.DEBUG})")
            return self.exchange
            
        except Exception as e:
            print(f"Error initializing CCXT exchange: {str(e)}")
            raise
    
    def initialize_exchange_pro(self) -> ccxtpro.binance:
        """
        Initialize the CCXT Pro Binance exchange instance for WebSocket connections.
        
        Returns:
            ccxtpro.binance: Initialized Binance Pro exchange instance
            
        Raises:
            Exception: If API keys are missing or initialization fails
        """
        try:
            if not settings.BINANCE_API_KEY or not settings.BINANCE_SECRET_KEY:
                raise ValueError("Binance API keys are required but not found in environment variables")
            
            self.exchange_pro = ccxtpro.binance({
                'apiKey': settings.BINANCE_API_KEY,
                'secret': settings.BINANCE_SECRET_KEY,
                'sandbox': settings.DEBUG,  # Use sandbox in debug mode
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'future',  # Use futures by default
                }
            })
            
            print(f"CCXT Pro Binance exchange initialized successfully (sandbox: {settings.DEBUG})")
            return self.exchange_pro
            
        except Exception as e:
            print(f"Error initializing CCXT Pro exchange: {str(e)}")
            raise
    
    def get_exchange(self) -> ccxt.binance:
        """
        Get the initialized CCXT exchange instance, initializing if necessary.
        
        Returns:
            ccxt.binance: The exchange instance
        """
        if self.exchange is None:
            self.initialize_exchange()
        return self.exchange
    
    def get_exchange_pro(self) -> ccxtpro.binance:
        """
        Get the initialized CCXT Pro exchange instance, initializing if necessary.
        
        Returns:
            ccxtpro.binance: The exchange pro instance
        """
        if self.exchange_pro is None:
            self.initialize_exchange_pro()
        return self.exchange_pro
    
    async def test_connection(self) -> Dict[str, Any]:
        """
        Test the connection to Binance API.
        
        Returns:
            Dict[str, Any]: Connection test results
        """
        try:
            exchange = self.get_exchange()
            # Test connection by fetching exchange status
            status = await exchange.fetch_status()
            return {
                "status": "success",
                "exchange_status": status,
                "message": "Connection to Binance API successful"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to connect to Binance API: {str(e)}"
            }

# Create global exchange service instance
exchange_service = ExchangeService()