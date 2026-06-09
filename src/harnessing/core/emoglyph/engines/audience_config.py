"""Audience Mode Configuration Module for EmoFriend MVP1.

Defines all mode-specific parameters for Kids Mode (童心模式, ages 5-12)
and Elderly Mode (長青模式, ages 65+).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List


class AudienceMode(Enum):
    """Supported audience modes for EmoFriend."""
    KIDS = "kids"
    ELDERLY = "elderly"


@dataclass
class AudienceConfig:
    """Mode-specific parameters for a given audience.

    Attributes:
        voice_style: TTS voice personality label.
        voice_speed: Speech rate multiplier (1.0 = normal).
        max_sentence_length: Maximum words per output sentence.
        pause_between_sentences: Seconds of silence between sentences.
        sound_effects: Whether to play UI sound effects.
        encouragement_frequency: How often to inject encouragement ("high" / "moderate").
        button_size_px: Minimum touch-target size in pixels.
        font_size_pt: Base font size in points.
        max_options_per_screen: Maximum selectable items shown at once.
        distress_threshold: Emotion intensity that triggers distress detection [0, 1].
        escalation_tier1_min: Minutes of sustained distress before tier-1 escalation.
        escalation_tier2_min: Minutes of sustained distress before tier-2 escalation.
        escalation_tier3_min: Minutes of sustained distress before tier-3 escalation.
        escalation_target: Who is contacted on escalation ("parent" / "family").
        active_engines: List of engine names enabled for this mode.
        emotion_count: Number of emotions in the mode's emotion set.
        emotion_set: Ordered list of emotion labels available.
        emo_character: Mascot character identifier.
        emo_character_emoji: Unicode emoji for the mascot.
        breathing_game_type: Type of guided breathing exercise.
        breathing_cycle_seconds: Duration of one inhale-exhale cycle in seconds.
        stress_breathing_threshold: Distress level above which breathing is suggested [0, 1].
        data_retention_days: How many days to retain session data.
        store_raw_sensor_data: Whether to persist raw sensor readings.
        physical_health_monitoring: Whether to monitor physical health metrics.
        fall_detection: Whether to enable fall-detection alerts.
        circadian_monitoring: Whether to track circadian rhythm patterns.
        keystroke_tracking: Whether to collect keystroke dynamics.
        parent_pin_required: Whether a parent PIN is needed to exit/modify settings.
        family_contact_required: Whether a family contact must be on file.
    """

    voice_style: str = ""
    voice_speed: float = 1.0
    max_sentence_length: int = 15
    pause_between_sentences: float = 1.0
    sound_effects: bool = True
    encouragement_frequency: str = "moderate"
    button_size_px: int = 48
    font_size_pt: int = 16
    max_options_per_screen: int = 5
    distress_threshold: float = 0.4
    escalation_tier1_min: float = 3.0
    escalation_tier2_min: float = 7.0
    escalation_tier3_min: float = 10.0
    escalation_target: str = "parent"
    active_engines: List[str] = field(default_factory=list)
    emotion_count: int = 5
    emotion_set: List[str] = field(default_factory=list)
    emo_character: str = ""
    emo_character_emoji: str = ""
    breathing_game_type: str = ""
    breathing_cycle_seconds: float = 7.0
    stress_breathing_threshold: float = 0.65
    data_retention_days: int = 90
    store_raw_sensor_data: bool = False
    physical_health_monitoring: bool = False
    fall_detection: bool = False
    circadian_monitoring: bool = False
    keystroke_tracking: bool = False
    parent_pin_required: bool = False
    family_contact_required: bool = False

    def __post_init__(self) -> None:
        if not 0.0 <= self.distress_threshold <= 1.0:
            raise ValueError(
                f"distress_threshold={self.distress_threshold} out of [0, 1]"
            )
        if self.voice_speed <= 0:
            raise ValueError(
                f"voice_speed={self.voice_speed} must be > 0"
            )
        if self.max_sentence_length < 1:
            raise ValueError(
                f"max_sentence_length={self.max_sentence_length} must be >= 1"
            )
        if self.pause_between_sentences < 0:
            raise ValueError(
                f"pause_between_sentences={self.pause_between_sentences} must be >= 0"
            )
        if self.button_size_px < 1:
            raise ValueError(
                f"button_size_px={self.button_size_px} must be >= 1"
            )
        if self.font_size_pt < 1:
            raise ValueError(
                f"font_size_pt={self.font_size_pt} must be >= 1"
            )
        if self.max_options_per_screen < 1:
            raise ValueError(
                f"max_options_per_screen={self.max_options_per_screen} must be >= 1"
            )
        if self.escalation_tier1_min < 0:
            raise ValueError(
                f"escalation_tier1_min={self.escalation_tier1_min} must be >= 0"
            )
        if self.escalation_tier2_min < self.escalation_tier1_min:
            raise ValueError(
                f"escalation_tier2_min={self.escalation_tier2_min} must be >= escalation_tier1_min"
            )
        if self.escalation_tier3_min < self.escalation_tier2_min:
            raise ValueError(
                f"escalation_tier3_min={self.escalation_tier3_min} must be >= escalation_tier2_min"
            )
        if not 0.0 <= self.stress_breathing_threshold <= 1.0:
            raise ValueError(
                f"stress_breathing_threshold={self.stress_breathing_threshold} out of [0, 1]"
            )
        if self.breathing_cycle_seconds <= 0:
            raise ValueError(
                f"breathing_cycle_seconds={self.breathing_cycle_seconds} must be > 0"
            )
        if self.data_retention_days < 1:
            raise ValueError(
                f"data_retention_days={self.data_retention_days} must be >= 1"
            )
        if len(self.emotion_set) != self.emotion_count:
            raise ValueError(
                f"emotion_set length {len(self.emotion_set)} != emotion_count {self.emotion_count}"
            )


# ---------------------------------------------------------------------------
# Pre-built configs
# ---------------------------------------------------------------------------

KIDS_CONFIG = AudienceConfig(
    voice_style="playful",
    voice_speed=1.2,
    max_sentence_length=10,
    pause_between_sentences=0.5,
    sound_effects=True,
    encouragement_frequency="high",
    button_size_px=48,
    font_size_pt=18,
    max_options_per_screen=3,
    distress_threshold=0.3,
    escalation_tier1_min=2.0,
    escalation_tier2_min=5.0,
    escalation_tier3_min=8.0,
    escalation_target="parent",
    active_engines=["mouth", "ear", "eye", "sense", "friendship", "sharing"],
    emotion_count=5,
    emotion_set=["happy", "sad", "angry", "scared", "loved"],
    emo_character="bee",
    emo_character_emoji="🐝",
    breathing_game_type="bubble",
    breathing_cycle_seconds=5.0,
    stress_breathing_threshold=0.6,
    data_retention_days=30,
    store_raw_sensor_data=False,
    physical_health_monitoring=False,
    fall_detection=False,
    circadian_monitoring=False,
    keystroke_tracking=False,
    parent_pin_required=True,
    family_contact_required=False,
)

ELDERLY_CONFIG = AudienceConfig(
    voice_style="warm_slow",
    voice_speed=0.7,
    max_sentence_length=20,
    pause_between_sentences=1.5,
    sound_effects=False,
    encouragement_frequency="moderate",
    button_size_px=56,
    font_size_pt=20,
    max_options_per_screen=5,
    distress_threshold=0.5,
    escalation_tier1_min=5.0,
    escalation_tier2_min=10.0,
    escalation_tier3_min=15.0,
    escalation_target="family",
    active_engines=["mouth", "ear", "heart", "body", "sense", "friendship", "therapy"],
    emotion_count=7,
    emotion_set=["happy", "sad", "angry", "scared", "calm", "lonely", "loved"],
    emo_character="ember",
    emo_character_emoji="🕯️",
    breathing_game_type="calm_counting",
    breathing_cycle_seconds=10.0,
    stress_breathing_threshold=0.7,
    data_retention_days=365,
    store_raw_sensor_data=True,
    physical_health_monitoring=True,
    fall_detection=True,
    circadian_monitoring=True,
    keystroke_tracking=False,
    parent_pin_required=False,
    family_contact_required=True,
)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

_CONFIG_MAP = {
    AudienceMode.KIDS: KIDS_CONFIG,
    AudienceMode.ELDERLY: ELDERLY_CONFIG,
}


def get_config(mode: AudienceMode) -> AudienceConfig:
    """Return the pre-built AudienceConfig for the given mode.

    Args:
        mode: The target audience mode.

    Returns:
        The corresponding AudienceConfig instance.

    Raises:
        ValueError: If *mode* is not a recognised AudienceMode value.
    """
    if not isinstance(mode, AudienceMode):
        raise TypeError(f"mode must be an AudienceMode, got {type(mode).__name__}")
    config = _CONFIG_MAP.get(mode)
    if config is None:
        raise ValueError(f"no config registered for mode {mode!r}")
    return config
