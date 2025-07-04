"""
Unit tests for FormattingService.

Tests comprehensive formatting functionality including edge cases,
different amount ranges, and various symbol precision configurations.
"""

import pytest
from unittest.mock import patch
from app.services.formatting_service import FormattingService, formatting_service


class TestFormattingService:
    """Test cases for FormattingService."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.service = FormattingService()
        
        # Sample symbol info for testing
        self.btc_symbol_info = {
            'symbol': 'BTC/USDT',
            'pricePrecision': 2,
            'amountPrecision': 8
        }
        
        self.eth_symbol_info = {
            'symbol': 'ETH/USDT',
            'pricePrecision': 2,
            'amountPrecision': 6
        }
        
        self.shib_symbol_info = {
            'symbol': 'SHIB/USDT',
            'pricePrecision': 6,
            'amountPrecision': 0
        }
    
    def test_singleton_pattern(self):
        """Test that FormattingService follows singleton pattern."""
        service1 = FormattingService()
        service2 = FormattingService()
        assert service1 is service2
        assert service1 is formatting_service
    
    def test_format_price_basic(self):
        """Test basic price formatting."""
        # Regular prices
        assert self.service.format_price(50000.12, self.btc_symbol_info) == "50000.12"
        assert self.service.format_price(3000.456, self.eth_symbol_info) == "3000.46"
        assert self.service.format_price(0.000012, self.shib_symbol_info) == "0.000012"
    
    def test_format_price_edge_cases(self):
        """Test price formatting edge cases."""
        # Zero and None
        assert self.service.format_price(0) == "0.00"
        assert self.service.format_price(None) == "0.00"
        
        # Very large numbers - prices should NOT use compact notation
        assert self.service.format_price(1500000) == "1500000.00"
        assert self.service.format_price(2500) == "2500.00"
        
        # Very small numbers
        assert self.service.format_price(0.000001) == "1.00e-06"
        
        # No symbol info
        assert self.service.format_price(123.456) == "123.46"
    
    def test_format_amount_ranges(self):
        """Test amount formatting for different ranges."""
        # Very small amounts (< 0.00001) - scientific notation
        assert self.service.format_amount(0.000001, self.btc_symbol_info) == "1.00e-06"
        assert self.service.format_amount(0.000005, self.btc_symbol_info) == "5.00e-06"
        
        # Small amounts (< 0.01) - high precision
        assert self.service.format_amount(0.001, self.btc_symbol_info) == "0.00100000"
        assert self.service.format_amount(0.005432, self.btc_symbol_info) == "0.00543200"
        
        # Regular amounts (0.01 - 1000)
        assert self.service.format_amount(0.5, self.btc_symbol_info) == "0.50000000"
        assert self.service.format_amount(10.25, self.btc_symbol_info) == "10.25000000"
        assert self.service.format_amount(100.123, self.btc_symbol_info) == "100.12300000"
        
        # Large amounts (>= 1000) - compact notation
        assert self.service.format_amount(1500, self.btc_symbol_info) == "1.50K"
        assert self.service.format_amount(2000000, self.btc_symbol_info) == "2.00M"
    
    def test_format_amount_different_precisions(self):
        """Test amount formatting with different symbol precisions."""
        # BTC (8 decimal places)
        assert self.service.format_amount(0.12345678, self.btc_symbol_info) == "0.12345678"
        
        # ETH (6 decimal places)
        assert self.service.format_amount(0.123456, self.eth_symbol_info) == "0.123456"
        
        # SHIB (0 decimal places for amounts)
        assert self.service.format_amount(123.456, self.shib_symbol_info) == "123.46"
    
    def test_format_amount_edge_cases(self):
        """Test amount formatting edge cases."""
        # Zero and None
        assert self.service.format_amount(0) == "0.00"
        assert self.service.format_amount(None) == "0.00"
        
        # No symbol info
        assert self.service.format_amount(123.456) == "123.46"
        
        # Negative amounts
        assert self.service.format_amount(-0.001, self.btc_symbol_info) == "-0.00100000"
        assert self.service.format_amount(-1500) == "-1.50K"
    
    def test_format_total_basic(self):
        """Test basic total formatting."""
        # Regular totals
        assert self.service.format_total(100.25) == "100.25"
        assert self.service.format_total(0.5) == "0.50"
        
        # Large totals - compact notation
        assert self.service.format_total(1500) == "1.50K"
        assert self.service.format_total(2000000) == "2.00M"
        
        # Small totals
        assert self.service.format_total(0.001) == "0.0010"
        assert self.service.format_total(0.000001) == "1.00e-06"
    
    def test_format_total_edge_cases(self):
        """Test total formatting edge cases."""
        # Zero and None
        assert self.service.format_total(0) == "0.00"
        assert self.service.format_total(None) == "0.00"
        
        # Negative totals
        assert self.service.format_total(-100.25) == "-100.25"
        assert self.service.format_total(-1500) == "-1.50K"
    
    def test_get_amount_precision(self):
        """Test amount precision calculation."""
        # With amount precision
        assert self.service.get_amount_precision(self.btc_symbol_info) == 8
        assert self.service.get_amount_precision(self.eth_symbol_info) == 6
        assert self.service.get_amount_precision(self.shib_symbol_info) == 0
        
        # Without amount precision, fall back to price precision
        symbol_info_no_amount = {'pricePrecision': 4}
        assert self.service.get_amount_precision(symbol_info_no_amount) == 4
        
        # No symbol info
        assert self.service.get_amount_precision(None) == 2
        assert self.service.get_amount_precision({}) == 2
        
        # Cap at maximum precision
        high_precision_symbol = {'amountPrecision': 12}
        assert self.service.get_amount_precision(high_precision_symbol) == 8
    
    def test_format_orderbook_level(self):
        """Test formatting entire order book level."""
        level = {
            'price': 50000.12,
            'amount': 0.001234,
            'cumulative': 125.67
        }
        
        formatted = self.service.format_orderbook_level(level, self.btc_symbol_info)
        
        # Check original fields are preserved
        assert formatted['price'] == 50000.12
        assert formatted['amount'] == 0.001234
        assert formatted['cumulative'] == 125.67
        
        # Check formatted fields are added
        assert formatted['price_formatted'] == "50000.12"
        assert formatted['amount_formatted'] == "0.00123400"
        assert formatted['cumulative_formatted'] == "125.67"
    
    def test_format_orderbook_level_edge_cases(self):
        """Test order book level formatting edge cases."""
        # Empty level
        level = {}
        formatted = self.service.format_orderbook_level(level)
        assert formatted['price_formatted'] == "0.00"
        assert formatted['amount_formatted'] == "0.00"
        assert formatted['cumulative_formatted'] == "0.00"
        
        # Level with None values
        level = {'price': None, 'amount': None, 'cumulative': None}
        formatted = self.service.format_orderbook_level(level)
        assert formatted['price_formatted'] == "0.00"
        assert formatted['amount_formatted'] == "0.00"
        assert formatted['cumulative_formatted'] == "0.00"
    
    def test_error_handling(self):
        """Test error handling in formatting functions."""
        # Invalid values should not crash
        with patch('app.services.formatting_service.logger') as mock_logger:
            # Test with invalid types
            result = self.service.format_price("invalid")
            assert result == "invalid"
            mock_logger.warning.assert_called()
            
            result = self.service.format_amount("invalid")
            assert result == "invalid"
            
            result = self.service.format_total("invalid")
            assert result == "invalid"
    
    def test_scientific_notation_thresholds(self):
        """Test scientific notation is used at correct thresholds."""
        # Just above threshold - should use regular formatting
        assert "e" not in self.service.format_amount(0.00001, self.btc_symbol_info)
        
        # Just below threshold - should use scientific notation
        assert "e" in self.service.format_amount(0.000009, self.btc_symbol_info)
        
        # Same for prices
        assert "e" not in self.service.format_price(0.00001)
        assert "e" in self.service.format_price(0.000009)
    
    def test_compact_notation_thresholds(self):
        """Test compact notation (K/M) is used at correct thresholds."""
        # Just below 1000 - regular formatting
        assert "K" not in self.service.format_amount(999.99)
        assert "M" not in self.service.format_amount(999.99)
        
        # At 1000 - should use K
        assert "K" in self.service.format_amount(1000)
        
        # At 1M - should use M
        assert "M" in self.service.format_amount(1000000)
    
    def test_real_world_scenarios(self):
        """Test with real-world trading scenarios."""
        # BTC/USDT scenario - high price, small amounts
        btc_level = {
            'price': 43247.82,
            'amount': 0.00023456,
            'cumulative': 1.23456789
        }
        formatted = self.service.format_orderbook_level(btc_level, self.btc_symbol_info)
        assert formatted['price_formatted'] == "43247.82"
        assert formatted['amount_formatted'] == "0.00023456"
        assert formatted['cumulative_formatted'] == "1.23"
        
        # SHIB/USDT scenario - low price, large amounts
        shib_level = {
            'price': 0.000008456,
            'amount': 125000000,
            'cumulative': 1000000000
        }
        formatted = self.service.format_orderbook_level(shib_level, self.shib_symbol_info)
        assert formatted['price_formatted'] == "8.46e-06"  # Scientific notation for very small prices
        assert formatted['amount_formatted'] == "125.00M"
        assert formatted['cumulative_formatted'] == "1000.00M"
    
    def test_get_formatting_stats(self):
        """Test formatting service statistics."""
        stats = self.service.get_formatting_stats()
        assert stats['service_initialized'] is True
        assert isinstance(stats['instance_id'], int)
    
    def test_extreme_amounts(self):
        """Test formatting with extreme amount values."""
        # Extremely small amounts
        assert self.service.format_amount(1e-10, self.btc_symbol_info) == "1.00e-10"
        assert self.service.format_amount(9.87654e-8, self.btc_symbol_info) == "9.88e-08"
        
        # Extremely large amounts
        assert self.service.format_amount(1e9, self.btc_symbol_info) == "1000.00M"
        assert self.service.format_amount(5.5e12, self.btc_symbol_info) == "5500000.00M"
        
        # Boundary values
        assert self.service.format_amount(0.999999, self.btc_symbol_info) == "0.99999900"
        assert self.service.format_amount(1000.0, self.btc_symbol_info) == "1.00K"
        assert self.service.format_amount(999999.99, self.btc_symbol_info) == "1000.00K"
        assert self.service.format_amount(1000000.0, self.btc_symbol_info) == "1.00M"
    
    def test_precision_limits(self):
        """Test formatting with various precision limits."""
        # Test maximum precision (capped at 8)
        max_precision_symbol = {'amountPrecision': 18}
        assert self.service.get_amount_precision(max_precision_symbol) == 8
        
        # Test minimum precision
        min_precision_symbol = {'amountPrecision': 0}
        assert self.service.get_amount_precision(min_precision_symbol) == 0
        
        # Test with negative precision (should default to 2)
        negative_precision_symbol = {'amountPrecision': -1}
        assert self.service.get_amount_precision(negative_precision_symbol) == 2
    
    def test_different_crypto_scenarios(self):
        """Test formatting for different cryptocurrency scenarios."""
        # High-value, low-supply crypto (like BTC)
        btc_scenario = {
            'price': 67890.12,
            'amount': 0.00000123,
            'cumulative': 0.00156789
        }
        formatted = self.service.format_orderbook_level(btc_scenario, self.btc_symbol_info)
        assert formatted['price_formatted'] == "67890.12"
        assert formatted['amount_formatted'] == "1.23e-06"
        assert formatted['cumulative_formatted'] == "0.0016"
        
        # Low-value, high-supply crypto (like SHIB)
        shib_scenario = {
            'price': 0.00000789,
            'amount': 50000000000,
            'cumulative': 100000000000
        }
        formatted = self.service.format_orderbook_level(shib_scenario, self.shib_symbol_info)
        assert formatted['price_formatted'] == "7.89e-06"
        assert formatted['amount_formatted'] == "50000.00M"
        assert formatted['cumulative_formatted'] == "100000.00M"
        
        # Mid-range crypto (like ETH)
        eth_scenario = {
            'price': 2345.67,
            'amount': 12.345678,
            'cumulative': 156.789012
        }
        formatted = self.service.format_orderbook_level(eth_scenario, self.eth_symbol_info)
        assert formatted['price_formatted'] == "2345.67"
        assert formatted['amount_formatted'] == "12.345678"
        assert formatted['cumulative_formatted'] == "156.79"
    
    def test_rounding_behavior(self):
        """Test rounding behavior with various precisions."""
        # Test rounding with different precisions
        value = 123.456789012345
        
        # BTC precision (8 decimals)
        assert self.service.format_amount(value, self.btc_symbol_info) == "123.45678901"
        
        # ETH precision (6 decimals)
        assert self.service.format_amount(value, self.eth_symbol_info) == "123.456789"
        
        # SHIB precision (0 decimals for amounts)
        assert self.service.format_amount(value, self.shib_symbol_info) == "123.46"
        
        # Test rounding edge cases
        assert self.service.format_amount(0.999995, {'amountPrecision': 4}) == "1.0000"
        assert self.service.format_amount(0.999949, {'amountPrecision': 4}) == "0.9999"
    
    def test_performance_with_large_datasets(self):
        """Test formatting performance with large datasets."""
        import time
        
        # Create a large dataset
        large_dataset = []
        for i in range(1000):
            large_dataset.append({
                'price': 50000 + i * 0.01,
                'amount': 0.001 + i * 0.000001,
                'cumulative': 1.0 + i * 0.1
            })
        
        # Time the formatting
        start_time = time.time()
        for level in large_dataset:
            self.service.format_orderbook_level(level, self.btc_symbol_info)
        end_time = time.time()
        
        # Should complete quickly (under 100ms for 1000 items)
        assert (end_time - start_time) < 0.1
    
    def test_locale_independence(self):
        """Test that formatting is locale-independent."""
        # Test with various decimal separators and thousand separators
        # (Should always use dot as decimal separator)
        assert "," not in self.service.format_amount(1234.5678, self.btc_symbol_info)
        assert "." in self.service.format_amount(1234.5678, self.btc_symbol_info)
        
        # Test with very precise values
        precise_value = 0.123456789012345
        result = self.service.format_amount(precise_value, self.btc_symbol_info)
        assert result.count('.') == 1  # Only one decimal point
        
    def test_thread_safety_simulation(self):
        """Test formatting service thread safety."""
        import threading
        import time
        
        results = []
        errors = []
        
        def format_worker():
            try:
                for i in range(100):
                    result = self.service.format_amount(i * 0.001, self.btc_symbol_info)
                    results.append(result)
                    time.sleep(0.001)  # Small delay to increase chance of race conditions
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=format_worker)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check that no errors occurred and results are consistent
        assert len(errors) == 0
        assert len(results) == 500  # 5 threads * 100 iterations each
        
        # Check some specific results for consistency
        expected_results = [
            self.service.format_amount(i * 0.001, self.btc_symbol_info) 
            for i in range(100)
        ]
        
        # Each expected result should appear exactly 5 times (once per thread)
        for expected in expected_results:
            assert results.count(expected) == 5