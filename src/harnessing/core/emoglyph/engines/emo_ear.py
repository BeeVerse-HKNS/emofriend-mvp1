"""EmoEar (耳) Auditory Perception Engine — 耳·聽覺感知引擎

七竅 (Seven Apertures) multimodal sensory system for EmoFriend.

TCM Organ: 腎 (Kidney) — 腎開竅於耳，腎氣通於耳
Panksepp Systems: CARE / PANIC

3-in-1 capabilities:
  1. Voice Tone Analysis — prosody + manner → emotional state
  2. Ambient Sound Classification — environment soundscape → stress context
  3. Respiration Detection — breathing pattern from microphone → anxiety indicator

EmoGlyph integration: Pulse Layer (L1) — converts auditory perception
to Pulse objects for downstream emotional processing.

Design principles:
- Stdlib only — backends are abstract interfaces; real implementations are external
- All float ranges validated via _clamp and __post_init__
- Full serialization via to_dict / from_dict
- Pulse conversion via to_pulse for EmoGlyph pipeline integration
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from ..pulse import Pulse, PulseType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """Clamp *value* into [lo, hi]."""
    return max(lo, min(hi, value))


# ---------------------------------------------------------------------------
# Constants — Manner → Panksepp mapping
# ---------------------------------------------------------------------------

# manner_tag → (PulseType, valence_offset, arousal_offset)
# Valence / arousal offsets are representative VAD anchors for each manner.
MANNER_PANKSEPP_MAP: Dict[str, Tuple[PulseType, float, float]] = {
    "flat":       (PulseType.PANIC, -0.5, 0.2),   # Monotone → PANIC dorsal ⚠️ Depression/shutdown
    "trembling":  (PulseType.FEAR,  -0.7, 0.8),   # Trembling → FEAR
    "rushed":     (PulseType.PANIC, -0.6, 0.9),   # Rushed → PANIC
    "sighing":    (PulseType.PANIC, -0.3, 0.3),   # Sighing → PANIC→CARE (stress reset attempt)
    "held breath":(PulseType.FEAR,  -0.6, 0.7),   # Held breath → FEAR ⚠️ Acute anxiety
    "hesitant":   (PulseType.FEAR,  -0.4, 0.5),   # Hesitant → FEAR
}

# ---------------------------------------------------------------------------
# Constants — Ambient sound → stress impact
# ---------------------------------------------------------------------------

# ambient_class → stress_impact  (negative = calming, positive = stressful)
AMBIENT_STRESS_MAP: Dict[str, float] = {
    "nature":       -0.3,   # Calming
    "traffic":       0.5,   # Stressful
    "silence":      -0.1,   # Neutral-slightly calm
    "crowd":         0.3,   # Moderate stress
    "construction":  0.6,   # Very stressful
    "music":        -0.2,   # Generally calming
}

# Valid manner tags
_VALID_MANNER_TAGS = frozenset(MANNER_PANKSEPP_MAP.keys())

# Valid ambient classes
_VALID_AMBIENT_CLASSES = frozenset(AMBIENT_STRESS_MAP.keys())

# Valid language codes
_VALID_LANGUAGES = frozenset({"zh-CN", "zh-HK", "zh-TW", "en", "ja", "ko", "unknown"})

# Valid breathing patterns
_VALID_BREATHING_PATTERNS = frozenset({"regular", "irregular", "sighing", "held"})

# Dominant emotion → PulseType lookup
_EMOTION_PULSE_MAP: Dict[str, PulseType] = {
    "SEEKING": PulseType.SEEKING,
    "RAGE":    PulseType.RAGE,
    "FEAR":    PulseType.FEAR,
    "LUST":    PulseType.LUST,
    "CARE":    PulseType.CARE,
    "PANIC":   PulseType.PANIC,
    "PLAY":    PulseType.PLAY,
    "NEUTRAL": PulseType.NEUTRAL,
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ProsodyFeatures:
    """Prosody Features — 韻律特徵

    Acoustic measurements extracted from voice input.
    All values are raw measurements; interpretation depends on
    the downstream manner-tag classification.
    """
    pitch_mean: float      # Hz — fundamental frequency mean
    pitch_range: float     # Hz — F0 range (max - min)
    energy_mean: float     # dB — average energy / loudness
    speech_rate: float     # syllables per second
    jitter: float          # pitch cycle variation (dimensionless, ≥ 0)
    shimmer: float         # amplitude variation (dimensionless, ≥ 0)

    def __post_init__(self) -> None:
        if self.pitch_mean < 0:
            raise ValueError(f"pitch_mean must be ≥ 0, got {self.pitch_mean}")
        if self.pitch_range < 0:
            raise ValueError(f"pitch_range must be ≥ 0, got {self.pitch_range}")
        if self.speech_rate < 0:
            raise ValueError(f"speech_rate must be ≥ 0, got {self.speech_rate}")
        if self.jitter < 0:
            raise ValueError(f"jitter must be ≥ 0, got {self.jitter}")
        if self.shimmer < 0:
            raise ValueError(f"shimmer must be ≥ 0, got {self.shimmer}")

    def to_dict(self) -> dict:
        return {
            "pitch_mean": self.pitch_mean,
            "pitch_range": self.pitch_range,
            "energy_mean": self.energy_mean,
            "speech_rate": self.speech_rate,
            "jitter": self.jitter,
            "shimmer": self.shimmer,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ProsodyFeatures:
        return cls(
            pitch_mean=data["pitch_mean"],
            pitch_range=data["pitch_range"],
            energy_mean=data["energy_mean"],
            speech_rate=data["speech_rate"],
            jitter=data["jitter"],
            shimmer=data["shimmer"],
        )


@dataclass
class EmoEarResult:
    """EmoEar Result — 耳·聽覺感知結果

    Unified result from the 3-in-1 auditory perception engine.
    Combines voice tone, ambient sound, and respiration analysis
    into a single emotional assessment.
    """
    # Core emotional assessment
    dominant_emotion: str          # Panksepp system name (SEEKING/RAGE/FEAR/LUST/CARE/PANIC/PLAY/NEUTRAL)
    valence: float                 # -1.0 to 1.0
    arousal: float                 # -1.0 to 1.0
    dominance: float               # -1.0 to 1.0
    intensity: float               # 0.0 to 1.0
    confidence: float              # 0.0 to 1.0

    # Voice-specific
    prosody: Optional[ProsodyFeatures] = None
    manner_tags: List[str] = field(default_factory=list)  # "hesitant", "rushed", "flat", "trembling", "sighing"
    language_detected: str = "unknown"                     # "zh-CN", "zh-HK", "en", "ja", "ko", "unknown"
    transcript: Optional[str] = None

    # Ambient-specific
    ambient_class: Optional[str] = None     # "traffic", "nature", "silence", "crowd", "construction", "music"
    ambient_db: Optional[float] = None      # Sound level in dB

    # Respiration-specific
    respiration_rate: Optional[float] = None    # Breaths per minute (normal: 12-20)
    breathing_pattern: Optional[str] = None     # "regular", "irregular", "sighing", "held"

    # Metadata
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        # Validate VAD ranges
        self.valence = _clamp(self.valence, -1.0, 1.0)
        self.arousal = _clamp(self.arousal, -1.0, 1.0)
        self.dominance = _clamp(self.dominance, -1.0, 1.0)
        self.intensity = _clamp(self.intensity, 0.0, 1.0)
        self.confidence = _clamp(self.confidence, 0.0, 1.0)

        # Validate dominant_emotion
        valid_emotions = set(_EMOTION_PULSE_MAP.keys())
        if self.dominant_emotion not in valid_emotions:
            raise ValueError(
                f"dominant_emotion must be one of {sorted(valid_emotions)}, "
                f"got {self.dominant_emotion!r}"
            )

        # Validate manner_tags
        for tag in self.manner_tags:
            if tag not in _VALID_MANNER_TAGS:
                raise ValueError(
                    f"Invalid manner tag {tag!r}. Must be one of {sorted(_VALID_MANNER_TAGS)}"
                )

        # Validate language_detected
        if self.language_detected not in _VALID_LANGUAGES:
            raise ValueError(
                f"language_detected must be one of {sorted(_VALID_LANGUAGES)}, "
                f"got {self.language_detected!r}"
            )

        # Validate ambient_class
        if self.ambient_class is not None and self.ambient_class not in _VALID_AMBIENT_CLASSES:
            raise ValueError(
                f"ambient_class must be one of {sorted(_VALID_AMBIENT_CLASSES)}, "
                f"got {self.ambient_class!r}"
            )

        # Validate ambient_db
        if self.ambient_db is not None and self.ambient_db < 0:
            raise ValueError(f"ambient_db must be ≥ 0, got {self.ambient_db}")

        # Validate respiration_rate
        if self.respiration_rate is not None and self.respiration_rate < 0:
            raise ValueError(f"respiration_rate must be ≥ 0, got {self.respiration_rate}")

        # Validate breathing_pattern
        if self.breathing_pattern is not None and self.breathing_pattern not in _VALID_BREATHING_PATTERNS:
            raise ValueError(
                f"breathing_pattern must be one of {sorted(_VALID_BREATHING_PATTERNS)}, "
                f"got {self.breathing_pattern!r}"
            )

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "dominant_emotion": self.dominant_emotion,
            "valence": self.valence,
            "arousal": self.arousal,
            "dominance": self.dominance,
            "intensity": self.intensity,
            "confidence": self.confidence,
            "prosody": self.prosody.to_dict() if self.prosody is not None else None,
            "manner_tags": list(self.manner_tags),
            "language_detected": self.language_detected,
            "transcript": self.transcript,
            "ambient_class": self.ambient_class,
            "ambient_db": self.ambient_db,
            "respiration_rate": self.respiration_rate,
            "breathing_pattern": self.breathing_pattern,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> EmoEarResult:
        prosody = None
        if data.get("prosody") is not None:
            prosody = ProsodyFeatures.from_dict(data["prosody"])

        ts = data.get("timestamp")
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
        elif ts is None:
            ts = datetime.now(timezone.utc)

        return cls(
            dominant_emotion=data["dominant_emotion"],
            valence=data["valence"],
            arousal=data["arousal"],
            dominance=data["dominance"],
            intensity=data["intensity"],
            confidence=data["confidence"],
            prosody=prosody,
            manner_tags=data.get("manner_tags", []),
            language_detected=data.get("language_detected", "unknown"),
            transcript=data.get("transcript"),
            ambient_class=data.get("ambient_class"),
            ambient_db=data.get("ambient_db"),
            respiration_rate=data.get("respiration_rate"),
            breathing_pattern=data.get("breathing_pattern"),
            timestamp=ts,
        )

    # ------------------------------------------------------------------
    # Pulse conversion
    # ------------------------------------------------------------------

    def to_pulse(self) -> Pulse:
        """Convert EmoEarResult to Pulse for EmoGlyph pipeline integration.

        Maps dominant_emotion → PulseType, then uses valence/arousal/dominance/intensity
        directly. Ambient stress context modulates valence as a bias.
        """
        pulse_type = _EMOTION_PULSE_MAP.get(self.dominant_emotion, PulseType.NEUTRAL)

        # Ambient stress modulation: shift valence by ambient stress impact
        ambient_bias = 0.0
        if self.ambient_class is not None:
            ambient_bias = AMBIENT_STRESS_MAP.get(self.ambient_class, 0.0) * 0.15

        # Breathing pattern modulation: irregular/held breathing boosts arousal
        breath_arousal_bias = 0.0
        if self.breathing_pattern in ("irregular", "held"):
            breath_arousal_bias = 0.1

        return Pulse(
            pulse_type=pulse_type,
            valence=_clamp(self.valence + ambient_bias, -1.0, 1.0),
            arousal=_clamp(self.arousal + breath_arousal_bias, -1.0, 1.0),
            dominance=self.dominance,
            intensity=self.intensity,
        )


# ---------------------------------------------------------------------------
# Abstract backends
# ---------------------------------------------------------------------------

class EmoEarBackend(ABC):
    """Abstract backend for auditory analysis — 聽覺分析後端抽象介面

    Concrete implementations connect to real audio processing services.
    The engine itself is backend-agnostic; only this interface matters.
    """

    @abstractmethod
    def analyze(self, audio_data: bytes, sample_rate: int = 16000) -> EmoEarResult:
        """Analyze raw audio bytes and return an EmoEarResult.

        Parameters
        ----------
        audio_data : bytes
            Raw PCM audio data (16-bit signed LE, mono).
        sample_rate : int
            Sample rate in Hz. Default 16000 (telephony/speech standard).

        Returns
        -------
        EmoEarResult
            Complete auditory perception result.
        """
        ...


class CloudEmoEarBackend(EmoEarBackend):
    """Cloud-based auditory backend — 雲端聽覺後端

    Placeholder for cloud API integrations:
    - Hume AI (prosody + vocal burst)
    - Google Speech-to-Text + emotion
    - Azure Speech (sentiment + prosody)

    Actual implementation requires API keys and network calls.
    """

    def analyze(self, audio_data: bytes, sample_rate: int = 16000) -> EmoEarResult:
        raise NotImplementedError(
            "CloudEmoEarBackend requires a concrete implementation "
            "with API credentials. Override this method in a subclass."
        )


class LocalEmoEarBackend(EmoEarBackend):
    """Local auditory backend — 本地聽覺後端

    Placeholder for on-device processing:
    - OpenSMILE (prosody feature extraction)
    - Whisper + librosa (transcription + acoustic features)
    - Custom respiration detection model

    Actual implementation requires model files and optional GPU.
    """

    def analyze(self, audio_data: bytes, sample_rate: int = 16000) -> EmoEarResult:
        raise NotImplementedError(
            "LocalEmoEarBackend requires a concrete implementation "
            "with model files. Override this method in a subclass."
        )


# ---------------------------------------------------------------------------
# Main Engine
# ---------------------------------------------------------------------------

class EmoEarEngine:
    """EmoEar (耳) Auditory Perception Engine — 耳·聽覺感知引擎

    TCM: 腎開竅於耳 (Kidney opens into the ear)
    Panksepp: CARE / PANIC systems

    3-in-1 auditory perception:
      1. Voice Tone Analysis — prosody + manner → emotional state
      2. Ambient Sound Classification — environment soundscape → stress context
      3. Respiration Detection — breathing pattern → anxiety indicator

    Usage::

        engine = EmoEarEngine()  # no backend → returns NEUTRAL placeholder
        result = engine.analyze(audio_bytes, sample_rate=16000)
        pulse = engine.to_pulse(result)
    """

    def __init__(self, backend: Optional[EmoEarBackend] = None) -> None:
        self._backend = backend

    # ------------------------------------------------------------------
    # Core analysis
    # ------------------------------------------------------------------

    def analyze(self, audio_data: bytes, sample_rate: int = 16000) -> EmoEarResult:
        """Analyze audio input and return a unified EmoEarResult.

        If no backend is configured, returns a NEUTRAL placeholder result
        so the pipeline can still function in dry-run / testing mode.

        Parameters
        ----------
        audio_data : bytes
            Raw PCM audio data.
        sample_rate : int
            Sample rate in Hz (default 16000).

        Returns
        -------
        EmoEarResult
            Complete auditory perception result.
        """
        if not isinstance(audio_data, (bytes, bytearray)):
            raise TypeError(
                f"audio_data must be bytes or bytearray, got {type(audio_data).__name__}"
            )
        if sample_rate <= 0:
            raise ValueError(f"sample_rate must be > 0, got {sample_rate}")

        if self._backend is not None:
            return self._backend.analyze(audio_data, sample_rate)

        # No backend: return NEUTRAL placeholder
        return EmoEarResult(
            dominant_emotion="NEUTRAL",
            valence=0.0,
            arousal=0.0,
            dominance=0.0,
            intensity=0.0,
            confidence=0.0,
        )

    # ------------------------------------------------------------------
    # Pulse conversion
    # ------------------------------------------------------------------

    def to_pulse(self, result: EmoEarResult) -> Pulse:
        """Convert an EmoEarResult to a Pulse for EmoGlyph pipeline.

        Delegates to ``EmoEarResult.to_pulse()`` — kept here as a
        convenience entry-point matching the engine-level API pattern.
        """
        if not isinstance(result, EmoEarResult):
            raise TypeError(
                f"result must be an EmoEarResult, got {type(result).__name__}"
            )
        return result.to_pulse()

    # ------------------------------------------------------------------
    # Manner-based quick inference
    # ------------------------------------------------------------------

    @staticmethod
    def infer_from_manner(manner_tag: str, confidence: float = 0.6) -> EmoEarResult:
        """Quick-infer an EmoEarResult from a single manner tag.

        Useful when only manner classification is available (no full prosody).
        Maps via ``MANNER_PANKSEPP_MAP`` to produce a basic VAD result.

        Parameters
        ----------
        manner_tag : str
            One of the keys in ``MANNER_PANKSEPP_MAP``.
        confidence : float
            Confidence for the inference (0.0–1.0).

        Returns
        -------
        EmoEarResult
            Result with VAD derived from the manner map.
        """
        if manner_tag not in MANNER_PANKSEPP_MAP:
            raise ValueError(
                f"Unknown manner tag {manner_tag!r}. "
                f"Must be one of {sorted(MANNER_PANKSEPP_MAP.keys())}"
            )
        pulse_type, valence, arousal = MANNER_PANKSEPP_MAP[manner_tag]
        # Derive dominance from PulseType baseline
        from ..pulse import VAD_BASELINES
        _, _, baseline_d = VAD_BASELINES.get(pulse_type, (0.0, 0.0, 0.0))

        return EmoEarResult(
            dominant_emotion=pulse_type.name,
            valence=valence,
            arousal=arousal,
            dominance=baseline_d,
            intensity=_clamp(confidence),
            confidence=_clamp(confidence),
            manner_tags=[manner_tag],
        )

    # ------------------------------------------------------------------
    # Ambient stress assessment
    # ------------------------------------------------------------------

    @staticmethod
    def ambient_stress_impact(ambient_class: str) -> float:
        """Return the stress impact score for an ambient sound class.

        Negative values indicate calming; positive values indicate stress.

        Parameters
        ----------
        ambient_class : str
            One of the keys in ``AMBIENT_STRESS_MAP``.

        Returns
        -------
        float
            Stress impact score.
        """
        if ambient_class not in AMBIENT_STRESS_MAP:
            raise ValueError(
                f"Unknown ambient class {ambient_class!r}. "
                f"Must be one of {sorted(AMBIENT_STRESS_MAP.keys())}"
            )
        return AMBIENT_STRESS_MAP[ambient_class]

    # ------------------------------------------------------------------
    # Respiration assessment
    # ------------------------------------------------------------------

    @staticmethod
    def assess_respiration(rate: float, pattern: str) -> Dict[str, float]:
        """Assess respiration-derived anxiety indicators.

        Parameters
        ----------
        rate : float
            Breaths per minute. Normal range: 12–20.
        pattern : str
            One of "regular", "irregular", "sighing", "held".

        Returns
        -------
        dict
            Keys: ``anxiety_risk`` (0.0–1.0), ``arousal_bias`` (-1.0–1.0).
        """
        if rate < 0:
            raise ValueError(f"rate must be ≥ 0, got {rate}")
        if pattern not in _VALID_BREATHING_PATTERNS:
            raise ValueError(
                f"pattern must be one of {sorted(_VALID_BREATHING_PATTERNS)}, "
                f"got {pattern!r}"
            )

        # Anxiety risk from rate deviation
        if 12 <= rate <= 20:
            rate_risk = 0.0
        elif rate < 12:
            # Bradypnea — possible calm or depression
            rate_risk = _clamp((12 - rate) / 12, 0.0, 0.5)
        else:
            # Tachypnea — anxiety / panic
            rate_risk = _clamp((rate - 20) / 20, 0.0, 1.0)

        # Pattern-based risk
        pattern_risk = {
            "regular": 0.0,
            "sighing": 0.2,
            "irregular": 0.5,
            "held": 0.8,
        }.get(pattern, 0.0)

        anxiety_risk = _clamp((rate_risk + pattern_risk) / 2)
        arousal_bias = _clamp(anxiety_risk * 0.6, -1.0, 1.0)

        return {"anxiety_risk": anxiety_risk, "arousal_bias": arousal_bias}
