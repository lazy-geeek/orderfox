/**
 * TabbedTradingDisplay - A unified component that consolidates OrderBook, 
 * LastTrades, and Liquidation displays into a single tabbed interface.
 * 
 * This component uses DaisyUI v5 radio input tabs pattern for state management
 * and implements lazy initialization to optimize performance. Components are
 * only created when their tab is first selected.
 * 
 * @module TabbedTradingDisplay
 */

import { createOrderBookDisplay, updateOrderBookDisplay } from './OrderBookDisplay.js';
import { createLastTradesDisplay, updateLastTradesDisplay } from './LastTradesDisplay.js';
import { LiquidationDisplay } from './LiquidationDisplay.js';
import { state, subscribe } from '../store/store.js';

/**
 * Creates and returns a tabbed trading display component that consolidates
 * OrderBook, LastTrades, and Liquidation components into a single interface.
 * 
 * Architecture:
 * - Uses DaisyUI v5 radio input tabs for tab switching
 * - Implements lazy initialization for performance optimization
 * - Maintains existing WebSocket connections and state management
 * - OrderBook and LastTrades use external WebSocketManager
 * - LiquidationDisplay manages its own WebSocket connections
 * 
 * @returns {Object} Component object with element and destroy method
 * @returns {HTMLElement} returns.element - The DOM element for the component
 * @returns {Function} returns.destroy - Method to clean up resources
 */
