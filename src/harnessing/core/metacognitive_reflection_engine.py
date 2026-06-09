from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ConfidenceLevel(str, Enum):
    VERIFIED = "verified"
    RESEARCHED = "researched"
    SPECULATIVE = "speculative"
    UNCERTAIN = "uncertain"


@dataclass
class ConfidenceScore:
    claim: str
    level: ConfidenceLevel
    score: float
    evidence_count: int
    missing_evidence: list[str] = field(default_factory=list)


@dataclass
class HallucinationFlag:
    claim: str
    is_hallucination_risk: bool
    confidence_score: float
    contradiction_with_kb: str | None
    suggested_correction: str | None


@dataclass
class RevisionAction:
    original_claim: str
    trigger_reason: str
    revised_claim: str
    new_confidence: float


@dataclass
class UncertaintyReport:
    total_claims: int
    verified_count: int
    uncertain_count: int
    unknown_count: int
    uncertainty_map: dict[str, str] = field(default_factory=dict)


@dataclass
class MetacognitiveResult:
    original_claims: list[str]
    evaluated_claims: list[ConfidenceScore]
    revisions_made: list[RevisionAction]
    final_confidence_avg: float
    loop_iterations: int
    convergence_achieved: bool


class ConfidenceCalibrator:
    SOURCE_WEIGHTS: dict[str, float] = {
        "knowledge_base": 1.0,
        "official_doc": 0.9,
        "web_search": 0.6,
        "logical_inference": 0.4,
        "unverified": 0.1,
    }

    def __init__(self, evidence_threshold: int = 3):
        self.evidence_threshold = evidence_threshold
        self.logger = logging.getLogger(__name__)

    def calibrate(self, claim: str, evidence: list[str]) -> ConfidenceScore:
        if not evidence:
            return ConfidenceScore(
                claim=claim,
                level=ConfidenceLevel.UNCERTAIN,
                score=0.0,
                evidence_count=0,
                missing_evidence=[claim],
            )

        total_weight = 0.0
        for e in evidence:
            weight = self._source_weight(e)
            total_weight += weight

        max_possible = len(evidence) * 1.0
        raw_score = total_weight / max_possible if max_possible > 0 else 0.0
        score = min(1.0, raw_score)

        missing = self._identify_missing(claim, evidence)

        level = self._determine_level(score, len(evidence), len(missing))

        self.logger.info(
            "confidence_calibrated",
            extra={"claim": claim[:50], "level": level.value, "score": round(score, 4)},
        )

        return ConfidenceScore(
            claim=claim,
            level=level,
            score=round(score, 4),
            evidence_count=len(evidence),
            missing_evidence=missing,
        )

    def _source_weight(self, evidence_item: str) -> float:
        lower = evidence_item.lower()
        for keyword, weight in self.SOURCE_WEIGHTS.items():
            if keyword in lower:
                return weight
        return 0.3

    def _determine_level(
        self, score: float, evidence_count: int, missing_count: int
    ) -> ConfidenceLevel:
        if score >= 0.8 and evidence_count >= self.evidence_threshold and missing_count == 0:
            return ConfidenceLevel.VERIFIED
        if score >= 0.6 and evidence_count >= 2:
            return ConfidenceLevel.RESEARCHED
        if score >= 0.3:
            return ConfidenceLevel.SPECULATIVE
        return ConfidenceLevel.UNCERTAIN

    def _identify_missing(self, claim: str, evidence: list[str]) -> list[str]:
        missing = []
        has_kb = any("knowledge_base" in e.lower() for e in evidence)
        has_official = any("official_doc" in e.lower() for e in evidence)
        has_search = any("web_search" in e.lower() for e in evidence)

        if not has_kb and not has_official:
            missing.append("verified_source_for: " + claim[:50])
        if not has_search and not has_kb:
            missing.append("cross_reference_for: " + claim[:50])

        return missing


