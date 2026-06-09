"""ParallelWorkspaceEngine — 平行工作區引擎

Enables simultaneous operation in both the root workspace and sub-folder
workspaces, with each workspace maintaining its own independent context.

Formula:
    ParallelWork = ⊕(Root, Sub) × Bridge - ContextLeak

Components:
- ⊕(Root, Sub) — Root and Sub-folder workspace composition (this engine)
- × Bridge — Structured communication channel (TaskBridge)
- - ContextLeak — Context isolation loss subtracted by ContextIsolationBarrier

The engine orchestrates the full 5-layer EmoGlyph processing cycle for
cross-workspace operations:

1. Pulse  — Sense sub-folder health and entropy
2. Current — Build minimal context pack needed for the operation
3. Construct — Validate instruction through barrier, plan operation with risk
4. Enactive — Dispatch via TaskBridge, generate BridgeInstruction for Sub-Agent
5. Resonance — Process Sub-Agent result through barrier, verify outcome

Since actual Sub-Agent execution happens at the TRAE IDE level (not in
Python), the enactive step produces a BridgeInstruction that the AI caller
uses with the Task tool.  The caller then calls complete_execution() with
the raw result to finalize the cycle.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .context_isolation_barrier import ContextIsolationBarrier, BarrierPolicy
from .task_bridge import TaskBridge, BridgeInstruction, BridgeResult
from .subproject_remote_controller import (
    SubProjectRemoteController,
    SubProjectInfo,
    SubProjectStatus,
)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class WorkspaceContext:
    """Snapshot of a sub-folder workspace's current state.

    Attributes:
        path: Absolute path to the workspace.
        name: Workspace name (e.g., "world-cup-2026").
        agents_md_summary: Brief summary of AGENTS.md (≤200 chars).
        key_files: Important files in the workspace.
        status: Current SubProjectStatus.
        last_operation: Last operation performed, or None.
        last_result_summary: Last result summary, or None.
    """

    path: str
    name: str
    agents_md_summary: str
    key_files: list[str]
    status: SubProjectStatus
    last_operation: str | None = None
    last_result_summary: str | None = None


@dataclass
class EmoGlyphLayerResult:
    """Result of the 5-layer EmoGlyph processing cycle.

    Each layer contributes a dict capturing its specific output:

    Attributes:
        pulse: Sensing — sub-folder health, entropy.
        current: Context — minimal info needed for the operation.
        construct: Planning — operation plan with risk assessment.
        enactive: Execution — Sub-Agent delegation result / instruction.
        resonance: Validation — result verification.
    """

    pulse: dict
    current: dict
    construct: dict
    enactive: dict
    resonance: dict


# ---------------------------------------------------------------------------
# ParallelWorkspaceEngine
# ---------------------------------------------------------------------------

class ParallelWorkspaceEngine:
    """Orchestrates parallel operations across root and sub-folder workspaces.

    Implements the full ParallelWork formula:

        ParallelWork = ⊕(Root, Sub) × Bridge - ContextLeak

    - ⊕(Root, Sub): This engine composes root and sub-folder workspaces so
      they can operate simultaneously without interfering.
    - × Bridge: TaskBridge provides the structured communication channel.
    - - ContextLeak: ContextIsolationBarrier subtracts any context that
      would leak across workspace boundaries.

    The engine is asynchronous-by-design: execute_in_subfolder() returns a
    PENDING BridgeResult with a BridgeInstruction.  The AI caller then
    executes the instruction via the TRAE IDE Task tool and calls
    complete_execution() to finalize.
    """

    # World Cup 2026 canonical paths (relative to root)
    WC2026_RESEARCH_PATH = "projects/research/world-cup-2026"
    WC2026_DEPLOY_PATH = "projects/deploy/world-2026-deploy"
    WC2026_ARCHIVED_PATH = "projects/archived/world-cup-2026-archived"

    def __init__(self, root_path: str | None = None) -> None:
        """Initialize the ParallelWorkspaceEngine.

        Args:
            root_path: Absolute path to the root workspace.  Defaults to cwd.
        """
        self.root_path = Path(root_path) if root_path else Path.cwd()

        self._barrier = ContextIsolationBarrier(policy=BarrierPolicy())
        self._bridge = TaskBridge(barrier=self._barrier)
        self._controller = SubProjectRemoteController(root_path=str(self.root_path))

        # Pending instructions awaiting Sub-Agent completion
        self._pending: dict[str, BridgeInstruction] = {}

        # Workspace context cache
        self._workspace_cache: dict[str, WorkspaceContext] = {}

        # Operation history for last_operation / last_result_summary
        self._operation_history: dict[str, dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # Core: execute_in_subfolder
    # ------------------------------------------------------------------

    def execute_in_subfolder(
        self,
        target_path: str,
        instruction: str,
        priority: str = "NORMAL",
    ) -> BridgeResult:
        """Execute an instruction in a sub-folder workspace.

        Runs the full 5-layer EmoGlyph cycle but, since actual Sub-Agent
        execution happens at the TRAE IDE level, stops after generating a
        BridgeInstruction.  The instruction is stored in the pending queue
        and the caller must invoke complete_execution() once the Sub-Agent
        returns.

        Steps:
        1. Pulse — Scan sub-folder status via SubProjectRemoteController
        2. Current — Build context pack via TaskBridge.build_context_pack()
        3. Construct — Validate instruction via ContextIsolationBarrier,
           plan operation with risk assessment
        4. Enactive — Dispatch via TaskBridge.dispatch(), store instruction
        5. Resonance — Deferred until complete_execution() is called

        Args:
            target_path: Absolute path to the sub-folder workspace.
            instruction: Task description for the Sub-Agent.
            priority: Priority level (LOW / NORMAL / HIGH / CRITICAL).

        Returns:
            BridgeResult with status="PENDING" and the instruction details
            in the summary field.
        """
        # --- Pulse ---
        sub_info = self._controller.scan_subproject(target_path)
        pulse_data = {
            "status": sub_info.status.value,
            "has_agents_md": sub_info.has_agents_md,
            "has_bridge_md": sub_info.has_bridge_md,
            "python_file_count": len(sub_info.python_files),
            "entropy": self._compute_entropy(sub_info),
        }

        # --- Current ---
        context_pack = self._bridge.build_context_pack(target_path)
        current_data = {
            "agents_md_summary": context_pack.get("agents_md_summary", ""),
            "key_files": context_pack.get("key_files", []),
            "subproject_name": context_pack.get("subproject_name", ""),
        }

        # --- Construct ---
        is_valid, reason = self._barrier.validate_instruction(
            instruction, context_pack
        )
        risk = self._assess_operation_risk(instruction, sub_info)
        construct_data = {
            "is_valid": is_valid,
            "validation_reason": reason,
            "risk": risk,
            "plan": f"Dispatch instruction to {sub_info.name} with {priority} priority"
            if is_valid
            else f"Blocked: {reason}",
        }

        if not is_valid:
            return BridgeResult(
                instruction_id="",
                status="FAILURE",
                summary=f"Instruction blocked by barrier: {reason}",
                errors=[reason],
                subproject_name=sub_info.name,
            )

        # --- Enactive ---
        bridge_instruction = self._bridge.dispatch(
            instruction=instruction,
            target_path=target_path,
            context_pack=context_pack,
            priority=priority,
        )
        self._pending[bridge_instruction.instruction_id] = bridge_instruction

        # Record operation
        self._operation_history[target_path] = {
            "last_operation": instruction[:200],
            "instruction_id": bridge_instruction.instruction_id,
            "timestamp": bridge_instruction.created_at,
        }

        enactive_data = {
            "instruction_id": bridge_instruction.instruction_id,
            "target_path": bridge_instruction.target_path,
            "priority": bridge_instruction.priority,
            "status": "PENDING",
            "note": "Awaiting Sub-Agent execution via TRAE IDE Task tool",
        }

        # --- Resonance (deferred) ---
        resonance_data = {
            "status": "DEFERRED",
            "note": "Call complete_execution() with Sub-Agent result to finalize",
        }

        # Update workspace cache
        self._update_workspace_cache(target_path, sub_info, instruction, None)

        return BridgeResult(
            instruction_id=bridge_instruction.instruction_id,
            status="PENDING",
            summary=(
                f"Instruction dispatched to {sub_info.name}. "
                f"ID: {bridge_instruction.instruction_id}. "
                f"Priority: {priority}. Risk: {risk}. "
                f"Call complete_execution() with this ID after Sub-Agent returns."
            ),
            subproject_name=sub_info.name,
        )

    # ------------------------------------------------------------------
    # Core: complete_execution
    # ------------------------------------------------------------------

    def complete_execution(
        self,
        instruction_id: str,
        raw_result: dict,
    ) -> BridgeResult:
        """Finalize a pending Sub-Agent execution.

        Called by the AI caller once the Sub-Agent has returned results.
        Filters the raw result through the ContextIsolationBarrier and
        constructs the final BridgeResult.

        Args:
            instruction_id: ID of the BridgeInstruction returned by
                execute_in_subfolder().
            raw_result: Raw result dict from the Sub-Agent.

        Returns:
            BridgeResult with the filtered, validated outcome.
        """
        if instruction_id not in self._pending:
            return BridgeResult(
                instruction_id=instruction_id,
                status="FAILURE",
                summary=f"Unknown instruction ID: {instruction_id}",
                errors=[f"No pending instruction with ID {instruction_id}"],
            )

        bridge_instruction = self._pending.pop(instruction_id)

        # Check for leakage in raw result
        leakage_warnings = self._barrier.check_leakage(raw_result)

        # Receive and filter through barrier
        bridge_result = self._bridge.receive(raw_result, instruction_id)

        # Attach leakage warnings if any
        if leakage_warnings:
            bridge_result.errors.extend(
                [f"[LEAKAGE WARNING] {w}" for w in leakage_warnings]
            )

        # Update operation history
        target_path = bridge_instruction.target_path
        if target_path in self._operation_history:
            self._operation_history[target_path]["last_result_summary"] = (
                bridge_result.summary[:200]
            )

        # Update workspace cache with result
        sub_info = self._controller.scan_subproject(target_path)
        self._update_workspace_cache(
            target_path,
            sub_info,
            bridge_instruction.instruction,
            bridge_result.summary,
        )

        return bridge_result

    # ------------------------------------------------------------------
    # Parallel execution
    # ------------------------------------------------------------------

    def execute_parallel(
        self,
        targets: list[dict],
    ) -> list[BridgeResult]:
        """Execute instructions on multiple sub-folders in parallel.

        Each target dict should contain:
            - "path": str — absolute path to the sub-folder
            - "instruction": str — task description
            - "priority": str — optional, defaults to "NORMAL"

        All results are initially PENDING; the caller must call
        complete_execution() for each instruction_id.

        Args:
            targets: List of target specifications.

        Returns:
            List of BridgeResults (all PENDING initially).
        """
        results: list[BridgeResult] = []
        for target in targets:
            path = target.get("path", "")
            instruction = target.get("instruction", "")
            priority = target.get("priority", "NORMAL")

            if not path or not instruction:
                results.append(
                    BridgeResult(
                        instruction_id="",
                        status="FAILURE",
                        summary="Missing 'path' or 'instruction' in target spec",
                        errors=["Invalid target specification"],
                    )
                )
                continue

            result = self.execute_in_subfolder(path, instruction, priority)
            results.append(result)

        return results

    # ------------------------------------------------------------------
    # World Cup 2026 dedicated methods
    # ------------------------------------------------------------------

    def read_wc2026_predictions(self) -> BridgeInstruction:
        """Generate instruction to read World Cup 2026 prediction results.

        Targets the research sub-folder and reads prediction output from
        formula_v10_emoglyph.py.

        Returns:
            BridgeInstruction for reading WC2026 predictions.
        """
        target_path = str(self.root_path / self.WC2026_RESEARCH_PATH)
        context_pack = self._bridge.build_context_pack(target_path)

        instruction = BridgeInstruction(
            target_path=target_path,
            instruction=(
                "Read the World Cup 2026 prediction results from "
                "formula_v10_emoglyph.py. Return the latest prediction "
                "output, including match outcomes and confidence scores."
            ),
            context_pack=context_pack,
            priority="NORMAL",
        )

        self._pending[instruction.instruction_id] = instruction
        return instruction

    def update_wc2026_formula(
        self,
        update_instructions: str,
    ) -> BridgeInstruction:
        """Generate instruction to update the WC2026 prediction formula.

        Args:
            update_instructions: Description of the formula changes to apply.

        Returns:
            BridgeInstruction for updating the WC2026 formula.
        """
        target_path = str(self.root_path / self.WC2026_RESEARCH_PATH)
        context_pack = self._bridge.build_context_pack(target_path)

        instruction = BridgeInstruction(
            target_path=target_path,
            instruction=(
                f"Update the World Cup 2026 prediction formula in "
                f"formula_v10_emoglyph.py with the following changes: "
                f"{update_instructions}"
            ),
            context_pack=context_pack,
            priority="HIGH",
        )

        self._pending[instruction.instruction_id] = instruction
        return instruction

    def deploy_wc2026(self) -> BridgeInstruction:
        """Generate instruction to deploy the World Cup 2026 project.

        Targets the deploy sub-folder.

        Returns:
            BridgeInstruction for deploying the WC2026 project.
        """
        target_path = str(self.root_path / self.WC2026_DEPLOY_PATH)
        context_pack = self._bridge.build_context_pack(target_path)

        instruction = BridgeInstruction(
            target_path=target_path,
            instruction=(
                "Deploy the World Cup 2026 project. Run deployment scripts, "
                "verify the deployment is healthy, and report the status."
            ),
            context_pack=context_pack,
            priority="CRITICAL",
        )

        self._pending[instruction.instruction_id] = instruction
        return instruction

    # ------------------------------------------------------------------
    # Workspace context
    # ------------------------------------------------------------------

    def get_workspace_context(self, path: str) -> WorkspaceContext:
        """Return a WorkspaceContext snapshot for a sub-folder.

        If a cached version exists it is returned; otherwise a fresh scan
        is performed.

        Args:
            path: Absolute path to the sub-folder workspace.

        Returns:
            WorkspaceContext with current state information.
        """
        if path in self._workspace_cache:
            return self._workspace_cache[path]

        sub_info = self._controller.scan_subproject(path)
        context = self._build_workspace_context(path, sub_info)
        self._workspace_cache[path] = context
        return context

    # ------------------------------------------------------------------
    # 5-layer processing
    # ------------------------------------------------------------------

    def process_5layer(
        self,
        target_path: str,
        instruction: str,
    ) -> EmoGlyphLayerResult:
        """Run the full 5-layer EmoGlyph processing cycle.

        Returns the result at each layer for diagnostic and logging
        purposes.  The enactive layer contains the BridgeInstruction
        details; the resonance layer is deferred until the Sub-Agent
        completes.

        Args:
            target_path: Absolute path to the sub-folder workspace.
            instruction: Task description for the Sub-Agent.

        Returns:
            EmoGlyphLayerResult with output from all 5 layers.
        """
        # --- Pulse ---
        sub_info = self._controller.scan_subproject(target_path)
        pulse: dict[str, Any] = {
            "status": sub_info.status.value,
            "has_agents_md": sub_info.has_agents_md,
            "has_bridge_md": sub_info.has_bridge_md,
            "python_file_count": len(sub_info.python_files),
            "data_file_count": len(sub_info.data_files),
            "config_file_count": len(sub_info.config_files),
            "entropy": self._compute_entropy(sub_info),
            "issues": sub_info.issues,
        }

        # --- Current ---
        context_pack = self._bridge.build_context_pack(target_path)
        current: dict[str, Any] = {
            "agents_md_summary": context_pack.get("agents_md_summary", ""),
            "key_files": context_pack.get("key_files", []),
            "subproject_name": context_pack.get("subproject_name", ""),
        }

        # --- Construct ---
        is_valid, reason = self._barrier.validate_instruction(
            instruction, context_pack
        )
        risk = self._assess_operation_risk(instruction, sub_info)
        construct: dict[str, Any] = {
            "is_valid": is_valid,
            "validation_reason": reason,
            "risk": risk,
            "plan": (
                f"Dispatch to {sub_info.name} with NORMAL priority"
                if is_valid
                else f"Blocked: {reason}"
            ),
        }

        # --- Enactive ---
        if is_valid:
            bridge_instruction = self._bridge.dispatch(
                instruction=instruction,
                target_path=target_path,
                context_pack=context_pack,
            )
            self._pending[bridge_instruction.instruction_id] = bridge_instruction
            enactive: dict[str, Any] = {
                "instruction_id": bridge_instruction.instruction_id,
                "target_path": bridge_instruction.target_path,
                "priority": bridge_instruction.priority,
                "status": "PENDING",
            }
        else:
            enactive = {
                "instruction_id": None,
                "status": "BLOCKED",
                "reason": reason,
            }

        # --- Resonance ---
        resonance: dict[str, Any] = {
            "status": "DEFERRED",
            "note": "Call complete_execution() with Sub-Agent result to finalize",
            "leakage_pre_scan": self._barrier.check_leakage(context_pack),
        }

        return EmoGlyphLayerResult(
            pulse=pulse,
            current=current,
            construct=construct,
            enactive=enactive,
            resonance=resonance,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_entropy(info: SubProjectInfo) -> float:
        """Compute a rough entropy score for a sub-project.

        Higher entropy means more disorder (stale, missing files, issues).

        Args:
            info: SubProjectInfo from the controller.

        Returns:
            Float between 0.0 (low entropy) and 1.0 (high entropy).
        """
        entropy = 0.0

        # Status contribution
        status_entropy = {
            SubProjectStatus.ACTIVE: 0.1,
            SubProjectStatus.NEEDS_ATTENTION: 0.5,
            SubProjectStatus.STALE: 0.7,
            SubProjectStatus.ARCHIVED: 0.3,
            SubProjectStatus.UNKNOWN: 0.9,
        }
        entropy += status_entropy.get(info.status, 0.5)

        # Missing key files increase entropy
        if not info.has_agents_md:
            entropy += 0.15
        if not info.has_bridge_md:
            entropy += 0.05
        if not info.has_requirements:
            entropy += 0.05

        # Issues increase entropy
        entropy += min(len(info.issues) * 0.1, 0.3)

        return min(entropy, 1.0)

    @staticmethod
    def _assess_operation_risk(
        instruction: str,
        sub_info: SubProjectInfo,
    ) -> str:
        """Assess the risk level of an operation.

        Args:
            instruction: The instruction text.
            sub_info: SubProjectInfo for the target workspace.

        Returns:
            Risk level string: "LOW", "MEDIUM", "HIGH", or "CRITICAL".
        """
        instruction_lower = instruction.lower()

        # Critical patterns
        critical_keywords = ("delete", "drop", "destroy", "credential", "secret", "password")
        for kw in critical_keywords:
            if kw in instruction_lower:
                return "CRITICAL"

        # High risk patterns
        high_keywords = ("deploy", "release", "migrate", "reset", "overwrite")
        for kw in high_keywords:
            if kw in instruction_lower:
                return "HIGH"

        # Medium risk patterns
        medium_keywords = ("update", "modify", "change", "write", "install")
        for kw in medium_keywords:
            if kw in instruction_lower:
                return "MEDIUM"

        # Workspace status contribution
        if sub_info.status == SubProjectStatus.ARCHIVED:
            return "HIGH"
        if sub_info.status == SubProjectStatus.NEEDS_ATTENTION:
            return "MEDIUM"

        return "LOW"

    def _build_workspace_context(
        self,
        path: str,
        sub_info: SubProjectInfo,
    ) -> WorkspaceContext:
        """Build a WorkspaceContext from SubProjectInfo.

        Args:
            path: Absolute path to the workspace.
            sub_info: SubProjectInfo from the controller.

        Returns:
            WorkspaceContext snapshot.
        """
        # Extract AGENTS.md summary (≤200 chars)
        agents_md_summary = ""
        agents_md = Path(path) / "AGENTS.md"
        if agents_md.exists():
            try:
                content = agents_md.read_text(encoding="utf-8")
                agents_md_summary = content.strip()[:200]
            except Exception:
                agents_md_summary = "(unreadable)"

        # Key files from SubProjectInfo
        key_files = list(sub_info.key_files.keys()) if sub_info.key_files else []
        if not key_files:
            key_files = sub_info.python_files[:20]

        # Operation history
        history = self._operation_history.get(path, {})
        last_op = history.get("last_operation")
        last_summary = history.get("last_result_summary")

        return WorkspaceContext(
            path=path,
            name=sub_info.name,
            agents_md_summary=agents_md_summary,
            key_files=key_files,
            status=sub_info.status,
            last_operation=last_op,
            last_result_summary=last_summary,
        )

    def _update_workspace_cache(
        self,
        path: str,
        sub_info: SubProjectInfo,
        instruction: str,
        result_summary: str | None,
    ) -> None:
        """Update the workspace context cache with latest operation info.

        Args:
            path: Absolute path to the workspace.
            sub_info: SubProjectInfo from the controller.
            instruction: The instruction that was dispatched.
            result_summary: Result summary if available, else None.
        """
        context = self._build_workspace_context(path, sub_info)
        context.last_operation = instruction[:200] if instruction else None
        context.last_result_summary = (
            result_summary[:200] if result_summary else None
        )
        self._workspace_cache[path] = context
