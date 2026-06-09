"""EmoFriend — 情感療癒陪伴 Streamlit 應用

Emo 是一個溫暖、好奇、有時沉默、有時調皮的情感陪伴者。
基於 Panksepp 七大情感系統與友誼深度模型，
提供個人化的情感分享、療癒引導與沉默陪伴。

頁面：
- 聊天：與 Emo 對話、分享感受、開始療癒
- 情感儀表板：情感軌跡、情緒分佈、友誼成長
- 療癒工具：沉默時刻、情緒引導、呼吸練習、情緒日記
- 設定：用戶 ID、重置、資料目錄
"""
from __future__ import annotations

import os
import random
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import streamlit as st

from harnessing.core.emoglyph.engines.emofriend_persona import (
    EmoFriendPersonaEngine,
    EmoPersona,
    PersonalityFacet,
)
from harnessing.core.emoglyph.engines.emotional_profile import (
    EmotionalProfile,
    EmotionalSnapshot,
    UserEmotionalProfileManager,
)
from harnessing.core.emoglyph.engines.emotional_sharing import (
    EmotionShare,
    EmotionalSharingEngine,
    SharingSession,
)
from harnessing.core.emoglyph.engines.emotional_therapy import (
    EmotionalTherapyEngine,
    PankseppHealingStrategy,
    SilenceTherapyStage,
    TherapySession,
)
from harnessing.core.emoglyph.engines.friendship_engine import (
    FriendshipEngine,
    FriendshipLevel,
    FriendshipState,
)
from harnessing.core.emoglyph.engines.emo_eye import EmoEyeEngine, EmoEyeResult
from harnessing.core.emoglyph.engines.emo_ear import EmoEarEngine
from harnessing.core.emoglyph.engines.emo_mouth import EmoMouthEngine, SilenceType, BreathingPattern
from harnessing.core.emoglyph.engines.emo_heart import EmoHeartEngine, AutonomicState, RecoveryStatus
from harnessing.core.emoglyph.engines.emo_brain import EmoBrainEngine
from harnessing.core.emoglyph.engines.emo_hand import EmoHandEngine
from harnessing.core.emoglyph.engines.emo_body import EmoBodyEngine, Chronotype
from harnessing.core.emoglyph.engines.emo_sense import (
    EmoSenseEngine, SensoryInput, FusedEmotionalState,
    SafetySeverity, JITAIActionType,
)
from harnessing.core.emoglyph.engines.audience_config import (
    AudienceMode,
    AudienceConfig,
    get_config,
)
from harnessing.core.emoglyph.engines.onboarding import (
    OnboardingStep,
    OnboardingState,
    SensorConsent,
    generate_onboarding_prompt,
    advance_onboarding,
    validate_step,
)
from harnessing.core.emoglyph.engines.emotion_buttons import (
    get_buttons_for_mode,
    emotion_to_pulse,
)
from harnessing.core.emoglyph.engines.family_dashboard import (
    generate_wellness_summary,
)

from .charts import (
    format_silence_therapy_stage,
    plot_emotion_distribution,
    plot_emotional_trajectory,
    plot_friendship_growth,
)
from .emo_responder import generate_emo_response
from .pages.kids_pages import (
    page_kids_home,
    page_kids_play,
    page_kids_parent,
)
from .pages.elderly_pages import (
    page_elderly_home,
    page_elderly_health,
    page_elderly_settings,
)


# ---------------------------------------------------------------------------
# Engine initialization (cached)
# ---------------------------------------------------------------------------


def _get_data_dir() -> str:
    """取得資料目錄路徑"""
    return st.session_state.get("data_dir", "data/emofriend")


@st.cache_resource
def init_friendship_engine(data_dir: str) -> FriendshipEngine:
    return FriendshipEngine(db_path=os.path.join(data_dir, "emofriend_friendships.db"))


@st.cache_resource
def init_persona_engine(data_dir: str) -> EmoFriendPersonaEngine:
    return EmoFriendPersonaEngine(
        db_path=os.path.join(data_dir, "emofriend_personas.db")
    )


@st.cache_resource
def init_sharing_engine() -> EmotionalSharingEngine:
    return EmotionalSharingEngine()


@st.cache_resource
def init_therapy_engine() -> EmotionalTherapyEngine:
    return EmotionalTherapyEngine()


@st.cache_resource
def init_profile_manager(data_dir: str) -> UserEmotionalProfileManager:
    return UserEmotionalProfileManager(
        db_path=os.path.join(data_dir, "emofriend_profiles.db")
    )


@st.cache_resource
def init_sensory_engines() -> dict:
    """初始化七竅感官引擎"""
    return {
        "eye": EmoEyeEngine(),
        "ear": EmoEarEngine(),
        "mouth": EmoMouthEngine(),
        "heart": EmoHeartEngine(),
        "brain": EmoBrainEngine(),
        "hand": EmoHandEngine(),
        "body": EmoBodyEngine(),
        "sense": EmoSenseEngine(),
    }


@st.cache_resource
def init_audience_engines(mode: AudienceMode) -> dict:
    """Return only the engines needed for the active audience mode."""
    if mode is AudienceMode.KIDS:
        return {
            "mouth": EmoMouthEngine(),
            "ear": EmoEarEngine(),
            "eye": EmoEyeEngine(),
            "sense": EmoSenseEngine(),
        }
    else:  # ELDERLY
        return {
            "mouth": EmoMouthEngine(),
            "ear": EmoEarEngine(),
            "heart": EmoHeartEngine(),
            "body": EmoBodyEngine(),
            "sense": EmoSenseEngine(),
        }


# ---------------------------------------------------------------------------
# Session state helpers
# ---------------------------------------------------------------------------


