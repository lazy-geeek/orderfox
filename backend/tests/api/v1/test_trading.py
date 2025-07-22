"""
Unit tests for trading API endpoints.

This module contains tests for the trading endpoints including
trade execution, position management, and trading mode settings.
"""

import pytest

# Chunk 5: REST API endpoints - Schema, bot, market data APIs
pytestmark = pytest.mark.chunk5
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
import sys
import os

sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
from app.main import app
from app.api.v1.schemas import TradeSide, OrderType
from app.api.v1.endpoints.trading import get_trading_engine_service  # New import

client = TestClient(app)


@pytest.fixture(name="mock_trading_service")
def mock_trading_service_fixture():
    """Fixture to provide a mocked TradingEngineService."""
    mock_service = AsyncMock()
    app.dependency_overrides[get_trading_engine_service] = lambda: mock_service
    yield mock_service
    app.dependency_overrides.clear()  # Clean up overrides after test


class TestTradeEndpoint:
    """Test cases for the /api/v1/trading/trade endpoint."""

    async def test_execute_trade_success_market_order(self, mock_trading_service):
        """Test successful market order execution."""
        mock_trading_service.execute_trade.return_value = {
            "status": "success",
            "message": "Paper trade executed for BTCUSDT",
            "orderId": "paper_BTCUSDT_test_id",
            "positionInfo": {
                "symbol": "BTCUSDT",
                "side": "buy",
                "amount": 0.1,
                "entryPrice": 43000.0,
                "markPrice": 43000.0,
                "unrealizedPnl": 0.0,
            },
        }

        trade_request = {
            "symbol": "BTCUSDT",
            "side": "long",
            "amount": 0.1,
            "type": "market",
        }
        response = client.post("/api/v1/trade", json=trade_request)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "Paper trade executed" in data["message"]
        assert "paper_BTCUSDT" in data["orderId"]
        assert data["positionInfo"]["symbol"] == "BTCUSDT"

        mock_trading_service.execute_trade.assert_called_once_with(
            symbol="BTCUSDT", side="long", amount=0.1, trade_type="market", price=None
        )

    async def test_execute_trade_success_limit_order(self, mock_trading_service):
        """Test successful limit order execution."""
        mock_trading_service.execute_trade.return_value = {
            "status": "success",
            "message": "Paper limit order placed for ETHUSDT",
            "orderId": "paper_ETHUSDT_limit_test_id",
            "positionInfo": {
                "symbol": "ETHUSDT",
                "side": "short",
                "amount": 1.0,
                "entryPrice": 2500.0,
                "markPrice": 2500.0,
                "unrealizedPnl": 0.0,
            },
        }

        trade_request = {
            "symbol": "ETHUSDT",
            "side": "short",
            "amount": 1.0,
            "type": "limit",
            "price": 2500.0,
        }
        response = client.post("/api/v1/trade", json=trade_request)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "paper_ETHUSDT" in data["orderId"]

        mock_trading_service.execute_trade.assert_called_once_with(
            symbol="ETHUSDT", side="short", amount=1.0, trade_type="limit", price=2500.0
        )

    def test_execute_trade_invalid_request_missing_fields(self):
        """Test trade execution with missing required fields."""
        trade_request = {
            "symbol": "BTCUSDT",
            # Missing side, amount, type
        }
        response = client.post("/api/v1/trade", json=trade_request)

        assert response.status_code == 422  # Validation error

    def test_execute_trade_invalid_amount(self):
        """Test trade execution with invalid amount."""
        trade_request = {
            "symbol": "BTCUSDT",
            "side": "long",
            "amount": -0.1,  # Invalid negative amount
            "type": "market",
        }
        response = client.post("/api/v1/trade", json=trade_request)

        assert response.status_code == 422  # Validation error

    def test_execute_trade_invalid_side(self):
        """Test trade execution with invalid side."""
        trade_request = {
            "symbol": "BTCUSDT",
            "side": "invalid_side",
            "amount": 0.1,
            "type": "market",
        }
        response = client.post("/api/v1/trade", json=trade_request)

        assert response.status_code == 422  # Validation error

    async def test_execute_trade_service_error(self, mock_trading_service):
        """Test trade execution when service raises an exception."""
        mock_trading_service.execute_trade.side_effect = Exception("Service error")

        trade_request = {
            "symbol": "BTCUSDT",
            "side": "long",
            "amount": 0.1,
            "type": "market",
        }
        response = client.post("/api/v1/trade", json=trade_request)

        assert response.status_code == 500
        assert (
            "Trade execution failed" in response.json()["detail"]
        )  # FastAPI's HTTPException detail


