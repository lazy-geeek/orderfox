#!/usr/bin/env python3
"""
Test script to validate Binance Partial Book Depth Streams implementation.
"""

import asyncio
import websockets
import json
import sys
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_binance_partial_depth_direct():
    """Test direct connection to Binance partial depth stream."""
    symbol = "btcusdt"
    depth_level = 20
    ws_url = f"wss://fstream.binance.com/ws/{symbol}@depth{depth_level}"
    
    logger.info(f"Testing direct Binance partial depth stream: {ws_url}")
    
    try:
        async with websockets.connect(ws_url) as websocket:
            logger.info("Connected to Binance partial depth stream")
            
            # Receive a few messages to validate format
            for i in range(3):
                message = await websocket.recv()
                data = json.loads(message)
                
                logger.info(f"Message {i+1}:")
                logger.info(f"  Event: {data.get('e')}")
                logger.info(f"  Symbol: {data.get('s')}")
                logger.info(f"  Bids count: {len(data.get('b', []))}")
                logger.info(f"  Asks count: {len(data.get('a', []))}")
                logger.info(f"  Timestamp: {data.get('E')}")
                
                # Validate format
                if data.get('e') == 'depthUpdate':
                    logger.info("✅ Received valid depthUpdate event")
                    
                    bids = data.get('b', [])
                    asks = data.get('a', [])
                    
                    if bids:
                        logger.info(f"  Sample bid: {bids[0]} (price={bids[0][0]}, amount={bids[0][1]})")
                    if asks:
                        logger.info(f"  Sample ask: {asks[0]} (price={asks[0][0]}, amount={asks[0][1]})")
                else:
                    logger.warning(f"❌ Unexpected event type: {data.get('e')}")
                
                print("---")
            
            logger.info("✅ Direct Binance partial depth stream test completed successfully")
            
    except Exception as e:
        logger.error(f"❌ Direct stream test failed: {str(e)}")
        return False
    
    return True

async def test_backend_orderbook_endpoint():
    """Test our backend orderbook WebSocket endpoint with partial depth streams."""
    ws_url = "ws://localhost:8000/api/v1/ws/orderbook/BTCUSDT?limit=20"
    
    logger.info(f"Testing backend orderbook endpoint: {ws_url}")
    
    try:
        async with websockets.connect(ws_url) as websocket:
            logger.info("Connected to backend orderbook WebSocket")
            
            # Receive a few messages to validate our backend integration
            for i in range(3):
                message = await websocket.recv()
                data = json.loads(message)
                
                logger.info(f"Backend message {i+1}:")
                logger.info(f"  Type: {data.get('type')}")
                logger.info(f"  Symbol: {data.get('symbol')}")
                logger.info(f"  Source: {data.get('source', 'not specified')}")
                logger.info(f"  Depth level: {data.get('depth_level', 'not specified')}")
                logger.info(f"  Bids count: {len(data.get('bids', []))}")
                logger.info(f"  Asks count: {len(data.get('asks', []))}")
                
                # Validate our backend format
                if data.get('type') == 'orderbook_update':
                    logger.info("✅ Received valid orderbook_update")
                    
                    if data.get('source') == 'binance_partial_depth':
                        logger.info("✅ Using Binance partial depth streams!")
                        logger.info(f"✅ Depth level: {data.get('depth_level')}")
                    
                    bids = data.get('bids', [])
                    asks = data.get('asks', [])
                    
                    if bids:
                        logger.info(f"  Sample bid: price={bids[0]['price']}, amount={bids[0]['amount']}")
                    if asks:
                        logger.info(f"  Sample ask: price={asks[0]['price']}, amount={asks[0]['amount']}")
                elif data.get('type') == 'error':
                    logger.error(f"❌ Backend error: {data.get('message')}")
                    return False
                else:
                    logger.warning(f"❌ Unexpected message type: {data.get('type')}")
                
                print("---")
            
            logger.info("✅ Backend integration test completed successfully")
            
    except ConnectionRefusedError:
        logger.error("❌ Backend server not running. Please start the backend first.")
        return False
    except Exception as e:
        logger.error(f"❌ Backend test failed: {str(e)}")
        return False
    
    return True

async def main():
    """Run all tests."""
    logger.info("🚀 Starting Binance Partial Book Depth Streams validation tests")
    
    # Test 1: Direct Binance connection
    logger.info("\n=== Test 1: Direct Binance Partial Depth Stream ===")
    direct_success = await test_binance_partial_depth_direct()
    
    # Test 2: Backend integration (only if backend is running)
    logger.info("\n=== Test 2: Backend Integration ===")
    backend_success = await test_backend_orderbook_endpoint()
    
    # Summary
    logger.info("\n=== Test Summary ===")
    logger.info(f"Direct Binance stream: {'✅ PASS' if direct_success else '❌ FAIL'}")
    logger.info(f"Backend integration: {'✅ PASS' if backend_success else '❌ FAIL'}")
    
    if direct_success and backend_success:
        logger.info("🎉 All tests passed! Partial depth streams are working correctly.")
        return 0
    elif direct_success:
        logger.info("⚠️ Direct stream works, but backend integration failed. Check backend server.")
        return 1
    else:
        logger.info("❌ Tests failed. Check implementation.")
        return 2

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)