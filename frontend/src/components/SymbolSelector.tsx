import React, { useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { RootState, AppDispatch } from '../store/store';
import { fetchSymbols, changeSelectedSymbol } from '../features/marketData/marketDataSlice';

interface SymbolSelectorProps {
  className?: string;
}

const SymbolSelector: React.FC<SymbolSelectorProps> = ({ className }) => {
  const dispatch = useDispatch<AppDispatch>();
  const {
    symbolsList,
    selectedSymbol,
    symbolsLoading,
    symbolsError
  } = useSelector((state: RootState) => state.marketData);

  useEffect(() => {
    // Fetch symbols on component mount
    dispatch(fetchSymbols());
  }, [dispatch]);

  const handleSymbolChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    const selectedValue = event.target.value;
    
    // Use the new centralized symbol change function that handles WebSocket cleanup
    dispatch(changeSelectedSymbol(selectedValue || null));
    
    // Log the selected symbol to console as requested
    const selectedSymbolData = symbolsList.find(symbol => symbol.id === selectedValue);
    console.log('Selected symbol:', selectedSymbolData);
  };

  if (symbolsLoading) {
    return (
      <div className={className}>
        <select disabled>
          <option>Loading symbols...</option>
        </select>
      </div>
    );
  }

  if (symbolsError) {
    return (
      <div className={className}>
        <select disabled>
          <option>Error fetching symbols</option>
        </select>
        <div style={{ color: 'red', fontSize: '0.875rem', marginTop: '0.25rem' }}>
          {symbolsError}
        </div>
      </div>
    );
  }

  return (
    <div className={className}>
      <select
        value={selectedSymbol || ''}
        onChange={handleSymbolChange}
        style={{
          padding: '0.5rem',
          borderRadius: '0.25rem',
          border: '1px solid #ccc',
          minWidth: '200px'
        }}
      >
        <option value="">Select a symbol...</option>
        {symbolsList.map((symbol) => (
          <option key={symbol.id} value={symbol.id}>
            {symbol.uiName}
            {typeof symbol.volume24h === 'number' && symbol.volume24h > 0 ?
              ` (${(symbol.volume24h / 1000000).toFixed(2)}M)` :
              ''}
          </option>
        ))}
      </select>
    </div>
  );
};

export default SymbolSelector;