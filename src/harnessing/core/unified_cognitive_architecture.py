from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from harnessing.core.attention_budget_manager import AttentionBudgetManager
from harnessing.core.causal_reasoning_engine import (
    CausalAnalysisResult,
    CausalReasoningEngine,
    Observation,
)
from harnessing.core.circular_thinking_engine import (
    ActionNode,
    CircularAnalysisResult,
    CircularThinkingEngine,
)
from harnessing.core.cross_folder_memory_bridge import CrossFolderMemoryBridge
from harnessing.core.metacognitive_reflection_engine import (
    MetacognitiveReflectionEngine,
    MetacognitiveResult,
)
from harnessing.core.world_model_constructor import WorldModelConstructor


class ThinkingMode(str, Enum):
    FAST = "FAST"
    SLOW = "SLOW"
    CIRCULAR = "CIRCULAR"
    CAUSAL = "CAUSAL"
    METACOGNITIVE = "METACOGNITIVE"
    FULL = "FULL"


@dataclass
class EngineOutput:
    engine_name: str
    output_data: dict
    confidence: float
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass
class SynergyEffect:
    source_engines: list[str]
    synergy_type: str
    description: str
    combined_confidence: float


@dataclass
class CognitiveState:
    active_mode: ThinkingMode
    active_engines: list[str]
    iteration_count: int
    convergence_score: float
    total_confidence: float


@dataclass
class CognitiveResult:
    task: str
    mode_used: ThinkingMode
    engine_outputs: list[EngineOutput]
    synergy_effects: list[SynergyEffect]
    convergence_achieved: bool
    final_confidence: float
    iterations: int
    recommendations: list[str]


_ENGINE_NAMES = [
    "circular_thinking",
    "cross_folder_memory",
    "metacognitive_reflection",
    "world_model",
    "causal_reasoning",
    "attention_budget",
]

_MODE_ENGINE_MAP: dict[ThinkingMode, list[str]] = {
    ThinkingMode.FAST: ["attention_budget"],
    ThinkingMode.SLOW: [
        "attention_budget",
        "metacognitive_reflection",
        "world_model",
    ],
    ThinkingMode.CIRCULAR: [
        "circular_thinking",
        "cross_folder_memory",
        "attention_budget",
    ],
    ThinkingMode.CAUSAL: [
        "causal_reasoning",
        "world_model",
        "attention_budget",
    ],
    ThinkingMode.METACOGNITIVE: [
        "metacognitive_reflection",
        "circular_thinking",
        "attention_budget",
    ],
    ThinkingMode.FULL: list(_ENGINE_NAMES),
}


class ThinkingModeSelector:
    _TASK_KEYWORDS: dict[str, list[str]] = {
        "simple": ["lookup", "fetch", "read", "get", "list", "check"],
        "complex": ["analyze", "design", "architect", "plan", "evaluate", "compare"],
        "interdependent": [
            "integrate",
            "coordinate",
            "orchestrate",
            "ripple",
            "cascade",
            "interconnect",
        ],
        "causal": ["cause", "effect", "why", "root", "consequence", "predict"],
        "quality": ["verify", "validate", "review", "audit", "confidence", "reflect"],
        "full": ["comprehensive", "full", "deep", "thorough", "exhaustive"],
    }

    def select(
        self, task_type: str, complexity: str, interdependency_level: str
    ) -> ThinkingMode:
        task_lower = task_type.lower()
        complexity_lower = complexity.lower()
        interdep_lower = interdependency_level.lower()

        for keyword in self._TASK_KEYWORDS["full"]:
            if keyword in task_lower:
                return ThinkingMode.FULL

        if interdep_lower in ("high", "very_high"):
            return ThinkingMode.CIRCULAR

        for keyword in self._TASK_KEYWORDS["causal"]:
            if keyword in task_lower:
                return ThinkingMode.CAUSAL

        for keyword in self._TASK_KEYWORDS["quality"]:
            if keyword in task_lower:
                return ThinkingMode.METACOGNITIVE

        if complexity_lower in ("high", "very_high"):
            return ThinkingMode.SLOW

        for keyword in self._TASK_KEYWORDS["interdependent"]:
            if keyword in task_lower:
                return ThinkingMode.CIRCULAR

        for keyword in self._TASK_KEYWORDS["complex"]:
            if keyword in task_lower:
                return ThinkingMode.SLOW

        return ThinkingMode.FAST


