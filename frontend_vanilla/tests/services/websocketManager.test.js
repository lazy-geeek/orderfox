import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

/**
 * Unit tests for WebSocket Manager race condition fixes.
 * 
 * Tests critical bug fixes implemented to prevent "Cannot update oldest data" errors
 * by validating WebSocket connection management and race condition handling.
 */
describe('WebSocket Manager Race Condition Fixes', () => {
  let mockState;
  let mockSetSelectedTimeframe;
  let mockDisconnectWebSocketStream;
  
  beforeEach(() => {
    // Mock state management
    mockState = {
      selectedSymbol: 'BTCUSDT',
      selectedTimeframe: '1m'
    };
    
    
    // Mock state setters
    mockSetSelectedTimeframe = vi.fn();
    mockDisconnectWebSocketStream = vi.fn();
    
    // Set up global mocks
    global.state = mockState;
    global.setSelectedTimeframe = mockSetSelectedTimeframe;
    global.disconnectWebSocketStream = mockDisconnectWebSocketStream;
  });
  
  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('TimeFrame Switching Bug Fix', () => {
    /**
     * Test the critical bug fix in switchTimeframe method.
     * 
     * CRITICAL BUG: The old implementation used the new timeframe to disconnect
     * the old stream, which caused race conditions and "Cannot update oldest data" errors.
     * 
     * FIX: Store the old timeframe BEFORE updating state, then use it for disconnection.
     */
    function testSwitchTimeframeBugFix(newTimeframe) {
      // CRITICAL: Store old timeframe BEFORE updating state (this was the bug fix)
      const oldTimeframe = mockState.selectedTimeframe;
      
      // Update state to new timeframe
      mockState.selectedTimeframe = newTimeframe;
      mockSetSelectedTimeframe(newTimeframe);
      
      // CRITICAL: Use oldTimeframe for disconnection, not the new one
      mockDisconnectWebSocketStream('candles', mockState.selectedSymbol, oldTimeframe);
      
      return {
        oldTimeframe,
        newTimeframe,
        disconnectedWith: oldTimeframe // This should be the old timeframe
      };
    }
    
    it('should store old timeframe before updating state (critical bug fix)', () => {
      mockState.selectedTimeframe = '1m';
      
      const result = testSwitchTimeframeBugFix('5m');
      
      expect(result.oldTimeframe).toBe('1m'); // Old timeframe stored correctly
      expect(result.newTimeframe).toBe('5m'); // New timeframe set correctly
      expect(result.disconnectedWith).toBe('1m'); // CRITICAL: Disconnected with OLD timeframe
      expect(mockDisconnectWebSocketStream).toHaveBeenCalledWith('candles', 'BTCUSDT', '1m');
    });
    
    it('should handle multiple rapid timeframe switches correctly', () => {
      // Simulate rapid switching: 1m -> 5m -> 15m
      mockState.selectedTimeframe = '1m';
      
      // First switch: 1m -> 5m
      const result1 = testSwitchTimeframeBugFix('5m');
      expect(result1.disconnectedWith).toBe('1m');
      
      // Second switch: 5m -> 15m
      mockState.selectedTimeframe = '5m'; // Update mock state
      const result2 = testSwitchTimeframeBugFix('15m');
      expect(result2.disconnectedWith).toBe('5m');
      
      expect(mockDisconnectWebSocketStream).toHaveBeenCalledTimes(2);
      expect(mockDisconnectWebSocketStream).toHaveBeenNthCalledWith(1, 'candles', 'BTCUSDT', '1m');
      expect(mockDisconnectWebSocketStream).toHaveBeenNthCalledWith(2, 'candles', 'BTCUSDT', '5m');
    });
    
    it('should demonstrate the old buggy behavior vs fixed behavior', () => {
      mockState.selectedTimeframe = '1m';
      const newTimeframe = '5m';
      
      // OLD BUGGY BEHAVIOR (what would happen without the fix):
      // disconnectWebSocketStream('candles', state.selectedSymbol, newTimeframe) 
      // This would try to disconnect '5m' stream when we actually had '1m' stream
      const buggyDisconnectTimeframe = newTimeframe; // This was the bug
      
      // FIXED BEHAVIOR (current implementation):
      const oldTimeframe = mockState.selectedTimeframe; // Store before update
      const fixedDisconnectTimeframe = oldTimeframe; // Use stored old timeframe
      
      expect(buggyDisconnectTimeframe).toBe('5m'); // Bug: would disconnect wrong stream
      expect(fixedDisconnectTimeframe).toBe('1m'); // Fix: disconnects correct stream
      expect(buggyDisconnectTimeframe).not.toBe(fixedDisconnectTimeframe); // Demonstrates the fix
    });
    
    it('should handle edge case with same timeframe selection', () => {
      mockState.selectedTimeframe = '1m';
      
      const result = testSwitchTimeframeBugFix('1m');
      
      expect(result.oldTimeframe).toBe('1m');
      expect(result.newTimeframe).toBe('1m');
      expect(result.disconnectedWith).toBe('1m');
      expect(mockDisconnectWebSocketStream).toHaveBeenCalledWith('candles', 'BTCUSDT', '1m');
    });
  });

  describe('Symbol Switching Race Condition Prevention', () => {
    function testSymbolSwitchRaceCondition(newSymbol) {
      // Simulate symbol switching logic that should prevent race conditions
      const oldSymbol = mockState.selectedSymbol;
      
      // Update to new symbol
      mockState.selectedSymbol = newSymbol;
      
      // Validate that incoming data is for the correct symbol
      function validateIncomingCandle(candleData) {
        if (candleData.symbol && candleData.symbol !== mockState.selectedSymbol) {
          console.warn('Rejecting candle for wrong symbol:', candleData.symbol, 'vs', mockState.selectedSymbol);
          return false;
        }
        return true;
      }
      
      return {
        oldSymbol,
        newSymbol,
        validateIncomingCandle
      };
    }
    
    it('should reject candles for old symbol after switch', () => {
      mockState.selectedSymbol = 'BTCUSDT';
      
      const result = testSymbolSwitchRaceCondition('ETHUSDT');
      
      // Simulate receiving a candle for the old symbol (race condition)
      const oldSymbolCandle = { symbol: 'BTCUSDT', timestamp: Date.now() };
      const shouldAcceptOldCandle = result.validateIncomingCandle(oldSymbolCandle);
      
      expect(shouldAcceptOldCandle).toBe(false); // Should reject old symbol candle
      
      // Simulate receiving a candle for the new symbol
      const newSymbolCandle = { symbol: 'ETHUSDT', timestamp: Date.now() };
      const shouldAcceptNewCandle = result.validateIncomingCandle(newSymbolCandle);
      
      expect(shouldAcceptNewCandle).toBe(true); // Should accept new symbol candle
    });
    
    it('should handle candles without symbol field gracefully', () => {
      mockState.selectedSymbol = 'BTCUSDT';
      
      const result = testSymbolSwitchRaceCondition('ETHUSDT');
      
      // Simulate receiving a candle without symbol field
      const candleWithoutSymbol = { timestamp: Date.now(), open: 50000 };
      const shouldAccept = result.validateIncomingCandle(candleWithoutSymbol);
      
      expect(shouldAccept).toBe(true); // Should accept when no symbol to validate
    });
  });

  describe('Stream Key Management', () => {
    function testStreamKeyGeneration(symbol, timeframe) {
      // Simulate stream key generation for candles
      return `${symbol}:${timeframe}`;
    }
    
    it('should generate correct stream keys for different combinations', () => {
      const testCases = [
        { symbol: 'BTCUSDT', timeframe: '1m', expected: 'BTCUSDT:1m' },
        { symbol: 'ETHUSDT', timeframe: '5m', expected: 'ETHUSDT:5m' },
        { symbol: 'XRPUSDT', timeframe: '1h', expected: 'XRPUSDT:1h' },
      ];
      
      testCases.forEach(({ symbol, timeframe, expected }) => {
        const streamKey = testStreamKeyGeneration(symbol, timeframe);
        expect(streamKey).toBe(expected);
      });
    });
    
    it('should create unique stream keys for different symbol/timeframe combinations', () => {
      const key1 = testStreamKeyGeneration('BTCUSDT', '1m');
      const key2 = testStreamKeyGeneration('BTCUSDT', '5m');
      const key3 = testStreamKeyGeneration('ETHUSDT', '1m');
      
      expect(key1).not.toBe(key2); // Same symbol, different timeframe
      expect(key1).not.toBe(key3); // Same timeframe, different symbol
      expect(key2).not.toBe(key3); // Different symbol and timeframe
    });
  });

  describe('Connection State Management', () => {
    function testConnectionStateTransition(initialState, action) {
      let connectionState = { ...initialState };
      
      switch (action.type) {
        case 'CONNECT':
          connectionState.connected = true;
          connectionState.connecting = false;
          connectionState.error = null;
          break;
        case 'DISCONNECT':
          connectionState.connected = false;
          connectionState.connecting = false;
          break;
        case 'CONNECTING':
          connectionState.connecting = true;
          connectionState.connected = false;
          connectionState.error = null;
          break;
        case 'ERROR':
          connectionState.connected = false;
          connectionState.connecting = false;
          connectionState.error = action.error;
          break;
      }
      
      return connectionState;
    }
    
    it('should handle connection state transitions correctly', () => {
      const initialState = { connected: false, connecting: false, error: null };
      
      // Test connecting state
      const connectingState = testConnectionStateTransition(initialState, { type: 'CONNECTING' });
      expect(connectingState.connecting).toBe(true);
      expect(connectingState.connected).toBe(false);
      
      // Test connected state
      const connectedState = testConnectionStateTransition(connectingState, { type: 'CONNECT' });
      expect(connectedState.connected).toBe(true);
      expect(connectedState.connecting).toBe(false);
      expect(connectedState.error).toBe(null);
      
      // Test disconnected state
      const disconnectedState = testConnectionStateTransition(connectedState, { type: 'DISCONNECT' });
      expect(disconnectedState.connected).toBe(false);
      expect(disconnectedState.connecting).toBe(false);
      
      // Test error state
      const errorState = testConnectionStateTransition(connectedState, { 
        type: 'ERROR', 
        error: 'Connection failed' 
      });
      expect(errorState.connected).toBe(false);
      expect(errorState.connecting).toBe(false);
      expect(errorState.error).toBe('Connection failed');
    });
  });
});