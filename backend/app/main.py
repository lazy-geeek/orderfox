import logging
import json
from fastapi import FastAPI, Request, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import ValidationError
from app.api.v1.endpoints.market_data_http import router as market_data_http_router
from app.api.v1.endpoints.market_data_ws import router as market_data_ws_router
from app.api.v1.endpoints import trading as trading_router
from app.core.logging_config import (
    setup_logging,
    configure_external_loggers,
    get_logger,
)
from app.core.config import settings

# Setup logging
setup_logging("DEBUG" if settings.DEBUG else "INFO")
configure_external_loggers()
logger = get_logger("main")

# Create FastAPI app instance
app = FastAPI(title="Trading Bot API", version="1.0.0")


# Global Exception Handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle FastAPI HTTPException."""
    logger.error(
        f"HTTP Exception: {exc.status_code} - {exc.detail} - Path: {request.url.path}"
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "status_code": exc.status_code},
    )


@app.exception_handler(StarletteHTTPException)
async def starlette_http_exception_handler(
    request: Request, exc: StarletteHTTPException
):
    """Handle Starlette HTTPException."""
    logger.error(
        f"Starlette HTTP Exception: {exc.status_code} - {exc.detail} - Path: {request.url.path}"
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "status_code": exc.status_code},
    )


@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    """Handle Pydantic ValidationError."""
    logger.error(f"Validation Error: {exc.errors()} - Path: {request.url.path}")
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Validation error",
            "status_code": 422,
            "errors": exc.errors(),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle all other unhandled exceptions."""
    logger.error(
        f"Unhandled Exception: {type(exc).__name__}: {str(exc)} - Path: {request.url.path}",
        exc_info=True,
    )
    return JSONResponse(
        status_code=500, content={"detail": "Internal server error", "status_code": 500}
    )


# Application Events
@app.on_event("startup")
async def startup_event():
    """Application startup event."""
    logger.info("Trading Bot API starting up...")
    logger.info(f"Debug mode: {settings.DEBUG}")
    logger.info("Application startup completed")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event."""
    logger.info("Trading Bot API shutting down...")
    logger.info("Application shutdown completed")


# Request logging middleware (excludes WebSocket connections)
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log incoming HTTP requests (excludes WebSocket connections)."""
    # Skip logging for WebSocket upgrade requests
    if request.headers.get("upgrade") == "websocket":
        return await call_next(request)

    logger.info(f"Incoming request: {request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(
        f"Request completed: {request.method} {request.url.path} - Status: {response.status_code}"
    )
    return response


# Add CORS middleware (allow all for development initially)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# Include API routers
app.include_router(market_data_http_router, prefix="/api/v1", tags=["market-data-http"])
app.include_router(market_data_ws_router, prefix="/api/v1", tags=["market-data-ws"])
app.include_router(trading_router.router, prefix="/api/v1", tags=["trading"])


# Test WebSocket endpoint for debugging
@app.websocket("/api/v1/ws/test")
async def websocket_test(websocket: WebSocket):
    """Test WebSocket endpoint for debugging connection issues."""
    logger.info(f"WebSocket test connection attempt from {websocket.client}")
    try:
        await websocket.accept()
        logger.info(f"WebSocket test connection established with {websocket.client}")

        # Send welcome message
        await websocket.send_text(
            json.dumps(
                {
                    "type": "connection_test",
                    "status": "success",
                    "message": "WebSocket connection established successfully",
                }
            )
        )

        # Keep connection alive and echo messages
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                logger.info(f"WebSocket test received: {message}")

                # Echo the message back
                await websocket.send_text(
                    json.dumps(
                        {"type": "echo", "original": message, "timestamp": "test"}
                    )
                )
            except json.JSONDecodeError:
                await websocket.send_text(
                    json.dumps({"type": "error", "message": "Invalid JSON received"})
                )

    except WebSocketDisconnect:
        logger.info(f"WebSocket test disconnected: {websocket.client}")
    except Exception as e:
        logger.error(f"WebSocket test error: {str(e)}", exc_info=True)
        try:
            await websocket.close(code=1011, reason=f"Server error: {str(e)}")
        except Exception:
            pass


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint that returns a welcome message."""
    return {"message": "Trading Bot API"}
