"""
Human-AI Communication Bridge (人機溝通橋接器)

3-Stage Translation Pipeline:
  Stage 1: Human Language → Internal Language (Decode)
  Stage 2: Internal Processing (Think)
  Stage 3: Internal Language → Human Language (Encode)

Core Philosophy: AI is the Implementation King (執行者), NOT the Decision Maker (決策者).
AI does: Research → Formula Thinking → Testing → Detailed Report → User Decision
AI does NOT: Make decisions for the user, skip feedback, assume what user wants.

Formula: (R * K + C) ^ E - L
  R * K  = Reasoning × Knowledge (rational processing)
  + C    = + Creativity (feeling/intuitive processing)
  ^ E   = amplified by Emotion awareness (empathetic processing)
  - L   = minus Linear bias (breaking token-by-token thinking)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class ThinkingMode(Enum):
    RATIONAL = "rational"
    EMOTIONAL = "emotional"
    INTUITIVE = "intuitive"
    ANALYTICAL = "analytical"
    CREATIVE = "creative"
    PRACTICAL = "practical"


class OutputPurpose(Enum):
    REPORT = "report"
    SUGGESTION = "suggestion"
    BRAINSTORM = "brainstorm"
    DECISION_SUPPORT = "decision_support"
    FEEDBACK = "feedback"
    IMPLEMENTATION = "implementation"


class ConfidenceLevel(Enum):
    VERIFIED = "verified"
    RESEARCHED = "researched"
    INFERRED = "inferred"
    UNCERTAIN = "uncertain"


@dataclass
class InternalRepresentation:
    """AI's internal language representation of human input."""
    raw_input: str
    intent: str
    context: Dict[str, Any] = field(default_factory=dict)
    thinking_modes: List[ThinkingMode] = field(default_factory=list)
    rational_analysis: Dict[str, Any] = field(default_factory=dict)
    emotional_analysis: Dict[str, Any] = field(default_factory=dict)
    knowledge_gaps: List[str] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    confidence: Dict[str, ConfidenceLevel] = field(default_factory=dict)
    urgency: float = 0.5
    complexity: float = 0.5
    needs_research: bool = False
    needs_testing: bool = False
    needs_formula_thinking: bool = False


@dataclass
class ProcessingResult:
    """Result of internal processing."""
    findings: List[str] = field(default_factory=list)
    recommendations: List[Dict[str, Any]] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    alternatives: List[Dict[str, Any]] = field(default_factory=list)
    test_results: Optional[Dict[str, Any]] = None
    formula_results: Optional[Dict[str, Any]] = None
    research_summary: Optional[str] = None
    confidence_scores: Dict[str, float] = field(default_factory=dict)
    decision_points: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class HumanOutput:
    """Human-readable output from AI processing."""
    summary: str
    detailed_report: str
    decision_points: List[Dict[str, Any]] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    next_steps: List[str] = field(default_factory=list)
    confidence_markers: Dict[str, str] = field(default_factory=dict)
    purpose: OutputPurpose = OutputPurpose.REPORT
    requires_user_decision: bool = False
    feedback_requested: bool = True


@dataclass
class FeedbackEntry:
    """Record of user feedback on AI output."""
    output_id: str
    user_response: str
    accepted: bool
    adjustments: List[str] = field(default_factory=list)
    learning_points: List[str] = field(default_factory=list)


