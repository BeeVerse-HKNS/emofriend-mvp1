from __future__ import annotations

import structlog
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logger = structlog.get_logger()


class GoalStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    ABANDONED = "abandoned"


class DriftType(Enum):
    SCOPE_CREEP = "scope_creep"
    PRIORITY_SHIFT = "priority_shift"
    RESOURCE_CONSTRAINT = "resource_constraint"
    EXTERNAL_DEPENDENCY = "external_dependency"
    GOAL_CONFLICT = "goal_conflict"


@dataclass
class SubGoal:
    id: str
    name: str
    description: str
    status: GoalStatus = GoalStatus.PENDING
    progress: float = 0.0
    weight: float = 1.0
    dependencies: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class Goal:
    id: str
    name: str
    description: str
    status: GoalStatus = GoalStatus.PENDING
    progress: float = 0.0
    sub_goals: list[SubGoal] = field(default_factory=list)
    target_metrics: dict[str, float] = field(default_factory=dict)
    current_metrics: dict[str, float] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class DriftEvent:
    timestamp: datetime
    drift_type: DriftType
    severity: float
    description: str
    affected_goal_id: str
    suggested_action: str


class GoalDecomposer:
    def __init__(self) -> None:
        self._decomposition_strategies = {
            "sequential": self._decompose_sequential,
            "parallel": self._decompose_parallel,
            "hierarchical": self._decompose_hierarchical,
        }

    def decompose(self, goal: Goal, strategy: str = "hierarchical") -> list[SubGoal]:
        decomposer = self._decomposition_strategies.get(strategy, self._decompose_hierarchical)
        return decomposer(goal)

    def _decompose_sequential(self, goal: Goal) -> list[SubGoal]:
        sub_goals = []
        phases = ["planning", "execution", "verification", "completion"]
        for i, phase in enumerate(phases):
            sg = SubGoal(
                id=f"{goal.id}-SG-{i:02d}",
                name=f"{goal.name}_{phase}",
                description=f"{phase.capitalize()} phase of {goal.name}",
                weight=1.0,
                dependencies=[f"{goal.id}-SG-{i-1:02d}"] if i > 0 else [],
            )
            sub_goals.append(sg)
        return sub_goals

    def _decompose_parallel(self, goal: Goal) -> list[SubGoal]:
        sub_goals = []
        aspects = ["data", "logic", "interface", "testing"]
        for i, aspect in enumerate(aspects):
            sg = SubGoal(
                id=f"{goal.id}-SG-{i:02d}",
                name=f"{goal.name}_{aspect}",
                description=f"{aspect.capitalize()} aspect of {goal.name}",
                weight=1.0,
                dependencies=[],
            )
            sub_goals.append(sg)
        return sub_goals

    def _decompose_hierarchical(self, goal: Goal) -> list[SubGoal]:
        sub_goals = []
        levels = [
            ("L1", "high_level", 1.5),
            ("L2", "mid_level", 1.0),
            ("L3", "low_level", 0.5),
        ]
        for i, (level, desc, weight) in enumerate(levels):
            sg = SubGoal(
                id=f"{goal.id}-{level}",
                name=f"{goal.name}_{desc}",
                description=f"{desc.replace('_', ' ').capitalize()} tasks for {goal.name}",
                weight=weight,
                dependencies=[f"{goal.id}-{levels[j][0]}" for j in range(i)] if i > 0 else [],
            )
            sub_goals.append(sg)
        return sub_goals

    def auto_decompose_from_description(self, description: str) -> list[str]:
        keywords = {
            "implement": ["design", "code", "test", "deploy"],
            "analyze": ["collect", "process", "analyze", "report"],
            "optimize": ["measure", "identify", "optimize", "verify"],
            "integrate": ["prepare", "connect", "validate", "monitor"],
        }
        for key, phases in keywords.items():
            if key in description.lower():
                return phases
        return ["plan", "execute", "verify"]


