from __future__ import annotations

import structlog
from dataclasses import dataclass, field
from typing import Any

from .base_engine import BaseInventionEngine
from .base_invention_engine import ConfidenceLevel, InventionResult

logger = structlog.get_logger()


@dataclass
class PhaseTransitionResult:
    detected: bool
    order_parameter: float
    critical_threshold: float
    emergence_type: str


class InteractionMatrixComputer:
    def __init__(self) -> None:
        self._matrix: list[list[float]] = []

    def compute_matrix(self, skills: list[dict[str, Any]]) -> list[list[float]]:
        n = len(skills)
        if n < 2:
            self._matrix = [[1.0]] if n == 1 else []
            return self._matrix
        self._matrix = [[0.0] * n for _ in range(n)]
        for i in range(n):
            self._matrix[i][i] = 1.0
            for j in range(i + 1, n):
                interaction = self._compute_pairwise(skills[i], skills[j])
                self._matrix[i][j] = interaction
                self._matrix[j][i] = interaction
        return self._matrix

    def _compute_pairwise(self, skill_a: dict[str, Any], skill_b: dict[str, Any]) -> float:
        cats_a = set(skill_a.get("categories", []))
        cats_b = set(skill_b.get("categories", []))
        overlap = len(cats_a & cats_b)
        union = len(cats_a | cats_b)
        jaccard = overlap / union if union > 0 else 0.0
        strength_a = skill_a.get("strength", 0.5)
        strength_b = skill_b.get("strength", 0.5)
        synergy = skill_a.get("synergy_partners", [])
        id_b = skill_b.get("id", "")
        bonus = 0.2 if id_b in synergy else 0.0
        interaction = (jaccard * 0.5 + strength_a * strength_b * 0.3 + bonus) / 0.8
        return min(max(interaction, 0.0), 1.0)


class OrderParameterCalculator:
    def calculate(self, interaction_matrix: list[list[float]]) -> float:
        n = len(interaction_matrix)
        if n < 2:
            return 0.0
        total = 0.0
        count = 0
        for i in range(n):
            for j in range(i + 1, n):
                total += interaction_matrix[i][j]
                count += 1
        return total / count if count > 0 else 0.0


class PhaseTransitionDetector:
    def __init__(self, critical_threshold: float = 0.6) -> None:
        self.critical_threshold = critical_threshold

    def detect(self, order_parameter: float) -> PhaseTransitionResult:
        detected = order_parameter > self.critical_threshold
        if detected:
            if order_parameter > 0.9:
                emergence_type = "strong_emergence"
            elif order_parameter > 0.75:
                emergence_type = "moderate_emergence"
            else:
                emergence_type = "weak_emergence"
        else:
            emergence_type = "no_emergence"
        return PhaseTransitionResult(
            detected=detected,
            order_parameter=order_parameter,
            critical_threshold=self.critical_threshold,
            emergence_type=emergence_type,
        )


class EmergenceCrystallizer:
    def crystallize(
        self, skills: list[dict[str, Any]], transition_result: PhaseTransitionResult
    ) -> dict[str, Any]:
        skill_ids = [s.get("id", f"skill_{i}") for i, s in enumerate(skills)]
        skill_names = [s.get("name", f"Skill-{i}") for i, s in enumerate(skills)]
        combined_categories: set[str] = set()
        for s in skills:
            combined_categories.update(s.get("categories", []))
        new_id = f"EMERGENT-{'-'.join(skill_ids)}"
        new_name = f"Emergent({'+'.join(skill_names)})"
        return {
            "id": new_id,
            "name": new_name,
            "source_skills": skill_ids,
            "emergence_type": transition_result.emergence_type,
            "order_parameter": transition_result.order_parameter,
            "categories": list(combined_categories),
            "is_emergent": True,
            "crystallized_at": transition_result.order_parameter,
        }


class EmergenceDetector(BaseInventionEngine):
    name = "EmergenceDetector"
    invention_id = "SCI-002"
    operator = "Ξ"
    formula = "Ξ(skills) → φ > φc → crystallize(emergent)"
    category = "SCI"
    description = "Detect when skill interactions produce emergent capabilities not present in any individual component"

    def __init__(self, critical_threshold: float = 0.6) -> None:
        self._interaction_computer = InteractionMatrixComputer()
        self._order_calculator = OrderParameterCalculator()
        self._transition_detector = PhaseTransitionDetector(critical_threshold)
        self._crystallizer = EmergenceCrystallizer()

    def execute(self, context: dict[str, Any]) -> InventionResult:
        skills = context.get("skills", [])
        if len(skills) < 2:
            logger.warning("emergence_detector_insufficient_skills", skill_count=len(skills))
            return InventionResult(
                output={"status": "insufficient_skills", "message": "At least 2 skills required"},
                confidence=ConfidenceLevel.VERIFIED,
                invention_id=self.invention_id,
            )
        try:
            interaction_matrix = self._interaction_computer.compute_matrix(skills)
            order_parameter = self._order_calculator.calculate(interaction_matrix)
            transition_result = self._transition_detector.detect(order_parameter)
            output: dict[str, Any] = {
                "status": "success",
                "order_parameter": order_parameter,
                "critical_threshold": transition_result.critical_threshold,
                "phase_transition_detected": transition_result.detected,
                "emergence_type": transition_result.emergence_type,
                "interaction_matrix_size": len(interaction_matrix),
            }
            synergy_partners: list[str] = []
            if transition_result.detected:
                crystallized = self._crystallizer.crystallize(skills, transition_result)
                output["crystallized_skill"] = crystallized
                synergy_partners = self.get_synergy_partners()
                logger.info(
                    "emergence_detected",
                    order_parameter=order_parameter,
                    emergence_type=transition_result.emergence_type,
                    crystallized_id=crystallized["id"],
                )
            else:
                logger.info(
                    "no_emergence_detected",
                    order_parameter=order_parameter,
                    threshold=transition_result.critical_threshold,
                )
            confidence = (
                ConfidenceLevel.VERIFIED
                if transition_result.detected and transition_result.emergence_type == "strong_emergence"
                else ConfidenceLevel.INFERRED
                if transition_result.detected
                else ConfidenceLevel.RESEARCHED
            )
            return InventionResult(
                output=output,
                confidence=confidence,
                synergy_detected=synergy_partners,
                invention_id=self.invention_id,
                metadata={"formula": self.formula, "operator": self.operator},
            )
        except Exception as exc:
            logger.error("emergence_detector_failed", error=str(exc))
            return InventionResult(
                output={"status": "error", "error": str(exc)},
                confidence=ConfidenceLevel.UNCERTAIN,
                invention_id=self.invention_id,
            )

    def validate(self, result: InventionResult) -> bool:
        if not result.is_valid():
            return False
        output = result.output
        if output.get("status") != "success":
            return False
        order_parameter = output.get("order_parameter", 0.0)
        if not (0.0 <= order_parameter <= 1.0):
            return False
        if output.get("phase_transition_detected"):
            if "crystallized_skill" not in output:
                return False
            crystallized = output["crystallized_skill"]
            if not crystallized.get("is_emergent"):
                return False
            if not crystallized.get("source_skills"):
                return False
        return True

    def get_synergy_partners(self) -> list[str]:
        return ["SCI-005", "SCI-003", "EWF-004"]
