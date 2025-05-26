import React from 'react';
import { useAppSelector, useAppDispatch } from '../../store/hooks';
import { setTradingModeApi, TradingMode } from '../../features/trading/tradingSlice';
import './TradingModeToggle.css';

/**
 * TradingModeToggle component that allows users to switch between Paper and Live trading modes.
 * 
 * Features:
 * - Displays current trading mode clearly
 * - Allows switching between 'paper' and 'live' modes
 * - Shows loading state during mode changes
 * - Integrates with Redux for state management
 */
const TradingModeToggle: React.FC = () => {
  const dispatch = useAppDispatch();
  const { tradingMode, isSubmittingTrade } = useAppSelector((state) => state.trading);

  const handleModeToggle = () => {
    const newMode: TradingMode = tradingMode === 'paper' ? 'live' : 'paper';
    dispatch(setTradingModeApi(newMode));
  };

  return (
    <div className="trading-mode-toggle">
      <span className="mode-label">Mode:</span>
      <button
        className={`mode-button ${tradingMode}`}
        onClick={handleModeToggle}
        disabled={isSubmittingTrade}
        title={`Switch to ${tradingMode === 'paper' ? 'Live' : 'Paper'} mode`}
      >
        {isSubmittingTrade ? (
          <span className="loading">
            <span className="spinner"></span>
            Switching...
          </span>
        ) : (
          <span className="mode-text">
            {tradingMode === 'paper' ? 'Paper' : 'Live'}
          </span>
        )}
      </button>
    </div>
  );
};

export default TradingModeToggle;