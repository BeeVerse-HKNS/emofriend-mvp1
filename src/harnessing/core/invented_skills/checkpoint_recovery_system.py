"""
INV-004 CheckpointRecoverySystem
Formula: M * S + P - A
Explanation: Memory 與 SelfHealing 協同 + Prediction 減去 Automation = 檢查點恢復系統
Target Painpoints: WAA-006, WAA-023, CAA-008, CAA-029
"""

import json
import os
import pickle
import shutil
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union


class CheckpointStatus(Enum):
    CREATED = "created"
    VALID = "valid"
    INVALID = "invalid"
    RESTORED = "restored"
    FAILED = "failed"


class RecoveryStrategy(Enum):
    LATEST = "latest"
    OLDEST = "oldest"
    BEST_SCORE = "best_score"
    BEFORE_FAILURE = "before_failure"


@dataclass
class Checkpoint:
    id: str
    timestamp: float
    step: int
    state: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    score: float = 0.0
    size_bytes: int = 0
    checksum: str = ""


@dataclass
class RecoveryResult:
    success: bool
    checkpoint_id: Optional[str]
    restored_state: Optional[Dict[str, Any]]
    message: str
    rollback_performed: bool = False
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class CheckpointManager:
    def __init__(
        self,
        checkpoint_dir: Path,
        max_checkpoints: int = 10,
        auto_cleanup: bool = True
    ):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.max_checkpoints = max_checkpoints
        self.auto_cleanup = auto_cleanup
        self._checkpoints: Dict[str, Checkpoint] = {}
        
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self._load_existing_checkpoints()

    def _load_existing_checkpoints(self) -> None:
        for cp_file in self.checkpoint_dir.glob("checkpoint_*.json"):
            try:
                with open(cp_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                checkpoint = Checkpoint(**data)
                self._checkpoints[checkpoint.id] = checkpoint
            except Exception:
                pass

    def _compute_checksum(self, state: Dict[str, Any]) -> str:
        state_str = json.dumps(state, sort_keys=True, default=str)
        import hashlib
        return hashlib.md5(state_str.encode()).hexdigest()[:16]

    def create(self, step: int, state: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> Checkpoint:
        checkpoint_id = f"cp_{int(time.time() * 1000)}"
        checksum = self._compute_checksum(state)
        
        checkpoint = Checkpoint(
            id=checkpoint_id,
            timestamp=time.time(),
            step=step,
            state=state,
            metadata=metadata or {},
            score=metadata.get('score', 0.0) if metadata else 0.0,
            checksum=checksum
        )
        
        self._checkpoints[checkpoint_id] = checkpoint
        self._save_checkpoint(checkpoint)
        
        if self.auto_cleanup:
            self._cleanup_old_checkpoints()
        
        return checkpoint

    def _save_checkpoint(self, checkpoint: Checkpoint) -> None:
        cp_file = self.checkpoint_dir / f"checkpoint_{checkpoint.id}.json"
        state_file = self.checkpoint_dir / f"state_{checkpoint.id}.pkl"
        
        with open(state_file, 'wb') as f:
            pickle.dump(checkpoint.state, f)
        
        checkpoint.size_bytes = os.path.getsize(state_file)
        
        cp_data = {
            'id': checkpoint.id,
            'timestamp': checkpoint.timestamp,
            'step': checkpoint.step,
            'state': {},
            'metadata': checkpoint.metadata,
            'score': checkpoint.score,
            'size_bytes': checkpoint.size_bytes,
            'checksum': checkpoint.checksum
        }
        
        with open(cp_file, 'w', encoding='utf-8') as f:
            json.dump(cp_data, f, indent=2)

    def _cleanup_old_checkpoints(self) -> None:
        if len(self._checkpoints) <= self.max_checkpoints:
            return
        
        sorted_cps = sorted(self._checkpoints.values(), key=lambda x: x.timestamp, reverse=True)
        to_remove = sorted_cps[self.max_checkpoints:]
        
        for cp in to_remove:
            self.delete(cp.id)

    def get(self, checkpoint_id: str) -> Optional[Checkpoint]:
        checkpoint = self._checkpoints.get(checkpoint_id)
        if checkpoint:
            state_file = self.checkpoint_dir / f"state_{checkpoint_id}.pkl"
            if state_file.exists():
                with open(state_file, 'rb') as f:
                    checkpoint.state = pickle.load(f)
        return checkpoint

    def get_all(self) -> List[Checkpoint]:
        return sorted(self._checkpoints.values(), key=lambda x: x.timestamp, reverse=True)

    def delete(self, checkpoint_id: str) -> bool:
        if checkpoint_id not in self._checkpoints:
            return False
        
        cp_file = self.checkpoint_dir / f"checkpoint_{checkpoint_id}.json"
        state_file = self.checkpoint_dir / f"state_{checkpoint_id}.pkl"
        
        cp_file.unlink(missing_ok=True)
        state_file.unlink(missing_ok=True)
        del self._checkpoints[checkpoint_id]
        
        return True


class StateSerializer:
    SERIALIZERS = {
        'json': lambda x: json.dumps(x, default=str).encode(),
        'pickle': lambda x: pickle.dumps(x)
    }
    
    DESERIALIZERS = {
        'json': lambda x: json.loads(x.decode()),
        'pickle': lambda x: pickle.loads(x)
    }

    def __init__(self, default_format: str = 'pickle'):
        self.default_format = default_format

    def serialize(self, state: Dict[str, Any], format: Optional[str] = None) -> bytes:
        fmt = format or self.default_format
        return self.SERIALIZERS[fmt](state)

    def deserialize(self, data: bytes, format: Optional[str] = None) -> Dict[str, Any]:
        fmt = format or self.default_format
        return self.DESERIALIZERS[fmt](data)

    def to_file(self, state: Dict[str, Any], path: Path, format: Optional[str] = None) -> None:
        data = self.serialize(state, format)
        with open(path, 'wb') as f:
            f.write(data)

    def from_file(self, path: Path, format: Optional[str] = None) -> Dict[str, Any]:
        with open(path, 'rb') as f:
            data = f.read()
        return self.deserialize(data, format)


class RecoveryExecutor:
    def __init__(self, checkpoint_manager: CheckpointManager):
        self.checkpoint_manager = checkpoint_manager
        self._recovery_history: List[RecoveryResult] = []

    def recover(
        self,
        strategy: RecoveryStrategy = RecoveryStrategy.LATEST,
        target_step: Optional[int] = None
    ) -> RecoveryResult:
        checkpoints = self.checkpoint_manager.get_all()
        
        if not checkpoints:
            return RecoveryResult(
                success=False,
                checkpoint_id=None,
                restored_state=None,
                message="沒有可用的檢查點"
            )
        
        target_checkpoint = self._select_checkpoint(checkpoints, strategy, target_step)
        
        if not target_checkpoint:
            return RecoveryResult(
                success=False,
                checkpoint_id=None,
                restored_state=None,
                message="無法選擇合適的檢查點"
            )
        
        checkpoint = self.checkpoint_manager.get(target_checkpoint.id)
        
        if not checkpoint or not checkpoint.state:
            return RecoveryResult(
                success=False,
                checkpoint_id=target_checkpoint.id,
                restored_state=None,
                message="檢查點狀態無效"
            )
        
        result = RecoveryResult(
            success=True,
            checkpoint_id=checkpoint.id,
            restored_state=checkpoint.state,
            message=f"成功從檢查點 {checkpoint.id} 恢復 (步驟 {checkpoint.step})"
        )
        
        self._recovery_history.append(result)
        return result

    def _select_checkpoint(
        self,
        checkpoints: List[Checkpoint],
        strategy: RecoveryStrategy,
        target_step: Optional[int]
    ) -> Optional[Checkpoint]:
        if target_step is not None:
            for cp in checkpoints:
                if cp.step <= target_step:
                    return cp
            return None
        
        if strategy == RecoveryStrategy.LATEST:
            return checkpoints[0] if checkpoints else None
        elif strategy == RecoveryStrategy.OLDEST:
            return checkpoints[-1] if checkpoints else None
        elif strategy == RecoveryStrategy.BEST_SCORE:
            return max(checkpoints, key=lambda x: x.score)
        elif strategy == RecoveryStrategy.BEFORE_FAILURE:
            return checkpoints[0] if len(checkpoints) > 0 else None
        
        return checkpoints[0] if checkpoints else None

    def get_recovery_history(self) -> List[RecoveryResult]:
        return self._recovery_history.copy()


class RollbackHandler:
    def __init__(self, checkpoint_manager: CheckpointManager):
        self.checkpoint_manager = checkpoint_manager
        self._rollback_history: List[Dict[str, Any]] = []

    def rollback(self, from_checkpoint_id: str, to_checkpoint_id: str) -> RecoveryResult:
        from_cp = self.checkpoint_manager.get(from_checkpoint_id)
        to_cp = self.checkpoint_manager.get(to_checkpoint_id)
        
        if not from_cp or not to_cp:
            return RecoveryResult(
                success=False,
                checkpoint_id=None,
                restored_state=None,
                message="檢查點不存在",
                rollback_performed=False
            )
        
        if to_cp.timestamp >= from_cp.timestamp:
            return RecoveryResult(
                success=False,
                checkpoint_id=to_checkpoint_id,
                restored_state=None,
                message="目標檢查點必須早於當前檢查點",
                rollback_performed=False
            )
        
        rollback_record = {
            'from': from_checkpoint_id,
            'to': to_checkpoint_id,
            'timestamp': datetime.now().isoformat()
        }
        self._rollback_history.append(rollback_record)
        
        return RecoveryResult(
            success=True,
            checkpoint_id=to_checkpoint_id,
            restored_state=to_cp.state,
            message=f"成功從 {from_checkpoint_id} 回滾到 {to_checkpoint_id}",
            rollback_performed=True
        )

    def rollback_to_step(self, step: int) -> RecoveryResult:
        checkpoints = self.checkpoint_manager.get_all()
        
        for cp in checkpoints:
            if cp.step == step:
                return RecoveryResult(
                    success=True,
                    checkpoint_id=cp.id,
                    restored_state=cp.state,
                    message=f"成功回滾到步驟 {step}",
                    rollback_performed=True
                )
        
        return RecoveryResult(
            success=False,
            checkpoint_id=None,
            restored_state=None,
            message=f"找不到步驟 {step} 的檢查點",
            rollback_performed=False
        )

    def get_rollback_history(self) -> List[Dict[str, Any]]:
        return self._rollback_history.copy()


class CheckpointRecoverySystem:
    """
    INV-004: CheckpointRecoverySystem
    Formula: M * S + P - A
    
    自動檢查點保存與故障後恢復
    """

    def __init__(
        self,
        checkpoint_dir: Path,
        max_checkpoints: int = 10,
        auto_save_interval: int = 100
    ):
        self.checkpoint_manager = CheckpointManager(
            checkpoint_dir=checkpoint_dir,
            max_checkpoints=max_checkpoints
        )
        self.serializer = StateSerializer()
        self.recovery_executor = RecoveryExecutor(self.checkpoint_manager)
        self.rollback_handler = RollbackHandler(self.checkpoint_manager)
        
        self.auto_save_interval = auto_save_interval
        self._current_step: int = 0
        self._current_state: Dict[str, Any] = {}
        self._last_checkpoint_id: Optional[str] = None

    def save_checkpoint(self, state: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> Checkpoint:
        self._current_state = state
        self._current_step += 1
        
        checkpoint = self.checkpoint_manager.create(
            step=self._current_step,
            state=state,
            metadata=metadata
        )
        self._last_checkpoint_id = checkpoint.id
        
        return checkpoint

    def auto_save(self, state: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> Optional[Checkpoint]:
        self._current_step += 1
        self._current_state = state
        
        if self._current_step % self.auto_save_interval == 0:
            return self.save_checkpoint(state, metadata)
        return None

    def recover(
        self,
        strategy: RecoveryStrategy = RecoveryStrategy.LATEST,
        target_step: Optional[int] = None
    ) -> RecoveryResult:
        result = self.recovery_executor.recover(strategy, target_step)
        
        if result.success and result.restored_state:
            self._current_state = result.restored_state
            self._current_step = result.checkpoint_id.split('_')[-1] if result.checkpoint_id else 0
        
        return result

    def rollback(self, to_checkpoint_id: Optional[str] = None, to_step: Optional[int] = None) -> RecoveryResult:
        if to_step is not None:
            return self.rollback_handler.rollback_to_step(to_step)
        
        if to_checkpoint_id and self._last_checkpoint_id:
            return self.rollback_handler.rollback(self._last_checkpoint_id, to_checkpoint_id)
        
        return RecoveryResult(
            success=False,
            checkpoint_id=None,
            restored_state=None,
            message="需要指定回滾目標"
        )

    def get_current_state(self) -> Dict[str, Any]:
        return self._current_state.copy()

    def get_checkpoints(self) -> List[Checkpoint]:
        return self.checkpoint_manager.get_all()

    def get_statistics(self) -> Dict[str, Any]:
        checkpoints = self.checkpoint_manager.get_all()
        total_size = sum(cp.size_bytes for cp in checkpoints)
        
        return {
            'current_step': self._current_step,
            'total_checkpoints': len(checkpoints),
            'total_size_bytes': total_size,
            'total_size_mb': total_size / (1024 * 1024),
            'last_checkpoint_id': self._last_checkpoint_id,
            'recovery_count': len(self.recovery_executor.get_recovery_history()),
            'rollback_count': len(self.rollback_handler.get_rollback_history())
        }

    def cleanup(self) -> int:
        checkpoints = self.checkpoint_manager.get_all()
        removed = 0
        
        for cp in checkpoints[self.checkpoint_manager.max_checkpoints:]:
            if self.checkpoint_manager.delete(cp.id):
                removed += 1
        
        return removed


if __name__ == "__main__":
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmpdir:
        system = CheckpointRecoverySystem(
            checkpoint_dir=Path(tmpdir),
            max_checkpoints=5,
            auto_save_interval=3
        )
        
        print("=== Test 1: Save Checkpoints ===")
        for i in range(5):
            state = {'data': list(range(i * 10, (i + 1) * 10)), 'step': i}
            cp = system.save_checkpoint(state, metadata={'score': i * 0.1})
            print(f"  Created checkpoint: {cp.id} at step {cp.step}")
        
        print("\n=== Test 2: List Checkpoints ===")
        for cp in system.get_checkpoints():
            print(f"  {cp.id}: step={cp.step}, score={cp.score}, size={cp.size_bytes} bytes")
        
        print("\n=== Test 3: Recovery ===")
        result = system.recover(strategy=RecoveryStrategy.LATEST)
        print(f"  Success: {result.success}")
        print(f"  Message: {result.message}")
        if result.restored_state:
            print(f"  Restored data: {result.restored_state.get('data', [])}")
        
        print("\n=== Test 4: Rollback ===")
        checkpoints = system.get_checkpoints()
        if len(checkpoints) >= 2:
            rollback_result = system.rollback(to_step=2)
            print(f"  Rollback success: {rollback_result.success}")
            print(f"  Message: {rollback_result.message}")
        
        print("\n=== Statistics ===")
        stats = system.get_statistics()
        print(json.dumps(stats, indent=2))
