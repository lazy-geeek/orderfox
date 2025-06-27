#!/usr/bin/env python3
"""Detailed test to debug WebSocket orderbook connection."""

import asyncio
import websockets
import json
import sys

async def detailed_test():
    """Detailed test with extended timeout and more logging."""
    ws_url = "ws://localhost:8000/api/v1/ws/orderbook/BTCUSDT?limit=20"
    
    print(f"🔗 Connecting to: {ws_url}")
    
    try:
        timeout = 30  # Extended timeout
        print(f"⏰ Using {timeout}s timeout")
        
        async with websockets.connect(ws_url) as websocket:
            print("✅ WebSocket connection established")
            
            print("📡 Waiting for first message...")
            
            # Try to receive multiple messages with timeout
            for i in range(5):
                try:
                    print(f"   Attempt {i+1}/5...")
                    message = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                    
                    print(f"📨 Received message {i+1}:")
                    
                    try:
                        data = json.loads(message)
                        print(f"   Type: {data.get('type')}")
                        print(f"   Symbol: {data.get('symbol')}")
                        print(f"   Source: {data.get('source', 'not specified')}")
                        print(f"   Depth level: {data.get('depth_level', 'not specified')}")
                        print(f"   Bids: {len(data.get('bids', []))}")
                        print(f"   Asks: {len(data.get('asks', []))}")
                        print(f"   Timestamp: {data.get('timestamp')}")
                        
                        if data.get('type') == 'error':
                            print(f"❌ Error message: {data.get('message')}")
                            return False
                        elif data.get('type') == 'orderbook_update':
                            print("✅ Valid orderbook update received!")
                            if data.get('source') == 'binance_partial_depth':
                                print("🎉 SUCCESS: Using Binance partial depth streams!")
                                print(f"   Depth level: {data.get('depth_level')}")
                                
                                # Show some actual data
                                bids = data.get('bids', [])
                                asks = data.get('asks', [])
                                if bids:
                                    print(f"   Top bid: ${bids[0]['price']} (amount: {bids[0]['amount']})")
                                if asks:
                                    print(f"   Top ask: ${asks[0]['price']} (amount: {asks[0]['amount']})")
                                
                                return True
                            else:
                                print(f"ℹ️ Using source: {data.get('source')}")
                                return True
                        else:
                            print(f"❓ Unknown message type: {data.get('type')}")
                            
                    except json.JSONDecodeError:
                        print(f"❌ Invalid JSON: {message[:200]}...")
                        
                    print("---")
                    
                except asyncio.TimeoutError:
                    print(f"   Timeout on attempt {i+1}")
                    if i == 4:  # Last attempt
                        print("❌ All attempts timed out")
                        return False
                    continue
                    
        return False
        
    except ConnectionRefusedError:
        print("❌ Connection refused - backend not running")
        return False
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting detailed WebSocket test")
    success = asyncio.run(detailed_test())
    print(f"\n{'✅ SUCCESS' if success else '❌ FAILED'}")
    sys.exit(0 if success else 1)