"""Onboarding Flow Module for EmoFriend MVP1.

Provides a 3-step onboarding process for kids and elderly users
that requires no technical knowledge.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Tuple

from .audience_config import AudienceMode


# ---------------------------------------------------------------------------
# Onboarding step enum
# ---------------------------------------------------------------------------

class OnboardingStep(Enum):
    """Steps in the onboarding flow."""
    CONSENT = "consent"
    MODE_SELECT = "mode_select"
    NAME_INPUT = "name_input"
    FIRST_EMOTION = "first_emotion"
    WELCOME = "welcome"
    COMPLETE = "complete"


# ---------------------------------------------------------------------------
# Sensor consent
# ---------------------------------------------------------------------------

@dataclass
class SensorConsent:
    """Per-sensor consent flags."""
    camera: bool = False
    microphone: bool = False
    keyboard: bool = False


# ---------------------------------------------------------------------------
# Sensor explanations (mode-specific)
# ---------------------------------------------------------------------------

SENSOR_EXPLANATIONS: dict[str, dict[AudienceMode, str]] = {
    "camera": {
        AudienceMode.KIDS: "Emo uses your camera to see your smile! 📸",
        AudienceMode.ELDERLY: "Emo 用相機了解你的表情。📸",
    },
    "microphone": {
        AudienceMode.KIDS: "Emo uses your mic to hear your voice! 🎤",
        AudienceMode.ELDERLY: "Emo 用麥克風聆聽你的聲音。🎤",
    },
    "keyboard": {
        AudienceMode.KIDS: "Emo uses your keyboard when you want to type! ⌨️",
        AudienceMode.ELDERLY: "Emo 用鍵盤讓你輸入文字。⌨️",
    },
}


# ---------------------------------------------------------------------------
# Onboarding state
# ---------------------------------------------------------------------------

@dataclass
class OnboardingState:
    """Mutable state tracking the user's progress through onboarding."""
    current_step: OnboardingStep = OnboardingStep.CONSENT
    user_name: str = ""
    audience_mode: Optional[AudienceMode] = None
    consent: SensorConsent = field(default_factory=SensorConsent)
    first_emotion: Optional[str] = None
    parent_pin: Optional[str] = None  # Kids mode only
    family_contact: Optional[str] = None  # Elderly mode only
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Prompt generation
# ---------------------------------------------------------------------------

def generate_onboarding_prompt(
    step: OnboardingStep,
    mode: Optional[AudienceMode] = None,
    *,
    name: str = "",
) -> str:
    """Return a user-facing prompt string for the given onboarding step.

    Args:
        step: The current onboarding step.
        mode: The audience mode (required for mode-specific prompts).
        name: The user's name (used in FIRST_EMOTION prompts).

    Returns:
        A prompt string to display to the user.
    """
    if step == OnboardingStep.CONSENT:
        return (
            "Before we start, let me ask your permission to use some things. "
            "You can say yes or no to each one!"
        )
    if step == OnboardingStep.MODE_SELECT:
        return "Hi! I'm Emo, your feeling friend! 🐝 Are you a little one, or a wise one?"
    if step == OnboardingStep.NAME_INPUT:
        if mode == AudienceMode.ELDERLY:
            return "你好！我是 Emo，你的情感陪伴。請問你怎麼稱呼？"
        return "I want to be your feeling friend! What's your name?"
    if step == OnboardingStep.FIRST_EMOTION:
        if mode == AudienceMode.ELDERLY:
            return f"{name}，很高興認識你。你現在感覺怎麼樣？"
        return f"Nice to meet you, {name}! How are you feeling right now?"
    if step == OnboardingStep.WELCOME:
        if mode == AudienceMode.ELDERLY:
            return "我會一直在這裡陪你。有什麼想聊的，隨時跟我說。"
        return "Great! I'll always be here when you need me. Want to say hi to me anytime! 🌟"
    if step == OnboardingStep.COMPLETE:
        return ""
    return ""


# ---------------------------------------------------------------------------
# Step advancement
# ---------------------------------------------------------------------------

def advance_onboarding(state: OnboardingState, **kwargs: object) -> OnboardingStep:
    """Advance the onboarding flow to the next step.

    Keyword arguments update the state before the transition is computed.
    Recognised kwargs correspond to OnboardingState fields:
        audience_mode, user_name, first_emotion, parent_pin, family_contact,
        consent, completed_at.

    Args:
        state: The current onboarding state (mutated in place).
        **kwargs: Fields to update on *state* before advancing.

    Returns:
        The next OnboardingStep.
    """
    # Apply any provided updates to the state
    if "audience_mode" in kwargs:
        state.audience_mode = kwargs["audience_mode"]  # type: ignore[assignment]
    if "user_name" in kwargs:
        state.user_name = str(kwargs["user_name"])
    if "first_emotion" in kwargs:
        state.first_emotion = str(kwargs["first_emotion"])
    if "parent_pin" in kwargs:
        state.parent_pin = str(kwargs["parent_pin"])
    if "family_contact" in kwargs:
        state.family_contact = str(kwargs["family_contact"])
    if "consent" in kwargs:
        state.consent = kwargs["consent"]  # type: ignore[assignment]
    if "completed_at" in kwargs:
        state.completed_at = kwargs["completed_at"]  # type: ignore[assignment]

    step = state.current_step

    if step == OnboardingStep.CONSENT:
        next_step = OnboardingStep.MODE_SELECT
    elif step == OnboardingStep.MODE_SELECT:
        next_step = OnboardingStep.NAME_INPUT
    elif step == OnboardingStep.NAME_INPUT:
        next_step = OnboardingStep.FIRST_EMOTION
    elif step == OnboardingStep.FIRST_EMOTION:
        next_step = OnboardingStep.WELCOME
    elif step == OnboardingStep.WELCOME:
        next_step = OnboardingStep.COMPLETE
        state.completed_at = datetime.now(timezone.utc)
    else:
        next_step = OnboardingStep.COMPLETE

    state.current_step = next_step
    return next_step


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_step(state: OnboardingState) -> Tuple[bool, Optional[str]]:
    """Validate that the current step has all required data before advancing.

    Returns:
        A tuple of (is_valid, error_message).
        (True, None) if the step is valid; (False, message) otherwise.
    """
    step = state.current_step

    if step == OnboardingStep.MODE_SELECT:
        if state.audience_mode is None:
            return (False, "Please select a mode (kids or elderly) before continuing.")
        if state.audience_mode == AudienceMode.KIDS and not state.parent_pin:
            return (False, "A parent PIN is required for Kids mode.")
        if state.audience_mode == AudienceMode.ELDERLY and not state.family_contact:
            return (False, "A family contact is required for Elderly mode.")

    elif step == OnboardingStep.NAME_INPUT:
        if not state.user_name.strip():
            return (False, "Please enter your name before continuing.")

    elif step == OnboardingStep.FIRST_EMOTION:
        if not state.first_emotion:
            return (False, "Please select how you are feeling before continuing.")

    return (True, None)
