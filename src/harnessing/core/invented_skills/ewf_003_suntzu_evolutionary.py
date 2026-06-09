from __future__ import annotations

import math
import structlog
from dataclasses import dataclass, field
from typing import Any

from .base_engine import BaseInventionEngine
from .base_invention_engine import ConfidenceLevel, InventionResult

logger = structlog.get_logger()

SUNTZU_FACTORS = {
    "dao": "Moral Law",
    "tian": "Heaven",
    "di": "Earth",
    "jiang": "Commander",
    "fa": "Method",
}


@dataclass
class CoevolutionResult:
    rounds_completed: int
    final_strategies: dict[str, float]
    cumulative_advantage: float
    conflict_avoided: float


class FiveFactorFitnessLandscape:
    def __init__(self) -> None:
        self._weights: dict[str, float] = {
            "dao": 0.30,
            "tian": 0.20,
            "di": 0.20,
            "jiang": 0.15,
            "fa": 0.15,
        }

    def compute_fitness(self, factors: dict[str, float]) -> float:
        total = 0.0
        for key, weight in self._weights.items():
            val = factors.get(key, 0.0)
            total += weight * val
        return max(0.0, min(1.0, total))

    def get_gradient(self, factors: dict[str, float]) -> dict[str, float]:
        gradient: dict[str, float] = {}
        eps = 1e-6
        base = self.compute_fitness(factors)
        for key in self._weights:
            perturbed = dict(factors)
            perturbed[key] = perturbed.get(key, 0.0) + eps
            grad_val = (self.compute_fitness(perturbed) - base) / eps
            gradient[key] = grad_val
        return gradient


class ReplicatorDynamics:
    def evolve(self, population: dict[str, float], fitnesses: dict[str, float], dt: float = 0.1) -> dict[str, float]:
        total_pop = sum(population.values())
        if total_pop <= 0.0:
            return dict(population)
        avg_fitness = sum(population[s] * fitnesses.get(s, 0.0) for s in population) / total_pop
        updated: dict[str, float] = {}
        for strategy, proportion in population.items():
            f_i = fitnesses.get(strategy, 0.0)
            x_i = proportion / total_pop
            dx = x_i * (f_i - avg_fitness) * dt
            new_val = x_i + dx
            updated[strategy] = max(0.0, new_val)
        total_updated = sum(updated.values())
        if total_updated > 0.0:
            for s in updated:
                updated[s] /= total_updated
        return updated


class ConflictCostTerm:
    def compute(self, population: dict[str, float], conflict_matrix: list[list[float]]) -> float:
        strategies = list(population.keys())
        cost = 0.0
        for i, s_i in enumerate(strategies):
            for j, s_j in enumerate(strategies):
                if i < len(conflict_matrix) and j < len(conflict_matrix[i]):
                    g_ij = conflict_matrix[i][j]
                else:
                    g_ij = 0.0
                cost += g_ij * population[s_i] * population[s_j]
        return cost


class CoevolutionarySimulator:
    def __init__(self) -> None:
        self._landscape = FiveFactorFitnessLandscape()
        self._replicator = ReplicatorDynamics()
        self._conflict = ConflictCostTerm()

    def simulate(
        self,
        initial_strategies: dict[str, float],
        rounds: int = 10,
        conflict_matrix: list[list[float] | None] | None = None,
        factors: dict[str, float] | None = None,
    ) -> CoevolutionResult:
        strategies = dict(initial_strategies)
        cumulative_advantage = 0.0
        conflict_avoided = 0.0
        default_factors: dict[str, float] = factors if factors is not None else {k: 0.5 for k in SUNTZU_FACTORS}
        base_fitness = self._landscape.compute_fitness(default_factors)
        n = len(strategies)
        if conflict_matrix is None:
            conflict_matrix = [[0.0] * n for _ in range(n)]
        for r in range(rounds):
            fitnesses: dict[str, float] = {}
            for s in strategies:
                strategy_factors = dict(default_factors)
                strategy_factors["jiang"] = strategies.get(s, 0.5)
                fitnesses[s] = self._landscape.compute_fitness(strategy_factors)
            pre_conflict = self._conflict.compute(strategies, conflict_matrix)
            strategies = self._replicator.evolve(strategies, fitnesses, dt=0.1)
            post_conflict = self._conflict.compute(strategies, conflict_matrix)
            conflict_avoided += max(0.0, pre_conflict - post_conflict)
            current_fitness = sum(strategies[s] * fitnesses.get(s, 0.0) for s in strategies)
            advantage = current_fitness - base_fitness
            cumulative_advantage += math.exp(advantage) if advantage > 0 else advantage
        return CoevolutionResult(
            rounds_completed=rounds,
            final_strategies=strategies,
            cumulative_advantage=cumulative_advantage,
            conflict_avoided=conflict_avoided,
        )


