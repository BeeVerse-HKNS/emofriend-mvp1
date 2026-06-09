"""
SubProjectHealthMonitor - 子項目健康監控引擎

功能：
1. 掃描 projects/ 目錄下所有子項目嘅 AGENTS.md
2. 提取狀態、痛點、最後更新時間
3. 分類項目健康狀態（ACTIVE/STALE/HIGH_RISK/COMPLETED）
4. 生成結構化健康報告

公式：P * S + G — 預測 × 自癒 + 守衛

相關規則：Rule 67 (Master Orchestrator 調度規則)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


class HealthStatus(Enum):
    ACTIVE = "ACTIVE"
    STALE = "STALE"
    HIGH_RISK = "HIGH_RISK"
    COMPLETED = "COMPLETED"
    UNKNOWN = "UNKNOWN"


class RiskLevel(Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    NONE = "NONE"


@dataclass
class ProjectHealth:
    name: str
    status: HealthStatus
    last_updated: datetime | None
    risk_level: RiskLevel
    pain_points: list[str] = field(default_factory=list)
    has_tasks: bool = False
    has_checklist: bool = False
    path: Path | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "risk_level": self.risk_level.value,
            "pain_points": self.pain_points,
            "has_tasks": self.has_tasks,
            "has_checklist": self.has_checklist,
            "path": str(self.path) if self.path else None,
        }


class SubProjectHealthMonitor:

    PROJECTS_DIR = "projects"
    AGENTS_FILE = "AGENTS.md"
    STALE_THRESHOLD_DAYS = 7
    HIGH_RISK_CRITICAL_THRESHOLD = 2

    STATUS_KEYWORDS: dict[str, list[str]] = {
        "completed": ["completed", "已完成", "done", "finished"],
        "paused": ["paused", "暫停", "on hold", "suspended"],
        "active": ["active", "活躍", "in progress", "進行中"],
        "stale": ["stale", "停滯", "stalled", "abandoned"],
    }

    PAIN_POINT_PATTERNS: list[tuple[RiskLevel, list[str]]] = [
        (RiskLevel.CRITICAL, ["CRITICAL", "嚴重", "緊急", "urgent", "critical"]),
        (RiskLevel.HIGH, ["HIGH", "高風險", "重要", "high", "major"]),
        (RiskLevel.MEDIUM, ["MEDIUM", "中等", "medium", "moderate"]),
    ]

    EXCLUDED_DIRS: set[str] = {
        "node_modules", "venv", ".venv", ".git", "__pycache__",
        ".ruff_cache", ".mypy_cache", "dist", "build", ".next",
        ".cache", ".tox", ".eggs", "env",
    }

    def __init__(self, root_path: Path | str):
        self.root_path = Path(root_path)
        self.projects_path = self.root_path / self.PROJECTS_DIR

    def scan(self) -> list[ProjectHealth]:
        results: list[ProjectHealth] = []

        if not self.projects_path.exists():
            return results

        for agents_md in self.projects_path.rglob(self.AGENTS_FILE):
            if self._is_excluded_path(agents_md):
                continue
            project_dir = agents_md.parent
            health = self._analyze_project(project_dir, agents_md)
            if health:
                results.append(health)

        return sorted(results, key=lambda h: h.name)

    def generate_report(self) -> str:
        projects = self.scan()

        lines: list[str] = []
        lines.append("# Harnessing 子項目健康報告")
        lines.append("")
        lines.append(f"> **生成時間**：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"> **掃描項目數**：{len(projects)}")
        lines.append("")

        self._append_summary(lines, projects)
        self._append_table(lines, projects)
        self._append_high_risk_details(lines, projects)
        self._append_stale_details(lines, projects)
        self._append_recommendations(lines, projects)

        lines.append("---")
        lines.append("")
        lines.append("*由 SubProjectHealthMonitor 自動生成*")

        return "\n".join(lines)

    def _analyze_project(self, project_dir: Path, agents_md: Path) -> ProjectHealth | None:
        name = self._extract_project_name(project_dir)
        content = self._read_agents_md(agents_md)
        last_updated = self._get_last_updated(agents_md, project_dir)
        pain_points = self._extract_pain_points(content)
        risk_level = self._determine_risk_level(pain_points)
        has_tasks = self._check_file_exists(project_dir, "tasks.md")
        has_checklist = self._check_file_exists(project_dir, "checklist.md")
        status = self._determine_health_status(content, last_updated, risk_level)

        return ProjectHealth(
            name=name,
            status=status,
            last_updated=last_updated,
            risk_level=risk_level,
            pain_points=pain_points,
            has_tasks=has_tasks,
            has_checklist=has_checklist,
            path=project_dir,
        )

    def _is_excluded_path(self, path: Path) -> bool:
        for part in path.parts:
            if part in self.EXCLUDED_DIRS:
                return True
        return False

    def _extract_project_name(self, project_dir: Path) -> str:
        try:
            return project_dir.relative_to(self.projects_path).as_posix()
        except ValueError:
            return project_dir.name

    def _read_agents_md(self, agents_md: Path) -> str:
        try:
            return agents_md.read_text(encoding="utf-8")
        except Exception:
            return ""

    def _get_last_updated(self, agents_md: Path, project_dir: Path) -> datetime | None:
        latest: datetime | None = None

        try:
            agents_md_mtime = datetime.fromtimestamp(agents_md.stat().st_mtime)
            latest = agents_md_mtime
        except OSError:
            pass

        for item in project_dir.rglob("*"):
            if item.is_file() and not item.name.startswith("."):
                if self._is_excluded_path(item):
                    continue
                try:
                    mtime = datetime.fromtimestamp(item.stat().st_mtime)
                    if latest is None or mtime > latest:
                        latest = mtime
                except OSError:
                    continue

        return latest

    def _extract_pain_points(self, content: str) -> list[str]:
        points: list[str] = []

        if not content:
            return points

        sections = re.split(r"^##\s+", content, flags=re.MULTILINE)
        for section in sections:
            first_line = section.split("\n")[0].strip().lower()
            if any(kw in first_line for kw in ["痛點", "pain", "問題", "issue", "風險", "risk"]):
                for line in section.split("\n"):
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if line.startswith("|"):
                        cells = [c.strip() for c in line.split("|") if c.strip()]
                        if len(cells) >= 2 and cells[0] not in ("痛點", "Pain Point", "Issue", "問題"):
                            points.append(f"{cells[0]}: {cells[1]}" if len(cells) > 1 else cells[0])
                    elif len(line) > 3:
                        clean = re.sub(r"^[|\-*>\s]+", "", line).strip()
                        if clean and len(clean) > 3:
                            points.append(clean)

        return points[:20]

    def _determine_risk_level(self, pain_points: list[str]) -> RiskLevel:
        critical_count = 0
        high_count = 0
        medium_count = 0

        for point in pain_points:
            point_upper = point.upper()
            for level, keywords in self.PAIN_POINT_PATTERNS:
                if any(kw.upper() in point_upper for kw in keywords):
                    if level == RiskLevel.CRITICAL:
                        critical_count += 1
                    elif level == RiskLevel.HIGH:
                        high_count += 1
                    elif level == RiskLevel.MEDIUM:
                        medium_count += 1
                    break

        if critical_count >= self.HIGH_RISK_CRITICAL_THRESHOLD:
            return RiskLevel.CRITICAL
        if critical_count >= 1 or high_count >= 2:
            return RiskLevel.HIGH
        if high_count >= 1 or medium_count >= 2:
            return RiskLevel.MEDIUM
        if medium_count >= 1 or len(pain_points) >= 3:
            return RiskLevel.LOW
        return RiskLevel.NONE

    def _determine_health_status(
        self,
        content: str,
        last_updated: datetime | None,
        risk_level: RiskLevel,
    ) -> HealthStatus:
        content_lower = content.lower()

        for status_value, keywords in self.STATUS_KEYWORDS.items():
            for kw in keywords:
                pattern = rf"(?:狀態|status|state)[：:]\s*{re.escape(kw)}"
                if re.search(pattern, content_lower):
                    if status_value == "completed":
                        return HealthStatus.COMPLETED
                    if status_value == "paused":
                        return HealthStatus.STALE

        if risk_level in (RiskLevel.CRITICAL, RiskLevel.HIGH):
            return HealthStatus.HIGH_RISK

        if last_updated is None:
            return HealthStatus.UNKNOWN

        days_since = (datetime.now() - last_updated).days
        if days_since > self.STALE_THRESHOLD_DAYS:
            return HealthStatus.STALE

        return HealthStatus.ACTIVE

    def _check_file_exists(self, project_dir: Path, filename: str) -> bool:
        if (project_dir / filename).exists():
            return True
        traefile = project_dir / ".trae" / filename
        if traefile.exists():
            return True
        for f in project_dir.rglob(filename):
            if f.is_file():
                return True
        return False

    def _append_summary(self, lines: list[str], projects: list[ProjectHealth]) -> None:
        total = len(projects)
        active = sum(1 for p in projects if p.status == HealthStatus.ACTIVE)
        stale = sum(1 for p in projects if p.status == HealthStatus.STALE)
        high_risk = sum(1 for p in projects if p.status == HealthStatus.HIGH_RISK)
        completed = sum(1 for p in projects if p.status == HealthStatus.COMPLETED)
        unknown = sum(1 for p in projects if p.status == HealthStatus.UNKNOWN)
        with_tasks = sum(1 for p in projects if p.has_tasks)
        with_checklist = sum(1 for p in projects if p.has_checklist)

        lines.append("## 健康摘要")
        lines.append("")
        lines.append(f"| 指標 | 數值 |")
        lines.append(f"|------|------|")
        lines.append(f"| 總項目數 | {total} |")
        lines.append(f"| 🟢 ACTIVE | {active} |")
        lines.append(f"| 🟡 STALE | {stale} |")
        lines.append(f"| 🔴 HIGH_RISK | {high_risk} |")
        lines.append(f"| ✅ COMPLETED | {completed} |")
        lines.append(f"| ⚪ UNKNOWN | {unknown} |")
        lines.append(f"| 有 tasks.md | {with_tasks} |")
        lines.append(f"| 有 checklist.md | {with_checklist} |")
        lines.append("")

    def _append_table(self, lines: list[str], projects: list[ProjectHealth]) -> None:
        lines.append("## 項目健康總覽")
        lines.append("")
        lines.append("| 項目名稱 | 狀態 | 最後更新 | 風險等級 | tasks.md | checklist.md |")
        lines.append("|----------|------|----------|----------|----------|-------------|")

        for p in projects:
            status_icon = self._status_icon(p.status)
            risk_icon = self._risk_icon(p.risk_level)
            updated = p.last_updated.strftime("%Y-%m-%d") if p.last_updated else "-"
            tasks = "✅" if p.has_tasks else "❌"
            checklist = "✅" if p.has_checklist else "❌"
            lines.append(f"| {p.name} | {status_icon} {p.status.value} | {updated} | {risk_icon} {p.risk_level.value} | {tasks} | {checklist} |")

        lines.append("")

    def _append_high_risk_details(self, lines: list[str], projects: list[ProjectHealth]) -> None:
        high_risk = [p for p in projects if p.status == HealthStatus.HIGH_RISK]
        if not high_risk:
            return

        lines.append("## 🔴 HIGH_RISK 項目詳情")
        lines.append("")

        for p in high_risk:
            lines.append(f"### {p.name}")
            lines.append("")
            if p.pain_points:
                lines.append("**痛點**：")
                for pp in p.pain_points:
                    lines.append(f"- {pp}")
                lines.append("")
            if not p.has_tasks:
                lines.append("⚠️ 缺少 tasks.md — 建議建立任務追蹤文件")
                lines.append("")
            if not p.has_checklist:
                lines.append("⚠️ 缺少 checklist.md — 建議建立檢查清單")
                lines.append("")

    def _append_stale_details(self, lines: list[str], projects: list[ProjectHealth]) -> None:
        stale = [p for p in projects if p.status == HealthStatus.STALE]
        if not stale:
            return

        lines.append("## 🟡 STALE 項目詳情")
        lines.append("")

        for p in stale:
            days = (datetime.now() - p.last_updated).days if p.last_updated else 0
            lines.append(f"### {p.name}")
            lines.append("")
            lines.append(f"- **最後更新**：{days} 天前")
            if p.pain_points:
                lines.append(f"- **痛點數量**：{len(p.pain_points)}")
            lines.append("")

    def _append_recommendations(self, lines: list[str], projects: list[ProjectHealth]) -> None:
        lines.append("## 建議行動")
        lines.append("")

        recs: list[str] = []
        num = 1

        high_risk = [p for p in projects if p.status == HealthStatus.HIGH_RISK]
        for p in high_risk:
            recs.append(f"{num}. 🔴 **{p.name}**：立即處理 CRITICAL/HIGH 痛點")
            num += 1

        stale = [p for p in projects if p.status == HealthStatus.STALE]
        for p in stale:
            days = (datetime.now() - p.last_updated).days if p.last_updated else 0
            recs.append(f"{num}. 🟡 **{p.name}**：已 {days} 天未更新，檢查是否需要繼續維護")
            num += 1

        no_tasks = [p for p in projects if not p.has_tasks and p.status in (HealthStatus.ACTIVE, HealthStatus.HIGH_RISK)]
        for p in no_tasks:
            recs.append(f"{num}. 📋 **{p.name}**：建立 tasks.md 以追蹤任務進度")
            num += 1

        no_checklist = [p for p in projects if not p.has_checklist and p.status == HealthStatus.HIGH_RISK]
        for p in no_checklist:
            recs.append(f"{num}. ✅ **{p.name}**：建立 checklist.md 以確保交付質量")
            num += 1

        if recs:
            lines.extend(recs)
        else:
            lines.append("所有項目健康狀態良好，無需立即行動。")

        lines.append("")

    def _status_icon(self, status: HealthStatus) -> str:
        icons = {
            HealthStatus.ACTIVE: "🟢",
            HealthStatus.STALE: "🟡",
            HealthStatus.HIGH_RISK: "🔴",
            HealthStatus.COMPLETED: "✅",
            HealthStatus.UNKNOWN: "⚪",
        }
        return icons.get(status, "⚪")

    def _risk_icon(self, risk: RiskLevel) -> str:
        icons = {
            RiskLevel.CRITICAL: "🔴",
            RiskLevel.HIGH: "🟠",
            RiskLevel.MEDIUM: "🟡",
            RiskLevel.LOW: "🟢",
            RiskLevel.NONE: "✅",
        }
        return icons.get(risk, "⚪")


def create_health_monitor(root_path: Path | str | None = None) -> SubProjectHealthMonitor:
    if root_path is None:
        root_path = Path(__file__).parent.parent.parent.parent
    return SubProjectHealthMonitor(root_path)


if __name__ == "__main__":
    import sys

    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    monitor = SubProjectHealthMonitor(root)

    print("=" * 70)
    print("Harnessing SubProject Health Monitor")
    print("=" * 70)

    projects = monitor.scan()

    print(f"\n掃描到 {len(projects)} 個子項目：\n")

    for p in projects:
        icon = {
            HealthStatus.ACTIVE: "🟢",
            HealthStatus.STALE: "🟡",
            HealthStatus.HIGH_RISK: "🔴",
            HealthStatus.COMPLETED: "✅",
            HealthStatus.UNKNOWN: "⚪",
        }.get(p.status, "⚪")

        updated = p.last_updated.strftime("%Y-%m-%d") if p.last_updated else "-"
        risk = p.risk_level.value
        print(f"  {icon} {p.name:<40} {p.status.value:<12} {updated:<12} {risk:<10} {len(p.pain_points)} pain points")

    print("\n" + "=" * 70)
    print("\nMarkdown 報告：\n")
    print(monitor.generate_report())
