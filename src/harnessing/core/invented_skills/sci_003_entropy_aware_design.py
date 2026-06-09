from __future__ import annotations

import math
import structlog
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .base_engine import BaseInventionEngine
from .base_invention_engine import ConfidenceLevel, InventionResult

logger = structlog.get_logger()


class BudgetStatus(Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"


ENTROPY_DIMENSIONS = [
    "code_complexity",
    "dependency_count",
    "config_drift",
    "test_coverage",
    "doc_freshness",
    "api_stability",
]

DIMENSION_WEIGHTS: dict[str, float] = {
    "code_complexity": 0.20,
    "dependency_count": 0.15,
    "config_drift": 0.15,
    "test_coverage": 0.20,
    "doc_freshness": 0.15,
    "api_stability": 0.15,
}


class EntropyMeasurer:
    def measure(self, system_data: dict[str, Any]) -> dict[str, float]:
        results: dict[str, float] = {}
        for dim in ENTROPY_DIMENSIONS:
            dim_data = system_data.get(dim)
            if dim_data is None:
                results[dim] = 0.0
                continue
            if isinstance(dim_data, (int, float)):
                results[dim] = min(max(float(dim_data), 0.0), 1.0)
                continue
            if isinstance(dim_data, dict):
                results[dim] = self._shannon(dim_data)
                continue
            if isinstance(dim_data, (list, tuple)):
                results[dim] = self._shannon_from_list(dim_data)
                continue
            results[dim] = 0.0
        return results

    @staticmethod
    def _shannon(distribution: dict[str, float]) -> float:
        total = sum(distribution.values())
        if total <= 0:
            return 0.0
        entropy = 0.0
        for p in distribution.values():
            if p > 0:
                prob = p / total
                entropy -= prob * math.log2(prob)
        max_entropy = math.log2(len(distribution)) if len(distribution) > 1 else 1.0
        return min(entropy / max_entropy, 1.0) if max_entropy > 0 else 0.0

    @staticmethod
    def _shannon_from_list(items: list | tuple) -> float:
        if not items:
            return 0.0
        counts: dict[Any, int] = {}
        for item in items:
            counts[item] = counts.get(item, 0) + 1
        total = len(items)
        entropy = 0.0
        for count in counts.values():
            prob = count / total
            if prob > 0:
                entropy -= prob * math.log2(prob)
        max_entropy = math.log2(len(counts)) if len(counts) > 1 else 1.0
        return min(entropy / max_entropy, 1.0) if max_entropy > 0 else 0.0


@dataclass
class EntropyBudget:
    s_max: float = 1.0
    s_warn_ratio: float = 0.8
    s_crit_ratio: float = 0.95

    @property
    def s_warn(self) -> float:
        return self.s_max * self.s_warn_ratio

    @property
    def s_crit(self) -> float:
        return self.s_max * self.s_crit_ratio

    def check(self, total_entropy: float) -> BudgetStatus:
        if total_entropy >= self.s_crit:
            return BudgetStatus.CRITICAL
        if total_entropy >= self.s_warn:
            return BudgetStatus.WARNING
        return BudgetStatus.HEALTHY


@dataclass
class InterventionAction:
    level: str
    dimension: str
    action: str
    priority: float


class MaxwellsDemon:
    MICRO_THRESHOLD = 0.6
    MESO_THRESHOLD = 0.8
    MACRO_THRESHOLD = 0.95

    def intervene(
        self, entropy_dimensions: dict[str, float], budget_status: BudgetStatus
    ) -> list[InterventionAction]:
        actions: list[InterventionAction] = []
        if budget_status == BudgetStatus.HEALTHY:
            return actions

        for dim, entropy in entropy_dimensions.items():
            if entropy < self.MICRO_THRESHOLD:
                continue
            if entropy >= self.MACRO_THRESHOLD:
                actions.append(
                    InterventionAction(
                        level="macro",
                        dimension=dim,
                        action=f"restructure_architecture: {dim} entropy at {entropy:.2f}",
                        priority=1.0,
                    )
                )
            elif entropy >= self.MESO_THRESHOLD:
                actions.append(
                    InterventionAction(
                        level="meso",
                        dimension=dim,
                        action=f"refactor_module: {dim} entropy at {entropy:.2f}",
                        priority=0.7,
                    )
                )
            else:
                actions.append(
                    InterventionAction(
                        level="micro",
                        dimension=dim,
                        action=f"auto_format_remove_unused: {dim} entropy at {entropy:.2f}",
                        priority=0.4,
                    )
                )

        actions.sort(key=lambda a: a.priority, reverse=True)
        return actions


@dataclass
class NegentropySuggestion:
    source: str
    pattern: str
    target_dimension: str
    expected_reduction: float


class NegentropyImporter:
    DEMON_CAPACITY_RATE = 0.3

    PATTERNS: dict[str, list[NegentropySuggestion]] = {
        "code_complexity": [
            NegentropySuggestion("standard", "linting_rules", "code_complexity", 0.15),
            NegentropySuggestion("standard", "design_patterns", "code_complexity", 0.20),
        ],
        "dependency_count": [
            NegentropySuggestion("standard", "dependency_audit", "dependency_count", 0.25),
            NegentropySuggestion("standard", "monorepo_consolidation", "dependency_count", 0.15),
        ],
        "config_drift": [
            NegentropySuggestion("standard", "config_schema_validation", "config_drift", 0.20),
            NegentropySuggestion("standard", "infrastructure_as_code", "config_drift", 0.30),
        ],
        "test_coverage": [
            NegentropySuggestion("standard", "coverage_gates", "test_coverage", 0.20),
            NegentropySuggestion("standard", "mutation_testing", "test_coverage", 0.15),
        ],
        "doc_freshness": [
            NegentropySuggestion("standard", "doc_gen_pipeline", "doc_freshness", 0.25),
            NegentropySuggestion("standard", "adr_templates", "doc_freshness", 0.10),
        ],
        "api_stability": [
            NegentropySuggestion("standard", "api_versioning", "api_stability", 0.20),
            NegentropySuggestion("standard", "contract_testing", "api_stability", 0.25),
        ],
    }

    def import_negentropy(
        self, current_entropy_rate: float
    ) -> list[NegentropySuggestion]:
        if current_entropy_rate <= self.DEMON_CAPACITY_RATE:
            return []
        suggestions: list[NegentropySuggestion] = []
        for dim, patterns in self.PATTERNS.items():
            suggestions.extend(patterns)
        suggestions.sort(key=lambda s: s.expected_reduction, reverse=True)
        return suggestions


class EntropyAwareDesign(BaseInventionEngine):
    name = "EntropyAwareDesign"
    invention_id = "SCI-003"
    operator = "S()"
    formula = "S(system) = Σ w_d * H_d → S > S_warn → Maxwell's demon"
    category = "SCI"
    description = (
        "Measure system entropy and trigger anti-entropy mechanisms when thresholds exceeded"
    )

    def __init__(self) -> None:
        self.measurer = EntropyMeasurer()
        self.budget = EntropyBudget()
        self.demon = MaxwellsDemon()
        self.negentropy_importer = NegentropyImporter()

    def execute(self, context: dict[str, Any]) -> InventionResult:
        system_data = context.get("system_data", {})
        if not system_data:
            logger.warning("no_system_data_provided")
            return InventionResult(
                output={"error": "no system_data in context"},
                confidence=ConfidenceLevel.UNCERTAIN,
                invention_id=self.invention_id,
            )

        entropy_dimensions = self.measurer.measure(system_data)

        total_entropy = sum(
            DIMENSION_WEIGHTS.get(dim, 0.0) * entropy_dimensions.get(dim, 0.0)
            for dim in ENTROPY_DIMENSIONS
        )

        budget_status = self.budget.check(total_entropy)

        interventions: list[dict[str, Any]] = []
        if budget_status != BudgetStatus.HEALTHY:
            actions = self.demon.intervene(entropy_dimensions, budget_status)
            interventions = [
                {
                    "level": a.level,
                    "dimension": a.dimension,
                    "action": a.action,
                    "priority": a.priority,
                }
                for a in actions
            ]

        entropy_rate = context.get("entropy_rate", 0.0)
        negentropy_suggestions: list[dict[str, Any]] = []
        if entropy_rate > self.negentropy_importer.DEMON_CAPACITY_RATE:
            suggestions = self.negentropy_importer.import_negentropy(entropy_rate)
            negentropy_suggestions = [
                {
                    "source": s.source,
                    "pattern": s.pattern,
                    "target_dimension": s.target_dimension,
                    "expected_reduction": s.expected_reduction,
                }
                for s in suggestions
            ]

        confidence = ConfidenceLevel.VERIFIED
        if not entropy_dimensions:
            confidence = ConfidenceLevel.UNCERTAIN
        elif budget_status == BudgetStatus.CRITICAL:
            confidence = ConfidenceLevel.RESEARCHED

        return InventionResult(
            output={
                "total_entropy": total_entropy,
                "entropy_dimensions": entropy_dimensions,
                "budget_status": budget_status.value,
                "s_warn": self.budget.s_warn,
                "s_crit": self.budget.s_crit,
                "interventions": interventions,
                "negentropy_suggestions": negentropy_suggestions,
            },
            confidence=confidence,
            synergy_detected=self.get_synergy_partners(),
            invention_id=self.invention_id,
        )

    def validate(self, result: InventionResult) -> bool:
        if not result.output:
            return False
        required_keys = {"total_entropy", "entropy_dimensions", "budget_status"}
        if not required_keys.issubset(result.output.keys()):
            return False
        total = result.output.get("total_entropy", -1.0)
        if not isinstance(total, (int, float)) or total < 0 or total > self.budget.s_max:
            return False
        dims = result.output.get("entropy_dimensions", {})
        if not isinstance(dims, dict):
            return False
        for dim in ENTROPY_DIMENSIONS:
            val = dims.get(dim)
            if val is not None and (not isinstance(val, (int, float)) or val < 0 or val > 1.0):
                return False
        return True

    def get_synergy_partners(self) -> list[str]:
        return ["SCI-001", "SCI-002", "EWF-005"]
