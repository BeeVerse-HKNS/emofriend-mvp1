"""Family Dashboard Module for EmoFriend MVP1.

Provides emotional wellness summaries for parents (kids mode) and family
members (elderly mode) without exposing raw sensor data.

Design principles:
- Self-contained, no external dependencies beyond stdlib
- Never expose raw sensor data or Panksepp terminology to families
- Mode-aware: English for kids/parents, Chinese for elderly/family
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List

from .audience_config import AudienceMode
from .emotional_profile import EmotionalSnapshot


# ---------------------------------------------------------------------------
# Panksepp → plain-language wellness label mapping
# ---------------------------------------------------------------------------

PANKSEPP_TO_WELLNESS_LABEL: dict[str, str] = {
    "PLAY": "happy and playful",
    "CARE": "warm and connected",
    "SEEKING": "curious and engaged",
    "FEAR": "worried or anxious",
    "RAGE": "frustrated or upset",
    "PANIC": "sad or lonely",
    "LUST": "energized",
    "NEUTRAL": "calm",
}


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class WellnessSummary:
    """Aggregated emotional wellness summary for family members.

    Attributes:
        score: Wellness score 1-10 (10 = best).
        trend: Whether wellness is improving, stable, or declining.
        dominant_emotion_label: Simple plain-language emotion label.
        key_events: Recent notable events described in plain language.
        recommendations: Actionable suggestions for family.
        period: Aggregation period ("daily" or "weekly").
        timestamp: When this summary was generated.
    """

    score: float
    trend: str
    dominant_emotion_label: str
    key_events: List[str]
    recommendations: List[str]
    period: str
    timestamp: datetime


@dataclass
class SafetyEventLog:
    """A safety-relevant event recorded for family notification.

    Attributes:
        event_type: Category of safety event.
        severity: Severity level.
        description: Plain-language description (no raw data).
        action_taken: What action was already taken.
        timestamp: When the event occurred.
    """

    event_type: str
    severity: str
    description: str
    action_taken: str
    timestamp: datetime


# ---------------------------------------------------------------------------
# Mode-specific recommendations
# ---------------------------------------------------------------------------

_KIDS_RECOMMENDATIONS: List[str] = [
    "Ask about their day",
    "Try a fun activity together",
    "Listen without judging",
]

_ELDERLY_RECOMMENDATIONS: List[str] = [
    "打個電話問候",
    "建議一起散步",
    "留意睡眠品質",
]


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------

def generate_wellness_summary(
    snapshots: List[EmotionalSnapshot],
    mode: AudienceMode,
    period: str = "daily",
) -> WellnessSummary:
    """Generate a wellness summary from a list of emotional snapshots.

    Args:
        snapshots: Ordered list of emotional snapshots (chronological).
        mode: Audience mode (KIDS or ELDERLY).
        period: Aggregation period, "daily" or "weekly".

    Returns:
        A WellnessSummary with score, trend, and recommendations.
    """
    now = datetime.now()

    if not snapshots:
        recommendations = (
            list(_KIDS_RECOMMENDATIONS)
            if mode == AudienceMode.KIDS
            else list(_ELDERLY_RECOMMENDATIONS)
        )
        return WellnessSummary(
            score=5.0,
            trend="stable",
            dominant_emotion_label="calm",
            key_events=[],
            recommendations=recommendations,
            period=period,
            timestamp=now,
        )

    # --- Wellness score from average valence ---
    avg_valence = sum(s.valence for s in snapshots) / len(snapshots)
    score = round((avg_valence + 1) * 5, 1)
    score = max(1.0, min(10.0, score))

    # --- Trend: compare recent half vs earlier half ---
    mid = len(snapshots) // 2
    if mid == 0:
        trend = "stable"
    else:
        earlier = snapshots[:mid]
        recent = snapshots[mid:]
        avg_earlier = sum(s.valence for s in earlier) / len(earlier)
        avg_recent = sum(s.valence for s in recent) / len(recent)
        diff = avg_recent - avg_earlier
        if diff > 0.1:
            trend = "improving"
        elif diff < -0.1:
            trend = "declining"
        else:
            trend = "stable"

    # --- Dominant emotion label ---
    emotion_counts: dict[str, int] = {}
    for s in snapshots:
        emotion_counts[s.dominant_emotion] = emotion_counts.get(s.dominant_emotion, 0) + 1
    most_frequent = max(emotion_counts, key=emotion_counts.get)  # type: ignore[arg-type]
    dominant_emotion_label = PANKSEPP_TO_WELLNESS_LABEL.get(most_frequent, "calm")

    # --- Key events: strong emotions ---
    key_events: List[str] = []
    for s in snapshots:
        if s.intensity > 0.8:
            label = PANKSEPP_TO_WELLNESS_LABEL.get(s.dominant_emotion, s.dominant_emotion)
            event_text = f"Strong {label} detected"
            if event_text not in key_events:
                key_events.append(event_text)

    # --- Recommendations based on mode ---
    recommendations = (
        list(_KIDS_RECOMMENDATIONS)
        if mode == AudienceMode.KIDS
        else list(_ELDERLY_RECOMMENDATIONS)
    )

    return WellnessSummary(
        score=score,
        trend=trend,
        dominant_emotion_label=dominant_emotion_label,
        key_events=key_events,
        recommendations=recommendations,
        period=period,
        timestamp=now,
    )


def generate_family_notification_text(
    summary: WellnessSummary,
    mode: AudienceMode,
    user_name: str = "Your loved one",
) -> str:
    """Generate a human-readable notification text for family members.

    Args:
        summary: The wellness summary to describe.
        mode: Audience mode (determines language).
        user_name: Name to use in the notification.

    Returns:
        A notification string in English (kids) or Chinese (elderly).
    """
    if mode == AudienceMode.KIDS:
        text = (
            f"{user_name} seems to be feeling {summary.dominant_emotion_label} "
            f"lately. Wellness score: {summary.score}/10. "
            f"{summary.recommendations[0]}"
        )
        if summary.trend == "declining":
            text += " Their emotional wellness has been declining. Extra attention may help."
        return text
    else:
        text = (
            f"{user_name} 近期的情緒狀態：{summary.dominant_emotion_label}。"
            f"健康指數：{summary.score}/10。"
            f"{summary.recommendations[0]}"
        )
        if summary.trend == "declining":
            text += " 情緒狀態有下降趨勢，建議多加關注。"
        return text


def create_safety_event(
    event_type: str,
    severity: str,
    description: str,
    action_taken: str,
) -> SafetyEventLog:
    """Factory function to create a SafetyEventLog.

    Args:
        event_type: One of the defined safety event types.
        severity: One of "LOW", "MEDIUM", "HIGH", "CRITICAL".
        description: Plain-language description.
        action_taken: What action was already taken.

    Returns:
        A SafetyEventLog instance.
    """
    return SafetyEventLog(
        event_type=event_type,
        severity=severity,
        description=description,
        action_taken=action_taken,
        timestamp=datetime.now(),
    )
