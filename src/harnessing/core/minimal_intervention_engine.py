from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import structlog

logger = structlog.get_logger()


class InterventionType(enum.Enum):
    PARAMETER_ADJUST = "parameter_adjust"
    CONFIG_SYNC = "config_sync"
    DEPENDENCY_UPDATE = "dependency_update"
    FILE_RESTORE = "file_restore"
    CONTEXT_REFRESH = "context_refresh"
    BRIDGE_UPDATE = "bridge_update"
    RULE_ADDITION = "rule_addition"
    AUTO_FIX = "auto_fix"
    ARCHIVE_CLEANUP = "archive_cleanup"
    SECURITY_PATCH = "security_patch"
    PARADIGM_SHIFT = "paradigm_shift"
    MANUAL_INTERVENTION = "manual_intervention"


class InterventionRisk(enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class LeveragePoint:
    id: int
    name: str
    intervention_type: InterventionType
    effort: float
    effectiveness: float
    risk: InterventionRisk
    description: str = ""
    auto_executable: bool = False

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "intervention_type": self.intervention_type.value,
            "effort": self.effort,
            "effectiveness": self.effectiveness,
            "risk": self.risk.value,
            "description": self.description,
            "auto_executable": self.auto_executable,
        }


@dataclass
class Intervention:
    project_name: str
    leverage_point: LeveragePoint
    reason: str
    entropy_before: float
    expected_entropy_after: float
    timestamp: datetime
    executed: bool = False
    result: str = ""

    def to_dict(self) -> dict:
        return {
            "project_name": self.project_name,
            "leverage_point": self.leverage_point.to_dict(),
            "reason": self.reason,
            "entropy_before": self.entropy_before,
            "expected_entropy_after": self.expected_entropy_after,
            "timestamp": self.timestamp.isoformat(),
            "executed": self.executed,
            "result": self.result,
        }


