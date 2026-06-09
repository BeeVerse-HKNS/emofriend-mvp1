"""Western Dark Strategy Mapper — 西方暗面映射.

Maps Western strategic traditions into a structured framework:
    - Machiavelli (The Prince): Power dynamics and realpolitik
    - 48 Laws of Power (Greene): Power acquisition and maintenance
    - Cialdini (Influence): Six principles of persuasion
    - Thaler (Nudge): Choice architecture and behavioral economics

Each strategy is classified with:
    - Ethical score (0.0-1.0)
    - Appropriate use context (defense/competition/negotiation)
    - Source text and tradition
"""

from __future__ import annotations

from enum import Enum
from typing import Any


class WesternTradition(Enum):
    """Western strategic traditions."""

    MACHIAVELLI = "The Prince"
    FORTY_EIGHT_LAWS = "48 Laws of Power"
    CIALDINI = "Influence"
    NUDGE = "Nudge"


class WesternStrategyCategory(Enum):
    """Categories of Western strategies."""

    POWER = "power"                 # Power acquisition and maintenance
    PERSUASION = "persuasion"       # Influence and persuasion techniques
    CHOICE_DESIGN = "choice_design" # Choice architecture and nudging
    COMPETITION = "competition"     # Competitive strategy
    DEFENSE = "defense"             # Defensive positioning
    NEGOTIATION = "negotiation"     # Negotiation tactics


# Western strategy catalog with ethical scores
_WESTERN_STRATEGIES: list[dict[str, Any]] = [
    # Machiavelli — Power Dynamics
    {"name": "Principe (The Prince)", "tradition": WesternTradition.MACHIAVELLI,
     "category": WesternStrategyCategory.POWER, "ethical_score": 0.3,
     "description": "It is better to be feared than loved, if you cannot be both.",
     "defense_use": "Understand power dynamics to protect yourself from exploitation."},
    {"name": "Appearances Matter", "tradition": WesternTradition.MACHIAVELLI,
     "category": WesternStrategyCategory.POWER, "ethical_score": 0.4,
     "description": "Everyone sees what you appear to be, few experience what you really are.",
     "defense_use": "Be aware that others may not be what they appear; verify claims."},
    # 48 Laws of Power — Power Acquisition
    {"name": "Law 1: Never Outshine the Master", "tradition": WesternTradition.FORTY_EIGHT_LAWS,
     "category": WesternStrategyCategory.POWER, "ethical_score": 0.35,
     "description": "Always make those above you feel comfortably superior.",
     "defense_use": "Understand organizational hierarchies to navigate them safely."},
    {"name": "Law 3: Conceal Intentions", "tradition": WesternTradition.FORTY_EIGHT_LAWS,
     "category": WesternStrategyCategory.POWER, "ethical_score": 0.3,
     "description": "Keep people off-balance by never revealing your purpose.",
     "defense_use": "Protect your strategic plans from being exploited by competitors."},
    {"name": "Law 15: Crush Completely", "tradition": WesternTradition.FORTY_EIGHT_LAWS,
     "category": WesternStrategyCategory.COMPETITION, "ethical_score": 0.15,
     "description": "When you crush an enemy, leave nothing to chance.",
     "defense_use": "Be aware that some competitors may try to eliminate you entirely."},
    {"name": "Law 16: Use Absence", "tradition": WesternTradition.FORTY_EIGHT_LAWS,
     "category": WesternStrategyCategory.POWER, "ethical_score": 0.5,
     "description": "Use absence to increase respect and honor.",
     "defense_use": "Recognize when scarcity creates perceived value."},
    # Cialdini — Influence
    {"name": "Reciprocity", "tradition": WesternTradition.CIALDINI,
     "category": WesternStrategyCategory.PERSUASION, "ethical_score": 0.65,
     "description": "People feel obligated to return favors.",
     "defense_use": "Provide genuine value first; detect when others use reciprocity to manipulate."},
    {"name": "Commitment & Consistency", "tradition": WesternTradition.CIALDINI,
     "category": WesternStrategyCategory.PERSUASION, "ethical_score": 0.6,
     "description": "Once committed, people feel pressure to behave consistently.",
     "defense_use": "Be cautious about early commitments; detect lock-in tactics."},
    {"name": "Social Proof", "tradition": WesternTradition.CIALDINI,
     "category": WesternStrategyCategory.PERSUASION, "ethical_score": 0.7,
     "description": "People follow the actions of similar others.",
     "defense_use": "Use genuine testimonials; detect fake social proof in marketing."},
    {"name": "Authority", "tradition": WesternTradition.CIALDINI,
     "category": WesternStrategyCategory.PERSUASION, "ethical_score": 0.65,
     "description": "People defer to experts and authority figures.",
     "defense_use": "Establish genuine expertise; question false authority claims."},
    {"name": "Liking", "tradition": WesternTradition.CIALDINI,
     "category": WesternStrategyCategory.PERSUASION, "ethical_score": 0.75,
     "description": "People prefer to say yes to those they like.",
     "defense_use": "Build genuine relationships; detect superficial charm tactics."},
    {"name": "Scarcity", "tradition": WesternTradition.CIALDINI,
     "category": WesternStrategyCategory.PERSUASION, "ethical_score": 0.55,
     "description": "Things seem more valuable when they are less available.",
     "defense_use": "Create genuine urgency; detect artificial scarcity tactics."},
    # Nudge — Choice Architecture
    {"name": "Default Effect", "tradition": WesternTradition.NUDGE,
     "category": WesternStrategyCategory.CHOICE_DESIGN, "ethical_score": 0.7,
     "description": "People tend to go with the pre-set default option.",
     "defense_use": "Set ethical defaults; detect manipulative default settings."},
    {"name": "Framing", "tradition": WesternTradition.NUDGE,
     "category": WesternStrategyCategory.CHOICE_DESIGN, "ethical_score": 0.6,
     "description": "How options are presented affects choices.",
     "defense_use": "Present options fairly; detect misleading framing in offers."},
    {"name": "Anchoring", "tradition": WesternTradition.NUDGE,
     "category": WesternStrategyCategory.NEGOTIATION, "ethical_score": 0.55,
     "description": "The first number mentioned anchors all subsequent negotiations.",
     "defense_use": "Set fair anchors; detect when others use extreme anchors."},
]


