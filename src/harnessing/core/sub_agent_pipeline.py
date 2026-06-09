from __future__ import annotations

import concurrent.futures
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class Task:
    id: str
    fn: Callable[[], Any]
    depends_on: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id or not isinstance(self.id, str):
            raise ValueError("Task.id must be a non-empty string")
        if not callable(self.fn):
            raise ValueError(f"Task.fn for {self.id} must be callable")
        self.depends_on = list(self.depends_on) if self.depends_on else []


@dataclass
class TaskResult:
    task_id: str
    status: TaskStatus
    value: Any = None
    error: Optional[str] = None
    started_at: float = 0.0
    finished_at: float = 0.0
    duration_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "status": self.status.value,
            "value": self.value,
            "error": self.error,
            "duration_seconds": round(self.duration_seconds, 4),
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }


@dataclass
class PipelineStats:
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    skipped_tasks: int = 0
    max_parallelism: int = 0
    total_duration_seconds: float = 0.0
    history: deque = field(default_factory=lambda: deque(maxlen=200))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_tasks": self.total_tasks,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "skipped_tasks": self.skipped_tasks,
            "max_parallelism": self.max_parallelism,
            "total_duration_seconds": round(self.total_duration_seconds, 4),
            "success_rate": round(
                self.completed_tasks / self.total_tasks, 4
            ) if self.total_tasks > 0 else 0.0,
        }


