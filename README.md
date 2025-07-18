# OrderFox Trading Bot

A full-stack cryptocurrency trading application with bot management capabilities, featuring vanilla JavaScript frontend and FastAPI backend with PostgreSQL database, TradingView Lightweight Charts, and comprehensive bot trading system.

## Prerequisites

Before setting up the project, ensure you have the following installed:

- **Python 3.8+** - Required for the backend FastAPI application
- **Node.js 16+** - Required for the frontend vanilla JavaScript application
- **npm** - Comes with Node.js, used for frontend package management
- **pip** - Python package manager (usually comes with Python)
- **PostgreSQL 12+** - Required for bot management database
- **Docker** (optional) - For containerized deployment

## Project Structure

```
orderfox/
├── backend/                     # FastAPI backend
│   ├── app/
│   │   ├── main.py             # FastAPI entry point
│   │   ├── api/                # API endpoints
│   │   ├── services/           # Business logic
│   │   ├── models/             # SQLModel database models
│   │   └── core/               # Config, logging, database
│   └── tests/                  # Pytest test suite
├── frontend_vanilla/            # Vanilla JS frontend
│   ├── src/
│   │   ├── components/         # UI components (DaisyUI)
│   │   ├── services/           # API & WebSocket services
│   │   ├── config/             # Configuration
│   │   └── store/              # State management
│   ├── tests/                  # Vitest & Playwright tests
│   └── main.js                 # App entry point
├── docker-compose.yml          # Docker development setup
├── .env.example               # Environment configuration template
└── scripts/                   # Development scripts
```

## Configuration

### 1. Copy the example environment file:
```bash
cp .env.example .env
```

### 2. Database Setup

The application uses PostgreSQL for bot management. You have two options:

#### Option A: Docker (Recommended)
```bash
docker-compose up -d postgres postgres-test
```

#### Option B: Local PostgreSQL
Install PostgreSQL locally and create databases:
```sql
CREATE DATABASE orderfox_db;
CREATE USER orderfox_user WITH PASSWORD 'orderfox_password';
GRANT ALL PRIVILEGES ON DATABASE orderfox_db TO orderfox_user;

-- For testing
CREATE DATABASE orderfox_test_db;
CREATE USER orderfox_test_user WITH PASSWORD 'orderfox_test_password';
GRANT ALL PRIVILEGES ON DATABASE orderfox_test_db TO orderfox_test_user;
```

### 3. Environment Variables

Key environment variables (see `.env.example` for complete list):

