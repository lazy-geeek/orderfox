"""
Unit tests for database module.

This module contains tests for Firebase initialization and database helper functions.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import json

from app.core.db import (
    initialize_firebase,
    get_db,
    save_settings,
    load_settings,
    save_paper_trade,
    load_paper_trade_history,
)


class TestFirebaseInitialization:
    """Test Firebase initialization functionality."""

    def setup_method(self):
        """Setup test environment."""
        # Reset global db variable before each test
        import app.core.db

        app.core.db.db = None

    @patch("app.core.db.settings")
    @patch("app.core.db.firebase_admin")
    @patch("app.core.db.credentials")
    @patch("app.core.db.firestore")
    @patch("builtins.print")
    def test_initialize_firebase_success(
        self,
        mock_print,
        mock_firestore,
        mock_credentials,
        mock_firebase_admin,
        mock_settings,
    ):
        """Test successful Firebase initialization."""
        # Setup mocks
        mock_settings.FIREBASE_CONFIG_JSON = (
            '{"project_id": "test-project", "private_key": "test-key"}'
        )
        mock_firebase_admin._apps = {}  # Empty apps dict
        mock_cred = MagicMock()
        mock_credentials.Certificate.return_value = mock_cred
        mock_db_client = MagicMock()
        mock_firestore.client.return_value = mock_db_client

        # Call function
        initialize_firebase()

        # Assertions
        mock_credentials.Certificate.assert_called_once()
        mock_firebase_admin.initialize_app.assert_called_once_with(mock_cred)
        mock_firestore.client.assert_called_once()

        # Check that success message was printed
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        success_message_found = any(
            "Firebase Admin SDK initialized successfully" in call
            for call in print_calls
        )
        assert success_message_found

    @patch("app.core.db.settings")
    @patch("app.core.db.firebase_admin")
    @patch("app.core.db.firestore")
    @patch("builtins.print")
    def test_initialize_firebase_already_initialized(
        self, mock_print, mock_firestore, mock_firebase_admin, mock_settings
    ):
        """Test Firebase initialization when already initialized."""
        # Setup mocks
        mock_settings.FIREBASE_CONFIG_JSON = '{"project_id": "test-project"}'
        mock_firebase_admin._apps = {"default": MagicMock()}  # Non-empty apps dict
        mock_app = MagicMock()
        mock_firebase_admin.get_app.return_value = mock_app
        mock_db_client = MagicMock()
        mock_firestore.client.return_value = mock_db_client

        # Call function
        initialize_firebase()

        # Assertions
        mock_firebase_admin.initialize_app.assert_not_called()
        mock_firebase_admin.get_app.assert_called_once()
        mock_firestore.client.assert_called_once_with(mock_app)

        # Check that already initialized message was printed
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        already_init_message_found = any(
            "already initialized" in call for call in print_calls
        )
        assert already_init_message_found

    @patch("app.core.db.settings")
    @patch("builtins.print")
    def test_initialize_firebase_no_config(self, mock_print, mock_settings):
        """Test Firebase initialization with no config."""
        # Setup mocks
        mock_settings.FIREBASE_CONFIG_JSON = None

        # Call function
        initialize_firebase()

        # Check that no config message was printed
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        no_config_message_found = any(
            "FIREBASE_CONFIG_JSON not found" in call for call in print_calls
        )
        assert no_config_message_found

    @patch("app.core.db.settings")
    @patch("builtins.print")
    def test_initialize_firebase_invalid_json(self, mock_print, mock_settings):
        """Test Firebase initialization with invalid JSON."""
        # Setup mocks
        mock_settings.FIREBASE_CONFIG_JSON = "invalid json string"

        # Call function
        initialize_firebase()

        # Check that JSON error message was printed
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        json_error_message_found = any(
            "not a valid JSON string" in call for call in print_calls
        )
        assert json_error_message_found

    @patch("app.core.db.settings")
    @patch("app.core.db.firebase_admin")
    @patch("app.core.db.credentials")
    @patch("builtins.print")
    def test_initialize_firebase_credentials_error(
        self, mock_print, mock_credentials, mock_firebase_admin, mock_settings
    ):
        """Test Firebase initialization with credentials error."""
        # Setup mocks
        mock_settings.FIREBASE_CONFIG_JSON = '{"project_id": "test-project"}'
        mock_firebase_admin._apps = {}
        mock_credentials.Certificate.side_effect = ValueError("Invalid credentials")

        # Call function
        initialize_firebase()

        # Check that credentials error message was printed
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        cred_error_message_found = any(
            "Error initializing Firebase Admin SDK" in call for call in print_calls
        )
        assert cred_error_message_found

    @patch("app.core.db.settings")
    @patch("app.core.db.firebase_admin")
    @patch("app.core.db.credentials")
    @patch("builtins.print")
    def test_initialize_firebase_unexpected_error(
        self, mock_print, mock_credentials, mock_firebase_admin, mock_settings
    ):
        """Test Firebase initialization with unexpected error."""
        # Setup mocks
        mock_settings.FIREBASE_CONFIG_JSON = '{"project_id": "test-project"}'
        mock_firebase_admin._apps = {}
        mock_credentials.Certificate.side_effect = RuntimeError("Unexpected error")

        # Call function
        initialize_firebase()

        # Check that unexpected error message was printed
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        unexpected_error_message_found = any(
            "unexpected error occurred" in call for call in print_calls
        )
        assert unexpected_error_message_found


class TestGetDb:
    """Test get_db functionality."""

    def setup_method(self):
        """Setup test environment."""
        import app.core.db

        app.core.db.db = None

    @patch("app.core.db.db", MagicMock())
    def test_get_db_returns_existing_client(self):
        """Test get_db returns existing database client."""
        import app.core.db

        mock_db_client = MagicMock()
        app.core.db.db = mock_db_client

        result = get_db()

        assert result == mock_db_client

    @patch("app.core.db.settings")
    @patch("app.core.db.initialize_firebase")
    @patch("builtins.print")
    def test_get_db_reinitializes_when_none_and_config_exists(
        self, mock_print, mock_initialize, mock_settings
    ):
        """Test get_db reinitializes when db is None but config exists."""
        import app.core.db

        app.core.db.db = None
        mock_settings.FIREBASE_CONFIG_JSON = '{"project_id": "test"}'

        get_db()

        mock_initialize.assert_called_once()
        # Check that re-initialization message was printed
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        reinit_message_found = any(
            "Attempting to re-initialize Firebase" in call for call in print_calls
        )
        assert reinit_message_found

    @patch("app.core.db.settings")
    def test_get_db_returns_none_when_no_config(self, mock_settings):
        """Test get_db returns None when no config exists."""
        import app.core.db

        app.core.db.db = None
        mock_settings.FIREBASE_CONFIG_JSON = None

        result = get_db()

        assert result is None


class TestSaveSettings:
    """Test save_settings functionality."""

    @pytest.mark.asyncio
    @patch("app.core.db.get_db")
    @patch("builtins.print")
    async def test_save_settings_success(self, mock_print, mock_get_db):
        """Test successful settings save."""
        # Setup mocks
        mock_db_client = MagicMock()
        mock_get_db.return_value = mock_db_client
        mock_doc_ref = AsyncMock()
        mock_db_client.collection.return_value.document.return_value.collection.return_value.document.return_value = (
            mock_doc_ref
        )

        user_settings = {"theme": "dark", "notifications": True}

        # Call function
        result = await save_settings("user123", user_settings)

        # Assertions
        assert result is True
        mock_doc_ref.set.assert_called_once_with(user_settings, merge=True)

        # Check that success message was printed
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        success_message_found = any(
            "Settings saved for user user123" in call for call in print_calls
        )
        assert success_message_found

    @pytest.mark.asyncio
    @patch("app.core.db.get_db")
    @patch("builtins.print")
    async def test_save_settings_no_db(self, mock_print, mock_get_db):
        """Test save_settings when database is not initialized."""
        mock_get_db.return_value = None

        result = await save_settings("user123", {"test": "data"})

        assert result is False

        # Check that error message was printed
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        error_message_found = any(
            "Firestore not initialized" in call for call in print_calls
        )
        assert error_message_found

    @pytest.mark.asyncio
    @patch("app.core.db.get_db")
    @patch("builtins.print")
    async def test_save_settings_exception(self, mock_print, mock_get_db):
        """Test save_settings with exception during save."""
        # Setup mocks
        mock_db_client = MagicMock()
        mock_get_db.return_value = mock_db_client
        mock_doc_ref = AsyncMock()
        mock_doc_ref.set.side_effect = Exception("Database error")
        mock_db_client.collection.return_value.document.return_value.collection.return_value.document.return_value = (
            mock_doc_ref
        )

        result = await save_settings("user123", {"test": "data"})

        assert result is False

        # Check that error message was printed
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        error_message_found = any(
            "Error saving settings for user user123" in call for call in print_calls
        )
        assert error_message_found


class TestLoadSettings:
    """Test load_settings functionality."""

    @pytest.mark.asyncio
    @patch("app.core.db.get_db")
    @patch("builtins.print")
    async def test_load_settings_success(self, mock_print, mock_get_db):
        """Test successful settings load."""
        # Setup mocks
        mock_db_client = MagicMock()
        mock_get_db.return_value = mock_db_client
        mock_doc_ref = AsyncMock()
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {"theme": "dark", "notifications": True}
        mock_doc_ref.get.return_value = mock_doc
        mock_db_client.collection.return_value.document.return_value.collection.return_value.document.return_value = (
            mock_doc_ref
        )

        # Call function
        result = await load_settings("user123")

        # Assertions
        assert result == {"theme": "dark", "notifications": True}
        mock_doc_ref.get.assert_called_once()

        # Check that success message was printed
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        success_message_found = any(
            "Settings loaded for user user123" in call for call in print_calls
        )
        assert success_message_found

    @pytest.mark.asyncio
    @patch("app.core.db.get_db")
    @patch("builtins.print")
    async def test_load_settings_not_found(self, mock_print, mock_get_db):
        """Test load_settings when settings don't exist."""
        # Setup mocks
        mock_db_client = MagicMock()
        mock_get_db.return_value = mock_db_client
        mock_doc_ref = AsyncMock()
        mock_doc = MagicMock()
        mock_doc.exists = False
        mock_doc_ref.get.return_value = mock_doc
        mock_db_client.collection.return_value.document.return_value.collection.return_value.document.return_value = (
            mock_doc_ref
        )

        result = await load_settings("user123")

        assert result is None

        # Check that not found message was printed
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        not_found_message_found = any(
            "No settings found for user user123" in call for call in print_calls
        )
        assert not_found_message_found

    @pytest.mark.asyncio
    @patch("app.core.db.get_db")
    @patch("builtins.print")
    async def test_load_settings_no_db(self, mock_print, mock_get_db):
        """Test load_settings when database is not initialized."""
        mock_get_db.return_value = None

        result = await load_settings("user123")

        assert result is None

        # Check that error message was printed
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        error_message_found = any(
            "Firestore not initialized" in call for call in print_calls
        )
        assert error_message_found