export function createTabbedTradingDisplay() {
    // Internal state to track initialized components
    const componentState = {
        initialized: {
            orderbook: false,
            trades: false,
            liquidations: false
        },
        components: {
            orderbook: null,
            trades: null,
            liquidations: null
        }
    };

    // Create main container with appropriate classes
    const container = document.createElement('div');
    container.className = 'orderfox-display-base orderfox-tabbed-trading-display';

    // Build the HTML structure with DaisyUI tabs
    container.innerHTML = `
        <div role="tablist" class="tabs tabs-boxed">
            <input type="radio" name="trading_tabs" class="tab" aria-label="Order Book" checked />
            <div class="tab-content bg-base-100 border-base-300 p-6">
                <div id="orderbook-placeholder" class="component-placeholder">
                    <div class="loading loading-spinner loading-lg"></div>
                    <span>Loading Order Book...</span>
                </div>
            </div>

            <input type="radio" name="trading_tabs" class="tab" aria-label="Trades" />
            <div class="tab-content bg-base-100 border-base-300 p-6">
                <div id="trades-placeholder" class="component-placeholder">
                    <div class="loading loading-spinner loading-lg"></div>
                    <span>Loading Trades...</span>
                </div>
            </div>

            <input type="radio" name="trading_tabs" class="tab" aria-label="Liquidations" />
            <div class="tab-content bg-base-100 border-base-300 p-6">
                <div id="liquidations-placeholder" class="component-placeholder">
                    <div class="loading loading-spinner loading-lg"></div>
                    <span>Loading Liquidations...</span>
                </div>
            </div>
        </div>
    `;

    /**
     * Initializes a component for the specified tab if not already initialized.
     * This is called lazily when a tab is first selected to optimize performance.
     * 
     * @param {string} tabName - The tab name ('orderbook', 'trades', or 'liquidations')
     */
    function initializeTabComponent(tabName) {
        if (componentState.initialized[tabName]) {
            return; // Already initialized
        }

        const placeholder = container.querySelector(`#${tabName}-placeholder`);
        if (!placeholder) {
            console.error(`Placeholder not found for tab: ${tabName}`);
            return;
        }

        try {
            let component;

            switch (tabName) {
                case 'orderbook':
                    // OrderBook uses external WebSocketManager for connection management
                    // This allows for dynamic parameter updates (depth, rounding) and
                    // centralized connection handling across the application
                    const orderBookElement = createOrderBookDisplay();
                    
                    // Initial update with current state
                    updateOrderBookDisplay(orderBookElement, state);
                    
                    // Subscribe to state changes
                    const orderBookUpdate = () => updateOrderBookDisplay(orderBookElement, state);
                    subscribe(orderBookUpdate);
                    
                    component = { element: orderBookElement, destroy: () => {} };
                    componentState.components.orderbook = component;
                    break;

                case 'trades':
                    // LastTrades also uses external WebSocketManager to maintain
                    // consistency with OrderBook and enable centralized symbol switching
                    const tradesElement = createLastTradesDisplay();
                    
                    // Initial update with current state
                    updateLastTradesDisplay(tradesElement, state);
                    
                    // Subscribe to state changes  
                    const tradesUpdate = () => updateLastTradesDisplay(tradesElement, state);
                    subscribe(tradesUpdate);
                    
                    component = { element: tradesElement, destroy: () => {} };
                    componentState.components.trades = component;
                    break;

                case 'liquidations':
                    // LiquidationDisplay uses internal WebSocket management because:
                    // 1. It connects to different streams (Binance @forceOrder)
                    // 2. It has complex connection pooling logic
                    // 3. It manages multiple subscribers per symbol
                    // This mixed approach is intentional for optimal performance
                    const liquidationContainer = document.createElement('div');
                    const liquidationInstance = new LiquidationDisplay(liquidationContainer);
                    component = { 
                        element: liquidationContainer, 
                        destroy: () => liquidationInstance.cleanup() 
                    };
                    componentState.components.liquidations = component;
                    break;

                default:
                    console.error(`Unknown tab name: ${tabName}`);
                    return;
            }

            // Replace placeholder with the actual component
            if (component && component.element) {
                placeholder.parentNode.replaceChild(component.element, placeholder);
                componentState.initialized[tabName] = true;
                console.log(`Initialized ${tabName} component`);
            } else {
                console.error(`Component creation failed for ${tabName}`);
            }
        } catch (error) {
            console.error(`Error initializing ${tabName} component:`, error);
            placeholder.innerHTML = `<div class="alert alert-error">Failed to load ${tabName}</div>`;
        }
    }

    /**
     * Handles tab change events by initializing the selected tab's component
     * if it hasn't been initialized yet.
     * 
     * Design Decision: DaisyUI radio inputs manage tab state without JavaScript,
     * providing better accessibility, persistent state, and simpler code.
     * We only handle the initialization logic, not the visual tab switching.
     * 
     * @param {Event} event - The change event from radio input
     */
    function handleTabChange(event) {
        const selectedLabel = event.target.getAttribute('aria-label');
        
        // Map aria-label to internal tab names
        const tabMapping = {
            'Order Book': 'orderbook',
            'Trades': 'trades',
            'Liquidations': 'liquidations'
        };

        const tabName = tabMapping[selectedLabel];
        if (tabName) {
            console.log(`Switching to ${selectedLabel} tab`);
            initializeTabComponent(tabName);
        }
    }

    // Add event listeners to all radio inputs for tab switching
    const radioInputs = container.querySelectorAll('input[name="trading_tabs"]');
    radioInputs.forEach(radio => {
        radio.addEventListener('change', handleTabChange);
    });

    // Initialize the default tab (Order Book) immediately since it's checked
    // Use setTimeout to ensure DOM is fully ready
    setTimeout(() => {
        initializeTabComponent('orderbook');
    }, 0);

    /**
     * Cleanup method to destroy all initialized components and remove event listeners.
     * This prevents memory leaks and properly disconnects WebSocket connections.
     */
    function destroy() {
        console.log('Destroying TabbedTradingDisplay...');

        // Clean up OrderBook component if initialized
        if (componentState.components.orderbook && componentState.components.orderbook.destroy) {
            componentState.components.orderbook.destroy();
        }

        // Clean up LastTrades component if initialized
        if (componentState.components.trades && componentState.components.trades.destroy) {
            componentState.components.trades.destroy();
        }

        // Clean up LiquidationDisplay instance if initialized
        if (componentState.components.liquidations && componentState.components.liquidations.destroy) {
            componentState.components.liquidations.destroy();
        }

        // Remove all event listeners
        const radioInputs = container.querySelectorAll('input[name="trading_tabs"]');
        radioInputs.forEach(radio => {
            radio.removeEventListener('change', handleTabChange);
        });

        // Clear component references
        componentState.components.orderbook = null;
        componentState.components.trades = null;
        componentState.components.liquidations = null;
        
        // Reset initialization state
        componentState.initialized.orderbook = false;
        componentState.initialized.trades = false;
        componentState.initialized.liquidations = false;

        console.log('TabbedTradingDisplay cleanup complete');
    }

    return {
        element: container,
        destroy
    };
}