class ProgressTracker:
    def __init__(self) -> None:
        self._progress_history: dict[str, list[tuple[datetime, float]]] = {}

    def track(self, goal: Goal) -> float:
        total_weight = sum(sg.weight for sg in goal.sub_goals) if goal.sub_goals else 1.0
        if total_weight == 0:
            total_weight = 1.0
        weighted_progress = sum(sg.progress * sg.weight for sg in goal.sub_goals)
        goal.progress = weighted_progress / total_weight
        goal.updated_at = datetime.now()
        self._record_history(goal.id, goal.progress)
        return goal.progress

    def _record_history(self, goal_id: str, progress: float) -> None:
        if goal_id not in self._progress_history:
            self._progress_history[goal_id] = []
        self._progress_history[goal_id].append((datetime.now(), progress))

    def get_velocity(self, goal_id: str) -> float:
        history = self._progress_history.get(goal_id, [])
        if len(history) < 2:
            return 0.0
        recent = history[-5:] if len(history) >= 5 else history
        if len(recent) < 2:
            return 0.0
        time_diff = (recent[-1][0] - recent[0][0]).total_seconds()
        if time_diff == 0:
            return 0.0
        progress_diff = recent[-1][1] - recent[0][1]
        return progress_diff / time_diff * 3600

    def estimate_completion(self, goal: Goal) -> datetime | None:
        velocity = self.get_velocity(goal.id)
        if velocity <= 0:
            return None
        remaining = 1.0 - goal.progress
        hours_remaining = remaining / velocity
        from datetime import timedelta
        return datetime.now() + timedelta(hours=hours_remaining)

    def get_progress_report(self, goal: Goal) -> dict[str, Any]:
        return {
            "goal_id": goal.id,
            "goal_name": goal.name,
            "overall_progress": goal.progress,
            "status": goal.status.value,
            "sub_goals": [
                {"id": sg.id, "name": sg.name, "progress": sg.progress, "status": sg.status.value}
                for sg in goal.sub_goals
            ],
            "velocity": self.get_velocity(goal.id),
            "estimated_completion": self.estimate_completion(goal).isoformat() if self.estimate_completion(goal) else None,
        }


class DriftDetector:
    def __init__(self, threshold: float = 0.15) -> None:
        self._threshold = threshold
        self._drift_history: list[DriftEvent] = []

    def detect(self, goal: Goal, original_goal: Goal | None = None) -> list[DriftEvent]:
        drifts = []
        if original_goal:
            scope_drift = self._detect_scope_creep(goal, original_goal)
            if scope_drift:
                drifts.append(scope_drift)
        metric_drift = self._detect_metric_deviation(goal)
        if metric_drift:
            drifts.append(metric_drift)
        progress_drift = self._detect_progress_anomaly(goal)
        if progress_drift:
            drifts.append(progress_drift)
        self._drift_history.extend(drifts)
        return drifts

    def _detect_scope_creep(self, current: Goal, original: Goal) -> DriftEvent | None:
        current_scope = len(current.sub_goals)
        original_scope = len(original.sub_goals)
        if original_scope == 0:
            return None
        scope_change = abs(current_scope - original_scope) / original_scope
        if scope_change > self._threshold:
            return DriftEvent(
                timestamp=datetime.now(),
                drift_type=DriftType.SCOPE_CREEP,
                severity=scope_change,
                description=f"Scope changed from {original_scope} to {current_scope} sub-goals",
                affected_goal_id=current.id,
                suggested_action="Review and prioritize sub-goals" if current_scope > original_scope else "Expand scope if needed",
            )
        return None

    def _detect_metric_deviation(self, goal: Goal) -> DriftEvent | None:
        if not goal.target_metrics or not goal.current_metrics:
            return None
        deviations = []
        for key, target in goal.target_metrics.items():
            current = goal.current_metrics.get(key, 0)
            if target == 0:
                continue
            deviation = abs(current - target) / target
            deviations.append(deviation)
        if not deviations:
            return None
        avg_deviation = sum(deviations) / len(deviations)
        if avg_deviation > self._threshold:
            return DriftEvent(
                timestamp=datetime.now(),
                drift_type=DriftType.GOAL_CONFLICT,
                severity=avg_deviation,
                description=f"Metrics deviating by {avg_deviation:.2%} from targets",
                affected_goal_id=goal.id,
                suggested_action="Realign metrics or adjust targets",
            )
        return None

    def _detect_progress_anomaly(self, goal: Goal) -> DriftEvent | None:
        if goal.status == GoalStatus.IN_PROGRESS and goal.progress < 0.1:
            return DriftEvent(
                timestamp=datetime.now(),
                drift_type=DriftType.RESOURCE_CONSTRAINT,
                severity=0.5,
                description="Goal in progress but minimal progress made",
                affected_goal_id=goal.id,
                suggested_action="Check for blockers or resource constraints",
            )
        return None

    def get_drift_summary(self) -> dict[str, Any]:
        if not self._drift_history:
            return {"total_drifts": 0, "by_type": {}, "avg_severity": 0.0}
        by_type: dict[str, int] = {}
        total_severity = 0.0
        for drift in self._drift_history:
            drift_type = drift.drift_type.value
            by_type[drift_type] = by_type.get(drift_type, 0) + 1
            total_severity += drift.severity
        return {
            "total_drifts": len(self._drift_history),
            "by_type": by_type,
            "avg_severity": total_severity / len(self._drift_history),
        }


