"""EmoSense (感官) Cross-Modal Fusion Engine — 跨模態融合引擎

EmoFriend 情感療癒產品 — 七竅 (Seven Apertures) 第 8 引擎

中醫臟腑: 三焦 (Triple Burner) — 連接所有其他臟腑的器官
Panksepp 系統: ALL (全部七大系統)

4-in-1 核心能力:
1. Cross-Modal Fusion — 加權融合全部 7 個引擎結果
2. Contradiction Detection — 臉≠聲、身≠文、心≠行 矛盾偵測
3. Safety Signal Detection — 多模態危機指標偵測
4. JITAI Trigger — 即時適應性介入決策

設計原則:
- 自包含，無外部依賴 (僅 stdlib)
- TYPE_CHECKING 避免循環導入
- 數值穩定 (_clamp)
- 可解釋 (每個矛盾/安全信號都有臨床解讀)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Dict, List, Optional

from ..pulse import Pulse, PulseType
from .audience_config import AudienceMode, AudienceConfig, get_config

if TYPE_CHECKING:
    from .emo_eye import EmoEyeResult
    from .emo_ear import EmoEarResult
    from .emo_heart import EmoHeartResult
    from .emo_brain import EmoBrainResult
    from .emo_hand import EmoHandResult
    from .emo_body import EmoBodyResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clamp(value: float, lo: float, hi: float) -> float:
    """將數值限制在 [lo, hi] 區間內 / Clamp value to [lo, hi]."""
    return max(lo, min(hi, value))


# ---------------------------------------------------------------------------
# Panksepp system classification
# ---------------------------------------------------------------------------

POSITIVE_SYSTEMS = {"SEEKING", "CARE", "PLAY", "LUST"}
NEGATIVE_SYSTEMS = {"RAGE", "FEAR", "PANIC"}

PANKSEPP_SYSTEMS = list(POSITIVE_SYSTEMS | NEGATIVE_SYSTEMS)

# Panksepp system name → PulseType mapping
_PANKSEPP_TO_PULSE: Dict[str, PulseType] = {
    "SEEKING": PulseType.SEEKING,
    "RAGE": PulseType.RAGE,
    "FEAR": PulseType.FEAR,
    "LUST": PulseType.LUST,
    "CARE": PulseType.CARE,
    "PANIC": PulseType.PANIC,
    "PLAY": PulseType.PLAY,
}

# ---------------------------------------------------------------------------
# Base weights for dynamic weight algorithm
# ---------------------------------------------------------------------------

BASE_WEIGHTS: Dict[str, float] = {
    "eye": 0.25,
    "ear": 0.20,
    "heart": 0.20,
    "brain": 0.10,
    "hand": 0.10,
    "body": 0.10,
    "text": 0.05,
}

# ---------------------------------------------------------------------------
# Contradiction detection rules
# ---------------------------------------------------------------------------

CONTRADICTION_RULES: List[Dict] = [
    {
        "modality_a": "eye",
        "emotion_a": "PLAY",
        "modality_b": "ear",
        "emotion_b": "FEAR",
        "clinical_interpretation": "Masking/emotional suppression",
        "therapy_response": "Switch to CARE system + gentle inquiry",
    },
    {
        "modality_a": "eye",
        "emotion_a": "CARE",
        "modality_b": "ear",
        "emotion_b": "RAGE",
        "clinical_interpretation": "Passive aggression",
        "therapy_response": "MU silence — let the anger surface safely",
    },
    {
        "modality_a": "eye",
        "emotion_a": "FEAR",
        "modality_b": "text",
        "emotion_b": "CARE",
        "clinical_interpretation": "Denial",
        "therapy_response": "MA silence — hold space for truth",
    },
    {
        "modality_a": "ear",
        "emotion_a": "NEUTRAL",
        "modality_b": "eye",
        "emotion_b": "PLAY",
        "clinical_interpretation": "High-functioning depression",
        "therapy_response": "Safety check — probe beneath the surface",
    },
    {
        "modality_a": "heart",
        "emotion_a": "FEAR",
        "modality_b": "body",
        "emotion_b": "SEEKING",
        "clinical_interpretation": "Pushing through stress",
        "therapy_response": "CARE response — acknowledge the effort and the strain",
    },
    {
        "modality_a": "body",
        "emotion_a": "PANIC",
        "modality_b": "hand",
        "emotion_b": "SEEKING",
        "clinical_interpretation": "Body-mind disconnect",
        "therapy_response": "Body awareness — reconnect body and mind",
    },
    {
        "modality_a": "body",
        "emotion_a": "PANIC",
        "modality_b": "hand",
        "emotion_b": "SEEKING",
        "signal_type": "circadian_disruption",
        "clinical_interpretation": "Digital addiction cycle",
        "therapy_response": "Digital wellness — break the cycle",
    },
]

# ---------------------------------------------------------------------------
# Safety signal detection rules
# ---------------------------------------------------------------------------

SAFETY_RULES: List[Dict] = [
    {
        "signal_type": "dorsal_vagal",
        "indicators": {
            "ear": "flat",
            "eye": "averted_gaze",
            "heart": "low_hrv",
        },
        "severity": "CRITICAL",
        "recommended_action": "Professional referral — dorsal vagal shutdown detected",
    },
    {
        "signal_type": "psychomotor_retardation",
        "indicators": {
            "body": "slow_gait",
            "body_posture": "slouched",
            "hand": "slow_typing",
        },
        "severity": "HIGH",
        "recommended_action": "Depression screening — psychomotor retardation pattern",
    },
    {
        "signal_type": "masking",
        "indicators": {
            "eye": "positive",
            "ear": "flat",
        },
        "sustained": True,
        "severity": "HIGH",
        "recommended_action": "Gentle inquiry — emotional masking detected",
    },
    {
        "signal_type": "cognitive_overload",
        "indicators": {
            "brain": "high_load",
            "brain_fatigue": True,
            "duration_min": 30,
        },
        "severity": "MEDIUM",
        "recommended_action": "Break suggestion — cognitive overload detected",
    },
    {
        "signal_type": "circadian_disruption",
        "indicators": {
            "body": "irregular_sleep",
            "body_light": "low_daylight",
        },
        "severity": "MEDIUM",
        "recommended_action": "Light/rhythm advice — circadian disruption detected",
    },
]


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class SafetySeverity(Enum):
    """安全信號嚴重程度 / Safety signal severity level."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class JITAIActionType(Enum):
    """即時適應性介入行動類型 / Just-In-Time Adaptive Intervention action type."""
    GUIDED_BREATHING = "guided_breathing"
    SILENCE = "silence"
    GROUNDING = "grounding"
    REFERRAL = "referral"
    BREAK_SUGGESTION = "break_suggestion"
    FLOW_PROTECTION = "flow_protection"
    LIGHT_THERAPY = "light_therapy"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class Contradiction:
    """跨模態矛盾 / Cross-modal contradiction between two modalities.

    當兩個感官通道的情緒信號不一致時產生矛盾，
    每個矛盾都有臨床解讀和對應的療癒策略。
    """
    modality_a: str              # "eye", "ear", "heart", "brain", "hand", "body", "text"
    modality_b: str
    emotion_a: str               # Panksepp system name
    emotion_b: str               # Panksepp system name
    clinical_interpretation: str  # e.g., "Masking/emotional suppression"
    therapy_response: str         # e.g., "Switch to CARE system"

    def __post_init__(self) -> None:
        valid_modalities = {"eye", "ear", "heart", "brain", "hand", "body", "text"}
        if self.modality_a not in valid_modalities:
            raise ValueError(f"Invalid modality_a: {self.modality_a}")
        if self.modality_b not in valid_modalities:
            raise ValueError(f"Invalid modality_b: {self.modality_b}")
        valid_emotions = set(PANKSEPP_SYSTEMS) | {"NEUTRAL"}
        if self.emotion_a not in valid_emotions:
            raise ValueError(f"Invalid emotion_a: {self.emotion_a}")
        if self.emotion_b not in valid_emotions:
            raise ValueError(f"Invalid emotion_b: {self.emotion_b}")

    def to_dict(self) -> Dict:
        return {
            "modality_a": self.modality_a,
            "modality_b": self.modality_b,
            "emotion_a": self.emotion_a,
            "emotion_b": self.emotion_b,
            "clinical_interpretation": self.clinical_interpretation,
            "therapy_response": self.therapy_response,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> Contradiction:
        return cls(
            modality_a=data["modality_a"],
            modality_b=data["modality_b"],
            emotion_a=data["emotion_a"],
            emotion_b=data["emotion_b"],
            clinical_interpretation=data["clinical_interpretation"],
            therapy_response=data["therapy_response"],
        )


@dataclass
class SafetySignal:
    """安全信號 / Safety signal from multi-modal crisis indicators.

    當多個感官通道同時顯示危機指標時觸發，
    嚴重程度從 LOW 到 CRITICAL。
    """
    signal_type: str               # "dorsal_vagal", "masking", "psychomotor_retardation", etc.
    severity: SafetySeverity
    contributing_modalities: List[str]
    recommended_action: str

    def __post_init__(self) -> None:
        valid_types = {
            "dorsal_vagal", "masking", "psychomotor_retardation",
            "cognitive_overload", "circadian_disruption",
        }
        if self.signal_type not in valid_types:
            raise ValueError(f"Invalid signal_type: {self.signal_type}")
        if not isinstance(self.severity, SafetySeverity):
            raise TypeError(f"severity must be SafetySeverity, got {type(self.severity).__name__}")
        if not self.contributing_modalities:
            raise ValueError("contributing_modalities must not be empty")

    def to_dict(self) -> Dict:
        return {
            "signal_type": self.signal_type,
            "severity": self.severity.value,
            "contributing_modalities": self.contributing_modalities,
            "recommended_action": self.recommended_action,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> SafetySignal:
        return cls(
            signal_type=data["signal_type"],
            severity=SafetySeverity(data["severity"]),
            contributing_modalities=data["contributing_modalities"],
            recommended_action=data["recommended_action"],
        )


@dataclass
class JITAIAction:
    """即時適應性介入行動 / Just-In-Time Adaptive Intervention action.

    根據融合後的情緒狀態和安全信號，
    推薦最適當的即時介入行動。
    """
    action_type: JITAIActionType
    urgency: float                 # 0.0 to 1.0
    reason: str
    target_engine: str             # Which engine should execute (e.g., "mouth", "therapy")

    def __post_init__(self) -> None:
        if not isinstance(self.action_type, JITAIActionType):
            raise TypeError(
                f"action_type must be JITAIActionType, got {type(self.action_type).__name__}"
            )
        if not 0.0 <= self.urgency <= 1.0:
            raise ValueError(f"urgency must be in [0, 1], got {self.urgency}")

    def to_dict(self) -> Dict:
        return {
            "action_type": self.action_type.value,
            "urgency": self.urgency,
            "reason": self.reason,
            "target_engine": self.target_engine,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> JITAIAction:
        return cls(
            action_type=JITAIActionType(data["action_type"]),
            urgency=data["urgency"],
            reason=data["reason"],
            target_engine=data["target_engine"],
        )


# ---------------------------------------------------------------------------
# Audience-specific safety data classes
# ---------------------------------------------------------------------------

@dataclass
class KidsSafetyRules:
    """兒童安全規則 / Safety rules for Kids Mode (ages 5-12).

    More sensitive distress thresholds and faster escalation
    to protect younger users.
    """
    distress_threshold: float = 0.3
    escalation_tier1_min: float = 2.0
    escalation_tier2_min: float = 5.0
    escalation_tier3_min: float = 8.0
    escalation_target: str = "parent"
    physical_health_monitoring: bool = False
    fall_detection: bool = False
    circadian_monitoring: bool = False
    keystroke_tracking: bool = False


@dataclass
class ElderlySafetyRules:
    """長者安全規則 / Safety rules for Elderly Mode (ages 65+).

    Includes physical health monitoring, fall detection,
    and circadian rhythm tracking.
    """
    distress_threshold: float = 0.5
    escalation_tier1_min: float = 5.0
    escalation_tier2_min: float = 10.0
    escalation_tier3_min: float = 15.0
    escalation_target: str = "family"
    physical_health_monitoring: bool = True
    fall_detection: bool = True
    circadian_monitoring: bool = True
    keystroke_tracking: bool = False


@dataclass
class SafetyEscalation:
    """安全升級 / Safety escalation event for audience-specific responses.

    Represents a tiered escalation triggered when sustained distress
    exceeds audience-configured thresholds.
    """
    tier: int                           # 1, 2, or 3
    audience_mode: AudienceMode
    message: str
    action: str
    notify_target: Optional[str]
    timestamp: datetime

    def __post_init__(self) -> None:
        if self.tier not in (1, 2, 3):
            raise ValueError(f"tier must be 1, 2, or 3, got {self.tier}")


# Panksepp system name → simple emotion label for family readability
_PANKSEPP_TO_SIMPLE: Dict[str, str] = {
    "SEEKING": "curious",
    "RAGE": "angry",
    "FEAR": "scared",
    "LUST": "excited",
    "CARE": "loving",
    "PANIC": "distressed",
    "PLAY": "happy",
    "NEUTRAL": "calm",
}


@dataclass
class SensoryInput:
    """感官輸入容器 / Container for all 7 modality results.

    匯集七竅引擎的所有結果，作為融合引擎的輸入。
    所有模態都是可選的——缺失的模態會在權重計算中處理。
    """
    text: Optional[str] = None
    eye_result: Optional[Dict] = None       # EmoEyeResult as dict (avoid circular import)
    ear_result: Optional[Dict] = None       # EmoEarResult as dict
    heart_result: Optional[Dict] = None     # EmoHeartResult as dict
    brain_result: Optional[Dict] = None     # EmoBrainResult as dict
    hand_result: Optional[Dict] = None      # EmoHandResult as dict
    body_result: Optional[Dict] = None      # EmoBodyResult as dict
    timestamp: Optional[datetime] = None

    def __post_init__(self) -> None:
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)

    @property
    def available_modalities(self) -> List[str]:
        """返回有數據的模態列表 / Return list of modalities with data."""
        modalities: List[str] = []
        if self.eye_result is not None:
            modalities.append("eye")
        if self.ear_result is not None:
            modalities.append("ear")
        if self.heart_result is not None:
            modalities.append("heart")
        if self.brain_result is not None:
            modalities.append("brain")
        if self.hand_result is not None:
            modalities.append("hand")
        if self.body_result is not None:
            modalities.append("body")
        if self.text is not None:
            modalities.append("text")
        return modalities

    def to_dict(self) -> Dict:
        return {
            "text": self.text,
            "eye_result": self.eye_result,
            "ear_result": self.ear_result,
            "heart_result": self.heart_result,
            "brain_result": self.brain_result,
            "hand_result": self.hand_result,
            "body_result": self.body_result,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> SensoryInput:
        ts = data.get("timestamp")
        return cls(
            text=data.get("text"),
            eye_result=data.get("eye_result"),
            ear_result=data.get("ear_result"),
            heart_result=data.get("heart_result"),
            brain_result=data.get("brain_result"),
            hand_result=data.get("hand_result"),
            body_result=data.get("body_result"),
            timestamp=datetime.fromisoformat(ts) if ts else None,
        )


@dataclass
class FusedEmotionalState:
    """融合情緒狀態 / Fused emotional state from all modalities.

    跨模態融合的最終輸出，包含：
    - 主導情緒 (Panksepp 系統)
    - VAD 維度 (效價/喚醒/支配)
    - 模態權重
    - 矛盾列表
    - 安全信號列表
    - JITAI 推薦
    - 情緒遮罩偵測結果
    """
    dominant_emotion: str               # Panksepp system
    valence: float                      # -1.0 to 1.0
    arousal: float                      # -1.0 to 1.0
    dominance: float                    # -1.0 to 1.0
    intensity: float                    # 0.0 to 1.0
    confidence: float                   # 0.0 to 1.0
    modality_weights: Dict[str, float]  # Dynamic weights per modality
    contradictions: List[Contradiction]
    safety_signals: List[SafetySignal]
    jitai_recommendation: Optional[JITAIAction]
    emotional_masking_detected: bool
    available_modalities: List[str]     # Which modalities contributed
    timestamp: datetime

    def __post_init__(self) -> None:
        self.valence = _clamp(self.valence, -1.0, 1.0)
        self.arousal = _clamp(self.arousal, -1.0, 1.0)
        self.dominance = _clamp(self.dominance, -1.0, 1.0)
        self.intensity = _clamp(self.intensity, 0.0, 1.0)
        self.confidence = _clamp(self.confidence, 0.0, 1.0)
        valid_emotions = set(PANKSEPP_SYSTEMS) | {"NEUTRAL"}
        if self.dominant_emotion not in valid_emotions:
            raise ValueError(
                f"Invalid dominant_emotion: {self.dominant_emotion}. "
                f"Must be one of: {sorted(valid_emotions)}"
            )

    def to_pulse(self) -> Pulse:
        """將融合狀態轉換為 Pulse 物件 / Convert fused state to Pulse object."""
        pulse_type = _PANKSEPP_TO_PULSE.get(self.dominant_emotion, PulseType.NEUTRAL)
        return Pulse(
            pulse_type=pulse_type,
            valence=self.valence,
            arousal=self.arousal,
            dominance=self.dominance,
            intensity=self.intensity,
        )

    def to_dict(self) -> Dict:
        return {
            "dominant_emotion": self.dominant_emotion,
            "valence": self.valence,
            "arousal": self.arousal,
            "dominance": self.dominance,
            "intensity": self.intensity,
            "confidence": self.confidence,
            "modality_weights": self.modality_weights,
            "contradictions": [c.to_dict() for c in self.contradictions],
            "safety_signals": [s.to_dict() for s in self.safety_signals],
            "jitai_recommendation": (
                self.jitai_recommendation.to_dict() if self.jitai_recommendation else None
            ),
            "emotional_masking_detected": self.emotional_masking_detected,
            "available_modalities": self.available_modalities,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict) -> FusedEmotionalState:
        contradictions = [
            Contradiction.from_dict(c) for c in data.get("contradictions", [])
        ]
        safety_signals = [
            SafetySignal.from_dict(s) for s in data.get("safety_signals", [])
        ]
        jitai = data.get("jitai_recommendation")
        return cls(
            dominant_emotion=data["dominant_emotion"],
            valence=data["valence"],
            arousal=data["arousal"],
            dominance=data["dominance"],
            intensity=data["intensity"],
            confidence=data["confidence"],
            modality_weights=data["modality_weights"],
            contradictions=contradictions,
            safety_signals=safety_signals,
            jitai_recommendation=JITAIAction.from_dict(jitai) if jitai else None,
            emotional_masking_detected=data["emotional_masking_detected"],
            available_modalities=data["available_modalities"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
        )


# ---------------------------------------------------------------------------
# EmoSense Engine
# ---------------------------------------------------------------------------

class EmoSenseEngine:
    """EmoSense (感官) 跨模態融合引擎 / Cross-Modal Fusion Engine.

    中醫臟腑: 三焦 (Triple Burner) — 連接所有其他臟腑的器官。
    三焦不對應單一器官，而是連接上、中、下三焦的系統，
    正如此引擎連接所有七竅引擎。

    4-in-1 核心能力:
    1. Cross-Modal Fusion — 加權融合全部 7 個引擎結果
    2. Contradiction Detection — 臉≠聲、身≠文、心≠行 矛盾偵測
    3. Safety Signal Detection — 多模態危機指標偵測
    4. JITAI Trigger — 即時適應性介入決策
    """

    def __init__(self) -> None:
        self._base_weights: Dict[str, float] = dict(BASE_WEIGHTS)
        self._audience_config: Optional[AudienceConfig] = None
        self._safety_rules: Optional[KidsSafetyRules | ElderlySafetyRules] = None

    # ------------------------------------------------------------------
    # Audience-specific safety configuration
    # ------------------------------------------------------------------

    def configure_for_audience(self, audience_mode: AudienceMode) -> None:
        """為特定受眾模式配置安全規則 / Configure safety rules for a specific audience mode.

        Sets internal audience config and safety rules based on the mode,
        and updates SAFETY_RULES thresholds accordingly.
        """
        self._audience_config = get_config(audience_mode)

        if audience_mode == AudienceMode.KIDS:
            self._safety_rules = KidsSafetyRules(
                distress_threshold=self._audience_config.distress_threshold,
                escalation_tier1_min=self._audience_config.escalation_tier1_min,
                escalation_tier2_min=self._audience_config.escalation_tier2_min,
                escalation_tier3_min=self._audience_config.escalation_tier3_min,
                escalation_target=self._audience_config.escalation_target,
                physical_health_monitoring=self._audience_config.physical_health_monitoring,
                fall_detection=self._audience_config.fall_detection,
                circadian_monitoring=self._audience_config.circadian_monitoring,
            )
        elif audience_mode == AudienceMode.ELDERLY:
            self._safety_rules = ElderlySafetyRules(
                distress_threshold=self._audience_config.distress_threshold,
                escalation_tier1_min=self._audience_config.escalation_tier1_min,
                escalation_tier2_min=self._audience_config.escalation_tier2_min,
                escalation_tier3_min=self._audience_config.escalation_tier3_min,
                escalation_target=self._audience_config.escalation_target,
                physical_health_monitoring=self._audience_config.physical_health_monitoring,
                fall_detection=self._audience_config.fall_detection,
                circadian_monitoring=self._audience_config.circadian_monitoring,
            )

        # Update SAFETY_RULES thresholds based on audience config
        self._update_safety_rules_thresholds()

    def _update_safety_rules_thresholds(self) -> None:
        """根據受眾配置更新安全規則閾值 / Update SAFETY_RULES thresholds from audience config."""
        if self._safety_rules is None:
            return

        for rule in SAFETY_RULES:
            if rule.get("severity") == "CRITICAL":
                rule["_audience_distress_threshold"] = self._safety_rules.distress_threshold
            elif rule.get("severity") == "HIGH":
                rule["_audience_distress_threshold"] = self._safety_rules.distress_threshold
            elif rule.get("severity") == "MEDIUM":
                rule["_audience_distress_threshold"] = self._safety_rules.distress_threshold

    def escalate_safety(
        self,
        signal: SafetySignal,
        audience_config: AudienceConfig,
    ) -> SafetyEscalation:
        """根據安全信號和受眾配置進行安全升級 / Escalate safety based on signal and audience config.

        Determines escalation tier based on signal severity and audience thresholds:
        - Tier 1 (gentle check-in): LOW/MEDIUM severity, distress_duration < tier1_min
        - Tier 2 (family notification): MEDIUM/HIGH severity, distress_duration >= tier2_min
        - Tier 3 (emergency): HIGH/CRITICAL severity
        """
        severity = signal.severity
        # Derive distress_duration from signal metadata if available
        distress_duration = 0.0
        if hasattr(signal, '_distress_duration'):
            distress_duration = signal._distress_duration
        # Use contributing modality count as a proxy for duration escalation
        distress_duration = float(len(signal.contributing_modalities)) * 2.0

        tier1_min = audience_config.escalation_tier1_min
        tier2_min = audience_config.escalation_tier2_min

        # Determine tier
        if severity in (SafetySeverity.HIGH, SafetySeverity.CRITICAL):
            tier = 3
        elif severity in (SafetySeverity.MEDIUM, SafetySeverity.HIGH) and distress_duration >= tier2_min:
            tier = 2
        elif severity in (SafetySeverity.LOW, SafetySeverity.MEDIUM):
            tier = 1
        else:
            tier = 1

        # Determine audience mode from config
        if audience_config.escalation_target == "parent":
            audience_mode = AudienceMode.KIDS
        else:
            audience_mode = AudienceMode.ELDERLY

        # Select message based on tier and audience mode
        if audience_mode == AudienceMode.KIDS:
            if tier == 1:
                message = "Are you okay? Want to take a breath with me?"
                action = "gentle_check_in"
            elif tier == 2:
                message = "I think someone who cares about you should know. Can I tell them?"
                action = "family_notification"
            else:
                message = "I'm letting your parent know right now."
                action = "emergency_notification"
        else:
            if tier == 1:
                message = "你還好嗎？要不要一起做個呼吸練習？"
                action = "gentle_check_in"
            elif tier == 2:
                message = "我想讓你的家人知道你的狀態，可以嗎？"
                action = "family_notification"
            else:
                message = "我正在通知你的緊急聯絡人。"
                action = "emergency_notification"

        notify_target = audience_config.escalation_target if tier >= 2 else None

        return SafetyEscalation(
            tier=tier,
            audience_mode=audience_mode,
            message=message,
            action=action,
            notify_target=notify_target,
            timestamp=datetime.now(timezone.utc),
        )

    def generate_family_notification(
        self,
        state: FusedEmotionalState,
        audience_mode: AudienceMode,
    ) -> str:
        """生成家庭通知 / Generate family notification message.

        Converts Panksepp system names to simple emotion labels
        for family readability.
        """
        simple_emotion = _PANKSEPP_TO_SIMPLE.get(
            state.dominant_emotion, state.dominant_emotion
        )

        if audience_mode == AudienceMode.KIDS:
            return (
                f"[Name] seems to be having a difficult time. "
                f"Emo suggests reaching out. Current feeling: {simple_emotion}"
            )
        else:
            return (
                f"[Name] 的情緒狀態需要關注。"
                f"Emo 建議您聯繫。目前感受：{simple_emotion}"
            )

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def fuse(self, sensory_input: SensoryInput) -> FusedEmotionalState:
        """融合所有模態數據 / Fuse all modality data into a unified emotional state.

        步驟:
        1. 收集可用模態
        2. 計算動態權重
        3. 加權平均 valence/arousal/dominance
        4. 偵測矛盾
        5. 偵測安全信號
        6. 加權投票決定主導情緒
        7. 推薦 JITAI 行動
        8. 返回 FusedEmotionalState
        """
        available = sensory_input.available_modalities

        if not available:
            return FusedEmotionalState(
                dominant_emotion="NEUTRAL",
                valence=0.0,
                arousal=0.0,
                dominance=0.0,
                intensity=0.0,
                confidence=0.0,
                modality_weights={},
                contradictions=[],
                safety_signals=[],
                jitai_recommendation=None,
                emotional_masking_detected=False,
                available_modalities=[],
                timestamp=sensory_input.timestamp or datetime.now(timezone.utc),
            )

        # Build modality data dict
        modalities = self._collect_modality_data(sensory_input)

        # Compute dynamic weights
        weights = self.compute_weights(modalities)

        # Weighted average of VAD
        valence = self._weighted_vad(modalities, weights, "valence")
        arousal = self._weighted_vad(modalities, weights, "arousal")
        dominance = self._weighted_vad(modalities, weights, "dominance")

        # Detect contradictions
        contradictions = self.detect_contradictions(modalities)

        # Adjust weights for contradictions (increase third modality by 0.05)
        weights = self._adjust_weights_for_contradictions(weights, contradictions, available)

        # Detect safety signals
        safety_signals = self.detect_safety_signals(modalities, contradictions)

        # Determine dominant emotion by weighted vote
        dominant_emotion = self._weighted_vote(modalities, weights)

        # Compute intensity and confidence
        intensity = self._compute_intensity(modalities, weights)
        confidence = self._compute_confidence(modalities, weights, available)

        # Detect emotional masking
        masking_detected = self._detect_masking(contradictions, safety_signals)

        # Build fused state (without JITAI first)
        fused = FusedEmotionalState(
            dominant_emotion=dominant_emotion,
            valence=valence,
            arousal=arousal,
            dominance=dominance,
            intensity=intensity,
            confidence=confidence,
            modality_weights=weights,
            contradictions=contradictions,
            safety_signals=safety_signals,
            jitai_recommendation=None,
            emotional_masking_detected=masking_detected,
            available_modalities=available,
            timestamp=sensory_input.timestamp or datetime.now(timezone.utc),
        )

        # Recommend JITAI action
        jitai = self.recommend_jitai(fused, safety_signals)
        fused.jitai_recommendation = jitai

        return fused

    # ------------------------------------------------------------------
    # Contradiction Detection
    # ------------------------------------------------------------------

    def detect_contradictions(
        self, modalities: Dict[str, Dict]
    ) -> List[Contradiction]:
        """偵測跨模態矛盾 / Detect contradictions between modalities.

        規則:
        - 如果 modality_a 的主導情緒為正面 (PLAY/CARE/SEEKING)
          且 modality_b 的主導情緒為負面 (FEAR/RAGE/PANIC) → 矛盾
        - 特定臨床解讀來自 CONTRADICTION_RULES
        """
        contradictions: List[Contradiction] = []
        modality_names = list(modalities.keys())

        for i in range(len(modality_names)):
            for j in range(i + 1, len(modality_names)):
                mod_a = modality_names[i]
                mod_b = modality_names[j]
                data_a = modalities[mod_a]
                data_b = modalities[mod_b]

                emotion_a = data_a.get("dominant_emotion", "NEUTRAL")
                emotion_b = data_b.get("dominant_emotion", "NEUTRAL")

                # Check if there's a positive vs negative contradiction
                a_positive = emotion_a in POSITIVE_SYSTEMS
                a_negative = emotion_a in NEGATIVE_SYSTEMS
                b_positive = emotion_b in POSITIVE_SYSTEMS
                b_negative = emotion_b in NEGATIVE_SYSTEMS

                is_contradiction = (
                    (a_positive and b_negative) or (a_negative and b_positive)
                )

                if not is_contradiction:
                    continue

                # Look up specific rule
                rule = self._find_contradiction_rule(mod_a, emotion_a, mod_b, emotion_b)

                if rule:
                    contradictions.append(Contradiction(
                        modality_a=mod_a,
                        modality_b=mod_b,
                        emotion_a=emotion_a,
                        emotion_b=emotion_b,
                        clinical_interpretation=rule["clinical_interpretation"],
                        therapy_response=rule["therapy_response"],
                    ))
                else:
                    # Generic contradiction
                    contradictions.append(Contradiction(
                        modality_a=mod_a,
                        modality_b=mod_b,
                        emotion_a=emotion_a,
                        emotion_b=emotion_b,
                        clinical_interpretation=(
                            f"Cross-modal mismatch: {mod_a}={emotion_a} vs "
                            f"{mod_b}={emotion_b}"
                        ),
                        therapy_response="Gentle inquiry — explore the discrepancy",
                    ))

        return contradictions

    def _find_contradiction_rule(
        self,
        mod_a: str,
        emotion_a: str,
        mod_b: str,
        emotion_b: str,
    ) -> Optional[Dict]:
        """查找匹配的矛盾規則 / Find matching contradiction rule."""
        for rule in CONTRADICTION_RULES:
            # Check direct match
            if (rule["modality_a"] == mod_a and rule["emotion_a"] == emotion_a
                    and rule["modality_b"] == mod_b and rule["emotion_b"] == emotion_b):
                return rule
            # Check reverse match (A↔B symmetric)
            if (rule["modality_a"] == mod_b and rule["emotion_a"] == emotion_b
                    and rule["modality_b"] == mod_a and rule["emotion_b"] == emotion_a):
                return rule
        return None

    # ------------------------------------------------------------------
    # Safety Signal Detection
    # ------------------------------------------------------------------

    def detect_safety_signals(
        self,
        modalities: Dict[str, Dict],
        contradictions: List[Contradiction],
    ) -> List[SafetySignal]:
        """偵測安全信號 / Detect safety signals from multi-modal crisis indicators.

        規則:
        - Dorsal vagal: flat voice + averted gaze + low HRV → CRITICAL
        - Psychomotor retardation: slow gait + slouched + slow typing → HIGH
        - Emotional masking: face≠voice sustained → HIGH
        - Cognitive overload: high load + fatigue + >30min → MEDIUM
        - Circadian disruption: irregular sleep + low daylight → MEDIUM
        """
        signals: List[SafetySignal] = []

        # 1. Dorsal vagal shutdown
        dorsal = self._check_dorsal_vagal(modalities)
        if dorsal:
            signals.append(dorsal)

        # 2. Psychomotor retardation
        psychomotor = self._check_psychomotor_retardation(modalities)
        if psychomotor:
            signals.append(psychomotor)

        # 3. Emotional masking (from contradictions)
        masking = self._check_emotional_masking(modalities, contradictions)
        if masking:
            signals.append(masking)

        # 4. Cognitive overload
        overload = self._check_cognitive_overload(modalities)
        if overload:
            signals.append(overload)

        # 5. Circadian disruption
        circadian = self._check_circadian_disruption(modalities)
        if circadian:
            signals.append(circadian)

        return signals

    def _check_dorsal_vagal(self, modalities: Dict[str, Dict]) -> Optional[SafetySignal]:
        """偵測背側迷走神經關閉 / Detect dorsal vagal shutdown pattern."""
        contributing: List[str] = []

        # Check ear: flat voice
        ear = modalities.get("ear", {})
        if ear.get("voice_quality") == "flat" or ear.get("prosody_variance", 1.0) < 0.15:
            contributing.append("ear")

        # Check eye: averted gaze
        eye = modalities.get("eye", {})
        if eye.get("gaze_pattern") == "averted" or eye.get("gaze_aversion_ratio", 0.0) > 0.6:
            contributing.append("eye")

        # Check heart: low HRV
        heart = modalities.get("heart", {})
        if heart.get("hrv") is not None and heart.get("hrv", 100.0) < 30.0:
            contributing.append("heart")

        if len(contributing) >= 2:
            return SafetySignal(
                signal_type="dorsal_vagal",
                severity=SafetySeverity.CRITICAL,
                contributing_modalities=contributing,
                recommended_action="Professional referral — dorsal vagal shutdown detected",
            )
        return None

    def _check_psychomotor_retardation(
        self, modalities: Dict[str, Dict]
    ) -> Optional[SafetySignal]:
        """偵測精神運動遲緩 / Detect psychomotor retardation pattern."""
        contributing: List[str] = []

        # Check body: slow gait
        body = modalities.get("body", {})
        if body.get("gait_speed") is not None and body.get("gait_speed", 1.0) < 0.5:
            contributing.append("body")
        # Check body: slouched posture
        if body.get("posture") == "slouched" or body.get("upright_ratio", 1.0) < 0.4:
            contributing.append("body")

        # Check hand: slow typing
        hand = modalities.get("hand", {})
        if hand.get("typing_speed") is not None and hand.get("typing_speed", 1.0) < 0.4:
            contributing.append("hand")

        if len(contributing) >= 2:
            return SafetySignal(
                signal_type="psychomotor_retardation",
                severity=SafetySeverity.HIGH,
                contributing_modalities=contributing,
                recommended_action="Depression screening — psychomotor retardation pattern",
            )
        return None

    def _check_emotional_masking(
        self,
        modalities: Dict[str, Dict],
        contradictions: List[Contradiction],
    ) -> Optional[SafetySignal]:
        """偵測情緒遮罩 / Detect emotional masking pattern."""
        # Check if eye and ear contradict (face ≠ voice)
        eye_ear_contradiction = any(
            (c.modality_a in ("eye", "ear") and c.modality_b in ("eye", "ear"))
            for c in contradictions
        )

        contributing: List[str] = []
        if "eye" in modalities:
            contributing.append("eye")
        if "ear" in modalities:
            contributing.append("ear")

        if eye_ear_contradiction and len(contributing) >= 2:
            return SafetySignal(
                signal_type="masking",
                severity=SafetySeverity.HIGH,
                contributing_modalities=contributing,
                recommended_action="Gentle inquiry — emotional masking detected",
            )
        return None

    def _check_cognitive_overload(
        self, modalities: Dict[str, Dict]
    ) -> Optional[SafetySignal]:
        """偵測認知過載 / Detect cognitive overload pattern."""
        contributing: List[str] = []

        # Check brain: high cognitive load
        brain = modalities.get("brain", {})
        if brain.get("cognitive_load") is not None and brain.get("cognitive_load", 0.0) > 0.7:
            contributing.append("brain")
        # Check brain: fatigue
        if brain.get("fatigue_level") is not None and brain.get("fatigue_level", 0.0) > 0.6:
            contributing.append("brain")
        # Check brain: duration > 30 min
        if brain.get("session_duration_min") is not None and brain.get("session_duration_min", 0.0) > 30:
            contributing.append("brain")

        if len(contributing) >= 2:
            return SafetySignal(
                signal_type="cognitive_overload",
                severity=SafetySeverity.MEDIUM,
                contributing_modalities=contributing,
                recommended_action="Break suggestion — cognitive overload detected",
            )
        return None

    def _check_circadian_disruption(
        self, modalities: Dict[str, Dict]
    ) -> Optional[SafetySignal]:
        """偵測晝夜節律紊亂 / Detect circadian disruption pattern."""
        contributing: List[str] = []

        # Check body: irregular sleep
        body = modalities.get("body", {})
        if body.get("sleep_regularity") is not None and body.get("sleep_regularity", 1.0) < 0.4:
            contributing.append("body")
        # Check body: low daylight exposure
        if body.get("daylight_exposure") is not None and body.get("daylight_exposure", 1.0) < 0.3:
            contributing.append("body")

        # Check hand: high social media usage (digital addiction cycle)
        hand = modalities.get("hand", {})
        if hand.get("social_media_usage") is not None and hand.get("social_media_usage", 0.0) > 0.7:
            contributing.append("hand")

        if len(contributing) >= 2:
            return SafetySignal(
                signal_type="circadian_disruption",
                severity=SafetySeverity.MEDIUM,
                contributing_modalities=contributing,
                recommended_action="Light/rhythm advice — circadian disruption detected",
            )
        return None

    # ------------------------------------------------------------------
    # JITAI Recommendation
    # ------------------------------------------------------------------

    def recommend_jitai(
        self,
        fused: FusedEmotionalState,
        safety_signals: List[SafetySignal],
    ) -> Optional[JITAIAction]:
        """推薦即時適應性介入行動 / Recommend Just-In-Time Adaptive Intervention.

        邏輯:
        - CRITICAL 安全信號 → 轉介
        - HIGH 安全信號 + 高喚醒 → 引導呼吸
        - 遮罩偵測 → 沉默 (MA/MU)
        - 心流狀態 (brain.flow_probability > 0.75) → 心流保護
        - 認知過載 → 休息建議
        - 晝夜紊亂 → 光療時機
        """
        # Priority 1: CRITICAL safety signal → referral
        critical_signals = [
            s for s in safety_signals if s.severity == SafetySeverity.CRITICAL
        ]
        if critical_signals:
            return JITAIAction(
                action_type=JITAIActionType.REFERRAL,
                urgency=1.0,
                reason=critical_signals[0].recommended_action,
                target_engine="therapy",
            )

        # Priority 2: HIGH safety signal + high arousal → guided breathing
        high_signals = [
            s for s in safety_signals if s.severity == SafetySeverity.HIGH
        ]
        if high_signals and fused.arousal > 0.5:
            return JITAIAction(
                action_type=JITAIActionType.GUIDED_BREATHING,
                urgency=_clamp(0.5 + fused.arousal * 0.4, 0.0, 1.0),
                reason=(
                    f"High arousal ({fused.arousal:.2f}) with safety signal: "
                    f"{high_signals[0].signal_type}"
                ),
                target_engine="mouth",
            )

        # Priority 3: Emotional masking → silence
        if fused.emotional_masking_detected:
            return JITAIAction(
                action_type=JITAIActionType.SILENCE,
                urgency=0.6,
                reason="Emotional masking detected — use silence to hold space",
                target_engine="therapy",
            )

        # Priority 4: Flow state protection
        brain_data = fused.modality_weights.get("brain")
        if brain_data is not None:
            # Check if brain data is available in the original modalities
            # We check the fused state's available modalities
            pass
        # Alternative: check if brain flow_probability was high
        # This is checked via the brain result if available
        if "brain" in fused.available_modalities:
            # We need to check the original brain data for flow_probability
            # Since we don't have direct access here, we use a heuristic:
            # If dominant_emotion is SEEKING with high intensity and low contradictions
            if (fused.dominant_emotion == "SEEKING"
                    and fused.intensity > 0.6
                    and not fused.contradictions):
                return JITAIAction(
                    action_type=JITAIActionType.FLOW_PROTECTION,
                    urgency=0.3,
                    reason="Flow state detected — protect the flow",
                    target_engine="mouth",
                )

        # Priority 5: Cognitive overload → break suggestion
        overload_signals = [
            s for s in safety_signals if s.signal_type == "cognitive_overload"
        ]
        if overload_signals:
            return JITAIAction(
                action_type=JITAIActionType.BREAK_SUGGESTION,
                urgency=0.5,
                reason=overload_signals[0].recommended_action,
                target_engine="mouth",
            )

        # Priority 6: Circadian disruption → light therapy
        circadian_signals = [
            s for s in safety_signals if s.signal_type == "circadian_disruption"
        ]
        if circadian_signals:
            return JITAIAction(
                action_type=JITAIActionType.LIGHT_THERAPY,
                urgency=0.4,
                reason=circadian_signals[0].recommended_action,
                target_engine="mouth",
            )

        # Priority 7: HIGH safety signal without high arousal → grounding
        if high_signals:
            return JITAIAction(
                action_type=JITAIActionType.GROUNDING,
                urgency=0.5,
                reason=f"Safety signal detected: {high_signals[0].signal_type}",
                target_engine="therapy",
            )

        return None

    # ------------------------------------------------------------------
    # Dynamic Weight Computation
    # ------------------------------------------------------------------

    def compute_weights(self, modalities: Dict[str, Dict]) -> Dict[str, float]:
        """計算動態模態權重 / Compute dynamic modality weights.

        算法:
        1. 從 BASE_WEIGHTS 開始
        2. 如果模態不可用，按比例重新分配其權重
        3. 如果模態信心 < 0.5，將其權重減半
        4. 如果兩個模態之間有矛盾，增加第三模態權重 0.05
        5. 歸一化使總和為 1.0
        """
        weights: Dict[str, float] = {}
        available = set(modalities.keys())

        # Step 1: Start with base weights for available modalities
        unavailable_weight = 0.0
        for mod, base_w in self._base_weights.items():
            if mod in available:
                weights[mod] = base_w
            else:
                unavailable_weight += base_w

        # Step 2: Redistribute unavailable weight proportionally
        if unavailable_weight > 0.0 and weights:
            total_available = sum(weights.values())
            if total_available > 0.0:
                for mod in weights:
                    weights[mod] += unavailable_weight * (weights[mod] / total_available)

        # Step 3: Reduce weight by half if confidence < 0.5
        for mod, data in modalities.items():
            confidence = data.get("confidence", 1.0)
            if confidence < 0.5 and mod in weights:
                weights[mod] *= 0.5

        # Step 4: Normalize to sum = 1.0
        total = sum(weights.values())
        if total > 0.0:
            weights = {mod: w / total for mod, w in weights.items()}

        return weights

    def _adjust_weights_for_contradictions(
        self,
        weights: Dict[str, float],
        contradictions: List[Contradiction],
        available: List[str],
    ) -> Dict[str, float]:
        """根據矛盾調整權重：增加第三模態權重 0.05 / Adjust weights for contradictions.

        如果兩個模態之間存在矛盾，增加不在矛盾中的第三模態權重。
        """
        if not contradictions:
            return weights

        weights = dict(weights)  # copy

        for contradiction in contradictions:
            involved = {contradiction.modality_a, contradiction.modality_b}
            third_modalities = [m for m in available if m not in involved]
            for third in third_modalities:
                if third in weights:
                    weights[third] += 0.05

        # Re-normalize
        total = sum(weights.values())
        if total > 0.0:
            weights = {mod: w / total for mod, w in weights.items()}

        return weights

    # ------------------------------------------------------------------
    # Pulse conversion
    # ------------------------------------------------------------------

    def to_pulse(self, state: FusedEmotionalState) -> Pulse:
        """將融合情緒狀態轉換為 Pulse / Convert FusedEmotionalState to Pulse."""
        return state.to_pulse()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _collect_modality_data(self, sensory_input: SensoryInput) -> Dict[str, Dict]:
        """收集模態數據 / Collect modality data from SensoryInput."""
        modalities: Dict[str, Dict] = {}
        if sensory_input.eye_result is not None:
            modalities["eye"] = sensory_input.eye_result
        if sensory_input.ear_result is not None:
            modalities["ear"] = sensory_input.ear_result
        if sensory_input.heart_result is not None:
            modalities["heart"] = sensory_input.heart_result
        if sensory_input.brain_result is not None:
            modalities["brain"] = sensory_input.brain_result
        if sensory_input.hand_result is not None:
            modalities["hand"] = sensory_input.hand_result
        if sensory_input.body_result is not None:
            modalities["body"] = sensory_input.body_result
        if sensory_input.text is not None:
            # Text modality: derive basic VAD from text analysis
            modalities["text"] = self._text_to_modality(sensory_input.text)
        return modalities

    def _text_to_modality(self, text: str) -> Dict:
        """將文字轉換為模態數據 / Convert text to modality data.

        簡單的基於關鍵詞的文字情緒分析。
        生產環境中應使用 NLP 模型。
        """
        text_lower = text.lower()

        # Simple keyword-based emotion detection
        emotion_scores: Dict[str, float] = {s: 0.0 for s in PANKSEPP_SYSTEMS}

        # FEAR keywords
        fear_words = ["afraid", "scared", "anxious", "worried", "恐懼", "害怕", "焦慮", "擔心"]
        for w in fear_words:
            if w in text_lower:
                emotion_scores["FEAR"] += 0.3

        # RAGE keywords
        rage_words = ["angry", "furious", "mad", "frustrated", "憤怒", "生氣", "煩躁"]
        for w in rage_words:
            if w in text_lower:
                emotion_scores["RAGE"] += 0.3

        # PANIC keywords
        panic_words = ["panic", "overwhelmed", "desperate", "恐慌", "崩潰", "絕望"]
        for w in panic_words:
            if w in text_lower:
                emotion_scores["PANIC"] += 0.3

        # CARE keywords
        care_words = ["care", "love", "gentle", "comfort", "關心", "愛", "溫柔", "安慰"]
        for w in care_words:
            if w in text_lower:
                emotion_scores["CARE"] += 0.3

        # PLAY keywords
        play_words = ["happy", "fun", "play", "joy", "快樂", "有趣", "玩", "喜悅"]
        for w in play_words:
            if w in text_lower:
                emotion_scores["PLAY"] += 0.3

        # SEEKING keywords
        seeking_words = ["curious", "wonder", "explore", "好奇", "探索", "想知道"]
        for w in seeking_words:
            if w in text_lower:
                emotion_scores["SEEKING"] += 0.3

        # LUST keywords
        lust_words = ["desire", "passion", "attracted", "渴望", "熱情"]
        for w in lust_words:
            if w in text_lower:
                emotion_scores["LUST"] += 0.3

        # Determine dominant emotion
        dominant = max(emotion_scores, key=lambda k: emotion_scores[k])
        max_score = emotion_scores[dominant]

        if max_score == 0.0:
            dominant = "NEUTRAL"

        # Derive VAD from dominant emotion
        if dominant in NEGATIVE_SYSTEMS:
            valence = -0.3 - min(max_score, 0.6)
            arousal = 0.3 + min(max_score, 0.5)
            dominance_val = -0.2 - min(max_score, 0.5)
        elif dominant in POSITIVE_SYSTEMS:
            valence = 0.3 + min(max_score, 0.5)
            arousal = 0.2 + min(max_score, 0.3)
            dominance_val = 0.1 + min(max_score, 0.3)
        else:
            valence = 0.0
            arousal = 0.0
            dominance_val = 0.0

        # Check for denial pattern: "I'm fine" with negative context
        denial_phrases = ["i'm fine", "i am fine", "nothing wrong", "我沒事", "我很好"]
        is_denial = any(p in text_lower for p in denial_phrases)

        return {
            "dominant_emotion": dominant,
            "valence": _clamp(valence, -1.0, 1.0),
            "arousal": _clamp(arousal, -1.0, 1.0),
            "dominance": _clamp(dominance_val, -1.0, 1.0),
            "confidence": _clamp(max_score if max_score > 0 else 0.1, 0.0, 1.0),
            "is_denial": is_denial,
        }

    def _weighted_vad(
        self,
        modalities: Dict[str, Dict],
        weights: Dict[str, float],
        dimension: str,
    ) -> float:
        """計算加權 VAD 維度 / Compute weighted VAD dimension."""
        total = 0.0
        weight_sum = 0.0
        for mod, data in modalities.items():
            w = weights.get(mod, 0.0)
            value = data.get(dimension, 0.0)
            total += w * value
            weight_sum += w
        if weight_sum == 0.0:
            return 0.0
        return _clamp(total / weight_sum, -1.0, 1.0)

    def _weighted_vote(
        self,
        modalities: Dict[str, Dict],
        weights: Dict[str, float],
    ) -> str:
        """加權投票決定主導情緒 / Weighted vote for dominant emotion."""
        emotion_weights: Dict[str, float] = {}
        for mod, data in modalities.items():
            w = weights.get(mod, 0.0)
            emotion = data.get("dominant_emotion", "NEUTRAL")
            emotion_weights[emotion] = emotion_weights.get(emotion, 0.0) + w

        if not emotion_weights:
            return "NEUTRAL"

        return max(emotion_weights, key=lambda k: emotion_weights[k])

    def _compute_intensity(
        self,
        modalities: Dict[str, Dict],
        weights: Dict[str, float],
    ) -> float:
        """計算融合強度 / Compute fused intensity."""
        total = 0.0
        weight_sum = 0.0
        for mod, data in modalities.items():
            w = weights.get(mod, 0.0)
            intensity = data.get("intensity", 0.5)
            total += w * intensity
            weight_sum += w
        if weight_sum == 0.0:
            return 0.0
        return _clamp(total / weight_sum, 0.0, 1.0)

    def _compute_confidence(
        self,
        modalities: Dict[str, Dict],
        weights: Dict[str, float],
        available: List[str],
    ) -> float:
        """計算融合信心 / Compute fused confidence.

        信心 = 加權平均信心 × 模態覆蓋率
        """
        # Weighted average confidence
        total = 0.0
        weight_sum = 0.0
        for mod, data in modalities.items():
            w = weights.get(mod, 0.0)
            conf = data.get("confidence", 0.5)
            total += w * conf
            weight_sum += w
        avg_confidence = total / weight_sum if weight_sum > 0.0 else 0.0

        # Modality coverage factor (more modalities = higher confidence)
        coverage = len(available) / len(BASE_WEIGHTS)

        return _clamp(avg_confidence * (0.5 + 0.5 * coverage), 0.0, 1.0)

    def _detect_masking(
        self,
        contradictions: List[Contradiction],
        safety_signals: List[SafetySignal],
    ) -> bool:
        """偵測情緒遮罩 / Detect emotional masking.

        如果存在臉≠聲矛盾或遮罩安全信號，則判定為遮罩。
        """
        # Check for masking safety signal
        for signal in safety_signals:
            if signal.signal_type == "masking":
                return True

        # Check for eye-ear contradiction
        for c in contradictions:
            if {c.modality_a, c.modality_b} == {"eye", "ear"}:
                return True

        return False
