"""EmoMouth (口) Expressive Output Engine — 口之表達輸出引擎

七竅 (Seven Apertures) 多模態感官系統 — EmoFriend 情感健康產品

TCM Organ: 脾 (Spleen)
Panksepp Systems: PLAY / RAGE

3-in-1 capabilities:
1. Emotional Speech Synthesis — multilingual TTS with emotional tone
2. Silence-as-Speech — MA/MU/ZEN silence generation
3. Guided Breathing Audio — respiration-guided audio for anxiety relief

This is an OUTPUT engine: converts FROM Pulse/state TO audio output.
Backends are abstract interfaces only — no external dependencies.

EmoGlyph 整合點: Pulse Layer → Audio Output
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Union

from ..pulse import Pulse, PulseType
from .audience_config import AudienceMode, AudienceConfig, get_config


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clamp(value: float, lo: float, hi: float) -> float:
    """Clamp a float value to [lo, hi] range."""
    return max(lo, min(hi, value))


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class SilenceType(Enum):
    """沉默類型 — Silence-as-Speech modes

    MA: Deep reflection — soft breath + 3-5s silence
    MU: Gentle acknowledgment — soft "嗯" + 2-3s silence
    ZEN: Shared presence — ambient nature + 5-10s
    """
    MA = "MA"
    MU = "MU"
    ZEN = "ZEN"


class BreathingPattern(Enum):
    """呼吸模式 — Guided breathing patterns

    FOUR_SEVEN_EIGHT: Inhale 4s, Hold 7s, Exhale 8s — anxiety relief
    BOX: Inhale 4s, Hold 4s, Exhale 4s — focus/calm
    COHERENT: Inhale 5s, Exhale 5s — HRV optimization
    """
    FOUR_SEVEN_EIGHT = "4-7-8"
    BOX = "box"
    COHERENT = "coherent"


# ---------------------------------------------------------------------------
# Silence & Breathing Configuration Constants
# ---------------------------------------------------------------------------

SILENCE_CONFIGS: Dict[SilenceType, Dict] = {
    SilenceType.MA: {
        "default_duration": 4.0,
        "min_duration": 3.0,
        "max_duration": 5.0,
        "description": "Deep reflection silence",
        "description_zh": "深度反思沉默",
    },
    SilenceType.MU: {
        "default_duration": 2.5,
        "min_duration": 2.0,
        "max_duration": 3.0,
        "description": "Gentle acknowledgment silence",
        "description_zh": "溫柔認可沉默",
    },
    SilenceType.ZEN: {
        "default_duration": 7.5,
        "min_duration": 5.0,
        "max_duration": 10.0,
        "description": "Shared presence silence",
        "description_zh": "共在沉默",
    },
}


@dataclass
class BreathingPhase:
    """呼吸階段 — A single phase in a breathing pattern

    phase: "inhale", "hold", or "exhale"
    duration: seconds for this phase
    """
    phase: str
    duration: float

    def __post_init__(self) -> None:
        valid_phases = {"inhale", "hold", "exhale"}
        if self.phase not in valid_phases:
            raise ValueError(
                f"phase must be one of {valid_phases}, got '{self.phase}'"
            )
        if not isinstance(self.duration, (int, float)):
            raise TypeError(
                f"duration must be numeric, got {type(self.duration).__name__}"
            )
        if self.duration <= 0:
            raise ValueError(f"duration must be positive, got {self.duration}")

    def to_dict(self) -> Dict:
        """Serialize to dictionary."""
        return {"phase": self.phase, "duration": self.duration}

    @classmethod
    def from_dict(cls, data: Dict) -> BreathingPhase:
        """Deserialize from dictionary."""
        return cls(phase=data["phase"], duration=data["duration"])


BREATHING_PATTERNS: Dict[BreathingPattern, List[BreathingPhase]] = {
    BreathingPattern.FOUR_SEVEN_EIGHT: [
        BreathingPhase("inhale", 4.0),
        BreathingPhase("hold", 7.0),
        BreathingPhase("exhale", 8.0),
    ],
    BreathingPattern.BOX: [
        BreathingPhase("inhale", 4.0),
        BreathingPhase("hold", 4.0),
        BreathingPhase("exhale", 4.0),
    ],
    BreathingPattern.COHERENT: [
        BreathingPhase("inhale", 5.0),
        BreathingPhase("exhale", 5.0),
    ],
}

# Voice style → Panksepp system mapping
VOICE_STYLE_PANKSEPP: Dict[str, PulseType] = {
    "warm": PulseType.CARE,
    "gentle": PulseType.CARE,
    "playful": PulseType.PLAY,
    "calm": PulseType.SEEKING,
}

# Valid language codes
VALID_LANGUAGES = {"zh-CN", "zh-HK", "en", "ja", "ko"}

# Valid voice styles
VALID_VOICE_STYLES = {"warm", "gentle", "playful", "calm"}


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class EmoMouthConfig:
    """口之配置 — EmoMouth output configuration

    language: target language code (zh-CN, zh-HK, en, ja, ko)
    voice_style: voice personality (warm, gentle, playful, calm)
    emotional_tone: Panksepp system name for emotional coloring
    speed: speech rate multiplier (0.5 - 2.0)
    silence_type: optional silence mode to apply
    """
    language: str
    voice_style: str
    emotional_tone: str
    speed: float
    silence_type: Optional[SilenceType] = None

    def __post_init__(self) -> None:
        if self.language not in VALID_LANGUAGES:
            raise ValueError(
                f"language must be one of {VALID_LANGUAGES}, got '{self.language}'"
            )
        if self.voice_style not in VALID_VOICE_STYLES:
            raise ValueError(
                f"voice_style must be one of {VALID_VOICE_STYLES}, "
                f"got '{self.voice_style}'"
            )
        valid_tones = {pt.name for pt in PulseType}
        if self.emotional_tone not in valid_tones:
            raise ValueError(
                f"emotional_tone must be a PulseType name "
                f"({sorted(valid_tones)}), got '{self.emotional_tone}'"
            )
        if not isinstance(self.speed, (int, float)):
            raise TypeError(
                f"speed must be numeric, got {type(self.speed).__name__}"
            )
        self.speed = _clamp(float(self.speed), 0.5, 2.0)

    def to_dict(self) -> Dict:
        """Serialize to dictionary."""
        return {
            "language": self.language,
            "voice_style": self.voice_style,
            "emotional_tone": self.emotional_tone,
            "speed": self.speed,
            "silence_type": self.silence_type.value if self.silence_type else None,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> EmoMouthConfig:
        """Deserialize from dictionary."""
        silence_type = None
        if data.get("silence_type"):
            silence_type = SilenceType(data["silence_type"])
        return cls(
            language=data["language"],
            voice_style=data["voice_style"],
            emotional_tone=data["emotional_tone"],
            speed=data["speed"],
            silence_type=silence_type,
        )


@dataclass
class EmoMouthResult:
    """口之結果 — EmoMouth output result

    audio_data: generated audio bytes (placeholder in core engine)
    sample_rate: audio sample rate in Hz
    duration_seconds: total audio duration
    emotional_tone: Panksepp system name used
    language: language code used
    silence_applied: silence type applied, if any
    breathing_pattern: breathing pattern used, if any
    timestamp: when this result was generated
    """
    audio_data: bytes
    sample_rate: int
    duration_seconds: float
    emotional_tone: str
    language: str
    silence_applied: Optional[SilenceType]
    breathing_pattern: Optional[BreathingPattern]
    timestamp: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.audio_data, bytes):
            raise TypeError(
                f"audio_data must be bytes, got {type(self.audio_data).__name__}"
            )
        if not isinstance(self.sample_rate, int) or self.sample_rate <= 0:
            raise ValueError(
                f"sample_rate must be a positive integer, got {self.sample_rate}"
            )
        if not isinstance(self.duration_seconds, (int, float)):
            raise TypeError(
                f"duration_seconds must be numeric, "
                f"got {type(self.duration_seconds).__name__}"
            )
        if self.duration_seconds < 0:
            raise ValueError(
                f"duration_seconds must be non-negative, "
                f"got {self.duration_seconds}"
            )
        if not isinstance(self.timestamp, datetime):
            raise TypeError(
                f"timestamp must be datetime, "
                f"got {type(self.timestamp).__name__}"
            )

    def to_dict(self) -> Dict:
        """Serialize to dictionary.

        Note: audio_data is represented as its byte length since
        raw bytes are not JSON-serializable.
        """
        return {
            "audio_data_length": len(self.audio_data),
            "sample_rate": self.sample_rate,
            "duration_seconds": self.duration_seconds,
            "emotional_tone": self.emotional_tone,
            "language": self.language,
            "silence_applied": (
                self.silence_applied.value if self.silence_applied else None
            ),
            "breathing_pattern": (
                self.breathing_pattern.value if self.breathing_pattern else None
            ),
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict) -> EmoMouthResult:
        """Deserialize from dictionary.

        Note: audio_data is reconstructed as empty bytes with the
        original length, since raw audio cannot be stored in JSON.
        """
        silence_applied = None
        if data.get("silence_applied"):
            silence_applied = SilenceType(data["silence_applied"])

        breathing_pattern = None
        if data.get("breathing_pattern"):
            breathing_pattern = BreathingPattern(data["breathing_pattern"])

        return cls(
            audio_data=b"\x00" * data.get("audio_data_length", 0),
            sample_rate=data["sample_rate"],
            duration_seconds=data["duration_seconds"],
            emotional_tone=data["emotional_tone"],
            language=data["language"],
            silence_applied=silence_applied,
            breathing_pattern=breathing_pattern,
            timestamp=datetime.fromisoformat(data["timestamp"]),
        )


# ---------------------------------------------------------------------------
# Audience Voice Profiles
# ---------------------------------------------------------------------------

@dataclass
class KidsVoiceProfile:
    """童心語音配置 — Voice profile adapted for children (ages 5-12).

    speed: speech rate multiplier (faster, energetic)
    style: voice personality label
    max_sentence_length: maximum words per sentence
    pause_between_sentences: seconds of silence between sentences
    sound_effects: whether to play UI sound effects
    encouragement_frequency: how often to inject encouragement
    """
    speed: float = 1.2
    style: str = "playful"
    max_sentence_length: int = 10
    pause_between_sentences: float = 0.5
    sound_effects: bool = True
    encouragement_frequency: str = "high"


@dataclass
class ElderlyVoiceProfile:
    """長青語音配置 — Voice profile adapted for elderly (ages 65+).

    speed: speech rate multiplier (slower, clearer)
    style: voice personality label
    max_sentence_length: maximum words per sentence
    pause_between_sentences: seconds of silence between sentences
    sound_effects: whether to play UI sound effects
    encouragement_frequency: how often to inject encouragement
    """
    speed: float = 0.7
    style: str = "warm_slow"
    max_sentence_length: int = 20
    pause_between_sentences: float = 1.5
    sound_effects: bool = False
    encouragement_frequency: str = "moderate"


# ---------------------------------------------------------------------------
# Audience Voice Style Mapping
# ---------------------------------------------------------------------------

# Map audience config voice_style to valid EmoMouthConfig voice_style
_AUDIENCE_VOICE_STYLE_MAP: Dict[str, str] = {
    "playful": "playful",
    "warm_slow": "warm",
    "warm": "warm",
    "gentle": "gentle",
    "calm": "calm",
}

# Map AudienceMode to emotional tone
_AUDIENCE_EMOTIONAL_TONE: Dict[AudienceMode, str] = {
    AudienceMode.KIDS: "PLAY",
    AudienceMode.ELDERLY: "CARE",
}

# Map AudienceMode to language
_AUDIENCE_LANGUAGE: Dict[AudienceMode, str] = {
    AudienceMode.KIDS: "en",
    AudienceMode.ELDERLY: "zh-CN",
}


# ---------------------------------------------------------------------------
# Abstract Backend
# ---------------------------------------------------------------------------

class EmoMouthBackend(ABC):
    """口之後端抽象 — Abstract TTS/audio generation backend.

    Concrete implementations connect to actual speech synthesis services.
    The core engine only depends on this interface.
    """

    @abstractmethod
    def synthesize(self, text: str, config: EmoMouthConfig) -> EmoMouthResult:
        """Synthesize speech from text with emotional configuration.

        text: the text to speak
        config: output configuration (language, voice style, tone, speed)
        Returns: EmoMouthResult with generated audio
        """
        ...


class CloudEmoMouthBackend(EmoMouthBackend):
    """雲端口之後端 — Cloud TTS backend placeholder.

    Integrations: Google Cloud TTS, Azure Speech Services, ElevenLabs.
    Actual implementation deferred to application layer.
    """

    def synthesize(self, text: str, config: EmoMouthConfig) -> EmoMouthResult:
        """Placeholder — returns empty audio result."""
        return EmoMouthResult(
            audio_data=b"",
            sample_rate=24000,
            duration_seconds=0.0,
            emotional_tone=config.emotional_tone,
            language=config.language,
            silence_applied=config.silence_type,
            breathing_pattern=None,
            timestamp=datetime.now(timezone.utc),
        )


class LocalEmoMouthBackend(EmoMouthBackend):
    """本地口之後端 — Local TTS backend placeholder.

    Integrations: pyttsx3, edge-tts, Coqui TTS.
    Actual implementation deferred to application layer.
    """

    def synthesize(self, text: str, config: EmoMouthConfig) -> EmoMouthResult:
        """Placeholder — returns empty audio result."""
        return EmoMouthResult(
            audio_data=b"",
            sample_rate=22050,
            duration_seconds=0.0,
            emotional_tone=config.emotional_tone,
            language=config.language,
            silence_applied=config.silence_type,
            breathing_pattern=None,
            timestamp=datetime.now(timezone.utc),
        )


# ---------------------------------------------------------------------------
# Default Sample Rate
# ---------------------------------------------------------------------------

DEFAULT_SAMPLE_RATE = 24000


# ---------------------------------------------------------------------------
# Main Engine
# ---------------------------------------------------------------------------

class EmoMouthEngine:
    """EmoMouth (口) Expressive Output Engine — 口之表達輸出引擎

    TCM Organ: 脾 (Spleen) — 主運化，化情為聲
    Panksepp Systems: PLAY / RAGE

    3-in-1 capabilities:
    1. Emotional Speech Synthesis — multilingual TTS with emotional tone
    2. Silence-as-Speech — MA/MU/ZEN silence generation
    3. Guided Breathing Audio — respiration-guided audio for anxiety relief

    This engine converts Pulse/state INTO audio output.
    It does NOT detect or analyze audio input.
    """

    def __init__(self, backend: Optional[EmoMouthBackend] = None) -> None:
        """Initialize EmoMouthEngine.

        backend: optional TTS backend. If None, uses LocalEmoMouthBackend.
        """
        self._backend = backend if backend is not None else LocalEmoMouthBackend()

    # ------------------------------------------------------------------
    # 1. Emotional Speech Synthesis
    # ------------------------------------------------------------------

    def speak(self, text: str, config: EmoMouthConfig) -> EmoMouthResult:
        """Synthesize emotional speech from text.

        text: the text to speak
        config: output configuration (language, voice style, tone, speed)
        Returns: EmoMouthResult with generated audio

        Generates multilingual TTS with emotional tone coloring.
        The backend handles actual audio generation; the core engine
        validates and routes the request.
        """
        if not isinstance(text, str) or not text.strip():
            raise ValueError("text must be a non-empty string")

        result = self._backend.synthesize(text, config)

        # If silence_type is configured, extend duration with silence
        if config.silence_type is not None:
            silence_duration = SILENCE_CONFIGS[config.silence_type]["default_duration"]
            result = EmoMouthResult(
                audio_data=result.audio_data,
                sample_rate=result.sample_rate,
                duration_seconds=result.duration_seconds + silence_duration,
                emotional_tone=result.emotional_tone,
                language=result.language,
                silence_applied=config.silence_type,
                breathing_pattern=result.breathing_pattern,
                timestamp=result.timestamp,
            )

        return result

    # ------------------------------------------------------------------
    # 2. Silence-as-Speech
    # ------------------------------------------------------------------

    def speak_silence(
        self,
        silence_type: Union[str, SilenceType],
        duration: Optional[float] = None,
    ) -> EmoMouthResult:
        """Generate silence-as-speech audio.

        silence_type: MA (deep reflection), MU (gentle acknowledgment),
                      or ZEN (shared presence)
        duration: override duration in seconds. If None, uses default
                  from SILENCE_CONFIGS.

        Returns: EmoMouthResult with silence audio placeholder.

        Silence modes:
        - MA: Deep reflection — soft breath + 3-5s silence
        - MU: Gentle acknowledgment — soft "嗯" + 2-3s silence
        - ZEN: Shared presence — ambient nature + 5-10s
        """
        if isinstance(silence_type, str):
            try:
                silence_type = SilenceType(silence_type.upper())
            except ValueError:
                raise ValueError(
                    f"silence_type must be one of "
                    f"{[s.value for s in SilenceType]}, "
                    f"got '{silence_type}'"
                )

        config = SILENCE_CONFIGS[silence_type]

        if duration is not None:
            if not isinstance(duration, (int, float)):
                raise TypeError(
                    f"duration must be numeric, "
                    f"got {type(duration).__name__}"
                )
            duration = _clamp(
                float(duration),
                config["min_duration"],
                config["max_duration"],
            )
        else:
            duration = config["default_duration"]

        return EmoMouthResult(
            audio_data=b"",
            sample_rate=DEFAULT_SAMPLE_RATE,
            duration_seconds=duration,
            emotional_tone="NEUTRAL",
            language="zh-CN",
            silence_applied=silence_type,
            breathing_pattern=None,
            timestamp=datetime.now(timezone.utc),
        )

    # ------------------------------------------------------------------
    # 3. Multilingual Speech
    # ------------------------------------------------------------------

    def speak_in_language(
        self,
        text: str,
        target_language: str,
        emotional_tone: str,
    ) -> EmoMouthResult:
        """Speak text in a specific language with emotional tone.

        text: the text to speak
        target_language: language code (zh-CN, zh-HK, en, ja, ko)
        emotional_tone: Panksepp system name for emotional coloring

        Returns: EmoMouthResult with generated audio.

        Automatically selects voice style based on emotional tone:
        - CARE → "warm"
        - PLAY → "playful"
        - SEEKING → "calm"
        - Others → "gentle"
        """
        if not isinstance(text, str) or not text.strip():
            raise ValueError("text must be a non-empty string")

        # Map emotional tone to voice style
        tone_to_style: Dict[str, str] = {
            "CARE": "warm",
            "PLAY": "playful",
            "SEEKING": "calm",
            "RAGE": "gentle",
            "FEAR": "gentle",
            "PANIC": "gentle",
            "LUST": "warm",
            "NEUTRAL": "calm",
            "VALENCE": "gentle",
            "AROUSAL": "gentle",
            "DOMINANCE": "gentle",
        }
        voice_style = tone_to_style.get(emotional_tone, "gentle")

        # Determine speed from emotional tone
        speed_map: Dict[str, float] = {
            "PLAY": 1.2,
            "RAGE": 1.1,
            "FEAR": 0.9,
            "PANIC": 1.0,
            "CARE": 0.9,
            "SEEKING": 1.0,
            "NEUTRAL": 1.0,
        }
        speed = speed_map.get(emotional_tone, 1.0)

        config = EmoMouthConfig(
            language=target_language,
            voice_style=voice_style,
            emotional_tone=emotional_tone,
            speed=speed,
        )

        return self.speak(text, config)

    # ------------------------------------------------------------------
    # 4. Guided Breathing
    # ------------------------------------------------------------------

    def guided_breathing(
        self,
        pattern: Union[str, BreathingPattern],
        cycles: int = 3,
    ) -> EmoMouthResult:
        """Generate guided breathing audio.

        pattern: breathing pattern name or enum
            "4-7-8" / FOUR_SEVEN_EIGHT — anxiety relief
            "box" / BOX — focus/calm
            "coherent" / COHERENT — HRV optimization
        cycles: number of breathing cycles (1-20)

        Returns: EmoMouthResult with breathing audio placeholder.

        Breathing patterns:
        - 4-7-8: Inhale 4s → Hold 7s → Exhale 8s (19s per cycle)
        - Box: Inhale 4s → Hold 4s → Exhale 4s (12s per cycle)
        - Coherent: Inhale 5s → Exhale 5s (10s per cycle)
        """
        if isinstance(pattern, str):
            pattern_map = {p.value: p for p in BreathingPattern}
            if pattern in pattern_map:
                pattern = pattern_map[pattern]
            else:
                try:
                    pattern = BreathingPattern(pattern)
                except ValueError:
                    raise ValueError(
                        f"pattern must be one of "
                        f"{[p.value for p in BreathingPattern]}, "
                        f"got '{pattern}'"
                    )

        if not isinstance(cycles, int) or cycles < 1:
            raise ValueError(f"cycles must be a positive integer, got {cycles}")
        if cycles > 20:
            raise ValueError(f"cycles must be <= 20, got {cycles}")

        phases = BREATHING_PATTERNS[pattern]
        cycle_duration = sum(p.duration for p in phases)
        total_duration = cycle_duration * cycles

        return EmoMouthResult(
            audio_data=b"",
            sample_rate=DEFAULT_SAMPLE_RATE,
            duration_seconds=total_duration,
            emotional_tone="CARE",
            language="zh-CN",
            silence_applied=None,
            breathing_pattern=pattern,
            timestamp=datetime.now(timezone.utc),
        )

    # ------------------------------------------------------------------
    # 5. Pulse Integration
    # ------------------------------------------------------------------

    def from_pulse(
        self,
        pulse: Pulse,
        text: Optional[str] = None,
    ) -> EmoMouthResult:
        """Convert Pulse to EmoMouthResult — determine output from emotional state.

        pulse: the emotional Pulse to convert
        text: optional text to speak. If None, generates silence or breathing.

        Decision logic:
        - High arousal + negative valence → guided breathing (anxiety relief)
        - Low arousal + negative valence → MA silence (deep reflection)
        - Positive valence → speak with matching tone
        - Neutral → MU silence (gentle acknowledgment)

        The Pulse's Panksepp system determines the emotional_tone
        for speech synthesis. Voice style is derived from
        VOICE_STYLE_PANKSEPP mapping.
        """
        if not isinstance(pulse, Pulse):
            raise TypeError(f"pulse must be a Pulse, got {type(pulse).__name__}")

        # Determine output mode from valence/arousal
        high_arousal = pulse.arousal > 0.5
        negative_valence = pulse.valence < -0.2
        positive_valence = pulse.valence > 0.2

        # High arousal + negative → guided breathing (anxiety relief)
        if high_arousal and negative_valence:
            return self.guided_breathing(BreathingPattern.FOUR_SEVEN_EIGHT, cycles=3)

        # Low arousal + negative → MA silence (deep reflection)
        if negative_valence:
            return self.speak_silence(SilenceType.MA)

        # Positive valence → speak with matching tone
        if positive_valence and text is not None:
            tone = pulse.pulse_type.name
            # Derive voice style from Panksepp system
            voice_style = "gentle"
            for style, ptype in VOICE_STYLE_PANKSEPP.items():
                if ptype == pulse.pulse_type:
                    voice_style = style
                    break

            # Speed modulated by arousal
            speed = _clamp(0.8 + pulse.arousal * 0.4, 0.5, 2.0)

            config = EmoMouthConfig(
                language="zh-CN",
                voice_style=voice_style,
                emotional_tone=tone,
                speed=speed,
            )
            return self.speak(text, config)

        # Neutral or no text → MU silence (gentle acknowledgment)
        return self.speak_silence(SilenceType.MU)

    # ------------------------------------------------------------------
    # 6. Audience Adaptation
    # ------------------------------------------------------------------

    def speak_to_audience(
        self, text: str, audience_mode: AudienceMode
    ) -> EmoMouthResult:
        """Speak text adapted for a specific audience mode.

        text: the text to speak
        audience_mode: KIDS or ELDERLY — determines voice style, speed, etc.
        Returns: EmoMouthResult with audience-adapted audio

        Adapts speech parameters based on audience configuration:
        - Kids: playful voice, faster speed, shorter sentences
        - Elderly: warm voice, slower speed, longer pauses
        """
        if not isinstance(text, str) or not text.strip():
            raise ValueError("text must be a non-empty string")

        config = get_config(audience_mode)

        # Split and truncate text for audience
        adapted_text = self._split_for_audience(
            text, config.max_sentence_length
        )

        # Map audience voice_style to a valid EmoMouthConfig voice_style
        voice_style = _AUDIENCE_VOICE_STYLE_MAP.get(
            config.voice_style, "gentle"
        )

        # Determine emotional tone based on audience mode
        emotional_tone = _AUDIENCE_EMOTIONAL_TONE.get(
            audience_mode, "NEUTRAL"
        )

        # Determine language based on audience mode
        language = _AUDIENCE_LANGUAGE.get(audience_mode, "zh-CN")

        mouth_config = EmoMouthConfig(
            language=language,
            voice_style=voice_style,
            emotional_tone=emotional_tone,
            speed=_clamp(config.voice_speed, 0.5, 2.0),
        )

        return self.speak(adapted_text, mouth_config)

    def speak_breathing_game(
        self,
        audience_mode: AudienceMode,
        pattern: str = "default",
    ) -> EmoMouthResult:
        """Generate audience-adapted breathing game audio.

        audience_mode: KIDS or ELDERLY — determines breathing game style
        pattern: breathing pattern name (reserved for future use)
        Returns: EmoMouthResult with breathing game audio

        Kids mode: bubble-blowing breathing game (playful, energetic)
        Elderly mode: calm counting breathing exercise (warm, slow)
        """
        if audience_mode == AudienceMode.KIDS:
            text = "Let's blow some bubbles! Breathe in... and blow out! Pop!"
        elif audience_mode == AudienceMode.ELDERLY:
            text = "慢慢吸氣...二...三...四...慢慢呼氣...二...三...四...五...六..."
        else:
            text = "Breathe in... and breathe out..."

        return self.speak_to_audience(text, audience_mode)

    def speak_encouragement(
        self, audience_mode: AudienceMode
    ) -> EmoMouthResult:
        """Generate audience-adapted encouragement audio.

        audience_mode: KIDS or ELDERLY — determines encouragement style
        Returns: EmoMouthResult with encouragement audio

        Kids mode: playful, emoji-rich encouragement
        Elderly mode: warm, gentle Chinese encouragement
        """
        import random

        kids_encouragements = [
            "You're doing great! 🌟",
            "I'm so proud of you! 🎉",
            "You're amazing! ✨",
            "Keep going, friend! 💪",
            "Wow, that was awesome! 🌈",
        ]

        elderly_encouragements = [
            "你做得很好。",
            "慢慢來，不著急。",
            "你很努力了。",
            "休息一下也沒關係。",
            "我一直在這裡陪你。",
        ]

        if audience_mode == AudienceMode.KIDS:
            text = random.choice(kids_encouragements)
        elif audience_mode == AudienceMode.ELDERLY:
            text = random.choice(elderly_encouragements)
        else:
            text = "You're doing well."

        return self.speak_to_audience(text, audience_mode)

    @staticmethod
    def _split_for_audience(text: str, max_words: int) -> str:
        """Split text into sentences and truncate long ones for audience.

        text: the input text
        max_words: maximum words per sentence before truncation
        Returns: text with sentences truncated to max_words

        Splits on sentence-ending punctuation (. ! ?), then for each
        sentence, if word count exceeds max_words, truncates and adds "...".
        Sentences are joined back with appropriate pauses.
        """
        import re

        # Split on sentence-ending punctuation
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())

        result_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            words = sentence.split()
            if len(words) > max_words:
                truncated = " ".join(words[:max_words]) + "..."
                result_sentences.append(truncated)
            else:
                result_sentences.append(sentence)

        return " ".join(result_sentences)


# ---------------------------------------------------------------------------
# Module-level smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    def _expect(cond: bool, label: str) -> None:
        print(("PASS" if cond else "FAIL") + f" — {label}")

    # SilenceType enum
    _expect(SilenceType.MA.value == "MA", "SilenceType.MA value")
    _expect(SilenceType.MU.value == "MU", "SilenceType.MU value")
    _expect(SilenceType.ZEN.value == "ZEN", "SilenceType.ZEN value")

    # BreathingPattern enum
    _expect(BreathingPattern.FOUR_SEVEN_EIGHT.value == "4-7-8", "4-7-8 pattern")
    _expect(BreathingPattern.BOX.value == "box", "box pattern")
    _expect(BreathingPattern.COHERENT.value == "coherent", "coherent pattern")

    # BreathingPhase validation
    bp = BreathingPhase("inhale", 4.0)
    _expect(bp.phase == "inhale" and bp.duration == 4.0, "BreathingPhase creation")
    bp_dict = bp.to_dict()
    bp_round = BreathingPhase.from_dict(bp_dict)
    _expect(bp_round.phase == "inhale" and bp_round.duration == 4.0, "BreathingPhase round-trip")

    try:
        BreathingPhase("invalid", 1.0)
    except ValueError:
        _expect(True, "invalid phase raises ValueError")
    else:
        _expect(False, "invalid phase raises ValueError")

    # SILENCE_CONFIGS
    _expect(SILENCE_CONFIGS[SilenceType.MA]["default_duration"] == 4.0, "MA default duration")
    _expect(SILENCE_CONFIGS[SilenceType.MU]["default_duration"] == 2.5, "MU default duration")
    _expect(SILENCE_CONFIGS[SilenceType.ZEN]["default_duration"] == 7.5, "ZEN default duration")

    # BREATHING_PATTERNS
    _expect(
        len(BREATHING_PATTERNS[BreathingPattern.FOUR_SEVEN_EIGHT]) == 3,
        "4-7-8 has 3 phases",
    )
    _expect(
        BREATHING_PATTERNS[BreathingPattern.FOUR_SEVEN_EIGHT][0].phase == "inhale",
        "4-7-8 first phase is inhale",
    )
    _expect(
        len(BREATHING_PATTERNS[BreathingPattern.COHERENT]) == 2,
        "coherent has 2 phases (no hold)",
    )

    # VOICE_STYLE_PANKSEPP
    _expect(VOICE_STYLE_PANKSEPP["warm"] == PulseType.CARE, "warm → CARE")
    _expect(VOICE_STYLE_PANKSEPP["playful"] == PulseType.PLAY, "playful → PLAY")
    _expect(VOICE_STYLE_PANKSEPP["calm"] == PulseType.SEEKING, "calm → SEEKING")

    # EmoMouthConfig validation
    config = EmoMouthConfig(
        language="zh-CN", voice_style="warm",
        emotional_tone="CARE", speed=1.0,
    )
    _expect(config.speed == 1.0, "config speed valid")

    try:
        EmoMouthConfig(language="xx", voice_style="warm", emotional_tone="CARE", speed=1.0)
    except ValueError:
        _expect(True, "invalid language raises ValueError")
    else:
        _expect(False, "invalid language raises ValueError")

    try:
        EmoMouthConfig(language="zh-CN", voice_style="angry", emotional_tone="CARE", speed=1.0)
    except ValueError:
        _expect(True, "invalid voice_style raises ValueError")
    else:
        _expect(False, "invalid voice_style raises ValueError")

    # Speed clamping
    fast_config = EmoMouthConfig(
        language="en", voice_style="playful",
        emotional_tone="PLAY", speed=5.0,
    )
    _expect(fast_config.speed == 2.0, "speed clamped to 2.0")

    # EmoMouthConfig round-trip
    config_dict = config.to_dict()
    config_round = EmoMouthConfig.from_dict(config_dict)
    _expect(config_round.language == "zh-CN", "config round-trip language")
    _expect(config_round.emotional_tone == "CARE", "config round-trip tone")

    # EmoMouthResult
    result = EmoMouthResult(
        audio_data=b"\x00\x01", sample_rate=24000,
        duration_seconds=3.0, emotional_tone="CARE",
        language="zh-CN", silence_applied=SilenceType.MA,
        breathing_pattern=None,
        timestamp=datetime.now(timezone.utc),
    )
    _expect(result.sample_rate == 24000, "result sample_rate")
    result_dict = result.to_dict()
    result_round = EmoMouthResult.from_dict(result_dict)
    _expect(result_round.sample_rate == 24000, "result round-trip sample_rate")

    # EmoMouthEngine
    engine = EmoMouthEngine()

    # speak_silence
    silence_ma = engine.speak_silence("MA")
    _expect(silence_ma.silence_applied == SilenceType.MA, "speak_silence MA type")
    _expect(
        abs(silence_ma.duration_seconds - 4.0) < 0.01,
        "speak_silence MA duration",
    )

    silence_mu = engine.speak_silence(SilenceType.MU, duration=2.8)
    _expect(
        abs(silence_mu.duration_seconds - 2.8) < 0.01,
        "speak_silence MU custom duration",
    )

    # Duration clamping
    silence_clamped = engine.speak_silence(SilenceType.MA, duration=1.0)
    _expect(
        abs(silence_clamped.duration_seconds - 3.0) < 0.01,
        "speak_silence MA duration clamped to min",
    )

    # guided_breathing
    breathing = engine.guided_breathing("4-7-8", cycles=2)
    _expect(
        breathing.breathing_pattern == BreathingPattern.FOUR_SEVEN_EIGHT,
        "guided_breathing pattern",
    )
    _expect(
        abs(breathing.duration_seconds - 38.0) < 0.01,
        "guided_breathing 2 cycles of 4-7-8 = 38s",
    )

    breathing_box = engine.guided_breathing(BreathingPattern.BOX, cycles=1)
    _expect(
        abs(breathing_box.duration_seconds - 12.0) < 0.01,
        "guided_breathing 1 cycle of box = 12s",
    )

    # from_pulse — high arousal negative → guided breathing
    pulse_fear = Pulse(PulseType.FEAR, -0.8, 0.8, -0.7, 0.9)
    result_fear = engine.from_pulse(pulse_fear)
    _expect(
        result_fear.breathing_pattern == BreathingPattern.FOUR_SEVEN_EIGHT,
        "from_pulse fear → guided breathing",
    )

    # from_pulse — low arousal negative → MA silence
    pulse_sad = Pulse(PulseType.PANIC, -0.6, 0.2, -0.5, 0.7)
    result_sad = engine.from_pulse(pulse_sad)
    _expect(
        result_sad.silence_applied == SilenceType.MA,
        "from_pulse low arousal negative → MA silence",
    )

    # from_pulse — positive → speak with tone
    pulse_play = Pulse(PulseType.PLAY, 0.8, 0.5, 0.3, 0.8)
    result_play = engine.from_pulse(pulse_play, text="Let's have fun!")
    _expect(
        result_play.emotional_tone == "PLAY",
        "from_pulse play → speak with PLAY tone",
    )

    # from_pulse — neutral → MU silence
    pulse_neutral = Pulse(PulseType.NEUTRAL, 0.0, 0.0, 0.0, 0.5)
    result_neutral = engine.from_pulse(pulse_neutral)
    _expect(
        result_neutral.silence_applied == SilenceType.MU,
        "from_pulse neutral → MU silence",
    )

    # speak_in_language
    result_en = engine.speak_in_language("Hello friend", "en", "CARE")
    _expect(result_en.language == "en", "speak_in_language language")
    _expect(result_en.emotional_tone == "CARE", "speak_in_language tone")

    # Backend placeholders
    cloud = CloudEmoMouthBackend()
    local = LocalEmoMouthBackend()
    _expect(
        cloud.synthesize("test", config).sample_rate == 24000,
        "CloudEmoMouthBackend placeholder",
    )
    _expect(
        local.synthesize("test", config).sample_rate == 22050,
        "LocalEmoMouthBackend placeholder",
    )

    print("OK — emo_mouth.py smoke tests done")
