"""Tests for decimal utilities."""

import pytest

# Chunk 1: Foundation tests - Database, config, utilities
pytestmark = pytest.mark.chunk1
from app.utils.decimal_utils import DecimalUtils


class TestDecimalUtils:
    """Test the decimal utilities."""
    
    def test_generate_power_of_10_options_precision_8(self):
        """Test generating rounding options for high precision symbols like SHIBUSDT."""
        options = DecimalUtils.generate_power_of_10_options(
            base_precision=8,
            max_options=7,
            max_value=1000
        )
        
        # Should generate clean decimal values without floating-point errors
        expected_options = [
            1e-08,   # 0.00000001
            1e-07,   # 0.0000001
            1e-06,   # 0.000001
            1e-05,   # 0.00001
            1e-04,   # 0.0001
            1e-03,   # 0.001
            1e-02    # 0.01
        ]
        
        assert len(options) == 7
        
        # Check that all values are clean (no floating-point precision errors)
        for i, option in enumerate(options):
            expected = expected_options[i]
            assert abs(option - expected) < 1e-15, f"Option {i}: expected {expected}, got {option}"
            
        # Specifically test that we don't get values like 9.999999999999999e-06
        for option in options:
            str_repr = str(option)
            assert "9.999999999999999" not in str_repr
            
    def test_generate_power_of_10_options_with_max_value(self):
        """Test that max_value limits the options correctly."""
        options = DecimalUtils.generate_power_of_10_options(
            base_precision=8,
            max_options=7,
            max_value=0.001  # Should stop at 0.001
        )
        
        # Should stop at 0.001 (1e-03) due to max_value
        expected_options = [
            1e-08,   # 0.00000001
            1e-07,   # 0.0000001
            1e-06,   # 0.000001
            1e-05,   # 0.00001
            1e-04,   # 0.0001
            1e-03    # 0.001
        ]
        
        assert len(options) == 6
        for i, option in enumerate(options):
            expected = expected_options[i]
            assert abs(option - expected) < 1e-15, f"Option {i}: expected {expected}, got {option}"
            
    def test_rounding_functions_with_high_precision(self):
        """Test rounding functions with high precision values."""
        # Test with a value that would cause floating-point precision issues
        value = 0.000009999999999999999
        multiple = 0.00001
        
        rounded_down = DecimalUtils.round_down(value, multiple)
        rounded_up = DecimalUtils.round_up(value, multiple)
        
        # Should round down to 0.0 and up to 0.00001
        assert rounded_down == 0.0
        assert rounded_up == 0.00001
        
        # Test with another problematic value
        value = 0.000015
        multiple = 0.00001
        
        rounded_down = DecimalUtils.round_down(value, multiple)
        rounded_up = DecimalUtils.round_up(value, multiple)
        
        # Should round down to 0.00001 and up to 0.00002
        assert rounded_down == 0.00001
        assert rounded_up == 0.00002