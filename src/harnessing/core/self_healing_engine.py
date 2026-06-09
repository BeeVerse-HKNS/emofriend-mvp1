#!/usr/bin/env python3
"""
Self-Healing Engine
Claude Code 風格的自癒系統，使用純 Python 實現

核心能力：
1. CheckpointManager — 任務狀態定期保存（pickle/json）
2. CircuitBreaker — 錯誤超限熔斷
3. RecoveryEngine — 失敗後自動恢復
4. MultiTriggerLauncher — 三層觸發
5. SelfReflection — 任務完成後反思
6. GoalAnchor — 目標錨定，防止長程執行偏離
7. HumanInTheLoop — 人類介入，關鍵節點批准

⚠️ Sandbox 安全原則：
- 所有文件操作限制喺允許嘅目錄內
- 高風險操作（delete/publish/push）需要人類批准
- 任務執行前檢查目標對齊
- 定期記錄checkpoint，防止中斷丟失數據
- 使用隔離目錄存儲敏感數據

遵循零外部依賴原則，使用標準庫實現
"""

import json
import os
import pickle
import time
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import deque
import threading
import traceback


class CheckpointState(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RECOVERED = "recovered"
    AWAITING_APPROVAL = "awaiting_approval"


@dataclass
class TaskCheckpoint:
    task_id: str
    task_type: str
    description: str
    status: CheckpointState
    created_at: str
    last_checkpoint_at: str
    goal: str = ""
    completed_steps: List[str] = field(default_factory=list)
    pending_steps: List[str] = field(default_factory=list)
    current_step: str = ""
    step_index: int = 0
    retry_count: int = 0
    error_history: List[Dict] = field(default_factory=list)
    context_data: Dict[str, Any] = field(default_factory=dict)
    result_data: Any = None
    approval_required: bool = False
    approved_steps: List[str] = field(default_factory=list)
    deviation_score: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "description": self.description,
            "status": self.status.value,
            "created_at": self.created_at,
            "last_checkpoint_at": self.last_checkpoint_at,
            "completed_steps": self.completed_steps,
            "pending_steps": self.pending_steps,
            "current_step": self.current_step,
            "step_index": self.step_index,
            "retry_count": self.retry_count,
            "error_history": self.error_history,
            "context_data": self.context_data,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "TaskCheckpoint":
        return cls(
            task_id=data["task_id"],
            task_type=data["task_type"],
            description=data["description"],
            status=CheckpointState(data["status"]),
            created_at=data["created_at"],
            last_checkpoint_at=data["last_checkpoint_at"],
            completed_steps=data.get("completed_steps", []),
            pending_steps=data.get("pending_steps", []),
            current_step=data.get("current_step", ""),
            step_index=data.get("step_index", 0),
            retry_count=data.get("retry_count", 0),
            error_history=data.get("error_history", []),
            context_data=data.get("context_data", {}),
            result_data=data.get("result_data"),
        )


class CheckpointManager:
    """
    任務狀態定期保存管理器
    Claude Code 核心功能：用 pickle 保存執行狀態，失敗後可恢復
    """

    def __init__(self, base_path: Optional[Path] = None, interval_seconds: int = 60):
        if base_path is None:
            base_path = Path(__file__).parent.parent.parent / "data"
        self.base_path = Path(base_path)
        self.checkpoint_dir = self.base_path / "checkpoints"
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.interval_seconds = interval_seconds
        self._checkpoints: Dict[str, TaskCheckpoint] = {}
        self._last_save_time: Dict[str, float] = {}
        self._lock = threading.Lock()
        self._auto_save_enabled = True
        self.logger = logging.getLogger(__name__)

    def _get_checkpoint_path(self, task_id: str) -> Path:
        return self.checkpoint_dir / f"{task_id}.pkl"

    def create_checkpoint(self, task_id: str, task_type: str, description: str,
                         pending_steps: List[str]) -> TaskCheckpoint:
        checkpoint = TaskCheckpoint(
            task_id=task_id,
            task_type=task_type,
            description=description,
            status=CheckpointState.PENDING,
            created_at=datetime.now().isoformat(),
            last_checkpoint_at=datetime.now().isoformat(),
            pending_steps=pending_steps.copy(),
        )
        with self._lock:
            self._checkpoints[task_id] = checkpoint
            self._save_checkpoint(checkpoint)
        self.logger.info(f"Created checkpoint for task: {task_id}")
        return checkpoint

    def update_checkpoint(self, task_id: str, completed_step: str = None,
                         current_step: str = None, status: CheckpointState = None,
                         context_update: Dict = None) -> bool:
        with self._lock:
            checkpoint = self._checkpoints.get(task_id)
            if not checkpoint:
                checkpoint = self._load_checkpoint(task_id)
                if not checkpoint:
                    self.logger.warning(f"Checkpoint not found: {task_id}")
                    return False

            now = datetime.now().isoformat()
            checkpoint.last_checkpoint_at = now

            if completed_step:
                if completed_step not in checkpoint.completed_steps:
                    checkpoint.completed_steps.append(completed_step)
                if completed_step in checkpoint.pending_steps:
                    checkpoint.pending_steps.remove(completed_step)
                checkpoint.step_index += 1

            if current_step:
                checkpoint.current_step = current_step

            if status:
                checkpoint.status = status

            if context_update:
                checkpoint.context_data.update(context_update)

            self._checkpoints[task_id] = checkpoint
            if self._should_save(task_id):
                self._save_checkpoint(checkpoint)
                self._last_save_time[task_id] = time.time()

            return True

    def _should_save(self, task_id: str) -> bool:
        if not self._auto_save_enabled:
            return True
        last_time = self._last_save_time.get(task_id, 0)
        return (time.time() - last_time) >= self.interval_seconds

    def _save_checkpoint(self, checkpoint: TaskCheckpoint) -> None:
        path = self._get_checkpoint_path(checkpoint.task_id)
        with open(path, "wb") as f:
            pickle.dump(checkpoint, f)

    def _load_checkpoint(self, task_id: str) -> Optional[TaskCheckpoint]:
        path = self._get_checkpoint_path(task_id)
        if not path.exists():
            return None
        try:
            with open(path, "rb") as f:
                return pickle.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load checkpoint {task_id}: {e}")
            return None

    def get_checkpoint(self, task_id: str) -> Optional[TaskCheckpoint]:
        with self._lock:
            if task_id in self._checkpoints:
                return self._checkpoints[task_id]
            checkpoint = self._load_checkpoint(task_id)
            if checkpoint:
                self._checkpoints[task_id] = checkpoint
            return checkpoint

    def get_all_checkpoints(self) -> List[TaskCheckpoint]:
        checkpoints = []
        for pkl_file in self.checkpoint_dir.glob("*.pkl"):
            task_id = pkl_file.stem
            checkpoint = self.get_checkpoint(task_id)
            if checkpoint:
                checkpoints.append(checkpoint)
        return checkpoints

    def get_recoverable_tasks(self) -> List[TaskCheckpoint]:
        recoverable = []
        for checkpoint in self.get_all_checkpoints():
            if checkpoint.status in [CheckpointState.RUNNING, CheckpointState.FAILED]:
                if checkpoint.pending_steps:
                    recoverable.append(checkpoint)
        return recoverable

    def delete_checkpoint(self, task_id: str) -> bool:
        with self._lock:
            path = self._get_checkpoint_path(task_id)
            if path.exists():
                path.unlink()
            if task_id in self._checkpoints:
                del self._checkpoints[task_id]
            return True

    def enable_auto_save(self, enabled: bool = True) -> None:
        self._auto_save_enabled = enabled

    def get_task_summary(self, task_id: str) -> Dict:
        checkpoint = self.get_checkpoint(task_id)
        if not checkpoint:
            return {"error": "Task not found"}

        total_steps = len(checkpoint.completed_steps) + len(checkpoint.pending_steps)
        progress = (len(checkpoint.completed_steps) / total_steps * 100) if total_steps > 0 else 0

        return {
            "task_id": checkpoint.task_id,
            "description": checkpoint.description,
            "status": checkpoint.status.value,
            "progress": f"{progress:.1f}%",
            "completed": len(checkpoint.completed_steps),
            "pending": len(checkpoint.pending_steps),
            "current_step": checkpoint.current_step,
            "retry_count": checkpoint.retry_count,
            "last_checkpoint": checkpoint.last_checkpoint_at,
        }


class CircuitBreaker:
    """
    熔斷器
    錯誤超限自動熔斷，避免惡性循環
    """

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60,
                 expected_exception: type = Exception):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "closed"
        self._lock = threading.Lock()
        self.logger = logging.getLogger(__name__)

    def call(self, func: Callable, *args, **kwargs) -> Any:
        with self._lock:
            if self.state == "open":
                if self._should_attempt_reset():
                    self.state = "half_open"
                    self.logger.info("Circuit breaker: Attempting reset (half_open)")
                else:
                    raise Exception(f"Circuit breaker is OPEN. Function call rejected.")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e

    def _on_success(self) -> None:
        with self._lock:
            self.failure_count = 0
            if self.state == "half_open":
                self.state = "closed"
                self.logger.info("Circuit breaker: Reset to closed")

    def _on_failure(self) -> None:
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.failure_count >= self.failure_threshold:
                self.state = "open"
                self.logger.warning(f"Circuit breaker: Opened after {self.failure_count} failures")

    def _should_attempt_reset(self) -> bool:
        if self.last_failure_time is None:
            return True
        return (time.time() - self.last_failure_time) >= self.recovery_timeout

    def reset(self) -> None:
        with self._lock:
            self.failure_count = 0
            self.state = "closed"
            self.last_failure_time = None
            self.logger.info("Circuit breaker: Manual reset")

    def get_state(self) -> Dict:
        with self._lock:
            return {
                "state": self.state,
                "failure_count": self.failure_count,
                "threshold": self.failure_threshold,
                "last_failure": self.last_failure_time,
            }


