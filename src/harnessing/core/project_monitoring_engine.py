"""
ProjectMonitoringEngine - Master Agent 項目監控引擎

功能：
1. 定時掃描（可配置間隔）
2. 異常偵測（停滯項目、過期依賴）
3. 趨勢分析（活躍度變化）

公式：P * M + K — 預測 × 監控 + 知識

相關規則：Rule 67 (Master Orchestrator 調度規則)
"""

from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from .project_scanner import ProjectScanner, SubProject

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertType(Enum):
    PROJECT_STALLED = "project_stalled"
    MISSING_AGENTS_MD = "missing_agents_md"
    HIGH_ERROR_COUNT = "high_error_count"
    DEPENDENCY_OUTDATED = "dependency_outdated"
    NO_RECENT_COMMITS = "no_recent_commits"
    PROGRESS_REGRESSION = "progress_regression"


@dataclass
class Alert:
    alert_type: AlertType
    severity: AlertSeverity
    project_name: str
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "alert_type": self.alert_type.value,
            "severity": self.severity.value,
            "project_name": self.project_name,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details,
        }


@dataclass
class MonitoringSnapshot:
    timestamp: datetime
    total_projects: int
    active_projects: int
    stalled_projects: int
    alerts: list[Alert]
    project_statuses: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "total_projects": self.total_projects,
            "active_projects": self.active_projects,
            "stalled_projects": self.stalled_projects,
            "alerts": [a.to_dict() for a in self.alerts],
            "project_statuses": self.project_statuses,
        }


