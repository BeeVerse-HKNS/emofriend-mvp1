from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger()

_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent

_VALID_STATUSES = {"ACTIVE", "STALE", "HIGH_RISK", "COMPLETED", "UNKNOWN"}


@dataclass
class SubprojectHiddenState:
    name: str
    health_score: float = 1.0
    entropy_value: float = 0.0
    last_active_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    pending_tasks: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    essential_context_hash: str = ""
    intervention_count: int = 0
    auto_fixed_count: int = 0
    status: str = "ACTIVE"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.status not in _VALID_STATUSES:
            self.status = "UNKNOWN"
        self.health_score = max(0.0, min(1.0, self.health_score))
        self.entropy_value = max(0.0, min(1.0, self.entropy_value))

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "health_score": self.health_score,
            "entropy_value": self.entropy_value,
            "last_active_time": self.last_active_time.isoformat(),
            "pending_tasks": self.pending_tasks,
            "dependencies": self.dependencies,
            "essential_context_hash": self.essential_context_hash,
            "intervention_count": self.intervention_count,
            "auto_fixed_count": self.auto_fixed_count,
            "status": self.status,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SubprojectHiddenState:
        last_active = data.get("last_active_time")
        if isinstance(last_active, str):
            last_active = datetime.fromisoformat(last_active)
        elif not isinstance(last_active, datetime):
            last_active = datetime.now(timezone.utc)
        return cls(
            name=data["name"],
            health_score=float(data.get("health_score", 1.0)),
            entropy_value=float(data.get("entropy_value", 0.0)),
            last_active_time=last_active,
            pending_tasks=list(data.get("pending_tasks", [])),
            dependencies=list(data.get("dependencies", [])),
            essential_context_hash=str(data.get("essential_context_hash", "")),
            intervention_count=int(data.get("intervention_count", 0)),
            auto_fixed_count=int(data.get("auto_fixed_count", 0)),
            status=str(data.get("status", "ACTIVE")),
            metadata=dict(data.get("metadata", {})),
        )


