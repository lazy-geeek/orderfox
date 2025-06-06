import { 
  createMockStore, 
  setupOrderBookTests, 
  cleanupOrderBookTests, 
  renderOrderBookDisplay,
  TestSetup
} from './OrderBookDisplay.test.helpers';

describe('OrderBookDisplay - Dynamic Rounding Options useEffect', () => {
  let testSetup: TestSetup;

  beforeEach(() => {
    testSetup = setupOrderBookTests();
  });

  afterEach(() => {
    cleanupOrderBookTests(testSetup);
  });

  it('dispatches setAvailableRoundingOptions with correct options based on pricePrecision', () => {
    const mockSymbolsList = [
      {
        id: 'btcusdt',
        symbol: 'BTCUSDT',
        baseAsset: 'BTC',
        quoteAsset: 'USDT',
        uiName: 'BTC/USDT',
        pricePrecision: 2,
      },
    ];
    const store = createMockStore({
      selectedSymbol: 'BTCUSDT',
      symbolsList: mockSymbolsList,
    });
    
    renderOrderBookDisplay(store);

    // Check that the store state has been updated with the expected rounding options
    const state = store.getState();
    expect(state.marketData.availableRoundingOptions).toEqual([0.01, 0.1, 1, 10, 100, 1000]);
    expect(state.marketData.selectedRounding).toBe(0.01); // Should be set to baseRounding
  });


  it('dispatches setAvailableRoundingOptions with empty options when selectedSymbolData is not available', () => {
    const store = createMockStore({
      selectedSymbol: 'BTCUSDT',
      symbolsList: [], // Empty list means selectedSymbolData will be null
    });
    
    renderOrderBookDisplay(store);

    // Check that the store state has been updated with empty options
    const state = store.getState();
    expect(state.marketData.availableRoundingOptions).toEqual([]);
    expect(state.marketData.selectedRounding).toBe(null);
  });

  it('dispatches setAvailableRoundingOptions with empty options when selectedSymbol is null', () => {
    const store = createMockStore({
      selectedSymbol: null,
      symbolsList: [],
    });
    
    renderOrderBookDisplay(store);

    // Check that the store state has been updated with empty options
    const state = store.getState();
    expect(state.marketData.availableRoundingOptions).toEqual([]);
    expect(state.marketData.selectedRounding).toBe(null);
  });

  it('limits option generation based on current price (price-relative stopping condition)', () => {
    const mockOrderBook = {
      symbol: 'BTCUSDT',
      bids: [{ price: 50, amount: 1.5 }], // Low price to trigger stopping condition
      asks: [{ price: 51, amount: 1.2 }],
      timestamp: Date.now(),
    };

    const mockSymbolsList = [
      {
        id: 'btcusdt',
        symbol: 'BTCUSDT',
        baseAsset: 'BTC',
        quoteAsset: 'USDT',
        uiName: 'BTC/USDT',
        pricePrecision: 2,
      },
    ];
    const store = createMockStore({
      selectedSymbol: 'BTCUSDT',
      symbolsList: mockSymbolsList,
      currentOrderBook: mockOrderBook,
    });
    
    renderOrderBookDisplay(store);

    // Check that the store state has been updated with limited options
    // With current price = 50, options should stop when nextOption > 50/10 = 5
    // So options should be [0.01, 0.1, 1] (since 10 > 5)
    const state = store.getState();
    expect(state.marketData.availableRoundingOptions).toEqual([0.01, 0.1, 1]);
    expect(state.marketData.selectedRounding).toBe(0.01);
  });

  it('generates fallback options when current price is unavailable', () => {
    const mockSymbolsList = [
      {
        id: 'btcusdt',
        symbol: 'BTCUSDT',
        baseAsset: 'BTC',
        quoteAsset: 'USDT',
        uiName: 'BTC/USDT',
        pricePrecision: 2,
      },
    ];
    const store = createMockStore({
      selectedSymbol: 'BTCUSDT',
      symbolsList: mockSymbolsList,
      currentOrderBook: null, // No current price available
    });
    
    renderOrderBookDisplay(store);

    // Check that the store state has been updated with fallback options
    // Should generate at least 3-4 options when no current price is available
    const state = store.getState();
    expect(state.marketData.availableRoundingOptions.length).toBeGreaterThanOrEqual(3);
    expect(state.marketData.availableRoundingOptions).toContain(0.01); // baseRounding
    expect(state.marketData.selectedRounding).toBe(0.01);
  });

  it('preserves existing selectedRounding if it exists in new options', () => {
    const mockSymbolsList = [
      {
        id: 'btcusdt',
        symbol: 'BTCUSDT',
        baseAsset: 'BTC',
        quoteAsset: 'USDT',
        uiName: 'BTC/USDT',
        pricePrecision: 2,
      },
    ];
    const store = createMockStore({
      selectedSymbol: 'BTCUSDT',
      symbolsList: mockSymbolsList,
      selectedRounding: 0.1, // Existing value that should be preserved
    });
    
    renderOrderBookDisplay(store);

    // Check that the existing selectedRounding is preserved
    const state = store.getState();
    expect(state.marketData.selectedRounding).toBe(0.1); // Should preserve existing value
    expect(state.marketData.availableRoundingOptions).toContain(0.1); // Should be in options
  });

  it('resets to baseRounding when existing selectedRounding is not in new options', () => {
    const mockSymbolsList = [
      {
        id: 'btcusdt',
        symbol: 'BTCUSDT',
        baseAsset: 'BTC',
        quoteAsset: 'USDT',
        uiName: 'BTC/USDT',
        pricePrecision: 2,
      },
    ];
    const store = createMockStore({
      selectedSymbol: 'BTCUSDT',
      symbolsList: mockSymbolsList,
      selectedRounding: 0.001, // Value that won't be in the generated options
    });
    
    renderOrderBookDisplay(store);

    // Check that selectedRounding is reset to baseRounding
    const state = store.getState();
    expect(state.marketData.selectedRounding).toBe(0.01); // Should reset to baseRounding
    expect(state.marketData.availableRoundingOptions).not.toContain(0.001); // Should not contain old value
  });

  it('respects maximum absolute value stopping condition', () => {
    const mockSymbolsList = [
      {
        id: 'btcusdt',
        symbol: 'BTCUSDT',
        baseAsset: 'BTC',
        quoteAsset: 'USDT',
        uiName: 'BTC/USDT',
        pricePrecision: 8,
      },
    ];
    const store = createMockStore({
      selectedSymbol: 'BTCUSDT',
      symbolsList: mockSymbolsList,
      currentOrderBook: null, // No current price to trigger price-based stopping
    });
    
    renderOrderBookDisplay(store);

    // Check that the store state respects the maximum absolute value (1000)
    const state = store.getState();
    const maxOption = Math.max(...state.marketData.availableRoundingOptions);
    expect(maxOption).toBeLessThanOrEqual(1000); // Should not exceed 1000
    expect(state.marketData.selectedRounding).toBe(0.00000001); // Should be baseRounding
  });
});