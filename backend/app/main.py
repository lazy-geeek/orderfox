import json
import time
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException, WebSocket, WebSocketDisconnect
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import ValidationError
from app.api.v1.endpoints.market_data_http import router as market_data_http_router
from app.api.v1.endpoints.market_data_ws import router as market_data_ws_router
from app.api.v1.endpoints.trades_ws import router as trades_ws_router
from app.api.v1.endpoints.liquidations_ws import router as liquidations_ws_router
from app.api.v1.endpoints.liquidation_volume import router as liquidation_volume_router
from app.api.v1.endpoints.bots import router as bots_router
from app.api.v1.endpoints import trading as trading_router
from app.core.logging_config import (
    setup_logging,
    configure_external_loggers,
    get_logger,
)
from app.core.config import settings, DEVCONTAINER_MODE, DEVELOPMENT
from app.core.database import init_db

# Setup logging
setup_logging("DEBUG" if settings.DEBUG else "INFO")
configure_external_loggers()
logger = get_logger("main")

# Configure debugpy for container debugging
if DEVCONTAINER_MODE:
    try:
        import debugpy
        if not debugpy.is_client_connected():
            debugpy.listen(("0.0.0.0", 5678))
            logger.info("Debugpy listening on 0.0.0.0:5678")
    except ImportError:
        logger.warning(
            "debugpy not available - install with: pip install debugpy")
    except Exception as e:
        logger.warning(f"Failed to configure debugpy: {e}")

# Lifespan context manager for startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    # Startup
    logger.info("Trading Bot API starting up...")
    logger.info(f"Debug mode: {settings.DEBUG}")
    logger.info(f"Development mode: {DEVELOPMENT}")
    logger.info(f"Container mode: {DEVCONTAINER_MODE}")
    logger.info(f"Server binding to: {settings.HOST}:{settings.PORT}")

    # Initialize database
    try:
        logger.info("Initializing database...")
        await init_db()
        logger.info("Database initialization completed")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        # Don't fail startup - allow the app to run without database for development
        logger.warning("Application will continue without database initialization")

    # Mount static files in development
    if settings.SERVE_STATIC_FILES:
        static_path = Path(settings.STATIC_FILES_PATH)
        if static_path.exists():
            app.mount(
                "/static",
                StaticFiles(
                    directory=str(static_path)),
                name="static")
            logger.info(f"Serving static files from: {static_path}")
        else:
            logger.warning(f"Static files directory not found: {static_path}")

    logger.info("Application startup completed")
    
    yield  # Application is running
    
    # Shutdown
    logger.info("Trading Bot API shutting down...")
    logger.info("Application shutdown completed")


# Create FastAPI app instance
app = FastAPI(
    title="Trading Bot API",
    version="1.0.0",
    debug=settings.DEBUG,
    docs_url="/docs" if DEVELOPMENT else None,  # Disable docs in production
    redoc_url="/redoc" if DEVELOPMENT else None,  # Disable redoc in production
    lifespan=lifespan
)


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
    logger.error(
        f"Validation Error: {exc.errors()} - Path: {request.url.path}")
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
        f"Unhandled Exception: {
            type(exc).__name__}: {
            str(exc)} - Path: {
                request.url.path}",
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "status_code": 500})


# Development middleware for timing and debugging
class DevelopmentMiddleware(BaseHTTPMiddleware):
    """Development middleware for request timing and debugging."""

    async def dispatch(self, request: Request, call_next):
        if DEVELOPMENT:
            start_time = time.time()
            response = await call_next(request)
            process_time = time.time() - start_time
            response.headers["X-Process-Time"] = str(process_time)

            # Log slow requests
            if process_time > 1.0:  # Log requests taking more than 1 second
                logger.warning(
                    f"Slow request: {
                        request.method} {
                        request.url.path} took {
                        process_time:.2f}s")

            return response
        else:
            return await call_next(request)



# Add development middleware
if DEVELOPMENT:
    app.add_middleware(DevelopmentMiddleware)

# Request logging middleware (excludes WebSocket connections)
if settings.REQUEST_LOGGING:
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        """Log incoming HTTP requests (excludes WebSocket connections)."""
        # Skip logging for WebSocket upgrade requests
        if request.headers.get("upgrade") == "websocket":
            return await call_next(request)

        logger.info(f"Incoming request: {request.method} {request.url.path}")
        response = await call_next(request)
        logger.info(
            f"Request completed: {
                request.method} {
                request.url.path} - Status: {
                response.status_code}")
        return response


# Add CORS middleware with environment-specific configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if DEVELOPMENT else [],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"],
    allow_headers=[
        "Accept",
        "Accept-Language",
        "Content-Language",
        "Content-Type",
        "Authorization",
        "X-Requested-With",
        "X-Process-Time"
    ],
    expose_headers=["X-Process-Time"] if DEVELOPMENT else [],
)

# Include API routers
app.include_router(
    market_data_http_router,
    prefix="/api/v1",
    tags=["market-data-http"])
app.include_router(
    market_data_ws_router,
    prefix="/api/v1",
    tags=["market-data-ws"])
app.include_router(
    trades_ws_router,
    prefix="/api/v1",
    tags=["trades-ws"])
app.include_router(
    liquidations_ws_router,
    prefix="/api/v1",
    tags=["liquidations-ws"])
app.include_router(
    liquidation_volume_router,
    prefix="/api/v1",
    tags=["liquidation-volume"])
app.include_router(bots_router, prefix="/api/v1/bots", tags=["bots"])
app.include_router(trading_router.router, prefix="/api/v1", tags=["trading"])


# Test WebSocket endpoint for debugging
@app.websocket("/api/v1/ws/test")
async def websocket_test(websocket: WebSocket):
    """Test WebSocket endpoint for debugging connection issues."""
    logger.info(f"WebSocket test connection attempt from {websocket.client}")
    try:
        await websocket.accept()
        logger.info(
            f"WebSocket test connection established with {
                websocket.client}")

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

# Health check endpoint


@app.get("/health")
async def health_check():
    """Health check endpoint for container orchestration."""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "service": "trading-bot-api",
        "version": "1.0.0"
    }


# Root endpoint - serve frontend in development
@app.get("/")
async def root():
    """Root endpoint that returns API info or serves frontend."""
    if settings.SERVE_STATIC_FILES:
        # Try to serve frontend index.html
        index_path = Path(settings.STATIC_FILES_PATH) / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path), media_type="text/html")

    return {
        "message": "Trading Bot API",
        "version": "1.0.0",
        "debug": settings.DEBUG,
        "development": DEVELOPMENT,
        "container": DEVCONTAINER_MODE,
        "docs": "/docs" if DEVELOPMENT else "Not available in production"
    }

# Catch-all route for SPA frontend (development only)
if settings.SERVE_STATIC_FILES:
    @app.get("/{path:path}")
    async def serve_spa(path: str):
        """Serve SPA frontend for client-side routing."""
        # Check if it's an API request
        if path.startswith(
                "api/") or path.startswith("docs") or path.startswith("redoc") or path == "health":
            raise HTTPException(status_code=404, detail="Not found")

        # Try to serve the requested file
        file_path = Path(settings.STATIC_FILES_PATH) / path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))

        # Fall back to index.html for SPA routing
        index_path = Path(settings.STATIC_FILES_PATH) / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path), media_type="text/html")

        raise HTTPException(status_code=404, detail="File not found")
