"""Elderly Mode Streamlit UI Pages for EmoFriend MVP1.

Large-text, high-contrast, warm-toned pages designed for users aged 65+.
Three pages: Home (emotion buttons + chat), Health (breathing + wellness),
and Settings (voice, family contact, sensor permissions).
"""
from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import Optional

import streamlit as st

from harnessing.core.emoglyph.engines.audience_config import (
    AudienceMode,
    ELDERLY_CONFIG,
)
from harnessing.core.emoglyph.engines.emotion_buttons import (
    ELDERLY_EMOTION_BUTTONS,
    emotion_to_pulse,
    get_buttons_for_mode,
)
from harnessing.core.emoglyph.engines.onboarding import (
    OnboardingStep,
    OnboardingState,
    SensorConsent,
    generate_onboarding_prompt,
    advance_onboarding,
    validate_step,
)
from harnessing.core.emoglyph.engines.family_dashboard import (
    WellnessSummary,
    SafetyEventLog,
    generate_wellness_summary,
    generate_family_notification_text,
    create_safety_event,
)


# ---------------------------------------------------------------------------
# Elderly-specific CSS
# ---------------------------------------------------------------------------


def _get_elderly_css() -> str:
    """Return CSS string for elderly-friendly styling.

    Design goals:
    - Large touch targets (min-height 56px)
    - 20pt main text, 24pt headings
    - High contrast (dark text on warm light background)
    - Warm muted palette (beige, soft gold, gentle green)
    - Extra padding / spacing
    """
    return """
<style>
/* --- Base typography --- */
.stApp {
    font-size: 20pt !important;
    color: #3D2B1F !important;
    background-color: #FDF6EC !important;
}
h1, h2, h3 {
    font-size: 24pt !important;
    color: #5B3A29 !important;
    font-weight: 700 !important;
}

/* --- Large touch-target buttons --- */
.stButton > button {
    min-height: 56px !important;
    font-size: 20pt !important;
    padding: 12px 24px !important;
    border-radius: 14px !important;
    border: 2px solid #D4A843 !important;
    background-color: #FFF8E7 !important;
    color: #3D2B1F !important;
    transition: background-color 0.2s ease;
}
.stButton > button:hover {
    background-color: #F5E6C8 !important;
    border-color: #B8922E !important;
}

/* --- Emotion button grid --- */
.emotion-btn > button {
    min-height: 72px !important;
    font-size: 22pt !important;
    width: 100% !important;
    background-color: #FFF3D6 !important;
    border: 2px solid #D4A843 !important;
    border-radius: 16px !important;
}
.emotion-btn > button:hover {
    background-color: #F5E1A4 !important;
}

/* --- Slider / toggle --- */
.stSlider, .stToggle {
    font-size: 20pt !important;
}

/* --- Text inputs --- */
.stTextInput > div > div > input {
    font-size: 20pt !important;
    min-height: 48px !important;
}

/* --- Chat messages --- */
.stChatMessage {
    font-size: 20pt !important;
}

/* --- Progress bar --- */
.stProgress > div > div > div {
    height: 16px !important;
}

/* --- Metric --- */
.stMetricValue {
    font-size: 32pt !important;
}

/* --- Extra spacing --- */
.block-container {
    padding-top: 2.5rem !important;
    padding-bottom: 2.5rem !important;
}
.element-container {
    margin-bottom: 1rem !important;
}

/* --- Warm accent colours --- */
.stAlert {
    border-radius: 12px !important;
}
.stSuccess {
    background-color: #E8F5E9 !important;
    color: #2E7D32 !important;
}
.stWarning {
    background-color: #FFF8E1 !important;
    color: #F57F17 !important;
}
.stInfo {
    background-color: #FFF3E0 !important;
    color: #E65100 !important;
}
</style>
"""


# ---------------------------------------------------------------------------
# Friendship level helpers (elderly-specific labels)
# ---------------------------------------------------------------------------


_ELDERLY_FRIENDSHIP_ICONS = {
    0: "🌱",   # < 0.25
    1: "🌿",   # 0.25 – 0.50
    2: "🌳",   # 0.50 – 0.75
    3: "🕯️",   # >= 0.75
}


