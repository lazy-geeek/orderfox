import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

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
    
    # Development settings
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    def __init__(self):
        """Initialize settings and validate required environment variables."""
        if not self.BINANCE_API_KEY:
            print("Warning: BINANCE_API_KEY not found in environment variables")
        if not self.BINANCE_SECRET_KEY:
            print("Warning: BINANCE_SECRET_KEY not found in environment variables")

# Create global settings instance
settings = Settings()