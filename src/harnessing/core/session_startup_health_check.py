from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog

from harnessing.core.auto_report_engine import AutoReportEngine
from harnessing.core.proactive_consistency_scanner import ConsistencyGap, ProactiveConsistencyScanner, Severity
from harnessing.core.subproject_health_monitor import HealthStatus, ProjectHealth, SubProjectHealthMonitor

logger = structlog.get_logger()

_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent


@dataclass
class StartupHealthSummary:
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    total_gaps: int = 0
    stale_projects: list[str] = field(default_factory=list)
    high_risk_projects: list[str] = field(default_factory=list)
    total_projects: int = 0
    active_projects: int = 0
    recommended_actions: list[str] = field(default_factory=list)
    consistency_gaps: list[ConsistencyGap] = field(default_factory=list)
    project_healths: list[ProjectHealth] = field(default_factory=list)
    full_report: str = ""
    timestamp: str = ""
    auto_fixed: list[str] = field(default_factory=list)
    as3e_report: dict[str, Any] | None = None
    stale_count: int = 0
    specs_status: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        result = {
            "critical_count": self.critical_count,
            "high_count": self.high_count,
            "medium_count": self.medium_count,
            "low_count": self.low_count,
            "total_gaps": self.total_gaps,
            "stale_projects": self.stale_projects,
            "high_risk_projects": self.high_risk_projects,
            "total_projects": self.total_projects,
            "active_projects": self.active_projects,
            "recommended_actions": self.recommended_actions,
            "auto_fixed": self.auto_fixed,
            "timestamp": self.timestamp,
        }
        if self.as3e_report is not None:
            result["as3e_report"] = self.as3e_report
        result["stale_count"] = self.stale_count
        if self.specs_status:
            result["specs_status"] = self.specs_status
        return result


