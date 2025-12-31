"""
Sleeper Analytics API - Main Application

FastAPI application for fantasy football analytics.
"""

from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sleeper_analytics import __version__
from sleeper_analytics.api.dependencies import ClientManager
from sleeper_analytics.api.routes import awards, benchwarmer, efficiency, faab, leagues, luck, matchups, trade_analyzer, trades, transactions, viz
from sleeper_analytics.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown."""
    # Startup
    settings = get_settings()
    print(f"🏈 Starting Sleeper Analytics API v{__version__}")
    print(f"   Debug mode: {settings.debug}")
    print(f"   Default season: {settings.default_season}")

    yield

    # Shutdown
    print("👋 Shutting down Sleeper Analytics API")
    await ClientManager.close_client()


def create_app() -> FastAPI:
    """Application factory to create the FastAPI app."""
    settings = get_settings()

    app = FastAPI(
        title=settings.api_title,
        description=settings.api_description,
        version=settings.api_version,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Health check endpoint
    @app.get("/health", tags=["Health"])
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "version": __version__}

    # Root endpoint
    @app.get("/", tags=["Root"])
    async def root():
        """Root endpoint with API info."""
        return {
            "name": settings.api_title,
            "version": __version__,
            "docs": "/docs",
            "health": "/health",
            "endpoints": {
                "leagues": "/api/leagues",
                "transactions": "/api/transactions",
                "matchups": "/api/matchups",
                "efficiency": "/api/efficiency",
                "trades": "/api/trades",
                "awards": "/api/awards",
                "benchwarmer": "/api/benchwarmer",
                "luck": "/api/luck",
                "faab": "/api/faab",
                "viz": "/api/viz",
            },
        }

    # Register API routes
    app.include_router(leagues.router, prefix="/api/leagues", tags=["Leagues"])
    app.include_router(transactions.router, prefix="/api/transactions", tags=["Transactions"])
    app.include_router(matchups.router, prefix="/api/matchups", tags=["Matchups"])
    app.include_router(efficiency.router, prefix="/api/efficiency", tags=["Efficiency"])
    app.include_router(trades.router, prefix="/api/trades", tags=["Trades"])
    app.include_router(trade_analyzer.router, prefix="/api/trade-analyzer", tags=["Trade Analyzer"])
    app.include_router(awards.router, prefix="/api/awards", tags=["Awards"])
    app.include_router(benchwarmer.router, prefix="/api/benchwarmer", tags=["Benchwarmer"])
    app.include_router(luck.router, prefix="/api/luck", tags=["Luck Analysis"])
    app.include_router(faab.router, prefix="/api/faab", tags=["FAAB Analysis"])
    app.include_router(viz.router, prefix="/api/viz", tags=["Visualization"])

    return app


# Create the application instance
app = create_app()


def run():
    """Run the application (used by the CLI entry point)."""
    settings = get_settings()
    uvicorn.run(
        "sleeper_analytics.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
    )


if __name__ == "__main__":
    run()
