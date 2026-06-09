"""Emotional Sharing Engine — EmoFriend 情感分享引擎

提供用戶與 Emo 之間的情感分享空間，根據友誼等級調整聆聽模式，
計算情感共振分數，並自動生成日記條目。

EmoGlyph 整合點: Resonance Layer + Current Layer + Friendship Engine

設計原則：
- 聆聽模式隨友誼深度動態調整（深度越高越沉默）
- 共振計算基於情感向量餘弦相似度
- 分享模式下永不給建議，只提供共情與陪伴
- 日記條目自動摘要每次分享會話
"""
from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from ..resonance import SilenceType, cosine_similarity
from .friendship_engine import FriendshipLevel


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class EmotionShare:
    """用戶分享的一次情感"""
    timestamp: datetime
    emotion_type: str       # Panksepp system name
    valence: float          # -1.0 to 1.0
    arousal: float          # 0.0 to 1.0
    intensity: float        # 0.0 to 1.0
    content: str            # what the user shared (text)
    trigger: Optional[str]  # what triggered this emotion

    def __post_init__(self) -> None:
        self.valence = _clamp(self.valence, -1.0, 1.0)
        self.arousal = _clamp(self.arousal, 0.0, 1.0)
        self.intensity = _clamp(self.intensity, 0.0, 1.0)


@dataclass
class EmoResponse:
    """Emo 對用戶情感分享的回應"""
    timestamp: datetime
    response_type: str          # "silence", "empathy", "brief_acknowledgment", "resonance"
    content: str                # what Emo said (or "" for silence)
    silence_type: Optional[str] # "MA", "MU", "ZEN" if response is silence
    resonance_score: float      # 0.0-1.0, how much Emo resonated

    def __post_init__(self) -> None:
        self.resonance_score = _clamp(self.resonance_score, 0.0, 1.0)


@dataclass
class DiaryEntry:
    """自動生成的分享日記條目"""
    date: datetime
    dominant_emotion: str
    emotion_intensity: float
    trigger: Optional[str]
    emos_response_summary: str     # brief summary of Emo's responses
    user_state_change: Optional[str]  # "improved", "stable", "worsened"
    key_moment: str                # the most significant moment of the session
    friendship_level: str          # at time of session


@dataclass
class SharingSession:
    """一次完整的情感分享會話"""
    session_id: str
    user_id: str
    start_time: datetime
    end_time: Optional[datetime]
    emotions_shared: List[EmotionShare]
    emos_responses: List[EmoResponse]
    resonance_scores: List[float]
    diary_entry: Optional[DiaryEntry]
    is_active: bool


# ---------------------------------------------------------------------------
# Listening mode
# ---------------------------------------------------------------------------

class ListeningMode(Enum):
    ACTIVE = 0      # Emo responds with empathy and brief reflections
    RECEPTIVE = 1   # Emo mostly listens, only brief acknowledgments
    SILENT = 2      # Emo is present but silent, giving full space


# ---------------------------------------------------------------------------
# Response templates (never advice — only empathy and presence)
# ---------------------------------------------------------------------------

_ACTIVE_RESPONSES = [
    "我能感受到你的{emotion}",
    "那聽起來真的很辛苦",
    "我在這裡陪著你",
    "你的感受是重要的",
    "謝謝你願意分享這些",
]

_RECEPTIVE_RESPONSES = [
    "我在聽",
    "我在這裡",
    "...",
    "嗯",
]

_SILENCE_TYPES = [SilenceType.MA, SilenceType.MU, SilenceType.ZEN]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def _friendship_depth(level: FriendshipLevel) -> float:
    """Map FriendshipLevel to a 0-1 depth value for resonance scaling."""
    _DEPTH_MAP = {
        FriendshipLevel.ACQUAINTANCE: 0.125,
        FriendshipLevel.CASUAL_FRIEND: 0.375,
        FriendshipLevel.CLOSE_FRIEND: 0.625,
        FriendshipLevel.SOUL_COMPANION: 0.875,
    }
    return _DEPTH_MAP.get(level, 0.0)


