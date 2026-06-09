"""LightDarkBalance Engine — 正暗平衡引擎.

Formula:
    LightDarkBalance = ⊕(Light, Dark)^Ξ × Context - |Light - Dark|

Core innovation of EmoGlyphPlay: "知暗行明" (Know the dark, act in the light).
Provides strategic awareness (Dark) while ensuring ethical action (Light),
creating a balanced approach to AI-assisted coding and decision-making.

Three Strategy Modes:
    🟢 Light Mode: Pure constructive, transparent strategies
    🟡 Balanced Mode: Strategic awareness with ethical guardrails
    🔴 Dark Mode: Full strategic awareness for defense/competition analysis
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from harnessing.emoglyphplay.core.context_engine import ContextEngine, ContextSnapshot


class StrategyMode(Enum):
    """Strategy disclosure modes — progressive disclosure of Dark strategies."""

    LIGHT = "light"       # 🟢 Pure constructive strategies only
    BALANCED = "balanced"  # 🟡 Strategic awareness with ethical guardrails
    DARK = "dark"         # 🔴 Full strategic awareness (defense/competition)


class StrategyOrigin(Enum):
    """Origin of a strategy — Eastern or Western tradition."""

    EASTERN = "eastern"
    WESTERN = "western"
    HYBRID = "hybrid"


class Strategy:
    """A single strategy with metadata and ethical classification."""

    def __init__(
        self,
        name: str,
        description: str,
        origin: StrategyOrigin,
        mode: StrategyMode,
        source: str,
        ethical_score: float,
        tags: list[str] | None = None,
    ) -> None:
        self.name = name
        self.description = description
        self.origin = origin
        self.mode = mode
        self.source = source
        self.ethical_score = max(0.0, min(1.0, ethical_score))  # 0.0=dangerous, 1.0=ethical
        self.tags = tags or []

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "origin": self.origin.value,
            "mode": self.mode.value,
            "source": self.source,
            "ethical_score": self.ethical_score,
            "tags": self.tags,
        }


class LightDarkBalanceResult:
    """Result of a LightDarkBalance analysis."""

    def __init__(
        self,
        light_strategies: list[Strategy],
        dark_strategies: list[Strategy],
        balance_score: float,
        context_snapshot: ContextSnapshot,
        mode: StrategyMode,
    ) -> None:
        self.light_strategies = light_strategies
        self.dark_strategies = dark_strategies
        self.balance_score = balance_score
        self.context_snapshot = context_snapshot
        self.mode = mode

    @property
    def all_strategies(self) -> list[Strategy]:
        return self.light_strategies + self.dark_strategies

    def to_dict(self) -> dict[str, Any]:
        return {
            "light_strategies": [s.to_dict() for s in self.light_strategies],
            "dark_strategies": [s.to_dict() for s in self.dark_strategies],
            "balance_score": round(self.balance_score, 4),
            "context": self.context_snapshot.to_dict(),
            "mode": self.mode.value,
        }


class LightDarkBalanceEngine:
    """LightDarkBalance Engine — 正暗平衡引擎.

    Implements the core formula:
        LightDarkBalance = ⊕(Light, Dark)^Ξ × Context - |Light - Dark|

    Where:
        ⊕ = synergistic combination (not simple addition)
        ^Ξ = Harness Engineering synergy amplification factor
        Context = f(culture, market, law, competition, relationship_depth)
        |Light - Dark| = imbalance penalty (too much of either is bad)

    Args:
        context_engine: ContextEngine instance for environment sensing.
        synergy_factor: Ξ amplification factor (default 1.5).
    """

    # Core Eastern Dark strategies (知暗)
    _EASTERN_DARK_CATALOG: list[dict[str, Any]] = [
        {"name": "以退為進", "source": "三十六計", "tag": "negotiation"},
        {"name": "聲東擊西", "source": "三十六計", "tag": "competition"},
        {"name": "暗度陳倉", "source": "三十六計", "tag": "strategy"},
        {"name": "欲擒故縱", "source": "三十六計", "tag": "patience"},
        {"name": "法術勢", "source": "韓非子", "tag": "governance"},
        {"name": "捭闔", "source": "鬼谷子", "tag": "persuasion"},
        {"name": "飛箝", "source": "鬼谷子", "tag": "influence"},
        {"name": "虛實", "source": "孫子兵法", "tag": "deception"},
        {"name": "奇正", "source": "孫子兵法", "tag": "tactics"},
    ]

    # Core Western Dark strategies
    _WESTERN_DARK_CATALOG: list[dict[str, Any]] = [
        {"name": "Principe", "source": "The Prince (Machiavelli)", "tag": "power"},
        {"name": "Law 1: Never Outshine", "source": "48 Laws of Power", "tag": "politics"},
        {"name": "Law 3: Conceal Intentions", "source": "48 Laws of Power", "tag": "strategy"},
        {"name": "Law 15: Crush Completely", "source": "48 Laws of Power", "tag": "competition"},
        {"name": "Reciprocity", "source": "Influence (Cialdini)", "tag": "persuasion"},
        {"name": "Commitment & Consistency", "source": "Influence (Cialdini)", "tag": "influence"},
        {"name": "Social Proof", "source": "Influence (Cialdini)", "tag": "persuasion"},
        {"name": "Scarcity", "source": "Influence (Cialdini)", "tag": "urgency"},
        {"name": "Nudge Architecture", "source": "Nudge (Thaler)", "tag": "choice_design"},
    ]

    def __init__(
        self,
        context_engine: ContextEngine | None = None,
        synergy_factor: float = 1.5,
    ) -> None:
        self.context_engine = context_engine or ContextEngine()
        self.synergy_factor = synergy_factor

    def analyze(
        self,
        input_text: str,
        mode: StrategyMode = StrategyMode.BALANCED,
        context_override: dict[str, Any] | None = None,
    ) -> LightDarkBalanceResult:
        """Analyze input and generate balanced Light/Dark strategies.

        Args:
            input_text: The task or situation to analyze.
            mode: Strategy disclosure mode (Light/Balanced/Dark).
            context_override: Optional context overrides.

        Returns:
            LightDarkBalanceResult with strategies and balance score.
        """
        context = self.context_engine.sense(input_text, context_override)

        # Generate Light strategies (always available)
        light_strategies = self._generate_light_strategies(input_text, context)

        # Generate Dark strategies (mode-dependent)
        dark_strategies = self._generate_dark_strategies(input_text, context, mode)

        # Calculate balance score
        light_weight = len(light_strategies) or 1
        dark_weight = len(dark_strategies) or 1
        raw_balance = (light_weight * dark_weight) ** self.synergy_factor
        imbalance_penalty = abs(light_weight - dark_weight)
        balance_score = raw_balance / (raw_balance + imbalance_penalty + 1e-9)

        return LightDarkBalanceResult(
            light_strategies=light_strategies,
            dark_strategies=dark_strategies,
            balance_score=balance_score,
            context_snapshot=context,
            mode=mode,
        )

    def _generate_light_strategies(
        self,
        input_text: str,
        context: ContextSnapshot,
    ) -> list[Strategy]:
        """Generate constructive, transparent strategies."""
        strategies: list[Strategy] = []
        text_lower = input_text.lower()

        # Universal Light strategies based on context
        if any(kw in text_lower for kw in ["refactor", "improve", "optimize"]):
            strategies.append(Strategy(
                name="Incremental Improvement",
                description="Break down improvements into small, verifiable steps.",
                origin=StrategyOrigin.WESTERN,
                mode=StrategyMode.LIGHT,
                source="Engineering Best Practices",
                ethical_score=1.0,
                tags=["refactoring", "safety"],
            ))

        if any(kw in text_lower for kw in ["debug", "fix", "error"]):
            strategies.append(Strategy(
                name="Root Cause Analysis",
                description="Trace the error to its source before applying fixes.",
                origin=StrategyOrigin.WESTERN,
                mode=StrategyMode.LIGHT,
                source="Debugging Methodology",
                ethical_score=1.0,
                tags=["debugging", "reliability"],
            ))

        if any(kw in text_lower for kw in ["design", "architect", "plan"]):
            strategies.append(Strategy(
                name="Structure-First Design",
                description="Define the structure before implementation; Rule 103.",
                origin=StrategyOrigin.EASTERN,
                mode=StrategyMode.LIGHT,
                source="Harness Engineering Rule 103",
                ethical_score=1.0,
                tags=["architecture", "planning"],
            ))

        # Always include a default Light strategy
        if not strategies:
            strategies.append(Strategy(
                name="Transparent Execution",
                description="Execute the task with full transparency and traceability.",
                origin=StrategyOrigin.HYBRID,
                mode=StrategyMode.LIGHT,
                source="EmoGlyphPlay Core",
                ethical_score=1.0,
                tags=["transparency", "trust"],
            ))

        return strategies

    def _generate_dark_strategies(
        self,
        input_text: str,
        context: ContextSnapshot,
        mode: StrategyMode,
    ) -> list[Strategy]:
        """Generate strategic awareness strategies based on mode."""
        if mode == StrategyMode.LIGHT:
            return []  # No Dark strategies in Light mode

        strategies: list[Strategy] = []
        text_lower = input_text.lower()

        # Competition-aware strategies
        if any(kw in text_lower for kw in ["compete", "market", "rival", "competitor"]):
            strategies.append(Strategy(
                name="虛實 (Deception & Reality)",
                description="Strategic awareness: understand what competitors show vs. what they hide. "
                            "Use this for DEFENSE only — know the dark to protect the light.",
                origin=StrategyOrigin.EASTERN,
                mode=StrategyMode.BALANCED,
                source="孫子兵法",
                ethical_score=0.7,
                tags=["competition", "defense", "awareness"],
            ))

        # Negotiation strategies
        if any(kw in text_lower for kw in ["negotiate", "deal", "contract", "price"]):
            strategies.append(Strategy(
                name="捭闔 (Open & Close)",
                description="Strategic awareness: understand when to open (disclose) and when to close "
                            "(withhold) information in negotiations. Ethical use: protect your interests "
                            "without deceiving.",
                origin=StrategyOrigin.EASTERN,
                mode=StrategyMode.BALANCED,
                source="鬼谷子",
                ethical_score=0.6,
                tags=["negotiation", "awareness"],
            ))

        # Influence strategies
        if any(kw in text_lower for kw in ["persuade", "convince", "influence", "sell"]):
            strategies.append(Strategy(
                name="Reciprocity Principle",
                description="Strategic awareness: people feel obligated to return favors. "
                            "Use ethically: provide genuine value first, don't manipulate.",
                origin=StrategyOrigin.WESTERN,
                mode=StrategyMode.BALANCED,
                source="Influence (Cialdini)",
                ethical_score=0.65,
                tags=["influence", "persuasion"],
            ))

        # Dark mode: add deeper strategic awareness
        if mode == StrategyMode.DARK:
            strategies.append(Strategy(
                name="法術勢 (Law-Method-Power)",
                description="Full strategic governance framework: 法(rules), 術(methods), 勢(power dynamics). "
                            "Understand power structures to navigate organizational complexity. "
                            "WARNING: For strategic awareness ONLY — never for unethical action.",
                origin=StrategyOrigin.EASTERN,
                mode=StrategyMode.DARK,
                source="韓非子",
                ethical_score=0.4,
                tags=["governance", "power", "defense"],
            ))
            strategies.append(Strategy(
                name="Law 3: Conceal Intentions",
                description="Full strategic awareness: in competitive environments, revealing plans "
                            "too early invites counter-moves. Use for DEFENSE: protect your strategy "
                            "from being exploited. Never use to deceive partners.",
                origin=StrategyOrigin.WESTERN,
                mode=StrategyMode.DARK,
                source="48 Laws of Power",
                ethical_score=0.35,
                tags=["competition", "defense", "caution"],
            ))

        return strategies

    def get_catalog(self, origin: StrategyOrigin | None = None) -> list[dict[str, Any]]:
        """Get the strategy catalog, optionally filtered by origin.

        Args:
            origin: Optional filter by Eastern/Western/Hybrid.

        Returns:
            List of strategy catalog entries.
        """
        catalogs = self._EASTERN_DARK_CATALOG + self._WESTERN_DARK_CATALOG
        if origin is None:
            return catalogs
        origin_map = {
            StrategyOrigin.EASTERN: self._EASTERN_DARK_CATALOG,
            StrategyOrigin.WESTERN: self._WESTERN_DARK_CATALOG,
        }
        return origin_map.get(origin, [])
