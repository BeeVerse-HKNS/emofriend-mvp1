"""ParallelMind — Multi-Project Parallel Workspace.

Formula: ParallelMind = ⊕(Root, Sub₁, Sub₂, ...) × Bridge - ContextLeak

Manages multiple isolated workspace contexts that can operate in parallel,
with context isolation barriers to prevent cross-project leakage and
task bridges for controlled inter-workspace communication.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any


class ParallelMind:
    """ParallelMind — Multi-Project Parallel Workspace.

    Inherits conceptually from: ParallelWorkspaceEngine, ContextIsolationBarrier,
    TaskBridge, SubProjectRemoteController.

    Provides isolated workspace contexts that can operate in parallel with
    context isolation barriers preventing cross-project leakage and task
    bridges for controlled inter-workspace communication.

    Args:
        max_workspaces: Maximum number of concurrent workspaces allowed.
        context_budget_root: Fraction of context budget allocated to the root workspace.
    """

    def __init__(self, max_workspaces: int = 5, context_budget_root: float = 0.6) -> None:
        self.max_workspaces = max_workspaces
        self.context_budget_root = context_budget_root
        self._workspaces: dict[str, dict[str, Any]] = {}

    async def create_workspace(self, project_path: str, name: str) -> str:
        """Create a new isolated workspace for a project.

        Args:
            project_path: Filesystem path to the project root.
            name: Human-readable name for the workspace.

        Returns:
            The unique workspace ID string.
        """
        if len(self._workspaces) >= self.max_workspaces:
            raise ValueError(
                f"Maximum workspaces ({self.max_workspaces}) reached. "
                "Destroy an existing workspace first."
            )
        workspace_id = f"ws-{uuid.uuid4().hex[:8]}"
        self._workspaces[workspace_id] = {
            "id": workspace_id,
            "name": name,
            "project_path": project_path,
            "status": "idle",
            "context_budget": 1.0 - self.context_budget_root,
            "pending_results": {},
        }
        return workspace_id

    async def dispatch(self, workspace_id: str, instruction: str) -> str:
        """Dispatch an instruction to a specific workspace.

        Args:
            workspace_id: Target workspace identifier.
            instruction: The instruction string to execute.

        Returns:
            A task reference ID for tracking the dispatched work.
        """
        if workspace_id not in self._workspaces:
            raise KeyError(f"Workspace '{workspace_id}' not found.")
        task_id = f"task-{uuid.uuid4().hex[:8]}"
        ws = self._workspaces[workspace_id]
        ws["status"] = "running"
        ws["pending_results"][task_id] = {"instruction": instruction, "status": "dispatched"}
        return task_id

    async def parallel_dispatch(self, instructions: dict[str, str]) -> dict[str, str]:
        """Dispatch instructions to multiple workspaces in parallel.

        Args:
            instructions: Mapping of workspace_id to instruction string.

        Returns:
            Mapping of workspace_id to task reference ID.
        """
        results: dict[str, str] = {}
        tasks = []
        for ws_id, instruction in instructions.items():
            tasks.append(self.dispatch(ws_id, instruction))
        task_ids = await asyncio.gather(*tasks)
        for ws_id, task_id in zip(instructions.keys(), task_ids):
            results[ws_id] = task_id
        return results

    async def get_status(self, workspace_id: str) -> dict:
        """Get the current status of a workspace.

        Args:
            workspace_id: Target workspace identifier.

        Returns:
            Status dictionary with keys: id, name, status, context_budget.
        """
        if workspace_id not in self._workspaces:
            raise KeyError(f"Workspace '{workspace_id}' not found.")
        ws = self._workspaces[workspace_id]
        return {
            "id": ws["id"],
            "name": ws["name"],
            "status": ws["status"],
            "context_budget": ws["context_budget"],
        }

    async def receive(self, workspace_id: str) -> dict:
        """Receive pending results from a workspace.

        Args:
            workspace_id: Target workspace identifier.

        Returns:
            Dictionary of pending task results.
        """
        if workspace_id not in self._workspaces:
            raise KeyError(f"Workspace '{workspace_id}' not found.")
        ws = self._workspaces[workspace_id]
        ws["status"] = "idle"
        results = dict(ws["pending_results"])
        ws["pending_results"] = {}
        return results

    async def destroy_workspace(self, workspace_id: str) -> bool:
        """Destroy an existing workspace and release its resources.

        Args:
            workspace_id: Target workspace identifier.

        Returns:
            True if the workspace was successfully destroyed.
        """
        if workspace_id not in self._workspaces:
            return False
        del self._workspaces[workspace_id]
        return True

    def list_workspaces(self) -> list[dict]:
        """List all active workspaces and their metadata.

        Returns:
            List of workspace metadata dictionaries.
        """
        return [
            {
                "id": ws["id"],
                "name": ws["name"],
                "project_path": ws["project_path"],
                "status": ws["status"],
            }
            for ws in self._workspaces.values()
        ]