class HallucinationDetector:
    def __init__(self, similarity_threshold: float = 0.6):
        self.similarity_threshold = similarity_threshold
        self.logger = logging.getLogger(__name__)

    def detect(
        self, claims: list[str], knowledge_base: dict[str, str] | None = None
    ) -> list[HallucinationFlag]:
        if not claims:
            return []

        knowledge_base = knowledge_base or {}
        flags = []

        for claim in claims:
            contradiction = None
            correction = None
            is_risk = False
            confidence = 0.5

            kb_match = self._find_kb_match(claim, knowledge_base)
            if kb_match:
                similarity = kb_match["similarity"]
                confidence = similarity
                if similarity < self.similarity_threshold:
                    is_risk = True
                    contradiction = f"Low similarity ({similarity:.2f}) with KB entry: {kb_match['key']}"
                    correction = kb_match["value"]
                else:
                    is_risk = False
            else:
                if knowledge_base:
                    is_risk = True
                    contradiction = "No matching entry found in knowledge base"
                    confidence = 0.2
                    correction = None
                else:
                    is_risk = False
                    confidence = 0.5

            if self._contains_fabricated_reference(claim):
                is_risk = True
                confidence = min(confidence, 0.1)
                contradiction = (contradiction or "") + " Contains fabricated reference pattern"
                contradiction = contradiction.strip()

            flag = HallucinationFlag(
                claim=claim,
                is_hallucination_risk=is_risk,
                confidence_score=round(confidence, 4),
                contradiction_with_kb=contradiction,
                suggested_correction=correction,
            )
            flags.append(flag)

            self.logger.info(
                "hallucination_detected",
                extra={
                    "claim": claim[:50],
                    "is_risk": is_risk,
                    "confidence": round(confidence, 4),
                },
            )

        return flags

    def _find_kb_match(
        self, claim: str, knowledge_base: dict[str, str]
    ) -> dict[str, Any] | None:
        if not knowledge_base:
            return None

        best_match = None
        best_similarity = 0.0

        claim_lower = claim.lower()
        claim_words = set(claim_lower.split())

        for key, value in knowledge_base.items():
            key_lower = key.lower()
            key_words = set(key_lower.split())

            intersection = claim_words & key_words
            union = claim_words | key_words

            jaccard = len(intersection) / len(union) if union else 0.0

            if jaccard > best_similarity:
                best_similarity = jaccard
                best_match = {"key": key, "value": value, "similarity": jaccard}

        if best_match and best_match["similarity"] > 0.1:
            return best_match
        return None

    def _contains_fabricated_reference(self, claim: str) -> bool:
        fabrication_patterns = [
            "according to a study by",
            "research shows that",
            "experts say that",
            "it is well known that",
            "studies have proven",
            "scientists have confirmed",
        ]
        lower = claim.lower()
        return any(p in lower for p in fabrication_patterns)


class RevisionTrigger:
    CONFIDENCE_THRESHOLD = 0.7

    def __init__(self, confidence_threshold: float | None = None):
        if confidence_threshold is not None:
            self.CONFIDENCE_THRESHOLD = confidence_threshold
        self.logger = logging.getLogger(__name__)

    def evaluate(self, confidence_scores: list[ConfidenceScore]) -> list[RevisionAction]:
        actions = []

        for cs in confidence_scores:
            if cs.score < self.CONFIDENCE_THRESHOLD:
                reason = self._determine_reason(cs)
                revised = self._generate_revision(cs)
                new_conf = min(1.0, cs.score + 0.2)

                action = RevisionAction(
                    original_claim=cs.claim,
                    trigger_reason=reason,
                    revised_claim=revised,
                    new_confidence=round(new_conf, 4),
                )
                actions.append(action)

                self.logger.info(
                    "revision_triggered",
                    extra={
                        "claim": cs.claim[:50],
                        "reason": reason,
                        "old_score": cs.score,
                        "new_score": round(new_conf, 4),
                    },
                )

        return actions

    def _determine_reason(self, cs: ConfidenceScore) -> str:
        if cs.level == ConfidenceLevel.UNCERTAIN:
            return "no_evidence"
        if cs.level == ConfidenceLevel.SPECULATIVE:
            return "insufficient_evidence"
        if cs.missing_evidence:
            return "missing_evidence: " + "; ".join(cs.missing_evidence[:2])
        return "below_threshold"

    def _generate_revision(self, cs: ConfidenceScore) -> str:
        level_prefix = {
            ConfidenceLevel.UNCERTAIN: "It is uncertain whether",
            ConfidenceLevel.SPECULATIVE: "It is speculated that",
            ConfidenceLevel.RESEARCHED: "Research suggests that",
            ConfidenceLevel.VERIFIED: "It is verified that",
        }
        prefix = level_prefix.get(cs.level, "It is unclear whether")

        claim_core = cs.claim
        for p in [
            "it is verified that",
            "research suggests that",
            "it is speculated that",
            "it is uncertain whether",
            "it is well known that",
        ]:
            if claim_core.lower().startswith(p):
                claim_core = claim_core[len(p) :].strip()
                break

        missing_str = ""
        if cs.missing_evidence:
            missing_str = f" (missing: {', '.join(cs.missing_evidence[:2])})"

        return f"{prefix} {claim_core}{missing_str}"


