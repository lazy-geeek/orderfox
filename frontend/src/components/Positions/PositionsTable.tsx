import React from 'react';
import './PositionsTable.css';

interface Position {
  symbol: string;
  side: 'Long' | 'Short';
  size: number;
  entryPrice: number;
  currentPrice: number;
  pnl: number;
}

const PositionsTable: React.FC = () => {
  // Placeholder data for demonstration
  const positions: Position[] = [
    {
      symbol: 'BTC/USDT',
      side: 'Long',
      size: 0.1,
      entryPrice: 60000,
      currentPrice: 61000,
      pnl: 100
    },
    {
      symbol: 'ETH/USDT',
      side: 'Short',
      size: 2,
      entryPrice: 3000,
      currentPrice: 2950,
      pnl: 100
    },
    {
      symbol: 'ADA/USDT',
      side: 'Long',
      size: 1000,
      entryPrice: 0.45,
      currentPrice: 0.47,
      pnl: 20
    }
  ];

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
      <table className="positions-table">
        <thead>
          <tr>
            <th>Symbol</th>
            <th>Side</th>
            <th>Size</th>
            <th>Entry Price</th>
            <th>Current Price</th>
            <th>PnL (USDT)</th>
          </tr>
        </thead>
        <tbody>
          {positions.map((position, index) => (
            <tr key={index}>
              <td className="symbol">{position.symbol}</td>
              <td className={`side ${position.side.toLowerCase()}`}>
                {position.side}
              </td>
              <td className="size">{position.size}</td>
              <td className="entry-price">${formatPrice(position.entryPrice)}</td>
              <td className="current-price">${formatPrice(position.currentPrice)}</td>
              <td className={`pnl ${position.pnl >= 0 ? 'positive' : 'negative'}`}>
                {formatPnL(position.pnl)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {positions.length === 0 && (
        <div className="no-positions">
          No open positions
        </div>
      )}
    </div>
  );
};

export default PositionsTable;