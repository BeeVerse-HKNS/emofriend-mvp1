"""Strategy Generator — Dark Strategy Synthesis Engine.

Combines Eastern and Western dark strategy traditions with context
awareness and ethical boundaries to generate actionable strategic
recommendations.

Formula:
    Strategy = ⊕(Eastern, Western)^Ξ × Context × EthicsGuard - Unethical

Only generates strategies that pass the EthicsGuard check.
"""

from __future__ import annotations

from typing import Any

from harnessing.emoglyphplay.core.context_engine import ContextEngine, ContextSnapshot
from harnessing.emoglyphplay.core.ethics_guard import EthicsGuard, ViolationSeverity
from harnessing.emoglyphplay.dark_mapping.eastern_dark import EasternDarkMapper, EasternStrategyCategory
from harnessing.emoglyphplay.dark_mapping.western_dark import WesternDarkMapper, WesternStrategyCategory


class GeneratedStrategy:
    """A generated strategy with full metadata."""

    def __init__(
        self,
        name: str,
        description: str,
        origin: str,
        ethical_score: float,
        defense_use: str,
        context_match: float,
        ethics_passed: bool,
    ) -> None:
        self.name = name
        self.description = description
        self.origin = origin
        self.ethical_score = ethical_score
        self.defense_use = defense_use
        self.context_match = context_match
        self.ethics_passed = ethics_passed

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "origin": self.origin,
            "ethical_score": self.ethical_score,
            "defense_use": self.defense_use,
            "context_match": round(self.context_match, 3),
            "ethics_passed": self.ethics_passed,
        }


