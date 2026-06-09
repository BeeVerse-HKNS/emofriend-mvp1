from __future__ import annotations

import math
import structlog
from dataclasses import dataclass, field
from typing import Any

from .base_engine import BaseInventionEngine
from .base_invention_engine import ConfidenceLevel, InventionResult

logger = structlog.get_logger()

MEADOWS_LEVERAGE_POINTS: dict[int, tuple[str, float, str]] = {
    1: ("paradigm", 1.0, "Power to transcend paradigms"),
    2: ("system_goals", 0.95, "Goals of the system"),
    3: ("information_flows", 0.9, "Power to add, change, or enhance feedback"),
    4: ("self_organization", 0.85, "Power to add, change, or evolve system structure"),
    5: ("rules", 0.8, "Rules of the system"),
    6: ("information_feedbacks", 0.75, "Information feedback loops"),
    7: ("regulating_negative_feedbacks", 0.7, "Regulating negative feedback loops"),
    8: ("positive_feedbacks", 0.65, "Positive feedback loops driving growth"),
    9: ("delays", 0.6, "Length of delays relative to system change rates"),
    10: ("stock_and_flow_structures", 0.5, "Structure of material stocks and flows"),
    11: ("buffers", 0.4, "Sizes of buffers and stabilizing stocks"),
    12: ("constants_parameters", 0.3, "Constants, parameters, numbers"),
}


@dataclass
class LeveragePoint:
    level: int
    name: str
    effectiveness: float
    description: str


@dataclass
class InterventionResult:
    intervention: dict
    emergence_score: float
    cost: float
    efficiency: float
    leverage_level: int


@dataclass
class SustainabilityReport:
    is_sustainable: bool
    durability_score: float
    decay_rate: float
    self_reinforcing: bool


class LeveragePointClassifier:
    _keyword_map: dict[int, list[str]] = {
        1: ["paradigm", "worldview", "mindset", "philosophy", "belief", "ontology"],
        2: ["goal", "objective", "purpose", "mission", "vision", "target"],
        3: ["information", "data", "feedback", "signal", "sensor", "monitor"],
        4: ["self-organize", "evolve", "adapt", "emerge", "autopoiesis", "co-evolve"],
        5: ["rule", "policy", "regulation", "law", "constraint", "governance"],
        6: ["feedback_loop", "circular", "reinforcing", "balancing", "loop", "cycle"],
        7: ["regulate", "control", "dampen", "stabilize", "governor", "thermostat"],
        8: ["amplify", "accelerate", "reinforce", "grow", "snowball", "compound"],
        9: ["delay", "lag", "latency", "time_constant", "response_time", "lead_time"],
        10: ["stock", "flow", "pipeline", "throughput", "capacity", "infrastructure"],
        11: ["buffer", "reserve", "surplus", "safety_stock", "slack", "cushion"],
        12: ["parameter", "constant", "coefficient", "threshold", "weight", "tuning"],
    }

    def classify(self, intervention: dict) -> LeveragePoint:
        text = " ".join(str(v).lower() for v in intervention.values())
        best_level = 12
        best_score = 0
        for level, keywords in self._keyword_map.items():
            score = sum(1 for kw in keywords if kw in text)
            if score > best_score:
                best_score = score
                best_level = level
        if best_score == 0:
            best_level = 12
        meta = MEADOWS_LEVERAGE_POINTS[best_level]
        return LeveragePoint(
            level=best_level,
            name=meta[0],
            effectiveness=meta[1],
            description=meta[2],
        )


