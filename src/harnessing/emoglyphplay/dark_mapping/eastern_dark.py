"""Eastern Dark Strategy Mapper — 東方暗面映射.

Maps Eastern strategic traditions into a structured framework:
    - 三十六計 (36 Stratagems): Tactical deception and competition strategies
    - 韓非子 (Han Feizi): Legalist governance — 法術勢
    - 鬼谷子 (Guiguzi): Persuasion and negotiation — 捭闔
    - 孫子兵法 (Art of War): Strategic warfare — 虛實/奇正

Each strategy is classified with:
    - Ethical score (0.0-1.0)
    - Appropriate use context (defense/competition/negotiation)
    - Source text and tradition
"""

from __future__ import annotations

from enum import Enum
from typing import Any


class EasternTradition(Enum):
    """Eastern strategic traditions."""

    THIRTY_SIX_STRATAGEMS = "三十六計"
    HAN_FEIZI = "韓非子"
    GUIGUZI = "鬼谷子"
    SUN_TZU = "孫子兵法"


class EasternStrategyCategory(Enum):
    """Categories of Eastern strategies."""

    DECEPTION = "deception"         # 虛實 — Strategic deception
    GOVERNANCE = "governance"       # 法術勢 — Organizational power
    PERSUASION = "persuasion"       # 捭闔 — Opening and closing
    TACTICS = "tactics"             # 奇正 — Conventional and unconventional
    PATIENCE = "patience"           # 欲擒故縱 — Strategic patience
    INTELLIGENCE = "intelligence"   # 知己知彼 — Information gathering
    POSITIONING = "positioning"     # 勢 — Positioning for advantage
    ADAPTATION = "adaptation"       # 變 — Adapting to circumstances


