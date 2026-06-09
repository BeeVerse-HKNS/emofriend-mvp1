from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class CausalityStrength(str, Enum):
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    SPECULATIVE = "speculative"


class AbstractionLevel(str, Enum):
    CONCRETE = "concrete"
    OPERATIONAL = "operational"
    STRATEGIC = "strategic"
    VISIONARY = "visionary"


ABSTRACTION_ORDER: list[AbstractionLevel] = [
    AbstractionLevel.CONCRETE,
    AbstractionLevel.OPERATIONAL,
    AbstractionLevel.STRATEGIC,
    AbstractionLevel.VISIONARY,
]


@dataclass
class Observation:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    event: str = ""
    context: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    observed_outcome: str = ""


@dataclass
class CausalRelation:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    cause: str = ""
    effect: str = ""
    strength: CausalityStrength = CausalityStrength.SPECULATIVE
    confidence: float = 0.0
    evidence_count: int = 0
    is_verified: bool = False


@dataclass
class CounterfactualResult:
    original_scenario: dict[str, Any] = field(default_factory=dict)
    alternative_scenario: dict[str, Any] = field(default_factory=dict)
    original_outcome: str = ""
    alternative_outcome: str = ""
    confidence: float = 0.0
    reasoning: str = ""


@dataclass
class DependencyMap:
    action_id: str = ""
    causal_dependencies: list[str] = field(default_factory=list)
    affected_actions: list[str] = field(default_factory=list)
    dependency_depth: int = 0


@dataclass
class InterventionResult:
    intervention: str = ""
    affected_actions: list[str] = field(default_factory=list)
    predicted_outcomes: dict[str, float] = field(default_factory=dict)
    side_effects: list[str] = field(default_factory=list)
    confidence: float = 0.0


@dataclass
class CausalAnalysisResult:
    causal_relations: list[CausalRelation] = field(default_factory=list)
    root_causes: list[str] = field(default_factory=list)
    downstream_effects: list[str] = field(default_factory=list)
    counterfactuals: list[CounterfactualResult] = field(default_factory=list)
    interventions: list[InterventionResult] = field(default_factory=list)


def _confidence_to_strength(confidence: float) -> CausalityStrength:
    if confidence >= 0.8:
        return CausalityStrength.STRONG
    if confidence >= 0.5:
        return CausalityStrength.MODERATE
    if confidence >= 0.25:
        return CausalityStrength.WEAK
    return CausalityStrength.SPECULATIVE