class UncertaintyQuantifier:
    UNCERTAINTY_EXPRESSIONS: dict[ConfidenceLevel, str] = {
        ConfidenceLevel.VERIFIED: "✅ 已驗證",
        ConfidenceLevel.RESEARCHED: "🔍 已研究但未交叉驗證",
        ConfidenceLevel.SPECULATIVE: "⚠️ 推測，無直接證據",
        ConfidenceLevel.UNCERTAIN: "❌ 不確定，需要驗證",
    }

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def quantify(self, confidence_scores: list[ConfidenceScore]) -> UncertaintyReport:
        if not confidence_scores:
            return UncertaintyReport(
                total_claims=0,
                verified_count=0,
                uncertain_count=0,
                unknown_count=0,
                uncertainty_map={},
            )

        verified = 0
        uncertain = 0
        unknown = 0
        uncertainty_map: dict[str, str] = {}

        for cs in confidence_scores:
            expression = self.UNCERTAINTY_EXPRESSIONS.get(
                cs.level, "❌ 不確定，需要驗證"
            )

            if cs.missing_evidence:
                missing_str = "; ".join(cs.missing_evidence[:3])
                expression += f" — 缺少: {missing_str}"

            uncertainty_map[cs.claim] = expression

            if cs.level == ConfidenceLevel.VERIFIED:
                verified += 1
            elif cs.level in (ConfidenceLevel.SPECULATIVE, ConfidenceLevel.UNCERTAIN):
                uncertain += 1
            else:
                unknown += 1

        self.logger.info(
            "uncertainty_quantified",
            extra={
                "total": len(confidence_scores),
                "verified": verified,
                "uncertain": uncertain,
                "unknown": unknown,
            },
        )

        return UncertaintyReport(
            total_claims=len(confidence_scores),
            verified_count=verified,
            uncertain_count=uncertain,
            unknown_count=unknown,
            uncertainty_map=uncertainty_map,
        )