# Eastern strategy catalog with ethical scores
_EASTERN_STRATEGIES: list[dict[str, Any]] = [
    # 三十六計 — Deception & Tactics
    {"name": "瞞天過海", "tradition": EasternTradition.THIRTY_SIX_STRATAGEMS,
     "category": EasternStrategyCategory.DECEPTION, "ethical_score": 0.3,
     "description": "Cross the sea under camouflage — conceal true intentions behind ordinary appearance.",
     "defense_use": "Detect when others are concealing their true intentions from you."},
    {"name": "圍魏救趙", "tradition": EasternTradition.THIRTY_SIX_STRATAGEMS,
     "category": EasternStrategyCategory.TACTICS, "ethical_score": 0.7,
     "description": "Relieve the siege of Zhao by attacking Wei — solve problems indirectly.",
     "defense_use": "Address root causes rather than symptoms in competitive defense."},
    {"name": "借刀殺人", "tradition": EasternTradition.THIRTY_SIX_STRATAGEMS,
     "category": EasternStrategyCategory.DECEPTION, "ethical_score": 0.2,
     "description": "Kill with a borrowed knife — use third parties to achieve objectives.",
     "defense_use": "Detect when competitors are using proxies against you."},
    {"name": "以逸待勞", "tradition": EasternTradition.THIRTY_SIX_STRATAGEMS,
     "category": EasternStrategyCategory.POSITIONING, "ethical_score": 0.8,
     "description": "Wait at ease for the exhausted enemy — conserve energy while opponents tire.",
     "defense_use": "Let competitors exhaust resources while you build sustainably."},
    {"name": "聲東擊西", "tradition": EasternTradition.THIRTY_SIX_STRATAGEMS,
     "category": EasternStrategyCategory.DECEPTION, "ethical_score": 0.35,
     "description": "Make noise in the east, strike in the west — misdirect attention.",
     "defense_use": "Detect misdirection in competitive announcements and press releases."},
    {"name": "暗度陳倉", "tradition": EasternTradition.THIRTY_SIX_STRATAGEMS,
     "category": EasternStrategyCategory.TACTICS, "ethical_score": 0.4,
     "description": "Secretly cross at Chencang — advance while appearing inactive.",
     "defense_use": "Monitor competitors' quiet moves behind public statements."},
    {"name": "欲擒故縱", "tradition": EasternTradition.THIRTY_SIX_STRATAGEMS,
     "category": EasternStrategyCategory.PATIENCE, "ethical_score": 0.6,
     "description": "Let the enemy off to capture them later — strategic patience.",
     "defense_use": "Don't overreact to competitive moves; wait for the right moment."},
    # 韓非子 — Governance
    {"name": "法 (Law)", "tradition": EasternTradition.HAN_FEIZI,
     "category": EasternStrategyCategory.GOVERNANCE, "ethical_score": 0.8,
     "description": "Clear rules and transparent enforcement — the foundation of order.",
     "defense_use": "Establish clear boundaries and rules to prevent exploitation."},
    {"name": "術 (Method)", "tradition": EasternTradition.HAN_FEIZI,
     "category": EasternStrategyCategory.GOVERNANCE, "ethical_score": 0.5,
     "description": "Management techniques — methods for maintaining organizational control.",
     "defense_use": "Understand organizational dynamics to protect team interests."},
    {"name": "勢 (Power)", "tradition": EasternTradition.HAN_FEIZI,
     "category": EasternStrategyCategory.POSITIONING, "ethical_score": 0.5,
     "description": "Power dynamics and positioning — leveraging structural advantages.",
     "defense_use": "Recognize power dynamics to navigate organizational politics ethically."},
    # 鬼谷子 — Persuasion
    {"name": "捭 (Open)", "tradition": EasternTradition.GUIGUZI,
     "category": EasternStrategyCategory.PERSUASION, "ethical_score": 0.7,
     "description": "Opening — probing and revealing information through dialogue.",
     "defense_use": "Use open questions to understand others' true positions."},
    {"name": "闔 (Close)", "tradition": EasternTradition.GUIGUZI,
     "category": EasternStrategyCategory.PERSUASION, "ethical_score": 0.6,
     "description": "Closing — withholding and protecting information strategically.",
     "defense_use": "Know when to protect sensitive information in negotiations."},
    {"name": "飛箝", "tradition": EasternTradition.GUIGUZI,
     "category": EasternStrategyCategory.PERSUASION, "ethical_score": 0.4,
     "description": "Flying clamp — praise then control; influence through validation.",
     "defense_use": "Detect when others use flattery to manipulate you."},
    # 孫子兵法 — Strategic Warfare
    {"name": "虛實", "tradition": EasternTradition.SUN_TZU,
     "category": EasternStrategyCategory.DECEPTION, "ethical_score": 0.45,
     "description": "Deception and reality — appear weak when strong, strong when weak.",
     "defense_use": "Analyze competitors' public signals vs. actual capabilities."},
    {"name": "奇正", "tradition": EasternTradition.SUN_TZU,
     "category": EasternStrategyCategory.TACTICS, "ethical_score": 0.7,
     "description": "Conventional and unconventional — combine expected and surprise moves.",
     "defense_use": "Prepare for both expected and unexpected competitive moves."},
    {"name": "知己知彼", "tradition": EasternTradition.SUN_TZU,
     "category": EasternStrategyCategory.INTELLIGENCE, "ethical_score": 0.9,
     "description": "Know yourself and know your enemy — information is power.",
     "defense_use": "Conduct thorough competitive analysis and self-assessment."},
    {"name": "不戰而屈人之兵", "tradition": EasternTradition.SUN_TZU,
     "category": EasternStrategyCategory.POSITIONING, "ethical_score": 0.85,
     "description": "Subdue the enemy without fighting — win through superior positioning.",
     "defense_use": "Build such strong positioning that competition becomes unnecessary."},
]


class EasternDarkMapper:
    """Eastern Dark Strategy Mapper — 東方暗面映射.

    Maps Eastern strategic traditions into structured, ethically-bounded
    strategies for defensive strategic awareness.

    Args:
        min_ethical_score: Minimum ethical score for strategies (0.0-1.0).
    """

    def __init__(self, min_ethical_score: float = 0.3) -> None:
        self.min_ethical_score = min_ethical_score

    def get_strategies(
        self,
        tradition: EasternTradition | None = None,
        category: EasternStrategyCategory | None = None,
    ) -> list[dict[str, Any]]:
        """Get Eastern strategies, optionally filtered.

        Args:
            tradition: Optional filter by tradition.
            category: Optional filter by category.

        Returns:
            List of strategy dictionaries.
        """
        results = []
        for s in _EASTERN_STRATEGIES:
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
        for s in _EASTERN_STRATEGIES:
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
        """Get all available Eastern traditions.

        Returns:
            List of tradition dictionaries with name and description.
        """
        return [
            {"name": t.value, "description": t.name.replace("_", " ").title()}
            for t in EasternTradition
        ]