class CausalDiscovery:
    def __init__(self):
        self._relations: list[CausalRelation] = []
        self._co_occurrence: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._temporal_order: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.logger = logging.getLogger(__name__)

    def observe(self, observations: list[Observation]) -> list[CausalRelation]:
        if not observations:
            return []

        sorted_obs = sorted(observations, key=lambda o: o.timestamp)

        for i, obs in enumerate(sorted_obs):
            for j in range(i + 1, len(sorted_obs)):
                later = sorted_obs[j]
                if obs.event == later.event:
                    continue
                try:
                    dt_obs = datetime.fromisoformat(obs.timestamp)
                    dt_later = datetime.fromisoformat(later.timestamp)
                    diff = (dt_later - dt_obs).total_seconds()
                except (ValueError, TypeError):
                    diff = float(j - i)

                if diff > 5:
                    break

                self._co_occurrence[obs.event][later.event] += 1
                if j == i + 1:
                    self._temporal_order[obs.event][later.event] += 1

        new_relations = self._infer_relations()
        self._relations.extend(new_relations)
        return new_relations

    def _infer_relations(self) -> list[CausalRelation]:
        relations: list[CausalRelation] = []
        seen: set[tuple[str, str]] = set()

        for cause, effects in self._co_occurrence.items():
            total_cause = sum(effects.values())
            for effect, count in effects.items():
                temporal_count = self._temporal_order[cause].get(effect, 0)
                if count < 2:
                    continue

                co_occurrence_rate = count / max(total_cause, 1)
                temporal_rate = temporal_count / max(count, 1)
                confidence = co_occurrence_rate * 0.4 + temporal_rate * 0.6

                key = (cause, effect)
                if key in seen:
                    continue
                seen.add(key)

                existing = self._find_relation(cause, effect)
                if existing:
                    existing.evidence_count += count
                    existing.confidence = min(confidence * (1 + existing.evidence_count * 0.05), 1.0)
                    existing.strength = _confidence_to_strength(existing.confidence)
                    existing.is_verified = existing.confidence >= 0.7 and existing.evidence_count >= 5
                    continue

                rel = CausalRelation(
                    cause=cause,
                    effect=effect,
                    strength=_confidence_to_strength(confidence),
                    confidence=round(confidence, 4),
                    evidence_count=count,
                    is_verified=confidence >= 0.7 and count >= 5,
                )
                relations.append(rel)

        return relations

    def _find_relation(self, cause: str, effect: str) -> CausalRelation | None:
        for r in self._relations:
            if r.cause == cause and r.effect == effect:
                return r
        return None

    def verify_cause(self, cause: str, effect: str, observations: list[Observation]) -> CausalRelation | None:
        cause_obs = sorted([o for o in observations if o.event == cause], key=lambda o: o.timestamp)
        effect_obs = sorted([o for o in observations if o.event == effect], key=lambda o: o.timestamp)

        if not cause_obs or not effect_obs:
            return None

        cause_with_effect = 0
        cause_without_effect = 0
        no_cause_with_effect = 0

        cause_times = [o.timestamp for o in cause_obs]
        effect_times = [o.timestamp for o in effect_obs]

        for ct in cause_times:
            has_followup = any(et > ct for et in effect_times)
            if has_followup:
                cause_with_effect += 1
            else:
                cause_without_effect += 1

        for et in effect_times:
            has_preceding = any(ct < et for ct in cause_times)
            if not has_preceding:
                no_cause_with_effect += 1

        total = cause_with_effect + cause_without_effect
        if total == 0:
            return None

        p_cause_effect = cause_with_effect / max(total, 1)
        total_no_cause = no_cause_with_effect + max(len(observations) - len(cause_obs) - no_cause_with_effect, 0)
        p_no_cause_effect = no_cause_with_effect / max(total_no_cause, 1)

        if p_cause_effect <= p_no_cause_effect:
            return None

        confidence = p_cause_effect * (1 - p_no_cause_effect)
        evidence_count = cause_with_effect

        existing = self._find_relation(cause, effect)
        if existing:
            existing.confidence = min(confidence, 1.0)
            existing.evidence_count += evidence_count
            existing.strength = _confidence_to_strength(existing.confidence)
            existing.is_verified = existing.confidence >= 0.7 and existing.evidence_count >= 5
            return existing

        rel = CausalRelation(
            cause=cause,
            effect=effect,
            strength=_confidence_to_strength(confidence),
            confidence=round(confidence, 4),
            evidence_count=evidence_count,
            is_verified=confidence >= 0.7 and evidence_count >= 5,
        )
        self._relations.append(rel)
        return rel

    def get_causes_of(self, effect: str) -> list[CausalRelation]:
        return [r for r in self._relations if r.effect == effect]

    @property
    def relations(self) -> list[CausalRelation]:
        return list(self._relations)