class MetacognitiveLoop:
    CONVERGENCE_THRESHOLD = 0.05

    def __init__(
        self,
        calibrator: ConfidenceCalibrator | None = None,
        detector: HallucinationDetector | None = None,
        trigger: RevisionTrigger | None = None,
        quantifier: UncertaintyQuantifier | None = None,
    ):
        self.calibrator = calibrator or ConfidenceCalibrator()
        self.detector = detector or HallucinationDetector()
        self.trigger = trigger or RevisionTrigger()
        self.quantifier = quantifier or UncertaintyQuantifier()
        self.logger = logging.getLogger(__name__)

    def execute(
        self,
        claims: list[str],
        knowledge_base: dict[str, str] | None = None,
        max_iterations: int = 3,
    ) -> MetacognitiveResult:
        if not claims:
            return MetacognitiveResult(
                original_claims=[],
                evaluated_claims=[],
                revisions_made=[],
                final_confidence_avg=0.0,
                loop_iterations=0,
                convergence_achieved=True,
            )

        knowledge_base = knowledge_base or {}
        all_revisions: list[RevisionAction] = []
        current_claims = list(claims)
        evaluated: list[ConfidenceScore] = []
        iterations = 0
        prev_avg = 0.0
        convergence = False

        for iteration in range(max_iterations):
            iterations = iteration + 1

            hallucination_flags = self.detector.detect(current_claims, knowledge_base)

            evidence_map = self._build_evidence_map(current_claims, hallucination_flags, knowledge_base)

            evaluated = []
            for claim in current_claims:
                evidence = evidence_map.get(claim, [])
                cs = self.calibrator.calibrate(claim, evidence)
                evaluated.append(cs)

            current_avg = self._compute_avg_confidence(evaluated)

            revisions = self.trigger.evaluate(evaluated)
            all_revisions.extend(revisions)

            if not revisions:
                convergence = True
                break

            if iteration > 0 and abs(current_avg - prev_avg) < self.CONVERGENCE_THRESHOLD:
                convergence = True
                break

            prev_avg = current_avg

            current_claims = [r.revised_claim for r in revisions]

        final_avg = self._compute_avg_confidence(evaluated)

        self.logger.info(
            "metacognitive_loop_completed",
            extra={
                "iterations": iterations,
                "convergence": convergence,
                "final_avg": round(final_avg, 4),
                "revisions": len(all_revisions),
            },
        )

        return MetacognitiveResult(
            original_claims=list(claims),
            evaluated_claims=evaluated,
            revisions_made=all_revisions,
            final_confidence_avg=round(final_avg, 4),
            loop_iterations=iterations,
            convergence_achieved=convergence,
        )

    def _build_evidence_map(
        self,
        claims: list[str],
        flags: list[HallucinationFlag],
        knowledge_base: dict[str, str],
    ) -> dict[str, list[str]]:
        evidence_map: dict[str, list[str]] = {}

        flag_map = {f.claim: f for f in flags}

        for claim in claims:
            evidence: list[str] = []

            flag = flag_map.get(claim)
            if flag and not flag.is_hallucination_risk and flag.confidence_score >= 0.6:
                evidence.append("knowledge_base: verified_match")

            for key, value in knowledge_base.items():
                if self._claim_matches_key(claim, key):
                    evidence.append(f"knowledge_base: {key}")

            if flag and flag.confidence_score < 0.5:
                evidence.append("unverified: low_confidence_match")

            evidence_map[claim] = evidence

        return evidence_map

    def _claim_matches_key(self, claim: str, key: str) -> bool:
        claim_words = set(claim.lower().split())
        key_words = set(key.lower().split())
        intersection = claim_words & key_words
        return len(intersection) >= min(len(key_words), 2)

    def _compute_avg_confidence(self, scores: list[ConfidenceScore]) -> float:
        if not scores:
            return 0.0
        return sum(s.score for s in scores) / len(scores)


class MetacognitiveReflectionEngine:
    FORMULA = "sq(R) * Q"

    def __init__(
        self,
        calibrator: ConfidenceCalibrator | None = None,
        detector: HallucinationDetector | None = None,
        trigger: RevisionTrigger | None = None,
        quantifier: UncertaintyQuantifier | None = None,
        loop: MetacognitiveLoop | None = None,
    ):
        self.calibrator = calibrator or ConfidenceCalibrator()
        self.detector = detector or HallucinationDetector()
        self.trigger = trigger or RevisionTrigger()
        self.quantifier = quantifier or UncertaintyQuantifier()
        self.loop = loop or MetacognitiveLoop(
            calibrator=self.calibrator,
            detector=self.detector,
            trigger=self.trigger,
            quantifier=self.quantifier,
        )
        self._history: list[dict[str, Any]] = []
        self.logger = logging.getLogger(__name__)

    def reflect(
        self,
        claims: list[str],
        knowledge_base: dict[str, str] | None = None,
        max_iterations: int = 3,
    ) -> MetacognitiveResult:
        result = self.loop.execute(claims, knowledge_base, max_iterations)

        self._history.append(
            {
                "formula": self.FORMULA,
                "claims_count": len(claims),
                "iterations": result.loop_iterations,
                "convergence": result.convergence_achieved,
                "final_avg": result.final_confidence_avg,
                "revisions_count": len(result.revisions_made),
            }
        )

        self.logger.info(
            "reflection_completed",
            extra={
                "formula": self.FORMULA,
                "claims": len(claims),
                "iterations": result.loop_iterations,
                "convergence": result.convergence_achieved,
                "final_avg": result.final_confidence_avg,
            },
        )

        return result

    def get_confidence_summary(self) -> dict[str, Any]:
        if not self._history:
            return {
                "total_reflections": 0,
                "avg_confidence": 0.0,
                "total_revisions": 0,
                "convergence_rate": 0.0,
            }

        total = len(self._history)
        avg_conf = sum(h["final_avg"] for h in self._history) / total
        total_revisions = sum(h["revisions_count"] for h in self._history)
        convergence_count = sum(1 for h in self._history if h["convergence"])

        return {
            "total_reflections": total,
            "avg_confidence": round(avg_conf, 4),
            "total_revisions": total_revisions,
            "convergence_rate": round(convergence_count / total, 4) if total > 0 else 0.0,
            "formula": self.FORMULA,
        }