class RealignmentTrigger:
    def __init__(self) -> None:
        self._realign_actions: dict[DriftType, callable] = {
            DriftType.SCOPE_CREEP: self._realign_scope,
            DriftType.PRIORITY_SHIFT: self._realign_priority,
            DriftType.RESOURCE_CONSTRAINT: self._realign_resources,
            DriftType.EXTERNAL_DEPENDENCY: self._realign_dependency,
            DriftType.GOAL_CONFLICT: self._realign_conflict,
        }

    def trigger(self, drift: DriftEvent, goal: Goal) -> dict[str, Any]:
        action = self._realign_actions.get(drift.drift_type, self._default_realign)
        return action(drift, goal)

    def _realign_scope(self, drift: DriftEvent, goal: Goal) -> dict[str, Any]:
        return {
            "action": "scope_realign",
            "suggestion": "Prioritize sub-goals and remove non-essential ones",
            "affected_sub_goals": [sg.id for sg in goal.sub_goals[-3:]] if len(goal.sub_goals) > 3 else [],
            "priority": "high" if drift.severity > 0.3 else "medium",
        }

    def _realign_priority(self, drift: DriftEvent, goal: Goal) -> dict[str, Any]:
        return {
            "action": "priority_realign",
            "suggestion": "Reorder sub-goals based on current priorities",
            "new_order": sorted(goal.sub_goals, key=lambda sg: sg.weight, reverse=True),
            "priority": "medium",
        }

    def _realign_resources(self, drift: DriftEvent, goal: Goal) -> dict[str, Any]:
        blocked = [sg for sg in goal.sub_goals if sg.status == GoalStatus.BLOCKED]
        return {
            "action": "resource_realign",
            "suggestion": "Allocate additional resources or remove blockers",
            "blocked_sub_goals": [sg.id for sg in blocked],
            "priority": "high",
        }

    def _realign_dependency(self, drift: DriftEvent, goal: Goal) -> dict[str, Any]:
        return {
            "action": "dependency_realign",
            "suggestion": "Resolve external dependencies or find alternatives",
            "priority": "high",
        }

    def _realign_conflict(self, drift: DriftEvent, goal: Goal) -> dict[str, Any]:
        return {
            "action": "conflict_realign",
            "suggestion": "Adjust metrics or resolve conflicting goals",
            "current_metrics": goal.current_metrics,
            "target_metrics": goal.target_metrics,
            "priority": "medium",
        }

    def _default_realign(self, drift: DriftEvent, goal: Goal) -> dict[str, Any]:
        return {
            "action": "default_realign",
            "suggestion": drift.suggested_action,
            "priority": "low",
        }


