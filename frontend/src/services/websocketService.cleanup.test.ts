import { disconnectWebSocketStream, connectWebSocketStream } from './websocketService';
import { AppDispatch } from '../store/store';
import {
  setOrderBookWsConnected,
} from '../features/marketData/marketDataSlice';

// Mock WebSocket
class MockWebSocket {
  url: string;
  readyState: number = 0; // CONNECTING
  onopen: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  
  private closeHandlerBackup: ((event: CloseEvent) => void) | null = null;

  constructor(url: string) {
    this.url = url;
    setTimeout(() => {
      this.readyState = 1; // OPEN
      if (this.onopen) {
        this.onopen(new Event('open'));
      }
    }, 10);
  }

  close(code?: number, reason?: string) {
    this.readyState = 3; // CLOSED
    // Store the close handler before it's nullified
    const handler = this.onclose || this.closeHandlerBackup;
    
    // Simulate the disconnectWebSocketStream clearing handlers
    if (code === 1000 && reason === 'Client initiated close') {
      this.closeHandlerBackup = this.onclose;
      this.onopen = null;
      this.onmessage = null;
      this.onerror = null;
      this.onclose = null;
    }
    
    // Still call the handler after a small delay to simulate async close
    setTimeout(() => {
      if (handler) {
        const event = new CloseEvent('close', { code: code || 1000, reason: reason || '' });
        handler(event);
      }
    }, 10);
  }

  send(data: string) {
    // Mock send
  }
}

// Mock the global WebSocket
(global as any).WebSocket = MockWebSocket;

describe('WebSocket Service Cleanup', () => {
  let mockDispatch: jest.MockedFunction<AppDispatch>;

  beforeEach(() => {
    mockDispatch = jest.fn();
    jest.clearAllMocks();
  });

  afterEach(() => {
    // Clean up all WebSocket connections
    disconnectWebSocketStream('orderbook', 'BTCUSDT');
    disconnectWebSocketStream('orderbook', 'ETHUSDT');
  });

  test('should properly clean up event handlers when disconnecting', async () => {
    // Connect to orderbook for BTCUSDT
    await connectWebSocketStream(mockDispatch, 'BTCUSDT', 'orderbook');
    
    // Wait for connection
    await new Promise(resolve => setTimeout(resolve, 20));

    // Verify connection was established
    expect(mockDispatch).toHaveBeenCalledWith(setOrderBookWsConnected(true));

    // Clear mock calls
    mockDispatch.mockClear();

    // Disconnect the WebSocket
    disconnectWebSocketStream('orderbook', 'BTCUSDT');

    // Wait a bit
    await new Promise(resolve => setTimeout(resolve, 50));

    // When manually disconnecting, the onclose handler is cleared first
    // so setOrderBookWsConnected(false) should not be called
    const calls = mockDispatch.mock.calls;
    const disconnectCalls = calls.filter(call =>
      call[0].type === 'marketData/setOrderBookWsConnected' &&
      call[0].payload === false
    );
    expect(disconnectCalls).toHaveLength(0);
  });

  test('should not mix data when switching symbols rapidly', async () => {
    // Connect to BTCUSDT
    await connectWebSocketStream(mockDispatch, 'BTCUSDT', 'orderbook');
    await new Promise(resolve => setTimeout(resolve, 20));

    // Verify first connection
    expect(mockDispatch).toHaveBeenCalledWith(setOrderBookWsConnected(true));
    const initialCalls = mockDispatch.mock.calls.length;

    // Immediately disconnect and connect to ETHUSDT
    disconnectWebSocketStream('orderbook', 'BTCUSDT');
    await new Promise(resolve => setTimeout(resolve, 50));
    
    await connectWebSocketStream(mockDispatch, 'ETHUSDT', 'orderbook');
    await new Promise(resolve => setTimeout(resolve, 20));

    // Verify proper cleanup occurred
    const allCalls = mockDispatch.mock.calls;
    
    // Find the calls after the initial connection
    const subsequentCalls = allCalls.slice(initialCalls);
    const connectedCalls = subsequentCalls.filter(call =>
      call[0].type === 'marketData/setOrderBookWsConnected' &&
      call[0].payload === true
    );
    
    // Should have connected to ETHUSDT
    expect(connectedCalls).toHaveLength(1);
    
    // Verify no mixed data by checking that we don't have multiple active connections
    const finalState = allCalls[allCalls.length - 1];
    expect(finalState[0].type).toBe('marketData/setOrderBookWsConnected');
    expect(finalState[0].payload).toBe(true);
  });

  test('should not attempt to reconnect after manual disconnect', async () => {
    // Connect to orderbook
    await connectWebSocketStream(mockDispatch, 'BTCUSDT', 'orderbook');
    await new Promise(resolve => setTimeout(resolve, 20));

    const initialCallCount = mockDispatch.mock.calls.length;

    // Manually disconnect
    disconnectWebSocketStream('orderbook', 'BTCUSDT');
    
    // Wait for potential reconnection attempts
    await new Promise(resolve => setTimeout(resolve, 1000));

    // Should not have any additional connection attempts
    const additionalCalls = mockDispatch.mock.calls.length - initialCallCount;
    // Should only have the disconnect call, no reconnection attempts
    expect(additionalCalls).toBeLessThanOrEqual(1);
  });
});