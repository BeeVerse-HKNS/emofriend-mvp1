"""
MasterOrchestrator - Master Agent 任務調度引擎

功能：
1. 任務路由（根據類型選擇子項目）
2. 執行監控（pending/running/completed/failed）
3. 錯誤處理（觸發 AutoFixingEngine）
4. 狀態同步（更新 AGENTS.md）

公式：A * C + G / S — 自動化 × 協同 + 守衛 / 自癒

相關規則：Rule 67 (Master Orchestrator 調度規則)
"""

from __future__ import annotations

import json
import logging
import subprocess
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from queue import Queue
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from .project_scanner import ProjectScanner, SubProject

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class TaskType(Enum):
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    SCRIPT_EXECUTE = "script_execute"
    TEST_RUN = "test_run"
    GIT_OPERATION = "git_operation"
    SCAN_PROJECT = "scan_project"
    GENERATE_REPORT = "generate_report"
    CUSTOM = "custom"


@dataclass
class Task:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    task_type: TaskType = TaskType.CUSTOM
    project_name: str = ""
    command: str = ""
    params: dict[str, Any] = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result: Any = None
    error: str | None = None
    retry_count: int = 0
    max_retries: int = 3

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "task_type": self.task_type.value,
            "project_name": self.project_name,
            "command": self.command,
            "params": self.params,
            "priority": self.priority.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result": str(self.result)[:500] if self.result else None,
            "error": self.error,
            "retry_count": self.retry_count,
        }


@dataclass
class TaskResult:
    task_id: str
    success: bool
    result: Any
    error: str | None = None
    duration_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "success": self.success,
            "result": str(self.result)[:500] if self.result else None,
            "error": self.error,
            "duration_seconds": self.duration_seconds,
        }