class TestPositionsEndpoint:
    """Test cases for the /api/v1/trading/positions endpoint."""

    async def test_get_positions_success(self, mock_trading_service):
        """Test successful retrieval of positions."""
        mock_trading_service.get_open_positions.return_value = [
            {
                "symbol": "BTCUSDT",
                "side": "long",
                "size": 0.1,
                "entryPrice": 43000.0,
                "markPrice": 43000.0,
                "unrealizedPnl": 0.0,
            },
            {
                "symbol": "ETHUSDT",
                "side": "short",
                "size": 1.0,
                "entryPrice": 2500.0,
                "markPrice": 2500.0,
                "unrealizedPnl": 0.0,
            },
        ]

        response = client.get("/api/v1/positions")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["symbol"] == "BTCUSDT"
        assert data[1]["symbol"] == "ETHUSDT"

        mock_trading_service.get_open_positions.assert_called_once()

    async def test_get_positions_empty(self, mock_trading_service):
        """Test retrieval when no positions exist."""
        mock_trading_service.get_open_positions.return_value = []

        response = client.get("/api/v1/positions")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0

    async def test_get_positions_service_error(self, mock_trading_service):
        """Test positions endpoint when service raises an exception."""
        mock_trading_service.get_open_positions.side_effect = Exception(
            "Database error"
        )

        response = client.get("/api/v1/positions")

        assert response.status_code == 500
        assert "Failed to fetch positions" in response.json()["detail"]


class TestSetTradingModeEndpoint:
    """Test cases for the /api/v1/trading/set_trading_mode endpoint."""

    async def test_set_trading_mode_success_paper(self, mock_trading_service):
        """Test successful setting of paper trading mode."""
        mock_trading_service.set_trading_mode.return_value = {
            "status": "success",
            "message": "Trading mode set to paper",
        }

        response = client.post("/api/v1/set_trading_mode", json={"mode": "paper"})

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "paper" in data["message"]

        mock_trading_service.set_trading_mode.assert_called_once_with("paper")

    async def test_set_trading_mode_success_live(self, mock_trading_service):
        """Test successful setting of live trading mode."""
        mock_trading_service.set_trading_mode.return_value = {
            "status": "success",
            "message": "Trading mode set to live",
        }

        response = client.post("/api/v1/set_trading_mode", json={"mode": "live"})

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

        mock_trading_service.set_trading_mode.assert_called_once_with("live")

    def test_set_trading_mode_missing_mode(self):
        """Test setting trading mode without mode field."""
        response = client.post("/api/v1/set_trading_mode", json={})

        assert response.status_code == 400
        assert "Missing 'mode'" in response.json()["detail"]

    def test_set_trading_mode_empty_body(self):
        """Test setting trading mode with empty request body."""
        response = client.post("/api/v1/set_trading_mode", json=None)

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

        response = client.post("/api/v1/set_trading_mode", json={"mode": "invalid"})

        assert response.status_code == 400
        assert "Invalid trading mode" in response.json()["detail"]

    async def test_set_trading_mode_service_exception(self, mock_trading_service):
        """Test setting trading mode when service raises an exception."""
        mock_trading_service.set_trading_mode.side_effect = Exception("Service error")

        response = client.post("/api/v1/set_trading_mode", json={"mode": "paper"})

        assert response.status_code == 500
        assert "Failed to set trading mode" in response.json()["detail"]


class TestTradingEndpointIntegration:
    """Integration tests for trading endpoints."""

    async def test_trading_workflow_paper_mode(self, mock_trading_service):
        """Test complete trading workflow in paper mode."""
        # Set up mock responses
        mock_trading_service.set_trading_mode.return_value = {
            "status": "success",
            "message": "Trading mode set to paper",
        }

        mock_trading_service.execute_trade.return_value = {
            "status": "success",
            "message": "Paper trade executed for BTCUSDT",
            "orderId": "paper_BTCUSDT_workflow_id",
            "positionInfo": {
                "symbol": "BTCUSDT",
                "side": "long",
                "size": 0.1,
                "entryPrice": 43000.0,
                "markPrice": 43000.0,
                "unrealizedPnl": 0.0,
            },
        }

        mock_trading_service.get_open_positions.return_value = [
            {
                "symbol": "BTCUSDT",
                "side": "long",
                "size": 0.1,
                "entryPrice": 43000.0,
                "markPrice": 43000.0,
                "unrealizedPnl": 0.0,
            }
        ]

        # 1. Set trading mode to paper
        mode_response = client.post("/api/v1/set_trading_mode", json={"mode": "paper"})
        assert mode_response.status_code == 200

        # 2. Execute a trade
        trade_request = {
            "symbol": "BTCUSDT",
            "side": "long",
            "amount": 0.1,
            "type": "market",
        }
        trade_response = client.post("/api/v1/trade", json=trade_request)
        assert trade_response.status_code == 200

        # 3. Check positions
        positions_response = client.get("/api/v1/positions")
        assert positions_response.status_code == 200
        positions = positions_response.json()
        assert len(positions) == 1
        assert positions[0]["symbol"] == "BTCUSDT"
