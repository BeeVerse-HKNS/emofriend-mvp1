"""Friendship Engine — EmoFriend 友誼引擎

追蹤用戶與 Emo 之間的友誼深度、信任、親密度，
根據友誼等級調整回應策略（沉默權重、共情深度、引導程度等）。

EmoGlyph 整合點: Resonance Layer + Current Layer

設計原則：
- depth 為友誼等級的主要驅動因子
- 信任來自一致性與安全感維護
- 親密度來自相互脆弱、深度沉默、情感共振
- 回應策略隨友誼等級動態調整
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import List, Optional


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


class FriendshipLevel(Enum):
    ACQUAINTANCE = 0      # depth < 0.25
    CASUAL_FRIEND = 1     # 0.25 <= depth < 0.5
    CLOSE_FRIEND = 2      # 0.5 <= depth < 0.75
    SOUL_COMPANION = 3    # depth >= 0.75


@dataclass
class SharedMoment:
    timestamp: datetime
    moment_type: str       # "vulnerability_shared", "silence_accepted", "healing_completed", "joy_shared"
    emotion_type: str      # Panksepp system name
    depth_impact: float    # how much this moment affected friendship depth
    description: str       # brief description

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "moment_type": self.moment_type,
            "emotion_type": self.emotion_type,
            "depth_impact": self.depth_impact,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SharedMoment":
        ts = data["timestamp"]
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
        return cls(
            timestamp=ts,
            moment_type=data["moment_type"],
            emotion_type=data["emotion_type"],
            depth_impact=data["depth_impact"],
            description=data["description"],
        )


@dataclass
class FriendshipState:
    user_id: str
    depth: float                              # 0.0-1.0, friendship depth
    trust: float                              # 0.0-1.0, trust level
    intimacy: float                           # 0.0-1.0, intimacy level
    first_met: Optional[datetime]             # when friendship started
    last_interaction: Optional[datetime]      # last interaction time
    interaction_count: int                    # total interactions
    shared_moments: List[SharedMoment] = field(default_factory=list)
    current_level: FriendshipLevel = FriendshipLevel.ACQUAINTANCE

    def __post_init__(self) -> None:
        self.depth = _clamp(self.depth)
        self.trust = _clamp(self.trust)
        self.intimacy = _clamp(self.intimacy)
        if self.current_level == FriendshipLevel.ACQUAINTANCE:
            self.current_level = _compute_level(self.depth)

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "depth": self.depth,
            "trust": self.trust,
            "intimacy": self.intimacy,
            "first_met": self.first_met.isoformat() if self.first_met else None,
            "last_interaction": self.last_interaction.isoformat() if self.last_interaction else None,
            "interaction_count": self.interaction_count,
            "shared_moments": [m.to_dict() for m in self.shared_moments],
            "current_level": self.current_level.value,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FriendshipState":
        first_met = data.get("first_met")
        if isinstance(first_met, str):
            first_met = datetime.fromisoformat(first_met)
        last_interaction = data.get("last_interaction")
        if isinstance(last_interaction, str):
            last_interaction = datetime.fromisoformat(last_interaction)
        moments_data = data.get("shared_moments", [])
        shared_moments = [SharedMoment.from_dict(m) for m in moments_data]
        level_val = data.get("current_level", 0)
        current_level = FriendshipLevel(level_val)
        return cls(
            user_id=data["user_id"],
            depth=data["depth"],
            trust=data["trust"],
            intimacy=data["intimacy"],
            first_met=first_met,
            last_interaction=last_interaction,
            interaction_count=data["interaction_count"],
            shared_moments=shared_moments,
            current_level=current_level,
        )


@dataclass
class ResponseStrategy:
    silence_weight: float       # 0.0-1.0, how much to use silence
    empathy_depth: float        # 0.0-1.0, how deep to go with empathy
    guidance_level: float       # 0.0-1.0, how much guidance to offer
    playfulness: float          # 0.0-1.0, how playful to be
    vulnerability_allowed: bool # whether Emo can show vulnerability
    explanation: str            # why this strategy

    def __repr__(self) -> str:
        return (
            f"ResponseStrategy(silence={self.silence_weight:.1f}, "
            f"empathy={self.empathy_depth:.1f}, guidance={self.guidance_level:.1f}, "
            f"play={self.playfulness:.1f}, vuln={self.vulnerability_allowed})"
        )


def _compute_level(depth: float) -> FriendshipLevel:
    if depth >= 0.75:
        return FriendshipLevel.SOUL_COMPANION
    elif depth >= 0.5:
        return FriendshipLevel.CLOSE_FRIEND
    elif depth >= 0.25:
        return FriendshipLevel.CASUAL_FRIEND
    else:
        return FriendshipLevel.ACQUAINTANCE


# Depth impact ranges per interaction type
_DEPTH_IMPACTS: dict[str, tuple[float, float]] = {
    "vulnerability_shared": (0.05, 0.15),
    "silence_accepted":     (0.03, 0.08),
    "healing_completed":    (0.08, 0.12),
    "joy_shared":           (0.02, 0.05),
}

# Trust increment per interaction type
_TRUST_IMPACTS: dict[str, float] = {
    "vulnerability_shared": 0.05,
    "silence_accepted":     0.03,
    "healing_completed":    0.06,
    "joy_shared":           0.02,
}

# Intimacy increment per interaction type
_INTIMACY_IMPACTS: dict[str, float] = {
    "vulnerability_shared": 0.06,
    "silence_accepted":     0.05,
    "healing_completed":    0.04,
    "joy_shared":           0.02,
}

# Response strategies per friendship level
_RESPONSE_STRATEGIES: dict[FriendshipLevel, dict] = {
    FriendshipLevel.ACQUAINTANCE: {
        "silence_weight": 0.1,
        "empathy_depth": 0.3,
        "guidance_level": 0.7,
        "playfulness": 0.2,
        "vulnerability_allowed": False,
        "explanation": "ACQUAINTANCE: 保持適度距離，提供清晰引導，低沉默權重，不展現脆弱",
    },
    FriendshipLevel.CASUAL_FRIEND: {
        "silence_weight": 0.3,
        "empathy_depth": 0.5,
        "guidance_level": 0.5,
        "playfulness": 0.4,
        "vulnerability_allowed": False,
        "explanation": "CASUAL_FRIEND: 適度沉默與共情，平衡引導，不展現脆弱",
    },
    FriendshipLevel.CLOSE_FRIEND: {
        "silence_weight": 0.6,
        "empathy_depth": 0.8,
        "guidance_level": 0.3,
        "playfulness": 0.6,
        "vulnerability_allowed": True,
        "explanation": "CLOSE_FRIEND: 深度共情與沉默，低引導，允許展現脆弱",
    },
    FriendshipLevel.SOUL_COMPANION: {
        "silence_weight": 0.8,
        "empathy_depth": 0.95,
        "guidance_level": 0.1,
        "playfulness": 0.5,
        "vulnerability_allowed": True,
        "explanation": "SOUL_COMPANION: 極深共情與沉默，極低引導，完全允許脆弱",
    },
}


class FriendshipEngine:
    """EmoFriend 友誼引擎 — 追蹤友誼狀態並調整回應策略"""

    def __init__(self, db_path: str | Path = "data/emofriend_friendships.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _init_schema(self) -> None:
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS emofriend_friendships (
                    user_id TEXT PRIMARY KEY,
                    depth REAL NOT NULL,
                    trust REAL NOT NULL,
                    intimacy REAL NOT NULL,
                    first_met TEXT,
                    last_interaction TEXT,
                    interaction_count INTEGER NOT NULL,
                    shared_moments_json TEXT NOT NULL DEFAULT '[]',
                    current_level INTEGER NOT NULL DEFAULT 0
                );
                """
            )
            conn.commit()

    def create_friendship(self, user_id: str) -> FriendshipState:
        now = datetime.now(timezone.utc)
        state = FriendshipState(
            user_id=user_id,
            depth=0.0,
            trust=0.1,
            intimacy=0.0,
            first_met=now,
            last_interaction=now,
            interaction_count=0,
            shared_moments=[],
            current_level=FriendshipLevel.ACQUAINTANCE,
        )
        self.save(state)
        return state

    def update_friendship(
        self,
        state: FriendshipState,
        interaction_type: str,
        emotion_intensity: float,
    ) -> FriendshipState:
        emotion_intensity = _clamp(emotion_intensity)

        # Compute depth impact
        lo, hi = _DEPTH_IMPACTS.get(interaction_type, (0.01, 0.03))
        depth_delta = lo + (hi - lo) * emotion_intensity
        state.depth = _clamp(state.depth + depth_delta)

        # Compute trust impact
        trust_delta = _TRUST_IMPACTS.get(interaction_type, 0.01) * emotion_intensity
        state.trust = _clamp(state.trust + trust_delta)

        # Compute intimacy impact
        intimacy_delta = _INTIMACY_IMPACTS.get(interaction_type, 0.01) * emotion_intensity
        state.intimacy = _clamp(state.intimacy + intimacy_delta)

        # Update metadata
        state.last_interaction = datetime.now(timezone.utc)
        state.interaction_count += 1
        state.current_level = _compute_level(state.depth)

        return state

    def get_friendship_level(self, state: FriendshipState) -> FriendshipLevel:
        return _compute_level(state.depth)

    def get_response_strategy(self, state: FriendshipState) -> ResponseStrategy:
        level = self.get_friendship_level(state)
        cfg = _RESPONSE_STRATEGIES[level]
        return ResponseStrategy(
            silence_weight=cfg["silence_weight"],
            empathy_depth=cfg["empathy_depth"],
            guidance_level=cfg["guidance_level"],
            playfulness=cfg["playfulness"],
            vulnerability_allowed=cfg["vulnerability_allowed"],
            explanation=cfg["explanation"],
        )

    def add_shared_moment(self, state: FriendshipState, moment: SharedMoment) -> FriendshipState:
        state.shared_moments.append(moment)
        state.depth = _clamp(state.depth + moment.depth_impact)
        state.current_level = _compute_level(state.depth)
        return state

    def can_unlock_depth(self, state: FriendshipState, required_level: FriendshipLevel) -> bool:
        return state.current_level.value >= required_level.value

    def save(self, state: FriendshipState) -> None:
        data = state.to_dict()
        moments_json = json.dumps(data["shared_moments"], ensure_ascii=False)
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO emofriend_friendships
                (user_id, depth, trust, intimacy, first_met, last_interaction,
                 interaction_count, shared_moments_json, current_level)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data["user_id"],
                    data["depth"],
                    data["trust"],
                    data["intimacy"],
                    data["first_met"],
                    data["last_interaction"],
                    data["interaction_count"],
                    moments_json,
                    data["current_level"],
                ),
            )
            conn.commit()

    def load(self, user_id: str) -> Optional[FriendshipState]:
        with sqlite3.connect(str(self.db_path)) as conn:
            row = conn.execute(
                """
                SELECT user_id, depth, trust, intimacy, first_met, last_interaction,
                       interaction_count, shared_moments_json, current_level
                FROM emofriend_friendships WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()

        if row is None:
            return None

        moments_raw = json.loads(row[7])
        return FriendshipState(
            user_id=row[0],
            depth=row[1],
            trust=row[2],
            intimacy=row[3],
            first_met=datetime.fromisoformat(row[4]) if row[4] else None,
            last_interaction=datetime.fromisoformat(row[5]) if row[5] else None,
            interaction_count=row[6],
            shared_moments=[SharedMoment.from_dict(m) for m in moments_raw],
            current_level=FriendshipLevel(row[8]),
        )


if __name__ == "__main__":
    engine = FriendshipEngine(db_path=":memory:")
    # We can't use :memory: for actual persistence, so just demonstrate the API
    state = engine.create_friendship("user_001")
    print(f"Created: {state.current_level.name}, depth={state.depth:.2f}")

    state = engine.update_friendship(state, "vulnerability_shared", 0.8)
    print(f"After vulnerability_shared: {state.current_level.name}, depth={state.depth:.2f}")

    strategy = engine.get_response_strategy(state)
    print(f"Strategy: {strategy}")

    moment = SharedMoment(
        timestamp=datetime.now(timezone.utc),
        moment_type="vulnerability_shared",
        emotion_type="CARE",
        depth_impact=0.1,
        description="User shared deep fear for the first time",
    )
    state = engine.add_shared_moment(state, moment)
    print(f"After shared moment: depth={state.depth:.2f}, moments={len(state.shared_moments)}")

    print(f"Can unlock CLOSE_FRIEND: {engine.can_unlock_depth(state, FriendshipLevel.CLOSE_FRIEND)}")
