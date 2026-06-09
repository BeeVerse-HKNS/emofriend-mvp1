"""ProceduralMemory — Skill and procedure memory for learned workflows.

Stores procedural knowledge (how-to sequences, skill definitions, and
workflow templates) that can be recalled and executed.
"""

from __future__ import annotations

from typing import Any


class ProceduralMemory:
    """ProceduralMemory — Skill and procedure memory.

    Stores procedural knowledge as named procedures with step sequences,
    enabling skill recall and workflow replay.

    Args:
        max_procedures: Maximum number of procedures to retain.
    """

    def __init__(self, max_procedures: int = 500) -> None:
        self.max_procedures = max_procedures
        self._procedures: dict[str, dict[str, Any]] = {}

    def store_procedure(
        self,
        name: str,
        steps: list[dict],
        category: str = "general",
        metadata: dict | None = None,
    ) -> str:
        """Store a procedural skill/workflow.

        Args:
            name: Human-readable name for the procedure.
            steps: Ordered list of step dictionaries.
            category: Category label for the procedure.
            metadata: Optional additional metadata.

        Returns:
            The procedure ID.
        """
        if len(self._procedures) >= self.max_procedures:
            oldest = next(iter(self._procedures))
            del self._procedures[oldest]

        proc_id = f"proc-{name.lower().replace(' ', '-')}"
        self._procedures[proc_id] = {
            "id": proc_id,
            "name": name,
            "steps": steps,
            "category": category,
            "metadata": metadata or {},
        }
        return proc_id

    def retrieve_procedure(self, proc_id: str) -> dict | None:
        """Retrieve a procedure by its ID.

        Args:
            proc_id: The procedure identifier.

        Returns:
            The procedure dictionary, or None if not found.
        """
        return self._procedures.get(proc_id)

    def list_procedures(self, category: str | None = None) -> list[dict]:
        """List stored procedures, optionally filtered by category.

        Args:
            category: Optional category filter.

        Returns:
            List of procedure summary dictionaries.
        """
        procs = self._procedures.values()
        if category:
            procs = [p for p in procs if p["category"] == category]
        return [
            {"id": p["id"], "name": p["name"], "category": p["category"], "step_count": len(p["steps"])}
            for p in procs
        ]

    def execute_step(self, proc_id: str, step_index: int) -> dict | None:
        """Get a specific step from a procedure for execution.

        Args:
            proc_id: The procedure identifier.
            step_index: Zero-based step index.

        Returns:
            The step dictionary, or None if not found.
        """
        proc = self._procedures.get(proc_id)
        if proc is None or step_index >= len(proc["steps"]):
            return None
        return proc["steps"][step_index]

    def clear(self) -> None:
        """Clear all procedures."""
        self._procedures.clear()
