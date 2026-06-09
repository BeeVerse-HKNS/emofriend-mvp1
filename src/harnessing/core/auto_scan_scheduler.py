"""
AutoScanScheduler — 內置定時掃描器

使用 Python threading.Timer 實現零外部依賴的自動掃描。
支持可配置掃描間隔、回調函數、優雅停止。

公式：log(M * A) — 抽象化監控 × 自動化
"""

import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional

from .project_scanner import ProjectScanner


class ScanTrigger(Enum):
    SCHEDULED = "scheduled"
    MANUAL = "manual"
    STARTUP = "startup"


@dataclass
class ScanResult:
    trigger: ScanTrigger
    timestamp: datetime
    projects_scanned: int
    bugs_found: int
    alerts_generated: int
    duration_seconds: float
    details: dict[str, Any] = field(default_factory=dict)


class AutoScanScheduler:
    def __init__(
        self,
        scan_callback: Optional[Callable[[ScanResult], None]] = None,
        interval_seconds: int = 300,
        projects_dir: str = "projects",
    ):
        self.interval_seconds = interval_seconds
        self.projects_dir = projects_dir
        self.scan_callback = scan_callback
        self.scanner = ProjectScanner(projects_dir)
        
        self._timer: Optional[threading.Timer] = None
        self._running = False
        self._lock = threading.Lock()
        self._last_scan: Optional[ScanResult] = None
        self._scan_history: list[ScanResult] = []
        self._max_history = 100

    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            self._running = True
            self._schedule_next_scan()
            self._run_scan(ScanTrigger.STARTUP)

    def stop(self) -> None:
        with self._lock:
            if not self._running:
                return
            self._running = False
            if self._timer:
                self._timer.cancel()
                self._timer = None

    def trigger_manual_scan(self) -> ScanResult:
        return self._run_scan(ScanTrigger.MANUAL)

    def _schedule_next_scan(self) -> None:
        if not self._running:
            return
        self._timer = threading.Timer(
            self.interval_seconds,
            self._scheduled_scan
        )
        self._timer.daemon = True
        self._timer.start()

    def _scheduled_scan(self) -> None:
        self._run_scan(ScanTrigger.SCHEDULED)
        with self._lock:
            if self._running:
                self._schedule_next_scan()

    def _run_scan(self, trigger: ScanTrigger) -> ScanResult:
        start_time = time.time()
        timestamp = datetime.now()
        
        try:
            projects = self.scanner.scan_all()
            projects_scanned = len(projects)
            
            bugs_found = 0
            alerts_generated = 0
            
            for project in projects:
                if project.status in ["error", "stalled"]:
                    alerts_generated += 1
                if project.missing_agents_md:
                    alerts_generated += 1
            
            duration = time.time() - start_time
            
            result = ScanResult(
                trigger=trigger,
                timestamp=timestamp,
                projects_scanned=projects_scanned,
                bugs_found=bugs_found,
                alerts_generated=alerts_generated,
                duration_seconds=duration,
                details={
                    "projects": [
                        {
                            "name": p.name,
                            "status": p.status.value if hasattr(p.status, 'value') else str(p.status),
                            "last_update": str(p.last_update) if p.last_update else None,
                        }
                        for p in projects[:10]
                    ]
                }
            )
            
        except Exception as e:
            duration = time.time() - start_time
            result = ScanResult(
                trigger=trigger,
                timestamp=timestamp,
                projects_scanned=0,
                bugs_found=0,
                alerts_generated=0,
                duration_seconds=duration,
                details={"error": str(e)}
            )
        
        self._last_scan = result
        self._scan_history.append(result)
        if len(self._scan_history) > self._max_history:
            self._scan_history = self._scan_history[-self._max_history:]
        
        if self.scan_callback:
            try:
                self.scan_callback(result)
            except Exception:
                pass
        
        return result

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def last_scan(self) -> Optional[ScanResult]:
        return self._last_scan

    @property
    def scan_history(self) -> list[ScanResult]:
        return self._scan_history.copy()

    def get_stats(self) -> dict[str, Any]:
        if not self._scan_history:
            return {
                "total_scans": 0,
                "avg_duration": 0,
                "total_projects_scanned": 0,
                "total_bugs_found": 0,
                "total_alerts": 0,
            }
        
        total = len(self._scan_history)
        return {
            "total_scans": total,
            "avg_duration": sum(s.duration_seconds for s in self._scan_history) / total,
            "total_projects_scanned": sum(s.projects_scanned for s in self._scan_history),
            "total_bugs_found": sum(s.bugs_found for s in self._scan_history),
            "total_alerts": sum(s.alerts_generated for s in self._scan_history),
            "scheduled_scans": sum(1 for s in self._scan_history if s.trigger == ScanTrigger.SCHEDULED),
            "manual_scans": sum(1 for s in self._scan_history if s.trigger == ScanTrigger.MANUAL),
        }
