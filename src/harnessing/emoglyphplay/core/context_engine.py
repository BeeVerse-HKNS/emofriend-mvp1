"""Context Engine — Environment Sensing Engine.

Formula:
    Context = f(culture, market, law, competition, relationship_depth)

Senses the operational environment to provide context-aware routing
and strategy selection for the EmoGlyphPlay engine.

Five Context Dimensions:
    1. Culture — Cultural norms and communication styles
    2. Market — Market conditions and competitive landscape
    3. Law — Regulatory and compliance requirements
    4. Competition — Competitive dynamics and positioning
    5. Relationship Depth — Trust level and relationship maturity
"""

from __future__ import annotations

from enum import Enum
from typing import Any


class Culture(Enum):
    """Cultural context types."""

    EASTERN = "eastern"
    WESTERN = "western"
    HYBRID = "hybrid"
    GLOBAL = "global"


class MarketCondition(Enum):
    """Market condition types."""

    GROWTH = "growth"
    STABLE = "stable"
    RECESSION = "recession"
    DISRUPTION = "disruption"


class RegulatoryIntensity(Enum):
    """Regulatory intensity levels."""

    LIGHT = "light"
    MODERATE = "moderate"
    STRICT = "strict"
    RESTRICTIVE = "restrictive"


class CompetitionLevel(Enum):
    """Competition intensity levels."""

    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    INTENSE = "intense"


class RelationshipDepth(Enum):
    """Relationship depth/maturity levels."""

    STRANGER = "stranger"       # No prior interaction
    ACQUAINTANCE = "acquaintance"  # Initial contact
    COLLABORATOR = "collaborator"  # Working together
    PARTNER = "partner"          # Trusted partner
    ALLY = "ally"               # Deep strategic alliance


class ContextSnapshot:
    """A snapshot of the current operational context.

    Captures all five context dimensions at a point in time.
    """

    def __init__(
        self,
        culture: Culture = Culture.GLOBAL,
        market: MarketCondition = MarketCondition.STABLE,
        law: RegulatoryIntensity = RegulatoryIntensity.MODERATE,
        competition: CompetitionLevel = CompetitionLevel.MODERATE,
        relationship_depth: RelationshipDepth = RelationshipDepth.STRANGER,
        raw_signals: dict[str, Any] | None = None,
    ) -> None:
        self.culture = culture
        self.market = market
        self.law = law
        self.competition = competition
        self.relationship_depth = relationship_depth
        self.raw_signals = raw_signals or {}

    @property
    def risk_level(self) -> float:
        """Calculate overall risk level from 0.0 (safe) to 1.0 (dangerous).

        Higher risk = more need for Dark strategy awareness.
        """
        risk_map = {
            RegulatoryIntensity.LIGHT: 0.1,
            RegulatoryIntensity.MODERATE: 0.3,
            RegulatoryIntensity.STRICT: 0.6,
            RegulatoryIntensity.RESTRICTIVE: 0.9,
        }
        law_risk = risk_map[self.law]

        comp_map = {
            CompetitionLevel.LOW: 0.1,
            CompetitionLevel.MODERATE: 0.3,
            CompetitionLevel.HIGH: 0.6,
            CompetitionLevel.INTENSE: 0.9,
        }
        comp_risk = comp_map[self.competition]

        market_map = {
            MarketCondition.GROWTH: 0.2,
            MarketCondition.STABLE: 0.3,
            MarketCondition.RECESSION: 0.7,
            MarketCondition.DISRUPTION: 0.8,
        }
        market_risk = market_map[self.market]

        return round((law_risk + comp_risk + market_risk) / 3.0, 3)

    @property
    def needs_dark_awareness(self) -> bool:
        """Whether Dark strategy awareness is recommended."""
        return self.risk_level >= 0.4

    def to_dict(self) -> dict[str, Any]:
        return {
            "culture": self.culture.value,
            "market": self.market.value,
            "law": self.law.value,
            "competition": self.competition.value,
            "relationship_depth": self.relationship_depth.value,
            "risk_level": self.risk_level,
            "needs_dark_awareness": self.needs_dark_awareness,
        }


# Keyword-based signal detection maps
_CULTURE_KEYWORDS: dict[str, Culture] = {
    "china": Culture.EASTERN, "chinese": Culture.EASTERN,
    "japan": Culture.EASTERN, "korea": Culture.EASTERN,
    "hong kong": Culture.HYBRID, "hk": Culture.HYBRID,
    "nansha": Culture.HYBRID, "南沙": Culture.HYBRID,
    "us": Culture.WESTERN, "usa": Culture.WESTERN,
    "europe": Culture.WESTERN, "uk": Culture.WESTERN,
    "global": Culture.GLOBAL, "international": Culture.GLOBAL,
}