class SessionStartupHealthCheck:

    def __init__(self, project_root: Path | None = None) -> None:
        self.project_root = project_root or _PROJECT_ROOT
        self._scanner = ProactiveConsistencyScanner(project_root=self.project_root)
        self._monitor = SubProjectHealthMonitor(self.project_root)
        self._report_engine = AutoReportEngine(project_root=self.project_root)

    def run_startup_check(self) -> StartupHealthSummary:
        logger.info("session_startup_health_check_start", project_root=str(self.project_root))

        consistency_gaps = self._scanner.scan()
        project_healths = self._monitor.scan()
        full_report = self._report_engine.generate_report(consistency_gaps, project_healths)

        severity_counts: dict[str, int] = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for g in consistency_gaps:
            severity_counts[g.severity.value] += 1

        stale_projects = [h.name for h in project_healths if h.status == HealthStatus.STALE]
        high_risk_projects = [h.name for h in project_healths if h.status == HealthStatus.HIGH_RISK]
        active_projects = sum(1 for h in project_healths if h.status == HealthStatus.ACTIVE)

        recommended_actions = self._build_recommended_actions(consistency_gaps, project_healths)

        auto_fixed = self._auto_fix_critical(consistency_gaps)

        try:
            from harnessing.core.autonomous_subproject_state_space_engine import AS3E
            as3e = AS3E(project_root=self.project_root)
            as3e_report = as3e.on_session_startup()
            summary_as3e_report = as3e_report.to_dict()
            auto_fixed.extend(as3e_report.auto_interventions)
            for proj in as3e_report.high_entropy_projects:
                if proj not in high_risk_projects:
                    high_risk_projects.append(proj)
        except Exception as e:
            logger.warning("as3e_scan_failed", error=str(e))
            summary_as3e_report = None

        specs_status = self.run_specs_status_scan()
        stale_count = specs_status.get("stale_count", 0)

        summary = StartupHealthSummary(
            critical_count=severity_counts["CRITICAL"],
            high_count=severity_counts["HIGH"],
            medium_count=severity_counts["MEDIUM"],
            low_count=severity_counts["LOW"],
            total_gaps=len(consistency_gaps),
            stale_projects=stale_projects,
            high_risk_projects=high_risk_projects,
            total_projects=len(project_healths),
            active_projects=active_projects,
            recommended_actions=recommended_actions,
            consistency_gaps=consistency_gaps,
            project_healths=project_healths,
            full_report=full_report,
            timestamp=datetime.now(timezone.utc).isoformat(),
            auto_fixed=auto_fixed,
            as3e_report=summary_as3e_report,
            stale_count=stale_count,
            specs_status=specs_status,
        )

        logger.info(
            "session_startup_health_check_complete",
            critical=summary.critical_count,
            high=summary.high_count,
            total_gaps=summary.total_gaps,
            stale=len(stale_projects),
            high_risk=len(high_risk_projects),
            auto_fixed=len(auto_fixed),
        )

        return summary

    def format_startup_summary(self, summary: StartupHealthSummary) -> str:
        lines: list[str] = []

        lines.append("## 🔍 Session 啟動健康檢查")
        lines.append("")
        lines.append(f"**時間**：{summary.timestamp}")
        lines.append("")

        if summary.critical_count == 0 and summary.high_count == 0 and not summary.stale_projects and not summary.high_risk_projects:
            lines.append("✅ **系統健康**：無 CRITICAL/HIGH 一致性缺口，無 STALE/HIGH_RISK 子項目。")
            lines.append("")
            return "\n".join(lines)

        lines.append("### 一致性缺口")
        lines.append("")
        lines.append("| 嚴重程度 | 數量 |")
        lines.append("|----------|------|")
        lines.append(f"| 🔴 CRITICAL | {summary.critical_count} |")
        lines.append(f"| 🟠 HIGH | {summary.high_count} |")
        lines.append(f"| 🟡 MEDIUM | {summary.medium_count} |")
        lines.append(f"| 🟢 LOW | {summary.low_count} |")
        lines.append("")

        lines.append("### 子項目狀態")
        lines.append("")
        lines.append(f"- 總項目數：{summary.total_projects}")
        lines.append(f"- 🟢 ACTIVE：{summary.active_projects}")
        lines.append(f"- 🟡 STALE：{len(summary.stale_projects)}")
        lines.append(f"- 🔴 HIGH_RISK：{len(summary.high_risk_projects)}")
        lines.append("")

        if summary.stale_projects:
            lines.append("**STALE 項目**：" + "、".join(summary.stale_projects))
            lines.append("")

        if summary.high_risk_projects:
            lines.append("**HIGH_RISK 項目**：" + "、".join(summary.high_risk_projects))
            lines.append("")

        if summary.specs_status and "error" not in summary.specs_status:
            lines.append("### 📄 Specs 狀態")
            lines.append("")
            lines.append(f"- 總 Specs：{summary.specs_status.get('total_specs', 0)}")
            lines.append(f"- ✅ 已完成：{summary.specs_status.get('completed_count', 0)}")
            lines.append(f"- 🔄 進行中：{summary.specs_status.get('in_progress_count', 0)}")
            lines.append(f"- ⏳ 待處理：{summary.specs_status.get('pending_count', 0)}")
            lines.append(f"- 🟡 過期：{summary.stale_count}")
            lines.append("")
            if summary.stale_count > 5:
                lines.append("⚠️ **警告**：過期 Specs 數量超過 5 個，建議盡快更新！")
                lines.append("")

        if summary.auto_fixed:
            lines.append("### 🔄 自動修復")
            lines.append("")
            for fix in summary.auto_fixed:
                lines.append(f"- ✅ {fix}")
            lines.append("")

        if summary.recommended_actions:
            lines.append("### 📋 建議行動")
            lines.append("")
            for action in summary.recommended_actions:
                lines.append(f"- {action}")
            lines.append("")

        return "\n".join(lines)

    def run_specs_status_scan(self) -> dict[str, Any]:
        try:
            from scripts.specs_status_scanner import scan_all_specs

            result = scan_all_specs(str(self.project_root / ".trae" / "specs"))
            return result
        except Exception as e:
            logger.warning("specs_status_scan_failed", error=str(e))
            return {"error": "specs_status_scanner not available", "stale_count": 0}

    def _build_recommended_actions(
        self,
        gaps: list[ConsistencyGap],
        healths: list[ProjectHealth],
    ) -> list[str]:
        actions: list[str] = []

        critical_gaps = [g for g in gaps if g.severity == Severity.CRITICAL]
        if critical_gaps:
            actions.append(f"🔴 立即修復 {len(critical_gaps)} 個 CRITICAL 一致性缺口")

        high_risk = [h for h in healths if h.status == HealthStatus.HIGH_RISK]
        for h in high_risk:
            actions.append(f"🔴 處理 {h.name} 嘅 HIGH_RISK 痛點")

        high_gaps = [g for g in gaps if g.severity == Severity.HIGH]
        if high_gaps:
            actions.append(f"🟠 修復 {len(high_gaps)} 個 HIGH 一致性缺口")

        stale = [h for h in healths if h.status == HealthStatus.STALE]
        for h in stale:
            days = (datetime.now() - h.last_updated).days if h.last_updated else 0
            actions.append(f"🟡 檢查 {h.name}（已 {days} 天未更新）")

        no_tasks = [
            h for h in healths
            if not h.has_tasks and h.status in (HealthStatus.ACTIVE, HealthStatus.HIGH_RISK)
        ]
        for h in no_tasks:
            actions.append(f"📋 為 {h.name} 建立 tasks.md")

        return actions

    def _auto_fix_critical(self, gaps: list[ConsistencyGap]) -> list[str]:
        fixed: list[str] = []
        critical_gaps = [g for g in gaps if g.severity == Severity.CRITICAL]

        if not critical_gaps:
            return fixed

        for gap in critical_gaps:
            if gap.gap_type == "modelfile_sync":
                logger.warning(
                    "critical_modelfile_sync_gap_detected",
                    description=gap.description,
                    suggested_fix=gap.suggested_fix,
                )
                fixed.append(f"偵測到 Modelfile 同步缺口：{gap.description}（需要手動執行 sync_beeverse_modelfile.py）")

        return fixed


def main() -> None:
    health_check = SessionStartupHealthCheck()
    summary = health_check.run_startup_check()
    formatted = health_check.format_startup_summary(summary)
    print(formatted)

    if summary.critical_count > 0:
        logger.error("startup_check_critical_issues", count=summary.critical_count)
    elif summary.high_count > 0:
        logger.warning("startup_check_high_issues", count=summary.high_count)
    else:
        logger.info("startup_check_passed")


if __name__ == "__main__":
    main()
