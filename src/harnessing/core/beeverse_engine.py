from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger()


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    CATASTROPHIC = "catastrophic"


class FormulaOp(str, Enum):
    UNION = "+"
    DIFFERENCE = "-"
    CROSS = "*"
    SPECIALIZE = "/"
    SELF_IMPROVE = "sq"
    DECOMPOSE = "sqrt"
    AMPLIFY = "^"
    ABSTRACT = "log"


class OptimizationTarget(str, Enum):
    SPEED = "speed"
    QUALITY = "quality"
    COST = "cost"
    RELIABILITY = "reliability"
    CREATIVITY = "creativity"


@dataclass
class FormulaStep:
    op: FormulaOp | None = None
    operand: str | None = None


@dataclass
class FormulaResult:
    formula_id: str
    steps: list[FormulaStep]
    coverage_categories: set[str]
    coverage_severities: set[Severity]
    coverage_dimensions: set[str]
    score: float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ImprovementCycle:
    cycle_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    baseline_score: float = 0.0
    current_score: float = 0.0
    iterations: int = 0
    best_formula: FormulaResult | None = None
    history: list[dict[str, Any]] = field(default_factory=list)


_ALL_CATEGORIES = {
    "failure", "recovery", "security", "data", "human", "system",
    "network", "resource", "integration", "timing", "compliance",
    "supply_chain", "environmental", "privacy", "business_continuity",
}

_ALL_SEVERITIES = {s for s in Severity}

_ABSTRACT_DIMENSIONS = {"complexity", "observability", "scalability"}

_BASE_DIMENSIONS = {
    "latency", "throughput", "accuracy", "availability", "durability",
    "consistency", "partition_tolerance", "recovery_time", "error_rate",
    "creativity_depth", "quality_requirement", "vram_constraint",
    "ram_constraint", "cpu_constraint", "token_efficiency",
    "knowledge_coverage", "self_healing_depth", "prediction_accuracy",
    "formula_effectiveness", "constraint_amplification",
}


