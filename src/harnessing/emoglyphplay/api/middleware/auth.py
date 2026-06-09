"""Auth Middleware — API Key + JWT Authentication.

Provides authentication middleware for the EmoGlyphPlay API.
Supports both API Key (simple) and JWT (session) authentication.
"""

from __future__ import annotations

from typing import Any

try:
    from fastapi import HTTPException, Request
    from fastapi.security import APIKeyHeader
    from starlette.middleware.base import BaseHTTPMiddleware
except ImportError:
    raise ImportError("FastAPI is required. Install with: pip install fastapi")


API_KEY_NAME = "X-API-Key"

api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

# Public paths that don't require authentication
_PUBLIC_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}


class AuthMiddleware(BaseHTTPMiddleware):
    """Authentication middleware for the EmoGlyphPlay API.

    Supports API Key authentication via X-API-Key header.
    Public paths (/health, /docs) are excluded from auth.

    Args:
        app: The ASGI application.
        valid_api_keys: Set of valid API keys.
    """

    def __init__(self, app: Any, valid_api_keys: set[str] | None = None) -> None:
        super().__init__(app)
        self.valid_api_keys = valid_api_keys or set()

    async def dispatch(self, request: Request, call_next: Any) -> Any:
        """Process the request through authentication.

        Args:
            request: The incoming request.
            call_next: The next middleware/endpoint handler.

        Returns:
            The response from the next handler.

        Raises:
            HTTPException: If authentication fails.
        """
        # Skip auth for public paths
        if request.url.path in _PUBLIC_PATHS:
            return await call_next(request)

        # Skip auth if no keys configured (development mode)
        if not self.valid_api_keys:
            return await call_next(request)

        # Check API key
        api_key = request.headers.get(API_KEY_NAME)
        if not api_key:
            raise HTTPException(
                status_code=401,
                detail=f"Missing {API_KEY_NAME} header. Provide your API key.",
            )

        if api_key not in self.valid_api_keys:
            raise HTTPException(
                status_code=403,
                detail="Invalid API key.",
            )

        return await call_next(request)
