# CLAUDE.md

This file provides guidance to Claude Code when working with the OrderFox codebase.

## Project Overview

OrderFox is a cryptocurrency trading application with real-time market data and paper trading capabilities.

**Tech Stack:**
- Frontend: Vanilla JavaScript with Vite and TradingView Lightweight Charts
- Backend: FastAPI + Python with WebSocket support
- Trading: Binance API integration via ccxt
- Real-time: WebSocket connections for live market data
- Charts: TradingView Lightweight Charts for professional candlestick visualization

## Quick Start

```bash
# Run both frontend and backend (from root)
npm run dev

# Or run separately:
# Backend
cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend
cd frontend_vanilla && npm run dev

# With Docker
docker-compose up --build
```

## Project Structure

```
orderfox/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── api/v1/endpoints/    # API endpoints
│   │   ├── services/            # Business logic
│   │   ├── models/              # Data models
│   │   └── core/                # Config, logging
│   └── tests/                   # Pytest test suite
└── frontend_vanilla/
    ├── src/
    │   ├── components/          # UI components
    │   ├── services/            # API & WebSocket
    │   └── store/               # State management
    └── main.js                  # App entry point
```

## Key Commands

### Development
```bash
# Install dependencies
cd backend && pip install -r requirements.txt
cd frontend_vanilla && npm install

# Run tests
cd backend && python -m pytest tests/ -v

# Full application test
python test_paper_trading.py
```

### Docker Development
```bash
docker-compose up --build    # Build and run
docker-compose logs -f       # View logs
docker-compose down          # Stop containers
```

## Configuration

Create `.env` file in root:
```
BINANCE_API_KEY=your_key
BINANCE_SECRET_KEY=your_secret
```

Optional settings:
- `MAX_ORDERBOOK_LIMIT`: Max order book depth (default: 50)
- `DEBUG`: Enable debug logging (true/false)
- `CORS_ORIGINS`: Allowed CORS origins

## Architecture Highlights

### Order Book System
- **Backend Aggregation**: All order book processing happens server-side
- **WebSocket Updates**: Real-time data with dynamic parameter updates
- **Caching**: TTL-based caching for performance (10x improvement)
- **Pre-formatted Data**: Backend sends formatted strings to frontend

### WebSocket Protocol

Connect to order book:
```
ws://localhost:8000/api/v1/ws/orderbook?symbol=BTCUSDT&limit=20&rounding=0.25
```

Update parameters without reconnecting:
```json
{
  "type": "update_params",
  "limit": 50,
  "rounding": 0.5
}
```

### State Management
- Frontend uses custom subscribe/notify pattern
- WebSocket service handles automatic reconnection
- Backend manages all data aggregation and formatting

## Common Tasks

### Adding a New API Endpoint
1. Create endpoint in `backend/app/api/v1/endpoints/`
2. Add to router in `backend/app/api/v1/api.py`
3. Create service logic in `backend/app/services/`
4. Add tests in `backend/tests/`

### Modifying Order Book Display
1. Backend: Update aggregation in `orderbook_aggregation_service.py`
2. Backend: Adjust formatting in `formatting_service.py`
3. Frontend: Update display in `OrderBookDisplay.js`

### Modifying Chart Display
1. Backend: Update chart data processing in `chart_data_service.py`
2. Backend: Adjust WebSocket data streaming in `market_data_ws.py`
3. Frontend: Update chart component in `LightweightChart.js`
4. Note: Uses TradingView Lightweight Charts API, not ECharts

### Chart Performance & UX Features
- **Zoom Preservation**: User zoom/pan state is preserved during real-time updates
- **Viewport-Based Data Loading**: Automatically calculates optimal candle count based on chart size
- **Efficient Real-time Updates**: Uses `series.update()` for single candle updates to maintain performance
- **Smart Auto-fitting**: Only calls `fitContent()` on initial load or symbol/timeframe changes

### Working with WebSockets
- Connection management: `connection_manager.py`
- Frontend WebSocket service: `websocketService.js`
- Dynamic updates supported without reconnection

## Testing

```bash
# Backend unit tests
cd backend && python -m pytest tests/ -v

# Specific test file
python -m pytest tests/services/test_orderbook_aggregation_service.py -v

# Chart data service tests
python -m pytest tests/services/test_chart_data_service.py -v

# Integration tests
python -m pytest tests/integration/ -v

# Performance tests
python -m pytest tests/load/ -v
```

## Important Notes

### Frontend URLs
- Always use relative URLs (`/api/v1`) in development
- Vite proxy handles routing to backend
- WebSocket URLs also use relative paths

### Order Book Limitations
- Binance API limits: max 5000 entries
- Limited price range for high rounding values
- This is a market limitation, not a bug

### Development Tips
- Backend and frontend auto-restart on file changes
- Check logs for WebSocket connection issues
- Use browser DevTools for WebSocket debugging
- Symbol info cached for 5 minutes

## Error Handling

- Backend: Comprehensive exception handling in FastAPI
- Frontend: WebSocket auto-reconnection on disconnect
- Logging: Structured logs with request timing
- Health check: GET /health endpoint

## VS Code Dev Container

```bash
# Open in Dev Container
1. Install "Dev Containers" extension
2. Ctrl+Shift+P → "Dev Containers: Reopen in Container"
3. Services start automatically
```

Container uses `/workspaces/orderfox` as working directory.

## Project specific rules

See @CLAUDE-RULES.md for detailed rules for this project.