class SunTzuEvolutionaryStrategy(BaseInventionEngine):
    name = "SunTzuEvolutionaryStrategy"
    invention_id = "EWF-003"
    operator = "(P × R) - G + E^t"
    formula = "(P × R) - G + E^t → replicator_dynamics → coevolution"
    category = "EWF"
    description = "Evolutionary game theory with Sun Tzu conflict minimization for strategic advantage"

    def __init__(self) -> None:
        self._landscape = FiveFactorFitnessLandscape()
        self._simulator = CoevolutionarySimulator()
        self._conflict = ConflictCostTerm()

    def execute(self, context: dict[str, Any]) -> InventionResult:
        try:
            competition = context.get("competition", {})
            strategies = competition.get("strategies", {"cooperate": 0.5, "defect": 0.3, "adapt": 0.2})
            rounds = competition.get("rounds", 10)
            conflict_matrix = competition.get("conflict_matrix", None)
            factors_input = competition.get("factors", None)

            factors: dict[str, float] = {}
            if factors_input is not None:
                factors = {k: float(v) for k, v in factors_input.items() if k in SUNTZU_FACTORS}
            for key in SUNTZU_FACTORS:
                if key not in factors:
                    factors[key] = 0.5

            fitness = self._landscape.compute_fitness(factors)
            gradient = self._landscape.get_gradient(factors)

            coevolution_result = self._simulator.simulate(
                initial_strategies=strategies,
                rounds=rounds,
                conflict_matrix=conflict_matrix,
                factors=factors,
            )

            n_strategies = len(coevolution_result.final_strategies)
            if conflict_matrix is None:
                conflict_matrix_for_cost = [[0.0] * n_strategies for _ in range(n_strategies)]
            else:
                conflict_matrix_for_cost = conflict_matrix
            final_conflict = self._conflict.compute(coevolution_result.final_strategies, conflict_matrix_for_cost)

            dominant = max(coevolution_result.final_strategies, key=coevolution_result.final_strategies.get) if coevolution_result.final_strategies else ""

            recommendations: list[str] = []
            if coevolution_result.conflict_avoided > 0.0:
                recommendations.append("minimize_direct_conflict")
            if fitness > 0.7:
                recommendations.append("exploit_positional_advantage")
            if gradient.get("dao", 0.0) > gradient.get("fa", 0.0):
                recommendations.append("prioritize_moral_law_over_method")
            if coevolution_result.cumulative_advantage > 0.0:
                recommendations.append("sustain_cooperative_dynamics")
            if dominant:
                recommendations.append(f"converge_on_{dominant}_strategy")

            output = {
                "fitness": fitness,
                "gradient": gradient,
                "coevolution": {
                    "rounds_completed": coevolution_result.rounds_completed,
                    "final_strategies": coevolution_result.final_strategies,
                    "cumulative_advantage": coevolution_result.cumulative_advantage,
                    "conflict_avoided": coevolution_result.conflict_avoided,
                },
                "final_conflict_cost": final_conflict,
                "dominant_strategy": dominant,
                "recommendations": recommendations,
                "five_factors": {SUNTZU_FACTORS[k]: v for k, v in factors.items()},
            }

            confidence = (
                ConfidenceLevel.VERIFIED
                if fitness > 0.7 and coevolution_result.conflict_avoided > 0.0
                else ConfidenceLevel.INFERRED
                if fitness > 0.4
                else ConfidenceLevel.RESEARCHED
            )

            logger.info(
                "suntzu_evolutionary_complete",
                invention_id=self.invention_id,
                fitness=fitness,
                dominant=dominant,
                conflict_avoided=coevolution_result.conflict_avoided,
            )

            return InventionResult(
                output=output,
                confidence=confidence,
                synergy_detected=self.get_synergy_partners(),
                invention_id=self.invention_id,
                metadata={"formula": self.formula, "operator": self.operator},
            )
        except Exception as exc:
            logger.error("suntzu_evolutionary_failed", invention_id=self.invention_id, error=str(exc))
            return InventionResult(
                output={"status": "error", "error": str(exc)},
                confidence=ConfidenceLevel.UNCERTAIN,
                invention_id=self.invention_id,
            )

    def validate(self, result: InventionResult) -> bool:
        if not result.output:
            return False
        if result.confidence == ConfidenceLevel.UNCERTAIN:
            return False
        if "error" in result.output:
            return False
        fitness = result.output.get("fitness", 0.0)
        if fitness < 0.0 or fitness > 1.0:
            return False
        coevolution = result.output.get("coevolution", {})
        if coevolution.get("rounds_completed", 0) <= 0:
            return False
        final_strategies = coevolution.get("final_strategies", {})
        if not final_strategies:
            return False
        total = sum(final_strategies.values())
        if total <= 0.0:
            return False
        return True

    def get_synergy_partners(self) -> list[str]:
        return ["EWF-005", "EWF-004", "SCI-004"]
