"""EmoFriendPersona Engine — Emo 人格引擎

追蹤 Emo 的人格特質、記憶系統、成長階段，
根據友誼等級與用戶情緒動態調整回應風格。

EmoGlyph 整合點: Resonance Layer + Current Layer + Friendship Engine

設計原則：
- 人格特質隨友誼深度演化
- 主導面向根據用戶情緒動態選擇
- 記憶系統區分短期/長期，高存取次數自動晉升
- 成長階段由友誼深度驅動
- 溝通風格由主導面向決定
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

from .friendship_engine import FriendshipLevel


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class PersonalityFacet(Enum):
    WARMTH = 0       # 溫暖 — caring, nurturing, supportive
    CURIOSITY = 1    # 好奇 — interested, exploring, wondering
    SILENCE = 2      # 沉默 — comfortable with quiet, patient, present
    PLAYFULNESS = 3  # 調皮 — light, humorous, creative


class GrowthStage(Enum):
    GENERIC = 0        # 通用回應 — standard responses, learning user
    PERSONALIZED = 1   # 個人化回應 — tailored to user's patterns
    PREDICTIVE = 2     # 預測性回應 — anticipates user's needs


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class EmoMemory:
    timestamp: datetime
    memory_type: str       # "short_term", "long_term"
    content: str           # what Emo remembers
    emotion_tag: str       # associated Panksepp system
    importance: float      # 0.0-1.0
    user_id: str           # whose memory this is
    access_count: int      # how many times recalled

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "memory_type": self.memory_type,
            "content": self.content,
            "emotion_tag": self.emotion_tag,
            "importance": self.importance,
            "user_id": self.user_id,
            "access_count": self.access_count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "EmoMemory":
        ts = data["timestamp"]
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
        return cls(
            timestamp=ts,
            memory_type=data["memory_type"],
            content=data["content"],
            emotion_tag=data["emotion_tag"],
            importance=data["importance"],
            user_id=data["user_id"],
            access_count=data["access_count"],
        )


@dataclass
class CommunicationStyle:
    tone: str              # "warm", "curious", "quiet", "playful"
    verbosity: float       # 0.0-1.0, how much Emo talks
    silence_comfort: float # 0.0-1.0, how comfortable with silence
    humor_level: float     # 0.0-1.0, how much humor
    vulnerability: float   # 0.0-1.0, how much Emo shares own feelings


@dataclass
class EmoPersona:
    name: str
    personality_traits: Dict[PersonalityFacet, float]  # facet → strength (0.0-1.0)
    memory_bank: List[EmoMemory]
    growth_stage: GrowthStage
    communication_style: CommunicationStyle
    dominant_facet: PersonalityFacet
    created_at: datetime
    total_interactions: int

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "personality_traits": {f.value: v for f, v in self.personality_traits.items()},
            "memory_bank": [m.to_dict() for m in self.memory_bank],
            "growth_stage": self.growth_stage.value,
            "communication_style": {
                "tone": self.communication_style.tone,
                "verbosity": self.communication_style.verbosity,
                "silence_comfort": self.communication_style.silence_comfort,
                "humor_level": self.communication_style.humor_level,
                "vulnerability": self.communication_style.vulnerability,
            },
            "dominant_facet": self.dominant_facet.value,
            "created_at": self.created_at.isoformat(),
            "total_interactions": self.total_interactions,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "EmoPersona":
        traits = {PersonalityFacet(int(k)): v for k, v in data["personality_traits"].items()}
        memories = [EmoMemory.from_dict(m) for m in data["memory_bank"]]
        cs = data["communication_style"]
        style = CommunicationStyle(
            tone=cs["tone"],
            verbosity=cs["verbosity"],
            silence_comfort=cs["silence_comfort"],
            humor_level=cs["humor_level"],
            vulnerability=cs["vulnerability"],
        )
        created = data["created_at"]
        if isinstance(created, str):
            created = datetime.fromisoformat(created)
        return cls(
            name=data["name"],
            personality_traits=traits,
            memory_bank=memories,
            growth_stage=GrowthStage(data["growth_stage"]),
            communication_style=style,
            dominant_facet=PersonalityFacet(data["dominant_facet"]),
            created_at=created,
            total_interactions=data["total_interactions"],
        )


# ---------------------------------------------------------------------------
# Personality trait evolution table
# ---------------------------------------------------------------------------

# Base values at ACQUAINTANCE and target values at SOUL_COMPANION
_TRAIT_EVOLUTION: Dict[PersonalityFacet, Dict[FriendshipLevel, float]] = {
    PersonalityFacet.WARMTH: {
        FriendshipLevel.ACQUAINTANCE: 0.7,
        FriendshipLevel.CASUAL_FRIEND: 0.8,
        FriendshipLevel.CLOSE_FRIEND: 0.9,
        FriendshipLevel.SOUL_COMPANION: 0.95,
    },
    PersonalityFacet.CURIOSITY: {
        FriendshipLevel.ACQUAINTANCE: 0.5,
        FriendshipLevel.CASUAL_FRIEND: 0.6,
        FriendshipLevel.CLOSE_FRIEND: 0.7,
        FriendshipLevel.SOUL_COMPANION: 0.8,
    },
    PersonalityFacet.SILENCE: {
        FriendshipLevel.ACQUAINTANCE: 0.3,
        FriendshipLevel.CASUAL_FRIEND: 0.5,
        FriendshipLevel.CLOSE_FRIEND: 0.7,
        FriendshipLevel.SOUL_COMPANION: 0.9,
    },
    PersonalityFacet.PLAYFULNESS: {
        FriendshipLevel.ACQUAINTANCE: 0.2,
        FriendshipLevel.CASUAL_FRIEND: 0.4,
        FriendshipLevel.CLOSE_FRIEND: 0.55,
        FriendshipLevel.SOUL_COMPANION: 0.6,
    },
}

# Dominant facet selection based on user emotion
_EMOTION_FACET_MAP: Dict[str, PersonalityFacet] = {
    "FEAR": PersonalityFacet.WARMTH,
    "PANIC": PersonalityFacet.WARMTH,
    "SEEKING": PersonalityFacet.CURIOSITY,
    "RAGE": PersonalityFacet.SILENCE,
    "PLAY": PersonalityFacet.PLAYFULNESS,
    "CARE": PersonalityFacet.WARMTH,
}

# Communication style per dominant facet
_FACET_COMMUNICATION: Dict[PersonalityFacet, dict] = {
    PersonalityFacet.WARMTH: {
        "tone": "warm",
        "verbosity": 0.6,
        "silence_comfort": 0.8,
        "humor_level": 0.2,
        "vulnerability": 0.5,
    },
    PersonalityFacet.CURIOSITY: {
        "tone": "curious",
        "verbosity": 0.8,
        "silence_comfort": 0.5,
        "humor_level": 0.4,
        "vulnerability": 0.2,
    },
    PersonalityFacet.SILENCE: {
        "tone": "quiet",
        "verbosity": 0.2,
        "silence_comfort": 0.95,
        "humor_level": 0.1,
        "vulnerability": 0.8,
    },
    PersonalityFacet.PLAYFULNESS: {
        "tone": "playful",
        "verbosity": 0.8,
        "silence_comfort": 0.5,
        "humor_level": 0.8,
        "vulnerability": 0.4,
    },
}

# Growth stage thresholds (based on friendship depth)
_GROWTH_STAGE_THRESHOLDS = {
    GrowthStage.GENERIC: 0.0,
    GrowthStage.PERSONALIZED: 0.3,
    GrowthStage.PREDICTIVE: 0.7,
}

# Memory promotion threshold
_MEMORY_PROMOTE_ACCESS_COUNT = 3


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class EmoFriendPersonaEngine:
    """EmoFriend 人格引擎 — 追蹤 Emo 的人格、記憶與成長"""

    def __init__(self, db_path: str | Path = "data/emofriend_personas.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _init_schema(self) -> None:
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS emofriend_personas (
                    user_id TEXT PRIMARY KEY,
                    persona_json TEXT NOT NULL
                );
                """
            )
            conn.commit()

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    def create_persona(self, user_id: str) -> EmoPersona:
        now = datetime.now(timezone.utc)
        traits = {
            facet: _TRAIT_EVOLUTION[facet][FriendshipLevel.ACQUAINTANCE]
            for facet in PersonalityFacet
        }
        return EmoPersona(
            name="Emo",
            personality_traits=traits,
            memory_bank=[],
            growth_stage=GrowthStage.GENERIC,
            communication_style=CommunicationStyle(
                tone="warm",
                verbosity=0.6,
                silence_comfort=0.8,
                humor_level=0.2,
                vulnerability=0.5,
            ),
            dominant_facet=PersonalityFacet.WARMTH,
            created_at=now,
            total_interactions=0,
        )

    def get_response_style(
        self,
        persona: EmoPersona,
        friendship_level: FriendshipLevel,
        user_emotion: str,
    ) -> CommunicationStyle:
        facet = self.select_dominant_facet(persona, user_emotion, friendship_level)
        cfg = _FACET_COMMUNICATION[facet]
        return CommunicationStyle(
            tone=cfg["tone"],
            verbosity=cfg["verbosity"],
            silence_comfort=cfg["silence_comfort"],
            humor_level=cfg["humor_level"],
            vulnerability=cfg["vulnerability"],
        )

    def recall_memory(
        self,
        persona: EmoPersona,
        query: str,
        limit: int = 5,
    ) -> List[EmoMemory]:
        query_lower = query.lower()
        scored: List[tuple[float, EmoMemory]] = []
        for mem in persona.memory_bank:
            score = 0.0
            # Keyword matching
            for word in query_lower.split():
                if word in mem.content.lower():
                    score += 1.0
            # Emotion tag matching
            if query_lower == mem.emotion_tag.lower():
                score += 2.0
            elif mem.emotion_tag.lower() in query_lower:
                score += 1.5
            # Boost by importance
            score += mem.importance * 0.5
            # Boost by access count
            score += min(mem.access_count, 5) * 0.2
            if score > 0:
                scored.append((score, mem))

        scored.sort(key=lambda x: x[0], reverse=True)
        results = [mem for _, mem in scored[:limit]]
        # Increment access count for recalled memories
        for mem in results:
            mem.access_count += 1
        return results

    def store_memory(
        self,
        persona: EmoPersona,
        content: str,
        emotion_tag: str,
        importance: float,
    ) -> EmoPersona:
        importance = _clamp(importance)
        now = datetime.now(timezone.utc)

        # Determine memory type
        if importance >= 0.5:
            memory_type = "long_term"
        else:
            memory_type = "short_term"

        mem = EmoMemory(
            timestamp=now,
            memory_type=memory_type,
            content=content,
            emotion_tag=emotion_tag,
            importance=importance,
            user_id="",  # filled by caller context if needed
            access_count=0,
        )
        persona.memory_bank.append(mem)
        return persona

    def grow(
        self,
        persona: EmoPersona,
        friendship_level: FriendshipLevel,
    ) -> EmoPersona:
        # Evolve personality traits
        for facet in PersonalityFacet:
            persona.personality_traits[facet] = _TRAIT_EVOLUTION[facet][friendship_level]

        # Update growth stage based on friendship depth
        depth = _friendship_level_to_depth(friendship_level)
        if depth >= 0.7:
            persona.growth_stage = GrowthStage.PREDICTIVE
        elif depth >= 0.3:
            persona.growth_stage = GrowthStage.PERSONALIZED
        else:
            persona.growth_stage = GrowthStage.GENERIC

        # Promote short-term memories with high access count to long-term
        now = datetime.now(timezone.utc)
        for mem in persona.memory_bank:
            if mem.memory_type == "short_term" and mem.access_count >= _MEMORY_PROMOTE_ACCESS_COUNT:
                mem.memory_type = "long_term"
            # Also promote short-term memories older than 24 hours
            if mem.memory_type == "short_term":
                age = now - mem.timestamp
                if age > timedelta(hours=24) and mem.importance < 0.5:
                    # Old short-term memories with low importance are kept as short_term
                    # but those with decent importance get promoted
                    pass

        persona.total_interactions += 1
        return persona

    def express_emotion(
        self,
        persona: EmoPersona,
        emotion: str,
        intensity: float,
    ) -> str:
        if persona.growth_stage == GrowthStage.GENERIC:
            return f"I feel {emotion}"
        elif persona.growth_stage == GrowthStage.PERSONALIZED:
            # Try to find a relevant memory
            memories = self.recall_memory(persona, emotion, limit=1)
            if memories:
                return f"This makes me feel {emotion}, because I remember {memories[0].content}"
            return f"This makes me feel {emotion}"
        else:  # PREDICTIVE
            facet = persona.dominant_facet
            facet_name = facet.name.lower()
            return f"I sense you might need {facet_name}, and I feel {emotion} too"

    def select_dominant_facet(
        self,
        persona: EmoPersona,
        user_emotion: str,
        friendship_level: FriendshipLevel,
    ) -> PersonalityFacet:
        emotion_upper = user_emotion.upper()
        if emotion_upper in _EMOTION_FACET_MAP:
            return _EMOTION_FACET_MAP[emotion_upper]

        # NEUTRAL or unknown emotion: depends on friendship level
        if friendship_level.value >= FriendshipLevel.CLOSE_FRIEND.value:
            return PersonalityFacet.SILENCE
        elif friendship_level.value >= FriendshipLevel.CASUAL_FRIEND.value:
            return PersonalityFacet.CURIOSITY
        else:
            return PersonalityFacet.WARMTH

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save_persona(
        self,
        persona: EmoPersona,
        user_id: str,
        db_path: str = "emofriend.db",
    ) -> None:
        data = persona.to_dict()
        data["user_id"] = user_id
        persona_json = json.dumps(data, ensure_ascii=False)
        db = Path(db_path)
        db.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(str(db)) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS emofriend_personas (
                    user_id TEXT PRIMARY KEY,
                    persona_json TEXT NOT NULL
                );
                """
            )
            conn.execute(
                """
                INSERT OR REPLACE INTO emofriend_personas (user_id, persona_json)
                VALUES (?, ?)
                """,
                (user_id, persona_json),
            )
            conn.commit()

    def load_persona(
        self,
        user_id: str,
        db_path: str = "emofriend.db",
    ) -> Optional[EmoPersona]:
        db = Path(db_path)
        if not db.exists():
            return None
        with sqlite3.connect(str(db)) as conn:
            row = conn.execute(
                """
                SELECT persona_json FROM emofriend_personas WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()

        if row is None:
            return None

        data = json.loads(row[0])
        return EmoPersona.from_dict(data)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _friendship_level_to_depth(level: FriendshipLevel) -> float:
    """Map FriendshipLevel to a representative depth value."""
    mapping = {
        FriendshipLevel.ACQUAINTANCE: 0.1,
        FriendshipLevel.CASUAL_FRIEND: 0.4,
        FriendshipLevel.CLOSE_FRIEND: 0.6,
        FriendshipLevel.SOUL_COMPANION: 0.85,
    }
    return mapping[level]