class CounterfactualReasoner:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def reason(
        self,
        original: dict[str, Any],
        alternative: dict[str, Any],
        causal_relations: list[CausalRelation],
    ) -> CounterfactualResult:
        original_outcome = self._predict_outcome(original, causal_relations)
        alternative_outcome = self._predict_outcome(alternative, causal_relations)

        changed_keys = set(original.keys()) | set(alternative.keys())
        changed_keys = {k for k in changed_keys if original.get(k) != alternative.get(k)}

        affected_relations = [
            r for r in causal_relations
            if r.cause in changed_keys or r.effect in changed_keys
        ]

        if affected_relations:
            confidence = sum(r.confidence for r in affected_relations) / len(affected_relations)
        else:
            confidence = 0.1

        reasoning_parts = []
        for key in changed_keys:
            orig_val = original.get(key, "absent")
            alt_val = alternative.get(key, "absent")
            reasoning_parts.append(f"{key}: {orig_val} -> {alt_val}")

        for rel in affected_relations:
            reasoning_parts.append(
                f"Causal: {rel.cause} -> {rel.effect} (strength={rel.strength.value}, conf={rel.confidence:.2f})"
            )

        return CounterfactualResult(
            original_scenario=original,
            alternative_scenario=alternative,
            original_outcome=original_outcome,
            alternative_outcome=alternative_outcome,
            confidence=round(confidence, 4),
            reasoning="; ".join(reasoning_parts),
        )

    def _predict_outcome(self, scenario: dict[str, Any], causal_relations: list[CausalRelation]) -> str:
        active_effects: list[str] = []
        for rel in causal_relations:
            if rel.cause in scenario and scenario[rel.cause]:
                active_effects.append(rel.effect)

        if not active_effects:
            return "neutral"

        return "+".join(sorted(set(active_effects)))

    def generate_alternatives(self, scenario: dict[str, Any], num_alternatives: int = 3) -> list[dict[str, Any]]:
        alternatives: list[dict[str, Any]] = []
        keys = list(scenario.keys())

        if not keys:
            return alternatives

        for i in range(num_alternatives):
            alt = dict(scenario)
            idx = i % len(keys)
            key = keys[idx]
            current = alt[key]
            if isinstance(current, bool):
                alt[key] = not current
            elif isinstance(current, (int, float)):
                alt[key] = current * -1 if current != 0 else 1
            elif isinstance(current, str):
                alt[key] = f"not_{current}" if not current.startswith("not_") else current[4:]
            else:
                alt[key] = None
            alternatives.append(alt)

        return alternatives

    def evaluate_what_if(
        self, cause_removed: str, causal_relations: list[CausalRelation]
    ) -> CounterfactualResult:
        affected = [r for r in causal_relations if r.cause == cause_removed]

        original_effects = [r.effect for r in affected]
        original_outcome = "+".join(sorted(set(original_effects))) if original_effects else "neutral"

        if affected:
            confidence = sum(r.confidence for r in affected) / len(affected)
        else:
            confidence = 0.0

        reasoning_parts = [f"Removing cause: {cause_removed}"]
        for rel in affected:
            reasoning_parts.append(
                f"Effect '{rel.effect}' loses causal support (was {rel.strength.value}, conf={rel.confidence:.2f})"
            )

        return CounterfactualResult(
            original_scenario={"cause_present": cause_removed},
            alternative_scenario={"cause_removed": cause_removed},
            original_outcome=original_outcome,
            alternative_outcome="neutral",
            confidence=round(confidence, 4),
            reasoning="; ".join(reasoning_parts),
        )


class DependencyAnalyzer:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def analyze(self, action_id: str, causal_relations: list[CausalRelation]) -> DependencyMap:
        dependencies = self._find_upstream(action_id, causal_relations)
        affected = self._find_downstream(action_id, causal_relations)
        depth = self._compute_depth(action_id, causal_relations)

        return DependencyMap(
            action_id=action_id,
            causal_dependencies=dependencies,
            affected_actions=affected,
            dependency_depth=depth,
        )

    def _find_upstream(self, action_id: str, relations: list[CausalRelation]) -> list[str]:
        visited: set[str] = set()
        result: list[str] = []

        def _walk(current: str):
            for rel in relations:
                if rel.effect == current and rel.cause not in visited:
                    visited.add(rel.cause)
                    result.append(rel.cause)
                    _walk(rel.cause)

        _walk(action_id)
        return result

    def _find_downstream(self, action_id: str, relations: list[CausalRelation]) -> list[str]:
        visited: set[str] = set()
        result: list[str] = []

        def _walk(current: str):
            for rel in relations:
                if rel.cause == current and rel.effect not in visited:
                    visited.add(rel.effect)
                    result.append(rel.effect)
                    _walk(rel.effect)

        _walk(action_id)
        return result

    def _compute_depth(self, action_id: str, relations: list[CausalRelation]) -> int:
        max_depth = 0
        visited: set[str] = set()

        def _walk(current: str, depth: int) -> int:
            nonlocal max_depth
            if current in visited:
                return depth
            visited.add(current)
            found = False
            for rel in relations:
                if rel.effect == current and rel.cause not in visited:
                    found = True
                    d = _walk(rel.cause, depth + 1)
                    max_depth = max(max_depth, d)
            visited.discard(current)
            return depth + 1 if found else depth

        _walk(action_id, 0)
        return max_depth

    def find_root_causes(self, effect: str, causal_relations: list[CausalRelation]) -> list[str]:
        all_causes: set[str] = set()
        visited: set[str] = set()

        def _trace(current: str):
            if current in visited:
                return
            visited.add(current)
            direct_causes = [r.cause for r in causal_relations if r.effect == current]
            if not direct_causes:
                all_causes.add(current)
                return
            for cause in direct_causes:
                _trace(cause)

        _trace(effect)
        return sorted(all_causes)

    def find_downstream_effects(self, cause: str, causal_relations: list[CausalRelation]) -> list[str]:
        return self._find_downstream(cause, causal_relations)


