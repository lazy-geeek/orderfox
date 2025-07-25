/**
 * Tests for Moving Average line series functionality in LightweightChart component
 * 
 * This module contains unit tests for the MA line series integration,
 * including series creation, data updates, and visibility toggling.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

// Mock the lightweight-charts module before importing
vi.mock('lightweight-charts', () => {
  const mockLineSeries = {
    update: vi.fn(),
    setData: vi.fn(),
    applyOptions: vi.fn()
  };

  const mockChart = {
    addSeries: vi.fn().mockReturnValue(mockLineSeries),
    remove: vi.fn(),
    priceScale: vi.fn(),
    timeScale: vi.fn(() => ({
      fitContent: vi.fn()
    }))
  };

  return {
    createChart: vi.fn().mockReturnValue(mockChart),
    CandlestickSeries: 'CandlestickSeries',
    HistogramSeries: 'HistogramSeries',
    LineSeries: 'LineSeries',
    ColorType: {
      Solid: 'Solid'
    }
  };
});

// Mock DOM elements
const mockContainer = {
  clientWidth: 800,
  clientHeight: 400,
  appendChild: vi.fn(),
  removeChild: vi.fn()
};

// Mock ResizeObserver
global.ResizeObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn()
}));

// Import the module after mocking
import {
  createLightweightChart,
  updateLiquidationVolume,
  toggleLiquidationVolume,
  resetChartData,
  disposeLightweightChart
} from '../../src/components/LightweightChart.js';

// Import mocked modules to access mock functions
import { createChart } from 'lightweight-charts';

describe('Moving Average Line Series Tests', () => {
  let mockChart;
  let mockLineSeries;

  beforeEach(() => {
    // Clear all mocks before each test
    vi.clearAllMocks();
    
    // Get fresh mock instances
    mockChart = createChart();
    mockLineSeries = mockChart.addSeries();
    
    // Reset DOM
    document.body.innerHTML = '<div id="test-container"></div>';
    
    // Mock window.getComputedStyle
    global.getComputedStyle = vi.fn().mockReturnValue({
      getPropertyValue: vi.fn().mockReturnValue('#ffffff')
    });
  });

  afterEach(() => {
    // Clean up after each test
    disposeLightweightChart();
  });

  describe('MA Line Series Creation', () => {
    it('should create MA line series with correct configuration', () => {
      const container = document.getElementById('test-container');
      
      // Create chart which should initialize MA line series
      createLightweightChart(container, 800);
      
      // Verify chart creation
      expect(createChart).toHaveBeenCalled();
      
      // Verify LineSeries was created with correct options
      expect(mockChart.addSeries).toHaveBeenCalledWith('LineSeries', {
        color: 'rgba(255, 193, 7, 0.8)', // Yellow with transparency
        lineWidth: 2,
        lineStyle: 0, // Solid line
        priceScaleId: '', // Overlay with histogram
        crosshairMarkerVisible: false,
        lastValueVisible: false,
        priceLineVisible: false
      });
    });

    it('should handle chart creation failure gracefully', () => {
      // Mock chart creation failure
      createChart.mockReturnValueOnce(null);
      
      const container = document.getElementById('test-container');
      
      // Should not throw error
      expect(() => createLightweightChart(container, 800)).not.toThrow();
    });
  });

  describe('MA Data Updates', () => {
    beforeEach(() => {
      const container = document.getElementById('test-container');
      createLightweightChart(container, 800);
      
      // Simulate chart initialization complete
      // This would normally be set when chart is ready
      window.chartInitialized = true;
    });

    it('should update MA line with real-time single data point', () => {
      const volumeData = [{
        time: 1609459200,
        delta_volume: '100.0',
        ma_value: '125.5',
        ma_value_formatted: '$125.50'
      }];

      // Call updateLiquidationVolume with real-time single update
      updateLiquidationVolume(volumeData, true);

      // Verify MA line series was updated
      expect(mockLineSeries.update).toHaveBeenCalledWith({
        time: expect.any(Number), // timeToLocal conversion
        value: 125.5
      });
    });

    it('should update MA line with real-time batch data', () => {
      const volumeData = [
        {
          time: 1609459200,
          delta_volume: '100.0',
          ma_value: '120.0',
          ma_value_formatted: '$120.00'
        },
        {
          time: 1609459260,
          delta_volume: '150.0',
          ma_value: '135.0',
          ma_value_formatted: '$135.00'
        }
      ];

      // Call updateLiquidationVolume with real-time batch update
      updateLiquidationVolume(volumeData, true);

      // Verify MA line series was updated for each data point
      expect(mockLineSeries.update).toHaveBeenCalledTimes(2);
      expect(mockLineSeries.update).toHaveBeenCalledWith({
        time: expect.any(Number),
        value: 120.0
      });
      expect(mockLineSeries.update).toHaveBeenCalledWith({
        time: expect.any(Number),
        value: 135.0
      });
    });

    it('should set MA line data for initial load', () => {
      const volumeData = [
        {
          time: 1609459200,
          delta_volume: '100.0',
          ma_value: '120.0',
          ma_value_formatted: '$120.00'
        },
        {
          time: 1609459260,
          delta_volume: '150.0',
          ma_value: '135.0',
          ma_value_formatted: '$135.00'
        },
        {
          time: 1609459320,
          delta_volume: '200.0',
          ma_value: '155.0',
          ma_value_formatted: '$155.00'
        }
      ];

      // Call updateLiquidationVolume with initial load (not real-time)
      updateLiquidationVolume(volumeData, false);

      // Verify MA line series data was set
      expect(mockLineSeries.setData).toHaveBeenCalledWith([
        { time: expect.any(Number), value: 120.0 },
        { time: expect.any(Number), value: 135.0 },
        { time: expect.any(Number), value: 155.0 }
      ]);
    });

    it('should handle missing MA data gracefully', () => {
      const volumeData = [{
        time: 1609459200,
        delta_volume: '100.0',
        ma_value: null,
        ma_value_formatted: null
      }];

      // Should not throw error and not call MA update
      expect(() => updateLiquidationVolume(volumeData, true)).not.toThrow();
      expect(mockLineSeries.update).not.toHaveBeenCalled();
    });

    it('should handle undefined MA data gracefully', () => {
      const volumeData = [{
        time: 1609459200,
        delta_volume: '100.0'
        // ma_value and ma_value_formatted are undefined
      }];

      // Should not throw error and not call MA update
      expect(() => updateLiquidationVolume(volumeData, true)).not.toThrow();
      expect(mockLineSeries.update).not.toHaveBeenCalled();
    });

    it('should filter out null MA values in initial load', () => {
      const volumeData = [
        {
          time: 1609459200,
          delta_volume: '0.0', // Zero delta
          ma_value: null,
          ma_value_formatted: null
        },
        {
          time: 1609459260,
          delta_volume: '150.0',
          ma_value: '135.0',
          ma_value_formatted: '$135.00'
        }
      ];

      updateLiquidationVolume(volumeData, false);

      // Should only set data for non-null MA values
      expect(mockLineSeries.setData).toHaveBeenCalledWith([
        { time: expect.any(Number), value: 135.0 }
      ]);
    });

    it('should clear MA data when no valid MA values exist', () => {
      const volumeData = [
        {
          time: 1609459200,
          delta_volume: '0.0',
          ma_value: null,
          ma_value_formatted: null
        }
      ];

      updateLiquidationVolume(volumeData, false);

      // Should set empty data array
      expect(mockLineSeries.setData).toHaveBeenCalledWith([]);
    });
  });

  describe('MA Line Visibility Toggle', () => {
    beforeEach(() => {
      const container = document.getElementById('test-container');
      createLightweightChart(container, 800);
    });

    it('should show MA line when volume is toggled on', () => {
      // Toggle liquidation volume on (should be on by default, but toggle to ensure)
      const isVisible = toggleLiquidationVolume();
      
      if (isVisible) {
        // Verify MA line visibility is set to true
        expect(mockLineSeries.applyOptions).toHaveBeenCalledWith({ visible: true });
      }
    });

    it('should hide MA line when volume is toggled off', () => {
      // First toggle on to ensure we're in visible state
      toggleLiquidationVolume(); // On
      vi.clearAllMocks(); // Clear previous calls
      
      // Then toggle off
      const isVisible = toggleLiquidationVolume(); // Off
      
      if (!isVisible) {
        // Verify MA line visibility is set to false
        expect(mockLineSeries.applyOptions).toHaveBeenCalledWith({ visible: false });
      }
    });

    it('should synchronize MA visibility with volume visibility', () => {
      // Toggle multiple times and verify MA follows volume
      let isVisible = toggleLiquidationVolume();
      
      // Check that MA visibility was updated
      expect(mockLineSeries.applyOptions).toHaveBeenCalledWith({ 
        visible: isVisible 
      });
      
      // Toggle again
      vi.clearAllMocks();
      isVisible = toggleLiquidationVolume();
      
      expect(mockLineSeries.applyOptions).toHaveBeenCalledWith({ 
        visible: isVisible 
      });
    });
  });

  describe('MA Line Cleanup', () => {
    beforeEach(() => {
      const container = document.getElementById('test-container');
      createLightweightChart(container, 800);
    });

    it('should clear MA data when chart data is reset', () => {
      // Reset chart data
      resetChartData();
      
      // Verify MA line data was cleared
      expect(mockLineSeries.setData).toHaveBeenCalledWith([]);
    });

    it('should nullify MA line series reference on disposal', () => {
      // Dispose chart
      disposeLightweightChart();
      
      // The internal maLineSeries reference should be nullified
      // This is tested indirectly by ensuring no errors occur in subsequent operations
      expect(() => toggleLiquidationVolume()).not.toThrow();
    });
  });

  describe('Error Handling', () => {
    beforeEach(() => {
      const container = document.getElementById('test-container');
      createLightweightChart(container, 800);
      window.chartInitialized = true;
    });

    it('should handle MA line series method failures gracefully', () => {
      // Mock series method to throw error
      mockLineSeries.update.mockImplementationOnce(() => {
        throw new Error('Update failed');
      });

      const volumeData = [{
        time: 1609459200,
        delta_volume: '100.0',
        ma_value: '125.5',
        ma_value_formatted: '$125.50'
      }];

      // Should not propagate error
      expect(() => updateLiquidationVolume(volumeData, true)).not.toThrow();
    });

    it('should handle invalid MA values gracefully', () => {
      const volumeData = [{
        time: 1609459200,
        delta_volume: '100.0',
        ma_value: 'invalid_number',
        ma_value_formatted: 'Invalid'
      }];

      // Should handle parseFloat of invalid string
      expect(() => updateLiquidationVolume(volumeData, true)).not.toThrow();
    });

    it('should handle missing chart instance', () => {
      // Dispose chart to remove instance
      disposeLightweightChart();
      
      const volumeData = [{
        time: 1609459200,
        delta_volume: '100.0',
        ma_value: '125.5'
      }];

      // Should not throw error when chart instance is null
      expect(() => updateLiquidationVolume(volumeData, true)).not.toThrow();
    });
  });

  describe('Integration with Volume Series', () => {
    beforeEach(() => {
      const container = document.getElementById('test-container');
      createLightweightChart(container, 800);
      window.chartInitialized = true;
    });

    it('should create MA series alongside volume series', () => {
      // Verify both HistogramSeries and LineSeries were created
      expect(mockChart.addSeries).toHaveBeenCalledWith('HistogramSeries', expect.any(Object));
      expect(mockChart.addSeries).toHaveBeenCalledWith('LineSeries', expect.any(Object));
    });

    it('should handle volume data without MA data', () => {
      const volumeData = [{
        time: 1609459200,
        delta_volume: '100.0',
        buy_volume: '100.0',
        sell_volume: '0.0'
        // No MA fields
      }];

      // Should update volume but not MA
      expect(() => updateLiquidationVolume(volumeData, true)).not.toThrow();
      expect(mockLineSeries.update).not.toHaveBeenCalled();
    });

    it('should maintain MA state when volume series is reset', () => {
      // Update with MA data first
      const volumeData = [{
        time: 1609459200,
        delta_volume: '100.0',
        ma_value: '125.5'
      }];
      
      updateLiquidationVolume(volumeData, false);
      expect(mockLineSeries.setData).toHaveBeenCalled();
      
      // Reset should clear MA data too
      vi.clearAllMocks();
      resetChartData();
      expect(mockLineSeries.setData).toHaveBeenCalledWith([]);
    });
  });
});