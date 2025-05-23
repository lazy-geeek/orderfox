from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.endpoints.market_data_http import router as market_data_http_router
from app.api.v1.endpoints.market_data_ws import router as market_data_ws_router

# Create FastAPI app instance
app = FastAPI(title="Trading Bot API", version="1.0.0")

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


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint that returns a welcome message."""
    return {"message": "Trading Bot API"}