_MARKET_KEYWORDS: dict[str, MarketCondition] = {
    "growth": MarketCondition.GROWTH, "expanding": MarketCondition.GROWTH,
    "boom": MarketCondition.GROWTH,
    "stable": MarketCondition.STABLE, "steady": MarketCondition.STABLE,
    "recession": MarketCondition.RECESSION, "downturn": MarketCondition.RECESSION,
    "crisis": MarketCondition.RECESSION,
    "disruption": MarketCondition.DISRUPTION, "ai revolution": MarketCondition.DISRUPTION,
}

_LAW_KEYWORDS: dict[str, RegulatoryIntensity] = {
    "pipl": RegulatoryIntensity.STRICT, "gdpr": RegulatoryIntensity.STRICT,
    "compliance": RegulatoryIntensity.MODERATE,
    "regulated": RegulatoryIntensity.STRICT,
    "icp": RegulatoryIntensity.STRICT, "算法備案": RegulatoryIntensity.STRICT,
    "free": RegulatoryIntensity.LIGHT, "open": RegulatoryIntensity.LIGHT,
}

_COMPETITION_KEYWORDS: dict[str, CompetitionLevel] = {
    "monopoly": CompetitionLevel.LOW, "dominant": CompetitionLevel.LOW,
    "compete": CompetitionLevel.MODERATE, "market": CompetitionLevel.MODERATE,
    "rival": CompetitionLevel.HIGH, "race": CompetitionLevel.HIGH,
    "war": CompetitionLevel.INTENSE, "cutthroat": CompetitionLevel.INTENSE,
}

_RELATIONSHIP_KEYWORDS: dict[str, RelationshipDepth] = {
    "first": RelationshipDepth.STRANGER, "new": RelationshipDepth.STRANGER,
    "colleague": RelationshipDepth.ACQUAINTANCE,
    "collaborate": RelationshipDepth.COLLABORATOR, "team": RelationshipDepth.COLLABORATOR,
    "partner": RelationshipDepth.PARTNER, "trust": RelationshipDepth.PARTNER,
    "ally": RelationshipDepth.ALLY, "long-term": RelationshipDepth.ALLY,
}


class ContextEngine:
    """Context Engine — Environment Sensing Engine.

    Senses the operational environment from input text and explicit
    configuration to provide context-aware strategy selection.

    Args:
        default_culture: Default cultural context.
        default_law: Default regulatory intensity.
    """

    def __init__(
        self,
        default_culture: Culture = Culture.GLOBAL,
        default_law: RegulatoryIntensity = RegulatoryIntensity.MODERATE,
    ) -> None:
        self.default_culture = default_culture
        self.default_law = default_law

    def sense(
        self,
        input_text: str,
        overrides: dict[str, Any] | None = None,
    ) -> ContextSnapshot:
        """Sense the operational context from input text.

        Args:
            input_text: The text to analyze for context signals.
            overrides: Optional explicit context overrides.

        Returns:
            ContextSnapshot with detected context dimensions.
        """
        text_lower = input_text.lower()
        raw_signals: dict[str, Any] = {"input_length": len(input_text)}

        # Detect culture
        culture = self._detect_from_keywords(text_lower, _CULTURE_KEYWORDS, self.default_culture)

        # Detect market condition
        market = self._detect_from_keywords(text_lower, _MARKET_KEYWORDS, MarketCondition.STABLE)

        # Detect regulatory intensity
        law = self._detect_from_keywords(text_lower, _LAW_KEYWORDS, self.default_law)

        # Detect competition level
        competition = self._detect_from_keywords(
            text_lower, _COMPETITION_KEYWORDS, CompetitionLevel.MODERATE
        )

        # Detect relationship depth
        relationship = self._detect_from_keywords(
            text_lower, _RELATIONSHIP_KEYWORDS, RelationshipDepth.STRANGER
        )

        # Apply overrides
        if overrides:
            if "culture" in overrides:
                culture = Culture(overrides["culture"])
            if "market" in overrides:
                market = MarketCondition(overrides["market"])
            if "law" in overrides:
                law = RegulatoryIntensity(overrides["law"])
            if "competition" in overrides:
                competition = CompetitionLevel(overrides["competition"])
            if "relationship_depth" in overrides:
                relationship = RelationshipDepth(overrides["relationship_depth"])

        return ContextSnapshot(
            culture=culture,
            market=market,
            law=law,
            competition=competition,
            relationship_depth=relationship,
            raw_signals=raw_signals,
        )

    @staticmethod
    def _detect_from_keywords(
        text: str,
        keyword_map: dict[str, Any],
        default: Any,
    ) -> Any:
        """Detect a context dimension from keyword matching.

        Args:
            text: Lowercase input text.
            keyword_map: Mapping of keywords to enum values.
            default: Default value if no keywords match.

        Returns:
            The detected enum value or default.
        """
        for keyword, value in keyword_map.items():
            if keyword in text:
                return value
        return default
