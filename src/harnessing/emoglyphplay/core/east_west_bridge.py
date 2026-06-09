"""EastWestBridge — East-West Thinking Fusion Engine.

Formula: EastWest = ⊕(Linear, Systemic, Dialectic, Pratitya, Wuxing, Wuwei, Intuitive, Ubuntu)^Ξ

Fuses Western analytical thinking styles (Linear, Systemic, Dialectic) with
Eastern holistic thinking styles (Pratitya, Wuxing, Wuwei, Intuitive, Ubuntu)
to produce enriched, multi-perspective responses.
"""

from __future__ import annotations

from enum import Enum


class ThinkingStyle(Enum):
    """Enumeration of supported thinking styles."""

    LINEAR = "linear"
    SYSTEMIC = "systemic"
    DIALECTIC = "dialectic"
    PRATITYA = "pratitya"
    WUXING = "wuxing"
    WUWEI = "wuwei"
    INTUITIVE = "intuitive"
    UBUNTU = "ubuntu"


_STYLE_DESCRIPTIONS: dict[ThinkingStyle, dict[str, str]] = {
    ThinkingStyle.LINEAR: {
        "name": "Linear (Western)",
        "origin": "Western",
        "description": "Step-by-step causal reasoning; A→B→C progression.",
        "strength": "Clear causality and reproducibility.",
    },
    ThinkingStyle.SYSTEMIC: {
        "name": "Systemic (Western)",
        "origin": "Western",
        "description": "Holistic system analysis with feedback loops and emergent properties.",
        "strength": "Understanding complex interdependencies.",
    },
    ThinkingStyle.DIALECTIC: {
        "name": "Dialectic (Western)",
        "origin": "Western",
        "description": "Thesis-antithesis-synthesis; resolving contradictions through dialogue.",
        "strength": "Resolving opposing viewpoints into higher understanding.",
    },
    ThinkingStyle.PRATITYA: {
        "name": "Pratītyasamutpāda (Eastern)",
        "origin": "Eastern",
        "description": "Dependent origination; nothing exists independently, all is inter-arising.",
        "strength": "Revealing hidden dependencies and mutual causation.",
    },
    ThinkingStyle.WUXING: {
        "name": "Wu Xing 五行 (Eastern)",
        "origin": "Eastern",
        "description": "Five-phase cycle: Wood→Fire→Earth→Metal→Water with generating and overcoming cycles.",
        "strength": "Dynamic phase transitions and cyclical processes.",
    },
    ThinkingStyle.WUWEI: {
        "name": "Wu Wei 无为 (Eastern)",
        "origin": "Eastern",
        "description": "Effortless action; aligning with natural flow rather than forcing outcomes.",
        "strength": "Sustainable action without burnout or resistance.",
    },
    ThinkingStyle.INTUITIVE: {
        "name": "Intuitive (Eastern)",
        "origin": "Eastern",
        "description": "Direct knowing beyond rational analysis; insight from pattern recognition.",
        "strength": "Rapid pattern matching and creative leaps.",
    },
    ThinkingStyle.UBUNTU: {
        "name": "Ubuntu (Eastern/African)",
        "origin": "Eastern/African",
        "description": "I am because we are; communal identity and relational existence.",
        "strength": "Collective wisdom and community-centered solutions.",
    },
}

_KEYWORD_MAP: dict[str, ThinkingStyle] = {
    "cause": ThinkingStyle.LINEAR,
    "effect": ThinkingStyle.LINEAR,
    "step": ThinkingStyle.LINEAR,
    "system": ThinkingStyle.SYSTEMIC,
    "feedback": ThinkingStyle.SYSTEMIC,
    "loop": ThinkingStyle.SYSTEMIC,
    "contradiction": ThinkingStyle.DIALECTIC,
    "thesis": ThinkingStyle.DIALECTIC,
    "debate": ThinkingStyle.DIALECTIC,
    "interdependence": ThinkingStyle.PRATITYA,
    "arising": ThinkingStyle.PRATITYA,
    "dependent": ThinkingStyle.PRATITYA,
    "phase": ThinkingStyle.WUXING,
    "cycle": ThinkingStyle.WUXING,
    "element": ThinkingStyle.WUXING,
    "flow": ThinkingStyle.WUWEI,
    "effortless": ThinkingStyle.WUWEI,
    "natural": ThinkingStyle.WUWEI,
    "intuition": ThinkingStyle.INTUITIVE,
    "insight": ThinkingStyle.INTUITIVE,
    "feel": ThinkingStyle.INTUITIVE,
    "community": ThinkingStyle.UBUNTU,
    "together": ThinkingStyle.UBUNTU,
    "we": ThinkingStyle.UBUNTU,
}


class EastWestBridge:
    """EastWestBridge — East-West Thinking Fusion Engine.

    Detects the thinking style in input text and can bridge/translate
    responses between different thinking paradigms to produce enriched,
    multi-perspective outputs.
    """

    def __init__(self) -> None:
        self._style_weights: dict[ThinkingStyle, float] = {
            style: 1.0 / len(ThinkingStyle) for style in ThinkingStyle
        }

    def detect_thinking_style(self, input_text: str) -> dict:
        """Detect the dominant thinking style in the input text.

        Args:
            input_text: The text to analyze for thinking style signals.

        Returns:
            Dictionary with keys: dominant_style, confidence, style_scores.
        """
        words = input_text.lower().split()
        scores: dict[ThinkingStyle, float] = {style: 0.0 for style in ThinkingStyle}
        for word in words:
            if word in _KEYWORD_MAP:
                scores[_KEYWORD_MAP[word]] += 1.0

        total = sum(scores.values()) or 1.0
        for style in scores:
            scores[style] = scores[style] / total

        dominant = max(scores, key=lambda s: scores[s])
        confidence = scores[dominant]

        return {
            "dominant_style": dominant.value,
            "confidence": round(confidence, 3),
            "style_scores": {s.value: round(v, 3) for s, v in scores.items()},
        }

    def bridge_response(
        self,
        response: str,
        source_style: ThinkingStyle,
        target_style: ThinkingStyle,
    ) -> str:
        """Bridge a response from one thinking style to another.

        Args:
            response: The original response text.
            source_style: The thinking style of the source response.
            target_style: The target thinking style to translate into.

        Returns:
            The bridged response string.
        """
        if source_style == target_style:
            return response
        # Stub: return original with a style annotation prefix
        source_desc = _STYLE_DESCRIPTIONS[source_style]["name"]
        target_desc = _STYLE_DESCRIPTIONS[target_style]["name"]
        return f"[{source_desc} → {target_desc}] {response}"

    def integrate_perspectives(self, perspectives: list[str]) -> str:
        """Integrate multiple perspective strings into a unified response.

        Args:
            perspectives: List of perspective strings to integrate.

        Returns:
            A synthesized string combining all perspectives.
        """
        if not perspectives:
            return ""
        if len(perspectives) == 1:
            return perspectives[0]
        # Stub: join with synthesis markers
        return " ⊕ ".join(perspectives)

    def get_style_description(self, style: ThinkingStyle) -> dict:
        """Get a detailed description of a thinking style.

        Args:
            style: The ThinkingStyle to describe.

        Returns:
            Dictionary with keys: name, origin, description, strength.
        """
        return dict(_STYLE_DESCRIPTIONS[style])
