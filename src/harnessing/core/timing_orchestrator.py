from __future__ import annotations

import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class ConflictStrategy(Enum):
    SERIALIZE = "serialize"
    MERGE = "merge"
    PRIORITY_FIRST = "priority_first"
    CANCEL_LOWER = "cancel_lower"


class TimingEventType(Enum):
    TASK_SCHEDULED = "task_scheduled"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    CONFLICT_DETECTED = "conflict_detected"
    CONFLICT_RESOLVED = "conflict_resolved"
    CLOCK_DRIFT = "clock_drift"
    CLOCK_CORRECTED = "clock_corrected"


class TimingHealth(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"


@dataclass
class ScheduledTask:
    task_id: str
    task_fn: Callable
    priority: int = 5
    scheduled_time: Optional[float] = None
    status: TaskStatus = TaskStatus.PENDING
    created_at: float = field(default_factory=time.time)
    exclusive_resources: Set[str] = field(default_factory=set)
    result: Any = None
    error: Optional[str] = None

    def __lt__(self, other: ScheduledTask) -> bool:
        if self.priority != other.priority:
            return self.priority < other.priority
        if self.scheduled_time is not None and other.scheduled_time is not None:
            return self.scheduled_time < other.scheduled_time
        return self.created_at < other.created_at


@dataclass
class ConflictGroup:
    conflict_id: str
    task_ids: List[str]
    resources: Set[str]
    detected_at: float = field(default_factory=time.time)
    resolved: bool = False
    resolution_strategy: Optional[ConflictStrategy] = None


@dataclass
class ComponentClock:
    component_id: str
    offset_ms: float = 0.0
    registered_at: float = field(default_factory=time.time)
    last_sync: float = field(default_factory=time.time)
    drift_ms: float = 0.0
    correction_history: List[float] = field(default_factory=list)


@dataclass
class TimingEvent:
    event_type: TimingEventType
    details: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])


class TaskScheduler:
    def __init__(self):
        self._tasks: Dict[str, ScheduledTask] = {}
        self._queue: List[str] = []

    def schedule_task(
        self,
        task_id: str,
        task_fn: Callable,
        priority: int = 5,
        scheduled_time: Optional[float] = None,
    ) -> ScheduledTask:
        if task_id in self._tasks:
            raise ValueError(f"Task {task_id} already exists")
        task = ScheduledTask(
            task_id=task_id,
            task_fn=task_fn,
            priority=priority,
            scheduled_time=scheduled_time,
        )
        self._tasks[task_id] = task
        self._queue.append(task_id)
        self._queue.sort(key=lambda tid: self._tasks[tid])
        return task

    def cancel_task(self, task_id: str) -> bool:
        if task_id not in self._tasks:
            return False
        task = self._tasks[task_id]
        if task.status in (TaskStatus.RUNNING, TaskStatus.COMPLETED):
            return False
        task.status = TaskStatus.CANCELLED
        if task_id in self._queue:
            self._queue.remove(task_id)
        return True

    def get_pending_tasks(self) -> List[ScheduledTask]:
        now = time.time()
        pending = []
        for tid in self._queue:
            task = self._tasks.get(tid)
            if task and task.status == TaskStatus.PENDING:
                if task.scheduled_time is None or task.scheduled_time <= now:
                    pending.append(task)
        pending.sort()
        return pending

    def get_next_task(self) -> Optional[ScheduledTask]:
        pending = self.get_pending_tasks()
        return pending[0] if pending else None

    def mark_running(self, task_id: str) -> bool:
        if task_id not in self._tasks:
            return False
        task = self._tasks[task_id]
        if task.status != TaskStatus.PENDING:
            return False
        task.status = TaskStatus.RUNNING
        if task_id in self._queue:
            self._queue.remove(task_id)
        return True

    def mark_completed(self, task_id: str, result: Any = None) -> bool:
        if task_id not in self._tasks:
            return False
        task = self._tasks[task_id]
        task.status = TaskStatus.COMPLETED
        task.result = result
        return True

    def mark_failed(self, task_id: str, error: str = "") -> bool:
        if task_id not in self._tasks:
            return False
        task = self._tasks[task_id]
        task.status = TaskStatus.FAILED
        task.error = error
        return True

    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        return self._tasks.get(task_id)

    def get_all_tasks(self) -> Dict[str, ScheduledTask]:
        return dict(self._tasks)


