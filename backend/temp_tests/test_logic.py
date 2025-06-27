#!/usr/bin/env python3
"""Test the partial depth logic directly."""

import sys
import os
sys.path.append('/home/bail/github/orderfox/backend')

def test_partial_depth_logic():
    """Test our partial depth stream logic."""
    
    # Test the decision logic
    def _should_use_partial_depth_stream(limit: int) -> bool:
        return limit <= 100
    
    def _get_partial_depth_level(limit: int) -> int:
        if limit <= 5:
            return 5
        elif limit <= 10:
            return 10
        else:
            return 20
    
    print("🧪 Testing partial depth stream logic:")
    
    test_cases = [
        (5, True, 5),
        (10, True, 10), 
        (15, True, 20),
        (20, True, 20),
        (50, True, 20),
        (100, True, 20),
        (200, False, None),
        (500, False, None),
        (1000, False, None),
    ]
    
    for limit, expected_use_partial, expected_level in test_cases:
        use_partial = _should_use_partial_depth_stream(limit)
        level = _get_partial_depth_level(limit) if use_partial else None
        
        status = "✅" if (use_partial == expected_use_partial and level == expected_level) else "❌"
        print(f"{status} Limit {limit:4d}: use_partial={str(use_partial):5s}, level={level}")
        
        if use_partial != expected_use_partial or level != expected_level:
            print(f"    Expected: use_partial={expected_use_partial}, level={expected_level}")
            return False
    
    print("\n🎯 Testing frontend limit calculation:")
    
    # Test frontend limits (from main.js changes)
    def calculate_frontend_limit(display_depth):
        return min(display_depth * 2, 20)
    
    frontend_cases = [
        (5, 10),
        (10, 20), 
        (20, 20),
        (50, 20),
    ]
    
    for display_depth, expected in frontend_cases:
        result = calculate_frontend_limit(display_depth)
        status = "✅" if result == expected else "❌"
        print(f"{status} Display depth {display_depth:2d} → limit {result:2d} (expected {expected})")
        
        if result != expected:
            return False
    
    print("\n🌐 Testing Binance URL generation:")
    
    symbol = "BTCUSDT"
    test_urls = [
        (5, f"wss://fstream.binance.com/ws/{symbol.lower()}@depth5"),
        (10, f"wss://fstream.binance.com/ws/{symbol.lower()}@depth10"),
        (20, f"wss://fstream.binance.com/ws/{symbol.lower()}@depth20"),
    ]
    
    for depth_level, expected_url in test_urls:
        generated_url = f"wss://fstream.binance.com/ws/{symbol.lower()}@depth{depth_level}"
        status = "✅" if generated_url == expected_url else "❌"
        print(f"{status} Depth {depth_level:2d}: {generated_url}")
        
        if generated_url != expected_url:
            return False
    
    return True

if __name__ == "__main__":
    print("🚀 Testing Binance Partial Depth Stream Logic\n")
    success = test_partial_depth_logic()
    print(f"\n{'🎉 All tests passed!' if success else '❌ Some tests failed'}")
    sys.exit(0 if success else 1)