class GoalTrackingSystem:
    def __init__(self) -> None:
        self._formula = "P * R + M - A"
        self._capability = "goal_tracking_system"
        self._decomposer = GoalDecomposer()
        self._tracker = ProgressTracker()
        self._drift_detector = DriftDetector()
        self._realign_trigger = RealignmentTrigger()
        self._goals: dict[str, Goal] = {}

    def analyze(self, input_data: dict) -> dict:
        try:
            result = self._process(input_data)
            logger.info("goal_tracking_system_success", capability=self._capability)
            return {"status": "success", "capability": self._capability, "result": result, "formula": self._formula}
        except Exception as exc:
            logger.error("goal_tracking_system_failed", capability=self._capability, error=str(exc))
            return {"status": "error", "capability": self._capability, "error": str(exc)}

    def execute(self, input_data: dict) -> dict:
        return self.analyze(input_data)

    def _process(self, input_data: dict) -> dict:
        action = input_data.get("action", "track")
        if action == "create":
            return self._create_goal(input_data)
        elif action == "decompose":
            return self._decompose_goal(input_data)
        elif action == "track":
            return self._track_progress(input_data)
        elif action == "detect_drift":
            return self._detect_drift(input_data)
        elif action == "realign":
            return self._realign_goal(input_data)
        elif action == "report":
            return self._generate_report(input_data)
        else:
            return {"processed": True, "input_keys": list(input_data.keys())}

    def _create_goal(self, input_data: dict) -> dict:
        goal = Goal(
            id=input_data.get("id", f"GOAL-{len(self._goals):03d}"),
            name=input_data.get("name", "Unnamed Goal"),
            description=input_data.get("description", ""),
            target_metrics=input_data.get("target_metrics", {}),
        )
        self._goals[goal.id] = goal
        return {"goal_id": goal.id, "status": "created"}

    def _decompose_goal(self, input_data: dict) -> dict:
        goal_id = input_data.get("goal_id")
        strategy = input_data.get("strategy", "hierarchical")
        goal = self._goals.get(goal_id)
        if not goal:
            return {"error": f"Goal {goal_id} not found"}
        sub_goals = self._decomposer.decompose(goal, strategy)
        goal.sub_goals = sub_goals
        return {
            "goal_id": goal_id,
            "sub_goals": [{"id": sg.id, "name": sg.name, "dependencies": sg.dependencies} for sg in sub_goals],
        }

    def _track_progress(self, input_data: dict) -> dict:
        goal_id = input_data.get("goal_id")
        goal = self._goals.get(goal_id)
        if not goal:
            return {"error": f"Goal {goal_id} not found"}
        updates = input_data.get("updates", {})
        for sg_id, progress in updates.items():
            for sg in goal.sub_goals:
                if sg.id == sg_id:
                    sg.progress = min(max(progress, 0.0), 1.0)
                    sg.updated_at = datetime.now()
                    if sg.progress >= 1.0:
                        sg.status = GoalStatus.COMPLETED
                    elif sg.progress > 0:
                        sg.status = GoalStatus.IN_PROGRESS
        overall = self._tracker.track(goal)
        if overall >= 1.0:
            goal.status = GoalStatus.COMPLETED
        elif overall > 0:
            goal.status = GoalStatus.IN_PROGRESS
        return {"goal_id": goal_id, "overall_progress": overall, "status": goal.status.value}

    def _detect_drift(self, input_data: dict) -> dict:
        goal_id = input_data.get("goal_id")
        goal = self._goals.get(goal_id)
        if not goal:
            return {"error": f"Goal {goal_id} not found"}
        original_id = input_data.get("original_goal_id")
        original = self._goals.get(original_id) if original_id else None
        drifts = self._drift_detector.detect(goal, original)
        return {
            "goal_id": goal_id,
            "drifts_detected": len(drifts),
            "drifts": [
                {
                    "type": d.drift_type.value,
                    "severity": d.severity,
                    "description": d.description,
                    "suggested_action": d.suggested_action,
                }
                for d in drifts
            ],
        }

    def _realign_goal(self, input_data: dict) -> dict:
        goal_id = input_data.get("goal_id")
        goal = self._goals.get(goal_id)
        if not goal:
            return {"error": f"Goal {goal_id} not found"}
        drifts = self._drift_detector.detect(goal)
        if not drifts:
            return {"goal_id": goal_id, "status": "no_drift_detected"}
        realignments = []
        for drift in drifts:
            realignment = self._realign_trigger.trigger(drift, goal)
            realignments.append(realignment)
        return {"goal_id": goal_id, "realignments": realignments}

    def _generate_report(self, input_data: dict) -> dict:
        goal_id = input_data.get("goal_id")
        if goal_id:
            goal = self._goals.get(goal_id)
            if not goal:
                return {"error": f"Goal {goal_id} not found"}
            return self._tracker.get_progress_report(goal)
        else:
            return {
                "total_goals": len(self._goals),
                "goals": [
                    self._tracker.get_progress_report(g) for g in self._goals.values()
                ],
                "drift_summary": self._drift_detector.get_drift_summary(),
            }


