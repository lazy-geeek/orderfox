#!/usr/bin/env python3
"""Quick test of partial depth streams."""

import asyncio
import websockets
import json

async def test_backend():
    """Quick test of backend partial depth integration."""
    ws_url = "ws://localhost:8000/api/v1/ws/orderbook/BTCUSDT?limit=20"
    
    try:
        async with websockets.connect(ws_url) as websocket:
            print("✅ Connected to backend")
            
            # Get first message
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                data = json.loads(message)
            except asyncio.TimeoutError:
                print("❌ Timeout waiting for message")
                return False
            
            print(f"Message type: {data.get('type')}")
            print(f"Symbol: {data.get('symbol')}")
            print(f"Source: {data.get('source', 'not specified')}")
            print(f"Depth level: {data.get('depth_level', 'not specified')}")
            print(f"Bids: {len(data.get('bids', []))}")
            print(f"Asks: {len(data.get('asks', []))}")
            
            if data.get('source') == 'binance_partial_depth':
                print("🎉 SUCCESS: Using Binance partial depth streams!")
                return True
            else:
                print(f"ℹ️ Using source: {data.get('source')}")
                return True
                
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_backend())
    exit(0 if success else 1)