class CognitiveOrchestrator:
    def __init__(self) -> None:
        self._active_engines: set[str] = set()
        self._mode: ThinkingMode = ThinkingMode.FAST

    def select_mode(self, task_description: str, complexity: str) -> ThinkingMode:
        selector = ThinkingModeSelector()
        interdep = "high" if any(
            w in task_description.lower()
            for w in ["interact", "depend", "connect", "affect", "cascade"]
        ) else "low"
        self._mode = selector.select(task_description, complexity, interdep)
        self._activate_for_mode(self._mode)
        return self._mode

    def activate_engine(self, engine_name: str) -> bool:
        if engine_name not in _ENGINE_NAMES:
            return False
        self._active_engines.add(engine_name)
        return True

    def deactivate_engine(self, engine_name: str) -> bool:
        if engine_name not in self._active_engines:
            return False
        self._active_engines.discard(engine_name)
        return True

    def get_active_engines(self) -> list[str]:
        return sorted(self._active_engines)

    def set_mode(self, mode: ThinkingMode) -> None:
        self._mode = mode
        self._activate_for_mode(mode)

    def _activate_for_mode(self, mode: ThinkingMode) -> None:
        engines = _MODE_ENGINE_MAP.get(mode, [])
        self._active_engines = set(engines)


class FeedbackAmplifier:
    _SYNERGY_RULES: list[tuple[str, str, str, str]] = [
        (
            "metacognitive_reflection",
            "circular_thinking",
            "AMPLIFY",
            "Metacognitive confidence scores improve circular convergence detection",
        ),
        (
            "circular_thinking",
            "causal_reasoning",
            "COMPLEMENT",
            "Circular dependency maps enrich causal chain discovery",
        ),
        (
            "world_model",
            "causal_reasoning",
            "AMPLIFY",
            "World model entities provide grounding for causal relations",
        ),
        (
            "cross_folder_memory",
            "metacognitive_reflection",
            "COMPLEMENT",
            "Cross-folder context supplies evidence for confidence calibration",
        ),
        (
            "metacognitive_reflection",
            "causal_reasoning",
            "COMPLEMENT",
            "Confidence scores validate causal relation strength",
        ),
        (
            "circular_thinking",
            "world_model",
            "COMPLEMENT",
            "Circular actions map to world model entities for richer analysis",
        ),
        (
            "attention_budget",
            "metacognitive_reflection",
            "AMPLIFY",
            "Attention budget prioritizes high-confidence claims for reflection",
        ),
        (
            "attention_budget",
            "causal_reasoning",
            "COMPLEMENT",
            "Attention budget focuses causal analysis on relevant observations",
        ),
    ]

    def amplify(self, engine_outputs: list[EngineOutput]) -> list[SynergyEffect]:
        if len(engine_outputs) < 2:
            return []

        effects: list[SynergyEffect] = []
        output_map = {o.engine_name: o for o in engine_outputs}

        for src, tgt, syn_type, desc in self._SYNERGY_RULES:
            if src in output_map and tgt in output_map:
                src_conf = output_map[src].confidence
                tgt_conf = output_map[tgt].confidence
                combined = min(1.0, (src_conf + tgt_conf) / 2 * 1.15)
                effects.append(
                    SynergyEffect(
                        source_engines=[src, tgt],
                        synergy_type=syn_type,
                        description=desc,
                        combined_confidence=round(combined, 4),
                    )
                )

        self._detect_contradictions(engine_outputs, effects)
        return effects

    def feed_forward(
        self, from_engine: str, to_engine: str, output: EngineOutput
    ) -> dict:
        feed_data: dict[str, Any] = {
            "source": from_engine,
            "target": to_engine,
            "confidence_hint": output.confidence,
            "data_keys": list(output.output_data.keys()),
        }

        if from_engine == "metacognitive_reflection" and to_engine == "circular_thinking":
            feed_data["confidence_adjustment"] = output.confidence
            feed_data["suggestion"] = "adjust_convergence_threshold"
        elif from_engine == "circular_thinking" and to_engine == "causal_reasoning":
            deps = output.output_data.get("inter_dependency_map", {})
            feed_data["dependency_context"] = deps
            feed_data["suggestion"] = "enrich_observations"
        elif from_engine == "world_model" and to_engine == "causal_reasoning":
            entities = output.output_data.get("total_entities", 0)
            feed_data["entity_count"] = entities
            feed_data["suggestion"] = "ground_causal_relations"
        elif from_engine == "attention_budget" and to_engine == "metacognitive_reflection":
            feed_data["suggestion"] = "prioritize_high_relevance_claims"
        elif from_engine == "cross_folder_memory" and to_engine == "metacognitive_reflection":
            feed_data["suggestion"] = "inject_kb_evidence"

        return feed_data

    def _detect_contradictions(
        self, outputs: list[EngineOutput], effects: list[SynergyEffect]
    ) -> None:
        output_map = {o.engine_name: o for o in outputs}
        if (
            "metacognitive_reflection" in output_map
            and "causal_reasoning" in output_map
        ):
            meta_conf = output_map["metacognitive_reflection"].confidence
            causal_conf = output_map["causal_reasoning"].confidence
            if abs(meta_conf - causal_conf) > 0.4:
                effects.append(
                    SynergyEffect(
                        source_engines=["metacognitive_reflection", "causal_reasoning"],
                        synergy_type="CONTRADICT",
                        description=f"Confidence divergence: metacognitive={meta_conf:.2f} vs causal={causal_conf:.2f}",
                        combined_confidence=round(min(meta_conf, causal_conf), 4),
                    )
                )


