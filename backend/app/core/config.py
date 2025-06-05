import os
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

    # Binance API Configuration
    BINANCE_API_KEY: Optional[str] = os.getenv("BINANCE_API_KEY")
    BINANCE_SECRET_KEY: Optional[str] = os.getenv("BINANCE_SECRET_KEY")

    # Firebase Configuration
    FIREBASE_CONFIG_JSON: Optional[str] = os.getenv("FIREBASE_CONFIG_JSON")

    # API Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Trading Bot API"

    # Market Data Configuration
    MAX_ORDERBOOK_LIMIT: int = int(os.getenv("MAX_ORDERBOOK_LIMIT", "1000"))

    # Development settings
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"

    def __init__(self):
        """Initialize settings and validate required environment variables."""
        # Enhanced validation with better logging
        if not self.BINANCE_API_KEY:
            print("Warning: BINANCE_API_KEY not found in environment variables")
            print(
                f"Available env vars: {[k for k in os.environ.keys() if 'BINANCE' in k]}"
            )
        else:
            print(f"BINANCE_API_KEY loaded: {self.BINANCE_API_KEY[:8]}...")

        if not self.BINANCE_SECRET_KEY:
            print("Warning: BINANCE_SECRET_KEY not found in environment variables")
        else:
            print(f"BINANCE_SECRET_KEY loaded: {self.BINANCE_SECRET_KEY[:8]}...")


# Create global settings instance
settings = Settings()
