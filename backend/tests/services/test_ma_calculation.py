"""
Tests for Moving Average calculation functionality.

This module contains unit tests for the MovingAverageCalculator class
used in liquidation volume data processing.
"""

import pytest
from app.services.liquidation_service import MovingAverageCalculator


class TestMovingAverageCalculator:
    """Test suite for MovingAverageCalculator class."""
    
    def test_ma_calculator_initialization(self):
        """Test that MovingAverageCalculator initializes correctly."""
        calc = MovingAverageCalculator(window_size=10)
        
        assert calc.window_size == 10
        assert calc.get_current_ma() is None
        assert len(calc.values) == 0
        assert calc.sum == 0.0
    
    def test_ma_calculator_default_window_size(self):
        """Test that MovingAverageCalculator uses default window size of 50."""
        calc = MovingAverageCalculator()
        
        assert calc.window_size == 50
    
    def test_ma_calculator_single_value(self):
        """Test MA calculation with a single value."""
        calc = MovingAverageCalculator(window_size=5)
        
        calc.add_value(1000, 100.0)
        
        assert calc.get_current_ma() == 100.0
        assert len(calc.values) == 1
        assert calc.sum == 100.0
    
    def test_ma_calculator_multiple_values_under_window(self):
        """Test MA calculation with values less than window size."""
        calc = MovingAverageCalculator(window_size=5)
        
        values = [(1000, 10.0), (2000, 20.0), (3000, 30.0)]
        for time, value in values:
            calc.add_value(time, value)
        
        # MA should be (10 + 20 + 30) / 3 = 20.0
        assert calc.get_current_ma() == 20.0
        assert len(calc.values) == 3
        assert calc.sum == 60.0
    
    def test_ma_calculator_exact_window_size(self):
        """Test MA calculation with exactly window size values."""
        calc = MovingAverageCalculator(window_size=5)
        
        values = [(1000, 10.0), (2000, 20.0), (3000, 30.0), (4000, 40.0), (5000, 50.0)]
        for time, value in values:
            calc.add_value(time, value)
        
        # MA should be (10 + 20 + 30 + 40 + 50) / 5 = 30.0
        assert calc.get_current_ma() == 30.0
        assert len(calc.values) == 5
        assert calc.sum == 150.0
    
    def test_ma_calculator_sliding_window(self):
        """Test MA calculation with sliding window (> window size values)."""
        calc = MovingAverageCalculator(window_size=5)
        
        values = [(1000, 10.0), (2000, 20.0), (3000, 30.0), (4000, 40.0), (5000, 50.0), (6000, 60.0)]
        for time, value in values:
            calc.add_value(time, value)
        
        # Should have last 5 values: [20, 30, 40, 50, 60]
        # MA should be (20 + 30 + 40 + 50 + 60) / 5 = 40.0
        assert calc.get_current_ma() == 40.0
        assert len(calc.values) == 5
        assert calc.sum == 200.0
    
    def test_ma_calculator_sliding_window_extended(self):
        """Test MA calculation with many values to verify sliding window behavior."""
        calc = MovingAverageCalculator(window_size=3)
        
        # Add 10 values
        for i in range(1, 11):
            calc.add_value(i * 1000, float(i * 10))
        
        # Should have last 3 values: [80, 90, 100]
        # MA should be (80 + 90 + 100) / 3 = 90.0
        assert calc.get_current_ma() == 90.0
        assert len(calc.values) == 3
        assert calc.sum == 270.0
    
    def test_ma_calculator_zero_values_ignored(self):
        """Test that zero values are ignored in MA calculation."""
        calc = MovingAverageCalculator(window_size=5)
        
        # Add mix of zero and non-zero values
        calc.add_value(1000, 0.0)  # Should be ignored
        calc.add_value(2000, 10.0)
        calc.add_value(3000, 0.0)  # Should be ignored
        calc.add_value(4000, 20.0)
        calc.add_value(5000, 30.0)
        
        # Should only have non-zero values: [10, 20, 30]
        # MA should be (10 + 20 + 30) / 3 = 20.0
        assert calc.get_current_ma() == 20.0
        assert len(calc.values) == 3
        assert calc.sum == 60.0
    
    def test_ma_calculator_all_zero_values(self):
        """Test that MA returns None when all values are zero."""
        calc = MovingAverageCalculator(window_size=5)
        
        # Add only zero values
        for i in range(5):
            calc.add_value(i * 1000, 0.0)
        
        assert calc.get_current_ma() is None
        assert len(calc.values) == 0
        assert calc.sum == 0.0
    
    def test_ma_calculator_clear(self):
        """Test that clear() resets the calculator state."""
        calc = MovingAverageCalculator(window_size=5)
        
        # Add some values
        values = [(1000, 10.0), (2000, 20.0), (3000, 30.0)]
        for time, value in values:
            calc.add_value(time, value)
        
        # Verify state before clear
        assert calc.get_current_ma() == 20.0
        assert len(calc.values) == 3
        assert calc.sum == 60.0
        
        # Clear and verify reset state
        calc.clear()
        
        assert calc.get_current_ma() is None
        assert len(calc.values) == 0
        assert calc.sum == 0.0
    
    def test_ma_calculator_negative_values(self):
        """Test MA calculation with negative values."""
        calc = MovingAverageCalculator(window_size=3)
        
        # Add mix of positive and negative values
        calc.add_value(1000, -10.0)
        calc.add_value(2000, 20.0)
        calc.add_value(3000, -5.0)
        
        # MA should be (-10 + 20 + (-5)) / 3 = 5.0 / 3 ≈ 1.67
        ma = calc.get_current_ma()
        assert ma is not None
        assert abs(ma - (5.0 / 3)) < 0.001  # Use small epsilon for float comparison
        assert len(calc.values) == 3
        assert calc.sum == 5.0
    
    def test_ma_calculator_decimal_values(self):
        """Test MA calculation with decimal values."""
        calc = MovingAverageCalculator(window_size=4)
        
        values = [(1000, 12.5), (2000, 25.75), (3000, 33.25), (4000, 18.5)]
        for time, value in values:
            calc.add_value(time, value)
        
        # MA should be (12.5 + 25.75 + 33.25 + 18.5) / 4 = 90.0 / 4 = 22.5
        assert calc.get_current_ma() == 22.5
        assert len(calc.values) == 4
        assert calc.sum == 90.0
    
    def test_ma_calculator_efficiency_with_large_window(self):
        """Test that MA calculation is efficient with large window size."""
        calc = MovingAverageCalculator(window_size=1000)
        
        # Add many values
        for i in range(1500):
            calc.add_value(i * 1000, float(i + 1))
        
        # Should maintain window size of 1000
        assert len(calc.values) == 1000
        
        # Should have values 501 to 1500 (last 1000 values)
        # MA should be sum of (501 to 1500) / 1000
        expected_sum = sum(range(501, 1501))
        expected_ma = expected_sum / 1000
        
        assert calc.get_current_ma() == expected_ma
        assert calc.sum == expected_sum
    
    def test_ma_calculator_time_values_ignored_in_calculation(self):
        """Test that time values don't affect MA calculation, only used for ordering."""
        calc = MovingAverageCalculator(window_size=3)
        
        # Add values with non-sequential times
        calc.add_value(5000, 30.0)
        calc.add_value(1000, 10.0)
        calc.add_value(3000, 20.0)
        
        # MA should be (30 + 10 + 20) / 3 = 20.0
        # Time values shouldn't affect the calculation
        assert calc.get_current_ma() == 20.0
        assert len(calc.values) == 3
        assert calc.sum == 60.0