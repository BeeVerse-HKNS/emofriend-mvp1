"""EmoBody (身) Physical Engine — 身體感知引擎

七竅 (Seven Apertures) 多模態感官系統 — 身 (Body) 端

TCM 臟腑: 腎+脾 (Kidney+Spleen)
Panksepp 系統: SEEKING / LUST

3-in-1 感知能力:
1. Posture Analysis — 網絡攝像頭姿態估計 → 抑鬱姿態偵測
2. Gait Analysis — 加速度計步態模式 → 精神運動評估
3. Circadian Rhythm — 睡眠/清醒 + 光照 + 社會節律 → 情緒預測

臨床映射:
- 姿態 → PANIC/SEEKING (DSM-5 抑鬱姿態)
- 步態 → PANIC/FEAR (DSM-5 精神運動遲緩)
- 節律 → PANIC/CARE (晝夜節律紊亂、季節性情緒)

EmoGlyph 整合點: Pulse Layer — 轉換為 Pulse 信號供上層共振使用

設計原則:
- 自包含，無外部依賴 (僅 stdlib)
- 後端為抽象介面，實際感測器由外部適配器注入
- 數值穩定 (所有浮點值使用 _clamp)
- 可解釋 (每個映射都有臨床依據)
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

from ..pulse import Pulse, PulseType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """將浮點值限制在 [lo, hi] 區間內"""
    return max(lo, min(hi, float(value)))


# ---------------------------------------------------------------------------
# Panksepp emotion name → PulseType lookup
# ---------------------------------------------------------------------------

_EMOTION_TO_PULSE: Dict[str, PulseType] = {
    "SEEKING": PulseType.SEEKING,
    "RAGE":    PulseType.RAGE,
    "FEAR":    PulseType.FEAR,
    "LUST":    PulseType.LUST,
    "CARE":    PulseType.CARE,
    "PANIC":   PulseType.PANIC,
    "PLAY":    PulseType.PLAY,
}


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

class Chronotype(Enum):
    """晝夜節律型態 / Chronotype classification"""
    MORNING = "morning"          # 晨型人 (雲雀型)
    INTERMEDIATE = "intermediate"  # 中間型
    EVENING = "evening"          # 夜型人 (貓頭鷹型)


@dataclass
class PostureMetrics:
    """姿態指標 / Posture analysis metrics

    基於網絡攝像頭姿態估計，偵測抑鬱姿態 (depressive posture)。

    Clinical reference:
    - DSM-5 抑鬱發作可伴隨姿態改變 (slouched, forward head)
    - 前傾頭角度 >15° 為 forward head posture (FHP)
    - 肩膀不對齊與慢性壓力相關
    """
    posture_score: float           # 0.0 (slouched) to 1.0 (upright)
    forward_head_angle: float      # degrees (normal: <15°, forward head: >15°)
    shoulder_alignment: float      # 0.0 (uneven) to 1.0 (aligned)
    fidgeting_rate: float          # movements per minute

    def __post_init__(self) -> None:
        self.posture_score = _clamp(self.posture_score, 0.0, 1.0)
        self.forward_head_angle = max(0.0, float(self.forward_head_angle))
        self.shoulder_alignment = _clamp(self.shoulder_alignment, 0.0, 1.0)
        self.fidgeting_rate = max(0.0, float(self.fidgeting_rate))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "posture_score": self.posture_score,
            "forward_head_angle": self.forward_head_angle,
            "shoulder_alignment": self.shoulder_alignment,
            "fidgeting_rate": self.fidgeting_rate,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PostureMetrics":
        return cls(
            posture_score=data["posture_score"],
            forward_head_angle=data["forward_head_angle"],
            shoulder_alignment=data["shoulder_alignment"],
            fidgeting_rate=data["fidgeting_rate"],
        )


@dataclass
class GaitMetrics:
    """步態指標 / Gait analysis metrics

    基於加速度計步態模式，評估精神運動狀態 (psychomotor assessment)。

    Clinical reference:
    - DSM-5 精神運動遲緩 (psychomotor retardation): 步速 <0.8 m/s
    - 正常步速: 1.0-1.4 m/s
    - 步態變異性 >0.05 與焦慮/跌倒風險相關
    - 手臂擺幅減少與抑鬱相關
    """
    walking_speed: float           # m/s (normal: 1.0-1.4)
    stride_regularity: float       # 0.0 to 1.0
    arm_swing_amplitude: float     # degrees (normal: 20-40°)
    gait_variability: float        # coefficient of variation (normal: <0.05)

    def __post_init__(self) -> None:
        self.walking_speed = max(0.0, float(self.walking_speed))
        self.stride_regularity = _clamp(self.stride_regularity, 0.0, 1.0)
        self.arm_swing_amplitude = max(0.0, float(self.arm_swing_amplitude))
        self.gait_variability = max(0.0, float(self.gait_variability))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "walking_speed": self.walking_speed,
            "stride_regularity": self.stride_regularity,
            "arm_swing_amplitude": self.arm_swing_amplitude,
            "gait_variability": self.gait_variability,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GaitMetrics":
        return cls(
            walking_speed=data["walking_speed"],
            stride_regularity=data["stride_regularity"],
            arm_swing_amplitude=data["arm_swing_amplitude"],
            gait_variability=data["gait_variability"],
        )


@dataclass
class CircadianMetrics:
    """晝夜節律指標 / Circadian rhythm metrics

    基於睡眠/清醒週期、光照暴露、社會節律穩定性，預測情緒狀態。

    Clinical reference:
    - 節律紊亂與雙相情感障礙、重度抑鬱相關
    - 光照不足 (<0.3) 為季節性情緒障礙 (SAD) 風險因子
    - 社會節律不穩定 (<0.4) 為雙相/抑鬱復發預測因子
    - Interpersonal and Social Rhythm Theory (IPSRT)
    """
    sleep_regularity: float        # 0.0 to 1.0
    social_rhythm_stability: float # 0.0 to 1.0, meal/activity timing consistency
    light_exposure_score: float    # 0.0 to 1.0, daylight adequacy
    chronotype: Chronotype
    circadian_disruption: float    # 0.0 to 1.0

    def __post_init__(self) -> None:
        self.sleep_regularity = _clamp(self.sleep_regularity, 0.0, 1.0)
        self.social_rhythm_stability = _clamp(self.social_rhythm_stability, 0.0, 1.0)
        self.light_exposure_score = _clamp(self.light_exposure_score, 0.0, 1.0)
        if isinstance(self.chronotype, str):
            self.chronotype = Chronotype(self.chronotype)
        self.circadian_disruption = _clamp(self.circadian_disruption, 0.0, 1.0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sleep_regularity": self.sleep_regularity,
            "social_rhythm_stability": self.social_rhythm_stability,
            "light_exposure_score": self.light_exposure_score,
            "chronotype": self.chronotype.value,
            "circadian_disruption": self.circadian_disruption,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CircadianMetrics":
        ct = data["chronotype"]
        if isinstance(ct, str):
            ct = Chronotype(ct)
        return cls(
            sleep_regularity=data["sleep_regularity"],
            social_rhythm_stability=data["social_rhythm_stability"],
            light_exposure_score=data["light_exposure_score"],
            chronotype=ct,
            circadian_disruption=data["circadian_disruption"],
        )


@dataclass
class FallRiskAssessment:
    """跌倒風險評估 / Fall risk assessment for elderly mode

    整合步態與姿態信號，評估老年人跌倒風險。

    Attributes:
        risk_level: 風險等級 ("NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL")
        confidence: 置信度 (0.0 to 1.0)
        contributing_factors: 風險貢獻因素列表
        gait_anomaly: 是否偵測到步態異常
        posture_collapse: 是否偵測到姿態崩塌
        timestamp: 評估時間戳
    """
    risk_level: str
    confidence: float
    contributing_factors: List[str]
    gait_anomaly: bool
    posture_collapse: bool
    timestamp: datetime

    VALID_RISK_LEVELS = {"NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"}

    def __post_init__(self) -> None:
        if self.risk_level not in self.VALID_RISK_LEVELS:
            raise ValueError(
                f"risk_level must be one of {self.VALID_RISK_LEVELS}, "
                f"got '{self.risk_level}'"
            )
        self.confidence = _clamp(self.confidence, 0.0, 1.0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "risk_level": self.risk_level,
            "confidence": self.confidence,
            "contributing_factors": self.contributing_factors,
            "gait_anomaly": self.gait_anomaly,
            "posture_collapse": self.posture_collapse,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FallRiskAssessment":
        ts = data["timestamp"]
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
        return cls(
            risk_level=data["risk_level"],
            confidence=data["confidence"],
            contributing_factors=data["contributing_factors"],
            gait_anomaly=data["gait_anomaly"],
            posture_collapse=data["posture_collapse"],
            timestamp=ts,
        )


@dataclass
class CircadianAlert:
    """晝夜節律警報 / Circadian rhythm alert for elderly mode

    偵測晝夜節律異常並提供警報與建議。

    Attributes:
        alert_type: 警報類型 ("SLEEP_IRREGULARITY", "LOW_DAYLIGHT",
                    "SOCIAL_RHYTHM_DISRUPTION", "CIRCADIAN_DISRUPTION")
        severity: 嚴重程度 ("LOW", "MEDIUM", "HIGH")
        days_irregular: 不規律天數
        recommendation: 建議
        timestamp: 警報時間戳
    """
    alert_type: str
    severity: str
    days_irregular: int
    recommendation: str
    timestamp: datetime

    VALID_ALERT_TYPES = {"SLEEP_IRREGULARITY", "LOW_DAYLIGHT",
                         "SOCIAL_RHYTHM_DISRUPTION", "CIRCADIAN_DISRUPTION"}
    VALID_SEVERITIES = {"LOW", "MEDIUM", "HIGH"}

    def __post_init__(self) -> None:
        if self.alert_type not in self.VALID_ALERT_TYPES:
            raise ValueError(
                f"alert_type must be one of {self.VALID_ALERT_TYPES}, "
                f"got '{self.alert_type}'"
            )
        if self.severity not in self.VALID_SEVERITIES:
            raise ValueError(
                f"severity must be one of {self.VALID_SEVERITIES}, "
                f"got '{self.severity}'"
            )
        self.days_irregular = max(0, int(self.days_irregular))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_type": self.alert_type,
            "severity": self.severity,
            "days_irregular": self.days_irregular,
            "recommendation": self.recommendation,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CircadianAlert":
        ts = data["timestamp"]
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
        return cls(
            alert_type=data["alert_type"],
            severity=data["severity"],
            days_irregular=data["days_irregular"],
            recommendation=data["recommendation"],
            timestamp=ts,
        )


@dataclass
class EmoBodyResult:
    """身體感知綜合結果 / EmoBody composite result

    整合姿態、步態、節律三維度分析結果，
    輸出主導情緒 (Panksepp)、效價、喚醒度、置信度。

    Attributes:
        posture: 姿態分析結果 (可為 None，若未提供)
        gait: 步態分析結果 (可為 None，若未提供)
        circadian: 節律分析結果 (可為 None，若未提供)
        dominant_emotion: 主導 Panksepp 情感系統名稱
        valence: 效價 (-1.0 極度負面 to +1.0 極度正面)
        arousal: 喚醒度 (-1.0 低喚醒 to +1.0 高喚醒)
        confidence: 置信度 (0.0 to 1.0)
        timestamp: 結果時間戳
    """
    posture: Optional[PostureMetrics]
    gait: Optional[GaitMetrics]
    circadian: Optional[CircadianMetrics]
    dominant_emotion: str          # Panksepp system name
    valence: float                 # -1.0 to 1.0
    arousal: float                 # -1.0 to 1.0
    confidence: float              # 0.0 to 1.0
    timestamp: datetime

    def __post_init__(self) -> None:
        if self.dominant_emotion not in _EMOTION_TO_PULSE:
            raise ValueError(
                f"dominant_emotion must be one of {list(_EMOTION_TO_PULSE.keys())}, "
                f"got '{self.dominant_emotion}'"
            )
        self.valence = _clamp(self.valence, -1.0, 1.0)
        self.arousal = _clamp(self.arousal, -1.0, 1.0)
        self.confidence = _clamp(self.confidence, 0.0, 1.0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "posture": self.posture.to_dict() if self.posture else None,
            "gait": self.gait.to_dict() if self.gait else None,
            "circadian": self.circadian.to_dict() if self.circadian else None,
            "dominant_emotion": self.dominant_emotion,
            "valence": self.valence,
            "arousal": self.arousal,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EmoBodyResult":
        posture = PostureMetrics.from_dict(data["posture"]) if data.get("posture") else None
        gait = GaitMetrics.from_dict(data["gait"]) if data.get("gait") else None
        circadian = CircadianMetrics.from_dict(data["circadian"]) if data.get("circadian") else None
        ts = data["timestamp"]
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
        return cls(
            posture=posture,
            gait=gait,
            circadian=circadian,
            dominant_emotion=data["dominant_emotion"],
            valence=data["valence"],
            arousal=data["arousal"],
            confidence=data["confidence"],
            timestamp=ts,
        )

    def to_pulse(self) -> Pulse:
        """將結果轉換為 Pulse 信號 / Convert to Pulse for EmoGlyph integration"""
        pulse_type = _EMOTION_TO_PULSE.get(self.dominant_emotion, PulseType.NEUTRAL)
        # dominance derived from valence × arousal interaction
        dominance = _clamp(self.valence * 0.5 + self.arousal * 0.3, -1.0, 1.0)
        return Pulse(
            pulse_type=pulse_type,
            valence=self.valence,
            arousal=self.arousal,
            dominance=dominance,
            intensity=self.confidence,
        )


# ---------------------------------------------------------------------------
# Clinical Mapping Tables
# ---------------------------------------------------------------------------

# Posture → (emotion, valence, arousal, weight)
# 姿態 → 臨床映射 (DSM-5 depressive posture)
# 權重 (weight) 用於多維度融合時的加權
_POSTURE_MAPS: list[Tuple[str, float, float, float]] = []  # populated in _classify_posture


def _classify_posture(
    posture: PostureMetrics,
) -> Tuple[str, float, float, float]:
    """姿態 → 情感映射 / Posture to emotion classification

    Clinical mapping:
    - posture_score < 0.3 AND forward_head_angle > 30 → PANIC dorsal (V=-0.6, A=0.2)
      抑鬱姿態 (depressive posture)
    - posture_score 0.3-0.6 → PANIC mild (V=-0.3, A=0.3)
      輕度駝背 (mild slouching)
    - posture_score > 0.7 → SEEKING (V=+0.3, A=0.4)
      警覺/直立 (alert/upright)
    - High fidgeting (>10 movements/min) → RAGE/FEAR (V=-0.4, A=0.6)
      焦慮/不安 (anxiety/restlessness)

    Returns:
        (dominant_emotion, valence, arousal, confidence_weight)
    """
    # Check fidgeting first — anxiety overrides posture pattern
    if posture.fidgeting_rate > 10.0:
        return ("FEAR", -0.4, 0.6, 0.6)

    # Depressive posture: severe slouch + forward head
    if posture.posture_score < 0.3 and posture.forward_head_angle > 30.0:
        return ("PANIC", -0.6, 0.2, 0.8)

    # Mild slouching
    if posture.posture_score < 0.6:
        return ("PANIC", -0.3, 0.3, 0.5)

    # Alert / upright posture
    if posture.posture_score > 0.7:
        return ("SEEKING", 0.3, 0.4, 0.5)

    # Neutral zone (0.6-0.7)
    return ("NEUTRAL", 0.0, 0.0, 0.3)


def _classify_gait(
    gait: GaitMetrics,
) -> Tuple[str, float, float, float]:
    """步態 → 情感映射 / Gait to emotion classification

    Clinical mapping (DSM-5 psychomotor retardation):
    - walking_speed < 0.8 AND stride_regularity < 0.5 → PANIC (V=-0.6, A=0.2)
      ⚠️ 精神運動遲緩 (psychomotor retardation)
    - walking_speed 0.8-1.0 → PANIC mild (V=-0.3, A=0.3)
      輕度遲緩
    - walking_speed > 1.2 AND stride_regularity > 0.8 → SEEKING (V=+0.4, A=0.5)
      健康步態
    - gait_variability > 0.1 → FEAR (V=-0.4, A=0.5)
      不穩/焦慮

    Returns:
        (dominant_emotion, valence, arousal, confidence_weight)
    """
    # High variability → anxiety/unsteady (overrides speed-based classification)
    if gait.gait_variability > 0.1:
        return ("FEAR", -0.4, 0.5, 0.6)

    # Psychomotor retardation
    if gait.walking_speed < 0.8 and gait.stride_regularity < 0.5:
        return ("PANIC", -0.6, 0.2, 0.8)

    # Mild slowing
    if gait.walking_speed < 1.0:
        return ("PANIC", -0.3, 0.3, 0.5)

    # Healthy gait
    if gait.walking_speed > 1.2 and gait.stride_regularity > 0.8:
        return ("SEEKING", 0.4, 0.5, 0.5)

    # Normal range (1.0-1.2 or moderate regularity)
    return ("NEUTRAL", 0.0, 0.0, 0.3)


def _classify_circadian(
    circadian: CircadianMetrics,
) -> Tuple[str, float, float, float]:
    """節律 → 情感映射 / Circadian rhythm to emotion classification

    Clinical mapping:
    - circadian_disruption > 0.7 → PANIC (V=-0.5, A=0.3)
      睡眠-清醒紊亂 (sleep-wake disruption)
    - light_exposure_score < 0.3 → PANIC (V=-0.4, A=0.2)
      季節性情緒風險 (seasonal affective risk)
    - social_rhythm_stability < 0.4 → FEAR (V=-0.3, A=0.4)
      雙相/抑鬱風險 (bipolar/depression risk)
    - All good → CARE (V=+0.3, A=0.3)
      健康節律 (healthy rhythm)

    Returns:
        (dominant_emotion, valence, arousal, confidence_weight)
    """
    # Circadian disruption takes highest priority
    if circadian.circadian_disruption > 0.7:
        return ("PANIC", -0.5, 0.3, 0.8)

    # Low light exposure → seasonal affective risk
    if circadian.light_exposure_score < 0.3:
        return ("PANIC", -0.4, 0.2, 0.6)

    # Unstable social rhythm → bipolar/depression risk
    if circadian.social_rhythm_stability < 0.4:
        return ("FEAR", -0.3, 0.4, 0.6)

    # All metrics healthy
    return ("CARE", 0.3, 0.3, 0.5)


# ---------------------------------------------------------------------------
# Main Engine
# ---------------------------------------------------------------------------

class EmoBodyEngine:
    """EmoBody 身體感知引擎 / Physical Sensory Engine

    七竅 (Seven Apertures) 之「身」端，
    整合姿態、步態、節律三維度身體感知，
    輸出 Panksepp 情感分類與 Pulse 信號。

    TCM: 腎主骨生髓 (骨骼/步態) + 脾主肌肉 (姿態/運動)
    Panksepp: SEEKING (活力/探索) + LUST (身體驅力)

    Usage:
        engine = EmoBodyEngine()
        result = engine.analyze_posture(0.4, 25.0, 0.6, 3.0)
        pulse = engine.to_pulse(result)
    """

    def __init__(self) -> None:
        """初始化 EmoBody 引擎"""
        pass  # stateless engine — all state is in the result objects

    # ------------------------------------------------------------------
    # Single-dimension analysis
    # ------------------------------------------------------------------

    def analyze_posture(
        self,
        posture_score: float,
        forward_head_angle: float,
        shoulder_alignment: float,
        fidgeting_rate: float,
    ) -> EmoBodyResult:
        """姿態分析 / Posture analysis

        Args:
            posture_score: 姿態分數 (0.0 駝背 to 1.0 直立)
            forward_head_angle: 前傾頭角度 (度數)
            shoulder_alignment: 肩膀對齊度 (0.0 不對齊 to 1.0 對齊)
            fidgeting_rate: 煩躁動作頻率 (次/分鐘)

        Returns:
            EmoBodyResult with posture metrics populated
        """
        posture = PostureMetrics(
            posture_score=posture_score,
            forward_head_angle=forward_head_angle,
            shoulder_alignment=shoulder_alignment,
            fidgeting_rate=fidgeting_rate,
        )
        emotion, valence, arousal, weight = _classify_posture(posture)
        return EmoBodyResult(
            posture=posture,
            gait=None,
            circadian=None,
            dominant_emotion=emotion,
            valence=valence,
            arousal=arousal,
            confidence=weight,
            timestamp=datetime.now(timezone.utc),
        )

    def analyze_gait(
        self,
        walking_speed: float,
        stride_regularity: float,
        arm_swing_amplitude: float,
        gait_variability: float,
    ) -> EmoBodyResult:
        """步態分析 / Gait analysis

        Args:
            walking_speed: 步行速度 (m/s)
            stride_regularity: 步幅規律性 (0.0 to 1.0)
            arm_swing_amplitude: 手臂擺幅 (度數)
            gait_variability: 步態變異係數

        Returns:
            EmoBodyResult with gait metrics populated
        """
        gait = GaitMetrics(
            walking_speed=walking_speed,
            stride_regularity=stride_regularity,
            arm_swing_amplitude=arm_swing_amplitude,
            gait_variability=gait_variability,
        )
        emotion, valence, arousal, weight = _classify_gait(gait)
        return EmoBodyResult(
            posture=None,
            gait=gait,
            circadian=None,
            dominant_emotion=emotion,
            valence=valence,
            arousal=arousal,
            confidence=weight,
            timestamp=datetime.now(timezone.utc),
        )

    def analyze_circadian(
        self,
        sleep_regularity: float,
        social_rhythm_stability: float,
        light_exposure_score: float,
        chronotype: Union[str, Chronotype],
        circadian_disruption: float,
    ) -> EmoBodyResult:
        """晝夜節律分析 / Circadian rhythm analysis

        Args:
            sleep_regularity: 睡眠規律性 (0.0 to 1.0)
            social_rhythm_stability: 社會節律穩定性 (0.0 to 1.0)
            light_exposure_score: 光照充足度 (0.0 to 1.0)
            chronotype: 晝夜型態 ("morning"/"intermediate"/"evening" 或 Chronotype)
            circadian_disruption: 節律紊亂度 (0.0 to 1.0)

        Returns:
            EmoBodyResult with circadian metrics populated
        """
        circadian = CircadianMetrics(
            sleep_regularity=sleep_regularity,
            social_rhythm_stability=social_rhythm_stability,
            light_exposure_score=light_exposure_score,
            chronotype=chronotype,
            circadian_disruption=circadian_disruption,
        )
        emotion, valence, arousal, weight = _classify_circadian(circadian)
        return EmoBodyResult(
            posture=None,
            gait=None,
            circadian=circadian,
            dominant_emotion=emotion,
            valence=valence,
            arousal=arousal,
            confidence=weight,
            timestamp=datetime.now(timezone.utc),
        )

    # ------------------------------------------------------------------
    # Multi-dimension classification
    # ------------------------------------------------------------------

    def classify_emotion(
        self,
        posture: Optional[PostureMetrics],
        gait: Optional[GaitMetrics],
        circadian: Optional[CircadianMetrics],
    ) -> Tuple[str, float, float, float]:
        """多維度情感分類 / Multi-dimension emotion classification

        融合姿態、步態、節律三維度結果，
        使用加權投票 (weighted voting) 決定主導情感。

        Args:
            posture: 姿態指標 (可為 None)
            gait: 步態指標 (可為 None)
            circadian: 節律指標 (可為 None)

        Returns:
            (dominant_emotion, valence, arousal, confidence)
        """
        signals: list[Tuple[str, float, float, float]] = []

        if posture is not None:
            signals.append(_classify_posture(posture))
        if gait is not None:
            signals.append(_classify_gait(gait))
        if circadian is not None:
            signals.append(_classify_circadian(circadian))

        if not signals:
            return ("NEUTRAL", 0.0, 0.0, 0.0)

        # Weighted voting: aggregate by emotion
        emotion_weights: Dict[str, float] = {}
        emotion_v: Dict[str, float] = {}
        emotion_a: Dict[str, float] = {}

        for emotion, valence, arousal, weight in signals:
            emotion_weights[emotion] = emotion_weights.get(emotion, 0.0) + weight
            emotion_v[emotion] = emotion_v.get(emotion, 0.0) + valence * weight
            emotion_a[emotion] = emotion_a.get(emotion, 0.0) + arousal * weight

        # Pick dominant emotion by total weight
        dominant = max(emotion_weights, key=lambda e: emotion_weights[e])

        # Weighted average valence and arousal across all signals
        total_weight = sum(w for _, _, _, w in signals)
        avg_valence = sum(v * w for _, v, _, w in signals) / total_weight if total_weight > 0 else 0.0
        avg_arousal = sum(a * w for _, _, a, w in signals) / total_weight if total_weight > 0 else 0.0

        # Confidence: based on agreement between dimensions
        confidence = _clamp(
            emotion_weights[dominant] / total_weight if total_weight > 0 else 0.0,
            0.0, 1.0,
        )

        return (dominant, _clamp(avg_valence, -1.0, 1.0), _clamp(avg_arousal, -1.0, 1.0), confidence)

    # ------------------------------------------------------------------
    # Elderly mode: Fall risk & Circadian alerts
    # ------------------------------------------------------------------

    def detect_fall_risk(
        self,
        gait_data: GaitMetrics,
        posture_data: PostureMetrics,
    ) -> FallRiskAssessment:
        """跌倒風險偵測 / Fall risk detection for elderly mode

        整合步態與姿態信號，評估老年人跌倒風險。

        Detection rules:
        - Gait anomaly: stride_regularity < 0.5 OR gait_variability > 0.3
        - Posture collapse: posture_score < 0.3

        Risk level mapping:
        - No anomaly → NONE
        - One mild anomaly → LOW
        - One significant anomaly → MEDIUM
        - Both gait + posture anomaly → HIGH
        - Both severe → CRITICAL

        Args:
            gait_data: 步態指標
            posture_data: 姿態指標

        Returns:
            FallRiskAssessment with risk level and contributing factors
        """
        factors: List[str] = []
        gait_anomaly = False
        posture_collapse = False

        # Mild gait anomaly thresholds
        gait_mild = (
            gait_data.stride_regularity < 0.5
            or gait_data.gait_variability > 0.3
        )
        # Severe gait anomaly thresholds
        gait_severe = (
            gait_data.stride_regularity < 0.3
            or gait_data.gait_variability > 0.5
        )

        # Mild posture collapse threshold
        posture_mild = posture_data.posture_score < 0.3
        # Severe posture collapse threshold
        posture_severe = posture_data.posture_score < 0.15

        if gait_mild:
            gait_anomaly = True
            if gait_data.stride_regularity < 0.5:
                factors.append("low_stride_regularity")
            if gait_data.gait_variability > 0.3:
                factors.append("high_gait_variability")

        if posture_mild:
            posture_collapse = True
            factors.append("posture_collapse")

        # Determine risk level
        if gait_severe and posture_severe:
            risk_level = "CRITICAL"
            confidence = 0.95
        elif gait_anomaly and posture_collapse:
            risk_level = "HIGH"
            confidence = 0.8
        elif gait_severe or posture_severe:
            risk_level = "MEDIUM"
            confidence = 0.65
        elif gait_mild or posture_mild:
            risk_level = "LOW"
            confidence = 0.4
        else:
            risk_level = "NONE"
            confidence = 0.9

        return FallRiskAssessment(
            risk_level=risk_level,
            confidence=confidence,
            contributing_factors=factors,
            gait_anomaly=gait_anomaly,
            posture_collapse=posture_collapse,
            timestamp=datetime.now(timezone.utc),
        )

    def check_circadian_alert(
        self,
        circadian_metrics: CircadianMetrics,
        history_days: int = 3,
    ) -> List[CircadianAlert]:
        """晝夜節律警報檢查 / Circadian alert check for elderly mode

        偵測晝夜節律異常並生成警報列表。

        Detection rules:
        - sleep_regularity < 0.4 for 3+ days → SLEEP_IRREGULARITY
        - light_exposure_score < 0.3 → LOW_DAYLIGHT
        - social_rhythm_stability < 0.4 → SOCIAL_RHYTHM_DISRUPTION
        - circadian_disruption > 0.6 → CIRCADIAN_DISRUPTION

        Args:
            circadian_metrics: 晝夜節律指標
            history_days: 不規律持續天數 (default: 3)

        Returns:
            List of CircadianAlert objects for detected anomalies
        """
        alerts: List[CircadianAlert] = []
        now = datetime.now(timezone.utc)

        # Sleep irregularity check
        if circadian_metrics.sleep_regularity < 0.4 and history_days >= 3:
            severity = "HIGH" if circadian_metrics.sleep_regularity < 0.2 else "MEDIUM"
            alerts.append(CircadianAlert(
                alert_type="SLEEP_IRREGULARITY",
                severity=severity,
                days_irregular=history_days,
                recommendation=(
                    "Establish consistent sleep-wake schedule. "
                    "Consider morning bright light therapy."
                ),
                timestamp=now,
            ))

        # Low daylight check
        if circadian_metrics.light_exposure_score < 0.3:
            severity = "HIGH" if circadian_metrics.light_exposure_score < 0.15 else "MEDIUM"
            alerts.append(CircadianAlert(
                alert_type="LOW_DAYLIGHT",
                severity=severity,
                days_irregular=history_days,
                recommendation=(
                    "Increase daylight exposure. Aim for 30+ minutes "
                    "of outdoor light each morning."
                ),
                timestamp=now,
            ))

        # Social rhythm disruption check
        if circadian_metrics.social_rhythm_stability < 0.4:
            severity = "HIGH" if circadian_metrics.social_rhythm_stability < 0.2 else "LOW"
            alerts.append(CircadianAlert(
                alert_type="SOCIAL_RHYTHM_DISRUPTION",
                severity=severity,
                days_irregular=history_days,
                recommendation=(
                    "Stabilize daily routines: regular meal times, "
                    "social activities, and exercise schedule."
                ),
                timestamp=now,
            ))

        # Circadian disruption check
        if circadian_metrics.circadian_disruption > 0.6:
            severity = "HIGH" if circadian_metrics.circadian_disruption > 0.8 else "MEDIUM"
            alerts.append(CircadianAlert(
                alert_type="CIRCADIAN_DISRUPTION",
                severity=severity,
                days_irregular=history_days,
                recommendation=(
                    "Significant circadian disruption detected. "
                    "Consult healthcare provider for chronotherapy assessment."
                ),
                timestamp=now,
            ))

        return alerts

    # ------------------------------------------------------------------
    # Pulse conversion
    # ------------------------------------------------------------------

    def to_pulse(self, result: EmoBodyResult) -> Pulse:
        """將 EmoBodyResult 轉換為 Pulse 信號 / Convert result to Pulse

        Args:
            result: EmoBody 分析結果

        Returns:
            Pulse object for EmoGlyph integration
        """
        return result.to_pulse()


# ---------------------------------------------------------------------------
# Module smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    engine = EmoBodyEngine()

    # Posture: depressive posture
    r_posture = engine.analyze_posture(
        posture_score=0.2, forward_head_angle=35.0,
        shoulder_alignment=0.4, fidgeting_rate=2.0,
    )
    print(f"Posture: {r_posture.dominant_emotion} V={r_posture.valence:+.1f} A={r_posture.arousal:+.1f}")

    # Gait: psychomotor retardation
    r_gait = engine.analyze_gait(
        walking_speed=0.6, stride_regularity=0.4,
        arm_swing_amplitude=15.0, gait_variability=0.03,
    )
    print(f"Gait: {r_gait.dominant_emotion} V={r_gait.valence:+.1f} A={r_gait.arousal:+.1f}")

    # Circadian: disrupted
    r_circadian = engine.analyze_circadian(
        sleep_regularity=0.3, social_rhythm_stability=0.5,
        light_exposure_score=0.2, chronotype="evening",
        circadian_disruption=0.8,
    )
    print(f"Circadian: {r_circadian.dominant_emotion} V={r_circadian.valence:+.1f} A={r_circadian.arousal:+.1f}")

    # Multi-dimension classification
    emotion, valence, arousal, confidence = engine.classify_emotion(
        posture=r_posture.posture,
        gait=r_gait.gait,
        circadian=r_circadian.circadian,
    )
    print(f"Fusion: {emotion} V={valence:+.2f} A={arousal:+.2f} conf={confidence:.2f}")

    # Pulse conversion
    pulse = engine.to_pulse(r_posture)
    print(f"Pulse: {pulse}")

    # Serialization round-trip
    d = r_gait.to_dict()
    r2 = EmoBodyResult.from_dict(d)
    print(f"Round-trip OK: {r2.dominant_emotion == r_gait.dominant_emotion}")
