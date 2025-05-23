import React, { useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { RootState, AppDispatch } from '../store/store';
import { fetchSymbols, setSelectedSymbol } from '../features/marketData/marketDataSlice';

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
    
    // Dispatch action to update selected symbol in Redux state
    dispatch(setSelectedSymbol(selectedValue));
    
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
            {symbol.symbol}
          </option>
        ))}
      </select>
    </div>
  );
};

export default SymbolSelector;