class ConflictResolver:
    def __init__(self, scheduler: TaskScheduler):
        self._scheduler = scheduler
        self._exclusions: Dict[str, Set[str]] = {}
        self._conflicts: Dict[str, ConflictGroup] = {}
        self._resolution_log: List[Dict[str, Any]] = []

    def register_exclusion(self, task_id: str, exclusive_resources: Set[str]) -> None:
        self._exclusions[task_id] = exclusive_resources
        task = self._scheduler.get_task(task_id)
        if task:
            task.exclusive_resources = exclusive_resources

    def detect_conflicts(self) -> List[ConflictGroup]:
        pending = self._scheduler.get_pending_tasks()
        resource_map: Dict[str, List[str]] = defaultdict(list)
        for task in pending:
            for res in task.exclusive_resources:
                resource_map[res].append(task.task_id)

        conflicts = []
        for res, task_ids in resource_map.items():
            if len(task_ids) > 1:
                conflict_id = str(uuid.uuid4())[:8]
                group = ConflictGroup(
                    conflict_id=conflict_id,
                    task_ids=task_ids,
                    resources={res},
                )
                self._conflicts[conflict_id] = group
                conflicts.append(group)

        overlapping: Dict[Tuple[str, ...], Set[str]] = defaultdict(set)
        for task in pending:
            if task.exclusive_resources:
                key = tuple(sorted(task.exclusive_resources))
                overlapping[key].add(task.task_id)

        for key, task_ids in overlapping.items():
            if len(task_ids) > 1:
                existing = False
                for c in conflicts:
                    if set(c.task_ids) == task_ids:
                        existing = True
                        break
                if not existing:
                    conflict_id = str(uuid.uuid4())[:8]
                    group = ConflictGroup(
                        conflict_id=conflict_id,
                        task_ids=list(task_ids),
                        resources=set(key),
                    )
                    self._conflicts[conflict_id] = group
                    conflicts.append(group)

        return conflicts

    def resolve_conflict(
        self, conflict_id: str, strategy: ConflictStrategy
    ) -> Dict[str, Any]:
        if conflict_id not in self._conflicts:
            return {"status": "not_found", "conflict_id": conflict_id}

        conflict = self._conflicts[conflict_id]
        if conflict.resolved:
            return {"status": "already_resolved", "conflict_id": conflict_id}

        result: Dict[str, Any] = {
            "conflict_id": conflict_id,
            "strategy": strategy.value,
            "actions": [],
        }

        if strategy == ConflictStrategy.SERIALIZE:
            tasks = []
            for tid in conflict.task_ids:
                task = self._scheduler.get_task(tid)
                if task:
                    tasks.append(task)
            tasks.sort()
            for i, task in enumerate(tasks):
                if task.scheduled_time is not None:
                    task.scheduled_time = task.scheduled_time + i * 1.0
                else:
                    task.scheduled_time = time.time() + i * 1.0
            result["actions"] = [
                {"task_id": t.task_id, "new_scheduled_time": t.scheduled_time}
                for t in tasks
            ]

        elif strategy == ConflictStrategy.MERGE:
            primary_id = conflict.task_ids[0]
            result["actions"] = [
                {
                    "action": "merge_into",
                    "source_tasks": conflict.task_ids[1:],
                    "target_task": primary_id,
                }
            ]
            for tid in conflict.task_ids[1:]:
                self._scheduler.cancel_task(tid)

        elif strategy == ConflictStrategy.PRIORITY_FIRST:
            tasks = []
            for tid in conflict.task_ids:
                task = self._scheduler.get_task(tid)
                if task:
                    tasks.append(task)
            tasks.sort()
            winner = tasks[0]
            for t in tasks[1:]:
                self._scheduler.cancel_task(t.task_id)
            result["actions"] = [
                {"action": "keep", "task_id": winner.task_id},
                *[
                    {"action": "cancel", "task_id": t.task_id}
                    for t in tasks[1:]
                ],
            ]

        elif strategy == ConflictStrategy.CANCEL_LOWER:
            tasks = []
            for tid in conflict.task_ids:
                task = self._scheduler.get_task(tid)
                if task:
                    tasks.append(task)
            if len(tasks) >= 2:
                tasks.sort()
                for t in tasks[1:]:
                    self._scheduler.cancel_task(t.task_id)
                result["actions"] = [
                    {"action": "cancel", "task_id": t.task_id} for t in tasks[1:]
                ]
            else:
                result["actions"] = [{"action": "no_action"}]

        conflict.resolved = True
        conflict.resolution_strategy = strategy
        self._resolution_log.append(result)
        result["status"] = "resolved"
        return result

    def get_conflicts(self) -> Dict[str, ConflictGroup]:
        return dict(self._conflicts)

    def get_resolution_log(self) -> List[Dict[str, Any]]:
        return list(self._resolution_log)


