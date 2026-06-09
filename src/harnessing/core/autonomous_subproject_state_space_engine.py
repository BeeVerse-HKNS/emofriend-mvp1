from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog

from harnessing.core.entropy_watchdog import EntropyAlert, EntropyReport, EntropyWatchdog
from harnessing.core.hidden_state_matrix import HiddenStateMatrix, SubprojectHiddenState
from harnessing.core.minimal_intervention_engine import Intervention, MinimalInterventionEngine
from harnessing.core.proactive_context_preloader import ProactiveContextPreloader
from harnessing.core.superposition_coordinator import CollapseEvent, SuperpositionCoordinator

logger = structlog.get_logger()

_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent


@dataclass
class AS3ESessionReport:
    timestamp: datetime
    total_projects: int
    high_entropy_projects: list[str]
    critical_alerts: list[str]
    auto_interventions: list[dict]
    preload_summary: str
    recommended_actions: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "total_projects": self.total_projects,
            "high_entropy_projects": self.high_entropy_projects,
            "critical_alerts": self.critical_alerts,
            "auto_interventions": self.auto_interventions,
            "preload_summary": self.preload_summary,
            "recommended_actions": self.recommended_actions,
        }


class AS3E:
    def __init__(self, project_root: Path | None = None) -> None:
        self.project_root = project_root or _PROJECT_ROOT
        self._state_matrix = HiddenStateMatrix(self.project_root)
        self._entropy_watchdog = EntropyWatchdog(self.project_root)
        self._coordinator = SuperpositionCoordinator()
        self._intervention_engine = MinimalInterventionEngine()
        self._preloader = ProactiveContextPreloader(self.project_root)

    def on_session_startup(self) -> AS3ESessionReport:
        now = datetime.now(timezone.utc)

        discovered = self._state_matrix.discover_subprojects()
        logger.info("as3e_startup_discovered", count=len(discovered))

        entropy_reports = self._entropy_watchdog.scan_all(discovered)
        entropy_map: dict[str, float] = {}
        for report in entropy_reports:
            entropy_map[report.project_name] = report.total_entropy

        self._coordinator.register_all(discovered, entropy_map)

        for report in entropy_reports:
            self._state_matrix.update_state(
                report.project_name,
                entropy_value=report.total_entropy,
                health_score=1.0 - report.total_entropy,
            )

        collapse_events = self._coordinator.check_collapse()

        auto_interventions: list[dict] = []
        critical_alerts: list[str] = []
        high_entropy_projects: list[str] = []

        for report in entropy_reports:
            if report.alert_level == EntropyAlert.CRITICAL:
                critical_alerts.append(
                    f"{report.project_name}: entropy={report.total_entropy:.2f}"
                )
            if report.total_entropy >= 0.6:
                high_entropy_projects.append(report.project_name)

            if self._entropy_watchdog.should_intervene(report):
                dimensions: dict[str, float] = {}
                for reading in report.readings:
                    dimensions[reading.dimension.value] = reading.value

                intervention = self._intervention_engine.select_intervention(
                    report.project_name,
                    report.total_entropy,
                    dimensions,
                )
                if intervention is not None:
                    executed = self._intervention_engine.execute_intervention(intervention)
                    self._state_matrix.record_intervention(
                        report.project_name, auto=executed.executed
                    )
                    auto_interventions.append(executed.to_dict())

                    for event in collapse_events:
                        if event.project_name == report.project_name:
                            self._coordinator.complete_collapse(
                                report.project_name,
                                [executed.leverage_point.name],
                            )
                            break

        self._preloader.preload_high_entropy(entropy_map)

        last_active_times: dict[str, datetime] = {}
        for name in discovered:
            state = self._state_matrix.get_state(name)
            if state is not None:
                last_active_times[name] = state.last_active_time

        startup_context = self._preloader.generate_startup_context(
            entropy_map, last_active_times
        )

        recommended_actions: list[str] = []
        for alert in critical_alerts:
            recommended_actions.append(f"URGENT: Review {alert}")
        for name in high_entropy_projects:
            recommended_actions.append(f"Scan and address high entropy in {name}")
        stale = self._state_matrix.get_stale_states()
        for state in stale:
            recommended_actions.append(f"Check stale project: {state.name}")
        if not recommended_actions:
            recommended_actions.append("All projects healthy — no action needed")

        report = AS3ESessionReport(
            timestamp=now,
            total_projects=len(discovered),
            high_entropy_projects=high_entropy_projects,
            critical_alerts=critical_alerts,
            auto_interventions=auto_interventions,
            preload_summary=startup_context,
            recommended_actions=recommended_actions,
        )

        logger.info(
            "as3e_session_startup_complete",
            total_projects=report.total_projects,
            high_entropy=len(report.high_entropy_projects),
            critical=len(report.critical_alerts),
            interventions=len(report.auto_interventions),
        )

        return report

    def on_session_end(self) -> None:
        self._state_matrix.save_all()
        logger.info("as3e_session_end", states_saved=len(self._state_matrix.get_all_states()))

    def on_user_action(self, project_name: str, action: str = "interact") -> Intervention | None:
        self._state_matrix.record_interaction(project_name)
        logger.info("as3e_user_action", project=project_name, action=action)

        report = self._entropy_watchdog.scan_project(project_name)
        self._state_matrix.update_state(
            project_name,
            entropy_value=report.total_entropy,
            health_score=1.0 - report.total_entropy,
        )
        self._coordinator.update_entropy(project_name, report.total_entropy)

        if not self._entropy_watchdog.should_intervene(report):
            return None

        dimensions: dict[str, float] = {}
        for reading in report.readings:
            dimensions[reading.dimension.value] = reading.value

        intervention = self._intervention_engine.select_intervention(
            project_name, report.total_entropy, dimensions
        )
        if intervention is None:
            return None

        executed = self._intervention_engine.execute_intervention(intervention)
        self._state_matrix.record_intervention(project_name, auto=executed.executed)

        self._preloader.invalidate_cache(project_name)

        logger.info(
            "as3e_user_action_intervention",
            project=project_name,
            leverage_point=executed.leverage_point.name,
            executed=executed.executed,
        )

        return executed

    def get_project_status(self, project_name: str) -> dict[str, Any]:
        state = self._state_matrix.get_state(project_name)
        entropy_report = self._entropy_watchdog.scan_project(project_name)
        superposition = self._coordinator.get_superposition(project_name)

        return {
            "hidden_state": state.to_dict() if state else None,
            "entropy_report": entropy_report.to_dict(),
            "superposition": superposition.to_dict() if superposition else None,
        }

    def get_full_report(self) -> dict[str, Any]:
        all_states = self._state_matrix.get_all_states()
        entropy_map: dict[str, float] = {
            name: state.entropy_value for name, state in all_states.items()
        }
        entropy_reports = self._entropy_watchdog.scan_all(list(all_states.keys()))
        coordinator_summary = self._coordinator.get_summary()
        recent_interventions = self._intervention_engine.get_intervention_history(limit=10)

        return {
            "all_hidden_states": {
                name: state.to_dict() for name, state in all_states.items()
            },
            "all_entropy_reports": {
                report.project_name: report.to_dict() for report in entropy_reports
            },
            "coordinator_summary": coordinator_summary,
            "recent_interventions": [i.to_dict() for i in recent_interventions],
        }

    def force_scan(self, project_name: str | None = None) -> list[EntropyReport]:
        if project_name is not None:
            report = self._entropy_watchdog.scan_project(project_name)
            self._state_matrix.update_state(
                project_name,
                entropy_value=report.total_entropy,
                health_score=1.0 - report.total_entropy,
            )
            self._coordinator.update_entropy(project_name, report.total_entropy)
            return [report]

        all_states = self._state_matrix.get_all_states()
        names = list(all_states.keys())
        reports = self._entropy_watchdog.scan_all(names)

        for report in reports:
            self._state_matrix.update_state(
                report.project_name,
                entropy_value=report.total_entropy,
                health_score=1.0 - report.total_entropy,
            )
            self._coordinator.update_entropy(report.project_name, report.total_entropy)

        return reports

    def force_intervene(self, project_name: str) -> Intervention | None:
        report = self._entropy_watchdog.scan_project(project_name)

        dimensions: dict[str, float] = {}
        for reading in report.readings:
            dimensions[reading.dimension.value] = reading.value

        intervention = self._intervention_engine.select_intervention(
            project_name, report.total_entropy, dimensions
        )
        if intervention is None:
            return None

        executed = self._intervention_engine.execute_intervention(intervention)
        self._state_matrix.record_intervention(project_name, auto=executed.executed)
        self._state_matrix.update_state(
            project_name,
            entropy_value=report.total_entropy,
            health_score=1.0 - report.total_entropy,
        )

        logger.info(
            "as3e_force_intervene",
            project=project_name,
            leverage_point=executed.leverage_point.name,
            executed=executed.executed,
        )

        return executed
