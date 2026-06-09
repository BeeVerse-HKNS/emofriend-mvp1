from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import json
import time
import hashlib
import random


class ResearchPhase(Enum):
    RESEARCH = "research"
    BRAINSTORM = "brainstorm"
    FORMULA = "formula"
    TEST = "test"
    LEARN = "learn"
    ENHANCE = "enhance"


class ThinkingMethodCategory(Enum):
    WESTERN = "western"
    EASTERN = "eastern"
    INDIGENOUS = "indigenous"
    AI_NATIVE = "ai_native"


@dataclass
class ThinkingMethod:
    name: str
    category: ThinkingMethodCategory
    description: str
    origin: str
    application: str


@dataclass
class ResearchSource:
    name: str
    url: str
    category: str
    reliability: str


@dataclass
class ResearchIteration:
    iteration: int
    phase: ResearchPhase
    thinking_methods_used: list[str]
    sources_queried: list[str]
    insights: list[str]
    new_directions: list[str]
    confidence: str
    timestamp: float = 0.0


@dataclass
class DeepResearchResult:
    total_iterations: int
    total_insights: int
    total_new_directions: int
    iterations: list[ResearchIteration]
    confidence_distribution: dict[str, int]
    thinking_methods_coverage: dict[str, int]
    source_coverage: dict[str, int]


_PHASE_METHOD_AFFINITY: dict[ResearchPhase, list[ThinkingMethodCategory]] = {
    ResearchPhase.RESEARCH: [ThinkingMethodCategory.WESTERN, ThinkingMethodCategory.AI_NATIVE],
    ResearchPhase.BRAINSTORM: [ThinkingMethodCategory.EASTERN, ThinkingMethodCategory.INDIGENOUS, ThinkingMethodCategory.AI_NATIVE],
    ResearchPhase.FORMULA: [ThinkingMethodCategory.WESTERN, ThinkingMethodCategory.AI_NATIVE],
    ResearchPhase.TEST: [ThinkingMethodCategory.WESTERN],
    ResearchPhase.LEARN: [ThinkingMethodCategory.EASTERN, ThinkingMethodCategory.INDIGENOUS],
    ResearchPhase.ENHANCE: [ThinkingMethodCategory.AI_NATIVE, ThinkingMethodCategory.EASTERN],
}

_PHASE_INSIGHT_TEMPLATES: dict[ResearchPhase, list[str]] = {
    ResearchPhase.RESEARCH: [
        "Discovered new factor: {topic}_factor_{idx}",
        "Identified correlation between {topic} and dimension {dim}",
        "Found research gap in {topic} at iteration {iter}",
        "Mapped knowledge boundary for {topic} sub-domain {idx}",
        "Uncovered latent variable affecting {topic} outcomes",
    ],
    ResearchPhase.BRAINSTORM: [
        "Novel approach: combine {topic} with {method} thinking",
        "Creative direction: reframe {topic} through {method} lens",
        "Breakthrough idea: apply {method} principle to {topic}",
        "Lateral insight: invert {topic} assumption using {method}",
        "Cross-pollination: merge {topic} with {method} paradigm",
    ],
    ResearchPhase.FORMULA: [
        "Formula generated: ({dim1} + {dim2}) * {dim3} for {topic}",
        "Coverage formula: log({dim1}) + {dim2} ^ {dim3} addresses {topic}",
        "Synergy formula: ({dim1} * {dim2}) - {dim3} optimizes {topic}",
        "Self-improve formula: sq({dim1}) + log({dim2}) for {topic}",
        "Decomposition formula: sqrt({dim1} * {dim2}) reveals {topic} structure",
    ],
    ResearchPhase.TEST: [
        "Test passed for {topic} scenario {idx} with coverage {coverage}",
        "Stress test: {topic} handles {idx} edge cases successfully",
        "Validation: {topic} formula achieves {coverage} coverage rate",
        "Boundary test: {topic} stable at iteration {iter} limits",
        "Regression test: {topic} maintains consistency across {idx} variants",
    ],
    ResearchPhase.LEARN: [
        "Rule extracted: {topic} requires {method} guardrail at depth {idx}",
        "Lesson: {topic} iteration {iter} reveals {method} optimization",
        "Pattern: {topic} converges when {method} applied at phase {idx}",
        "Error rule: {topic} fails without {method} validation step",
        "Insight: {topic} benefits from {method} feedback loop",
    ],
    ResearchPhase.ENHANCE: [
        "Enhanced {topic} with {method} skill at level {idx}",
        "Upgraded {topic} pipeline using {method} optimization",
        "Integrated {method} capability into {topic} framework",
        "Deployed {method} enhancement for {topic} at iteration {iter}",
        "Synchronized {method} improvement to {topic} production system",
    ],
}

_DIMENSION_KEYS = ["K", "R", "C", "M", "S", "G", "A", "P", "F", "H"]

_CONFIDENCE_WEIGHTS = {
    ResearchPhase.RESEARCH: {"✅": 0.4, "🔍": 0.35, "⚠️": 0.2, "❌": 0.05},
    ResearchPhase.BRAINSTORM: {"✅": 0.2, "🔍": 0.3, "⚠️": 0.35, "❌": 0.15},
    ResearchPhase.FORMULA: {"✅": 0.3, "🔍": 0.3, "⚠️": 0.25, "❌": 0.15},
    ResearchPhase.TEST: {"✅": 0.5, "🔍": 0.25, "⚠️": 0.2, "❌": 0.05},
    ResearchPhase.LEARN: {"✅": 0.45, "🔍": 0.3, "⚠️": 0.2, "❌": 0.05},
    ResearchPhase.ENHANCE: {"✅": 0.35, "🔍": 0.3, "⚠️": 0.25, "❌": 0.1},
}

_DIRECTION_TEMPLATES = [
    "Explore {topic} through {method} analytical framework",
    "Apply {method} optimization to {topic} bottleneck",
    "Investigate {topic} cross-domain synergy with {method}",
    "Develop {method}-inspired metric for {topic} evaluation",
    "Construct {topic} knowledge graph using {method} principles",
    "Validate {topic} hypothesis via {method} experimental design",
    "Scale {topic} solution using {method} decomposition strategy",
    "Integrate {method} feedback loop into {topic} pipeline",
]