class ClockSynchronizer:
    def __init__(self):
        self._clocks: Dict[str, ComponentClock] = {}
        self._reference_time: float = time.time()
        self._correction_threshold_ms: float = 100.0

    def register_clock(self, component_id: str, offset_ms: float = 0.0) -> ComponentClock:
        clock = ComponentClock(
            component_id=component_id,
            offset_ms=offset_ms,
        )
        self._clocks[component_id] = clock
        return clock

    def get_synchronized_time(self) -> float:
        if not self._clocks:
            return time.time()
        offsets = [c.offset_ms for c in self._clocks.values()]
        avg_offset_ms = sum(offsets) / len(offsets)
        return time.time() + avg_offset_ms / 1000.0

    def get_synchronized_datetime(self) -> datetime:
        return datetime.fromtimestamp(self.get_synchronized_time(), tz=timezone.utc)

    def detect_drift(self, threshold_ms: float = 100.0) -> List[ComponentClock]:
        drifting = []
        now = time.time()
        for clock in self._clocks.values():
            elapsed = now - clock.last_sync
            estimated_drift = clock.drift_ms + elapsed * 0.1
            if abs(estimated_drift) > threshold_ms:
                drifting_clock = ComponentClock(
                    component_id=clock.component_id,
                    offset_ms=clock.offset_ms,
                    registered_at=clock.registered_at,
                    last_sync=clock.last_sync,
                    drift_ms=estimated_drift,
                    correction_history=clock.correction_history,
                )
                drifting.append(drifting_clock)
        return drifting

    def correct_drift(self, component_id: str) -> Dict[str, Any]:
        if component_id not in self._clocks:
            return {"status": "not_found", "component_id": component_id}

        clock = self._clocks[component_id]
        now = time.time()
        elapsed = now - clock.last_sync
        current_drift = clock.drift_ms + elapsed * 0.1

        correction = -current_drift
        clock.offset_ms += correction
        clock.drift_ms = 0.0
        clock.last_sync = now
        clock.correction_history.append(correction)

        return {
            "status": "corrected",
            "component_id": component_id,
            "previous_drift_ms": current_drift,
            "correction_ms": correction,
            "new_offset_ms": clock.offset_ms,
        }

    def get_clock(self, component_id: str) -> Optional[ComponentClock]:
        return self._clocks.get(component_id)

    def get_all_clocks(self) -> Dict[str, ComponentClock]:
        return dict(self._clocks)

    def simulate_drift(self, component_id: str, drift_ms: float) -> bool:
        if component_id not in self._clocks:
            return False
        self._clocks[component_id].drift_ms += drift_ms
        return True


