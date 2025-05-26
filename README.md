# OrderFox Trading Bot

A full-stack trading application with React TypeScript frontend and FastAPI backend for cryptocurrency trading.

## Prerequisites

Before setting up the project, ensure you have the following installed:

- **Python 3.8+** - Required for the backend FastAPI application
- **Node.js 16+** - Required for the frontend React application
- **npm** - Comes with Node.js, used for frontend package management
- **pip** - Python package manager (usually comes with Python)

## Project Structure

- `frontend/` - React TypeScript application with Redux state management
- `backend/` - FastAPI Python backend with WebSocket support
- `.env.example` - Example environment configuration file
- `backend/tests/` - Backend unit tests using pytest
- `frontend/src/` - Frontend source code with components and features

## Configuration

Before running the application, you need to set up your environment variables:

### 1. Copy the example environment file:
```bash
cp .env.example .env
```

### 2. Open the newly created `.env` file and fill in your actual credentials and configuration values.

### Environment Variables

- **`BINANCE_API_KEY`**: Your API key for the Binance exchange. You can obtain this from your Binance account settings under API Management.

- **`BINANCE_SECRET_KEY`**: Your secret key for the Binance exchange. This is provided when you create your API key.

- **`FIREBASE_CONFIG_JSON`**: Path to your Firebase service account JSON file. This is optional and only needed if you want to use Firebase features. You can obtain this from your Firebase project settings under Service Accounts.

- **`REACT_APP_API_BASE_URL`**: The base URL for API calls from the frontend to the backend API (default: http://localhost:8000/api/v1).

- **`DEFAULT_TRADING_MODE`**: The default trading mode for the application (default: paper). Options are "paper" for paper trading or "live" for live trading.

**Important:** The `.env` file contains sensitive information and should not be committed to version control. It is included in `.gitignore` by default.

## Getting Started

### Backend Setup

1. **Create and activate a Python virtual environment** (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Navigate to the backend directory:**
```bash
cd backend
```

3. **Install Python dependencies:**
```bash
pip install -r requirements.txt
```

4. **Run the FastAPI server:**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup

1. **Navigate to the frontend directory:**
```bash
cd frontend
```

2. **Install Node.js dependencies:**
```bash
npm install
```

3. **Start the React development server:**
```bash
npm start
```

## Running the Application

### Starting the Backend
Navigate to the `backend` directory and run:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Starting the Frontend
Navigate to the `frontend` directory and run:
```bash
npm start
```

### Access URLs
- **Frontend Application:** http://localhost:3000 (or your configured port)
- **Backend API:** http://localhost:8000
- **API Documentation:** http://localhost:8000/docs (Swagger UI)

## Usage

### Basic Application Flow

1. **Select a Trading Symbol:** Use the symbol selector to choose a cryptocurrency trading pair (e.g., BTCUSDT, ETHUSDT).

2. **View Market Data:**
   - Monitor real-time candlestick charts showing price movements
   - Observe the order book with current bid/ask prices and volumes
   - All data updates automatically via WebSocket connections

3. **Paper Trading:**
   - The application starts in paper trading mode by default for safe testing
   - Use the manual trading form to simulate buy/sell orders
   - Monitor your positions in the positions table
   - All trades are simulated with virtual funds

4. **Trading Interface:**
   - **Manual Trade Form:** Enter order details (symbol, side, quantity, price)
   - **Order Book Display:** View current market depth and liquidity
   - **Positions Table:** Track your current holdings and P&L
   - **Trading Mode Toggle:** Switch between paper and live trading (when configured)

### Key Features in Use

- **Real-time Data:** Market data updates automatically without page refresh
- **Paper Trading:** Test strategies safely with simulated funds
- **Order Management:** Place and track trading orders
- **Portfolio Tracking:** Monitor positions and performance
- **Responsive Design:** Works on desktop and mobile devices

## Features

- **Real-time Market Data:** Live candlestick charts and order book updates via WebSocket
- **Manual Trading Interface:** Intuitive form for placing buy/sell orders
- **Order Book Display:** Real-time bid/ask prices with market depth visualization
- **Position Management:** Track holdings, P&L, and portfolio performance
- **Paper Trading Mode:** Safe testing environment with simulated funds
- **Trading Mode Toggle:** Switch between paper and live trading
- **Responsive Design:** Works seamlessly on desktop and mobile devices
- **API Documentation:** Auto-generated Swagger UI for backend endpoints

## Testing

### Backend Tests
Run the backend test suite:
```bash
cd backend
python -m pytest tests/ -v
```

### Frontend Tests
Run the frontend test suite:
```bash
cd frontend
npm test
```

### Paper Trading Test
A comprehensive paper trading test is available:
```bash
python test_paper_trading.py
```

## Development

### Technology Stack
- **Frontend:** React 18 with TypeScript, Redux Toolkit for state management, CSS3 for styling
- **Backend:** FastAPI with Python 3.8+, WebSocket support for real-time data, Pydantic for data validation
- **Testing:** Jest and React Testing Library for frontend, pytest for backend
- **API Integration:** Binance API for market data and trading operations
- **Real-time Communication:** WebSocket connections for live market data updates

### Architecture
- **Frontend:** Component-based React architecture with Redux for global state
- **Backend:** RESTful API with WebSocket endpoints, service layer pattern
- **Data Flow:** Real-time market data via WebSocket, trading operations via REST API
- **State Management:** Redux slices for market data and trading state