class TestSavePaperTrade:
    """Test save_paper_trade functionality."""

    @pytest.mark.asyncio
    @patch("app.core.db.get_db")
    @patch("app.core.db.firestore")
    @patch("builtins.print")
    async def test_save_paper_trade_success(
        self, mock_print, mock_firestore, mock_get_db
    ):
        """Test successful paper trade save."""
        # Setup mocks
        mock_db_client = MagicMock()
        mock_get_db.return_value = mock_db_client
        mock_firestore.SERVER_TIMESTAMP = "server_timestamp"
        mock_doc_ref = MagicMock()
        mock_doc_ref.id = "trade_123"
        mock_collection = AsyncMock()
        mock_collection.add.return_value = mock_doc_ref
        mock_db_client.collection.return_value.document.return_value.collection.return_value = (
            mock_collection
        )

        trade_data = {"symbol": "BTCUSDT", "side": "buy", "amount": 0.1}

        # Call function
        result = await save_paper_trade("user123", trade_data)

        # Assertions
        assert result == "trade_123"
        expected_trade_data = {**trade_data, "timestamp": "server_timestamp"}
        mock_collection.add.assert_called_once_with(expected_trade_data)

        # Check that success message was printed
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        success_message_found = any(
            "Paper trade saved for user user123 with ID: trade_123" in call
            for call in print_calls
        )
        assert success_message_found

    @pytest.mark.asyncio
    @patch("app.core.db.get_db")
    @patch("builtins.print")
    async def test_save_paper_trade_no_db(self, mock_print, mock_get_db):
        """Test save_paper_trade when database is not initialized."""
        mock_get_db.return_value = None

        result = await save_paper_trade("user123", {"test": "data"})

        assert result is None

        # Check that error message was printed
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        error_message_found = any(
            "Firestore not initialized" in call for call in print_calls
        )
        assert error_message_found