if __name__ == "__main__":
    system = GoalTrackingSystem()

    print("=" * 60)
    print("Test 1: Create Goal")
    print("=" * 60)
    result = system.execute({
        "action": "create",
        "name": "Implement Feature X",
        "description": "Implement and test feature X for the application",
        "target_metrics": {"test_coverage": 0.9, "performance": 100},
    })
    goal_id = result["result"]["goal_id"]
    print(f"Created goal: {goal_id}")

    print("\n" + "=" * 60)
    print("Test 2: Decompose Goal")
    print("=" * 60)
    result = system.execute({
        "action": "decompose",
        "goal_id": goal_id,
        "strategy": "hierarchical",
    })
    print(f"Sub-goals created: {len(result['result']['sub_goals'])}")
    for sg in result["result"]["sub_goals"]:
        print(f"  - {sg['id']}: {sg['name']}")

    print("\n" + "=" * 60)
    print("Test 3: Track Progress")
    print("=" * 60)
    sub_goal_ids = [sg["id"] for sg in result["result"]["sub_goals"]]
    updates = {sg_id: 0.3 + (i * 0.2) for i, sg_id in enumerate(sub_goal_ids)}
    result = system.execute({
        "action": "track",
        "goal_id": goal_id,
        "updates": updates,
    })
    print(f"Overall progress: {result['result']['overall_progress']:.2%}")
    print(f"Status: {result['result']['status']}")

    print("\n" + "=" * 60)
    print("Test 4: Detect Drift")
    print("=" * 60)
    result = system.execute({
        "action": "detect_drift",
        "goal_id": goal_id,
    })
    print(f"Drifts detected: {result['result']['drifts_detected']}")
    for drift in result["result"]["drifts"]:
        print(f"  - {drift['type']}: {drift['description']}")

    print("\n" + "=" * 60)
    print("Test 5: Generate Report")
    print("=" * 60)
    result = system.execute({
        "action": "report",
        "goal_id": goal_id,
    })
    report = result["result"]
    print(f"Goal: {report['goal_name']}")
    print(f"Progress: {report['overall_progress']:.2%}")
    print(f"Velocity: {report['velocity']:.4f}/hour")

    print("\n" + "=" * 60)
    print("All tests passed!")
    print("=" * 60)
