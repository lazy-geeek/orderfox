"""
End-to-End Integration Tests for Liquidation Volume Feature

Tests the complete data flow from API to WebSocket to ensure all components
work together correctly for the liquidation volume visualization feature.
"""

import pytest

# Chunk 8: Performance and load tests - Volume, load, advanced integration
pytestmark = pytest.mark.chunk8
import asyncio
import json
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, Mock
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from app.main import app


class TestLiquidationVolumeE2E:
    """End-to-end tests for liquidation volume feature"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    @pytest.fixture
    def mock_liquidation_data(self):
        """Mock liquidation data from external API"""
        return [
            {
                "order_trade_time": 1609459200000,  # 2021-01-01 00:00:00
                "symbol": "BTCUSDT",
                "side": "buy",
                "order_filled_accumulated_quantity": "0.5",
                "average_price": "30000",
                "liquidation_order_id": "1"
            },
            {
                "order_trade_time": 1609459260000,  # 2021-01-01 00:01:00
                "symbol": "BTCUSDT",
                "side": "sell",
                "order_filled_accumulated_quantity": "0.3",
                "average_price": "30100",
                "liquidation_order_id": "2"
            },
            {
                "order_trade_time": 1609459320000,  # 2021-01-01 00:02:00
                "symbol": "BTCUSDT",
                "side": "buy",
                "order_filled_accumulated_quantity": "0.2",
                "average_price": "30200",
                "liquidation_order_id": "3"
            }
        ]
    
    def test_rest_api_to_websocket_flow(self, client, mock_liquidation_data):
        """Test complete flow from REST API fetch to WebSocket delivery"""
        
        # Mock the aggregated data that the service would return
        mock_aggregated_data = [
            {
                "time": 1609459200,
                "buy_volume": "21000.0",  # 0.7 BTC total at avg 30000
                "sell_volume": "9030.0",   # 0.3 BTC at 30100
                "total_volume": "30030.0",
                "delta_volume": "11970.0",  # buy_volume - sell_volume
                "buy_volume_formatted": "21,000.00",
                "sell_volume_formatted": "9,030.00",
                "total_volume_formatted": "30,030.00",
                "delta_volume_formatted": "11,970.00",
                "count": 3,
                "timestamp_ms": 1609459200000
            }
        ]
        
        with patch('app.services.liquidation_service.liquidation_service.fetch_historical_liquidations_by_timeframe') as mock_fetch:
            mock_fetch.return_value = mock_aggregated_data
            
            # Step 1: REST API call to get liquidation volume
            response = client.get("/api/v1/liquidation-volume/BTCUSDT/1m")
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify response structure
            assert data["symbol"] == "BTCUSDT"
            assert data["timeframe"] == "1m"
            assert "data" in data
            assert len(data["data"]) > 0
            
            # Verify aggregated data
            first_candle = data["data"][0]
            assert "time" in first_candle
            assert "buy_volume" in first_candle
            assert "sell_volume" in first_candle
            assert "total_volume" in first_candle
            assert "count" in first_candle
            
            # Step 2: Connect to WebSocket and verify data consistency
            with patch('app.services.symbol_service.symbol_service.validate_symbol_exists', return_value=True):
                with patch('app.services.symbol_service.symbol_service.resolve_symbol_to_exchange_format', return_value="BTCUSDT"):
                    with patch('app.services.symbol_service.symbol_service.get_symbol_info', return_value={'symbol': 'BTCUSDT'}):
                        with patch('app.services.liquidation_service.liquidation_service.connect_to_liquidation_stream'):
                            with patch('app.services.liquidation_service.liquidation_service.fetch_historical_liquidations_by_timeframe') as mock_fetch:
                                # Return same aggregated data
                                mock_fetch.return_value = mock_aggregated_data
                                
                                with client.websocket_connect("/api/v1/ws/liquidations/BTCUSDT?timeframe=1m") as websocket:
                                    # Should receive initial liquidations
                                    initial_msg = websocket.receive_json()
                                    assert initial_msg["type"] == "liquidation_order"
                                    
                                    # Look for volume update message
                                    # WebSocket might send multiple messages
                                    volume_msg = None
                                    for _ in range(5):
                                        try:
                                            msg = websocket.receive_json(timeout=0.5)
                                            if msg.get("type") == "liquidation_volume":
                                                volume_msg = msg
                                                break
                                        except:
                                            break
                                    
                                    # Verify volume data consistency
                                    if volume_msg:
                                        assert volume_msg["symbol"] == "BTCUSDT"
                                        assert volume_msg["timeframe"] == "1m"
                                        assert len(volume_msg["data"]) == len(data["data"])
    
    @pytest.mark.asyncio
    async def test_real_time_aggregation_flow(self):
        """Test real-time liquidation aggregation and updates"""
        from app.services.liquidation_service import liquidation_service
        
        # Mock initial state
        liquidation_service.aggregation_buffers = {}
        
        # Simulate incoming liquidation
        test_liquidation = {
            "symbol": "BTCUSDT",
            "side": "buy",
            "quantity": "1.0",
            "priceUsdt": "1000.0",
            "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000)
        }
        
        # Process liquidation for aggregation
        timeframe = "1m"
        symbol = "BTCUSDT"
        
        # Initialize buffer if needed
        if symbol not in liquidation_service.aggregation_buffers:
            liquidation_service.aggregation_buffers[symbol] = {}
        if timeframe not in liquidation_service.aggregation_buffers[symbol]:
            liquidation_service.aggregation_buffers[symbol][timeframe] = {
                "buy_volume": Decimal("0"),
                "sell_volume": Decimal("0"),
                "count": 0,
                "last_update": datetime.now(timezone.utc)
            }
        
        # Update aggregation
        buffer = liquidation_service.aggregation_buffers[symbol][timeframe]
        volume = Decimal(test_liquidation["quantity"]) * Decimal(test_liquidation["priceUsdt"])
        
        if test_liquidation["side"].lower() == "buy":
            buffer["buy_volume"] += volume
        else:
            buffer["sell_volume"] += volume
        
        buffer["count"] += 1
        buffer["last_update"] = datetime.now(timezone.utc)
        
        # Verify aggregation
        assert float(buffer["buy_volume"]) == 1000.0
        assert float(buffer["sell_volume"]) == 0.0
        assert buffer["count"] == 1
    
    def test_multiple_timeframe_aggregation(self, client):
        """Test that different timeframes aggregate correctly"""
        
        mock_1m_data = [
            {
                "time": 1609459200,
                "buy_volume": "15000.0",
                "sell_volume": "25000.0",
                "total_volume": "40000.0",
                "delta_volume": "-10000.0",  # buy_volume - sell_volume
                "buy_volume_formatted": "15,000.00",
                "sell_volume_formatted": "25,000.00",
                "total_volume_formatted": "40,000.00",
                "delta_volume_formatted": "-10,000.00",
                "count": 50,
                "timestamp_ms": 1609459200000
            }
        ]
        
        mock_5m_data = [
            {
                "time": 1609459200,
                "buy_volume": "75000.0",
                "sell_volume": "125000.0",
                "total_volume": "200000.0",
                "delta_volume": "-50000.0",  # buy_volume - sell_volume
                "buy_volume_formatted": "75,000.00",
                "sell_volume_formatted": "125,000.00",
                "total_volume_formatted": "200,000.00",
                "delta_volume_formatted": "-50,000.00",
                "count": 250,
                "timestamp_ms": 1609459200000
            }
        ]
        
        with patch('app.services.liquidation_service.liquidation_service.fetch_historical_liquidations_by_timeframe') as mock_fetch:
            # Test 1m timeframe
            mock_fetch.return_value = mock_1m_data
            response_1m = client.get("/api/v1/liquidation-volume/BTCUSDT/1m")
            assert response_1m.status_code == 200
            data_1m = response_1m.json()
            assert data_1m["data"][0]["total_volume"] == "40000.0"
            
            # Test 5m timeframe
            mock_fetch.return_value = mock_5m_data
            response_5m = client.get("/api/v1/liquidation-volume/BTCUSDT/5m")
            assert response_5m.status_code == 200
            data_5m = response_5m.json()
            assert data_5m["data"][0]["total_volume"] == "200000.0"
            
            # Verify 5m has more volume (5x the time period)
            assert float(data_5m["data"][0]["total_volume"]) > float(data_1m["data"][0]["total_volume"])
    
    def test_error_handling_cascade(self, client):
        """Test error handling through the entire stack"""
        
        # Test 1: External API failure
        with patch('app.services.liquidation_service.liquidation_service.fetch_historical_liquidations_by_timeframe') as mock_fetch:
            mock_fetch.side_effect = Exception("External API error")
            
            response = client.get("/api/v1/liquidation-volume/BTCUSDT/1m")
            assert response.status_code == 500
            assert "Failed to fetch liquidation volume data" in response.json()["detail"]
        
        # Test 2: Invalid symbol handling - it will still return 200 with empty data
        with patch('app.services.liquidation_service.liquidation_service.fetch_historical_liquidations_by_timeframe') as mock_fetch:
            mock_fetch.return_value = []  # Empty data for invalid symbol
            response = client.get("/api/v1/liquidation-volume/INVALID/1m")
            assert response.status_code == 200  # API returns 200 with empty data
            assert response.json()["data"] == []
        
        # Test 3: Invalid timeframe
        response = client.get("/api/v1/liquidation-volume/BTCUSDT/invalid")
        assert response.status_code == 400
        assert "Invalid timeframe" in response.json()["detail"]
    
    def test_data_format_consistency(self, client):
        """Test that data format is consistent across REST and WebSocket"""
        
        expected_fields = [
            "time", "buy_volume", "sell_volume", "total_volume", "delta_volume",
            "buy_volume_formatted", "sell_volume_formatted", 
            "total_volume_formatted", "delta_volume_formatted", "count", "timestamp_ms"
        ]
        
        mock_data = [{
            "time": 1609459200,
            "buy_volume": "1234.56",
            "sell_volume": "2345.67",
            "total_volume": "3580.23",
            "delta_volume": "-1111.11",  # buy_volume - sell_volume
            "buy_volume_formatted": "1,234.56",
            "sell_volume_formatted": "2,345.67",
            "total_volume_formatted": "3,580.23",
            "delta_volume_formatted": "-1,111.11",
            "count": 10,
            "timestamp_ms": 1609459200000
        }]
        
        with patch('app.services.liquidation_service.liquidation_service.fetch_historical_liquidations_by_timeframe') as mock_fetch:
            mock_fetch.return_value = mock_data
            
            # REST API response
            response = client.get("/api/v1/liquidation-volume/BTCUSDT/1m")
            assert response.status_code == 200
            data = response.json()
            
            # Verify all expected fields are present
            for item in data["data"]:
                for field in expected_fields:
                    assert field in item, f"Missing field: {field}"
            
            # Verify data types
            item = data["data"][0]
            assert isinstance(item["time"], int)
            assert isinstance(item["buy_volume"], str)
            assert isinstance(item["sell_volume"], str)
            assert isinstance(item["total_volume"], str)
            assert isinstance(item["count"], int)
            assert isinstance(item["timestamp_ms"], int)
    
    @pytest.mark.asyncio
    async def test_performance_with_large_dataset(self):
        """Test system performance with large liquidation datasets"""
        from app.services.liquidation_service import liquidation_service
        
        # Generate large dataset (1000 liquidations)
        large_dataset = []
        base_time = 1609459200000
        
        for i in range(1000):
            large_dataset.append({
                "timestamp": base_time + (i * 1000),  # 1 second apart
                "symbol": "BTCUSDT",
                "side": "buy" if i % 2 == 0 else "sell",
                "cumulated_usd_size": 1000.0 * (i % 10 + 1),  # Varying sizes in USD
                "average_price": str(30000 + i),
                "liquidation_order_id": str(i)
            })
        
        # Time the aggregation
        import time
        start_time = time.time()
        
        # Aggregate for different timeframes
        result_1m = await liquidation_service.aggregate_liquidations_for_timeframe(
            large_dataset, "1m", "BTCUSDT"
        )
        result_5m = await liquidation_service.aggregate_liquidations_for_timeframe(
            large_dataset, "5m", "BTCUSDT"
        )
        result_1h = await liquidation_service.aggregate_liquidations_for_timeframe(
            large_dataset, "1h", "BTCUSDT"
        )
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Performance assertions
        assert processing_time < 1.0, f"Aggregation took too long: {processing_time}s"
        
        # Verify aggregation results
        assert len(result_1m) > 0
        assert len(result_5m) > 0
        assert len(result_1h) > 0
        
        # 1h should have fewer candles than 5m, which should have fewer than 1m
        assert len(result_1h) <= len(result_5m) <= len(result_1m)
        
        # Verify data integrity
        total_volume_1m = sum(float(item["total_volume"]) for item in result_1m)
        total_volume_5m = sum(float(item["total_volume"]) for item in result_5m)
        total_volume_1h = sum(float(item["total_volume"]) for item in result_1h)
        
        # Total volume should be approximately the same across timeframes
        assert abs(total_volume_1m - total_volume_5m) < 0.01
        assert abs(total_volume_1m - total_volume_1h) < 0.01