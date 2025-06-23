# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

OrderFox is a full-stack cryptocurrency trading application with:
- **Frontend**: React 18 + TypeScript + Redux Toolkit
- **Backend**: FastAPI + Python with WebSocket support
- **Trading**: Binance API integration with paper trading mode
- **Real-time**: WebSocket connections for live market data

## Development Commands

### Backend (FastAPI)
```bash
# Run backend server
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run backend tests
cd backend
python -m pytest tests/ -v

# Install dependencies
cd backend
pip install -r requirements.txt
```

### Frontend (React)
```bash
# Run frontend server
cd frontend
npm start

# Run frontend tests
cd frontend
npm test

# Build for production
cd frontend
npm run build

# Run both frontend and backend concurrently
cd frontend
npm run dev

# Install dependencies
cd frontend
npm install
```

### Full Application Testing
```bash
# Run comprehensive paper trading test
python test_paper_trading.py
```

## Architecture

### Backend Structure
- **app/main.py**: FastAPI application entry point with CORS, exception handling, and startup/shutdown events
- **app/core/**: Core functionality (config, database, logging)
- **app/api/v1/endpoints/**: API endpoints for market data (HTTP/WebSocket) and trading
- **app/services/**: Business logic services (exchange, symbol, trading engine)
- **backend/tests/**: Backend unit tests using pytest

### Frontend Structure
- **src/store/**: Redux store configuration with listener middleware for symbol/timeframe changes
- **src/features/**: Redux slices for market data and trading state management
- **src/components/**: React components (Chart, OrderBook, ManualTrade, Positions, etc.)
- **src/services/**: API client and WebSocket service for backend communication
- **src/utils/**: Utilities for formatting and data processing

### Key Technical Details
- **State Management**: Redux Toolkit with listener middleware that automatically manages WebSocket connections when symbols/timeframes change
- **Real-time Data**: WebSocket connections for order book and candlestick data that auto-reconnect on symbol changes
- **API Integration**: Binance API through ccxt library with paper trading mode support
- **Error Handling**: Comprehensive exception handling in FastAPI with proper logging
- **Environment**: Configuration through .env files with automatic path detection

### Configuration
- Environment variables loaded from .env file (multiple path detection)
- Required: BINANCE_API_KEY, BINANCE_SECRET_KEY
- Optional: FIREBASE_CONFIG_JSON, DEBUG, MAX_ORDERBOOK_LIMIT
- Trading mode defaults to paper trading for safety

### Testing Strategy
- Backend: pytest with test coverage for all endpoints and services
- Frontend: Jest + React Testing Library for component and service tests
- Integration: Comprehensive paper trading test that validates full application flow