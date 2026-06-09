"""EmoEye (眼) Visual Perception Engine — 視覺感知引擎

七竅 (Seven Apertures) 多模態感官系統 — 眼

TCM 臟腑對應: 肝 (Liver) — 肝開竅於目
Panksepp 系統: FEAR / SEEKING

三合一能力 (3-in-1 Capabilities):
1. 面部情緒偵測 (Facial Emotion Detection)
   — 微表情 → Panksepp 七大系統映射
2. rPPG 心率偵測 (Remote Photoplethysmography)
   — 面部視頻 → 心率 + HRV → 饋入 EmoHeart
3. 姿態分析 (Posture Analysis)
   — 頭部姿態 + 肩膀位置 → 饋入 EmoBody

Panksepp 面部表情映射:
    Duchenne smile       → PLAY   (V=+0.7, A=0.5)
    Frown + raised brows → FEAR   (V=-0.6, A=0.7)
    Tight lips + narrow  → RAGE   (V=-0.7, A=0.8)
    Wide eyes + open     → PANIC  (V=-0.8, A=0.9)
    Soft smile + relaxed → CARE   (V=+0.5, A=0.3)
    Raised brows + focus → SEEKING(V=+0.3, A=0.6)
    Downward gaze + slouch → PANIC dorsal (V=-0.5, A=0.2) ⚠️ Shutdown signal

設計原則:
- 自包含，無外部依賴 (僅 stdlib) — 後端為抽象介面
- 數值穩定 — 所有浮點範圍使用 _clamp 保護
- 可序列化 — 所有 dataclass 支援 to_dict / from_dict
- Pulse 整合 — to_pulse() 方法將結果轉為 Pulse 物件
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from ..pulse import Pulse, PulseType
from .audience_config import AudienceMode


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clamp(value: float, lo: float, hi: float) -> float:
    """將浮點數限制在 [lo, hi] 區間內"""
    return max(lo, min(hi, value))


# ---------------------------------------------------------------------------
# Facial Expression → Panksepp Mapping
# ---------------------------------------------------------------------------

FACIAL_EXPRESSION_MAP: Dict[str, Tuple[PulseType, float, float]] = {
    # expression_name: (PulseType, valence, arousal)
    "duchenne_smile":       (PulseType.PLAY,    +0.7, 0.5),
    "frown_raised_brows":   (PulseType.FEAR,    -0.6, 0.7),
    "tight_lips_narrow_eyes": (PulseType.RAGE,  -0.7, 0.8),
    "wide_eyes_open_mouth": (PulseType.PANIC,   -0.8, 0.9),
    "soft_smile_relaxed":   (PulseType.CARE,    +0.5, 0.3),
    "raised_brows_focused": (PulseType.SEEKING, +0.3, 0.6),
    # ⚠️ Shutdown signal — PANIC dorsal vagal
    "downward_gaze_slouch": (PulseType.PANIC,   -0.5, 0.2),
}

# Reverse lookup: Panksepp system name → PulseType
_PANKSEPP_NAME_TO_PULSE: Dict[str, PulseType] = {
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
# Simplified Emotion Set for Kids (童心模式簡化情緒集)
# ---------------------------------------------------------------------------

PANKSEPP_TO_BASIC_EMOTION: Dict[str, str] = {
    "SEEKING": "happy",   # curiosity = positive
    "RAGE":    "angry",
    "FEAR":    "scared",
    "LUST":    "loved",   # desire/attraction → warmth
    "CARE":    "loved",
    "PANIC":   "sad",
    "PLAY":    "happy",
    "NEUTRAL": "happy",   # default to positive
}

BASIC_EMOTION_VAD: Dict[str, Tuple[float, float, float]] = {
    # basic_emotion: (valence, arousal, dominance)
    "happy":  ( 0.7,  0.5,  0.5),
    "sad":    (-0.6,  0.2, -0.3),
    "angry":  (-0.7,  0.8,  0.6),
    "scared": (-0.6,  0.7, -0.5),
    "loved":  ( 0.8,  0.3,  0.2),
}


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class HeadPose:
    """頭部姿態 — Head pose estimation from webcam

    三軸旋轉角度，用於判斷注意力方向與情緒狀態。
    """
    tilt: float   # degrees, positive = right tilt (右傾)
    yaw: float    # degrees, positive = looking right (向右看)
    roll: float   # degrees, positive = tilting right (右旋)

    def __post_init__(self) -> None:
        self.tilt = _clamp(float(self.tilt), -90.0, 90.0)
        self.yaw  = _clamp(float(self.yaw),  -90.0, 90.0)
        self.roll = _clamp(float(self.roll), -90.0, 90.0)

    def to_dict(self) -> Dict[str, float]:
        return {"tilt": self.tilt, "yaw": self.yaw, "roll": self.roll}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> HeadPose:
        return cls(
            tilt=float(data["tilt"]),
            yaw=float(data["yaw"]),
            roll=float(data["roll"]),
        )


@dataclass
class ShoulderPosition:
    """肩膀位置 — Shoulder position from webcam

    正規化座標與對齊度，用於姿態評估與壓力偵測。
    """
    left_y: float     # 0.0-1.0 normalized vertical position
    right_y: float    # 0.0-1.0 normalized vertical position
    alignment: float  # 0.0 (uneven) to 1.0 (perfectly aligned)

    def __post_init__(self) -> None:
        self.left_y    = _clamp(float(self.left_y),    0.0, 1.0)
        self.right_y   = _clamp(float(self.right_y),   0.0, 1.0)
        self.alignment = _clamp(float(self.alignment), 0.0, 1.0)

    def to_dict(self) -> Dict[str, float]:
        return {
            "left_y": self.left_y,
            "right_y": self.right_y,
            "alignment": self.alignment,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ShoulderPosition:
        return cls(
            left_y=float(data["left_y"]),
            right_y=float(data["right_y"]),
            alignment=float(data["alignment"]),
        )


@dataclass
class HRVMetrics:
    """心率變異度指標 — Heart Rate Variability metrics from rPPG

    由遠程光電容積脈搏波 (rPPG) 提取的心率與 HRV 指標，
    饋入 EmoHeart 引擎進行更深層心血管情緒分析。
    """
    heart_rate: float    # BPM
    sdnn: float          # ms, standard deviation of NN intervals
    rmssd: float         # ms, root mean square of successive differences
    lf_hf_ratio: float   # sympathetic / parasympathetic balance
    stress_index: float  # 0.0 (relaxed) to 1.0 (high stress)

    def __post_init__(self) -> None:
        if self.heart_rate < 0:
            raise ValueError(f"heart_rate must be >= 0, got {self.heart_rate}")
        if self.sdnn < 0:
            raise ValueError(f"sdnn must be >= 0, got {self.sdnn}")
        if self.rmssd < 0:
            raise ValueError(f"rmssd must be >= 0, got {self.rmssd}")
        self.stress_index = _clamp(float(self.stress_index), 0.0, 1.0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "heart_rate": self.heart_rate,
            "sdnn": self.sdnn,
            "rmssd": self.rmssd,
            "lf_hf_ratio": self.lf_hf_ratio,
            "stress_index": self.stress_index,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> HRVMetrics:
        return cls(
            heart_rate=float(data["heart_rate"]),
            sdnn=float(data["sdnn"]),
            rmssd=float(data["rmssd"]),
            lf_hf_ratio=float(data["lf_hf_ratio"]),
            stress_index=float(data["stress_index"]),
        )


@dataclass
class EmoEyeResult:
    """EmoEye 視覺感知結果 — Visual perception result

    整合面部情緒、rPPG 心率、姿態分析三大感知通道的結果。
    """
    dominant_emotion: str    # Panksepp system name
    valence: float           # -1.0 to 1.0
    arousal: float           # -1.0 to 1.0
    dominance: float         # -1.0 to 1.0
    intensity: float         # 0.0 to 1.0
    confidence: float        # 0.0 to 1.0

    # Visual-specific fields
    facial_landmarks: Optional[List[float]] = None  # flat list of landmark coordinates
    head_pose: Optional[HeadPose] = None
    shoulder_position: Optional[ShoulderPosition] = None
    rppg_heart_rate: Optional[float] = None         # BPM from facial video
    rppg_hrv: Optional[HRVMetrics] = None           # HRV metrics from rPPG
    posture_score: Optional[float] = None            # 0.0 (slouched) to 1.0 (upright)

    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        self.valence   = _clamp(float(self.valence),   -1.0, 1.0)
        self.arousal   = _clamp(float(self.arousal),   -1.0, 1.0)
        self.dominance = _clamp(float(self.dominance), -1.0, 1.0)
        self.intensity = _clamp(float(self.intensity),  0.0, 1.0)
        self.confidence = _clamp(float(self.confidence), 0.0, 1.0)

        if self.dominant_emotion not in _PANKSEPP_NAME_TO_PULSE:
            raise ValueError(
                f"dominant_emotion must be a Panksepp system name, "
                f"got '{self.dominant_emotion}'. "
                f"Valid: {list(_PANKSEPP_NAME_TO_PULSE.keys())}"
            )

        if self.rppg_heart_rate is not None and self.rppg_heart_rate < 0:
            raise ValueError(
                f"rppg_heart_rate must be >= 0, got {self.rppg_heart_rate}"
            )

        if self.posture_score is not None:
            self.posture_score = _clamp(float(self.posture_score), 0.0, 1.0)

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "dominant_emotion": self.dominant_emotion,
            "valence": self.valence,
            "arousal": self.arousal,
            "dominance": self.dominance,
            "intensity": self.intensity,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat(),
        }
        if self.facial_landmarks is not None:
            result["facial_landmarks"] = self.facial_landmarks
        if self.head_pose is not None:
            result["head_pose"] = self.head_pose.to_dict()
        if self.shoulder_position is not None:
            result["shoulder_position"] = self.shoulder_position.to_dict()
        if self.rppg_heart_rate is not None:
            result["rppg_heart_rate"] = self.rppg_heart_rate
        if self.rppg_hrv is not None:
            result["rppg_hrv"] = self.rppg_hrv.to_dict()
        if self.posture_score is not None:
            result["posture_score"] = self.posture_score
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> EmoEyeResult:
        head_pose = None
        if data.get("head_pose") is not None:
            head_pose = HeadPose.from_dict(data["head_pose"])

        shoulder_position = None
        if data.get("shoulder_position") is not None:
            shoulder_position = ShoulderPosition.from_dict(data["shoulder_position"])

        rppg_hrv = None
        if data.get("rppg_hrv") is not None:
            rppg_hrv = HRVMetrics.from_dict(data["rppg_hrv"])

        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        elif timestamp is None:
            timestamp = datetime.now(timezone.utc)

        return cls(
            dominant_emotion=data["dominant_emotion"],
            valence=float(data["valence"]),
            arousal=float(data["arousal"]),
            dominance=float(data["dominance"]),
            intensity=float(data["intensity"]),
            confidence=float(data["confidence"]),
            facial_landmarks=data.get("facial_landmarks"),
            head_pose=head_pose,
            shoulder_position=shoulder_position,
            rppg_heart_rate=data.get("rppg_heart_rate"),
            rppg_hrv=rppg_hrv,
            posture_score=data.get("posture_score"),
            timestamp=timestamp,
        )

    def to_pulse(self) -> Pulse:
        """將 EmoEyeResult 轉為 Pulse 物件 — Convert to Pulse for EmoGlyph integration"""
        pulse_type = _PANKSEPP_NAME_TO_PULSE.get(
            self.dominant_emotion, PulseType.NEUTRAL
        )
        return Pulse(
            pulse_type=pulse_type,
            valence=self.valence,
            arousal=self.arousal,
            dominance=self.dominance,
            intensity=self.intensity,
        )


# ---------------------------------------------------------------------------
# Abstract Backend
# ---------------------------------------------------------------------------

class EmoEyeBackend(ABC):
    """EmoEye 後端抽象介面 — Abstract backend for visual perception

    具體實作可選擇雲端 API 或本地模型，引擎本身不依賴任何外部套件。
    """

    @abstractmethod
    def detect(self, image_data: bytes) -> EmoEyeResult:
        """從影像資料偵測視覺情緒 — Detect visual emotion from image data

        Args:
            image_data: Raw image bytes (JPEG/PNG/etc.)

        Returns:
            EmoEyeResult with detected emotion, pose, and rPPG data.
        """
        ...


class CloudEmoEyeBackend(EmoEyeBackend):
    """雲端視覺感知後端 — Cloud visual perception backend

    整合:
    - Google Vision API / Azure Face API / Hume AI — 面部情緒偵測
    - Binah.ai — rPPG 心率偵測

    此為佔位實作，實際部署時需配置 API 金鑰。
    """

    def detect(self, image_data: bytes) -> EmoEyeResult:
        # Placeholder — cloud API integration
        return EmoEyeResult(
            dominant_emotion="NEUTRAL",
            valence=0.0,
            arousal=0.0,
            dominance=0.0,
            intensity=0.0,
            confidence=0.0,
        )


class LocalEmoEyeBackend(EmoEyeBackend):
    """本地視覺感知後端 — Local visual perception backend

    整合:
    - OpenCV + FER / DeepFace — 面部情緒偵測
    - MediaPipe Pose — 姿態分析
    - PhysNet — rPPG 心率偵測

    此為佔位實作，實際部署時需安裝對應套件。
    """

    def detect(self, image_data: bytes) -> EmoEyeResult:
        # Placeholder — local model inference
        return EmoEyeResult(
            dominant_emotion="NEUTRAL",
            valence=0.0,
            arousal=0.0,
            dominance=0.0,
            intensity=0.0,
            confidence=0.0,
        )


# ---------------------------------------------------------------------------
# Main Engine
# ---------------------------------------------------------------------------

class EmoEyeEngine:
    """EmoEye 視覺感知引擎 — Visual Perception Engine

    七竅之首 — 眼 (肝開竅於目)

    三合一感知:
    1. 面部情緒偵測 → Panksepp 七大系統
    2. rPPG 心率偵測 → 饋入 EmoHeart
    3. 姿態分析 → 饋入 EmoBody

    使用方式:
        engine = EmoEyeEngine(backend=LocalEmoEyeBackend())
        result = engine.detect(image_bytes)
        pulse = engine.to_pulse(result)
    """

    def __init__(self, backend: Optional[EmoEyeBackend] = None) -> None:
        self._backend = backend

    def detect(self, image_data: bytes, simplified: bool = False) -> EmoEyeResult:
        """執行視覺感知偵測 — Run visual perception detection

        Args:
            image_data: Raw image bytes from webcam or video frame.
            simplified: When True, map Panksepp emotions to a simplified
                5-emotion set for kids and override VAD values accordingly.

        Returns:
            EmoEyeResult with all detected visual signals.

        Raises:
            RuntimeError: If no backend is configured.
        """
        if self._backend is None:
            raise RuntimeError(
                "No EmoEyeBackend configured. "
                "Pass a backend to EmoEyeEngine(backend=...)."
            )
        result = self._backend.detect(image_data)
        if simplified:
            basic_emotion = PANKSEPP_TO_BASIC_EMOTION.get(
                result.dominant_emotion, "happy"
            )
            v, a, d = BASIC_EMOTION_VAD[basic_emotion]
            object.__setattr__(result, "dominant_emotion", basic_emotion)
            object.__setattr__(result, "valence", _clamp(v, -1.0, 1.0))
            object.__setattr__(result, "arousal", _clamp(a, -1.0, 1.0))
            object.__setattr__(result, "dominance", _clamp(d, -1.0, 1.0))
        return result

    def to_pulse(self, result: EmoEyeResult) -> Pulse:
        """將偵測結果轉為 Pulse — Convert detection result to Pulse

        透過 dominant_emotion 查找 PulseType，結合 valence/arousal/dominance/intensity
        產生標準 Pulse 物件，供 EmoGlyph 系統整合使用。
        """
        return result.to_pulse()

    def detect_for_audience(
        self, image_data: bytes, audience_mode: AudienceMode
    ) -> EmoEyeResult:
        """依受眾模式執行偵測 — Detect with audience-appropriate emotion mapping

        Kids mode uses the simplified 5-emotion set; elderly mode uses
        the full Panksepp 7-system mapping.

        Args:
            image_data: Raw image bytes from webcam or video frame.
            audience_mode: Target audience mode (KIDS or ELDERLY).

        Returns:
            EmoEyeResult with audience-appropriate emotion labels and VAD.
        """
        simplified = audience_mode == AudienceMode.KIDS
        return self.detect(image_data, simplified=simplified)

    @staticmethod
    def lookup_expression(expression_name: str) -> Tuple[PulseType, float, float]:
        """查詢面部表情映射 — Look up facial expression → Panksepp mapping

        Args:
            expression_name: Key in FACIAL_EXPRESSION_MAP.

        Returns:
            (PulseType, valence, arousal) tuple.

        Raises:
            KeyError: If expression_name is not in the map.
        """
        if expression_name not in FACIAL_EXPRESSION_MAP:
            raise KeyError(
                f"Unknown expression '{expression_name}'. "
                f"Valid: {list(FACIAL_EXPRESSION_MAP.keys())}"
            )
        return FACIAL_EXPRESSION_MAP[expression_name]

    @staticmethod
    def expression_to_result(
        expression_name: str,
        dominance: float = 0.0,
        intensity: float = 0.5,
        confidence: float = 0.5,
        head_pose: Optional[HeadPose] = None,
        shoulder_position: Optional[ShoulderPosition] = None,
        rppg_heart_rate: Optional[float] = None,
        rppg_hrv: Optional[HRVMetrics] = None,
        posture_score: Optional[float] = None,
        facial_landmarks: Optional[List[float]] = None,
    ) -> EmoEyeResult:
        """從面部表情名稱快速建立 EmoEyeResult — Build result from expression name

        使用 FACIAL_EXPRESSION_MAP 查找 valence/arousal，其餘欄位可自訂。
        """
        pulse_type, valence, arousal = FACIAL_EXPRESSION_MAP[expression_name]
        return EmoEyeResult(
            dominant_emotion=pulse_type.name,
            valence=valence,
            arousal=arousal,
            dominance=dominance,
            intensity=intensity,
            confidence=confidence,
            facial_landmarks=facial_landmarks,
            head_pose=head_pose,
            shoulder_position=shoulder_position,
            rppg_heart_rate=rppg_heart_rate,
            rppg_hrv=rppg_hrv,
            posture_score=posture_score,
        )


# ---------------------------------------------------------------------------
# Module self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    def _expect(cond: bool, label: str) -> None:
        print(("PASS" if cond else "FAIL") + f" — {label}")

    # HeadPose validation
    hp = HeadPose(tilt=100.0, yaw=45.0, roll=-30.0)
    _expect(hp.tilt == 90.0, "HeadPose tilt clamped to 90")

    # ShoulderPosition validation
    sp = ShoulderPosition(left_y=0.5, right_y=0.6, alignment=1.5)
    _expect(sp.alignment == 1.0, "ShoulderPosition alignment clamped to 1.0")

    # HRVMetrics validation
    hrv = HRVMetrics(heart_rate=72.0, sdnn=50.0, rmssd=30.0, lf_hf_ratio=1.5, stress_index=0.3)
    _expect(hrv.heart_rate == 72.0, "HRVMetrics heart_rate preserved")

    try:
        HRVMetrics(heart_rate=-1, sdnn=0, rmssd=0, lf_hf_ratio=0, stress_index=0)
    except ValueError:
        _expect(True, "HRVMetrics negative heart_rate raises ValueError")

    # EmoEyeResult validation
    result = EmoEyeResult(
        dominant_emotion="FEAR",
        valence=-0.6,
        arousal=0.7,
        dominance=-0.5,
        intensity=0.8,
        confidence=0.9,
        head_pose=hp,
        shoulder_position=sp,
        rppg_heart_rate=72.0,
        rppg_hrv=hrv,
        posture_score=0.6,
    )
    _expect(result.dominant_emotion == "FEAR", "EmoEyeResult dominant_emotion preserved")
    _expect(result.head_pose is not None, "EmoEyeResult head_pose preserved")

    try:
        EmoEyeResult(
            dominant_emotion="INVALID",
            valence=0.0, arousal=0.0, dominance=0.0,
            intensity=0.0, confidence=0.0,
        )
    except ValueError:
        _expect(True, "EmoEyeResult invalid dominant_emotion raises ValueError")

    # to_pulse
    pulse = result.to_pulse()
    _expect(pulse.pulse_type == PulseType.FEAR, "to_pulse maps FEAR correctly")
    _expect(abs(pulse.valence - (-0.6)) < 1e-6, "to_pulse valence preserved")

    # to_dict / from_dict round-trip
    d = result.to_dict()
    restored = EmoEyeResult.from_dict(d)
    _expect(restored.dominant_emotion == "FEAR", "from_dict dominant_emotion round-trip")
    _expect(abs(restored.valence - result.valence) < 1e-6, "from_dict valence round-trip")
    _expect(restored.head_pose is not None, "from_dict head_pose round-trip")

    # FACIAL_EXPRESSION_MAP lookup
    pt, v, a = EmoEyeEngine.lookup_expression("duchenne_smile")
    _expect(pt == PulseType.PLAY, "lookup_expression maps duchenne_smile → PLAY")
    _expect(abs(v - 0.7) < 1e-6, "lookup_expression valence for duchenne_smile")

    # expression_to_result
    expr_result = EmoEyeEngine.expression_to_result("soft_smile_relaxed", intensity=0.7)
    _expect(expr_result.dominant_emotion == "CARE", "expression_to_result → CARE")
    _expect(abs(expr_result.intensity - 0.7) < 1e-6, "expression_to_result intensity")

    # Engine without backend raises RuntimeError
    engine_no_backend = EmoEyeEngine()
    try:
        engine_no_backend.detect(b"fake")
    except RuntimeError:
        _expect(True, "detect without backend raises RuntimeError")

    # Engine with placeholder backend
    engine = EmoEyeEngine(backend=LocalEmoEyeBackend())
    placeholder_result = engine.detect(b"fake")
    _expect(placeholder_result.dominant_emotion == "NEUTRAL", "placeholder backend returns NEUTRAL")

    print("OK — emo_eye.py smoke tests done")