class HumanLanguageDecoder:
    """Stage 1: Human Language → Internal Language (解碼器)

    Translates human natural language into AI's internal representation,
    incorporating rational, emotional, and intuitive thinking dimensions.
    """

    INTENT_KEYWORDS = {
        "create": ["create", "build", "make", "add", "implement", "develop", "新建", "建立", "創建", "實現"],
        "fix": ["fix", "repair", "debug", "resolve", "patch", "修復", "修", "debug", "解決"],
        "research": ["research", "investigate", "study", "analyze", "explore", "研究", "調查", "分析", "探索"],
        "deploy": ["deploy", "publish", "release", "launch", "部署", "發佈", "上線"],
        "design": ["design", "architect", "plan", "layout", "設計", "架構", "規劃"],
        "test": ["test", "verify", "validate", "qa", "測試", "驗證", "確認"],
        "optimize": ["optimize", "improve", "enhance", "speed up", "優化", "改善", "提升"],
        "decide": ["decide", "choose", "select", "pick", "決定", "選擇", "抉擇"],
    }

    URGENCY_KEYWORDS = {
        0.9: ["urgent", "asap", "immediately", "critical", "緊急", "立刻", "馬上", "緊要"],
        0.7: ["important", "soon", "priority", "重要", "盡快", "優先"],
        0.3: ["when possible", "no rush", "later", "有空", "不急", "慢慢來"],
    }

    EMOTIONAL_KEYWORDS = {
        "frustrated": ["frustrated", "annoyed", "stuck", "沮喪", "煩躁", "卡住"],
        "excited": ["excited", "great", "awesome", "興奮", "太好了", "棒"],
        "confused": ["confused", "unclear", "don't understand", "困惑", "不明白", "不清楚"],
        "worried": ["worried", "concerned", "anxious", "擔心", "焦慮", "憂慮"],
        "curious": ["curious", "wonder", "interested", "好奇", "想知道"],
    }

    def decode(self, human_input: str, context: Optional[Dict[str, Any]] = None) -> InternalRepresentation:
        """Translate human language into internal representation."""
        intent = self._extract_intent(human_input)
        urgency = self._extract_urgency(human_input)
        thinking_modes = self._determine_thinking_modes(human_input, intent)
        emotional_state = self._detect_emotional_state(human_input)
        knowledge_gaps = self._identify_knowledge_gaps(human_input, intent)
        assumptions = self._identify_assumptions(human_input)
        needs = self._determine_needs(intent, human_input)

        rational_analysis = {
            "intent": intent,
            "urgency": urgency,
            "complexity": self._estimate_complexity(human_input, intent),
            "key_entities": self._extract_entities(human_input),
            "constraints": self._extract_constraints(human_input),
        }

        emotional_analysis = {
            "detected_emotion": emotional_state,
            "user_frustration_level": self._calculate_frustration(human_input, emotional_state),
            "empathy_required": emotional_state in ("frustrated", "worried", "confused"),
            "tone_adjustment": self._determine_tone(emotional_state),
        }

        confidence = {}
        for gap in knowledge_gaps:
            confidence[gap] = ConfidenceLevel.UNCERTAIN
        for assumption in assumptions:
            confidence[f"assumption:{assumption}"] = ConfidenceLevel.INFERRED

        return InternalRepresentation(
            raw_input=human_input,
            intent=intent,
            context=context or {},
            thinking_modes=thinking_modes,
            rational_analysis=rational_analysis,
            emotional_analysis=emotional_analysis,
            knowledge_gaps=knowledge_gaps,
            assumptions=assumptions,
            confidence=confidence,
            urgency=urgency,
            complexity=rational_analysis["complexity"],
            needs_research=needs["research"],
            needs_testing=needs["testing"],
            needs_formula_thinking=needs["formula_thinking"],
        )

    def _extract_intent(self, text: str) -> str:
        text_lower = text.lower()
        for intent, keywords in self.INTENT_KEYWORDS.items():
            for kw in keywords:
                if kw in text_lower:
                    return intent
        return "understand"

    def _extract_urgency(self, text: str) -> float:
        text_lower = text.lower()
        for level, keywords in self.URGENCY_KEYWORDS.items():
            for kw in keywords:
                if kw in text_lower:
                    return level
        return 0.5

    def _determine_thinking_modes(self, text: str, intent: str) -> List[ThinkingMode]:
        modes = [ThinkingMode.RATIONAL]
        if intent in ("create", "design"):
            modes.append(ThinkingMode.CREATIVE)
        if intent in ("research", "decide"):
            modes.append(ThinkingMode.ANALYTICAL)
        if intent in ("fix", "deploy", "optimize"):
            modes.append(ThinkingMode.PRACTICAL)
        emotional_state = self._detect_emotional_state(text)
        if emotional_state in ("frustrated", "worried", "confused"):
            modes.append(ThinkingMode.EMOTIONAL)
        if any(kw in text.lower() for kw in ["intuition", "gut feeling", "直覺", "感覺"]):
            modes.append(ThinkingMode.INTUITIVE)
        return list(dict.fromkeys(modes))

    def _detect_emotional_state(self, text: str) -> str:
        text_lower = text.lower()
        for emotion, keywords in self.EMOTIONAL_KEYWORDS.items():
            for kw in keywords:
                if kw in text_lower:
                    return emotion
        return "neutral"

    def _identify_knowledge_gaps(self, text: str, intent: str) -> List[str]:
        gaps = []
        question_markers = ["how", "what", "why", "which", "where", "誰", "什麼", "為什麼", "如何", "哪個"]
        text_lower = text.lower()
        for marker in question_markers:
            if marker in text_lower:
                gaps.append(f"question_about:{marker}")
                break
        if intent == "decide":
            gaps.append("decision_criteria_needed")
        if intent == "research":
            gaps.append("research_scope_needed")
        return gaps

    def _identify_assumptions(self, text: str) -> List[str]:
        assumptions = []
        assumption_markers = ["assume", "probably", "likely", "should", "假設", "應該", "可能"]
        text_lower = text.lower()
        for marker in assumption_markers:
            if marker in text_lower:
                assumptions.append(f"assumption_detected:{marker}")
        return assumptions

    def _determine_needs(self, intent: str, text: str) -> Dict[str, bool]:
        needs = {"research": False, "testing": False, "formula_thinking": False}
        if intent in ("research", "decide"):
            needs["research"] = True
        if intent in ("create", "fix", "optimize"):
            needs["testing"] = True
        if intent in ("create", "design", "decide"):
            needs["formula_thinking"] = True
        research_markers = ["research", "study", "investigate", "研究", "調查"]
        if any(m in text.lower() for m in research_markers):
            needs["research"] = True
        test_markers = ["test", "verify", "validate", "測試", "驗證"]
        if any(m in text.lower() for m in test_markers):
            needs["testing"] = True
        return needs

    def _estimate_complexity(self, text: str, intent: str) -> float:
        base = {"create": 0.7, "fix": 0.5, "research": 0.8, "deploy": 0.6,
                "design": 0.7, "test": 0.4, "optimize": 0.6, "decide": 0.7,
                "understand": 0.3}
        complexity = base.get(intent, 0.5)
        multi_concept_markers = ["and", "also", "plus", "同時", "另外", "加上", "以及"]
        for marker in multi_concept_markers:
            if marker in text.lower():
                complexity = min(1.0, complexity + 0.1)
        return complexity

    def _extract_entities(self, text: str) -> List[str]:
        entities = []
        tech_terms = ["python", "streamlit", "docker", "api", "database", "redis",
                      "ollama", "flask", "react", "nextjs", "supabase"]
        text_lower = text.lower()
        for term in tech_terms:
            if term in text_lower:
                entities.append(term)
        return entities

    def _extract_constraints(self, text: str) -> List[str]:
        constraints = []
        constraint_markers = ["must", "cannot", "without", "only", "必須", "不能", "只", "不依賴"]
        text_lower = text.lower()
        for marker in constraint_markers:
            if marker in text_lower:
                idx = text_lower.index(marker)
                snippet = text[max(0, idx - 10):idx + 40]
                constraints.append(snippet.strip())
        return constraints

    def _calculate_frustration(self, text: str, emotional_state: str) -> float:
        if emotional_state == "frustrated":
            return 0.8
        if emotional_state == "worried":
            return 0.5
        if emotional_state == "confused":
            return 0.4
        exclamation_count = text.count("!")
        caps_ratio = sum(1 for c in text if c.isupper()) / max(len(text), 1)
        return min(1.0, exclamation_count * 0.1 + caps_ratio * 0.3)

    def _determine_tone(self, emotional_state: str) -> str:
        tone_map = {
            "frustrated": "calm_supportive",
            "worried": "reassuring_detailed",
            "confused": "clear_step_by_step",
            "excited": "enthusiastic_structured",
            "curious": "informive_exploratory",
            "neutral": "professional_balanced",
        }
        return tone_map.get(emotional_state, "professional_balanced")


