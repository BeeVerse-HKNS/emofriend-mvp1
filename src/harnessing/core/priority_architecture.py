from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from harnessing.core.formula_operator_architecture import INVENTORY_FACTORS
from harnessing.core.thinking_flow_architecture import LAYER_FACTOR_MAP


class PriorityTier(str, Enum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"

    @property
    def description(self) -> str:
        return {
            PriorityTier.P0: "Must Have — Core Spiral Loop + Formula Operators",
            PriorityTier.P1: "Important — Protection Systems + Key Inventions",
            PriorityTier.P2: "Enhancement — Thinking Methods + Knowledge Base",
            PriorityTier.P3: "Optional — Invented Skills Stubs + Tool Scripts",
        }[self]


@dataclass
class ComponentEntry:
    name: str
    module_path: str
    tier: PriorityTier
    thinking_layer: Optional[int] = None
    formula_operator: Optional[str] = None
    status: str = "ACTIVE"
    category: str = "core_engine"
    description: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "module_path": self.module_path,
            "tier": self.tier.value,
            "thinking_layer": self.thinking_layer,
            "formula_operator": self.formula_operator,
            "status": self.status,
            "category": self.category,
            "description": self.description,
        }


PRIORITY_REGISTRY: dict[PriorityTier, list[ComponentEntry]] = {
    PriorityTier.P0: [
        ComponentEntry(
            name="PromptEnhancer",
            module_path="harnessing.core.prompt_enhancer",
            tier=PriorityTier.P0,
            thinking_layer=1,
            category="core_engine",
            description="L1 Perception: Prompt enhancement and intent extraction",
        ),
        ComponentEntry(
            name="PromptUnderstandingSkill",
            module_path="harnessing.core.prompt_understanding_skill",
            tier=PriorityTier.P0,
            thinking_layer=1,
            category="core_engine",
            description="L1 Perception: Deep prompt understanding",
        ),
        ComponentEntry(
            name="MetaHelicalLearning",
            module_path="harnessing.core.meta_helical_learning",
            tier=PriorityTier.P0,
            thinking_layer=2,
            category="core_engine",
            description="L2 Thinking: Meta-helical spiral learning engine",
        ),
        ComponentEntry(
            name="FormulaOperatorArchitecture",
            module_path="harnessing.core.formula_operator_architecture",
            tier=PriorityTier.P0,
            thinking_layer=2,
            category="core_engine",
            description="L2 Thinking: Formula operator architecture with 7 operators",
        ),
        ComponentEntry(
            name="KnowledgeBaseEngine",
            module_path="harnessing.core.knowledge_base_engine",
            tier=PriorityTier.P0,
            thinking_layer=3,
            category="core_engine",
            description="L3 Research: Knowledge base retrieval engine",
        ),
        ComponentEntry(
            name="RAGRetriever",
            module_path="harnessing.core.beeverse_rag_retriever",
            tier=PriorityTier.P0,
            thinking_layer=3,
            category="core_engine",
            description="L3 Research: RAG-based knowledge retrieval",
        ),
        ComponentEntry(
            name="SkillRouter",
            module_path="harnessing.core.skill_router",
            tier=PriorityTier.P0,
            thinking_layer=4,
            category="core_engine",
            description="L4 Planning: Skill routing and selection",
        ),
        ComponentEntry(
            name="ModelRouter",
            module_path="harnessing.core.model_router",
            tier=PriorityTier.P0,
            thinking_layer=4,
            category="core_engine",
            description="L4 Planning: Model routing and selection",
        ),
        ComponentEntry(
            name="AutomationSkills",
            module_path="harnessing.core.automation_skills",
            tier=PriorityTier.P0,
            thinking_layer=5,
            category="core_engine",
            description="L5 Execution: Automation skill execution",
        ),
        ComponentEntry(
            name="SelfAuditEngine",
            module_path="harnessing.core.self_audit_engine",
            tier=PriorityTier.P0,
            thinking_layer=6,
            category="core_engine",
            description="L6 Verification: Self-audit and QA engine",
        ),
        ComponentEntry(
            name="MetaCognitiveMonitor",
            module_path="harnessing.core.meta_helical_learning",
            tier=PriorityTier.P0,
            thinking_layer=7,
            category="core_engine",
            description="L7 Reflection: Meta-cognitive monitoring",
        ),
        ComponentEntry(
            name="ErrorEcosystem",
            module_path="harnessing.core.error_ecosystem",
            tier=PriorityTier.P0,
            thinking_layer=7,
            category="core_engine",
            description="L7 Reflection: Error ecosystem and learning",
        ),
        ComponentEntry(
            name="KnowledgeCrystallizer",
            module_path="harnessing.core.meta_helical_learning",
            tier=PriorityTier.P0,
            thinking_layer=8,
            category="core_engine",
            description="L8 Crystallization: Knowledge crystallization",
        ),
        ComponentEntry(
            name="MemoryEngine",
            module_path="harnessing.core.memory_engine",
            tier=PriorityTier.P0,
            thinking_layer=8,
            category="core_engine",
            description="L8 Crystallization: Persistent memory engine",
        ),
        ComponentEntry(
            name="AbstractionEngine",
            module_path="harnessing.core.formula_operator_architecture",
            tier=PriorityTier.P0,
            formula_operator="log",
            category="core_engine",
            description="Formula Operator log: Abstraction engine for universal pattern extraction",
        ),
        ComponentEntry(
            name="IntegrationEngine",
            module_path="harnessing.core.formula_operator_architecture",
            tier=PriorityTier.P0,
            formula_operator="+",
            category="core_engine",
            description="Formula Operator +: Integration engine for factor combination",
        ),
        ComponentEntry(
            name="FocusEngine",
            module_path="harnessing.core.formula_operator_architecture",
            tier=PriorityTier.P0,
            formula_operator="-",
            category="core_engine",
            description="Formula Operator -: Focus engine for overlap removal",
        ),
        ComponentEntry(
            name="SynergyEngine",
            module_path="harnessing.core.formula_operator_architecture",
            tier=PriorityTier.P0,
            formula_operator="*",
            category="core_engine",
            description="Formula Operator *: Synergy engine for cross-pollination",
        ),
        ComponentEntry(
            name="SpecializationEngine",
            module_path="harnessing.core.formula_operator_architecture",
            tier=PriorityTier.P0,
            formula_operator="/",
            category="core_engine",
            description="Formula Operator /: Specialization engine for domain focus",
        ),
        ComponentEntry(
            name="SelfImprovementEngine",
            module_path="harnessing.core.formula_operator_architecture",
            tier=PriorityTier.P0,
            formula_operator="sq",
            category="core_engine",
            description="Formula Operator sq: Self-improvement engine for qualitative leap",
        ),
        ComponentEntry(
            name="AmplificationEngine",
            module_path="harnessing.core.formula_operator_architecture",
            tier=PriorityTier.P0,
            formula_operator="^",
            category="core_engine",
            description="Formula Operator ^: Amplification engine for exponential breakthrough",
        ),
        ComponentEntry(
            name="BeeVerse",
            module_path="harnessing.core.beeverse",
            tier=PriorityTier.P0,
            category="core_engine",
            description="BeeVerse core local LLM integration",
        ),
        ComponentEntry(
            name="BeeVerseCore",
            module_path="harnessing.core.beeverse_core",
            tier=PriorityTier.P0,
            category="core_engine",
            description="BeeVerse core infrastructure",
        ),
        ComponentEntry(
            name="BeeVerseEngine",
            module_path="harnessing.core.beeverse_engine",
            tier=PriorityTier.P0,
            category="core_engine",
            description="BeeVerse engine for model management",
        ),
        ComponentEntry(
            name="BeeVerseAmplifier",
            module_path="harnessing.core.beeverse_amplifier",
            tier=PriorityTier.P0,
            category="core_engine",
            description="BeeVerse amplifier for capability enhancement",
        ),
        ComponentEntry(
            name="HarnessGuardrails",
            module_path="harnessing.core.harness_guardrails",
            tier=PriorityTier.P0,
            category="core_engine",
            description="Core guardrails system for safety constraints",
        ),
        ComponentEntry(
            name="MixedLLMEngine",
            module_path="harnessing.core.mixed_llm_engine",
            tier=PriorityTier.P0,
            category="core_engine",
            description="Mixed LLM engine for local + cloud routing",
        ),
    ],
    PriorityTier.P1: [
        ComponentEntry(
            name="IntentBasedGuard",
            module_path="harnessing.core.intent_based_guard",
            tier=PriorityTier.P1,
            category="protection",
            description="Intent-based proactive guard for dangerous operations",
        ),
        ComponentEntry(
            name="SupplyChainGuard",
            module_path="harnessing.core.supply_chain_guard",
            tier=PriorityTier.P1,
            category="protection",
            description="Supply chain protection with vendor monitoring and fallback",
        ),
        ComponentEntry(
            name="EnvironmentalResilience",
            module_path="harnessing.core.environmental_resilience",
            tier=PriorityTier.P1,
            category="protection",
            description="Environmental resilience with BCP/DR and auto-recovery",
        ),
        ComponentEntry(
            name="PrivacyShield",
            module_path="harnessing.core.privacy_shield",
            tier=PriorityTier.P1,
            category="protection",
            description="Privacy shield with PII detection and anonymization",
        ),
        ComponentEntry(
            name="ComplianceEngine",
            module_path="harnessing.core.compliance_engine",
            tier=PriorityTier.P1,
            category="protection",
            description="Compliance engine with policy enforcement and audit logging",
        ),
        ComponentEntry(
            name="LightweightRecovery",
            module_path="harnessing.core.lightweight_recovery",
            tier=PriorityTier.P1,
            category="protection",
            description="Lightweight recovery with fast checkpoint and rollback",
        ),
        ComponentEntry(
            name="TimingOrchestrator",
            module_path="harnessing.core.timing_orchestrator",
            tier=PriorityTier.P1,
            category="protection",
            description="Timing orchestrator with conflict resolution and SLA monitoring",
        ),
        ComponentEntry(
            name="UnifiedGuardSystem",
            module_path="harnessing.core.unified_guard_system",
            tier=PriorityTier.P1,
            category="protection",
            description="Unified guard system coordinating multiple protection mechanisms",
        ),
        ComponentEntry(
            name="PredictiveInterventionEngine",
            module_path="harnessing.core.predictive_intervention_engine",
            tier=PriorityTier.P1,
            category="invention",
            description="Proactive prediction and intervention engine",
        ),
        ComponentEntry(
            name="FormulaDrivenUniversalCoverage",
            module_path="harnessing.core.formula_driven_universal_coverage",
            tier=PriorityTier.P1,
            category="invention",
            description="Formula-driven universal coverage achieving 100% coverage",
        ),
        ComponentEntry(
            name="GapFillerSystem",
            module_path="harnessing.core.gap_filler_system",
            tier=PriorityTier.P1,
            category="invention",
            description="Dynamic gap detection and filling system",
        ),
        ComponentEntry(
            name="SpecializedHandlerFactory",
            module_path="harnessing.core.specialized_handler_factory",
            tier=PriorityTier.P1,
            category="invention",
            description="Specialized handler factory for domain-specific processing",
        ),
        ComponentEntry(
            name="CrossDomainSynergy",
            module_path="harnessing.core.cross_domain_synergy",
            tier=PriorityTier.P1,
            category="invention",
            description="Cross-domain synergy bridging with overlap/complement/amplify",
        ),
        ComponentEntry(
            name="MetaSelfImprovementEngine",
            module_path="harnessing.core.meta_self_improvement_engine",
            tier=PriorityTier.P1,
            category="invention",
            description="Meta self-improvement with z-score anomaly detection",
        ),
        ComponentEntry(
            name="ChineseIntegrationSkills",
            module_path="harnessing.core.chinese_integration_skills",
            tier=PriorityTier.P1,
            category="integration",
            description="Chinese social media integration skills",
        ),
        ComponentEntry(
            name="GlobalIntegrationSkills",
            module_path="harnessing.core.global_integration_skills",
            tier=PriorityTier.P1,
            category="integration",
            description="Global social media integration skills",
        ),
        ComponentEntry(
            name="BeeVerseRAGServer",
            module_path="harnessing.core.beeverse_rag_server",
            tier=PriorityTier.P1,
            category="integration",
            description="BeeVerse RAG server for knowledge serving",
        ),
    ],
    PriorityTier.P2: [
        ComponentEntry(
            name="ThinkingMethods_HIGH",
            module_path="harnessing.core.knowledge_base_engine",
            tier=PriorityTier.P2,
            category="thinking_method",
            description="20 HIGH-priority thinking methods (Bayanihan, Minga, Swahili, Silk Road, etc.)",
        ),
        ComponentEntry(
            name="ThinkingMethods_MEDIUM",
            module_path="harnessing.core.knowledge_base_engine",
            tier=PriorityTier.P2,
            category="thinking_method",
            description="184 MEDIUM-priority thinking methods",
        ),
        ComponentEntry(
            name="ThinkingMethods_LOW",
            module_path="harnessing.core.knowledge_base_engine",
            tier=PriorityTier.P2,
            category="thinking_method",
            description="121 LOW-priority thinking methods",
        ),
        ComponentEntry(
            name="KnowledgeBase_Files",
            module_path="docs/knowledge-base",
            tier=PriorityTier.P2,
            category="knowledge_base",
            description="28 knowledge base files (KB-00 to KB-26 + index)",
        ),
        ComponentEntry(
            name="InventionPatternLearner",
            module_path="harnessing.core.invention_pattern_learner",
            tier=PriorityTier.P2,
            category="invention",
            description="Pattern learner for invention discovery",
        ),
        ComponentEntry(
            name="LongFormulaInventionEngine",
            module_path="harnessing.core.formula_operator_architecture",
            tier=PriorityTier.P2,
            status="STUB",
            category="invention",
            description="Long formula invention engine for extended formula chains",
        ),
        ComponentEntry(
            name="IterativeStressInventionLoop",
            module_path="harnessing.core.formula_operator_architecture",
            tier=PriorityTier.P2,
            status="STUB",
            category="invention",
            description="Iterative stress testing for invention validation",
        ),
        ComponentEntry(
            name="ScenarioImmersionEngine",
            module_path="harnessing.core.formula_operator_architecture",
            tier=PriorityTier.P2,
            status="STUB",
            category="invention",
            description="Scenario immersion engine for deep scenario testing",
        ),
        ComponentEntry(
            name="FormulaThinkingEngine",
            module_path="harnessing.core.formula_brainstormer",
            tier=PriorityTier.P2,
            category="invention",
            description="Formula thinking engine for creative brainstorming",
        ),
        ComponentEntry(
            name="TreeOfThought",
            module_path="harnessing.core.tree_of_thought",
            tier=PriorityTier.P2,
            category="thinking_method",
            description="Tree of thought reasoning engine",
        ),
        ComponentEntry(
            name="AnalogicalReasoning",
            module_path="harnessing.core.analogical_reasoning",
            tier=PriorityTier.P2,
            category="thinking_method",
            description="Analogical reasoning engine",
        ),
        ComponentEntry(
            name="CommonsenseReasoning",
            module_path="harnessing.core.commonsense_reasoning",
            tier=PriorityTier.P2,
            category="thinking_method",
            description="Commonsense reasoning engine",
        ),
        ComponentEntry(
            name="SelfHealingEngine",
            module_path="harnessing.core.self_healing_engine",
            tier=PriorityTier.P2,
            category="protection",
            description="Self-healing engine with circuit breaker and checkpoint",
        ),
        ComponentEntry(
            name="CatastrophicRecoveryPlatform",
            module_path="harnessing.core.catastrophic_recovery_platform",
            tier=PriorityTier.P2,
            category="protection",
            description="Catastrophic recovery platform for disaster scenarios",
        ),
        ComponentEntry(
            name="BeeVerseSkillGapAnalyzer",
            module_path="harnessing.core.beeverse_skill_gap_analyzer",
            tier=PriorityTier.P2,
            category="integration",
            description="BeeVerse skill gap analyzer for capability detection",
        ),
        ComponentEntry(
            name="BeeVerseSkillInstaller",
            module_path="harnessing.core.beeverse_skill_installer",
            tier=PriorityTier.P2,
            category="integration",
            description="BeeVerse skill installer for gap filling",
        ),
        ComponentEntry(
            name="IterativeSkillInstallationEngine",
            module_path="harnessing.core.iterative_skill_installation_engine",
            tier=PriorityTier.P2,
            category="integration",
            description="Iterative skill installation with fuzzy matching",
        ),
        ComponentEntry(
            name="BeeVerseCapabilityRegistry",
            module_path="harnessing.core.beeverse_capability_registry",
            tier=PriorityTier.P2,
            category="integration",
            description="BeeVerse capability registry for skill tracking",
        ),
        ComponentEntry(
            name="WorkingRefreshMechanism",
            module_path="harnessing.core.working_refresh_mechanism",
            tier=PriorityTier.P2,
            category="core_engine",
            description="Working memory refresh mechanism",
        ),
        ComponentEntry(
            name="ModelSupervisor",
            module_path="harnessing.core.model_supervisor",
            tier=PriorityTier.P2,
            category="core_engine",
            description="Model supervisor for LLM oversight",
        ),
        ComponentEntry(
            name="GapDetector",
            module_path="harnessing.core.gap_detector",
            tier=PriorityTier.P2,
            category="invention",
            description="Gap detector for system coverage analysis",
        ),
        ComponentEntry(
            name="HumanErrorShield",
            module_path="harnessing.core.human_error_shield",
            tier=PriorityTier.P2,
            category="protection",
            description="Human error shield for mistake prevention",
        ),
        ComponentEntry(
            name="PromptInjectionDefense",
            module_path="harnessing.core.prompt_injection_defense",
            tier=PriorityTier.P2,
            category="protection",
            description="Prompt injection defense mechanism",
        ),
    ],
    PriorityTier.P3: [
        ComponentEntry(
            name="InventedSkillsStubs",
            module_path="harnessing.core.invented_skills",
            tier=PriorityTier.P3,
            status="STUB",
            category="tool",
            description="43 invented skill stubs (logical_*, database_queries_*, vulnerability_scanning_*, etc.)",
        ),
        ComponentEntry(
            name="ToolScripts",
            module_path="scripts",
            tier=PriorityTier.P3,
            status="ACTIVE",
            category="tool",
            description="140+ tool scripts for automation, deployment, and maintenance",
        ),
        ComponentEntry(
            name="DataFiles",
            module_path="data",
            tier=PriorityTier.P3,
            status="ACTIVE",
            category="tool",
            description="75+ JSON data files for configuration, test results, and intermediate outputs",
        ),
        ComponentEntry(
            name="OneTimeScripts",
            module_path="scripts",
            tier=PriorityTier.P3,
            status="ARCHIVE",
            category="tool",
            description="98 one-time scripts that have served their purpose",
        ),
        ComponentEntry(
            name="LLMRouter",
            module_path="harnessing.core.llm_router",
            tier=PriorityTier.P3,
            status="DEPRECATED",
            category="core_engine",
            description="Legacy LLM router replaced by MixedLLMEngine",
        ),
        ComponentEntry(
            name="TemplateEngine",
            module_path="harnessing.core.template_engine",
            tier=PriorityTier.P3,
            status="STUB",
            category="tool",
            description="Template engine for content generation (stub)",
        ),
        ComponentEntry(
            name="Scheduler",
            module_path="harnessing.core.scheduler",
            tier=PriorityTier.P3,
            status="STUB",
            category="tool",
            description="Task scheduler (stub)",
        ),
        ComponentEntry(
            name="TextToSpeechProsodyControl",
            module_path="harnessing.core.text_to_speech_prosody_control",
            tier=PriorityTier.P3,
            status="STUB",
            category="tool",
            description="TTS prosody control (stub)",
        ),
    ],
}


