# CLAUDE.md

Global guidance for Claude Code. See `backend/CLAUDE.md` and `frontend_vanilla/CLAUDE.md` for specific guidance.

## Project Overview

OrderFox - Cryptocurrency trading application with bot management, real-time market data, and trading capabilities.

**Tech Stack:**
- Frontend: Vanilla JavaScript, Vite, DaisyUI v5, TradingView Lightweight Charts v5
- Backend: FastAPI, Python, WebSocket, PostgreSQL (SQLModel ORM)
- Trading: Binance API via ccxt
- Real-time: WebSocket for live market data

## Quick Start

```bash
# From root directory (/home/bail/github/orderfox)
npm run dev          # Smart server management (manual use)
npm run dev:bg       # Claude Code: Start servers in background
npm run dev:wait     # Wait for servers to be ready
npm run dev:status   # Check server status
```

**Server Behavior:**
- Auto-reload on file changes
- Persist between sessions
- Smart detection prevents duplicate starts

## Essential Commands

```bash
# Development
npm run dev:bg && npm run dev:wait    # Start development
npm run lint                           # Frontend ESLint
npm run typecheck                      # Backend type checking

# Type Checking (Critical)
cd backend && pyright app/             # Exact Pylance validation

# Testing
cd backend && ./scripts/run-backend-tests.sh              # Backend tests
cd frontend_vanilla && ./run-tests-minimal.sh complete    # E2E tests

# Dependencies
cd backend && pip install -r requirements.txt
cd frontend_vanilla && npm install
```

## Project Structure

```
orderfox/
├── backend/                # FastAPI backend
│   ├── app/
│   │   ├── api/           # Endpoints
│   │   ├── services/      # Business logic
│   │   ├── models/        # SQLModel schemas
│   │   └── core/          # Config, database
│   └── tests/
├── frontend_vanilla/       # Vanilla JS frontend
│   ├── src/
│   │   ├── components/    # UI components
│   │   ├── services/      # API/WebSocket
│   │   └── store/         # State management
│   └── tests/
└── scripts/               # Development scripts
```

## Architecture Principles

- **Thin Client**: All logic in backend, frontend only displays
- **Bot Context**: Trading data contextualized to selected bot
- **WebSocket First**: Real-time data via WebSocket connections
- **Backend Coordination**: Backend handles all timing and sequencing
- **Type Safety**: All Python must pass pyright, all JS must pass ESLint

## Environment Variables

Create `.env` in root:
```bash
# Database
DATABASE_URL=postgresql://orderfox_user:orderfox_password@localhost:5432/orderfox_db

# Backend
BACKEND_PORT=8000
BACKEND_URL=http://localhost:8000
BINANCE_WS_BASE_URL=wss://fstream.binance.com

# Frontend  
FRONTEND_PORT=3000
VITE_APP_API_BASE_URL=http://localhost:8000/api/v1
VITE_APP_WS_BASE_URL=ws://localhost:8000/api/v1

# Optional
BINANCE_API_KEY=your_key
BINANCE_SECRET_KEY=your_secret
```

## Key Development Rules

1. **Always use absolute paths**: `/home/bail/github/orderfox/`
2. **Check servers before starting**: Use `npm run dev:status`
3. **Type check before committing**: Run pyright and ESLint
4. **Never bypass service layers**: Use Symbol Service for symbols
5. **Trust backend data**: Frontend doesn't validate or transform

See component-specific CLAUDE.md files for detailed patterns.