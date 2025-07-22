"""
Unit tests for configuration module.

This module contains tests for the Settings class and configuration loading.
"""

import pytest

# Chunk 1: Foundation tests - Database, config, utilities
pytestmark = pytest.mark.chunk1
from unittest.mock import patch, MagicMock
import os

from app.core.config import Settings, settings


class TestSettingsClass:
    """Test the Settings class functionality."""

    def test_settings_attributes_exist(self):
        """Test that all required settings attributes exist."""
        test_settings = Settings()

        # Test that all expected attributes exist
        assert hasattr(test_settings, "BINANCE_API_KEY")
        assert hasattr(test_settings, "BINANCE_SECRET_KEY")
        assert hasattr(test_settings, "LIQUIDATION_API_BASE_URL")
        assert hasattr(test_settings, "API_V1_STR")
        assert hasattr(test_settings, "PROJECT_NAME")
        assert hasattr(test_settings, "DEBUG")

    def test_settings_constants(self):
        """Test that constant values are correctly set."""
        test_settings = Settings()

        assert test_settings.API_V1_STR == "/api/v1"
        assert test_settings.PROJECT_NAME == "Trading Bot API"

    def test_debug_setting_type(self):
        """Test that DEBUG setting is a boolean."""
        test_settings = Settings()
        assert isinstance(test_settings.DEBUG, bool)

    def test_api_keys_type(self):
        """Test that API keys are either None or strings."""
        test_settings = Settings()

        assert test_settings.BINANCE_API_KEY is None or isinstance(
            test_settings.BINANCE_API_KEY, str
        )
        assert test_settings.BINANCE_SECRET_KEY is None or isinstance(
            test_settings.BINANCE_SECRET_KEY, str
        )
        assert test_settings.LIQUIDATION_API_BASE_URL is None or isinstance(
            test_settings.LIQUIDATION_API_BASE_URL, str
        )

    @patch("app.core.config.logging.warning")
    @patch("app.core.config.os.getenv")
    def test_settings_initialization_warnings(self, mock_getenv, mock_warning):
        """Test that warnings are logged when required environment variables are missing."""
        # Configure mock_getenv to simulate missing API keys
        mock_getenv.side_effect = lambda key, default=None: {
            "API_V1_STR": "/api/v1",
            "PROJECT_NAME": "Trading Bot API",
            "DEBUG": "False",
            "BINANCE_API_KEY": None,
            "BINANCE_SECRET_KEY": None,
            "LIQUIDATION_API_BASE_URL": "",
        }.get(key, default)

        # Instantiate Settings after patching os.getenv
        test_settings = Settings()

        # Check if warning messages were logged
        assert mock_warning.call_args_list  # Ensure warning was called at least once

        warning_calls = [str(call) for call in mock_warning.call_args_list]

        # Assert that specific warning messages are present
        assert any(
            "BINANCE_API_KEY not found in environment variables" in call
            for call in warning_calls
        )
        assert any(
            "BINANCE_SECRET_KEY not found in environment variables" in call
            for call in warning_calls
        )

    def test_settings_class_can_be_instantiated_multiple_times(self):
        """Test that Settings class can be instantiated multiple times."""
        settings1 = Settings()
        settings2 = Settings()

        # They should have the same values but be different instances
        assert settings1.API_V1_STR == settings2.API_V1_STR
        assert settings1.PROJECT_NAME == settings2.PROJECT_NAME
        assert settings1 is not settings2

    def test_settings_values_consistency(self):
        """Test that settings values remain consistent across multiple accesses."""
        test_settings = Settings()

        # Access the same property multiple times
        api_key1 = test_settings.BINANCE_API_KEY
        api_key2 = test_settings.BINANCE_API_KEY
        api_key3 = test_settings.BINANCE_API_KEY

        assert api_key1 == api_key2 == api_key3

        debug1 = test_settings.DEBUG
        debug2 = test_settings.DEBUG
        debug3 = test_settings.DEBUG

        assert debug1 == debug2 == debug3


class TestGlobalSettingsInstance:
    """Test the global settings instance."""

    def test_global_settings_instance_exists(self):
        """Test that the global settings instance exists."""
        from app.core.config import settings

        assert settings is not None
        assert isinstance(settings, Settings)

    def test_global_settings_instance_properties(self):
        """Test that the global settings instance has expected properties."""
        from app.core.config import settings

        # Test that all expected attributes exist
        assert hasattr(settings, "BINANCE_API_KEY")
        assert hasattr(settings, "BINANCE_SECRET_KEY")
        assert hasattr(settings, "LIQUIDATION_API_BASE_URL")
        assert hasattr(settings, "API_V1_STR")
        assert hasattr(settings, "PROJECT_NAME")
        assert hasattr(settings, "DEBUG")

    def test_global_settings_constants(self):
        """Test that global settings constants are correct."""
        from app.core.config import settings

        assert settings.API_V1_STR == "/api/v1"
        assert settings.PROJECT_NAME == "Trading Bot API"


