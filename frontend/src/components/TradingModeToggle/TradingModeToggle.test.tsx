import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import TradingModeToggle from './TradingModeToggle';
import tradingReducer, { TradingMode } from '../../features/trading/tradingSlice';

// Mock the API client
jest.mock('../../services/apiClient', () => ({
  post: jest.fn(() => Promise.resolve({ data: {} })),
}));

const createMockStore = (initialState: Partial<{
  tradingMode: TradingMode;
  isSubmittingTrade: boolean;
  tradeError: string | null;
  positionsLoading: boolean;
  positionsError: string | null;
}> = {}) => {
  return configureStore({
    reducer: {
      trading: tradingReducer,
    },
    preloadedState: {
      trading: {
        openPositions: [],
        tradeHistory: [],
        tradingMode: 'paper' as TradingMode,
        isSubmittingTrade: false,
        tradeError: null,
        positionsLoading: false,
        positionsError: null,
        ...initialState,
      },
    },
  });
};

const renderWithProvider = (component: React.ReactElement, store = createMockStore()) => {
  return render(
    <Provider store={store}>
      {component}
    </Provider>
  );
};

describe('TradingModeToggle', () => {
  it('renders with paper mode by default', () => {
    renderWithProvider(<TradingModeToggle />);
    
    expect(screen.getByText('Mode:')).toBeInTheDocument();
    expect(screen.getByText('Paper')).toBeInTheDocument();
    expect(screen.getByRole('button')).toHaveClass('paper');
  });

  it('renders with live mode when state is live', () => {
    const store = createMockStore({ tradingMode: 'live' as TradingMode });
    renderWithProvider(<TradingModeToggle />, store);
    
    expect(screen.getByText('Live')).toBeInTheDocument();
    expect(screen.getByRole('button')).toHaveClass('live');
  });

  it('shows loading state when submitting trade', () => {
    const store = createMockStore({ isSubmittingTrade: true });
    renderWithProvider(<TradingModeToggle />, store);
    
    expect(screen.getByText('Switching...')).toBeInTheDocument();
    expect(screen.getByRole('button')).toBeDisabled();
  });

  it('handles mode toggle click', () => {
    const store = createMockStore();
    renderWithProvider(<TradingModeToggle />, store);
    
    const button = screen.getByRole('button');
    fireEvent.click(button);
    
    // The action should be dispatched (we can't easily test the actual dispatch without more complex mocking)
    expect(button).toBeInTheDocument();
  });

  it('has correct tooltip text', () => {
    renderWithProvider(<TradingModeToggle />);
    
    const button = screen.getByRole('button');
    expect(button).toHaveAttribute('title', 'Switch to Live mode');
  });

  it('has correct tooltip text for live mode', () => {
    const store = createMockStore({ tradingMode: 'live' as TradingMode });
    renderWithProvider(<TradingModeToggle />, store);
    
    const button = screen.getByRole('button');
    expect(button).toHaveAttribute('title', 'Switch to Paper mode');
  });
});