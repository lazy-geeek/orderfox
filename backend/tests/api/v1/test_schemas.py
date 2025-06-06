"""
Unit tests for Pydantic schemas.

Tests the validation, serialization, and error handling
of all schema models defined in schemas.py.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError
from app.api.v1.schemas import SymbolInfo, OrderBookLevel, OrderBook, Candle


class TestSymbolInfo:
    """Test cases for SymbolInfo schema."""

    def test_symbol_info_valid_creation(self):
        """Test expected use: creating a valid SymbolInfo instance."""
        symbol_data = {
            "symbol": "BTC/USDT",
            "baseAsset": "BTC",
            "quoteAsset": "USDT",
            "exchange": "binance",
            "pricePrecision": 8,
        }

        symbol_info = SymbolInfo(**symbol_data)

        assert symbol_info.symbol == "BTC/USDT"
        assert symbol_info.baseAsset == "BTC"
        assert symbol_info.quoteAsset == "USDT"
        assert symbol_info.exchange == "binance"
        assert symbol_info.pricePrecision == 8
        assert isinstance(symbol_info.pricePrecision, int)

    def test_symbol_info_with_optional_fields_none(self):
        """Test valid creation when pricePrecision is not provided."""
        symbol_data = {
            "symbol": "ETH/USDT",
            "baseAsset": "ETH",
            "quoteAsset": "USDT",
            "exchange": "coinbase",
        }
        symbol_info = SymbolInfo(**symbol_data)
        assert symbol_info.pricePrecision is None

    def test_symbol_info_edge_case_long_names(self):
        """Test edge case: symbols with very long names and new fields."""
        symbol_data = {
            "symbol": "VERYLONGCRYPTOCURRENCYNAME/USDT",
            "baseAsset": "VERYLONGCRYPTOCURRENCYNAME",
            "quoteAsset": "USDT",
            "exchange": "LONGCURRENCYEXCHANGE",
            "pricePrecision": 2,
        }

        symbol_info = SymbolInfo(**symbol_data)

        assert symbol_info.symbol == "VERYLONGCRYPTOCURRENCYNAME/USDT"
        assert symbol_info.baseAsset == "VERYLONGCRYPTOCURRENCYNAME"
        assert symbol_info.pricePrecision == 2

    def test_symbol_info_missing_required_field(self):
        """Test failure case: missing required field."""
        symbol_data = {
            "symbol": "BTC/USDT",
            "baseAsset": "BTC",
            "exchange": "binance",
            # Missing quoteAsset
        }

        with pytest.raises(ValidationError) as exc_info:
            SymbolInfo(**symbol_data)

        assert "quoteAsset" in str(exc_info.value)

    def test_symbol_info_invalid_price_precision_type(self):
        """Test failure case: pricePrecision with incorrect type."""
        symbol_data = {
            "symbol": "LTC/USDT",
            "baseAsset": "LTC",
            "quoteAsset": "USDT",
            "exchange": "binance",
            "pricePrecision": "invalid",  # Incorrect type
        }
        with pytest.raises(ValidationError) as exc_info:
            SymbolInfo(**symbol_data)
        assert "Input should be a valid integer" in str(exc_info.value)


class TestOrderBookLevel:
    """Test cases for OrderBookLevel schema."""

    def test_order_book_level_valid_creation(self):
        """Test expected use: creating a valid OrderBookLevel instance."""
        level_data = {"price": 43250.50, "amount": 1.25}

        level = OrderBookLevel(**level_data)

        assert level.price == 43250.50
        assert level.amount == 1.25

    def test_order_book_level_edge_case_very_small_values(self):
        """Test edge case: very small but valid price and amount values."""
        level_data = {"price": 0.00000001, "amount": 0.00000001}

        level = OrderBookLevel(**level_data)

        assert level.price == 0.00000001
        assert level.amount == 0.00000001

    def test_order_book_level_negative_price_failure(self):
        """Test failure case: negative price should fail validation."""
        level_data = {"price": -100.0, "amount": 1.25}

        with pytest.raises(ValidationError) as exc_info:
            OrderBookLevel(**level_data)

        assert "greater than 0" in str(exc_info.value)

    def test_order_book_level_zero_amount_failure(self):
        """Test failure case: zero amount should fail validation."""
        level_data = {"price": 43250.50, "amount": 0.0}

        with pytest.raises(ValidationError) as exc_info:
            OrderBookLevel(**level_data)

        assert "greater than 0" in str(exc_info.value)


class TestOrderBook:
    """Test cases for OrderBook schema."""

    def test_order_book_valid_creation(self):
        """Test expected use: creating a valid OrderBook instance."""
        order_book_data = {
            "symbol": "BTCUSDT",
            "bids": [
                {"price": 43250.50, "amount": 1.25},
                {"price": 43250.00, "amount": 0.75},
            ],
            "asks": [
                {"price": 43251.00, "amount": 0.50},
                {"price": 43251.50, "amount": 2.00},
            ],
            "timestamp": int(
                datetime(2024, 1, 1, 12, 0, 0).timestamp() * 1000
            ),  # Unix timestamp in milliseconds
        }

        order_book = OrderBook(**order_book_data)

        assert order_book.symbol == "BTCUSDT"
        assert len(order_book.bids) == 2
        assert len(order_book.asks) == 2
        assert order_book.bids[0].price == 43250.50
        assert order_book.asks[0].price == 43251.00

    def test_order_book_edge_case_empty_levels(self):
        """Test edge case: order book with empty bids or asks."""
        order_book_data = {
            "symbol": "BTCUSDT",
            "bids": [],
            "asks": [{"price": 43251.00, "amount": 0.50}],
            "timestamp": int(
                datetime(2024, 1, 1, 12, 0, 0).timestamp() * 1000
            ),  # Unix timestamp in milliseconds
        }

        order_book = OrderBook(**order_book_data)

        assert order_book.symbol == "BTCUSDT"
        assert len(order_book.bids) == 0
        assert len(order_book.asks) == 1

    def test_order_book_missing_symbol_failure(self):
        """Test failure case: missing symbol field."""
        order_book_data = {
            # Missing symbol
            "bids": [{"price": 43250.50, "amount": 1.25}],
            "asks": [{"price": 43251.00, "amount": 0.50}],
            "timestamp": int(
                datetime(2024, 1, 1, 12, 0, 0).timestamp() * 1000
            ),  # Unix timestamp in milliseconds
        }

        with pytest.raises(ValidationError) as exc_info:
            OrderBook(**order_book_data)

        assert "symbol" in str(exc_info.value)


class TestCandle:
    """Test cases for Candle schema."""

    def test_candle_valid_creation(self):
        """Test expected use: creating a valid Candle instance."""
        candle_data = {
            "timestamp": int(
                datetime(2024, 1, 1, 12, 0, 0).timestamp() * 1000
            ),  # Unix timestamp in milliseconds
            "open": 43200.00,
            "high": 43300.00,
            "low": 43150.00,
            "close": 43250.00,
            "volume": 125.75,
        }

        candle = Candle(**candle_data)

        assert candle.open == 43200.00
        assert candle.high == 43300.00
        assert candle.low == 43150.00
        assert candle.close == 43250.00
        assert candle.volume == 125.75

    def test_candle_edge_case_zero_volume(self):
        """Test edge case: candle with zero volume (valid)."""
        candle_data = {
            "timestamp": int(
                datetime(2024, 1, 1, 12, 0, 0).timestamp() * 1000
            ),  # Unix timestamp in milliseconds
            "open": 43200.00,
            "high": 43200.00,
            "low": 43200.00,
            "close": 43200.00,
            "volume": 0.0,
        }

        candle = Candle(**candle_data)

        assert candle.volume == 0.0
        assert candle.open == candle.high == candle.low == candle.close

    def test_candle_negative_price_failure(self):
        """Test failure case: negative price values should fail."""
        candle_data = {
            "timestamp": int(
                datetime(2024, 1, 1, 12, 0, 0).timestamp() * 1000
            ),  # Unix timestamp in milliseconds
            "open": -43200.00,  # Invalid negative price
            "high": 43300.00,
            "low": 43150.00,
            "close": 43250.00,
            "volume": 125.75,
        }

        with pytest.raises(ValidationError) as exc_info:
            Candle(**candle_data)

        assert "greater than 0" in str(exc_info.value)

    def test_candle_negative_volume_failure(self):
        """Test failure case: negative volume should fail."""
        candle_data = {
            "timestamp": int(
                datetime(2024, 1, 1, 12, 0, 0).timestamp() * 1000
            ),  # Unix timestamp in milliseconds
            "open": 43200.00,
            "high": 43300.00,
            "low": 43150.00,
            "close": 43250.00,
            "volume": -125.75,  # Invalid negative volume
        }

        with pytest.raises(ValidationError) as exc_info:
            Candle(**candle_data)

        assert "greater than or equal to 0" in str(exc_info.value)


class TestSchemasSerialization:
    """Test JSON serialization and deserialization of schemas."""

    def test_symbol_info_json_serialization(self):
        """Test that SymbolInfo can be serialized to and from JSON."""
        symbol_data = {
            "symbol": "BTC/USDT",
            "baseAsset": "BTC",
            "quoteAsset": "USDT",
            "exchange": "binance",
            "pricePrecision": 8,
            "tickSize": 0.00000001,
        }

        symbol_info = SymbolInfo(**symbol_data)
        json_data = symbol_info.model_dump(by_alias=True)

        # Verify JSON structure
        assert json_data["symbol"] == symbol_data["symbol"]
        assert json_data["baseAsset"] == symbol_data["baseAsset"]
        assert json_data["quoteAsset"] == symbol_data["quoteAsset"]
        assert json_data["exchange"] == symbol_data["exchange"]
        assert json_data["pricePrecision"] == symbol_data["pricePrecision"]
        assert json_data["tickSize"] == symbol_data["tickSize"]

        # Verify round-trip
        symbol_info_restored = SymbolInfo(**json_data)
        assert symbol_info_restored == symbol_info

    def test_order_book_json_serialization(self):
        """Test that OrderBook can be serialized to and from JSON."""
        timestamp = int(datetime(2024, 1, 1, 12, 0, 0).timestamp() * 1000)
        order_book_data = {
            "symbol": "BTCUSDT",
            "bids": [{"price": 43250.50, "amount": 1.25}],
            "asks": [{"price": 43251.00, "amount": 0.50}],
            "timestamp": timestamp,
        }

        order_book = OrderBook(**order_book_data)
        json_data = order_book.model_dump()

        # Verify timestamp is properly serialized
        assert "timestamp" in json_data

        # Verify round-trip (note: datetime will be converted to string in JSON)
        order_book_restored = OrderBook(
            **{
                **json_data,
                "timestamp": timestamp,  # Restore datetime object for comparison
            }
        )
        assert order_book_restored.symbol == order_book.symbol
        assert len(order_book_restored.bids) == len(order_book.bids)
