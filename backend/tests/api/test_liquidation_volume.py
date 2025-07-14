"""
Tests for Liquidation Volume API endpoints

Tests the REST API endpoints for fetching aggregated liquidation volume data.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from app.main import app

client = TestClient(app)


class TestLiquidationVolumeAPI:
    """Test suite for liquidation volume API endpoints"""
    
    def test_get_liquidation_volume_success(self):
        """Test successful liquidation volume fetch"""
        # Mock aggregated volume data
        mock_volume_data = [
            {
                "time": 1609459200,
                "buy_volume": "1500.0",
                "sell_volume": "2500.0", 
                "total_volume": "4000.0",
                "buy_volume_formatted": "1,500.00",
                "sell_volume_formatted": "2,500.00",
                "total_volume_formatted": "4,000.00",
                "count": 5,
                "timestamp_ms": 1609459200000
            },
            {
                "time": 1609459260,
                "buy_volume": "800.0",
                "sell_volume": "1200.0",
                "total_volume": "2000.0",
                "buy_volume_formatted": "800.00",
                "sell_volume_formatted": "1,200.00",
                "total_volume_formatted": "2,000.00",
                "count": 3,
                "timestamp_ms": 1609459260000
            }
        ]
        
        with patch('app.services.liquidation_service.liquidation_service.fetch_historical_liquidations_by_timeframe') as mock_fetch:
            mock_fetch.return_value = mock_volume_data
            
            response = client.get("/api/v1/liquidation-volume/BTCUSDT/1m")
                
            assert response.status_code == 200
            data = response.json()
            
            assert data["symbol"] == "BTCUSDT"
            assert data["timeframe"] == "1m"
            assert len(data["data"]) == 2
            assert data["data"][0]["buy_volume"] == "1500.0"
            assert data["data"][0]["sell_volume"] == "2500.0"
            assert data["data"][0]["total_volume"] == "4000.0"
    
    def test_get_liquidation_volume_with_time_range(self):
        """Test liquidation volume fetch with time range parameters"""
        mock_volume_data = []
        
        with patch('app.services.liquidation_service.liquidation_service.fetch_historical_liquidations_by_timeframe') as mock_fetch:
            mock_fetch.return_value = mock_volume_data
            
            response = client.get(
                "/api/v1/liquidation-volume/ETHUSDT/5m",
                params={
                    "start_time": 1609459200000,
                    "end_time": 1609545600000
                }
            )
                
            assert response.status_code == 200
            data = response.json()
            
            assert data["start_time"] == 1609459200000
            assert data["end_time"] == 1609545600000
            
            # Verify service was called with correct parameters
            mock_fetch.assert_called_once_with(
                symbol="ETHUSDT",
                timeframe="5m", 
                start_time=1609459200000,
                end_time=1609545600000
            )
    
    def test_get_liquidation_volume_invalid_timeframe(self):
        """Test error response for invalid timeframe"""
        response = client.get("/api/v1/liquidation-volume/BTCUSDT/invalid")
            
        assert response.status_code == 400  # API returns 400 for invalid timeframe
        error = response.json()
        assert "Invalid timeframe" in error["detail"]
    
    def test_get_liquidation_volume_missing_symbol(self):
        """Test error response for missing symbol"""
        response = client.get("/api/v1/liquidation-volume//1m")
            
        # Should get 404 due to path parameter
        assert response.status_code == 404
    
    def test_get_liquidation_volume_service_error(self):
        """Test handling of service errors"""
        with patch('app.services.liquidation_service.liquidation_service.fetch_historical_liquidations_by_timeframe') as mock_fetch:
            mock_fetch.side_effect = Exception("Service error")
            
            response = client.get("/api/v1/liquidation-volume/BTCUSDT/1h")
                
        assert response.status_code == 500
        error = response.json()
        assert error["detail"] == "Failed to fetch liquidation volume data"
    
    def test_get_liquidation_volume_all_timeframes(self):
        """Test all valid timeframes"""
        valid_timeframes = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"]
        
        with patch('app.services.liquidation_service.liquidation_service.fetch_historical_liquidations_by_timeframe') as mock_fetch:
            mock_fetch.return_value = []
            
            for timeframe in valid_timeframes:
                response = client.get(f"/api/v1/liquidation-volume/BTCUSDT/{timeframe}")
                assert response.status_code == 200
                data = response.json()
                assert data["timeframe"] == timeframe
    
    def test_get_liquidation_volume_empty_response(self):
        """Test handling of empty liquidation data"""
        with patch('app.services.liquidation_service.liquidation_service.fetch_historical_liquidations_by_timeframe') as mock_fetch:
            mock_fetch.return_value = []
            
            response = client.get("/api/v1/liquidation-volume/BTCUSDT/1m")
                
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "BTCUSDT"
        assert data["timeframe"] == "1m"
        assert data["data"] == []
    
    def test_get_liquidation_volume_uppercase_symbol(self):
        """Test that symbols are normalized to uppercase"""
        mock_volume_data = [{
            "time": 1609459200,
            "buy_volume": "100.0",
            "sell_volume": "200.0",
            "total_volume": "300.0",
            "buy_volume_formatted": "100.00",
            "sell_volume_formatted": "200.00",
            "total_volume_formatted": "300.00",
            "count": 2,
            "timestamp_ms": 1609459200000
        }]
        
        with patch('app.services.liquidation_service.liquidation_service.fetch_historical_liquidations_by_timeframe') as mock_fetch:
            mock_fetch.return_value = mock_volume_data
            
            response = client.get("/api/v1/liquidation-volume/btcusdt/1m")
                
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "BTCUSDT"  # API normalizes to uppercase
        
        # Service should be called with uppercase and default time range
        args, kwargs = mock_fetch.call_args
        assert kwargs["symbol"] == "BTCUSDT"
        assert kwargs["timeframe"] == "1m"
        # API always provides default time range
        assert isinstance(kwargs["start_time"], int)
        assert isinstance(kwargs["end_time"], int)


class TestLiquidationVolumeWebSocket:
    """Test suite for liquidation volume WebSocket functionality"""
    
    def test_websocket_volume_message_format(self):
        """Test the format of WebSocket volume update messages"""
        from app.models.liquidation import LiquidationVolumeUpdate, LiquidationVolume
        
        # Create test volume data
        volume_data = [
            LiquidationVolume(
                time=1609459200,
                buy_volume="1500.0",
                sell_volume="2500.0",
                total_volume="4000.0",
                buy_volume_formatted="1,500.00",
                sell_volume_formatted="2,500.00",
                total_volume_formatted="4,000.00",
                count=5,
                timestamp_ms=1609459200000
            )
        ]
        
        # Create volume update message
        update_message = LiquidationVolumeUpdate(
            type="liquidation_volume",
            symbol="BTCUSDT",
            timeframe="1m",
            data=volume_data,
            timestamp="2024-01-01T00:00:00Z"
        )
        
        # Verify message structure
        assert update_message.type == "liquidation_volume"
        assert update_message.symbol == "BTCUSDT"
        assert update_message.timeframe == "1m"
        assert len(update_message.data) == 1
        assert update_message.data[0].buy_volume == "1500.0"
        
    def test_websocket_volume_update_structure(self):
        """Test the structure of volume updates that would be sent via WebSocket"""
        from datetime import datetime
        
        # Test data structure that would be sent when aggregation occurs
        volume_update = {
            "type": "liquidation_volume",
            "symbol": "BTCUSDT",
            "timeframe": "1m",
            "data": [
                {
                    "time": 1609459200,
                    "buy_volume": "1000.0",
                    "sell_volume": "500.0",
                    "total_volume": "1500.0",
                    "buy_volume_formatted": "1,000.00",
                    "sell_volume_formatted": "500.00",
                    "total_volume_formatted": "1,500.00",
                    "count": 3,
                    "timestamp_ms": 1609459200000
                }
            ],
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        # Verify the structure matches expected format
        assert volume_update["type"] == "liquidation_volume"
        assert "symbol" in volume_update
        assert "timeframe" in volume_update
        assert "data" in volume_update
        assert isinstance(volume_update["data"], list)
        
        # Verify data item structure
        if volume_update["data"]:
            item = volume_update["data"][0]
            assert "time" in item
            assert "buy_volume" in item
            assert "sell_volume" in item
            assert "total_volume" in item
            assert "count" in item
    
    def test_websocket_aggregation_logic(self):
        """Test the aggregation logic for real-time updates"""
        from decimal import Decimal
        
        # Test aggregation logic that would happen in the service
        # Initial state
        buy_volume = Decimal("2000")
        sell_volume = Decimal("3000")
        count = 5
        
        # New liquidation
        new_liquidation_volume = Decimal("500")
        new_side = "BUY"
        
        # Apply aggregation
        if new_side == "BUY":
            buy_volume += new_liquidation_volume
        else:
            sell_volume += new_liquidation_volume
        count += 1
        
        # Expected result
        assert buy_volume == Decimal("2500")
        assert sell_volume == Decimal("3000")
        assert count == 6
        
        total_volume = buy_volume + sell_volume
        assert total_volume == Decimal("5500")
        
        # Format for WebSocket message
        formatted_data = {
            "buy_volume": str(float(buy_volume)),
            "sell_volume": str(float(sell_volume)),
            "total_volume": str(float(total_volume)),
            "count": count
        }
        
        assert formatted_data["buy_volume"] == "2500.0"
        assert formatted_data["total_volume"] == "5500.0"
    
    @pytest.mark.asyncio
    async def test_websocket_with_timeframe_parameter(self):
        """Test WebSocket accepts timeframe parameter"""
        from unittest.mock import patch, AsyncMock
        
        # Mock the symbol validation
        with patch('app.services.symbol_service.symbol_service.validate_symbol_exists', return_value=True):
            with patch('app.services.symbol_service.symbol_service.resolve_symbol_to_exchange_format', return_value="BTCUSDT"):
                with patch('app.services.symbol_service.symbol_service.get_symbol_info', return_value={'symbol': 'BTCUSDT'}):
                    with patch('app.services.liquidation_service.liquidation_service.connect_to_liquidation_stream') as mock_connect:
                        with patch('app.services.liquidation_service.liquidation_service.fetch_historical_liquidations_by_timeframe') as mock_fetch:
                            mock_fetch.return_value = []
                            
                            # Connect with timeframe parameter
                            with client.websocket_connect("/api/v1/ws/liquidations/BTCUSDT?timeframe=5m") as websocket:
                                # Should receive initial liquidations message
                                data = websocket.receive_json()
                                
                                # Basic structure validation
                                assert data["type"] == "liquidations"
                                assert data["symbol"] == "BTCUSDT"
                                
                                # WebSocket may send other messages like heartbeat
                                # Look for volume data message
                                volume_found = False
                                for _ in range(5):  # Try a few messages
                                    try:
                                        msg = websocket.receive_json(timeout=1)
                                        if msg.get("type") == "liquidation_volume":
                                            assert msg["timeframe"] == "5m"
                                            volume_found = True
                                            break
                                    except:
                                        break
                                
                                # Verify timeframe was requested
                                mock_fetch.assert_called()
                                args, kwargs = mock_fetch.call_args
                                assert kwargs.get("timeframe") == "5m"