import os
import logging
from typing import Optional
from dotenv import load_dotenv

# Try multiple locations for .env file
env_paths = [
    ".env",  # Current directory
    "../.env",  # Parent directory (if running from backend/)
    "../../.env",  # Grandparent directory (if running from backend/app/)
]

env_loaded = False
for env_path in env_paths:
    if os.path.exists(env_path):
        load_dotenv(env_path)
        env_loaded = True
        print(f"Loaded environment variables from: {env_path}")
        break

if not env_loaded:
    print("Warning: No .env file found in expected locations")


class Settings:
    """Application settings loaded from environment variables."""

    # Container Detection
    DEVCONTAINER_MODE: bool = os.getenv(
        "DEVCONTAINER_MODE", "False").lower() == "true"
    IN_CONTAINER: bool = os.path.exists(
        "/.dockerenv") or os.getenv("CONTAINER", "False").lower() == "true"

    # Host Configuration
    HOST: str = "0.0.0.0" if DEVCONTAINER_MODE or IN_CONTAINER else "127.0.0.1"
    PORT: int = int(os.getenv("FASTAPI_PORT", os.getenv("PORT", "8000")))

    # Binance API Configuration
    BINANCE_API_KEY: Optional[str] = os.getenv("BINANCE_API_KEY")
    BINANCE_SECRET_KEY: Optional[str] = os.getenv("BINANCE_SECRET_KEY")
    BINANCE_WS_BASE_URL: str = os.getenv(
        "BINANCE_WS_BASE_URL",
        "wss://fstream.binance.com")
    BINANCE_API_BASE_URL: str = os.getenv(
        "BINANCE_API_BASE_URL", "https://fapi.binance.com")

    # Liquidation API Configuration
    LIQUIDATION_API_BASE_URL: Optional[str] = os.getenv("LIQUIDATION_API_BASE_URL", "")

    # Firebase Configuration
    FIREBASE_CONFIG_JSON: Optional[str] = os.getenv("FIREBASE_CONFIG_JSON")

    # API Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Trading Bot API"

    # Market Data Configuration
    MAX_ORDERBOOK_LIMIT: int = int(os.getenv("MAX_ORDERBOOK_LIMIT", "5000"))

    # Development settings
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    DEVELOPMENT: bool = os.getenv(
        "NODE_ENV", "production") == "development" or DEBUG
    AUTO_RELOAD: bool = DEVELOPMENT and (DEVCONTAINER_MODE or IN_CONTAINER)

    # Logging Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "DEBUG" if DEBUG else "INFO")
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    CONSOLE_LOGGING: bool = os.getenv(
        "CONSOLE_LOGGING", "True").lower() == "true"
    REQUEST_LOGGING: bool = DEBUG and os.getenv(
        "REQUEST_LOGGING", "True").lower() == "true"

    # Static Files Configuration (for development)
    SERVE_STATIC_FILES: bool = DEVELOPMENT and os.getenv(
        "SERVE_STATIC_FILES", "True").lower() == "true"
    STATIC_FILES_PATH: str = os.getenv(
        "STATIC_FILES_PATH", "../frontend_vanilla/dist")

    # CORS Configuration
    CORS_ORIGINS: list = (
        os.getenv("CORS_ORIGINS",
                  "http://localhost:3000,http://127.0.0.1:3000,http://0.0.0.0:3000,http://localhost:8080,http://127.0.0.1:8080,http://0.0.0.0:8080"
                  if DEVELOPMENT else "").split(",")
        if os.getenv("CORS_ORIGINS") or DEVELOPMENT
        else []
    )

    # WebSocket Configuration
    WS_HEARTBEAT_INTERVAL: int = int(os.getenv("WS_HEARTBEAT_INTERVAL", "30"))
    WS_TIMEOUT: int = int(os.getenv("WS_TIMEOUT", "60"))

    def __init__(self):
        """Initialize settings and validate required environment variables."""
        self.BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
        self.BINANCE_SECRET_KEY = os.getenv("BINANCE_SECRET_KEY")

        # Configure logging
        self._configure_logging()

        # Log container detection info
        if self.DEVCONTAINER_MODE:
            logging.info("Running in VS Code Dev Container mode")
        elif self.IN_CONTAINER:
            logging.info("Running in container environment")
        else:
            logging.info("Running in local development mode")

        logging.info(f"Server will bind to {self.HOST}:{self.PORT}")
        logging.info(f"Debug mode: {self.DEBUG}")
        logging.info(f"Development mode: {self.DEVELOPMENT}")

        # Validate required environment variables
        if not self.BINANCE_API_KEY:
            logging.warning(
                "BINANCE_API_KEY not found in environment variables")
        if not self.BINANCE_SECRET_KEY:
            logging.warning(
                "BINANCE_SECRET_KEY not found in environment variables")
        
        # Log liquidation API configuration
        if self.LIQUIDATION_API_BASE_URL:
            logging.info(f"Liquidation API configured: {self.LIQUIDATION_API_BASE_URL}")
        else:
            logging.warning("LIQUIDATION_API_BASE_URL not set - historical liquidations disabled")

    def _configure_logging(self):
        """Configure logging based on environment settings."""
        # Set log level
        log_level = getattr(logging, self.LOG_LEVEL.upper(), logging.INFO)

        # Configure root logger
        logging.basicConfig(
            level=log_level,
            format=self.LOG_FORMAT,
            force=True  # Override any existing configuration
        )

        # Configure console handler if needed
        if self.CONSOLE_LOGGING:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(log_level)
            formatter = logging.Formatter(self.LOG_FORMAT)
            console_handler.setFormatter(formatter)

            # Add handler to root logger if not already present
            root_logger = logging.getLogger()
            if not any(isinstance(h, logging.StreamHandler)
                       for h in root_logger.handlers):
                root_logger.addHandler(console_handler)

        # Set specific logger levels for noisy libraries in development
        if self.DEBUG:
            logging.getLogger("uvicorn").setLevel(logging.INFO)
            logging.getLogger("uvicorn.access").setLevel(
                logging.INFO if self.REQUEST_LOGGING else logging.WARNING)
            logging.getLogger("websockets").setLevel(logging.INFO)
        else:
            # Production: reduce noise
            logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
            logging.getLogger("websockets").setLevel(logging.WARNING)


# Create global settings instance
settings = Settings()

# Export commonly used values for convenience
DEBUG = settings.DEBUG
DEVELOPMENT = settings.DEVELOPMENT
DEVCONTAINER_MODE = settings.DEVCONTAINER_MODE
IN_CONTAINER = settings.IN_CONTAINER
