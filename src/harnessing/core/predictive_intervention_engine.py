#!/usr/bin/env python3
"""
PredictiveInterventionEngine — 預測干預引擎

全新技巧：現有世界未有的 AI Agent 自我保護機制

核心概念：
- 現有 Self-Improvement = 學習過去的錯誤
- 新引擎 = 預測未來的錯誤，在發生之前干預

數學原理：
- 乘法放大：預測準確率 × 干預時機 = 錯誤預防效益
- 加法組合：歷史模式 + 當前狀態 + 趨勢分析 = 風險評分

這不是錯誤分類（ErrorClassifier），而是：
- 錯誤分類 = 錯誤發生後分類
- 預測干預 = 錯誤發生前預測

使用方法：
```python
from src.harnessing.core.predictive_intervention_engine import PredictiveInterventionEngine

engine = PredictiveInterventionEngine()

# 記錄系統狀態
engine.record_state({"cpu": 85, "memory": 90, "error_rate": 0.05})

# 預測風險
risks = engine.predict_risks()

# 執行預防干預
for risk in risks:
    engine.intervene(risk)
```
"""

import json
import logging
from enum import Enum
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
import threading
import time
from collections import deque


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RiskPrediction:
    risk_type: str
    probability: float
    risk_level: RiskLevel
    timeframe: str
    indicators: List[str]
    recommended_action: str
    confidence: float


@dataclass
class Intervention:
    risk_prediction: RiskPrediction
    action_taken: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    effectiveness: float = 0.0


@dataclass
class Pattern:
    name: str
    sequence: List[str]
    frequency: int
    lead_time: int
    accuracy: float


@dataclass
class SystemState:
    timestamp: str
    metrics: Dict[str, float]
    events: List[str]


class PatternRecognizer:
    """
    模式識別器
    識別歷史事件序列中的模式
    """

    def __init__(self, min_frequency: int = 3, min_lead_time: int = 1):
        self.min_frequency = min_frequency
        self.min_lead_time = min_lead_time
        self.logger = logging.getLogger(__name__)
        self._patterns: List[Pattern] = []
        self._sequences: deque = deque(maxlen=1000)

    def record_sequence(self, sequence: List[str]) -> None:
        self._sequences.append(sequence)

    def analyze_patterns(self) -> List[Pattern]:
        sequence_strs = [json.dumps(s, sort_keys=True) for s in self._sequences]

        from collections import Counter
        counter = Counter(sequence_strs)

        patterns = []
        for seq_str, freq in counter.items():
            if freq >= self.min_frequency:
                seq = json.loads(seq_str)
                patterns.append(Pattern(
                    name=f"pattern_{len(patterns)}",
                    sequence=seq,
                    frequency=freq,
                    lead_time=self._calculate_lead_time(seq),
                    accuracy=freq / len(self._sequences)
                ))

        self._patterns = patterns
        return patterns

    def _calculate_lead_time(self, sequence: List[str]) -> int:
        if len(sequence) >= 2:
            return len(sequence) - 1
        return self.min_lead_time

    def predict_from_patterns(self, current_sequence: List[str]) -> List[RiskPrediction]:
        predictions = []

        for pattern in self._patterns:
            if self._matches_prefix(pattern.sequence, current_sequence):
                remaining = pattern.sequence[len(current_sequence):]
                predictions.append(RiskPrediction(
                    risk_type="pattern_based",
                    probability=pattern.accuracy,
                    risk_level=self._probability_to_level(pattern.accuracy),
                    timeframe=f"{pattern.lead_time} steps",
                    indicators=[f"Pattern: {pattern.name}", f"Frequency: {pattern.frequency}"],
                    recommended_action=f"Monitor for: {', '.join(remaining)}",
                    confidence=pattern.accuracy
                ))

        return predictions

    def _matches_prefix(self, pattern: List[str], sequence: List[str]) -> bool:
        if len(pattern) <= len(sequence):
            return False
        return pattern[:len(sequence)] == sequence

    def _probability_to_level(self, probability: float) -> RiskLevel:
        if probability >= 0.8:
            return RiskLevel.HIGH
        elif probability >= 0.5:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW


