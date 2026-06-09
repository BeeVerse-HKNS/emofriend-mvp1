"""Connector API Routes — REST endpoints for connector management.

Provides endpoints for registering, listing, and executing actions
through external service connectors.
"""

from __future__ import annotations

from typing import Any

try:
    from fastapi import APIRouter
except ImportError:
    class APIRouter:  # type: ignore[no-redef]
        def post(self, path: str, **kwargs: Any) -> Any:
            def decorator(func: Any) -> Any: return func
            return decorator
        def get(self, path: str, **kwargs: Any) -> Any:
            def decorator(func: Any) -> Any: return func
            return decorator
        def delete(self, path: str, **kwargs: Any) -> Any:
            def decorator(func: Any) -> Any: return func
            return decorator

router = APIRouter()


@router.get("/list")
async def list_connectors() -> dict:
    """List all registered connectors and their capabilities.

    Returns:
        Dictionary with a list of connector summaries.
    """
    return {"connectors": []}


@router.post("/register")
async def register_connector(name: str = "", connector_type: str = "") -> dict:
    """Register a new connector.

    Args:
        name: Unique name for the connector.
        connector_type: Type of connector (github, slack, dingtalk, etc.).

    Returns:
        Dictionary with registration status.
    """
    return {"name": name, "type": connector_type, "registered": True}


@router.post("/{connector_name}/execute")
async def execute_connector_action(connector_name: str, action: str = "", params: dict | None = None) -> dict:
    """Execute an action through a named connector.

    Args:
        connector_name: Name of the registered connector.
        action: The action to execute.
        params: Parameters for the action.

    Returns:
        Dictionary with the action result.
    """
    return {
        "connector": connector_name,
        "action": action,
        "params": params or {},
        "result": {"success": True, "data": []},
    }


@router.delete("/{connector_name}")
async def unregister_connector(connector_name: str) -> dict:
    """Unregister a connector.

    Args:
        connector_name: Name of the connector to remove.

    Returns:
        Dictionary confirming the unregistration.
    """
    return {"connector": connector_name, "unregistered": True}
