"""Tests for formatting service rounding-aware formatting."""

import pytest
from app.services.formatting_service import FormattingService


class TestFormattingServiceRounding:
    """Test rounding-aware price formatting."""
    
    @pytest.fixture
    def formatting_service(self):
        """Get formatting service instance."""
        return FormattingService()
    
    @pytest.fixture
    def btc_symbol_info(self):
        """BTC symbol info for testing."""
        return {
            'symbol': 'BTCUSDT',
            'pricePrecision': 2,
            'amountPrecision': 8
        }
    
    @pytest.fixture
    def shib_symbol_info(self):
        """SHIB symbol info for testing."""
        return {
            'symbol': 'SHIBUSDT',
            'pricePrecision': 8,
            'amountPrecision': 0
        }
    
    def test_format_price_with_large_rounding(self, formatting_service, btc_symbol_info):
        """Test price formatting with large rounding values (10+)."""
        # Prices that should display as integers
        test_cases = [
            (108980.0, 10.0, "108980"),
            (108970.0, 10.0, "108970"),
            (108960.0, 10.0, "108960"),
            (50000.0, 100.0, "50000"),
            (49900.0, 100.0, "49900")
        ]
        
        for price, rounding, expected in test_cases:
            result = formatting_service.format_price(price, btc_symbol_info, rounding)
            assert result == expected, f"Price {price} with rounding {rounding} should be '{expected}', got '{result}'"
    
    def test_format_price_with_unit_rounding(self, formatting_service, btc_symbol_info):
        """Test price formatting with unit rounding (1.0)."""
        test_cases = [
            (108983.0, 1.0, "108983"),  # Whole number
            (108983.5, 1.0, "108983.5"), # Half unit
            (108983.7, 1.0, "108983.7")  # Fractional
        ]
        
        for price, rounding, expected in test_cases:
            result = formatting_service.format_price(price, btc_symbol_info, rounding)
            assert result == expected, f"Price {price} with rounding {rounding} should be '{expected}', got '{result}'"
    
    def test_format_price_with_decimal_rounding(self, formatting_service, btc_symbol_info):
        """Test price formatting with decimal rounding."""
        test_cases = [
            (108983.45, 0.1, "108983.4"),
            (108983.45, 0.01, "108983.45"),
            (108983.456, 0.001, "108983.456")
        ]
        
        for price, rounding, expected in test_cases:
            result = formatting_service.format_price(price, btc_symbol_info, rounding)
            assert result == expected, f"Price {price} with rounding {rounding} should be '{expected}', got '{result}'"
    
    def test_format_price_high_precision_symbols(self, formatting_service, shib_symbol_info):
        """Test price formatting for high precision symbols."""
        test_cases = [
            (0.00001000, 0.00001, "0.00001"),    # 5 decimal places minimum for 0.00001 rounding
            (0.00001500, 0.00001, "0.00002"),    # Rounded value
            (0.00010000, 0.0001, "0.0001"),     # 4 decimal places minimum for 0.0001 rounding
            (0.00100000, 0.001, "0.001")        # 3 decimal places minimum for 0.001 rounding
        ]
        
        for price, rounding, expected in test_cases:
            result = formatting_service.format_price(price, shib_symbol_info, rounding)
            assert result == expected, f"Price {price} with rounding {rounding} should be '{expected}', got '{result}'"
    
    def test_format_price_without_rounding_fallback(self, formatting_service, btc_symbol_info):
        """Test that formatting falls back to symbol precision when no rounding provided."""
        # Without rounding, should use symbol's pricePrecision (2 for BTC)
        result = formatting_service.format_price(108983.456, btc_symbol_info, None)
        assert result == "108983.46", f"Without rounding should use symbol precision, got '{result}'"
        
        # Test with no symbol info and no rounding
        result = formatting_service.format_price(108983.456, None, None)
        assert result == "108983.46", f"Without symbol or rounding should use default precision, got '{result}'"
    
    def test_format_price_with_very_small_values(self, formatting_service, btc_symbol_info):
        """Test formatting of very small values with scientific notation."""
        test_cases = [
            (0.000001, 0.00001, "1.00e-06"),    # Much smaller than rounding, use scientific
            (0.0000005, 0.000001, "0.000000")   # Close to rounding level, use decimal
        ]
        
        for price, rounding, expected in test_cases:
            result = formatting_service.format_price(price, btc_symbol_info, rounding)
            assert result == expected, f"Price {price} with rounding {rounding} should be '{expected}', got '{result}'"
    
    def test_rounding_edge_cases(self, formatting_service, btc_symbol_info):
        """Test edge cases for rounding."""
        # Zero rounding should fallback to symbol precision
        result = formatting_service.format_price(108983.456, btc_symbol_info, 0.0)
        assert result == "108983.46"
        
        # Negative rounding should fallback to symbol precision  
        result = formatting_service.format_price(108983.456, btc_symbol_info, -1.0)
        assert result == "108983.46"