from __future__ import annotations

import hashlib
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class Actor(Enum):
    MASTER = "master"
    SUB = "sub"
    EXTERNAL = "external"
    UNKNOWN = "unknown"


class Winner(Enum):
    MASTER = "master"
    SUB = "sub"
    BOTH = "both"
    NEITHER = "neither"


class ConflictType(Enum):
    FILE_WRITE = "file_write"
    FILE_DELETE = "file_delete"
    TOKEN_CONSUME = "token_consume"
    RESOURCE_LOCK = "resource_lock"
    NAMESPACE_OVERLAP = "namespace_overlap"
    NONE = "none"


@dataclass
class Conflict:
    conflict_id: str
    conflict_type: ConflictType
    file_path: str
    actors: List[str]
    detected_at: float
    resolution_hint: str = ""


@dataclass
class Resolution:
    winner: Winner
    reason: str
    retry_instruction: str
    master_action_hash: str
    sub_action_hash: str
    master_score: float
    sub_score: float
    conflict: Optional[Conflict] = None
    resolved_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "winner": self.winner.value,
            "reason": self.reason,
            "retry_instruction": self.retry_instruction,
            "master_action_hash": self.master_action_hash,
            "sub_action_hash": self.sub_action_hash,
            "master_score": self.master_score,
            "sub_score": self.sub_score,
            "conflict": self.conflict.__dict__ if self.conflict else None,
            "resolved_at": self.resolved_at,
        }


@dataclass
class ResolverStats:
    actions_registered: int = 0
    conflicts_detected: int = 0
    resolutions_issued: int = 0
    master_wins: int = 0
    sub_wins: int = 0
    both_accepted: int = 0
    neither_accepted: int = 0
    exceptions: int = 0
    last_run_timestamp: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        total = max(self.resolutions_issued, 1)
        return {
            "actions_registered": self.actions_registered,
            "conflicts_detected": self.conflicts_detected,
            "resolutions_issued": self.resolutions_issued,
            "master_wins": self.master_wins,
            "sub_wins": self.sub_wins,
            "both_accepted": self.both_accepted,
            "neither_accepted": self.neither_accepted,
            "exceptions": self.exceptions,
            "last_run_timestamp": self.last_run_timestamp,
            "master_win_rate": round(self.master_wins / total, 4),
            "sub_win_rate": round(self.sub_wins / total, 4),
        }


