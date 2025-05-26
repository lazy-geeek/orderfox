import React, { useState } from 'react';
import { useAppSelector, useAppDispatch } from '../../store/hooks';
import { executePaperTrade, executeLiveTrade, clearTradeError } from '../../features/trading/tradingSlice';
import './ManualTradeForm.css';

/**
 * ManualTradeForm component for executing manual trades.
 * 
 * Features:
 * - Form inputs for symbol, side, amount, type, and price
 * - Validation for required fields and logical constraints
 * - Integration with Redux for trade execution
 * - Loading states and error handling
 * - Automatic form clearing after successful submission
 */
const ManualTradeForm: React.FC = () => {
  const dispatch = useAppDispatch();
  const { tradingMode, isSubmittingTrade, tradeError } = useAppSelector((state) => state.trading);
  const { selectedSymbol } = useAppSelector((state) => state.marketData);

  // Form state
  const [formData, setFormData] = useState({
    symbol: selectedSymbol || '',
    side: 'buy',
    amount: '',
    type: 'market',
    price: ''
  });

  // Update symbol when selectedSymbol changes
  React.useEffect(() => {
    if (selectedSymbol) {
      setFormData(prev => ({ ...prev, symbol: selectedSymbol }));
    }
  }, [selectedSymbol]);

  // Clear error when form data changes
  React.useEffect(() => {
    if (tradeError) {
      dispatch(clearTradeError());
    }
  }, [formData, dispatch, tradeError]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const validateForm = (): string | null => {
    if (!formData.symbol.trim()) {
      return 'Symbol is required';
    }
    
    const amount = parseFloat(formData.amount);
    if (!formData.amount || isNaN(amount) || amount <= 0) {
      return 'Amount must be a positive number';
    }

    if (formData.type === 'limit') {
      const price = parseFloat(formData.price);
      if (!formData.price || isNaN(price) || price <= 0) {
        return 'Price is required and must be positive for limit orders';
      }
    }

    return null;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    const validationError = validateForm();
    if (validationError) {
      alert(validationError);
      return;
    }

    // Prepare trade details
    const tradeDetails = {
      symbol: formData.symbol.trim(),
      side: formData.side === 'buy' ? 'long' : 'short', // Map UI values to backend values
      amount: parseFloat(formData.amount),
      type: formData.type,
      ...(formData.type === 'limit' && { price: parseFloat(formData.price) })
    };

    try {
      // Execute trade based on trading mode
      if (tradingMode === 'paper') {
        await dispatch(executePaperTrade(tradeDetails)).unwrap();
      } else {
        await dispatch(executeLiveTrade(tradeDetails)).unwrap();
      }

      // Clear form on success
      setFormData({
        symbol: selectedSymbol || '',
        side: 'buy',
        amount: '',
        type: 'market',
        price: ''
      });
    } catch (error) {
      // Error is handled by Redux and displayed via tradeError
      console.error('Trade execution failed:', error);
    }
  };

  return (
    <div className="manual-trade-form">
      <h3 className="form-title">Manual Trade</h3>
      
      <form onSubmit={handleSubmit} className="trade-form">
        {/* Symbol Input */}
        <div className="form-group">
          <label htmlFor="symbol">Symbol</label>
          <input
            type="text"
            id="symbol"
            name="symbol"
            value={formData.symbol}
            onChange={handleInputChange}
            placeholder="e.g., BTC/USDT"
            className="form-input"
            disabled={isSubmittingTrade}
          />
        </div>

        {/* Side Selection */}
        <div className="form-group">
          <label htmlFor="side">Side</label>
          <select
            id="side"
            name="side"
            value={formData.side}
            onChange={handleInputChange}
            className="form-select"
            disabled={isSubmittingTrade}
          >
            <option value="buy">Buy (Long)</option>
            <option value="sell">Sell (Short)</option>
          </select>
        </div>

        {/* Amount Input */}
        <div className="form-group">
          <label htmlFor="amount">Amount</label>
          <input
            type="number"
            id="amount"
            name="amount"
            value={formData.amount}
            onChange={handleInputChange}
            placeholder="0.00"
            step="0.00001"
            min="0"
            className="form-input"
            disabled={isSubmittingTrade}
          />
        </div>

        {/* Type Selection */}
        <div className="form-group">
          <label htmlFor="type">Type</label>
          <select
            id="type"
            name="type"
            value={formData.type}
            onChange={handleInputChange}
            className="form-select"
            disabled={isSubmittingTrade}
          >
            <option value="market">Market</option>
            <option value="limit">Limit</option>
          </select>
        </div>

        {/* Price Input (conditional) */}
        {formData.type === 'limit' && (
          <div className="form-group">
            <label htmlFor="price">Price</label>
            <input
              type="number"
              id="price"
              name="price"
              value={formData.price}
              onChange={handleInputChange}
              placeholder="0.00"
              step="0.01"
              min="0"
              className="form-input"
              disabled={isSubmittingTrade}
            />
          </div>
        )}

        {/* Error Display */}
        {tradeError && (
          <div className="error-message">
            {tradeError}
          </div>
        )}

        {/* Submit Button */}
        <button
          type="submit"
          className={`submit-button ${isSubmittingTrade ? 'loading' : ''}`}
          disabled={isSubmittingTrade}
        >
          {isSubmittingTrade ? (
            <>
              <span className="loading-spinner"></span>
              Submitting...
            </>
          ) : (
            `Submit ${tradingMode === 'paper' ? 'Paper' : 'Live'} Trade`
          )}
        </button>
      </form>
    </div>
  );
};

export default ManualTradeForm;