class BeeVerseEngine:
    def __init__(self) -> None:
        self._skill_coverage: dict[str, dict[str, set]] = {}
        self._improvement_cycles: dict[str, ImprovementCycle] = {}
        self._formula_history: list[FormulaResult] = []
        self._performance_baseline: dict[str, list[float]] = {}

    def register_skill(self, name: str, categories: set[str], severities: set[Severity], dimensions: set[str]) -> None:
        self._skill_coverage[name] = {
            "categories": categories,
            "severities": severities,
            "dimensions": dimensions,
        }

    def evaluate_formula(self, steps: list[FormulaStep]) -> FormulaResult:
        result_categories: set[str] = set()
        result_severities: set[Severity] = set()
        result_dimensions: set[str] = set()
        stack: list[dict[str, set]] = []

        for step in steps:
            if step.op == FormulaOp.UNION:
                if len(stack) >= 2:
                    b, a = stack.pop(), stack.pop()
                    result_categories = a["categories"] | b["categories"]
                    result_severities = a["severities"] | b["severities"]
                    result_dimensions = a["dimensions"] | b["dimensions"]
                    stack.append({"categories": result_categories, "severities": result_severities, "dimensions": result_dimensions})
            elif step.op == FormulaOp.DIFFERENCE:
                if len(stack) >= 2:
                    b, a = stack.pop(), stack.pop()
                    result_categories = a["categories"] - b["categories"]
                    result_severities = a["severities"] - b["severities"]
                    result_dimensions = a["dimensions"] - b["dimensions"]
                    stack.append({"categories": result_categories, "severities": result_severities, "dimensions": result_dimensions})
            elif step.op == FormulaOp.CROSS:
                if len(stack) >= 2:
                    b, a = stack.pop(), stack.pop()
                    result_categories = a["categories"] & b["categories"]
                    result_severities = a["severities"] | b["severities"]
                    result_dimensions = a["dimensions"] | b["dimensions"]
                    stack.append({"categories": result_categories, "severities": result_severities, "dimensions": result_dimensions})
            elif step.op == FormulaOp.SPECIALIZE:
                if len(stack) >= 2:
                    b, a = stack.pop(), stack.pop()
                    result_categories = a["categories"] & b["categories"]
                    result_severities = a["severities"]
                    result_dimensions = a["dimensions"] & b["dimensions"]
                    stack.append({"categories": result_categories, "severities": result_severities, "dimensions": result_dimensions})
            elif step.op == FormulaOp.SELF_IMPROVE:
                if stack:
                    a = stack.pop()
                    result_categories = a["categories"]
                    result_severities = _ALL_SEVERITIES
                    result_dimensions = a["dimensions"] | _ABSTRACT_DIMENSIONS
                    stack.append({"categories": result_categories, "severities": result_severities, "dimensions": result_dimensions})
            elif step.op == FormulaOp.DECOMPOSE:
                if stack:
                    a = stack.pop()
                    result_categories = a["categories"]
                    result_severities = {Severity.LOW, Severity.MEDIUM}
                    result_dimensions = a["dimensions"]
                    stack.append({"categories": result_categories, "severities": result_severities, "dimensions": result_dimensions})
            elif step.op == FormulaOp.AMPLIFY:
                if len(stack) >= 2:
                    b, a = stack.pop(), stack.pop()
                    result_categories = a["categories"] | b["categories"]
                    result_severities = {Severity.HIGH, Severity.CRITICAL, Severity.CATASTROPHIC}
                    result_dimensions = a["dimensions"] | b["dimensions"]
                    stack.append({"categories": result_categories, "severities": result_severities, "dimensions": result_dimensions})
            elif step.op == FormulaOp.ABSTRACT:
                if stack:
                    a = stack.pop()
                    result_categories = _ALL_CATEGORIES
                    result_severities = a["severities"]
                    result_dimensions = _ABSTRACT_DIMENSIONS
                    stack.append({"categories": result_categories, "severities": result_severities, "dimensions": result_dimensions})
            elif step.operand:
                skill_cov = self._skill_coverage.get(step.operand, {
                    "categories": {step.operand},
                    "severities": {Severity.LOW, Severity.MEDIUM},
                    "dimensions": {step.operand + "_dim"},
                })
                stack.append({
                    "categories": set(skill_cov["categories"]),
                    "severities": set(skill_cov["severities"]) if all(isinstance(s, Severity) for s in skill_cov["severities"]) else {Severity.LOW, Severity.MEDIUM},
                    "dimensions": set(skill_cov["dimensions"]),
                })

        if stack:
            final = stack[-1]
            result_categories = final["categories"]
            result_severities = final["severities"]
            result_dimensions = final["dimensions"]

        cat_coverage = len(result_categories) / len(_ALL_CATEGORIES) if _ALL_CATEGORIES else 0
        sev_coverage = len(result_severities) / len(_ALL_SEVERITIES) if _ALL_SEVERITIES else 0
        dim_coverage = len(result_dimensions) / len(_BASE_DIMENSIONS) if _BASE_DIMENSIONS else 0
        score = (cat_coverage + sev_coverage + dim_coverage) / 3.0

        formula_result = FormulaResult(
            formula_id=uuid.uuid4().hex[:8],
            steps=steps,
            coverage_categories=result_categories,
            coverage_severities=result_severities,
            coverage_dimensions=result_dimensions,
            score=score,
        )
        self._formula_history.append(formula_result)
        return formula_result

    def self_improve(self, target: OptimizationTarget = OptimizationTarget.QUALITY, max_iterations: int = 10) -> ImprovementCycle:
        cycle = ImprovementCycle()
        cycle.baseline_score = self._get_current_score(target)
        cycle.current_score = cycle.baseline_score

        i14_steps = [
            FormulaStep(op=FormulaOp.ABSTRACT, operand="S+P"),
            FormulaStep(op=FormulaOp.SELF_IMPROVE, operand="F"),
            FormulaStep(op=FormulaOp.AMPLIFY, operand="C^H"),
            FormulaStep(op=FormulaOp.UNION),
            FormulaStep(op=FormulaOp.UNION),
        ]

        best = self.evaluate_formula(i14_steps)
        cycle.best_formula = best
        cycle.current_score = best.score
        cycle.iterations = 1

        for i in range(1, max_iterations):
            candidate_steps = self._generate_variant(i14_steps, i, target)
            candidate = self.evaluate_formula(candidate_steps)

            if candidate.score > best.score:
                best = candidate
                cycle.current_score = candidate.score
                cycle.history.append({
                    "iteration": i + 1,
                    "score": candidate.score,
                    "improvement": candidate.score - cycle.current_score,
                })

        cycle.best_formula = best
        return cycle

    def get_optimization_for_severity(self, severity: Severity) -> dict[str, Any]:
        strategies = {
            Severity.LOW: {"retry": True, "max_retries": 1, "backoff": 1.0},
            Severity.MEDIUM: {"retry": True, "max_retries": 2, "backoff": 2.0},
            Severity.HIGH: {"retry": True, "max_retries": 3, "backoff": 4.0, "fallback": True},
            Severity.CRITICAL: {"retry": True, "max_retries": 5, "backoff": 8.0, "fallback": True, "alert": True},
            Severity.CATASTROPHIC: {"retry": False, "fallback": True, "alert": True, "human_review": True},
        }
        return strategies.get(severity, strategies[Severity.MEDIUM])

    def record_performance(self, metric: str, value: float) -> None:
        if metric not in self._performance_baseline:
            self._performance_baseline[metric] = []
        self._performance_baseline[metric].append(value)
        if len(self._performance_baseline[metric]) > 1000:
            self._performance_baseline[metric] = self._performance_baseline[metric][-1000:]

    def get_z_score(self, metric: str, current_value: float) -> float:
        values = self._performance_baseline.get(metric, [])
        if len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
        std = math.sqrt(variance) if variance > 0 else 1.0
        return (current_value - mean) / std

    def _get_current_score(self, target: OptimizationTarget) -> float:
        metric_map = {
            OptimizationTarget.SPEED: "latency",
            OptimizationTarget.QUALITY: "quality_score",
            OptimizationTarget.COST: "token_cost",
            OptimizationTarget.RELIABILITY: "success_rate",
            OptimizationTarget.CREATIVITY: "creativity_score",
        }
        values = self._performance_baseline.get(metric_map.get(target, "quality_score"), [])
        if not values:
            return 0.0
        return sum(values[-10:]) / min(10, len(values))

    def _generate_variant(self, base_steps: list[FormulaStep], iteration: int, target: OptimizationTarget) -> list[FormulaStep]:
        variant = list(base_steps)
        if iteration % 3 == 0:
            variant.append(FormulaStep(op=FormulaOp.SELF_IMPROVE))
        elif iteration % 3 == 1:
            variant.append(FormulaStep(op=FormulaOp.ABSTRACT, operand="meta"))
        else:
            variant.append(FormulaStep(op=FormulaOp.CROSS, operand="domain"))
        return variant