class TimingOrchestrator:
    def __init__(self):
        self.scheduler = TaskScheduler()
        self.conflict_resolver = ConflictResolver(self.scheduler)
        self.clock_sync = ClockSynchronizer()
        self._event_log: List[TimingEvent] = []
        self._execution_order: List[str] = []

    def orchestrate(self, task_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        for task_spec in task_list:
            task_id = task_spec.get("task_id", str(uuid.uuid4())[:8])
            task_fn = task_spec.get("task_fn", lambda: None)
            priority = task_spec.get("priority", 5)
            scheduled_time = task_spec.get("scheduled_time")
            exclusive_resources = task_spec.get("exclusive_resources", set())

            self.scheduler.schedule_task(
                task_id=task_id,
                task_fn=task_fn,
                priority=priority,
                scheduled_time=scheduled_time,
            )

            if exclusive_resources:
                self.conflict_resolver.register_exclusion(task_id, exclusive_resources)

        conflicts = self.conflict_resolver.detect_conflicts()
        if conflicts:
            for conflict in conflicts:
                self._log_event(
                    TimingEventType.CONFLICT_DETECTED,
                    {
                        "conflict_id": conflict.conflict_id,
                        "task_ids": conflict.task_ids,
                        "resources": list(conflict.resources),
                    },
                )
                resolution = self.conflict_resolver.resolve_conflict(
                    conflict.conflict_id, ConflictStrategy.PRIORITY_FIRST
                )
                self._log_event(
                    TimingEventType.CONFLICT_RESOLVED,
                    resolution,
                )

        pending = self.scheduler.get_pending_tasks()
        self._execution_order = [t.task_id for t in pending]

        return {
            "total_tasks": len(task_list),
            "conflicts_found": len(conflicts),
            "execution_order": self._execution_order,
            "synchronized_time": self.clock_sync.get_synchronized_datetime().isoformat(),
        }

    def handle_timing_event(
        self, event_type: TimingEventType, details: Dict[str, Any]
    ) -> Dict[str, Any]:
        event = TimingEvent(event_type=event_type, details=details)
        self._event_log.append(event)

        if event_type == TimingEventType.TASK_SCHEDULED:
            task_id = details.get("task_id")
            if task_id:
                task = self.scheduler.get_task(task_id)
                if task:
                    return {"status": "acknowledged", "task_id": task_id}

        elif event_type == TimingEventType.CLOCK_DRIFT:
            component_id = details.get("component_id")
            if component_id:
                correction = self.clock_sync.correct_drift(component_id)
                self._log_event(TimingEventType.CLOCK_CORRECTED, correction)
                return correction

        elif event_type == TimingEventType.CONFLICT_DETECTED:
            conflicts = self.conflict_resolver.detect_conflicts()
            return {"status": "checked", "conflicts": len(conflicts)}

        return {"status": "handled", "event_type": event_type.value}

    def get_timing_status(self) -> Dict[str, Any]:
        all_tasks = self.scheduler.get_all_tasks()
        status_counts = defaultdict(int)
        for task in all_tasks.values():
            status_counts[task.status.value] += 1

        drifting = self.clock_sync.detect_drift()
        unresolved = [
            c for c in self.conflict_resolver.get_conflicts().values() if not c.resolved
        ]

        if unresolved or len(drifting) > 1:
            health = TimingHealth.CRITICAL
        elif drifting or status_counts.get("failed", 0) > 0:
            health = TimingHealth.DEGRADED
        else:
            health = TimingHealth.HEALTHY

        return {
            "health": health.value,
            "task_summary": dict(status_counts),
            "total_tasks": len(all_tasks),
            "drifting_clocks": len(drifting),
            "unresolved_conflicts": len(unresolved),
            "synchronized_time": self.clock_sync.get_synchronized_datetime().isoformat(),
            "execution_order": self._execution_order,
        }

    def _log_event(self, event_type: TimingEventType, details: Dict[str, Any]) -> None:
        event = TimingEvent(event_type=event_type, details=details)
        self._event_log.append(event)

    def get_event_log(self) -> List[TimingEvent]:
        return list(self._event_log)


def main():
    print("=" * 60)
    print("TimingOrchestrator 系統示範")
    print("=" * 60)

    print("\n--- 1. TaskScheduler 示範 ---")
    scheduler = TaskScheduler()

    scheduler.schedule_task(
        task_id="task_a",
        task_fn=lambda: "result_a",
        priority=3,
    )
    scheduler.schedule_task(
        task_id="task_b",
        task_fn=lambda: "result_b",
        priority=1,
    )
    scheduler.schedule_task(
        task_id="task_c",
        task_fn=lambda: "result_c",
        priority=5,
        scheduled_time=time.time() + 10,
    )

    print(f"Pending tasks: {[t.task_id for t in scheduler.get_pending_tasks()]}")
    print(f"Next task: {scheduler.get_next_task().task_id if scheduler.get_next_task() else None}")

    scheduler.cancel_task("task_c")
    print(f"After cancel task_c: {[t.task_id for t in scheduler.get_pending_tasks()]}")

    print("\n--- 2. ConflictResolver 示範 ---")
    scheduler2 = TaskScheduler()
    resolver = ConflictResolver(scheduler2)

    scheduler2.schedule_task("high_p", lambda: "high", priority=1)
    scheduler2.schedule_task("low_p", lambda: "low", priority=9)
    scheduler2.schedule_task("mid_p", lambda: "mid", priority=5)

    resolver.register_exclusion("high_p", {"database", "file_io"})
    resolver.register_exclusion("low_p", {"database"})
    resolver.register_exclusion("mid_p", {"file_io"})

    conflicts = resolver.detect_conflicts()
    print(f"Detected {len(conflicts)} conflict(s)")
    for c in conflicts:
        print(f"  Conflict {c.conflict_id}: tasks={c.task_ids}, resources={c.resources}")

    for c in conflicts:
        result = resolver.resolve_conflict(c.conflict_id, ConflictStrategy.PRIORITY_FIRST)
        print(f"  Resolved: {result['status']}, actions={result['actions']}")

    print("\n--- 3. ClockSynchronizer 示範 ---")
    clock_sync = ClockSynchronizer()

    clock_sync.register_clock("component_alpha", offset_ms=0)
    clock_sync.register_clock("component_beta", offset_ms=50)
    clock_sync.register_clock("component_gamma", offset_ms=-30)

    print(f"Synchronized time: {clock_sync.get_synchronized_datetime().isoformat()}")

    clock_sync.simulate_drift("component_beta", 200)
    drifting = clock_sync.detect_drift(threshold_ms=100)
    print(f"Drifting clocks: {[c.component_id for c in drifting]}")

    correction = clock_sync.correct_drift("component_beta")
    print(f"Correction result: {correction}")

    drifting_after = clock_sync.detect_drift(threshold_ms=100)
    print(f"Drifting after correction: {[c.component_id for c in drifting_after]}")

    print("\n--- 4. TimingOrchestrator 整合示範 ---")
    orchestrator = TimingOrchestrator()

    task_list = [
        {
            "task_id": "content_gen",
            "task_fn": lambda: "generated_content",
            "priority": 2,
            "exclusive_resources": {"llm_api", "database"},
        },
        {
            "task_id": "content_publish",
            "task_fn": lambda: "published",
            "priority": 3,
            "exclusive_resources": {"database"},
        },
        {
            "task_id": "analytics",
            "task_fn": lambda: "analytics_result",
            "priority": 5,
            "exclusive_resources": {"database"},
        },
        {
            "task_id": "cleanup",
            "task_fn": lambda: "cleaned",
            "priority": 8,
        },
    ]

    result = orchestrator.orchestrate(task_list)
    print(f"Orchestration result:")
    print(f"  Total tasks: {result['total_tasks']}")
    print(f"  Conflicts found: {result['conflicts_found']}")
    print(f"  Execution order: {result['execution_order']}")
    print(f"  Sync time: {result['synchronized_time']}")

    orchestrator.clock_sync.register_clock("scheduler_node", offset_ms=0)
    orchestrator.clock_sync.register_clock("worker_node_1", offset_ms=15)
    orchestrator.clock_sync.simulate_drift("worker_node_1", 150)

    drift_result = orchestrator.handle_timing_event(
        TimingEventType.CLOCK_DRIFT,
        {"component_id": "worker_node_1"},
    )
    print(f"  Clock drift correction: {drift_result['status']}")

    status = orchestrator.get_timing_status()
    print(f"\nTiming status:")
    print(f"  Health: {status['health']}")
    print(f"  Task summary: {status['task_summary']}")
    print(f"  Drifting clocks: {status['drifting_clocks']}")
    print(f"  Unresolved conflicts: {status['unresolved_conflicts']}")

    print("\n" + "=" * 60)
    print("TimingOrchestrator 示範完成 ✅")
    print("=" * 60)


if __name__ == "__main__":
    main()
