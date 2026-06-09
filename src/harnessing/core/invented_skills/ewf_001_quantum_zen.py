from __future__ import annotations

import math
import structlog
from dataclasses import dataclass, field
from typing import Any

from .base_engine import BaseInventionEngine
from .base_invention_engine import ConfidenceLevel, InventionResult

logger = structlog.get_logger()


@dataclass
class FlowStateResult:
    in_flow: bool
    skill_challenge_ratio: float
    flow_intensity: float


class DualThresholdCollapse:
    def __init__(self, theta_evidence: float = 0.6, alpha_attachment: float = 0.4) -> None:
        self.theta_evidence = theta_evidence
        self.alpha_attachment = alpha_attachment

    def should_collapse(self, evidence_level: float, attachment_level: float) -> bool:
        return evidence_level > self.theta_evidence and attachment_level < self.alpha_attachment


class AttachmentMeasurer:
    def __init__(
        self,
        time_weight: float = 0.4,
        emotion_weight: float = 0.35,
        commitment_weight: float = 0.25,
    ) -> None:
        self.time_weight = time_weight
        self.emotion_weight = emotion_weight
        self.commitment_weight = commitment_weight

    def measure(self, context: dict[str, Any]) -> float:
        time_invested = float(context.get("time_invested", 0.0))
        emotional_language = float(context.get("emotional_language", 0.0))
        commitment_signals = float(context.get("commitment_signals", 0.0))
        raw = (
            self.time_weight * min(time_invested, 1.0)
            + self.emotion_weight * min(emotional_language, 1.0)
            + self.commitment_weight * min(commitment_signals, 1.0)
        )
        return max(0.0, min(1.0, raw))


class SqrtAttachmentOperator:
    def apply(self, attachment: float) -> float:
        clamped = max(0.0, min(1.0, attachment))
        return math.sqrt(clamped)


class FlowStateDetector:
    def detect(self, skill_level: float, challenge_level: float) -> FlowStateResult:
        skill_level = max(0.0, min(1.0, skill_level))
        challenge_level = max(0.0, min(1.0, challenge_level))
        ratio = skill_level / challenge_level if challenge_level > 0.0 else float("inf")
        in_flow = 0.74 <= ratio <= 1.34
        if in_flow:
            deviation = abs(ratio - 1.0)
            intensity = max(0.0, 1.0 - deviation / 0.34)
        else:
            intensity = 0.0
        return FlowStateResult(
            in_flow=in_flow,
            skill_challenge_ratio=round(ratio, 4),
            flow_intensity=round(intensity, 4),
        )


class QuantumZenCognition(BaseInventionEngine):
    name = "QuantumZenCognition"
    invention_id = "EWF-001"
    operator = "⊕ × √(attachment)"
    formula = "⊕(awareness) × √(attachment) → collapse(P(evidence) > θ AND attachment < α)"
    category = "EWF"
    description = "Dual-threshold decision framework combining quantum superposition with Zen mindfulness"

    def __init__(
        self,
        theta_evidence: float = 0.6,
        alpha_attachment: float = 0.4,
    ) -> None:
        self._collapse = DualThresholdCollapse(
            theta_evidence=theta_evidence,
            alpha_attachment=alpha_attachment,
        )
        self._attachment_measurer = AttachmentMeasurer()
        self._sqrt_operator = SqrtAttachmentOperator()
        self._flow_detector = FlowStateDetector()

    def execute(self, context: dict[str, Any]) -> InventionResult:
        try:
            decision = context.get("decision", {})
            if not decision:
                logger.warning("no_decision_context", invention_id=self.invention_id)
                return InventionResult(
                    output={},
                    confidence=ConfidenceLevel.UNCERTAIN,
                    invention_id=self.invention_id,
                )

            attachment_raw = self._attachment_measurer.measure(decision)
            attachment_sqrt = self._sqrt_operator.apply(attachment_raw)

            evidence_level = float(decision.get("evidence_level", 0.0))
            collapsed = self._collapse.should_collapse(evidence_level, attachment_raw)

            output: dict[str, Any] = {
                "attachment_raw": round(attachment_raw, 4),
                "attachment_sqrt": round(attachment_sqrt, 4),
                "evidence_level": round(evidence_level, 4),
                "collapsed": collapsed,
                "decision_timing": "immediate" if collapsed else "defer",
            }

            if collapsed:
                skill_level = float(decision.get("skill_level", 0.5))
                challenge_level = float(decision.get("challenge_level", 0.5))
                flow_result = self._flow_detector.detect(skill_level, challenge_level)
                output["flow_state"] = {
                    "in_flow": flow_result.in_flow,
                    "skill_challenge_ratio": flow_result.skill_challenge_ratio,
                    "flow_intensity": flow_result.flow_intensity,
                }
                confidence = (
                    ConfidenceLevel.VERIFIED
                    if flow_result.in_flow
                    else ConfidenceLevel.INFERRED
                )
            else:
                output["flow_state"] = None
                confidence = ConfidenceLevel.RESEARCHED

            logger.info(
                "quantum_zen_cognition_executed",
                invention_id=self.invention_id,
                collapsed=collapsed,
                attachment_raw=attachment_raw,
                evidence_level=evidence_level,
            )

            return InventionResult(
                output=output,
                confidence=confidence,
                synergy_detected=self.get_synergy_partners(),
                invention_id=self.invention_id,
                metadata={
                    "formula": self.formula,
                    "operator": self.operator,
                    "category": self.category,
                },
            )

        except Exception as exc:
            logger.error("quantum_zen_cognition_failed", invention_id=self.invention_id, error=str(exc))
            return InventionResult(
                output={"state": "error", "error": str(exc)},
                confidence=ConfidenceLevel.UNCERTAIN,
                invention_id=self.invention_id,
            )

    def validate(self, result: InventionResult) -> bool:
        if not result.is_valid():
            return False
        output = result.output
        if "attachment_raw" not in output:
            return False
        if "attachment_sqrt" not in output:
            return False
        if "collapsed" not in output:
            return False
        if "decision_timing" not in output:
            return False
        if output["collapsed"] and output.get("flow_state") is None:
            return False
        return True

    def get_synergy_partners(self) -> list[str]:
        return ["SCI-001", "EWF-004", "EWF-002"]
