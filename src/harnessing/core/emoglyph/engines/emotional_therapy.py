"""Emotional Therapy Engine — 情感療癒引擎

EmoFriend 產品核心：基於 Panksepp 七大情感系統的療癒引擎，
結合沉默療法 (Silence Therapy)、慈悲回應、五行引導，
根據友誼等級動態調整療癒策略。

EmoGlyph 整合點: Resonance Layer + Current Layer + Construct Layer

設計原則：
- Panksepp 系統驅動：每種情感系統有專屬療癒策略
- 沉默療法遞進：MA → MU → ZEN，由深到淺
- 友誼等級影響：越深友誼越多沉默、越少引導
- 安全底線：高強度或自傷風險時轉介專業
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from ..resonance import SilenceType
from .friendship_engine import FriendshipLevel


class TherapyOutcome(Enum):
    IN_PROGRESS = 0
    IMPROVED = 1       # emotion intensity decreased
    STABLE = 2         # no significant change
    ESCALATED = 3      # emotion intensity increased (needs different approach)
    REFERRED = 4       # suggested professional help


class SilenceTherapyStage(Enum):
    MA = 0    # Deep reflection - Emo is present but silent, giving space
    MU = 1    # Gentle acknowledgment - brief "I'm here" signals
    ZEN = 2   # Present moment - shared silence, both in the now


@dataclass
class TherapyIntervention:
    timestamp: datetime
    intervention_type: str   # "silence_therapy", "panksepp_guided", "compassionate_response", "construct_guided"
    target_system: str       # Panksepp system name
    description: str
    effectiveness: float     # 0.0-1.0, estimated

    def __post_init__(self) -> None:
        if not 0.0 <= self.effectiveness <= 1.0:
            raise ValueError(f"effectiveness must be in [0, 1], got {self.effectiveness}")


@dataclass
class TherapySession:
    session_id: str
    user_id: str
    start_time: datetime
    end_time: Optional[datetime]
    start_emotion: str           # Panksepp system name
    start_intensity: float
    end_emotion: Optional[str]
    end_intensity: Optional[float]
    interventions: List[TherapyIntervention]
    outcome: TherapyOutcome
    friendship_level_at_start: FriendshipLevel


@dataclass
class PankseppHealingStrategy:
    system: str               # Panksepp system name
    approach: str             # healing approach description
    silence_type: SilenceType # which silence to use
    guidance_prompt: str      # what Emo might say
    construct_element: str    # Five Element for Construct layer
    expected_outcome: str


# Friendship-level intervention weight configuration
_FRIENDSHIP_INTERVENTION_WEIGHTS = {
    FriendshipLevel.ACQUAINTANCE: {
        "silence_weight": 0.1,
        "guidance_weight": 0.7,
        "compassion_weight": 0.2,
    },
    FriendshipLevel.CASUAL_FRIEND: {
        "silence_weight": 0.3,
        "guidance_weight": 0.4,
        "compassion_weight": 0.3,
    },
    FriendshipLevel.CLOSE_FRIEND: {
        "silence_weight": 0.5,
        "guidance_weight": 0.2,
        "compassion_weight": 0.3,
    },
    FriendshipLevel.SOUL_COMPANION: {
        "silence_weight": 0.7,
        "guidance_weight": 0.1,
        "compassion_weight": 0.2,
    },
}

# Silence therapy stage duration multipliers by friendship level
_SILENCE_DURATION_MULTIPLIERS = {
    FriendshipLevel.ACQUAINTANCE: 0.5,
    FriendshipLevel.CASUAL_FRIEND: 1.0,
    FriendshipLevel.CLOSE_FRIEND: 1.5,
    FriendshipLevel.SOUL_COMPANION: 2.0,
}

# Self-harm indicator keywords for professional referral
_SELF_HARM_INDICATORS = [
    "self-harm", "self harm", "suicide", "kill myself",
    "end my life", "don't want to live", "hurt myself",
    "自傷", "自殘", "自殺", "不想活", "結束生命", "傷害自己",
]


class EmotionalTherapyEngine:
    """EmoFriend 情感療癒引擎 — 基於 Panksepp 系統的療癒策略"""

    def __init__(self) -> None:
        self.healing_strategies: dict[str, PankseppHealingStrategy] = {
            "CARE": PankseppHealingStrategy(
                system="CARE",
                approach="comfort_nurture",
                silence_type=SilenceType.MU,
                guidance_prompt="I'm here with you. You don't have to face this alone.",
                construct_element="water",
                expected_outcome="feeling_comforted",
            ),
            "PLAY": PankseppHealingStrategy(
                system="PLAY",
                approach="transform_joy",
                silence_type=SilenceType.MA,
                guidance_prompt="What if we looked at this from a different angle?",
                construct_element="wood",
                expected_outcome="lightness_curiosity",
            ),
            "SEEKING": PankseppHealingStrategy(
                system="SEEKING",
                approach="explore_curiosity",
                silence_type=SilenceType.ZEN,
                guidance_prompt="What are you curious about right now?",
                construct_element="wood",
                expected_outcome="meaning_discovery",
            ),
            "FEAR": PankseppHealingStrategy(
                system="FEAR",
                approach="safety_grounding",
                silence_type=SilenceType.MU,
                guidance_prompt="You're safe here. Let's breathe together.",
                construct_element="earth",
                expected_outcome="grounded_safe",
            ),
            "RAGE": PankseppHealingStrategy(
                system="RAGE",
                approach="cool_down_channel",
                silence_type=SilenceType.MA,
                guidance_prompt="Your anger is valid. Let's give it space to move.",
                construct_element="metal",
                expected_outcome="energy_channeled",
            ),
            "PANIC": PankseppHealingStrategy(
                system="PANIC",
                approach="reconnect_belong",
                silence_type=SilenceType.ZEN,
                guidance_prompt="You matter. You're not alone.",
                construct_element="fire",
                expected_outcome="connection_belonging",
            ),
            "LUST": PankseppHealingStrategy(
                system="LUST",
                approach="vitality_life_force",
                silence_type=SilenceType.ZEN,
                guidance_prompt="What makes you feel alive?",
                construct_element="fire",
                expected_outcome="vitality_awakened",
            ),
        }

    def start_session(
        self,
        user_id: str,
        emotion: str,
        intensity: float,
        friendship_level: FriendshipLevel,
    ) -> TherapySession:
        """Start a new therapy session."""
        if not 0.0 <= intensity <= 1.0:
            raise ValueError(f"intensity must be in [0, 1], got {intensity}")
        if emotion not in self.healing_strategies:
            raise ValueError(
                f"Unknown emotion system: {emotion}. "
                f"Must be one of: {list(self.healing_strategies.keys())}"
            )
        session_id = str(uuid.uuid4())
        return TherapySession(
            session_id=session_id,
            user_id=user_id,
            start_time=datetime.now(timezone.utc),
            end_time=None,
            start_emotion=emotion,
            start_intensity=intensity,
            end_emotion=None,
            end_intensity=None,
            interventions=[],
            outcome=TherapyOutcome.IN_PROGRESS,
            friendship_level_at_start=friendship_level,
        )

    def choose_intervention(
        self,
        session: TherapySession,
        friendship_level: FriendshipLevel,
    ) -> TherapyIntervention:
        """Choose the best intervention based on emotion and friendship level."""
        weights = _FRIENDSHIP_INTERVENTION_WEIGHTS[friendship_level]
        emotion = session.start_emotion

        # Determine intervention type based on weights and session state
        intervention_count = len(session.interventions)
        strategy = self.healing_strategies[emotion]

        # For early interventions, lean toward structured approaches
        # For later interventions, lean toward silence
        if intervention_count == 0:
            # First intervention: guided approach
            if weights["guidance_weight"] >= weights["silence_weight"]:
                return self.apply_panksepp_healing(session, emotion)
            else:
                return self.apply_silence_therapy(session, SilenceTherapyStage.MA)
        elif intervention_count == 1:
            # Second intervention: compassionate response or silence
            if weights["compassion_weight"] >= weights["silence_weight"]:
                return TherapyIntervention(
                    timestamp=datetime.now(timezone.utc),
                    intervention_type="compassionate_response",
                    target_system=emotion,
                    description=f"Compassionate response for {emotion}: {strategy.guidance_prompt}",
                    effectiveness=self._estimate_effectiveness(session, friendship_level),
                )
            else:
                return self.apply_silence_therapy(session, SilenceTherapyStage.MU)
        else:
            # Later interventions: silence therapy progression
            stage = self._next_silence_stage(session)
            return self.apply_silence_therapy(session, stage)

    def apply_silence_therapy(
        self,
        session: TherapySession,
        stage: SilenceTherapyStage,
    ) -> TherapyIntervention:
        """Apply silence therapy at the given stage."""
        emotion = session.start_emotion
        strategy = self.healing_strategies[emotion]
        duration_multiplier = _SILENCE_DURATION_MULTIPLIERS[
            session.friendship_level_at_start
        ]

        stage_descriptions = {
            SilenceTherapyStage.MA: (
                f"Deep reflection silence for {emotion}. "
                f"Emo is present but silent, giving space. "
                f"Duration factor: {duration_multiplier:.1f}x"
            ),
            SilenceTherapyStage.MU: (
                f"Gentle acknowledgment silence for {emotion}. "
                f"Emo sends brief presence signals ('...', 'I'm here'). "
                f"Duration factor: {duration_multiplier:.1f}x"
            ),
            SilenceTherapyStage.ZEN: (
                f"Present moment shared silence for {emotion}. "
                f"Both present in the now, beyond words. "
                f"Duration factor: {duration_multiplier:.1f}x"
            ),
        }

        # Effectiveness increases with friendship level and stage progression
        base_effectiveness = 0.3 + 0.15 * stage.value
        friendship_bonus = session.friendship_level_at_start.value * 0.1
        effectiveness = min(1.0, base_effectiveness + friendship_bonus)

        return TherapyIntervention(
            timestamp=datetime.now(timezone.utc),
            intervention_type="silence_therapy",
            target_system=emotion,
            description=stage_descriptions[stage],
            effectiveness=effectiveness,
        )

    def apply_panksepp_healing(
        self,
        session: TherapySession,
        system: str,
    ) -> TherapyIntervention:
        """Apply Panksepp-guided healing for a specific system."""
        if system not in self.healing_strategies:
            raise ValueError(
                f"Unknown system: {system}. "
                f"Must be one of: {list(self.healing_strategies.keys())}"
            )
        strategy = self.healing_strategies[system]

        # Effectiveness based on strategy match and friendship level
        base_effectiveness = 0.5
        friendship_bonus = session.friendship_level_at_start.value * 0.08
        effectiveness = min(1.0, base_effectiveness + friendship_bonus)

        return TherapyIntervention(
            timestamp=datetime.now(timezone.utc),
            intervention_type="panksepp_guided",
            target_system=system,
            description=(
                f"Panksepp-guided healing for {system}: {strategy.approach}. "
                f"Using {strategy.silence_type.value} silence. "
                f"Guidance: \"{strategy.guidance_prompt}\""
            ),
            effectiveness=effectiveness,
        )

    def apply_construct_guidance(
        self,
        session: TherapySession,
        element: str,
    ) -> TherapyIntervention:
        """Apply Construct-layer guidance using Five Elements."""
        valid_elements = {"wood", "fire", "earth", "metal", "water"}
        if element not in valid_elements:
            raise ValueError(
                f"Unknown element: {element}. Must be one of: {sorted(valid_elements)}"
            )

        element_descriptions = {
            "wood": "Growth and flexibility — like a tree bending in the wind, not breaking",
            "fire": "Warmth and vitality — the spark that connects and enlivens",
            "earth": "Stability and grounding — the solid ground beneath your feet",
            "metal": "Structure and boundaries — clarity and definition",
            "water": "Flowing and adapting — wisdom through depth and softness",
        }

        # Find which Panksepp system maps to this element
        matching_system = session.start_emotion
        for sys_name, strategy in self.healing_strategies.items():
            if strategy.construct_element == element:
                matching_system = sys_name
                break

        base_effectiveness = 0.4
        friendship_bonus = session.friendship_level_at_start.value * 0.1
        effectiveness = min(1.0, base_effectiveness + friendship_bonus)

        return TherapyIntervention(
            timestamp=datetime.now(timezone.utc),
            intervention_type="construct_guided",
            target_system=matching_system,
            description=(
                f"Construct guidance via {element} element: {element_descriptions[element]}"
            ),
            effectiveness=effectiveness,
        )

    def end_session(
        self,
        session: TherapySession,
        end_emotion: str,
        end_intensity: float,
    ) -> TherapySession:
        """End a therapy session and determine outcome."""
        if not 0.0 <= end_intensity <= 1.0:
            raise ValueError(f"end_intensity must be in [0, 1], got {end_intensity}")

        session.end_time = datetime.now(timezone.utc)
        session.end_emotion = end_emotion
        session.end_intensity = end_intensity

        # Determine outcome
        intensity_delta = session.start_intensity - end_intensity

        if self.should_refer_professional(session):
            session.outcome = TherapyOutcome.REFERRED
        elif intensity_delta > 0.1:
            session.outcome = TherapyOutcome.IMPROVED
        elif intensity_delta < -0.1:
            session.outcome = TherapyOutcome.ESCALATED
        else:
            session.outcome = TherapyOutcome.STABLE

        return session

    def should_refer_professional(self, session: TherapySession) -> bool:
        """Check if professional referral is needed.

        Referral when:
        - intensity > 0.9 after 3+ interventions
        - self-harm indicators detected in intervention descriptions
        """
        # Check intensity threshold after sufficient interventions
        current_intensity = session.end_intensity if session.end_intensity is not None else session.start_intensity
        if current_intensity > 0.9 and len(session.interventions) >= 3:
            return True

        # Check for self-harm indicators in intervention descriptions
        for intervention in session.interventions:
            desc_lower = intervention.description.lower()
            for indicator in _SELF_HARM_INDICATORS:
                if indicator in desc_lower:
                    return True

        return False

    def _next_silence_stage(self, session: TherapySession) -> SilenceTherapyStage:
        """Determine the next silence therapy stage based on session history.

        Progression: MA → MU → ZEN
        """
        silence_interventions = [
            i for i in session.interventions
            if i.intervention_type == "silence_therapy"
        ]
        if not silence_interventions:
            return SilenceTherapyStage.MA
        # Progress through stages
        stage_index = min(len(silence_interventions), SilenceTherapyStage.ZEN.value)
        return SilenceTherapyStage(stage_index)

    def _estimate_effectiveness(
        self,
        session: TherapySession,
        friendship_level: FriendshipLevel,
    ) -> float:
        """Estimate intervention effectiveness based on session context."""
        base = 0.4
        friendship_bonus = friendship_level.value * 0.1
        # More interventions = diminishing returns
        intervention_penalty = len(session.interventions) * 0.05
        return min(1.0, max(0.1, base + friendship_bonus - intervention_penalty))
