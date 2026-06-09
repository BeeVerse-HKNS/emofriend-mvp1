from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger()


class CollapseReason(Enum):
    ENTROPY_BREACH = "entropy_breach"
    USER_REQUEST = "user_request"
    SCHEDULED_CHECK = "scheduled_check"
    DEPENDENCY_TRIGGER = "dependency_trigger"


class SuperpositionState(Enum):
    READY = "READY"
    COLLAPSING = "COLLAPSING"
    PROCESSING = "PROCESSING"
    RESTING = "RESTING"


@dataclass
class SubprojectSuperposition:
    name: str
    state: SuperpositionState = SuperpositionState.READY
    entropy_value: float = 0.0
    priority_score: float = 0.0
    last_collapse_time: datetime | None = None
    collapse_count: int = 0
    pending_actions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "state": self.state.value,
            "entropy_value": self.entropy_value,
            "priority_score": self.priority_score,
            "last_collapse_time": self.last_collapse_time.isoformat() if self.last_collapse_time else None,
            "collapse_count": self.collapse_count,
            "pending_actions": self.pending_actions,
        }


@dataclass
class CollapseEvent:
    project_name: str
    reason: CollapseReason
    entropy_at_collapse: float
    timestamp: datetime
    actions_taken: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_name": self.project_name,
            "reason": self.reason.value,
            "entropy_at_collapse": self.entropy_at_collapse,
            "timestamp": self.timestamp.isoformat(),
            "actions_taken": self.actions_taken,
        }


class SuperpositionCoordinator:
    def __init__(self) -> None:
        self._superpositions: dict[str, SubprojectSuperposition] = {}
        self._collapse_history: list[CollapseEvent] = []
        self.entropy_threshold: float = 0.6
        self.max_collapse_history: int = 100

    def register_project(self, name: str, entropy_value: float = 0.0) -> None:
        sp = SubprojectSuperposition(
            name=name,
            entropy_value=entropy_value,
            priority_score=entropy_value * 10 + (1 if True else 0),
        )
        self._superpositions[name] = sp
        logger.info("project_registered", name=name, entropy_value=entropy_value, priority_score=sp.priority_score)

    def register_all(self, project_names: list[str], entropy_values: dict[str, float] | None = None) -> None:
        entropy_values = entropy_values or {}
        for name in project_names:
            ev = entropy_values.get(name, 0.0)
            self.register_project(name, ev)
        logger.info("all_projects_registered", count=len(project_names))

    def update_entropy(self, name: str, entropy_value: float) -> None:
        sp = self._superpositions.get(name)
        if sp is None:
            logger.warning("update_entropy_unknown_project", name=name)
            return
        sp.entropy_value = entropy_value
        sp.priority_score = entropy_value * 10 + (1 if sp.state == SuperpositionState.READY else 0)
        logger.info("entropy_updated", name=name, entropy_value=entropy_value, priority_score=sp.priority_score)
        if entropy_value > self.entropy_threshold:
            logger.info("entropy_breach_detected", name=name, entropy_value=entropy_value, threshold=self.entropy_threshold)
            self.check_collapse()

    def check_collapse(self) -> list[CollapseEvent]:
        events: list[CollapseEvent] = []
        candidates = sorted(
            [sp for sp in self._superpositions.values() if sp.state == SuperpositionState.READY],
            key=lambda s: s.priority_score,
            reverse=True,
        )
        for sp in candidates:
            if sp.entropy_value > self.entropy_threshold:
                event = self.collapse(sp.name, CollapseReason.ENTROPY_BREACH)
                events.append(event)
            elif sp.last_collapse_time is not None:
                now = datetime.now(timezone.utc)
                elapsed = (now - sp.last_collapse_time).total_seconds()
                if elapsed > 3600:
                    event = self.collapse(sp.name, CollapseReason.SCHEDULED_CHECK)
                    events.append(event)
        return events

    def collapse(self, name: str, reason: CollapseReason) -> CollapseEvent:
        sp = self._superpositions.get(name)
        if sp is None:
            logger.error("collapse_unknown_project", name=name)
            raise ValueError(f"Project '{name}' not registered")
        if sp.state != SuperpositionState.READY:
            logger.warning("collapse_not_ready", name=name, current_state=sp.state.value)
            return CollapseEvent(
                project_name=name,
                reason=reason,
                entropy_at_collapse=sp.entropy_value,
                timestamp=datetime.now(timezone.utc),
                actions_taken=[],
            )
        sp.state = SuperpositionState.COLLAPSING
        sp.collapse_count += 1
        event = CollapseEvent(
            project_name=name,
            reason=reason,
            entropy_at_collapse=sp.entropy_value,
            timestamp=datetime.now(timezone.utc),
        )
        self._collapse_history.append(event)
        if len(self._collapse_history) > self.max_collapse_history:
            self._collapse_history = self._collapse_history[-self.max_collapse_history:]
        logger.info("project_collapsed", name=name, reason=reason.value, entropy=sp.entropy_value, collapse_count=sp.collapse_count)
        return event

    def complete_collapse(self, name: str, actions_taken: list[str]) -> None:
        sp = self._superpositions.get(name)
        if sp is None:
            logger.error("complete_collapse_unknown_project", name=name)
            return
        if sp.state != SuperpositionState.COLLAPSING:
            logger.warning("complete_collapse_not_collapsing", name=name, current_state=sp.state.value)
            return
        sp.state = SuperpositionState.RESTING
        sp.last_collapse_time = datetime.now(timezone.utc)
        sp.pending_actions = actions_taken
        for event in reversed(self._collapse_history):
            if event.project_name == name and not event.actions_taken:
                event.actions_taken = actions_taken
                break
        sp.state = SuperpositionState.READY
        logger.info("collapse_completed", name=name, actions_count=len(actions_taken))

    def get_superposition(self, name: str) -> SubprojectSuperposition | None:
        return self._superpositions.get(name)

    def get_all_superpositions(self) -> dict[str, SubprojectSuperposition]:
        return dict(self._superpositions)

    def get_collapse_history(self, limit: int = 20) -> list[CollapseEvent]:
        return list(reversed(self._collapse_history[-limit:]))

    def get_priority_order(self) -> list[str]:
        sorted_sps = sorted(
            self._superpositions.values(),
            key=lambda s: s.priority_score,
            reverse=True,
        )
        return [sp.name for sp in sorted_sps]

    def get_summary(self) -> dict[str, Any]:
        state_counts = {s: 0 for s in SuperpositionState}
        for sp in self._superpositions.values():
            state_counts[sp.state] += 1
        top5 = sorted(
            self._superpositions.values(),
            key=lambda s: s.priority_score,
            reverse=True,
        )[:5]
        return {
            "total_projects": len(self._superpositions),
            "ready_count": state_counts[SuperpositionState.READY],
            "collapsing_count": state_counts[SuperpositionState.COLLAPSING],
            "processing_count": state_counts[SuperpositionState.PROCESSING],
            "resting_count": state_counts[SuperpositionState.RESTING],
            "high_priority_projects": [sp.to_dict() for sp in top5],
        }
