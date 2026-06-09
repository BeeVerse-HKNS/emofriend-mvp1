from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from harnessing.core.formula_operator_architecture import INVENTORY_FACTORS


class VerificationStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    PARTIAL = "PARTIAL"


class ComponentStatus(str, Enum):
    ACTIVE = "ACTIVE"
    STUB = "STUB"
    DEPRECATED = "DEPRECATED"


class Priority(str, Enum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


class ConvergenceReason(str, Enum):
    VERIFICATION_PASS = "verification_pass"
    MAX_DEPTH = "max_depth"
    ATTRACTOR_DETECTED = "attractor_detected"


LAYER_FACTOR_MAP = {
    1: ["K", "R"],
    2: ["R", "C", "F"],
    3: ["K", "P"],
    4: ["A", "R"],
    5: ["A", "H"],
    6: ["G", "S"],
    7: ["M", "S"],
    8: ["K", "M"],
}

LAYER_NAMES = {
    1: "Perception",
    2: "Thinking",
    3: "Research",
    4: "Planning",
    5: "Execution",
    6: "Verification",
    7: "Reflection",
    8: "Crystallization",
}

LAYER_NAMES_ZH = {
    1: "感知層",
    2: "思考層",
    3: "研究層",
    4: "規劃層",
    5: "執行層",
    6: "驗證層",
    7: "反思層",
    8: "結晶層",
}


@dataclass
class ComponentInfo:
    name: str
    module_path: str
    status: ComponentStatus = ComponentStatus.ACTIVE
    priority: Priority = Priority.P1


@dataclass
class LayerStatus:
    layer_id: int
    name: str
    name_zh: str
    factors: list[str]
    components: list[ComponentInfo] = field(default_factory=list)
    last_processed: Optional[str] = None
    process_count: int = 0

    @property
    def active_components(self) -> list[ComponentInfo]:
        return [c for c in self.components if c.status == ComponentStatus.ACTIVE]

    @property
    def p0_components(self) -> list[ComponentInfo]:
        return [c for c in self.components if c.priority == Priority.P0]


@dataclass
class FlowContext:
    raw_prompt: str = ""
    enhanced_prompt: Optional[str] = None
    intent: Optional[str] = None
    thinking_depth: int = 0
    max_depth: int = 3
    research_findings: list[str] = field(default_factory=list)
    plan: Optional[str] = None
    execution_results: list[str] = field(default_factory=list)
    verification_status: Optional[VerificationStatus] = None
    reflection_insights: list[str] = field(default_factory=list)
    crystallized_knowledge: list[str] = field(default_factory=list)
    confidence: float = 0.0
    layer_history: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    _current_layer: int = 0
    _knowledge_gap_detected: bool = False
    _attractor_detected: bool = False
    _convergence_reason: Optional[ConvergenceReason] = None

    def advance_layer(self) -> int:
        self._current_layer += 1
        if self._current_layer > 8:
            self._current_layer = 1
            self.thinking_depth += 1
        layer_name = LAYER_NAMES.get(self._current_layer, f"L{self._current_layer}")
        self.layer_history.append(f"D{self.thinking_depth}-{layer_name}")
        return self._current_layer

    def set_layer(self, layer_id: int) -> None:
        self._current_layer = max(1, min(8, layer_id))
        layer_name = LAYER_NAMES.get(self._current_layer, f"L{self._current_layer}")
        self.layer_history.append(f"D{self.thinking_depth}-{layer_name}")

    @property
    def current_layer(self) -> int:
        return self._current_layer

    @property
    def is_converged(self) -> bool:
        return self._convergence_reason is not None

    @property
    def convergence_reason(self) -> Optional[ConvergenceReason]:
        return self._convergence_reason

    def mark_converged(self, reason: ConvergenceReason) -> None:
        self._convergence_reason = reason

    def update_confidence(self, delta: float) -> None:
        self.confidence = max(0.0, min(1.0, self.confidence + delta))


@dataclass
class FlowResult:
    answer: str = ""
    confidence: float = 0.0
    spiral_iterations: int = 0
    layers_visited: list[str] = field(default_factory=list)
    research_used: list[str] = field(default_factory=list)
    verification_status: str = ""
    crystallized: bool = False
    convergence_reason: Optional[ConvergenceReason] = None
    metadata: dict = field(default_factory=dict)


LAYER_COMPONENTS: dict[int, list[ComponentInfo]] = {
    1: [
        ComponentInfo(name="PromptEnhancer", module_path="harnessing.core.prompt_enhancer", status=ComponentStatus.ACTIVE, priority=Priority.P0),
        ComponentInfo(name="PromptUnderstandingSkill", module_path="harnessing.core.prompt_understanding_skill", status=ComponentStatus.ACTIVE, priority=Priority.P0),
        ComponentInfo(name="AttractorDetector", module_path="harnessing.core.meta_helical_learning", status=ComponentStatus.ACTIVE, priority=Priority.P1),
    ],
    2: [
        ComponentInfo(name="MetaHelicalLearning", module_path="harnessing.core.meta_helical_learning", status=ComponentStatus.ACTIVE, priority=Priority.P0),
        ComponentInfo(name="FormulaThinking", module_path="harnessing.core.formula_operator_architecture", status=ComponentStatus.ACTIVE, priority=Priority.P0),
        ComponentInfo(name="TreeOfThought", module_path="harnessing.core.tree_of_thought", status=ComponentStatus.ACTIVE, priority=Priority.P1),
        ComponentInfo(name="AnalogicalReasoning", module_path="harnessing.core.analogical_reasoning", status=ComponentStatus.ACTIVE, priority=Priority.P1),
    ],
    3: [
        ComponentInfo(name="KnowledgeBaseEngine", module_path="harnessing.core.knowledge_base_engine", status=ComponentStatus.ACTIVE, priority=Priority.P0),
        ComponentInfo(name="RAGRetriever", module_path="harnessing.core.beeverse_rag_retriever", status=ComponentStatus.ACTIVE, priority=Priority.P0),
        ComponentInfo(name="WebSearch", module_path="harnessing.core.web_search", status=ComponentStatus.STUB, priority=Priority.P2),
        ComponentInfo(name="DeepResearch", module_path="harnessing.core.deep_research", status=ComponentStatus.STUB, priority=Priority.P2),
    ],
    4: [
        ComponentInfo(name="SkillRouter", module_path="harnessing.core.skill_router", status=ComponentStatus.ACTIVE, priority=Priority.P0),
        ComponentInfo(name="ModelRouter", module_path="harnessing.core.model_router", status=ComponentStatus.ACTIVE, priority=Priority.P0),
        ComponentInfo(name="MixedLLMEngine", module_path="harnessing.core.mixed_llm_engine", status=ComponentStatus.ACTIVE, priority=Priority.P1),
    ],
    5: [
        ComponentInfo(name="AutomationSkills", module_path="harnessing.core.automation_skills", status=ComponentStatus.ACTIVE, priority=Priority.P0),
        ComponentInfo(name="ChineseIntegration", module_path="harnessing.core.chinese_integration_skills", status=ComponentStatus.ACTIVE, priority=Priority.P1),
        ComponentInfo(name="GlobalIntegration", module_path="harnessing.core.global_integration_skills", status=ComponentStatus.ACTIVE, priority=Priority.P1),
    ],
    6: [
        ComponentInfo(name="SelfAuditEngine", module_path="harnessing.core.self_audit_engine", status=ComponentStatus.ACTIVE, priority=Priority.P0),
        ComponentInfo(name="QA", module_path="harnessing.core.qa_engine", status=ComponentStatus.STUB, priority=Priority.P1),
        ComponentInfo(name="StressTest", module_path="harnessing.core.stress_test", status=ComponentStatus.STUB, priority=Priority.P2),
        ComponentInfo(name="ConsistencyCheck", module_path="harnessing.core.consistency_check", status=ComponentStatus.STUB, priority=Priority.P2),
    ],
    7: [
        ComponentInfo(name="MetaCognitiveMonitor", module_path="harnessing.core.meta_helical_learning", status=ComponentStatus.ACTIVE, priority=Priority.P0),
        ComponentInfo(name="ErrorEcosystem", module_path="harnessing.core.error_ecosystem", status=ComponentStatus.ACTIVE, priority=Priority.P1),
        ComponentInfo(name="DecisionLog", module_path="harnessing.core.memory_engine", status=ComponentStatus.ACTIVE, priority=Priority.P1),
    ],
    8: [
        ComponentInfo(name="KnowledgeCrystallizer", module_path="harnessing.core.meta_helical_learning", status=ComponentStatus.ACTIVE, priority=Priority.P0),
        ComponentInfo(name="MemoryEngine", module_path="harnessing.core.memory_engine", status=ComponentStatus.ACTIVE, priority=Priority.P0),
        ComponentInfo(name="AGENTS_md", module_path="AGENTS.md", status=ComponentStatus.ACTIVE, priority=Priority.P0),
    ],
}


class ThinkingLayer:
    def __init__(self, layer_id: int):
        self.layer_id = layer_id
        self.name = LAYER_NAMES[layer_id]
        self.name_zh = LAYER_NAMES_ZH[layer_id]
        self.factors = LAYER_FACTOR_MAP[layer_id]
        self.components = LAYER_COMPONENTS.get(layer_id, [])

    def process(self, context: FlowContext) -> FlowContext:
        handler = {
            1: self._process_perception,
            2: self._process_thinking,
            3: self._process_research,
            4: self._process_planning,
            5: self._process_execution,
            6: self._process_verification,
            7: self._process_reflection,
            8: self._process_crystallization,
        }.get(self.layer_id)
        if handler:
            context = handler(context)
        return context

    def validate(self, context: FlowContext) -> bool:
        if self.layer_id == 1:
            return bool(context.raw_prompt)
        if self.layer_id == 2:
            return context.enhanced_prompt is not None
        if self.layer_id == 3:
            return context._knowledge_gap_detected
        if self.layer_id == 4:
            return True
        if self.layer_id == 5:
            return context.plan is not None
        if self.layer_id == 6:
            return len(context.execution_results) > 0
        if self.layer_id == 7:
            return context.verification_status in (VerificationStatus.FAIL, VerificationStatus.PARTIAL)
        if self.layer_id == 8:
            return context.verification_status == VerificationStatus.PASS
        return True

    def _process_perception(self, context: FlowContext) -> FlowContext:
        context.enhanced_prompt = context.raw_prompt
        context.intent = self._extract_intent(context.raw_prompt)
        context._knowledge_gap_detected = self._detect_knowledge_gap(context)
        context._attractor_detected = self._detect_attractor(context)
        context.update_confidence(0.1)
        return context

    def _process_thinking(self, context: FlowContext) -> FlowContext:
        if context.intent:
            context.update_confidence(0.15)
        if context._knowledge_gap_detected:
            context.update_confidence(-0.05)
        return context

    def _process_research(self, context: FlowContext) -> FlowContext:
        if context._knowledge_gap_detected:
            context.research_findings.append(f"Research cycle D{context.thinking_depth}")
            context.update_confidence(0.1)
        return context

    def _process_planning(self, context: FlowContext) -> FlowContext:
        if context.research_findings:
            findings_summary = "; ".join(context.research_findings[-3:])
        else:
            findings_summary = "direct reasoning"
        context.plan = f"Plan D{context.thinking_depth}: based on [{findings_summary}]"
        context.update_confidence(0.1)
        return context

    def _process_execution(self, context: FlowContext) -> FlowContext:
        if context.plan:
            context.execution_results.append(f"Executed: {context.plan}")
            context.update_confidence(0.1)
        return context

    def _process_verification(self, context: FlowContext) -> FlowContext:
        if context.confidence >= 0.8:
            context.verification_status = VerificationStatus.PASS
        elif context.confidence >= 0.5:
            context.verification_status = VerificationStatus.PARTIAL
        else:
            context.verification_status = VerificationStatus.FAIL
        return context

    def _process_reflection(self, context: FlowContext) -> FlowContext:
        if context.verification_status == VerificationStatus.FAIL:
            context.reflection_insights.append(f"D{context.thinking_depth}: verification failed, confidence={context.confidence:.2f}")
            context._knowledge_gap_detected = True
        elif context.verification_status == VerificationStatus.PARTIAL:
            context.reflection_insights.append(f"D{context.thinking_depth}: partial pass, confidence={context.confidence:.2f}")
            context._knowledge_gap_detected = True
        if len(context.reflection_insights) >= 2:
            latest = context.reflection_insights[-2:]
            if latest[0] == latest[1]:
                context._attractor_detected = True
        return context

    def _process_crystallization(self, context: FlowContext) -> FlowContext:
        if context.verification_status == VerificationStatus.PASS:
            crystal = f"Crystal D{context.thinking_depth}: intent={context.intent}, confidence={context.confidence:.2f}"
            context.crystallized_knowledge.append(crystal)
        return context

    @staticmethod
    def _extract_intent(prompt: str) -> str:
        if not prompt:
            return ""
        words = prompt.strip().split()
        if len(words) <= 5:
            return prompt.strip()
        return " ".join(words[:5]) + "..."

    @staticmethod
    def _detect_knowledge_gap(context: FlowContext) -> bool:
        if context.thinking_depth == 0:
            return True
        return context.verification_status in (VerificationStatus.FAIL, VerificationStatus.PARTIAL)

    @staticmethod
    def _detect_attractor(context: FlowContext) -> bool:
        if len(context.reflection_insights) < 2:
            return False
        return context.reflection_insights[-1] == context.reflection_insights[-2]


class ThinkingFlowEngine:
    def __init__(self, max_depth: int = 3, confidence_threshold: float = 0.8):
        self.max_depth = max_depth
        self.confidence_threshold = confidence_threshold
        self.layers: dict[int, ThinkingLayer] = {i: ThinkingLayer(i) for i in range(1, 9)}
        self._layer_status_cache: dict[int, LayerStatus] = {}

    def execute(self, prompt: str, max_depth: int | None = None) -> FlowResult:
        effective_max = max_depth if max_depth is not None else self.max_depth
        context = FlowContext(raw_prompt=prompt, max_depth=effective_max)

        while not context.is_converged:
            context = self._run_spiral_cycle(context)
            if self.check_convergence(context):
                break

        return self._build_result(context)

    def execute_layer(self, layer: int, context: FlowContext) -> FlowContext:
        if layer < 1 or layer > 8:
            return context
        thinking_layer = self.layers[layer]
        if thinking_layer.validate(context):
            context = thinking_layer.process(context)
        return context

    def check_convergence(self, context: FlowContext) -> bool:
        if context.verification_status == VerificationStatus.PASS and context.confidence >= self.confidence_threshold:
            context.mark_converged(ConvergenceReason.VERIFICATION_PASS)
            return True
        if context.thinking_depth >= context.max_depth:
            context.mark_converged(ConvergenceReason.MAX_DEPTH)
            return True
        if context._attractor_detected:
            context.mark_converged(ConvergenceReason.ATTRACTOR_DETECTED)
            return True
        return False

    def get_layer_status(self) -> dict[str, LayerStatus]:
        if self._layer_status_cache:
            return {f"L{k}": v for k, v in self._layer_status_cache.items()}
        status_map = {}
        for lid, layer in self.layers.items():
            status_map[lid] = LayerStatus(
                layer_id=lid,
                name=layer.name,
                name_zh=layer.name_zh,
                factors=layer.factors,
                components=layer.components,
            )
        self._layer_status_cache = status_map
        return {f"L{k}": v for k, v in status_map.items()}

    def spiral_report(self, context: FlowContext) -> str:
        lines = [
            f"=== Thinking Flow Spiral Report ===",
            f"Depth: {context.thinking_depth}/{context.max_depth}",
            f"Confidence: {context.confidence:.2f}",
            f"Verification: {context.verification_status.value if context.verification_status else 'N/A'}",
            f"Converged: {context.is_converged}",
            f"Convergence Reason: {context.convergence_reason.value if context.convergence_reason else 'N/A'}",
            f"Intent: {context.intent or 'N/A'}",
            f"Research Findings: {len(context.research_findings)}",
            f"Execution Results: {len(context.execution_results)}",
            f"Reflection Insights: {len(context.reflection_insights)}",
            f"Crystallized Knowledge: {len(context.crystallized_knowledge)}",
            f"Layer History: {' → '.join(context.layer_history) if context.layer_history else 'None'}",
            f"Knowledge Gap: {context._knowledge_gap_detected}",
            f"Attractor: {context._attractor_detected}",
        ]
        return "\n".join(lines)

    def _run_spiral_cycle(self, context: FlowContext) -> FlowContext:
        for layer_id in range(1, 7):
            if context.is_converged:
                break

            context._current_layer = layer_id
            layer_name = LAYER_NAMES.get(layer_id, f"L{layer_id}")
            context.layer_history.append(f"D{context.thinking_depth}-{layer_name}")
            context = self.execute_layer(layer_id, context)

        if context.is_converged:
            return context

        if context.verification_status == VerificationStatus.PASS:
            context._current_layer = 8
            context.layer_history.append(f"D{context.thinking_depth}-Crystallization")
            context = self.execute_layer(8, context)
        else:
            context._current_layer = 7
            context.layer_history.append(f"D{context.thinking_depth}-Reflection")
            context = self.execute_layer(7, context)
            context.thinking_depth += 1

        return context

    def _build_result(self, context: FlowContext) -> FlowResult:
        answer_parts = []
        if context.intent:
            answer_parts.append(f"Intent: {context.intent}")
        if context.plan:
            answer_parts.append(f"Plan: {context.plan}")
        if context.execution_results:
            answer_parts.append(f"Results: {'; '.join(context.execution_results[-3:])}")
        if not answer_parts:
            answer_parts.append(context.raw_prompt)

        return FlowResult(
            answer=" | ".join(answer_parts),
            confidence=context.confidence,
            spiral_iterations=context.thinking_depth,
            layers_visited=list(context.layer_history),
            research_used=list(context.research_findings),
            verification_status=context.verification_status.value if context.verification_status else "N/A",
            crystallized=len(context.crystallized_knowledge) > 0,
            convergence_reason=context.convergence_reason,
            metadata=dict(context.metadata),
        )


class ThinkingFlowOrchestrator:
    def __init__(self, engine: ThinkingFlowEngine | None = None):
        self.engine = engine or ThinkingFlowEngine()

    def process(self, prompt: str, max_depth: int = 3) -> FlowResult:
        return self.engine.execute(prompt, max_depth=max_depth)

    def get_architecture_overview(self) -> dict:
        layer_status = self.engine.get_layer_status()
        overview = {
            "total_layers": 8,
            "spiral_pattern": "L1→L2→L3→L4→L5→L6→L7→L8→L1→...",
            "convergence_criteria": [
                "L6 Verification PASS + confidence >= threshold",
                "Max spiral iterations reached",
                "Attractor detected (L7 finds no new insights)",
            ],
            "layers": {},
        }
        for key, status in layer_status.items():
            overview["layers"][key] = {
                "name": status.name,
                "name_zh": status.name_zh,
                "factors": status.factors,
                "factor_names": [INVENTORY_FACTORS.get(f, {}).get("name", f) for f in status.factors],
                "active_components": len(status.active_components),
                "p0_components": len(status.p0_components),
                "total_components": len(status.components),
            }
        return overview

    def get_factor_layer_map(self) -> dict[str, list[int]]:
        factor_layers: dict[str, list[int]] = {}
        for layer_id, factors in LAYER_FACTOR_MAP.items():
            for f in factors:
                factor_layers.setdefault(f, []).append(layer_id)
        return factor_layers

    def explain_spiral(self, prompt: str) -> str:
        lines = [
            f"=== Spiral Flow Explanation for: '{prompt[:50]}...' ===",
            "",
            "The Thinking Flow follows a SPIRAL pattern, not linear:",
            "",
        ]

        layer_descriptions = {
            1: "L1 Perception (感知層): Enhance prompt, extract intent, detect knowledge gaps",
            2: "L2 Thinking (思考層): Deep reasoning with Meta-Helical Learning + Formula Thinking",
            3: "L3 Research (研究層): Retrieve knowledge from KB, RAG, or web search",
            4: "L4 Planning (規劃層): Route to skills, select models, create execution plan",
            5: "L5 Execution (執行層): Execute automation, integration, and action skills",
            6: "L6 Verification (驗證層): QA check, self-audit, stress test, consistency check",
            7: "L7 Reflection (反思層): If FAIL/PARTIAL → analyze errors, learn, spiral back to L1",
            8: "L8 Crystallization (結晶層): If PASS → persist knowledge to MemoryEngine + AGENTS.md",
        }

        for i in range(1, 9):
            lines.append(f"  {layer_descriptions[i]}")
            if i == 6:
                lines.append("")
                lines.append("  ┌─ If PASS → L7 (Reflection) → L8 (Crystallization) → END")
                lines.append("  └─ If FAIL/PARTIAL → L7 (Reflection) → SPIRAL BACK to L1")
                lines.append("")
            if i == 7:
                lines.append("")
                lines.append("  L7 → L1: THIS IS THE SPIRAL — re-perceive with new insights")
                lines.append("")

        lines.extend([
            "Convergence: The spiral stops when:",
            "  1. L6 Verification passes (confidence >= threshold)",
            "  2. Max iterations reached",
            "  3. Attractor detected (L7 finds no new insights)",
            "",
            "Factor Mapping:",
        ])
        for layer_id, factors in LAYER_FACTOR_MAP.items():
            factor_names = [INVENTORY_FACTORS.get(f, {}).get("name", f) for f in factors]
            lines.append(f"  L{layer_id} {LAYER_NAMES[layer_id]}: {' + '.join(factor_names)}")

        return "\n".join(lines)


if __name__ == "__main__":
    engine = ThinkingFlowEngine(max_depth=3, confidence_threshold=0.8)

    print("=" * 60)
    print("Thinking Flow Architecture — 8-Layer Spiral Engine")
    print("=" * 60)

    print("\n📊 Architecture Overview:")
    orchestrator = ThinkingFlowOrchestrator(engine)
    overview = orchestrator.get_architecture_overview()
    for layer_key, info in overview["layers"].items():
        print(f"  {layer_key} {info['name']} ({info['name_zh']}): "
              f"factors={'+'.join(info['factors'])} | "
              f"components={info['active_components']}/{info['total_components']} active")

    print("\n🔗 Factor → Layer Map:")
    factor_map = orchestrator.get_factor_layer_map()
    for factor, layers in factor_map.items():
        fname = INVENTORY_FACTORS.get(factor, {}).get("name", factor)
        layer_strs = [f"L{l}" for l in layers]
        print(f"  {factor} ({fname}): {', '.join(layer_strs)}")

    print("\n🌀 Spiral Execution Test:")
    result = engine.execute("How to build an AI agent with harness engineering?", max_depth=3)
    print(f"  Answer: {result.answer[:100]}...")
    print(f"  Confidence: {result.confidence:.2f}")
    print(f"  Spiral Iterations: {result.spiral_iterations}")
    print(f"  Verification: {result.verification_status}")
    print(f"  Crystallized: {result.crystallized}")
    print(f"  Convergence: {result.convergence_reason}")
    print(f"  Layers Visited: {' → '.join(result.layers_visited)}")

    print("\n📋 Spiral Report:")
    report_ctx = FlowContext(raw_prompt="test prompt", max_depth=3)
    report_ctx = engine.execute_layer(1, report_ctx)
    report_ctx = engine.execute_layer(2, report_ctx)
    report_ctx._current_layer = 2
    report_ctx.layer_history = ["D0-Perception", "D0-Thinking"]
    print(engine.spiral_report(report_ctx))

    print("\n📖 Spiral Explanation:")
    print(orchestrator.explain_spiral("Build an AI agent"))

    print("\n✅ Thinking Flow Architecture demo complete")
