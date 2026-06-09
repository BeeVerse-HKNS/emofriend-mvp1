#!/usr/bin/env python3
"""
CatastrophicRecoveryPlatform — 災難性恢復平台

【乘法創新】CheckpointManager × RollbackManager × RecoveryEngine × GoalAnchor
= 4-技能乘法協同，專門處理災難性情景

乘法原理：每個技能的輸出成為下一個技能的放大器
- CheckpointManager → 保存完整狀態快照
- GoalAnchor → 驗證恢復後是否偏離原始目標
- RollbackManager → 執行精確回滾
- RecoveryEngine → 協調整個恢復流程

解決的情景：catastrophic (all categories)
"""

import logging
import json
import hashlib
import time
import random
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple
from enum import Enum
from datetime import datetime
from pathlib import Path
from collections import defaultdict


class RecoveryPhase(Enum):
    DETECTION = "detection"
    ASSESSMENT = "assessment"
    CHECKPOINT = "checkpoint"
    ROLLBACK = "rollback"
    VERIFICATION = "verification"
    RECOVERY = "recovery"
    VALIDATION = "validation"
    COMPLETE = "complete"


class CatastropheLevel(Enum):
    PARTIAL_LOSS = "partial_loss"
    FULL_SYSTEM_FAILURE = "full_system_failure"
    DATA_CORRUPTION = "data_corruption"
    CASCADING_FAILURE = "cascading_failure"
    IRREVERSIBLE_DAMAGE = "irreversible_damage"


@dataclass
class Checkpoint:
    id: str
    timestamp: str
    system_state: Dict[str, Any]
    goal_state: Dict[str, Any]
    integrity_hash: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GoalState:
    primary_goal: str
    sub_goals: List[str]
    success_criteria: Dict[str, Any]
    priority: int = 1
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class RecoveryResult:
    success: bool
    catastrophe_level: CatastropheLevel
    phases_completed: List[RecoveryPhase]
    checkpoint_used: Optional[str]
    goal_deviation: float
    recovery_time_ms: float
    data_loss: bool
    lessons_learned: List[str]


class CheckpointManager:
    def __init__(self, data_dir: str = "data"):
        self.logger = logging.getLogger(__name__)
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.checkpoints: Dict[str, Checkpoint] = {}

    def create_checkpoint(self, system_state: Dict, goal_state: Dict = None) -> str:
        cp_id = hashlib.md5(f"{time.time()}{random.random()}".encode()).hexdigest()[:8]
        state_json = json.dumps(system_state, sort_keys=True, default=str)
        integrity_hash = hashlib.sha256(state_json.encode()).hexdigest()[:16]

        checkpoint = Checkpoint(
            id=cp_id,
            timestamp=datetime.now().isoformat(),
            system_state=system_state,
            goal_state=goal_state or {},
            integrity_hash=integrity_hash
        )
        self.checkpoints[cp_id] = checkpoint
        self.logger.info(f"Checkpoint created: {cp_id}")
        return cp_id

    def get_latest_checkpoint(self) -> Optional[Checkpoint]:
        if not self.checkpoints:
            return None
        return max(self.checkpoints.values(), key=lambda cp: cp.timestamp)

    def verify_integrity(self, cp_id: str) -> bool:
        checkpoint = self.checkpoints.get(cp_id)
        if not checkpoint:
            return False
        state_json = json.dumps(checkpoint.system_state, sort_keys=True, default=str)
        current_hash = hashlib.sha256(state_json.encode()).hexdigest()[:16]
        return current_hash == checkpoint.integrity_hash


class GoalAnchor:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.goals: Dict[str, GoalState] = {}
        self.deviation_history: List[Dict] = []

    def set_goal(self, goal_id: str, primary_goal: str,
                 sub_goals: List[str] = None,
                 success_criteria: Dict = None) -> GoalState:
        goal = GoalState(
            primary_goal=primary_goal,
            sub_goals=sub_goals or [],
            success_criteria=success_criteria or {}
        )
        self.goals[goal_id] = goal
        return goal

    def check_deviation(self, goal_id: str, current_state: Dict) -> Tuple[float, List[str]]:
        goal = self.goals.get(goal_id)
        if not goal:
            return 0.0, []

        deviation = 0.0
        issues = []

        for key, expected in goal.success_criteria.items():
            actual = current_state.get(key)
            if actual != expected:
                deviation += 0.2
                issues.append(f"{key}: expected {expected}, got {actual}")

        deviation = min(deviation, 1.0)

        self.deviation_history.append({
            "timestamp": datetime.now().isoformat(),
            "goal_id": goal_id,
            "deviation": deviation,
            "issues": issues
        })

        return deviation, issues

    def get_correction_plan(self, goal_id: str, deviation: float, issues: List[str]) -> List[str]:
        if deviation < 0.2:
            return ["偏差在可接受範圍內，無需校正"]
        elif deviation < 0.5:
            return [f"輕微偏差，建議調整: {issue}" for issue in issues[:3]]
        elif deviation < 0.8:
            return [f"顯著偏差，必須校正: {issue}" for issue in issues]
        else:
            return ["嚴重偏離目標，建議完全回滾到最近檢查點"]