class ConvergenceMonitor:
    def __init__(self, stability_window: int = 3, stability_threshold: float = 0.02):
        self._history: list[CognitiveState] = []
        self._convergence_trend: list[float] = []
        self._stability_window = stability_window
        self._stability_threshold = stability_threshold

    def check_convergence(self, states: list[CognitiveState]) -> bool:
        if not states:
            return False

        if len(states) == 1:
            return states[0].convergence_score >= 0.9

        recent = states[-self._stability_window :]
        if len(recent) < 2:
            return recent[-1].convergence_score >= 0.9

        scores = [s.convergence_score for s in recent]
        variance = sum((s - sum(scores) / len(scores)) ** 2 for s in scores) / len(
            scores
        )

        self._convergence_trend.append(states[-1].convergence_score)

        return variance <= self._stability_threshold and states[-1].convergence_score >= 0.8

    def get_convergence_trend(self) -> list[float]:
        return list(self._convergence_trend)

    def is_stable(self) -> bool:
        if len(self._convergence_trend) < self._stability_window:
            return False
        recent = self._convergence_trend[-self._stability_window :]
        variance = sum((s - sum(recent) / len(recent)) ** 2 for s in recent) / len(
            recent
        )
        return variance <= self._stability_threshold

    def record_state(self, state: CognitiveState) -> None:
        self._history.append(state)
        self._convergence_trend.append(state.convergence_score)

    def reset(self) -> None:
        self._history.clear()
        self._convergence_trend.clear()