class TestLoadPaperTradeHistory:
    """Test load_paper_trade_history functionality."""

    @pytest.mark.asyncio
    @patch("app.core.db.get_db")
    @patch("app.core.db.firestore")
    @patch("builtins.print")
    async def test_load_paper_trade_history_success(
        self, mock_print, mock_firestore, mock_get_db
    ):
        """Test successful paper trade history load."""
        # Setup mocks
        mock_db_client = MagicMock()
        mock_get_db.return_value = mock_db_client

        # Mock documents
        mock_doc1 = MagicMock()
        mock_doc1.id = "trade_1"
        mock_doc1.to_dict.return_value = {"symbol": "BTCUSDT", "side": "buy"}

        mock_doc2 = MagicMock()
        mock_doc2.id = "trade_2"
        mock_doc2.to_dict.return_value = {"symbol": "ETHUSDT", "side": "sell"}

        # Mock async iterator
        async def mock_stream():
            yield mock_doc1
            yield mock_doc2

        mock_query = AsyncMock()
        mock_query.stream.return_value = mock_stream()
        mock_trades_ref = MagicMock()
        mock_trades_ref.order_by.return_value.limit.return_value = mock_query
        mock_db_client.collection.return_value.document.return_value.collection.return_value = (
            mock_trades_ref
        )

        # Call function
        result = await load_paper_trade_history("user123", limit=10)

        # Assertions
        assert len(result) == 2
        assert result[0]["symbol"] == "BTCUSDT"
        assert result[0]["id"] == "trade_1"
        assert result[1]["symbol"] == "ETHUSDT"
        assert result[1]["id"] == "trade_2"

        # Check that success message was printed
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        success_message_found = any(
            "Loaded 2 paper trades for user user123" in call for call in print_calls
        )
        assert success_message_found

    @pytest.mark.asyncio
    @patch("app.core.db.get_db")
    @patch("builtins.print")
    async def test_load_paper_trade_history_no_db(self, mock_print, mock_get_db):
        """Test load_paper_trade_history when database is not initialized."""
        mock_get_db.return_value = None

        result = await load_paper_trade_history("user123")

        assert result == []

        # Check that error message was printed
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        error_message_found = any(
            "Firestore not initialized" in call for call in print_calls
        )
        assert error_message_found

    @pytest.mark.asyncio
    @patch("app.core.db.get_db")
    @patch("builtins.print")
    async def test_load_paper_trade_history_exception(self, mock_print, mock_get_db):
        """Test load_paper_trade_history with exception during load."""
        # Setup mocks
        mock_db_client = MagicMock()
        mock_get_db.return_value = mock_db_client
        mock_trades_ref = MagicMock()
        mock_trades_ref.order_by.side_effect = Exception("Database error")
        mock_db_client.collection.return_value.document.return_value.collection.return_value = (
            mock_trades_ref
        )

        result = await load_paper_trade_history("user123")

        assert result == []

        # Check that error message was printed
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        error_message_found = any(
            "Error loading paper trade history for user user123" in call
            for call in print_calls
        )
        assert error_message_found