class EmergenceMeasure:
    def measure(self, system_state: dict, intervention: dict) -> float:
        f_with = self._evaluate(system_state, intervention)
        f_without = self._evaluate(system_state, {})
        delta = abs(f_with - f_without)
        magnitude = self._intervention_magnitude(intervention)
        if magnitude < 1e-12:
            return 0.0
        return delta / magnitude

    def _evaluate(self, system_state: dict, intervention: dict) -> float:
        base = sum(float(v) for v in system_state.values() if isinstance(v, (int, float)))
        intervention_effect = 0.0
        for key, val in intervention.items():
            if isinstance(val, (int, float)):
                state_val = system_state.get(key, 0.0)
                if isinstance(state_val, (int, float)):
                    intervention_effect += val * (1.0 + 0.1 * abs(state_val))
                else:
                    intervention_effect += val
            elif isinstance(val, str):
                intervention_effect += 0.5
        synergy = 0.0
        int_keys = [k for k, v in intervention.items() if isinstance(v, (int, float))]
        for i, ki in enumerate(int_keys):
            for kj in int_keys[i + 1 :]:
                vi = float(intervention[ki])
                vj = float(intervention[kj])
                synergy += 0.05 * vi * vj
        return base + intervention_effect + synergy

    def _intervention_magnitude(self, intervention: dict) -> float:
        if not intervention:
            return 1e-12
        total = 0.0
        for val in intervention.values():
            if isinstance(val, (int, float)):
                total += float(val) ** 2
            else:
                total += 1.0
        return math.sqrt(total)


class MinimalInterventionOptimizer:
    def __init__(self) -> None:
        self._emergence = EmergenceMeasure()
        self._classifier = LeveragePointClassifier()

    def optimize(
        self,
        system_state: dict,
        threshold: float = 0.5,
        candidates: list | None = None,
    ) -> InterventionResult:
        if candidates is None:
            candidates = self._generate_candidates(system_state)

        best: InterventionResult | None = None
        for candidate in candidates:
            emergence = self._emergence.measure(system_state, candidate)
            if emergence < threshold:
                continue
            cost = self._compute_cost(candidate)
            lp = self._classifier.classify(candidate)
            efficiency = emergence / cost if cost > 1e-12 else float("inf")
            result = InterventionResult(
                intervention=candidate,
                emergence_score=emergence,
                cost=cost,
                efficiency=efficiency,
                leverage_level=lp.level,
            )
            if best is None or efficiency > best.efficiency:
                best = result

        if best is None:
            fallback = candidates[0] if candidates else {}
            emergence = self._emergence.measure(system_state, fallback)
            cost = self._compute_cost(fallback)
            lp = self._classifier.classify(fallback)
            efficiency = emergence / cost if cost > 1e-12 else 0.0
            best = InterventionResult(
                intervention=fallback,
                emergence_score=emergence,
                cost=cost,
                efficiency=efficiency,
                leverage_level=lp.level,
            )

        return best

    def _generate_candidates(self, system_state: dict) -> list[dict]:
        candidates: list[dict] = []
        keys = [k for k, v in system_state.items() if isinstance(v, (int, float))]
        for key in keys:
            val = float(system_state[key])
            candidates.append({key: val * 0.01})
            candidates.append({key: val * -0.01})
        for i, ki in enumerate(keys):
            for kj in keys[i + 1 :]:
                vi = float(system_state[ki]) * 0.01
                vj = float(system_state[kj]) * 0.01
                candidates.append({ki: vi, kj: vj})
        return candidates

    def _compute_cost(self, intervention: dict) -> float:
        total = 0.0
        for val in intervention.values():
            if isinstance(val, (int, float)):
                total += abs(float(val))
            else:
                total += 1.0
        return total


class SustainabilityValidator:
    def validate(
        self, intervention_result: InterventionResult, time_horizon: int = 10
    ) -> SustainabilityReport:
        emergence = intervention_result.emergence_score
        efficiency = intervention_result.efficiency
        leverage = intervention_result.leverage_level

        leverage_factor = (13 - leverage) / 12.0
        durability = min(1.0, emergence * efficiency * leverage_factor)
        decay_rate = max(0.0, 1.0 - durability) / time_horizon

        durability_over_horizon = durability * math.exp(-decay_rate * time_horizon)
        is_sustainable = durability_over_horizon >= 0.5

        self_reinforcing = (
            leverage <= 4
            and emergence > 0.6
            and efficiency > 0.5
        )

        return SustainabilityReport(
            is_sustainable=is_sustainable,
            durability_score=round(durability, 6),
            decay_rate=round(decay_rate, 6),
            self_reinforcing=self_reinforcing,
        )