def _detect_state_change(emotions: List[EmotionShare]) -> Optional[str]:
    """Detect if user's emotional state changed during the session."""
    if len(emotions) < 2:
        return "stable"
    first = emotions[0]
    last = emotions[-1]
    valence_diff = last.valence - first.valence
    if valence_diff > 0.2:
        return "improved"
    elif valence_diff < -0.2:
        return "worsened"
    return "stable"


def _find_key_moment(
    emotions: List[EmotionShare],
    responses: List[EmoResponse],
) -> str:
    """Find the most significant moment (highest intensity or most resonant)."""
    if not emotions:
        return "No emotions shared"
    # Find the emotion with highest intensity
    peak_idx = 0
    peak_intensity = 0.0
    for i, e in enumerate(emotions):
        if e.intensity > peak_intensity:
            peak_intensity = e.intensity
            peak_idx = i
    peak_emotion = emotions[peak_idx]
    trigger_text = f" (trigger: {peak_emotion.trigger})" if peak_emotion.trigger else ""
    return f"{peak_emotion.emotion_type} at intensity {peak_emotion.intensity:.2f}{trigger_text}"


def _summarize_responses(responses: List[EmoResponse]) -> str:
    """Summarize Emo's response pattern."""
    if not responses:
        return "No responses"
    counts: dict[str, int] = {}
    for r in responses:
        counts[r.response_type] = counts.get(r.response_type, 0) + 1
    parts = [f"{count} {rtype}" for rtype, count in sorted(counts.items())]
    return "mostly " + ", ".join(parts)


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class EmotionalSharingEngine:
    """EmoFriend 情感分享引擎 — 提供情感分享空間與聆聽模式"""

    def start_sharing(
        self,
        user_id: str,
        friendship_level: FriendshipLevel,
    ) -> SharingSession:
        """Start a new sharing session."""
        now = datetime.now(timezone.utc)
        return SharingSession(
            session_id=str(uuid.uuid4()),
            user_id=user_id,
            start_time=now,
            end_time=None,
            emotions_shared=[],
            emos_responses=[],
            resonance_scores=[],
            diary_entry=None,
            is_active=True,
        )

    def get_listening_mode(
        self,
        friendship_level: FriendshipLevel,
        emotion_intensity: float,
    ) -> ListeningMode:
        """Determine listening mode based on friendship level and emotion intensity."""
        emotion_intensity = _clamp(emotion_intensity)

        if friendship_level == FriendshipLevel.SOUL_COMPANION:
            return ListeningMode.SILENT

        if friendship_level == FriendshipLevel.CLOSE_FRIEND:
            # SILENT or RECEPTIVE — trust the process
            if emotion_intensity >= 0.7:
                return ListeningMode.SILENT
            return ListeningMode.RECEPTIVE

        if friendship_level == FriendshipLevel.CASUAL_FRIEND:
            return ListeningMode.RECEPTIVE

        # ACQUAINTANCE
        if emotion_intensity >= 0.6:
            return ListeningMode.RECEPTIVE
        return ListeningMode.ACTIVE

    def resonate(
        self,
        session: SharingSession,
        emotion_share: EmotionShare,
    ) -> float:
        """Calculate resonance score between user's emotion and Emo's empathic response.

        Formula: resonance = cosine_similarity(user_vec, emo_vec) * (0.5 + 0.5 * friendship_depth)
        """
        # User's emotion vector
        user_vec = [emotion_share.valence, emotion_share.arousal, emotion_share.intensity]

        # Emo's empathic response vector — mirrors user's emotion with slight dampening
        # Emo resonates by reflecting the user's emotional state
        emo_vec = [
            emotion_share.valence * 0.9,
            emotion_share.arousal * 0.85,
            emotion_share.intensity * 0.8,
        ]

        # Base cosine similarity
        similarity = cosine_similarity(user_vec, emo_vec)

        # Scale by friendship depth
        # Use the last response's resonance as a proxy for friendship depth if available,
        # otherwise compute from session context
        friendship_depth = 0.5  # default mid-range
        if session.resonance_scores:
            # Higher accumulated resonance suggests deeper friendship
            friendship_depth = _clamp(sum(session.resonance_scores) / len(session.resonance_scores))

        resonance = similarity * (0.5 + 0.5 * friendship_depth)
        return _clamp(resonance, 0.0, 1.0)

    def listen(
        self,
        session: SharingSession,
        emotion_share: EmotionShare,
        friendship_level: FriendshipLevel,
    ) -> EmoResponse:
        """Listen to user's emotion share and generate Emo's response."""
        if not session.is_active:
            raise ValueError("Cannot listen to an inactive session")

        mode = self.get_listening_mode(friendship_level, emotion_share.intensity)
        now = datetime.now(timezone.utc)

        # Calculate resonance score
        resonance_score = self.resonate(session, emotion_share)

        if mode == ListeningMode.SILENT:
            # Choose silence type based on emotion characteristics
            if emotion_share.intensity >= 0.8:
                silence_type = SilenceType.ZEN  # deep presence for intense emotions
            elif emotion_share.valence < -0.5:
                silence_type = SilenceType.MU  # no-answer for deep negative
            else:
                silence_type = SilenceType.MA  # active contemplation otherwise
            response = EmoResponse(
                timestamp=now,
                response_type="silence",
                content="",
                silence_type=silence_type.value,
                resonance_score=resonance_score,
            )
        elif mode == ListeningMode.RECEPTIVE:
            import random
            content = random.choice(_RECEPTIVE_RESPONSES)
            response = EmoResponse(
                timestamp=now,
                response_type="brief_acknowledgment",
                content=content,
                silence_type=None,
                resonance_score=resonance_score,
            )
        else:
            # ACTIVE mode
            import random
            emotion_name = emotion_share.emotion_type.lower()
            content = random.choice(_ACTIVE_RESPONSES).format(emotion=emotion_name)
            response = EmoResponse(
                timestamp=now,
                response_type="empathy",
                content=content,
                silence_type=None,
                resonance_score=resonance_score,
            )

        # Update session
        session.emotions_shared.append(emotion_share)
        session.emos_responses.append(response)
        session.resonance_scores.append(resonance_score)

        return response

    def create_diary_entry(
        self,
        session: SharingSession,
        friendship_level: str,
    ) -> DiaryEntry:
        """Auto-generate a diary entry from the sharing session."""
        if not session.emotions_shared:
            return DiaryEntry(
                date=session.start_time,
                dominant_emotion="NEUTRAL",
                emotion_intensity=0.0,
                trigger=None,
                emos_response_summary="No responses",
                user_state_change="stable",
                key_moment="No emotions shared",
                friendship_level=friendship_level,
            )

        # Find dominant emotion (highest intensity)
        dominant = max(session.emotions_shared, key=lambda e: e.intensity)

        # Detect state change
        state_change = _detect_state_change(session.emotions_shared)

        # Find key moment
        key_moment = _find_key_moment(session.emotions_shared, session.emos_responses)

        # Summarize responses
        response_summary = _summarize_responses(session.emos_responses)

        return DiaryEntry(
            date=session.start_time,
            dominant_emotion=dominant.emotion_type,
            emotion_intensity=dominant.intensity,
            trigger=dominant.trigger,
            emos_response_summary=response_summary,
            user_state_change=state_change,
            key_moment=key_moment,
            friendship_level=friendship_level,
        )

    def end_sharing(self, session: SharingSession) -> SharingSession:
        """End the sharing session."""
        session.end_time = datetime.now(timezone.utc)
        session.is_active = False
        return session