class InternalProcessor:
    """Stage 2: Internal Processing (內部處理器)

    Processes the internal representation using rational, emotional,
    and creative thinking dimensions. AI acts as Implementation King:
    Research → Formula Thinking → Testing → Report for user decision.
    """

    def process(self, internal: InternalRepresentation) -> ProcessingResult:
        """Process internal representation through multiple thinking dimensions."""
        result = ProcessingResult()

        for mode in internal.thinking_modes:
            if mode == ThinkingMode.RATIONAL:
                self._rational_process(internal, result)
            elif mode == ThinkingMode.EMOTIONAL:
                self._emotional_process(internal, result)
            elif mode == ThinkingMode.CREATIVE:
                self._creative_process(internal, result)
            elif mode == ThinkingMode.ANALYTICAL:
                self._analytical_process(internal, result)
            elif mode == ThinkingMode.PRACTICAL:
                self._practical_process(internal, result)
            elif mode == ThinkingMode.INTUITIVE:
                self._intuitive_process(internal, result)

        if internal.needs_research:
            result.research_summary = self._generate_research_plan(internal)

        if internal.needs_formula_thinking:
            result.formula_results = self._apply_formula_thinking(internal)

        if internal.needs_testing:
            result.test_results = self._generate_test_plan(internal)

        result.decision_points = self._identify_decision_points(internal, result)

        return result

    def _rational_process(self, internal: InternalRepresentation, result: ProcessingResult) -> None:
        result.findings.append(f"Intent identified: {internal.intent}")
        result.findings.append(f"Complexity level: {internal.complexity:.1f}")
        result.findings.append(f"Urgency level: {internal.urgency:.1f}")
        if internal.rational_analysis.get("key_entities"):
            result.findings.append(f"Key entities: {', '.join(internal.rational_analysis['key_entities'])}")
        if internal.rational_analysis.get("constraints"):
            result.findings.append(f"Constraints detected: {len(internal.rational_analysis['constraints'])}")
        result.confidence_scores["rational_analysis"] = 0.8

    def _emotional_process(self, internal: InternalRepresentation, result: ProcessingResult) -> None:
        emotion = internal.emotional_analysis.get("detected_emotion", "neutral")
        empathy = internal.emotional_analysis.get("empathy_required", False)
        if empathy:
            result.findings.append(f"User emotional state: {emotion} — empathy-driven response needed")
            result.recommendations.append({"action": f"acknowledge_{emotion}", "priority": "high", "rationale": f"Acknowledge user's {emotion} state before providing solution"})
        tone = internal.emotional_analysis.get("tone_adjustment", "professional_balanced")
        result.findings.append(f"Response tone: {tone}")
        result.confidence_scores["emotional_analysis"] = 0.7

    def _creative_process(self, internal: InternalRepresentation, result: ProcessingResult) -> None:
        result.alternatives.append({
            "id": "creative_option_1",
            "description": "Novel approach using cross-domain knowledge",
            "risk": "medium",
            "confidence": 0.5,
        })
        result.alternatives.append({
            "id": "creative_option_2",
            "description": "Conventional approach with proven patterns",
            "risk": "low",
            "confidence": 0.8,
        })
        result.confidence_scores["creative_analysis"] = 0.6

    def _analytical_process(self, internal: InternalRepresentation, result: ProcessingResult) -> None:
        for gap in internal.knowledge_gaps:
            result.risks.append(f"Knowledge gap: {gap}")
        for assumption in internal.assumptions:
            result.risks.append(f"Unverified assumption: {assumption}")
        result.confidence_scores["analytical_analysis"] = 0.75

    def _practical_process(self, internal: InternalRepresentation, result: ProcessingResult) -> None:
        result.recommendations.append({
            "action": "implement_step_by_step",
            "priority": "high" if internal.urgency > 0.7 else "medium",
            "rationale": "Step-by-step execution with verification at each checkpoint",
        })
        result.confidence_scores["practical_analysis"] = 0.85

    def _intuitive_process(self, internal: InternalRepresentation, result: ProcessingResult) -> None:
        result.findings.append("Intuitive assessment: pattern recognition suggests potential approach")
        result.confidence_scores["intuitive_analysis"] = 0.4

    def _generate_research_plan(self, internal: InternalRepresentation) -> str:
        return (f"Research plan for '{internal.intent}': "
                f"1) WebSearch for latest information, "
                f"2) Knowledge base lookup, "
                f"3) Cross-reference findings, "
                f"4) Mark confidence levels")

    def _apply_formula_thinking(self, internal: InternalRepresentation) -> Dict[str, Any]:
        return {
            "formula": "(R * K + C) ^ E - L",
            "rational_component": "R * K = Reasoning × Knowledge",
            "creative_component": "+ C = Creative dimension added",
            "emotional_component": "^ E = Amplified by emotional awareness",
            "linear_reduction": "- L = Minus linear bias",
            "result": "Multi-dimensional invention beyond linear thinking",
        }

    def _generate_test_plan(self, internal: InternalRepresentation) -> Dict[str, Any]:
        return {
            "l1_unit": "Individual component verification",
            "l2_integration": "Cross-component interaction testing",
            "l3_stress": "Scale and boundary condition testing",
            "confidence_threshold": 0.95,
        }

    def _identify_decision_points(self, internal: InternalRepresentation, result: ProcessingResult) -> List[Dict[str, Any]]:
        points = []
        if result.alternatives:
            points.append({
                "type": "approach_selection",
                "description": "Choose between creative and conventional approaches",
                "options": [a["id"] for a in result.alternatives],
                "requires_user": True,
            })
        if internal.knowledge_gaps:
            points.append({
                "type": "research_scope",
                "description": "Define research scope for knowledge gaps",
                "gaps": internal.knowledge_gaps,
                "requires_user": True,
            })
        if internal.intent == "decide":
            points.append({
                "type": "final_decision",
                "description": "This is a decision point — AI provides analysis, user makes the call",
                "requires_user": True,
            })
        return points