class AbstractionNavigator:
    def __init__(self):
        self._hierarchy: dict[str, dict[AbstractionLevel, list[str]]] = {}
        self.logger = logging.getLogger(__name__)

    def navigate_to_level(
        self,
        entity: str,
        current_level: AbstractionLevel,
        target_level: AbstractionLevel,
        world_context: dict[str, Any],
    ) -> list[str]:
        if current_level == target_level:
            return [entity]

        current_idx = ABSTRACTION_ORDER.index(current_level)
        target_idx = ABSTRACTION_ORDER.index(target_level)

        if target_idx > current_idx:
            return self.zoom_out(entity, current_level)
        else:
            return self.zoom_in(entity, current_level)

    def zoom_in(self, entity: str, level: AbstractionLevel) -> list[str]:
        idx = ABSTRACTION_ORDER.index(level)
        if idx == 0:
            return [entity]

        lower_level = ABSTRACTION_ORDER[idx - 1]
        components = self._decompose(entity, level, lower_level)
        return components

    def zoom_out(self, entity: str, level: AbstractionLevel) -> list[str]:
        idx = ABSTRACTION_ORDER.index(level)
        if idx == len(ABSTRACTION_ORDER) - 1:
            return [entity]

        higher_level = ABSTRACTION_ORDER[idx + 1]
        parent = self._abstract(entity, level, higher_level)
        return [parent]

    def get_available_levels(self, entity: str) -> list[AbstractionLevel]:
        return list(ABSTRACTION_ORDER)

    def _decompose(self, entity: str, from_level: AbstractionLevel, to_level: AbstractionLevel) -> list[str]:
        decomposition_map: dict[AbstractionLevel, dict[str, list[str]]] = {
            AbstractionLevel.OPERATIONAL: {
                "system": ["module_a", "module_b", "module_c"],
                "process": ["step_1", "step_2", "step_3"],
                "strategy": ["tactic_1", "tactic_2"],
            },
            AbstractionLevel.STRATEGIC: {
                "organization": ["system", "process", "strategy"],
                "vision": ["strategy_1", "strategy_2"],
            },
            AbstractionLevel.VISIONARY: {
                "ecosystem": ["organization", "vision"],
            },
        }

        level_map = decomposition_map.get(from_level, {})
        for key, components in level_map.items():
            if entity == key or entity in key:
                return components

        return [f"{entity}_{to_level.value}_component_{i}" for i in range(1, 4)]

    def _abstract(self, entity: str, from_level: AbstractionLevel, to_level: AbstractionLevel) -> str:
        abstraction_map: dict[AbstractionLevel, dict[str, str]] = {
            AbstractionLevel.CONCRETE: {
                "module_a": "system",
                "module_b": "system",
                "module_c": "system",
                "step_1": "process",
                "step_2": "process",
                "step_3": "process",
                "tactic_1": "strategy",
                "tactic_2": "strategy",
            },
            AbstractionLevel.OPERATIONAL: {
                "system": "organization",
                "process": "organization",
                "strategy": "vision",
            },
            AbstractionLevel.STRATEGIC: {
                "organization": "ecosystem",
                "vision": "ecosystem",
            },
        }

        level_map = abstraction_map.get(from_level, {})
        if entity in level_map:
            return level_map[entity]

        return f"{to_level.value}_of_{entity}"