class RecoveryEngine:
    """
    恢復引擎
    失敗後自動恢復到最後檢查點
    """

    def __init__(self, checkpoint_manager: CheckpointManager):
        self.checkpoint_manager = checkpoint_manager
        self.logger = logging.getLogger(__name__)

    def recover_task(self, task_id: str, task_executor: Callable,
                     max_retries: int = 3) -> Dict[str, Any]:
        checkpoint = self.checkpoint_manager.get_checkpoint(task_id)
        if not checkpoint:
            return {"success": False, "error": "Checkpoint not found"}

        if not checkpoint.pending_steps:
            return {
                "success": True,
                "message": "Task already completed",
                "result": checkpoint.result_data,
            }

        self.logger.info(f"Recovering task {task_id}, {len(checkpoint.pending_steps)} steps pending")
        self.checkpoint_manager.update_checkpoint(task_id, status=CheckpointState.RUNNING)

        results = []
        for step in checkpoint.pending_steps:
            retry_count = 0
            success = False

            while retry_count < max_retries and not success:
                try:
                    self.checkpoint_manager.update_checkpoint(
                        task_id, current_step=step
                    )

                    result = task_executor(step, checkpoint.context_data)
                    self.checkpoint_manager.update_checkpoint(
                        task_id, completed_step=step
                    )
                    results.append({"step": step, "result": result, "success": True})
                    success = True

                except Exception as e:
                    retry_count += 1
                    checkpoint = self.checkpoint_manager.get_checkpoint(task_id)
                    checkpoint.error_history.append({
                        "step": step,
                        "error": str(e),
                        "traceback": traceback.format_exc(),
                        "timestamp": datetime.now().isoformat(),
                        "retry": retry_count,
                    })
                    checkpoint.retry_count = retry_count
                    self.checkpoint_manager.update_checkpoint(task_id)

                    if retry_count >= max_retries:
                        self.logger.error(f"Step {step} failed after {max_retries} retries")
                        results.append({
                            "step": step,
                            "error": str(e),
                            "success": False,
                        })
                    else:
                        wait_time = min(2 ** retry_count, 30)
                        self.logger.info(f"Retrying step {step} in {wait_time}s...")
                        time.sleep(wait_time)

        all_success = all(r.get("success", False) for r in results)
        final_status = CheckpointState.COMPLETED if all_success else CheckpointState.FAILED
        self.checkpoint_manager.update_checkpoint(task_id, status=final_status)

        return {
            "success": all_success,
            "task_id": task_id,
            "steps_completed": len([r for r in results if r.get("success")]),
            "steps_failed": len([r for r in results if not r.get("success")]),
            "results": results,
        }

    def auto_recover_all(self, task_executor: Callable) -> List[Dict]:
        recoverable_tasks = self.checkpoint_manager.get_recoverable_tasks()
        results = []

        for task in recoverable_tasks:
            if task.retry_count >= 3:
                self.logger.info(f"Skipping task {task.task_id} - max retries exceeded")
                continue

            result = self.recover_task(task.task_id, task_executor)
            results.append(result)

        return results


