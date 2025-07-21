"""
Tests for the Bot API endpoints.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from httpx import AsyncClient
from fastapi import status
from fastapi.testclient import TestClient
import json

from app.main import app
from app.models.bot import Bot, BotCreate, BotUpdate
from app.core.database import get_session


@pytest.mark.database
@pytest.mark.docker
class TestBotsAPI:
    """Test Bot API endpoints with real database."""
    
    @pytest_asyncio.fixture
    async def client(self, test_session):
        """Create an async test client with database session override."""
        async def override_get_session():
            yield test_session
        
        app.dependency_overrides[get_session] = override_get_session
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            yield client
        
        # Clean up
        app.dependency_overrides.clear()
    
    async def test_create_bot_success(self, client, test_session):
        """Test creating a bot successfully."""
        bot_data = {
            "name": "Test Bot",
            "symbol": "BTCUSDT",
            "isActive": True
        }
        
        response = await client.post("/api/v1/bots/", json=bot_data)
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "Test Bot"
        assert data["symbol"] == "BTCUSDT"
        assert data["isActive"] is True
        assert data["isPaperTrading"] is True  # Default value
        assert "id" in data
        assert "createdAt" in data
        assert "updatedAt" in data
    
    def test_create_bot_validation_error(self, client, test_session):
        """Test creating a bot with validation error."""
        bot_data = {
            "name": "",  # Empty name should fail
            "symbol": "BTCUSDT",
            "isActive": True
        }
        
        response = client.post("/api/v1/bots/", json=bot_data)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_create_bot_missing_fields(self, client, test_session):
        """Test creating a bot with missing required fields."""
        bot_data = {
            "name": "Test Bot"
            # Missing symbol and isActive
        }
        
        response = client.post("/api/v1/bots/", json=bot_data)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_get_bots_empty(self, client, test_session):
        """Test getting bots when database is empty."""
        response = client.get("/api/v1/bots/")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["bots"] == []
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["pageSize"] == 50
    
    def test_get_bots_with_data(self, client, test_session, multiple_bots):
        """Test getting bots with data."""
        response = client.get("/api/v1/bots/")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["bots"]) == 4
        assert data["total"] == 4
        assert data["page"] == 1
        assert data["pageSize"] == 50
        # Verify isPaperTrading field is included in list response
        for bot in data["bots"]:
            assert "isPaperTrading" in bot
    
    def test_get_bots_pagination(self, client, test_session, multiple_bots):
        """Test bot pagination."""
        response = client.get("/api/v1/bots/?page=1&page_size=2")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["bots"]) == 2
        assert data["total"] == 4
        assert data["page"] == 1
        assert data["pageSize"] == 2
    
    def test_get_bots_invalid_pagination(self, client, test_session):
        """Test bot pagination with invalid parameters."""
        response = client.get("/api/v1/bots/?page=0&page_size=200")
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_get_bot_success(self, client, test_session, sample_bot):
        """Test getting a specific bot."""
        response = client.get(f"/api/v1/bots/{sample_bot.id}")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == str(sample_bot.id)
        assert data["name"] == sample_bot.name
        assert data["symbol"] == sample_bot.symbol
        assert data["isActive"] == sample_bot.is_active
        assert "isPaperTrading" in data  # Field should be present
    
    def test_get_bot_not_found(self, client, test_session):
        """Test getting a non-existent bot."""
        fake_id = uuid4()
        response = client.get(f"/api/v1/bots/{fake_id}")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["detail"] == "Bot not found"
    
    def test_get_bot_invalid_uuid(self, client, test_session):
        """Test getting a bot with invalid UUID."""
        response = client.get("/api/v1/bots/invalid-uuid")
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_update_bot_success(self, client, test_session, sample_bot):
        """Test updating a bot successfully."""
        update_data = {
            "name": "Updated Bot",
            "isActive": False,
            "isPaperTrading": False
        }
        
        response = client.patch(f"/api/v1/bots/{sample_bot.id}", json=update_data)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Updated Bot"
        assert data["isActive"] is False
        assert data["isPaperTrading"] is False
        assert data["symbol"] == sample_bot.symbol  # Unchanged
    
    def test_update_bot_not_found(self, client, test_session):
        """Test updating a non-existent bot."""
        fake_id = uuid4()
        update_data = {"name": "Updated Bot"}
        
        response = client.patch(f"/api/v1/bots/{fake_id}", json=update_data)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["detail"] == "Bot not found"
    
    def test_update_bot_validation_error(self, client, test_session, sample_bot):
        """Test updating a bot with validation error."""
        update_data = {
            "name": "",  # Empty name should fail
        }
        
        response = client.patch(f"/api/v1/bots/{sample_bot.id}", json=update_data)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_delete_bot_success(self, client, test_session, sample_bot):
        """Test deleting a bot successfully."""
        bot_id = sample_bot.id
        
        response = client.delete(f"/api/v1/bots/{bot_id}")
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # Verify bot is deleted
        get_response = client.get(f"/api/v1/bots/{bot_id}")
        assert get_response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_delete_bot_not_found(self, client, test_session):
        """Test deleting a non-existent bot."""
        fake_id = uuid4()
        
        response = client.delete(f"/api/v1/bots/{fake_id}")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["detail"] == "Bot not found"
    
    def test_get_active_symbols_empty(self, client, test_session):
        """Test getting active symbols when no bots exist."""
        response = client.get("/api/v1/bots/symbols/active")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data == []
    
    def test_get_active_symbols_with_data(self, client, test_session, multiple_bots):
        """Test getting active symbols with data."""
        response = client.get("/api/v1/bots/symbols/active")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
        assert "BTCUSDT" in data
        assert "ETHUSDT" in data
        assert "ADAUSDT" not in data  # Inactive
    
    def test_get_bot_stats_by_symbol(self, client, test_session, multiple_bots):
        """Test getting bot statistics by symbol."""
        response = client.get("/api/v1/bots/symbols/stats")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 3
        
        # Find stats for each symbol
        btc_stats = next(s for s in data if s["symbol"] == "BTCUSDT")
        eth_stats = next(s for s in data if s["symbol"] == "ETHUSDT")
        ada_stats = next(s for s in data if s["symbol"] == "ADAUSDT")
        
        assert btc_stats["totalCount"] == 2
        assert btc_stats["activeCount"] == 1
        assert eth_stats["totalCount"] == 1
        assert eth_stats["activeCount"] == 1
        assert ada_stats["totalCount"] == 1
        assert ada_stats["activeCount"] == 0
    
    def test_get_bots_by_symbol_all(self, client, test_session, multiple_bots):
        """Test getting all bots by symbol."""
        response = client.get("/api/v1/bots/symbols/BTCUSDT")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
        for bot in data:
            assert bot["symbol"] == "BTCUSDT"
    
    def test_get_bots_by_symbol_active_only(self, client, test_session, multiple_bots):
        """Test getting active bots by symbol."""
        response = client.get("/api/v1/bots/symbols/BTCUSDT?active_only=true")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["symbol"] == "BTCUSDT"
        assert data[0]["isActive"] is True
    
    def test_get_bots_by_symbol_none_found(self, client, test_session, multiple_bots):
        """Test getting bots by symbol when none exist."""
        response = client.get("/api/v1/bots/symbols/NONEXISTENT")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 0
    
    def test_update_bot_status_success(self, client, test_session, sample_bot):
        """Test updating bot status successfully."""
        response = client.patch(f"/api/v1/bots/{sample_bot.id}/status?is_active=false")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["isActive"] is False
        assert data["id"] == str(sample_bot.id)
    
    def test_update_bot_status_not_found(self, client, test_session):
        """Test updating status for non-existent bot."""
        fake_id = uuid4()
        response = client.patch(f"/api/v1/bots/{fake_id}/status?is_active=false")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["detail"] == "Bot not found"
    
    def test_update_bot_status_missing_parameter(self, client, test_session, sample_bot):
        """Test updating bot status without required parameter."""
        response = client.patch(f"/api/v1/bots/{sample_bot.id}/status")
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_health_check_success(self, client, test_session, multiple_bots):
        """Test health check endpoint."""
        response = client.get("/api/v1/bots/health")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
    
    async def test_bot_paper_trading_toggle(self, client, test_session):
        """Test toggling paper trading mode on a bot."""
        # Create a bot with paper trading enabled (default)
        bot_data = {
            "name": "Paper Trading Bot",
            "symbol": "BTCUSDT",
            "isActive": True
        }
        
        create_response = await client.post("/api/v1/bots/", json=bot_data)
        assert create_response.status_code == status.HTTP_201_CREATED
        bot_id = create_response.json()["id"]
        assert create_response.json()["isPaperTrading"] is True
        
        # Toggle to live trading
        update_data = {"isPaperTrading": False}
        update_response = await client.patch(f"/api/v1/bots/{bot_id}", json=update_data)
        assert update_response.status_code == status.HTTP_200_OK
        assert update_response.json()["isPaperTrading"] is False
        
        # Toggle back to paper trading
        update_data2 = {"isPaperTrading": True}
        update_response2 = await client.patch(f"/api/v1/bots/{bot_id}", json=update_data2)
        assert update_response2.status_code == status.HTTP_200_OK
        assert update_response2.json()["isPaperTrading"] is True
    
    def test_api_error_handling(self, client, test_session):
        """Test API error handling with various scenarios."""
        # Test invalid JSON
        response = client.post("/api/v1/bots/", data="invalid json")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Test unsupported HTTP method
        response = client.put("/api/v1/bots/")
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
    
    def test_concurrent_bot_operations(self, client, test_session):
        """Test concurrent bot operations."""
        import concurrent.futures
        import threading
        
        def create_bot(name_suffix):
            bot_data = {
                "name": f"Concurrent Bot {name_suffix}",
                "symbol": "BTCUSDT",
                "isActive": True
            }
            response = client.post("/api/v1/bots/", json=bot_data)
            return response.status_code == status.HTTP_201_CREATED
        
        # Create multiple bots concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(create_bot, i) for i in range(5)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # All should succeed
        assert all(results)
        
        # Verify all bots were created
        response = client.get("/api/v1/bots/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 5
    
    async def test_bot_paper_trading_toggle(self, client, test_session, sample_bot):
        """Test toggling paper trading mode on a bot."""
        # First verify bot defaults to paper trading
        response = await client.get(f"/api/v1/bots/{sample_bot.id}")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["isPaperTrading"] is True
        
        # Toggle to live trading
        update_data = {"isPaperTrading": False}
        response = await client.patch(f"/api/v1/bots/{sample_bot.id}", json=update_data)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["isPaperTrading"] is False
        
        # Toggle back to paper trading
        update_data = {"isPaperTrading": True}
        response = await client.patch(f"/api/v1/bots/{sample_bot.id}", json=update_data)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["isPaperTrading"] is True


@pytest.mark.asyncio
class TestBotsAPIUnit:
    """Unit tests for Bot API endpoints without database."""
    
    def test_endpoint_paths(self):
        """Test that all expected endpoints are available."""
        with TestClient(app) as client:
            # Test that endpoints return appropriate responses (even if they fail due to missing DB)
            # This tests that the routes are properly registered
            
            # Should return 500 (internal server error) due to missing database, not 404
            response = client.get("/api/v1/bots/")
            assert response.status_code != status.HTTP_404_NOT_FOUND
            
            response = client.get("/api/v1/bots/symbols/active")
            assert response.status_code != status.HTTP_404_NOT_FOUND
            
            response = client.get("/api/v1/bots/symbols/stats")
            assert response.status_code != status.HTTP_404_NOT_FOUND
            
            response = client.get("/api/v1/bots/health")
            assert response.status_code != status.HTTP_404_NOT_FOUND
    
    def test_response_models(self):
        """Test that response models are correctly configured."""
        from app.api.v1.endpoints.bots import router
        
        # Check that all routes have proper response models
        routes = [route for route in router.routes if hasattr(route, 'response_model')]
        
        # Verify key routes have response models
        route_paths = [route.path for route in routes]
        assert "/" in route_paths  # create_bot and get_bots
        assert "/{bot_id}" in route_paths  # get_bot, update_bot, delete_bot
        assert "/symbols/active" in route_paths
        assert "/symbols/stats" in route_paths
        assert "/symbols/{symbol}" in route_paths
        assert "/{bot_id}/status" in route_paths
        assert "/health" in route_paths
    
    @patch('app.api.v1.endpoints.bots.bot_service')
    @patch('app.api.v1.endpoints.bots.data_stream_manager')
    def test_error_handling_in_endpoints(self, mock_stream_manager, mock_bot_service):
        """Test error handling in endpoints."""
        # Mock services to raise exceptions
        mock_bot_service.get_all_bots.side_effect = Exception("Database error")
        mock_stream_manager.update_active_streams.side_effect = Exception("Stream error")
        
        with TestClient(app) as client:
            # Override the database dependency
            def mock_get_session():
                return MagicMock()
            
            app.dependency_overrides[get_session] = mock_get_session
            
            try:
                response = client.get("/api/v1/bots/")
                assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
                assert "Internal server error" in response.json()["detail"]
            finally:
                app.dependency_overrides.clear()
    
    def test_request_validation(self):
        """Test request validation for various endpoints."""
        with TestClient(app) as client:
            # Test invalid UUID format
            response = client.get("/api/v1/bots/invalid-uuid")
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
            
            # Test invalid query parameters
            response = client.get("/api/v1/bots/?page=-1")
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
            
            response = client.get("/api/v1/bots/?page_size=1000")
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY