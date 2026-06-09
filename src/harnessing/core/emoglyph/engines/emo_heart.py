"""EmoHeart (心) Physiological Engine — 心臟生理引擎

七竅 (Seven Apertures) 多模態感官系統 — 心竅

TCM 臟腑: 心 (Heart) — 心主血脈，心藏神
Panksepp 系統: PANIC / CARE

3-in-1 能力:
1. HRV Analysis — 心率變異度分析 (rPPG 或穿戴式裝置 → 壓力指數)
2. Stress Biomarker Fusion — 壓力生物標記融合 (HRV + 呼吸 + 皮膚溫度代理 → 壓力分數)
3. Wearable Integration — 穿戴式裝置整合 (Apple HealthKit / Oura API / Fitbit API → 情感健康脈絡)

自律神經狀態分類:
- SYMPATHETIC_DOMINANT  — 戰鬥/逃跑活躍 (交感神經主導)
- PARASYMPATHETIC_DOMINANT — 休息/消化活躍 (副交感神經主導)
- BALANCED — 健康調節 (平衡)
- DORSAL_VAGAL — 關閉/凍結 ⚠️ (背側迷走神經)

壓力分數融合公式:
    stress_score = w_hrv × (1 - hrv.rmssd / max_rmssd)
                 + w_resp × respiration_deviation
                 + w_context × ambient_stress

設計原則:
- 自包含，無外部依賴 (僅 stdlib)
- 數值穩定 (所有浮點值經 _clamp 保護)
- 可解釋 (每個輸入都有生理學依據)
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from ..pulse import Pulse, PulseType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clamp(value: float, lo: float, hi: float) -> float:
    """將浮點數限制在 [lo, hi] 區間內 / Clamp float to [lo, hi]."""
    return max(lo, min(hi, value))


# ---------------------------------------------------------------------------
# Constants — 融合權重與閾值
# ---------------------------------------------------------------------------

# Stress score fusion weights
W_HRV: float = 0.5       # HRV 權重
W_RESP: float = 0.3      # 呼吸權重
W_CONTEXT: float = 0.2   # 環境壓力權重

# HRV normalisation ceiling
MAX_RMSSD: float = 100.0  # rmssd 歸一化上限 (ms)

# Normal respiration rate (breaths per minute)
NORMAL_RESPIRATION: float = 16.0

# Autonomic classification thresholds
LF_HF_SYMPATHETIC_THRESHOLD: float = 2.5   # 交感神經閾值
HR_SYMPATHETIC_THRESHOLD: float = 90.0     # 心率交感閾值 (BPM)
LF_HF_PARASYMPATHETIC_THRESHOLD: float = 0.5  # 副交感神經閾值
HR_PARASYMPATHETIC_THRESHOLD: float = 60.0    # 心率副交感閾值 (BPM)
RMSSD_DORSAL_THRESHOLD: float = 15.0       # 背側迷走 rmssd 閾值 (ms)
SDNN_DORSAL_THRESHOLD: float = 20.0        # 背側迷走 sdnn 閾值 (ms)


# ---------------------------------------------------------------------------
# Autonomic State — 自律神經狀態
# ---------------------------------------------------------------------------

class AutonomicState(Enum):
    """自律神經狀態 / Autonomic nervous system state.

    SYMPATHETIC_DOMINANT   — 戰鬥/逃跑活躍 (交感神經主導)
    PARASYMPATHETIC_DOMINANT — 休息/消化活躍 (副交感神經主導)
    BALANCED               — 健康調節 (平衡)
    DORSAL_VAGAL           — 關閉/凍結 ⚠️ (背側迷走神經)
    """
    SYMPATHETIC_DOMINANT = "sympathetic_dominant"
    PARASYMPATHETIC_DOMINANT = "parasympathetic_dominant"
    BALANCED = "balanced"
    DORSAL_VAGAL = "dorsal_vagal"


# ---------------------------------------------------------------------------
# Recovery Status — 恢復狀態
# ---------------------------------------------------------------------------

class RecoveryStatus(Enum):
    """恢復狀態 / Recovery status.

    RECOVERED  — 已恢復
    RECOVERING — 恢復中
    DEPLETED   — 耗竭
    """
    RECOVERED = "recovered"
    RECOVERING = "recovering"
    DEPLETED = "depleted"


# ---------------------------------------------------------------------------
# Data Classes — 資料類別
# ---------------------------------------------------------------------------

@dataclass
class HRVMetrics:
    """心率變異度指標 / Heart Rate Variability metrics.

    heart_rate:  心率 BPM (正常: 60-100)
    sdnn:        NN 間期標準差 ms (正常: 30-80)
    rmssd:       相鄰 NN 差值的均方根 ms (正常: 20-60)
    lf_hf_ratio: 低頻/高頻功率比 — 交感/副交感平衡 (正常: 0.5-2.0)
    stress_index: 壓力指數 0.0 (放鬆) ~ 1.0 (高壓力)
    """
    heart_rate: float
    sdnn: float
    rmssd: float
    lf_hf_ratio: float
    stress_index: float

    def __post_init__(self) -> None:
        if not 20.0 <= self.heart_rate <= 220.0:
            raise ValueError(
                f"heart_rate must be in [20, 220], got {self.heart_rate}"
            )
        if not 0.0 <= self.sdnn <= 500.0:
            raise ValueError(
                f"sdnn must be in [0, 500], got {self.sdnn}"
            )
        if not 0.0 <= self.rmssd <= 500.0:
            raise ValueError(
                f"rmssd must be in [0, 500], got {self.rmssd}"
            )
        if not 0.0 <= self.lf_hf_ratio <= 20.0:
            raise ValueError(
                f"lf_hf_ratio must be in [0, 20], got {self.lf_hf_ratio}"
            )
        self.stress_index = _clamp(self.stress_index, 0.0, 1.0)

    def to_dict(self) -> Dict[str, Any]:
        """序列化為字典 / Serialize to dict."""
        return {
            "heart_rate": self.heart_rate,
            "sdnn": self.sdnn,
            "rmssd": self.rmssd,
            "lf_hf_ratio": self.lf_hf_ratio,
            "stress_index": self.stress_index,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> HRVMetrics:
        """從字典反序列化 / Deserialize from dict."""
        return cls(
            heart_rate=float(data["heart_rate"]),
            sdnn=float(data["sdnn"]),
            rmssd=float(data["rmssd"]),
            lf_hf_ratio=float(data["lf_hf_ratio"]),
            stress_index=float(data["stress_index"]),
        )


@dataclass
class SleepData:
    """睡眠數據 / Sleep data.

    total_hours:      總睡眠時數
    deep_sleep_hours: 深層睡眠時數
    rem_sleep_hours:  快速動眼睡眠時數
    sleep_efficiency: 睡眠效率 0.0-1.0
    sleep_regularity: 睡眠規律性 0.0-1.0
    """
    total_hours: float
    deep_sleep_hours: float
    rem_sleep_hours: float
    sleep_efficiency: float
    sleep_regularity: float

    def __post_init__(self) -> None:
        if not 0.0 <= self.total_hours <= 24.0:
            raise ValueError(
                f"total_hours must be in [0, 24], got {self.total_hours}"
            )
        if not 0.0 <= self.deep_sleep_hours <= self.total_hours:
            raise ValueError(
                f"deep_sleep_hours must be in [0, {self.total_hours}], "
                f"got {self.deep_sleep_hours}"
            )
        if not 0.0 <= self.rem_sleep_hours <= self.total_hours:
            raise ValueError(
                f"rem_sleep_hours must be in [0, {self.total_hours}], "
                f"got {self.rem_sleep_hours}"
            )
        self.sleep_efficiency = _clamp(self.sleep_efficiency, 0.0, 1.0)
        self.sleep_regularity = _clamp(self.sleep_regularity, 0.0, 1.0)

    def to_dict(self) -> Dict[str, Any]:
        """序列化為字典 / Serialize to dict."""
        return {
            "total_hours": self.total_hours,
            "deep_sleep_hours": self.deep_sleep_hours,
            "rem_sleep_hours": self.rem_sleep_hours,
            "sleep_efficiency": self.sleep_efficiency,
            "sleep_regularity": self.sleep_regularity,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SleepData:
        """從字典反序列化 / Deserialize from dict."""
        return cls(
            total_hours=float(data["total_hours"]),
            deep_sleep_hours=float(data["deep_sleep_hours"]),
            rem_sleep_hours=float(data["rem_sleep_hours"]),
            sleep_efficiency=float(data["sleep_efficiency"]),
            sleep_regularity=float(data["sleep_regularity"]),
        )


@dataclass
class ActivityData:
    """活動數據 / Activity data.

    steps:            步數
    active_minutes:   活動分鐘數
    sedentary_hours:  久坐時數
    calories_burned:  消耗卡路里
    """
    steps: int
    active_minutes: float
    sedentary_hours: float
    calories_burned: float

    def __post_init__(self) -> None:
        if self.steps < 0:
            raise ValueError(f"steps must be >= 0, got {self.steps}")
        if self.active_minutes < 0.0:
            raise ValueError(
                f"active_minutes must be >= 0, got {self.active_minutes}"
            )
        if self.sedentary_hours < 0.0:
            raise ValueError(
                f"sedentary_hours must be >= 0, got {self.sedentary_hours}"
            )
        if self.calories_burned < 0.0:
            raise ValueError(
                f"calories_burned must be >= 0, got {self.calories_burned}"
            )

    def to_dict(self) -> Dict[str, Any]:
        """序列化為字典 / Serialize to dict."""
        return {
            "steps": self.steps,
            "active_minutes": self.active_minutes,
            "sedentary_hours": self.sedentary_hours,
            "calories_burned": self.calories_burned,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ActivityData:
        """從字典反序列化 / Deserialize from dict."""
        return cls(
            steps=int(data["steps"]),
            active_minutes=float(data["active_minutes"]),
            sedentary_hours=float(data["sedentary_hours"]),
            calories_burned=float(data["calories_burned"]),
        )


@dataclass
class EmoHeartResult:
    """EmoHeart 引擎結果 / EmoHeart engine result.

    hrv:              心率變異度指標 (可為 None)
    stress_score:     壓力分數 0.0-1.0 (融合 HRV + 呼吸 + 脈絡)
    autonomic_state:  自律神經狀態
    recovery_status:  恢復狀態
    source:           數據來源 ("rppg", "wearable_apple", "wearable_oura",
                      "wearable_fitbit", "manual")
    respiration_rate: 呼吸速率 (次/分鐘，可為 None)
    timestamp:        時間戳記
    """
    hrv: Optional[HRVMetrics]
    stress_score: float
    autonomic_state: AutonomicState
    recovery_status: RecoveryStatus
    source: str
    respiration_rate: Optional[float]
    timestamp: datetime

    def __post_init__(self) -> None:
        self.stress_score = _clamp(self.stress_score, 0.0, 1.0)
        if self.source not in (
            "rppg", "wearable_apple", "wearable_oura",
            "wearable_fitbit", "manual",
        ):
            raise ValueError(f"Invalid source: {self.source}")
        if self.respiration_rate is not None:
            if not 4.0 <= self.respiration_rate <= 60.0:
                raise ValueError(
                    f"respiration_rate must be in [4, 60], "
                    f"got {self.respiration_rate}"
                )

    def to_dict(self) -> Dict[str, Any]:
        """序列化為字典 / Serialize to dict."""
        return {
            "hrv": self.hrv.to_dict() if self.hrv is not None else None,
            "stress_score": self.stress_score,
            "autonomic_state": self.autonomic_state.value,
            "recovery_status": self.recovery_status.value,
            "source": self.source,
            "respiration_rate": self.respiration_rate,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> EmoHeartResult:
        """從字典反序列化 / Deserialize from dict."""
        hrv_data = data.get("hrv")
        return cls(
            hrv=HRVMetrics.from_dict(hrv_data) if hrv_data is not None else None,
            stress_score=float(data["stress_score"]),
            autonomic_state=AutonomicState(data["autonomic_state"]),
            recovery_status=RecoveryStatus(data["recovery_status"]),
            source=str(data["source"]),
            respiration_rate=(
                float(data["respiration_rate"])
                if data.get("respiration_rate") is not None
                else None
            ),
            timestamp=datetime.fromisoformat(data["timestamp"]),
        )

    def to_pulse(self) -> Pulse:
        """將結果轉換為 EmoGlyph Pulse / Convert result to EmoGlyph Pulse.

        自律神經狀態 → PulseType 映射:
        - SYMPATHETIC_DOMINANT → FEAR (低壓力) 或 PANIC (高壓力)
        - PARASYMPATHETIC_DOMINANT → CARE
        - BALANCED → NEUTRAL
        - DORSAL_VAGAL → PANIC (高強度)
        """
        if self.autonomic_state == AutonomicState.SYMPATHETIC_DOMINANT:
            if self.stress_score >= 0.7:
                pulse_type = PulseType.PANIC
            else:
                pulse_type = PulseType.FEAR
            intensity = _clamp(self.stress_score, 0.0, 1.0)
        elif self.autonomic_state == AutonomicState.PARASYMPATHETIC_DOMINANT:
            pulse_type = PulseType.CARE
            intensity = _clamp(0.3 + 0.3 * (1.0 - self.stress_score), 0.0, 1.0)
        elif self.autonomic_state == AutonomicState.BALANCED:
            pulse_type = PulseType.NEUTRAL
            intensity = _clamp(0.3, 0.0, 1.0)
        elif self.autonomic_state == AutonomicState.DORSAL_VAGAL:
            pulse_type = PulseType.PANIC
            intensity = _clamp(0.9, 0.0, 1.0)
        else:
            pulse_type = PulseType.NEUTRAL
            intensity = 0.3

        return Pulse.from_type(pulse_type, intensity=intensity)


# ---------------------------------------------------------------------------
# Autonomic State → Therapy Mapping — 自律神經狀態 → 療癒映射
# ---------------------------------------------------------------------------

AUTONOMIC_THERAPY_MAP: Dict[AutonomicState, Dict[str, Any]] = {
    AutonomicState.SYMPATHETIC_DOMINANT: {
        "label_zh": "交感神經主導",
        "label_en": "Sympathetic Dominant",
        "therapies": ["guided_breathing_478", "grounding_exercise"],
        "description_zh": "引導呼吸 (4-7-8)、接地練習",
        "description_en": "Guided breathing (4-7-8), grounding exercise",
    },
    AutonomicState.PARASYMPATHETIC_DOMINANT: {
        "label_zh": "副交感神經主導",
        "label_en": "Parasympathetic Dominant",
        "therapies": ["normal_interaction", "encourage_expression"],
        "description_zh": "正常互動，鼓勵表達",
        "description_en": "Normal interaction, encourage expression",
    },
    AutonomicState.BALANCED: {
        "label_zh": "自律平衡",
        "label_en": "Balanced Autonomic",
        "therapies": ["maintain_current_approach"],
        "description_zh": "維持當前方式",
        "description_en": "Maintain current approach",
    },
    AutonomicState.DORSAL_VAGAL: {
        "label_zh": "背側迷走神經 ⚠️",
        "label_en": "Dorsal Vagal ⚠️",
        "therapies": ["safety_check", "professional_referral"],
        "description_zh": "安全確認，專業轉介",
        "description_en": "Safety check, professional referral",
    },
}


# ---------------------------------------------------------------------------
# Abstract Wearable Adapter — 穿戴式裝置抽象介面
# ---------------------------------------------------------------------------

class WearableAdapter(ABC):
    """穿戴式裝置抽象介面 / Abstract wearable device adapter.

    所有穿戴式裝置適配器必須實作此介面。
    All wearable device adapters must implement this interface.
    """

    @abstractmethod
    def get_hrv(self) -> HRVMetrics:
        """取得心率變異度數據 / Get HRV metrics."""
        ...

    @abstractmethod
    def get_sleep(self) -> SleepData:
        """取得睡眠數據 / Get sleep data."""
        ...

    @abstractmethod
    def get_activity(self) -> ActivityData:
        """取得活動數據 / Get activity data."""
        ...


class AppleHealthKitAdapter(WearableAdapter):
    """Apple HealthKit 適配器 (佔位) / Apple HealthKit adapter (placeholder).

    實際實作需整合 HealthKit API，此處僅為介面佔位。
    Actual implementation requires HealthKit API integration; this is a
    placeholder for the interface only.
    """

    def get_hrv(self) -> HRVMetrics:
        raise NotImplementedError("AppleHealthKitAdapter.get_hrv() not yet implemented")

    def get_sleep(self) -> SleepData:
        raise NotImplementedError("AppleHealthKitAdapter.get_sleep() not yet implemented")

    def get_activity(self) -> ActivityData:
        raise NotImplementedError("AppleHealthKitAdapter.get_activity() not yet implemented")


class OuraAPIAdapter(WearableAdapter):
    """Oura Ring API 適配器 (佔位) / Oura Ring API adapter (placeholder).

    實際實作需整合 Oura API，此處僅為介面佔位。
    Actual implementation requires Oura API integration; this is a
    placeholder for the interface only.
    """

    def get_hrv(self) -> HRVMetrics:
        raise NotImplementedError("OuraAPIAdapter.get_hrv() not yet implemented")

    def get_sleep(self) -> SleepData:
        raise NotImplementedError("OuraAPIAdapter.get_sleep() not yet implemented")

    def get_activity(self) -> ActivityData:
        raise NotImplementedError("OuraAPIAdapter.get_activity() not yet implemented")


class FitbitAPIAdapter(WearableAdapter):
    """Fitbit API 適配器 (佔位) / Fitbit API adapter (placeholder).

    實際實作需整合 Fitbit Web API，此處僅為介面佔位。
    Actual implementation requires Fitbit Web API integration; this is a
    placeholder for the interface only.
    """

    def get_hrv(self) -> HRVMetrics:
        raise NotImplementedError("FitbitAPIAdapter.get_hrv() not yet implemented")

    def get_sleep(self) -> SleepData:
        raise NotImplementedError("FitbitAPIAdapter.get_sleep() not yet implemented")

    def get_activity(self) -> ActivityData:
        raise NotImplementedError("FitbitAPIAdapter.get_activity() not yet implemented")


# ---------------------------------------------------------------------------
# EmoHeart Engine — 心臟生理引擎
# ---------------------------------------------------------------------------

class EmoHeartEngine:
    """EmoHeart (心) 生理引擎 / EmoHeart (Heart) Physiological Engine.

    七竅多模態感官系統 — 心竅。
    負責心率變異度分析、壓力生物標記融合、穿戴式裝置整合。

    Heart aperture of the Seven Apertures multimodal sensory system.
    Responsible for HRV analysis, stress biomarker fusion, and wearable
    device integration.

    Usage:
        engine = EmoHeartEngine()
        result = engine.measure_stress(
            hrv=HRVMetrics(heart_rate=85, sdnn=45, rmssd=30,
                           lf_hf_ratio=1.8, stress_index=0.4),
            respiration_rate=18.0,
            ambient_stress=0.2,
        )
        pulse = engine.to_pulse(result)
    """

    def __init__(self, wearable: Optional[WearableAdapter] = None) -> None:
        """初始化 EmoHeart 引擎 / Initialize EmoHeart engine.

        Args:
            wearable: 穿戴式裝置適配器 (可選) / Wearable device adapter (optional).
        """
        self._wearable = wearable

    # ------------------------------------------------------------------
    # Core: Stress Measurement — 壓力量測
    # ------------------------------------------------------------------

    def measure_stress(
        self,
        hrv: Optional[HRVMetrics] = None,
        respiration_rate: Optional[float] = None,
        ambient_stress: float = 0.0,
    ) -> EmoHeartResult:
        """量測壓力 / Measure stress.

        融合 HRV、呼吸速率與環境壓力，計算綜合壓力分數。

        融合公式:
            stress_score = w_hrv × (1 - hrv.rmssd / max_rmssd)
                         + w_resp × respiration_deviation
                         + w_context × ambient_stress

        Args:
            hrv:              心率變異度指標 (可為 None)
            respiration_rate: 呼吸速率 (次/分鐘，可為 None)
            ambient_stress:   環境壓力 0.0-1.0

        Returns:
            EmoHeartResult 包含壓力分數、自律神經狀態、恢復狀態等
        """
        ambient_stress = _clamp(ambient_stress, 0.0, 1.0)

        # --- HRV component ---
        hrv_component: float = 0.0
        if hrv is not None:
            hrv_component = 1.0 - _clamp(hrv.rmssd / MAX_RMSSD, 0.0, 1.0)

        # --- Respiration component ---
        resp_component: float = 0.0
        if respiration_rate is not None:
            respiration_rate = _clamp(respiration_rate, 4.0, 60.0)
            deviation = abs(respiration_rate - NORMAL_RESPIRATION) / NORMAL_RESPIRATION
            resp_component = _clamp(deviation, 0.0, 1.0)

        # --- Fused stress score ---
        stress_score = (
            W_HRV * hrv_component
            + W_RESP * resp_component
            + W_CONTEXT * ambient_stress
        )
        stress_score = _clamp(stress_score, 0.0, 1.0)

        # --- Autonomic state ---
        autonomic_state = self.classify_autonomic(hrv) if hrv is not None else AutonomicState.BALANCED

        # --- Recovery status ---
        recovery_status = self.classify_recovery(hrv)

        # --- Determine source ---
        source = "manual"

        return EmoHeartResult(
            hrv=hrv,
            stress_score=stress_score,
            autonomic_state=autonomic_state,
            recovery_status=recovery_status,
            source=source,
            respiration_rate=respiration_rate,
            timestamp=datetime.now(timezone.utc),
        )

    # ------------------------------------------------------------------
    # Core: Wearable Data — 穿戴式裝置數據
    # ------------------------------------------------------------------

    def get_wearable_data(self) -> EmoHeartResult:
        """從穿戴式裝置取得數據並計算壓力 / Get data from wearable and compute stress.

        Requires a wearable adapter to be configured via __init__.

        Returns:
            EmoHeartResult based on wearable data.

        Raises:
            RuntimeError: If no wearable adapter is configured.
        """
        if self._wearable is None:
            raise RuntimeError(
                "No wearable adapter configured. "
                "Pass a WearableAdapter to EmoHeartEngine() constructor."
            )

        hrv = self._wearable.get_hrv()
        sleep = self._wearable.get_sleep()
        activity = self._wearable.get_activity()

        # Determine source label from adapter type
        adapter_type = type(self._wearable).__name__
        source_map: Dict[str, str] = {
            "AppleHealthKitAdapter": "wearable_apple",
            "OuraAPIAdapter": "wearable_oura",
            "FitbitAPIAdapter": "wearable_fitbit",
        }
        source = source_map.get(adapter_type, "manual")

        # Compute stress with wearable HRV
        stress_score = self._compute_stress_score(hrv, ambient_stress=0.0)

        # Classify autonomic state
        autonomic_state = self.classify_autonomic(hrv)

        # Classify recovery with sleep context
        recovery_status = self.classify_recovery(hrv, sleep=sleep)

        return EmoHeartResult(
            hrv=hrv,
            stress_score=stress_score,
            autonomic_state=autonomic_state,
            recovery_status=recovery_status,
            source=source,
            respiration_rate=None,
            timestamp=datetime.now(timezone.utc),
        )

    # ------------------------------------------------------------------
    # Classification: Autonomic State — 自律神經狀態分類
    # ------------------------------------------------------------------

    def classify_autonomic(self, hrv: HRVMetrics) -> AutonomicState:
        """分類自律神經狀態 / Classify autonomic nervous system state.

        分類規則:
        - lf_hf_ratio > 2.5 AND heart_rate > 90 → SYMPATHETIC_DOMINANT
        - lf_hf_ratio < 0.5 AND heart_rate < 60 → PARASYMPATHETIC_DOMINANT
        - rmssd < 15 AND sdnn < 20 → DORSAL_VAGAL ⚠️
        - Otherwise → BALANCED

        Args:
            hrv: 心率變異度指標

        Returns:
            AutonomicState 分類結果
        """
        # DORSAL_VAGAL has highest priority — safety concern
        if hrv.rmssd < RMSSD_DORSAL_THRESHOLD and hrv.sdnn < SDNN_DORSAL_THRESHOLD:
            return AutonomicState.DORSAL_VAGAL

        if hrv.lf_hf_ratio > LF_HF_SYMPATHETIC_THRESHOLD and hrv.heart_rate > HR_SYMPATHETIC_THRESHOLD:
            return AutonomicState.SYMPATHETIC_DOMINANT

        if hrv.lf_hf_ratio < LF_HF_PARASYMPATHETIC_THRESHOLD and hrv.heart_rate < HR_PARASYMPATHETIC_THRESHOLD:
            return AutonomicState.PARASYMPATHETIC_DOMINANT

        return AutonomicState.BALANCED

    # ------------------------------------------------------------------
    # Classification: Recovery Status — 恢復狀態分類
    # ------------------------------------------------------------------

    def classify_recovery(
        self,
        hrv: Optional[HRVMetrics],
        sleep: Optional[SleepData] = None,
    ) -> RecoveryStatus:
        """分類恢復狀態 / Classify recovery status.

        分類邏輯:
        - 無 HRV 數據 → RECOVERING (保守估計)
        - HRV 壓力指數 < 0.3 且 (睡眠效率 > 0.85 或無睡眠數據) → RECOVERED
        - HRV 壓力指數 > 0.7 或 (睡眠效率 < 0.5 且深層睡眠 < 1h) → DEPLETED
        - Otherwise → RECOVERING

        Args:
            hrv:   心率變異度指標 (可為 None)
            sleep: 睡眠數據 (可為 None)

        Returns:
            RecoveryStatus 分類結果
        """
        if hrv is None:
            return RecoveryStatus.RECOVERING

        # Good recovery: low stress + adequate sleep
        if hrv.stress_index < 0.3:
            if sleep is None or sleep.sleep_efficiency > 0.85:
                return RecoveryStatus.RECOVERED

        # Depleted: high stress or poor sleep
        if hrv.stress_index > 0.7:
            return RecoveryStatus.DEPLETED

        if sleep is not None:
            if sleep.sleep_efficiency < 0.5 and sleep.deep_sleep_hours < 1.0:
                return RecoveryStatus.DEPLETED

        return RecoveryStatus.RECOVERING

    # ------------------------------------------------------------------
    # Pulse Conversion — Pulse 轉換
    # ------------------------------------------------------------------

    def to_pulse(self, result: EmoHeartResult) -> Pulse:
        """將 EmoHeartResult 轉換為 Pulse / Convert EmoHeartResult to Pulse.

        自律神經狀態 → PulseType 映射:
        - SYMPATHETIC_DOMINANT → FEAR (低壓力) 或 PANIC (高壓力)
        - PARASYMPATHETIC_DOMINANT → CARE
        - BALANCED → NEUTRAL
        - DORSAL_VAGAL → PANIC (高強度)

        Args:
            result: EmoHeart 引擎結果

        Returns:
            Pulse 物件
        """
        return result.to_pulse()

    # ------------------------------------------------------------------
    # Therapy Recommendation — 療癒推薦
    # ------------------------------------------------------------------

    def get_therapy_recommendation(
        self, autonomic_state: AutonomicState
    ) -> Dict[str, Any]:
        """根據自律神經狀態推薦療癒策略 / Recommend therapy based on autonomic state.

        Args:
            autonomic_state: 自律神經狀態

        Returns:
            包含療癒建議的字典
        """
        return AUTONOMIC_THERAPY_MAP.get(
            autonomic_state,
            AUTONOMIC_THERAPY_MAP[AutonomicState.BALANCED],
        )

    # ------------------------------------------------------------------
    # Internal Helpers — 內部輔助
    # ------------------------------------------------------------------

    def _compute_stress_score(
        self,
        hrv: HRVMetrics,
        respiration_rate: Optional[float] = None,
        ambient_stress: float = 0.0,
    ) -> float:
        """計算融合壓力分數 / Compute fused stress score.

        stress_score = w_hrv × (1 - hrv.rmssd / max_rmssd)
                     + w_resp × respiration_deviation
                     + w_context × ambient_stress
        """
        ambient_stress = _clamp(ambient_stress, 0.0, 1.0)

        hrv_component = 1.0 - _clamp(hrv.rmssd / MAX_RMSSD, 0.0, 1.0)

        resp_component: float = 0.0
        if respiration_rate is not None:
            deviation = abs(respiration_rate - NORMAL_RESPIRATION) / NORMAL_RESPIRATION
            resp_component = _clamp(deviation, 0.0, 1.0)

        score = (
            W_HRV * hrv_component
            + W_RESP * resp_component
            + W_CONTEXT * ambient_stress
        )
        return _clamp(score, 0.0, 1.0)


# ---------------------------------------------------------------------------
# Module smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    engine = EmoHeartEngine()

    # Test 1: Normal balanced state
    hrv_balanced = HRVMetrics(
        heart_rate=72, sdnn=50, rmssd=40,
        lf_hf_ratio=1.2, stress_index=0.3,
    )
    result = engine.measure_stress(hrv=hrv_balanced, respiration_rate=16.0)
    print(f"Balanced: stress={result.stress_score:.3f}, "
          f"autonomic={result.autonomic_state.value}, "
          f"recovery={result.recovery_status.value}")

    # Test 2: Sympathetic dominant (stressed)
    hrv_stressed = HRVMetrics(
        heart_rate=95, sdnn=25, rmssd=15,
        lf_hf_ratio=3.5, stress_index=0.8,
    )
    result_stress = engine.measure_stress(
        hrv=hrv_stressed, respiration_rate=22.0, ambient_stress=0.5,
    )
    print(f"Stressed: stress={result_stress.stress_score:.3f}, "
          f"autonomic={result_stress.autonomic_state.value}, "
          f"recovery={result_stress.recovery_status.value}")

    # Test 3: Dorsal vagal (shutdown)
    hrv_shutdown = HRVMetrics(
        heart_rate=55, sdnn=12, rmssd=8,
        lf_hf_ratio=0.3, stress_index=0.9,
    )
    result_dv = engine.measure_stress(hrv=hrv_shutdown)
    print(f"Dorsal Vagal: stress={result_dv.stress_score:.3f}, "
          f"autonomic={result_dv.autonomic_state.value}, "
          f"recovery={result_dv.recovery_status.value}")

    # Test 4: Pulse conversion
    pulse = engine.to_pulse(result_stress)
    print(f"Pulse: {pulse}")

    # Test 5: Therapy recommendation
    therapy = engine.get_therapy_recommendation(result_stress.autonomic_state)
    print(f"Therapy: {therapy['label_zh']} → {therapy['description_zh']}")

    # Test 6: Serialization round-trip
    d = result.to_dict()
    restored = EmoHeartResult.from_dict(d)
    print(f"Round-trip OK: stress={restored.stress_score:.3f}")

    print("OK — emo_heart.py smoke tests done")
