"""
EmoGlyph Structure Driver — 結構驅動引擎
Formula: Output = ⊕(P,C,Co,E,R)^Ξ × PV × Flow - L

Replaces traditional LLM rule→skill→decision pipeline with
structure-driven processing through the 5-layer circular model.
All layers activate simultaneously (⊕ Superposition) with
bidirectional interdependency awareness, personality vector
modulation, and flow state optimization.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
import math
import time


class InterdependencyType(Enum):
    """互依類型 — 4 types of bidirectional relationships between layers"""
    COMPLEMENTARY = "complementary"  # 互補型: A + B > max(A, B)
    DEPENDENT = "dependent"          # 依賴型: B needs A
    CONFLICTING = "conflicting"      # 衝突型: A contradicts B
    FEEDBACK = "feedback"            # 反饋型: A↔B 循環


class ProcessingMode(Enum):
    """處理模式"""
    STRUCTURE_DRIVEN = "structure_driven"  # 結構驅動 (primary)
    RULE_FALLBACK = "rule_fallback"        # 規則後備 (subordinate)
    EMERGENCE = "emergence"                # 湧現模式 (cross-layer)


@dataclass
class LayerState:
    """單層狀態 — State of a single EmoGlyph layer during processing"""
    name: str
    activation: float = 0.0       # 0.0-1.0 activation level
    output: Dict[str, Any] = field(default_factory=dict)
    personality_modifier: float = 1.0  # PV modulation factor
    flow_depth: float = 1.0       # Flow-adjusted processing depth
    interdependency_signals: Dict[str, float] = field(default_factory=dict)


@dataclass
class EmergencePattern:
    """湧現模式 — A pattern that emerges from cross-layer interaction"""
    pattern_id: str
    source_layers: List[str]
    pattern_type: str  # "synergy", "conflict", "novelty", "insight"
    strength: float    # 0.0-1.0
    description: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StructureProcessingResult:
    """結構處理結果 — Complete result from structure-driven processing"""
    # Core output
    output: str
    confidence: float  # 0.0-1.0

    # Layer states after processing
    layer_states: Dict[str, LayerState]

    # Emergence patterns detected
    emergence_patterns: List[EmergencePattern]

    # Processing metadata
    processing_mode: ProcessingMode
    personality_modulated: bool
    flow_optimized: bool
    processing_time_ms: float

    # Comparison with rule-based approach
    rule_based_output: Optional[str] = None
    structural_advantage: Optional[str] = None  # What structure added vs rules

    # Formula components
    superposition_value: float = 0.0   # ⊕(P,C,Co,E,R)
    emergence_value: float = 0.0       # Ξ
    personality_value: float = 1.0     # PV
    flow_value: float = 1.0            # Flow
    linear_bias: float = 0.0           # L


class EmoGlyphStructureDriver:
    """
    結構驅動引擎 — The core orchestrator that replaces rule-based processing
    with structure-driven processing through the 5-layer circular model.

    Instead of: Input → Rule Match → Skill Execute → Output
    We do:      Input → ⊕(P,C,Co,E,R)^Ξ × PV × Flow - L → Structure-Driven Output

    The 5 layers process SIMULTANEOUSLY (not sequentially), with:
    - Bidirectional interdependency awareness (10 connections)
    - Personality vector modulation (25D vector)
    - Flow state optimization (challenge/skill ratio)
    - Emergence detection (cross-layer patterns)
    """

    # 10 bidirectional interdependency mappings
    INTERDEPENDENCY_MAP = {
        ("pulse", "current"): InterdependencyType.COMPLEMENTARY,
        ("pulse", "construct"): InterdependencyType.FEEDBACK,
        ("pulse", "enactive"): InterdependencyType.CONFLICTING,
        ("pulse", "resonance"): InterdependencyType.FEEDBACK,
        ("current", "construct"): InterdependencyType.DEPENDENT,
        ("current", "enactive"): InterdependencyType.COMPLEMENTARY,
        ("current", "resonance"): InterdependencyType.FEEDBACK,
        ("construct", "enactive"): InterdependencyType.FEEDBACK,
        ("construct", "resonance"): InterdependencyType.DEPENDENT,
        ("enactive", "resonance"): InterdependencyType.CONFLICTING,
    }

    def __init__(self, personality_vector=None, flow_navigator=None):
        """
        Initialize the Structure Driver.

        Args:
            personality_vector: Optional PersonalityVector for modulation
            flow_navigator: Optional FlowStateNavigator for depth adjustment
        """
        self.personality_vector = personality_vector
        self.flow_navigator = flow_navigator
        self._layer_states: Dict[str, LayerState] = {}
        self._emergence_history: List[EmergencePattern] = []
        self._conflict_log: List[Dict] = []

    def process(self, input_text: str, context: Optional[Dict] = None) -> StructureProcessingResult:
        """
        Main processing method — Structure-driven processing pipeline.

        Instead of rule matching, this:
        1. Activates all 5 layers simultaneously (⊕ Superposition)
        2. Applies bidirectional interdependency signals
        3. Modulates with personality vector
        4. Adjusts depth with flow state
        5. Detects emergence patterns
        6. Assembles structure-driven output

        Args:
            input_text: User input text
            context: Optional context dict (domain, urgency, etc.)

        Returns:
            StructureProcessingResult with full processing details
        """
        start_time = time.time()
        context = context or {}

        # Step 1: Initialize all 5 layers simultaneously
        self._initialize_layers()

        # Step 2: Activate all layers with input (⊕ Superposition)
        self._activate_superposition(input_text, context)

        # Step 3: Apply bidirectional interdependency signals
        self._apply_interdependencies()

        # Step 4: Modulate with personality vector (PV)
        pv_value = self._apply_personality_modulation()

        # Step 5: Adjust with flow state (Flow)
        flow_value = self._apply_flow_optimization(input_text)

        # Step 6: Detect emergence patterns (Ξ)
        emergence_patterns = self._detect_emergence()
        emergence_value = self._compute_emergence_value(emergence_patterns)

        # Step 7: Compute superposition value
        superposition_value = self._compute_superposition()

        # Step 8: Assemble structure-driven output
        output, confidence = self._assemble_output(input_text, context)

        # Step 9: Compute linear bias (L)
        linear_bias = self._compute_linear_bias()

        # Step 10: Apply core formula
        # Output = ⊕(P,C,Co,E,R)^Ξ × PV × Flow - L
        formula_result = self._apply_core_formula(
            superposition_value, emergence_value, pv_value, flow_value, linear_bias
        )

        processing_time = (time.time() - start_time) * 1000

        # Determine structural advantage
        structural_advantage = self._compute_structural_advantage(emergence_patterns)

        return StructureProcessingResult(
            output=output,
            confidence=min(1.0, confidence * formula_result),
            layer_states=dict(self._layer_states),
            emergence_patterns=emergence_patterns,
            processing_mode=ProcessingMode.STRUCTURE_DRIVEN,
            personality_modulated=pv_value != 1.0,
            flow_optimized=flow_value != 1.0,
            processing_time_ms=processing_time,
            structural_advantage=structural_advantage,
            superposition_value=superposition_value,
            emergence_value=emergence_value,
            personality_value=pv_value,
            flow_value=flow_value,
            linear_bias=linear_bias,
        )

    def _initialize_layers(self):
        """Initialize all 5 layer states"""
        for name in ["pulse", "current", "construct", "enactive", "resonance"]:
            self._layer_states[name] = LayerState(name=name)

    def _activate_superposition(self, input_text: str, context: Dict):
        """
        ⊕ Superposition — Activate all 5 layers simultaneously.
        Each layer processes the input independently but with awareness
        of the other layers' potential contributions.
        """
        text_len = len(input_text)
        has_urgency = context.get("urgency", "normal") != "normal"
        has_domain = "domain" in context

        # Pulse: emotional signal detection
        pulse_activation = 0.5 + 0.1 * min(text_len / 100, 1.0)
        if any(w in input_text.lower() for w in ["urgent", "急", "help", "救命", "bug", "error"]):
            pulse_activation = min(1.0, pulse_activation + 0.3)
        self._layer_states["pulse"].activation = pulse_activation
        self._layer_states["pulse"].output = {
            "emotional_signal": "high_alert" if pulse_activation > 0.7 else "normal",
            "valence": -0.3 if "bug" in input_text.lower() or "error" in input_text.lower() else 0.2,
        }

        # Current: contextual analysis
        current_activation = 0.4 + 0.2 * (1 if has_domain else 0) + 0.1 * min(text_len / 200, 1.0)
        self._layer_states["current"].activation = current_activation
        self._layer_states["current"].output = {
            "domain": context.get("domain", "general"),
            "complexity": "high" if text_len > 200 else "medium" if text_len > 50 else "low",
            "urgency": context.get("urgency", "normal"),
        }

        # Construct: structural planning
        construct_activation = 0.3 + 0.2 * min(text_len / 150, 1.0)
        self._layer_states["construct"].activation = construct_activation
        self._layer_states["construct"].output = {
            "plan_type": "detailed" if text_len > 100 else "quick",
            "approach": "systematic" if current_activation > 0.5 else "intuitive",
        }

        # Enactive: execution readiness
        enactive_activation = 0.3 + 0.2 * (1 if has_urgency else 0)
        self._layer_states["enactive"].activation = enactive_activation
        self._layer_states["enactive"].output = {
            "execution_mode": "fast" if has_urgency else "thorough",
            "action_readiness": "high" if enactive_activation > 0.6 else "medium",
        }

        # Resonance: quality gate
        resonance_activation = 0.4 + 0.1 * min(text_len / 100, 1.0)
        self._layer_states["resonance"].activation = resonance_activation
        self._layer_states["resonance"].output = {
            "quality_threshold": "high" if current_activation > 0.6 else "standard",
            "evaluation_mode": "strict" if pulse_activation > 0.7 else "balanced",
        }

    def _apply_interdependencies(self):
        """
        Apply bidirectional interdependency signals between all layer pairs.
        Each pair has a specific interdependency type that determines how
        signals flow between them.
        """
        for (layer_a, layer_b), itype in self.INTERDEPENDENCY_MAP.items():
            state_a = self._layer_states[layer_a]
            state_b = self._layer_states[layer_b]

            signal_a_to_b = state_a.activation * 0.1
            signal_b_to_a = state_b.activation * 0.1

            if itype == InterdependencyType.COMPLEMENTARY:
                # A + B > max(A, B) — synergistic boost
                boost = min(state_a.activation, state_b.activation) * 0.15
                state_a.interdependency_signals[layer_b] = signal_b_to_a + boost
                state_b.interdependency_signals[layer_a] = signal_a_to_b + boost

            elif itype == InterdependencyType.DEPENDENT:
                # B needs A — A feeds B
                state_b.interdependency_signals[layer_a] = signal_a_to_b * 1.5
                state_a.interdependency_signals[layer_b] = signal_b_to_a * 0.5

            elif itype == InterdependencyType.CONFLICTING:
                # A contradicts B — dynamic balance
                diff = abs(state_a.activation - state_b.activation)
                state_a.interdependency_signals[layer_b] = signal_b_to_a * (1 - diff * 0.5)
                state_b.interdependency_signals[layer_a] = signal_a_to_b * (1 - diff * 0.5)

            elif itype == InterdependencyType.FEEDBACK:
                # A↔B circular — iterative convergence
                avg = (state_a.activation + state_b.activation) / 2
                convergence = 1 - abs(state_a.activation - state_b.activation)
                state_a.interdependency_signals[layer_b] = signal_b_to_a * convergence
                state_b.interdependency_signals[layer_a] = signal_a_to_b * convergence

            # Apply interdependency signals to activations
            for state in [state_a, state_b]:
                total_signal = sum(state.interdependency_signals.values())
                state.activation = min(1.0, state.activation + total_signal * 0.05)

    def _apply_personality_modulation(self) -> float:
        """
        Apply personality vector modulation to all layers.
        Returns the PV factor for the core formula.
        """
        if self.personality_vector is None:
            return 1.0

        # Get layer modifiers from personality vector
        try:
            modifiers = self.personality_vector.get_layer_modifiers()
            for layer_name, state in self._layer_states.items():
                if layer_name in modifiers:
                    mod = modifiers[layer_name]
                    state.personality_modifier = mod
                    state.activation = min(1.0, state.activation * mod)

            # PV factor: average personality influence
            pv_factor = 1.0 + 0.1 * sum(
                s.personality_modifier - 1.0 for s in self._layer_states.values()
            ) / len(self._layer_states)
            return max(0.5, min(2.0, pv_factor))
        except Exception:
            return 1.0

    def _apply_flow_optimization(self, input_text: str) -> float:
        """
        Adjust processing depth based on flow state.
        Returns the Flow factor for the core formula.
        """
        if self.flow_navigator is None:
            return 1.0

        try:
            # Estimate challenge level from input
            challenge = min(1.0, len(input_text) / 500 + 0.3)
            skill = 0.7  # Default skill level

            flow_state = self.flow_navigator.assess_flow(challenge, skill)

            # Adjust layer depths based on flow zone
            for state in self._layer_states.values():
                if flow_state.zone.value == "flow":
                    state.flow_depth = 1.2  # Deeper processing in flow
                elif flow_state.zone.value == "boredom":
                    state.flow_depth = 0.8  # Lighter processing when bored
                elif flow_state.zone.value == "anxiety":
                    state.flow_depth = 1.0  # Standard processing when anxious

                state.activation = min(1.0, state.activation * state.flow_depth)

            return flow_state.flow_depth() if hasattr(flow_state, 'flow_depth') else 1.0
        except Exception:
            return 1.0

    def _detect_emergence(self) -> List[EmergencePattern]:
        """
        Ξ Emergence detection — Identify patterns that emerge from
        cross-layer interactions, beyond what any single layer could produce.
        """
        patterns = []

        # Check for synergy: complementary layers both highly activated
        for (la, lb), itype in self.INTERDEPENDENCY_MAP.items():
            sa = self._layer_states[la]
            sb = self._layer_states[lb]

            if itype == InterdependencyType.COMPLEMENTARY:
                if sa.activation > 0.6 and sb.activation > 0.6:
                    strength = (sa.activation + sb.activation) / 2
                    patterns.append(EmergencePattern(
                        pattern_id=f"synergy_{la}_{lb}",
                        source_layers=[la, lb],
                        pattern_type="synergy",
                        strength=strength,
                        description=f"Synergy between {la} and {lb}: combined activation {strength:.2f}",
                    ))

            elif itype == InterdependencyType.CONFLICTING:
                if abs(sa.activation - sb.activation) > 0.4:
                    patterns.append(EmergencePattern(
                        pattern_id=f"conflict_{la}_{lb}",
                        source_layers=[la, lb],
                        pattern_type="conflict",
                        strength=abs(sa.activation - sb.activation),
                        description=f"Tension between {la} ({sa.activation:.2f}) and {lb} ({sb.activation:.2f})",
                    ))

        # Check for novelty: all layers highly activated simultaneously
        all_high = all(s.activation > 0.5 for s in self._layer_states.values())
        if all_high:
            avg_activation = sum(s.activation for s in self._layer_states.values()) / 5
            patterns.append(EmergencePattern(
                pattern_id="novelty_full_activation",
                source_layers=list(self._layer_states.keys()),
                pattern_type="novelty",
                strength=avg_activation,
                description=f"All layers highly activated: average {avg_activation:.2f} — emergent capability likely",
            ))

        # Check for insight: feedback loops converging
        feedback_layers = [
            (la, lb) for (la, lb), itype in self.INTERDEPENDENCY_MAP.items()
            if itype == InterdependencyType.FEEDBACK
        ]
        for la, lb in feedback_layers:
            sa = self._layer_states[la]
            sb = self._layer_states[lb]
            convergence = 1 - abs(sa.activation - sb.activation)
            if convergence > 0.8:
                patterns.append(EmergencePattern(
                    pattern_id=f"insight_{la}_{lb}",
                    source_layers=[la, lb],
                    pattern_type="insight",
                    strength=convergence,
                    description=f"Feedback convergence between {la} and {lb}: {convergence:.2f}",
                ))

        self._emergence_history.extend(patterns)
        return patterns

    def _compute_emergence_value(self, patterns: List[EmergencePattern]) -> float:
        """Compute Ξ emergence value from detected patterns"""
        if not patterns:
            return 1.0

        # Ξ = 1 + Σ(pattern_strength × pattern_weight)
        weights = {"synergy": 0.15, "conflict": 0.05, "novelty": 0.2, "insight": 0.25}
        emergence = 1.0
        for p in patterns:
            emergence += p.strength * weights.get(p.pattern_type, 0.1)

        return min(3.0, emergence)

    def _compute_superposition(self) -> float:
        """Compute ⊕(P,C,Co,E,R) superposition value"""
        activations = [s.activation for s in self._layer_states.values()]
        # ⊕ is not simple average — it's geometric mean weighted by interdependencies
        product = 1.0
        for a in activations:
            product *= max(0.01, a)
        geometric_mean = product ** (1.0 / len(activations))

        # Boost by interdependency signal strength
        total_signals = sum(
            sum(s.interdependency_signals.values())
            for s in self._layer_states.values()
        )
        boost = 1.0 + total_signals * 0.01

        return min(1.0, geometric_mean * boost)

    def _compute_linear_bias(self) -> float:
        """
        Compute L (linear bias) — the tendency to fall back to
        sequential/rule-based processing. Lower is better.
        """
        # L increases when layers are activated sequentially (not simultaneously)
        # L decreases when interdependency signals are strong
        total_interdependency = sum(
            sum(s.interdependency_signals.values())
            for s in self._layer_states.values()
        )

        # Check if activations are too uniform (suggests linear processing)
        activations = [s.activation for s in self._layer_states.values()]
        variance = sum((a - sum(activations)/len(activations))**2 for a in activations) / len(activations)

        # Low variance + low interdependency = high linear bias
        linear_bias = max(0.0, 0.5 - total_interdependency * 0.05 - variance * 2.0)
        return linear_bias

    def _apply_core_formula(self, superposition: float, emergence: float,
                           pv: float, flow: float, linear_bias: float) -> float:
        """
        Apply the core formula:
        Output = ⊕(P,C,Co,E,R)^Ξ × PV × Flow - L

        This formula computes the structural processing quality:
        - ⊕(P,C,Co,E,R): Superposition of all 5 layers
        - ^Ξ: Emergence exponent (cross-layer patterns amplify output)
        - × PV: Personality vector modulation
        - × Flow: Flow state optimization
        - - L: Subtract linear bias (penalize sequential thinking)
        """
        result = (superposition ** emergence) * pv * flow - linear_bias
        return max(0.0, min(2.0, result))

    def _assemble_output(self, input_text: str, context: Dict) -> Tuple[str, float]:
        """
        Assemble the final structure-driven output from all layer states.
        This replaces the traditional rule-matched output.
        """
        # Collect outputs from all layers
        pulse_out = self._layer_states["pulse"].output
        current_out = self._layer_states["current"].output
        construct_out = self._layer_states["construct"].output
        enactive_out = self._layer_states["enactive"].output
        resonance_out = self._layer_states["resonance"].output

        # Structure-driven output assembly
        emotional_context = pulse_out.get("emotional_signal", "normal")
        domain = current_out.get("domain", "general")
        complexity = current_out.get("complexity", "medium")
        plan_type = construct_out.get("plan_type", "quick")
        execution_mode = enactive_out.get("execution_mode", "thorough")
        quality_threshold = resonance_out.get("quality_threshold", "standard")

        # Build output based on structural analysis
        output_parts = []
        if emotional_context == "high_alert":
            output_parts.append("[Structure: Alert Mode]")
        output_parts.append(f"[Domain: {domain}, Complexity: {complexity}]")
        output_parts.append(f"[Plan: {plan_type}, Execution: {execution_mode}]")
        output_parts.append(f"[Quality: {quality_threshold}]")
        output_parts.append(input_text)

        output = " | ".join(output_parts)

        # Confidence based on layer activations and emergence
        avg_activation = sum(s.activation for s in self._layer_states.values()) / 5
        confidence = avg_activation

        return output, confidence

    def _compute_structural_advantage(self, patterns: List[EmergencePattern]) -> str:
        """Compute what structural processing added vs rule-based approach"""
        advantages = []

        # Check personality modulation
        if any(s.personality_modifier != 1.0 for s in self._layer_states.values()):
            advantages.append("Personality-modulated processing")

        # Check flow optimization
        if any(s.flow_depth != 1.0 for s in self._layer_states.values()):
            advantages.append("Flow-state depth adjustment")

        # Check emergence
        synergy_count = sum(1 for p in patterns if p.pattern_type == "synergy")
        if synergy_count > 0:
            advantages.append(f"{synergy_count} cross-layer synergies detected")

        insight_count = sum(1 for p in patterns if p.pattern_type == "insight")
        if insight_count > 0:
            advantages.append(f"{insight_count} feedback convergence insights")

        novelty_count = sum(1 for p in patterns if p.pattern_type == "novelty")
        if novelty_count > 0:
            advantages.append("Full-layer activation — emergent capability")

        if not advantages:
            return "Standard structural processing"

        return "; ".join(advantages)

    def get_layer_states(self) -> Dict[str, LayerState]:
        """Get current layer states"""
        return dict(self._layer_states)

    def get_emergence_history(self) -> List[EmergencePattern]:
        """Get all detected emergence patterns"""
        return list(self._emergence_history)

    def get_conflict_log(self) -> List[Dict]:
        """Get all logged structure-vs-rule conflicts"""
        return list(self._conflict_log)

    def log_conflict(self, rule_id: str, rule_output: str, structure_output: str, reason: str):
        """Log a conflict where structural processing overrode a rule"""
        self._conflict_log.append({
            "rule_id": rule_id,
            "rule_output": rule_output,
            "structure_output": structure_output,
            "reason": reason,
            "timestamp": time.time(),
        })
