"""Kids Mode Streamlit UI Pages for EmoFriend MVP1.

Three kid-friendly pages:
- Home: emotion buttons, chat with Emo, friendship progress
- Play: breathing bubble game, badges, growth chart
- Parent: PIN-protected dashboard for parents
"""
from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import List

import streamlit as st

from harnessing.core.emoglyph.engines.audience_config import AudienceMode, KIDS_CONFIG
from harnessing.core.emoglyph.engines.emotion_buttons import (
    KIDS_EMOTION_BUTTONS,
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
# Kids-specific CSS
# ---------------------------------------------------------------------------

def _get_kids_css() -> str:
    """Return CSS string for kids-specific styling."""
    return """
    <style>
    /* Big touch-friendly buttons */
    .stButton > button {
        min-height: 48px !important;
        font-size: 18pt !important;
        border-radius: 16px !important;
        padding: 12px 24px !important;
    }

    /* Main text size */
    .stMarkdown, .stText {
        font-size: 18pt !important;
    }

    /* Warm color scheme */
    .stApp {
        background-color: #FFF8E7 !important;
    }

    /* Rounded corners on all elements */
    .stContainer, .stExpander, .stDataFrame, div[data-testid="stForm"] {
        border-radius: 16px !important;
    }

    /* Large emoji sizes in emotion buttons */
    .emotion-btn {
        font-size: 36px !important;
        line-height: 1.4 !important;
    }

    /* Chat messages */
    .stChatMessage {
        border-radius: 16px !important;
    }

    /* Progress bar warm colors */
    .stProgress > div > div > div {
        background: linear-gradient(90deg, #FFD700, #FFA500, #90EE90) !important;
    }

    /* Sidebar warm tint */
    [data-testid="stSidebar"] {
        background-color: #FFF3CD !important;
    }

    /* Metric cards */
    [data-testid="stMetricValue"] {
        font-size: 24pt !important;
        color: #FF8C00 !important;
    }
    </style>
    """


# ---------------------------------------------------------------------------
# Encouragement helpers (no LLM needed)
# ---------------------------------------------------------------------------

_KIDS_ENCOURAGEMENTS = {
    "happy": [
        "That's wonderful! I love your smile! 🌟",
        "Yay! Happy feelings are the best! 🎉",
        "Your happiness makes me happy too! 💛",
    ],
    "sad": [
        "It's okay to feel sad. I'm right here with you. 💛",
        "Sad feelings come and go like clouds. I'll wait with you. 🌈",
        "Even on rainy days, the sun is still there. I believe in you! ☀️",
    ],
    "angry": [
        "I hear you! Take a deep breath with me. 🌬️",
        "Feeling angry is okay. Let's blow some bubbles together! 🫧",
        "When we're mad, breathing helps. You're so brave! 💪",
    ],
    "scared": [
        "You're safe with me. I'm right here! 🤗",
        "Being brave doesn't mean no scared — it means you keep going! 🌟",
        "Let's take a breath together. You're not alone. 💛",
    ],
    "loved": [
        "Aww, that makes my heart glow! 🥰",
        "Love is the best feeling! You deserve all the love! 💖",
        "I love being your friend! You're amazing! ✨",
    ],
}

_EMO_CHAT_RESPONSES = {
    "happy": "That sounds great! Tell me more about what made you happy! 🌟",
    "sad": "I'm here for you. Would you like to tell me more? 💛",
    "angry": "I understand. Sometimes things feel unfair. I'm listening. 🤗",
    "scared": "It's okay to feel scared. You're safe here with me. 🌈",
    "loved": "That's so lovely! Feeling loved is wonderful! 💖",
    "default": "I'm listening! Tell me more! 🐝",
}


def _get_encouragement(basic_emotion: str) -> str:
    """Pick a random encouragement for the given basic emotion."""
    options = _KIDS_ENCOURAGEMENTS.get(basic_emotion, _KIDS_ENCOURAGEMENTS["happy"])
    return random.choice(options)


def _get_emo_chat_response(basic_emotion: str) -> str:
    """Pick a simple chat response from Emo."""
    return _EMO_CHAT_RESPONSES.get(basic_emotion, _EMO_CHAT_RESPONSES["default"])


# ---------------------------------------------------------------------------
# Friendship level helpers
# ---------------------------------------------------------------------------

def _friendship_emoji(depth: float) -> str:
    """Return emoji for friendship level based on depth."""
    if depth < 0.25:
        return "🌱"
    elif depth < 0.5:
        return "🌿"
    elif depth < 0.75:
        return "🌳"
    else:
        return "🌟"


def _friendship_label(depth: float) -> str:
    """Return label for friendship level."""
    if depth < 0.25:
        return "New Friend"
    elif depth < 0.5:
        return "Good Friend"
    elif depth < 0.75:
        return "Best Friend"
    else:
        return "Emo Best Friend!"


# ---------------------------------------------------------------------------
# Badge helpers
# ---------------------------------------------------------------------------

_BADGE_DEFS = [
    (1, "🌱", "First Chat"),
    (5, "🌿", "5 Chats"),
    (10, "🌳", "10 Chats"),
    (20, "🌟", "Emo Best Friend"),
]


def _earned_badges(chat_count: int) -> List[tuple]:
    """Return list of (emoji, label, earned) for all badges."""
    result = []
    for threshold, emoji, label in _BADGE_DEFS:
        earned = chat_count >= threshold
        result.append((emoji, label, earned))
    return result


# ---------------------------------------------------------------------------
# Page: Kids Home
# ---------------------------------------------------------------------------

def page_kids_home(
    friendship_engine,
    persona_engine,
    sharing_engine,
    therapy_engine,
    profile_manager,
    sensory_engines,
    data_dir,
) -> None:
    """Kids home page — emotion buttons, chat, friendship progress."""
    st.markdown(_get_kids_css(), unsafe_allow_html=True)

    st.title("🐝 Emo — Your Feeling Friend!")

    # --- Session state init ---
    if "kids_chat_count" not in st.session_state:
        st.session_state.kids_chat_count = 0
    if "kids_messages" not in st.session_state:
        st.session_state.kids_messages = []

    # --- Emotion buttons row ---
    st.subheader("How are you feeling?")

    cols = st.columns(len(KIDS_EMOTION_BUTTONS))
    for idx, btn in enumerate(KIDS_EMOTION_BUTTONS):
        with cols[idx]:
            if st.button(
                f"{btn.emoji}\n{btn.label}",
                key=f"emo_btn_{btn.basic_emotion}",
            ):
                # Convert to Pulse
                pulse = emotion_to_pulse(btn)

                # Emo encouragement
                encouragement = _get_encouragement(btn.basic_emotion)
                st.session_state.kids_messages.append({
                    "role": "user",
                    "content": f"{btn.emoji} I feel {btn.label}!",
                })
                st.session_state.kids_messages.append({
                    "role": "emo",
                    "content": encouragement,
                })
                st.session_state.kids_chat_count += 1

                # Try to update friendship if engine available
                try:
                    user_id = st.session_state.get("user_id", "demo_user")
                    friendship = friendship_engine.load(user_id)
                    if friendship is None:
                        friendship = friendship_engine.create_friendship(user_id)
                    friendship = friendship_engine.update_friendship(
                        friendship, "joy_shared", pulse.intensity,
                    )
                    friendship_engine.save(friendship)
                except Exception:
                    pass

                st.rerun()

    st.markdown("---")

    # --- Microphone button (placeholder) ---
    st.markdown("### 🎤 Talk to Emo!")
    st.info("Voice input coming soon! For now, type below to chat with Emo. 🐝")

    # --- Chat area ---
    st.markdown("### Chat with Emo")

    # Display chat history
    for msg in st.session_state.kids_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Text input
    if prompt := st.chat_input("Type to Emo..."):
        st.session_state.kids_messages.append({
            "role": "user",
            "content": prompt,
        })

        # Simple keyword-based emotion detection for kids
        basic_emotion = "default"
        prompt_lower = prompt.lower()
        _KEYWORD_MAP = {
            "happy": ["happy", "glad", "fun", "yay", "haha", "smile", "laugh"],
            "sad": ["sad", "cry", "miss", "lonely", "down", "unhappy"],
            "angry": ["angry", "mad", "hate", "upset", "frustrated", "annoyed"],
            "scared": ["scared", "afraid", "worry", "nervous", "fear", "anxious"],
            "loved": ["love", "hug", "cared", "warm", "special", "thankful"],
        }
        for emotion, keywords in _KEYWORD_MAP.items():
            if any(kw in prompt_lower for kw in keywords):
                basic_emotion = emotion
                break

        emo_response = _get_emo_chat_response(basic_emotion)
        st.session_state.kids_messages.append({
            "role": "emo",
            "content": emo_response,
        })
        st.session_state.kids_chat_count += 1
        st.rerun()

    st.markdown("---")

    # --- Friendship level progress bar ---
    st.subheader("Our Friendship")
    try:
        user_id = st.session_state.get("user_id", "demo_user")
        friendship = friendship_engine.load(user_id)
        depth = friendship.depth if friendship else 0.0
    except Exception:
        depth = 0.0

    emoji = _friendship_emoji(depth)
    label = _friendship_label(depth)
    st.progress(depth, text=f"{emoji} {label} — {depth:.0%}")


# ---------------------------------------------------------------------------
# Page: Kids Play
# ---------------------------------------------------------------------------

def page_kids_play(sensory_engines, data_dir) -> None:
    """Kids play page — breathing game, badges, growth chart."""
    st.markdown(_get_kids_css(), unsafe_allow_html=True)

    st.title("🎮 Play with Emo!")

    if "kids_chat_count" not in st.session_state:
        st.session_state.kids_chat_count = 0
    if "bubble_active" not in st.session_state:
        st.session_state.bubble_active = False
    if "bubble_phase" not in st.session_state:
        st.session_state.bubble_phase = "idle"  # idle, inhale, exhale
    if "kids_emotion_log" not in st.session_state:
        st.session_state.kids_emotion_log = {}

    # --- Breathing Bubble Game ---
    st.subheader("🫧 Breathing Bubble Game")

    if not st.session_state.bubble_active:
        if st.button("🫧 Blow Bubbles!", key="start_bubble"):
            st.session_state.bubble_active = True
            st.session_state.bubble_phase = "inhale"
            st.rerun()
    else:
        phase = st.session_state.bubble_phase

        if phase == "inhale":
            st.markdown("### 🫧 Breathe in... (bubble grows)")
            # Visual breathing indicator
            inhale_placeholder = st.empty()
            for step in range(1, 6):
                bubble_size = step * 20
                inhale_placeholder.progress(
                    step / 5,
                    text="🫧 " + "●" * step + "○" * (5 - step),
                )

            st.markdown("### 💥 ...and blow out! (bubble pops!)")
            if st.button("💥 Pop!", key="pop_bubble"):
                st.session_state.bubble_phase = "exhale"
                st.rerun()

        elif phase == "exhale":
            st.markdown("### 💥 POP! Great job! 🎉")
            st.balloons()
            st.markdown("You did awesome! Want to blow more bubbles?")
            if st.button("🫧 Again!", key="again_bubble"):
                st.session_state.bubble_phase = "inhale"
                st.rerun()
            if st.button("⏹️ Stop", key="stop_bubble"):
                st.session_state.bubble_active = False
                st.session_state.bubble_phase = "idle"
                st.rerun()

    st.markdown("---")

    # --- Friendship Badges ---
    st.subheader("🏅 Friendship Badges")

    chat_count = st.session_state.kids_chat_count
    badges = _earned_badges(chat_count)

    badge_cols = st.columns(len(badges))
    for idx, (emoji, label, earned) in enumerate(badges):
        with badge_cols[idx]:
            if earned:
                st.markdown(f"### {emoji}")
                st.markdown(f"**{label}**")
            else:
                st.markdown(f"### 🔒")
                st.markdown(f"*{label}*")

    st.caption(f"You've chatted with Emo {chat_count} time{'s' if chat_count != 1 else ''}!")

    st.markdown("---")

    # --- Emotional Growth Chart ---
    st.subheader("📊 Emotions This Week")

    # Build sample data from session state emotion log
    emotion_log = st.session_state.kids_emotion_log
    if not emotion_log:
        # Seed with some sample data for demo
        emotion_log = {
            "😊 Happy": random.randint(1, 5),
            "😢 Sad": random.randint(0, 3),
            "😠 Angry": random.randint(0, 2),
            "😨 Scared": random.randint(0, 2),
            "🥰 Loved": random.randint(1, 4),
        }
        st.session_state.kids_emotion_log = emotion_log

    import pandas as pd
    chart_df = pd.DataFrame(
        list(emotion_log.items()),
        columns=["Emotion", "Count"],
    )
    st.bar_chart(chart_df, x="Emotion", y="Count")


# ---------------------------------------------------------------------------
# Page: Kids Parent Dashboard
# ---------------------------------------------------------------------------

_DEFAULT_PIN = "1234"


def page_kids_parent(friendship_engine, profile_manager, data_dir) -> None:
    """PIN-protected parent dashboard with wellness info and settings."""
    st.markdown(_get_kids_css(), unsafe_allow_html=True)

    st.title("👨‍👩‍👧 Parent Dashboard")

    # --- PIN entry ---
    if "parent_authenticated" not in st.session_state:
        st.session_state.parent_authenticated = False

    if not st.session_state.parent_authenticated:
        st.markdown("### 🔒 Enter Parent PIN")
        pin = st.text_input("PIN", type="password", key="parent_pin_input")
        if st.button("Unlock", key="unlock_dashboard"):
            if pin == _DEFAULT_PIN:
                st.session_state.parent_authenticated = True
                st.rerun()
            else:
                st.error("Incorrect PIN. Please try again.")
        st.info("Default PIN: 1234 (change this in production!)")
        return

    # --- Logout button ---
    if st.button("🔓 Lock Dashboard", key="lock_dashboard"):
        st.session_state.parent_authenticated = False
        st.rerun()

    st.markdown("---")

    # --- Dashboard content ---
    st.subheader("📊 Weekly Emotion Trend")

    # Sample weekly data for demo
    import pandas as pd
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    wellness_scores = [round(random.uniform(5.0, 9.0), 1) for _ in days]
    trend_df = pd.DataFrame({"Day": days, "Wellness Score": wellness_scores})
    st.line_chart(trend_df, x="Day", y="Wellness Score")

    st.markdown("---")

    # --- Time spent with Emo ---
    st.subheader("⏱️ Time with Emo")
    chat_count = st.session_state.get("kids_chat_count", 0)
    estimated_minutes = chat_count * 2  # rough estimate
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Chats This Week", chat_count)
    with col2:
        st.metric("Est. Time (min)", estimated_minutes)

    st.markdown("---")

    # --- Safety events log ---
    st.subheader("🛡️ Safety Events")

    safety_events = st.session_state.get("kids_safety_events", [])
    if not safety_events:
        # Demo data
        safety_events = [
            create_safety_event(
                event_type="distress_detected",
                severity="LOW",
                description="Child showed signs of frustration during play",
                action_taken="Emo offered breathing exercise",
            ),
        ]
        st.session_state.kids_safety_events = safety_events

    if safety_events:
        for evt in safety_events:
            severity_icon = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🟠", "CRITICAL": "🔴"}
            icon = severity_icon.get(evt.severity, "⚪")
            st.markdown(
                f"{icon} **{evt.event_type}** — {evt.description}  \n"
                f"*Action: {evt.action_taken}* | {evt.timestamp.strftime('%Y-%m-%d %H:%M')}"
            )
    else:
        st.success("No safety events recorded. All good! 🟢")

    st.markdown("---")

    # --- Friendship growth summary ---
    st.subheader("💛 Friendship Growth")
    try:
        user_id = st.session_state.get("user_id", "demo_user")
        friendship = friendship_engine.load(user_id)
        if friendship:
            emoji = _friendship_emoji(friendship.depth)
            label = _friendship_label(friendship.depth)
            st.markdown(f"**Level**: {emoji} {label}")
            st.markdown(f"**Depth**: {friendship.depth:.0%}")
            st.markdown(f"**Trust**: {friendship.trust:.0%}")
            st.markdown(f"**Interactions**: {friendship.interaction_count}")
        else:
            st.info("No friendship data yet. Start chatting with Emo!")
    except Exception:
        st.info("Friendship data will appear after your child chats with Emo.")

    st.markdown("---")

    # --- Recommended conversation starters ---
    st.subheader("💬 Conversation Starters")
    starters = [
        "Ask about their day",
        "What made them smile today?",
        "Is anything worrying them?",
    ]
    for starter in starters:
        st.markdown(f"- {starter}")

    st.markdown("---")

    # --- Settings ---
    st.subheader("⚙️ Settings")

    # Sensor permissions
    st.markdown("##### Sensor Permissions")
    consent = st.session_state.get("kids_sensor_consent", SensorConsent())

    cam = st.checkbox("📷 Camera", value=consent.camera, key="parent_cam")
    mic = st.checkbox("🎤 Microphone", value=consent.microphone, key="parent_mic")
    key = st.checkbox("⌨️ Keyboard", value=consent.keyboard, key="parent_key")

    if st.button("Save Permissions", key="save_permissions"):
        st.session_state.kids_sensor_consent = SensorConsent(
            camera=cam, microphone=mic, keyboard=key,
        )
        st.success("Permissions saved!")

    # Data retention info
    st.markdown("##### Data Retention")
    st.info(
        f"Kids mode data is retained for **{KIDS_CONFIG.data_retention_days} days**.  \n"
        f"Raw sensor data is **{'stored' if KIDS_CONFIG.store_raw_sensor_data else 'NOT stored'}**.  \n"
        f"All data is stored locally on this device."
    )

    # Reset button
    st.markdown("##### Reset")
    if st.button("🔄 Reset All Kids Data", key="reset_kids_data"):
        st.session_state.kids_chat_count = 0
        st.session_state.kids_messages = []
        st.session_state.kids_emotion_log = {}
        st.session_state.kids_safety_events = []
        st.session_state.bubble_active = False
        st.session_state.bubble_phase = "idle"
        st.warning("All kids session data has been reset.")
