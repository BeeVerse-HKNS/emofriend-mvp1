"""Workspace API Routes — REST endpoints for workspace management.

Provides CRUD operations for parallel workspaces and instruction dispatch.
"""

from __future__ import annotations

from typing import Any

try:
    from fastapi import APIRouter
except ImportError:
    # Stub for when FastAPI is not installed
    class APIRouter:  # type: ignore[no-redef]
        def post(self, path: str, **kwargs: Any) -> Any:
            def decorator(func: Any) -> Any:
                return func
            return decorator
        def get(self, path: str, **kwargs: Any) -> Any:
            def decorator(func: Any) -> Any:
                return func
            return decorator
        def delete(self, path: str, **kwargs: Any) -> Any:
            def decorator(func: Any) -> Any:
                return func
            return decorator

router = APIRouter()


@router.post("/create")
async def create_workspace(name: str = "", project_path: str = "") -> dict:
    """Create a new parallel workspace.

    Args:
        name: Human-readable workspace name.
        project_path: Filesystem path to the project.

    Returns:
        Dictionary with workspace_id and status.
    """
    return {"workspace_id": "ws-stub", "name": name, "status": "created"}


@router.get("/list")
async def list_workspaces() -> dict:
    """List all active workspaces.

    Returns:
        Dictionary with a list of workspace summaries.
    """
    return {"workspaces": []}


@router.get("/{workspace_id}/status")
async def get_workspace_status(workspace_id: str) -> dict:
    """Get the status of a specific workspace.

    Args:
        workspace_id: The workspace identifier.

    Returns:
        Status dictionary for the workspace.
    """
    return {"id": workspace_id, "status": "idle"}


@router.post("/{workspace_id}/dispatch")
async def dispatch_instruction(workspace_id: str, instruction: str = "") -> dict:
    """Dispatch an instruction to a workspace.

    Args:
        workspace_id: Target workspace identifier.
        instruction: The instruction to execute.

    Returns:
        Dictionary with task_id and dispatch status.
    """
    return {"workspace_id": workspace_id, "task_id": "task-stub", "status": "dispatched"}


@router.delete("/{workspace_id}")
async def destroy_workspace(workspace_id: str) -> dict:
    """Destroy a workspace and release its resources.

    Args:
        workspace_id: The workspace to destroy.

    Returns:
        Dictionary with success status.
    """
    return {"workspace_id": workspace_id, "destroyed": True}