class ProjectMonitoringEngine:
    """
    Master Agent 項目監控引擎

    持續監控所有子項目狀態，偵測異常並生成告警。
    """

    DEFAULT_SCAN_INTERVAL = 300
    STALLED_THRESHOLD_DAYS = 7
    ERROR_COUNT_THRESHOLD = 10

    def __init__(
        self,
        scanner: ProjectScanner,
        scan_interval: int = DEFAULT_SCAN_INTERVAL,
        stalled_threshold_days: int = STALLED_THRESHOLD_DAYS,
        alert_callback: Callable[[Alert], None] | None = None,
    ):
        self.scanner = scanner
        self.scan_interval = scan_interval
        self.stalled_threshold_days = stalled_threshold_days
        self.alert_callback = alert_callback

        self._snapshots: list[MonitoringSnapshot] = []
        self._alerts: list[Alert] = []
        self._running = False
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

    def start(self) -> None:
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self._thread.start()
        logger.info("Monitoring engine started")

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Monitoring engine stopped")

    def _monitoring_loop(self) -> None:
        while self._running:
            try:
                self.scan_and_check()
            except Exception as e:
                logger.error(f"Monitoring error: {e}")

            time.sleep(self.scan_interval)

    def scan_and_check(self) -> MonitoringSnapshot:
        projects = self.scanner.scan_all(force_refresh=True)
        alerts: list[Alert] = []

        for p in projects:
            alerts.extend(self._check_project(p))

        snapshot = MonitoringSnapshot(
            timestamp=datetime.now(),
            total_projects=len(projects),
            active_projects=sum(1 for p in projects if p.status.value == "active"),
            stalled_projects=sum(1 for p in projects if p.status.value == "stalled"),
            alerts=alerts,
            project_statuses={p.name: p.status.value for p in projects},
        )

        with self._lock:
            self._snapshots.append(snapshot)
            self._alerts.extend(alerts)

            if len(self._snapshots) > 100:
                self._snapshots = self._snapshots[-100:]
            if len(self._alerts) > 1000:
                self._alerts = self._alerts[-1000:]

        for alert in alerts:
            if self.alert_callback:
                self.alert_callback(alert)
            self._log_alert(alert)

        return snapshot

    def _check_project(self, project: SubProject) -> list[Alert]:
        alerts: list[Alert] = []

        if not project.has_agents_md:
            alerts.append(
                Alert(
                    alert_type=AlertType.MISSING_AGENTS_MD,
                    severity=AlertSeverity.WARNING,
                    project_name=project.name,
                    message=f"項目 {project.name} 缺少 AGENTS.md 文件",
                    details={"path": str(project.path)},
                )
            )

        if project.last_update:
            days_since = (datetime.now() - project.last_update).days
            if days_since > self.stalled_threshold_days:
                alerts.append(
                    Alert(
                        alert_type=AlertType.PROJECT_STALLED,
                        severity=AlertSeverity.WARNING if days_since < 14 else AlertSeverity.ERROR,
                        project_name=project.name,
                        message=f"項目 {project.name} 已停滯 {days_since} 天",
                        details={"days_stalled": days_since, "last_update": project.last_update.isoformat()},
                    )
                )

        if project.error_count > self.ERROR_COUNT_THRESHOLD:
            alerts.append(
                Alert(
                    alert_type=AlertType.HIGH_ERROR_COUNT,
                    severity=AlertSeverity.ERROR,
                    project_name=project.name,
                    message=f"項目 {project.name} 錯誤計數過高：{project.error_count}",
                    details={"error_count": project.error_count},
                )
            )

        return alerts

    def _log_alert(self, alert: Alert) -> None:
        log_msg = f"[{alert.severity.value.upper()}] {alert.alert_type.value}: {alert.message}"
        if alert.severity == AlertSeverity.CRITICAL:
            logger.critical(log_msg)
        elif alert.severity == AlertSeverity.ERROR:
            logger.error(log_msg)
        elif alert.severity == AlertSeverity.WARNING:
            logger.warning(log_msg)
        else:
            logger.info(log_msg)

    def get_current_status(self) -> MonitoringSnapshot | None:
        with self._lock:
            return self._snapshots[-1] if self._snapshots else None

    def get_alerts(
        self,
        severity: AlertSeverity | None = None,
        alert_type: AlertType | None = None,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[Alert]:
        with self._lock:
            alerts = self._alerts.copy()

        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        if alert_type:
            alerts = [a for a in alerts if a.alert_type == alert_type]
        if since:
            alerts = [a for a in alerts if a.timestamp >= since]

        return alerts[-limit:]

    def get_trend_analysis(self, hours: int = 24) -> dict[str, Any]:
        cutoff = datetime.now() - timedelta(hours=hours)

        with self._lock:
            relevant_snapshots = [s for s in self._snapshots if s.timestamp >= cutoff]

        if not relevant_snapshots:
            return {"error": "No data available for trend analysis"}

        first = relevant_snapshots[0]
        last = relevant_snapshots[-1]

        return {
            "period_hours": hours,
            "snapshot_count": len(relevant_snapshots),
            "active_projects_change": last.active_projects - first.active_projects,
            "stalled_projects_change": last.stalled_projects - first.stalled_projects,
            "total_alerts": sum(len(s.alerts) for s in relevant_snapshots),
            "first_snapshot": first.to_dict(),
            "last_snapshot": last.to_dict(),
        }

    def export_monitoring_data(self, output_path: Path | str) -> Path:
        output_path = Path(output_path)

        with self._lock:
            data = {
                "export_time": datetime.now().isoformat(),
                "snapshots": [s.to_dict() for s in self._snapshots],
                "alerts": [a.to_dict() for a in self._alerts],
                "trend": self.get_trend_analysis(),
            }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

        return output_path

    def is_running(self) -> bool:
        return self._running


def create_monitoring_engine(
    root_path: Path | str,
    scan_interval: int = 300,
    alert_callback: Callable[[Alert], None] | None = None,
) -> ProjectMonitoringEngine:
    from .project_scanner import ProjectScanner

    scanner = ProjectScanner(root_path)
    return ProjectMonitoringEngine(scanner, scan_interval=scan_interval, alert_callback=alert_callback)


if __name__ == "__main__":
    import sys

    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()

    def print_alert(alert: Alert) -> None:
        print(f"[{alert.severity.value.upper()}] {alert.message}")

    engine = create_monitoring_engine(root, alert_callback=print_alert)

    print("執行一次性掃描...")
    snapshot = engine.scan_and_check()

    print(f"\n掃描結果：")
    print(f"  總項目：{snapshot.total_projects}")
    print(f"  活躍項目：{snapshot.active_projects}")
    print(f"  停滯項目：{snapshot.stalled_projects}")
    print(f"  告警數量：{len(snapshot.alerts)}")

    if snapshot.alerts:
        print("\n告警列表：")
        for alert in snapshot.alerts:
            print(f"  [{alert.severity.value}] {alert.project_name}: {alert.message}")