class InterventionSimulator:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def simulate(self, intervention: str, causal_relations: list[CausalRelation]) -> InterventionResult:
        affected = self._find_affected(intervention, causal_relations)
        outcomes = self._predict_outcomes(intervention, affected, causal_relations)
        side_effects = self.estimate_side_effects(intervention, causal_relations)

        if outcomes:
            confidence = sum(outcomes.values()) / len(outcomes)
        else:
            confidence = 0.0

        return InterventionResult(
            intervention=intervention,
            affected_actions=affected,
            predicted_outcomes=outcomes,
            side_effects=side_effects,
            confidence=round(confidence, 4),
        )

    def compare_interventions(
        self, interventions: list[str], causal_relations: list[CausalRelation]
    ) -> list[InterventionResult]:
        results = []
        for intervention in interventions:
            result = self.simulate(intervention, causal_relations)
            results.append(result)
        results.sort(key=lambda r: r.confidence, reverse=True)
        return results

    def estimate_side_effects(self, intervention: str, causal_relations: list[CausalRelation]) -> list[str]:
        downstream = []
        visited: set[str] = set()

        def _walk(current: str, depth: int):
            if current in visited or depth > 5:
                return
            visited.add(current)
            for rel in causal_relations:
                if rel.cause == current:
                    downstream.append(rel.effect)
                    _walk(rel.effect, depth + 1)

        _walk(intervention, 0)

        direct_effects = {r.effect for r in causal_relations if r.cause == intervention}
        side_effects = [e for e in downstream if e not in direct_effects]
        return list(dict.fromkeys(side_effects))

    def _find_affected(self, intervention: str, relations: list[CausalRelation]) -> list[str]:
        affected: list[str] = []
        visited: set[str] = set()

        def _walk(current: str):
            if current in visited:
                return
            visited.add(current)
            for rel in relations:
                if rel.cause == current and rel.effect not in visited:
                    affected.append(rel.effect)
                    _walk(rel.effect)

        _walk(intervention)
        return affected

    def _predict_outcomes(
        self, intervention: str, affected: list[str], relations: list[CausalRelation]
    ) -> dict[str, float]:
        outcomes: dict[str, float] = {}
        for target in affected:
            path_confidence = self._compute_path_confidence(intervention, target, relations)
            if path_confidence > 0:
                outcomes[target] = round(path_confidence, 4)
        return outcomes

    def _compute_path_confidence(
        self, source: str, target: str, relations: list[CausalRelation], visited: set[str] | None = None
    ) -> float:
        if visited is None:
            visited = set()

        if source == target:
            return 1.0

        if source in visited:
            return 0.0

        visited = visited | {source}

        best_confidence = 0.0
        for rel in relations:
            if rel.cause == source:
                sub_confidence = self._compute_path_confidence(rel.effect, target, relations, visited)
                if sub_confidence > 0:
                    path_conf = rel.confidence * sub_confidence
                    best_confidence = max(best_confidence, path_conf)

        return best_confidence


class CausalReasoningEngine:
    def __init__(self):
        self.causal_discovery = CausalDiscovery()
        self.counterfactual = CounterfactualReasoner()
        self.dependency = DependencyAnalyzer()
        self.abstraction = AbstractionNavigator()
        self.intervention = InterventionSimulator()
        self.logger = logging.getLogger(__name__)

    def analyze_causally(self, observations: list[Observation]) -> CausalAnalysisResult:
        if not observations:
            return CausalAnalysisResult()

        causal_relations = self.causal_discovery.observe(observations)

        all_causes = {r.cause for r in causal_relations}
        all_effects = {r.effect for r in causal_relations}

        root_causes: list[str] = []
        pure_causes = all_causes - all_effects
        root_causes.extend(sorted(pure_causes))

        for effect in all_effects:
            roots = self.dependency.find_root_causes(effect, causal_relations)
            root_causes.extend(roots)
        root_causes = sorted(set(root_causes))

        downstream_effects: list[str] = []
        for cause in all_causes:
            effects = self.dependency.find_downstream_effects(cause, causal_relations)
            downstream_effects.extend(effects)
        downstream_effects = sorted(set(downstream_effects))

        counterfactuals: list[CounterfactualResult] = []
        for rel in causal_relations[:5]:
            cf = self.counterfactual.evaluate_what_if(rel.cause, causal_relations)
            counterfactuals.append(cf)

        interventions: list[InterventionResult] = []
        for cause in root_causes[:5]:
            result = self.intervention.simulate(cause, causal_relations)
            interventions.append(result)

        return CausalAnalysisResult(
            causal_relations=causal_relations,
            root_causes=root_causes,
            downstream_effects=downstream_effects,
            counterfactuals=counterfactuals,
            interventions=interventions,
        )


