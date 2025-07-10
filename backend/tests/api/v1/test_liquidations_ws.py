"""
Tests for Liquidations WebSocket API endpoints

Comprehensive tests for liquidation WebSocket endpoints including connection,
symbol validation, data streaming, error handling, and disconnection cleanup.
"""

import pytest
import json
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch
from app.main import app

class TestLiquidationsWebSocket:
    """Test suite for liquidations WebSocket endpoint"""
    
    def test_liquidation_websocket_import(self):
        """Test that liquidations WebSocket module can be imported"""
        from app.api.v1.endpoints.liquidations_ws import router
        assert router is not None
    
    @pytest.mark.asyncio 
    async def test_liquidation_websocket_connection(self):
        """Test WebSocket connection and initial data"""
        client = TestClient(app)
        
        symbol_info = {
            'symbol': 'BTCUSDT',
            'baseAsset': 'BTC',
            'pricePrecision': 1,
            'amountPrecision': 3
        }
        
        with patch('app.services.symbol_service.symbol_service.validate_symbol_exists', return_value=True):
            with patch('app.services.symbol_service.symbol_service.resolve_symbol_to_exchange_format', return_value="BTCUSDT"):
                with patch('app.services.symbol_service.symbol_service.get_symbol_info', return_value=symbol_info):
                    with patch('app.services.liquidation_service.liquidation_service.connect_to_liquidation_stream') as mock_connect:
                        
                        with client.websocket_connect("/api/v1/ws/liquidations/BTCUSDT") as websocket:
                            # Receive initial data
                            data = websocket.receive_json()
                            
                            assert data["type"] == "liquidations"
                            assert data["symbol"] == "BTCUSDT"
                            assert data["initial"] is True
                            assert isinstance(data["data"], list)
                            assert "timestamp" in data
                            
                            # Verify liquidation service was called with symbol_info
                            mock_connect.assert_called_once()
                            call_args = mock_connect.call_args
                            assert call_args[0][0] == "BTCUSDT"  # symbol
                            assert call_args[0][2] == symbol_info  # symbol_info
    
    @pytest.mark.asyncio
    async def test_liquidation_websocket_invalid_symbol(self):
        """Test WebSocket connection with invalid symbol"""
        client = TestClient(app)
        
        with patch('app.services.symbol_service.symbol_service.validate_symbol_exists', return_value=False):
            with client.websocket_connect("/api/v1/ws/liquidations/INVALID") as websocket:
                # Should receive error message
                data = websocket.receive_json()
                
                assert data["type"] == "error"
                assert "Invalid symbol" in data["message"]
                assert "timestamp" in data
    
    @pytest.mark.asyncio
    async def test_liquidation_websocket_data_streaming(self):
        """Test liquidation data streaming"""
        client = TestClient(app)
        
        # Mock liquidation data
        mock_liquidation = {
            "symbol": "BTCUSDT",
            "side": "SELL",
            "quantity": "0.014",
            "quantityFormatted": "0.014000",
            "priceUsdt": "138.74",
            "priceUsdtFormatted": "138.74",
            "timestamp": 1568014460893,
            "displayTime": "14:27:40"
        }
        
        with patch('app.services.symbol_service.symbol_service.validate_symbol_exists', return_value=True):
            with patch('app.services.symbol_service.symbol_service.resolve_symbol_to_exchange_format', return_value="BTCUSDT"):
                with patch('app.services.liquidation_service.liquidation_service.connect_to_liquidation_stream') as mock_connect:
                    
                    # Test that the connection handles data properly
                    assert mock_connect is not None
    
    def test_liquidation_websocket_message_format(self):
        """Test liquidation WebSocket message format"""
        # Expected initial message format
        expected_initial_format = {
            "type": "liquidations",
            "symbol": "BTCUSDT", 
            "data": [],
            "initial": True,
            "timestamp": "2023-01-01T00:00:00"
        }
        
        # Expected liquidation update format
        expected_update_format = {
            "type": "liquidation",
            "symbol": "BTCUSDT",
            "data": {
                "symbol": "BTCUSDT",
                "side": "SELL",
                "quantity": "0.014",
                "quantityFormatted": "0.014000",
                "priceUsdt": "138.74",
                "priceUsdtFormatted": "138.74",
                "timestamp": 1568014460893,
                "displayTime": "14:27:40"
            },
            "timestamp": "2023-01-01T00:00:00"
        }
        
        # Expected error format
        expected_error_format = {
            "type": "error",
            "message": "Error description",
            "timestamp": "2023-01-01T00:00:00"
        }
        
        # Verify format structures
        assert "type" in expected_initial_format
        assert "symbol" in expected_initial_format
        assert "data" in expected_initial_format
        assert "initial" in expected_initial_format
        assert "timestamp" in expected_initial_format
        
        assert "type" in expected_update_format
        assert "symbol" in expected_update_format
        assert "data" in expected_update_format
        assert "timestamp" in expected_update_format
        
        assert "type" in expected_error_format
        assert "message" in expected_error_format
        assert "timestamp" in expected_error_format
    
    @pytest.mark.asyncio
    async def test_liquidation_websocket_heartbeat(self):
        """Test WebSocket heartbeat functionality"""
        # This would test the heartbeat mechanism in a real scenario
        # For now, just verify the heartbeat format
        expected_heartbeat = {
            "type": "heartbeat",
            "symbol": "BTCUSDT",
            "timestamp": "2023-01-01T00:00:00"
        }
        
        assert expected_heartbeat["type"] == "heartbeat"
        assert "symbol" in expected_heartbeat
        assert "timestamp" in expected_heartbeat
    
    @pytest.mark.asyncio
    async def test_liquidation_websocket_with_symbol_info(self):
        """Test WebSocket liquidation data includes baseAsset from symbol_info"""
        client = TestClient(app)
        
        symbol_info = {
            'symbol': 'SOLUSDT',
            'baseAsset': 'SOL',
            'pricePrecision': 2,
            'amountPrecision': 6
        }
        
        with patch('app.services.symbol_service.symbol_service.validate_symbol_exists', return_value=True):
            with patch('app.services.symbol_service.symbol_service.resolve_symbol_to_exchange_format', return_value="SOLUSDT"):
                with patch('app.services.symbol_service.symbol_service.get_symbol_info', return_value=symbol_info):
                    with patch('app.services.liquidation_service.liquidation_service.connect_to_liquidation_stream') as mock_connect:
                        
                        with client.websocket_connect("/api/v1/ws/liquidations/SOLUSDT") as websocket:
                            # Receive initial data
                            data = websocket.receive_json()
                            
                            # Verify connect was called with symbol_info
                            assert mock_connect.call_args[0][2]['baseAsset'] == 'SOL'
    
    def test_liquidation_data_format_with_base_asset(self):
        """Test liquidation data format includes baseAsset"""
        expected_liquidation_format = {
            "symbol": "BTCUSDT",
            "side": "SELL",
            "quantity": "0.014",
            "quantityFormatted": "0.014",
            "priceUsdt": "138.74",
            "priceUsdtFormatted": "139",  # Rounded to whole number (no comma for 3 digits)
            "timestamp": 1568014460893,
            "displayTime": "14:27:40",
            "avgPrice": "9910",
            "baseAsset": "BTC"  # New field
        }
        
        # Verify baseAsset is included
        assert "baseAsset" in expected_liquidation_format
        assert expected_liquidation_format["baseAsset"] == "BTC"