from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger()

_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent


class EntropyDimension(Enum):
    CODE_DRIFT = "code_drift"
    DEPENDENCY_STALENESS = "dependency_staleness"
    CONFIG_CONFLICT = "config_conflict"
    FILE_MISSING = "file_missing"
    CONTEXT_STALENESS = "context_staleness"


class EntropyAlert(Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class EntropyReading:
    project_name: str
    dimension: EntropyDimension
    value: float
    timestamp: datetime
    details: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_name": self.project_name,
            "dimension": self.dimension.value,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details,
        }


@dataclass
class EntropyReport:
    project_name: str
    total_entropy: float
    alert_level: EntropyAlert
    readings: list[EntropyReading] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_name": self.project_name,
            "total_entropy": self.total_entropy,
            "alert_level": self.alert_level.value,
            "readings": [r.to_dict() for r in self.readings],
            "timestamp": self.timestamp.isoformat(),
        }


class EntropyWatchdog:
    DRIFT_THRESHOLD_DAYS = 7
    DEPENDENCY_STALE_DAYS = 30
    CONTEXT_STALE_DAYS = 7
    CONFIG_FILES = (".env", "config.py", "settings.py")
    REQUIRED_FILES = ("AGENTS.md", ".harnessing-bridge.md", ".trae/rules/project_rules.md")

    def __init__(self, project_root: Path | None = None) -> None:
        self.project_root = project_root or _PROJECT_ROOT
        self.thresholds = {"critical": 0.8, "high": 0.6, "medium": 0.4}
        self.dimension_weights = {
            EntropyDimension.CODE_DRIFT: 0.25,
            EntropyDimension.DEPENDENCY_STALENESS: 0.20,
            EntropyDimension.CONFIG_CONFLICT: 0.20,
            EntropyDimension.FILE_MISSING: 0.15,
            EntropyDimension.CONTEXT_STALENESS: 0.20,
        }

    def scan_project(self, project_name: str) -> EntropyReport:
        project_dir = self._find_project_dir(project_name)
        now = datetime.now(timezone.utc)

        if project_dir is None:
            readings = [
                EntropyReading(
                    project_name=project_name,
                    dimension=dim,
                    value=1.0,
                    timestamp=now,
                    details="project directory not found",
                )
                for dim in EntropyDimension
            ]
            total = 1.0
            return EntropyReport(
                project_name=project_name,
                total_entropy=total,
                alert_level=self.get_alert_level(total),
                readings=readings,
                timestamp=now,
            )

        readings = [
            self._measure_code_drift(project_name, project_dir, now),
            self._measure_dependency_staleness(project_name, project_dir, now),
            self._measure_config_conflict(project_name, project_dir, now),
            self._measure_file_missing(project_name, project_dir, now),
            self._measure_context_staleness(project_name, project_dir, now),
        ]

        total = sum(
            r.value * self.dimension_weights[r.dimension] for r in readings
        )
        total = min(max(total, 0.0), 1.0)

        return EntropyReport(
            project_name=project_name,
            total_entropy=total,
            alert_level=self.get_alert_level(total),
            readings=readings,
            timestamp=now,
        )

    def scan_all(self, project_names: list[str]) -> list[EntropyReport]:
        reports = [self.scan_project(name) for name in project_names]
        return sorted(reports, key=lambda r: r.total_entropy, reverse=True)

    def get_alert_level(self, entropy: float) -> EntropyAlert:
        if entropy > self.thresholds["critical"]:
            return EntropyAlert.CRITICAL
        if entropy > self.thresholds["high"]:
            return EntropyAlert.HIGH
        if entropy > self.thresholds["medium"]:
            return EntropyAlert.MEDIUM
        return EntropyAlert.LOW

    def should_intervene(self, report: EntropyReport) -> bool:
        return report.alert_level in (EntropyAlert.CRITICAL, EntropyAlert.HIGH)

    def _find_project_dir(self, project_name: str) -> Path | None:
        projects_dir = self.project_root / "projects"
        if not projects_dir.exists():
            return None

        for match in projects_dir.rglob(project_name):
            if match.is_dir():
                return match

        return None

    def _measure_code_drift(
        self, project_name: str, project_dir: Path, now: datetime
    ) -> EntropyReading:
        py_files = list(project_dir.rglob("*.py"))
        if not py_files:
            return EntropyReading(
                project_name=project_name,
                dimension=EntropyDimension.CODE_DRIFT,
                value=0.5,
                timestamp=now,
                details="no python files found",
            )

        recent_count = 0
        for f in py_files:
            try:
                mtime = datetime.fromtimestamp(os.path.getmtime(f), tz=timezone.utc)
                if (now - mtime).days <= self.DRIFT_THRESHOLD_DAYS:
                    recent_count += 1
            except OSError:
                continue

        ratio = recent_count / len(py_files)

        if ratio > 0.5:
            value = 0.1
            details = f"most files recent ({recent_count}/{len(py_files)})"
        elif ratio > 0.0:
            value = 0.5
            details = f"mixed recency ({recent_count}/{len(py_files)} recent)"
        else:
            value = 0.9
            details = f"all files older than {self.DRIFT_THRESHOLD_DAYS} days"

        return EntropyReading(
            project_name=project_name,
            dimension=EntropyDimension.CODE_DRIFT,
            value=value,
            timestamp=now,
            details=details,
        )

    def _measure_dependency_staleness(
        self, project_name: str, project_dir: Path, now: datetime
    ) -> EntropyReading:
        dep_files = list(project_dir.rglob("requirements.txt")) + list(
            project_dir.rglob("package.json")
        )

        if not dep_files:
            return EntropyReading(
                project_name=project_name,
                dimension=EntropyDimension.DEPENDENCY_STALENESS,
                value=0.5,
                timestamp=now,
                details="no dependency files found",
            )

        oldest_days = 0
        for f in dep_files:
            try:
                mtime = datetime.fromtimestamp(os.path.getmtime(f), tz=timezone.utc)
                age_days = (now - mtime).days
                if age_days > oldest_days:
                    oldest_days = age_days
            except OSError:
                continue

        if oldest_days > self.DEPENDENCY_STALE_DAYS:
            value = 0.9
            details = f"dependency file(s) older than {self.DEPENDENCY_STALE_DAYS} days ({oldest_days}d)"
        else:
            value = 0.1
            details = f"dependency file(s) recent ({oldest_days}d old)"

        return EntropyReading(
            project_name=project_name,
            dimension=EntropyDimension.DEPENDENCY_STALENESS,
            value=value,
            timestamp=now,
            details=details,
        )

    def _measure_config_conflict(
        self, project_name: str, project_dir: Path, now: datetime
    ) -> EntropyReading:
        config_count = 0
        found: list[str] = []
        for cfg_name in self.CONFIG_FILES:
            for match in project_dir.rglob(cfg_name):
                if match.is_file():
                    config_count += 1
                    found.append(match.name)

        if config_count > 2:
            value = 0.9
            details = f"{config_count} config files: {', '.join(found)}"
        elif config_count >= 1:
            value = 0.2
            details = f"{config_count} config file(s): {', '.join(found)}"
        else:
            value = 0.0
            details = "no config files"

        return EntropyReading(
            project_name=project_name,
            dimension=EntropyDimension.CONFIG_CONFLICT,
            value=value,
            timestamp=now,
            details=details,
        )

    def _measure_file_missing(
        self, project_name: str, project_dir: Path, now: datetime
    ) -> EntropyReading:
        missing: list[str] = []
        for req in self.REQUIRED_FILES:
            target = project_dir / req
            if not target.exists():
                matches = list(project_dir.rglob(req))
                if not matches:
                    missing.append(req)

        value = len(missing) * 0.33
        value = min(value, 1.0)

        if missing:
            details = f"missing: {', '.join(missing)}"
        else:
            details = "all required files present"

        return EntropyReading(
            project_name=project_name,
            dimension=EntropyDimension.FILE_MISSING,
            value=value,
            timestamp=now,
            details=details,
        )

    def _measure_context_staleness(
        self, project_name: str, project_dir: Path, now: datetime
    ) -> EntropyReading:
        bridge_file = project_dir / ".harnessing-bridge.md"

        if not bridge_file.exists():
            matches = list(project_dir.rglob(".harnessing-bridge.md"))
            if matches:
                bridge_file = matches[0]
            else:
                return EntropyReading(
                    project_name=project_name,
                    dimension=EntropyDimension.CONTEXT_STALENESS,
                    value=1.0,
                    timestamp=now,
                    details=".harnessing-bridge.md missing",
                )

        try:
            mtime = datetime.fromtimestamp(
                os.path.getmtime(bridge_file), tz=timezone.utc
            )
            age_days = (now - mtime).days
        except OSError:
            return EntropyReading(
                project_name=project_name,
                dimension=EntropyDimension.CONTEXT_STALENESS,
                value=1.0,
                timestamp=now,
                details="cannot read bridge file mtime",
            )

        if age_days > self.CONTEXT_STALE_DAYS:
            value = 0.9
            details = f"bridge file {age_days}d old (>{self.CONTEXT_STALE_DAYS}d)"
        else:
            value = 0.1
            details = f"bridge file recent ({age_days}d old)"

        return EntropyReading(
            project_name=project_name,
            dimension=EntropyDimension.CONTEXT_STALENESS,
            value=value,
            timestamp=now,
            details=details,
        )
