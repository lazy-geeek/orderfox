/**
 * Unit tests for liquidation volume update logic in LightweightChart.
 * Tests update() vs setData() logic and volume data accumulation.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { JSDOM } from 'jsdom';

// Create a test-specific module that exports the function we want to test
// This allows us to test the function in isolation with controlled state
const createTestableUpdateFunction = () => {
  // Module state
  let volumeSeries = null;
  let volumeSeriesVisible = true;
  let chartInitialized = false;
  let currentVolumeData = [];
  let pendingVolumeData = null;
  
  // Mock console for testing
  
  // The actual function implementation (copied from LightweightChart.js)
  function timeToLocal(time) {
    return time; // Identity function for testing
  }
  
  function updateLiquidationVolume(volumeData, isRealTimeUpdate = false) {
    console.log('updateLiquidationVolume called, volumeSeries:', !!volumeSeries, 'visible:', volumeSeriesVisible, 'isRealTimeUpdate:', isRealTimeUpdate);
    if (!volumeSeries || !volumeSeriesVisible) {
      console.warn('Volume series not ready or not visible');
      return;
    }
    
    // If chart hasn't been initialized yet, buffer the volume data
    if (!chartInitialized) {
      pendingVolumeData = volumeData;
      return;
    }
    
    // Debug: Log sample of volume data
    console.log('Updating liquidation volume with', volumeData.length, 'data points', 'isRealTimeUpdate:', isRealTimeUpdate);
    if (volumeData.length > 0) {
      console.log('Sample data:', volumeData[0], '...', volumeData[volumeData.length - 1]);
    }
    
    if (isRealTimeUpdate && volumeData.length === 1) {
      // Real-time update - use update() method to preserve existing data
      const item = volumeData[0];
      const deltaVolume = parseFloat(item.delta_volume || 0);
      
      if (deltaVolume !== 0) {
        const color = deltaVolume > 0 ? '#0ECB81' : '#F6465D';
        const histogramBar = {
          time: timeToLocal(item.time),
          value: Math.abs(deltaVolume),
          color: color,
        };
        
        try {
          // CRITICAL: Use update() for real-time updates to preserve historical data
          volumeSeries.update(histogramBar);
          console.log('Updated liquidation volume bar:', histogramBar);
          
          // Update currentVolumeData for tooltips
          // Find and update existing entry or add new one
          const existingIndex = currentVolumeData.findIndex(d => d.time === item.time);
          if (existingIndex >= 0) {
            currentVolumeData[existingIndex] = item;
          } else {
            // Insert in correct position to maintain time order
            currentVolumeData.push(item);
            currentVolumeData.sort((a, b) => a.time - b.time);
          }
        } catch (error) {
          console.error('Error updating liquidation volume:', error);
          // Fall back to setData if update fails
          updateLiquidationVolume(volumeData, false);
        }
      }
    } else if (isRealTimeUpdate && volumeData.length > 1) {
      // Real-time batch update - use update() for each item
      console.log('Processing real-time batch update with', volumeData.length, 'items');
      
      volumeData.forEach(item => {
        const deltaVolume = parseFloat(item.delta_volume || 0);
        
        if (deltaVolume !== 0) {
          const color = deltaVolume > 0 ? '#0ECB81' : '#F6465D';
          const histogramBar = {
            time: timeToLocal(item.time),
            value: Math.abs(deltaVolume),
            color: color,
          };
          
          try {
            volumeSeries.update(histogramBar);
            
            // Update currentVolumeData for tooltips
            const existingIndex = currentVolumeData.findIndex(d => d.time === item.time);
            if (existingIndex >= 0) {
              currentVolumeData[existingIndex] = item;
            } else {
              currentVolumeData.push(item);
            }
          } catch (error) {
            console.error('Error updating liquidation volume bar:', error, histogramBar);
          }
        }
      });
      
      // Sort after batch update
      currentVolumeData.sort((a, b) => a.time - b.time);
    } else {
      // Initial load - use setData() to establish the baseline
      console.log('Initial volume data load - using setData()');
      
      // Store volume data for tooltips
      currentVolumeData = volumeData;
      
      // Process volume data into histogram format using delta
      const histogramData = volumeData
        .filter(item => {
          // Filter out items with zero delta (no bars to show)
          const deltaVolume = parseFloat(item.delta_volume || 0);
          return deltaVolume !== 0;
        })
        .map(item => {
          // Use delta volume from backend
          const deltaVolume = parseFloat(item.delta_volume || 0);
          
          // Green if delta > 0 (more shorts liquidated), red if delta < 0 (more longs liquidated)
          const color = deltaVolume > 0 ? '#0ECB81' : '#F6465D';
          
          return {
            time: timeToLocal(item.time), // Convert UTC to local time to match candles
            value: Math.abs(deltaVolume), // Use absolute value for bar height
            color: color,
          };
        });
      
      console.log('Filtered histogram data points with non-zero values:', histogramData.length);
      
      // Update series data
      if (!volumeSeries) {
        console.warn('Volume series not initialized - cannot update liquidation volume');
        return;
      }
      // CRITICAL: Only use setData() for initial load, not for updates
      volumeSeries.setData(histogramData);
    }
    
    // Don't call fitContent here as it affects the main chart zoom
  }
  
  // Return the function and state setters for testing
  return {
    updateLiquidationVolume,
    setVolumeSeries: (series) => { volumeSeries = series; },
    setVolumeSeriesVisible: (visible) => { volumeSeriesVisible = visible; },
    setChartInitialized: (initialized) => { chartInitialized = initialized; },
    getCurrentVolumeData: () => currentVolumeData,
    setCurrentVolumeData: (data) => { currentVolumeData = data; },
    getPendingVolumeData: () => pendingVolumeData,
  };
};

// Mock histogram series
const mockHistogramSeries = {
  setData: vi.fn(),
  update: vi.fn(),
  applyOptions: vi.fn()
};

describe('Liquidation Volume Updates', () => {
  let testModule;
  let updateLiquidationVolume;
  let dom;
  let window;
  let document;

  beforeEach(() => {
    // Set up DOM environment
    dom = new JSDOM('<!DOCTYPE html><html><body></body></html>');
    window = dom.window;
    document = window.document;
    
    // Make globals available
    global.window = window;
    global.document = document;
    
    // Clear all mocks
    vi.clearAllMocks();
    
    // Create fresh test module
    testModule = createTestableUpdateFunction();
    updateLiquidationVolume = testModule.updateLiquidationVolume;
    
    // Set up default state
    testModule.setVolumeSeries(mockHistogramSeries);
    testModule.setVolumeSeriesVisible(true);
    testModule.setChartInitialized(true);
    testModule.setCurrentVolumeData([]);
  });

  afterEach(() => {
    delete global.window;
    delete global.document;
  });

  describe('update() vs setData() logic', () => {
    it('should use setData() for initial load (isRealTimeUpdate = false)', () => {
      const volumeData = [
        { time: 1000, delta_volume: '100', buy_volume: '60', sell_volume: '40' },
        { time: 2000, delta_volume: '-50', buy_volume: '25', sell_volume: '75' }
      ];

      updateLiquidationVolume(volumeData, false);

      // Should call setData, not update
      expect(mockHistogramSeries.setData).toHaveBeenCalledTimes(1);
      expect(mockHistogramSeries.update).not.toHaveBeenCalled();

      // Check data format
      const callData = mockHistogramSeries.setData.mock.calls[0][0];
      expect(callData).toHaveLength(2);
      expect(callData[0]).toEqual({
        time: 1000,
        value: 100,
        color: '#0ECB81' // Green for positive delta
      });
      expect(callData[1]).toEqual({
        time: 2000,
        value: 50,
        color: '#F6465D' // Red for negative delta
      });
    });

    it('should use update() for single real-time update (isRealTimeUpdate = true)', () => {
      const volumeData = [
        { time: 3000, delta_volume: '75', buy_volume: '100', sell_volume: '25' }
      ];

      updateLiquidationVolume(volumeData, true);

      // Should call update, not setData
      expect(mockHistogramSeries.update).toHaveBeenCalledTimes(1);
      expect(mockHistogramSeries.setData).not.toHaveBeenCalled();

      // Check update data
      expect(mockHistogramSeries.update).toHaveBeenCalledWith({
        time: 3000,
        value: 75,
        color: '#0ECB81'
      });
    });

    it('should use update() for batch real-time updates', () => {
      const volumeData = [
        { time: 4000, delta_volume: '25', buy_volume: '50', sell_volume: '25' },
        { time: 5000, delta_volume: '-30', buy_volume: '10', sell_volume: '40' }
      ];

      updateLiquidationVolume(volumeData, true);

      // Should call update twice, not setData
      expect(mockHistogramSeries.update).toHaveBeenCalledTimes(2);
      expect(mockHistogramSeries.setData).not.toHaveBeenCalled();

      // Check each update
      expect(mockHistogramSeries.update).toHaveBeenNthCalledWith(1, {
        time: 4000,
        value: 25,
        color: '#0ECB81'
      });
      expect(mockHistogramSeries.update).toHaveBeenNthCalledWith(2, {
        time: 5000,
        value: 30,
        color: '#F6465D'
      });
    });

    it('should skip updates with zero delta volume', () => {
      const volumeData = [
        { time: 6000, delta_volume: '0', buy_volume: '50', sell_volume: '50' }
      ];

      updateLiquidationVolume(volumeData, true);

      // Should not call either method for zero delta
      expect(mockHistogramSeries.update).not.toHaveBeenCalled();
      expect(mockHistogramSeries.setData).not.toHaveBeenCalled();
    });

    it('should filter out zero deltas in setData mode', () => {
      const volumeData = [
        { time: 7000, delta_volume: '100', buy_volume: '100', sell_volume: '0' },
        { time: 8000, delta_volume: '0', buy_volume: '50', sell_volume: '50' },
        { time: 9000, delta_volume: '-75', buy_volume: '0', sell_volume: '75' }
      ];

      updateLiquidationVolume(volumeData, false);

      // Should only include non-zero deltas
      const callData = mockHistogramSeries.setData.mock.calls[0][0];
      expect(callData).toHaveLength(2);
      expect(callData[0].time).toBe(7000);
      expect(callData[1].time).toBe(9000);
    });
  });

  describe('Volume data state management', () => {
    it('should store volume data for tooltips on initial load', () => {
      const volumeData = [
        { time: 10000, delta_volume: '50', buy_volume: '75', sell_volume: '25' },
        { time: 11000, delta_volume: '-25', buy_volume: '25', sell_volume: '50' }
      ];

      updateLiquidationVolume(volumeData, false);

      // Should store complete data
      expect(testModule.getCurrentVolumeData()).toEqual(volumeData);
    });

    it('should update existing volume data on real-time update', () => {
      // Set initial data
      testModule.setCurrentVolumeData([
        { time: 12000, delta_volume: '100', buy_volume: '100', sell_volume: '0' }
      ]);

      const updateData = [
        { time: 12000, delta_volume: '150', buy_volume: '200', sell_volume: '50' }
      ];

      updateLiquidationVolume(updateData, true);

      // Should update existing entry
      expect(testModule.getCurrentVolumeData()).toHaveLength(1);
      expect(testModule.getCurrentVolumeData()[0]).toEqual(updateData[0]);
    });

    it('should append new volume data on real-time update', () => {
      // Set initial data
      testModule.setCurrentVolumeData([
        { time: 13000, delta_volume: '50', buy_volume: '50', sell_volume: '0' }
      ]);

      const updateData = [
        { time: 14000, delta_volume: '75', buy_volume: '100', sell_volume: '25' }
      ];

      updateLiquidationVolume(updateData, true);

      // Should append new entry
      expect(testModule.getCurrentVolumeData()).toHaveLength(2);
      expect(testModule.getCurrentVolumeData()[1]).toEqual(updateData[0]);
    });

    it('should maintain time order after batch updates', () => {
      // Set initial data
      testModule.setCurrentVolumeData([
        { time: 15000, delta_volume: '10', buy_volume: '10', sell_volume: '0' },
        { time: 17000, delta_volume: '30', buy_volume: '30', sell_volume: '0' }
      ]);

      const updateData = [
        { time: 16000, delta_volume: '20', buy_volume: '20', sell_volume: '0' },
        { time: 18000, delta_volume: '40', buy_volume: '40', sell_volume: '0' }
      ];

      updateLiquidationVolume(updateData, true);

      // Should maintain sorted order
      expect(testModule.getCurrentVolumeData()).toHaveLength(4);
      expect(testModule.getCurrentVolumeData().map(d => d.time)).toEqual([15000, 16000, 17000, 18000]);
    });
  });

  describe('Initialization timing', () => {
    it('should buffer data if chart not initialized', () => {
      testModule.setChartInitialized(false);

      const volumeData = [
        { time: 19000, delta_volume: '100', buy_volume: '100', sell_volume: '0' }
      ];

      updateLiquidationVolume(volumeData, false);

      // Should not update series
      expect(mockHistogramSeries.setData).not.toHaveBeenCalled();
      expect(mockHistogramSeries.update).not.toHaveBeenCalled();

      // Should buffer data
      expect(testModule.getPendingVolumeData()).toEqual(volumeData);
    });

    it('should not update if volume series not visible', () => {
      testModule.setVolumeSeriesVisible(false);

      const volumeData = [
        { time: 20000, delta_volume: '50', buy_volume: '50', sell_volume: '0' }
      ];

      updateLiquidationVolume(volumeData, false);

      // Should not update series
      expect(mockHistogramSeries.setData).not.toHaveBeenCalled();
      expect(mockHistogramSeries.update).not.toHaveBeenCalled();
    });

    it('should not update if volume series not created', () => {
      testModule.setVolumeSeries(null);

      const volumeData = [
        { time: 21000, delta_volume: '25', buy_volume: '25', sell_volume: '0' }
      ];

      updateLiquidationVolume(volumeData, false);

      // Should not update series
      expect(mockHistogramSeries.setData).not.toHaveBeenCalled();
      expect(mockHistogramSeries.update).not.toHaveBeenCalled();
    });
  });

  describe('Message type routing', () => {
    it('should handle liquidation_volume messages correctly', () => {
      // This test verifies the message structure expectations
      const liquidationVolumeMessage = {
        type: 'liquidation_volume',
        symbol: 'BTCUSDT',
        timeframe: '1m',
        data: [
          { time: 22000, delta_volume: '100', buy_volume: '150', sell_volume: '50' }
        ],
        is_update: true
      };

      // Simulate global handler as it would be in main.js
      const globalHandler = (data) => {
        updateLiquidationVolume(data.data, data.is_update);
      };
      
      globalHandler(liquidationVolumeMessage);

      // Should have called update() due to is_update flag
      expect(mockHistogramSeries.update).toHaveBeenCalledTimes(1);
    });
  });

  describe('Error handling', () => {
    it('should handle update errors gracefully', () => {
      // Make update throw an error
      mockHistogramSeries.update.mockImplementationOnce(() => {
        throw new Error('Update failed');
      });

      const volumeData = [
        { time: 23000, delta_volume: '50', buy_volume: '50', sell_volume: '0' }
      ];

      // Mock console.error to check it's called
      const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});

      updateLiquidationVolume(volumeData, true);

      // Should log error
      expect(consoleError).toHaveBeenCalledWith('Error updating liquidation volume:', expect.any(Error));

      // Should fall back to setData
      expect(mockHistogramSeries.setData).toHaveBeenCalledTimes(1);

      consoleError.mockRestore();
    });
  });
});