class DaoEmergenceFramework(BaseInventionEngine):
    name = "DaoEmergenceFramework"
    invention_id = "EWF-004"
    operator = "log(sq(S)) + K/R"
    formula = "log(sq(S)) + K/R → argmin|I| subject to E(I) ≥ θ"
    category = "EWF"
    description = "Find minimal interventions that catalyze self-organizing emergence"

    def __init__(self) -> None:
        self._classifier = LeveragePointClassifier()
        self._optimizer = MinimalInterventionOptimizer()
        self._validator = SustainabilityValidator()
        self._emergence = EmergenceMeasure()

    def execute(self, context: dict[str, Any]) -> InventionResult:
        try:
            system_state = context.get("system_state", {})
            if not system_state:
                logger.warning("no_system_state", invention_id=self.invention_id)
                return InventionResult(
                    output={},
                    confidence=ConfidenceLevel.UNCERTAIN,
                    invention_id=self.invention_id,
                )

            threshold = context.get("threshold", 0.5)
            candidates = context.get("candidates", None)
            time_horizon = context.get("time_horizon", 10)

            available_interventions = candidates or self._optimizer._generate_candidates(system_state)
            leverage_points = []
            for intervention in available_interventions:
                lp = self._classifier.classify(intervention)
                leverage_points.append(
                    {
                        "level": lp.level,
                        "name": lp.name,
                        "effectiveness": lp.effectiveness,
                        "description": lp.description,
                    }
                )

            optimal = self._optimizer.optimize(
                system_state=system_state,
                threshold=threshold,
                candidates=candidates,
            )

            sustainability = self._validator.validate(optimal, time_horizon=time_horizon)

            lp_result = self._classifier.classify(optimal.intervention)

            s_score = optimal.emergence_score
            k_ratio = optimal.efficiency
            operator_value = 0.0
            if s_score > 0:
                operator_value = math.log(s_score ** 2 + 1e-12) + k_ratio

            output = {
                "optimal_intervention": optimal.intervention,
                "emergence_score": optimal.emergence_score,
                "cost": optimal.cost,
                "efficiency": optimal.efficiency,
                "leverage_level": optimal.leverage_level,
                "leverage_point": {
                    "level": lp_result.level,
                    "name": lp_result.name,
                    "effectiveness": lp_result.effectiveness,
                    "description": lp_result.description,
                },
                "sustainability": {
                    "is_sustainable": sustainability.is_sustainable,
                    "durability_score": sustainability.durability_score,
                    "decay_rate": sustainability.decay_rate,
                    "self_reinforcing": sustainability.self_reinforcing,
                },
                "operator_value": round(operator_value, 6),
                "classified_leverage_points": leverage_points,
            }

            if sustainability.is_sustainable and optimal.efficiency > 0.5:
                confidence = ConfidenceLevel.VERIFIED
            elif sustainability.is_sustainable or optimal.emergence_score >= threshold:
                confidence = ConfidenceLevel.RESEARCHED
            elif optimal.emergence_score > 0:
                confidence = ConfidenceLevel.INFERRED
            else:
                confidence = ConfidenceLevel.UNCERTAIN

            logger.info(
                "dao_emergence_executed",
                invention_id=self.invention_id,
                emergence_score=optimal.emergence_score,
                efficiency=optimal.efficiency,
                leverage_level=optimal.leverage_level,
                sustainable=sustainability.is_sustainable,
            )

            return InventionResult(
                output=output,
                confidence=confidence,
                synergy_detected=self.get_synergy_partners(),
                metadata={
                    "formula": self.formula,
                    "operator": self.operator,
                    "category": self.category,
                },
                invention_id=self.invention_id,
            )

        except Exception as exc:
            logger.error("dao_emergence_failed", invention_id=self.invention_id, error=str(exc))
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
        if "optimal_intervention" not in result.output:
            return False
        emergence = result.output.get("emergence_score", 0.0)
        if emergence <= 0.0:
            return False
        sustainability = result.output.get("sustainability", {})
        if not sustainability.get("is_sustainable", False):
            return False
        return True

    def get_synergy_partners(self) -> list[str]:
        return ["EWF-001", "EWF-003", "SCI-002"]
