import React, { useEffect } from 'react';
import { useAppSelector, useAppDispatch } from '../../store/hooks';
import { fetchOpenPositions, executePaperTrade, executeLiveTrade } from '../../features/trading/tradingSlice';
import './PositionsTable.css';

// Position interface matching backend schema
interface Position {
  symbol: string;
  side: string;
  size: number;
  entryPrice: number;
  markPrice: number;
  unrealizedPnl: number;
}

const PositionsTable: React.FC = () => {
  const dispatch = useAppDispatch();
  const { openPositions, tradingMode, isSubmittingTrade } = useAppSelector((state) => state.trading);

  // Fetch positions on mount and when trading mode changes
  useEffect(() => {
    dispatch(fetchOpenPositions());
  }, [dispatch, tradingMode]);

  const handleClosePosition = async (position: Position) => {
    const tradeDetails = {
      symbol: position.symbol,
      side: 'close',
      amount: position.size,
      type: 'market'
    };

    if (tradingMode === 'paper') {
      dispatch(executePaperTrade(tradeDetails));
    } else {
      dispatch(executeLiveTrade(tradeDetails));
    }
  };

  const formatPrice = (price: number): string => {
    return price.toLocaleString('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 8
    });
  };

  const formatPnL = (pnl: number): string => {
    const sign = pnl >= 0 ? '+' : '';
    return `${sign}${pnl.toFixed(2)}`;
  };

  return (
    <div className="positions-table-container">
      <h3 className="positions-title">Open Positions</h3>
      {openPositions.length === 0 ? (
        <div className="no-positions">
          No open positions.
        </div>
      ) : (
        <table className="positions-table">
          <thead>
            <tr>
              <th>Symbol</th>
              <th>Side</th>
              <th>Size</th>
              <th>Entry Price</th>
              <th>Current Price</th>
              <th>PnL (USDT)</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {openPositions.map((position: Position, index: number) => (
              <tr key={index}>
                <td className="symbol">{position.symbol}</td>
                <td className={`side ${position.side.toLowerCase()}`}>
                  {position.side.charAt(0).toUpperCase() + position.side.slice(1)}
                </td>
                <td className="size">{position.size}</td>
                <td className="entry-price">${formatPrice(position.entryPrice)}</td>
                <td className="current-price">${formatPrice(position.markPrice)}</td>
                <td className={`pnl ${position.unrealizedPnl >= 0 ? 'positive' : 'negative'}`}>
                  {formatPnL(position.unrealizedPnl)}
                </td>
                <td className="actions">
                  <button
                    className="close-button"
                    onClick={() => handleClosePosition(position)}
                    disabled={isSubmittingTrade}
                  >
                    {isSubmittingTrade ? 'Closing...' : 'Close'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
};

export default PositionsTable;