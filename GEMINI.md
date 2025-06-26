# OrderFox Repository Structure and Architectural Design

This document outlines the structure and architectural design of the OrderFox project, a real-time cryptocurrency trading application.

## Project Overview

OrderFox is a full-stack application with a React frontend and a Python (FastAPI) backend. It provides real-time market data visualization, including candlestick charts and order books, and supports both paper and live trading.

## High-Level Architecture

The application is divided into two main components:

1.  **Frontend**: A single-page application (SPA) built with React, TypeScript, and Redux for state management. It communicates with the backend via HTTP and WebSockets.
2.  **Backend**: A Python-based API built with FastAPI. It handles business logic, data fetching from the exchange (Binance), and real-time data streaming.

## Backend Architecture

The backend follows a layered architecture to separate concerns and improve maintainability.

### Core Components

*   **`main.py`**: The entry point of the FastAPI application. It initializes the app, sets up middleware (CORS, logging), and includes the API routers.
*   **`api/`**: Contains the API endpoints, organized by version (v1).
    *   **`endpoints/`**: Defines the HTTP and WebSocket endpoints.
        *   `market_data_http.py`: Endpoints for fetching historical market data (symbols, order books, candles).
        *   `market_data_ws.py`: WebSocket endpoints for real-time data streaming (order book, ticker, candles).
        *   `trading.py`: Endpoints for executing trades and managing positions.
        *   `connection_manager.py`: Manages WebSocket connections and subscriptions.
    *   **`schemas.py`**: Pydantic models for data validation and serialization.
*   **`core/`**: Core application components.
    *   `config.py`: Manages application settings and environment variables.
    *   `logging_config.py`: Configures logging for the application.
*   **`services/`**: Contains the business logic of the application.
    *   `exchange_service.py`: A service that abstracts the interaction with the `ccxt` library to connect to the Binance exchange. It handles both REST and WebSocket connections.
    *   `symbol_service.py`: Manages trading symbols, including caching and format conversion.
    *   `trading_engine_service.py`: The core of the trading logic. It handles order execution, position management, and trading signals. It supports both paper and live trading modes.

### Key Libraries

*   **FastAPI**: For building the high-performance API.
*   **`ccxt` / `ccxt.pro`**: For interacting with the Binance exchange for both REST and WebSocket data.
*   **Pydantic**: For data validation and settings management.
*   **`uvicorn`**: As the ASGI server to run the application.

## Frontend Architecture

The frontend is built using React and follows a component-based architecture. Redux is used for centralized state management, ensuring a predictable state container for the application.

### Core Components

*   **`App.tsx`**: The root component of the application.
*   **`index.tsx`**: The entry point of the React application, where the Redux store is provided to the component tree.
*   **`components/`**: Reusable UI components.
    *   `SymbolSelector.tsx`: A dropdown to select the trading symbol.
    *   `Chart/CandlestickChart.tsx`: Displays the candlestick chart using `echarts-for-react`.
    *   `OrderBook/OrderBookDisplay.tsx`: Shows the real-time order book.
    *   `ManualTrade/ManualTradeForm.tsx`: A form for manually executing trades.
    *   `Positions/PositionsTable.tsx`: Displays open trading positions.
*   **`features/`**: Redux Toolkit slices, which encapsulate the state and logic for different application features.
    *   `marketData/marketDataSlice.ts`: Manages the state for market data, including symbols, order books, and candles. It also handles WebSocket connections for real-time updates.
    *   `trading/tradingSlice.ts`: Manages the state for trading operations, including open positions and trading mode.
*   **`services/`**: Services for interacting with the backend.
    *   `apiClient.ts`: An Axios instance configured for making HTTP requests to the backend.
    *   `websocketService.ts`: Manages WebSocket connections for real-time data streams.
*   **`store/`**: Redux store configuration.
    *   `store.ts`: Configures the Redux store and middleware.

### Key Libraries

*   **React**: For building the user interface.
*   **Redux Toolkit**: For efficient and predictable state management.
*   **Axios**: For making HTTP requests to the backend.
*   **ECharts for React**: For rendering the candlestick chart.
*   **TypeScript**: For static typing, improving code quality and maintainability.

## Communication Flow

1.  **Initial Data Load**: The frontend fetches initial data (e.g., available symbols, historical candles) from the backend via HTTP requests.
2.  **Real-time Updates**: The frontend establishes WebSocket connections to the backend for real-time updates on order books, tickers, and candles.
3.  **Trading Operations**: When a user executes a trade, the frontend sends a request to the backend's trading endpoint. The backend then processes the trade (either paper or live) and returns the result.

## Getting Started

To run the application, you need to have both the frontend and backend servers running.

*   **Backend**: `uvicorn app.main:app --reload`
*   **Frontend**: `npm start`

A convenience script `npm run dev` is available in the frontend's `package.json` to start both servers concurrently.
Use this as prefered method to run the application.
