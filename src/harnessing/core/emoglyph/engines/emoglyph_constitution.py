"""
EmoGlyph Constitution — 情感符號憲法
The "Operating System" for Structure-Driven AI Processing

Defines 5 Constitutional Principles that govern all AI processing,
making the structural model take precedence over rules/skills/decisions.
Traditional rules become subordinate patterns — invoked BY the structure,
not INSTEAD of the structure.

Analogous to a nation's constitution that governs all laws,
the EmoGlyph Constitution governs all processing patterns.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
import time


class ConstitutionalPrinciple(Enum):
    """憲法原則 — The 5 fundamental principles of structure-driven AI"""
    CIRCULAR_PROCESSING = "circular_processing"          # 五層循環處理原則
    PERSONALITY_MODULATION = "personality_modulation"    # 人格向量調製原則
    FLOW_OPTIMIZATION = "flow_optimization"              # 心流狀態優化原則
    EMERGENCE_OVER_RULE = "emergence_over_rule"          # 湧現優先於規則原則
    HUMAN_STEER_AGENT_EXECUTE = "human_steer_agent_execute"  # 人類掌舵智能體執行原則


class ConflictResolution(Enum):
    """衝突解決策略"""
    STRUCTURE_WINS = "structure_wins"      # 結構優先
    RULE_WINS = "rule_wins"                # 規則優先 (rare)
    NEGOTIATE = "negotiate"                # 協商 (blend both)
    DEFER_TO_HUMAN = "defer_to_human"      # 交給人類決定


class AmendmentStatus(Enum):
    """修正案狀態"""
    PROPOSED = "proposed"
    UNDER_REVIEW = "under_review"
    RATIFIED = "ratified"
    REJECTED = "rejected"


@dataclass
class ConstitutionalConflict:
    """憲法衝突 — A conflict between structural processing and a rule"""
    conflict_id: str
    principle: ConstitutionalPrinciple
    rule_id: str
    rule_description: str
    structure_path: str
    resolution: ConflictResolution
    reason: str
    timestamp: float = 0.0

    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()


@dataclass
class ConstitutionalAmendment:
    """憲法修正案 — A proposed change to the Constitution"""
    amendment_id: str
    principle: ConstitutionalPrinciple
    description: str
    rationale: str
    status: AmendmentStatus = AmendmentStatus.PROPOSED
    proposed_at: float = 0.0
    ratified_at: Optional[float] = None

    def __post_init__(self):
        if self.proposed_at == 0.0:
            self.proposed_at = time.time()


@dataclass
class PrincipleViolation:
    """原則違反 — A detected violation of a constitutional principle"""
    principle: ConstitutionalPrinciple
    violation_type: str
    description: str
    severity: float  # 0.0-1.0
    suggested_fix: str


@dataclass
class ConstitutionState:
    """憲法狀態 — Current state of the Constitution"""
    active_principles: Dict[ConstitutionalPrinciple, bool] = field(default_factory=dict)
    conflict_count: int = 0
    amendment_count: int = 0
    last_conflict: Optional[ConstitutionalConflict] = None
    principle_strengths: Dict[ConstitutionalPrinciple, float] = field(default_factory=dict)


class ConstitutionalGuard:
    """
    憲法守衛 — Validates that all processing follows the structural model.

    The Guard checks every processing step against the 5 Constitutional
    Principles and logs any violations. When a rule conflicts with the
    structural model, the Guard ensures the structural path is followed.
    """

    PRINCIPLE_DESCRIPTIONS = {
        ConstitutionalPrinciple.CIRCULAR_PROCESSING: (
            "五層循環處理原則 — All AI processing must go through the 5-layer "
            "circular model (Pulse↔Current↔Construct↔Enactive↔Resonance) "
            "with simultaneous activation and bidirectional interdependency."
        ),
        ConstitutionalPrinciple.PERSONALITY_MODULATION: (
            "人格向量調製原則 — All layer outputs must be modulated by the "
            "25D Personality Vector (DISC₄ + OCEAN₅ + MBTI₈ + VAK₃ + Eastern₅). "
            "Generic, personality-blind processing violates this principle."
        ),
        ConstitutionalPrinciple.FLOW_OPTIMIZATION: (
            "心流狀態優化原則 — Processing depth must be adjusted based on "
            "the user's flow state (challenge/skill ratio). Static, "
            "one-size-fits-all processing depth violates this principle."
        ),
        ConstitutionalPrinciple.EMERGENCE_OVER_RULE: (
            "湧現優先於規則原則 — When cross-layer emergence patterns are "
            "detected, they take precedence over rule-based decisions. "
            "Rules are subordinate patterns invoked BY the structure, "
            "not INSTEAD of the structure."
        ),
        ConstitutionalPrinciple.HUMAN_STEER_AGENT_EXECUTE: (
            "人類掌舵智能體執行原則 — The AI is the implementation king, "
            "not the decision maker. The AI provides reports, suggestions "
            "with confidence levels, decision points, and feedback requests. "
            "The human makes all final decisions."
        ),
    }

    def __init__(self):
        self._conflicts: List[ConstitutionalConflict] = []
        self._amendments: List[ConstitutionalAmendment] = []
        self._violation_log: List[PrincipleViolation] = []
        self._state = ConstitutionState(
            active_principles={p: True for p in ConstitutionalPrinciple},
            principle_strengths={p: 1.0 for p in ConstitutionalPrinciple},
        )

    def validate_processing(self, processing_result: Dict) -> Tuple[bool, List[PrincipleViolation]]:
        """
        Validate that a processing result follows all constitutional principles.

        Args:
            processing_result: Dict containing processing details

        Returns:
            Tuple of (is_valid, violations_list)
        """
        violations = []

        # Check Circular Processing Principle
        if self._state.active_principles[ConstitutionalPrinciple.CIRCULAR_PROCESSING]:
            layer_states = processing_result.get("layer_states", {})
            if len(layer_states) < 5:
                violations.append(PrincipleViolation(
                    principle=ConstitutionalPrinciple.CIRCULAR_PROCESSING,
                    violation_type="incomplete_layers",
                    description=f"Only {len(layer_states)} layers activated, expected 5",
                    severity=0.8,
                    suggested_fix="Ensure all 5 layers are activated simultaneously",
                ))

            # Check for sequential processing (linear bias)
            if processing_result.get("linear_bias", 0) > 0.3:
                violations.append(PrincipleViolation(
                    principle=ConstitutionalPrinciple.CIRCULAR_PROCESSING,
                    violation_type="linear_bias",
                    description=f"Linear bias too high: {processing_result.get('linear_bias', 0):.2f}",
                    severity=0.5,
                    suggested_fix="Strengthen interdependency signals between layers",
                ))

        # Check Personality Modulation Principle
        if self._state.active_principles[ConstitutionalPrinciple.PERSONALITY_MODULATION]:
            if not processing_result.get("personality_modulated", False):
                violations.append(PrincipleViolation(
                    principle=ConstitutionalPrinciple.PERSONALITY_MODULATION,
                    violation_type="no_personality_modulation",
                    description="Processing was not modulated by personality vector",
                    severity=0.6,
                    suggested_fix="Apply PersonalityVector modulation to all layer outputs",
                ))

        # Check Flow Optimization Principle
        if self._state.active_principles[ConstitutionalPrinciple.FLOW_OPTIMIZATION]:
            if not processing_result.get("flow_optimized", False):
                violations.append(PrincipleViolation(
                    principle=ConstitutionalPrinciple.FLOW_OPTIMIZATION,
                    violation_type="no_flow_optimization",
                    description="Processing depth was not adjusted by flow state",
                    severity=0.4,
                    suggested_fix="Apply FlowStateNavigator to adjust processing depth",
                ))

        # Check Emergence-Over-Rule Principle
        if self._state.active_principles[ConstitutionalPrinciple.EMERGENCE_OVER_RULE]:
            emergence_patterns = processing_result.get("emergence_patterns", [])
            processing_mode = processing_result.get("processing_mode", "rule_fallback")
            if processing_mode == "rule_fallback" and len(emergence_patterns) > 0:
                violations.append(PrincipleViolation(
                    principle=ConstitutionalPrinciple.EMERGENCE_OVER_RULE,
                    violation_type="rule_over_emergence",
                    description="Rule-based processing used despite emergence patterns",
                    severity=0.7,
                    suggested_fix="Follow emergence-driven path instead of rule fallback",
                ))

        # Check Human-Steer-Agent-Execute Principle
        if self._state.active_principles[ConstitutionalPrinciple.HUMAN_STEER_AGENT_EXECUTE]:
            if processing_result.get("auto_decided", False):
                violations.append(PrincipleViolation(
                    principle=ConstitutionalPrinciple.HUMAN_STEER_AGENT_EXECUTE,
                    violation_type="auto_decision",
                    description="AI made a decision without human input",
                    severity=0.9,
                    suggested_fix="Present options with confidence levels and defer to human",
                ))

        # Log violations
        self._violation_log.extend(violations)

        is_valid = len(violations) == 0
        return is_valid, violations

    def resolve_conflict(self, rule_id: str, rule_description: str,
                        structure_path: str, principle: ConstitutionalPrinciple,
                        reason: str) -> ConstitutionalConflict:
        """
        Resolve a conflict between a rule and the structural model.
        By default, the structural model wins (STRUCTURE_WINS).
        """
        # Default resolution: structure wins
        resolution = ConflictResolution.STRUCTURE_WINS

        # Exception: if the rule is a safety rule, defer to human
        safety_keywords = ["安全", "safety", "harm", "危險", "illegal", "違法"]
        if any(kw in rule_description.lower() for kw in safety_keywords):
            resolution = ConflictResolution.DEFER_TO_HUMAN

        conflict = ConstitutionalConflict(
            conflict_id=f"conflict_{len(self._conflicts) + 1}",
            principle=principle,
            rule_id=rule_id,
            rule_description=rule_description,
            structure_path=structure_path,
            resolution=resolution,
            reason=reason,
        )

        self._conflicts.append(conflict)
        self._state.conflict_count += 1
        self._state.last_conflict = conflict

        return conflict

    def propose_amendment(self, principle: ConstitutionalPrinciple,
                         description: str, rationale: str) -> ConstitutionalAmendment:
        """
        Propose a constitutional amendment.
        Amendments allow the Constitution to evolve over time.
        """
        amendment = ConstitutionalAmendment(
            amendment_id=f"amendment_{len(self._amendments) + 1}",
            principle=principle,
            description=description,
            rationale=rationale,
        )

        self._amendments.append(amendment)
        self._state.amendment_count += 1

        return amendment

    def ratify_amendment(self, amendment_id: str) -> bool:
        """Ratify a proposed amendment"""
        for amendment in self._amendments:
            if amendment.amendment_id == amendment_id:
                amendment.status = AmendmentStatus.RATIFIED
                amendment.ratified_at = time.time()
                return True
        return False

    def get_principle_description(self, principle: ConstitutionalPrinciple) -> str:
        """Get the description of a constitutional principle"""
        return self.PRINCIPLE_DESCRIPTIONS.get(principle, "Unknown principle")

    def get_all_principles(self) -> Dict[ConstitutionalPrinciple, str]:
        """Get all constitutional principles with descriptions"""
        return dict(self.PRINCIPLE_DESCRIPTIONS)

    def get_state(self) -> ConstitutionState:
        """Get current constitution state"""
        return self._state

    def get_conflicts(self) -> List[ConstitutionalConflict]:
        """Get all logged conflicts"""
        return list(self._conflicts)

    def get_amendments(self) -> List[ConstitutionalAmendment]:
        """Get all proposed amendments"""
        return list(self._amendments)

    def get_violations(self) -> List[PrincipleViolation]:
        """Get all logged violations"""
        return list(self._violation_log)

    def is_principle_active(self, principle: ConstitutionalPrinciple) -> bool:
        """Check if a principle is currently active"""
        return self._state.active_principles.get(principle, False)

    def set_principle_strength(self, principle: ConstitutionalPrinciple, strength: float):
        """Set the strength of a constitutional principle (0.0-1.0)"""
        self._state.principle_strengths[principle] = max(0.0, min(1.0, strength))


class EmoGlyphConstitution:
    """
    情感符號憲法 — The governing architecture for structure-driven AI.

    This is the "Constitution" that all AI processing must follow.
    It establishes the structural model as the primary processing paradigm,
    with traditional rules/skills/decisions as subordinate patterns.

    The Constitution consists of:
    1. 5 Constitutional Principles (the fundamental laws)
    2. ConstitutionalGuard (enforcement mechanism)
    3. Amendment process (evolution mechanism)
    4. Conflict resolution (structure vs rule disputes)

    Usage:
        constitution = EmoGlyphConstitution()

        # Validate processing
        is_valid, violations = constitution.validate(processing_result)

        # Resolve conflict
        conflict = constitution.resolve_conflict(
            rule_id="R42",
            rule_description="Always use Python for backend",
            structure_path="Current→Construct→Enactive",
            principle=ConstitutionalPrinciple.EMERGENCE_OVER_RULE,
            reason="Structural analysis suggests Rust is better for this use case"
        )
    """

    def __init__(self):
        self._guard = ConstitutionalGuard()
        self._version = "1.0.0"
        self._ratification_date = time.time()

    @property
    def guard(self) -> ConstitutionalGuard:
        """Get the Constitutional Guard"""
        return self._guard

    @property
    def version(self) -> str:
        """Get the Constitution version"""
        return self._version

    def validate(self, processing_result: Dict) -> Tuple[bool, List[PrincipleViolation]]:
        """
        Validate that a processing result follows the Constitution.
        Delegates to ConstitutionalGuard.
        """
        return self._guard.validate_processing(processing_result)

    def resolve_conflict(self, rule_id: str, rule_description: str,
                        structure_path: str, principle: ConstitutionalPrinciple,
                        reason: str) -> ConstitutionalConflict:
        """
        Resolve a conflict between a rule and the structural model.
        Delegates to ConstitutionalGuard.
        """
        return self._guard.resolve_conflict(
            rule_id, rule_description, structure_path, principle, reason
        )

    def get_preamble(self) -> str:
        """
        Get the Constitution preamble — the founding statement.
        """
        return (
            "EmoGlyph Constitution — 情感符號憲法\n"
            "═══════════════════════════════════\n\n"
            "We establish this Constitution to govern all AI processing,\n"
            "replacing the traditional rule→skill→decision pipeline with\n"
            "structure-driven processing through the 5-layer circular model.\n\n"
            "Core Formula: Output = ⊕(P,C,Co,E,R)^Ξ × PV × Flow - L\n\n"
            "Principles:\n"
            "1. Circular Processing — All 5 layers activate simultaneously\n"
            "2. Personality Modulation — 25D vector modulates all outputs\n"
            "3. Flow Optimization — Processing depth adapts to flow state\n"
            "4. Emergence Over Rule — Cross-layer patterns override rules\n"
            "5. Human Steer, Agent Execute — AI implements, human decides\n\n"
            "Rules are subordinate patterns — invoked BY the structure,\n"
            "not INSTEAD of the structure."
        )

    def get_comparison_with_traditional_llm(self) -> Dict[str, str]:
        """
        Get a comparison between EmoGlyph Constitution and traditional LLM processing.
        This is the user-facing explanation of the paradigm shift.
        """
        return {
            "traditional_llm": (
                "Input → Token Processing → Rule Matching → Skill Execution → Output\n"
                "特點：線性處理、關鍵詞匹配、無情境感知、無人格調製、無心流優化"
            ),
            "emoglyph_constitution": (
                "Input → ⊕(P,C,Co,E,R)^Ξ × PV × Flow - L → Structure-Driven Output\n"
                "特點：循環處理、結構驅動、人格調製、心流優化、湧現優先"
            ),
            "key_differences": (
                "1. 循環 vs 線性 — EmoGlyph 5層同時處理，傳統LLM逐步處理\n"
                "2. 人格感知 vs 通用 — EmoGlyph 25D人格向量調製，傳統LLM一刀切\n"
                "3. 心流優化 vs 靜態 — EmoGlyph 根據心流狀態調整深度，傳統LLM固定深度\n"
                "4. 湧現驅動 vs 規則驅動 — EmoGlyph 跨層湧現優先，傳統LLM規則匹配\n"
                "5. 人類掌舵 vs AI自決 — EmoGlyph 人類做決定，傳統LLM AI自行決定"
            ),
            "practical_example": (
                "用戶說「我要在中國收錢」：\n"
                "傳統LLM：匹配「支付」關鍵詞 → 推薦 PayPal → 輸出\n"
                "EmoGlyph：Pulse(渴望) + Current(中國+支付) 同時共振 → "
                "Construct(組裝支付技能圖) → 自動推薦 alipay + douyinpay → "
                "Resonance(質量評估) → 輸出含人格調製的建議"
            ),
        }
