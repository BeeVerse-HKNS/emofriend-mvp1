"""EmoBrain (腦) Cognitive Engine — 認知引擎

七竅 (Seven Apertures) 多模態感官系統 — EmoFriend 情感健康產品

TCM 臟腑: 髓 (Brain/Marrow)
Panksepp 系統: SEEKING / FEAR

3-in-1 核心能力:
1. Attention Tracking — 眼動追蹤 → 專注/走神偵測
2. Cognitive Load Estimation — 瞳孔擴張 + 打字速度 + 反應時間 → 心智負荷
3. Flow State Detection — HRV 一致性 + 持續專注 + 打字節奏 → 心流機率

認知狀態 → JITAI 映射:
- 高認知負荷 + 疲勞 → 建議休息，簡化 UI
- 走神 + 焦慮 → 接地練習，重新聚焦提示
- 心流狀態偵測 → 保護心流 — 抑制通知，最小化 UI
- 認知超載持續 >30 分鐘 → 職業倦怠風險 — 主動介入

設計原則:
- 自包含，無外部依賴 (僅 stdlib)
- 數值穩定 (_clamp 所有浮點範圍)
- 可解釋 (每個信號來源可追溯)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from ..pulse import Pulse, PulseType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """將數值限制在 [lo, hi] 範圍內 / Clamp value to [lo, hi]"""
    return max(lo, min(hi, value))


# ---------------------------------------------------------------------------
# Flow State Detection Weights / 心流偵測權重
# ---------------------------------------------------------------------------

FLOW_WEIGHT_HRV: float = 0.25       # HRV 一致性權重
FLOW_WEIGHT_ATTENTION: float = 0.35  # 專注度權重
FLOW_WEIGHT_TYPING: float = 0.25     # 打字節奏一致性權重
FLOW_WEIGHT_SELF: float = 0.15       # 自我狀態 (1 - fatigue) 權重

FLOW_THRESHOLD: float = 0.75         # 心流狀態閾值

# Mind wandering thresholds / 走神偵測閾值
MIND_WANDER_ATTENTION_THRESHOLD: float = 0.3   # 專注度低於此值可能走神
MIND_WANDER_LOAD_THRESHOLD: float = 0.4        # 認知負荷低於此值配合低專注度判定走神
BLINK_RATE_WANDER_THRESHOLD: float = 25.0      # 眨眼率 > 25 次/分鐘 → 走神輔助信號

# Cognitive load thresholds / 認知負荷閾值
COGNITIVE_OVERLOAD_THRESHOLD: float = 0.8      # 高認知負荷閾值
FATIGUE_HIGH_THRESHOLD: float = 0.6            # 高疲勞閾值

# Emotion → PulseType mapping / 情緒 → Pulse 類型映射
_EMOTION_PULSE_MAP: Dict[str, PulseType] = {
    "SEEKING": PulseType.SEEKING,
    "FEAR": PulseType.FEAR,
    "PANIC": PulseType.PANIC,
}


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class CognitiveState:
    """認知狀態 / Cognitive State

    描述用戶當前的認知狀態，包含專注度、認知負荷、心流機率、
    走神狀態、疲勞程度及信號來源。

    Attributes:
        attention_level: 專注度 (0.0 分心 ~ 1.0 高度專注)
        cognitive_load: 認知負荷 (0.0 閒置 ~ 1.0 超載)
        flow_probability: 心流機率 (0.0 ~ 1.0)
        mind_wandering: 是否走神
        fatigue_level: 疲勞程度 (0.0 ~ 1.0)
        source_signals: 信號來源列表 (如 "gaze", "typing", "hrv", "blink_rate")
    """
    attention_level: float       # 0.0 (distracted) to 1.0 (focused)
    cognitive_load: float        # 0.0 (idle) to 1.0 (overloaded)
    flow_probability: float      # 0.0 to 1.0
    mind_wandering: bool
    fatigue_level: float         # 0.0 to 1.0
    source_signals: List[str]    # ["gaze", "typing", "hrv", "blink_rate"]

    def __post_init__(self) -> None:
        self.attention_level = _clamp(self.attention_level)
        self.cognitive_load = _clamp(self.cognitive_load)
        self.flow_probability = _clamp(self.flow_probability)
        self.fatigue_level = _clamp(self.fatigue_level)

    def to_dict(self) -> dict:
        """序列化為字典 / Serialize to dictionary"""
        return {
            "attention_level": self.attention_level,
            "cognitive_load": self.cognitive_load,
            "flow_probability": self.flow_probability,
            "mind_wandering": self.mind_wandering,
            "fatigue_level": self.fatigue_level,
            "source_signals": list(self.source_signals),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CognitiveState":
        """從字典反序列化 / Deserialize from dictionary"""
        return cls(
            attention_level=data["attention_level"],
            cognitive_load=data["cognitive_load"],
            flow_probability=data["flow_probability"],
            mind_wandering=data["mind_wandering"],
            fatigue_level=data["fatigue_level"],
            source_signals=list(data.get("source_signals", [])),
        )


@dataclass
class EmoBrainResult:
    """EmoBrain 評估結果 / EmoBrain Assessment Result

    包含認知狀態、主導情緒、效價、喚醒度、信心度及時間戳。

    Attributes:
        cognitive: 認知狀態詳情
        dominant_emotion: 主導 Panksepp 系統 ("SEEKING" / "FEAR" / "PANIC")
        valence: 效價 (-1.0 負面 ~ +1.0 正面)
        arousal: 喚醒度 (-1.0 低喚醒 ~ +1.0 高喚醒)
        confidence: 信心度 (0.0 ~ 1.0)
        timestamp: 評估時間戳
    """
    cognitive: CognitiveState
    dominant_emotion: str       # Panksepp system (SEEKING/FEAR/PANIC)
    valence: float              # -1.0 to 1.0
    arousal: float              # -1.0 to 1.0
    confidence: float           # 0.0 to 1.0
    timestamp: datetime

    def __post_init__(self) -> None:
        self.valence = _clamp(self.valence, -1.0, 1.0)
        self.arousal = _clamp(self.arousal, -1.0, 1.0)
        self.confidence = _clamp(self.confidence)
        if self.dominant_emotion not in ("SEEKING", "FEAR", "PANIC"):
            raise ValueError(
                f"dominant_emotion must be SEEKING/FEAR/PANIC, got '{self.dominant_emotion}'"
            )

    def to_dict(self) -> dict:
        """序列化為字典 / Serialize to dictionary"""
        return {
            "cognitive": self.cognitive.to_dict(),
            "dominant_emotion": self.dominant_emotion,
            "valence": self.valence,
            "arousal": self.arousal,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "EmoBrainResult":
        """從字典反序列化 / Deserialize from dictionary"""
        ts = data["timestamp"]
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
        return cls(
            cognitive=CognitiveState.from_dict(data["cognitive"]),
            dominant_emotion=data["dominant_emotion"],
            valence=data["valence"],
            arousal=data["arousal"],
            confidence=data["confidence"],
            timestamp=ts,
        )

    def to_pulse(self) -> Pulse:
        """將評估結果轉換為 Pulse 物件 / Convert result to Pulse object

        使用 dominant_emotion 查找 PulseType，並以認知狀態的
        valence/arousal 作為 Pulse 的效價/喚醒度。
        """
        pulse_type = _EMOTION_PULSE_MAP.get(self.dominant_emotion, PulseType.NEUTRAL)
        return Pulse(
            pulse_type=pulse_type,
            valence=self.valence,
            arousal=self.arousal,
            dominance=0.0,
            intensity=self.confidence,
        )


# ---------------------------------------------------------------------------
# JITAI Recommendation / JITAI 推薦
# ---------------------------------------------------------------------------

@dataclass
class JitaiRecommendation:
    """JITAI (Just-In-Time Adaptive Intervention) 推薦 / 即時適應性介入推薦

    根據認知狀態生成行動建議，如建議休息、保護心流、接地練習等。

    Attributes:
        action_type: 行動類型 ("protect_flow", "suggest_break", "grounding",
                     "refocus", "burnout_warning", "simplify_ui", "none")
        reason: 推薦原因說明
        priority: 優先級 (0.0 ~ 1.0)
        suppress_notifications: 是否抑制通知
    """
    action_type: str
    reason: str
    priority: float
    suppress_notifications: bool = False

    def __post_init__(self) -> None:
        valid_actions = {
            "protect_flow", "suggest_break", "grounding",
            "refocus", "burnout_warning", "simplify_ui", "none",
        }
        if self.action_type not in valid_actions:
            raise ValueError(
                f"action_type must be one of {valid_actions}, got '{self.action_type}'"
            )
        self.priority = _clamp(self.priority)


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class EmoBrainEngine:
    """EmoBrain (腦) 認知引擎 / Cognitive Engine

    TCM 臟腑對應: 髓 (Brain/Marrow)
    Panksepp 系統: SEEKING / FEAR

    三合一能力:
    1. Attention Tracking — 專注/走神偵測
    2. Cognitive Load Estimation — 心智負荷估算
    3. Flow State Detection — 心流狀態偵測

    使用方式:
        engine = EmoBrainEngine()
        result = engine.assess_cognitive(
            attention=0.8, cognitive_load=0.3,
            typing_rhythm_consistency=0.7, hrv_coherence=0.6,
        )
        pulse = engine.to_pulse(result)
    """

    def __init__(self) -> None:
        """初始化 EmoBrain 引擎 / Initialize EmoBrain engine"""
        self._flow_weights = {
            "hrv": FLOW_WEIGHT_HRV,
            "attention": FLOW_WEIGHT_ATTENTION,
            "typing": FLOW_WEIGHT_TYPING,
            "self": FLOW_WEIGHT_SELF,
        }

    # ------------------------------------------------------------------
    # Main Assessment / 主評估方法
    # ------------------------------------------------------------------

    def assess_cognitive(
        self,
        attention: float = 0.5,
        cognitive_load: float = 0.5,
        typing_rhythm_consistency: float = 0.5,
        hrv_coherence: float = 0.5,
        blink_rate: Optional[float] = None,
        fatigue: float = 0.0,
    ) -> EmoBrainResult:
        """綜合認知評估 / Comprehensive cognitive assessment

        整合多通道信號，計算認知狀態、心流機率、走神偵測及情緒分類。

        Args:
            attention: 專注度 (0.0 ~ 1.0)，來自眼動追蹤
            cognitive_load: 認知負荷 (0.0 ~ 1.0)，來自瞳孔擴張/打字速度/反應時間
            typing_rhythm_consistency: 打字節奏一致性 (0.0 ~ 1.0)
            hrv_coherence: HRV 一致性 (0.0 ~ 1.0)
            blink_rate: 眨眼率 (次/分鐘)，可選輔助信號
            fatigue: 疲勞程度 (0.0 ~ 1.0)

        Returns:
            EmoBrainResult 包含完整認知評估結果
        """
        # Clamp all inputs
        attention = _clamp(attention)
        cognitive_load = _clamp(cognitive_load)
        typing_rhythm_consistency = _clamp(typing_rhythm_consistency)
        hrv_coherence = _clamp(hrv_coherence)
        fatigue = _clamp(fatigue)

        # Build source signals list
        source_signals: List[str] = []
        source_signals.append("gaze")       # attention comes from eye tracking
        source_signals.append("typing")     # typing rhythm + cognitive load from typing
        source_signals.append("hrv")        # HRV coherence
        if blink_rate is not None:
            source_signals.append("blink_rate")

        # Build preliminary cognitive state for detection
        preliminary = CognitiveState(
            attention_level=attention,
            cognitive_load=cognitive_load,
            flow_probability=0.0,  # placeholder, computed below
            mind_wandering=False,  # placeholder, computed below
            fatigue_level=fatigue,
            source_signals=source_signals,
        )

        # Detect flow state
        flow_prob = self.detect_flow(preliminary, typing_rhythm_consistency, hrv_coherence)
        preliminary.flow_probability = flow_prob

        # Detect mind wandering
        mind_wandering = self.detect_mind_wandering(preliminary, blink_rate)
        preliminary.mind_wandering = mind_wandering

        # Classify emotion
        dominant_emotion, valence, arousal = self.classify_emotion(preliminary)

        # Compute confidence based on signal richness and consistency
        confidence = self._compute_confidence(
            attention, cognitive_load, typing_rhythm_consistency, hrv_coherence, blink_rate
        )

        return EmoBrainResult(
            cognitive=preliminary,
            dominant_emotion=dominant_emotion,
            valence=valence,
            arousal=arousal,
            confidence=confidence,
            timestamp=datetime.now(timezone.utc),
        )

    # ------------------------------------------------------------------
    # Flow State Detection / 心流狀態偵測
    # ------------------------------------------------------------------

    def detect_flow(
        self,
        cognitive: CognitiveState,
        typing_rhythm_consistency: float = 0.5,
        hrv_coherence: float = 0.5,
    ) -> float:
        """偵測心流狀態 / Detect flow state

        心流公式:
            flow_prob = w_hrv × hrv_coherence
                      + w_attention × attention_level
                      + w_typing × rhythm_consistency
                      + w_self × (1 - fatigue)

        權重: w_hrv=0.25, w_attention=0.35, w_typing=0.25, w_self=0.15
        閾值: flow_prob >= 0.75 → 心流狀態

        Args:
            cognitive: 當前認知狀態
            typing_rhythm_consistency: 打字節奏一致性 (0.0 ~ 1.0)
            hrv_coherence: HRV 一致性 (0.0 ~ 1.0)

        Returns:
            心流機率 (0.0 ~ 1.0)
        """
        typing_rhythm_consistency = _clamp(typing_rhythm_consistency)
        hrv_coherence = _clamp(hrv_coherence)

        flow_prob = (
            self._flow_weights["hrv"] * hrv_coherence
            + self._flow_weights["attention"] * cognitive.attention_level
            + self._flow_weights["typing"] * typing_rhythm_consistency
            + self._flow_weights["self"] * (1.0 - cognitive.fatigue_level)
        )

        return _clamp(flow_prob)

    # ------------------------------------------------------------------
    # Mind Wandering Detection / 走神偵測
    # ------------------------------------------------------------------

    def detect_mind_wandering(
        self,
        cognitive: CognitiveState,
        blink_rate: Optional[float] = None,
    ) -> bool:
        """偵測走神狀態 / Detect mind wandering

        偵測條件:
        - attention_level < 0.3 AND cognitive_load < 0.4 → 走神
        - blink_rate > 25 次/分鐘 → 走神 (輔助信號)

        Args:
            cognitive: 當前認知狀態
            blink_rate: 眨眼率 (次/分鐘)，可選

        Returns:
            是否走神
        """
        # Primary detection: low attention + low cognitive load
        if cognitive.attention_level < MIND_WANDER_ATTENTION_THRESHOLD and \
           cognitive.cognitive_load < MIND_WANDER_LOAD_THRESHOLD:
            return True

        # Supplementary signal: high blink rate
        if blink_rate is not None and blink_rate > BLINK_RATE_WANDER_THRESHOLD:
            return True

        return False

    # ------------------------------------------------------------------
    # Emotion Classification / 情緒分類
    # ------------------------------------------------------------------

    def classify_emotion(
        self, cognitive: CognitiveState
    ) -> Tuple[str, float, float]:
        """根據認知狀態分類 Panksepp 情緒 / Classify Panksepp emotion from cognitive state

        分類規則:
        - 高專注 + 低負荷 + 高心流 → SEEKING (V=+0.5, A=0.6)
        - 低專注 + 高負荷 → FEAR (V=-0.4, A=0.7)
        - 高負荷 + 高疲勞 → PANIC dorsal (V=-0.5, A=0.3)
        - 中等專注 + 中等負荷 → SEEKING (V=+0.2, A=0.4)

        Args:
            cognitive: 當前認知狀態

        Returns:
            (dominant_emotion, valence, arousal) 三元組
        """
        att = cognitive.attention_level
        load = cognitive.cognitive_load
        flow = cognitive.flow_probability
        fatigue = cognitive.fatigue_level

        # Rule 1: High attention + low load + high flow → SEEKING
        if att > 0.6 and load < 0.4 and flow >= FLOW_THRESHOLD:
            return ("SEEKING", 0.5, 0.6)

        # Rule 2: Low attention + high load → FEAR
        if att < 0.4 and load > 0.6:
            return ("FEAR", -0.4, 0.7)

        # Rule 3: High load + high fatigue → PANIC dorsal
        if load > COGNITIVE_OVERLOAD_THRESHOLD and fatigue > FATIGUE_HIGH_THRESHOLD:
            return ("PANIC", -0.5, 0.3)

        # Rule 4: Moderate attention + moderate load → SEEKING (default)
        return ("SEEKING", 0.2, 0.4)

    # ------------------------------------------------------------------
    # JITAI Recommendation / JITAI 推薦
    # ------------------------------------------------------------------

    def recommend_jitai(self, result: EmoBrainResult) -> JitaiRecommendation:
        """根據認知評估結果生成 JITAI 推薦 / Generate JITAI recommendation

        映射規則:
        - 心流狀態 (flow >= 0.75) → 保護心流，抑制通知
        - 高認知負荷 + 高疲勞 → 建議休息，簡化 UI
        - 走神 + 焦慮 (FEAR) → 接地練習，重新聚焦
        - 認知超載 + 高疲勞 → 職業倦怠風險警告

        Args:
            result: EmoBrain 評估結果

        Returns:
            JitaiRecommendation 推薦行動
        """
        cog = result.cognitive

        # Priority 1: Protect flow state
        if cog.flow_probability >= FLOW_THRESHOLD:
            return JitaiRecommendation(
                action_type="protect_flow",
                reason=(
                    f"心流狀態偵測 (flow={cog.flow_probability:.2f})，"
                    "保護專注，抑制通知 / Flow state detected, protecting focus"
                ),
                priority=0.9,
                suppress_notifications=True,
            )

        # Priority 2: Burnout risk — high load + high fatigue
        if cog.cognitive_load > COGNITIVE_OVERLOAD_THRESHOLD and \
           cog.fatigue_level > FATIGUE_HIGH_THRESHOLD:
            return JitaiRecommendation(
                action_type="burnout_warning",
                reason=(
                    f"認知超載 (load={cog.cognitive_load:.2f}) + 高疲勞 "
                    f"(fatigue={cog.fatigue_level:.2f})，職業倦怠風險 / "
                    "Burnout risk: cognitive overload + high fatigue"
                ),
                priority=0.85,
                suppress_notifications=False,
            )

        # Priority 3: High cognitive load + fatigue → suggest break
        if cog.cognitive_load > COGNITIVE_OVERLOAD_THRESHOLD and \
           cog.fatigue_level > 0.3:
            return JitaiRecommendation(
                action_type="suggest_break",
                reason=(
                    f"高認知負荷 (load={cog.cognitive_load:.2f}) + 疲勞 "
                    f"(fatigue={cog.fatigue_level:.2f})，建議休息 / "
                    "High cognitive load + fatigue, suggest break"
                ),
                priority=0.7,
                suppress_notifications=False,
            )

        # Priority 4: Mind wandering + anxiety (FEAR) → grounding
        if cog.mind_wandering and result.dominant_emotion == "FEAR":
            return JitaiRecommendation(
                action_type="grounding",
                reason=(
                    "走神 + 焦慮狀態，建議接地練習 / "
                    "Mind wandering + anxiety, suggest grounding exercise"
                ),
                priority=0.6,
                suppress_notifications=False,
            )

        # Priority 5: Mind wandering alone → refocus
        if cog.mind_wandering:
            return JitaiRecommendation(
                action_type="refocus",
                reason=(
                    "走神偵測，建議重新聚焦 / "
                    "Mind wandering detected, suggest refocus"
                ),
                priority=0.4,
                suppress_notifications=False,
            )

        # Priority 6: High load alone → simplify UI
        if cog.cognitive_load > COGNITIVE_OVERLOAD_THRESHOLD:
            return JitaiRecommendation(
                action_type="simplify_ui",
                reason=(
                    f"高認知負荷 (load={cog.cognitive_load:.2f})，簡化 UI / "
                    "High cognitive load, simplify UI"
                ),
                priority=0.5,
                suppress_notifications=False,
            )

        # Default: no intervention needed
        return JitaiRecommendation(
            action_type="none",
            reason="認知狀態正常，無需介入 / Cognitive state normal, no intervention needed",
            priority=0.0,
            suppress_notifications=False,
        )

    # ------------------------------------------------------------------
    # Pulse Conversion / Pulse 轉換
    # ------------------------------------------------------------------

    def to_pulse(self, result: EmoBrainResult) -> Pulse:
        """將 EmoBrainResult 轉換為 Pulse 物件 / Convert EmoBrainResult to Pulse

        使用 dominant_emotion 查找 PulseType，並以認知狀態的
        valence/arousal 作為 Pulse 的效價/喚醒度，confidence 作為 intensity。

        Args:
            result: EmoBrain 評估結果

        Returns:
            Pulse 物件
        """
        return result.to_pulse()

    # ------------------------------------------------------------------
    # Internal Helpers / 內部輔助方法
    # ------------------------------------------------------------------

    def _compute_confidence(
        self,
        attention: float,
        cognitive_load: float,
        typing_rhythm: float,
        hrv_coherence: float,
        blink_rate: Optional[float],
    ) -> float:
        """計算評估信心度 / Compute assessment confidence

        信心度基於:
        - 信號數量 (更多信號 → 更高信心)
        - 信號一致性 (信號間相關性)

        Args:
            attention: 專注度
            cognitive_load: 認知負荷
            typing_rhythm: 打字節奏一致性
            hrv_coherence: HRV 一致性
            blink_rate: 眨眼率 (可選)

        Returns:
            信心度 (0.0 ~ 1.0)
        """
        # Signal count contribution: more signals → higher confidence
        signal_count = 4  # attention, load, typing, hrv always present
        if blink_rate is not None:
            signal_count += 1
        count_factor = min(1.0, signal_count / 5.0)

        # Consistency contribution: signals that agree → higher confidence
        # High attention + low load = consistent; low attention + high load = consistent
        # Mismatched signals reduce confidence
        signals = [attention, cognitive_load, typing_rhythm, hrv_coherence]
        mean_signal = sum(signals) / len(signals)
        variance = sum((s - mean_signal) ** 2 for s in signals) / len(signals)
        consistency_factor = 1.0 - _clamp(variance * 4.0)  # scale variance to [0, 1]

        # Combined confidence
        confidence = 0.6 * count_factor + 0.4 * consistency_factor
        return _clamp(confidence)


# ---------------------------------------------------------------------------
# Module-level smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    engine = EmoBrainEngine()

    # Scenario 1: Flow state
    result_flow = engine.assess_cognitive(
        attention=0.9, cognitive_load=0.2,
        typing_rhythm_consistency=0.85, hrv_coherence=0.8,
        fatigue=0.1,
    )
    print(f"Flow scenario: emotion={result_flow.dominant_emotion}, "
          f"flow={result_flow.cognitive.flow_probability:.2f}, "
          f"V={result_flow.valence:+.2f}, A={result_flow.arousal:+.2f}")
    jitai_flow = engine.recommend_jitai(result_flow)
    print(f"  JITAI: {jitai_flow.action_type} (suppress={jitai_flow.suppress_notifications})")

    # Scenario 2: Overload + fatigue
    result_overload = engine.assess_cognitive(
        attention=0.3, cognitive_load=0.9,
        typing_rhythm_consistency=0.2, hrv_coherence=0.3,
        fatigue=0.7,
    )
    print(f"Overload scenario: emotion={result_overload.dominant_emotion}, "
          f"load={result_overload.cognitive.cognitive_load:.2f}, "
          f"V={result_overload.valence:+.2f}, A={result_overload.arousal:+.2f}")
    jitai_overload = engine.recommend_jitai(result_overload)
    print(f"  JITAI: {jitai_overload.action_type}")

    # Scenario 3: Mind wandering
    result_wander = engine.assess_cognitive(
        attention=0.2, cognitive_load=0.3,
        typing_rhythm_consistency=0.3, hrv_coherence=0.4,
        blink_rate=30.0,
    )
    print(f"Wandering scenario: mind_wandering={result_wander.cognitive.mind_wandering}, "
          f"emotion={result_wander.dominant_emotion}")

    # Pulse conversion
    pulse = engine.to_pulse(result_flow)
    print(f"Pulse: {pulse}")

    # Serialization round-trip
    data = result_flow.to_dict()
    restored = EmoBrainResult.from_dict(data)
    assert restored.dominant_emotion == result_flow.dominant_emotion
    assert abs(restored.valence - result_flow.valence) < 1e-9
    print("OK — emo_brain.py smoke tests done")
