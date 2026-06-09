from __future__ import annotations

import math
import structlog
from dataclasses import dataclass, field
from typing import Any, Callable

from .base_engine import BaseInventionEngine
from .base_invention_engine import InventionResult, ConfidenceLevel

logger = structlog.get_logger()


@dataclass
class NavigationResult:
    path: list[list[float]]
    final_position: list[float]
    final_potential: float
    converged: bool


@dataclass
class TunnelResult:
    tunneled: bool
    new_position: list[float]
    new_potential: float
    probability: float


@dataclass
class InfluenceFunction:
    center: list[float]
    amplitude: float
    sigma: float
    skill_name: str

    def evaluate(self, position: list[float]) -> float:
        dist_sq = sum((p - c) ** 2 for p, c in zip(position, self.center))
        return -self.amplitude * math.exp(-dist_sq / (2 * self.sigma ** 2))

    def gradient(self, position: list[float]) -> list[float]:
        dist_sq = sum((p - c) ** 2 for p, c in zip(position, self.center))
        coeff = self.amplitude * math.exp(-dist_sq / (2 * self.sigma ** 2)) / (self.sigma ** 2)
        return [coeff * (p - c) for p, c in zip(position, self.center)]


class InfluenceFunctionConstructor:
    def __init__(self, default_amplitude: float = 1.0, default_sigma: float = 1.0) -> None:
        self._default_amplitude = default_amplitude
        self._default_sigma = default_sigma

    def construct(self, skills: list[dict[str, Any]]) -> list[InfluenceFunction]:
        influence_functions: list[InfluenceFunction] = []
        for idx, skill in enumerate(skills):
            center = skill.get("center", [float(idx)])
            amplitude = skill.get("amplitude", self._default_amplitude)
            sigma = skill.get("sigma", self._default_sigma)
            name = skill.get("name", f"skill_{idx}")
            influence_functions.append(
                InfluenceFunction(center=center, amplitude=amplitude, sigma=sigma, skill_name=name)
            )
        logger.info(
            "influence_functions_constructed",
            count=len(influence_functions),
            skills=[s.get("name", f"skill_{i}") for i, s in enumerate(skills)],
        )
        return influence_functions


class PotentialFieldComputer:
    def __init__(self, repulsion_strength: float = 0.01) -> None:
        self._repulsion_strength = repulsion_strength

    def compute(self, position: list[float], influence_functions: list[InfluenceFunction]) -> float:
        potential = 0.0
        for inf_fn in influence_functions:
            potential += inf_fn.evaluate(position)
        if len(influence_functions) > 1:
            for i in range(len(influence_functions)):
                for j in range(i + 1, len(influence_functions)):
                    dist_sq = sum(
                        (a - b) ** 2
                        for a, b in zip(influence_functions[i].center, influence_functions[j].center)
                    )
                    potential += self._repulsion_strength / (math.sqrt(dist_sq) + 1e-8)
        return potential

    def gradient(self, position: list[float], influence_functions: list[InfluenceFunction]) -> list[float]:
        if not influence_functions:
            return [0.0] * len(position)
        dim = len(position)
        grad = [0.0] * dim
        for inf_fn in influence_functions:
            inf_grad = inf_fn.gradient(position)
            for d in range(dim):
                grad[d] += inf_grad[d]
        return grad


class GradientDescentNavigator:
    def __init__(self, convergence_threshold: float = 1e-6) -> None:
        self._convergence_threshold = convergence_threshold

    def navigate(
        self,
        start_position: list[float],
        field: PotentialFieldComputer,
        influence_functions: list[InfluenceFunction],
        steps: int = 50,
        learning_rate: float = 0.1,
    ) -> NavigationResult:
        position = list(start_position)
        path = [list(position)]
        current_potential = field.compute(position, influence_functions)
        converged = False

        for _ in range(steps):
            grad = field.gradient(position, influence_functions)
            new_position = [p - learning_rate * g for p, g in zip(position, grad)]
            new_potential = field.compute(new_position, influence_functions)
            delta = abs(new_potential - current_potential)
            position = new_position
            current_potential = new_potential
            path.append(list(position))
            if delta < self._convergence_threshold:
                converged = True
                break

        logger.info(
            "gradient_descent_complete",
            steps_taken=len(path) - 1,
            converged=converged,
            final_potential=current_potential,
        )
        return NavigationResult(
            path=path,
            final_position=list(position),
            final_potential=current_potential,
            converged=converged,
        )