class TrendAnalyzer:
    """
    趨勢分析器
    分析指標趨勢，識別異常上升/下降
    """

    def __init__(self, window_size: int = 10):
        self.window_size = window_size
        self.logger = logging.getLogger(__name__)
        self._metric_history: Dict[str, deque] = {}

    def record_metric(self, metric_name: str, value: float) -> None:
        if metric_name not in self._metric_history:
            self._metric_history[metric_name] = deque(maxlen=self.window_size)
        self._metric_history[metric_name].append(value)

    def analyze_trends(self) -> List[Dict]:
        trends = []

        for metric_name, values in self._metric_history.items():
            if len(values) < 3:
                continue

            recent_avg = sum(list(values)[-3:]) / 3
            older_avg = sum(list(values)[:-3]) / max(len(values) - 3, 1)

            if older_avg > 0:
                change_rate = (recent_avg - older_avg) / older_avg
            else:
                change_rate = 0

            if abs(change_rate) > 0.2:
                trend = {
                    "metric": metric_name,
                    "change_rate": change_rate,
                    "direction": "increasing" if change_rate > 0 else "decreasing",
                    "risk_level": self._change_to_risk_level(change_rate)
                }
                trends.append(trend)

        return trends

    def _change_to_risk_level(self, change_rate: float) -> RiskLevel:
        if abs(change_rate) > 0.5:
            return RiskLevel.CRITICAL
        elif abs(change_rate) > 0.3:
            return RiskLevel.HIGH
        elif abs(change_rate) > 0.2:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW

    def predict_from_trends(self, trends: List[Dict]) -> List[RiskPrediction]:
        predictions = []

        for trend in trends:
            if trend["direction"] == "increasing":
                predictions.append(RiskPrediction(
                    risk_type="trend_based",
                    probability=min(abs(trend["change_rate"]), 1.0),
                    risk_level=trend["risk_level"],
                    timeframe="next 1-3 steps",
                    indicators=[f"{trend['metric']} increasing at {trend['change_rate']:.1%}"],
                    recommended_action=f"Reduce {trend['metric']} or scale resources",
                    confidence=0.7
                ))

        return predictions


class ThresholdMonitor:
    """
    閾值監控器
    監控關鍵指標是否接近危險閾值
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._thresholds: Dict[str, Dict] = {}

    def set_threshold(self, metric: str, warning: float, critical: float,
                    inverse: bool = False) -> None:
        self._thresholds[metric] = {
            "warning": warning,
            "critical": critical,
            "inverse": inverse
        }

    def check_thresholds(self, metrics: Dict[str, float]) -> List[RiskPrediction]:
        predictions = []

        for metric, value in metrics.items():
            if metric not in self._thresholds:
                continue

            threshold = self._thresholds[metric]
            is_risk, level, proximity = self._evaluate_threshold(
                value, threshold["warning"], threshold["critical"], threshold["inverse"]
            )

            if is_risk:
                predictions.append(RiskPrediction(
                    risk_type="threshold_based",
                    probability=proximity,
                    risk_level=level,
                    timeframe="immediate" if level == RiskLevel.CRITICAL else "soon",
                    indicators=[f"{metric}={value:.2f} approaching threshold"],
                    recommended_action=self._get_action(metric, level),
                    confidence=0.9
                ))

        return predictions

    def _evaluate_threshold(self, value: float, warning: float,
                          critical: float, inverse: bool) -> tuple:
        if inverse:
            if value < critical:
                return True, RiskLevel.CRITICAL, 1.0
            elif value < warning:
                proximity = 1 - (value / warning) if warning > 0 else 0.5
                return True, RiskLevel.MEDIUM, proximity
        else:
            if value > critical:
                return True, RiskLevel.CRITICAL, 1.0
            elif value > warning:
                proximity = (value - warning) / (critical - warning) if critical > warning else 0.5
                return True, RiskLevel.MEDIUM, proximity

        return False, RiskLevel.LOW, 0.0

    def _get_action(self, metric: str, level: RiskLevel) -> str:
        actions = {
            "cpu": "Scale up or distribute load",
            "memory": "Clear caches or increase memory",
            "error_rate": "Investigate recent changes",
            "latency": "Optimize or scale service",
        }
        base = actions.get(metric, "Take preventive action")
        if level == RiskLevel.CRITICAL:
            return f"URGENT: {base}"
        return base


class InterventionExecutor:
    """
    干預執行器
    執行預防性干預措施
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._handlers: Dict[str, List[Callable]] = {}
        self._interventions: List[Intervention] = []

    def register_handler(self, risk_type: str, handler: Callable) -> None:
        if risk_type not in self._handlers:
            self._handlers[risk_type] = []
        self._handlers[risk_type].append(handler)

    def execute(self, risk: RiskPrediction) -> bool:
        handlers = self._handlers.get(risk.risk_type, [])
        handlers.extend(self._handlers.get("*", []))

        action_taken = "no_action"

        for handler in handlers:
            try:
                result = handler(risk)
                if result:
                    action_taken = handler.__name__ if hasattr(handler, '__name__') else "custom"
                    break
            except Exception as e:
                self.logger.error(f"Intervention handler failed: {e}")

        intervention = Intervention(
            risk_prediction=risk,
            action_taken=action_taken,
            effectiveness=0.5
        )
        self._interventions.append(intervention)

        self.logger.info(f"Executed intervention for {risk.risk_type}: {action_taken}")
        return action_taken != "no_action"

    def get_intervention_history(self, limit: int = 100) -> List[Intervention]:
        return self._interventions[-limit:]