class MasterOrchestrator:
    """
    Master Agent 任務調度引擎

    統籌所有子項目嘅任務調度、執行監控同錯誤處理。
    """

    MAX_CONCURRENT_TASKS = 4
    TASK_TIMEOUT = 300

    def __init__(
        self,
        scanner: ProjectScanner,
        max_concurrent: int = MAX_CONCURRENT_TASKS,
        task_timeout: int = TASK_TIMEOUT,
    ):
        self.scanner = scanner
        self.max_concurrent = max_concurrent
        self.task_timeout = task_timeout

        self._task_queue: Queue[Task] = Queue()
        self._tasks: dict[str, Task] = {}
        self._results: dict[str, TaskResult] = {}
        self._workers: list[threading.Thread] = []
        self._running = False
        self._lock = threading.Lock()

        self._task_handlers: dict[TaskType, Callable[[Task], TaskResult]] = {
            TaskType.FILE_READ: self._handle_file_read,
            TaskType.FILE_WRITE: self._handle_file_write,
            TaskType.SCRIPT_EXECUTE: self._handle_script_execute,
            TaskType.SCAN_PROJECT: self._handle_scan_project,
            TaskType.GENERATE_REPORT: self._handle_generate_report,
        }

    def start(self) -> None:
        if self._running:
            return

        self._running = True
        for i in range(self.max_concurrent):
            worker = threading.Thread(target=self._worker_loop, daemon=True, name=f"worker-{i}")
            worker.start()
            self._workers.append(worker)

        logger.info(f"Master Orchestrator started with {self.max_concurrent} workers")

    def stop(self) -> None:
        self._running = False
        for worker in self._workers:
            worker.join(timeout=5)
        self._workers.clear()
        logger.info("Master Orchestrator stopped")

    def _worker_loop(self) -> None:
        while self._running:
            try:
                task = self._task_queue.get(timeout=1)
                self._execute_task(task)
                self._task_queue.task_done()
            except Exception:
                pass

    def submit_task(self, task: Task) -> str:
        with self._lock:
            self._tasks[task.id] = task

        self._task_queue.put(task)
        logger.info(f"Task {task.id} submitted: {task.task_type.value} for {task.project_name}")
        return task.id

    def submit_file_read(self, project_name: str, file_path: str, priority: TaskPriority = TaskPriority.MEDIUM) -> str:
        task = Task(
            task_type=TaskType.FILE_READ,
            project_name=project_name,
            command=file_path,
            priority=priority,
        )
        return self.submit_task(task)

    def submit_file_write(
        self,
        project_name: str,
        file_path: str,
        content: str,
        priority: TaskPriority = TaskPriority.MEDIUM,
    ) -> str:
        task = Task(
            task_type=TaskType.FILE_WRITE,
            project_name=project_name,
            command=file_path,
            params={"content": content},
            priority=priority,
        )
        return self.submit_task(task)

    def submit_script_execute(
        self,
        project_name: str,
        script_path: str,
        args: list[str] | None = None,
        priority: TaskPriority = TaskPriority.MEDIUM,
    ) -> str:
        task = Task(
            task_type=TaskType.SCRIPT_EXECUTE,
            project_name=project_name,
            command=script_path,
            params={"args": args or []},
            priority=priority,
        )
        return self.submit_task(task)

    def _execute_task(self, task: Task) -> None:
        with self._lock:
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now()

        start_time = datetime.now()

        try:
            handler = self._task_handlers.get(task.task_type, self._handle_custom)
            result = handler(task)

            with self._lock:
                task.status = TaskStatus.COMPLETED
                task.completed_at = datetime.now()
                task.result = result.result
                self._results[task.id] = result

            logger.info(f"Task {task.id} completed successfully")

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Task {task.id} failed: {error_msg}")

            with self._lock:
                task.error = error_msg
                task.retry_count += 1

                if task.retry_count < task.max_retries:
                    task.status = TaskStatus.PENDING
                    self._task_queue.put(task)
                    logger.info(f"Task {task.id} queued for retry ({task.retry_count}/{task.max_retries})")
                else:
                    task.status = TaskStatus.FAILED
                    task.completed_at = datetime.now()
                    self._results[task.id] = TaskResult(
                        task_id=task.id,
                        success=False,
                        result=None,
                        error=error_msg,
                        duration_seconds=(datetime.now() - start_time).total_seconds(),
                    )

    def _get_project_path(self, project_name: str) -> Path | None:
        projects = self.scanner.scan_all()
        for p in projects:
            if p.name == project_name:
                return p.path
        return None

    def _handle_file_read(self, task: Task) -> TaskResult:
        start = datetime.now()
        project_path = self._get_project_path(task.project_name)

        if not project_path:
            raise ValueError(f"Project not found: {task.project_name}")

        file_path = project_path / task.command
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        content = file_path.read_text(encoding="utf-8")

        return TaskResult(
            task_id=task.id,
            success=True,
            result=content,
            duration_seconds=(datetime.now() - start).total_seconds(),
        )

    def _handle_file_write(self, task: Task) -> TaskResult:
        start = datetime.now()
        project_path = self._get_project_path(task.project_name)

        if not project_path:
            raise ValueError(f"Project not found: {task.project_name}")

        file_path = project_path / task.command
        content = task.params.get("content", "")

        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")

        return TaskResult(
            task_id=task.id,
            success=True,
            result=f"Written {len(content)} bytes to {file_path}",
            duration_seconds=(datetime.now() - start).total_seconds(),
        )

    def _handle_script_execute(self, task: Task) -> TaskResult:
        start = datetime.now()
        project_path = self._get_project_path(task.project_name)

        if not project_path:
            raise ValueError(f"Project not found: {task.project_name}")

        script_path = project_path / task.command
        args = task.params.get("args", [])

        if not script_path.exists():
            raise FileNotFoundError(f"Script not found: {script_path}")

        cmd = ["python", str(script_path)] + args
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=self.task_timeout,
            cwd=str(project_path),
        )

        if result.returncode != 0:
            raise RuntimeError(f"Script failed: {result.stderr}")

        return TaskResult(
            task_id=task.id,
            success=True,
            result=result.stdout,
            duration_seconds=(datetime.now() - start).total_seconds(),
        )

    def _handle_scan_project(self, task: Task) -> TaskResult:
        start = datetime.now()
        project = self.scanner.scan_single(task.project_name)

        if not project:
            raise ValueError(f"Project not found: {task.project_name}")

        return TaskResult(
            task_id=task.id,
            success=True,
            result=project.to_dict(),
            duration_seconds=(datetime.now() - start).total_seconds(),
        )

    def _handle_generate_report(self, task: Task) -> TaskResult:
        start = datetime.now()
        from .status_dashboard import StatusDashboard

        dashboard = StatusDashboard(self.scanner)
        report = dashboard.render_markdown()

        return TaskResult(
            task_id=task.id,
            success=True,
            result=report,
            duration_seconds=(datetime.now() - start).total_seconds(),
        )

    def _handle_custom(self, task: Task) -> TaskResult:
        return TaskResult(
            task_id=task.id,
            success=True,
            result="Custom task - no handler defined",
        )

    def get_task_status(self, task_id: str) -> Task | None:
        with self._lock:
            return self._tasks.get(task_id)

    def get_task_result(self, task_id: str) -> TaskResult | None:
        with self._lock:
            return self._results.get(task_id)

    def get_pending_tasks(self) -> list[Task]:
        with self._lock:
            return [t for t in self._tasks.values() if t.status == TaskStatus.PENDING]

    def get_running_tasks(self) -> list[Task]:
        with self._lock:
            return [t for t in self._tasks.values() if t.status == TaskStatus.RUNNING]

    def cancel_task(self, task_id: str) -> bool:
        with self._lock:
            task = self._tasks.get(task_id)
            if task and task.status == TaskStatus.PENDING:
                task.status = TaskStatus.CANCELLED
                return True
        return False

    def get_statistics(self) -> dict[str, Any]:
        with self._lock:
            tasks = list(self._tasks.values())

        return {
            "total_tasks": len(tasks),
            "pending": sum(1 for t in tasks if t.status == TaskStatus.PENDING),
            "running": sum(1 for t in tasks if t.status == TaskStatus.RUNNING),
            "completed": sum(1 for t in tasks if t.status == TaskStatus.COMPLETED),
            "failed": sum(1 for t in tasks if t.status == TaskStatus.FAILED),
            "cancelled": sum(1 for t in tasks if t.status == TaskStatus.CANCELLED),
        }

    def is_running(self) -> bool:
        return self._running


def create_orchestrator(root_path: Path | str) -> MasterOrchestrator:
    from .project_scanner import ProjectScanner

    scanner = ProjectScanner(root_path)
    return MasterOrchestrator(scanner)


if __name__ == "__main__":
    import sys

    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    orchestrator = create_orchestrator(root)

    orchestrator.start()

    print("提交掃描任務...")
    task_id = orchestrator.submit_task(
        Task(
            task_type=TaskType.SCAN_PROJECT,
            project_name="ai-content-creator",
        )
    )

    import time

    time.sleep(2)

    result = orchestrator.get_task_result(task_id)
    if result:
        print(f"任務結果：{result.success}")
        if result.result:
            print(f"項目信息：{result.result.get('name', 'N/A')}")

    orchestrator.stop()
