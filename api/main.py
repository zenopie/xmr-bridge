"""Main FastAPI application for XMR Bridge."""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from bridge import SimpleBridge, BridgeConfig
from api.dependencies import set_bridge
from api.models import HealthResponse
from api.routes import deposits, withdrawals, websocket

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    # Startup
    logger.info("Starting XMR Bridge API...")

    # Load configuration and create bridge
    config = BridgeConfig.from_env()
    bridge = SimpleBridge(config)

    # Set global bridge instance for dependency injection
    set_bridge(bridge)

    # Start bridge in background
    asyncio.create_task(bridge.run())

    # Wait for initialization
    await asyncio.sleep(2)
    logger.info("XMR Bridge API started successfully")

    yield

    # Shutdown
    logger.info("Stopping XMR Bridge API...")
    await bridge.stop()
    logger.info("XMR Bridge API stopped")


# Create FastAPI app
app = FastAPI(
    title="XMR Bridge API",
    description="REST API for Monero to Secret Network bridge",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(deposits.router)
app.include_router(withdrawals.router)
app.include_router(websocket.router)


@app.get("/", response_model=HealthResponse)
async def root():
    """API health check."""
    return HealthResponse(
        status="online",
        service="XMR Bridge API",
        version="1.0.0"
    )


@app.get("/health")
async def health_check():
    """Simple health check for monitoring."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )
