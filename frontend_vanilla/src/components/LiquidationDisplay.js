/**
 * Liquidation Display Component
 * 
 * Displays real-time liquidation orders from Binance futures with
 * proper formatting, color-coded buy/sell sides, and connection status.
 * Follows the thin client pattern - backend provides all formatted data.
 */

import { subscribe, state } from '../store/store.js';
import { connectWebSocketStream, disconnectWebSocketStream } from '../services/websocketService.js';

export class LiquidationDisplay {
    constructor(container) {
        this.container = container;
        this.isConnected = false;
        this.liquidations = [];
        this.maxLiquidations = 50;
        this.currentSymbol = null;
        
        this.init();
    }
    
    init() {
        this.render();
        this.setupStateSubscriptions();
        this.setupWebSocket();
    }
    
    render() {
        this.container.innerHTML = `
            <div class="orderfox-liquidation-display orderfox-display-base">
                <div class="display-header">
                    <span class="display-title">Liquidations</span>
                    <div class="connection-status disconnected">
                        <span class="status-dot"></span>
                        <span class="status-text">Disconnected</span>
                    </div>
                </div>
                <div class="display-content">
                    <div class="liquidation-header">
                        <span>Side</span>
                        <span>Quantity</span>
                        <span>Price (USDT)</span>
                        <span>Time</span>
                    </div>
                    <div id="liquidation-list" class="liquidation-list">
                        <div class="empty-state">Waiting for liquidations...</div>
                    </div>
                </div>
            </div>
        `;
        
        this.liquidationListEl = this.container.querySelector('#liquidation-list');
    }
    
    setupWebSocket() {
        const symbol = state.selectedSymbol;
        if (!symbol) {
            // Update connection status to show we're waiting for symbol selection
            this.updateConnectionStatus(false);
            return;
        }
        
        // Clean up existing connection for old symbol
        if (this.currentSymbol && this.currentSymbol !== symbol) {
            disconnectWebSocketStream('liquidations', this.currentSymbol);
        }
        
        this.currentSymbol = symbol;
        
        // Connect to liquidation stream
        connectWebSocketStream(symbol, 'liquidations');
    }
    
    addLiquidation(liquidation) {
        // Add to beginning of array
        this.liquidations.unshift(liquidation);
        
        // Limit array size
        if (this.liquidations.length > this.maxLiquidations) {
            this.liquidations = this.liquidations.slice(0, this.maxLiquidations);
        }
        
        // Create new element
        const liquidationEl = this.createLiquidationElement(liquidation);
        
        // Remove empty state if exists
        const emptyState = this.liquidationListEl.querySelector('.empty-state');
        if (emptyState) {
            emptyState.remove();
        }
        
        // Add to DOM with animation
        liquidationEl.style.opacity = '0';
        liquidationEl.style.transform = 'translateY(-10px)';
        this.liquidationListEl.insertBefore(liquidationEl, this.liquidationListEl.firstChild);
        
        // Trigger animation
        requestAnimationFrame(() => {
            liquidationEl.style.transition = 'opacity 0.3s, transform 0.3s';
            liquidationEl.style.opacity = '1';
            liquidationEl.style.transform = 'translateY(0)';
        });
        
        // Remove excess elements
        while (this.liquidationListEl.children.length > this.maxLiquidations) {
            this.liquidationListEl.removeChild(this.liquidationListEl.lastChild);
        }
    }
    
    createLiquidationElement(liquidation) {
        const div = document.createElement('div');
        div.className = 'liquidation-item';
        
        const sideClass = liquidation.side === 'BUY' ? 'bid-price' : 'ask-price';
        
        div.innerHTML = `
            <span class="liquidation-side ${sideClass}">${liquidation.side}</span>
            <span class="liquidation-quantity">${liquidation.quantityFormatted}</span>
            <span class="liquidation-price">${liquidation.priceUsdtFormatted}</span>
            <span class="liquidation-time">${liquidation.displayTime}</span>
        `;
        
        return div;
    }
    
    renderLiquidations() {
        if (this.liquidations.length === 0) {
            this.liquidationListEl.innerHTML = '<div class="empty-state">Waiting for liquidations...</div>';
            return;
        }
        
        this.liquidationListEl.innerHTML = this.liquidations
            .map(liq => {
                const sideClass = liq.side === 'BUY' ? 'bid-price' : 'ask-price';
                return `
                    <div class="liquidation-item">
                        <span class="liquidation-side ${sideClass}">${liq.side}</span>
                        <span class="liquidation-quantity">${liq.quantityFormatted}</span>
                        <span class="liquidation-price">${liq.priceUsdtFormatted}</span>
                        <span class="liquidation-time">${liq.displayTime}</span>
                    </div>
                `;
            })
            .join('');
    }
    
    updateConnectionStatus(connected) {
        this.isConnected = connected;
        const statusEl = this.container.querySelector('.connection-status');
        const statusTextEl = this.container.querySelector('.status-text');
        
        if (connected) {
            statusEl.classList.remove('disconnected');
            statusEl.classList.add('connected');
            statusTextEl.textContent = 'Connected';
        } else {
            statusEl.classList.remove('connected');
            statusEl.classList.add('disconnected');
            statusTextEl.textContent = 'Disconnected';
        }
    }
    
    setupStateSubscriptions() {
        // Subscribe to symbol changes
        subscribe((key) => {
            if (key === 'selectedSymbol' && state.selectedSymbol !== this.currentSymbol) {
                this.currentSymbol = state.selectedSymbol;
                this.liquidations = [];  // Clear old data
                this.renderLiquidations();
                this.setupWebSocket();
            }
        });
        
        // Set up global liquidation update function
        window.updateLiquidationDisplay = (data) => {
            if (data.type === 'liquidations' && data.initial) {
                this.liquidations = data.data || [];
                this.renderLiquidations();
                this.updateConnectionStatus(true);
            } else if (data.type === 'liquidation') {
                this.addLiquidation(data.data);
                this.updateConnectionStatus(true);
            } else if (data.type === 'error') {
                console.error('Liquidation stream error:', data.message);
                this.updateConnectionStatus(false);
            }
        };
    }
    
    cleanup() {
        if (this.currentSymbol) {
            disconnectWebSocketStream(this.currentSymbol, 'liquidations');
        }
        if (window.updateLiquidationDisplay) {
            delete window.updateLiquidationDisplay;
        }
    }
}

/**
 * Create the Liquidation display component
 * @returns {HTMLElement} The created component container
 */
function createLiquidationDisplay() {
  const container = document.createElement('div');
  container.className = 'orderfox-display-base orderfox-liquidation-display';

  container.innerHTML = `
    <div class="display-header">
      <h3>Liquidations</h3>
      <div class="header-controls">
        <span class="symbol-label"></span>
        <div class="connection-status">
          <span class="status-indicator disconnected">○</span>
          <span class="status-text">Disconnected</span>
        </div>
      </div>
    </div>
    <div class="display-content">
      <div class="liquidation-section">
        <div class="section-header liquidation-header">
          <span class="side-header">Side</span>
          <span class="quantity-header">Quantity</span>
          <span class="price-header">Price (USDT)</span>
        </div>
        <div class="liquidation-container">
          <div class="liquidation-list" id="liquidation-list">
            <!-- Liquidations will be inserted here -->
          </div>
        </div>
      </div>
    </div>
    <div class="display-footer">
      <span class="timestamp"></span>
    </div>
  `;

  return container;
}

export { 
  createLiquidationDisplay
};