class Pipeline:
    def __init__(self, max_workers: Optional[int] = None, fail_fast: bool = True) -> None:
        self._tasks: Dict[str, Task] = {}
        self._results: Dict[str, TaskResult] = {}
        self._max_workers = max_workers
        self._fail_fast = fail_fast
        self._stats = PipelineStats()
        logger.info(f"pipeline_initialized max_workers={max_workers} fail_fast={fail_fast}")

    def add_task(self, task: Task) -> None:
        if task.id in self._tasks:
            raise ValueError(f"task_id_already_exists id={task.id}")
        for dep in task.depends_on:
            if not isinstance(dep, str):
                raise ValueError(f"dependency_must_be_string dep={dep}")
        self._tasks[task.id] = task
        logger.debug(f"pipeline_task_added id={task.id} deps={task.depends_on}")

    def add_tasks(self, tasks: List[Task]) -> None:
        for t in tasks:
            self.add_task(t)

    def task_count(self) -> int:
        return len(self._tasks)

    def _validate_dependencies(self) -> None:
        for task in self._tasks.values():
            for dep in task.depends_on:
                if dep not in self._tasks:
                    raise ValueError(
                        f"missing_dependency task={task.id} missing={dep}"
                    )
                if dep == task.id:
                    raise ValueError(f"self_dependency task={task.id}")

    def _detect_cycle(self) -> None:
        WHITE, GRAY, BLACK = 0, 1, 2
        color: Dict[str, int] = {tid: WHITE for tid in self._tasks}
        stack: List[str] = []

        def dfs(node: str) -> None:
            color[node] = GRAY
            stack.append(node)
            for dep in self._tasks[node].depends_on:
                if dep not in color:
                    continue
                if color[dep] == GRAY:
                    cycle = stack[stack.index(dep):] + [dep]
                    raise ValueError(f"cycle_detected path={cycle}")
                if color[dep] == WHITE:
                    dfs(dep)
            stack.pop()
            color[node] = BLACK

        for tid in self._tasks:
            if color[tid] == WHITE:
                dfs(tid)

    def _topological_order(self) -> List[str]:
        in_degree: Dict[str, int] = {tid: 0 for tid in self._tasks}
        children: Dict[str, List[str]] = {tid: [] for tid in self._tasks}
        for tid, task in self._tasks.items():
            for dep in task.depends_on:
                in_degree[tid] += 1
                children[dep].append(tid)
        queue = [tid for tid, deg in in_degree.items() if deg == 0]
        order: List[str] = []
        while queue:
            queue.sort()
            current = queue.pop(0)
            order.append(current)
            for child in children[current]:
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    queue.append(child)
        if len(order) != len(self._tasks):
            missing = set(self._tasks.keys()) - set(order)
            raise ValueError(f"cycle_detected remaining={missing}")
        return order

    def _ready_tasks(self, completed: Set[str], failed: Set[str]) -> List[str]:
        ready = []
        for tid, task in self._tasks.items():
            if tid in completed or tid in failed:
                continue
            if all(dep in completed for dep in task.depends_on):
                if any(dep in failed for dep in task.depends_on):
                    self._results[tid] = TaskResult(
                        task_id=tid,
                        status=TaskStatus.SKIPPED,
                        error="upstream_dependency_failed",
                    )
                    self._stats.skipped_tasks += 1
                    failed.add(tid)
                    logger.warning(f"pipeline_task_skipped id={tid} reason=upstream_failed")
                    continue
                ready.append(tid)
        return ready

    def _execute_task(self, task: Task) -> TaskResult:
        started = time.time()
        result = TaskResult(
            task_id=task.id,
            status=TaskStatus.RUNNING,
            started_at=started,
        )
        try:
            value = task.fn()
            finished = time.time()
            result.status = TaskStatus.COMPLETED
            result.value = value
            result.finished_at = finished
            result.duration_seconds = finished - started
            self._stats.completed_tasks += 1
            logger.info(
                f"pipeline_task_completed id={task.id} duration={result.duration_seconds:.4f}"
            )
        except Exception as exc:
            finished = time.time()
            result.status = TaskStatus.FAILED
            result.error = f"{type(exc).__name__}: {exc}"
            result.finished_at = finished
            result.duration_seconds = finished - started
            self._stats.failed_tasks += 1
            logger.error(
                f"pipeline_task_failed id={task.id} error={result.error} duration={result.duration_seconds:.4f}"
            )
            if self._fail_fast:
                raise
        return result

    def execute(self) -> Dict[str, Any]:
        self._validate_dependencies()
        self._detect_cycle()
        self._results = {}
        self._stats = PipelineStats(total_tasks=len(self._tasks))
        order = self._topological_order()
        completed: Set[str] = set()
        failed: Set[str] = set()
        start_time = time.time()
        logger.info(
            f"pipeline_execute_start tasks={len(self._tasks)} order={order} max_workers={self._max_workers}"
        )
        with concurrent.futures.ThreadPoolExecutor(max_workers=self._max_workers) as pool:
            in_flight: Dict[concurrent.futures.Future, str] = {}
            try:
                while len(completed) + len(failed) < len(self._tasks):
                    ready = self._ready_tasks(completed, failed)
                    for tid in ready:
                        if tid in in_flight:
                            continue
                        task = self._tasks[tid]
                        future = pool.submit(self._execute_task, task)
                        in_flight[future] = tid
                    if not in_flight:
                        break
                    done, _ = concurrent.futures.wait(
                        in_flight.keys(),
                        return_when=concurrent.futures.FIRST_COMPLETED,
                    )
                    if len(in_flight) > self._stats.max_parallelism:
                        self._stats.max_parallelism = len(in_flight)
                    for future in done:
                        tid = in_flight.pop(future)
                        try:
                            result = future.result()
                        except Exception as exc:
                            result = TaskResult(
                                task_id=tid,
                                status=TaskStatus.FAILED,
                                error=f"{type(exc).__name__}: {exc}",
                                finished_at=time.time(),
                            )
                            self._stats.failed_tasks += 1
                            failed.add(tid)
                            self._results[tid] = result
                            if self._fail_fast:
                                for pending in in_flight:
                                    pending.cancel()
                                raise
                            continue
                        self._results[tid] = result
                        if result.status == TaskStatus.COMPLETED:
                            completed.add(tid)
                        elif result.status == TaskStatus.FAILED:
                            failed.add(tid)
            except Exception as exc:
                logger.error(f"pipeline_execute_aborted error={exc}")
                for pending in in_flight:
                    pending.cancel()
        self._stats.total_duration_seconds = time.time() - start_time
        self._stats.history.append({
            "timestamp": start_time,
            "tasks": len(self._tasks),
            "completed": self._stats.completed_tasks,
            "failed": self._stats.failed_tasks,
            "skipped": self._stats.skipped_tasks,
            "max_parallelism": self._stats.max_parallelism,
            "duration": self._stats.total_duration_seconds,
        })
        logger.info(
            f"pipeline_execute_complete completed={self._stats.completed_tasks} "
            f"failed={self._stats.failed_tasks} skipped={self._stats.skipped_tasks} "
            f"duration={self._stats.total_duration_seconds:.4f}"
        )
        return {tid: r.value for tid, r in self._results.items()}

    def results(self) -> Dict[str, TaskResult]:
        return dict(self._results)

    def stats(self) -> Dict[str, Any]:
        base = self._stats.to_dict()
        base["registered_tasks"] = len(self._tasks)
        base["max_workers"] = self._max_workers
        base["fail_fast"] = self._fail_fast
        return base

    def reset(self) -> None:
        self._tasks.clear()
        self._results.clear()
        self._stats = PipelineStats()
        logger.info("pipeline_reset")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(name)s | %(levelname)s | %(message)s")

    p = Pipeline()

    p.add_task(Task(id="fetch", fn=lambda: {"data": [1, 2, 3]}))
    p.add_task(Task(id="parse", fn=lambda: {"parsed": True}, depends_on=["fetch"]))
    p.add_task(Task(id="validate", fn=lambda: {"valid": True}, depends_on=["parse"]))
    p.add_task(Task(id="transform_a", fn=lambda: {"variant": "A"}, depends_on=["validate"]))
    p.add_task(Task(id="transform_b", fn=lambda: {"variant": "B"}, depends_on=["validate"]))
    p.add_task(Task(id="merge", fn=lambda a, b: {"merged": True}, depends_on=["transform_a", "transform_b"]))

    results = p.execute()
    print(f"Results: {results}")
    print(f"Stats: {p.stats()}")

    print("\n=== Cycle detection ===")
    p2 = Pipeline()
    p2.add_task(Task(id="x", fn=lambda: 1, depends_on=["y"]))
    p2.add_task(Task(id="y", fn=lambda: 2, depends_on=["x"]))
    try:
        p2.execute()
    except ValueError as exc:
        print(f"Correctly detected cycle: {exc}")

    print("\n=== Missing dependency ===")
    p3 = Pipeline()
    p3.add_task(Task(id="a", fn=lambda: 1, depends_on=["nonexistent"]))
    try:
        p3.execute()
    except ValueError as exc:
        print(f"Correctly detected missing dep: {exc}")


if __name__ == "__main__":
    main()
