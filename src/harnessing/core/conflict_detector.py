"""
ConflictDetector — 衝突偵測器

偵測以下類型衝突：
1. 依賴衝突 — 不同子項目使用唔同版本嘅同一依賴
2. 規則衝突 — 唔同子項目嘅規則互相矛盾
3. 資源衝突 — 檔案被多個子項目引用
4. 配置衝突 — 唔同子項目嘅配置唔一致

公式：C * D — 衝突 × 依賴 交叉分析
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class ConflictType(Enum):
    DEPENDENCY = "dependency"
    RULE = "rule"
    RESOURCE = "resource"
    CONFIG = "config"


class ConflictSeverity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Conflict:
    conflict_type: ConflictType
    severity: ConflictSeverity
    title: str
    description: str
    projects_involved: list[str]
    details: dict[str, Any] = field(default_factory=dict)
    resolution_suggestion: Optional[str] = None


@dataclass
class ConflictReport:
    timestamp: str
    total_conflicts: int
    by_type: dict[str, int]
    by_severity: dict[str, int]
    conflicts: list[Conflict]


class ConflictDetector:
    def __init__(self, projects_dir: str = "projects"):
        self.projects_dir = Path(projects_dir)
        self._dependency_cache: dict[str, dict[str, str]] = {}
        self._config_cache: dict[str, dict[str, Any]] = {}

    def detect(self) -> ConflictReport:
        from datetime import datetime
        
        conflicts = []
        
        conflicts.extend(self._detect_dependency_conflicts())
        conflicts.extend(self._detect_resource_conflicts())
        conflicts.extend(self._detect_config_conflicts())
        
        by_type: dict[str, int] = {}
        by_severity: dict[str, int] = {}
        
        for c in conflicts:
            type_key = c.conflict_type.value
            sev_key = c.severity.value
            by_type[type_key] = by_type.get(type_key, 0) + 1
            by_severity[sev_key] = by_severity.get(sev_key, 0) + 1
        
        return ConflictReport(
            timestamp=datetime.now().isoformat(),
            total_conflicts=len(conflicts),
            by_type=by_type,
            by_severity=by_severity,
            conflicts=conflicts,
        )

    def _detect_dependency_conflicts(self) -> list[Conflict]:
        conflicts = []
        
        if not self.projects_dir.exists():
            return conflicts
        
        dependencies: dict[str, dict[str, str]] = {}
        
        for project_dir in self.projects_dir.iterdir():
            if not project_dir.is_dir():
                continue
            
            project_name = project_dir.name
            deps = self._parse_dependencies(project_dir)
            dependencies[project_name] = deps
            self._dependency_cache[project_name] = deps
        
        package_versions: dict[str, dict[str, str]] = {}
        for project, deps in dependencies.items():
            for package, version in deps.items():
                if package not in package_versions:
                    package_versions[package] = {}
                package_versions[package][project] = version
        
        for package, project_versions in package_versions.items():
            unique_versions = set(project_versions.values())
            if len(unique_versions) > 1:
                conflicts.append(Conflict(
                    conflict_type=ConflictType.DEPENDENCY,
                    severity=ConflictSeverity.HIGH,
                    title=f"Dependency Version Conflict: {package}",
                    description=f"Package '{package}' has different versions across projects",
                    projects_involved=list(project_versions.keys()),
                    details={
                        "package": package,
                        "versions": project_versions,
                    },
                    resolution_suggestion=f"Align all projects to use the same version of '{package}'",
                ))
        
        return conflicts

    def _parse_dependencies(self, project_dir: Path) -> dict[str, str]:
        deps = {}
        
        requirements = project_dir / "requirements.txt"
        if requirements.exists():
            deps.update(self._parse_requirements(requirements))
        
        pyproject = project_dir / "pyproject.toml"
        if pyproject.exists():
            deps.update(self._parse_pyproject(pyproject))
        
        return deps

    def _parse_requirements(self, file_path: Path) -> dict[str, str]:
        deps = {}
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            for line in content.split("\n"):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                
                match = re.match(r"^([a-zA-Z0-9_-]+)\s*([=<>!]+)\s*([^\s]+)", line)
                if match:
                    deps[match.group(1)] = match.group(3)
                elif "==" in line:
                    parts = line.split("==")
                    if len(parts) == 2:
                        deps[parts[0].strip()] = parts[1].strip()
        except Exception:
            pass
        return deps

    def _parse_pyproject(self, file_path: Path) -> dict[str, str]:
        deps = {}
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            
            deps_pattern = r'"([a-zA-Z0-9_-]+)\s*([=<>!]+)\s*([^\"]+)"'
            for match in re.finditer(deps_pattern, content):
                deps[match.group(1)] = match.group(3)
        except Exception:
            pass
        return deps

    def _detect_resource_conflicts(self) -> list[Conflict]:
        conflicts = []
        
        if not self.projects_dir.exists():
            return conflicts
        
        shared_resources: dict[str, list[str]] = {}
        
        for project_dir in self.projects_dir.iterdir():
            if not project_dir.is_dir():
                continue
            
            project_name = project_dir.name
            
            for py_file in project_dir.rglob("*.py"):
                if ".venv" in str(py_file) or "__pycache__" in str(py_file):
                    continue
                
                try:
                    content = py_file.read_text(encoding="utf-8", errors="ignore")
                    
                    import_pattern = r"from\s+(\.\.+/+[^\s]+)|import\s+(\.\.+/+[^\s]+)"
                    for match in re.finditer(import_pattern, content):
                        resource = match.group(1) or match.group(2)
                        if resource:
                            if resource not in shared_resources:
                                shared_resources[resource] = []
                            shared_resources[resource].append(project_name)
                except Exception:
                    pass
        
        for resource, projects in shared_resources.items():
            if len(set(projects)) > 1:
                conflicts.append(Conflict(
                    conflict_type=ConflictType.RESOURCE,
                    severity=ConflictSeverity.MEDIUM,
                    title=f"Shared Resource: {resource}",
                    description=f"Resource '{resource}' is referenced by multiple projects",
                    projects_involved=list(set(projects)),
                    details={"resource": resource},
                    resolution_suggestion="Consider centralizing this resource or creating a shared module",
                ))
        
        return conflicts

    def _detect_config_conflicts(self) -> list[Conflict]:
        conflicts = []
        
        if not self.projects_dir.exists():
            return conflicts
        
        configs: dict[str, dict[str, Any]] = {}
        
        for project_dir in self.projects_dir.iterdir():
            if not project_dir.is_dir():
                continue
            
            project_name = project_dir.name
            config = self._parse_config(project_dir)
            configs[project_name] = config
            self._config_cache[project_name] = config
        
        return conflicts

    def _parse_config(self, project_dir: Path) -> dict[str, Any]:
        config = {}
        
        env_example = project_dir / ".env.example"
        if env_example.exists():
            try:
                content = env_example.read_text(encoding="utf-8", errors="ignore")
                for line in content.split("\n"):
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        key = line.split("=")[0].strip()
                        config[f"env.{key}"] = True
            except Exception:
                pass
        
        return config

    def get_dependency_summary(self) -> dict[str, Any]:
        all_deps: dict[str, set[str]] = {}
        
        for project, deps in self._dependency_cache.items():
            for package, version in deps.items():
                if package not in all_deps:
                    all_deps[package] = set()
                all_deps[package].add(f"{project}:{version}")
        
        return {
            "total_packages": len(all_deps),
            "packages": {k: list(v) for k, v in all_deps.items()},
        }

    def get_project_dependencies(self, project_name: str) -> dict[str, str]:
        return self._dependency_cache.get(project_name, {})