class QuantumTunneling:
    def __init__(self, jump_scale: float = 1.0) -> None:
        self._jump_scale = jump_scale

    def tunnel(
        self,
        current_potential: float,
        barrier_height: float,
        temperature: float = 1.0,
    ) -> TunnelResult:
        delta_v = barrier_height - current_potential
        if delta_v <= 0:
            return TunnelResult(
                tunneled=True,
                new_position=[0.0],
                new_potential=current_potential,
                probability=1.0,
            )
        probability = math.exp(-delta_v / max(temperature, 1e-8))
        tunneled = probability > 0.5
        new_potential = current_potential
        new_position = [0.0]
        if tunneled:
            jump = self._jump_scale * math.sqrt(delta_v)
            new_potential = current_potential - delta_v * 0.5
            new_position = [jump]
        logger.info(
            "quantum_tunneling_attempt",
            tunneled=tunneled,
            probability=probability,
            delta_v=delta_v,
        )
        return TunnelResult(
            tunneled=tunneled,
            new_position=new_position,
            new_potential=new_potential,
            probability=probability,
        )


class FieldTheoreticInvention(BaseInventionEngine):
    name = "FieldTheoreticInvention"
    invention_id = "SCI-004"
    operator = "𝔽()"
    formula = "𝔽(skills) → V(x) = Σ Vᵢ(x) → ∇V → tunnel(ΔV)"
    category = "SCI"
    description = "Model invention space as potential field with gradient descent navigation and quantum tunneling"

    def __init__(self) -> None:
        self._influence_constructor = InfluenceFunctionConstructor()
        self._field_computer = PotentialFieldComputer()
        self._navigator = GradientDescentNavigator()
        self._tunneling = QuantumTunneling()

    def execute(self, context: dict[str, Any]) -> InventionResult:
        skills = context.get("skills", [])
        if not skills:
            logger.warning("no_skills_provided", invention_id=self.invention_id)
            return InventionResult(
                output={},
                confidence=ConfidenceLevel.UNCERTAIN,
                invention_id=self.invention_id,
            )

        influence_functions = self._influence_constructor.construct(skills)

        start_position = context.get("start_position", [0.0] * len(influence_functions[0].center))
        steps = context.get("steps", 50)
        learning_rate = context.get("learning_rate", 0.1)

        nav_result = self._navigator.navigate(
            start_position=start_position,
            field=self._field_computer,
            influence_functions=influence_functions,
            steps=steps,
            learning_rate=learning_rate,
        )

        tunnel_result = None
        if not nav_result.converged:
            barrier_height = context.get("barrier_height", nav_result.final_potential + 1.0)
            temperature = context.get("temperature", 1.0)
            tunnel_result = self._tunneling.tunnel(
                current_potential=nav_result.final_potential,
                barrier_height=barrier_height,
                temperature=temperature,
            )
            if tunnel_result.tunneled:
                combined_position = [
                    p + t
                    for p, t in zip(nav_result.final_position, tunnel_result.new_position)
                ]
                nav_result = self._navigator.navigate(
                    start_position=combined_position,
                    field=self._field_computer,
                    influence_functions=influence_functions,
                    steps=steps,
                    learning_rate=learning_rate,
                )

        output = {
            "influence_functions": [
                {"name": fn.skill_name, "center": fn.center, "amplitude": fn.amplitude, "sigma": fn.sigma}
                for fn in influence_functions
            ],
            "navigation": {
                "path_length": len(nav_result.path),
                "final_position": nav_result.final_position,
                "final_potential": nav_result.final_potential,
                "converged": nav_result.converged,
            },
            "tunneling": {
                "attempted": tunnel_result is not None,
                "tunneled": tunnel_result.tunneled if tunnel_result else False,
                "probability": tunnel_result.probability if tunnel_result else 0.0,
            }
            if tunnel_result
            else {"attempted": False, "tunneled": False, "probability": 0.0},
        }

        confidence = ConfidenceLevel.VERIFIED if nav_result.converged else ConfidenceLevel.INFERRED

        return InventionResult(
            output=output,
            confidence=confidence,
            synergy_detected=self.get_synergy_partners(),
            invention_id=self.invention_id,
            metadata={"operator": self.operator, "formula": self.formula},
        )

    def validate(self, result: InventionResult) -> bool:
        if not result.output:
            return False
        if result.confidence == ConfidenceLevel.UNCERTAIN:
            return False
        nav = result.output.get("navigation", {})
        if not nav.get("final_position"):
            return False
        return True

    def get_synergy_partners(self) -> list[str]:
        return ["SCI-005", "EWF-003", "SCI-001"]