class UnifiedCognitiveArchitecture:
    FORMULA = "log(sq(R)*Q) + log(M*W) + (R^D)-U + G/A"

    def __init__(self, project_dir: str | None = None) -> None:
        self.circular_engine = CircularThinkingEngine()
        self.memory_bridge = CrossFolderMemoryBridge(
            project_dir or "."
        )
        self.metacognitive_engine = MetacognitiveReflectionEngine()
        self.world_model = WorldModelConstructor()
        self.causal_engine = CausalReasoningEngine()
        self.attention_manager = AttentionBudgetManager()

        self.orchestrator = CognitiveOrchestrator()
        self.mode_selector = ThinkingModeSelector()
        self.feedback_amplifier = FeedbackAmplifier()
        self.convergence_monitor = ConvergenceMonitor()

        self._state_history: list[CognitiveState] = []
        self._iteration_count: int = 0

    def think(
        self,
        task: str,
        mode: ThinkingMode | None = None,
        max_iterations: int = 3,
    ) -> CognitiveResult:
        if mode is None:
            mode = self.orchestrator.select_mode(task, "medium")

        self.orchestrator.set_mode(mode)
        active = self.orchestrator.get_active_engines()

        all_outputs: list[EngineOutput] = []
        all_synergies: list[SynergyEffect] = []
        convergence_achieved = False
        final_confidence = 0.0

        for iteration in range(max_iterations):
            self._iteration_count += 1
            iteration_outputs = self._run_active_engines(task, active)

            if iteration > 0 and all_outputs:
                self._apply_feed_forward(all_outputs, iteration_outputs)

            all_outputs.extend(iteration_outputs)

            synergies = self.feedback_amplifier.amplify(all_outputs)
            all_synergies = synergies

            final_confidence = self._compute_formula_confidence(all_outputs)
            convergence_score = self._compute_convergence(all_outputs)

            state = CognitiveState(
                active_mode=mode,
                active_engines=active,
                iteration_count=self._iteration_count,
                convergence_score=convergence_score,
                total_confidence=final_confidence,
            )
            self._state_history.append(state)
            self.convergence_monitor.record_state(state)

            if self.convergence_monitor.check_convergence(self._state_history):
                convergence_achieved = True
                break

        recommendations = self._generate_recommendations(
            all_outputs, all_synergies, convergence_achieved
        )

        return CognitiveResult(
            task=task,
            mode_used=mode,
            engine_outputs=all_outputs,
            synergy_effects=all_synergies,
            convergence_achieved=convergence_achieved,
            final_confidence=round(final_confidence, 4),
            iterations=min(self._iteration_count, max_iterations),
            recommendations=recommendations,
        )

    def analyze(self, task: str) -> CognitiveResult:
        mode = self.orchestrator.select_mode(task, "medium")
        return self.think(task, mode=mode)

    def get_status(self) -> CognitiveState:
        if self._state_history:
            return self._state_history[-1]
        return CognitiveState(
            active_mode=ThinkingMode.FAST,
            active_engines=[],
            iteration_count=0,
            convergence_score=0.0,
            total_confidence=0.0,
        )

    def _run_active_engines(
        self, task: str, active_engines: list[str]
    ) -> list[EngineOutput]:
        outputs: list[EngineOutput] = []

        if "circular_thinking" in active_engines:
            outputs.append(self._run_circular(task))
        if "cross_folder_memory" in active_engines:
            outputs.append(self._run_memory(task))
        if "metacognitive_reflection" in active_engines:
            outputs.append(self._run_metacognitive(task))
        if "world_model" in active_engines:
            outputs.append(self._run_world_model(task))
        if "causal_reasoning" in active_engines:
            outputs.append(self._run_causal(task))
        if "attention_budget" in active_engines:
            outputs.append(self._run_attention(task))

        return outputs

    def _run_circular(self, task: str) -> EngineOutput:
        action = ActionNode(
            id=f"task_{self._iteration_count}",
            name=task[:80],
            description=task,
        )
        self.circular_engine.add_action(action)
        analysis = self.circular_engine.circular_analysis()
        convergence = self.circular_engine.check_convergence()

        return EngineOutput(
            engine_name="circular_thinking",
            output_data={
                "total_actions": analysis.total_actions,
                "total_dependencies": analysis.total_dependencies,
                "feedback_loops": len(analysis.feedback_loops),
                "critical_actions": analysis.critical_actions,
                "inter_dependency_map": analysis.inter_dependency_map,
                "is_converged": convergence.is_converged,
            },
            confidence=self._circular_confidence(convergence),
        )

    def _run_memory(self, task: str) -> EngineOutput:
        context = self.memory_bridge.inject_context()
        validation = self.memory_bridge.validate_bridge()

        return EngineOutput(
            engine_name="cross_folder_memory",
            output_data={
                "context_length": len(context),
                "bridge_valid": validation.is_valid,
                "master_found": validation.master_found,
                "available_contexts": self.memory_bridge.list_available_contexts(),
            },
            confidence=0.9 if validation.is_valid else 0.4,
        )

    def _run_metacognitive(self, task: str) -> EngineOutput:
        claims = [task]
        result = self.metacognitive_engine.reflect(claims)
        summary = self.metacognitive_engine.get_confidence_summary()

        return EngineOutput(
            engine_name="metacognitive_reflection",
            output_data={
                "iterations": result.loop_iterations,
                "convergence": result.convergence_achieved,
                "final_avg_confidence": result.final_confidence_avg,
                "revisions_count": len(result.revisions_made),
                "total_reflections": summary.get("total_reflections", 0),
            },
            confidence=result.final_confidence_avg,
        )

    def _run_world_model(self, task: str) -> EngineOutput:
        interaction = {
            "entities": [{"name": task[:40], "entity_type": "CONCEPT", "attributes": {"task": True}}],
        }
        summary = self.world_model.construct_from_interactions([interaction])

        return EngineOutput(
            engine_name="world_model",
            output_data={
                "total_entities": summary.total_entities,
                "total_relations": summary.total_relations,
                "total_chains": summary.total_chains,
                "coverage_score": summary.coverage_score,
            },
            confidence=summary.coverage_score,
        )

    def _run_causal(self, task: str) -> EngineOutput:
        obs = Observation(event=task[:40], observed_outcome="analyzed")
        result = self.causal_engine.analyze_causally([obs])

        return EngineOutput(
            engine_name="causal_reasoning",
            output_data={
                "causal_relations_count": len(result.causal_relations),
                "root_causes": result.root_causes,
                "downstream_effects": result.downstream_effects,
                "counterfactuals_count": len(result.counterfactuals),
                "interventions_count": len(result.interventions),
            },
            confidence=self._causal_confidence(result),
        )

    def _run_attention(self, task: str) -> EngineOutput:
        result = self.attention_manager.auto_manage()

        return EngineOutput(
            engine_name="attention_budget",
            output_data={
                "active_info_count": len(result.active_info),
                "freed_tokens": result.freed_tokens,
                "budget_utilization": result.budget_status.get("utilization", 0.0),
                "remaining_budget": result.budget_status.get("remaining", 0.0),
            },
            confidence=1.0 - result.budget_status.get("utilization", 0.5),
        )

    def _apply_feed_forward(
        self, prev_outputs: list[EngineOutput], current_outputs: list[EngineOutput]
    ) -> None:
        for prev in prev_outputs:
            for curr in current_outputs:
                feed = self.feedback_amplifier.feed_forward(
                    prev.engine_name, curr.engine_name, prev
                )
                if feed.get("suggestion"):
                    curr.output_data[f"feed_from_{prev.engine_name}"] = feed

    def _compute_formula_confidence(self, outputs: list[EngineOutput]) -> float:
        output_map = {o.engine_name: o for o in outputs}

        r = output_map.get("metacognitive_reflection")
        q = output_map.get("circular_thinking")
        m = output_map.get("cross_folder_memory")
        w = output_map.get("world_model")
        d = output_map.get("causal_reasoning")
        g = output_map.get("attention_budget")

        r_val = r.confidence if r else 0.5
        q_val = q.confidence if q else 0.5
        m_val = m.confidence if m else 0.5
        w_val = w.confidence if w else 0.5
        d_val = d.confidence if d else 0.5
        g_val = g.confidence if g else 0.5

        sq_r = r_val * r_val
        term1 = math.log(max(sq_r * q_val, 1e-10))
        term2 = math.log(max(m_val * w_val, 1e-10))
        term3 = (r_val ** d_val) - (1.0 - d_val)
        term4 = g_val / max(1.0 - g_val, 0.01)

        raw = term1 + term2 + term3 + term4
        normalized = 1.0 / (1.0 + math.exp(-raw))
        return max(0.0, min(1.0, normalized))

    def _compute_convergence(self, outputs: list[EngineOutput]) -> float:
        if not outputs:
            return 0.0
        confidences = [o.confidence for o in outputs]
        avg = sum(confidences) / len(confidences)
        if len(confidences) < 2:
            return avg
        variance = sum((c - avg) ** 2 for c in confidences) / len(confidences)
        consistency = 1.0 - min(variance * 4, 1.0)
        return avg * 0.7 + consistency * 0.3

    def _circular_confidence(self, convergence: Any) -> float:
        if convergence.total_actions == 0:
            return 0.5
        stable_ratio = convergence.stable_actions / max(convergence.total_actions, 1)
        return stable_ratio * 0.8 + (1.0 if convergence.is_converged else 0.2) * 0.2

    def _causal_confidence(self, result: CausalAnalysisResult) -> float:
        if not result.causal_relations:
            return 0.3
        avg = sum(r.confidence for r in result.causal_relations) / len(
            result.causal_relations
        )
        verified = sum(1 for r in result.causal_relations if r.is_verified)
        verified_bonus = verified / max(len(result.causal_relations), 1) * 0.2
        return min(1.0, avg + verified_bonus)

    def _generate_recommendations(
        self,
        outputs: list[EngineOutput],
        synergies: list[SynergyEffect],
        converged: bool,
    ) -> list[str]:
        recs: list[str] = []

        if not converged:
            recs.append("Consider increasing iteration count for convergence")

        contradictions = [s for s in synergies if s.synergy_type == "CONTRADICT"]
        if contradictions:
            recs.append(
                f"Resolve {len(contradictions)} confidence contradiction(s) between engines"
            )

        output_map = {o.engine_name: o for o in outputs}
        if "metacognitive_reflection" in output_map:
            meta = output_map["metacognitive_reflection"]
            if meta.confidence < 0.5:
                recs.append("Low metacognitive confidence — add more evidence sources")

        if "circular_thinking" in output_map:
            circ = output_map["circular_thinking"]
            if circ.output_data.get("feedback_loops", 0) > 3:
                recs.append(
                    "High feedback loop count — consider simplifying dependencies"
                )

        if "attention_budget" in output_map:
            attn = output_map["attention_budget"]
            if attn.output_data.get("budget_utilization", 0) > 0.8:
                recs.append("Attention budget near capacity — prioritize critical info")

        if "causal_reasoning" in output_map:
            causal = output_map["causal_reasoning"]
            if not causal.output_data.get("root_causes"):
                recs.append("No root causes identified — provide more observations")

        if not recs:
            recs.append("Analysis complete — all engines operating within normal parameters")

        return recs


