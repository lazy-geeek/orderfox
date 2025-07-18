"""
Simple tests for Bot API endpoints with proper database integration.
"""

import pytest
from fastapi.testclient import TestClient
from fastapi import status
from uuid import uuid4
from unittest.mock import AsyncMock, patch

from app.main import app
from app.models.bot import BotCreate, BotUpdate
from app.core.database import get_session


class TestBotsAPISimple:
    """Simple tests for Bot API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create a test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        session = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.refresh = AsyncMock()
        session.close = AsyncMock()
        return session
    
    @pytest.fixture
    def mock_bot_service(self):
        """Create a mock bot service."""
        with patch('app.api.v1.endpoints.bots.bot_service') as mock:
            yield mock
    
    @pytest.fixture
    def mock_stream_manager(self):
        """Create a mock data stream manager."""
        with patch('app.api.v1.endpoints.bots.data_stream_manager') as mock:
            yield mock
    
    @pytest.fixture
    def override_db_session(self, mock_session):
        """Override database session dependency."""
        def get_test_session():
            return mock_session
        
        app.dependency_overrides[get_session] = get_test_session
        yield
        app.dependency_overrides.clear()
    
    def test_create_bot_success(self, client, mock_bot_service, mock_stream_manager, override_db_session):
        """Test creating a bot successfully."""
        # Mock bot service response
        mock_bot_service.create_bot.return_value = AsyncMock(
            id=uuid4(),
            name="Test Bot",
            symbol="BTCUSDT",
            is_active=True,
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z"
        )
        
        bot_data = {
            "name": "Test Bot",
            "symbol": "BTCUSDT",
            "isActive": True
        }
        
        response = client.post("/api/v1/bots/", json=bot_data)
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "Test Bot"
        assert data["symbol"] == "BTCUSDT"
        assert data["isActive"] is True
        
        # Verify service was called
        mock_bot_service.create_bot.assert_called_once()
        mock_stream_manager.update_active_streams.assert_called_once()
    
    def test_create_bot_validation_error(self, client, override_db_session):
        """Test creating a bot with validation error."""
        bot_data = {
            "name": "",  # Empty name should fail
            "symbol": "BTCUSDT",
            "isActive": True
        }
        
        response = client.post("/api/v1/bots/", json=bot_data)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_create_bot_missing_fields(self, client, override_db_session):
        """Test creating a bot with missing required fields."""
        bot_data = {
            "name": "Test Bot"
            # Missing symbol
        }
        
        response = client.post("/api/v1/bots/", json=bot_data)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_get_bots_success(self, client, mock_bot_service, override_db_session):
        """Test getting bots successfully."""
        # Mock bot service response
        mock_bot_service.get_all_bots.return_value = AsyncMock(
            bots=[],
            total=0,
            page=1,
            page_size=50
        )
        
        response = client.get("/api/v1/bots/")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["bots"] == []
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["pageSize"] == 50
        
        # Verify service was called
        mock_bot_service.get_all_bots.assert_called_once()
    
    def test_get_bot_success(self, client, mock_bot_service, override_db_session):
        """Test getting a specific bot successfully."""
        bot_id = uuid4()
        
        # Mock bot service response
        mock_bot_service.get_bot.return_value = AsyncMock(
            id=bot_id,
            name="Test Bot",
            symbol="BTCUSDT",
            is_active=True
        )
        
        response = client.get(f"/api/v1/bots/{bot_id}")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == str(bot_id)
        assert data["name"] == "Test Bot"
        assert data["symbol"] == "BTCUSDT"
        assert data["isActive"] is True
        
        # Verify service was called
        mock_bot_service.get_bot.assert_called_once_with(bot_id, mock_session=None)
    
    def test_get_bot_not_found(self, client, mock_bot_service, override_db_session):
        """Test getting a non-existent bot."""
        bot_id = uuid4()
        
        # Mock bot service to return None
        mock_bot_service.get_bot.return_value = None
        
        response = client.get(f"/api/v1/bots/{bot_id}")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["detail"] == "Bot not found"
    
    def test_update_bot_success(self, client, mock_bot_service, mock_stream_manager, override_db_session):
        """Test updating a bot successfully."""
        bot_id = uuid4()
        
        # Mock bot service responses
        mock_bot_service.get_bot.return_value = AsyncMock(
            id=bot_id,
            name="Original Bot",
            symbol="BTCUSDT",
            is_active=True
        )
        
        mock_bot_service.update_bot.return_value = AsyncMock(
            id=bot_id,
            name="Updated Bot",
            symbol="BTCUSDT",
            is_active=False
        )
        
        update_data = {
            "name": "Updated Bot",
            "isActive": False
        }
        
        response = client.patch(f"/api/v1/bots/{bot_id}", json=update_data)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Updated Bot"
        assert data["isActive"] is False
        
        # Verify services were called
        mock_bot_service.get_bot.assert_called_once()
        mock_bot_service.update_bot.assert_called_once()
        mock_stream_manager.update_active_streams.assert_called_once()
    
    def test_update_bot_not_found(self, client, mock_bot_service, override_db_session):
        """Test updating a non-existent bot."""
        bot_id = uuid4()
        
        # Mock bot service to return None
        mock_bot_service.get_bot.return_value = None
        
        update_data = {"name": "Updated Bot"}
        
        response = client.patch(f"/api/v1/bots/{bot_id}", json=update_data)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["detail"] == "Bot not found"
    
    def test_delete_bot_success(self, client, mock_bot_service, mock_stream_manager, override_db_session):
        """Test deleting a bot successfully."""
        bot_id = uuid4()
        
        # Mock bot service responses
        mock_bot_service.get_bot.return_value = AsyncMock(
            id=bot_id,
            name="Test Bot",
            symbol="BTCUSDT",
            is_active=True
        )
        
        mock_bot_service.delete_bot.return_value = True
        
        response = client.delete(f"/api/v1/bots/{bot_id}")
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # Verify services were called
        mock_bot_service.get_bot.assert_called_once()
        mock_bot_service.delete_bot.assert_called_once()
        mock_stream_manager.update_active_streams.assert_called_once()
    
    def test_delete_bot_not_found(self, client, mock_bot_service, override_db_session):
        """Test deleting a non-existent bot."""
        bot_id = uuid4()
        
        # Mock bot service to return None
        mock_bot_service.get_bot.return_value = None
        
        response = client.delete(f"/api/v1/bots/{bot_id}")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["detail"] == "Bot not found"
    
    def test_get_active_symbols(self, client, mock_bot_service, override_db_session):
        """Test getting active symbols."""
        # Mock bot service response
        mock_bot_service.get_active_symbols.return_value = ["BTCUSDT", "ETHUSDT"]
        
        response = client.get("/api/v1/bots/symbols/active")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data == ["BTCUSDT", "ETHUSDT"]
        
        # Verify service was called
        mock_bot_service.get_active_symbols.assert_called_once()
    
    def test_get_bot_stats_by_symbol(self, client, mock_bot_service, override_db_session):
        """Test getting bot statistics by symbol."""
        # Mock bot service response
        mock_bot_service.get_bot_stats_by_symbol.return_value = [
            AsyncMock(symbol="BTCUSDT", total_count=2, active_count=1),
            AsyncMock(symbol="ETHUSDT", total_count=1, active_count=1)
        ]
        
        response = client.get("/api/v1/bots/symbols/stats")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
        
        # Verify service was called
        mock_bot_service.get_bot_stats_by_symbol.assert_called_once()
    
    def test_get_bots_by_symbol(self, client, mock_bot_service, override_db_session):
        """Test getting bots by symbol."""
        # Mock bot service response
        mock_bot_service.get_bots_by_symbol.return_value = [
            AsyncMock(id=uuid4(), name="Bot 1", symbol="BTCUSDT", is_active=True)
        ]
        
        response = client.get("/api/v1/bots/symbols/BTCUSDT")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["symbol"] == "BTCUSDT"
        
        # Verify service was called
        mock_bot_service.get_bots_by_symbol.assert_called_once_with("BTCUSDT", mock_session=None, active_only=False)
    
    def test_update_bot_status(self, client, mock_bot_service, mock_stream_manager, override_db_session):
        """Test updating bot status."""
        bot_id = uuid4()
        
        # Mock bot service response
        mock_bot_service.set_bot_active_status.return_value = AsyncMock(
            id=bot_id,
            name="Test Bot",
            symbol="BTCUSDT",
            is_active=False
        )
        
        response = client.patch(f"/api/v1/bots/{bot_id}/status?is_active=false")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["isActive"] is False
        
        # Verify services were called
        mock_bot_service.set_bot_active_status.assert_called_once_with(bot_id, False, mock_session=None)
        mock_stream_manager.update_active_streams.assert_called_once()
    
    def test_update_bot_status_not_found(self, client, mock_bot_service, override_db_session):
        """Test updating status for non-existent bot."""
        bot_id = uuid4()
        
        # Mock bot service to return None
        mock_bot_service.set_bot_active_status.return_value = None
        
        response = client.patch(f"/api/v1/bots/{bot_id}/status?is_active=false")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["detail"] == "Bot not found"
    
    def test_health_check(self, client, mock_bot_service, mock_stream_manager, override_db_session):
        """Test health check endpoint."""
        # Mock service responses
        mock_bot_service.get_bot_stats_by_symbol.return_value = [
            AsyncMock(symbol="BTCUSDT", total_count=2, active_count=1)
        ]
        
        mock_bot_service.get_cache_stats.return_value = {
            "bot_cache_size": 10,
            "bot_cache_maxsize": 100
        }
        
        mock_stream_manager.health_check.return_value = {
            "status": "healthy",
            "active_streams": 2,
            "timestamp": 1234567890
        }
        
        response = client.get("/api/v1/bots/health")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert "bot_service" in data
        assert "data_stream_manager" in data
        assert "timestamp" in data
    
    def test_invalid_uuid_format(self, client, override_db_session):
        """Test endpoints with invalid UUID format."""
        response = client.get("/api/v1/bots/invalid-uuid")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        response = client.patch("/api/v1/bots/invalid-uuid", json={"name": "Test"})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        response = client.delete("/api/v1/bots/invalid-uuid")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_pagination_validation(self, client, override_db_session):
        """Test pagination parameter validation."""
        # Invalid page number
        response = client.get("/api/v1/bots/?page=0")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Invalid page size
        response = client.get("/api/v1/bots/?page_size=1000")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_missing_required_query_params(self, client, override_db_session):
        """Test endpoints missing required query parameters."""
        bot_id = uuid4()
        
        # Missing is_active parameter
        response = client.patch(f"/api/v1/bots/{bot_id}/status")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_error_handling_service_exceptions(self, client, mock_bot_service, override_db_session):
        """Test error handling when services raise exceptions."""
        # Mock service to raise an exception
        mock_bot_service.get_all_bots.side_effect = Exception("Database error")
        
        response = client.get("/api/v1/bots/")
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert data["detail"] == "Internal server error"