class TestDatabaseEdgeCases:
    """Test edge cases and integration scenarios."""

    @pytest.mark.asyncio
    async def test_empty_user_id_handling(self):
        """Test functions handle empty user IDs gracefully."""
        # These should not raise exceptions
        result1 = await save_settings("", {"test": "data"})
        result2 = await load_settings("")
        result3 = await save_paper_trade("", {"test": "data"})
        result4 = await load_paper_trade_history("")

        # All should return appropriate failure values
        assert result1 is False
        assert result2 is None
        assert result3 is None
        assert result4 == []

    @pytest.mark.asyncio
    @patch("app.core.db.get_db")
    async def test_large_data_handling(self, mock_get_db):
        """Test handling of large data structures."""
        mock_get_db.return_value = None  # Simulate no DB to avoid actual operations

        # Create large data structure
        large_settings = {f"key_{i}": f"value_{i}" * 100 for i in range(1000)}

        # Should handle gracefully
        result = await save_settings("user123", large_settings)
        assert result is False  # Due to no DB, but shouldn't crash

    @pytest.mark.asyncio
    async def test_special_characters_in_user_id(self):
        """Test handling of special characters in user IDs."""
        special_user_ids = [
            "user@example.com",
            "user-with-dashes",
            "user_with_underscores",
            "user123!@#",
            "用户123",  # Unicode characters
        ]

        for user_id in special_user_ids:
            # These should not raise exceptions
            result1 = await save_settings(user_id, {"test": "data"})
            result2 = await load_settings(user_id)
            result3 = await save_paper_trade(user_id, {"test": "data"})
            result4 = await load_paper_trade_history(user_id)

            # All should return appropriate failure values (due to no real DB)
            assert result1 is False
            assert result2 is None
            assert result3 is None
            assert result4 == []