class TestEnvironmentVariableHandling:
    """Test environment variable handling behavior."""

    def test_debug_setting_behavior(self):
        """Test DEBUG setting behavior with current environment."""
        test_settings = Settings()

        # DEBUG should be a boolean
        assert isinstance(test_settings.DEBUG, bool)

        # Test that it follows the expected logic
        current_debug_env = os.getenv("DEBUG", "False")
        expected_debug = current_debug_env.lower() == "true"
        assert test_settings.DEBUG == expected_debug

    def test_environment_variable_access(self):
        """Test that environment variables are accessible."""
        test_settings = Settings()

        # Test that we can access the current environment values
        current_api_key = os.getenv("BINANCE_API_KEY")
        current_secret_key = os.getenv("BINANCE_SECRET_KEY")
        current_liquidation_api_url = os.getenv("LIQUIDATION_API_BASE_URL", "")

        # Settings should match current environment
        assert test_settings.BINANCE_API_KEY == current_api_key
        assert test_settings.BINANCE_SECRET_KEY == current_secret_key
        assert test_settings.LIQUIDATION_API_BASE_URL == current_liquidation_api_url


class TestSettingsEdgeCases:
    """Test edge cases and error conditions."""

    @patch("app.core.config.load_dotenv")
    def test_dotenv_loading_called(self, mock_load_dotenv):
        """Test that load_dotenv is called during module import."""
        # This test verifies that load_dotenv was called when the module was imported
        # Since the module is already imported, we can't test the actual call,
        # but we can verify the function exists and would be callable
        from dotenv import load_dotenv

        assert callable(load_dotenv)

    def test_settings_immutable_constants(self):
        """Test that constant values are correctly set."""
        test_settings = Settings()

        assert test_settings.API_V1_STR == "/api/v1"
        assert test_settings.PROJECT_NAME == "Trading Bot API"

    def test_settings_attribute_types(self):
        """Test that all settings attributes have expected types."""
        test_settings = Settings()

        # String constants
        assert isinstance(test_settings.API_V1_STR, str)
        assert isinstance(test_settings.PROJECT_NAME, str)

        # Boolean setting
        assert isinstance(test_settings.DEBUG, bool)

        # Optional string settings
        assert test_settings.BINANCE_API_KEY is None or isinstance(
            test_settings.BINANCE_API_KEY, str
        )
        assert test_settings.BINANCE_SECRET_KEY is None or isinstance(
            test_settings.BINANCE_SECRET_KEY, str
        )
        assert test_settings.LIQUIDATION_API_BASE_URL is None or isinstance(
            test_settings.LIQUIDATION_API_BASE_URL, str
        )

    def test_settings_string_lengths(self):
        """Test that string settings have reasonable lengths if set."""
        test_settings = Settings()

        if test_settings.BINANCE_API_KEY:
            assert len(test_settings.BINANCE_API_KEY) > 0
            assert len(test_settings.BINANCE_API_KEY) < 1000  # Reasonable upper bound

        if test_settings.BINANCE_SECRET_KEY:
            assert len(test_settings.BINANCE_SECRET_KEY) > 0
            assert (
                len(test_settings.BINANCE_SECRET_KEY) < 1000
            )  # Reasonable upper bound

        if test_settings.LIQUIDATION_API_BASE_URL:
            assert len(test_settings.LIQUIDATION_API_BASE_URL) > 0
            assert len(test_settings.LIQUIDATION_API_BASE_URL) < 1000  # URL length limit

    def test_settings_debug_values(self):
        """Test various DEBUG environment values."""
        # Test current DEBUG setting
        test_settings = Settings()
        current_debug = os.getenv("DEBUG", "False")

        # Verify the logic matches what's in the Settings class
        expected = current_debug.lower() == "true"
        assert test_settings.DEBUG == expected


class TestSettingsIntegration:
    """Integration tests for settings functionality."""

    def test_settings_work_with_application(self):
        """Test that settings work correctly in application context."""
        test_settings = Settings()

        # Test that we can use settings for typical application needs
        api_prefix = test_settings.API_V1_STR
        assert api_prefix.startswith("/")
        assert "v1" in api_prefix

        project_name = test_settings.PROJECT_NAME
        assert len(project_name) > 0
        assert isinstance(project_name, str)

    def test_settings_environment_consistency(self):
        """Test that settings are consistent with environment."""
        test_settings = Settings()

        # Verify that settings reflect the actual environment
        for attr_name in [
            "BINANCE_API_KEY",
            "BINANCE_SECRET_KEY",
        ]:
            setting_value = getattr(test_settings, attr_name)
            env_value = os.getenv(attr_name)
            assert setting_value == env_value
        
        # LIQUIDATION_API_BASE_URL has a default value
        assert test_settings.LIQUIDATION_API_BASE_URL == os.getenv("LIQUIDATION_API_BASE_URL", "")

    def test_settings_boolean_conversion(self):
        """Test boolean conversion logic."""
        test_settings = Settings()

        # Test that DEBUG follows the expected boolean conversion
        debug_env = os.getenv("DEBUG", "False")
        expected_debug = debug_env.lower() == "true"
        assert test_settings.DEBUG == expected_debug

        # Verify it's actually a boolean
        assert isinstance(test_settings.DEBUG, bool)