- **`DATABASE_URL`**: PostgreSQL connection string
- **`BINANCE_API_KEY`**: Your API key for the Binance exchange
- **`BINANCE_SECRET_KEY`**: Your secret key for the Binance exchange
- **`LIQUIDATION_API_BASE_URL`**: Optional external API for liquidation data
- **`VITE_APP_API_BASE_URL`**: Frontend API endpoint (default: http://localhost:8000/api/v1)

**Important:** The `.env` file contains sensitive information and should not be committed to version control.

## Getting Started

### Quick Start (Recommended)

Use the smart server management system:

```bash
# Start both frontend and backend servers
npm run dev

# For background operation (Claude Code)
npm run dev:bg
npm run dev:wait
```

### Manual Setup

#### Backend Setup

1. **Create and activate a Python virtual environment** (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Install Python dependencies:**
```bash
cd backend
pip install -r requirements.txt
```

3. **Run the FastAPI server:**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend Setup

1. **Install Node.js dependencies:**
```bash
cd frontend_vanilla
npm install
```

2. **Start the Vite development server:**
```bash
npm run dev
```

### Docker Development

For a complete containerized setup:

```bash
docker-compose up --build
```

## Running the Application

### Access URLs
- **Frontend Application:** http://localhost:3000
- **Backend API:** http://localhost:8000
- **API Documentation:** http://localhost:8000/docs (Swagger UI)
- **Database:** PostgreSQL on localhost:5432 (dev) and localhost:5433 (test)

## Usage

### Bot Management System

1. **Create Trading Bots:**
   - Use the "New Bot" button to create trading bots
   - Configure bot name, trading symbol, and initial status
   - Each bot can trade a specific cryptocurrency pair

2. **Bot Operations:**
   - **Edit Bot:** Modify bot configuration (name, symbol)
   - **Toggle Status:** Start/stop bot trading
   - **Delete Bot:** Remove bot from system
   - **Select Bot:** Choose active bot for trading interface

3. **Trading Interface:**
   - **Professional Charts:** TradingView Lightweight Charts with multiple timeframes
   - **Real-time Data:** Live market data via WebSocket connections
   - **Order Book:** Current bid/ask prices and market depth
   - **Trade History:** Recent trades with buy/sell indicators
   - **Liquidation Data:** Real-time liquidation events and volume

### Key Features in Use

- **Bot Context:** All trading data is contextualized to the selected bot
- **Real-time Updates:** Market data updates automatically without page refresh
- **Responsive Design:** Works on desktop, tablet, and mobile devices
- **State Persistence:** Bot configurations and selections persist across sessions
- **Error Handling:** Graceful error handling with user-friendly messages

## Features

### Frontend Features
- **Bot Management UI:** Create, edit, delete, and manage trading bots
- **Professional Chart Visualization:** TradingView Lightweight Charts
- **Real-time Market Data:** Live updates via WebSocket connections
- **Order Book Display:** Real-time bid/ask prices with market depth
- **Trade History:** Live trade feed with buy/sell indicators  
- **Liquidation Monitoring:** Real-time liquidation events and volume
- **Responsive Design:** DaisyUI components with mobile-first approach
- **Dark/Light Mode:** Theme switching with smooth transitions

### Backend Features
- **Bot Management API:** Full CRUD operations for trading bots
- **PostgreSQL Database:** Persistent bot storage with SQLModel
- **WebSocket Streaming:** Real-time market data delivery
- **Symbol Service:** Centralized symbol management with caching
- **Exchange Integration:** Binance API with ccxt and ccxt pro
- **Data Aggregation:** Server-side processing and formatting
- **Connection Management:** Efficient WebSocket connection handling

## Testing

### Backend Tests
```bash
cd backend
python -m pytest tests/ -v
```

### Frontend Tests
```bash
cd frontend_vanilla

# Unit tests (Vitest)
npm test
npm run test:run

# End-to-end tests (Playwright)
npm run test:e2e
npm run test:e2e:ui
```

### Test Coverage
- **Backend:** 98% test coverage with pytest
- **Frontend:** 100% test coverage with Vitest
- **E2E Tests:** Comprehensive Playwright browser tests
- **Integration Tests:** WebSocket and API integration testing

## Development

### Technology Stack

**Frontend:**
- **Framework:** Vanilla JavaScript with Vite
- **UI Components:** DaisyUI v5 with TailwindCSS v4
- **Charts:** TradingView Lightweight Charts
- **State Management:** Custom subscribe/notify pattern
- **Testing:** Vitest for unit tests, Playwright for E2E
- **Build Tool:** Vite with hot module replacement

**Backend:**
- **Framework:** FastAPI with Python 3.8+
- **Database:** PostgreSQL with SQLModel ORM
- **WebSocket:** Real-time data streaming
- **Testing:** pytest with async support
- **API Integration:** Binance API via ccxt/ccxt pro
- **Data Processing:** Pandas for aggregation

### Architecture

**Frontend Architecture:**
- **Thin Client:** All business logic handled by backend
- **Component-based:** Modular UI components with shared base classes
- **State Management:** Lightweight subscribe/notify pattern
- **WebSocket Manager:** Centralized connection management
- **Bot Context:** All trading data contextualized to selected bot

**Backend Architecture:**
- **Service Layer:** Clean separation of business logic
- **Repository Pattern:** Database operations abstracted
- **WebSocket Streams:** Real-time data delivery
- **Caching Layer:** Performance optimization for market data
- **Error Handling:** Comprehensive exception handling

### Development Workflow

1. **Server Management:**
   ```bash
   npm run dev:status    # Check server status
   npm run dev:restart   # Restart with fresh logs
   npm run dev:stop      # Stop all servers
   ```

2. **Code Quality:**
   ```bash
   npm run lint          # Frontend linting
   npm run lint:fix      # Auto-fix linting issues
   cd backend && python -m pylint app/  # Backend linting
   ```

3. **Testing:**
   ```bash
   npm run test:run      # Frontend unit tests
   npm run test:e2e      # E2E browser tests
   cd backend && python -m pytest tests/ -v  # Backend tests
   ```

## Database Schema

### Bot Model
```sql
CREATE TABLE bots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

## API Endpoints

### Bot Management
- `GET /api/v1/bots` - List all bots
- `POST /api/v1/bots` - Create new bot
- `GET /api/v1/bots/{bot_id}` - Get bot details
- `PUT /api/v1/bots/{bot_id}` - Update bot
- `DELETE /api/v1/bots/{bot_id}` - Delete bot
- `PATCH /api/v1/bots/{bot_id}/toggle` - Toggle bot status

### Market Data
- `GET /api/v1/symbols` - List available symbols
- `ws://localhost:8000/api/v1/ws/candles/{symbol}` - Chart data stream
- `ws://localhost:8000/api/v1/ws/trades/{symbol}` - Trades stream
- `ws://localhost:8000/api/v1/ws/orderbook` - Order book stream
- `ws://localhost:8000/api/v1/ws/liquidations/{symbol}` - Liquidations stream

## Deployment

### Docker Deployment
```bash
# Build and start all services
docker-compose up --build

# Production deployment
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Manual Deployment
1. Set up PostgreSQL database
2. Configure environment variables
3. Install dependencies
4. Run production builds
5. Start services with process manager

## Contributing

1. Fork the repository
2. Create a feature branch
3. Write tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

MIT License - see LICENSE file for details.