class MinimalInterventionEngine:
    def __init__(self) -> None:
        self._leverage_points: list[LeveragePoint] = [
            LeveragePoint(
                id=1,
                name="Parameter adjust",
                intervention_type=InterventionType.PARAMETER_ADJUST,
                effort=0.1,
                effectiveness=0.2,
                risk=InterventionRisk.LOW,
                auto_executable=True,
            ),
            LeveragePoint(
                id=2,
                name="Config sync",
                intervention_type=InterventionType.CONFIG_SYNC,
                effort=0.15,
                effectiveness=0.3,
                risk=InterventionRisk.LOW,
                auto_executable=True,
            ),
            LeveragePoint(
                id=3,
                name="Dependency update",
                intervention_type=InterventionType.DEPENDENCY_UPDATE,
                effort=0.2,
                effectiveness=0.4,
                risk=InterventionRisk.MEDIUM,
                auto_executable=True,
            ),
            LeveragePoint(
                id=4,
                name="File restore",
                intervention_type=InterventionType.FILE_RESTORE,
                effort=0.25,
                effectiveness=0.5,
                risk=InterventionRisk.MEDIUM,
                auto_executable=True,
            ),
            LeveragePoint(
                id=5,
                name="Context refresh",
                intervention_type=InterventionType.CONTEXT_REFRESH,
                effort=0.2,
                effectiveness=0.45,
                risk=InterventionRisk.LOW,
                auto_executable=True,
            ),
            LeveragePoint(
                id=6,
                name="Bridge update",
                intervention_type=InterventionType.BRIDGE_UPDATE,
                effort=0.15,
                effectiveness=0.35,
                risk=InterventionRisk.LOW,
                auto_executable=True,
            ),
            LeveragePoint(
                id=7,
                name="Rule addition",
                intervention_type=InterventionType.RULE_ADDITION,
                effort=0.3,
                effectiveness=0.6,
                risk=InterventionRisk.MEDIUM,
                auto_executable=False,
            ),
            LeveragePoint(
                id=8,
                name="Auto fix",
                intervention_type=InterventionType.AUTO_FIX,
                effort=0.35,
                effectiveness=0.55,
                risk=InterventionRisk.MEDIUM,
                auto_executable=True,
            ),
            LeveragePoint(
                id=9,
                name="Archive cleanup",
                intervention_type=InterventionType.ARCHIVE_CLEANUP,
                effort=0.2,
                effectiveness=0.3,
                risk=InterventionRisk.LOW,
                auto_executable=True,
            ),
            LeveragePoint(
                id=10,
                name="Security patch",
                intervention_type=InterventionType.SECURITY_PATCH,
                effort=0.4,
                effectiveness=0.7,
                risk=InterventionRisk.HIGH,
                auto_executable=False,
            ),
            LeveragePoint(
                id=11,
                name="Paradigm shift",
                intervention_type=InterventionType.PARADIGM_SHIFT,
                effort=0.9,
                effectiveness=0.95,
                risk=InterventionRisk.CRITICAL,
                auto_executable=False,
            ),
            LeveragePoint(
                id=12,
                name="Manual intervention",
                intervention_type=InterventionType.MANUAL_INTERVENTION,
                effort=1.0,
                effectiveness=1.0,
                risk=InterventionRisk.CRITICAL,
                auto_executable=False,
            ),
        ]
        self._intervention_history: list[Intervention] = []
        self.effectiveness_threshold: float = 0.5

    def select_intervention(
        self,
        project_name: str,
        entropy: float,
        entropy_dimensions: dict[str, float],
    ) -> Intervention | None:
        preferred_types = self._map_dimensions_to_types(entropy_dimensions)
        candidates = [lp for lp in self._leverage_points if lp.effectiveness >= self.effectiveness_threshold]
        if not candidates:
            return None

        preferred_candidates = [lp for lp in candidates if lp.intervention_type in preferred_types]
        pool = preferred_candidates if preferred_candidates else candidates

        selected = min(pool, key=lambda lp: lp.effort)
        expected_entropy_after = entropy * (1 - selected.effectiveness)

        reason_parts: list[str] = []
        for dim, val in entropy_dimensions.items():
            if val > 0.6:
                reason_parts.append(f"{dim}={val:.2f}")
        reason = f"High entropy dimensions: {', '.join(reason_parts)}" if reason_parts else "Entropy above threshold"

        intervention = Intervention(
            project_name=project_name,
            leverage_point=selected,
            reason=reason,
            entropy_before=entropy,
            expected_entropy_after=expected_entropy_after,
            timestamp=datetime.now(timezone.utc),
        )
        logger.info(
            "intervention_selected",
            project=project_name,
            leverage_point=selected.name,
            effort=selected.effort,
            effectiveness=selected.effectiveness,
            entropy_before=entropy,
            expected_entropy_after=expected_entropy_after,
        )
        return intervention

    def _map_dimensions_to_types(self, entropy_dimensions: dict[str, float]) -> set[InterventionType]:
        preferred: set[InterventionType] = set()
        if entropy_dimensions.get("code_drift", 0) > 0.6:
            preferred.add(InterventionType.FILE_RESTORE)
            preferred.add(InterventionType.AUTO_FIX)
        if entropy_dimensions.get("dependency_staleness", 0) > 0.6:
            preferred.add(InterventionType.DEPENDENCY_UPDATE)
        if entropy_dimensions.get("config_conflict", 0) > 0.6:
            preferred.add(InterventionType.CONFIG_SYNC)
        if entropy_dimensions.get("file_missing", 0) > 0.6:
            preferred.add(InterventionType.BRIDGE_UPDATE)
            preferred.add(InterventionType.FILE_RESTORE)
        if entropy_dimensions.get("context_staleness", 0) > 0.6:
            preferred.add(InterventionType.CONTEXT_REFRESH)
        return preferred

    def execute_intervention(self, intervention: Intervention) -> Intervention:
        lp = intervention.leverage_point
        if lp.auto_executable and lp.risk in (InterventionRisk.LOW, InterventionRisk.MEDIUM):
            intervention.executed = True
            intervention.result = "auto_executed"
            logger.info(
                "intervention_auto_executed",
                project=intervention.project_name,
                leverage_point=lp.name,
            )
        else:
            intervention.executed = False
            intervention.result = "requires_user_approval"
            logger.info(
                "intervention_requires_approval",
                project=intervention.project_name,
                leverage_point=lp.name,
                risk=lp.risk.value,
            )
        self._intervention_history.append(intervention)
        return intervention

    def get_intervention_history(
        self,
        project_name: str | None = None,
        limit: int = 20,
    ) -> list[Intervention]:
        if project_name is None:
            return self._intervention_history[-limit:]
        filtered = [i for i in self._intervention_history if i.project_name == project_name]
        return filtered[-limit:]

    def get_leverage_points(self) -> list[LeveragePoint]:
        return list(self._leverage_points)

    def get_auto_executable_points(self) -> list[LeveragePoint]:
        return [lp for lp in self._leverage_points if lp.auto_executable]
