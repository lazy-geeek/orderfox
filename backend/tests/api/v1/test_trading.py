"""
Unit tests for trading API endpoints.

This module contains tests for the trading endpoints including
trade execution, position management, and trading mode settings.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
import sys
import os

sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
from app.main import app
from app.api.v1.schemas import TradeSide, OrderType

client = TestClient(app)


class TestTradeEndpoint:
    """Test cases for the /api/v1/trading/trade endpoint."""

    @patch("app.api.v1.endpoints.trading.get_trading_engine_service")
    def test_execute_trade_success_market_order(self, mock_get_service):
        """Test successful market order execution."""
        # Mock trading engine service
        mock_service = AsyncMock()
        mock_get_service.return_value = mock_service

        mock_service.execute_trade.return_value = {
            "status": "success",
            "message": "Trade executed successfully",
            "orderId": "12345",
            "positionInfo": {
                "symbol": "BTCUSDT",
                "side": "buy",
                "amount": 0.1,
                "entry_price": 43000.0,
            },
        }

        # Make request
        trade_request = {
            "symbol": "BTCUSDT",
            "side": "long",
            "amount": 0.1,
            "type": "market",
        }
        response = client.post("/api/v1/trading/trade", json=trade_request)

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["message"] == "Trade executed successfully"
        assert data["orderId"] == "12345"
        assert data["positionInfo"]["symbol"] == "BTCUSDT"

        # Verify service was called correctly
        mock_service.execute_trade.assert_called_once_with(
            symbol="BTCUSDT", side="long", amount=0.1, trade_type="market", price=None
        )

    @patch("app.api.v1.endpoints.trading.get_trading_engine_service")
    def test_execute_trade_success_limit_order(self, mock_get_service):
        """Test successful limit order execution."""
        mock_service = AsyncMock()
        mock_get_service.return_value = mock_service

        mock_service.execute_trade.return_value = {
            "status": "success",
            "message": "Limit order placed",
            "orderId": "67890",
        }

        trade_request = {
            "symbol": "ETHUSDT",
            "side": "short",
            "amount": 1.0,
            "type": "limit",
            "price": 2500.0,
        }
        response = client.post("/api/v1/trading/trade", json=trade_request)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["orderId"] == "67890"

        mock_service.execute_trade.assert_called_once_with(
            symbol="ETHUSDT", side="short", amount=1.0, trade_type="limit", price=2500.0
        )

    def test_execute_trade_invalid_request_missing_fields(self):
        """Test trade execution with missing required fields."""
        trade_request = {
            "symbol": "BTCUSDT",
            # Missing side, amount, type
        }
        response = client.post("/api/v1/trading/trade", json=trade_request)

        assert response.status_code == 422  # Validation error

    def test_execute_trade_invalid_amount(self):
        """Test trade execution with invalid amount."""
        trade_request = {
            "symbol": "BTCUSDT",
            "side": "long",
            "amount": -0.1,  # Invalid negative amount
            "type": "market",
        }
        response = client.post("/api/v1/trading/trade", json=trade_request)

        assert response.status_code == 422  # Validation error

    def test_execute_trade_invalid_side(self):
        """Test trade execution with invalid side."""
        trade_request = {
            "symbol": "BTCUSDT",
            "side": "invalid_side",
            "amount": 0.1,
            "type": "market",
        }
        response = client.post("/api/v1/trading/trade", json=trade_request)

        assert response.status_code == 422  # Validation error

    @patch("app.api.v1.endpoints.trading.get_trading_engine_service")
    def test_execute_trade_service_error(self, mock_get_service):
        """Test trade execution when service raises an exception."""
        mock_service = AsyncMock()
        mock_get_service.return_value = mock_service
        mock_service.execute_trade.side_effect = Exception("Service error")

        trade_request = {
            "symbol": "BTCUSDT",
            "side": "long",
            "amount": 0.1,
            "type": "market",
        }
        response = client.post("/api/v1/trading/trade", json=trade_request)

        assert response.status_code == 500
        assert "Service error" in response.json()["detail"]


class TestPositionsEndpoint:
    """Test cases for the /api/v1/trading/positions endpoint."""

    @patch("app.api.v1.endpoints.trading.get_trading_engine_service")
    def test_get_positions_success(self, mock_get_service):
        """Test successful retrieval of positions."""
        mock_service = AsyncMock()
        mock_get_service.return_value = mock_service

        mock_positions = [
            {
                "symbol": "BTCUSDT",
                "side": "long",
                "amount": 0.1,
                "entry_price": 43000.0,
            },
            {
                "symbol": "ETHUSDT",
                "side": "short",
                "amount": 1.0,
                "entry_price": 2500.0,
            },
        ]
        mock_service.get_open_positions.return_value = mock_positions

        response = client.get("/api/v1/trading/positions")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["symbol"] == "BTCUSDT"
        assert data[1]["symbol"] == "ETHUSDT"

        mock_service.get_open_positions.assert_called_once()

    @patch("app.api.v1.endpoints.trading.get_trading_engine_service")
    def test_get_positions_empty(self, mock_get_service):
        """Test retrieval when no positions exist."""
        mock_service = AsyncMock()
        mock_get_service.return_value = mock_service
        mock_service.get_open_positions.return_value = []

        response = client.get("/api/v1/trading/positions")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0

    @patch("app.api.v1.endpoints.trading.get_trading_engine_service")
    def test_get_positions_service_error(self, mock_get_service):
        """Test positions endpoint when service raises an exception."""
        mock_service = AsyncMock()
        mock_get_service.return_value = mock_service
        mock_service.get_open_positions.side_effect = Exception("Database error")

        response = client.get("/api/v1/trading/positions")

        assert response.status_code == 500
        assert "Database error" in response.json()["detail"]


class TestSetTradingModeEndpoint:
    """Test cases for the /api/v1/trading/set_trading_mode endpoint."""

    @patch("app.api.v1.endpoints.trading.get_trading_engine_service")
    def test_set_trading_mode_success_paper(self, mock_get_service):
        """Test successful setting of paper trading mode."""
        mock_service = AsyncMock()
        mock_get_service.return_value = mock_service

        mock_service.set_trading_mode.return_value = {
            "status": "success",
            "message": "Trading mode set to paper",
        }

        response = client.post(
            "/api/v1/trading/set_trading_mode", json={"mode": "paper"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "paper" in data["message"]

        mock_service.set_trading_mode.assert_called_once_with("paper")

    @patch("app.api.v1.endpoints.trading.get_trading_engine_service")
    def test_set_trading_mode_success_live(self, mock_get_service):
        """Test successful setting of live trading mode."""
        mock_service = AsyncMock()
        mock_get_service.return_value = mock_service

        mock_service.set_trading_mode.return_value = {
            "status": "success",
            "message": "Trading mode set to live",
        }

        response = client.post(
            "/api/v1/trading/set_trading_mode", json={"mode": "live"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

        mock_service.set_trading_mode.assert_called_once_with("live")

    def test_set_trading_mode_missing_mode(self):
        """Test setting trading mode without mode field."""
        response = client.post("/api/v1/trading/set_trading_mode", json={})

        assert response.status_code == 400
        assert "Missing 'mode'" in response.json()["detail"]

    def test_set_trading_mode_empty_body(self):
        """Test setting trading mode with empty request body."""
        response = client.post("/api/v1/trading/set_trading_mode", json=None)

        assert response.status_code == 422  # Validation error

    @patch("app.api.v1.endpoints.trading.get_trading_engine_service")
    def test_set_trading_mode_service_error_response(self, mock_get_service):
        """Test setting trading mode when service returns error status."""
        mock_service = AsyncMock()
        mock_get_service.return_value = mock_service

        mock_service.set_trading_mode.return_value = {
            "status": "error",
            "message": "Invalid trading mode",
        }

        response = client.post(
            "/api/v1/trading/set_trading_mode", json={"mode": "invalid"}
        )

        assert response.status_code == 400
        assert "Invalid trading mode" in response.json()["detail"]

    @patch("app.api.v1.endpoints.trading.get_trading_engine_service")
    def test_set_trading_mode_service_exception(self, mock_get_service):
        """Test setting trading mode when service raises an exception."""
        mock_service = AsyncMock()
        mock_get_service.return_value = mock_service
        mock_service.set_trading_mode.side_effect = Exception("Service error")

        response = client.post(
            "/api/v1/trading/set_trading_mode", json={"mode": "paper"}
        )

        assert response.status_code == 500
        assert "Service error" in response.json()["detail"]


class TestTradingEndpointIntegration:
    """Integration tests for trading endpoints."""

    @patch("app.api.v1.endpoints.trading.get_trading_engine_service")
    def test_trading_workflow_paper_mode(self, mock_get_service):
        """Test complete trading workflow in paper mode."""
        mock_service = AsyncMock()
        mock_get_service.return_value = mock_service

        # Set up mock responses
        mock_service.set_trading_mode.return_value = {
            "status": "success",
            "message": "Trading mode set to paper",
        }

        mock_service.execute_trade.return_value = {
            "status": "success",
            "message": "Paper trade executed",
            "orderId": "paper_123",
            "positionInfo": {
                "symbol": "BTCUSDT",
                "side": "buy",
                "amount": 0.1,
                "entry_price": 43000.0,
            },
        }

        mock_service.get_open_positions.return_value = [
            {"symbol": "BTCUSDT", "side": "long", "amount": 0.1, "entry_price": 43000.0}
        ]

        # 1. Set trading mode to paper
        mode_response = client.post(
            "/api/v1/trading/set_trading_mode", json={"mode": "paper"}
        )
        assert mode_response.status_code == 200

        # 2. Execute a trade
        trade_request = {
            "symbol": "BTCUSDT",
            "side": "long",
            "amount": 0.1,
            "type": "market",
        }
        trade_response = client.post("/api/v1/trading/trade", json=trade_request)
        assert trade_response.status_code == 200

        # 3. Check positions
        positions_response = client.get("/api/v1/trading/positions")
        assert positions_response.status_code == 200
        positions = positions_response.json()
        assert len(positions) == 1
        assert positions[0]["symbol"] == "BTCUSDT"
