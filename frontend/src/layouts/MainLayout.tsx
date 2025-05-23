import React from 'react';
import SymbolSelector from '../components/SymbolSelector';
import CandlestickChart from '../components/Chart/CandlestickChart';
import OrderBookDisplay from '../components/OrderBook/OrderBookDisplay';
import PositionsTable from '../components/Positions/PositionsTable';

/**
 * MainLayout component that defines the overall page structure for the crypto trading bot.
 * 
 * Layout structure:
 * - Header: Contains the symbol selector
 * - Main content area: Displays the candlestick chart (left) and order book (right)
 * - Bottom area: Shows the positions table
 */
const MainLayout: React.FC = () => {
  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100vh',
      fontFamily: 'Arial, sans-serif'
    }}>
      {/* Header Section */}
      <header style={{
        padding: '1rem',
        backgroundColor: '#2c3e50',
        color: 'white',
        borderBottom: '2px solid #34495e'
      }}>
        <h1 style={{ margin: '0 0 1rem 0', fontSize: '1.5rem' }}>Crypto Trading Bot</h1>
        <SymbolSelector />
      </header>

      {/* Main Content Area */}
      <div style={{
        display: 'flex',
        flex: 1,
        gap: '1rem',
        padding: '1rem'
      }}>
        {/* Chart Section (Left) */}
        <main style={{
          flex: 2,
          display: 'flex',
          flexDirection: 'column'
        }}>
          <CandlestickChart />
        </main>

        {/* Right Sidebar */}
        <aside style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column'
        }}>
          <OrderBookDisplay />
        </aside>
      </div>

      {/* Bottom Section */}
      <footer style={{
        padding: '1rem',
        borderTop: '1px solid #ccc',
        backgroundColor: '#f9f9f9'
      }}>
        <PositionsTable />
      </footer>
    </div>
  );
};

export default MainLayout;