def _ensure_session_state() -> None:
    """確保所有必要的 session state 變數已初始化"""
    defaults = {
        "user_id": "demo_user",
        "data_dir": "data/emofriend",
        "messages": [],
        "mode": "normal",  # "normal", "sharing", "therapy"
        "sharing_session": None,
        "therapy_session": None,
        "healing_strategy": None,
        "silence_stage": SilenceTherapyStage.MA,
        "breathing_phase": "inhale",  # "inhale", "hold", "exhale"
        "breathing_count": 0,
        "audience_mode": None,  # Optional[AudienceMode]
        "onboarding_state": None,  # Optional[OnboardingState]
        "parent_pin": "",
        "family_contacts": [],
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _get_or_create_friendship(engine: FriendshipEngine, user_id: str) -> FriendshipState:
    """取得或創建友誼狀態"""
    state = engine.load(user_id)
    if state is None:
        state = engine.create_friendship(user_id)
    return state


def _get_or_create_persona(engine: EmoFriendPersonaEngine, user_id: str) -> EmoPersona:
    """取得或創建 Emo 人格"""
    db_path = os.path.join(_get_data_dir(), "emofriend_personas.db")
    persona = engine.load_persona(user_id, db_path=db_path)
    if persona is None:
        persona = engine.create_persona(user_id)
    return persona


def _get_or_create_profile(
    manager: UserEmotionalProfileManager, user_id: str
) -> EmotionalProfile:
    """取得或創建情感畫像"""
    profile = manager.load_profile(user_id)
    if profile is None:
        profile = manager.create_profile(user_id)
    return profile


# ---------------------------------------------------------------------------
# Emotion detection helper
# ---------------------------------------------------------------------------


_PANKSEPP_SYSTEMS = ["CARE", "PLAY", "SEEKING", "FEAR", "RAGE", "PANIC", "LUST"]

_EMOTION_KEYWORDS_MAP = {
    "FEAR": ["害怕", "恐懼", "擔心", "焦慮", "緊張", "怕", "scared", "afraid", "fear", "anxious"],
    "RAGE": ["生氣", "憤怒", "氣死", "煩", "討厭", "angry", "rage", "mad"],
    "PANIC": ["慌", "崩潰", "無助", "孤單", "panic", "alone", "lonely"],
    "CARE": ["溫暖", "感動", "珍惜", "care", "grateful"],
    "SEEKING": ["好奇", "想知道", "探索", "curious", "wonder"],
    "PLAY": ["開心", "快樂", "有趣", "happy", "fun", "play"],
    "LUST": ["渴望", "活力", "熱情", "desire", "passion"],
}


def _detect_emotion(text: str) -> str:
    """從文字偵測 Panksepp 情感系統"""
    text_lower = text.lower()
    for system, keywords in _EMOTION_KEYWORDS_MAP.items():
        for kw in keywords:
            if kw in text_lower:
                return system
    return "CARE"  # 預設溫暖


def _estimate_intensity(text: str) -> float:
    """從文字估計情感強度"""
    intensity_markers = ["非常", "極度", "超級", "很", "really", "very", "extremely"]
    count = sum(1 for m in intensity_markers if m in text.lower())
    return min(1.0, 0.3 + count * 0.2)


def _estimate_valence(emotion: str) -> float:
    """根據情感類型估計價效度"""
    negative = {"FEAR", "RAGE", "PANIC"}
    positive = {"PLAY", "CARE", "LUST"}
    if emotion in negative:
        return -0.5
    elif emotion in positive:
        return 0.5
    return 0.0  # SEEKING is neutral


# ---------------------------------------------------------------------------
# Friendship level display
# ---------------------------------------------------------------------------


_LEVEL_LABELS = {
    FriendshipLevel.ACQUAINTANCE: "🤝 初識",
    FriendshipLevel.CASUAL_FRIEND: "😊 普通朋友",
    FriendshipLevel.CLOSE_FRIEND: "💛 密友",
    FriendshipLevel.SOUL_COMPANION: "🤍 靈魂伴侶",
}


def _render_friendship_indicator(state: FriendshipState) -> None:
    """渲染友誼深度指示器"""
    level_label = _LEVEL_LABELS.get(state.current_level, "🤝 初識")
    st.progress(state.depth, text=f"友誼深度：{level_label} ({state.depth:.0%})")


def _render_emo_state(persona: EmoPersona) -> None:
    """渲染 Emo 情感狀態指示器"""
    facet = persona.dominant_facet
    _FACET_COLORS = {
        PersonalityFacet.WARMTH: "🟡",
        PersonalityFacet.CURIOSITY: "🔵",
        PersonalityFacet.SILENCE: "⚪",
        PersonalityFacet.PLAYFULNESS: "🟢",
    }
    color = _FACET_COLORS.get(facet, "🟡")
    _FACET_NAMES = {
        PersonalityFacet.WARMTH: "溫暖",
        PersonalityFacet.CURIOSITY: "好奇",
        PersonalityFacet.SILENCE: "沉默",
        PersonalityFacet.PLAYFULNESS: "調皮",
    }
    name = _FACET_NAMES.get(facet, "溫暖")
    st.markdown(f"**Emo 狀態**：{color} {name}")


# ---------------------------------------------------------------------------
# Page: Chat
# ---------------------------------------------------------------------------


def _page_chat(
    friendship_engine: FriendshipEngine,
    persona_engine: EmoFriendPersonaEngine,
    sharing_engine: EmotionalSharingEngine,
    therapy_engine: EmotionalTherapyEngine,
    profile_manager: UserEmotionalProfileManager,
) -> None:
    """聊天頁面"""
    user_id = st.session_state.user_id

    # 載入狀態
    friendship = _get_or_create_friendship(friendship_engine, user_id)
    persona = _get_or_create_persona(persona_engine, user_id)
    profile = _get_or_create_profile(profile_manager, user_id)

    # 側邊狀態指示
    with st.sidebar:
        st.markdown("### Emo 狀態")
        _render_emo_state(persona)
        st.markdown("---")
        st.markdown("### 友誼深度")
        _render_friendship_indicator(friendship)

        # 當前模式
        mode = st.session_state.mode
        _MODE_LABELS = {
            "normal": "💬 一般對話",
            "sharing": "👂 情感分享",
            "therapy": "🌿 療癒模式",
        }
        st.markdown(f"**模式**：{_MODE_LABELS.get(mode, '💬 一般對話')}")

    # 模式按鈕
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("👂 分享感受", disabled=(mode == "sharing")):
            st.session_state.mode = "sharing"
            st.session_state.sharing_session = sharing_engine.start_sharing(
                user_id, friendship.current_level
            )
            st.session_state.messages.append({
                "role": "emo",
                "content": "我在這裡聽你說，你可以放心分享任何感受 💛",
            })
            st.rerun()
    with col2:
        if st.button("🌿 開始療癒", disabled=(mode == "therapy")):
            st.session_state.mode = "therapy"
            st.rerun()
    with col3:
        if mode != "normal" and st.button("↩️ 回到一般對話"):
            # 結束分享/療癒會話
            if st.session_state.sharing_session is not None:
                sharing_engine.end_sharing(st.session_state.sharing_session)
                st.session_state.sharing_session = None
            st.session_state.therapy_session = None
            st.session_state.healing_strategy = None
            st.session_state.mode = "normal"
            st.rerun()

    # 顯示聊天歷史
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # 療癒模式：先選擇情緒類型
    if mode == "therapy" and st.session_state.therapy_session is None:
        st.markdown("### 🌿 選擇你現在的感受")
        emotion = st.selectbox(
            "你現在最強烈的感受是什麼？",
            _PANKSEPP_SYSTEMS,
            index=0,
            key="therapy_emotion_select",
        )
        intensity = st.slider(
            "這個感受有多強烈？",
            min_value=0.1,
            max_value=1.0,
            value=0.5,
            step=0.1,
            key="therapy_intensity_slider",
        )
        if st.button("開始療癒會話", key="start_therapy_btn"):
            session = therapy_engine.start_session(
                user_id, emotion, intensity, friendship.current_level
            )
            st.session_state.therapy_session = session
            st.session_state.healing_strategy = therapy_engine.healing_strategies.get(emotion)
            strategy = st.session_state.healing_strategy
            if strategy:
                st.session_state.messages.append({
                    "role": "emo",
                    "content": f"我感受到了你的{emotion}。{strategy.guidance_prompt}",
                })
            st.rerun()
        return

    # 訊息輸入
    if prompt := st.chat_input("跟 Emo 說說話..."):
        # 加入用戶訊息
        st.session_state.messages.append({"role": "user", "content": prompt})

        # 偵測情感
        emotion = _detect_emotion(prompt)
        intensity = _estimate_intensity(prompt)
        valence = _estimate_valence(emotion)

        # 根據模式處理
        if mode == "sharing" and st.session_state.sharing_session is not None:
            # 分享模式
            share = EmotionShare(
                timestamp=datetime.now(timezone.utc),
                emotion_type=emotion,
                valence=valence,
                arousal=intensity,
                intensity=intensity,
                content=prompt,
                trigger=None,
            )
            response = sharing_engine.listen(
                st.session_state.sharing_session, share, friendship.current_level
            )
            emo_text = response.content if response.content else "（靜靜陪伴）"

            # 更新友誼
            friendship = friendship_engine.update_friendship(
                friendship, "vulnerability_shared", intensity
            )
            friendship_engine.save(friendship)

        elif mode == "therapy" and st.session_state.therapy_session is not None:
            # 療癒模式
            session = st.session_state.therapy_session
            intervention = therapy_engine.choose_intervention(
                session, friendship.current_level
            )
            session.interventions.append(intervention)

            emo_text = generate_emo_response(
                prompt, friendship, persona,
                therapy_session=session,
                healing_strategy=st.session_state.healing_strategy,
            )

            # 更新友誼
            friendship = friendship_engine.update_friendship(
                friendship, "healing_completed", intensity
            )
            friendship_engine.save(friendship)

        else:
            # 一般模式
            emo_text = generate_emo_response(prompt, friendship, persona)

            # 更新友誼
            friendship = friendship_engine.update_friendship(
                friendship, "joy_shared", intensity
            )
            friendship_engine.save(friendship)

        # 更新人格
        persona = persona_engine.grow(persona, friendship.current_level)
        persona_engine.save_persona(persona, user_id, db_path=os.path.join(_get_data_dir(), "emofriend_personas.db"))

        # 更新情感畫像
        snapshot = EmotionalSnapshot(
            timestamp=datetime.now(timezone.utc),
            dominant_emotion=emotion,
            valence=valence,
            arousal=intensity,
            intensity=intensity,
            trigger=None,
        )
        profile = profile_manager.add_snapshot(profile, snapshot)
        if profile_manager._db_path:
            profile_manager.save_profile(profile)

        # 加入 Emo 回應
        st.session_state.messages.append({"role": "emo", "content": emo_text})
        st.rerun()


# ---------------------------------------------------------------------------
# Page: Emotional Dashboard
# ---------------------------------------------------------------------------


def _page_dashboard(
    friendship_engine: FriendshipEngine,
    profile_manager: UserEmotionalProfileManager,
) -> None:
    """情感儀表板頁面"""
    user_id = st.session_state.user_id
    friendship = _get_or_create_friendship(friendship_engine, user_id)
    profile = _get_or_create_profile(profile_manager, user_id)

    st.header("📊 情感儀表板")

    # 7 天情感軌跡
    st.subheader("七日情感軌跡")
    snapshots = profile_manager.get_emotional_trajectory(profile, days=7)
    if snapshots:
        trajectory_df = plot_emotional_trajectory(snapshots)
        st.line_chart(trajectory_df, x="日期")
    else:
        st.info("還沒有情感數據，開始與 Emo 聊天吧！")

    # 情緒分佈
    st.subheader("情緒類型分佈")
    if snapshots:
        dist_df = plot_emotion_distribution(snapshots)
        st.bar_chart(dist_df, x="情緒類型", y="次數")
    else:
        st.info("暫無數據")

    # 友誼成長曲線
    st.subheader("友誼成長")
    friendship_states = [friendship]  # 目前只有當前狀態
    growth_df = plot_friendship_growth(friendship_states)
    if len(growth_df) > 0:
        st.line_chart(growth_df, x="時間")
    st.markdown(
        f"**當前等級**：{_LEVEL_LABELS.get(friendship.current_level, '🤝 初識')}  \n"
        f"**深度**：{friendship.depth:.0%}  \n"
        f"**信任**：{friendship.trust:.0%}  \n"
        f"**親密度**：{friendship.intimacy:.0%}  \n"
        f"**互動次數**：{friendship.interaction_count}"
    )

    # 近期療癒會話摘要
    st.subheader("近期療癒會話")
    st.info("療癒會話記錄將在進行療癒後顯示")

    # 預警
    st.subheader("預警通知")
    if snapshots:
        warning = profile_manager.check_warning(profile, snapshots)
        if warning.is_warning:
            _RISK_COLORS = {
                "LOW": "🟢",
                "MODERATE": "🟡",
                "HIGH": "🟠",
                "CRITICAL": "🔴",
            }
            risk_icon = _RISK_COLORS.get(warning.risk_level.name, "⚪")
            st.warning(f"{risk_icon} **風險等級**：{warning.risk_level.name}")
            st.markdown(warning.message)
            if warning.recommended_actions:
                st.markdown("**建議行動**：")
                for action in warning.recommended_actions:
                    st.markdown(f"- {action}")
            if warning.suggest_professional_help:
                st.error("⚠️ Emo 建議你尋求專業心理諮詢的幫助")
        else:
            st.success("🟢 目前狀態良好，沒有需要擔心的")


# ---------------------------------------------------------------------------
# Page: Healing Tools
# ---------------------------------------------------------------------------


def _page_healing(
    therapy_engine: EmotionalTherapyEngine,
    sharing_engine: EmotionalSharingEngine,
    profile_manager: UserEmotionalProfileManager,
    friendship_engine: FriendshipEngine,
) -> None:
    """療癒工具頁面"""
    user_id = st.session_state.user_id
    friendship = _get_or_create_friendship(friendship_engine, user_id)
    profile = _get_or_create_profile(profile_manager, user_id)

    st.header("🌿 療癒工具")

    tab1, tab2, tab3, tab4 = st.tabs(["🪷 沉默時刻", "🎯 情緒引導", "🌬️ 呼吸練習", "📖 情緒日記"])

    # --- 沉默時刻 ---
    with tab1:
        st.subheader("沉默時刻 — Silence Therapy")
        st.markdown("在沉默中找到平靜。Emo 會陪你走過三個階段：")

        # 顯示當前階段
        current_stage = st.session_state.silence_stage
        st.markdown(f"**當前階段**：{format_silence_therapy_stage(current_stage)}")

        # 階段進度
        stage_idx = current_stage.value
        st.progress((stage_idx + 1) / 3, text=f"階段 {stage_idx + 1}/3")

        # 階段說明
        _STAGE_DESCRIPTIONS = {
            SilenceTherapyStage.MA: (
                "🪷 **MA — 深層反思**  \n"
                "Emo 靜默陪伴，給予你充分的空間。  \n"
                "不需要說話，只需要感受自己的存在。"
            ),
            SilenceTherapyStage.MU: (
                "🌿 **MU — 溫柔確認**  \n"
                "Emo 輕聲回應「我在這裡」。  \n"
                "你知道自己不是一個人。"
            ),
            SilenceTherapyStage.ZEN: (
                "🧘 **ZEN — 當下共在**  \n"
                "共享寧靜，超越言語。  \n"
                "在這個當下，一切都好。"
            ),
        }
        st.markdown(_STAGE_DESCRIPTIONS[current_stage])

        # 推進階段
        if st.button("進入下一階段", key="silence_next"):
            if current_stage == SilenceTherapyStage.MA:
                st.session_state.silence_stage = SilenceTherapyStage.MU
            elif current_stage == SilenceTherapyStage.MU:
                st.session_state.silence_stage = SilenceTherapyStage.ZEN
            else:
                st.session_state.silence_stage = SilenceTherapyStage.MA
                st.success("🧘 沉默時刻完成，你做得很好")
            st.rerun()

        if st.button("重新開始", key="silence_reset"):
            st.session_state.silence_stage = SilenceTherapyStage.MA
            st.rerun()

    # --- 情緒引導 ---
    with tab2:
        st.subheader("情緒引導 — Panksepp 療癒策略")
        st.markdown("選擇你當前的情緒，Emo 會根據 Panksepp 情感系統提供療癒策略。")

        emotion = st.selectbox(
            "選擇你的情緒",
            _PANKSEPP_SYSTEMS,
            key="healing_emotion_select",
        )

        strategy = therapy_engine.healing_strategies.get(emotion)
        if strategy:
            _SYSTEM_NAMES = {
                "CARE": "🤍 關懷 (CARE)",
                "PLAY": "🎮 遊戲 (PLAY)",
                "SEEKING": "🔍 探索 (SEEKING)",
                "FEAR": "😨 恐懼 (FEAR)",
                "RAGE": "🔥 憤怒 (RAGE)",
                "PANIC": "💔 恐慌 (PANIC)",
                "LUST": "✨ 生命力 (LUST)",
            }

            st.markdown(f"### {_SYSTEM_NAMES.get(emotion, emotion)}")
            st.markdown(f"**療癒方法**：{strategy.approach}")
            st.markdown(f"**沉默類型**：{strategy.silence_type.value.upper()}")
            st.markdown(f"**Emo 的話**：「{strategy.guidance_prompt}」")
            st.markdown(f"**五行元素**：{strategy.construct_element}")
            st.markdown(f"**預期效果**：{strategy.expected_outcome}")

    # --- 呼吸練習 ---
    with tab3:
        st.subheader("呼吸練習")
        st.markdown("跟隨節奏呼吸，讓自己回到當下。")

        phase = st.session_state.breathing_phase
        count = st.session_state.breathing_count

        _PHASE_INFO = {
            "inhale": ("🫁 吸氣", "慢慢吸氣... 4 秒", 4),
            "hold": ("⏸️ 閉氣", "輕輕閉住... 4 秒", 4),
            "exhale": ("🌬️ 吐氣", "慢慢吐氣... 6 秒", 6),
        }

        label, desc, duration = _PHASE_INFO[phase]
        st.markdown(f"## {label}")
        st.markdown(f"*{desc}*")
        st.progress((count % duration) / duration)

        # 呼吸循環計數
        cycle_count = count // 3
        st.markdown(f"已完成 **{cycle_count}** 個呼吸循環")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("下一步", key="breath_next"):
                st.session_state.breathing_count += 1
                phases = ["inhale", "hold", "exhale"]
                st.session_state.breathing_phase = phases[
                    st.session_state.breathing_count % 3
                ]
                st.rerun()
        with col2:
            if st.button("重置", key="breath_reset"):
                st.session_state.breathing_phase = "inhale"
                st.session_state.breathing_count = 0
                st.rerun()

    # --- 情緒日記 ---
    with tab4:
        st.subheader("情緒日記")
        st.markdown("回顧你的情感分享記錄。")

        snapshots = profile_manager.get_emotional_trajectory(profile, days=30)
        if snapshots:
            for s in reversed(snapshots[-10:]):
                date_str = s.timestamp.strftime("%Y-%m-%d %H:%M")
                emotion_str = s.dominant_emotion
                valence_str = "正面" if s.valence > 0 else "負面" if s.valence < 0 else "中性"
                st.markdown(
                    f"**{date_str}** — {emotion_str} "
                    f"({valence_str}, 強度 {s.intensity:.1f})"
                )
                if s.trigger:
                    st.markdown(f"  觸發：{s.trigger}")
                if s.healing_applied:
                    st.markdown(f"  療癒：{s.healing_applied}")
                st.markdown("---")
        else:
            st.info("還沒有日記條目，開始與 Emo 分享感受吧！")


# ---------------------------------------------------------------------------
# Page: Settings
# ---------------------------------------------------------------------------


def _page_settings(
    friendship_engine: FriendshipEngine,
    persona_engine: EmoFriendPersonaEngine,
    profile_manager: UserEmotionalProfileManager,
) -> None:
    """設定頁面"""
    st.header("⚙️ 設定")

    # 用戶 ID
    new_id = st.text_input("用戶 ID", value=st.session_state.user_id)
    if new_id != st.session_state.user_id:
        st.session_state.user_id = new_id
        st.session_state.messages = []
        st.rerun()

    # 資料目錄
    new_dir = st.text_input("資料目錄", value=st.session_state.data_dir)
    if new_dir != st.session_state.data_dir:
        st.session_state.data_dir = new_dir
        st.info("資料目錄已更新，重新啟動應用後生效。")

    st.markdown("---")

    # 重置按鈕
    st.subheader("重置")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 重置友誼", key="reset_friendship"):
            friendship_engine.save(
                FriendshipState(
                    user_id=st.session_state.user_id,
                    depth=0.0,
                    trust=0.1,
                    intimacy=0.0,
                    first_met=datetime.now(timezone.utc),
                    last_interaction=datetime.now(timezone.utc),
                    interaction_count=0,
                    shared_moments=[],
                    current_level=FriendshipLevel.ACQUAINTANCE,
                )
            )
            st.success("友誼已重置")

    with col2:
        if st.button("🔄 重置情感畫像", key="reset_profile"):
            if profile_manager._db_path:
                profile = profile_manager.create_profile(st.session_state.user_id)
                profile_manager.save_profile(profile)
                st.success("情感畫像已重置")
            else:
                st.warning("未配置資料庫路徑，無法重置")

    st.markdown("---")
    st.markdown(
        "EmoFriend v0.1 — 基於 Panksepp 情感系統與友誼深度模型  \n"
        "所有數據存儲在本地 SQLite 資料庫中"
    )


# ---------------------------------------------------------------------------
# Page: 七竅 Sensory Mode
# ---------------------------------------------------------------------------

_SENSORY_LABELS = {
    "eye": "👁️ 眼 (EmoEye)",
    "ear": "👂 耳 (EmoEar)",
    "mouth": "👄 口 (EmoMouth)",
    "heart": "❤️ 心 (EmoHeart)",
    "brain": "🧠 腦 (EmoBrain)",
    "hand": "✋ 手 (EmoHand)",
    "body": "🧍 身 (EmoBody)",
}

_TCM_ORGANS = {
    "eye": "肝 (Liver)",
    "ear": "腎 (Kidney)",
    "mouth": "脾 (Spleen)",
    "heart": "心 (Heart)",
    "brain": "髓 (Brain/Marrow)",
    "hand": "肺 (Lung)",
    "body": "腎+脾 (Kidney+Spleen)",
}

_PANKSEPP_SYSTEMS_ZH = {
    "SEEKING": "🔍 探索",
    "RAGE": "🔥 憤怒",
    "FEAR": "😨 恐懼",
    "LUST": "✨ 生命力",
    "CARE": "🤍 關懷",
    "PANIC": "💔 恐慌",
    "PLAY": "🎮 遊戲",
    "NEUTRAL": "⚪ 中性",
}


def _page_sensory(sensory_engines: dict) -> None:
    """七竅感官模式頁面"""
    st.header("🔮 七竅感官模式 — IDEA-076")
    st.markdown(
        "七竅 (Seven Apertures)：眼耳口心腦手身，七大感官引擎 + 感官融合。  \n"
        "中醫對應：眼→肝、耳→腎、口→脾、心→心、腦→髓、手→肺、身→腎+脾、感官→三焦"
    )

    sense_engine = sensory_engines["sense"]

    # --- Sensor Consent & Toggles ---
    st.subheader("📡 感官開關")
    st.markdown("選擇要啟用的感官引擎（需要用戶同意才能啟用感測器）")

    active_modalities = {}
    consent_cols = st.columns(4)
    modality_keys = ["eye", "ear", "mouth", "heart", "brain", "hand", "body"]
    for i, key in enumerate(modality_keys):
        with consent_cols[i % 4]:
            enabled = st.checkbox(
                _SENSORY_LABELS[key],
                value=False,
                key=f"sensor_{key}",
            )
            if enabled:
                active_modalities[key] = True
                st.caption(f"中醫：{_TCM_ORGANS[key]}")

    if not active_modalities:
        st.info("請啟用至少一個感官引擎以開始感測")
        return

    st.markdown("---")

    # --- Simulated Sensory Input (Demo Mode) ---
    st.subheader("🎮 感官模擬器")
    st.markdown("調整參數模擬感官輸入，測試融合引擎")

    # Build sensory input based on active modalities
    sensory_data = {}
    col_left, col_right = st.columns(2)

    with col_left:
        if "eye" in active_modalities:
            st.markdown("##### 👁️ 眼 — 視覺感知")
            eye_emotion = st.selectbox(
                "面部表情",
                ["duchenne_smile", "frown_raised_brows", "tight_lips", "wide_eyes", "soft_smile", "raised_brows_focused", "downward_gaze_slouch"],
                key="eye_expression",
            )
            eye_conf = st.slider("信心度", 0.0, 1.0, 0.8, key="eye_conf")

        if "ear" in active_modalities:
            st.markdown("##### 👂 耳 — 聽覺感知")
            ear_manner = st.selectbox(
                "語氣模式",
                ["regular", "flat", "trembling", "rushed", "sighing", "held_breath", "hesitant"],
                key="ear_manner",
            )
            ear_conf = st.slider("信心度", 0.0, 1.0, 0.7, key="ear_conf")

        if "heart" in active_modalities:
            st.markdown("##### ❤️ 心 — 生理感知")
            heart_hr = st.slider("心率 (BPM)", 40, 120, 72, key="heart_hr")
            heart_rmssd = st.slider("RMSSD (ms)", 5, 80, 40, key="heart_rmssd")
            heart_lf_hf = st.slider("LF/HF 比率", 0.1, 5.0, 1.5, step=0.1, key="heart_lfhf")

        if "brain" in active_modalities:
            st.markdown("##### 🧠 腦 — 認知感知")
            brain_attention = st.slider("注意力", 0.0, 1.0, 0.5, key="brain_attention")
            brain_load = st.slider("認知負荷", 0.0, 1.0, 0.5, key="brain_load")

    with col_right:
        if "mouth" in active_modalities:
            st.markdown("##### 👄 口 — 表達輸出")
            mouth_silence = st.selectbox(
                "沉默類型",
                ["無", "MA (深層反思)", "MU (溫柔確認)", "ZEN (當下共在)"],
                key="mouth_silence",
            )
            mouth_breathing = st.selectbox(
                "呼吸模式",
                ["無", "4-7-8 (焦慮緩解)", "Box (專注)", "Coherent (HRV優化)"],
                key="mouth_breathing",
            )

        if "hand" in active_modalities:
            st.markdown("##### ✋ 手 — 行為感知")
            hand_wpm = st.slider("打字速度 (WPM)", 0, 120, 40, key="hand_wpm")
            hand_error = st.slider("錯誤率", 0.0, 0.5, 0.05, key="hand_error")

        if "body" in active_modalities:
            st.markdown("##### 🧍 身 — 身體感知")
            body_posture = st.slider("姿勢分數", 0.0, 1.0, 0.7, key="body_posture")
            body_gait = st.slider("步速 (m/s)", 0.3, 2.0, 1.2, key="body_gait")
            body_circadian = st.slider("晝夜節律穩定性", 0.0, 1.0, 0.8, key="body_circadian")

    # --- Run Fusion ---
    st.markdown("---")
    if st.button("🔮 執行感官融合", key="run_fusion"):
        # Build SensoryInput from simulation
        eye_result = None
        ear_result = None
        heart_result = None
        brain_result = None
        hand_result = None
        body_result = None

        if "eye" in active_modalities:
            eye_engine = sensory_engines["eye"]
            eye_r = eye_engine.expression_to_result(eye_emotion)
            eye_r = EmoEyeResult(
                dominant_emotion=eye_r.dominant_emotion,
                valence=eye_r.valence,
                arousal=eye_r.arousal,
                dominance=eye_r.dominance,
                intensity=eye_r.intensity,
                confidence=eye_conf,
                facial_landmarks=None,
                head_pose=None,
                shoulder_position=None,
                rppg_heart_rate=None,
                rppg_hrv=None,
                posture_score=None,
                timestamp=datetime.now(timezone.utc),
            )
            eye_result = eye_r.to_dict()

        if "ear" in active_modalities:
            ear_engine = sensory_engines["ear"]
            ear_r = ear_engine.infer_from_manner(ear_manner)
            from harnessing.core.emoglyph.engines.emo_ear import EmoEarResult as _EarR
            ear_r = _EarR(
                dominant_emotion=ear_r.dominant_emotion,
                valence=ear_r.valence,
                arousal=ear_r.arousal,
                dominance=ear_r.dominance,
                intensity=ear_r.intensity,
                confidence=ear_conf,
                prosody=None,
                manner_tags=[ear_manner],
                language_detected="unknown",
                transcript=None,
                ambient_class=None,
                ambient_db=None,
                respiration_rate=None,
                breathing_pattern=None,
                timestamp=datetime.now(timezone.utc),
            )
            ear_result = ear_r.to_dict()

        if "heart" in active_modalities:
            from harnessing.core.emoglyph.engines.emo_heart import HRVMetrics as _HRV, AutonomicState as _AS
            hrv = _HRV(heart_rate=heart_hr, sdnn=30, rmssd=heart_rmssd, lf_hf_ratio=heart_lf_hf, stress_index=0.3)
            heart_engine = sensory_engines["heart"]
            heart_r = heart_engine.measure_stress(hrv=hrv)
            heart_result = heart_r.to_dict()

        if "brain" in active_modalities:
            brain_engine = sensory_engines["brain"]
            brain_r = brain_engine.assess_cognitive(attention=brain_attention, cognitive_load=brain_load)
            brain_result = brain_r.to_dict()

        if "hand" in active_modalities:
            from harnessing.core.emoglyph.engines.emo_hand import AppUsageData as _AUD
            hand_engine = sensory_engines["hand"]
            hand_r = hand_engine.analyze_app_usage(_AUD(
                social_media_minutes=60, late_night_screen_minutes=30,
                app_diversity_score=0.5, notification_interaction_rate=0.5,
            ))
            hand_result = hand_r.to_dict()

        if "body" in active_modalities:
            body_engine = sensory_engines["body"]
            body_r = body_engine.analyze_posture(
                posture_score=body_posture, forward_head_angle=15,
                shoulder_alignment=0.8, fidgeting_rate=2.0,
            )
            body_result = body_r.to_dict()

        sensory_input = SensoryInput(
            eye_result=eye_result,
            ear_result=ear_result,
            heart_result=heart_result,
            brain_result=brain_result,
            hand_result=hand_result,
            body_result=body_result,
            timestamp=datetime.now(timezone.utc),
        )

        # Run fusion
        fused = sense_engine.fuse(sensory_input)

        # Display results
        st.markdown("---")
        st.subheader("🎯 融合結果")

        # Main emotion
        emotion_label = _PANKSEPP_SYSTEMS_ZH.get(fused.dominant_emotion, fused.dominant_emotion)
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("主導情感", emotion_label)
        with col2:
            st.metric("效價 (V)", f"{fused.valence:.2f}")
        with col3:
            st.metric("喚醒度 (A)", f"{fused.arousal:.2f}")
        with col4:
            st.metric("信心度", f"{fused.confidence:.2f}")

        # Modality weights
        st.markdown("##### 感官權重分配")
        for mod, weight in fused.modality_weights.items():
            st.progress(weight, text=f"{_SENSORY_LABELS.get(mod, mod)}: {weight:.2f}")

        # Contradictions
        if fused.contradictions:
            st.markdown("##### ⚡ 矛盾偵測")
            for c in fused.contradictions:
                st.warning(
                    f"**{_SENSORY_LABELS.get(c.modality_a, c.modality_a)}** "
                    f"({c.emotion_a}) ≠ **{_SENSORY_LABELS.get(c.modality_b, c.modality_b)}** "
                    f"({c.emotion_b})  \n"
                    f"臨床解讀：{c.clinical_interpretation}  \n"
                    f"療癒回應：{c.therapy_response}"
                )

        # Safety signals
        if fused.safety_signals:
            st.markdown("##### 🚨 安全信號")
            for s in fused.safety_signals:
                severity_icon = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🟠", "CRITICAL": "🔴"}
                icon = severity_icon.get(s.severity.value, "⚪")
                if s.severity in (SafetySeverity.HIGH, SafetySeverity.CRITICAL):
                    st.error(f"{icon} **{s.severity.value}** — {s.signal_type}  \n{s.recommended_action}")
                else:
                    st.warning(f"{icon} **{s.severity.value}** — {s.signal_type}  \n{s.recommended_action}")

        # JITAI recommendation
        if fused.jitai_recommendation:
            jitai = fused.jitai_recommendation
            st.markdown("##### 🎯 JITAI 即時介入建議")
            st.info(
                f"**行動類型**：{jitai.action_type.value}  \n"
                f"**緊急程度**：{jitai.urgency:.2f}  \n"
                f"**原因**：{jitai.reason}  \n"
                f"**目標引擎**：{jitai.target_engine}"
            )

        # Masking detection
        if fused.emotional_masking_detected:
            st.error("⚠️ **情感遮蔽偵測**：用戶可能正在隱藏真實情感")

        # EmoMouth output suggestion
        if "mouth" in active_modalities:
            st.markdown("##### 👄 EmoMouth 輸出建議")
            mouth_engine = sensory_engines["mouth"]
            pulse = fused.to_pulse()
            mouth_result = mouth_engine.from_pulse(pulse)
            if mouth_result.silence_applied:
                st.markdown(f"建議沉默類型：**{mouth_result.silence_applied.value}** ({mouth_result.duration_seconds}s)")
            if mouth_result.breathing_pattern:
                st.markdown(f"建議呼吸模式：**{mouth_result.breathing_pattern.value}**")
            st.markdown(f"情感語調：**{mouth_result.emotional_tone}**")


# ---------------------------------------------------------------------------
# Page: Onboarding
# ---------------------------------------------------------------------------


def _page_onboarding() -> None:
    """Step-by-step onboarding flow for audience mode selection."""
    # Initialise onboarding state if needed
    if st.session_state.onboarding_state is None:
        st.session_state.onboarding_state = OnboardingState()

    state = st.session_state.onboarding_state
    step = state.current_step

    st.markdown("## 💛 Welcome to EmoFriend!")
    st.markdown("*Your feeling companion*")

    # ---- CONSENT step ----
    if step == OnboardingStep.CONSENT:
        prompt = generate_onboarding_prompt(step)
        st.markdown(f"### 📋 {prompt}")

        st.markdown("**Before we start, let me ask your permission:**")

        cam = st.checkbox(
            "📷 Camera — Emo uses your camera to see your smile!",
            value=state.consent.camera,
            key="onboard_camera",
        )
        mic = st.checkbox(
            "🎤 Microphone — Emo uses your mic to hear your voice!",
            value=state.consent.microphone,
            key="onboard_microphone",
        )
        key = st.checkbox(
            "⌨️ Keyboard — Emo uses your keyboard when you want to type!",
            value=state.consent.keyboard,
            key="onboard_keyboard",
        )

        if st.button("Next →", key="onboard_consent_next"):
            state.consent = SensorConsent(camera=cam, microphone=mic, keyboard=key)
            advance_onboarding(state)
            st.rerun()

    # ---- MODE_SELECT step ----
    elif step == OnboardingStep.MODE_SELECT:
        prompt = generate_onboarding_prompt(step)
        st.markdown(f"### 🐝 {prompt}")

        col1, col2 = st.columns(2)
        with col1:
            if st.button(
                "🧒\nI'm a kid!",
                key="onboard_mode_kids",
            ):
                state.audience_mode = AudienceMode.KIDS
                # Ask for parent PIN for kids mode
                pin = st.session_state.get("onboard_parent_pin", "")
                if not pin:
                    pin = "1234"  # default PIN
                state.parent_pin = pin
                advance_onboarding(state, audience_mode=AudienceMode.KIDS)
                st.rerun()

        with col2:
            if st.button(
                "👴\nI'm a grown-up friend!",
                key="onboard_mode_elderly",
            ):
                state.audience_mode = AudienceMode.ELDERLY
                # Ask for family contact for elderly mode
                contact = st.session_state.get("onboard_family_contact", "")
                state.family_contact = contact
                advance_onboarding(state, audience_mode=AudienceMode.ELDERLY)
                st.rerun()

        # Mode-specific extra fields
        if state.audience_mode is None:
            # Show optional fields based on which mode they might pick
            with st.expander("🧒 Kids Mode — Parent PIN"):
                pin_val = st.text_input(
                    "Set a Parent PIN (default: 1234)",
                    value="1234",
                    key="onboard_parent_pin",
                    max_chars=6,
                )
                st.caption("A PIN is needed to access the parent dashboard in Kids mode.")

            with st.expander("👴 Elderly Mode — Family Contact"):
                contact_val = st.text_input(
                    "Family contact (phone or email)",
                    value="",
                    key="onboard_family_contact",
                )
                st.caption("A family contact helps us keep your loved ones informed.")

    # ---- NAME_INPUT step ----
    elif step == OnboardingStep.NAME_INPUT:
        mode = state.audience_mode
        prompt = generate_onboarding_prompt(step, mode)
        st.markdown(f"### ✏️ {prompt}")

        name = st.text_input(
            "Your name",
            value=state.user_name,
            key="onboard_name_input",
            placeholder="Type your name here...",
        )

        if st.button("Next →", key="onboard_name_next"):
            if not name.strip():
                st.warning("Please enter your name!")
            else:
                advance_onboarding(state, user_name=name.strip())
                st.rerun()

    # ---- FIRST_EMOTION step ----
    elif step == OnboardingStep.FIRST_EMOTION:
        mode = state.audience_mode
        prompt = generate_onboarding_prompt(step, mode, name=state.user_name)
        st.markdown(f"### 🎭 {prompt}")

        buttons = get_buttons_for_mode(mode) if mode else []
        cols = st.columns(min(len(buttons), 5))
        for idx, btn in enumerate(buttons):
            with cols[idx % len(cols)]:
                if st.button(
                    f"{btn.emoji}\n{btn.label}",
                    key=f"onboard_emotion_{btn.basic_emotion}",
                ):
                    advance_onboarding(state, first_emotion=btn.basic_emotion)
                    st.rerun()

    # ---- WELCOME step ----
    elif step == OnboardingStep.WELCOME:
        mode = state.audience_mode
        prompt = generate_onboarding_prompt(step, mode)
        st.markdown(f"### 🌟 {prompt}")

        if mode == AudienceMode.KIDS:
            st.markdown(f"🐝 **{state.user_name}**, Emo is so happy to meet you!")
            st.balloons()
        else:
            st.markdown(f"🕯️ **{state.user_name}**，Emo 會一直在這裡陪你。")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🌟 Let's Go!", key="onboard_lets_go"):
                advance_onboarding(state)
                st.session_state["audience_mode"] = state.audience_mode
                st.session_state["onboarding_state"] = state
                st.rerun()
        with col2:
            if mode == AudienceMode.ELDERLY:
                if st.button("🌟 開始", key="onboard_start_zh"):
                    advance_onboarding(state)
                    st.session_state["audience_mode"] = state.audience_mode
                    st.session_state["onboarding_state"] = state
                    st.rerun()


# ---------------------------------------------------------------------------
# Main app
# ---------------------------------------------------------------------------


def main() -> None:
    """EmoFriend 主應用入口"""
    st.set_page_config(
        page_title="EmoFriend — 情感療癒陪伴",
        page_icon="💛",
        layout="wide",
    )

    _ensure_session_state()

    # 初始化引擎
    data_dir = _get_data_dir()
    Path(data_dir).mkdir(parents=True, exist_ok=True)

    friendship_engine = init_friendship_engine(data_dir)
    persona_engine = init_persona_engine(data_dir)
    sharing_engine = init_sharing_engine()
    therapy_engine = init_therapy_engine()
    profile_manager = init_profile_manager(data_dir)

    # 初始化七竅引擎（Classic Mode 用）
    sensory_engines = init_sensory_engines()

    # ---- Audience mode routing ----
    audience_mode = st.session_state.get("audience_mode")

    # If no audience mode selected → show onboarding
    if audience_mode is None:
        _page_onboarding()
        return

    # ---- Sidebar navigation (mode-aware) ----
    with st.sidebar:
        if audience_mode == AudienceMode.KIDS:
            st.markdown("# 🐝 EmoFriend")
            st.markdown("*Your Feeling Friend*")
            st.markdown("---")
            page = st.radio(
                "導航",
                ["🏠 Home", "🎮 Play", "👨‍👩‍👧 Parent"],
                label_visibility="collapsed",
            )
        elif audience_mode == AudienceMode.ELDERLY:
            st.markdown("# 🕯️ EmoFriend")
            st.markdown("*你的情感陪伴*")
            st.markdown("---")
            page = st.radio(
                "導航",
                ["🏠 首頁", "💪 健康", "⚙️ 設定"],
                label_visibility="collapsed",
            )
        else:
            # Fallback — should not happen
            page = None

        # Mode switching button
        st.markdown("---")
        if st.button("🔄 Switch Mode", key="switch_mode_btn"):
            st.session_state["audience_mode"] = None
            st.session_state["onboarding_state"] = None
            st.rerun()

        # Classic Mode link
        st.markdown("---")
        if st.button("🔧 Classic Mode", key="classic_mode_btn"):
            st.session_state["audience_mode"] = "classic"
            st.rerun()

    # ---- Kids Mode routing ----
    if audience_mode == AudienceMode.KIDS:
        audience_engines = init_audience_engines(AudienceMode.KIDS)

        if page == "🏠 Home":
            page_kids_home(
                friendship_engine, persona_engine, sharing_engine,
                therapy_engine, profile_manager, audience_engines, data_dir,
            )
        elif page == "🎮 Play":
            page_kids_play(audience_engines, data_dir)
        elif page == "👨‍👩‍👧 Parent":
            page_kids_parent(friendship_engine, profile_manager, data_dir)

    # ---- Elderly Mode routing ----
    elif audience_mode == AudienceMode.ELDERLY:
        audience_engines = init_audience_engines(AudienceMode.ELDERLY)

        if page == "🏠 首頁":
            page_elderly_home(
                friendship_engine, persona_engine, sharing_engine,
                therapy_engine, profile_manager, audience_engines, data_dir,
            )
        elif page == "💪 健康":
            page_elderly_health(audience_engines, profile_manager, data_dir)
        elif page == "⚙️ 設定":
            page_elderly_settings(friendship_engine, profile_manager, data_dir)

    # ---- Classic Mode routing (original pages) ----
    elif audience_mode == "classic":
        with st.sidebar:
            st.markdown("# 💛 EmoFriend")
            st.markdown("*情感療癒陪伴*")
            st.markdown("---")
            page = st.radio(
                "導航",
                ["💬 聊天", "📊 情感儀表板", "🌿 疗癒工具", "🔮 七竅感官", "⚙️ 設定"],
                label_visibility="collapsed",
            )

        if page == "💬 聊天":
            _page_chat(
                friendship_engine, persona_engine, sharing_engine,
                therapy_engine, profile_manager,
            )
        elif page == "📊 情感儀表板":
            _page_dashboard(friendship_engine, profile_manager)
        elif page == "🌿 疗癒工具":
            _page_healing(
                therapy_engine, sharing_engine, profile_manager, friendship_engine,
            )
        elif page == "🔮 七竅感官":
            _page_sensory(sensory_engines)
        elif page == "⚙️ 設定":
            _page_settings(friendship_engine, persona_engine, profile_manager)


if __name__ == "__main__":
    main()
