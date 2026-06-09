from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger()

_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent


class PreloadLevel(Enum):
    MINIMAL = "MINIMAL"
    STANDARD = "STANDARD"
    FULL = "FULL"


class PreloadPriority(Enum):
    HIGH_ENTROPY = 1
    RECENTLY_ACTIVE = 2
    LOW_ENTROPY = 3


@dataclass
class ContextChunk:
    project_name: str
    level: PreloadLevel
    content: str
    char_count: int
    timestamp: datetime
    source_files: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_name": self.project_name,
            "level": self.level.value,
            "content": self.content,
            "char_count": self.char_count,
            "timestamp": self.timestamp.isoformat(),
            "source_files": self.source_files,
        }


class ProactiveContextPreloader:

    BRIDGE_FILENAME = ".harnessing-bridge.md"
    AGENTS_FILENAME = "AGENTS.md"
    ESSENTIAL_CONTEXT_HEADER = "## Essential Context"
    EXCLUDED_DIRS: set[str] = {
        "node_modules", "venv", ".venv", ".git", "__pycache__",
        ".ruff_cache", ".mypy_cache", "dist", "build", ".next",
        ".cache", ".tox", ".eggs", "env",
    }

    def __init__(self, project_root: Path | None = None) -> None:
        self.project_root = project_root or _PROJECT_ROOT
        self.token_budgets: dict[PreloadLevel, int] = {
            PreloadLevel.MINIMAL: 200,
            PreloadLevel.STANDARD: 500,
            PreloadLevel.FULL: 2000,
        }
        self._cache: dict[str, ContextChunk] = {}
        self._preload_order: list[str] = []

    def compute_preload_order(
        self,
        entropy_values: dict[str, float],
        last_active_times: dict[str, datetime] | None = None,
    ) -> list[str]:
        last_active_times = last_active_times or {}
        now = datetime.now(timezone.utc)
        scored: list[tuple[str, float]] = []

        for project_name, entropy in entropy_values.items():
            score = 0.0
            last_active = last_active_times.get(project_name)

            if entropy >= 0.6:
                score = 1000 + entropy * 100
            elif last_active is not None:
                hours_since = (now - last_active).total_seconds() / 3600
                if hours_since <= 24:
                    score = 500 + (1 - hours_since / 24) * 100
                else:
                    score = entropy * 50
            else:
                score = entropy * 50

            scored.append((project_name, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        self._preload_order = [name for name, _ in scored]
        return self._preload_order

    def preload_project(
        self,
        project_name: str,
        level: PreloadLevel = PreloadLevel.STANDARD,
    ) -> ContextChunk:
        project_path = self._find_project_path(project_name)
        source_files: list[str] = []
        parts: list[str] = []

        if project_path is not None:
            agents_content = self._extract_from_agents_md(project_path, level)
            if agents_content:
                parts.append(agents_content)
                agents_file = project_path / self.AGENTS_FILENAME
                if agents_file.exists():
                    source_files.append(str(agents_file))

            if level in (PreloadLevel.STANDARD, PreloadLevel.FULL):
                bridge_content = self._extract_from_bridge(project_path)
                if bridge_content:
                    parts.append(bridge_content)
                    bridge_file = project_path / self.BRIDGE_FILENAME
                    if bridge_file.exists():
                        source_files.append(str(bridge_file))

        if not parts:
            parts.append(f"{project_name}: no context available")

        content = "\n".join(parts)
        budget = self.token_budgets[level]
        if len(content) > budget:
            content = content[:budget]

        chunk = ContextChunk(
            project_name=project_name,
            level=level,
            content=content,
            char_count=len(content),
            timestamp=datetime.now(timezone.utc),
            source_files=source_files,
        )
        self._cache[project_name] = chunk
        logger.info(
            "preload_project",
            project_name=project_name,
            level=level.value,
            char_count=chunk.char_count,
        )
        return chunk

    def preload_all(
        self,
        entropy_values: dict[str, float],
        last_active_times: dict[str, datetime] | None = None,
        level: PreloadLevel = PreloadLevel.MINIMAL,
    ) -> list[ContextChunk]:
        order = self.compute_preload_order(entropy_values, last_active_times)
        results: list[ContextChunk] = []
        for name in order:
            results.append(self.preload_project(name, level))
        return results

    def preload_high_entropy(
        self,
        entropy_values: dict[str, float],
        threshold: float = 0.6,
    ) -> list[ContextChunk]:
        results: list[ContextChunk] = []
        for name, entropy in entropy_values.items():
            if entropy >= threshold:
                results.append(self.preload_project(name, PreloadLevel.STANDARD))
        results.sort(
            key=lambda c: entropy_values.get(c.project_name, 0),
            reverse=True,
        )
        return results

    def get_cached(self, project_name: str) -> ContextChunk | None:
        return self._cache.get(project_name)

    def invalidate_cache(self, project_name: str | None = None) -> None:
        if project_name is None:
            self._cache.clear()
        else:
            self._cache.pop(project_name, None)

    def generate_startup_context(
        self,
        entropy_values: dict[str, float],
        last_active_times: dict[str, datetime] | None = None,
    ) -> str:
        last_active_times = last_active_times or {}
        now = datetime.now(timezone.utc)
        total = len(entropy_values)

        high_entropy = sorted(
            [(n, e) for n, e in entropy_values.items() if e >= 0.6],
            key=lambda x: x[1],
            reverse=True,
        )

        recently_active: list[str] = []
        for name, ts in last_active_times.items():
            hours = (now - ts).total_seconds() / 3600
            if hours <= 24:
                recently_active.append(name)
        recently_active.sort()

        actions: list[str] = []
        for name, entropy in high_entropy[:3]:
            actions.append(f"scan {name}")
        for name in recently_active[:2]:
            if name not in [n for n, _ in high_entropy]:
                actions.append(f"update {name} deps")

        parts: list[str] = [f"AS3E: {total} projects"]
        if high_entropy:
            he_str = ", ".join(f"{n}({e:.2f})" for n, e in high_entropy[:3])
            parts.append(f"⚠️ High entropy: {he_str}")
        if recently_active:
            parts.append(f"🕐 Recent: {', '.join(recently_active[:3])}")
        if actions:
            parts.append(f"Actions: {', '.join(actions[:4])}")

        result = " | ".join(parts)
        if len(result) > 500:
            result = result[:497] + "..."
        return result

    def _find_project_path(self, project_name: str) -> Path | None:
        projects_dir = self.project_root / "projects"
        if not projects_dir.exists():
            return None

        direct = projects_dir / project_name
        if direct.exists() and direct.is_dir():
            return direct

        for agents_md in projects_dir.rglob(self.AGENTS_FILENAME):
            if self._is_excluded_path(agents_md):
                continue
            candidate = agents_md.parent
            try:
                relative = candidate.relative_to(projects_dir)
                if relative.as_posix() == project_name or relative.name == project_name:
                    return candidate
            except ValueError:
                continue

        return None

    def _extract_from_agents_md(self, project_path: Path, level: PreloadLevel) -> str:
        agents_md = project_path / self.AGENTS_FILENAME
        if not agents_md.exists():
            return ""

        try:
            content = agents_md.read_text(encoding="utf-8")
        except Exception:
            return ""

        lines = content.split("\n")
        project_title = ""
        status_line = ""
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("# ") and not project_title:
                project_title = stripped[2:].strip()
            if any(kw in stripped.lower() for kw in ["狀態", "status", "state"]):
                status_line = stripped
                break

        if level == PreloadLevel.MINIMAL:
            parts = [f"Project: {project_title}" if project_title else f"Project: {project_path.name}"]
            if status_line:
                parts.append(status_line)
            return " | ".join(parts)

        if level == PreloadLevel.STANDARD:
            parts = [f"Project: {project_title}" if project_title else f"Project: {project_path.name}"]
            if status_line:
                parts.append(status_line)
            pain_section = self._extract_section(content, ["痛點", "pain", "問題", "issue"])
            if pain_section:
                parts.append(pain_section)
            return "\n".join(parts)

        parts = [f"Project: {project_title}" if project_title else f"Project: {project_path.name}"]
        if status_line:
            parts.append(status_line)
        for section_name in ["痛點", "pain", "問題", "issue", "決策", "decision", "任務", "task", "依賴", "depend"]:
            section = self._extract_section(content, [section_name])
            if section:
                parts.append(section)
        return "\n".join(parts)

    def _extract_from_bridge(self, project_path: Path) -> str:
        bridge_file = project_path / self.BRIDGE_FILENAME
        if not bridge_file.exists():
            return ""

        try:
            content = bridge_file.read_text(encoding="utf-8")
        except Exception:
            return ""

        idx = content.find(self.ESSENTIAL_CONTEXT_HEADER)
        if idx == -1:
            return ""

        after = content[idx + len(self.ESSENTIAL_CONTEXT_HEADER):]
        next_section = after.find("\n## ")
        if next_section == -1:
            essential = after.strip()
        else:
            essential = after[:next_section].strip()

        return essential

    def _extract_section(self, content: str, keywords: list[str]) -> str:
        lines = content.split("\n")
        in_section = False
        section_lines: list[str] = []
        section_header = ""

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("## "):
                if in_section:
                    break
                header_lower = stripped.lower()
                if any(kw in header_lower for kw in keywords):
                    in_section = True
                    section_header = stripped
                continue

            if in_section:
                if stripped.startswith("### "):
                    section_lines.append(stripped)
                elif stripped and not stripped.startswith("---"):
                    section_lines.append(stripped)

        if not section_lines:
            return ""

        return f"{section_header}\n" + "\n".join(section_lines[:10])

    def _is_excluded_path(self, path: Path) -> bool:
        for part in path.parts:
            if part in self.EXCLUDED_DIRS:
                return True
        return False