class WesternDarkMapper:
    """Western Dark Strategy Mapper — 西方暗面映射.

    Maps Western strategic traditions into structured, ethically-bounded
    strategies for defensive strategic awareness.

    Args:
        min_ethical_score: Minimum ethical score for strategies (0.0-1.0).
    """

    def __init__(self, min_ethical_score: float = 0.3) -> None:
        self.min_ethical_score = min_ethical_score

    def get_strategies(
        self,
        tradition: WesternTradition | None = None,
        category: WesternStrategyCategory | None = None,
    ) -> list[dict[str, Any]]:
        """Get Western strategies, optionally filtered.

        Args:
            tradition: Optional filter by tradition.
            category: Optional filter by category.

        Returns:
            List of strategy dictionaries.
        """
        results = []
        for s in _WESTERN_STRATEGIES:
            if s["ethical_score"] < self.min_ethical_score:
                continue
            if tradition and s["tradition"] != tradition:
                continue
            if category and s["category"] != category:
                continue
            results.append({
                "name": s["name"],
                "tradition": s["tradition"].value,
                "category": s["category"].value,
                "ethical_score": s["ethical_score"],
                "description": s["description"],
                "defense_use": s["defense_use"],
            })
        return results

    def find_strategy(self, name: str) -> dict[str, Any] | None:
        """Find a strategy by name.

        Args:
            name: The strategy name to search for.

        Returns:
            Strategy dictionary or None if not found.
        """
        for s in _WESTERN_STRATEGIES:
            if s["name"] == name:
                return {
                    "name": s["name"],
                    "tradition": s["tradition"].value,
                    "category": s["category"].value,
                    "ethical_score": s["ethical_score"],
                    "description": s["description"],
                    "defense_use": s["defense_use"],
                }
        return None

    def get_traditions(self) -> list[dict[str, str]]:
        """Get all available Western traditions.

        Returns:
            List of tradition dictionaries with name and description.
        """
        return [
            {"name": t.value, "description": t.name.replace("_", " ").title()}
            for t in WesternTradition
        ]
