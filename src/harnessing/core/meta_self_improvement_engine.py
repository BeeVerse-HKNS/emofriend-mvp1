from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class OptimizationStrategy(str, Enum):
    THROTTLE = "throttle"
    EXPAND = "expand"
    REFACTOR = "refactor"


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class AnomalyFlag(str, Enum):
    NORMAL = "normal"
    ELEVATED = "elevated"
    ANOMALY = "anomaly"


@dataclass
class ImprovementOpportunity:
    metric_name: str
    current_value: float
    baseline_mean: float
    baseline_std: float
    z_score: float
    flag: AnomalyFlag
    suggested_strategy: OptimizationStrategy
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class OptimizationResult:
    strategy: OptimizationStrategy
    target: str
    applied: bool
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class PerformanceBaseline:
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self._metrics: dict[str, list[float]] = {}
        self.logger = logging.getLogger(__name__)

    def record(self, metric_name: str, value: float) -> None:
        if metric_name not in self._metrics:
            self._metrics[metric_name] = []
        self._metrics[metric_name].append(value)
        if len(self._metrics[metric_name]) > self.max_history:
            self._metrics[metric_name] = self._metrics[metric_name][-self.max_history:]

    def record_batch(self, metrics: dict[str, float]) -> None:
        for name, value in metrics.items():
            self.record(name, value)

    def get_mean(self, metric_name: str) -> float:
        values = self._metrics.get(metric_name, [])
        if not values:
            return 0.0
        return sum(values) / len(values)

    def get_std(self, metric_name: str) -> float:
        values = self._metrics.get(metric_name, [])
        if len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
        return math.sqrt(variance)

    def get_z_score(self, metric_name: str, value: float) -> float:
        std = self.get_std(metric_name)
        if std == 0.0:
            return 0.0
        mean = self.get_mean(metric_name)
        return (value - mean) / std

    def get_metric_history(self, metric_name: str) -> list[float]:
        return list(self._metrics.get(metric_name, []))

    def get_all_metrics(self) -> dict[str, dict[str, float]]:
        result = {}
        for name in self._metrics:
            result[name] = {
                "mean": self.get_mean(name),
                "std": self.get_std(name),
                "sample_count": len(self._metrics[name]),
                "latest": self._metrics[name][-1] if self._metrics[name] else 0.0,
            }
        return result


class ImprovementDetector:
    def __init__(self, baseline: PerformanceBaseline, z_threshold: float = 2.0):
        self.baseline = baseline
        self.z_threshold = z_threshold
        self.logger = logging.getLogger(__name__)

    def detect(self, metrics: dict[str, float]) -> list[ImprovementOpportunity]:
        opportunities = []
        for metric_name, current_value in metrics.items():
            z_score = self.baseline.get_z_score(metric_name, current_value)
            abs_z = abs(z_score)

            if abs_z >= self.z_threshold:
                flag = AnomalyFlag.ANOMALY
            elif abs_z >= self.z_threshold * 0.5:
                flag = AnomalyFlag.ELEVATED
            else:
                flag = AnomalyFlag.NORMAL

            if flag == AnomalyFlag.NORMAL:
                continue

            strategy = self._suggest_strategy(metric_name, z_score)

            opportunity = ImprovementOpportunity(
                metric_name=metric_name,
                current_value=current_value,
                baseline_mean=self.baseline.get_mean(metric_name),
                baseline_std=self.baseline.get_std(metric_name),
                z_score=z_score,
                flag=flag,
                suggested_strategy=strategy,
            )
            opportunities.append(opportunity)

        opportunities.sort(key=lambda o: abs(o.z_score), reverse=True)
        return opportunities

    def _suggest_strategy(self, metric_name: str, z_score: float) -> OptimizationStrategy:
        if z_score > 0:
            if "rate" in metric_name or "count" in metric_name or "frequency" in metric_name:
                return OptimizationStrategy.THROTTLE
            return OptimizationStrategy.EXPAND
        return OptimizationStrategy.REFACTOR


