"""
Structural Thinking Router — 結構思維路由器
Replaces traditional skill-router with structure-driven routing.

Instead of: Input → Keyword Match → Skill Invocation
We do:      Input → Pulse(emotional) + Current(context+personality) → Structural Processing Plan

The router considers:
- Emotional signal (Pulse layer) for urgency/priority routing
- Contextual analysis (Current layer) for domain/complexity routing
- Personality vector (25D) for personalized processing paths
- Flow state (challenge/skill ratio) for optimal processing depth
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
import time


class RoutingStrategy(Enum):
    """路由策略"""
    STRUCTURE_DRIVEN = "structure_driven"    # 結構驅動路由
    PERSONALITY_WEIGHTED = "personality_weighted"  # 人格加權路由
    FLOW_ADJUSTED = "flow_adjusted"          # 心流調整路由
    EMERGENCE_GUIDED = "emergence_guided"    # 湧現引導路由


class ProcessingDepth(Enum):
    """處理深度"""
    QUICK = "quick"          # 快速處理 (1-2 layers)
    STANDARD = "standard"    # 標準處理 (3-4 layers)
    DEEP = "deep"            # 深度處理 (all 5 layers)
    EMERGENCE = "emergence"  # 湧現處理 (all 5 + cross-layer)


class DomainType(Enum):
    """領域類型"""
    CODING = "coding"
    RESEARCH = "research"
    DESIGN = "design"
    BUSINESS = "business"
    COMPLIANCE = "compliance"
    COMMUNICATION = "communication"
    GENERAL = "general"


@dataclass
class EmotionalSignal:
    """情緒信號 — Parsed from Pulse layer"""
    valence: float = 0.0      # -1.0 to +1.0
    arousal: float = 0.0      # -1.0 to +1.0
    urgency: float = 0.0      # 0.0 to 1.0
    signal_type: str = "neutral"  # neutral, alert, excited, frustrated, curious


@dataclass
class ContextualAnalysis:
    """情境分析 — Parsed from Current layer"""
    domain: DomainType = DomainType.GENERAL
    complexity: float = 0.5   # 0.0 to 1.0
    specificity: float = 0.5  # 0.0 to 1.0
    requires_creativity: bool = False
    requires_precision: bool = False
    requires_compliance: bool = False


@dataclass
class StructuralProcessingPlan:
    """結構處理計劃 — The output of structural routing (replaces skill invocation)"""
    # Routing decision
    strategy: RoutingStrategy
    depth: ProcessingDepth
    primary_layers: List[str]  # Which layers to emphasize
    secondary_layers: List[str]  # Which layers to support

    # Emotional and contextual context
    emotional_signal: EmotionalSignal
    contextual_analysis: ContextualAnalysis

    # Personality modulation
    personality_weight: float = 1.0  # PV factor
    personality_style: str = "balanced"  # DISC-influenced style

    # Flow state
    flow_depth_factor: float = 1.0
    flow_zone: str = "flow"  # boredom, flow, anxiety

    # Processing metadata
    confidence: float = 0.5
    estimated_complexity: float = 0.5
    routing_reason: str = ""

    # What this plan provides vs traditional skill routing
    structural_advantage: str = ""


class StructuralThinkingRouter:
    """
    結構思維路由器 — Replaces skill-router with structure-driven routing.

    Instead of matching keywords to skills, this router:
    1. Parses emotional signals from input (Pulse)
    2. Analyzes context and domain (Current)
    3. Considers personality vector for personalized paths
    4. Adjusts depth based on flow state
    5. Generates a Structural Processing Plan (not a skill invocation)

    The plan tells the Structure Driver HOW to process the input,
    not WHICH skill to invoke.
    """

    # Domain detection keywords
    DOMAIN_KEYWORDS = {
        DomainType.CODING: ["code", "bug", "deploy", "api", "function", "class", "編程", "代碼", "部署", "修復"],
        DomainType.RESEARCH: ["research", "study", "analyze", "investigate", "研究", "分析", "調查"],
        DomainType.DESIGN: ["design", "ui", "ux", "layout", "color", "設計", "界面", "佈局"],
        DomainType.BUSINESS: ["business", "revenue", "market", "strategy", "商業", "收入", "市場", "策略"],
        DomainType.COMPLIANCE: ["compliance", "compliant", "legal", "regulation", "law", "合規", "法律", "法規"],
        DomainType.COMMUNICATION: ["write", "explain", "present", "communicate", "寫", "解釋", "溝通"],
    }

    # Urgency detection keywords
    URGENCY_KEYWORDS = {
        "high": ["urgent", "asap", "emergency", "critical", "急", "緊急", "立即", "救命"],
        "medium": ["soon", "important", "priority", "快", "重要", "優先"],
    }

    # Creativity detection keywords
    CREATIVITY_KEYWORDS = ["create", "design", "invent", "imagine", "創建", "設計", "發明", "想像"]

    # Precision detection keywords
    PRECISION_KEYWORDS = ["exact", "precise", "accurate", "calculate", "精確", "準確", "計算"]

    def __init__(self, personality_vector=None, flow_navigator=None):
        """
        Initialize the Structural Thinking Router.

        Args:
            personality_vector: Optional PersonalityVector for modulation
            flow_navigator: Optional FlowStateNavigator for depth adjustment
        """
        self.personality_vector = personality_vector
        self.flow_navigator = flow_navigator

    def route(self, input_text: str, context: Optional[Dict] = None) -> StructuralProcessingPlan:
        """
        Route input through structural analysis instead of skill matching.

        Args:
            input_text: User input text
            context: Optional context dict

        Returns:
            StructuralProcessingPlan with routing decisions
        """
        context = context or {}

        # Step 1: Parse emotional signal (Pulse layer)
        emotional_signal = self._parse_emotional_signal(input_text)

        # Step 2: Analyze context (Current layer)
        contextual_analysis = self._analyze_context(input_text, context)

        # Step 3: Determine routing strategy
        strategy = self._determine_strategy(emotional_signal, contextual_analysis)

        # Step 4: Determine processing depth
        depth = self._determine_depth(emotional_signal, contextual_analysis)

        # Step 5: Select primary and secondary layers
        primary, secondary = self._select_layers(strategy, depth, emotional_signal, contextual_analysis)

        # Step 6: Apply personality modulation
        personality_weight, personality_style = self._apply_personality_routing()

        # Step 7: Apply flow state adjustment
        flow_depth, flow_zone = self._apply_flow_routing(input_text)

        # Step 8: Compute confidence and complexity
        confidence = self._compute_confidence(emotional_signal, contextual_analysis)
        estimated_complexity = contextual_analysis.complexity

        # Step 9: Generate routing reason
        routing_reason = self._generate_routing_reason(
            strategy, depth, emotional_signal, contextual_analysis
        )

        # Step 10: Compute structural advantage
        structural_advantage = self._compute_structural_advantage(
            emotional_signal, contextual_analysis, personality_weight, flow_depth
        )

        return StructuralProcessingPlan(
            strategy=strategy,
            depth=depth,
            primary_layers=primary,
            secondary_layers=secondary,
            emotional_signal=emotional_signal,
            contextual_analysis=contextual_analysis,
            personality_weight=personality_weight,
            personality_style=personality_style,
            flow_depth_factor=flow_depth,
            flow_zone=flow_zone,
            confidence=confidence,
            estimated_complexity=estimated_complexity,
            routing_reason=routing_reason,
            structural_advantage=structural_advantage,
        )

    def _parse_emotional_signal(self, text: str) -> EmotionalSignal:
        """Parse emotional signals from input text (Pulse layer function)"""
        text_lower = text.lower()

        # Detect urgency
        urgency = 0.0
        signal_type = "neutral"
        for level, keywords in self.URGENCY_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                if level == "high":
                    urgency = 0.9
                    signal_type = "alert"
                elif level == "medium":
                    urgency = 0.5
                    signal_type = "concerned"

        # Detect valence
        valence = 0.0
        negative_words = ["bug", "error", "fail", "broken", "crash", "錯誤", "失敗", "壞了"]
        positive_words = ["great", "love", "awesome", "perfect", "好", "棒", "完美"]
        if any(w in text_lower for w in negative_words):
            valence = -0.5
            if signal_type == "neutral":
                signal_type = "frustrated"
        elif any(w in text_lower for w in positive_words):
            valence = 0.5
            if signal_type == "neutral":
                signal_type = "excited"

        # Detect curiosity
        if any(w in text_lower for w in ["how", "why", "what", "怎麼", "為什麼", "什麼"]):
            if signal_type == "neutral":
                signal_type = "curious"

        # Detect arousal
        arousal = urgency * 0.7 + abs(valence) * 0.3

        return EmotionalSignal(
            valence=valence,
            arousal=arousal,
            urgency=urgency,
            signal_type=signal_type,
        )

    def _analyze_context(self, text: str, context: Dict) -> ContextualAnalysis:
        """Analyze context from input text (Current layer function)"""
        text_lower = text.lower()

        # Detect domain
        domain = DomainType.GENERAL
        max_score = 0
        for d, keywords in self.DOMAIN_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > max_score:
                max_score = score
                domain = d

        # Override with context domain if provided
        if "domain" in context:
            try:
                domain = DomainType(context["domain"])
            except ValueError:
                pass

        # Estimate complexity
        complexity = min(1.0, len(text) / 500 + 0.2)
        if any(w in text_lower for w in ["complex", "complicated", "複雜", "多步驟"]):
            complexity = min(1.0, complexity + 0.2)

        # Estimate specificity
        specificity = min(1.0, len(text) / 200 + 0.3)

        # Detect requirements
        requires_creativity = any(kw in text_lower for kw in self.CREATIVITY_KEYWORDS)
        requires_precision = any(kw in text_lower for kw in self.PRECISION_KEYWORDS)
        requires_compliance = any(kw in text_lower for kw in ["compliance", "compliant", "legal", "合規", "法律"])
        # Also set compliance if domain is compliance
        if domain == DomainType.COMPLIANCE:
            requires_compliance = True

        return ContextualAnalysis(
            domain=domain,
            complexity=complexity,
            specificity=specificity,
            requires_creativity=requires_creativity,
            requires_precision=requires_precision,
            requires_compliance=requires_compliance,
        )

    def _determine_strategy(self, emotional: EmotionalSignal,
                           context: ContextualAnalysis) -> RoutingStrategy:
        """Determine the routing strategy based on emotional and contextual signals"""
        if emotional.urgency > 0.7:
            return RoutingStrategy.STRUCTURE_DRIVEN  # Fast, direct routing

        if context.requires_creativity:
            return RoutingStrategy.EMERGENCE_GUIDED  # Let emergence guide creative tasks

        if self.personality_vector is not None:
            return RoutingStrategy.PERALITY_WEIGHTED  # Personality-informed routing

        if self.flow_navigator is not None:
            return RoutingStrategy.FLOW_ADJUSTED  # Flow-optimized routing

        return RoutingStrategy.STRUCTURE_DRIVEN  # Default

    def _determine_depth(self, emotional: EmotionalSignal,
                        context: ContextualAnalysis) -> ProcessingDepth:
        """Determine processing depth based on signals"""
        # High urgency → quick processing
        if emotional.urgency > 0.8:
            return ProcessingDepth.QUICK

        # High complexity or compliance → deep processing
        if context.complexity > 0.8 or context.requires_compliance:
            return ProcessingDepth.DEEP

        # Creativity → emergence processing
        if context.requires_creativity:
            return ProcessingDepth.EMERGENCE

        # Medium complexity → standard
        if context.complexity > 0.4:
            return ProcessingDepth.STANDARD

        return ProcessingDepth.STANDARD

    def _select_layers(self, strategy: RoutingStrategy, depth: ProcessingDepth,
                       emotional: EmotionalSignal,
                       context: ContextualAnalysis) -> Tuple[List[str], List[str]]:
        """Select primary and secondary layers based on strategy and depth"""
        all_layers = ["pulse", "current", "construct", "enactive", "resonance"]

        if depth == ProcessingDepth.QUICK:
            # Quick: Pulse + Current + Enactive
            primary = ["pulse", "current", "enactive"]
            secondary = ["construct", "resonance"]

        elif depth == ProcessingDepth.STANDARD:
            # Standard: Pulse + Current + Construct + Enactive
            primary = ["pulse", "current", "construct", "enactive"]
            secondary = ["resonance"]

        elif depth == ProcessingDepth.DEEP:
            # Deep: All 5 layers
            primary = all_layers
            secondary = []

        elif depth == ProcessingDepth.EMERGENCE:
            # Emergence: All 5 layers with emphasis on cross-layer
            primary = all_layers
            secondary = []

        else:
            primary = all_layers
            secondary = []

        # Adjust based on emotional signal
        if emotional.signal_type == "alert":
            # Alert: prioritize Pulse and Enactive
            if "pulse" not in primary:
                primary.insert(0, "pulse")
            if "enactive" not in primary:
                primary.append("enactive")

        # Adjust based on context
        if context.requires_precision:
            # Precision: prioritize Construct and Resonance
            if "construct" not in primary:
                primary.append("construct")
            if "resonance" not in primary:
                primary.append("resonance")

        return primary, secondary

    def _apply_personality_routing(self) -> Tuple[float, str]:
        """Apply personality vector to routing decisions"""
        if self.personality_vector is None:
            return 1.0, "balanced"

        try:
            disc = self.personality_vector.disc
            primary = disc.primary_type()

            style_map = {
                "D": (1.2, "direct"),       # Dominance → direct, fast
                "I": (1.1, "expressive"),    # Influence → expressive, creative
                "S": (0.9, "supportive"),    # Steadiness → supportive, thorough
                "C": (1.15, "analytical"),   # Conscientiousness → analytical, precise
            }

            return style_map.get(primary.value, (1.0, "balanced"))
        except Exception:
            return 1.0, "balanced"

    def _apply_flow_routing(self, input_text: str) -> Tuple[float, str]:
        """Apply flow state to routing decisions"""
        if self.flow_navigator is None:
            return 1.0, "flow"

        try:
            challenge = min(1.0, len(input_text) / 500 + 0.3)
            skill = 0.7
            flow_state = self.flow_navigator.assess_flow(challenge, skill)

            zone = flow_state.zone.value if hasattr(flow_state.zone, 'value') else "flow"
            depth_factor = flow_state.flow_depth() if hasattr(flow_state, 'flow_depth') else 1.0

            return depth_factor, zone
        except Exception:
            return 1.0, "flow"

    def _compute_confidence(self, emotional: EmotionalSignal,
                           context: ContextualAnalysis) -> float:
        """Compute routing confidence"""
        # Higher specificity and clearer domain → higher confidence
        confidence = 0.5 + context.specificity * 0.2

        # Clear emotional signal → higher confidence
        if emotional.signal_type != "neutral":
            confidence += 0.1

        # Known domain → higher confidence
        if context.domain != DomainType.GENERAL:
            confidence += 0.1

        return min(1.0, confidence)

    def _generate_routing_reason(self, strategy: RoutingStrategy, depth: ProcessingDepth,
                                 emotional: EmotionalSignal,
                                 context: ContextualAnalysis) -> str:
        """Generate a human-readable routing reason"""
        parts = [
            f"Strategy: {strategy.value}",
            f"Depth: {depth.value}",
            f"Emotional: {emotional.signal_type}",
            f"Domain: {context.domain.value}",
        ]
        return " | ".join(parts)

    def _compute_structural_advantage(self, emotional: EmotionalSignal,
                                      context: ContextualAnalysis,
                                      personality_weight: float,
                                      flow_depth: float) -> str:
        """Compute what structural routing provides vs skill routing"""
        advantages = []

        if emotional.signal_type != "neutral":
            advantages.append(f"Emotional awareness ({emotional.signal_type})")

        if context.domain != DomainType.GENERAL:
            advantages.append(f"Domain-specific routing ({context.domain.value})")

        if personality_weight != 1.0:
            advantages.append("Personality-modulated path")

        if flow_depth != 1.0:
            advantages.append("Flow-adjusted depth")

        if context.requires_creativity:
            advantages.append("Emergence-guided creative processing")

        if context.requires_compliance:
            advantages.append("Compliance-aware deep processing")

        if not advantages:
            return "Standard structural routing"

        return "; ".join(advantages)