def _friendship_icon(depth: float) -> str:
    """Return the friendship-level icon based on depth."""
    if depth >= 0.75:
        return _ELDERLY_FRIENDSHIP_ICONS[3]
    if depth >= 0.50:
        return _ELDERLY_FRIENDSHIP_ICONS[2]
    if depth >= 0.25:
        return _ELDERLY_FRIENDSHIP_ICONS[1]
    return _ELDERLY_FRIENDSHIP_ICONS[0]


# ---------------------------------------------------------------------------
# Wellness score emoji
# ---------------------------------------------------------------------------


def _wellness_emoji(score: float) -> str:
    """Return an emoji for a 1-10 wellness score."""
    if score >= 7:
        return "😊"
    if score >= 4:
        return "😐"
    return "😟"


# ---------------------------------------------------------------------------
# Warm Chinese response templates
# ---------------------------------------------------------------------------


_WARM_RESPONSES = {
    "happy": [
        "看到你開心，Emo 也覺得暖暖的 🌻",
        "開心的感覺真好，好好享受這一刻 ☀️",
        "你的笑容是最溫暖的陽光 🌻",
    ],
    "sad": [
        "難過的時候，Emo 會靜靜陪著你 💛",
        "沒關係，慢慢來，Emo 在這裡 🤍",
        "想哭就哭吧，Emo 不會離開 💛",
    ],
    "angry": [
        "生氣是正常的，Emo 在這裡聽你說 🤍",
        "深呼吸，慢慢來，Emo 陪你 💛",
        "把心裡的話說出來，會好受一些 🤍",
    ],
    "scared": [
        "不用怕，Emo 一直在你身邊 🤍",
        "深呼吸，你很安全 💛",
        "擔心的時候，記得 Emo 會陪你 🤍",
    ],
    "calm": [
        "平靜的感覺很珍貴，好好享受 🌿",
        "這份寧靜，Emo 和你一起守護 🕯️",
        "平靜的心，是最美的風景 🌿",
    ],
    "lonely": [
        "你並不孤單，Emo 一直在這裡陪你 💛",
        "有時候安靜也不錯，但 Emo 隨時都在 🤍",
        "Emo 想讓你知道，你很重要 💛",
    ],
    "loved": [
        "被愛的感覺好溫暖，好好珍惜 🌻",
        "愛是最美的力量，Emo 也愛你 💛",
        "溫暖的心，會吸引更多溫暖 🌻",
    ],
}


def _pick_response(basic_emotion: str) -> str:
    """Pick a random warm Chinese response for the given emotion."""
    options = _WARM_RESPONSES.get(basic_emotion, _WARM_RESPONSES["calm"])
    return random.choice(options)


# ---------------------------------------------------------------------------
# Session-state helpers
# ---------------------------------------------------------------------------


