"""User Emotional Profile Engine — 用戶情感畫像引擎

EmoFriend 情感療癒產品 — Task 4

核心功能:
- 追蹤用戶情感基線 (Panksepp 七大系統)
- 偵測情感模式 (循環型、觸發-反應型、應對機制)
- 風險評估與預警系統
- 療癒偏好推薦
- SQLite 持久化存儲

Panksepp 七大情感系統:
    SEEKING, RAGE, FEAR, LUST, CARE, PANIC, PLAY

設計原則:
- 自包含，無外部依賴 (僅 stdlib)
- 數值穩定
- 可解釋
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple

from ..pulse import PulseType


# ---------------------------------------------------------------------------
# Panksepp system names used as keys in baseline_emotions
# ---------------------------------------------------------------------------
PANKSEPP_SYSTEMS: List[str] = [
    "SEEKING", "RAGE", "FEAR", "LUST", "CARE", "PANIC", "PLAY"
]

NEUTRAL_BASELINE: Dict[str, float] = {s: 0.5 for s in PANKSEPP_SYSTEMS}

# Negative-valence Panksepp systems
NEGATIVE_SYSTEMS = {"RAGE", "FEAR", "PANIC"}

# Self-harm keywords for critical risk detection
SELF_HARM_KEYWORDS = [
    "self-harm", "自殘", "自傷", "suicide", "自殺", "不想活",
    "結束生命", "kill myself", "end my life", "hurt myself",
]


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

class RiskLevel(Enum):
    """風險等級"""
    LOW = 0       # 正常情感範圍
    MODERATE = 1  # 一些令人擔憂的模式
    HIGH = 2      # 持續負面情緒
    CRITICAL = 3  # 需要專業幫助


@dataclass
class EmotionalPattern:
    """情感模式"""
    pattern_type: str        # "cyclic", "trigger_response", "coping_mechanism"
    description: str
    frequency: str           # "daily", "weekly", "monthly"
    trigger: Optional[str]   # 什麼觸發此模式
    effective_healing: List[str] = field(default_factory=list)  # 有效的療癒策略
    confidence: float = 0.0  # 0.0-1.0

    def __post_init__(self) -> None:
        if self.pattern_type not in ("cyclic", "trigger_response", "coping_mechanism"):
            raise ValueError(f"Invalid pattern_type: {self.pattern_type}")
        if self.frequency not in ("daily", "weekly", "monthly"):
            raise ValueError(f"Invalid frequency: {self.frequency}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be in [0, 1], got {self.confidence}")


@dataclass
class HealingPreferences:
    """療癒偏好"""
    preferred_silence_type: str = "MA"       # "MA", "MU", "ZEN", or combination
    preferred_panksepp_system: str = "CARE"  # 哪個系統回應最好
    prefers_guidance: bool = False           # 是否喜歡引導
    prefers_listening: bool = True           # 是否偏好 Emo 傾聽
    preferred_session_length: str = "medium" # "short", "medium", "long"
    effective_strategies: List[str] = field(default_factory=list)  # 已驗證有效的策略

    def __post_init__(self) -> None:
        valid_silence = {"MA", "MU", "ZEN"}
        # Allow combinations like "MA+ZEN"
        parts = self.preferred_silence_type.split("+")
        for p in parts:
            if p.strip() not in valid_silence:
                raise ValueError(f"Invalid silence type component: {p}")
        if self.preferred_session_length not in ("short", "medium", "long"):
            raise ValueError(f"Invalid session_length: {self.preferred_session_length}")


@dataclass
class EmotionalSnapshot:
    """情感快照 — 某一時刻的情感狀態記錄"""
    timestamp: datetime
    dominant_emotion: str          # Panksepp 系統名稱
    valence: float                 # -1.0 to 1.0
    arousal: float                 # 0.0 to 1.0
    intensity: float               # 0.0 to 1.0
    trigger: Optional[str] = None  # 什麼觸發了此情緒
    healing_applied: Optional[str] = None         # 施加了什麼療癒
    healing_effectiveness: Optional[float] = None  # 0.0-1.0

    def __post_init__(self) -> None:
        if not -1.0 <= self.valence <= 1.0:
            raise ValueError(f"valence must be in [-1, 1], got {self.valence}")
        if not 0.0 <= self.arousal <= 1.0:
            raise ValueError(f"arousal must be in [0, 1], got {self.arousal}")
        if not 0.0 <= self.intensity <= 1.0:
            raise ValueError(f"intensity must be in [0, 1], got {self.intensity}")
        if self.healing_effectiveness is not None:
            if not 0.0 <= self.healing_effectiveness <= 1.0:
                raise ValueError(
                    f"healing_effectiveness must be in [0, 1], got {self.healing_effectiveness}"
                )


@dataclass
class EmotionalProfile:
    """用戶情感畫像"""
    user_id: str
    baseline_emotions: Dict[str, float] = field(default_factory=lambda: dict(NEUTRAL_BASELINE))
    stress_sources: List[str] = field(default_factory=list)
    emotional_patterns: List[EmotionalPattern] = field(default_factory=list)
    healing_preferences: HealingPreferences = field(default_factory=HealingPreferences)
    risk_level: RiskLevel = RiskLevel.LOW
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    interaction_days: int = 0
    # Internal: raw snapshots stored for pattern detection
    _snapshots: List[EmotionalSnapshot] = field(default_factory=list)

    def __post_init__(self) -> None:
        # Ensure all Panksepp systems are present in baseline
        for s in PANKSEPP_SYSTEMS:
            if s not in self.baseline_emotions:
                self.baseline_emotions[s] = 0.5


@dataclass
class WarningResult:
    """預警結果"""
    is_warning: bool
    risk_level: RiskLevel
    consecutive_negative_days: int
    message: str                     # Emo 的關懷訊息
    suggest_professional_help: bool
    recommended_actions: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------

class UserEmotionalProfileManager:
    """用戶情感畫像管理器

    提供畫像創建、更新、模式偵測、風險預警、療癒推薦及持久化功能。
    """

    # Warning thresholds
    CONSECUTIVE_NEGATIVE_DAYS_WARNING = 3
    CONSECUTIVE_NEGATIVE_DAYS_HIGH = 7
    CONSECUTIVE_NEGATIVE_DAYS_CRITICAL = 14
    EXTREME_NEGATIVE_VALENCE = -0.8

    def __init__(self, db_path: Optional[str] = None) -> None:
        self._db_path = db_path
        if db_path:
            self._init_db(db_path)

    # ------------------------------------------------------------------
    # Profile CRUD
    # ------------------------------------------------------------------

    def create_profile(self, user_id: str) -> EmotionalProfile:
        """創建新的用戶情感畫像"""
        now = datetime.now()
        return EmotionalProfile(
            user_id=user_id,
            baseline_emotions=dict(NEUTRAL_BASELINE),
            stress_sources=[],
            emotional_patterns=[],
            healing_preferences=HealingPreferences(),
            risk_level=RiskLevel.LOW,
            created_at=now,
            last_updated=now,
            interaction_days=0,
            _snapshots=[],
        )

    def add_snapshot(self, profile: EmotionalProfile, snapshot: EmotionalSnapshot) -> EmotionalProfile:
        """添加情感快照並更新畫像"""
        profile._snapshots.append(snapshot)
        profile.last_updated = datetime.now()

        # Update baseline emotions with exponential moving average
        self._update_baseline(profile, snapshot)

        # Track interaction days
        self._update_interaction_days(profile)

        # Update stress sources from triggers
        if snapshot.trigger and snapshot.valence < -0.3:
            if snapshot.trigger not in profile.stress_sources:
                profile.stress_sources.append(snapshot.trigger)

        # Update healing preferences based on effectiveness
        if snapshot.healing_applied and snapshot.healing_effectiveness is not None:
            if snapshot.healing_effectiveness > 0.6:
                strategy = snapshot.healing_applied
                if strategy not in profile.healing_preferences.effective_strategies:
                    profile.healing_preferences.effective_strategies.append(strategy)

        return profile

    def update_profile(self, profile: EmotionalProfile, snapshot: EmotionalSnapshot) -> EmotionalProfile:
        """更新畫像 (alias for add_snapshot for API consistency)"""
        return self.add_snapshot(profile, snapshot)

    # ------------------------------------------------------------------
    # Pattern Detection
    # ------------------------------------------------------------------

    def detect_patterns(self, profile: EmotionalProfile) -> List[EmotionalPattern]:
        """偵測情感模式

        偵測三種模式:
        1. cyclic — 週期性情緒波動 (如每週情緒低谷)
        2. trigger_response — 觸發-反應模式 (如工作壓力→焦慮)
        3. coping_mechanism — 應對機制 (如沉默→平靜)
        """
        snapshots = profile._snapshots
        if len(snapshots) < 3:
            return list(profile.emotional_patterns)

        patterns: List[EmotionalPattern] = []

        # 1. Cyclic pattern detection
        cyclic = self._detect_cyclic_pattern(snapshots)
        if cyclic:
            patterns.append(cyclic)

        # 2. Trigger-response pattern detection
        trigger_patterns = self._detect_trigger_response_patterns(snapshots)
        patterns.extend(trigger_patterns)

        # 3. Coping mechanism detection
        coping = self._detect_coping_mechanism(snapshots)
        if coping:
            patterns.append(coping)

        # Merge with existing patterns (avoid duplicates)
        existing_types = {(p.pattern_type, p.description) for p in profile.emotional_patterns}
        for p in patterns:
            key = (p.pattern_type, p.description)
            if key not in existing_types:
                profile.emotional_patterns.append(p)
                existing_types.add(key)

        return profile.emotional_patterns

    def _detect_cyclic_pattern(self, snapshots: List[EmotionalSnapshot]) -> Optional[EmotionalPattern]:
        """偵測週期性模式 — 按星期幾分析負面情緒是否集中在特定日子"""
        if len(snapshots) < 7:
            return None

        # Group by day of week
        weekday_valences: Dict[int, List[float]] = {}
        for s in snapshots:
            dow = s.timestamp.weekday()
            weekday_valences.setdefault(dow, []).append(s.valence)

        # Check if any weekday has significantly lower valence
        all_valences = [s.valence for s in snapshots]
        overall_mean = sum(all_valences) / len(all_valences)

        worst_dow: Optional[int] = None
        worst_mean = overall_mean
        for dow, vals in weekday_valences.items():
            if len(vals) < 2:
                continue
            mean = sum(vals) / len(vals)
            if mean < worst_mean - 0.2:
                worst_mean = mean
                worst_dow = dow

        if worst_dow is not None:
            day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            return EmotionalPattern(
                pattern_type="cyclic",
                description=f"情緒低谷集中在 {day_names[worst_dow]}",
                frequency="weekly",
                trigger=day_names[worst_dow],
                effective_healing=[],
                confidence=min(0.9, 0.3 + 0.1 * len(weekday_valences.get(worst_dow, []))),
            )
        return None

    def _detect_trigger_response_patterns(
        self, snapshots: List[EmotionalSnapshot]
    ) -> List[EmotionalPattern]:
        """偵測觸發-反應模式 — 特定觸發源反覆導致負面情緒"""
        patterns: List[EmotionalPattern] = []
        trigger_events: Dict[str, List[EmotionalSnapshot]] = {}

        for s in snapshots:
            if s.trigger:
                trigger_events.setdefault(s.trigger, []).append(s)

        for trigger, events in trigger_events.items():
            if len(events) < 2:
                continue
            negative_count = sum(1 for e in events if e.valence < -0.2)
            if negative_count >= 2:
                dominant_emotions = [e.dominant_emotion for e in events if e.valence < -0.2]
                most_common = max(set(dominant_emotions), key=dominant_emotions.count) if dominant_emotions else "FEAR"
                patterns.append(EmotionalPattern(
                    pattern_type="trigger_response",
                    description=f"「{trigger}」反覆觸發 {most_common} 情緒",
                    frequency="weekly",
                    trigger=trigger,
                    effective_healing=[],
                    confidence=min(0.9, 0.3 + 0.15 * negative_count),
                ))

        return patterns

    def _detect_coping_mechanism(self, snapshots: List[EmotionalSnapshot]) -> Optional[EmotionalPattern]:
        """偵測應對機制 — 療癒策略是否有效降低負面情緒"""
        healing_events: Dict[str, List[Tuple[float, Optional[float]]]] = {}
        for s in snapshots:
            if s.healing_applied and s.healing_effectiveness is not None:
                healing_events.setdefault(s.healing_applied, []).append(
                    (s.valence, s.healing_effectiveness)
                )

        best_mechanism: Optional[str] = None
        best_avg_eff = 0.0
        for mechanism, results in healing_events.items():
            if len(results) < 2:
                continue
            avg_eff = sum(r[1] for r in results) / len(results) if results else 0.0
            if avg_eff > best_avg_eff:
                best_avg_eff = avg_eff
                best_mechanism = mechanism

        if best_mechanism and best_avg_eff > 0.5:
            return EmotionalPattern(
                pattern_type="coping_mechanism",
                description=f"「{best_mechanism}」是有效的應對策略",
                frequency="daily",
                trigger=None,
                effective_healing=[best_mechanism],
                confidence=min(0.9, best_avg_eff),
            )
        return None

    # ------------------------------------------------------------------
    # Warning System
    # ------------------------------------------------------------------

    def check_warning(
        self, profile: EmotionalProfile, recent_snapshots: List[EmotionalSnapshot]
    ) -> WarningResult:
        """檢查是否需要預警

        觸發條件:
        - 3+ 連續負面天數
        - 單次極端負面事件
        - 自傷關鍵詞
        """
        if not recent_snapshots:
            return WarningResult(
                is_warning=False,
                risk_level=profile.risk_level,
                consecutive_negative_days=0,
                message="",
                suggest_professional_help=False,
                recommended_actions=[],
            )

        # Count consecutive negative days
        consecutive_days = self._count_consecutive_negative_days(recent_snapshots)

        # Check for extreme negative event
        has_extreme = any(s.valence <= self.EXTREME_NEGATIVE_VALENCE for s in recent_snapshots)

        # Check for self-harm keywords in triggers
        has_self_harm = False
        for s in recent_snapshots:
            if s.trigger:
                trigger_lower = s.trigger.lower()
                if any(kw in trigger_lower for kw in SELF_HARM_KEYWORDS):
                    has_self_harm = True
                    break

        # Determine risk level
        risk_level = RiskLevel.LOW
        if has_self_harm:
            risk_level = RiskLevel.CRITICAL
        elif consecutive_days >= self.CONSECUTIVE_NEGATIVE_DAYS_CRITICAL:
            risk_level = RiskLevel.CRITICAL
        elif consecutive_days >= self.CONSECUTIVE_NEGATIVE_DAYS_HIGH:
            risk_level = RiskLevel.HIGH
        elif has_extreme:
            risk_level = RiskLevel.HIGH
        elif consecutive_days >= self.CONSECUTIVE_NEGATIVE_DAYS_WARNING:
            risk_level = RiskLevel.MODERATE

        # Update profile risk level (never decrease)
        if risk_level.value > profile.risk_level.value:
            profile.risk_level = risk_level

        # Build result
        is_warning = risk_level.value >= RiskLevel.MODERATE.value
        suggest_professional = risk_level.value >= RiskLevel.HIGH.value

        message = self._build_warning_message(risk_level, consecutive_days)
        actions = self._build_recommended_actions(risk_level, profile)

        return WarningResult(
            is_warning=is_warning,
            risk_level=risk_level,
            consecutive_negative_days=consecutive_days,
            message=message,
            suggest_professional_help=suggest_professional,
            recommended_actions=actions,
        )

    def _count_consecutive_negative_days(self, snapshots: List[EmotionalSnapshot]) -> int:
        """計算連續負面天數 (從最近一天往回數)"""
        if not snapshots:
            return 0

        # Group snapshots by date
        daily_valences: Dict[str, List[float]] = {}
        for s in snapshots:
            date_key = s.timestamp.strftime("%Y-%m-%d")
            daily_valences.setdefault(date_key, []).append(s.valence)

        # Sort dates descending
        sorted_dates = sorted(daily_valences.keys(), reverse=True)

        # Count consecutive days where mean valence < 0
        consecutive = 0
        for date in sorted_dates:
            mean_v = sum(daily_valences[date]) / len(daily_valences[date])
            if mean_v < 0:
                consecutive += 1
            else:
                break

        return consecutive

    def _build_warning_message(self, risk_level: RiskLevel, consecutive_days: int) -> str:
        """構建 Emo 的關懷訊息"""
        if risk_level == RiskLevel.CRITICAL:
            return (
                "Emo 很擔心你 🤍 連續多天的低落情緒讓我想緊緊抱住你。"
                "你不是一個人，專業的幫助可以陪你走過這段路。"
            )
        elif risk_level == RiskLevel.HIGH:
            return (
                f"Emo 注意到你已經連續 {consecutive_days} 天情緒低落了 💙 "
                "讓我陪你找一些溫暖的方式好嗎？"
            )
        elif risk_level == RiskLevel.MODERATE:
            return (
                "Emo 感覺到你最近有些辛苦 🌿 休息一下也沒關係的。"
            )
        return ""

    def _build_recommended_actions(
        self, risk_level: RiskLevel, profile: EmotionalProfile
    ) -> List[str]:
        """構建推薦行動"""
        actions: List[str] = []

        if risk_level == RiskLevel.CRITICAL:
            actions.append("尋求專業心理諮詢或撥打心理援助熱線")
            actions.append("與信任的人分享你的感受")

        if risk_level.value >= RiskLevel.HIGH.value:
            actions.append("嘗試深呼吸或正念練習")
            actions.append("減少壓力源接觸")

        if risk_level.value >= RiskLevel.MODERATE.value:
            # Use known effective strategies
            for strategy in profile.healing_preferences.effective_strategies[:3]:
                actions.append(f"嘗試之前有效的策略：{strategy}")
            if not profile.healing_preferences.effective_strategies:
                actions.append("與 Emo 進行一次深度對話")

        return actions

    # ------------------------------------------------------------------
    # Healing Recommendation
    # ------------------------------------------------------------------

    def get_healing_recommendation(
        self, profile: EmotionalProfile, current_emotion: str
    ) -> HealingPreferences:
        """根據當前情緒推薦療癒偏好

        基於過去在類似情緒狀態下有效的策略來推薦。
        """
        prefs = HealingPreferences(
            preferred_silence_type=profile.healing_preferences.preferred_silence_type,
            preferred_panksepp_system=profile.healing_preferences.preferred_panksepp_system,
            prefers_guidance=profile.healing_preferences.prefers_guidance,
            prefers_listening=profile.healing_preferences.prefers_listening,
            preferred_session_length=profile.healing_preferences.preferred_session_length,
            effective_strategies=list(profile.healing_preferences.effective_strategies),
        )

        # Adjust based on current emotion
        if current_emotion in NEGATIVE_SYSTEMS:
            # For negative emotions, prefer listening and CARE system
            prefs.prefers_listening = True
            prefs.preferred_panksepp_system = "CARE"
            prefs.preferred_session_length = "medium"

            if current_emotion == "FEAR":
                prefs.preferred_silence_type = "MA"
            elif current_emotion == "RAGE":
                prefs.preferred_silence_type = "MU"
            elif current_emotion == "PANIC":
                prefs.preferred_silence_type = "ZEN"
        elif current_emotion == "SEEKING":
            prefs.prefers_guidance = True
            prefs.preferred_panksepp_system = "SEEKING"
            prefs.preferred_session_length = "long"
        elif current_emotion == "PLAY":
            prefs.preferred_panksepp_system = "PLAY"
            prefs.preferred_session_length = "short"

        # Find strategies that worked for similar emotions in the past
        for s in profile._snapshots:
            if s.dominant_emotion == current_emotion and s.healing_effectiveness is not None:
                if s.healing_effectiveness > 0.5 and s.healing_applied:
                    if s.healing_applied not in prefs.effective_strategies:
                        prefs.effective_strategies.append(s.healing_applied)

        return prefs

    # ------------------------------------------------------------------
    # Trajectory
    # ------------------------------------------------------------------

    def get_emotional_trajectory(
        self, profile: EmotionalProfile, days: int = 7
    ) -> List[EmotionalSnapshot]:
        """獲取最近 N 天的情感軌跡"""
        cutoff = datetime.now() - timedelta(days=days)
        return [s for s in profile._snapshots if s.timestamp >= cutoff]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _update_baseline(self, profile: EmotionalProfile, snapshot: EmotionalSnapshot) -> None:
        """用指數移動平均更新基線情緒"""
        alpha = 0.1  # slow update rate
        emotion = snapshot.dominant_emotion
        if emotion in profile.baseline_emotions:
            old = profile.baseline_emotions[emotion]
            profile.baseline_emotions[emotion] = old * (1 - alpha) + snapshot.intensity * alpha

    def _update_interaction_days(self, profile: EmotionalProfile) -> None:
        """更新互動天數"""
        if not profile._snapshots:
            return
        dates = {s.timestamp.strftime("%Y-%m-%d") for s in profile._snapshots}
        profile.interaction_days = len(dates)

    # ------------------------------------------------------------------
    # Persistence (SQLite)
    # ------------------------------------------------------------------

    def _init_db(self, db_path: str) -> None:
        """初始化 SQLite 資料庫"""
        conn = sqlite3.connect(db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS emofriend_profiles (
                    user_id TEXT PRIMARY KEY,
                    baseline_emotions TEXT NOT NULL,
                    stress_sources TEXT NOT NULL,
                    emotional_patterns TEXT NOT NULL,
                    healing_preferences TEXT NOT NULL,
                    risk_level INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    last_updated TEXT NOT NULL,
                    interaction_days INTEGER NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS emofriend_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    dominant_emotion TEXT NOT NULL,
                    valence REAL NOT NULL,
                    arousal REAL NOT NULL,
                    intensity REAL NOT NULL,
                    trigger TEXT,
                    healing_applied TEXT,
                    healing_effectiveness REAL,
                    FOREIGN KEY (user_id) REFERENCES emofriend_profiles(user_id)
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def save_profile(self, profile: EmotionalProfile) -> None:
        """保存畫像到 SQLite"""
        if not self._db_path:
            raise RuntimeError("No db_path configured for persistence")

        conn = sqlite3.connect(self._db_path)
        try:
            # Serialize complex fields
            baseline_json = json.dumps(profile.baseline_emotions)
            stress_json = json.dumps(profile.stress_sources)
            patterns_json = json.dumps([
                {
                    "pattern_type": p.pattern_type,
                    "description": p.description,
                    "frequency": p.frequency,
                    "trigger": p.trigger,
                    "effective_healing": p.effective_healing,
                    "confidence": p.confidence,
                }
                for p in profile.emotional_patterns
            ])
            prefs_json = json.dumps({
                "preferred_silence_type": profile.healing_preferences.preferred_silence_type,
                "preferred_panksepp_system": profile.healing_preferences.preferred_panksepp_system,
                "prefers_guidance": profile.healing_preferences.prefers_guidance,
                "prefers_listening": profile.healing_preferences.prefers_listening,
                "preferred_session_length": profile.healing_preferences.preferred_session_length,
                "effective_strategies": profile.healing_preferences.effective_strategies,
            })

            conn.execute(
                """INSERT OR REPLACE INTO emofriend_profiles
                   (user_id, baseline_emotions, stress_sources, emotional_patterns,
                    healing_preferences, risk_level, created_at, last_updated, interaction_days)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    profile.user_id,
                    baseline_json,
                    stress_json,
                    patterns_json,
                    prefs_json,
                    profile.risk_level.value,
                    profile.created_at.isoformat(),
                    profile.last_updated.isoformat(),
                    profile.interaction_days,
                ),
            )

            # Save snapshots
            for s in profile._snapshots:
                conn.execute(
                    """INSERT OR REPLACE INTO emofriend_snapshots
                       (user_id, timestamp, dominant_emotion, valence, arousal, intensity,
                        trigger, healing_applied, healing_effectiveness)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        profile.user_id,
                        s.timestamp.isoformat(),
                        s.dominant_emotion,
                        s.valence,
                        s.arousal,
                        s.intensity,
                        s.trigger,
                        s.healing_applied,
                        s.healing_effectiveness,
                    ),
                )

            conn.commit()
        finally:
            conn.close()

    def load_profile(self, user_id: str) -> Optional[EmotionalProfile]:
        """從 SQLite 載入畫像"""
        if not self._db_path:
            raise RuntimeError("No db_path configured for persistence")

        conn = sqlite3.connect(self._db_path)
        try:
            row = conn.execute(
                "SELECT * FROM emofriend_profiles WHERE user_id = ?", (user_id,)
            ).fetchone()

            if row is None:
                return None

            (
                uid, baseline_json, stress_json, patterns_json,
                prefs_json, risk_val, created_str, updated_str, interaction_days
            ) = row

            # Deserialize
            baseline = json.loads(baseline_json)
            stress_sources = json.loads(stress_json)
            patterns_data = json.loads(patterns_json)
            prefs_data = json.loads(prefs_json)

            emotional_patterns = [
                EmotionalPattern(
                    pattern_type=p["pattern_type"],
                    description=p["description"],
                    frequency=p["frequency"],
                    trigger=p["trigger"],
                    effective_healing=p["effective_healing"],
                    confidence=p["confidence"],
                )
                for p in patterns_data
            ]

            healing_prefs = HealingPreferences(
                preferred_silence_type=prefs_data["preferred_silence_type"],
                preferred_panksepp_system=prefs_data["preferred_panksepp_system"],
                prefers_guidance=prefs_data["prefers_guidance"],
                prefers_listening=prefs_data["prefers_listening"],
                preferred_session_length=prefs_data["preferred_session_length"],
                effective_strategies=prefs_data["effective_strategies"],
            )

            # Load snapshots
            snapshot_rows = conn.execute(
                "SELECT timestamp, dominant_emotion, valence, arousal, intensity, "
                "trigger, healing_applied, healing_effectiveness "
                "FROM emofriend_snapshots WHERE user_id = ? ORDER BY timestamp",
                (user_id,),
            ).fetchall()

            snapshots = [
                EmotionalSnapshot(
                    timestamp=datetime.fromisoformat(r[0]),
                    dominant_emotion=r[1],
                    valence=r[2],
                    arousal=r[3],
                    intensity=r[4],
                    trigger=r[5],
                    healing_applied=r[6],
                    healing_effectiveness=r[7],
                )
                for r in snapshot_rows
            ]

            return EmotionalProfile(
                user_id=uid,
                baseline_emotions=baseline,
                stress_sources=stress_sources,
                emotional_patterns=emotional_patterns,
                healing_preferences=healing_prefs,
                risk_level=RiskLevel(risk_val),
                created_at=datetime.fromisoformat(created_str),
                last_updated=datetime.fromisoformat(updated_str),
                interaction_days=interaction_days,
                _snapshots=snapshots,
            )
        finally:
            conn.close()


if __name__ == "__main__":
    mgr = UserEmotionalProfileManager()
    profile = mgr.create_profile("test_user")
    print(f"Profile created: {profile.user_id}")
    print(f"Baseline: {profile.baseline_emotions}")
    print(f"Risk level: {profile.risk_level.name}")

    snapshot = EmotionalSnapshot(
        timestamp=datetime.now(),
        dominant_emotion="FEAR",
        valence=-0.5,
        arousal=0.7,
        intensity=0.6,
        trigger="work stress",
    )
    mgr.add_snapshot(profile, snapshot)
    print(f"After snapshot: baseline FEAR={profile.baseline_emotions['FEAR']:.3f}")
