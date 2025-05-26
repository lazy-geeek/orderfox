import ccxt
import ccxtpro
from typing import Optional, Dict, Any
from fastapi import HTTPException
from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger("exchange_service")


class ExchangeService:
    """Service for managing CCXT exchange connections and operations."""

    def __init__(self):
        self.exchange: Optional[ccxt.Exchange] = None
        self.exchange_pro: Optional[Any] = None

    def initialize_exchange(self) -> ccxt.Exchange:
        """
        Initialize the CCXT Binance exchange instance for REST API calls.

        Returns:
            ccxt.Exchange: Initialized Binance exchange instance

        Raises:
            HTTPException: If API keys are missing or initialization fails
        """
        try:
            logger.info("Initializing CCXT Binance exchange...")

            if not settings.BINANCE_API_KEY or not settings.BINANCE_SECRET_KEY:
                logger.warning("Binance API keys not found - initializing in demo mode")
                # Initialize exchange without API keys for demo/public endpoints
                self.exchange = ccxt.binance(
                    {
                        "sandbox": True,  # Always use sandbox for demo mode
                        "enableRateLimit": True,
                        "options": {
                            "defaultType": "future",  # Use futures by default
                        },
                    }
                )
            else:
                self.exchange = ccxt.binance(
                    {
                        "apiKey": settings.BINANCE_API_KEY,
                        "secret": settings.BINANCE_SECRET_KEY,
                        "sandbox": settings.DEBUG,  # Use sandbox in debug mode
                        "enableRateLimit": True,
                        "options": {
                            "defaultType": "future",  # Use futures by default
                        },
                    }
                )

            logger.info(
                f"CCXT Binance exchange initialized successfully (sandbox: {settings.DEBUG})"
            )
            return self.exchange

        except HTTPException:
            raise
        except ccxt.NetworkError as e:
            logger.error(f"Network error initializing CCXT exchange: {str(e)}")
            raise HTTPException(status_code=503, detail="Exchange network error")
        except ccxt.ExchangeError as e:
            logger.error(f"Exchange error initializing CCXT exchange: {str(e)}")
            raise HTTPException(status_code=502, detail="Exchange API error")
        except Exception as e:
            logger.error(
                f"Unexpected error initializing CCXT exchange: {str(e)}", exc_info=True
            )
            raise HTTPException(
                status_code=500, detail="Exchange initialization failed"
            )

    def initialize_exchange_pro(self) -> Any:
        """
        Initialize the CCXT Pro Binance exchange instance for WebSocket connections.

        Returns:
            Any: Initialized Binance Pro exchange instance

        Raises:
            HTTPException: If API keys are missing or initialization fails
        """
        try:
            logger.info("Initializing CCXT Pro Binance exchange...")

            if not settings.BINANCE_API_KEY or not settings.BINANCE_SECRET_KEY:
                logger.warning(
                    "Binance API keys not found - initializing Pro exchange in demo mode"
                )
                # Initialize exchange without API keys for demo/public endpoints
                self.exchange_pro = ccxtpro.binance(
                    {
                        "sandbox": True,  # Always use sandbox for demo mode
                        "enableRateLimit": True,
                        "options": {
                            "defaultType": "future",  # Use futures by default
                        },
                    }
                )
            else:
                self.exchange_pro = ccxtpro.binance(
                    {
                        "apiKey": settings.BINANCE_API_KEY,
                        "secret": settings.BINANCE_SECRET_KEY,
                        "sandbox": settings.DEBUG,  # Use sandbox in debug mode
                        "enableRateLimit": True,
                        "options": {
                            "defaultType": "future",  # Use futures by default
                        },
                    }
                )

            logger.info(
                f"CCXT Pro Binance exchange initialized successfully (sandbox: {settings.DEBUG})"
            )
            return self.exchange_pro

        except HTTPException:
            raise
        except ccxt.NetworkError as e:
            logger.error(f"Network error initializing CCXT Pro exchange: {str(e)}")
            raise HTTPException(status_code=503, detail="Exchange network error")
        except ccxt.ExchangeError as e:
            logger.error(f"Exchange error initializing CCXT Pro exchange: {str(e)}")
            raise HTTPException(status_code=502, detail="Exchange API error")
        except Exception as e:
            logger.error(
                f"Unexpected error initializing CCXT Pro exchange: {str(e)}",
                exc_info=True,
            )
            raise HTTPException(
                status_code=500, detail="Exchange initialization failed"
            )

    def get_exchange(self) -> ccxt.Exchange:
        """
        Get the initialized CCXT exchange instance, initializing if necessary.

        Returns:
            ccxt.Exchange: The exchange instance
        """
        if self.exchange is None:
            self.initialize_exchange()
        return self.exchange

    def get_exchange_pro(self) -> Any:
        """
        Get the initialized CCXT Pro exchange instance, initializing if necessary.

        Returns:
            Any: The exchange pro instance
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
            logger.info("Testing connection to Binance API...")
            exchange = self.get_exchange()

            # Test connection by fetching exchange status
            status = await exchange.fetch_status()

            logger.info("Connection to Binance API successful")
            return {
                "status": "success",
                "exchange_status": status,
                "message": "Connection to Binance API successful",
            }
        except ccxt.NetworkError as e:
            logger.error(f"Network error testing Binance API connection: {str(e)}")
            return {
                "status": "error",
                "message": "Network error connecting to Binance API",
            }
        except ccxt.ExchangeError as e:
            logger.error(f"Exchange error testing Binance API connection: {str(e)}")
            return {
                "status": "error",
                "message": "Exchange API error",
            }
        except HTTPException as e:
            logger.error(f"HTTP error testing Binance API connection: {str(e.detail)}")
            return {
                "status": "error",
                "message": e.detail,
            }
        except Exception as e:
            logger.error(
                f"Unexpected error testing Binance API connection: {str(e)}",
                exc_info=True,
            )
            return {
                "status": "error",
                "message": "Failed to connect to Binance API",
            }


# Create global exchange service instance
exchange_service = ExchangeService()