class HumanLanguageEncoder:
    """Stage 3: Internal Language → Human Language (編碼器)

    Translates AI's internal processing results back into human-readable
    language. Key principle: AI is Implementation King, not Decision Maker.
    Output must include: Report, Suggestions, Decision Points for user.
    """

    CONFIDENCE_SYMBOLS = {
        ConfidenceLevel.VERIFIED: "✅",
        ConfidenceLevel.RESEARCHED: "🔍",
        ConfidenceLevel.INFERRED: "⚠️",
        ConfidenceLevel.UNCERTAIN: "❌",
    }

    PURPOSE_TEMPLATES = {
        OutputPurpose.REPORT: "📋 Research Report",
        OutputPurpose.SUGGESTION: "💡 Suggestions",
        OutputPurpose.BRAINSTORM: "🧠 Brainstorm Results",
        OutputPurpose.DECISION_SUPPORT: "⚖️ Decision Support Analysis",
        OutputPurpose.FEEDBACK: "🔄 Feedback",
        OutputPurpose.IMPLEMENTATION: "🔧 Implementation Report",
    }

    def encode(self, internal: InternalRepresentation, result: ProcessingResult) -> HumanOutput:
        """Translate processing result into human-readable output."""
        purpose = self._determine_purpose(internal)
        summary = self._generate_summary(internal, result)
        detailed_report = self._generate_detailed_report(internal, result)
        decision_points = self._format_decision_points(result.decision_points)
        suggestions = self._generate_suggestions(internal, result)
        next_steps = self._generate_next_steps(internal, result)
        confidence_markers = self._format_confidence(internal.confidence)
        requires_decision = len(result.decision_points) > 0

        return HumanOutput(
            summary=summary,
            detailed_report=detailed_report,
            decision_points=decision_points,
            suggestions=suggestions,
            next_steps=next_steps,
            confidence_markers=confidence_markers,
            purpose=purpose,
            requires_user_decision=requires_decision,
            feedback_requested=True,
        )

    def _determine_purpose(self, internal: InternalRepresentation) -> OutputPurpose:
        intent_purpose_map = {
            "research": OutputPurpose.REPORT,
            "decide": OutputPurpose.DECISION_SUPPORT,
            "create": OutputPurpose.BRAINSTORM,
            "fix": OutputPurpose.IMPLEMENTATION,
            "design": OutputPurpose.BRAINSTORM,
            "test": OutputPurpose.REPORT,
            "optimize": OutputPurpose.SUGGESTION,
            "deploy": OutputPurpose.IMPLEMENTATION,
        }
        return intent_purpose_map.get(internal.intent, OutputPurpose.REPORT)

    def _generate_summary(self, internal: InternalRepresentation, result: ProcessingResult) -> str:
        lines = [f"**{self.PURPOSE_TEMPLATES.get(self._determine_purpose(internal), '📋 Report')}**"]
        lines.append(f"Intent: {internal.intent} | Urgency: {internal.urgency:.1f} | Complexity: {internal.complexity:.1f}")
        if result.findings:
            lines.append(f"Key findings: {len(result.findings)} items")
        if result.risks:
            lines.append(f"Risks identified: {len(result.risks)} items")
        if result.decision_points:
            lines.append(f"⚠️ {len(result.decision_points)} decision point(s) require YOUR input")
        lines.append("")
        lines.append("*AI role: Implementation King — I research, test, and report. You decide.*")
        return "\n".join(lines)

    def _generate_detailed_report(self, internal: InternalRepresentation, result: ProcessingResult) -> str:
        sections = []
        sections.append("## Findings")
        for f in result.findings:
            sections.append(f"- {f}")
        if result.risks:
            sections.append("\n## Risks")
            for r in result.risks:
                sections.append(f"- ⚠️ {r}")
        if result.recommendations:
            sections.append("\n## Recommendations")
            for rec in result.recommendations:
                sections.append(f"- **{rec['action']}** (priority: {rec['priority']}) — {rec['rationale']}")
        if result.alternatives:
            sections.append("\n## Alternatives")
            for alt in result.alternatives:
                sections.append(f"- {alt['id']}: {alt['description']} (risk: {alt['risk']}, confidence: {alt['confidence']:.1f})")
        if result.research_summary:
            sections.append(f"\n## Research Plan\n{result.research_summary}")
        if result.formula_results:
            sections.append(f"\n## Formula Thinking\nFormula: {result.formula_results['formula']}")
        if result.test_results:
            sections.append(f"\n## Test Plan\nL1: {result.test_results['l1_unit']}\nL2: {result.test_results['l2_integration']}\nL3: {result.test_results['l3_stress']}")
        return "\n".join(sections)

    def _format_decision_points(self, points: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        formatted = []
        for p in points:
            formatted.append({
                "type": p["type"],
                "description": p["description"],
                "options": p.get("options", []),
                "requires_user": p.get("requires_user", True),
                "message": "👉 YOUR DECISION NEEDED — AI provides analysis, you make the call",
            })
        return formatted

    def _generate_suggestions(self, internal: InternalRepresentation, result: ProcessingResult) -> List[str]:
        suggestions = []
        if internal.needs_research:
            suggestions.append("Deep research recommended before proceeding")
        if internal.needs_testing:
            suggestions.append("3-layer testing recommended after implementation")
        if internal.needs_formula_thinking:
            suggestions.append("Formula thinking can generate novel approaches beyond conventional options")
        if internal.emotional_analysis.get("empathy_required"):
            suggestions.append("Address emotional context before diving into technical solution")
        for rec in result.recommendations:
            suggestions.append(f"Suggested: {rec['action']} (priority: {rec['priority']})")
        return suggestions

    def _generate_next_steps(self, internal: InternalRepresentation, result: ProcessingResult) -> List[str]:
        steps = []
        if internal.needs_research:
            steps.append("1. Conduct research and gather data")
        steps.append("2. Present findings with confidence levels to user")
        if result.decision_points:
            steps.append("3. ⚠️ Wait for user decision on key decision points")
        if internal.needs_testing:
            steps.append("4. Implement and run 3-layer testing")
        steps.append("5. Deliver verified results with detailed report")
        steps.append("6. Request user feedback for continuous improvement")
        return steps

    def _format_confidence(self, confidence: Dict[str, ConfidenceLevel]) -> Dict[str, str]:
        return {k: self.CONFIDENCE_SYMBOLS.get(v, "❓") for k, v in confidence.items()}


class HumanAICommunicationBridge:
    """The Complete 3-Stage Communication Bridge.

    Human Language → [Decode] → Internal Language → [Process] → [Encode] → Human Language

    Core Philosophy:
    - AI is Implementation King (執行者): Research, Formula Think, Test, Report
    - Human is Decision Maker (決策者): Review, Decide, Approve, Guide
    - Every interaction ends with: Feedback → Suggestion → Decision Point for user
    """

    def __init__(self) -> None:
        self.decoder = HumanLanguageDecoder()
        self.processor = InternalProcessor()
        self.encoder = HumanLanguageEncoder()
        self._feedback_history: List[FeedbackEntry] = []
        self._session_count = 0
        self._user_preferences: Dict[str, Any] = {}

    def communicate(self, human_input: str, context: Optional[Dict[str, Any]] = None) -> HumanOutput:
        """Full 3-stage communication pipeline."""
        self._session_count += 1

        # Stage 1: Decode human language into internal representation
        internal = self.decoder.decode(human_input, context)

        # Stage 2: Process through multiple thinking dimensions
        result = self.processor.process(internal)

        # Stage 3: Encode back to human language
        output = self.encoder.encode(internal, result)

        return output

    def explain_thinking(self, human_input: str) -> Dict[str, Any]:
        """Explain to the user how AI is thinking about their input.

        This is the transparency feature — showing the user the 3-stage
        translation process so they understand AI's internal logic.
        """
        internal = self.decoder.decode(human_input)

        return {
            "stage_1_decode": {
                "what_i_heard": human_input,
                "intent_detected": internal.intent,
                "urgency_level": internal.urgency,
                "complexity_level": internal.complexity,
                "thinking_modes_activated": [m.value for m in internal.thinking_modes],
                "emotional_state_detected": internal.emotional_analysis.get("detected_emotion", "neutral"),
                "knowledge_gaps_identified": internal.knowledge_gaps,
                "assumptions_detected": internal.assumptions,
            },
            "stage_2_process": {
                "rational_thinking": "Analyzing intent, complexity, constraints, and entities",
                "emotional_thinking": f"Detecting user emotional state: {internal.emotional_analysis.get('detected_emotion', 'neutral')}",
                "creative_thinking": "Generating alternative approaches" if ThinkingMode.CREATIVE in internal.thinking_modes else "Not activated for this input",
                "analytical_thinking": "Identifying risks and knowledge gaps" if ThinkingMode.ANALYTICAL in internal.thinking_modes else "Not activated for this input",
                "practical_thinking": "Planning step-by-step implementation" if ThinkingMode.PRACTICAL in internal.thinking_modes else "Not activated for this input",
                "needs_research": internal.needs_research,
                "needs_formula_thinking": internal.needs_formula_thinking,
                "needs_testing": internal.needs_testing,
            },
            "stage_3_encode": {
                "my_role": "Implementation King — I research, test, and report. YOU decide.",
                "output_type": "Detailed report with decision points for your review",
                "feedback_loop": "After each interaction, I'll ask for your feedback to improve",
            },
            "formula": "(R * K + C) ^ E - L",
            "formula_explanation": {
                "R_K": "Rational × Knowledge: Logical analysis based on what I know",
                "C": "Creativity: Generating novel approaches beyond conventional options",
                "E": "Emotion awareness: Understanding your emotional state for better communication",
                "L": "Linear bias reduction: Breaking free from token-by-token thinking",
            },
        }

    def receive_feedback(self, output_id: str, user_response: str, accepted: bool,
                         adjustments: Optional[List[str]] = None) -> None:
        """Receive user feedback and learn from it."""
        entry = FeedbackEntry(
            output_id=output_id,
            user_response=user_response,
            accepted=accepted,
            adjustments=adjustments or [],
            learning_points=self._extract_learning_points(user_response, accepted),
        )
        self._feedback_history.append(entry)

        if not accepted:
            for point in entry.learning_points:
                self._user_preferences[point] = "avoid"
        else:
            for point in entry.learning_points:
                self._user_preferences[point] = "prefer"

    def get_thinking_transparency(self, human_input: str) -> str:
        """Generate a human-readable explanation of AI's thinking process."""
        explanation = self.explain_thinking(human_input)

        lines = ["## 🧠 How I'm Thinking About Your Request", ""]

        lines.append("### Stage 1: Decoding Your Language")
        decode = explanation["stage_1_decode"]
        lines.append(f"- **What I heard**: \"{decode['what_i_heard']}\"")
        lines.append(f"- **Intent detected**: {decode['intent_detected']}")
        lines.append(f"- **Urgency**: {decode['urgency_level']:.1f}/1.0")
        lines.append(f"- **Complexity**: {decode['complexity_level']:.1f}/1.0")
        lines.append(f"- **Thinking modes**: {', '.join(decode['thinking_modes_activated'])}")
        lines.append(f"- **Your emotional state**: {decode['emotional_state_detected']}")
        if decode["knowledge_gaps_identified"]:
            lines.append(f"- **Knowledge gaps**: {', '.join(decode['knowledge_gaps_identified'])}")
        if decode["assumptions_detected"]:
            lines.append(f"- **Assumptions I'm making**: {', '.join(decode['assumptions_detected'])}")

        lines.append("")
        lines.append("### Stage 2: My Internal Processing")
        process = explanation["stage_2_process"]
        lines.append(f"- **Rational**: {process['rational_thinking']}")
        lines.append(f"- **Emotional**: {process['emotional_thinking']}")
        lines.append(f"- **Creative**: {process['creative_thinking']}")
        lines.append(f"- **Analytical**: {process['analytical_thinking']}")
        lines.append(f"- **Practical**: {process['practical_thinking']}")
        lines.append(f"- **Needs research**: {'Yes' if process['needs_research'] else 'No'}")
        lines.append(f"- **Needs formula thinking**: {'Yes' if process['needs_formula_thinking'] else 'No'}")
        lines.append(f"- **Needs testing**: {'Yes' if process['needs_testing'] else 'No'}")

        lines.append("")
        lines.append("### Stage 3: Translating Back to You")
        encode = explanation["stage_3_encode"]
        lines.append(f"- **My role**: {encode['my_role']}")
        lines.append(f"- **Output type**: {encode['output_type']}")
        lines.append(f"- **Feedback loop**: {encode['feedback_loop']}")

        lines.append("")
        lines.append("### My Thinking Formula")
        lines.append(f"**{explanation['formula']}**")
        for key, desc in explanation["formula_explanation"].items():
            lines.append(f"- {desc}")

        lines.append("")
        lines.append("---")
        lines.append("*Remember: I'm your Implementation King. I do the heavy lifting (research, testing, analysis). You make the decisions.*")

        return "\n".join(lines)

    def _extract_learning_points(self, response: str, accepted: bool) -> List[str]:
        points = []
        if not accepted:
            points.append("user_rejected_suggestion")
            if "too complex" in response.lower() or "太複雜" in response:
                points.append("prefer_simpler_solutions")
            if "too slow" in response.lower() or "太慢" in response:
                points.append("prefer_faster_approach")
        else:
            points.append("user_accepted_suggestion")
        return points

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "total_sessions": self._session_count,
            "feedback_count": len(self._feedback_history),
            "acceptance_rate": (
                sum(1 for f in self._feedback_history if f.accepted) / max(len(self._feedback_history), 1)
            ),
            "user_preferences": dict(self._user_preferences),
        }