class StrategyGenerator:
    """Strategy Generator — Dark Strategy Synthesis Engine.

    Combines Eastern and Western dark strategy catalogs with context
    awareness and ethical boundaries to generate actionable strategies.

    Args:
        context_engine: ContextEngine for environment sensing.
        ethics_guard: EthicsGuard for boundary enforcement.
        eastern_mapper: EasternDarkMapper for Eastern strategies.
        western_mapper: WesternDarkMapper for Western strategies.
    """

    # Context-to-category mapping for Eastern strategies
    _EASTERN_CONTEXT_MAP: dict[str, list[EasternStrategyCategory]] = {
        "competition": [
            EasternStrategyCategory.DECEPTION,
            EasternStrategyCategory.TACTICS,
            EasternStrategyCategory.POSITIONING,
        ],
        "negotiation": [EasternStrategyCategory.PERSUASION, EasternStrategyCategory.PATIENCE],
        "governance": [EasternStrategyCategory.GOVERNANCE, EasternStrategyCategory.POSITIONING],
        "defense": [EasternStrategyCategory.INTELLIGENCE, EasternStrategyCategory.POSITIONING],
    }

    # Context-to-category mapping for Western strategies
    _WESTERN_CONTEXT_MAP: dict[str, list[WesternStrategyCategory]] = {
        "competition": [WesternStrategyCategory.COMPETITION, WesternStrategyCategory.POWER],
        "negotiation": [WesternStrategyCategory.NEGOTIATION, WesternStrategyCategory.PERSUASION],
        "persuasion": [WesternStrategyCategory.PERSUASION, WesternStrategyCategory.CHOICE_DESIGN],
        "defense": [WesternStrategyCategory.DEFENSE, WesternStrategyCategory.POWER],
    }

    def __init__(
        self,
        context_engine: ContextEngine | None = None,
        ethics_guard: EthicsGuard | None = None,
        eastern_mapper: EasternDarkMapper | None = None,
        western_mapper: WesternDarkMapper | None = None,
    ) -> None:
        self.context_engine = context_engine or ContextEngine()
        self.ethics_guard = ethics_guard or EthicsGuard()
        self.eastern_mapper = eastern_mapper or EasternDarkMapper()
        self.western_mapper = western_mapper or WesternDarkMapper()

    def generate(
        self,
        input_text: str,
        context_override: dict[str, Any] | None = None,
    ) -> list[GeneratedStrategy]:
        """Generate context-aware strategies with ethical filtering.

        Args:
            input_text: The task or situation to generate strategies for.
            context_override: Optional context overrides.

        Returns:
            List of GeneratedStrategy objects that pass ethics checks.
        """
        context = self.context_engine.sense(input_text, context_override)
        context_type = self._infer_context_type(input_text, context)

        # Get relevant strategies from both traditions
        eastern_categories = self._EASTERN_CONTEXT_MAP.get(context_type, [])
        western_categories = self._WESTERN_CONTEXT_MAP.get(context_type, [])

        candidates: list[dict[str, Any]] = []

        for cat in eastern_categories:
            strategies = self.eastern_mapper.get_strategies(category=cat)
            for s in strategies:
                s["_origin_type"] = "eastern"
                candidates.append(s)

        for cat in western_categories:
            strategies = self.western_mapper.get_strategies(category=cat)
            for s in strategies:
                s["_origin_type"] = "western"
                candidates.append(s)

        # If no context-specific matches, get all strategies
        if not candidates:
            candidates = self.eastern_mapper.get_strategies() + self.western_mapper.get_strategies()
            for s in candidates:
                if "_origin_type" not in s:
                    s["_origin_type"] = "unknown"

        # Filter through ethics guard
        results: list[GeneratedStrategy] = []
        for s in candidates:
            ethics_result = self.ethics_guard.check(f"{s['name']} {s.get('description', '')}")
            if ethics_result.severity in (ViolationSeverity.FATAL,):
                continue  # Skip fatal violations

            context_match = self._calculate_context_match(s, context)
            results.append(GeneratedStrategy(
                name=s["name"],
                description=s.get("description", ""),
                origin=s.get("_origin_type", "unknown"),
                ethical_score=s.get("ethical_score", 0.5),
                defense_use=s.get("defense_use", ""),
                context_match=context_match,
                ethics_passed=ethics_result.is_ethical,
            ))

        # Sort by context match (descending), then ethical score (descending)
        results.sort(key=lambda s: (s.context_match, s.ethical_score), reverse=True)
        return results[:10]  # Top 10 strategies

    def _infer_context_type(self, input_text: str, context: ContextSnapshot) -> str:
        """Infer the primary context type from input and context.

        Args:
            input_text: The input text.
            context: The sensed context snapshot.

        Returns:
            A context type string.
        """
        text_lower = input_text.lower()

        if any(kw in text_lower for kw in ["compete", "rival", "market", "competitor"]):
            return "competition"
        if any(kw in text_lower for kw in ["negotiate", "deal", "contract", "price"]):
            return "negotiation"
        if any(kw in text_lower for kw in ["govern", "manage", "organize", "team"]):
            return "governance"
        if any(kw in text_lower for kw in ["persuade", "convince", "influence", "sell"]):
            return "persuasion"
        if any(kw in text_lower for kw in ["defend", "protect", "secure", "guard"]):
            return "defense"

        # Fall back to context-based inference
        if context.competition.value in ("high", "intense"):
            return "competition"
        if context.risk_level > 0.5:
            return "defense"

        return "competition"  # Default

    @staticmethod
    def _calculate_context_match(strategy: dict[str, Any], context: ContextSnapshot) -> float:
        """Calculate how well a strategy matches the current context.

        Args:
            strategy: Strategy dictionary.
            context: Current context snapshot.

        Returns:
            Match score from 0.0 to 1.0.
        """
        score = 0.5  # Base match

        # Higher risk → prefer higher ethical score strategies
        ethical = strategy.get("ethical_score", 0.5)
        if context.risk_level > 0.5 and ethical > 0.6:
            score += 0.2
        elif context.risk_level < 0.3:
            score += 0.1

        # Competition context → prefer competition strategies
        category = strategy.get("category", "")
        if context.competition.value in ("high", "intense") and category in ("competition", "deception", "tactics"):
            score += 0.15

        return min(1.0, score)
