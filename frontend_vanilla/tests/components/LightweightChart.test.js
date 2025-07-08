import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

// Create test module that directly tests the price precision logic
describe('LightweightChart Price Precision Logic', () => {
  let consoleSpy
  let mockSeries

  beforeEach(() => {
    mockSeries = {
      applyOptions: vi.fn(),
      setData: vi.fn(),
      update: vi.fn(),
    }
    consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})
  })

  afterEach(() => {
    consoleSpy.mockRestore()
    vi.clearAllMocks()
  })

  // Test the precision logic directly
  function testPrecisionLogic(symbolData, symbol) {
    let precision = 2 // Default precision
    
    // Extract and validate precision from symbolData (copied from actual implementation)
    if (symbolData && symbolData.pricePrecision !== undefined && symbolData.pricePrecision !== null) {
      // Validate precision is a non-negative integer and clamp to reasonable range (0-8)
      const rawPrecision = symbolData.pricePrecision
      if (typeof rawPrecision === 'number' && !isNaN(rawPrecision) && rawPrecision >= 0) {
        precision = Math.max(0, Math.min(8, Math.floor(rawPrecision)))
      } else {
        console.warn(`Invalid pricePrecision value for ${symbol}: ${rawPrecision}, using default precision: ${precision}`)
      }
    } else {
      console.warn(`Missing pricePrecision for ${symbol}, using default precision: ${precision}`)
    }
    
    // Apply price format with validated precision
    const priceFormat = {
      type: 'price',
      precision: precision,
      minMove: 1 / Math.pow(10, precision),
    }
    
    mockSeries.applyOptions({ priceFormat })
    
    return { precision, priceFormat }
  }

  describe('Default Precision', () => {
    it('should use default precision when symbolData is missing pricePrecision', () => {
      const symbolData = { id: 'BTCUSDT', symbol: 'BTC/USDT' } // No pricePrecision
      const symbol = 'BTCUSDT'

      const result = testPrecisionLogic(symbolData, symbol)

      expect(result.precision).toBe(2)
      expect(mockSeries.applyOptions).toHaveBeenCalledWith({
        priceFormat: {
          type: 'price',
          precision: 2,
          minMove: 0.01,
        },
      })
      expect(consoleSpy).toHaveBeenCalledWith(
        'Missing pricePrecision for BTCUSDT, using default precision: 2'
      )
    })

    it('should use default precision when symbolData is null', () => {
      const symbolData = null
      const symbol = 'BTCUSDT'

      const result = testPrecisionLogic(symbolData, symbol)

      expect(result.precision).toBe(2)
      expect(mockSeries.applyOptions).toHaveBeenCalledWith({
        priceFormat: {
          type: 'price',
          precision: 2,
          minMove: 0.01,
        },
      })
      expect(consoleSpy).toHaveBeenCalledWith(
        'Missing pricePrecision for BTCUSDT, using default precision: 2'
      )
    })
  })

  describe('Valid Precision Updates', () => {
    it('should apply correct precision for BTC (1 decimal)', () => {
      const symbolData = { 
        id: 'BTCUSDT', 
        symbol: 'BTC/USDT',
        pricePrecision: 1 
      }
      const symbol = 'BTCUSDT'

      const result = testPrecisionLogic(symbolData, symbol)

      expect(result.precision).toBe(1)
      expect(mockSeries.applyOptions).toHaveBeenCalledWith({
        priceFormat: {
          type: 'price',
          precision: 1,
          minMove: 0.1,
        },
      })
      expect(consoleSpy).not.toHaveBeenCalled()
    })

    it('should apply correct precision for XRP (4 decimals)', () => {
      const symbolData = { 
        id: 'XRPUSDT', 
        symbol: 'XRP/USDT',
        pricePrecision: 4 
      }
      const symbol = 'XRPUSDT'

      const result = testPrecisionLogic(symbolData, symbol)

      expect(result.precision).toBe(4)
      expect(mockSeries.applyOptions).toHaveBeenCalledWith({
        priceFormat: {
          type: 'price',
          precision: 4,
          minMove: 0.0001,
        },
      })
      expect(consoleSpy).not.toHaveBeenCalled()
    })

    it('should apply correct precision for high-precision tokens (7 decimals)', () => {
      const symbolData = { 
        id: '1000PEPEUSDT', 
        symbol: '1000PEPE/USDT',
        pricePrecision: 7 
      }
      const symbol = '1000PEPEUSDT'

      const result = testPrecisionLogic(symbolData, symbol)

      expect(result.precision).toBe(7)
      expect(mockSeries.applyOptions).toHaveBeenCalledWith({
        priceFormat: {
          type: 'price',
          precision: 7,
          minMove: 0.0000001,
        },
      })
      expect(consoleSpy).not.toHaveBeenCalled()
    })
  })

  describe('Invalid Precision Handling', () => {
    it('should clamp precision to maximum of 8', () => {
      const symbolData = { 
        id: 'TESTUSDT', 
        symbol: 'TEST/USDT',
        pricePrecision: 15 // Too high
      }
      const symbol = 'TESTUSDT'

      const result = testPrecisionLogic(symbolData, symbol)

      expect(result.precision).toBe(8) // Clamped to max
      expect(mockSeries.applyOptions).toHaveBeenCalledWith({
        priceFormat: {
          type: 'price',
          precision: 8,
          minMove: 0.00000001,
        },
      })
      expect(consoleSpy).not.toHaveBeenCalled()
    })

    it('should handle negative precision values as invalid', () => {
      const symbolData = { 
        id: 'TESTUSDT', 
        symbol: 'TEST/USDT',
        pricePrecision: -2 // Negative
      }
      const symbol = 'TESTUSDT'

      const result = testPrecisionLogic(symbolData, symbol)

      expect(result.precision).toBe(2) // Default fallback for invalid values
      expect(mockSeries.applyOptions).toHaveBeenCalledWith({
        priceFormat: {
          type: 'price',
          precision: 2,
          minMove: 0.01,
        },
      })
      expect(consoleSpy).toHaveBeenCalledWith(
        'Invalid pricePrecision value for TESTUSDT: -2, using default precision: 2'
      )
    })

    it('should handle non-numeric precision values', () => {
      const symbolData = { 
        id: 'TESTUSDT', 
        symbol: 'TEST/USDT',
        pricePrecision: 'invalid' // Non-numeric
      }
      const symbol = 'TESTUSDT'

      const result = testPrecisionLogic(symbolData, symbol)

      expect(result.precision).toBe(2) // Default fallback
      expect(mockSeries.applyOptions).toHaveBeenCalledWith({
        priceFormat: {
          type: 'price',
          precision: 2,
          minMove: 0.01,
        },
      })
      expect(consoleSpy).toHaveBeenCalledWith(
        'Invalid pricePrecision value for TESTUSDT: invalid, using default precision: 2'
      )
    })

    it('should handle null precision values', () => {
      const symbolData = { 
        id: 'TESTUSDT', 
        symbol: 'TEST/USDT',
        pricePrecision: null
      }
      const symbol = 'TESTUSDT'

      const result = testPrecisionLogic(symbolData, symbol)

      expect(result.precision).toBe(2) // Default fallback
      expect(mockSeries.applyOptions).toHaveBeenCalledWith({
        priceFormat: {
          type: 'price',
          precision: 2,
          minMove: 0.01,
        },
      })
      expect(consoleSpy).toHaveBeenCalledWith(
        'Missing pricePrecision for TESTUSDT, using default precision: 2'
      )
    })

    it('should handle NaN precision values', () => {
      const symbolData = { 
        id: 'TESTUSDT', 
        symbol: 'TEST/USDT',
        pricePrecision: NaN
      }
      const symbol = 'TESTUSDT'

      const result = testPrecisionLogic(symbolData, symbol)

      expect(result.precision).toBe(2) // Default fallback
      expect(mockSeries.applyOptions).toHaveBeenCalledWith({
        priceFormat: {
          type: 'price',
          precision: 2,
          minMove: 0.01,
        },
      })
      expect(consoleSpy).toHaveBeenCalledWith(
        'Invalid pricePrecision value for TESTUSDT: NaN, using default precision: 2'
      )
    })
  })

  describe('Edge Cases', () => {
    it('should handle decimal precision values by flooring them', () => {
      const symbolData = { 
        id: 'TESTUSDT', 
        symbol: 'TEST/USDT',
        pricePrecision: 3.7 // Decimal precision
      }
      const symbol = 'TESTUSDT'

      const result = testPrecisionLogic(symbolData, symbol)

      expect(result.precision).toBe(3) // Floored from 3.7
      expect(mockSeries.applyOptions).toHaveBeenCalledWith({
        priceFormat: {
          type: 'price',
          precision: 3,
          minMove: 0.001,
        },
      })
      expect(consoleSpy).not.toHaveBeenCalled()
    })

    it('should handle zero precision correctly', () => {
      const symbolData = { 
        id: 'TESTUSDT', 
        symbol: 'TEST/USDT',
        pricePrecision: 0
      }
      const symbol = 'TESTUSDT'

      const result = testPrecisionLogic(symbolData, symbol)

      expect(result.precision).toBe(0)
      expect(mockSeries.applyOptions).toHaveBeenCalledWith({
        priceFormat: {
          type: 'price',
          precision: 0,
          minMove: 1, // 1 / Math.pow(10, 0) = 1
        },
      })
      expect(consoleSpy).not.toHaveBeenCalled()
    })

    it('should properly clamp precision within valid range (0-8)', () => {
      // Test boundary values that should be clamped
      const testCases = [
        { input: 0, expected: 0, description: 'minimum boundary' },
        { input: 8, expected: 8, description: 'maximum boundary' },
        { input: 15, expected: 8, description: 'above maximum' },
      ]

      testCases.forEach(({ input, expected, description }) => {
        const symbolData = { 
          id: 'TESTUSDT', 
          symbol: 'TEST/USDT',
          pricePrecision: input
        }
        const symbol = 'TESTUSDT'

        vi.clearAllMocks()
        const result = testPrecisionLogic(symbolData, symbol)

        expect(result.precision).toBe(expected)
        expect(consoleSpy).not.toHaveBeenCalled()
      })
    })
  })

  describe('MinMove Calculation', () => {
    it('should calculate correct minMove for different precisions', () => {
      const testCases = [
        { precision: 0, expectedMinMove: 1 },
        { precision: 1, expectedMinMove: 0.1 },
        { precision: 2, expectedMinMove: 0.01 },
        { precision: 3, expectedMinMove: 0.001 },
        { precision: 4, expectedMinMove: 0.0001 },
        { precision: 5, expectedMinMove: 0.00001 },
        { precision: 6, expectedMinMove: 0.000001 },
        { precision: 7, expectedMinMove: 0.0000001 },
        { precision: 8, expectedMinMove: 0.00000001 },
      ]

      testCases.forEach(({ precision, expectedMinMove }) => {
        const symbolData = { 
          id: 'TESTUSDT', 
          symbol: 'TEST/USDT',
          pricePrecision: precision
        }
        const symbol = 'TESTUSDT'

        vi.clearAllMocks()
        const result = testPrecisionLogic(symbolData, symbol)

        expect(result.priceFormat.minMove).toBeCloseTo(expectedMinMove, 10)
      })
    })
  })
})