class DeepResearch100xEngine:
    def __init__(self):
        self.thinking_methods: dict[str, ThinkingMethod] = {}
        self.research_sources: dict[str, ResearchSource] = {}
        self.iterations: list[ResearchIteration] = []
        self.results: Optional[DeepResearchResult] = None
        self._init_thinking_methods()
        self._init_research_sources()

    def _init_thinking_methods(self):
        western_methods = [
            ThinkingMethod("Design Thinking", ThinkingMethodCategory.WESTERN, "Human-centered innovation approach", "Stanford d.school", "Problem framing and solution ideation"),
            ThinkingMethod("TRIZ", ThinkingMethodCategory.WESTERN, "Theory of inventive problem solving via contradictions", "Genrich Altshuller, USSR", "Systematic invention and patent analysis"),
            ThinkingMethod("SCAMPER", ThinkingMethodCategory.WESTERN, "Structured creative thinking via 7 prompts", "Bob Eberle", "Product and process improvement"),
            ThinkingMethod("Six Thinking Hats", ThinkingMethodCategory.WESTERN, "Parallel thinking via role-based perspectives", "Edward de Bono", "Group decision making and analysis"),
            ThinkingMethod("Lateral Thinking", ThinkingMethodCategory.WESTERN, "Indirect reasoning to escape established patterns", "Edward de Bono", "Creative problem solving beyond logic"),
            ThinkingMethod("Mind Mapping", ThinkingMethodCategory.WESTERN, "Radial diagram for associative thinking", "Tony Buzan", "Knowledge organization and brainstorming"),
            ThinkingMethod("First Principles", ThinkingMethodCategory.WESTERN, "Decompose to fundamental truths and rebuild", "Aristotle / Elon Musk", "Breaking assumptions for novel solutions"),
            ThinkingMethod("Scientific Method", ThinkingMethodCategory.WESTERN, "Hypothesis-driven experimentation", "Francis Bacon", "Empirical validation and theory building"),
            ThinkingMethod("Systems Thinking", ThinkingMethodCategory.WESTERN, "Holistic analysis of interrelated components", "Ludwig von Bertalanffy", "Understanding complex system behavior"),
            ThinkingMethod("Critical Path Method", ThinkingMethodCategory.WESTERN, "Schedule-based project optimization", "DuPont / Remington Rand", "Task sequencing and resource allocation"),
        ]
        eastern_methods = [
            ThinkingMethod("易經思維", ThinkingMethodCategory.EASTERN, "Binary change dynamics via 64 hexagrams", "伏羲 / 周文王", "Pattern recognition in complex transitions"),
            ThinkingMethod("孫子兵法", ThinkingMethodCategory.EASTERN, "Strategic advantage through deception and positioning", "孫武", "Competitive strategy and resource optimization"),
            ThinkingMethod("禪宗思維", ThinkingMethodCategory.EASTERN, "Direct insight beyond rational analysis via koan", "菩提達摩", "Breaking mental models for breakthrough"),
            ThinkingMethod("太極思維", ThinkingMethodCategory.EASTERN, "Dynamic balance of complementary opposites", "老子 / 莊子", "Managing trade-offs and equilibrium"),
            ThinkingMethod("諸葛亮三十六計", ThinkingMethodCategory.EASTERN, "36 stratagems for adversarial advantage", "諸葛亮", "Tactical problem solving under constraints"),
            ThinkingMethod("儒家系統思維", ThinkingMethodCategory.EASTERN, "Relational ethics and hierarchical harmony", "孔子 / 孟子", "Stakeholder alignment and governance"),
            ThinkingMethod("道家無為思維", ThinkingMethodCategory.EASTERN, "Effortless action aligned with natural flow", "老子", "Minimal intervention for maximum effect"),
            ThinkingMethod("墨家邏輯思維", ThinkingMethodCategory.EASTERN, "Rigorous argumentation and empirical testing", "墨子", "Logical proof and practical verification"),
            ThinkingMethod("法家制度思維", ThinkingMethodCategory.EASTERN, "Rule-based governance with clear incentives", "韓非子", "System design with enforcement mechanisms"),
            ThinkingMethod("兵家博弈思維", ThinkingMethodCategory.EASTERN, "Game-theoretic analysis of conflict", "孫臏 / 吳起", "Multi-agent competitive optimization"),
        ]
        indigenous_methods = [
            ThinkingMethod("Haudenosaunee Great Law", ThinkingMethodCategory.INDIGENOUS, "Seventh-generation decision making", "Haudenosaunee Confederacy", "Long-term impact assessment"),
            ThinkingMethod("Bayanihan", ThinkingMethodCategory.INDIGENOUS, "Collective community action for shared goals", "Philippines", "Distributed collaboration and mutual aid"),
            ThinkingMethod("Minga", ThinkingMethodCategory.INDIGENOUS, "Reciprocal communal work for common benefit", "Andean Indigenous Communities", "Community-driven infrastructure"),
            ThinkingMethod("Ubuntu", ThinkingMethodCategory.INDIGENOUS, "I am because we are — relational identity", "Southern Africa", "Inclusive system design and ethics"),
            ThinkingMethod("Whakapapa", ThinkingMethodCategory.INDIGENOUS, "Genealogical layering connecting all things", "Maori", "System lineage and dependency tracing"),
            ThinkingMethod("Two-Eyed Seeing", ThinkingMethodCategory.INDIGENOUS, "Integrating Indigenous and Western knowledge", "Elder Albert Marshall, Mi'kmaq", "Multi-paradigm synthesis"),
        ]
        ai_native_methods = [
            ThinkingMethod("Prompt Engineering", ThinkingMethodCategory.AI_NATIVE, "Structured input design for LLM optimization", "AI Community", "Maximizing LLM output quality"),
            ThinkingMethod("Chain-of-Thought", ThinkingMethodCategory.AI_NATIVE, "Step-by-step reasoning decomposition", "Google Research", "Complex reasoning tasks"),
            ThinkingMethod("Tree-of-Thought", ThinkingMethodCategory.AI_NATIVE, "Branching exploration of reasoning paths", "Yao et al., Princeton", "Multi-path problem solving"),
            ThinkingMethod("Self-Consistency", ThinkingMethodCategory.AI_NATIVE, "Majority voting across sampled reasoning chains", "Wang et al.", "Improving reasoning reliability"),
            ThinkingMethod("ReAct", ThinkingMethodCategory.AI_NATIVE, "Interleaved reasoning and action loops", "Yao et al.", "Agent-based task execution"),
            ThinkingMethod("Reflexion", ThinkingMethodCategory.AI_NATIVE, "Self-evaluation and iterative improvement", "Shinn et al.", "Learning from failed attempts"),
            ThinkingMethod("AutoGPT Pattern", ThinkingMethodCategory.AI_NATIVE, "Autonomous goal decomposition and execution", "Significant Gravitas", "Self-directed task completion"),
            ThinkingMethod("RAG", ThinkingMethodCategory.AI_NATIVE, "Retrieval-augmented generation from knowledge base", "Lewis et al., Facebook AI", "Grounded knowledge synthesis"),
            ThinkingMethod("Few-Shot Learning", ThinkingMethodCategory.AI_NATIVE, "Learning from minimal examples via in-context learning", "Brown et al., OpenAI", "Rapid task adaptation"),
            ThinkingMethod("Constitutional AI", ThinkingMethodCategory.AI_NATIVE, "Self-improvement via principle-based critique", "Anthropic", "Safety-aligned output generation"),
            ThinkingMethod("Formula Thinking", ThinkingMethodCategory.AI_NATIVE, "Mathematical operator composition for invention", "Harnessing Engineering", "Systematic innovation generation"),
            ThinkingMethod("Meta-Prompting", ThinkingMethodCategory.AI_NATIVE, "Prompts that generate and refine other prompts", "AI Research Community", "Recursive self-improvement"),
            ThinkingMethod("Multi-Agent Debate", ThinkingMethodCategory.AI_NATIVE, "Adversarial collaboration between AI agents", "Du et al.", "Improving answer quality via critique"),
            ThinkingMethod("Knowledge Distillation", ThinkingMethodCategory.AI_NATIVE, "Compressing large model knowledge into smaller models", "Hinton et al.", "Efficient model deployment"),
            ThinkingMethod("Self-Play", ThinkingMethodCategory.AI_NATIVE, "Agent improves by competing against itself", "Silver et al., DeepMind", "Exceeding human-level performance"),
        ]
        for method in western_methods + eastern_methods + indigenous_methods + ai_native_methods:
            self.thinking_methods[method.name] = method

    def _init_research_sources(self):
        western_sources = [
            ResearchSource("arXiv", "https://arxiv.org", "western", "✅"),
            ResearchSource("Nature", "https://nature.com", "western", "✅"),
            ResearchSource("Science", "https://science.org", "western", "✅"),
            ResearchSource("MIT OpenCourseWare", "https://ocw.mit.edu", "western", "✅"),
            ResearchSource("Stanford AI Lab", "https://ai.stanford.edu", "western", "🔍"),
            ResearchSource("Oxford Research", "https://research.ox.ac.uk", "western", "🔍"),
            ResearchSource("Cambridge Research", "https://cam.ac.uk/research", "western", "🔍"),
            ResearchSource("Max Planck Institute", "https://mpg.de", "western", "✅"),
        ]
        eastern_sources = [
            ResearchSource("中國科學院", "https://cas.cn", "eastern", "✅"),
            ResearchSource("清華大學", "https://tsinghua.edu.cn", "eastern", "✅"),
            ResearchSource("東京大學", "https://u-tokyo.ac.jp", "eastern", "✅"),
            ResearchSource("IISc Bangalore", "https://iisc.ac.in", "eastern", "🔍"),
            ResearchSource("KAIST", "https://kaist.ac.kr", "eastern", "🔍"),
            ResearchSource("NUS", "https://nus.edu.sg", "eastern", "✅"),
            ResearchSource("北京大學", "https://pku.edu.cn", "eastern", "✅"),
            ResearchSource("復旦大學", "https://fudan.edu.cn", "eastern", "🔍"),
        ]
        china_sources = [
            ResearchSource("知網 CNKI", "https://cnki.net", "china", "✅"),
            ResearchSource("萬方數據", "https://wanfangdata.com.cn", "china", "✅"),
            ResearchSource("百度學術", "https://xueshu.baidu.com", "china", "🔍"),
            ResearchSource("騰訊AI Lab", "https://ai.tencent.com", "china", "🔍"),
            ResearchSource("阿里達摩院", "https://damo.alibaba.com", "china", "🔍"),
            ResearchSource("華為諾亞方舟實驗室", "https://noahlab.huawei.com", "china", "⚠️"),
            ResearchSource("字節跳動AI Lab", "https://ailab.bytedance.com", "china", "⚠️"),
            ResearchSource("商湯科技研究院", "https://sensetime.com", "china", "⚠️"),
        ]
        for source in western_sources + eastern_sources + china_sources:
            self.research_sources[source.name] = source

    def _select_methods_for_phase(self, phase: ResearchPhase, iteration: int) -> list[str]:
        preferred_categories = _PHASE_METHOD_AFFINITY.get(phase, [ThinkingMethodCategory.AI_NATIVE])
        seed = hash(f"{phase.value}_{iteration}") % (2**31)
        rng = random.Random(seed)
        category_methods: dict[ThinkingMethodCategory, list[str]] = {}
        for name, method in self.thinking_methods.items():
            if method.category not in category_methods:
                category_methods[method.category] = []
            category_methods[method.category].append(name)
        selected: list[str] = []
        for cat in preferred_categories:
            available = category_methods.get(cat, [])
            if available:
                count = min(2 + (iteration // 20), len(available))
                chosen = rng.sample(available, count)
                selected.extend(chosen)
        all_methods = list(self.thinking_methods.keys())
        if iteration % 7 == 0 and len(all_methods) > len(selected):
            extra = rng.choice([m for m in all_methods if m not in selected])
            selected.append(extra)
        return selected

    def _select_sources_for_topic(self, topic: str, iteration: int) -> list[str]:
        seed = hash(f"{topic}_{iteration}") % (2**31)
        rng = random.Random(seed)
        topic_lower = topic.lower()
        category_weights = {"western": 1.0, "eastern": 1.0, "china": 1.0}
        eastern_keywords = ["易經", "孫子", "禪", "太極", "儒家", "道家", "墨家", "法家", "兵家", "中國", "東方"]
        china_keywords = ["中國", "知網", "萬方", "百度", "騰訊", "阿里", "華為", "字節", "商湯"]
        western_keywords = ["design", "TRIZ", "SCAMPER", "scientific", "system", "first principle"]
        for kw in eastern_keywords:
            if kw in topic_lower:
                category_weights["eastern"] = 2.0
                break
        for kw in china_keywords:
            if kw in topic_lower:
                category_weights["china"] = 2.0
                break
        for kw in western_keywords:
            if kw in topic_lower:
                category_weights["western"] = 2.0
                break
        selected: list[str] = []
        for cat, weight in category_weights.items():
            cat_sources = [s.name for s in self.research_sources.values() if s.category == cat]
            count = max(1, int(weight * (1 + iteration // 25)))
            count = min(count, len(cat_sources))
            if cat_sources:
                chosen = rng.sample(cat_sources, count)
                selected.extend(chosen)
        return selected

    def _generate_insights(self, topic: str, phase: ResearchPhase, iteration: int, methods: list[str]) -> list[str]:
        templates = _PHASE_INSIGHT_TEMPLATES.get(phase, [])
        if not templates:
            return []
        seed = hash(f"insight_{topic}_{phase.value}_{iteration}") % (2**31)
        rng = random.Random(seed)
        num_insights = min(2 + iteration // 15, 5)
        insights: list[str] = []
        for i in range(num_insights):
            template = rng.choice(templates)
            method_name = rng.choice(methods) if methods else "general"
            dim1 = rng.choice(_DIMENSION_KEYS)
            dim2 = rng.choice([d for d in _DIMENSION_KEYS if d != dim1])
            dim3 = rng.choice([d for d in _DIMENSION_KEYS if d not in (dim1, dim2)])
            coverage = round(0.6 + iteration * 0.004 + rng.uniform(-0.02, 0.02), 4)
            insight = template.format(
                topic=topic,
                method=method_name,
                idx=i + 1,
                iter=iteration,
                dim=dim1,
                dim1=dim1,
                dim2=dim2,
                dim3=dim3,
                coverage=coverage,
            )
            insights.append(insight)
        return insights

    def _generate_directions(self, topic: str, iteration: int, methods: list[str]) -> list[str]:
        seed = hash(f"direction_{topic}_{iteration}") % (2**31)
        rng = random.Random(seed)
        num_directions = min(1 + iteration // 20, 4)
        directions: list[str] = []
        for i in range(num_directions):
            template = rng.choice(_DIRECTION_TEMPLATES)
            method_name = rng.choice(methods) if methods else "general"
            direction = template.format(topic=topic, method=method_name)
            directions.append(direction)
        return directions

    def _determine_confidence(self, phase: ResearchPhase, iteration: int) -> str:
        weights = _CONFIDENCE_WEIGHTS.get(phase, _CONFIDENCE_WEIGHTS[ResearchPhase.RESEARCH])
        iteration_boost = min(iteration * 0.005, 0.15)
        adjusted = {
            "✅": weights["✅"] + iteration_boost,
            "🔍": weights["🔍"],
            "⚠️": max(weights["⚠️"] - iteration_boost * 0.5, 0.05),
            "❌": max(weights["❌"] - iteration_boost * 0.5, 0.01),
        }
        total = sum(adjusted.values())
        normalized = {k: v / total for k, v in adjusted.items()}
        seed = hash(f"confidence_{phase.value}_{iteration}") % (2**31)
        rng = random.Random(seed)
        roll = rng.random()
        cumulative = 0.0
        for level, prob in normalized.items():
            cumulative += prob
            if roll <= cumulative:
                return level
        return "⚠️"

    def run_iteration(self, iteration: int, topic: str, phase: ResearchPhase) -> ResearchIteration:
        methods = self._select_methods_for_phase(phase, iteration)
        sources = self._select_sources_for_topic(topic, iteration)
        insights = self._generate_insights(topic, phase, iteration, methods)
        directions = self._generate_directions(topic, iteration, methods)
        confidence = self._determine_confidence(phase, iteration)
        result = ResearchIteration(
            iteration=iteration,
            phase=phase,
            thinking_methods_used=methods,
            sources_queried=sources,
            insights=insights,
            new_directions=directions,
            confidence=confidence,
            timestamp=time.time(),
        )
        self.iterations.append(result)
        return result

    def run_batch(self, start: int, end: int, topics: list[str]) -> list[ResearchIteration]:
        phases = list(ResearchPhase)
        results: list[ResearchIteration] = []
        for i in range(start, end + 1):
            phase = phases[(i - 1) % len(phases)]
            topic = topics[(i - 1) % len(topics)] if topics else "universal_coverage"
            result = self.run_iteration(i, topic, phase)
            results.append(result)
        return results

    def run_full_100x(self, topics: list[str]) -> DeepResearchResult:
        self.iterations.clear()
        phases = list(ResearchPhase)
        for i in range(1, 101):
            phase = phases[(i - 1) % len(phases)]
            topic = topics[(i - 1) % len(topics)] if topics else "universal_coverage"
            self.run_iteration(i, topic, phase)
        total_insights = sum(len(it.insights) for it in self.iterations)
        total_directions = sum(len(it.new_directions) for it in self.iterations)
        confidence_dist: dict[str, int] = {"✅": 0, "🔍": 0, "⚠️": 0, "❌": 0}
        for it in self.iterations:
            if it.confidence in confidence_dist:
                confidence_dist[it.confidence] += 1
            else:
                confidence_dist[it.confidence] = 1
        methods_coverage: dict[str, int] = {}
        for it in self.iterations:
            for method in it.thinking_methods_used:
                methods_coverage[method] = methods_coverage.get(method, 0) + 1
        source_coverage: dict[str, int] = {}
        for it in self.iterations:
            for source in it.sources_queried:
                source_coverage[source] = source_coverage.get(source, 0) + 1
        self.results = DeepResearchResult(
            total_iterations=len(self.iterations),
            total_insights=total_insights,
            total_new_directions=total_directions,
            iterations=self.iterations,
            confidence_distribution=confidence_dist,
            thinking_methods_coverage=methods_coverage,
            source_coverage=source_coverage,
        )
        return self.results

    def get_insights_by_method(self, method_name: str) -> list[str]:
        insights: list[str] = []
        for it in self.iterations:
            if method_name in it.thinking_methods_used:
                insights.extend(it.insights)
        return insights

    def get_insights_by_phase(self, phase: ResearchPhase) -> list[str]:
        insights: list[str] = []
        for it in self.iterations:
            if it.phase == phase:
                insights.extend(it.insights)
        return insights

    def export_results(self) -> dict:
        if self.results is None:
            return {
                "total_iterations": len(self.iterations),
                "iterations": [
                    {
                        "iteration": it.iteration,
                        "phase": it.phase.value,
                        "thinking_methods_used": it.thinking_methods_used,
                        "sources_queried": it.sources_queried,
                        "insights": it.insights,
                        "new_directions": it.new_directions,
                        "confidence": it.confidence,
                        "timestamp": it.timestamp,
                    }
                    for it in self.iterations
                ],
            }
        return {
            "total_iterations": self.results.total_iterations,
            "total_insights": self.results.total_insights,
            "total_new_directions": self.results.total_new_directions,
            "confidence_distribution": self.results.confidence_distribution,
            "thinking_methods_coverage": self.results.thinking_methods_coverage,
            "source_coverage": self.results.source_coverage,
            "iterations": [
                {
                    "iteration": it.iteration,
                    "phase": it.phase.value,
                    "thinking_methods_used": it.thinking_methods_used,
                    "sources_queried": it.sources_queried,
                    "insights": it.insights,
                    "new_directions": it.new_directions,
                    "confidence": it.confidence,
                    "timestamp": it.timestamp,
                }
                for it in self.results.iterations
            ],
        }

    def save_results(self, filepath: str) -> None:
        data = self.export_results()
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
