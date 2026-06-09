"""EmoHand (手) Behavioral Engine — 行為引擎

七竅 (Seven Apertures) 多模態感官系統 — 手 (Hand) 通道

中醫臟腑: 肺 (Lung)
Panksepp 系統: PLAY / RAGE

三合一能力:
1. Keystroke Dynamics — 打字速度、節奏、錯誤率 → 情感狀態
2. Scroll/Touch Behavior — 滾動速度、點擊模式 → 挫折/抑鬱
3. App Usage Patterns — 社交媒體使用、深夜屏幕時間 → 心情指標

行為→情感映射:
- 慢速打字 + 高錯誤率 → PANIC (認知疲勞/抑鬱)
- 快速不穩定打字 (高節奏變異) → RAGE (挫折)
- 慢速滾動 + 長停頓 → PANIC (抑鬱認知)
- 不穩定滾動 + 高急動度 → RAGE (挫折)
- 高社交媒體 + 深夜使用 → SEEKING 適應不良 (抑鬱風險)
- 低 App 多樣性 → PANIC (社交退縮)

設計原則:
- 自包含，無外部依賴 (僅 stdlib)
- 數值穩定 (所有浮點值使用 _clamp)
- 可解釋 (每個映射都有行為依據)
- Pulse 整合 (to_pulse 轉換為 EmoGlyph 脈衝)
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from math import sqrt
from typing import Any, Dict, List, Optional, Tuple

from ..pulse import Pulse, PulseType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clamp(value: float, lo: float, hi: float) -> float:
    """將浮點值限制在 [lo, hi] 範圍內 / Clamp float to [lo, hi]."""
    return max(lo, min(hi, value))


# ---------------------------------------------------------------------------
# Behavioral → Emotion Mapping Table
# ---------------------------------------------------------------------------

BEHAVIORAL_EMOTION_MAP: Dict[str, Dict[str, Any]] = {
    "slow_typing_high_errors": {
        "description_zh": "慢速打字 + 高錯誤率 — 認知疲勞/抑鬱",
        "description_en": "Slow typing + high errors — cognitive fatigue / depression",
        "emotion": "PANIC",
        "valence": -0.5,
        "arousal": 0.3,
        "confidence": 0.6,
    },
    "fast_erratic_typing": {
        "description_zh": "快速不穩定打字 (高節奏變異) — 挫折",
        "description_en": "Fast erratic typing (high rhythm variability) — frustration",
        "emotion": "RAGE",
        "valence": -0.7,
        "arousal": 0.8,
        "confidence": 0.7,
    },
    "slow_scrolling_long_pauses": {
        "description_zh": "慢速滾動 + 長停頓 — 抑鬱認知",
        "description_en": "Slow scrolling + long pauses — depressive cognition",
        "emotion": "PANIC",
        "valence": -0.4,
        "arousal": 0.2,
        "confidence": 0.5,
    },
    "erratic_scrolling_high_jerk": {
        "description_zh": "不穩定滾動 + 高急動度 — 挫折",
        "description_en": "Erratic scrolling + high jerk — frustration",
        "emotion": "RAGE",
        "valence": -0.6,
        "arousal": 0.7,
        "confidence": 0.65,
    },
    "high_social_late_night": {
        "description_zh": "高社交媒體 + 深夜使用 — SEEKING 適應不良 (抑鬱風險)",
        "description_en": "High social media + late night — maladaptive SEEKING (depression risk)",
        "emotion": "SEEKING",
        "valence": -0.3,
        "arousal": 0.5,
        "confidence": 0.55,
    },
    "low_app_diversity": {
        "description_zh": "低 App 多樣性 — 社交退縮",
        "description_en": "Low app diversity — social withdrawal",
        "emotion": "PANIC",
        "valence": -0.4,
        "arousal": 0.2,
        "confidence": 0.5,
    },
}

# Emotion string → PulseType lookup
_EMOTION_TO_PULSE: Dict[str, PulseType] = {
    "SEEKING": PulseType.SEEKING,
    "RAGE": PulseType.RAGE,
    "FEAR": PulseType.FEAR,
    "LUST": PulseType.LUST,
    "CARE": PulseType.CARE,
    "PANIC": PulseType.PANIC,
    "PLAY": PulseType.PLAY,
    "NEUTRAL": PulseType.NEUTRAL,
}


# ---------------------------------------------------------------------------
# Data Classes — Input Events
# ---------------------------------------------------------------------------

@dataclass
class KeyEvent:
    """鍵盤事件 / Keyboard event (press or release)."""
    key: str
    timestamp: float          # seconds since epoch
    event_type: str           # "press" or "release"

    def __post_init__(self) -> None:
        if self.event_type not in ("press", "release"):
            raise ValueError(
                f"event_type must be 'press' or 'release', got {self.event_type!r}"
            )
        if self.timestamp < 0:
            raise ValueError(f"timestamp must be >= 0, got {self.timestamp}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "timestamp": self.timestamp,
            "event_type": self.event_type,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KeyEvent":
        return cls(
            key=data["key"],
            timestamp=data["timestamp"],
            event_type=data["event_type"],
        )


@dataclass
class ScrollEvent:
    """滾動/觸控事件 / Scroll or touch event."""
    timestamp: float
    delta_y: float            # positive = scroll down
    velocity: float           # pixels per second

    def __post_init__(self) -> None:
        if self.timestamp < 0:
            raise ValueError(f"timestamp must be >= 0, got {self.timestamp}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "delta_y": self.delta_y,
            "velocity": self.velocity,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScrollEvent":
        return cls(
            timestamp=data["timestamp"],
            delta_y=data["delta_y"],
            velocity=data["velocity"],
        )


@dataclass
class AppUsageData:
    """App 使用數據 / Application usage data."""
    social_media_minutes: float
    late_night_screen_minutes: float   # screen time after 23:00
    app_diversity_score: float         # 0.0-1.0, number of distinct apps used
    notification_interaction_rate: float  # 0.0-1.0

    def __post_init__(self) -> None:
        if self.social_media_minutes < 0:
            raise ValueError(
                f"social_media_minutes must be >= 0, got {self.social_media_minutes}"
            )
        if self.late_night_screen_minutes < 0:
            raise ValueError(
                f"late_night_screen_minutes must be >= 0, got {self.late_night_screen_minutes}"
            )
        if not 0.0 <= self.app_diversity_score <= 1.0:
            raise ValueError(
                f"app_diversity_score must be in [0, 1], got {self.app_diversity_score}"
            )
        if not 0.0 <= self.notification_interaction_rate <= 1.0:
            raise ValueError(
                f"notification_interaction_rate must be in [0, 1], got {self.notification_interaction_rate}"
            )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "social_media_minutes": self.social_media_minutes,
            "late_night_screen_minutes": self.late_night_screen_minutes,
            "app_diversity_score": self.app_diversity_score,
            "notification_interaction_rate": self.notification_interaction_rate,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AppUsageData":
        return cls(
            social_media_minutes=data["social_media_minutes"],
            late_night_screen_minutes=data["late_night_screen_minutes"],
            app_diversity_score=data["app_diversity_score"],
            notification_interaction_rate=data["notification_interaction_rate"],
        )


# ---------------------------------------------------------------------------
# Data Classes — Computed Metrics
# ---------------------------------------------------------------------------

@dataclass
class KeystrokeMetrics:
    """鍵盤動態指標 / Keystroke dynamics metrics."""
    typing_speed_wpm: float          # words per minute
    dwell_time_mean: float           # ms, key hold duration
    flight_time_mean: float          # ms, interval between keys
    error_rate: float                # 0.0-1.0, backspace frequency
    rhythm_variability: float        # coefficient of variation of flight times

    def __post_init__(self) -> None:
        if self.typing_speed_wpm < 0:
            raise ValueError(
                f"typing_speed_wpm must be >= 0, got {self.typing_speed_wpm}"
            )
        if self.dwell_time_mean < 0:
            raise ValueError(
                f"dwell_time_mean must be >= 0, got {self.dwell_time_mean}"
            )
        if self.flight_time_mean < 0:
            raise ValueError(
                f"flight_time_mean must be >= 0, got {self.flight_time_mean}"
            )
        if not 0.0 <= self.error_rate <= 1.0:
            raise ValueError(
                f"error_rate must be in [0, 1], got {self.error_rate}"
            )
        if self.rhythm_variability < 0:
            raise ValueError(
                f"rhythm_variability must be >= 0, got {self.rhythm_variability}"
            )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "typing_speed_wpm": self.typing_speed_wpm,
            "dwell_time_mean": self.dwell_time_mean,
            "flight_time_mean": self.flight_time_mean,
            "error_rate": self.error_rate,
            "rhythm_variability": self.rhythm_variability,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KeystrokeMetrics":
        return cls(
            typing_speed_wpm=data["typing_speed_wpm"],
            dwell_time_mean=data["dwell_time_mean"],
            flight_time_mean=data["flight_time_mean"],
            error_rate=data["error_rate"],
            rhythm_variability=data["rhythm_variability"],
        )


@dataclass
class ScrollMetrics:
    """滾動/觸控行為指標 / Scroll/touch behavior metrics."""
    scroll_velocity: float           # average pixels per second
    scroll_jerk: float               # acceleration changes (erratic = frustrated)
    tap_frequency: float             # taps per minute
    session_duration: float          # seconds

    def __post_init__(self) -> None:
        if self.scroll_velocity < 0:
            raise ValueError(
                f"scroll_velocity must be >= 0, got {self.scroll_velocity}"
            )
        if self.scroll_jerk < 0:
            raise ValueError(
                f"scroll_jerk must be >= 0, got {self.scroll_jerk}"
            )
        if self.tap_frequency < 0:
            raise ValueError(
                f"tap_frequency must be >= 0, got {self.tap_frequency}"
            )
        if self.session_duration < 0:
            raise ValueError(
                f"session_duration must be >= 0, got {self.session_duration}"
            )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scroll_velocity": self.scroll_velocity,
            "scroll_jerk": self.scroll_jerk,
            "tap_frequency": self.tap_frequency,
            "session_duration": self.session_duration,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScrollMetrics":
        return cls(
            scroll_velocity=data["scroll_velocity"],
            scroll_jerk=data["scroll_jerk"],
            tap_frequency=data["tap_frequency"],
            session_duration=data["session_duration"],
        )


@dataclass
class EmoHandResult:
    """EmoHand 行為分析結果 / EmoHand behavioral analysis result.

    整合鍵盤、滾動、App 使用三通道的行為分析結果，
    輸出主導情感 (Panksepp 系統)、效價、喚醒度與信心值。
    """
    keystroke: Optional[KeystrokeMetrics]
    scroll: Optional[ScrollMetrics]
    app_usage: Optional[AppUsageData]
    dominant_emotion: str            # Panksepp system name
    valence: float                   # -1.0 to 1.0
    arousal: float                   # -1.0 to 1.0
    confidence: float                # 0.0 to 1.0
    timestamp: datetime

    def __post_init__(self) -> None:
        if self.dominant_emotion not in _EMOTION_TO_PULSE:
            raise ValueError(
                f"dominant_emotion must be a valid Panksepp system, "
                f"got {self.dominant_emotion!r}"
            )
        if not -1.0 <= self.valence <= 1.0:
            raise ValueError(
                f"valence must be in [-1, 1], got {self.valence}"
            )
        if not -1.0 <= self.arousal <= 1.0:
            raise ValueError(
                f"arousal must be in [-1, 1], got {self.arousal}"
            )
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                f"confidence must be in [0, 1], got {self.confidence}"
            )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "keystroke": self.keystroke.to_dict() if self.keystroke else None,
            "scroll": self.scroll.to_dict() if self.scroll else None,
            "app_usage": self.app_usage.to_dict() if self.app_usage else None,
            "dominant_emotion": self.dominant_emotion,
            "valence": self.valence,
            "arousal": self.arousal,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EmoHandResult":
        return cls(
            keystroke=KeystrokeMetrics.from_dict(data["keystroke"]) if data.get("keystroke") else None,
            scroll=ScrollMetrics.from_dict(data["scroll"]) if data.get("scroll") else None,
            app_usage=AppUsageData.from_dict(data["app_usage"]) if data.get("app_usage") else None,
            dominant_emotion=data["dominant_emotion"],
            valence=data["valence"],
            arousal=data["arousal"],
            confidence=data["confidence"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
        )

    def to_pulse(self) -> Pulse:
        """將分析結果轉換為 EmoGlyph Pulse / Convert result to Pulse object."""
        pulse_type = _EMOTION_TO_PULSE.get(self.dominant_emotion, PulseType.NEUTRAL)
        # Derive dominance from valence: negative valence → submissive, positive → dominant
        dominance = _clamp(self.valence * 0.5, -1.0, 1.0)
        return Pulse(
            pulse_type=pulse_type,
            valence=_clamp(self.valence, -1.0, 1.0),
            arousal=_clamp(self.arousal, -1.0, 1.0),
            dominance=dominance,
            intensity=_clamp(self.confidence, 0.0, 1.0),
        )


# ---------------------------------------------------------------------------
# Main Engine
# ---------------------------------------------------------------------------

class EmoHandEngine:
    """EmoHand (手) 行為引擎 / Behavioral Engine.

    中醫臟腑: 肺 (Lung) — 主氣、主皮毛，與手部行為相應
    Panksepp 系統: PLAY / RAGE — 手部行為反映遊戲性與挫折感

    三通道分析:
    1. analyze_keystroke — 鍵盤動態 → 情感狀態
    2. analyze_scroll — 滾動/觸控 → 挫折/抑鬱
    3. analyze_app_usage — App 使用模式 → 心情指標

    使用方式:
        engine = EmoHandEngine()
        result = engine.analyze_keystroke(key_events)
        pulse = engine.to_pulse(result)
    """

    # Keystroke thresholds
    SLOW_TYPING_WPM = 30.0          # below this = slow typing
    HIGH_ERROR_RATE = 0.08          # above this = high errors
    HIGH_RHYTHM_VARIABILITY = 0.5   # above this = erratic rhythm
    FAST_TYPING_WPM = 60.0         # above this = fast typing

    # Scroll thresholds
    SLOW_SCROLL_VELOCITY = 50.0     # pixels/sec, below = slow
    HIGH_SCROLL_JERK = 5000.0       # high jerk = erratic
    HIGH_TAP_FREQUENCY = 30.0       # taps/min, above = agitated

    # App usage thresholds
    HIGH_SOCIAL_MEDIA_MINUTES = 120.0   # 2+ hours
    HIGH_LATE_NIGHT_MINUTES = 60.0      # 1+ hour after 23:00
    LOW_APP_DIVERSITY = 0.3             # below = narrow usage

    def __init__(self) -> None:
        """初始化 EmoHand 引擎 / Initialize the EmoHand engine."""
        pass

    # ------------------------------------------------------------------
    # Keystroke Analysis
    # ------------------------------------------------------------------

    def analyze_keystroke(self, key_events: List[KeyEvent]) -> EmoHandResult:
        """分析鍵盤動態 / Analyze keystroke dynamics.

        從按鍵事件序列計算:
        - typing_speed_wpm: 每分鐘字數
        - dwell_time_mean: 平均按鍵持續時間 (ms)
        - flight_time_mean: 平均鍵間間隔 (ms)
        - error_rate: 退格鍵頻率
        - rhythm_variability: 鍵間間隔的變異係數

        Args:
            key_events: 按鍵事件列表，需包含 press 和 release 事件

        Returns:
            EmoHandResult 包含鍵盤指標和推斷的情感狀態
        """
        metrics = self._compute_keystroke_metrics(key_events)
        dominant_emotion, valence, arousal, confidence = self.classify_emotion(
            keystroke=metrics, scroll=None, app_usage=None,
        )
        return EmoHandResult(
            keystroke=metrics,
            scroll=None,
            app_usage=None,
            dominant_emotion=dominant_emotion,
            valence=valence,
            arousal=arousal,
            confidence=confidence,
            timestamp=datetime.now(timezone.utc),
        )

    def _compute_keystroke_metrics(self, key_events: List[KeyEvent]) -> KeystrokeMetrics:
        """從按鍵事件計算鍵盤指標 / Compute keystroke metrics from key events."""
        if not key_events:
            return KeystrokeMetrics(
                typing_speed_wpm=0.0,
                dwell_time_mean=0.0,
                flight_time_mean=0.0,
                error_rate=0.0,
                rhythm_variability=0.0,
            )

        # Separate press and release events
        presses: List[KeyEvent] = [e for e in key_events if e.event_type == "press"]
        releases: List[KeyEvent] = [e for e in key_events if e.event_type == "release"]

        # Compute typing speed (WPM)
        # Assume average word = 5 characters; count unique press events
        total_chars = len(presses)
        if total_chars < 2:
            typing_speed_wpm = 0.0
        else:
            time_span = presses[-1].timestamp - presses[0].timestamp
            if time_span <= 0:
                typing_speed_wpm = 0.0
            else:
                words = total_chars / 5.0
                minutes = time_span / 60.0
                typing_speed_wpm = words / minutes if minutes > 0 else 0.0

        # Compute dwell times (press → release for same key)
        dwell_times: List[float] = []
        # Build a map: key → list of (press_time, release_time)
        press_map: Dict[str, List[float]] = {}
        for p in presses:
            press_map.setdefault(p.key, []).append(p.timestamp)

        release_map: Dict[str, List[float]] = {}
        for r in releases:
            release_map.setdefault(r.key, []).append(r.timestamp)

        for key in press_map:
            p_times = sorted(press_map[key])
            r_times = sorted(release_map.get(key, []))
            for i, pt in enumerate(p_times):
                # Find the first release after this press
                matching = [rt for rt in r_times if rt > pt]
                if matching:
                    dwell_times.append((matching[0] - pt) * 1000.0)  # convert to ms

        dwell_time_mean = sum(dwell_times) / len(dwell_times) if dwell_times else 0.0

        # Compute flight times (release → next press)
        flight_times: List[float] = []
        sorted_presses = sorted(presses, key=lambda e: e.timestamp)
        for i in range(1, len(sorted_presses)):
            ft = (sorted_presses[i].timestamp - sorted_presses[i - 1].timestamp) * 1000.0
            if ft > 0:
                flight_times.append(ft)

        flight_time_mean = sum(flight_times) / len(flight_times) if flight_times else 0.0

        # Compute rhythm variability (CV of flight times)
        if len(flight_times) >= 2 and flight_time_mean > 0:
            variance = sum((ft - flight_time_mean) ** 2 for ft in flight_times) / len(flight_times)
            std_dev = sqrt(variance)
            rhythm_variability = std_dev / flight_time_mean
        else:
            rhythm_variability = 0.0

        # Compute error rate (backspace count / total key count)
        backspace_count = sum(
            1 for e in presses
            if e.key.lower() in ("backspace", "delete", "back")
        )
        error_rate = backspace_count / total_chars if total_chars > 0 else 0.0

        return KeystrokeMetrics(
            typing_speed_wpm=typing_speed_wpm,
            dwell_time_mean=dwell_time_mean,
            flight_time_mean=flight_time_mean,
            error_rate=_clamp(error_rate, 0.0, 1.0),
            rhythm_variability=rhythm_variability,
        )

    # ------------------------------------------------------------------
    # Scroll Analysis
    # ------------------------------------------------------------------

    def analyze_scroll(self, scroll_events: List[ScrollEvent]) -> EmoHandResult:
        """分析滾動/觸控行為 / Analyze scroll/touch behavior.

        從滾動事件序列計算:
        - scroll_velocity: 平均滾動速度 (pixels/sec)
        - scroll_jerk: 加速度變化 (不穩定 = 挫折)
        - tap_frequency: 每分鐘點擊次數
        - session_duration: 會話持續時間 (秒)

        Args:
            scroll_events: 滾動事件列表

        Returns:
            EmoHandResult 包含滾動指標和推斷的情感狀態
        """
        metrics = self._compute_scroll_metrics(scroll_events)
        dominant_emotion, valence, arousal, confidence = self.classify_emotion(
            keystroke=None, scroll=metrics, app_usage=None,
        )
        return EmoHandResult(
            keystroke=None,
            scroll=metrics,
            app_usage=None,
            dominant_emotion=dominant_emotion,
            valence=valence,
            arousal=arousal,
            confidence=confidence,
            timestamp=datetime.now(timezone.utc),
        )

    def _compute_scroll_metrics(self, scroll_events: List[ScrollEvent]) -> ScrollMetrics:
        """從滾動事件計算滾動指標 / Compute scroll metrics from scroll events."""
        if not scroll_events:
            return ScrollMetrics(
                scroll_velocity=0.0,
                scroll_jerk=0.0,
                tap_frequency=0.0,
                session_duration=0.0,
            )

        # Session duration
        timestamps = [e.timestamp for e in scroll_events]
        session_duration = max(timestamps) - min(timestamps) if len(timestamps) >= 2 else 0.0

        # Average scroll velocity (absolute delta_y / time_delta)
        velocities: List[float] = []
        for i in range(1, len(scroll_events)):
            dt = scroll_events[i].timestamp - scroll_events[i - 1].timestamp
            if dt > 0:
                v = abs(scroll_events[i].delta_y) / dt
                velocities.append(v)

        scroll_velocity = sum(velocities) / len(velocities) if velocities else 0.0

        # Scroll jerk: variance of velocity changes
        if len(velocities) >= 2:
            velocity_changes = [
                velocities[i] - velocities[i - 1]
                for i in range(1, len(velocities))
            ]
            mean_change = sum(velocity_changes) / len(velocity_changes)
            jerk_variance = sum(
                (vc - mean_change) ** 2 for vc in velocity_changes
            ) / len(velocity_changes)
            scroll_jerk = sqrt(jerk_variance)
        else:
            scroll_jerk = 0.0

        # Tap frequency (events per minute)
        if session_duration > 0:
            tap_frequency = len(scroll_events) / (session_duration / 60.0)
        else:
            tap_frequency = 0.0

        return ScrollMetrics(
            scroll_velocity=scroll_velocity,
            scroll_jerk=scroll_jerk,
            tap_frequency=tap_frequency,
            session_duration=session_duration,
        )

    # ------------------------------------------------------------------
    # App Usage Analysis
    # ------------------------------------------------------------------

    def analyze_app_usage(self, usage_data: AppUsageData) -> EmoHandResult:
        """分析 App 使用模式 / Analyze app usage patterns.

        從 App 使用數據推斷情感狀態:
        - 高社交媒體 + 深夜使用 → SEEKING 適應不良
        - 低 App 多樣性 → PANIC (社交退縮)

        Args:
            usage_data: App 使用數據

        Returns:
            EmoHandResult 包含 App 使用指標和推斷的情感狀態
        """
        dominant_emotion, valence, arousal, confidence = self.classify_emotion(
            keystroke=None, scroll=None, app_usage=usage_data,
        )
        return EmoHandResult(
            keystroke=None,
            scroll=None,
            app_usage=usage_data,
            dominant_emotion=dominant_emotion,
            valence=valence,
            arousal=arousal,
            confidence=confidence,
            timestamp=datetime.now(timezone.utc),
        )

    # ------------------------------------------------------------------
    # Emotion Classification
    # ------------------------------------------------------------------

    def classify_emotion(
        self,
        keystroke: Optional[KeystrokeMetrics],
        scroll: Optional[ScrollMetrics],
        app_usage: Optional[AppUsageData],
    ) -> Tuple[str, float, float, float]:
        """綜合分類情感狀態 / Classify emotional state from all available channels.

        基於行為→情感映射表，從各通道指標推斷主導情感。
        當多通道同時啟用時，取信心值最高的通道作為主導。

        Args:
            keystroke: 鍵盤指標 (可選)
            scroll: 滾動指標 (可選)
            app_usage: App 使用數據 (可選)

        Returns:
            (dominant_emotion, valence, arousal, confidence) 元組
        """
        candidates: List[Tuple[str, float, float, float]] = []

        # Keystroke channel
        if keystroke is not None:
            ks_emotion, ks_v, ks_a, ks_c = self._classify_keystroke(keystroke)
            candidates.append((ks_emotion, ks_v, ks_a, ks_c))

        # Scroll channel
        if scroll is not None:
            sc_emotion, sc_v, sc_a, sc_c = self._classify_scroll(scroll)
            candidates.append((sc_emotion, sc_v, sc_a, sc_c))

        # App usage channel
        if app_usage is not None:
            au_emotion, au_v, au_a, au_c = self._classify_app_usage(app_usage)
            candidates.append((au_emotion, au_v, au_a, au_c))

        if not candidates:
            return ("NEUTRAL", 0.0, 0.0, 0.0)

        # Pick the candidate with highest confidence
        best = max(candidates, key=lambda c: c[3])

        # If multiple channels, blend valence/arousal weighted by confidence
        if len(candidates) > 1:
            total_conf = sum(c[3] for c in candidates)
            if total_conf > 0:
                blended_v = sum(c[1] * c[3] for c in candidates) / total_conf
                blended_a = sum(c[2] * c[3] for c in candidates) / total_conf
                return (
                    best[0],
                    _clamp(blended_v, -1.0, 1.0),
                    _clamp(blended_a, -1.0, 1.0),
                    best[3],
                )

        return best

    def _classify_keystroke(
        self, ks: KeystrokeMetrics
    ) -> Tuple[str, float, float, float]:
        """從鍵盤指標分類情感 / Classify emotion from keystroke metrics."""
        # Slow typing + high errors → PANIC
        if ks.typing_speed_wpm < self.SLOW_TYPING_WPM and ks.error_rate > self.HIGH_ERROR_RATE:
            mapping = BEHAVIORAL_EMOTION_MAP["slow_typing_high_errors"]
            # Scale confidence by how extreme the values are
            speed_factor = 1.0 - (ks.typing_speed_wpm / self.SLOW_TYPING_WPM)
            error_factor = ks.error_rate / max(self.HIGH_ERROR_RATE * 2, 0.01)
            confidence = _clamp(
                mapping["confidence"] * (0.5 + 0.5 * min(speed_factor + error_factor, 1.0)),
                0.0, 1.0,
            )
            return (mapping["emotion"], mapping["valence"], mapping["arousal"], confidence)

        # Fast erratic typing → RAGE
        if ks.typing_speed_wpm > self.FAST_TYPING_WPM and ks.rhythm_variability > self.HIGH_RHYTHM_VARIABILITY:
            mapping = BEHAVIORAL_EMOTION_MAP["fast_erratic_typing"]
            speed_factor = min(ks.typing_speed_wpm / 120.0, 1.0)
            rhythm_factor = min(ks.rhythm_variability / 1.0, 1.0)
            confidence = _clamp(
                mapping["confidence"] * (0.5 + 0.5 * min(speed_factor + rhythm_factor, 1.0)),
                0.0, 1.0,
            )
            return (mapping["emotion"], mapping["valence"], mapping["arousal"], confidence)

        # Slow typing alone → mild PANIC
        if ks.typing_speed_wpm < self.SLOW_TYPING_WPM:
            mapping = BEHAVIORAL_EMOTION_MAP["slow_typing_high_errors"]
            confidence = _clamp(mapping["confidence"] * 0.5, 0.0, 1.0)
            return (mapping["emotion"], mapping["valence"] * 0.6, mapping["arousal"] * 0.6, confidence)

        # High errors alone → mild RAGE
        if ks.error_rate > self.HIGH_ERROR_RATE:
            mapping = BEHAVIORAL_EMOTION_MAP["fast_erratic_typing"]
            confidence = _clamp(mapping["confidence"] * 0.5, 0.0, 1.0)
            return (mapping["emotion"], mapping["valence"] * 0.5, mapping["arousal"] * 0.5, confidence)

        # Default: PLAY (normal typing behavior)
        return ("PLAY", 0.3, 0.2, 0.3)

    def _classify_scroll(
        self, sc: ScrollMetrics
    ) -> Tuple[str, float, float, float]:
        """從滾動指標分類情感 / Classify emotion from scroll metrics."""
        # Erratic scrolling + high jerk → RAGE
        if sc.scroll_jerk > self.HIGH_SCROLL_JERK:
            mapping = BEHAVIORAL_EMOTION_MAP["erratic_scrolling_high_jerk"]
            jerk_factor = min(sc.scroll_jerk / (self.HIGH_SCROLL_JERK * 2), 1.0)
            confidence = _clamp(
                mapping["confidence"] * (0.5 + 0.5 * jerk_factor),
                0.0, 1.0,
            )
            return (mapping["emotion"], mapping["valence"], mapping["arousal"], confidence)

        # Slow scrolling → PANIC
        if sc.scroll_velocity < self.SLOW_SCROLL_VELOCITY and sc.session_duration > 0:
            mapping = BEHAVIORAL_EMOTION_MAP["slow_scrolling_long_pauses"]
            slowness_factor = 1.0 - (sc.scroll_velocity / self.SLOW_SCROLL_VELOCITY)
            confidence = _clamp(
                mapping["confidence"] * (0.5 + 0.5 * slowness_factor),
                0.0, 1.0,
            )
            return (mapping["emotion"], mapping["valence"], mapping["arousal"], confidence)

        # High tap frequency → mild RAGE (agitation)
        if sc.tap_frequency > self.HIGH_TAP_FREQUENCY:
            mapping = BEHAVIORAL_EMOTION_MAP["erratic_scrolling_high_jerk"]
            tap_factor = min(sc.tap_frequency / (self.HIGH_TAP_FREQUENCY * 2), 1.0)
            confidence = _clamp(mapping["confidence"] * 0.4 * tap_factor, 0.0, 1.0)
            return (mapping["emotion"], mapping["valence"] * 0.5, mapping["arousal"] * 0.6, confidence)

        # Default: PLAY (normal scrolling)
        return ("PLAY", 0.2, 0.1, 0.3)

    def _classify_app_usage(
        self, au: AppUsageData
    ) -> Tuple[str, float, float, float]:
        """從 App 使用數據分類情感 / Classify emotion from app usage data."""
        # High social media + late night → maladaptive SEEKING
        if (au.social_media_minutes > self.HIGH_SOCIAL_MEDIA_MINUTES
                and au.late_night_screen_minutes > self.HIGH_LATE_NIGHT_MINUTES):
            mapping = BEHAVIORAL_EMOTION_MAP["high_social_late_night"]
            social_factor = min(au.social_media_minutes / 300.0, 1.0)
            night_factor = min(au.late_night_screen_minutes / 120.0, 1.0)
            confidence = _clamp(
                mapping["confidence"] * (0.5 + 0.5 * min(social_factor + night_factor, 1.0)),
                0.0, 1.0,
            )
            return (mapping["emotion"], mapping["valence"], mapping["arousal"], confidence)

        # Low app diversity → PANIC (social withdrawal)
        if au.app_diversity_score < self.LOW_APP_DIVERSITY:
            mapping = BEHAVIORAL_EMOTION_MAP["low_app_diversity"]
            diversity_factor = 1.0 - (au.app_diversity_score / self.LOW_APP_DIVERSITY)
            confidence = _clamp(
                mapping["confidence"] * (0.5 + 0.5 * diversity_factor),
                0.0, 1.0,
            )
            return (mapping["emotion"], mapping["valence"], mapping["arousal"], confidence)

        # High social media alone → mild SEEKING
        if au.social_media_minutes > self.HIGH_SOCIAL_MEDIA_MINUTES:
            mapping = BEHAVIORAL_EMOTION_MAP["high_social_late_night"]
            confidence = _clamp(mapping["confidence"] * 0.4, 0.0, 1.0)
            return (mapping["emotion"], mapping["valence"] * 0.5, mapping["arousal"] * 0.5, confidence)

        # High late night alone → mild PANIC
        if au.late_night_screen_minutes > self.HIGH_LATE_NIGHT_MINUTES:
            mapping = BEHAVIORAL_EMOTION_MAP["low_app_diversity"]
            confidence = _clamp(mapping["confidence"] * 0.4, 0.0, 1.0)
            return (mapping["emotion"], mapping["valence"] * 0.5, mapping["arousal"] * 0.5, confidence)

        # Default: PLAY (healthy usage)
        return ("PLAY", 0.2, 0.1, 0.3)

    # ------------------------------------------------------------------
    # Pulse Conversion
    # ------------------------------------------------------------------

    def to_pulse(self, result: EmoHandResult) -> Pulse:
        """將 EmoHandResult 轉換為 Pulse / Convert EmoHandResult to Pulse object.

        Args:
            result: EmoHand 行為分析結果

        Returns:
            Pulse 物件，包含情感類型、效價、喚醒度、支配度與強度
        """
        return result.to_pulse()
