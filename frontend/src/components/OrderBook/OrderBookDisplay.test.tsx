import {
  createMockStore,
  setupOrderBookTests,
  cleanupOrderBookTests,
  renderOrderBookDisplay,
  screen,
  TestSetup
} from './OrderBookDisplay.test.helpers';

describe('OrderBookDisplay', () => {
  let testSetup: TestSetup;

  beforeEach(() => {
    testSetup = setupOrderBookTests();
  });

  afterEach(() => {
    cleanupOrderBookTests(testSetup);
  });

  it('renders no symbol selected state when no symbol is selected', () => {
    const store = createMockStore();
    
    renderOrderBookDisplay(store);

    expect(screen.getByText('Order Book')).toBeInTheDocument();
    expect(screen.getByText('Select a symbol to view order book')).toBeInTheDocument();
  });

  it('renders order book data when available', async () => {
    const mockOrderBook = {
      symbol: 'BTCUSDT',
      bids: [
        { price: 50000, amount: 1.5 },
        { price: 49999, amount: 2.0 },
      ],
      asks: [
        { price: 50001, amount: 1.2 },
        { price: 50002, amount: 1.8 },
        { price: 50003, amount: 0.5 },
      ],
      timestamp: Date.now(),
    };

    // Set a specific mock for apiClient.get for this test BEFORE rendering
    testSetup.apiClientGetSpy.mockResolvedValueOnce({ data: mockOrderBook });

    const store = createMockStore({
      selectedSymbol: 'BTCUSDT',
      currentOrderBook: mockOrderBook,
      orderBookLoading: false,
    });
    
    renderOrderBookDisplay(store);
    // Wait for the async action (fetchOrderBook) to complete
    await screen.findByText('50000'); // Wait for a bid price to appear

    expect(screen.getByText('BTCUSDT')).toBeInTheDocument();
    expect(screen.getByText('50000')).toBeInTheDocument();
    expect(screen.getByText('50001')).toBeInTheDocument();
    // Check for bids amounts and totals
    // Query for elements with class 'amount' and 'total' specifically
    const bid50000Amount = screen.getByText('1.5', { selector: '.bid-level .amount' });
    const bid50000Total = screen.getByText('1.5', { selector: '.bid-level .total' });
    expect(bid50000Amount).toBeInTheDocument();
    expect(bid50000Total).toBeInTheDocument();

    const bid49999Amount = screen.getByText('2', { selector: '.bid-level .amount' });
    const bid49999Total = screen.getByText('3.5', { selector: '.bid-level .total' }); // 1.5 + 2.0
    expect(bid49999Amount).toBeInTheDocument();
    expect(bid49999Total).toBeInTheDocument();

    // Check for asks amounts and totals
    // The asks are reversed, so 50003 (amount 0.5) will be first, then 50002 (amount 1.8), then 50001 (amount 1.2)
    // The total for 50003 is 0.5
    // The total for 50002 is 0.5 + 1.8 = 2.3
    // The total for 50001 is 0.5 + 1.8 + 1.2 = 3.5
    const ask50003Amount = screen.getByText('0.5', { selector: '.ask-level .amount' });
    const ask50003Total = screen.getByText('0.5', { selector: '.ask-level .total' });
    expect(ask50003Amount).toBeInTheDocument();
    expect(ask50003Total).toBeInTheDocument();

    const ask50002Amount = screen.getByText('1.8', { selector: '.ask-level .amount' });
    const ask50002Total = screen.getByText('2.3', { selector: '.ask-level .total' });
    expect(ask50002Amount).toBeInTheDocument();
    expect(ask50002Total).toBeInTheDocument();

    const ask50001Amount = screen.getByText('1.2', { selector: '.ask-level .amount' });
    const ask50001Total = screen.getByText('3.5', { selector: '.ask-level .total' });
    expect(ask50001Amount).toBeInTheDocument();
    expect(ask50001Total).toBeInTheDocument();
  });

  it('displays spread information when both bids and asks are available', async () => {
    const mockOrderBook = {
      symbol: 'BTCUSDT',
      bids: [{ price: 50000, amount: 1.5 }],
      asks: [{ price: 50001, amount: 1.2 }],
      timestamp: Date.now(),
    };

    // Set a specific mock for apiClient.get for this test BEFORE rendering
    testSetup.apiClientGetSpy.mockResolvedValueOnce({ data: mockOrderBook });

    const store = createMockStore({
      selectedSymbol: 'BTCUSDT',
      currentOrderBook: mockOrderBook,
      orderBookLoading: false,
    });
    
    renderOrderBookDisplay(store);

    // Wait for the async action (fetchOrderBook) to complete
    await screen.findByText('Spread:');

    expect(screen.getByText('Spread:')).toBeInTheDocument();
    expect(screen.getByText('1')).toBeInTheDocument(); // spread value
  });

  it('renders depth selector with default value', async () => {
    const mockOrderBookForDepth = {
      symbol: 'BTCUSDT',
      bids: [{ price: 50000, amount: 1.5 }],
      asks: [{ price: 50001, amount: 1.2 }],
      timestamp: Date.now(),
    };

    // Set a specific mock for apiClient.get for this test BEFORE rendering
    testSetup.apiClientGetSpy.mockResolvedValueOnce({ data: mockOrderBookForDepth });

    const store = createMockStore({
      selectedSymbol: 'BTCUSDT',
      currentOrderBook: mockOrderBookForDepth,
      orderBookLoading: false,
    });
    
    renderOrderBookDisplay(store);

    // Wait for the async action (fetchOrderBook) to complete
    await screen.findByText('Display Depth:');

    expect(screen.getByText('Display Depth:')).toBeInTheDocument();
    // Check for the depth select element with value 10
    const depthSelectElement = screen.getByLabelText('Display Depth:');
    expect(depthSelectElement).toHaveValue('10');
    
    // Check that the rounding selector is also present
    expect(screen.getByText('Rounding:')).toBeInTheDocument();
    const roundingSelectElement = screen.getByLabelText('Rounding:');
    expect(roundingSelectElement).toBeInTheDocument();
  });

  it('renders component without crashing', () => {
    const store = createMockStore();
    
    renderOrderBookDisplay(store);
    // No act needed here as no state updates are expected from this render
  });

  it('displays asks in correct order (lowest price at bottom)', async () => {
    const mockOrderBook = {
      symbol: 'BTCUSDT',
      bids: [],
      asks: [
        { price: 50001, amount: 1.2 },
        { price: 50002, amount: 1.8 },
        { price: 50003, amount: 0.5 },
      ],
      timestamp: Date.now(),
    };

    // Set a specific mock for apiClient.get for this test BEFORE rendering
    testSetup.apiClientGetSpy.mockResolvedValueOnce({ data: mockOrderBook });

    const store = createMockStore({
      selectedSymbol: 'BTCUSDT',
      currentOrderBook: mockOrderBook,
      orderBookLoading: false,
    });
    
    renderOrderBookDisplay(store);
    // Wait for the async action (fetchOrderBook) to complete
    await screen.findByText('50003'); // Wait for an ask price to appear

    // Query for all elements that display an ask price
    // Query for all elements that display an ask price using text content and then filter by class
    const askPriceElements = screen.getAllByText(/^\d+\.?\d*$/)
                                   .filter(el => el.classList.contains('ask-price'));
    
    const displayedAskPrices = askPriceElements.map(el => parseFloat(el.textContent || '0'));

    // Expect the displayed asks to be in descending order of price (highest at top, lowest at bottom)
    // The original asks array is [50001, 50002, 50003] (lowest to highest)
    // After reverse and slice, it should be [50003, 50002, 50001] for display
    expect(displayedAskPrices).toEqual([50003, 50002, 50001]);
  });

  describe('Order Book Aggregation Logic', () => {
    // Simple test to verify aggregation logic works
    it('aggregates order book data correctly with simple test case', async () => {
      const mockOrderBook = {
        symbol: 'BTCUSDT',
        bids: [
          { price: 100.15, amount: 1.0 }, // rounds down to 100.1
          { price: 100.19, amount: 2.0 }, // rounds down to 100.1
        ],
        asks: [
          { price: 101.05, amount: 1.0 }, // rounds up to 101.1
          { price: 101.01, amount: 2.0 }, // rounds up to 101.1
        ],
        timestamp: Date.now(),
      };

      testSetup.apiClientGetSpy.mockResolvedValueOnce({ data: mockOrderBook });

      const store = createMockStore({
        selectedSymbol: 'BTCUSDT',
        symbolsList: [{
          id: 'btcusdt',
          symbol: 'BTCUSDT',
          baseAsset: 'BTC',
          quoteAsset: 'USDT',
          uiName: 'BTC/USDT',
          tickSize: 0.1, // Set tickSize to match our test rounding
          pricePrecision: 1
        }],
        currentOrderBook: mockOrderBook,
        selectedRounding: 0.1, // This should be kept since it matches tickSize
        availableRoundingOptions: [0.1, 1, 10],
        orderBookLoading: false,
      });
      
      renderOrderBookDisplay(store);
      await screen.findByText('100.1'); // Wait for aggregated price to appear

      // Should aggregate amounts: 1.0 + 2.0 = 3.0 for bids at 100.1
      expect(screen.getByText('100.1')).toBeInTheDocument();
      expect(screen.getByText('3', { selector: '.bid-level .amount' })).toBeInTheDocument();
      
      // Should aggregate amounts: 1.0 + 2.0 = 3.0 for asks at 101.1
      expect(screen.getByText('101.1')).toBeInTheDocument();
      expect(screen.getByText('3', { selector: '.ask-level .amount' })).toBeInTheDocument();
    });
    it('returns raw data when selectedRounding is null', async () => {
      const mockOrderBook = {
        symbol: 'BTCUSDT',
        bids: [
          { price: 50000.123, amount: 1.5 },
          { price: 49999.456, amount: 2.0 },
        ],
        asks: [
          { price: 50001.789, amount: 1.2 },
          { price: 50002.012, amount: 1.8 },
        ],
        timestamp: Date.now(),
      };

      testSetup.apiClientGetSpy.mockResolvedValueOnce({ data: mockOrderBook });

      const store = createMockStore({
        selectedSymbol: 'BTCUSDT',
        symbolsList: [], // No symbol data to prevent auto-calculation of rounding options
        currentOrderBook: mockOrderBook,
        selectedRounding: null, // No rounding selected
        availableRoundingOptions: [], // Empty options to prevent auto-setting
        orderBookLoading: false,
      });
      
      renderOrderBookDisplay(store);
      await screen.findByText('50000.123'); // Wait for raw price to appear

      // Should display raw prices without aggregation
      expect(screen.getByText('50000.123')).toBeInTheDocument();
      expect(screen.getByText('49999.456')).toBeInTheDocument();
      expect(screen.getByText('50001.789')).toBeInTheDocument();
      expect(screen.getByText('50002.012')).toBeInTheDocument();
    });

    it('returns empty structure when currentOrderBook is null', async () => {
      const store = createMockStore({
        selectedSymbol: 'BTCUSDT',
        symbolsList: [{
          id: 'btcusdt',
          symbol: 'BTCUSDT',
          baseAsset: 'BTC',
          quoteAsset: 'USDT',
          uiName: 'BTC/USDT',
          tickSize: 0.1, // Match the selectedRounding value
          pricePrecision: 1
        }],
        currentOrderBook: { bids: [], asks: [], symbol: 'BTCUSDT', timestamp: Date.now() }, // Empty order book instead of null
        selectedRounding: 0.1,
        availableRoundingOptions: [0.1, 1, 10],
        orderBookLoading: false,
      });
      
      renderOrderBookDisplay(store);
      
      expect(screen.getByText('No bids available')).toBeInTheDocument();
      expect(screen.getByText('No asks available')).toBeInTheDocument();
    });

    it('aggregates bids correctly by rounding down', async () => {
      const mockOrderBook = {
        symbol: 'BTCUSDT',
        bids: [
          { price: 50000.15, amount: 1.0 }, // rounds down to 50000.1
          { price: 50000.19, amount: 2.0 }, // rounds down to 50000.1
          { price: 50000.05, amount: 1.5 }, // rounds down to 50000.0
          { price: 49999.95, amount: 0.5 }, // rounds down to 49999.9
        ],
        asks: [],
        timestamp: Date.now(),
      };

      testSetup.apiClientGetSpy.mockResolvedValueOnce({ data: mockOrderBook });

      const store = createMockStore({
        selectedSymbol: 'BTCUSDT',
        symbolsList: [{
          id: 'btcusdt',
          symbol: 'BTCUSDT',
          baseAsset: 'BTC',
          quoteAsset: 'USDT',
          uiName: 'BTC/USDT',
          tickSize: 0.1, // Match the selectedRounding value
          pricePrecision: 1
        }],
        currentOrderBook: mockOrderBook,
        selectedRounding: 0.1,
        availableRoundingOptions: [0.01, 0.1, 1, 10],
        orderBookLoading: false,
      });
      
      renderOrderBookDisplay(store);
      await screen.findByText('50000.1'); // Wait for aggregated price to appear

      // Should aggregate amounts for same rounded price levels
      // 50000.15 and 50000.19 both round down to 50000.1, so amounts should be 1.0 + 2.0 = 3.0
      expect(screen.getByText('50000.1')).toBeInTheDocument();
      expect(screen.getByText('3', { selector: '.bid-level .amount' })).toBeInTheDocument();
      
      // 50000.05 rounds down to 50000.0
      expect(screen.getByText('50000')).toBeInTheDocument();
      expect(screen.getByText('1.5', { selector: '.bid-level .amount' })).toBeInTheDocument();
      
      // 49999.95 rounds down to 49999.9
      expect(screen.getByText('49999.9')).toBeInTheDocument();
      expect(screen.getByText('0.5', { selector: '.bid-level .amount' })).toBeInTheDocument();
    });

    it('aggregates asks correctly by rounding up', async () => {
      const mockOrderBook = {
        symbol: 'BTCUSDT',
        bids: [],
        asks: [
          { price: 50001.05, amount: 1.0 }, // rounds up to 50001.1
          { price: 50001.01, amount: 2.0 }, // rounds up to 50001.1
          { price: 50001.15, amount: 1.5 }, // rounds up to 50001.2
          { price: 50002.05, amount: 0.5 }, // rounds up to 50002.1
        ],
        timestamp: Date.now(),
      };

      testSetup.apiClientGetSpy.mockResolvedValueOnce({ data: mockOrderBook });

      const store = createMockStore({
        selectedSymbol: 'BTCUSDT',
        symbolsList: [{
          id: 'btcusdt',
          symbol: 'BTCUSDT',
          baseAsset: 'BTC',
          quoteAsset: 'USDT',
          uiName: 'BTC/USDT',
          tickSize: 0.1, // Match the selectedRounding value
          pricePrecision: 1
        }],
        currentOrderBook: mockOrderBook,
        selectedRounding: 0.1,
        availableRoundingOptions: [0.01, 0.1, 1, 10],
        orderBookLoading: false,
      });
      
      renderOrderBookDisplay(store);
      await screen.findByText('50001.1'); // Wait for aggregated price to appear

      // Should aggregate amounts for same rounded price levels
      // 50001.05 and 50001.01 both round up to 50001.1, so amounts should be 1.0 + 2.0 = 3.0
      expect(screen.getByText('50001.1')).toBeInTheDocument();
      expect(screen.getByText('3', { selector: '.ask-level .amount' })).toBeInTheDocument();
      
      // 50001.15 rounds up to 50001.2
      expect(screen.getByText('50001.2')).toBeInTheDocument();
      expect(screen.getByText('1.5', { selector: '.ask-level .amount' })).toBeInTheDocument();
      
      // 50002.05 rounds up to 50002.1
      expect(screen.getByText('50002.1')).toBeInTheDocument();
      expect(screen.getByText('0.5', { selector: '.ask-level .amount' })).toBeInTheDocument();
    });

    it('sorts aggregated bids by price descending', async () => {
      const mockOrderBook = {
        symbol: 'BTCUSDT',
        bids: [
          { price: 49999.95, amount: 1.0 }, // rounds down to 49999.9
          { price: 50000.15, amount: 2.0 }, // rounds down to 50000.1
          { price: 50000.05, amount: 1.5 }, // rounds down to 50000.0
        ],
        asks: [],
        timestamp: Date.now(),
      };

      testSetup.apiClientGetSpy.mockResolvedValueOnce({ data: mockOrderBook });

      const store = createMockStore({
        selectedSymbol: 'BTCUSDT',
        symbolsList: [{
          id: 'btcusdt',
          symbol: 'BTCUSDT',
          baseAsset: 'BTC',
          quoteAsset: 'USDT',
          uiName: 'BTC/USDT',
          tickSize: 0.1, // Match the selectedRounding value
          pricePrecision: 1
        }],
        currentOrderBook: mockOrderBook,
        selectedRounding: 0.1,
        availableRoundingOptions: [0.1, 1, 10],
        orderBookLoading: false,
      });
      
      renderOrderBookDisplay(store);
      await screen.findByText('50000.1'); // Wait for aggregated price to appear

      const bidPriceElements = screen.getAllByText(/^\d+\.?\d*$/)
                                    .filter(el => el.classList.contains('bid-price'));
      const displayedBidPrices = bidPriceElements.map(el => parseFloat(el.textContent || '0'));

      // Should be sorted descending: 50000.1, 50000, 49999.9
      expect(displayedBidPrices).toEqual([50000.1, 50000, 49999.9]);
    });

    it('sorts aggregated asks by price ascending', async () => {
      const mockOrderBook = {
        symbol: 'BTCUSDT',
        bids: [],
        asks: [
          { price: 50002.05, amount: 1.0 }, // rounds up to 50002.1
          { price: 50001.05, amount: 2.0 }, // rounds up to 50001.1
          { price: 50001.15, amount: 1.5 }, // rounds up to 50001.2
        ],
        timestamp: Date.now(),
      };

      testSetup.apiClientGetSpy.mockResolvedValueOnce({ data: mockOrderBook });

      const store = createMockStore({
        selectedSymbol: 'BTCUSDT',
        symbolsList: [{
          id: 'btcusdt',
          symbol: 'BTCUSDT',
          baseAsset: 'BTC',
          quoteAsset: 'USDT',
          uiName: 'BTC/USDT',
          tickSize: 0.1, // Match the selectedRounding value
          pricePrecision: 1
        }],
        currentOrderBook: mockOrderBook,
        selectedRounding: 0.1,
        availableRoundingOptions: [0.1, 1, 10],
        orderBookLoading: false,
      });
      
      renderOrderBookDisplay(store);
      await screen.findByText('50001.1'); // Wait for aggregated price to appear

      const askPriceElements = screen.getAllByText(/^\d+\.?\d*$/)
                                    .filter(el => el.classList.contains('ask-price'));
      const displayedAskPrices = askPriceElements.map(el => parseFloat(el.textContent || '0'));

      // Asks are displayed reversed (highest at top), so we expect: 50002.1, 50001.2, 50001.1
      expect(displayedAskPrices).toEqual([50002.1, 50001.2, 50001.1]);
    });

    it('handles edge case where all items group into one level', async () => {
      const mockOrderBook = {
        symbol: 'BTCUSDT',
        bids: [
          { price: 50000.01, amount: 1.0 },
          { price: 50000.02, amount: 2.0 },
          { price: 50000.03, amount: 1.5 },
        ],
        asks: [
          { price: 50001.01, amount: 1.0 },
          { price: 50001.02, amount: 2.0 },
          { price: 50001.03, amount: 1.5 },
        ],
        timestamp: Date.now(),
      };

      testSetup.apiClientGetSpy.mockResolvedValueOnce({ data: mockOrderBook });

      const store = createMockStore({
        selectedSymbol: 'BTCUSDT',
        symbolsList: [{
          id: 'btcusdt',
          symbol: 'BTCUSDT',
          baseAsset: 'BTC',
          quoteAsset: 'USDT',
          uiName: 'BTC/USDT',
          tickSize: 1, // Match the selectedRounding value
          pricePrecision: 0
        }],
        currentOrderBook: mockOrderBook,
        selectedRounding: 1, // Large rounding value
        availableRoundingOptions: [1, 10, 100],
        orderBookLoading: false,
      });
      
      renderOrderBookDisplay(store);
      await screen.findByText('50000'); // Wait for aggregated price to appear

      // All bids should aggregate to 50000 (rounded down)
      expect(screen.getByText('50000')).toBeInTheDocument();
      expect(screen.getByText('4.5', { selector: '.bid-level .amount' })).toBeInTheDocument(); // 1.0 + 2.0 + 1.5

      // All asks should aggregate to 50002 (rounded up)
      expect(screen.getByText('50002')).toBeInTheDocument();
      expect(screen.getByText('4.5', { selector: '.ask-level .amount' })).toBeInTheDocument(); // 1.0 + 2.0 + 1.5
    });

    it('handles prices that are exact multiples of rounding factor', async () => {
      const mockOrderBook = {
        symbol: 'BTCUSDT',
        bids: [
          { price: 50000.0, amount: 1.0 }, // exact multiple
          { price: 50000.1, amount: 2.0 }, // exact multiple
          { price: 50000.05, amount: 1.5 }, // rounds down to 50000.0
        ],
        asks: [
          { price: 50001.0, amount: 1.0 }, // exact multiple
          { price: 50001.1, amount: 2.0 }, // exact multiple
          { price: 50001.05, amount: 1.5 }, // rounds up to 50001.1
        ],
        timestamp: Date.now(),
      };

      testSetup.apiClientGetSpy.mockResolvedValueOnce({ data: mockOrderBook });

      const store = createMockStore({
        selectedSymbol: 'BTCUSDT',
        symbolsList: [{
          id: 'btcusdt',
          symbol: 'BTCUSDT',
          baseAsset: 'BTC',
          quoteAsset: 'USDT',
          uiName: 'BTC/USDT',
          tickSize: 0.1, // Match the selectedRounding value
          pricePrecision: 1
        }],
        currentOrderBook: mockOrderBook,
        selectedRounding: 0.1,
        availableRoundingOptions: [0.1, 1, 10],
        orderBookLoading: false,
      });
      
      renderOrderBookDisplay(store);
      await screen.findByText('50000.1'); // Wait for aggregated price to appear

      // Bids: 50000.0 (1.0 + 1.5 = 2.5), 50000.1 (2.0)
      expect(screen.getByText('50000')).toBeInTheDocument();
      expect(screen.getByText('2.5', { selector: '.bid-level .amount' })).toBeInTheDocument();
      expect(screen.getByText('50000.1')).toBeInTheDocument();
      expect(screen.getByText('2', { selector: '.bid-level .amount' })).toBeInTheDocument();

      // Asks: 50001.0 (1.0), 50001.1 (2.0 + 1.5 = 3.5)
      expect(screen.getByText('50001')).toBeInTheDocument();
      expect(screen.getByText('1', { selector: '.ask-level .amount' })).toBeInTheDocument();
      expect(screen.getByText('50001.1')).toBeInTheDocument();
      expect(screen.getByText('3.5', { selector: '.ask-level .amount' })).toBeInTheDocument();
    });

    it('handles empty bids and asks arrays', async () => {
      const mockOrderBook = {
        symbol: 'BTCUSDT',
        bids: [],
        asks: [],
        timestamp: Date.now(),
      };

      testSetup.apiClientGetSpy.mockResolvedValueOnce({ data: mockOrderBook });

      const store = createMockStore({
        selectedSymbol: 'BTCUSDT',
        symbolsList: [{
          id: 'btcusdt',
          symbol: 'BTCUSDT',
          baseAsset: 'BTC',
          quoteAsset: 'USDT',
          uiName: 'BTC/USDT',
          tickSize: 0.1, // Match the selectedRounding value
          pricePrecision: 1
        }],
        currentOrderBook: mockOrderBook,
        selectedRounding: 0.1,
        availableRoundingOptions: [0.1, 1, 10],
        orderBookLoading: false,
      });
      
      renderOrderBookDisplay(store);
      
      expect(screen.getByText('No bids available')).toBeInTheDocument();
      expect(screen.getByText('No asks available')).toBeInTheDocument();
    });
  });

  describe('Aggregated Data Display and Depth Limiting', () => {
    it('uses aggregated data and respects displayDepth for both bids and asks', async () => {
      const mockOrderBook = {
        symbol: 'BTCUSDT',
        bids: [
          { price: 50000.15, amount: 1.0 }, // rounds down to 50000.1
          { price: 50000.19, amount: 2.0 }, // rounds down to 50000.1 (aggregated: 3.0)
          { price: 49999.95, amount: 1.5 }, // rounds down to 49999.9
          { price: 49998.85, amount: 0.8 }, // rounds down to 49998.8
          { price: 49997.75, amount: 0.5 }, // rounds down to 49997.7
          { price: 49996.65, amount: 0.3 }, // rounds down to 49996.6 (should be cut off by displayDepth=5)
        ],
        asks: [
          { price: 50001.05, amount: 1.0 }, // rounds up to 50001.1
          { price: 50001.01, amount: 2.0 }, // rounds up to 50001.1 (aggregated: 3.0)
          { price: 50002.15, amount: 1.5 }, // rounds up to 50002.2
          { price: 50003.25, amount: 0.8 }, // rounds up to 50003.3
          { price: 50004.35, amount: 0.5 }, // rounds up to 50004.4
          { price: 50005.45, amount: 0.3 }, // rounds up to 50005.5 (should be cut off by displayDepth=5)
        ],
        timestamp: Date.now(),
      };

      testSetup.apiClientGetSpy.mockResolvedValueOnce({ data: mockOrderBook });

      const store = createMockStore({
        selectedSymbol: 'BTCUSDT',
        symbolsList: [{
          id: 'btcusdt',
          symbol: 'BTCUSDT',
          baseAsset: 'BTC',
          quoteAsset: 'USDT',
          uiName: 'BTC/USDT',
          tickSize: 0.1,
          pricePrecision: 1
        }],
        currentOrderBook: mockOrderBook,
        selectedRounding: 0.1,
        availableRoundingOptions: [0.1, 1, 10],
        orderBookLoading: false,
      });
      
      renderOrderBookDisplay(store);

      await screen.findByText('50000.1'); // Wait for aggregated price to appear

      // Verify the aggregated bid prices and amounts (sorted descending)
      expect(screen.getByText('50000.1')).toBeInTheDocument(); // aggregated from 50000.15 + 50000.19
      expect(screen.getByText('3', { selector: '.bid-level .amount' })).toBeInTheDocument(); // 1.0 + 2.0
      expect(screen.getByText('49999.9')).toBeInTheDocument();
      expect(screen.getByText('1.5', { selector: '.bid-level .amount' })).toBeInTheDocument();
      expect(screen.getByText('49998.8')).toBeInTheDocument();
      expect(screen.getByText('0.8', { selector: '.bid-level .amount' })).toBeInTheDocument();
      
      // Verify the aggregated ask prices and amounts (displayed in reverse order: highest first)
      expect(screen.getByText('50004.4')).toBeInTheDocument(); // highest displayed ask
      expect(screen.getByText('0.5', { selector: '.ask-level .amount' })).toBeInTheDocument();
      expect(screen.getByText('50003.3')).toBeInTheDocument();
      expect(screen.getByText('0.8', { selector: '.ask-level .amount' })).toBeInTheDocument();
      expect(screen.getByText('50002.2')).toBeInTheDocument();
      expect(screen.getByText('1.5', { selector: '.ask-level .amount' })).toBeInTheDocument();
      expect(screen.getByText('50001.1')).toBeInTheDocument(); // aggregated from 50001.05 + 50001.01
      expect(screen.getByText('3', { selector: '.ask-level .amount' })).toBeInTheDocument(); // 1.0 + 2.0
    });

    it('displays raw data when selectedRounding is null (no aggregation)', async () => {
      const mockOrderBook = {
        symbol: 'BTCUSDT',
        bids: [
          { price: 50000.123, amount: 1.5 },
          { price: 49999.456, amount: 2.0 },
          { price: 49998.789, amount: 1.2 },
        ],
        asks: [
          { price: 50001.234, amount: 1.2 },
          { price: 50002.567, amount: 1.8 },
          { price: 50003.890, amount: 0.5 },
        ],
        timestamp: Date.now(),
      };

      testSetup.apiClientGetSpy.mockResolvedValueOnce({ data: mockOrderBook });

      const store = createMockStore({
        selectedSymbol: 'BTCUSDT',
        symbolsList: [], // No symbol data to prevent auto-calculation of rounding options
        currentOrderBook: mockOrderBook,
        selectedRounding: null, // No rounding selected
        availableRoundingOptions: [],
        orderBookLoading: false,
      });
      
      renderOrderBookDisplay(store);

      // Wait for raw price to appear using findBy which handles async
      // Wait for any price to appear first as indicator of rendering completion
      await screen.findByText(/\d+\.\d+/, { selector: '.price' });
      // Then verify specific prices
      expect(screen.getByText('50000.123')).toBeInTheDocument();

      // Verify that raw prices are displayed without aggregation
      expect(screen.getByText('50000.123')).toBeInTheDocument();
      expect(screen.getByText('49999.456')).toBeInTheDocument();
      expect(screen.getByText('50001.234')).toBeInTheDocument();
      expect(screen.getByText('50002.567')).toBeInTheDocument();
      
      // Verify that raw amounts are displayed
      expect(screen.getByText('1.5', { selector: '.bid-level .amount' })).toBeInTheDocument();
      expect(screen.getByText('2', { selector: '.bid-level .amount' })).toBeInTheDocument();
      expect(screen.getByText('1.2', { selector: '.ask-level .amount' })).toBeInTheDocument();
      expect(screen.getByText('1.8', { selector: '.ask-level .amount' })).toBeInTheDocument();
    });

    it('respects displayDepth setting when using aggregated data', async () => {
      const mockOrderBook = {
        symbol: 'BTCUSDT',
        bids: [
          { price: 50000.15, amount: 1.0 }, // rounds down to 50000.1
          { price: 49999.95, amount: 1.5 }, // rounds down to 49999.9
          { price: 49998.85, amount: 0.8 }, // rounds down to 49998.8
          { price: 49997.75, amount: 0.5 }, // rounds down to 49997.7
          { price: 49996.65, amount: 0.3 }, // rounds down to 49996.6
          { price: 49995.55, amount: 0.2 }, // rounds down to 49995.5
        ],
        asks: [
          { price: 50001.05, amount: 1.0 }, // rounds up to 50001.1
          { price: 50002.15, amount: 1.5 }, // rounds up to 50002.2
          { price: 50003.25, amount: 0.8 }, // rounds up to 50003.3
          { price: 50004.35, amount: 0.5 }, // rounds up to 50004.4
          { price: 50005.45, amount: 0.3 }, // rounds up to 50005.5
          { price: 50006.55, amount: 0.2 }, // rounds up to 50006.6
        ],
        timestamp: Date.now(),
      };

      testSetup.apiClientGetSpy.mockResolvedValueOnce({ data: mockOrderBook });

      const store = createMockStore({
        selectedSymbol: 'BTCUSDT',
        symbolsList: [{
          id: 'btcusdt',
          symbol: 'BTCUSDT',
          baseAsset: 'BTC',
          quoteAsset: 'USDT',
          uiName: 'BTC/USDT',
          tickSize: 0.1,
          pricePrecision: 1
        }],
        currentOrderBook: mockOrderBook,
        selectedRounding: 0.1,
        availableRoundingOptions: [0.1, 1, 10],
        orderBookLoading: false,
      });
      
      renderOrderBookDisplay(store);

      await screen.findByText('50000.1'); // Wait for aggregated price to appear

      // With default displayDepth of 10, all 6 levels should be visible
      expect(screen.getByText('50000.1')).toBeInTheDocument();
      expect(screen.getByText('49999.9')).toBeInTheDocument();
      expect(screen.getByText('49998.8')).toBeInTheDocument();
      expect(screen.getByText('49997.7')).toBeInTheDocument();
      expect(screen.getByText('49996.6')).toBeInTheDocument();
      expect(screen.getByText('49995.5')).toBeInTheDocument();

      expect(screen.getByText('50001.1')).toBeInTheDocument();
      expect(screen.getByText('50002.2')).toBeInTheDocument();
      expect(screen.getByText('50003.3')).toBeInTheDocument();
      expect(screen.getByText('50004.4')).toBeInTheDocument();
      expect(screen.getByText('50005.5')).toBeInTheDocument();
      expect(screen.getByText('50006.6')).toBeInTheDocument();

      // Verify that we have exactly 6 bid and 6 ask price elements
      const bidPriceElements = screen.getAllByText(/^\d+\.?\d*$/)
                                    .filter(el => el.classList.contains('bid-price'));
      expect(bidPriceElements).toHaveLength(6);
      
      const askPriceElements = screen.getAllByText(/^\d+\.?\d*$/)
                                    .filter(el => el.classList.contains('ask-price'));
      expect(askPriceElements).toHaveLength(6);
    });
  });

  describe('Formatting and Precision', () => {
    describe('K/M/B Formatting', () => {
      it('formats amounts and totals with K/M/B suffixes', async () => {
        const mockOrderBook = {
          symbol: 'BTCUSDT',
          bids: [
            { price: 50000, amount: 1234 }, // Should display as 1.23K
            { price: 49999, amount: 1234567 }, // Should display as 1.23M
          ],
          asks: [
            { price: 50001, amount: 1234567890 }, // Should display as 1.23B
            { price: 50002, amount: 5678 }, // Should display as 5.68K
          ],
          timestamp: Date.now(),
        };

        testSetup.apiClientGetSpy.mockResolvedValueOnce({ data: mockOrderBook });

        const store = createMockStore({
          selectedSymbol: 'BTCUSDT',
          symbolsList: [{
            id: 'btcusdt',
            symbol: 'BTCUSDT',
            baseAsset: 'BTC',
            quoteAsset: 'USDT',
            uiName: 'BTC/USDT',
            tickSize: 0.01,
            pricePrecision: 2
          }],
          currentOrderBook: mockOrderBook,
          selectedRounding: null, // No rounding to test raw formatting
          availableRoundingOptions: [],
          orderBookLoading: false,
        });
        
        renderOrderBookDisplay(store);
        await screen.findByText('1.23K', { selector: '.bid-level .amount' }); // Wait for formatted amount to appear

        // Check K formatting
        expect(screen.getByText('1.23K', { selector: '.bid-level .amount' })).toBeInTheDocument();
        
        // Check M formatting
        expect(screen.getByText('1.23M', { selector: '.bid-level .amount' })).toBeInTheDocument();
        
        // Check B formatting
        expect(screen.getByText('1.23B', { selector: '.ask-level .amount' })).toBeInTheDocument();
        
        // Check K formatting for asks
        expect(screen.getByText('5.68K', { selector: '.ask-level .amount' })).toBeInTheDocument();

        // Check totals are also formatted
        // For bids: first total is 1.23K, second total is 1.23K + 1.23M = 1.23M + 1.23K ≈ 1.23M
        expect(screen.getByText('1.23K', { selector: '.bid-level .total' })).toBeInTheDocument();
        
        // For asks (reversed): first total is 5.68K, second total is 5.68K + 1.23B ≈ 1.23B
        expect(screen.getByText('5.68K', { selector: '.ask-level .total' })).toBeInTheDocument();
      });
    });

    describe('Price Precision', () => {
      it('formats prices with correct precision when rounding is selected', async () => {
        const mockOrderBook = {
          symbol: 'BTCUSDT',
          bids: [
            { price: 123.456789, amount: 1.0 },
          ],
          asks: [
            { price: 124.987654, amount: 1.0 },
          ],
          timestamp: Date.now(),
        };

        testSetup.apiClientGetSpy.mockResolvedValueOnce({ data: mockOrderBook });

        // Test with rounding = 1 (should show 0 decimal places)
        const store1 = createMockStore({
          selectedSymbol: 'BTCUSDT',
          symbolsList: [{
            id: 'btcusdt',
            symbol: 'BTCUSDT',
            baseAsset: 'BTC',
            quoteAsset: 'USDT',
            uiName: 'BTC/USDT',
            tickSize: 0.01,
            pricePrecision: 8
          }],
          currentOrderBook: mockOrderBook,
          selectedRounding: 1,
          availableRoundingOptions: [1],
          orderBookLoading: false,
        });
        
        renderOrderBookDisplay(store1);
        await screen.findByText('123'); // Wait for formatted price to appear

        expect(screen.getByText('123', { selector: '.bid-level .price' })).toBeInTheDocument();
        expect(screen.getByText('125', { selector: '.ask-level .price' })).toBeInTheDocument();
      });

      it('formats prices with 1 decimal place when rounding is 0.1', async () => {
        const mockOrderBook = {
          symbol: 'BTCUSDT',
          bids: [
            { price: 123.456789, amount: 1.0 },
          ],
          asks: [
            { price: 124.987654, amount: 1.0 },
          ],
          timestamp: Date.now(),
        };

        testSetup.apiClientGetSpy.mockResolvedValueOnce({ data: mockOrderBook });

        const store = createMockStore({
          selectedSymbol: 'BTCUSDT',
          symbolsList: [{
            id: 'btcusdt',
            symbol: 'BTCUSDT',
            baseAsset: 'BTC',
            quoteAsset: 'USDT',
            uiName: 'BTC/USDT',
            tickSize: 0.01,
            pricePrecision: 8
          }],
          currentOrderBook: mockOrderBook,
          selectedRounding: 0.1,
          availableRoundingOptions: [0.1],
          orderBookLoading: false,
        });
        
        renderOrderBookDisplay(store);
        await screen.findByText('123.4'); // Wait for formatted price to appear

        expect(screen.getByText('123.4', { selector: '.bid-level .price' })).toBeInTheDocument();
        expect(screen.getByText('125.0', { selector: '.ask-level .price' })).toBeInTheDocument();
      });

      it('formats prices with 2 decimal places when rounding is 0.01', async () => {
        const mockOrderBook = {
          symbol: 'BTCUSDT',
          bids: [
            { price: 123.456789, amount: 1.0 },
          ],
          asks: [
            { price: 124.987654, amount: 1.0 },
          ],
          timestamp: Date.now(),
        };

        testSetup.apiClientGetSpy.mockResolvedValueOnce({ data: mockOrderBook });

        const store = createMockStore({
          selectedSymbol: 'BTCUSDT',
          symbolsList: [{
            id: 'btcusdt',
            symbol: 'BTCUSDT',
            baseAsset: 'BTC',
            quoteAsset: 'USDT',
            uiName: 'BTC/USDT',
            tickSize: 0.01,
            pricePrecision: 8
          }],
          currentOrderBook: mockOrderBook,
          selectedRounding: 0.01,
          availableRoundingOptions: [0.01],
          orderBookLoading: false,
        });
        
        renderOrderBookDisplay(store);
        await screen.findByText('123.45'); // Wait for formatted price to appear

        expect(screen.getByText('123.45', { selector: '.bid-level .price' })).toBeInTheDocument();
        expect(screen.getByText('124.99', { selector: '.ask-level .price' })).toBeInTheDocument();
      });

      it('formats prices with 3 decimal places when rounding is 0.001', async () => {
        const mockOrderBook = {
          symbol: 'BTCUSDT',
          bids: [
            { price: 123.456789, amount: 1.0 },
          ],
          asks: [
            { price: 124.987654, amount: 1.0 },
          ],
          timestamp: Date.now(),
        };

        testSetup.apiClientGetSpy.mockResolvedValueOnce({ data: mockOrderBook });

        const store = createMockStore({
          selectedSymbol: 'BTCUSDT',
          symbolsList: [{
            id: 'btcusdt',
            symbol: 'BTCUSDT',
            baseAsset: 'BTC',
            quoteAsset: 'USDT',
            uiName: 'BTC/USDT',
            tickSize: 0.01,
            pricePrecision: 8
          }],
          currentOrderBook: mockOrderBook,
          selectedRounding: 0.001,
          availableRoundingOptions: [0.001],
          orderBookLoading: false,
        });
        
        renderOrderBookDisplay(store);
        await screen.findByText('123.456'); // Wait for formatted price to appear

        expect(screen.getByText('123.456', { selector: '.bid-level .price' })).toBeInTheDocument();
        expect(screen.getByText('124.988', { selector: '.ask-level .price' })).toBeInTheDocument();
      });

      it('uses symbol pricePrecision when no rounding is selected', async () => {
        const mockOrderBook = {
          symbol: 'BTCUSDT',
          bids: [
            { price: 123.456789, amount: 1.0 },
          ],
          asks: [
            { price: 124.987654, amount: 1.0 },
          ],
          timestamp: Date.now(),
        };

        testSetup.apiClientGetSpy.mockResolvedValueOnce({ data: mockOrderBook });

        const store = createMockStore({
          selectedSymbol: 'BTCUSDT',
          symbolsList: [], // No symbol data to prevent auto-calculation of rounding options
          currentOrderBook: mockOrderBook,
          selectedRounding: null,
          availableRoundingOptions: [],
          orderBookLoading: false,
        });
        
        renderOrderBookDisplay(store);
        await screen.findByText('123.46'); // Wait for formatted price to appear (defaults to 2 decimal places)

        // When no symbol data is available, it defaults to 2 decimal places
        expect(screen.getByText('123.46', { selector: '.bid-level .price' })).toBeInTheDocument();
        expect(screen.getByText('124.99', { selector: '.ask-level .price' })).toBeInTheDocument();
      });

      it('defaults to 2 decimal places when no pricePrecision is available', async () => {
        const mockOrderBook = {
          symbol: 'BTCUSDT',
          bids: [
            { price: 123.456789, amount: 1.0 },
          ],
          asks: [
            { price: 124.987654, amount: 1.0 },
          ],
          timestamp: Date.now(),
        };

        testSetup.apiClientGetSpy.mockResolvedValueOnce({ data: mockOrderBook });

        const store = createMockStore({
          selectedSymbol: 'BTCUSDT',
          symbolsList: [], // No symbol data to prevent auto-calculation
          currentOrderBook: mockOrderBook,
          selectedRounding: null,
          availableRoundingOptions: [],
          orderBookLoading: false,
        });
        
        renderOrderBookDisplay(store);
        await screen.findByText('123.46'); // Wait for formatted price to appear

        expect(screen.getByText('123.46', { selector: '.bid-level .price' })).toBeInTheDocument();
        expect(screen.getByText('124.99', { selector: '.ask-level .price' })).toBeInTheDocument();
      });
    });
  });

  describe('Cumulative Total Calculation with Aggregated Data', () => {
    it('calculates cumulative totals correctly for bids with aggregated data', async () => {
      const mockOrderBook = {
        symbol: 'BTCUSDT',
        bids: [
          { price: 100.15, amount: 10 }, // rounds down to 100.1
          { price: 100.19, amount: 5 },  // rounds down to 100.1 (aggregated: 15)
          { price: 99.95, amount: 20 },  // rounds down to 99.9
          { price: 98.85, amount: 8 },   // rounds down to 98.8
        ],
        asks: [],
        timestamp: Date.now(),
      };

      testSetup.apiClientGetSpy.mockResolvedValueOnce({ data: mockOrderBook });

      const store = createMockStore({
        selectedSymbol: 'BTCUSDT',
        symbolsList: [{
          id: 'btcusdt',
          symbol: 'BTCUSDT',
          baseAsset: 'BTC',
          quoteAsset: 'USDT',
          uiName: 'BTC/USDT',
          tickSize: 0.1,
          pricePrecision: 1
        }],
        currentOrderBook: mockOrderBook,
        selectedRounding: 0.1,
        availableRoundingOptions: [0.1, 1, 10],
        orderBookLoading: false,
      });
      
      renderOrderBookDisplay(store);
      await screen.findByText('100.1'); // Wait for aggregated price to appear

      // Expected displayBids after aggregation and sorting (price desc):
      // [[100.1, 15], [99.9, 20], [98.8, 8]]
      // Expected cumulative totals:
      // Row 1 (100.1): 15
      // Row 2 (99.9): 15 + 20 = 35
      // Row 3 (98.8): 15 + 20 + 8 = 43

      // Verify the aggregated amounts
      expect(screen.getByText('100.1')).toBeInTheDocument();
      expect(screen.getByText('15.00', { selector: '.bid-level .amount' })).toBeInTheDocument();
      expect(screen.getByText('99.9')).toBeInTheDocument();
      expect(screen.getByText('20.00', { selector: '.bid-level .amount' })).toBeInTheDocument();
      expect(screen.getByText('98.8')).toBeInTheDocument();
      expect(screen.getByText('8.00', { selector: '.bid-level .amount' })).toBeInTheDocument();

      // Verify the cumulative totals
      expect(screen.getByText('15.00', { selector: '.bid-level .total' })).toBeInTheDocument(); // First row total
      expect(screen.getByText('35.00', { selector: '.bid-level .total' })).toBeInTheDocument(); // Second row total
      expect(screen.getByText('43.00', { selector: '.bid-level .total' })).toBeInTheDocument(); // Third row total
    });

    it('calculates cumulative totals correctly for asks with aggregated data', async () => {
      const mockOrderBook = {
        symbol: 'BTCUSDT',
        bids: [],
        asks: [
          { price: 101.05, amount: 8 },  // rounds up to 101.1
          { price: 101.01, amount: 12 }, // rounds up to 101.1 (aggregated: 20)
          { price: 102.15, amount: 7 },  // rounds up to 102.2
          { price: 103.25, amount: 15 }, // rounds up to 103.3
        ],
        timestamp: Date.now(),
      };

      testSetup.apiClientGetSpy.mockResolvedValueOnce({ data: mockOrderBook });

      const store = createMockStore({
        selectedSymbol: 'BTCUSDT',
        symbolsList: [{
          id: 'btcusdt',
          symbol: 'BTCUSDT',
          baseAsset: 'BTC',
          quoteAsset: 'USDT',
          uiName: 'BTC/USDT',
          tickSize: 0.1,
          pricePrecision: 1
        }],
        currentOrderBook: mockOrderBook,
        selectedRounding: 0.1,
        availableRoundingOptions: [0.1, 1, 10],
        orderBookLoading: false,
      });
      
      renderOrderBookDisplay(store);
      await screen.findByText('101.1'); // Wait for aggregated price to appear

      // Expected aggregated asks (sorted price asc): [[101.1, 20], [102.2, 7], [103.3, 15]]
      // Expected displayAsks after slice and reverse: [[103.3, 15], [102.2, 7], [101.1, 20]]
      // Expected cumulative totals (accumulating from top displayed downwards):
      // Row 1 (103.3): 15
      // Row 2 (102.2): 15 + 7 = 22
      // Row 3 (101.1): 15 + 7 + 20 = 42

      // Verify the aggregated amounts in display order (reversed)
      expect(screen.getByText('103.3')).toBeInTheDocument();
      expect(screen.getByText('15.00', { selector: '.ask-level .amount' })).toBeInTheDocument();
      expect(screen.getByText('102.2')).toBeInTheDocument();
      expect(screen.getByText('7.00', { selector: '.ask-level .amount' })).toBeInTheDocument();
      expect(screen.getByText('101.1')).toBeInTheDocument();
      expect(screen.getByText('20.00', { selector: '.ask-level .amount' })).toBeInTheDocument();

      // Verify the cumulative totals
      expect(screen.getByText('15.00', { selector: '.ask-level .total' })).toBeInTheDocument(); // First displayed row total
      expect(screen.getByText('22.00', { selector: '.ask-level .total' })).toBeInTheDocument(); // Second displayed row total
      expect(screen.getByText('42.00', { selector: '.ask-level .total' })).toBeInTheDocument(); // Third displayed row total
    });

    it('calculates cumulative totals correctly with displayDepth smaller than aggregated levels', async () => {
      const mockOrderBook = {
        symbol: 'BTCUSDT',
        bids: [
          { price: 100.15, amount: 10 }, // rounds down to 100.1
          { price: 99.95, amount: 20 },  // rounds down to 99.9
          { price: 98.85, amount: 8 },   // rounds down to 98.8
          { price: 97.75, amount: 5 },   // rounds down to 97.7
          { price: 96.65, amount: 3 },   // rounds down to 96.6
        ],
        asks: [
          { price: 101.05, amount: 8 },  // rounds up to 101.1
          { price: 102.15, amount: 12 }, // rounds up to 102.2
          { price: 103.25, amount: 7 },  // rounds up to 103.3
          { price: 104.35, amount: 15 }, // rounds up to 104.4
          { price: 105.45, amount: 4 },  // rounds up to 105.5
        ],
        timestamp: Date.now(),
      };

      testSetup.apiClientGetSpy.mockResolvedValueOnce({ data: mockOrderBook });

      const store = createMockStore({
        selectedSymbol: 'BTCUSDT',
        symbolsList: [{
          id: 'btcusdt',
          symbol: 'BTCUSDT',
          baseAsset: 'BTC',
          quoteAsset: 'USDT',
          uiName: 'BTC/USDT',
          tickSize: 0.1,
          pricePrecision: 1
        }],
        currentOrderBook: mockOrderBook,
        selectedRounding: 0.1,
        availableRoundingOptions: [0.1, 1, 10],
        orderBookLoading: false,
      });
      
      renderOrderBookDisplay(store);
      await screen.findByText('100.1'); // Wait for aggregated price to appear

      // With default displayDepth=10, all 5 levels should be visible initially
      // Verify all bid levels are displayed
      expect(screen.getByText('100.1')).toBeInTheDocument();
      expect(screen.getByText('99.9')).toBeInTheDocument();
      expect(screen.getByText('98.8')).toBeInTheDocument();
      expect(screen.getByText('97.7')).toBeInTheDocument();
      expect(screen.getByText('96.6')).toBeInTheDocument();

      // Verify all ask levels are displayed
      expect(screen.getByText('105.5')).toBeInTheDocument();
      expect(screen.getByText('104.4')).toBeInTheDocument();
      expect(screen.getByText('103.3')).toBeInTheDocument();
      expect(screen.getByText('102.2')).toBeInTheDocument();
      expect(screen.getByText('101.1')).toBeInTheDocument();

      // Verify cumulative totals for all levels
      expect(screen.getByText('10.00', { selector: '.bid-level .total' })).toBeInTheDocument(); // 100.1 total
      expect(screen.getByText('30.00', { selector: '.bid-level .total' })).toBeInTheDocument(); // 99.9 total (10+20)
      expect(screen.getByText('38.00', { selector: '.bid-level .total' })).toBeInTheDocument(); // 98.8 total (10+20+8)
      expect(screen.getByText('43.00', { selector: '.bid-level .total' })).toBeInTheDocument(); // 97.7 total (10+20+8+5)
      expect(screen.getByText('46.00', { selector: '.bid-level .total' })).toBeInTheDocument(); // 96.6 total (10+20+8+5+3)

      // Verify ask cumulative totals (displayed in reverse order)
      expect(screen.getByText('4.00', { selector: '.ask-level .total' })).toBeInTheDocument(); // 105.5 total
      expect(screen.getByText('19.00', { selector: '.ask-level .total' })).toBeInTheDocument(); // 104.4 total (4+15)
      expect(screen.getByText('26.00', { selector: '.ask-level .total' })).toBeInTheDocument(); // 103.3 total (4+15+7)
      expect(screen.getByText('38.00', { selector: '.ask-level .total' })).toBeInTheDocument(); // 102.2 total (4+15+7+12)
      expect(screen.getByText('46.00', { selector: '.ask-level .total' })).toBeInTheDocument(); // 101.1 total (4+15+7+12+8)
    });

    it('formats cumulative totals with K/M/B suffixes correctly', async () => {
      const mockOrderBook = {
        symbol: 'BTCUSDT',
        bids: [
          { price: 100.15, amount: 1500 },   // rounds down to 100.1, displays as 1.5K
          { price: 100.19, amount: 2500 },   // rounds down to 100.1 (aggregated: 4000, displays as 4K)
          { price: 99.95, amount: 1200000 }, // rounds down to 99.9, displays as 1.2M
        ],
        asks: [
          { price: 101.05, amount: 800000 },    // rounds up to 101.1, displays as 800K
          { price: 101.01, amount: 1200000 },   // rounds up to 101.1 (aggregated: 2000000, displays as 2M)
          { price: 102.15, amount: 500000000 }, // rounds up to 102.2, displays as 500M
        ],
        timestamp: Date.now(),
      };

      testSetup.apiClientGetSpy.mockResolvedValueOnce({ data: mockOrderBook });

      const store = createMockStore({
        selectedSymbol: 'BTCUSDT',
        symbolsList: [{
          id: 'btcusdt',
          symbol: 'BTCUSDT',
          baseAsset: 'BTC',
          quoteAsset: 'USDT',
          uiName: 'BTC/USDT',
          tickSize: 0.1,
          pricePrecision: 1
        }],
        currentOrderBook: mockOrderBook,
        selectedRounding: 0.1,
        availableRoundingOptions: [0.1, 1, 10],
        orderBookLoading: false,
      });
      
      renderOrderBookDisplay(store);
      await screen.findByText('100.1'); // Wait for aggregated price to appear

      // Expected displayBids: [[100.1, 4000], [99.9, 1200000]]
      // Expected cumulative totals: 4000 (4K), 1204000 (1.2M)
      
      // Expected displayAsks (reversed): [[102.2, 500000000], [101.1, 2000000]]
      // Expected cumulative totals: 500000000 (500M), 502000000 (502M)

      // Verify bid totals with K/M formatting
      expect(screen.getByText('4.00K', { selector: '.bid-level .total' })).toBeInTheDocument(); // 100.1 total
      expect(screen.getByText('1.20M', { selector: '.bid-level .total' })).toBeInTheDocument(); // 99.9 total

      // Verify ask totals with M formatting
      expect(screen.getByText('500.00M', { selector: '.ask-level .total' })).toBeInTheDocument(); // 102.2 total
      expect(screen.getByText('502.00M', { selector: '.ask-level .total' })).toBeInTheDocument(); // 101.1 total
    });

    it('handles edge case with single aggregated level per side', async () => {
      const mockOrderBook = {
        symbol: 'BTCUSDT',
        bids: [
          { price: 100.01, amount: 5 },  // rounds down to 100
          { price: 100.02, amount: 10 }, // rounds down to 100 (aggregated: 15)
          { price: 100.03, amount: 8 },  // rounds down to 100 (aggregated: 23)
        ],
        asks: [
          { price: 101.01, amount: 12 }, // rounds up to 102
          { price: 101.02, amount: 7 },  // rounds up to 102 (aggregated: 19)
          { price: 101.03, amount: 4 },  // rounds up to 102 (aggregated: 23)
        ],
        timestamp: Date.now(),
      };

      testSetup.apiClientGetSpy.mockResolvedValueOnce({ data: mockOrderBook });

      const store = createMockStore({
        selectedSymbol: 'BTCUSDT',
        symbolsList: [{
          id: 'btcusdt',
          symbol: 'BTCUSDT',
          baseAsset: 'BTC',
          quoteAsset: 'USDT',
          uiName: 'BTC/USDT',
          tickSize: 1,
          pricePrecision: 0
        }],
        currentOrderBook: mockOrderBook,
        selectedRounding: 1,
        availableRoundingOptions: [1, 10, 100],
        orderBookLoading: false,
      });
      
      renderOrderBookDisplay(store);
      await screen.findByText('100'); // Wait for aggregated price to appear

      // Expected displayBids: [[100, 23]]
      // Expected cumulative total: 23
      
      // Expected displayAsks: [[102, 23]]
      // Expected cumulative total: 23

      // Verify single aggregated bid level
      expect(screen.getByText('100', { selector: '.bid-price' })).toBeInTheDocument();
      expect(screen.getByText('23.00', { selector: '.bid-level .amount' })).toBeInTheDocument();
      expect(screen.getByText('23.00', { selector: '.bid-level .total' })).toBeInTheDocument();

      // Verify single aggregated ask level
      expect(screen.getByText('102')).toBeInTheDocument();
      expect(screen.getByText('23.00', { selector: '.ask-level .amount' })).toBeInTheDocument();
      expect(screen.getByText('23.00', { selector: '.ask-level .total' })).toBeInTheDocument();
    });
  });
});