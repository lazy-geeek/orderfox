import { createCandlestickChart, createTimeframeSelector, createVolumeToggleButton, updateLatestCandle, updateLiquidationVolume, toggleLiquidationVolume, resetChartData, updateChartTitle, updateCandlestickChart } from './LightweightChart.js';
import { createTabbedTradingDisplay } from './TabbedTradingDisplay.js';
import { WebSocketManager } from '../services/websocketManager.js';
import { state, subscribe, notify, openModal as storeOpenModal, closeModal as storeCloseModal, setBotError } from '../store/store.js';

/**
 * Creates a modal dialog for the trading interface using DaisyUI v5 dialog element
 * @returns {Object} Modal object with element, open, close, and destroy methods
 */
export function createTradingModal() {
  // Create native dialog element
  const dialog = document.createElement('dialog');
  dialog.id = 'trading-modal';
  dialog.className = 'modal';
  dialog.setAttribute('data-testid', 'trading-modal');

  // Modal box with custom sizing
  const modalBox = document.createElement('div');
  modalBox.className = 'modal-box w-11/12 max-w-[1400px] h-[90vh] p-0 overflow-hidden';

  // Close button form (DaisyUI pattern)
  const closeForm = document.createElement('form');
  closeForm.method = 'dialog';
  closeForm.className = 'absolute top-2 right-2 z-10';

  const closeButton = document.createElement('button');
  closeButton.className = 'btn btn-sm btn-circle btn-ghost';
  closeButton.setAttribute('data-testid', 'modal-close-button');
  closeButton.innerHTML = '✕';
  closeButton.setAttribute('aria-label', 'Close modal');

  closeForm.appendChild(closeButton);
  modalBox.appendChild(closeForm);

  // Trading interface container with loading state
  const tradingInterfaceContainer = document.createElement('div');
  tradingInterfaceContainer.className = 'trading-interface-container h-full p-4 overflow-auto';
  tradingInterfaceContainer.setAttribute('data-testid', 'trading-interface-container');
  
  // Add loading indicator initially
  tradingInterfaceContainer.innerHTML = `
    <div class="loading-container flex items-center justify-center h-full">
      <div class="text-center">
        <div class="loading loading-spinner loading-lg"></div>
        <p class="mt-4">Loading trading interface...</p>
      </div>
    </div>
  `;

  modalBox.appendChild(tradingInterfaceContainer);
  dialog.appendChild(modalBox);

  // Component state tracking
  let isInitialized = false;
  let tradingComponents = null;
  let chartUpdateSubscription = null;
  let isModalActive = false;

  /**
   * Initialize trading interface components (lazy loading)
   */
  function initializeTradingInterface() {
    if (isInitialized) {
      return tradingComponents;
    }

    // Create trading content wrapper with side-by-side layout
    const tradingContentWrapper = document.createElement('div');
    tradingContentWrapper.className = 'trading-content-wrapper flex flex-col lg:flex-row gap-4 h-full';

    // Left Section - Chart (flexible width)
    const leftSection = document.createElement('div');
    leftSection.className = 'left-section flex-1 min-w-0';

    // Chart container
    const candlestickChartContainer = document.createElement('div');
    candlestickChartContainer.className = 'chart-container';
    
    // Create chart
    createCandlestickChart(candlestickChartContainer);

    // CRITICAL: Set up global functions for WebSocket data flow
    // These are essential for proper WebSocket integration in modal context
    window.updateLatestCandleDirectly = updateLatestCandle;
    window.state = state;
    window.notify = notify;
    window.resetChartData = resetChartData;
    
    // Set up global function for liquidation volume updates
    window.updateLiquidationVolume = (data) => {
      if (data && data.data && Array.isArray(data.data)) {
        // Use the is_update flag from backend to determine if this is a real-time update
        const isRealTimeUpdate = data.is_update || false;
        console.log('Processing liquidation volume update, is_update:', isRealTimeUpdate, 'data points:', data.data.length);
        updateLiquidationVolume(data.data, isRealTimeUpdate);
      }
    };

    // Set up global function for liquidation volume toggle
    window.toggleLiquidationVolume = () => {
      return toggleLiquidationVolume();
    };

    // CRITICAL: Subscribe to candle data updates
    // This ensures the chart is updated when historical or real-time data arrives
    chartUpdateSubscription = (key) => {
      // Only process updates if modal is active (prevent updates after modal close)
      if (!isModalActive) return;
      
      if (key === 'currentCandles') {
        // Check if we have candle data to display
        if (state.currentCandles && state.currentCandles.length > 0) {
          console.log('Chart subscription: updating with', state.currentCandles.length, 'candles');
          const selectedSymbolData = state.symbolsList.find(s => s.id === state.selectedSymbol);
          updateCandlestickChart(
            { currentCandles: state.currentCandles },
            state.selectedSymbol,
            state.selectedTimeframe,
            false, // Not initial load if we're getting updates
            selectedSymbolData
          );
        } else {
          console.log('Chart subscription: currentCandles updated but empty');
        }
      }
    };
    
    // Subscribe to state changes
    subscribe(chartUpdateSubscription);

    // Chart controls container
    const chartControls = document.createElement('div');
    chartControls.className = 'chart-controls flex gap-4 mb-2';
    chartControls.style.display = 'flex';
    chartControls.style.gap = '1rem';
    chartControls.style.marginBottom = '0.5rem';

    // Create timeframe selector
    const timeframeSelector = createTimeframeSelector((newTimeframe) => {
      WebSocketManager.switchTimeframe(newTimeframe);
    });

    // Create volume toggle button
    const volumeToggleButton = createVolumeToggleButton();

    chartControls.appendChild(timeframeSelector);
    chartControls.appendChild(volumeToggleButton);

    candlestickChartContainer.prepend(chartControls);
    leftSection.appendChild(candlestickChartContainer);

    // Right Section - Tabbed Trading Tables (fixed/min width)
    const rightSection = document.createElement('div');
    rightSection.className = 'right-section w-full lg:w-96 flex-shrink-0';

    // Create tabbed trading display
    const tabbedTradingDisplay = createTabbedTradingDisplay();
    rightSection.appendChild(tabbedTradingDisplay.element);

    // Assemble the layout
    tradingContentWrapper.appendChild(leftSection);
    tradingContentWrapper.appendChild(rightSection);

    // Store component references
    tradingComponents = {
      wrapper: tradingContentWrapper,
      chartContainer: candlestickChartContainer,
      timeframeSelector,
      volumeToggleButton,
      tabbedDisplay: tabbedTradingDisplay
    };

    isInitialized = true;
    return tradingComponents;
  }

  /**
   * Open the modal and set up trading interface
   */
  async function openModal() {
    try {
      // Show modal immediately with loading state
      dialog.showModal();

      // Set modal as active for subscriptions
      isModalActive = true;

      // Set modal state and view (store function)
      storeOpenModal();

      // Use requestAnimationFrame to defer component initialization
      requestAnimationFrame(async () => {
        try {
          // Initialize components if not already done
          const components = initializeTradingInterface();
          
          // Clear loading indicator and add trading interface
          tradingInterfaceContainer.innerHTML = '';
          tradingInterfaceContainer.appendChild(components.wrapper);

          // Connect WebSockets for selected bot with timeout
          const selectedBot = state.bots.find(bot => bot.id === state.selectedBotId);
          if (selectedBot) {
            // Add timeout for WebSocket connections
            const connectionTimeout = new Promise((_, reject) => {
              setTimeout(() => reject(new Error('WebSocket connection timeout')), 15000);
            });
            
            const connectionPromise = WebSocketManager.switchToBotContext(selectedBot);
            
            await Promise.race([connectionPromise, connectionTimeout]);
            
            // CRITICAL: Update chart title immediately after WebSocket connections
            // This ensures the symbol overlay shows the selected bot's symbol
            updateChartTitle(selectedBot.symbol, state.selectedTimeframe);
            
            // CRITICAL: Check if historical data already exists and trigger initial update
            // This handles the case where historical data arrived before subscription was ready
            if (state.currentCandles && state.currentCandles.length > 0) {
              console.log('Historical data already loaded, triggering initial chart update');
              const selectedSymbolData = state.symbolsList.find(s => s.id === state.selectedSymbol);
              updateCandlestickChart(
                { currentCandles: state.currentCandles },
                state.selectedSymbol,
                state.selectedTimeframe,
                true, // This IS initial load
                selectedSymbolData
              );
            }
          } else {
            throw new Error('No bot selected for trading modal');
          }

          console.log('Trading modal opened successfully');
        } catch (error) {
          console.error('Error in deferred modal initialization:', error);
          showModalError(`Failed to initialize trading interface: ${error.message}`);
        }
      });
    } catch (error) {
      // Remove loading state on error
      tradingInterfaceContainer.classList.remove('loading');
      
      // Close modal if it was opened
      if (dialog.open) {
        dialog.close();
      }
      
      console.error('Error opening trading modal:', error);
      
      // Show user-friendly error message
      showModalError(`Failed to open trading interface: ${error.message}`);
      
      throw error;
    }
  }

  /**
   * Close the modal and clean up
   */
  async function closeModal() {
    try {
      // Set modal as inactive
      isModalActive = false;

      // Disconnect all WebSockets
      WebSocketManager.disconnectAllWebSockets();

      // Close modal using native dialog method
      dialog.close();

      // Reset view state (store function)
      storeCloseModal();

      console.log('Trading modal closed successfully');
    } catch (error) {
      console.error('Error closing trading modal:', error);
    }
  }

  /**
   * Handle cleanup when modal is closed (triggered by close event)
   */
  async function handleModalClose() {
    try {
      // Set modal as inactive
      isModalActive = false;

      // Disconnect all WebSockets
      WebSocketManager.disconnectAllWebSockets();

      // Reset view state (store function)
      storeCloseModal();

      console.log('Trading modal closed via event');
    } catch (error) {
      console.error('Error handling modal close:', error);
    }
  }

  // Event listeners for modal close
  dialog.addEventListener('close', handleModalClose);

  // ESC key handling (default dialog behavior)
  dialog.addEventListener('cancel', () => {
    // Allow default ESC behavior
    console.log('Modal closed via ESC key');
  });

  // Prevent backdrop click from closing modal
  dialog.addEventListener('click', (event) => {
    // Only close if clicking the dialog itself, not its children
    if (event.target === dialog) {
      event.preventDefault();
      event.stopPropagation();
    }
  });

  // Global error handler for unhandled WebSocket errors in modal context
  dialog.addEventListener('error', (event) => {
    console.error('Modal error event:', event);
    showModalError('An unexpected error occurred in the trading interface');
  });

  /**
   * Destroy the modal and clean up resources
   */
  function destroy() {
    // Set modal as inactive
    isModalActive = false;

    // Clean up WebSocket connections
    try {
      WebSocketManager.disconnectAllWebSockets();
    } catch (error) {
      console.error('Error disconnecting WebSockets during modal destroy:', error);
    }

    // Clean up component references
    if (tradingComponents && tradingComponents.tabbedDisplay) {
      tradingComponents.tabbedDisplay.destroy();
    }
    tradingComponents = null;
    isInitialized = false;

    // Remove from DOM if attached
    if (dialog.parentNode) {
      dialog.parentNode.removeChild(dialog);
    }
  }

  /**
   * Show error message to user in modal context
   */
  function showModalError(message) {
    try {
      // Use the already imported store function
      setBotError(message);
      
      // Also log for debugging
      console.error('Modal Error:', message);
      
      // Show a temporary visual error indicator in the modal if possible
      if (tradingInterfaceContainer) {
        const errorElement = document.createElement('div');
        errorElement.className = 'alert alert-error modal-error-alert';
        errorElement.style.cssText = `
          position: absolute;
          top: 10px;
          left: 50%;
          transform: translateX(-50%);
          z-index: 20;
          max-width: 90%;
          animation: slideDown 0.3s ease-out;
        `;
        errorElement.innerHTML = `
          <div class="flex">
            <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>${message}</span>
          </div>
        `;
        
        // Add click handler to dismiss error
        errorElement.addEventListener('click', () => {
          if (errorElement.parentNode) {
            errorElement.remove();
          }
        });
        
        // Add to modal container
        tradingInterfaceContainer.appendChild(errorElement);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
          if (errorElement.parentNode) {
            errorElement.remove();
          }
        }, 5000);
      }
    } catch (error) {
      console.error('Error showing modal error message:', error);
      // Fallback to simple console error
      console.error('Modal Error (fallback):', message);
    }
  }

  /**
   * Switch to a different bot context without closing the modal
   */
  async function switchBotContext(bot) {
    try {
      if (!dialog.open) {
        const error = 'Cannot switch bot context - modal is not open';
        console.warn(error);
        showModalError(error);
        return;
      }

      if (!bot) {
        throw new Error('Invalid bot provided for context switch');
      }

      console.log(`Switching modal to bot context: ${bot.name}`);
      
      // Show loading state while switching
      tradingInterfaceContainer.classList.add('loading');
      
      // Add timeout for bot context switching
      const switchTimeout = new Promise((_, reject) => {
        setTimeout(() => reject(new Error('Bot context switch timeout')), 10000);
      });
      
      const switchPromise = WebSocketManager.switchToBotContext(bot);
      
      // Use WebSocketManager to switch to new bot context with timeout
      await Promise.race([switchPromise, switchTimeout]);
      
      // Remove loading state
      tradingInterfaceContainer.classList.remove('loading');
      
      console.log('Bot context switched successfully in modal');
    } catch (error) {
      // Remove loading state on error
      tradingInterfaceContainer.classList.remove('loading');
      
      console.error('Error switching bot context in modal:', error);
      
      // Show user-friendly error message
      showModalError(`Failed to switch to ${bot?.name || 'selected bot'}: ${error.message}`);
      
      throw error;
    }
  }

  return {
    element: dialog,
    open: openModal,
    close: closeModal,
    switchBotContext,
    destroy,
    isOpen: () => dialog.open
  };
}