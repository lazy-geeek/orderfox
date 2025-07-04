"""
Decimal arithmetic utilities for precise financial calculations.
Avoids floating-point precision issues common in trading applications.
"""

import math
from decimal import Decimal, ROUND_DOWN, ROUND_UP
from typing import List


class DecimalUtils:
    """Utility class for precise decimal arithmetic operations."""
    
    @staticmethod
    def round_down(value: float, multiple: float) -> float:
        """
        Round a value down to the nearest multiple using decimal arithmetic.
        
        Args:
            value: The value to round
            multiple: The multiple to round to
            
        Returns:
            Rounded down value
        """
        if multiple <= 0:
            return value
        
        # Use decimal arithmetic to avoid floating-point precision issues
        decimal_value = Decimal(str(value))
        decimal_multiple = Decimal(str(multiple))
        
        # Calculate how many multiples fit into the value and round down
        quotient = decimal_value / decimal_multiple
        rounded_quotient = quotient.quantize(Decimal('1'), rounding=ROUND_DOWN)
        
        return float(rounded_quotient * decimal_multiple)
    
    @staticmethod
    def round_up(value: float, multiple: float) -> float:
        """
        Round a value up to the nearest multiple using decimal arithmetic.
        
        Args:
            value: The value to round
            multiple: The multiple to round to
            
        Returns:
            Rounded up value
        """
        if multiple <= 0:
            return value
        
        # Use decimal arithmetic to avoid floating-point precision issues
        decimal_value = Decimal(str(value))
        decimal_multiple = Decimal(str(multiple))
        
        # Calculate how many multiples fit into the value and round up
        quotient = decimal_value / decimal_multiple
        rounded_quotient = quotient.quantize(Decimal('1'), rounding=ROUND_UP)
        
        return float(rounded_quotient * decimal_multiple)
    
    @staticmethod
    def generate_power_of_10_options(base_precision: int, max_options: int = 7, 
                                   max_value: float = None) -> List[float]:
        """
        Generate a list of rounding options based on powers of 10.
        Uses decimal arithmetic to avoid floating-point precision issues.
        
        Args:
            base_precision: Number of decimal places for the base option
            max_options: Maximum number of options to generate
            max_value: Maximum value limit for options
            
        Returns:
            List of clean decimal values
        """
        options = []
        
        # Generate options using decimal arithmetic
        for i in range(max_options):
            # Calculate 10^(-base_precision + i)
            exponent = -base_precision + i
            option_decimal = Decimal(10) ** exponent
            option_float = float(option_decimal)
            
            # Stop if we exceed max_value
            if max_value is not None and option_float > max_value:
                break
                
            options.append(option_float)
        
        return options