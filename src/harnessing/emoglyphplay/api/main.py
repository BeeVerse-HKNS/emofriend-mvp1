"""EmoGlyphPlay API — FastAPI application for the EmoGlyphPlay engine.

Provides a REST API for intelligent routing, strategic awareness,
workspace management, personality vectors, memory systems,
connectors, and subscriptions.
"""

from __future__ import annotations

from typing import Any


def create_app() -> Any:
    """Create and configure the FastAPI application.

    Returns:
        A configured FastAPI application instance.
    """
    try:
        from fastapi import FastAPI
    except ImportError:
        raise ImportError(
            "FastAPI is required for the API server. "
            "Install it with: pip install fastapi uvicorn"
        )

    app = FastAPI(
        title="EmoGlyphPlay API",
        description="AI Coding Partner with Intelligent Routing Engine — 知暗行明",
        version="0.2.0",
    )

    # Register routers — MVP-Lite core endpoints
    from harnessing.emoglyphplay.api.routes.connector import router as connector_router
    from harnessing.emoglyphplay.api.routes.memory import router as memory_router
    from harnessing.emoglyphplay.api.routes.personality import router as personality_router
    from harnessing.emoglyphplay.api.routes.route import router as route_router
    from harnessing.emoglyphplay.api.routes.strategy import router as strategy_router
    from harnessing.emoglyphplay.api.routes.subscription import router as subscription_router

    # Register routers — Management endpoints
    from harnessing.emoglyphplay.api.routes.workspace import router as workspace_router

    # MVP-Lite routes
    app.include_router(route_router, prefix="/api/v1/route", tags=["route"])
    app.include_router(strategy_router, prefix="/api/v1/strategy", tags=["strategy"])

    # Management routes
    app.include_router(workspace_router, prefix="/api/v1/workspace", tags=["workspace"])
    app.include_router(personality_router, prefix="/api/v1/personality", tags=["personality"])
    app.include_router(memory_router, prefix="/api/v1/memory", tags=["memory"])
    app.include_router(connector_router, prefix="/api/v1/connector", tags=["connector"])
    app.include_router(subscription_router, prefix="/api/v1/subscription", tags=["subscription"])

    @app.get("/health")
    async def health_check() -> dict:
        return {"status": "ok", "version": "0.2.0", "engine": "EmoGlyphPlay"}

    return app


# Module-level app instance for uvicorn
app = create_app()