class MasterSubAgentConflictResolver:
    PRIORITY_MATRIX: Dict[ConflictType, float] = {
        ConflictType.FILE_WRITE: 0.7,
        ConflictType.FILE_DELETE: 0.9,
        ConflictType.TOKEN_CONSUME: 0.5,
        ConflictType.RESOURCE_LOCK: 0.8,
        ConflictType.NAMESPACE_OVERLAP: 0.6,
        ConflictType.NONE: 0.1,
    }

    URGENCY_KEYWORDS: Dict[str, float] = {
        "critical": 1.0,
        "urgent": 0.9,
        "blocker": 0.95,
        "deadline": 0.85,
        "production": 0.8,
        "high": 0.7,
        "normal": 0.5,
        "low": 0.3,
        "background": 0.2,
    }

    def __init__(self, master_boost: float = 0.15) -> None:
        self._master_boost = master_boost
        self._pending: Dict[str, Dict[str, Any]] = {}
        self._file_index: Dict[str, List[str]] = {}
        self._history: List[Resolution] = []
        self._stats = ResolverStats()
        logger.info("MasterSubAgentConflictResolver initialized")

    def register_action(self, actor: str, action: dict) -> str:
        self._stats.actions_registered += 1
        action_id = f"ACT-{uuid.uuid4().hex[:8]}"
        stamped = {
            "id": action_id,
            "actor": actor,
            "action": action,
            "registered_at": time.time(),
        }
        self._pending[action_id] = stamped
        file_path = self._extract_file_path(action)
        if file_path:
            self._file_index.setdefault(file_path, []).append(action_id)
        logger.debug("Registered action %s by %s on %s", action_id, actor, file_path or "n/a")
        return action_id

    def _extract_file_path(self, action: dict) -> Optional[str]:
        for key in ("file_path", "path", "target", "resource"):
            if key in action and isinstance(action[key], str):
                return action[key]
        return None

    def detect_file_conflict(self, file_path: str) -> Optional[Conflict]:
        if file_path not in self._file_index:
            return None
        actions = self._file_index[file_path]
        if len(actions) < 2:
            return None
        actors = [self._pending[a]["actor"] for a in actions if a in self._pending]
        master_count = sum(1 for a in actors if a == "master" or a == Actor.MASTER.value)
        sub_count = sum(1 for a in actors if a == "sub" or a == Actor.SUB.value)
        if master_count >= 1 and sub_count >= 1:
            self._stats.conflicts_detected += 1
            return Conflict(
                conflict_id=f"CONF-{uuid.uuid4().hex[:8]}",
                conflict_type=ConflictType.FILE_WRITE,
                file_path=file_path,
                actors=list(set(actors)),
                detected_at=time.time(),
                resolution_hint="master and sub both target the same file",
            )
        if len(set(actors)) > 1:
            self._stats.conflicts_detected += 1
            return Conflict(
                conflict_id=f"CONF-{uuid.uuid4().hex[:8]}",
                conflict_type=ConflictType.FILE_WRITE,
                file_path=file_path,
                actors=list(set(actors)),
                detected_at=time.time(),
            )
        return None

    def resolve(
        self,
        action_master: dict,
        action_sub: dict,
        conflict: Optional[Conflict] = None,
    ) -> Resolution:
        self._stats.resolutions_issued += 1
        try:
            master_score = self._score_action(action_master, actor=Actor.MASTER)
            sub_score = self._score_action(action_sub, actor=Actor.SUB)
            if conflict is None:
                file_path = self._extract_file_path(action_master) or self._extract_file_path(action_sub)
                if file_path:
                    conflict = self.detect_file_conflict(file_path)
            winner, reason, retry = self._decide(master_score, sub_score, action_master, action_sub, conflict)
            resolution = Resolution(
                winner=winner,
                reason=reason,
                retry_instruction=retry,
                master_action_hash=self._hash_action(action_master),
                sub_action_hash=self._hash_action(action_sub),
                master_score=master_score,
                sub_score=sub_score,
                conflict=conflict,
            )
            self._apply_stats(winner)
            self._history.append(resolution)
            return resolution
        except Exception as exc:  # noqa: BLE001
            self._stats.exceptions += 1
            logger.exception("resolve failed: %s", exc)
            return Resolution(
                winner=Winner.NEITHER,
                reason=f"exception: {exc}",
                retry_instruction="retry with simplified action dicts",
                master_action_hash="",
                sub_action_hash="",
                master_score=0.0,
                sub_score=0.0,
            )

    def _score_action(self, action: dict, actor: Actor) -> float:
        base = 0.5
        ctype = self._classify_conflict_type(action)
        base += self.PRIORITY_MATRIX[ctype]
        urgency_text = (action.get("urgency") or action.get("priority") or "").lower()
        if isinstance(urgency_text, str):
            for kw, score in self.URGENCY_KEYWORDS.items():
                if kw in urgency_text:
                    base += score * 0.3
                    break
        if action.get("deadline_ts"):
            try:
                dt = float(action["deadline_ts"])
                if dt - time.time() < 3600:
                    base += 0.4
                elif dt - time.time() < 86400:
                    base += 0.2
            except (TypeError, ValueError):
                pass
        if action.get("retry_count"):
            try:
                base += min(int(action["retry_count"]) * 0.05, 0.2)
            except (TypeError, ValueError):
                pass
        if actor == Actor.MASTER:
            base += self._master_boost
        return round(base, 4)

    def _classify_conflict_type(self, action: dict) -> ConflictType:
        op = (action.get("action") or action.get("op") or "").lower()
        if op in ("write", "create", "update"):
            return ConflictType.FILE_WRITE
        if op in ("delete", "remove"):
            return ConflictType.FILE_DELETE
        if op in ("consume", "spend"):
            return ConflictType.TOKEN_CONSUME
        if op in ("lock", "acquire"):
            return ConflictType.RESOURCE_LOCK
        if op in ("namespace", "register"):
            return ConflictType.NAMESPACE_OVERLAP
        return ConflictType.NONE

    def _decide(
        self,
        master_score: float,
        sub_score: float,
        action_master: dict,
        action_sub: dict,
        conflict: Optional[Conflict],
    ) -> Tuple[Winner, str, str]:
        if abs(master_score - sub_score) < 0.05 and master_score > 0 and sub_score > 0:
            return (
                Winner.BOTH,
                "scores within 0.05 tolerance; safe to merge sequentially",
                "apply master first, then sub on top of master's output",
            )
        if master_score >= sub_score:
            return (
                Winner.MASTER,
                f"master score {master_score} >= sub score {sub_score}",
                "sub-agent should wait for master result, then re-derive",
            )
        return (
            Winner.SUB,
            f"sub score {sub_score} > master score {master_score} (urgency override)",
            "master should yield to sub-agent and re-queue after sub completes",
        )

    def _apply_stats(self, winner: Winner) -> None:
        if winner == Winner.MASTER:
            self._stats.master_wins += 1
        elif winner == Winner.SUB:
            self._stats.sub_wins += 1
        elif winner == Winner.BOTH:
            self._stats.both_accepted += 1
        else:
            self._stats.neither_accepted += 1
        self._stats.last_run_timestamp = time.time()

    def _hash_action(self, action: dict) -> str:
        canonical = json.dumps(action, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]

    def clear_pending(self) -> None:
        self._pending.clear()
        self._file_index.clear()

    def get_history(self, limit: int = 20) -> List[Resolution]:
        return self._history[-limit:]

    def stats(self) -> Dict[str, Any]:
        return self._stats.to_dict()