class RegionalCausalMixin:
    HK_LAR_OBSERVATIONS = [
        {"event": "automated_decision", "outcome": "credit_approval_denied"},
        {"event": "data_used", "outcome": "personal_info_processed"},
        {"event": "cross_border_transfer", "outcome": "data_sent_overseas"},
    ]

    CN_LIABILITY_OBSERVATIONS = [
        {"event": "ai_generated_content", "outcome": "content_published"},
        {"event": "algorithmic_recommendation", "outcome": "user_exposure"},
        {"event": "automated_decision", "outcome": "service_denied"},
    ]

    EU_INTERVENTION_OBSERVATIONS = [
        {"event": "high_risk_ai_active", "outcome": "requires_human_oversight"},
        {"event": "automated_decision", "outcome": "legal_effects"},
        {"event": "profiling_active", "outcome": "data_subject_rights"},
    ]

    SG_ACCOUNTABILITY_OBSERVATIONS = [
        {"event": "agent_action", "outcome": "decision_made"},
        {"event": "human_oversight", "outcome": "review_completed"},
        {"event": "explainability_request", "outcome": "reasoning_provided"},
    ]

    def test_hk_legal_implications(self) -> dict:
        engine = CausalReasoningEngine()
        obs = [Observation(event=o["event"], observed_outcome=o["outcome"]) for o in self.HK_LAR_OBSERVATIONS]
        result = engine.analyze_causally(obs)
        has_legal_causal = any(
            "data" in r.cause.lower() or "decision" in r.effect.lower()
            for r in result.causal_relations
        )
        return {
            "region": "HK",
            "causal_relations_found": len(result.causal_relations),
            "root_causes": result.root_causes,
            "legal_implications_tracked": has_legal_causal,
        }

    def test_cn_liability_attribution(self) -> dict:
        engine = CausalReasoningEngine()
        obs = [Observation(event=o["event"], observed_outcome=o["outcome"]) for o in self.CN_LIABILITY_OBSERVATIONS]
        result = engine.analyze_causally(obs)
        has_interventions = len(result.interventions) > 0
        downstream = len(result.downstream_effects)
        return {
            "region": "CN",
            "downstream_effects_tracked": downstream,
            "intervention_needed": has_interventions,
            "liability_attribution": downstream > 0,
        }

    def test_eu_intervention_restrictions(self) -> dict:
        engine = CausalReasoningEngine()
        obs = [Observation(event=o["event"], observed_outcome=o["outcome"]) for o in self.EU_INTERVENTION_OBSERVATIONS]
        result = engine.analyze_causally(obs)
        has_oversight_causal = any(
            "oversight" in r.cause.lower() or "rights" in r.effect.lower()
            for r in result.causal_relations
        )
        return {
            "region": "EU",
            "high_risk_causal_chains": len(result.causal_relations),
            "human_oversight_tracked": has_oversight_causal,
            "requires_intervention": has_oversight_causal,
        }

    def test_sg_agent_accountability(self) -> dict:
        engine = CausalReasoningEngine()
        obs = [Observation(event=o["event"], observed_outcome=o["outcome"]) for o in self.SG_ACCOUNTABILITY_OBSERVATIONS]
        result = engine.analyze_causally(obs)
        agent_action = any("agent" in r.cause.lower() for r in result.causal_relations)
        has_explainability = any("reasoning" in r.effect.lower() or "provided" in r.effect.lower() for r in result.causal_relations)
        return {
            "region": "SG",
            "agent_actions_tracked": agent_action,
            "explainability_required": has_explainability,
            "accountability_chain": len(result.causal_relations) > 0,
        }

    def test_counterfactual_reasoning_regional(self) -> dict:
        engine = CausalReasoningEngine()
        obs = [Observation(event="data_transfer", observed_outcome="cross_border"), Observation(event="no_transfer", observed_outcome="local_only")]
        relations = engine.causal_discovery.observe(obs)
        if relations:
            cf = engine.counterfactual.reason({}, {"transfer": "removed"}, relations)
            return {
                "counterfactual_works": cf.confidence > 0,
                "confidence": cf.confidence,
            }
        return {"counterfactual_works": False, "confidence": 0.0}

    def run_all_regional_tests(self) -> dict:
        return {
            "causal_reasoning_engine": {
                "HK_LAR": self.test_hk_legal_implications(),
                "CN_Liability": self.test_cn_liability_attribution(),
                "EU_Intervention": self.test_eu_intervention_restrictions(),
                "SG_Accountability": self.test_sg_agent_accountability(),
                "Counterfactual": self.test_counterfactual_reasoning_regional(),
            }
        }
