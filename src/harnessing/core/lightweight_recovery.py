from __future__ import annotations

import hashlib
import json
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class RecoveryStatus(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
    SKIPPED = "skipped"


class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"


@dataclass
class CheckpointEntry:
    state_key: str
    state_value: Any
    timestamp: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SnapshotEntry:
    state_key: str
    value: Any
    version: int
    content_hash: str
    timestamp: float


@dataclass
class DiffEntry:
    state_key: str
    from_version: int
    to_version: int
    diff: Dict[str, Any]
    timestamp: float


@dataclass
class RecoveryAttempt:
    error_type: str
    strategy_name: str
    status: RecoveryStatus
    timestamp: float
    context: Dict[str, Any] = field(default_factory=dict)
    result_message: str = ""


@dataclass
class RecoveryResult:
    error_type: str
    status: RecoveryStatus
    strategy_used: str
    attempts: int
    recovery_time_seconds: float
    message: str
    context: Dict[str, Any] = field(default_factory=dict)


class QuickCheckpoint:
    def __init__(self) -> None:
        self._store: Dict[str, List[CheckpointEntry]] = defaultdict(list)

    def save_checkpoint(self, state_key: str, state_value: Any) -> CheckpointEntry:
        entry = CheckpointEntry(
            state_key=state_key,
            state_value=state_value,
            timestamp=time.time(),
        )
        self._store[state_key].append(entry)
        logger.info(f"checkpoint_saved key={state_key} entries={len(self._store[state_key])}")
        return entry

    def load_checkpoint(self, state_key: str) -> Optional[Any]:
        entries = self._store.get(state_key)
        if not entries:
            logger.warning(f"checkpoint_not_found key={state_key}")
            return None
        latest = entries[-1]
        logger.info(f"checkpoint_loaded key={state_key} age_seconds={time.time() - latest.timestamp:.2f}")
        return latest.state_value

    def list_checkpoints(self) -> Dict[str, int]:
        return {key: len(entries) for key, entries in self._store.items()}

    def clear_old_checkpoints(self, max_age_seconds: float = 3600) -> int:
        cutoff = time.time() - max_age_seconds
        removed = 0
        for key in list(self._store.keys()):
            original_len = len(self._store[key])
            self._store[key] = [e for e in self._store[key] if e.timestamp >= cutoff]
            removed += original_len - len(self._store[key])
            if not self._store[key]:
                del self._store[key]
        logger.info(f"old_checkpoints_cleared removed={removed} max_age={max_age_seconds}")
        return removed


class FastRollback:
    def __init__(self) -> None:
        self._snapshots: Dict[str, List[SnapshotEntry]] = defaultdict(list)
        self._diffs: List[DiffEntry] = []
        self._version_counter: Dict[str, int] = defaultdict(int)

    def create_snapshot(self, state_key: str, value: Any) -> SnapshotEntry:
        self._version_counter[state_key] += 1
        version = self._version_counter[state_key]
        content_hash = self._compute_hash(value)
        entry = SnapshotEntry(
            state_key=state_key,
            value=value,
            version=version,
            content_hash=content_hash,
            timestamp=time.time(),
        )
        snapshots = self._snapshots[state_key]
        if snapshots:
            diff = self.compute_diff(snapshots[-1].value, value)
            self._diffs.append(DiffEntry(
                state_key=state_key,
                from_version=snapshots[-1].version,
                to_version=version,
                diff=diff,
                timestamp=time.time(),
            ))
        snapshots.append(entry)
        logger.info(f"snapshot_created key={state_key} version={version} hash={content_hash[:8]}")
        return entry

    def compute_diff(self, old_value: Any, new_value: Any) -> Dict[str, Any]:
        try:
            old_str = json.dumps(old_value, sort_keys=True, default=str)
            new_str = json.dumps(new_value, sort_keys=True, default=str)
        except (TypeError, ValueError):
            return {"changed": True, "type": "non_serializable"}
        if old_str == new_str:
            return {"changed": False}
        old_hash = hashlib.md5(old_str.encode()).hexdigest()
        new_hash = hashlib.md5(new_str.encode()).hexdigest()
        return {
            "changed": True,
            "old_hash": old_hash,
            "new_hash": new_hash,
            "old_size": len(old_str),
            "new_size": len(new_str),
        }

    def rollback_to(self, state_key: str, target_version: int) -> Optional[Any]:
        snapshots = self._snapshots.get(state_key, [])
        for snap in snapshots:
            if snap.version == target_version:
                logger.info(f"rollback_executed key={state_key} target_version={target_version}")
                return snap.value
        logger.warning(f"rollback_version_not_found key={state_key} target={target_version}")
        return None

    def get_snapshot_history(self, state_key: str) -> List[Dict[str, Any]]:
        snapshots = self._snapshots.get(state_key, [])
        return [
            {
                "version": s.version,
                "content_hash": s.content_hash,
                "timestamp": s.timestamp,
                "datetime": datetime.fromtimestamp(s.timestamp).isoformat(),
            }
            for s in snapshots
        ]

    def _compute_hash(self, value: Any) -> str:
        try:
            serialized = json.dumps(value, sort_keys=True, default=str)
        except (TypeError, ValueError):
            serialized = str(value)
        return hashlib.md5(serialized.encode()).hexdigest()


class AutoRecovery:
    def __init__(self, checkpoint: QuickCheckpoint, rollback: FastRollback) -> None:
        self._checkpoint = checkpoint
        self._rollback = rollback
        self._strategies: Dict[str, Callable[..., RecoveryStatus]] = {}
        self._history: List[RecoveryAttempt] = []
        self._register_builtin_strategies()

    def _register_builtin_strategies(self) -> None:
        self._strategies["retry"] = self._strategy_retry
        self._strategies["rollback"] = self._strategy_rollback
        self._strategies["reset_to_default"] = self._strategy_reset_to_default

    def register_recovery_strategy(self, error_type: str, strategy_fn: Callable[..., RecoveryStatus]) -> None:
        self._strategies[error_type] = strategy_fn
        logger.info(f"recovery_strategy_registered error_type={error_type}")

    def attempt_recovery(self, error_type: str, context: Optional[Dict[str, Any]] = None) -> RecoveryAttempt:
        ctx = context or {}
        strategy_fn = self._strategies.get(error_type)
        if not strategy_fn:
            attempt = RecoveryAttempt(
                error_type=error_type,
                strategy_name="none",
                status=RecoveryStatus.SKIPPED,
                timestamp=time.time(),
                context=ctx,
                result_message=f"No strategy registered for error_type: {error_type}",
            )
            self._history.append(attempt)
            logger.warning(f"no_recovery_strategy error_type={error_type}")
            return attempt
        try:
            status = strategy_fn(ctx)
            attempt = RecoveryAttempt(
                error_type=error_type,
                strategy_name=error_type,
                status=status,
                timestamp=time.time(),
                context=ctx,
                result_message=f"Strategy {error_type} returned {status.value}",
            )
        except Exception as exc:
            attempt = RecoveryAttempt(
                error_type=error_type,
                strategy_name=error_type,
                status=RecoveryStatus.FAILED,
                timestamp=time.time(),
                context=ctx,
                result_message=f"Strategy failed: {exc}",
            )
            logger.error(f"recovery_strategy_failed error_type={error_type} error={exc}")
        self._history.append(attempt)
        return attempt

    def get_recovery_history(self) -> List[Dict[str, Any]]:
        return [
            {
                "error_type": a.error_type,
                "strategy_name": a.strategy_name,
                "status": a.status.value,
                "timestamp": a.timestamp,
                "datetime": datetime.fromtimestamp(a.timestamp).isoformat(),
                "result_message": a.result_message,
            }
            for a in self._history
        ]

    def _strategy_retry(self, context: Dict[str, Any]) -> RecoveryStatus:
        max_retries = context.get("max_retries", 3)
        action = context.get("action")
        if not action or not callable(action):
            return RecoveryStatus.SKIPPED
        for attempt_num in range(max_retries):
            try:
                action()
                logger.info(f"retry_succeeded attempt={attempt_num + 1}")
                return RecoveryStatus.SUCCESS
            except Exception as exc:
                logger.warning(f"retry_failed attempt={attempt_num + 1} error={exc}")
                if attempt_num == max_retries - 1:
                    return RecoveryStatus.FAILED
        return RecoveryStatus.FAILED

    def _strategy_rollback(self, context: Dict[str, Any]) -> RecoveryStatus:
        state_key = context.get("state_key")
        target_version = context.get("target_version")
        if not state_key:
            return RecoveryStatus.SKIPPED
        if target_version is not None:
            result = self._rollback.rollback_to(state_key, target_version)
        else:
            history = self._rollback.get_snapshot_history(state_key)
            if len(history) < 2:
                return RecoveryStatus.SKIPPED
            target_version = history[-2]["version"]
            result = self._rollback.rollback_to(state_key, target_version)
        return RecoveryStatus.SUCCESS if result is not None else RecoveryStatus.FAILED

    def _strategy_reset_to_default(self, context: Dict[str, Any]) -> RecoveryStatus:
        state_key = context.get("state_key")
        default_value = context.get("default_value")
        if state_key is None or default_value is None:
            return RecoveryStatus.SKIPPED
        self._checkpoint.save_checkpoint(state_key, default_value)
        return RecoveryStatus.SUCCESS


class LightweightRecovery:
    def __init__(self) -> None:
        self.checkpoint = QuickCheckpoint()
        self.rollback = FastRollback()
        self.recovery = AutoRecovery(self.checkpoint, self.rollback)
        self._failure_counts: Dict[str, int] = defaultdict(int)
        self._start_time = time.time()

    def handle_failure(
        self,
        error_type: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> RecoveryResult:
        start = time.time()
        ctx = context or {}
        self._failure_counts[error_type] += 1
        attempt = self.recovery.attempt_recovery(error_type, ctx)
        elapsed = time.time() - start
        result = RecoveryResult(
            error_type=error_type,
            status=attempt.status,
            strategy_used=attempt.strategy_name,
            attempts=self._failure_counts[error_type],
            recovery_time_seconds=round(elapsed, 4),
            message=attempt.result_message,
            context=ctx,
        )
        logger.info(
            f"failure_handled error_type={error_type} status={attempt.status.value} "
            f"strategy={attempt.strategy_name} elapsed={elapsed:.4f}"
        )
        return result

    def get_recovery_status(self) -> Dict[str, Any]:
        checkpoints = self.checkpoint.list_checkpoints()
        total_snapshots = sum(len(v) for v in self.rollback._snapshots.values())
        recovery_history = self.recovery.get_recovery_history()
        success_count = sum(1 for h in recovery_history if h["status"] == "success")
        failed_count = sum(1 for h in recovery_history if h["status"] == "failed")
        return {
            "uptime_seconds": round(time.time() - self._start_time, 2),
            "checkpoints": checkpoints,
            "total_snapshots": total_snapshots,
            "total_recovery_attempts": len(recovery_history),
            "successful_recoveries": success_count,
            "failed_recoveries": failed_count,
            "failure_counts_by_type": dict(self._failure_counts),
            "registered_strategies": list(self.recovery._strategies.keys()),
        }

    def perform_health_check(self) -> Dict[str, Any]:
        status = HealthStatus.HEALTHY
        issues: List[str] = []
        recovery_history = self.recovery.get_recovery_history()
        if recovery_history:
            recent = [h for h in recovery_history if time.time() - h["timestamp"] < 300]
            recent_failures = sum(1 for h in recent if h["status"] == "failed")
            if recent_failures >= 5:
                status = HealthStatus.CRITICAL
                issues.append(f"{recent_failures} recent recovery failures in last 5 minutes")
            elif recent_failures >= 2:
                status = HealthStatus.DEGRADED
                issues.append(f"{recent_failures} recent recovery failures in last 5 minutes")
        for error_type, count in self._failure_counts.items():
            if count >= 10:
                issues.append(f"High failure count for {error_type}: {count}")
                if status == HealthStatus.HEALTHY:
                    status = HealthStatus.DEGRADED
        return {
            "status": status.value,
            "issues": issues,
            "timestamp": datetime.now().isoformat(),
            "recovery_summary": self.get_recovery_status(),
        }


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(name)s | %(levelname)s | %(message)s")

    print("=" * 60)
    print("LightweightRecovery System Demo")
    print("=" * 60)

    lr = LightweightRecovery()

    print("\n--- QuickCheckpoint Demo ---")
    lr.checkpoint.save_checkpoint("task_progress", {"step": 1, "status": "running"})
    lr.checkpoint.save_checkpoint("task_progress", {"step": 2, "status": "running"})
    lr.checkpoint.save_checkpoint("config", {"model": "qwen3:8b", "temperature": 0.7})

    loaded = lr.checkpoint.load_checkpoint("task_progress")
    print(f"  Loaded task_progress: {loaded}")

    loaded_config = lr.checkpoint.load_checkpoint("config")
    print(f"  Loaded config: {loaded_config}")

    print(f"  All checkpoints: {lr.checkpoint.list_checkpoints()}")

    import time as _time
    old_key = "_old_test"
    lr.checkpoint.save_checkpoint(old_key, "old_data")
    lr.checkpoint._store[old_key][0].timestamp = _time.time() - 7200
    removed = lr.checkpoint.clear_old_checkpoints(max_age_seconds=3600)
    print(f"  Cleared {removed} old checkpoint(s)")

    print("\n--- FastRollback Demo ---")
    lr.rollback.create_snapshot("model_config", {"model": "qwen3:8b"})
    lr.rollback.create_snapshot("model_config", {"model": "qwen3:8b", "temperature": 0.7})
    lr.rollback.create_snapshot("model_config", {"model": "glm-5.1", "temperature": 0.7})

    diff = lr.rollback.compute_diff(
        {"model": "qwen3:8b"},
        {"model": "glm-5.1"},
    )
    print(f"  Diff: {diff}")

    history = lr.rollback.get_snapshot_history("model_config")
    print(f"  Snapshot history: {history}")

    rolled_back = lr.rollback.rollback_to("model_config", 1)
    print(f"  Rolled back to v1: {rolled_back}")

    print("\n--- AutoRecovery Demo ---")
    call_count = {"n": 0}

    def flaky_action():
        call_count["n"] += 1
        if call_count["n"] < 3:
            raise RuntimeError(f"Flaky failure #{call_count['n']}")
        return "ok"

    result = lr.handle_failure("retry", {"action": flaky_action, "max_retries": 3})
    print(f"  Retry result: status={result.status.value}, strategy={result.strategy_used}")

    lr.rollback.create_snapshot("pipeline_state", {"stage": "research", "data": "initial"})
    lr.rollback.create_snapshot("pipeline_state", {"stage": "script", "data": "corrupted"})

    result = lr.handle_failure("rollback", {"state_key": "pipeline_state", "target_version": 1})
    print(f"  Rollback result: status={result.status.value}")

    result = lr.handle_failure(
        "reset_to_default",
        {"state_key": "model_config", "default_value": {"model": "qwen3:8b", "temperature": 0.5}},
    )
    print(f"  Reset result: status={result.status.value}")

    print("\n--- Custom Strategy Demo ---")
    def custom_network_recovery(ctx: Dict[str, Any]) -> RecoveryStatus:
        endpoint = ctx.get("endpoint", "unknown")
        print(f"    Custom recovery: reconnecting to {endpoint}")
        return RecoveryStatus.SUCCESS

    lr.recovery.register_recovery_strategy("network_error", custom_network_recovery)
    result = lr.handle_failure("network_error", {"endpoint": "api.example.com"})
    print(f"  Custom strategy result: status={result.status.value}")

    print("\n--- Unknown Error Type Demo ---")
    result = lr.handle_failure("unknown_error_type")
    print(f"  Unknown type result: status={result.status.value}, message={result.message}")

    print("\n--- Recovery Status ---")
    status = lr.get_recovery_status()
    for k, v in status.items():
        print(f"  {k}: {v}")

    print("\n--- Health Check ---")
    health = lr.perform_health_check()
    print(f"  Status: {health['status']}")
    print(f"  Issues: {health['issues']}")

    print("\n" + "=" * 60)
    print("LightweightRecovery Demo Complete")
    print("=" * 60)


if __name__ == "__main__":
    main()