class RegionalUnifiedMixin:
    HK_PDPO_TASKS = [
        "Check if user data collection complies with PDPO principles",
        "Verify automated decision-making transparency requirements",
    ]

    CN_LOCALIZATION_TASKS = [
        "Analyze data localization requirements for China users",
        "Assess cross-border data transfer compliance",
    ]

    EU_RISK_TASKS = [
        "Evaluate if AI system qualifies as high-risk under AI Act",
        "Assess human oversight requirements for automated decisions",
    ]

    SG_GOVERNANCE_TASKS = [
        "Review Agent AI governance framework compliance",
        "Verify transparency measures for agent decisions",
    ]

    def test_hk_pdbo_mode_selection(self) -> dict:
        unified = UnifiedCognitiveArchitecture()
        mode = unified.orchestrator.select_mode(HK_PDPO_TASKS[0], "high")
        unified.orchestrator.set_mode(mode)
        active = unified.orchestrator.get_active_engines()
        return {
            "region": "HK",
            "selected_mode": mode.value,
            "active_engines": active,
            "pdpo_aware": len(active) >= 2,
        }

    def test_cn_localization_orchestration(self) -> dict:
        unified = UnifiedCognitiveArchitecture()
        result = unified.think(CN_LOCALIZATION_TASKS[0])
        has_world_model = any("world_model" in e.engine_name for e in result.engine_outputs)
        has_causal = any("causal_reasoning" in e.engine_name for e in result.engine_outputs)
        return {
            "region": "CN",
            "data_tracking_active": has_world_model,
            "compliance_analysis": has_causal,
            "localization_orchestrated": has_world_model and has_causal,
        }

    def test_eu_risk_classification(self) -> dict:
        unified = UnifiedCognitiveArchitecture()
        result = unified.think(EU_RISK_TASKS[0])
        confidence = result.final_confidence
        has_risk_analysis = any("causal" in e.engine_name for e in result.engine_outputs)
        return {
            "region": "EU",
            "risk_classification_confidence": confidence,
            "high_risk_analysis": has_risk_analysis,
            "ai_act_compliant": confidence > 0.5,
        }

    def test_sg_agent_governance(self) -> dict:
        unified = UnifiedCognitiveArchitecture()
        result = unified.think(SG_GOVERNANCE_TASKS[0])
        has_metacog = any("metacognitive" in e.engine_name for e in result.engine_outputs)
        has_explainability = any("revisions" in str(e.output_data) for e in result.engine_outputs)
        return {
            "region": "SG",
            "governance_mode": result.mode_used.value,
            "explainability_analysis": has_explainability,
            "imda_compliant": has_metacog and result.convergence_achieved,
        }

    def test_multi_region_convergence(self) -> dict:
        unified = UnifiedCognitiveArchitecture()
        all_converged = True
        confidences = []
        for task in self.HK_PDPO_TASKS + self.CN_LOCALIZATION_TASKS + self.EU_RISK_TASKS:
            result = unified.think(task)
            all_converged = all_converged and result.convergence_achieved
            confidences.append(result.final_confidence)
        return {
            "all_converged": all_converged,
            "avg_confidence": sum(confidences) / len(confidences) if confidences else 0,
            "max_confidence": max(confidences) if confidences else 0,
            "min_confidence": min(confidences) if confidences else 0,
        }

    def run_all_regional_tests(self) -> dict:
        return {
            "unified_cognitive_architecture": {
                "HK_PDPO": self.test_hk_pdbo_mode_selection(),
                "CN_Localization": self.test_cn_localization_orchestration(),
                "EU_Risk": self.test_eu_risk_classification(),
                "SG_Governance": self.test_sg_agent_governance(),
                "MultiRegion": self.test_multi_region_convergence(),
            }
        }


HK_PDPO_TASKS = RegionalUnifiedMixin.HK_PDPO_TASKS
CN_LOCALIZATION_TASKS = RegionalUnifiedMixin.CN_LOCALIZATION_TASKS
EU_RISK_TASKS = RegionalUnifiedMixin.EU_RISK_TASKS
SG_GOVERNANCE_TASKS = RegionalUnifiedMixin.SG_GOVERNANCE_TASKS
