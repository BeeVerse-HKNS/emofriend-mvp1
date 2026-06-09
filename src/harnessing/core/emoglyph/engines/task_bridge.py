"""TaskBridge — Parallel Workspace Communication Channel

Implements the × Bridge component of the EmoGlyph parallel workspace formula:

    ParallelWork = ⊕(Root, Sub) × Bridge - ContextLeak

- ⊕(Root, Sub) — Root and Sub-folder workspace composition
- × Bridge — Structured communication channel (this engine)
- - ContextLeak — Context isolation loss subtracted by ContextIsolationBarrier

The TaskBridge enables structured, priority-aware communication between the root
workspace and sub-folder workspaces. It packages instructions with minimal context,
dispatches them to Sub-Agents, and validates/filtered results through the
ContextIsolationBarrier to prevent context leakage across workspace boundaries.

Core capabilities:
1. Dispatch — Package instruction + sub-folder context for Sub-Agent execution
2. Receive — Validate Sub-Agent results against ContextIsolationBarrier
3. Query — Lightweight status query without launching a Sub-Agent
4. Context Pack — Build minimal context from sub-folder (AGENTS.md, key files)
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .context_isolation_barrier import ContextIsolationBarrier, BarrierPolicy


@dataclass
class BridgeInstruction:
    """A structured instruction dispatched from root to sub-folder workspace.

    Contains the task description, target path, minimal context pack,
    and priority level for Sub-Agent execution.
    """

    target_path: str
    instruction: str
    context_pack: dict
    priority: str = "NORMAL"
    instruction_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass
class BridgeResult:
    """A validated result returned from a sub-folder workspace Sub-Agent.

    Results are filtered through the ContextIsolationBarrier to prevent
    context leakage. The summary is compact (≤500 tokens) and contains
    only the essential outcome information.
    """

    instruction_id: str
    status: str
    summary: str
    modified_files: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    token_count: int = 0
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    subproject_name: str = ""


class TaskBridge:
    """Communication channel between root and sub-folder workspaces.

    Implements the × Bridge factor in ParallelWork = ⊕(Root, Sub) × Bridge - ContextLeak.
    Ensures structured dispatch/receive with ContextIsolationBarrier validation
    to prevent context leakage across workspace boundaries.
    """

    VALID_PRIORITIES = frozenset({"LOW", "NORMAL", "HIGH", "CRITICAL"})
    VALID_STATUSES = frozenset({"SUCCESS", "FAILURE", "PARTIAL", "TIMEOUT"})

    def __init__(self, barrier: ContextIsolationBarrier | None = None) -> None:
        """Initialize TaskBridge with an optional ContextIsolationBarrier.

        Args:
            barrier: ContextIsolationBarrier instance for result validation.
                     If not provided, a default barrier with STRICT policy
                     is created.
        """
        self._barrier = barrier or ContextIsolationBarrier(
            policy=BarrierPolicy.STRICT
        )
        self._dispatch_log: dict[str, BridgeInstruction] = {}

    def dispatch(
        self,
        instruction: str,
        target_path: str,
        context_pack: dict | None = None,
        priority: str = "NORMAL",
    ) -> BridgeInstruction:
        """Package instruction + sub-folder context for Sub-Agent execution.

        Builds a BridgeInstruction with the given task, target path, and
        context. If no context_pack is provided, one is automatically built
        from the target sub-folder.

        Args:
            instruction: The task description to execute in the sub-folder.
            target_path: Absolute path to the sub-folder workspace.
            context_pack: Optional pre-built context. If None, built automatically.
            priority: Priority level (LOW/NORMAL/HIGH/CRITICAL).

        Returns:
            BridgeInstruction ready for Sub-Agent dispatch.

        Raises:
            ValueError: If priority is not a valid level.
        """
        if priority not in self.VALID_PRIORITIES:
            raise ValueError(
                f"Invalid priority '{priority}'. "
                f"Must be one of {sorted(self.VALID_PRIORITIES)}"
            )

        pack = context_pack if context_pack is not None else self.build_context_pack(target_path)

        bridge_instruction = BridgeInstruction(
            target_path=target_path,
            instruction=instruction,
            context_pack=pack,
            priority=priority,
        )

        self._dispatch_log[bridge_instruction.instruction_id] = bridge_instruction
        return bridge_instruction

    def receive(self, raw_result: dict, instruction_id: str) -> BridgeResult:
        """Validate Sub-Agent result against ContextIsolationBarrier.

        Filters the raw result through the barrier to remove any context
        that should not leak across workspace boundaries, then constructs
        a BridgeResult with the filtered data.

        Args:
            raw_result: Raw result dict from Sub-Agent execution.
            instruction_id: ID of the original BridgeInstruction.

        Returns:
            BridgeResult with validated and filtered content.
        """
        status = raw_result.get("status", "FAILURE")
        if status not in self.VALID_STATUSES:
            status = "FAILURE"

        summary = raw_result.get("summary", "")
        modified_files = raw_result.get("modified_files", [])
        errors = raw_result.get("errors", [])
        subproject_name = raw_result.get("subproject_name", "")

        # Validate through ContextIsolationBarrier
        # Use filter_result on a dict with allowed keys, then extract values
        filtered = self._barrier.filter_result({
            "result_summary": summary,
            "modified_file_paths": modified_files,
            "error_messages": errors,
            "operation_status": status,
            "subproject_name": subproject_name,
        })
        filtered_summary = filtered.get("result_summary", "")
        filtered_modified = filtered.get("modified_file_paths", [])
        filtered_error_list = filtered.get("error_messages", [])

        # Estimate token count (rough: ~4 chars per token)
        token_count = max(1, len(filtered_summary) // 4)

        # Enforce 500-token cap on summary
        if token_count > 500:
            # Truncate to approximately 500 tokens (~2000 chars)
            filtered_summary = filtered_summary[:2000]
            token_count = 500

        # Resolve subproject name from dispatch log if missing
        if not subproject_name and instruction_id in self._dispatch_log:
            target = self._dispatch_log[instruction_id].target_path
            subproject_name = Path(target).name

        return BridgeResult(
            instruction_id=instruction_id,
            status=status,
            summary=filtered_summary,
            modified_files=filtered_modified,
            errors=filtered_error_list,
            token_count=token_count,
            subproject_name=subproject_name,
        )

    def query_status(
        self, subproject_name: str, cached_info: dict | None = None
    ) -> dict:
        """Lightweight status query without launching a Sub-Agent.

        Returns cached or provided info about a subproject's current state.
        Does not trigger any Sub-Agent execution — purely informational.

        Args:
            subproject_name: Name of the subproject to query.
            cached_info: Optional cached data about the subproject.

        Returns:
            Dict with subproject status information.
        """
        if cached_info is not None:
            return {
                "subproject_name": subproject_name,
                "source": "cache",
                "status": cached_info.get("status", "UNKNOWN"),
                "last_updated": cached_info.get("last_updated", ""),
                "pending_instructions": cached_info.get("pending_instructions", 0),
                "recent_errors": cached_info.get("recent_errors", []),
            }

        # Check dispatch log for any pending instructions targeting this subproject
        pending = [
            ins
            for ins in self._dispatch_log.values()
            if Path(ins.target_path).name == subproject_name
        ]

        return {
            "subproject_name": subproject_name,
            "source": "dispatch_log",
            "status": "UNKNOWN",
            "last_updated": "",
            "pending_instructions": len(pending),
            "recent_errors": [],
        }

    def build_context_pack(self, target_path: str) -> dict:
        """Build minimal context pack from a sub-folder workspace.

        Reads the AGENTS.md summary and lists key files to provide just
        enough context for a Sub-Agent to operate without full workspace
        access.

        Args:
            target_path: Absolute path to the sub-folder workspace.

        Returns:
            Dict with keys: agents_md_summary, key_files, subproject_name.
        """
        p = Path(target_path)
        subproject_name = p.name
        agents_md_summary = ""
        key_files: list[str] = []

        # Read AGENTS.md summary
        agents_md = p / "AGENTS.md"
        if agents_md.exists():
            try:
                content = agents_md.read_text(encoding="utf-8")
                agents_md_summary = self._extract_summary(content)
                key_files.append("AGENTS.md")
            except Exception:
                agents_md_summary = "(unreadable)"

        # List key files (limited set of important patterns)
        key_patterns = ("*.py", "*.toml", "*.yml", "*.yaml", "*.json", "*.md")
        for pattern in key_patterns:
            for f in p.rglob(pattern):
                rel = str(f.relative_to(p))
                if "__pycache__" in rel or ".mypy_cache" in rel or "node_modules" in rel:
                    continue
                if rel not in key_files:
                    key_files.append(rel)
                # Cap at 50 files to keep context minimal
                if len(key_files) >= 50:
                    break
            if len(key_files) >= 50:
                break

        return {
            "agents_md_summary": agents_md_summary,
            "key_files": key_files,
            "subproject_name": subproject_name,
        }

    @staticmethod
    def _extract_summary(content: str, max_chars: int = 1000) -> str:
        """Extract a compact summary from AGENTS.md content.

        Takes the first meaningful section (up to max_chars) as the summary,
        stripping excessive whitespace.

        Args:
            content: Full AGENTS.md text content.
            max_chars: Maximum characters for the summary.

        Returns:
            Compact summary string.
        """
        # Take content up to the first major section break or max_chars
        summary = content.strip()[:max_chars]
        # Normalize whitespace
        summary = re.sub(r"\n{3,}", "\n\n", summary)
        return summary.strip()
