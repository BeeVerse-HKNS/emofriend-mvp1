from __future__ import annotations

import cmath
import math
import structlog
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .base_engine import BaseInventionEngine
from .base_invention_engine import ConfidenceLevel, InventionResult

logger = structlog.get_logger()


class CognitiveBias(Enum):
    ANCHORING = "anchoring"
    CONFIRMATION = "confirmation"
    AVAILABILITY = "availability"


@dataclass
class Hypothesis:
    id: str
    content: str
    amplitude: complex = complex(1.0, 0.0)
    evidence: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class HypothesisContainer:
    def __init__(self) -> None:
        self._hypotheses: list[Hypothesis] = []

    def add_hypothesis(self, hypothesis: Hypothesis) -> None:
        self._hypotheses.append(hypothesis)
        self.normalize()

    def get_amplitudes(self) -> list[complex]:
        return [h.amplitude for h in self._hypotheses]

    def normalize(self) -> None:
        if not self._hypotheses:
            return
        norm = math.sqrt(sum(abs(h.amplitude) ** 2 for h in self._hypotheses))
        if norm == 0:
            equal_amp = 1.0 / math.sqrt(len(self._hypotheses))
            for h in self._hypotheses:
                h.amplitude = complex(equal_amp, 0.0)
            return
        for h in self._hypotheses:
            h.amplitude = h.amplitude / norm

    def get_hypotheses(self) -> list[Hypothesis]:
        return list(self._hypotheses)

    def get_probabilities(self) -> dict[str, float]:
        return {h.id: abs(h.amplitude) ** 2 for h in self._hypotheses}

    def update_evidence(self, hypothesis_id: str, evidence_delta: float) -> None:
        for h in self._hypotheses:
            if h.id == hypothesis_id:
                h.evidence = max(0.0, h.evidence + evidence_delta)
                boost = 1.0 + evidence_delta * 0.1
                h.amplitude = h.amplitude * boost
                break
        self.normalize()