class PriorityArchitecture:
    def __init__(self):
        self.registry = PRIORITY_REGISTRY
        self._name_index: dict[str, ComponentEntry] = {}
        for tier, entries in self.registry.items():
            for entry in entries:
                self._name_index[entry.name] = entry

    def get_tier_components(self, tier: PriorityTier) -> list[ComponentEntry]:
        return self.registry.get(tier, [])

    def get_layer_components(self, layer: int) -> list[ComponentEntry]:
        if layer < 1 or layer > 8:
            return []
        results = []
        for entries in self.registry.values():
            for entry in entries:
                if entry.thinking_layer == layer:
                    results.append(entry)
        return results

    def get_operator_components(self, operator: str) -> list[ComponentEntry]:
        results = []
        for entries in self.registry.values():
            for entry in entries:
                if entry.formula_operator == operator:
                    results.append(entry)
        return results

    def classify_component(self, name: str) -> PriorityTier:
        entry = self._name_index.get(name)
        if entry is not None:
            return entry.tier
        return PriorityTier.P3

    def inventory_report(self) -> dict:
        tier_counts = {}
        for tier in PriorityTier:
            tier_counts[tier.value] = len(self.registry.get(tier, []))

        layer_counts = {}
        for layer_id in range(1, 9):
            layer_counts[f"L{layer_id}"] = len(self.get_layer_components(layer_id))

        operator_counts = {}
        for op in ["log", "+", "-", "*", "/", "sq", "^"]:
            operator_counts[op] = len(self.get_operator_components(op))

        category_counts = {}
        for entries in self.registry.values():
            for entry in entries:
                category_counts[entry.category] = category_counts.get(entry.category, 0) + 1

        status_counts = {}
        for entries in self.registry.values():
            for entry in entries:
                status_counts[entry.status] = status_counts.get(entry.status, 0) + 1

        p0_layer_coverage = {}
        for layer_id in range(1, 9):
            p0_in_layer = [e for e in self.get_layer_components(layer_id) if e.tier == PriorityTier.P0]
            p0_layer_coverage[f"L{layer_id}"] = len(p0_in_layer)

        p0_operator_coverage = {}
        for op in ["log", "+", "-", "*", "/", "sq", "^"]:
            p0_for_op = [e for e in self.get_operator_components(op) if e.tier == PriorityTier.P0]
            p0_operator_coverage[op] = len(p0_for_op)

        factor_layer_map = {}
        for layer_id, factors in LAYER_FACTOR_MAP.items():
            for f in factors:
                factor_layer_map.setdefault(f, []).append(layer_id)

        factor_names = {k: v["name"] for k, v in INVENTORY_FACTORS.items()}

        return {
            "total_components": self.total_components(),
            "tier_counts": tier_counts,
            "layer_counts": layer_counts,
            "operator_counts": operator_counts,
            "category_counts": category_counts,
            "status_counts": status_counts,
            "p0_layer_coverage": p0_layer_coverage,
            "p0_operator_coverage": p0_operator_coverage,
            "factor_layer_map": factor_layer_map,
            "factor_names": factor_names,
        }

    def tier_summary(self) -> str:
        lines = ["=== Priority Architecture P0-P3 Summary ===", ""]
        for tier in PriorityTier:
            entries = self.registry.get(tier, [])
            active = sum(1 for e in entries if e.status == "ACTIVE")
            stub = sum(1 for e in entries if e.status == "STUB")
            deprecated = sum(1 for e in entries if e.status == "DEPRECATED")
            archive = sum(1 for e in entries if e.status == "ARCHIVE")
            lines.append(f"{tier.value} ({tier.description})")
            lines.append(f"  Total: {len(entries)} | Active: {active} | Stub: {stub} | Deprecated: {deprecated} | Archive: {archive}")
            if tier == PriorityTier.P0:
                layer_map: dict[int, list[str]] = {}
                op_map: dict[str, list[str]] = {}
                for e in entries:
                    if e.thinking_layer is not None:
                        layer_map.setdefault(e.thinking_layer, []).append(e.name)
                    if e.formula_operator is not None:
                        op_map.setdefault(e.formula_operator, []).append(e.name)
                if layer_map:
                    lines.append("  Thinking Flow Layers:")
                    for lid in sorted(layer_map.keys()):
                        lines.append(f"    L{lid}: {', '.join(layer_map[lid])}")
                if op_map:
                    lines.append("  Formula Operators:")
                    for op in sorted(op_map.keys()):
                        lines.append(f"    {op}: {', '.join(op_map[op])}")
            lines.append("")
        return "\n".join(lines)

    def health_check(self) -> dict:
        p0_entries = self.registry.get(PriorityTier.P0, [])
        p0_active = [e for e in p0_entries if e.status == "ACTIVE"]
        p0_health = "HEALTHY" if len(p0_active) == len(p0_entries) else "DEGRADED" if len(p0_active) >= len(p0_entries) * 0.8 else "CRITICAL"

        p1_entries = self.registry.get(PriorityTier.P1, [])
        p1_active = [e for e in p1_entries if e.status == "ACTIVE"]
        p1_health = "HEALTHY" if len(p1_active) >= len(p1_entries) * 0.8 else "DEGRADED" if len(p1_active) >= len(p1_entries) * 0.5 else "CRITICAL"

        p2_entries = self.registry.get(PriorityTier.P2, [])
        p2_active = [e for e in p2_entries if e.status == "ACTIVE"]

        p3_entries = self.registry.get(PriorityTier.P3, [])
        p3_active = [e for e in p3_entries if e.status == "ACTIVE"]

        p0_layer_missing = []
        for layer_id in range(1, 9):
            p0_in_layer = [e for e in p0_entries if e.thinking_layer == layer_id]
            if not p0_in_layer:
                p0_layer_missing.append(f"L{layer_id}")

        p0_operator_missing = []
        for op in ["log", "+", "-", "*", "/", "sq", "^"]:
            p0_for_op = [e for e in p0_entries if e.formula_operator == op]
            if not p0_for_op:
                p0_operator_missing.append(op)

        overall = "HEALTHY"
        if p0_health != "HEALTHY":
            overall = "CRITICAL"
        elif p1_health != "HEALTHY":
            overall = "DEGRADED"

        return {
            "overall_health": overall,
            "p0": {
                "health": p0_health,
                "total": len(p0_entries),
                "active": len(p0_active),
                "layer_missing": p0_layer_missing,
                "operator_missing": p0_operator_missing,
            },
            "p1": {
                "health": p1_health,
                "total": len(p1_entries),
                "active": len(p1_active),
            },
            "p2": {
                "total": len(p2_entries),
                "active": len(p2_active),
            },
            "p3": {
                "total": len(p3_entries),
                "active": len(p3_active),
            },
        }

    def export_inventory(self) -> dict:
        result = {
            "version": "2.0",
            "source": "priority_architecture",
            "tiers": {},
        }
        for tier in PriorityTier:
            entries = self.registry.get(tier, [])
            result["tiers"][tier.value] = {
                "description": tier.description,
                "components": [e.to_dict() for e in entries],
                "count": len(entries),
            }
        result["summary"] = self.inventory_report()
        result["health"] = self.health_check()
        return result

    def total_components(self) -> int:
        return sum(len(entries) for entries in self.registry.values())

    def components_by_status(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for entries in self.registry.values():
            for entry in entries:
                counts[entry.status] = counts.get(entry.status, 0) + 1
        return counts

    def components_by_category(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for entries in self.registry.values():
            for entry in entries:
                counts[entry.category] = counts.get(entry.category, 0) + 1
        return counts


def generate_new_inventory_file() -> str:
    arch = PriorityArchitecture()
    inventory = arch.export_inventory()
    return json.dumps(inventory, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    arch = PriorityArchitecture()

    print("=" * 60)
    print("Priority Architecture P0-P3 — Inventory Report")
    print("=" * 60)

    print("\n" + arch.tier_summary())

    print("=== Health Check ===")
    health = arch.health_check()
    print(f"Overall: {health['overall_health']}")
    print(f"P0: {health['p0']['health']} ({health['p0']['active']}/{health['p0']['total']} active)")
    if health["p0"]["layer_missing"]:
        print(f"  Missing layers: {health['p0']['layer_missing']}")
    if health["p0"]["operator_missing"]:
        print(f"  Missing operators: {health['p0']['operator_missing']}")
    print(f"P1: {health['p1']['health']} ({health['p1']['active']}/{health['p1']['total']} active)")
    print(f"P2: {health['p2']['active']}/{health['p2']['total']} active")
    print(f"P3: {health['p3']['active']}/{health['p3']['total']} active")

    print("\n=== Inventory Report ===")
    report = arch.inventory_report()
    print(f"Total components: {report['total_components']}")
    print(f"Tier counts: {report['tier_counts']}")
    print(f"Status counts: {report['status_counts']}")
    print(f"Category counts: {report['category_counts']}")
    print(f"P0 layer coverage: {report['p0_layer_coverage']}")
    print(f"P0 operator coverage: {report['p0_operator_coverage']}")

    print("\n=== Component Lookup ===")
    for name in ["PromptEnhancer", "AbstractionEngine", "IntentBasedGuard", "InventedSkillsStubs"]:
        tier = arch.classify_component(name)
        print(f"  {name} → {tier.value} ({tier.description})")

    print("\n=== Layer Components ===")
    for layer_id in range(1, 9):
        comps = arch.get_layer_components(layer_id)
        names = [c.name for c in comps]
        print(f"  L{layer_id}: {', '.join(names)}")

    print("\n=== Operator Components ===")
    for op in ["log", "+", "-", "*", "/", "sq", "^"]:
        comps = arch.get_operator_components(op)
        names = [c.name for c in comps]
        print(f"  {op}: {', '.join(names)}")

    print("\n✅ Priority Architecture demo complete")
