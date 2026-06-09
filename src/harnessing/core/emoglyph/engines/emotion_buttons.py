"""Emotion Button Component for EmoFriend MVP1.

Provides large, emoji-based emotion selector buttons as the primary
non-verbal input method for kids and elderly users.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from .audience_config import AudienceMode
from ..pulse import Pulse, PulseType


@dataclass(frozen=True)
class EmotionButton:
    """A single emoji-based emotion selector button.

    Attributes:
        emoji: The emoji character displayed on the button.
        label: Text label (e.g., "Happy", "開心").
        panksepp_system: Which Panksepp affective system this maps to.
        valence: VAD valence value in [-1, 1].
        arousal: VAD arousal value in [-1, 1].
        dominance: VAD dominance value in [-1, 1].
        basic_emotion: Simple emotion name (happy, sad, angry, scared, loved, calm, lonely).
    """

    emoji: str
    label: str
    panksepp_system: PulseType
    valence: float
    arousal: float
    dominance: float
    basic_emotion: str


# ---------------------------------------------------------------------------
# Pre-built button sets
# ---------------------------------------------------------------------------

KIDS_EMOTION_BUTTONS: List[EmotionButton] = [
    EmotionButton(emoji="😊", label="Happy", panksepp_system=PulseType.PLAY, valence=0.7, arousal=0.5, dominance=0.5, basic_emotion="happy"),
    EmotionButton(emoji="😢", label="Sad", panksepp_system=PulseType.PANIC, valence=-0.6, arousal=0.2, dominance=-0.3, basic_emotion="sad"),
    EmotionButton(emoji="😠", label="Angry", panksepp_system=PulseType.RAGE, valence=-0.7, arousal=0.8, dominance=0.6, basic_emotion="angry"),
    EmotionButton(emoji="😨", label="Scared", panksepp_system=PulseType.FEAR, valence=-0.6, arousal=0.7, dominance=-0.5, basic_emotion="scared"),
    EmotionButton(emoji="🥰", label="Loved", panksepp_system=PulseType.CARE, valence=0.8, arousal=0.3, dominance=0.2, basic_emotion="loved"),
]

ELDERLY_EMOTION_BUTTONS: List[EmotionButton] = [
    EmotionButton(emoji="😊", label="開心", panksepp_system=PulseType.PLAY, valence=0.7, arousal=0.5, dominance=0.5, basic_emotion="happy"),
    EmotionButton(emoji="😢", label="難過", panksepp_system=PulseType.PANIC, valence=-0.6, arousal=0.2, dominance=-0.3, basic_emotion="sad"),
    EmotionButton(emoji="😠", label="生氣", panksepp_system=PulseType.RAGE, valence=-0.7, arousal=0.8, dominance=0.6, basic_emotion="angry"),
    EmotionButton(emoji="😨", label="擔心", panksepp_system=PulseType.FEAR, valence=-0.6, arousal=0.7, dominance=-0.5, basic_emotion="scared"),
    EmotionButton(emoji="😌", label="平靜", panksepp_system=PulseType.SEEKING, valence=0.3, arousal=0.2, dominance=0.3, basic_emotion="calm"),
    EmotionButton(emoji="😔", label="孤單", panksepp_system=PulseType.PANIC, valence=-0.5, arousal=0.1, dominance=-0.4, basic_emotion="lonely"),
    EmotionButton(emoji="🥰", label="溫暖", panksepp_system=PulseType.CARE, valence=0.8, arousal=0.3, dominance=0.2, basic_emotion="loved"),
]


# ---------------------------------------------------------------------------
# Conversion helpers
# ---------------------------------------------------------------------------

def emotion_to_pulse(button: EmotionButton) -> Pulse:
    """Create a Pulse from an EmotionButton's Panksepp system and VAD values.

    Args:
        button: The EmotionButton to convert.

    Returns:
        A Pulse with the button's affective parameters and a default
        intensity of 0.7.
    """
    return Pulse(
        pulse_type=button.panksepp_system,
        valence=button.valence,
        arousal=button.arousal,
        dominance=button.dominance,
        intensity=0.7,
    )


def get_buttons_for_mode(mode: AudienceMode) -> List[EmotionButton]:
    """Return the emotion button list for the given audience mode.

    Args:
        mode: The target audience mode.

    Returns:
        KIDS_EMOTION_BUTTONS for KIDS mode, ELDERLY_EMOTION_BUTTONS for ELDERLY.
    """
    if mode is AudienceMode.KIDS:
        return KIDS_EMOTION_BUTTONS
    return ELDERLY_EMOTION_BUTTONS


def find_button_by_emoji(emoji: str, mode: AudienceMode) -> Optional[EmotionButton]:
    """Search the button list for the matching emoji.

    Args:
        emoji: The emoji character to look up.
        mode: The audience mode whose button list to search.

    Returns:
        The matching EmotionButton, or None if not found.
    """
    for button in get_buttons_for_mode(mode):
        if button.emoji == emoji:
            return button
    return None