class PredictiveInterventionEngine:
    """
    預測干預引擎

    核心功能：
    1. 模式識別 - 識別歷史事件序列中的規律
    2. 趨勢分析 - 分析指標變化趨勢
    3. 閾值監控 - 監控關鍵指標是否接近危險值
    4. 預防干預 - 在風險變成實際錯誤前執行干預

    與現有技能的根本區別：
    - ErrorClassifier = 錯誤發生後分類（反應型）
    - RetryManager = 錯誤發生後重試（反應型）
    - SelfImprovementEngine = 錯誤發生後學習（反應型）
    - PredictiveInterventionEngine = 錯誤發生前預測+干預（主動型）

    數學原理：
    - 預測準確率 × 干預時機 = 錯誤預防效益
    - 歷史模式 + 當前狀態 + 趨勢 = 風險評分
    """

    def __init__(self, base_path: Optional[Path] = None):
        if base_path is None:
            base_path = Path(__file__).parent.parent.parent / "data"
        self.base_path = Path(base_path)
        self.predictions_dir = self.base_path / "predictions"
        self.predictions_dir.mkdir(parents=True, exist_ok=True)

        self.logger = logging.getLogger(__name__)

        self.pattern_recognizer = PatternRecognizer()
        self.trend_analyzer = TrendAnalyzer()
        self.threshold_monitor = ThresholdMonitor()
        self.intervention_executor = InterventionExecutor()

        self._state_history: deque = deque(maxlen=1000)
        self._predictions: List[RiskPrediction] = []

        self._setup_default_thresholds()
        self._setup_default_interventions()

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )

    def _setup_default_thresholds(self) -> None:
        self.threshold_monitor.set_threshold("cpu", 70, 90)
        self.threshold_monitor.set_threshold("memory", 70, 85)
        self.threshold_monitor.set_threshold("error_rate", 0.05, 0.1)
        self.threshold_monitor.set_threshold("latency_ms", 500, 1000)

    def _setup_default_interventions(self) -> None:
        def scale_resources(risk):
            self.logger.warning(f"SCALE RESOURCES: {risk.risk_type}")
            return True

        def alert_team(risk):
            self.logger.warning(f"ALERT TEAM: {risk.recommended_action}")
            return True

        self.intervention_executor.register_handler("threshold_based", scale_resources)
        self.intervention_executor.register_handler("trend_based", alert_team)
        self.intervention_executor.register_handler("pattern_based", alert_team)

    def record_state(self, metrics: Dict[str, float], events: List[str] = None) -> None:
        state = SystemState(
            timestamp=datetime.now().isoformat(),
            metrics=metrics,
            events=events or []
        )
        self._state_history.append(state)

        for metric_name, value in metrics.items():
            self.trend_analyzer.record_metric(metric_name, value)

        if events:
            event_sequence = [e for e in events]
            self.pattern_recognizer.record_sequence(event_sequence)

    def predict_risks(self) -> List[RiskPrediction]:
        predictions = []

        current_metrics = self._get_current_metrics()
        if current_metrics:
            predictions.extend(self.threshold_monitor.check_thresholds(current_metrics))

        trends = self.trend_analyzer.analyze_trends()
        predictions.extend(self.trend_analyzer.predict_from_trends(trends))

        patterns = self.pattern_recognizer.analyze_patterns()
        current_sequence = self._get_current_event_sequence()
        predictions.extend(self.pattern_recognizer.predict_from_patterns(current_sequence))

        predictions = self._deduplicate_and_rank(predictions)

        self._predictions = predictions
        self._save_predictions(predictions)

        return predictions

    def _get_current_metrics(self) -> Dict[str, float]:
        if not self._state_history:
            return {}
        return self._state_history[-1].metrics

    def _get_current_event_sequence(self) -> List[str]:
        if not self._state_history:
            return []
        return self._state_history[-1].events

    def _deduplicate_and_rank(self, predictions: List[RiskPrediction]) -> List[RiskPrediction]:
        seen = {}
        for p in predictions:
            key = p.risk_type
            if key not in seen or p.probability > seen[key].probability:
                seen[key] = p

        result = sorted(seen.values(), key=lambda x: -x.probability)
        return result

    def intervene(self, risk: RiskPrediction) -> bool:
        return self.intervention_executor.execute(risk)

    def intervene_all(self, max_risks: int = 5) -> Dict:
        risks = self.predict_risks()[:max_risks]
        results = []

        for risk in risks:
            if risk.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
                success = self.intervene(risk)
                results.append({
                    "risk": risk.risk_type,
                    "level": risk.risk_level.value,
                    "intervened": success
                })

        return {
            "risks_predicted": len(risks),
            "interventions_executed": len(results),
            "details": results
        }

    def _save_predictions(self, predictions: List[RiskPrediction]) -> None:
        date_str = datetime.now().strftime("%Y-%m-%d")
        path = self.predictions_dir / f"{date_str}_predictions.json"

        data = [
            {
                "risk_type": p.risk_type,
                "probability": p.probability,
                "risk_level": p.risk_level.value,
                "timeframe": p.timeframe,
                "indicators": p.indicators,
                "recommended_action": p.recommended_action,
                "confidence": p.confidence,
            }
            for p in predictions
        ]

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def get_prediction_summary(self) -> Dict:
        if not self._predictions:
            return {"status": "no_predictions", "risks": []}

        high_risks = [p for p in self._predictions if p.risk_level == RiskLevel.HIGH]
        critical_risks = [p for p in self._predictions if p.risk_level == RiskLevel.CRITICAL]

        return {
            "total_risks": len(self._predictions),
            "critical": len(critical_risks),
            "high": len(high_risks),
            "risks": [
                {
                    "type": p.risk_type,
                    "level": p.risk_level.value,
                    "probability": f"{p.probability:.1%}",
                    "action": p.recommended_action,
                }
                for p in self._predictions[:5]
            ]
        }


def main():
    print("=" * 60)
    print("PredictiveInterventionEngine Demo")
    print("=" * 60)

    engine = PredictiveInterventionEngine()

    print("\n1. Recording system states...")
    engine.record_state({"cpu": 50, "memory": 60, "error_rate": 0.01})
    engine.record_state({"cpu": 60, "memory": 65, "error_rate": 0.02})
    engine.record_state({"cpu": 75, "memory": 75, "error_rate": 0.03}, events=["high_cpu_warning"])
    engine.record_state({"cpu": 85, "memory": 80, "error_rate": 0.05}, events=["high_cpu_warning", "memory_pressure"])

    print("\n2. Predicting risks...")
    risks = engine.predict_risks()

    print(f"   Found {len(risks)} potential risks:")
    for risk in risks:
        print(f"   - {risk.risk_type}: {risk.risk_level.value} ({risk.probability:.1%})")
        print(f"     Action: {risk.recommended_action}")

    print("\n3. Executing interventions...")
    result = engine.intervene_all()

    print(f"   Intervened: {result['interventions_executed']} of {result['risks_predicted']} risks")

    print("\n4. Prediction summary:")
    summary = engine.get_prediction_summary()
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