_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS hidden_states (
    name TEXT PRIMARY KEY,
    health_score REAL,
    entropy_value REAL,
    last_active_time TEXT,
    pending_tasks TEXT,
    dependencies TEXT,
    essential_context_hash TEXT,
    intervention_count INTEGER,
    auto_fixed_count INTEGER,
    status TEXT,
    metadata TEXT
)
"""

_UPSERT_SQL = """
INSERT INTO hidden_states (
    name, health_score, entropy_value, last_active_time,
    pending_tasks, dependencies, essential_context_hash,
    intervention_count, auto_fixed_count, status, metadata
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(name) DO UPDATE SET
    health_score = excluded.health_score,
    entropy_value = excluded.entropy_value,
    last_active_time = excluded.last_active_time,
    pending_tasks = excluded.pending_tasks,
    dependencies = excluded.dependencies,
    essential_context_hash = excluded.essential_context_hash,
    intervention_count = excluded.intervention_count,
    auto_fixed_count = excluded.auto_fixed_count,
    status = excluded.status,
    metadata = excluded.metadata
"""


class HiddenStateMatrix:

    def __init__(self, project_root: Path | None = None) -> None:
        self.project_root = project_root or _PROJECT_ROOT
        self.db_path = self.project_root / "data" / "subproject_hidden_states.db"
        self._states: dict[str, SubprojectHiddenState] = {}
        self._init_db()
        self._load_states()

    def _init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(_CREATE_TABLE_SQL)
            conn.commit()

    def _load_states(self) -> None:
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM hidden_states")
            for row in cursor.fetchall():
                state = self._row_to_state(row)
                self._states[state.name] = state

    def _row_to_state(self, row: sqlite3.Row) -> SubprojectHiddenState:
        return SubprojectHiddenState(
            name=row["name"],
            health_score=row["health_score"],
            entropy_value=row["entropy_value"],
            last_active_time=datetime.fromisoformat(row["last_active_time"]),
            pending_tasks=json.loads(row["pending_tasks"]),
            dependencies=json.loads(row["dependencies"]),
            essential_context_hash=row["essential_context_hash"],
            intervention_count=row["intervention_count"],
            auto_fixed_count=row["auto_fixed_count"],
            status=row["status"],
            metadata=json.loads(row["metadata"]),
        )

    def _state_to_params(self, state: SubprojectHiddenState) -> tuple:
        return (
            state.name,
            state.health_score,
            state.entropy_value,
            state.last_active_time.isoformat(),
            json.dumps(state.pending_tasks),
            json.dumps(state.dependencies),
            state.essential_context_hash,
            state.intervention_count,
            state.auto_fixed_count,
            state.status,
            json.dumps(state.metadata),
        )

    def save_state(self, state: SubprojectHiddenState) -> None:
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(_UPSERT_SQL, self._state_to_params(state))
            conn.commit()
        self._states[state.name] = state
        logger.debug("hidden_state_saved", name=state.name, status=state.status)

    def save_all(self) -> None:
        with sqlite3.connect(str(self.db_path)) as conn:
            for state in self._states.values():
                conn.execute(_UPSERT_SQL, self._state_to_params(state))
            conn.commit()
        logger.debug("all_hidden_states_saved", count=len(self._states))

    def get_state(self, name: str) -> SubprojectHiddenState | None:
        return self._states.get(name)

    def get_all_states(self) -> dict[str, SubprojectHiddenState]:
        return dict(self._states)

    def update_state(self, name: str, **kwargs: Any) -> SubprojectHiddenState:
        state = self._states.get(name)
        if state is None:
            state = SubprojectHiddenState(name=name)
        for key, value in kwargs.items():
            if hasattr(state, key):
                setattr(state, key, value)
        state.__post_init__()
        self.save_state(state)
        return state

    def discover_subprojects(self) -> list[str]:
        projects_dir = self.project_root / "projects"
        if not projects_dir.is_dir():
            logger.debug("projects_dir_not_found", path=str(projects_dir))
            return []
        discovered: list[str] = []
        for child in sorted(projects_dir.iterdir()):
            if not child.is_dir():
                continue
            has_bridge = (child / "AGENTS.md").is_file() or (child / ".harnessing-bridge.md").is_file()
            if has_bridge:
                discovered.append(child.name)
                if child.name not in self._states:
                    new_state = SubprojectHiddenState(name=child.name)
                    self.save_state(new_state)
                    logger.info("subproject_auto_created", name=child.name)
        return discovered

    def remove_state(self, name: str) -> None:
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("DELETE FROM hidden_states WHERE name = ?", (name,))
            conn.commit()
        self._states.pop(name, None)
        logger.debug("hidden_state_removed", name=name)

    def get_high_entropy_states(self, threshold: float = 0.6) -> list[SubprojectHiddenState]:
        return sorted(
            [s for s in self._states.values() if s.entropy_value >= threshold],
            key=lambda s: s.entropy_value,
            reverse=True,
        )

    def get_stale_states(self, stale_days: int = 7) -> list[SubprojectHiddenState]:
        now = datetime.now(timezone.utc)
        result: list[SubprojectHiddenState] = []
        for state in self._states.values():
            last = state.last_active_time
            if last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
            delta = (now - last).total_seconds() / 86400.0
            if delta > stale_days:
                result.append(state)
        return result

    def record_interaction(self, name: str) -> None:
        self.update_state(name, last_active_time=datetime.now(timezone.utc))

    def record_intervention(self, name: str, auto: bool = True) -> None:
        state = self._states.get(name)
        if state is None:
            state = SubprojectHiddenState(name=name)
        if auto:
            state.auto_fixed_count += 1
        else:
            state.intervention_count += 1
        self.save_state(state)