class SelfOptimizer:
    def __init__(self):
        self._applied_optimizations: list[OptimizationResult] = []
        self.logger = logging.getLogger(__name__)

    def apply(
        self, strategy: OptimizationStrategy, target: str, context: dict[str, Any] | None = None
    ) -> OptimizationResult:
        context = context or {}

        if strategy == OptimizationStrategy.THROTTLE:
            result = self._apply_throttle(target, context)
        elif strategy == OptimizationStrategy.EXPAND:
            result = self._apply_expand(target, context)
        elif strategy == OptimizationStrategy.REFACTOR:
            result = self._apply_refactor(target, context)
        else:
            result = OptimizationResult(
                strategy=strategy,
                target=target,
                applied=False,
                details={"reason": "unknown_strategy"},
            )

        self._applied_optimizations.append(result)
        self.logger.info(
            "optimization_applied",
            extra={"strategy": strategy.value, "target": target, "applied": result.applied},
        )
        return result

    def _apply_throttle(self, target: str, context: dict[str, Any]) -> OptimizationResult:
        current_rate = context.get("current_rate", 1.0)
        new_rate = current_rate * 0.7
        return OptimizationResult(
            strategy=OptimizationStrategy.THROTTLE,
            target=target,
            applied=True,
            details={
                "previous_rate": current_rate,
                "new_rate": round(new_rate, 4),
                "reduction_pct": 30.0,
            },
        )

    def _apply_expand(self, target: str, context: dict[str, Any]) -> OptimizationResult:
        current_coverage = context.get("current_coverage", 0.5)
        new_coverage = min(1.0, current_coverage * 1.3)
        return OptimizationResult(
            strategy=OptimizationStrategy.EXPAND,
            target=target,
            applied=True,
            details={
                "previous_coverage": current_coverage,
                "new_coverage": round(new_coverage, 4),
                "increase_pct": 30.0,
            },
        )

    def _apply_refactor(self, target: str, context: dict[str, Any]) -> OptimizationResult:
        current_complexity = context.get("current_complexity", 10)
        new_complexity = max(1, int(current_complexity * 0.6))
        return OptimizationResult(
            strategy=OptimizationStrategy.REFACTOR,
            target=target,
            applied=True,
            details={
                "previous_complexity": current_complexity,
                "new_complexity": new_complexity,
                "reduction_pct": 40.0,
            },
        )

    def get_history(self) -> list[dict[str, Any]]:
        return [
            {
                "strategy": r.strategy.value,
                "target": r.target,
                "applied": r.applied,
                "details": r.details,
                "timestamp": r.timestamp,
            }
            for r in self._applied_optimizations
        ]


class MetaSelfImprovementEngine:
    def __init__(self, z_threshold: float = 2.0, max_baseline_history: int = 1000):
        self.baseline = PerformanceBaseline(max_history=max_baseline_history)
        self.detector = ImprovementDetector(self.baseline, z_threshold=z_threshold)
        self.optimizer = SelfOptimizer()
        self.improvement_history: list[dict[str, Any]] = []
        self.logger = logging.getLogger(__name__)

    def check_performance(self, metrics: dict[str, float]) -> dict[str, Any]:
        anomalies = {}
        health = HealthStatus.HEALTHY

        for metric_name, value in metrics.items():
            z_score = self.baseline.get_z_score(metric_name, value)
            abs_z = abs(z_score)

            if abs_z >= self.detector.z_threshold:
                flag = AnomalyFlag.ANOMALY.value
                health = HealthStatus.CRITICAL
            elif abs_z >= self.detector.z_threshold * 0.5:
                flag = AnomalyFlag.ELEVATED.value
                if health == HealthStatus.HEALTHY:
                    health = HealthStatus.DEGRADED
            else:
                flag = AnomalyFlag.NORMAL.value

            anomalies[metric_name] = {
                "value": value,
                "z_score": round(z_score, 4),
                "flag": flag,
                "baseline_mean": round(self.baseline.get_mean(metric_name), 4),
                "baseline_std": round(self.baseline.get_std(metric_name), 4),
            }

        return {
            "health": health.value,
            "anomalies": anomalies,
            "metrics_checked": len(metrics),
            "timestamp": datetime.now().isoformat(),
        }

    def detect_improvements(self) -> list[dict[str, Any]]:
        latest_metrics = {}
        for name in self.baseline._metrics:
            values = self.baseline._metrics[name]
            if values:
                latest_metrics[name] = values[-1]

        opportunities = self.detector.detect(latest_metrics)
        return [
            {
                "metric_name": o.metric_name,
                "current_value": o.current_value,
                "baseline_mean": round(o.baseline_mean, 4),
                "baseline_std": round(o.baseline_std, 4),
                "z_score": round(o.z_score, 4),
                "flag": o.flag.value,
                "suggested_strategy": o.suggested_strategy.value,
            }
            for o in opportunities
        ]

    def apply_optimization(
        self, strategy: OptimizationStrategy, target: str, context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        result = self.optimizer.apply(strategy, target, context)
        return {
            "strategy": result.strategy.value,
            "target": result.target,
            "applied": result.applied,
            "details": result.details,
            "timestamp": result.timestamp,
        }

    def record_baseline(self, metrics: dict[str, float]) -> None:
        self.baseline.record_batch(metrics)

    def run_cycle(self, metrics: dict[str, float]) -> dict[str, Any]:
        self.record_baseline(metrics)

        performance = self.check_performance(metrics)

        latest_metrics = {}
        for name in self.baseline._metrics:
            values = self.baseline._metrics[name]
            if values:
                latest_metrics[name] = values[-1]
        opportunities = self.detector.detect(latest_metrics)

        optimizations = []
        for opp in opportunities:
            ctx = {
                "current_rate": opp.current_value,
                "current_coverage": opp.current_value,
                "current_complexity": int(abs(opp.z_score) * 10),
            }
            result = self.optimizer.apply(opp.suggested_strategy, opp.metric_name, ctx)
            optimizations.append({
                "strategy": result.strategy.value,
                "target": result.target,
                "applied": result.applied,
                "details": result.details,
            })

        cycle_result = {
            "performance": performance,
            "improvements_detected": len(opportunities),
            "optimizations_applied": len(optimizations),
            "optimizations": optimizations,
            "timestamp": datetime.now().isoformat(),
        }

        self.improvement_history.append(cycle_result)
        return cycle_result
