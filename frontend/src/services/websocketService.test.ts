import { connectWebSocketStream, disconnectWebSocketStream } from './websocketService';

// Mock WebSocket at module level
const mockWebSocket = {
  readyState: 0,
  close: jest.fn(),
  onopen: null,
  onmessage: null,
  onerror: null,
  onclose: null,
  CONNECTING: 0,
  OPEN: 1,
  CLOSING: 2,
  CLOSED: 3,
};

// Mock global WebSocket constructor
const MockWebSocketConstructor = jest.fn(() => mockWebSocket);
(global as any).WebSocket = MockWebSocketConstructor;

// Mock dispatch function
const mockDispatch = jest.fn();

describe('WebSocket Service - Connection Management', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockWebSocket.readyState = 0; // CONNECTING
    mockWebSocket.close.mockClear();
    MockWebSocketConstructor.mockClear();
    
    // Reset internal state by accessing the module internals through require cache
    jest.resetModules();
  });

  test('should prevent multiple simultaneous connections for same stream', async () => {
    const symbol = 'BTCUSDT';
    const streamType = 'orderbook' as const;

    // Start first connection - should create WebSocket
    connectWebSocketStream(mockDispatch, symbol, streamType);
    
    // Try to start second connection immediately - should be prevented
    connectWebSocketStream(mockDispatch, symbol, streamType);

    // Should only create one WebSocket instance due to connection-in-progress check
    expect(MockWebSocketConstructor).toHaveBeenCalledTimes(1);
  });

  test('should handle connection in CONNECTING state', async () => {
    const symbol = 'ETHUSDT'; // Use different symbol to avoid state conflicts
    const streamType = 'orderbook' as const;

    // First call creates connection
    connectWebSocketStream(mockDispatch, symbol, streamType);
    
    // Second call should be prevented due to connection in progress
    connectWebSocketStream(mockDispatch, symbol, streamType);

    // Should only attempt one connection due to duplicate prevention
    expect(MockWebSocketConstructor).toHaveBeenCalledTimes(1);
  });

  test('should handle connection in OPEN state', async () => {
    const symbol = 'ADAUSDT'; // Use different symbol to avoid state conflicts
    const streamType = 'orderbook' as const;

    // Set mock to OPEN state and create connection
    mockWebSocket.readyState = mockWebSocket.OPEN;
    connectWebSocketStream(mockDispatch, symbol, streamType);
    
    // Reset mock call count to test second attempt
    MockWebSocketConstructor.mockClear();
    
    // Second call should be prevented due to OPEN state
    connectWebSocketStream(mockDispatch, symbol, streamType);

    // Should not create another WebSocket instance
    expect(MockWebSocketConstructor).toHaveBeenCalledTimes(0);
  });

  test('should call disconnect function without errors', () => {
    const symbol = 'XRPUSDT'; // Use different symbol to avoid state conflicts
    const streamType = 'orderbook' as const;

    // Should not throw an error even when no connection exists
    expect(() => {
      disconnectWebSocketStream(streamType, symbol);
    }).not.toThrow();
  });

  test('should create WebSocket with correct URL', () => {
    const symbol = 'DOTUSDT'; // Use different symbol to avoid state conflicts
    const streamType = 'orderbook' as const;

    connectWebSocketStream(mockDispatch, symbol, streamType);

    expect(MockWebSocketConstructor).toHaveBeenCalledWith(
      'ws://localhost:8000/api/v1/ws/orderbook/DOTUSDT'
    );
  });

  test('should create WebSocket with timeframe for candles', () => {
    const symbol = 'ETHUSDT';
    const streamType = 'candles' as const;
    const timeframe = '1m';

    connectWebSocketStream(mockDispatch, symbol, streamType, timeframe);

    expect(MockWebSocketConstructor).toHaveBeenCalledWith(
      'ws://localhost:8000/api/v1/ws/candles/ETHUSDT/1m'
    );
  });
});