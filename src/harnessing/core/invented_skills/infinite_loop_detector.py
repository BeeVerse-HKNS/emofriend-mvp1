"""
INV-003 InfiniteLoopDetector
Formula: S² + A * R
Explanation: SelfHealing 自我改善 + Automation 與 Reasoning 協同 = 無限循環偵測器
Target Painpoints: WAA-001, WAA-002
"""

import hashlib
import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class LoopStatus(Enum):
    NORMAL = "normal"
    SUSPICIOUS = "suspicious"
    DETECTED = "detected"
    INTERVENED = "intervened"


class InterventionType(Enum):
    WARN = "warn"
    PAUSE = "pause"
    TERMINATE = "terminate"
    REDIRECT = "redirect"


@dataclass
class ExecutionState:
    step: int
    action: str
    context_hash: str
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LoopPattern:
    pattern_id: str
    start_step: int
    end_step: int
    cycle_length: int
    occurrences: int
    actions: List[str] = field(default_factory=list)


@dataclass
class DetectionResult:
    status: LoopStatus
    confidence: float
    pattern: Optional[LoopPattern] = None
    message: str = ""
    intervention: Optional[InterventionType] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class LoopPatternRecognizer:
    def __init__(self, min_cycle_length: int = 2, max_cycle_length: int = 10):
        self.min_cycle_length = min_cycle_length
        self.max_cycle_length = max_cycle_length
        self._patterns: Dict[str, LoopPattern] = {}

    def compute_context_hash(self, action: str, context: Dict[str, Any]) -> str:
        key = f"{action}:{json.dumps(context, sort_keys=True, default=str)}"
        return hashlib.md5(key.encode()).hexdigest()[:16]

    def detect_cycle(self, states: List[ExecutionState]) -> Optional[LoopPattern]:
        if len(states) < self.min_cycle_length * 2:
            return None
        
        hashes = [s.context_hash for s in states]
        
        for cycle_len in range(self.min_cycle_length, min(self.max_cycle_length + 1, len(hashes) // 2 + 1)):
            for start in range(len(hashes) - cycle_len * 2 + 1):
                pattern = hashes[start:start + cycle_len]
                next_pattern = hashes[start + cycle_len:start + cycle_len * 2]
                
                if pattern == next_pattern:
                    pattern_id = hashlib.md5(''.join(pattern).encode()).hexdigest()[:8]
                    actions = [states[start + i].action for i in range(cycle_len)]
                    
                    return LoopPattern(
                        pattern_id=pattern_id,
                        start_step=states[start].step,
                        end_step=states[start + cycle_len * 2 - 1].step,
                        cycle_length=cycle_len,
                        occurrences=2,
                        actions=actions
                    )
        
        return None

    def get_known_patterns(self) -> Dict[str, LoopPattern]:
        return self._patterns

    def register_pattern(self, pattern: LoopPattern) -> None:
        self._patterns[pattern.pattern_id] = pattern


class ExecutionMonitor:
    def __init__(self, max_history: int = 1000, similarity_threshold: float = 0.8):
        self.max_history = max_history
        self.similarity_threshold = similarity_threshold
        self._history: List[ExecutionState] = []
        self._step_counter: int = 0

    def record(self, action: str, context: Dict[str, Any], recognizer: LoopPatternRecognizer) -> ExecutionState:
        self._step_counter += 1
        context_hash = recognizer.compute_context_hash(action, context)
        
        state = ExecutionState(
            step=self._step_counter,
            action=action,
            context_hash=context_hash,
            metadata={'context_size': len(context)}
        )
        
        self._history.append(state)
        
        if len(self._history) > self.max_history:
            self._history = self._history[-self.max_history:]
        
        return state

    def get_history(self, last_n: Optional[int] = None) -> List[ExecutionState]:
        if last_n is None:
            return self._history.copy()
        return self._history[-last_n:]

    def get_repetition_count(self, context_hash: str) -> int:
        return sum(1 for s in self._history if s.context_hash == context_hash)

    def get_action_frequency(self) -> Dict[str, int]:
        freq: Dict[str, int] = {}
        for state in self._history:
            freq[state.action] = freq.get(state.action, 0) + 1
        return freq


class InterventionTrigger:
    def __init__(
        self,
        warning_threshold: int = 3,
        pause_threshold: int = 5,
        terminate_threshold: int = 10
    ):
        self.warning_threshold = warning_threshold
        self.pause_threshold = pause_threshold
        self.terminate_threshold = terminate_threshold
        self._interventions: List[Dict[str, Any]] = []

    def evaluate(self, repetition_count: int, pattern: Optional[LoopPattern] = None) -> InterventionType:
        if repetition_count >= self.terminate_threshold:
            return InterventionType.TERMINATE
        elif repetition_count >= self.pause_threshold:
            return InterventionType.PAUSE
        elif repetition_count >= self.warning_threshold:
            return InterventionType.WARN
        return InterventionType.WARN

    def trigger(self, intervention_type: InterventionType, reason: str, pattern: Optional[LoopPattern] = None) -> Dict[str, Any]:
        intervention = {
            'type': intervention_type.value,
            'reason': reason,
            'pattern_id': pattern.pattern_id if pattern else None,
            'timestamp': datetime.now().isoformat()
        }
        self._interventions.append(intervention)
        return intervention

    def get_intervention_history(self) -> List[Dict[str, Any]]:
        return self._interventions.copy()


class GoalDriftDetector:
    def __init__(self, drift_threshold: float = 0.3):
        self.drift_threshold = drift_threshold
        self._original_goal: Optional[str] = None
        self._goal_embeddings: List[str] = []

    def set_original_goal(self, goal: str) -> None:
        self._original_goal = goal
        self._goal_embeddings = [self._compute_goal_hash(goal)]

    def _compute_goal_hash(self, goal: str) -> str:
        return hashlib.md5(goal.lower().encode()).hexdigest()[:16]

    def check_drift(self, current_goal: str) -> Tuple[bool, float]:
        if not self._original_goal:
            return False, 0.0
        
        original_hash = self._compute_goal_hash(self._original_goal)
        current_hash = self._compute_goal_hash(current_goal)
        
        if original_hash == current_hash:
            return False, 0.0
        
        self._goal_embeddings.append(current_hash)
        
        unique_embeddings = len(set(self._goal_embeddings))
        drift_score = (unique_embeddings - 1) / max(len(self._goal_embeddings), 1)
        
        return drift_score > self.drift_threshold, drift_score

    def get_drift_history(self) -> List[str]:
        return self._goal_embeddings.copy()


class InfiniteLoopDetector:
    """
    INV-003: InfiniteLoopDetector
    Formula: S² + A * R
    
    偵測並防止 Agent 任務執行中的無限循環
    """

    def __init__(
        self,
        max_history: int = 1000,
        warning_threshold: int = 3,
        pause_threshold: int = 5,
        terminate_threshold: int = 10
    ):
        self.pattern_recognizer = LoopPatternRecognizer()
        self.monitor = ExecutionMonitor(max_history=max_history)
        self.intervention = InterventionTrigger(
            warning_threshold=warning_threshold,
            pause_threshold=pause_threshold,
            terminate_threshold=terminate_threshold
        )
        self.drift_detector = GoalDriftDetector()

    def analyze(self, action: str, context: Dict[str, Any], current_goal: Optional[str] = None) -> DetectionResult:
        state = self.monitor.record(action, context, self.pattern_recognizer)
        
        repetition_count = self.monitor.get_repetition_count(state.context_hash)
        
        history = self.monitor.get_history(last_n=50)
        pattern = self.pattern_recognizer.detect_cycle(history)
        
        if pattern:
            self.pattern_recognizer.register_pattern(pattern)
        
        intervention_type = self.intervention.evaluate(repetition_count, pattern)
        
        status = LoopStatus.NORMAL
        confidence = 0.0
        message = "執行正常"
        
        if pattern and repetition_count >= 3:
            status = LoopStatus.DETECTED
            confidence = min(0.5 + repetition_count * 0.1, 1.0)
            message = f"偵測到循環模式: {pattern.cycle_length} 步循環，出現 {pattern.occurrences} 次"
        elif repetition_count >= 3:
            status = LoopStatus.SUSPICIOUS
            confidence = 0.3 + repetition_count * 0.05
            message = f"可疑重複: 相同狀態出現 {repetition_count} 次"
        
        if current_goal:
            has_drifted, drift_score = self.drift_detector.check_drift(current_goal)
            if has_drifted:
                status = LoopStatus.DETECTED
                confidence = max(confidence, 0.7)
                message += f" | 目標漂移: {drift_score:.2f}"
        
        if status in [LoopStatus.DETECTED, LoopStatus.SUSPICIOUS]:
            self.intervention.trigger(intervention_type, message, pattern)
        
        return DetectionResult(
            status=status,
            confidence=confidence,
            pattern=pattern,
            message=message,
            intervention=intervention_type if status != LoopStatus.NORMAL else None
        )

    def set_goal(self, goal: str) -> None:
        self.drift_detector.set_original_goal(goal)

    def get_statistics(self) -> Dict[str, Any]:
        return {
            'total_steps': self.monitor._step_counter,
            'history_size': len(self.monitor._history),
            'known_patterns': len(self.pattern_recognizer.get_known_patterns()),
            'interventions': len(self.intervention.get_intervention_history()),
            'action_frequency': self.monitor.get_action_frequency()
        }

    def reset(self) -> None:
        self.monitor._history.clear()
        self.monitor._step_counter = 0
        self.pattern_recognizer._patterns.clear()
        self.intervention._interventions.clear()
        self.drift_detector._goal_embeddings.clear()


if __name__ == "__main__":
    detector = InfiniteLoopDetector(
        warning_threshold=3,
        pause_threshold=5,
        terminate_threshold=8
    )
    
    detector.set_goal("完成數據處理任務")
    
    print("=== Test 1: Normal Execution ===")
    for i in range(5):
        result = detector.analyze(
            action=f"process_item_{i}",
            context={'item_id': i, 'status': 'processing'}
        )
        print(f"  Step {i+1}: {result.status.value} - {result.message}")
    
    print("\n=== Test 2: Loop Detection ===")
    loop_context = {'item_id': 1, 'status': 'retry'}
    for i in range(10):
        result = detector.analyze(
            action="retry_operation",
            context=loop_context
        )
        print(f"  Step {i+1}: {result.status.value} (confidence: {result.confidence:.2f}) - {result.message}")
        if result.intervention:
            print(f"    Intervention: {result.intervention.value}")
        if result.status == LoopStatus.DETECTED and result.intervention == InterventionType.TERMINATE:
            break
    
    print("\n=== Statistics ===")
    stats = detector.get_statistics()
    print(json.dumps(stats, indent=2))
