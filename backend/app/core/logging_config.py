import logging
import sys
from typing import Dict, Any


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """
    Configure and setup application logging.

    Args:
        log_level: The logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Returns:
        logging.Logger: Configured logger instance
    """
    # Create formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    # Get root logger
    logger = logging.getLogger("trading_bot")
    logger.setLevel(getattr(logging, log_level.upper()))

    # Clear any existing handlers to avoid duplicates
    logger.handlers.clear()

    # Add console handler
    logger.addHandler(console_handler)

    # Prevent propagation to root logger to avoid duplicate logs
    logger.propagate = False

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.

    Args:
        name: The name of the module/logger

    Returns:
        logging.Logger: Logger instance
    """
    return logging.getLogger(f"trading_bot.{name}")


# Configure logging for external libraries
def configure_external_loggers():
    """Configure logging levels for external libraries to reduce noise."""
    # Reduce ccxt logging noise
    logging.getLogger("ccxt").setLevel(logging.WARNING)

    # Reduce websocket logging noise
    logging.getLogger("websockets").setLevel(logging.WARNING)

    # Reduce urllib3 logging noise
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    # Reduce httpx logging noise (used by FastAPI)
    logging.getLogger("httpx").setLevel(logging.WARNING)
