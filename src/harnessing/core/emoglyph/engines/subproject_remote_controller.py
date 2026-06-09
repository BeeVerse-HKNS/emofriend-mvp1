"""SubProjectRemoteController — 子項目遙控器

EmoGlyph Structure-Driven 子項目管理引擎。
通過結構驅動處理（非傳統規則匹配），實現跨資料夾的遙控能力。

公式：Remote = ⊕(P,C,Co,E,R) × Bridge - Isolation
- ⊕(P,C,Co,E,R) — 五層結構疊加處理
- × Bridge — 跨資料夾橋接因子
- - Isolation — 減去 Solo 框架的隔離限制

核心能力：
1. 掃描子項目結構（Pulse — 感知）
2. 讀取子項目狀態（Current — 上下文）
3. 規劃跨資料夾操作（Construct — 建構）
4. 執行遠端操作（Enactive — 行動）
5. 驗證操作結果（Resonance — 共振）
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class SubProjectStatus(Enum):
    ACTIVE = "ACTIVE"
    NEEDS_ATTENTION = "NEEDS_ATTENTION"
    STALE = "STALE"
    ARCHIVED = "ARCHIVED"
    UNKNOWN = "UNKNOWN"


class OperationType(Enum):
    READ = "READ"
    WRITE = "WRITE"
    EXECUTE = "EXECUTE"
    SCAN = "SCAN"
    MODIFY = "MODIFY"
    DEPLOY = "DEPLOY"


class OperationRisk(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class SubProjectInfo:
    name: str
    path: str
    status: SubProjectStatus = SubProjectStatus.UNKNOWN
    has_agents_md: bool = False
    has_bridge_md: bool = False
    has_requirements: bool = False
    has_dockerfile: bool = False
    python_files: list[str] = field(default_factory=list)
    data_files: list[str] = field(default_factory=list)
    config_files: list[str] = field(default_factory=list)
    key_files: dict[str, str] = field(default_factory=dict)
    issues: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RemoteOperation:
    operation_type: OperationType
    target_path: str
    description: str
    risk: OperationRisk
    requires_confirmation: bool = False
    status: str = "PENDING"
    result: Any = None
    error: str | None = None


@dataclass
class RemoteControlResult:
    success: bool
    subproject: SubProjectInfo | None = None
    operations: list[RemoteOperation] = field(default_factory=list)
    summary: str = ""
    structural_advantage: float = 0.0
    pulse_score: float = 0.0
    current_score: float = 0.0
    construct_score: float = 0.0
    enactive_score: float = 0.0
    resonance_score: float = 0.0


class SubProjectRemoteController:

    def __init__(self, root_path: str | None = None):
        self.root_path = Path(root_path) if root_path else Path.cwd()
        self._cache: dict[str, SubProjectInfo] = {}
        self._parallel_engine: Any | None = None

    def _get_parallel_engine(self) -> Any:
        """Lazily create a ParallelWorkspaceEngine instance.

        Uses lazy import to avoid circular dependency between
        SubProjectRemoteController and ParallelWorkspaceEngine.
        """
        if self._parallel_engine is None:
            from .parallel_workspace_engine import ParallelWorkspaceEngine

            self._parallel_engine = ParallelWorkspaceEngine(
                root_path=str(self.root_path)
            )
        return self._parallel_engine

    def scan_all_subprojects(self) -> list[SubProjectInfo]:
        projects_dir = self.root_path / "projects"
        if not projects_dir.exists():
            return []

        results = []
        for item in projects_dir.rglob("AGENTS.md"):
            subproject_path = item.parent
            info = self._scan_subproject(str(subproject_path))
            results.append(info)
            self._cache[info.name] = info

        return results

    def scan_subproject(self, path: str) -> SubProjectInfo:
        if path in self._cache:
            return self._cache[path]
        info = self._scan_subproject(path)
        self._cache[info.name] = info
        return info

    def _scan_subproject(self, path: str) -> SubProjectInfo:
        p = Path(path)
        name = p.name

        info = SubProjectInfo(name=name, path=str(p))

        agents_md = p / "AGENTS.md"
        info.has_agents_md = agents_md.exists()
        if info.has_agents_md:
            info.status = self._detect_status(agents_md)
            info.key_files["AGENTS.md"] = str(agents_md)
            info.metadata.update(self._parse_agents_md(agents_md))

        info.has_bridge_md = (p / ".harnessing-bridge.md").exists()
        info.has_requirements = (p / "requirements.txt").exists()
        info.has_dockerfile = (p / "Dockerfile").exists()

        for f in p.rglob("*.py"):
            rel = str(f.relative_to(p))
            if "__pycache__" in rel or ".mypy_cache" in rel:
                continue
            info.python_files.append(rel)

        for f in p.rglob("*.json"):
            rel = str(f.relative_to(p))
            if "__pycache__" in rel or ".mypy_cache" in rel:
                continue
            info.data_files.append(rel)

        for f in p.rglob("*.toml"):
            rel = str(f.relative_to(p))
            info.config_files.append(rel)
        for f in p.rglob("*.yml"):
            rel = str(f.relative_to(p))
            info.config_files.append(rel)

        if info.status == SubProjectStatus.UNKNOWN:
            if "archived" in name.lower():
                info.status = SubProjectStatus.ARCHIVED
            elif info.has_agents_md:
                info.status = SubProjectStatus.ACTIVE
            else:
                info.status = SubProjectStatus.STALE

        return info

    def _detect_status(self, agents_md: Path) -> SubProjectStatus:
        try:
            content = agents_md.read_text(encoding="utf-8")
            if "NEEDS_ATTENTION" in content:
                return SubProjectStatus.NEEDS_ATTENTION
            if "ARCHIVED" in content:
                return SubProjectStatus.ARCHIVED
            if "STALE" in content:
                return SubProjectStatus.STALE
            if "ACTIVE" in content:
                return SubProjectStatus.ACTIVE
        except Exception:
            pass
        return SubProjectStatus.UNKNOWN

    def _parse_agents_md(self, agents_md: Path) -> dict[str, Any]:
        metadata: dict[str, Any] = {}
        try:
            content = agents_md.read_text(encoding="utf-8")
            purpose_match = re.search(r"## 項目定位\n(.+?)(?:\n##|\Z)", content, re.DOTALL)
            if purpose_match:
                metadata["purpose"] = purpose_match.group(1).strip()
            issues_match = re.search(r"## 當前問題\n(.+?)(?:\n##|\Z)", content, re.DOTALL)
            if issues_match:
                metadata["issues"] = [line.strip("- ") for line in issues_match.group(1).strip().split("\n") if line.strip().startswith("-")]
        except Exception:
            pass
        return metadata

    def remote_read(self, subproject_path: str, file_path: str) -> RemoteOperation:
        full_path = Path(subproject_path) / file_path
        op = RemoteOperation(
            operation_type=OperationType.READ,
            target_path=str(full_path),
            description=f"Read {file_path} from {subproject_path}",
            risk=OperationRisk.LOW,
        )
        try:
            if full_path.exists():
                op.result = full_path.read_text(encoding="utf-8")
                op.status = "SUCCESS"
            else:
                op.error = f"File not found: {full_path}"
                op.status = "FAILED"
        except Exception as e:
            op.error = str(e)
            op.status = "FAILED"
        return op

    def remote_scan_structure(self, subproject_path: str) -> RemoteControlResult:
        info = self.scan_subproject(subproject_path)

        pulse = self._compute_pulse(info)
        current = self._compute_current(info)
        construct = self._compute_construct(info)
        enactive = self._compute_enactive(info)
        resonance = self._compute_resonance(info)

        bridge_factor = 1.0
        if info.has_bridge_md:
            bridge_factor = 1.5
        if info.has_agents_md:
            bridge_factor *= 1.2

        isolation = 0.3
        if info.status == SubProjectStatus.ARCHIVED:
            isolation = 0.6

        structural_advantage = (pulse + current + construct + enactive + resonance) / 5.0 * bridge_factor - isolation

        return RemoteControlResult(
            success=True,
            subproject=info,
            summary=self._generate_summary(info),
            structural_advantage=structural_advantage,
            pulse_score=pulse,
            current_score=current,
            construct_score=construct,
            enactive_score=enactive,
            resonance_score=resonance,
        )

    def remote_execute_plan(
        self,
        target_path: str,
        instruction: str,
        priority: str = "NORMAL",
    ) -> dict:
        """Execute an instruction in a sub-folder via ParallelWorkspaceEngine.

        Delegates to ParallelWorkspaceEngine.execute_in_subfolder() for
        asynchronous Sub-Agent execution instead of synchronous local ops.

        Args:
            target_path: Absolute path to the sub-folder workspace.
            instruction: Task description for the Sub-Agent.
            priority: Priority level (LOW / NORMAL / HIGH / CRITICAL).

        Returns:
            BridgeResult converted to dict with instruction_id, status,
            summary, and other fields.
        """
        engine = self._get_parallel_engine()
        bridge_result = engine.execute_in_subfolder(target_path, instruction, priority)
        return {
            "instruction_id": bridge_result.instruction_id,
            "status": bridge_result.status,
            "summary": bridge_result.summary,
            "subproject_name": bridge_result.subproject_name,
            "modified_files": bridge_result.modified_files,
            "errors": bridge_result.errors,
            "token_count": bridge_result.token_count,
            "timestamp": bridge_result.timestamp,
        }

    def complete_remote_execution(
        self,
        instruction_id: str,
        raw_result: dict,
    ) -> dict:
        """Finalize a pending Sub-Agent execution.

        Called once the Sub-Agent has returned results.  Delegates to
        ParallelWorkspaceEngine.complete_execution() which filters the
        raw result through the ContextIsolationBarrier.

        Args:
            instruction_id: ID of the BridgeInstruction returned by
                remote_execute_plan().
            raw_result: Raw result dict from the Sub-Agent.

        Returns:
            BridgeResult converted to dict with validated outcome.
        """
        engine = self._get_parallel_engine()
        bridge_result = engine.complete_execution(instruction_id, raw_result)
        return {
            "instruction_id": bridge_result.instruction_id,
            "status": bridge_result.status,
            "summary": bridge_result.summary,
            "subproject_name": bridge_result.subproject_name,
            "modified_files": bridge_result.modified_files,
            "errors": bridge_result.errors,
            "token_count": bridge_result.token_count,
            "timestamp": bridge_result.timestamp,
        }

    def remote_control(
        self,
        target_path: str,
        instruction: str,
        priority: str = "NORMAL",
    ) -> dict:
        """High-level API combining scan + plan + execute.

        Steps:
        1. Scan the sub-project via scan_subproject(target_path)
        2. Execute via ParallelWorkspaceEngine
        3. Return combined result with SubProjectInfo + BridgeResult

        Args:
            target_path: Absolute path to the sub-folder workspace.
            instruction: Task description for the Sub-Agent.
            priority: Priority level (LOW / NORMAL / HIGH / CRITICAL).

        Returns:
            Dict with "subproject" (SubProjectInfo as dict) and
            "execution" (BridgeResult as dict).
        """
        subproject_info = self.scan_subproject(target_path)
        execution_result = self.remote_execute_plan(target_path, instruction, priority)
        return {
            "subproject": {
                "name": subproject_info.name,
                "path": subproject_info.path,
                "status": subproject_info.status.value,
                "has_agents_md": subproject_info.has_agents_md,
                "has_bridge_md": subproject_info.has_bridge_md,
                "has_requirements": subproject_info.has_requirements,
                "has_dockerfile": subproject_info.has_dockerfile,
                "python_files": subproject_info.python_files,
                "data_files": subproject_info.data_files,
                "config_files": subproject_info.config_files,
                "key_files": subproject_info.key_files,
                "issues": subproject_info.issues,
                "metadata": subproject_info.metadata,
            },
            "execution": execution_result,
        }

    def _compute_pulse(self, info: SubProjectInfo) -> float:
        score = 0.5
        if info.has_agents_md:
            score += 0.2
        if info.status == SubProjectStatus.NEEDS_ATTENTION:
            score += 0.2
        elif info.status == SubProjectStatus.ACTIVE:
            score += 0.3
        if len(info.python_files) > 10:
            score += 0.1
        return min(score, 1.0)

    def _compute_current(self, info: SubProjectInfo) -> float:
        score = 0.3
        if info.has_bridge_md:
            score += 0.3
        if info.metadata.get("purpose"):
            score += 0.2
        if info.metadata.get("issues"):
            score += 0.2
        return min(score, 1.0)

    def _compute_construct(self, info: SubProjectInfo) -> float:
        score = 0.3
        if info.has_requirements:
            score += 0.2
        if info.has_dockerfile:
            score += 0.2
        if len(info.config_files) > 0:
            score += 0.15
        if len(info.python_files) > 5:
            score += 0.15
        return min(score, 1.0)

    def _compute_enactive(self, info: SubProjectInfo) -> float:
        score = 0.3
        if len(info.python_files) > 20:
            score += 0.3
        elif len(info.python_files) > 10:
            score += 0.2
        if info.has_dockerfile:
            score += 0.2
        if any("deploy" in f.lower() for f in info.python_files):
            score += 0.2
        return min(score, 1.0)

    def _compute_resonance(self, info: SubProjectInfo) -> float:
        score = 0.3
        if info.status == SubProjectStatus.ACTIVE:
            score += 0.3
        elif info.status == SubProjectStatus.NEEDS_ATTENTION:
            score += 0.2
        if info.has_agents_md:
            score += 0.2
        if info.has_bridge_md:
            score += 0.2
        return min(score, 1.0)

    def _assess_risk(self, op_type: OperationType, target: str) -> OperationRisk:
        if op_type in (OperationType.READ, OperationType.SCAN):
            return OperationRisk.LOW
        if op_type == OperationType.EXECUTE:
            if any(kw in target.lower() for kw in ("deploy", "delete", "drop", "reset")):
                return OperationRisk.HIGH
            return OperationRisk.MEDIUM
        if op_type == OperationType.WRITE:
            if any(kw in target.lower() for kw in (".env", "secret", "credential")):
                return OperationRisk.CRITICAL
            return OperationRisk.MEDIUM
        if op_type == OperationType.MODIFY:
            if any(kw in target.lower() for kw in ("config", "setting", "database")):
                return OperationRisk.HIGH
            return OperationRisk.MEDIUM
        return OperationRisk.LOW

    def _generate_summary(self, info: SubProjectInfo) -> str:
        lines = [
            f"SubProject: {info.name}",
            f"Path: {info.path}",
            f"Status: {info.status.value}",
            f"Python files: {len(info.python_files)}",
            f"Data files: {len(info.data_files)}",
            f"Config files: {len(info.config_files)}",
            f"Has AGENTS.md: {info.has_agents_md}",
            f"Has Bridge: {info.has_bridge_md}",
            f"Has Dockerfile: {info.has_dockerfile}",
        ]
        if info.metadata.get("purpose"):
            lines.append(f"Purpose: {info.metadata['purpose']}")
        if info.metadata.get("issues"):
            lines.append(f"Issues: {len(info.metadata['issues'])}")
        return "\n".join(lines)

    def get_world_cup_2026_info(self) -> dict[str, SubProjectInfo]:
        results = {}
        for subdir in ("research/world-cup-2026", "world-2026-deploy", "world-2026_archived"):
            full_path = self.root_path / "projects" / subdir
            if full_path.exists():
                info = self.scan_subproject(str(full_path))
                results[subdir] = info
        return results
