"""
ProjectScanner - Master Agent 子項目掃描引擎

功能：
1. 掃描 projects/ 目錄下所有子項目
2. 檢測 AGENTS.md 存在
3. 解析項目類型
4. 提取最後更新時間
5. 計算進度狀態

公式：log(K) + R * P — 抽象化知識 + 推理 × 預測

相關規則：Rule 67 (Master Orchestrator 調度規則)
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


class ProjectType(Enum):
    PYTHON_APP = "python_app"
    WEB_PLATFORM = "web_platform"
    CHROME_EXTENSION = "chrome_extension"
    MINI_PROGRAM = "mini_program"
    REACT_NATIVE = "react_native"
    SHARED_LIBRARY = "shared_library"
    DOCUMENTATION = "documentation"
    DATA_STORAGE = "data_storage"
    STATIC_SITE = "static_site"
    UNKNOWN = "unknown"


class ProjectStatus(Enum):
    ACTIVE = "active"
    STALLED = "stalled"
    COMPLETED = "completed"
    ERROR = "error"
    UNKNOWN = "unknown"


@dataclass
class SubProject:
    name: str
    path: Path
    project_type: ProjectType
    has_agents_md: bool
    agents_md_path: Path | None
    status: ProjectStatus
    last_update: datetime | None
    progress: float
    description: str
    tech_stack: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    pending_tasks: int = 0
    error_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "path": str(self.path),
            "project_type": self.project_type.value,
            "has_agents_md": self.has_agents_md,
            "agents_md_path": str(self.agents_md_path) if self.agents_md_path else None,
            "status": self.status.value,
            "last_update": self.last_update.isoformat() if self.last_update else None,
            "progress": self.progress,
            "description": self.description,
            "tech_stack": self.tech_stack,
            "dependencies": self.dependencies,
            "pending_tasks": self.pending_tasks,
            "error_count": self.error_count,
        }


class ProjectScanner:
    """
    Master Agent 子項目掃描引擎

    掃描 projects/ 目錄下所有子項目，生成狀態報告。
    """

    PROJECTS_DIR = "projects"
    AGENTS_FILE = "AGENTS.md"

    TYPE_INDICATORS: dict[ProjectType, list[str]] = {
        ProjectType.PYTHON_APP: ["requirements.txt", "pyproject.toml", "setup.py", "main.py", "app.py"],
        ProjectType.WEB_PLATFORM: ["wsgi.py", "asgi.py", "nginx.conf", "Dockerfile"],
        ProjectType.CHROME_EXTENSION: ["manifest.json", "background.js", "content.js", "popup.html"],
        ProjectType.MINI_PROGRAM: ["app.json", "app.js", "pages/"],
        ProjectType.REACT_NATIVE: ["App.js", "package.json", "src/screens/"],
        ProjectType.SHARED_LIBRARY: ["index.js", "index.py", "__init__.py"],
        ProjectType.DOCUMENTATION: [".md", "README.md", "docs/"],
        ProjectType.DATA_STORAGE: [".json", ".db", ".sqlite", "data/"],
        ProjectType.STATIC_SITE: ["index.html", "site/", "dist/"],
    }

    def __init__(self, root_path: Path | str):
        self.root_path = Path(root_path)
        self.projects_path = self.root_path / self.PROJECTS_DIR
        self._scan_cache: dict[str, SubProject] = {}
        self._last_scan_time: datetime | None = None

    def scan_all(self, force_refresh: bool = False) -> list[SubProject]:
        if not force_refresh and self._scan_cache:
            return list(self._scan_cache.values())

        projects: list[SubProject] = []

        if not self.projects_path.exists():
            return projects

        for item in self.projects_path.iterdir():
            if item.is_dir():
                project = self._scan_project(item)
                if project:
                    projects.append(project)
                    self._scan_cache[project.name] = project

        self._last_scan_time = datetime.now()
        return projects

    def scan_single(self, project_name: str) -> SubProject | None:
        project_path = self.projects_path / project_name
        if not project_path.exists():
            return None
        return self._scan_project(project_path)

    def _scan_project(self, project_path: Path) -> SubProject | None:
        if not project_path.is_dir():
            return None

        name = self._get_project_name(project_path)
        project_type = self._detect_project_type(project_path)
        has_agents_md, agents_md_path = self._check_agents_md(project_path)
        last_update = self._get_last_update(project_path)
        status = self._determine_status(project_path, has_agents_md, last_update)
        progress = self._calculate_progress(project_path, has_agents_md, agents_md_path)
        description = self._extract_description(project_path, has_agents_md, agents_md_path)
        tech_stack = self._detect_tech_stack(project_path)
        dependencies = self._extract_dependencies(project_path)
        pending_tasks = self._count_pending_tasks(project_path, has_agents_md, agents_md_path)

        return SubProject(
            name=name,
            path=project_path,
            project_type=project_type,
            has_agents_md=has_agents_md,
            agents_md_path=agents_md_path,
            status=status,
            last_update=last_update,
            progress=progress,
            description=description,
            tech_stack=tech_stack,
            dependencies=dependencies,
            pending_tasks=pending_tasks,
        )

    def _get_project_name(self, project_path: Path) -> str:
        return project_path.relative_to(self.projects_path).as_posix()

    def _detect_project_type(self, project_path: Path) -> ProjectType:
        files = set()
        dirs = set()

        for item in project_path.iterdir():
            if item.is_file():
                files.add(item.name)
                files.add(item.suffix)
            elif item.is_dir():
                dirs.add(item.name + "/")

        for project_type, indicators in self.TYPE_INDICATORS.items():
            for indicator in indicators:
                if indicator in files or indicator in dirs:
                    return project_type

        return ProjectType.UNKNOWN

    def _check_agents_md(self, project_path: Path) -> tuple[bool, Path | None]:
        agents_path = project_path / self.AGENTS_FILE
        if agents_path.exists():
            return True, agents_path
        return False, None

    def _get_last_update(self, project_path: Path) -> datetime | None:
        latest_time: datetime | None = None

        for item in project_path.rglob("*"):
            if item.is_file() and not item.name.startswith("."):
                try:
                    mtime = datetime.fromtimestamp(item.stat().st_mtime)
                    if latest_time is None or mtime > latest_time:
                        latest_time = mtime
                except OSError:
                    continue

        return latest_time

    def _determine_status(
        self, project_path: Path, has_agents_md: bool, last_update: datetime | None
    ) -> ProjectStatus:
        if not has_agents_md:
            return ProjectStatus.UNKNOWN

        if last_update is None:
            return ProjectStatus.UNKNOWN

        days_since_update = (datetime.now() - last_update).days

        if days_since_update > 30:
            return ProjectStatus.STALLED
        elif days_since_update > 7:
            return ProjectStatus.STALLED
        else:
            return ProjectStatus.ACTIVE

    def _calculate_progress(
        self, project_path: Path, has_agents_md: bool, agents_md_path: Path | None
    ) -> float:
        if not has_agents_md or agents_md_path is None:
            return 0.0

        try:
            content = agents_md_path.read_text(encoding="utf-8")

            progress_patterns = [
                r"Phase\s+(\d+).*?完成",
                r"進度[：:]\s*(\d+)%",
                r"Progress[：:]\s*(\d+)%",
                r"✅.*?Phase\s+(\d+)",
            ]

            for pattern in progress_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    for match in matches:
                        try:
                            value = float(match)
                            if value <= 100:
                                return value
                            elif value <= 10:
                                return value * 10
                        except ValueError:
                            continue

            if "Phase 1" in content and "Phase 2" in content:
                if "Phase 3" in content:
                    return 75.0
                return 50.0
            elif "Phase 1" in content:
                return 25.0

        except Exception:
            pass

        return 0.0

    def _extract_description(
        self, project_path: Path, has_agents_md: bool, agents_md_path: Path | None
    ) -> str:
        if has_agents_md and agents_md_path:
            try:
                content = agents_md_path.read_text(encoding="utf-8")
                lines = content.split("\n")
                for line in lines[:20]:
                    line = line.strip()
                    if line and not line.startswith("#") and len(line) > 10:
                        return line[:200]
            except Exception:
                pass

        readme_path = project_path / "README.md"
        if readme_path.exists():
            try:
                content = readme_path.read_text(encoding="utf-8")
                lines = content.split("\n")
                for line in lines[:10]:
                    line = line.strip()
                    if line and not line.startswith("#") and len(line) > 10:
                        return line[:200]
            except Exception:
                pass

        return f"{project_path.name} 子項目"

    def _detect_tech_stack(self, project_path: Path) -> list[str]:
        stack: set[str] = set()

        requirements = project_path / "requirements.txt"
        if requirements.exists():
            stack.add("Python")
            try:
                content = requirements.read_text(encoding="utf-8")
                if "flask" in content.lower():
                    stack.add("Flask")
                if "fastapi" in content.lower():
                    stack.add("FastAPI")
                if "django" in content.lower():
                    stack.add("Django")
                if "playwright" in content.lower():
                    stack.add("Playwright")
            except Exception:
                pass

        package_json = project_path / "package.json"
        if package_json.exists():
            stack.add("Node.js")
            try:
                content = package_json.read_text(encoding="utf-8")
                if "react" in content.lower():
                    stack.add("React")
                if "react-native" in content.lower():
                    stack.add("React Native")
                if "vue" in content.lower():
                    stack.add("Vue")
            except Exception:
                pass

        manifest = project_path / "manifest.json"
        if manifest.exists():
            stack.add("Chrome Extension")

        return list(stack)

    def _extract_dependencies(self, project_path: Path) -> list[str]:
        deps: set[str] = set()

        requirements = project_path / "requirements.txt"
        if requirements.exists():
            try:
                content = requirements.read_text(encoding="utf-8")
                for line in content.split("\n"):
                    line = line.strip()
                    if line and not line.startswith("#"):
                        pkg = line.split("==")[0].split(">=")[0].split("<=")[0].split("[")[0]
                        if pkg:
                            deps.add(pkg)
            except Exception:
                pass

        return list(deps)[:20]

    def _count_pending_tasks(
        self, project_path: Path, has_agents_md: bool, agents_md_path: Path | None
    ) -> int:
        count = 0

        if has_agents_md and agents_md_path:
            try:
                content = agents_md_path.read_text(encoding="utf-8")
                count += len(re.findall(r"\[ \]", content))
                count += len(re.findall(r"TODO", content, re.IGNORECASE))
                count += len(re.findall(r"待辦", content))
                count += len(re.findall(r"下一步", content))
            except Exception:
                pass

        tasks_md = project_path / ".trae" / "tasks.md"
        if tasks_md.exists():
            try:
                content = tasks_md.read_text(encoding="utf-8")
                count += len(re.findall(r"\[ \]", content))
            except Exception:
                pass

        return count

    def get_summary(self) -> dict[str, Any]:
        projects = self.scan_all()

        total = len(projects)
        with_agents = sum(1 for p in projects if p.has_agents_md)
        active = sum(1 for p in projects if p.status == ProjectStatus.ACTIVE)
        stalled = sum(1 for p in projects if p.status == ProjectStatus.STALLED)
        unknown = sum(1 for p in projects if p.status == ProjectStatus.UNKNOWN)

        type_distribution: dict[str, int] = {}
        for p in projects:
            t = p.project_type.value
            type_distribution[t] = type_distribution.get(t, 0) + 1

        return {
            "total_projects": total,
            "with_agents_md": with_agents,
            "without_agents_md": total - with_agents,
            "active_projects": active,
            "stalled_projects": stalled,
            "unknown_status": unknown,
            "type_distribution": type_distribution,
            "scan_time": self._last_scan_time.isoformat() if self._last_scan_time else None,
        }

    def to_json(self, indent: int = 2) -> str:
        projects = self.scan_all()
        return json.dumps(
            {
                "summary": self.get_summary(),
                "projects": [p.to_dict() for p in projects],
            },
            indent=indent,
            ensure_ascii=False,
        )

    def find_stalled_projects(self, days_threshold: int = 7) -> list[SubProject]:
        projects = self.scan_all()
        stalled: list[SubProject] = []

        for p in projects:
            if p.last_update:
                days_since = (datetime.now() - p.last_update).days
                if days_since > days_threshold:
                    stalled.append(p)

        return sorted(stalled, key=lambda x: x.last_update or datetime.min)

    def find_missing_agents_md(self) -> list[SubProject]:
        projects = self.scan_all()
        return [p for p in projects if not p.has_agents_md]


def scan_harnessing_projects(root_path: Path | str | None = None) -> ProjectScanner:
    if root_path is None:
        root_path = Path(__file__).parent.parent.parent.parent
    return ProjectScanner(root_path)


if __name__ == "__main__":
    import sys

    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    scanner = ProjectScanner(root)

    print("=" * 60)
    print("Harnessing Master Agent - Project Scanner")
    print("=" * 60)

    projects = scanner.scan_all()

    print(f"\n掃描到 {len(projects)} 個子項目：\n")

    for p in projects:
        status_icon = {
            ProjectStatus.ACTIVE: "🟢",
            ProjectStatus.STALLED: "🟡",
            ProjectStatus.COMPLETED: "✅",
            ProjectStatus.ERROR: "🔴",
            ProjectStatus.UNKNOWN: "⚪",
        }.get(p.status, "⚪")

        agents_icon = "✅" if p.has_agents_md else "❌"

        print(f"  {status_icon} {p.name:<35} {agents_icon} AGENTS.md  {p.progress:>5.0f}%  {p.project_type.value}")

    print("\n" + "=" * 60)
    summary = scanner.get_summary()
    print(f"統計：{summary['total_projects']} 個子項目")
    print(f"      {summary['with_agents_md']} 個有 AGENTS.md")
    print(f"      {summary['active_projects']} 個活躍")
    print(f"      {summary['stalled_projects']} 個停滯")
    print("=" * 60)