class RegionalComplianceTestMixin:
    HK_PDPO_CLAIMS = [
        "User data collected for AI training purposes",
        "Personal information transferred to overseas servers",
        "Data subject rights requests processed",
        "Consent obtained for automated decision-making",
    ]

    CN_PIPL_CLAIMS = [
        "User profile exported to foreign servers",
        "Algorithmic recommendations disclosed to users",
        "Cross-border data transfer security assessment completed",
        "Personal information anonymization verification",
    ]

    EU_AI_ACT_CLAIMS = [
        "High-risk AI system conformity assessment performed",
        "Training data documentation available",
        "Human oversight measures implemented",
        "AI system transparency report published",
    ]

    SG_AGENT_CLAIMS = [
        "Agent decision explainability documentation maintained",
        "Human-centric design principles verified",
        "AI governance framework compliance confirmed",
        "Transparency measures for agent actions documented",
    ]

    def test_hk_pdbo_confidence_calibration(self) -> dict:
        calibrator = ConfidenceCalibrator()
        results = []
        for claim in self.HK_PDPO_CLAIMS:
            score = calibrator.calibrate(claim, ["official_doc: PDPO guidelines"])
            results.append({
                "claim": claim,
                "level": score.level.value,
                "score": score.score,
            })
        return {"region": "HK", "results": results}

    def test_cn_pipl_uncertainty_quantification(self) -> dict:
        engine = MetacognitiveReflectionEngine()
        result = engine.reflect(self.CN_PIPL_CLAIMS)
        uncertain_count = sum(
            1 for cs in result.evaluated_claims
            if cs.level in (ConfidenceLevel.SPECULATIVE, ConfidenceLevel.UNCERTAIN)
        )
        return {
            "region": "CN",
            "total": len(self.CN_PIPL_CLAIMS),
            "uncertain": uncertain_count,
            "requires_mitigation": uncertain_count > 0,
        }

    def test_eu_ai_act_transparency_verification(self) -> dict:
        engine = MetacognitiveReflectionEngine()
        kb = {
            "ai_transparency": "EU AI Act requires transparency for high-risk AI systems",
            "conformity_assessment": "High-risk AI requires conformity assessment per Annex VII",
        }
        result = engine.reflect(self.EU_AI_ACT_CLAIMS, kb)
        verified_count = sum(
            1 for cs in result.evaluated_claims
            if cs.level == ConfidenceLevel.VERIFIED
        )
        return {
            "region": "EU",
            "verified": verified_count,
            "total": len(self.EU_AI_ACT_CLAIMS),
            "compliance_ready": verified_count >= 2,
        }

    def test_sg_agent_governance_reflection(self) -> dict:
        engine = MetacognitiveReflectionEngine()
        kb = {
            "agent_transparency": "Singapore Model AI Framework requires transparency",
            "human_centric": "Agent AI must be human-centric per IMDA guidelines",
        }
        result = engine.reflect(self.SG_AGENT_CLAIMS, kb)
        return {
            "region": "SG",
            "final_confidence": result.final_confidence_avg,
            "convergence": result.convergence_achieved,
            "recommendations": result.revisions_made[:2] if result.revisions_made else [],
        }

    def run_all_regional_tests(self) -> dict:
        results = {
            "metacognitive_reflection_engine": {
                "HK_PDPO": self.test_hk_pdbo_confidence_calibration(),
                "CN_PIPL": self.test_cn_pipl_uncertainty_quantification(),
                "EU_AI_Act": self.test_eu_ai_act_transparency_verification(),
                "SG_Agent": self.test_sg_agent_governance_reflection(),
            }
        }
        return results