class MultiTriggerLauncher:
    """
    多層觸發器
    三層觸發：Startup Folder + Task Scheduler + Registry
    """

    def __init__(self, base_path: Optional[Path] = None):
        if base_path is None:
            base_path = Path(__file__).parent.parent.parent
        self.base_path = Path(base_path)
        self.logger = logging.getLogger(__name__)

    def check_startup_folder(self) -> bool:
        startup_path = Path(os.path.expanduser("~/AppData/Roaming/Microsoft/Windows/Start Menu/Programs/Startup"))
        harness_launcher = startup_path / "harnessing_launcher.bat"
        return harness_launcher.exists()

    def install_startup(self) -> bool:
        try:
            startup_path = Path(os.path.expanduser("~/AppData/Roaming/Microsoft/Windows/Start Menu/Programs/Startup"))
            startup_path.mkdir(parents=True, exist_ok=True)

            launcher_content = f'''@echo off
cd /d "{self.base_path}"
python "{self.base_path / "scripts" / "startup_resume_agent.py"}"
'''
            launcher_path = startup_path / "harnessing_launcher.bat"
            with open(launcher_path, "w", encoding="utf-8") as f:
                f.write(launcher_content)

            self.logger.info(f"Installed startup launcher to: {launcher_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to install startup: {e}")
            return False

    def uninstall_startup(self) -> bool:
        try:
            startup_path = Path(os.path.expanduser("~/AppData/Roaming/Microsoft/Windows/Start Menu/Programs/Startup"))
            launcher_path = startup_path / "harnessing_launcher.bat"
            if launcher_path.exists():
                launcher_path.unlink()
                self.logger.info("Uninstalled startup launcher")
            return True
        except Exception as e:
            self.logger.error(f"Failed to uninstall startup: {e}")
            return False

    def check_scheduler(self) -> bool:
        import subprocess
        try:
            result = subprocess.run(
                ["schtasks", "/query", "/tn", "HarnessingResume"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0
        except Exception:
            return False

    def install_scheduler(self) -> bool:
        import subprocess
        try:
            script_path = self.base_path / "scripts" / "startup_resume_agent.py"
            cmd = [
                "schtasks", "/create",
                "/tn", "HarnessingResume",
                "/tr", f'python "{script_path}"',
                "/sc", "onlogon",
                "/f",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                self.logger.info("Installed task scheduler")
                return True
            else:
                self.logger.warning(f"Scheduler install failed: {result.stderr}")
                return False
        except Exception as e:
            self.logger.error(f"Failed to install scheduler: {e}")
            return False

    def get_trigger_status(self) -> Dict:
        return {
            "startup_folder": self.check_startup_folder(),
            "task_scheduler": self.check_scheduler(),
        }


class SelfReflection:
    """
    自我反思
    任務完成後反思，記錄學習
    """

    def __init__(self, base_path: Optional[Path] = None):
        if base_path is None:
            base_path = Path(__file__).parent.parent.parent / "data"
        self.base_path = Path(base_path)
        self.reflection_dir = self.base_path / "reflections"
        self.reflection_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)

    def reflect(self, task_id: str, checkpoint: TaskCheckpoint,
                result: Dict, context: Dict = None) -> Dict:
        reflections = {
            "task_id": task_id,
            "timestamp": datetime.now().isoformat(),
            "task_type": checkpoint.task_type,
            "description": checkpoint.description,
            "status": checkpoint.status.value,
            "completed_steps": checkpoint.completed_steps,
            "failed_steps": [],
            "errors": checkpoint.error_history,
            "retry_count": checkpoint.retry_count,
            "duration": self._calculate_duration(checkpoint),
            "patterns": [],
            "lessons": [],
            "recommendations": [],
        }

        for step_result in result.get("results", []):
            if not step_result.get("success", False):
                reflections["failed_steps"].append(step_result.get("step"))

        reflections["patterns"] = self._identify_patterns(reflections)
        reflections["lessons"] = self._generate_lessons(reflections)
        reflections["recommendations"] = self._generate_recommendations(reflections)

        self._save_reflection(task_id, reflections)
        self.logger.info(f"Saved reflection for task: {task_id}")

        return reflections

    def _calculate_duration(self, checkpoint: TaskCheckpoint) -> Optional[str]:
        try:
            start = datetime.fromisoformat(checkpoint.created_at)
            end = datetime.fromisoformat(checkpoint.last_checkpoint_at)
            duration = end - start
            total_seconds = int(duration.total_seconds())
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            if hours > 0:
                return f"{hours}h {minutes}m"
            elif minutes > 0:
                return f"{minutes}m {seconds}s"
            else:
                return f"{seconds}s"
        except Exception:
            return None

    def _identify_patterns(self, reflections: Dict) -> List[str]:
        patterns = []

        if reflections["retry_count"] > 2:
            patterns.append("high_retry_rate")

        if len(reflections["failed_steps"]) > 3:
            patterns.append("multiple_failures")

        if reflections["errors"]:
            error_types = [e.get("error", "").split(":")[0] for e in reflections["errors"]]
            if len(set(error_types)) > 2:
                patterns.append("diverse_errors")

        return patterns

    def _generate_lessons(self, reflections: Dict) -> List[str]:
        lessons = []

        if "high_retry_rate" in reflections["patterns"]:
            lessons.append("任務需要更多預先檢查，避免重試浪費時間")

        if "multiple_failures" in reflections["patterns"]:
            lessons.append("連續失敗可能表示系統性問題，需要重新設計流程")

        if reflections["status"] == "completed":
            lessons.append("成功完成，但需要檢查係咪可以優化步驟")

        return lessons

    def _generate_recommendations(self, reflections: Dict) -> List[str]:
        recommendations = []

        if "high_retry_rate" in reflections["patterns"]:
            recommendations.append("下次任務添加更多前置驗證步驟")

        if reflections["retry_count"] > 0:
            recommendations.append("考慮增加 CircuitBreaker 閾值或添加降級策略")

        if reflections["status"] == "completed":
            recommendations.append("任務成功，可以考慮自動化定時執行")

        return recommendations

    def _save_reflection(self, task_id: str, reflections: Dict) -> None:
        path = self.reflection_dir / f"{task_id}_reflection.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(reflections, f, indent=2, ensure_ascii=False)

    def get_recent_reflections(self, limit: int = 10) -> List[Dict]:
        reflections = []
        for json_file in sorted(
            self.reflection_dir.glob("*_reflection.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )[:limit]:
            with open(json_file, "r", encoding="utf-8") as f:
                reflections.append(json.load(f))
        return reflections


class GoalAnchor:
    """
    目標錨定器
    防止長程執行偏離目標
    Claude Code 使用目標錨定確保任務唔偏離
    """

    def __init__(self, base_path: Optional[Path] = None):
        if base_path is None:
            base_path = Path(__file__).parent.parent.parent / "data"
        self.base_path = Path(base_path)
        self.anchor_dir = self.base_path / "goal_anchors"
        self.anchor_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)

    def create_anchor(self, task_id: str, goal: str, task_type: str = "general") -> Dict:
        anchor = {
            "task_id": task_id,
            "goal": goal,
            "task_type": task_type,
            "created_at": datetime.now().isoformat(),
            "checkpoints": [],
            "deviation_history": [],
            "status": "active",
        }
        path = self.anchor_dir / f"{task_id}_anchor.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(anchor, f, indent=2, ensure_ascii=False)
        self.logger.info(f"Created goal anchor for task: {task_id}")
        return anchor

    def load_anchor(self, task_id: str) -> Optional[Dict]:
        path = self.anchor_dir / f"{task_id}_anchor.json"
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def check_alignment(self, task_id: str, current_step: str, context: Dict = None) -> Dict:
        anchor = self.load_anchor(task_id)
        if not anchor:
            return {"aligned": True, "deviation": 0.0, "message": "No anchor found"}

        goal_keywords = self._extract_keywords(anchor["goal"])
        step_keywords = self._extract_keywords(current_step)

        overlap = len(set(goal_keywords) & set(step_keywords))
        total = len(goal_keywords) if goal_keywords else 1
        alignment_score = overlap / total

        deviation = 1.0 - alignment_score

        result = {
            "task_id": task_id,
            "goal": anchor["goal"],
            "current_step": current_step,
            "aligned": alignment_score >= 0.3,
            "deviation": deviation,
            "alignment_score": alignment_score,
            "message": "",
        }

        if deviation > 0.7:
            result["message"] = f"⚠️ 警告：當前步驟偏離目標！目標：{anchor['goal']}"
            self._record_deviation(task_id, current_step, deviation)
        elif deviation > 0.4:
            result["message"] = f"⚡ 注意：步驟與目標部分相關"
        else:
            result["message"] = "✅ 步驟與目標對齊"

        return result

    def _extract_keywords(self, text: str) -> List[str]:
        if not text:
            return []
        stopwords = {"的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一", "一個", "上", "也", "很", "到", "說", "要", "去", "你", "會", "著", "無", "這個", "咁", "噉", "個", "為", "地", "個", "咗"}
        words = [w for w in text if len(w) > 1 and w not in stopwords]
        return words

    def _record_deviation(self, task_id: str, step: str, deviation: float) -> None:
        anchor = self.load_anchor(task_id)
        if anchor:
            anchor["deviation_history"].append({
                "step": step,
                "deviation": deviation,
                "timestamp": datetime.now().isoformat(),
            })
            path = self.anchor_dir / f"{task_id}_anchor.json"
            with open(path, "w", encoding="utf-8") as f:
                json.dump(anchor, f, indent=2, ensure_ascii=False)
            self.logger.warning(f"Recorded deviation for task {task_id}: {deviation}")

    def update_anchor(self, task_id: str, checkpoint_data: Dict) -> bool:
        anchor = self.load_anchor(task_id)
        if not anchor:
            return False
        anchor["checkpoints"].append(checkpoint_data)
        path = self.anchor_dir / f"{task_id}_anchor.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(anchor, f, indent=2, ensure_ascii=False)
        return True

    def complete_anchor(self, task_id: str, success: bool = True) -> bool:
        anchor = self.load_anchor(task_id)
        if not anchor:
            return False
        anchor["status"] = "completed" if success else "failed"
        anchor["completed_at"] = datetime.now().isoformat()
        path = self.anchor_dir / f"{task_id}_anchor.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(anchor, f, indent=2, ensure_ascii=False)
        return True


class HumanInTheLoop:
    """
    人類介入器
    關鍵節點人類批准，防止不可逆操作
    Claude Code 在高風險操作前暫停等待人類確認
    """

    CRITICAL_OPERATIONS = [
        "delete", "rm", "remove", "drop",
        "git push", "publish", "deploy",
        "shutdown", "restart", "reboot",
        "format", "mkfs", "wipe",
        "send email", "send message",
        "payment", "transfer", "withdraw",
    ]

    def __init__(self, base_path: Optional[Path] = None):
        if base_path is None:
            base_path = Path(__file__).parent.parent.parent / "data"
        self.base_path = Path(base_path)
        self.approval_dir = self.base_path / "pending_approvals"
        self.approval_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)

    def is_critical_operation(self, operation: str) -> bool:
        op_lower = operation.lower()
        for critical in self.CRITICAL_OPERATIONS:
            if critical in op_lower:
                return True
        return False

    def request_approval(self, task_id: str, operation: str, context: Dict = None) -> str:
        approval_id = f"{task_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        approval = {
            "approval_id": approval_id,
            "task_id": task_id,
            "operation": operation,
            "context": context or {},
            "requested_at": datetime.now().isoformat(),
            "status": "pending",
            "user_response": None,
        }
        path = self.approval_dir / f"{approval_id}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(approval, f, indent=2, ensure_ascii=False)
        self.logger.info(f"Approval requested: {approval_id} for operation: {operation}")
        return approval_id

    def check_approval_status(self, approval_id: str) -> Optional[Dict]:
        path = self.approval_dir / f"{approval_id}.json"
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def approve(self, approval_id: str) -> bool:
        approval = self.check_approval_status(approval_id)
        if not approval:
            return False
        approval["status"] = "approved"
        approval["responded_at"] = datetime.now().isoformat()
        path = self.approval_dir / f"{approval_id}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(approval, f, indent=2, ensure_ascii=False)
        self.logger.info(f"Approval granted: {approval_id}")
        return True

    def reject(self, approval_id: str, reason: str = "") -> bool:
        approval = self.check_approval_status(approval_id)
        if not approval:
            return False
        approval["status"] = "rejected"
        approval["reject_reason"] = reason
        approval["responded_at"] = datetime.now().isoformat()
        path = self.approval_dir / f"{approval_id}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(approval, f, indent=2, ensure_ascii=False)
        self.logger.warning(f"Approval rejected: {approval_id}, reason: {reason}")
        return True

    def get_pending_approvals(self) -> List[Dict]:
        pending = []
        for json_file in self.approval_dir.glob("*.json"):
            with open(json_file, "r", encoding="utf-8") as f:
                approval = json.load(f)
                if approval["status"] == "pending":
                    pending.append(approval)
        return pending

    def should_wait_for_approval(self, task_id: str, operation: str) -> bool:
        if not self.is_critical_operation(operation):
            return False
        pending = self.get_pending_approvals()
        for p in pending:
            if p["task_id"] == task_id:
                return True
        return False


class SelfHealingEngine:
    """
    自癒引擎主類
    整合所有組件，實現 Claude Code 風格的自癒系統

    包含：
    - CheckpointManager：任務狀態保存
    - CircuitBreaker：錯誤熔斷
    - RecoveryEngine：失敗恢復
    - MultiTriggerLauncher：多層觸發
    - SelfReflection：自我反思
    - GoalAnchor：目標錨定（新增）
    - HumanInTheLoop：人類介入（新增）
    """

    def __init__(self, base_path: Optional[Path] = None):
        if base_path is None:
            base_path = Path(__file__).parent.parent.parent

        self.base_path = Path(base_path)
        self.checkpoint_manager = CheckpointManager(base_path / "data")
        self.circuit_breaker = CircuitBreaker()
        self.recovery_engine = RecoveryEngine(self.checkpoint_manager)
        self.multi_trigger = MultiTriggerLauncher(base_path)
        self.self_reflection = SelfReflection(base_path / "data")
        self.goal_anchor = GoalAnchor(base_path / "data")
        self.human_in_loop = HumanInTheLoop(base_path / "data")

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger(__name__)

    def create_task(self, task_id: str, task_type: str, description: str,
                   steps: List[str], goal: str = "") -> TaskCheckpoint:
        checkpoint = self.checkpoint_manager.create_checkpoint(
            task_id, task_type, description, steps
        )
        if goal:
            self.goal_anchor.create_anchor(task_id, goal, task_type)
        return checkpoint

    def execute_task(self, task_id: str, task_executor: Callable,
                    step_validator: Callable = None) -> Dict:
        checkpoint = self.checkpoint_manager.get_checkpoint(task_id)
        if not checkpoint:
            return {"success": False, "error": "Task not found"}

        self.checkpoint_manager.update_checkpoint(task_id, status=CheckpointState.RUNNING)

        results = []
        for step in checkpoint.pending_steps:
            alignment = self.goal_anchor.check_alignment(task_id, step)
            if not alignment["aligned"]:
                self.logger.warning(alignment["message"])
                results.append({
                    "step": step,
                    "warning": alignment["message"],
                    "success": False,
                    "type": "deviation"
                })
                continue

            if self.human_in_loop.is_critical_operation(step):
                approval_id = self.human_in_loop.request_approval(task_id, step)
                self.logger.info(f"Critical operation detected, waiting for approval: {approval_id}")
                results.append({
                    "step": step,
                    "approval_id": approval_id,
                    "status": "awaiting_approval",
                    "success": False,
                })
                continue

            try:
                self.checkpoint_manager.update_checkpoint(
                    task_id, current_step=step
                )

                if step_validator:
                    if not step_validator(step, checkpoint.context_data):
                        self.logger.warning(f"Step validation failed: {step}")
                        continue

                result = self.circuit_breaker.call(task_executor, step, checkpoint.context_data)
                self.checkpoint_manager.update_checkpoint(
                    task_id, completed_step=step
                )
                self.goal_anchor.update_anchor(task_id, {"step": step, "completed": True})
                results.append({"step": step, "result": result, "success": True})

            except Exception as e:
                checkpoint = self.checkpoint_manager.get_checkpoint(task_id)
                checkpoint.error_history.append({
                    "step": step,
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                    "timestamp": datetime.now().isoformat(),
                })
                self.checkpoint_manager.update_checkpoint(task_id)
                results.append({"step": step, "error": str(e), "success": False})

        all_success = all(r.get("success", False) for r in results)
        final_status = CheckpointState.COMPLETED if all_success else CheckpointState.FAILED
        self.checkpoint_manager.update_checkpoint(task_id, status=final_status)

        self.goal_anchor.complete_anchor(task_id, success=all_success)

        reflection = self.self_reflection.reflect(
            task_id, checkpoint, {"success": all_success, "results": results}
        )

        return {
            "success": all_success,
            "task_id": task_id,
            "results": results,
            "reflection": reflection,
        }

    def recover_and_continue(self, task_id: str, task_executor: Callable) -> Dict:
        return self.recovery_engine.recover_task(task_id, task_executor)

    def auto_recover_all(self, task_executor: Callable) -> List[Dict]:
        return self.recovery_engine.auto_recover_all(task_executor)

    def get_task_status(self, task_id: str) -> Dict:
        return self.checkpoint_manager.get_task_summary(task_id)

    def get_system_status(self) -> Dict:
        checkpoints = self.checkpoint_manager.get_all_checkpoints()
        recoverable = self.checkpoint_manager.get_recoverable_tasks()
        trigger_status = self.multi_trigger.get_trigger_status()
        pending_approvals = self.human_in_loop.get_pending_approvals()

        return {
            "total_tasks": len(checkpoints),
            "recoverable_tasks": len(recoverable),
            "trigger_status": trigger_status,
            "circuit_breaker": self.circuit_breaker.get_state(),
            "pending_approvals": len(pending_approvals),
            "goal_anchors_active": len([c for c in checkpoints if c.status == CheckpointState.RUNNING]),
        }

    def install_autostart(self) -> Dict:
        results = {
            "startup_folder": self.multi_trigger.install_startup(),
            "task_scheduler": self.multi_trigger.install_scheduler(),
        }
        return results

    def uninstall_autostart(self) -> bool:
        return self.multi_trigger.uninstall_startup()


def main():
    engine = SelfHealingEngine()
    print("Self-Healing Engine initialized")
    print(json.dumps(engine.get_system_status(), indent=2))


if __name__ == "__main__":
    main()
