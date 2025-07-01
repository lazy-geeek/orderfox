#!/usr/bin/env python3
"""Test Binance partial depth streams functionality."""

import asyncio
import json
import websockets
import time
from datetime import datetime


async def test_partial_depth_stream(symbol: str, depth_level: int):
    """Test a single partial depth stream."""
    ws_symbol = symbol.lower()
    ws_url = f"wss://fstream.binance.com/ws/{ws_symbol}@depth{depth_level}"
    
    print(f"\n🔍 Testing {symbol} with depth level {depth_level}")
    print(f"📡 Connecting to: {ws_url}")
    
    messages_received = 0
    start_time = time.time()
    
    try:
        async with websockets.connect(ws_url) as websocket:
            print(f"✅ Connected successfully!")
            
            # Receive and analyze 5 messages
            while messages_received < 5:
                message = await websocket.recv()
                data = json.loads(message)
                
                messages_received += 1
                
                # Analyze the message
                if data.get("e") == "depthUpdate":
                    event_time = datetime.fromtimestamp(data["E"] / 1000)
                    num_bids = len(data.get("b", []))
                    num_asks = len(data.get("a", []))
                    
                    print(f"\n📊 Message {messages_received}:")
                    print(f"   Time: {event_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
                    print(f"   Symbol: {data['s']}")
                    print(f"   Bids: {num_bids} levels")
                    print(f"   Asks: {num_asks} levels")
                    
                    if num_bids > 0:
                        best_bid = data["b"][0]
                        print(f"   Best Bid: {best_bid[0]} @ {best_bid[1]}")
                    
                    if num_asks > 0:
                        best_ask = data["a"][0]
                        print(f"   Best Ask: {best_ask[0]} @ {best_ask[1]}")
                    
                    # Verify depth level
                    if num_bids != depth_level or num_asks != depth_level:
                        print(f"   ⚠️ WARNING: Expected {depth_level} levels, got {num_bids} bids and {num_asks} asks")
                
                else:
                    print(f"\n❓ Unknown message type: {data.get('e', 'N/A')}")
            
            elapsed_time = time.time() - start_time
            print(f"\n⏱️ Received {messages_received} messages in {elapsed_time:.2f} seconds")
            print(f"📈 Average rate: {messages_received/elapsed_time:.2f} messages/second")
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return False
    
    return True


async def test_all_partial_depths():
    """Test partial depth streams for multiple symbols and depth levels."""
    test_configs = [
        ("BTCUSDT", 5),
        ("BTCUSDT", 10),
        ("BTCUSDT", 20),
        ("ETHUSDT", 5),
        ("ETHUSDT", 20),
        ("BNBUSDT", 10),
    ]
    
    print("🚀 Starting Binance Partial Depth Stream Tests")
    print("=" * 60)
    
    results = []
    
    for symbol, depth in test_configs:
        success = await test_partial_depth_stream(symbol, depth)
        results.append((symbol, depth, success))
        
        # Small delay between tests
        await asyncio.sleep(1)
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 Test Summary:")
    print("-" * 60)
    
    for symbol, depth, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{symbol} @ depth{depth}: {status}")
    
    successful = sum(1 for _, _, success in results if success)
    total = len(results)
    print(f"\n🎯 Overall: {successful}/{total} tests passed")


async def compare_with_full_orderbook():
    """Compare partial depth data with full orderbook to verify accuracy."""
    symbol = "BTCUSDT"
    depth_level = 10
    
    print("\n🔄 Comparing partial depth with full orderbook")
    print("=" * 60)
    
    # Import ccxt for full orderbook comparison
    try:
        import ccxt.pro as ccxtpro
        
        exchange = ccxtpro.binance({
            'enableRateLimit': True,
            'options': {
                'defaultType': 'future',  # USDT-M futures
            }
        })
        
        # Get full orderbook
        full_orderbook = await exchange.fetch_order_book(symbol, limit=20)
        
        # Connect to partial depth stream
        ws_symbol = symbol.lower()
        ws_url = f"wss://fstream.binance.com/ws/{ws_symbol}@depth{depth_level}"
        
        async with websockets.connect(ws_url) as websocket:
            # Get one message from partial depth
            message = await websocket.recv()
            partial_data = json.loads(message)
            
            if partial_data.get("e") == "depthUpdate":
                print(f"\n📊 Comparison for {symbol}:")
                
                # Compare best bid/ask
                partial_best_bid = float(partial_data["b"][0][0]) if partial_data["b"] else 0
                partial_best_ask = float(partial_data["a"][0][0]) if partial_data["a"] else 0
                
                full_best_bid = full_orderbook["bids"][0][0] if full_orderbook["bids"] else 0
                full_best_ask = full_orderbook["asks"][0][0] if full_orderbook["asks"] else 0
                
                print(f"\nBest Bid:")
                print(f"  Partial: {partial_best_bid}")
                print(f"  Full:    {full_best_bid}")
                print(f"  Diff:    {abs(partial_best_bid - full_best_bid)}")
                
                print(f"\nBest Ask:")
                print(f"  Partial: {partial_best_ask}")
                print(f"  Full:    {full_best_ask}")
                print(f"  Diff:    {abs(partial_best_ask - full_best_ask)}")
                
                # Check if prices are reasonably close (within 0.1%)
                bid_diff_pct = abs(partial_best_bid - full_best_bid) / full_best_bid * 100
                ask_diff_pct = abs(partial_best_ask - full_best_ask) / full_best_ask * 100
                
                if bid_diff_pct < 0.1 and ask_diff_pct < 0.1:
                    print("\n✅ Prices match within 0.1% tolerance")
                else:
                    print(f"\n⚠️ Price difference exceeds tolerance: Bid {bid_diff_pct:.3f}%, Ask {ask_diff_pct:.3f}%")
        
        await exchange.close()
        
    except ImportError:
        print("⚠️ ccxt.pro not available for comparison test")
    except Exception as e:
        print(f"❌ Comparison test error: {str(e)}")


if __name__ == "__main__":
    # Run all tests
    asyncio.run(test_all_partial_depths())
    
    # Run comparison test
    asyncio.run(compare_with_full_orderbook())