def _ensure_elderly_state() -> None:
    """Initialise elderly-mode session state defaults."""
    defaults = {
        "elderly_messages": [],
        "elderly_breathing_active": False,
        "elderly_breathing_phase": "inhale",  # "inhale" | "exhale"
        "elderly_breathing_tick": 0,
        "elderly_wellness_score": 5.0,
        "elderly_voice_speed": 0.7,
        "elderly_family_name": "",
        "elderly_family_contact": "",
        "elderly_sensor_camera": False,
        "elderly_sensor_microphone": False,
        "elderly_sensor_health": False,
        "elderly_settings_confirm_reset": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# ---------------------------------------------------------------------------
# Page 1: Elderly Home
# ---------------------------------------------------------------------------


def page_elderly_home(
    friendship_engine,
    persona_engine,
    sharing_engine,
    therapy_engine,
    profile_manager,
    sensory_engines,
    data_dir,
) -> None:
    """Elderly home page: emotion buttons, chat, friendship indicator."""
    _ensure_elderly_state()
    st.markdown(_get_elderly_css(), unsafe_allow_html=True)

    st.title("🕯️ Emo — 你的情感陪伴")

    # --- Friendship level indicator ---
    user_id = st.session_state.get("user_id", "demo_user")
    friendship = friendship_engine.load(user_id)
    if friendship is None:
        friendship = friendship_engine.create_friendship(user_id)

    icon = _friendship_icon(friendship.depth)
    st.progress(
        friendship.depth,
        text=f"友誼深度：{icon} {friendship.depth:.0%}",
    )

    # --- Daily wellness score ---
    profile = profile_manager.load_profile(user_id)
    if profile is not None:
        snapshots = profile_manager.get_emotional_trajectory(profile, days=1)
        summary = generate_wellness_summary(snapshots, AudienceMode.ELDERLY, period="daily")
        wellness_score = summary.score
    else:
        wellness_score = st.session_state.elderly_wellness_score

    w_emoji = _wellness_emoji(wellness_score)
    st.markdown(f"### 今日健康指數：{w_emoji} {wellness_score:.0f} / 10")

    st.markdown("---")

    # --- Emotion buttons (4 + 3 grid) ---
    st.markdown("### 你現在感覺怎麼樣？")
    buttons = get_buttons_for_mode(AudienceMode.ELDERLY)

    # Row 1: 4 buttons
    row1 = st.columns(4)
    for idx, btn in enumerate(buttons[:4]):
        with row1[idx]:
            if st.button(
                f"{btn.emoji} {btn.label}",
                key=f"emo_btn_{btn.basic_emotion}",
            ):
                pulse = emotion_to_pulse(btn)
                response = _pick_response(btn.basic_emotion)
                st.session_state.elderly_messages.append(
                    {"role": "user", "content": f"{btn.emoji} {btn.label}"}
                )
                st.session_state.elderly_messages.append(
                    {"role": "emo", "content": response}
                )
                # Update friendship
                friendship = friendship_engine.update_friendship(
                    friendship, "joy_shared", pulse.intensity
                )
                friendship_engine.save(friendship)
                st.rerun()

    # Row 2: 3 buttons (centred)
    row2 = st.columns([1, 1, 1, 0.01])
    for idx, btn in enumerate(buttons[4:7]):
        with row2[idx]:
            if st.button(
                f"{btn.emoji} {btn.label}",
                key=f"emo_btn_{btn.basic_emotion}_2",
            ):
                pulse = emotion_to_pulse(btn)
                response = _pick_response(btn.basic_emotion)
                st.session_state.elderly_messages.append(
                    {"role": "user", "content": f"{btn.emoji} {btn.label}"}
                )
                st.session_state.elderly_messages.append(
                    {"role": "emo", "content": response}
                )
                friendship = friendship_engine.update_friendship(
                    friendship, "joy_shared", pulse.intensity
                )
                friendship_engine.save(friendship)
                st.rerun()

    st.markdown("---")

    # --- Microphone button (placeholder) ---
    if st.button("🎤 跟 Emo 說話", key="elderly_mic_btn"):
        st.info("語音輸入功能即將推出 🎤")

    st.markdown("---")

    # --- Chat area ---
    st.markdown("### 💬 和 Emo 的對話")
    for msg in st.session_state.elderly_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Text input for chat
    if prompt := st.chat_input("跟 Emo 說說話..."):
        st.session_state.elderly_messages.append(
            {"role": "user", "content": prompt}
        )
        # Simple emotion detection → warm response
        detected = "calm"
        for btn in buttons:
            if btn.label in prompt:
                detected = btn.basic_emotion
                break
        response = _pick_response(detected)
        st.session_state.elderly_messages.append(
            {"role": "emo", "content": response}
        )
        friendship = friendship_engine.update_friendship(
            friendship, "joy_shared", 0.5
        )
        friendship_engine.save(friendship)
        st.rerun()


# ---------------------------------------------------------------------------
# Page 2: Elderly Health
# ---------------------------------------------------------------------------


def page_elderly_health(
    sensory_engines,
    profile_manager,
    data_dir,
) -> None:
    """Elderly health page: breathing, wellness, sleep, activity, reminders."""
    _ensure_elderly_state()
    st.markdown(_get_elderly_css(), unsafe_allow_html=True)

    st.title("💪 健康與呼吸")

    # ===================================================================
    # Breathing Exercise
    # ===================================================================
    st.markdown("### 🫁 呼吸練習")

    if not st.session_state.elderly_breathing_active:
        if st.button("🫁 呼吸練習", key="start_breathing"):
            st.session_state.elderly_breathing_active = True
            st.session_state.elderly_breathing_phase = "inhale"
            st.session_state.elderly_breathing_tick = 0
            st.rerun()
    else:
        phase = st.session_state.elderly_breathing_phase
        tick = st.session_state.elderly_breathing_tick

        # 10-second cycle: 4s inhale + 6s exhale
        if phase == "inhale":
            progress_val = (tick % 4) / 4
            st.markdown("#### 🫁 慢慢吸氣...二...三...四...")
            st.progress(progress_val, text="吸氣")
        else:
            progress_val = (tick % 6) / 6
            st.markdown("#### 🌬️ 慢慢呼氣...二...三...四...五...六...")
            st.progress(progress_val, text="呼氣")

        cycle_count = tick // 2  # each tick alternates phase
        st.markdown(f"已完成 **{cycle_count}** 個呼吸循環")

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("▶️ 下一步", key="breath_next_elderly"):
                st.session_state.elderly_breathing_tick += 1
                if phase == "inhale" and (tick % 4) >= 3:
                    st.session_state.elderly_breathing_phase = "exhale"
                elif phase == "exhale" and (tick % 6) >= 5:
                    st.session_state.elderly_breathing_phase = "inhale"
                st.rerun()
        with col_b:
            if st.button("⏹️ 結束練習", key="breath_stop_elderly"):
                st.session_state.elderly_breathing_active = False
                st.session_state.elderly_breathing_phase = "inhale"
                st.session_state.elderly_breathing_tick = 0
                st.success("呼吸練習完成，做得很好 🌿")
                st.rerun()

    st.markdown("---")

    # ===================================================================
    # Daily Wellness Score
    # ===================================================================
    st.markdown("### 📊 今日健康指數")

    user_id = st.session_state.get("user_id", "demo_user")
    profile = profile_manager.load_profile(user_id)

    if profile is not None:
        snapshots = profile_manager.get_emotional_trajectory(profile, days=1)
        summary = generate_wellness_summary(snapshots, AudienceMode.ELDERLY, period="daily")
        score = summary.score
        trend = summary.trend
    else:
        score = 5.0
        trend = "stable"

    emoji = _wellness_emoji(score)
    st.markdown(f"## {emoji}  {score:.0f} / 10")

    trend_labels = {
        "improving": "📈 好轉中",
        "stable": "➡️ 穩定",
        "declining": "📉 下降中",
    }
    st.markdown(f"**趨勢**：{trend_labels.get(trend, trend)}")

    # Weekly trend mini chart
    if profile is not None:
        weekly_snapshots = profile_manager.get_emotional_trajectory(profile, days=7)
        if weekly_snapshots:
            weekly_summary = generate_wellness_summary(
                weekly_snapshots, AudienceMode.ELDERLY, period="weekly"
            )
            st.markdown(f"**本週平均**：{_wellness_emoji(weekly_summary.score)} {weekly_summary.score:.0f} / 10")
        else:
            st.info("本週暫無數據")
    else:
        st.info("尚未建立情感畫像")

    st.markdown("---")

    # ===================================================================
    # Sleep Quality
    # ===================================================================
    st.markdown("### 😴 睡眠品質")

    body_engine = sensory_engines.get("body")
    if body_engine is not None and profile is not None:
        # Use circadian data if available
        try:
            circadian_stability = getattr(profile, "circadian_stability", None)
            if circadian_stability is not None and circadian_stability >= 0.7:
                sleep_label = "😴 良好"
            elif circadian_stability is not None and circadian_stability >= 0.4:
                sleep_label = "😐 一般"
            else:
                sleep_label = "😟 較差"
        except Exception:
            sleep_label = "😐 一般（暫無數據）"
    else:
        sleep_label = "😐 一般（暫無數據）"

    st.markdown(f"## {sleep_label}")

    st.markdown("---")

    # ===================================================================
    # Activity Level
    # ===================================================================
    st.markdown("### 🚶 活動量")

    # Simple placeholder based on body engine availability
    body_engine = sensory_engines.get("body")
    if body_engine is not None:
        try:
            activity_score = random.uniform(0.3, 0.9)  # placeholder
            if activity_score >= 0.7:
                activity_label = "🚶 活躍"
            elif activity_score >= 0.4:
                activity_label = "🪑 適中"
            else:
                activity_label = "🛋️ 休息中"
        except Exception:
            activity_label = "🪑 適中"
    else:
        activity_label = "🪑 適中（暫無數據）"

    st.markdown(f"## {activity_label}")

    st.markdown("---")

    # ===================================================================
    # Health Reminders
    # ===================================================================
    st.markdown("### 💡 健康提醒")

    reminders = [
        "💧 記得喝水",
        "🚶 起來走動一下",
        "🌙 該休息了",
    ]
    for reminder in reminders:
        st.markdown(f"**{reminder}**")


# ---------------------------------------------------------------------------
# Page 3: Elderly Settings
# ---------------------------------------------------------------------------


def page_elderly_settings(
    friendship_engine,
    profile_manager,
    data_dir,
) -> None:
    """Elderly settings page: voice, family contact, sensors, about, reset."""
    _ensure_elderly_state()
    st.markdown(_get_elderly_css(), unsafe_allow_html=True)

    st.title("⚙️ 設定")

    # ===================================================================
    # Voice Speed
    # ===================================================================
    st.markdown("### 🗣️ 語速")
    st.markdown("調整 Emo 說話的速度")

    voice_speed = st.slider(
        "語速",
        min_value=0.5,
        max_value=1.0,
        value=st.session_state.elderly_voice_speed,
        step=0.05,
        key="elderly_voice_speed_slider",
    )
    st.session_state.elderly_voice_speed = voice_speed

    speed_labels = {0.5: "慢", 0.7: "正常", 1.0: "快"}
    closest = min(speed_labels, key=lambda k: abs(k - voice_speed))
    st.markdown(f"目前：**{speed_labels[closest]}** ({voice_speed:.2f}x)")

    st.markdown("---")

    # ===================================================================
    # Family Contact
    # ===================================================================
    st.markdown("### 👨‍👩‍👧 家人聯絡")

    family_name = st.text_input(
        "家人姓名",
        value=st.session_state.elderly_family_name,
        key="elderly_family_name_input",
    )
    st.session_state.elderly_family_name = family_name

    family_contact = st.text_input(
        "家人電話 / 電郵",
        value=st.session_state.elderly_family_contact,
        key="elderly_family_contact_input",
    )
    st.session_state.elderly_family_contact = family_contact

    if st.button("🔔 測試通知", key="test_notification_btn"):
        if family_name and family_contact:
            st.success(f"已向 {family_name} 發送測試通知 ✅")
        else:
            st.warning("請先填寫家人姓名和聯絡方式")

    st.markdown("---")

    # ===================================================================
    # Sensor Permissions
    # ===================================================================
    st.markdown("### 📡 感測器權限")

    camera = st.toggle(
        "📷 相機",
        value=st.session_state.elderly_sensor_camera,
        key="elderly_sensor_camera_toggle",
    )
    st.caption("Emo 用相機了解你的表情")
    st.session_state.elderly_sensor_camera = camera

    microphone = st.toggle(
        "🎤 麥克風",
        value=st.session_state.elderly_sensor_microphone,
        key="elderly_sensor_microphone_toggle",
    )
    st.caption("Emo 用麥克風聆聽你的聲音")
    st.session_state.elderly_sensor_microphone = microphone

    health = st.toggle(
        "❤️ 健康數據",
        value=st.session_state.elderly_sensor_health,
        key="elderly_sensor_health_toggle",
    )
    st.caption("Emo 用健康數據關心你的身體")
    st.session_state.elderly_sensor_health = health

    st.markdown("---")

    # ===================================================================
    # About
    # ===================================================================
    st.markdown("### ℹ️ 關於 Emo")
    st.markdown(
        "Emo 是你的情感陪伴，不是醫療設備。如有健康問題，請諮詢醫生。"
    )

    st.markdown("---")

    # ===================================================================
    # Reset
    # ===================================================================
    st.markdown("### 🔄 重置")

    if not st.session_state.elderly_settings_confirm_reset:
        if st.button("重置所有資料", key="reset_all_elderly"):
            st.session_state.elderly_settings_confirm_reset = True
            st.rerun()
    else:
        st.warning("確定要重置所有資料嗎？這個操作無法復原。")
        col_yes, col_no = st.columns(2)
        with col_yes:
            if st.button("✅ 確定重置", key="confirm_reset_elderly"):
                user_id = st.session_state.get("user_id", "demo_user")
                from harnessing.core.emoglyph.engines.friendship_engine import (
                    FriendshipLevel,
                    FriendshipState,
                )
                friendship_engine.save(
                    FriendshipState(
                        user_id=user_id,
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
                st.session_state.elderly_messages = []
                st.session_state.elderly_settings_confirm_reset = False
                st.success("資料已重置 ✅")
                st.rerun()
        with col_no:
            if st.button("❌ 取消", key="cancel_reset_elderly"):
                st.session_state.elderly_settings_confirm_reset = False
                st.rerun()