class InterferenceComputer:
    def __init__(self, compatibility_threshold: float = 0.0) -> None:
        self._compatibility_threshold = compatibility_threshold

    def compute_interference(self, hypotheses: list[Hypothesis]) -> list[list[complex]]:
        n = len(hypotheses)
        if n == 0:
            return []
        matrix: list[list[complex]] = [[complex(0, 0)] * n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                alpha_i = hypotheses[i].amplitude
                alpha_j = hypotheses[j].amplitude
                interference = alpha_i * alpha_j.conjugate()
                matrix[i][j] = interference
        return matrix

    def classify_interference(self, interference_matrix: list[list[complex]]) -> dict[str, list[tuple[int, int]]]:
        constructive: list[tuple[int, int]] = []
        destructive: list[tuple[int, int]] = []
        neutral: list[tuple[int, int]] = []
        n = len(interference_matrix)
        for i in range(n):
            for j in range(i + 1, n):
                real_part = interference_matrix[i][j].real
                if real_part > self._compatibility_threshold:
                    constructive.append((i, j))
                elif real_part < -self._compatibility_threshold:
                    destructive.append((i, j))
                else:
                    neutral.append((i, j))
        return {
            "constructive": constructive,
            "destructive": destructive,
            "neutral": neutral,
        }

    def apply_interference(self, hypotheses: list[Hypothesis], interference_matrix: list[list[complex]]) -> list[Hypothesis]:
        n = len(hypotheses)
        if n == 0:
            return []
        result = []
        for i in range(n):
            interference_sum = complex(0, 0)
            for j in range(n):
                if i != j:
                    interference_sum += interference_matrix[i][j]
            new_amplitude = hypotheses[i].amplitude + interference_sum * 0.1
            updated = Hypothesis(
                id=hypotheses[i].id,
                content=hypotheses[i].content,
                amplitude=new_amplitude,
                evidence=hypotheses[i].evidence,
                metadata={**hypotheses[i].metadata},
            )
            result.append(updated)
        norm = math.sqrt(sum(abs(h.amplitude) ** 2 for h in result))
        if norm > 0:
            for h in result:
                h.amplitude = h.amplitude / norm
        return result


class CollapseCriteria:
    def __init__(
        self,
        theta_evidence: float = 0.7,
        theta_coherence: float = 0.85,
        theta_time: float = 0.9,
    ) -> None:
        self._theta_evidence = theta_evidence
        self._theta_coherence = theta_coherence
        self._theta_time = theta_time

    def should_collapse(self, context: dict[str, Any]) -> bool:
        evidence = context.get("evidence", 0.0)
        coherence = context.get("coherence", 0.0)
        time_pressure = context.get("time_pressure", 0.0)
        if evidence > self._theta_evidence:
            return True
        if coherence > self._theta_coherence:
            return True
        if time_pressure > self._theta_time:
            return True
        return False

    def get_thresholds(self) -> dict[str, float]:
        return {
            "theta_evidence": self._theta_evidence,
            "theta_coherence": self._theta_coherence,
            "theta_time": self._theta_time,
        }


class DecoherenceProtection:
    def __init__(self) -> None:
        self._bias_patterns: dict[CognitiveBias, float] = {
            CognitiveBias.ANCHORING: 0.3,
            CognitiveBias.CONFIRMATION: 0.4,
            CognitiveBias.AVAILABILITY: 0.25,
        }

    def protect(self, hypotheses: list[Hypothesis]) -> list[Hypothesis]:
        if not hypotheses:
            return []
        filtered = list(hypotheses)
        filtered = self._reduce_anchoring(filtered)
        filtered = self._reduce_confirmation(filtered)
        filtered = self._reduce_availability(filtered)
        norm = math.sqrt(sum(abs(h.amplitude) ** 2 for h in filtered))
        if norm > 0:
            for h in filtered:
                h.amplitude = h.amplitude / norm
        return filtered

    def _reduce_anchoring(self, hypotheses: list[Hypothesis]) -> list[Hypothesis]:
        if not hypotheses:
            return hypotheses
        first_amplitude = abs(hypotheses[0].amplitude)
        total_amplitude = sum(abs(h.amplitude) for h in hypotheses)
        if total_amplitude == 0:
            return hypotheses
        anchoring_ratio = first_amplitude / total_amplitude
        if anchoring_ratio > self._bias_patterns[CognitiveBias.ANCHORING]:
            damping = self._bias_patterns[CognitiveBias.ANCHORING] / anchoring_ratio
            hypotheses[0].amplitude = hypotheses[0].amplitude * damping
        return hypotheses

    def _reduce_confirmation(self, hypotheses: list[Hypothesis]) -> list[Hypothesis]:
        for h in hypotheses:
            if h.evidence > 0.8:
                confirmation_boost = h.evidence - 0.8
                damping = 1.0 - confirmation_boost * self._bias_patterns[CognitiveBias.CONFIRMATION]
                h.amplitude = h.amplitude * max(0.1, damping)
        return hypotheses

    def _reduce_availability(self, hypotheses: list[Hypothesis]) -> list[Hypothesis]:
        recency_scores = [h.metadata.get("recency", 1.0) for h in hypotheses]
        max_recency = max(recency_scores) if recency_scores else 1.0
        if max_recency <= 0:
            return hypotheses
        for h in hypotheses:
            recency = h.metadata.get("recency", 1.0)
            if recency / max_recency > 0.8:
                availability_damping = 1.0 - self._bias_patterns[CognitiveBias.AVAILABILITY] * 0.5
                h.amplitude = h.amplitude * availability_damping
        return hypotheses


class QuantumSuperpositionInvention(BaseInventionEngine):
    name = "QuantumSuperpositionInvention"
    invention_id = "SCI-001"
    operator = "⊕"
    formula = "⊕(H₁, ..., Hₙ) → interference → collapse(evidence > θ)"
    category = "SCI"
    description = "Maintain multiple hypotheses in superposition until evidence forces collapse"

    def __init__(
        self,
        theta_evidence: float = 0.7,
        theta_coherence: float = 0.85,
        theta_time: float = 0.9,
    ) -> None:
        self._container = HypothesisContainer()
        self._interference_computer = InterferenceComputer()
        self._collapse_criteria = CollapseCriteria(
            theta_evidence=theta_evidence,
            theta_coherence=theta_coherence,
            theta_time=theta_time,
        )
        self._decoherence_protection = DecoherenceProtection()

    def execute(self, context: dict[str, Any]) -> InventionResult:
        try:
            hypotheses_data = context.get("hypotheses", [])
            if not hypotheses_data:
                logger.warning("no_hypotheses_provided", invention_id=self.invention_id)
                return InventionResult(
                    output={"state": "empty", "message": "No hypotheses provided"},
                    confidence=ConfidenceLevel.UNCERTAIN,
                    invention_id=self.invention_id,
                )

            container = HypothesisContainer()
            for h_data in hypotheses_data:
                hypothesis = Hypothesis(
                    id=h_data.get("id", ""),
                    content=h_data.get("content", ""),
                    evidence=h_data.get("evidence", 0.0),
                    metadata=h_data.get("metadata", {}),
                )
                container.add_hypothesis(hypothesis)

            raw_hypotheses = container.get_hypotheses()
            interference_matrix = self._interference_computer.compute_interference(raw_hypotheses)
            interference_classification = self._interference_computer.classify_interference(interference_matrix)
            post_interference = self._interference_computer.apply_interference(raw_hypotheses, interference_matrix)

            for h in post_interference:
                container.add_hypothesis(h)

            protected = self._decoherence_protection.protect(container.get_hypotheses())

            max_evidence = max((h.evidence for h in protected), default=0.0)
            probabilities = {h.id: abs(h.amplitude) ** 2 for h in protected}
            max_prob_id = max(probabilities, key=probabilities.get) if probabilities else ""
            coherence = max(probabilities.values()) if probabilities else 0.0

            collapse_context = {
                "evidence": max_evidence,
                "coherence": coherence,
                "time_pressure": context.get("time_pressure", 0.0),
            }

            should_collapse = self._collapse_criteria.should_collapse(collapse_context)

            if should_collapse:
                collapsed = max(protected, key=lambda h: abs(h.amplitude) ** 2)
                result_output = {
                    "state": "collapsed",
                    "collapsed_hypothesis": {
                        "id": collapsed.id,
                        "content": collapsed.content,
                        "probability": abs(collapsed.amplitude) ** 2,
                        "evidence": collapsed.evidence,
                    },
                    "all_probabilities": probabilities,
                    "interference_summary": {
                        "constructive_pairs": len(interference_classification["constructive"]),
                        "destructive_pairs": len(interference_classification["destructive"]),
                        "neutral_pairs": len(interference_classification["neutral"]),
                    },
                    "collapse_reason": self._get_collapse_reason(collapse_context),
                    "thresholds": self._collapse_criteria.get_thresholds(),
                }
                confidence = ConfidenceLevel.VERIFIED if max_evidence > 0.8 else ConfidenceLevel.RESEARCHED
                logger.info(
                    "quantum_superposition_collapsed",
                    invention_id=self.invention_id,
                    collapsed_id=collapsed.id,
                    probability=abs(collapsed.amplitude) ** 2,
                )
            else:
                result_output = {
                    "state": "superposition",
                    "hypotheses": [
                        {
                            "id": h.id,
                            "content": h.content,
                            "probability": abs(h.amplitude) ** 2,
                            "evidence": h.evidence,
                        }
                        for h in protected
                    ],
                    "interference_summary": {
                        "constructive_pairs": len(interference_classification["constructive"]),
                        "destructive_pairs": len(interference_classification["destructive"]),
                        "neutral_pairs": len(interference_classification["neutral"]),
                    },
                    "coherence": coherence,
                    "max_evidence": max_evidence,
                    "thresholds": self._collapse_criteria.get_thresholds(),
                }
                confidence = ConfidenceLevel.INFERRED
                logger.info(
                    "quantum_superposition_maintained",
                    invention_id=self.invention_id,
                    hypothesis_count=len(protected),
                    coherence=coherence,
                )

            return InventionResult(
                output=result_output,
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
            logger.error("quantum_superposition_failed", invention_id=self.invention_id, error=str(exc))
            return InventionResult(
                output={"state": "error", "error": str(exc)},
                confidence=ConfidenceLevel.UNCERTAIN,
                invention_id=self.invention_id,
            )

    def validate(self, result: InventionResult) -> bool:
        if not result.output:
            return False
        if result.confidence == ConfidenceLevel.UNCERTAIN:
            return False
        state = result.output.get("state")
        if state == "collapsed":
            collapsed = result.output.get("collapsed_hypothesis", {})
            if not collapsed.get("id"):
                return False
            prob = collapsed.get("probability", 0.0)
            if prob <= 0.0:
                return False
            return True
        if state == "superposition":
            hypotheses = result.output.get("hypotheses", [])
            if len(hypotheses) < 2:
                return False
            total_prob = sum(h.get("probability", 0.0) for h in hypotheses)
            if abs(total_prob - 1.0) > 0.1:
                return False
            return True
        return False

    def get_synergy_partners(self) -> list[str]:
        return ["EWF-001", "SCI-004", "SCI-003"]

    def _get_collapse_reason(self, context: dict[str, float]) -> str:
        thresholds = self._collapse_criteria.get_thresholds()
        if context["evidence"] > thresholds["theta_evidence"]:
            return "evidence_threshold_exceeded"
        if context["coherence"] > thresholds["theta_coherence"]:
            return "coherence_threshold_exceeded"
        if context["time_pressure"] > thresholds["theta_time"]:
            return "time_pressure_threshold_exceeded"
        return "unknown"