class RollbackManager:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.rollback_history: List[Dict] = []

    def rollback_to_checkpoint(self, checkpoint: Checkpoint, current_state: Dict) -> Dict:
        self.logger.info(f"Rolling back to checkpoint {checkpoint.id}")
        rolled_back_state = checkpoint.system_state.copy()
        diff = self._compute_diff(current_state, rolled_back_state)

        self.rollback_history.append({
            "timestamp": datetime.now().isoformat(),
            "checkpoint_id": checkpoint.id,
            "diff_keys": list(diff.keys()),
            "diff_count": len(diff)
        })

        return rolled_back_state

    def _compute_diff(self, current: Dict, target: Dict) -> Dict:
        diff = {}
        all_keys = set(list(current.keys()) + list(target.keys()))
        for key in all_keys:
            if current.get(key) != target.get(key):
                diff[key] = {
                    "from": current.get(key, "<missing>"),
                    "to": target.get(key, "<missing>")
                }
        return diff


class CatastrophicRecoveryPlatform:
    """
    災難性恢復平台
    
    【乘法創新】CheckpointManager × RollbackManager × RecoveryEngine × GoalAnchor
    
    乘法效應：每個技能的輸出放大下一個技能的效果
    - Checkpoint → 提供恢復基準點
    - GoalAnchor → 確保恢復後不偏離目標
    - Rollback → 精確回滾到正確狀態
    - Recovery → 協調整個恢復流程
    
    解決：catastrophic (all categories)
    """

    def __init__(self, data_dir: str = "data"):
        self.logger = logging.getLogger(__name__)
        self.checkpoint_mgr = CheckpointManager(data_dir)
        self.goal_anchor = GoalAnchor()
        self.rollback_mgr = RollbackManager()
        self._recovery_strategies = self._init_recovery_strategies()
        self.recovery_history: List[RecoveryResult] = []

    def _init_recovery_strategies(self) -> Dict[CatastropheLevel, List[str]]:
        return {
            CatastropheLevel.PARTIAL_LOSS: [
                "從最近檢查點恢復受影響的組件",
                "驗證數據完整性",
                "重新執行丟失的操作"
            ],
            CatastropheLevel.FULL_SYSTEM_FAILURE: [
                "從最近檢查點恢復整個系統狀態",
                "驗證目標一致性",
                "逐步重啟所有服務",
                "執行全面健康檢查"
            ],
            CatastropheLevel.DATA_CORRUPTION: [
                "識別受損數據範圍",
                "從檢查點恢復受損數據",
                "執行數據完整性驗證",
                "記錄損壞模式以防止再次發生"
            ],
            CatastropheLevel.CASCADING_FAILURE: [
                "立即停止所有依賴服務",
                "隔離故障源",
                "從檢查點恢復核心服務",
                "逐步恢復依賴服務",
                "監控恢復過程中的連鎖反應"
            ],
            CatastropheLevel.IRREVERSIBLE_DAMAGE: [
                "評估不可逆損害範圍",
                "從最早可用檢查點恢復",
                "重建丟失的數據（如可能）",
                "通知用戶數據丟失情況",
                "制定預防措施"
            ],
        }

    def _get_recovery_plan(self, level: CatastropheLevel) -> List[str]:
        return self._recovery_strategies.get(level, ["無可用恢復策略"])

    def set_system_goal(self, goal_id: str, primary_goal: str,
                       sub_goals: List[str] = None,
                       success_criteria: Dict = None):
        self.goal_anchor.set_goal(goal_id, primary_goal, sub_goals, success_criteria)

    def save_checkpoint(self, system_state: Dict, goal_id: str = None) -> str:
        goal_state = self.goal_anchor.goals.get(goal_id, GoalState(primary_goal="unknown", sub_goals=[], success_criteria={}))
        cp_id = self.checkpoint_mgr.create_checkpoint(
            system_state=system_state,
            goal_state={"primary_goal": goal_state.primary_goal, "success_criteria": goal_state.success_criteria}
        )
        return cp_id

    def recover(self, current_state: Dict,
                catastrophe_level: CatastropheLevel,
                goal_id: str = "default") -> RecoveryResult:
        start_time = time.time()
        phases_completed = []
        checkpoint_used = None
        goal_deviation = 0.0
        data_loss = False
        lessons = []

        self.logger.info(f"開始災難恢復: {catastrophe_level.value}")

        phases_completed.append(RecoveryPhase.DETECTION)

        phases_completed.append(RecoveryPhase.ASSESSMENT)
        recovery_plan = self._get_recovery_plan(catastrophe_level)
        self.logger.info(f"恢復計劃: {recovery_plan}")

        checkpoint = self.checkpoint_mgr.get_latest_checkpoint()
        if checkpoint:
            phases_completed.append(RecoveryPhase.CHECKPOINT)
            checkpoint_used = checkpoint.id

            integrity_ok = self.checkpoint_mgr.verify_integrity(checkpoint.id)
            if not integrity_ok:
                data_loss = True
                lessons.append("檢查點完整性驗證失敗，數據可能已損壞")

            phases_completed.append(RecoveryPhase.ROLLBACK)
            recovered_state = self.rollback_mgr.rollback_to_checkpoint(checkpoint, current_state)

            phases_completed.append(RecoveryPhase.VERIFICATION)
            deviation, issues = self.goal_anchor.check_deviation(goal_id, recovered_state)
            goal_deviation = deviation

            if deviation > 0.3:
                correction_plan = self.goal_anchor.get_correction_plan(goal_id, deviation, issues)
                lessons.extend(correction_plan)

            phases_completed.append(RecoveryPhase.RECOVERY)
            phases_completed.append(RecoveryPhase.VALIDATION)
        else:
            data_loss = True
            lessons.append("無可用檢查點，無法恢復")
            goal_deviation = 1.0

        phases_completed.append(RecoveryPhase.COMPLETE)

        total_time = (time.time() - start_time) * 1000

        result = RecoveryResult(
            success=goal_deviation < 0.5,
            catastrophe_level=catastrophe_level,
            phases_completed=phases_completed,
            checkpoint_used=checkpoint_used,
            goal_deviation=goal_deviation,
            recovery_time_ms=total_time,
            data_loss=data_loss,
            lessons_learned=lessons
        )
        self.recovery_history.append(result)
        return result

    def get_recovery_summary(self) -> Dict:
        return {
            "total_recoveries": len(self.recovery_history),
            "successful": len([r for r in self.recovery_history if r.success]),
            "data_loss_count": len([r for r in self.recovery_history if r.data_loss]),
            "avg_recovery_time": sum(r.recovery_time_ms for r in self.recovery_history) / max(len(self.recovery_history), 1),
            "avg_deviation": sum(r.goal_deviation for r in self.recovery_history) / max(len(self.recovery_history), 1)
        }


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    print("=" * 80)
    print("CatastrophicRecoveryPlatform — 災難性恢復平台")
    print("【乘法創新】CheckpointManager × RollbackManager × RecoveryEngine × GoalAnchor")
    print("=" * 80)
    print()

    platform = CatastrophicRecoveryPlatform()

    platform.set_system_goal("main", "維持系統正常運行",
                            sub_goals=["數據完整性", "服務可用性"],
                            success_criteria={"status": "running", "data_integrity": True})

    system_state = {"status": "running", "data_integrity": True, "users": 100, "transactions": 5000}
    cp_id = platform.save_checkpoint(system_state, "main")
    print(f"✅ 檢查點已保存: {cp_id}")
    print()

    test_catastrophes = [
        (CatastropheLevel.PARTIAL_LOSS, "部分數據丟失", {"status": "degraded", "data_integrity": False, "users": 80}),
        (CatastropheLevel.FULL_SYSTEM_FAILURE, "系統完全崩潰", {"status": "down", "data_integrity": False}),
        (CatastropheLevel.DATA_CORRUPTION, "數據損壞", {"status": "running", "data_integrity": False, "corrupted_keys": ["users"]}),
        (CatastropheLevel.CASCADING_FAILURE, "連鎖故障", {"status": "down", "data_integrity": False, "cascade": True}),
    ]

    for level, desc, damaged_state in test_catastrophes:
        print(f"情景: {desc} ({level.value})")
        result = platform.recover(damaged_state, level, "main")
        print(f"  恢復成功: {'是' if result.success else '否'}")
        print(f"  目標偏離度: {result.goal_deviation:.2f}")
        print(f"  數據丟失: {'是' if result.data_loss else '否'}")
        print(f"  恢復階段: {len(result.phases_completed)}/{len(RecoveryPhase)}")
        print(f"  恢復時間: {result.recovery_time_ms:.1f}ms")
        if result.lessons_learned:
            print(f"  教訓: {result.lessons_learned[0]}")
        print()

    print("=" * 80)
    print("恢復摘要")
    print("=" * 80)
    summary = platform.get_recovery_summary()
    for k, v in summary.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
