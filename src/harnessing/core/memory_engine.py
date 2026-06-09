from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import chromadb
import structlog
from pydantic import BaseModel, Field

from harnessing.db.schema import DB_PATH
from harnessing.db.vector_store import VECTOR_DB_PATH

logger = structlog.get_logger()

_DEFAULT_DB_PATH = DB_PATH
_DEFAULT_CHROMA_PATH = VECTOR_DB_PATH


class Decision(BaseModel):
    task: str
    alternatives: list[dict[str, Any]] = Field(default_factory=list)
    chosen: str = ""
    rationale: str = ""
    outcome: str = "pending"


class ErrorRule(BaseModel):
    error_desc: str
    root_cause: str
    rule_text: str
    rule_source: str
    verified: bool = False


class UserPreference(BaseModel):
    key: str
    value: str


class SessionLog(BaseModel):
    session_id: str
    summary: str = ""
    files_changed: list[str] = Field(default_factory=list)


_CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    task TEXT NOT NULL,
    alternatives_json TEXT NOT NULL DEFAULT '[]',
    chosen TEXT NOT NULL DEFAULT '',
    rationale TEXT NOT NULL DEFAULT '',
    outcome TEXT NOT NULL DEFAULT 'pending'
);

CREATE TABLE IF NOT EXISTS error_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    error_desc TEXT NOT NULL,
    root_cause TEXT NOT NULL DEFAULT '',
    rule_text TEXT NOT NULL,
    rule_source TEXT NOT NULL DEFAULT '',
    verified INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS user_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT NOT NULL UNIQUE,
    value TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS session_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    session_id TEXT NOT NULL,
    summary TEXT NOT NULL DEFAULT '',
    files_changed_json TEXT NOT NULL DEFAULT '[]'
);
"""


class MemoryEngine:
    def __init__(
        self,
        db_path: str | Path | None = None,
        chroma_path: str | Path | None = None,
    ) -> None:
        self.db_path = Path(db_path) if db_path else _DEFAULT_DB_PATH
        self.chroma_path = Path(chroma_path) if chroma_path else _DEFAULT_CHROMA_PATH

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.chroma_path.parent.mkdir(parents=True, exist_ok=True)

        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_CREATE_TABLES_SQL)

        self._chroma_client = chromadb.PersistentClient(path=str(self.chroma_path))
        self._collection = self._chroma_client.get_or_create_collection(
            name="harnessing_memory",
            metadata={"description": "Harnessing memory engine semantic search"},
        )

        logger.info("memory_engine_initialized", db_path=str(self.db_path), chroma_path=str(self.chroma_path))

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def save_decision(
        self,
        task: str,
        alternatives: list[dict[str, Any]],
        chosen: str,
        rationale: str,
    ) -> int:
        row_id = self._save_decision_sqlite(task, alternatives, chosen, rationale)
        self._save_decision_chroma(row_id, task, alternatives, chosen, rationale)
        logger.info("decision_saved", id=row_id, task=task, chosen=chosen)
        return row_id

    def _save_decision_sqlite(
        self,
        task: str,
        alternatives: list[dict[str, Any]],
        chosen: str,
        rationale: str,
    ) -> int:
        cursor = self._conn.execute(
            "INSERT INTO decisions (timestamp, task, alternatives_json, chosen, rationale) VALUES (?, ?, ?, ?, ?)",
            (self._now(), task, json.dumps(alternatives, ensure_ascii=False), chosen, rationale),
        )
        self._conn.commit()
        return cursor.lastrowid

    def _save_decision_chroma(
        self,
        row_id: int,
        task: str,
        alternatives: list[dict[str, Any]],
        chosen: str,
        rationale: str,
    ) -> None:
        doc = f"Decision: {task} | Chosen: {chosen} | Rationale: {rationale}"
        self._collection.upsert(
            ids=[f"decision-{row_id}"],
            documents=[doc],
            metadatas=[{"type": "decision", "task": task, "chosen": chosen}],
        )

    def save_error_rule(
        self,
        error_desc: str,
        root_cause: str,
        rule_text: str,
        rule_source: str,
    ) -> int:
        cursor = self._conn.execute(
            "INSERT INTO error_rules (timestamp, error_desc, root_cause, rule_text, rule_source, verified) VALUES (?, ?, ?, ?, ?, 0)",
            (self._now(), error_desc, root_cause, rule_text, rule_source),
        )
        self._conn.commit()
        row_id = cursor.lastrowid

        doc = f"Error: {error_desc} | Rule: {rule_text} | Source: {rule_source}"
        self._collection.upsert(
            ids=[f"error_rule-{row_id}"],
            documents=[doc],
            metadatas=[{"type": "error_rule", "source": rule_source}],
        )

        logger.info("error_rule_saved", id=row_id, error=error_desc, rule=rule_text)
        return row_id

    def verify_error_rule(self, rule_id: int) -> None:
        self._conn.execute("UPDATE error_rules SET verified = 1 WHERE id = ?", (rule_id,))
        self._conn.commit()
        logger.info("error_rule_verified", id=rule_id)

    def save_preference(self, key: str, value: str) -> None:
        now = self._now()
        existing = self._conn.execute("SELECT id FROM user_preferences WHERE key = ?", (key,)).fetchone()
        if existing:
            self._conn.execute(
                "UPDATE user_preferences SET value = ?, updated_at = ? WHERE key = ?",
                (value, now, key),
            )
        else:
            self._conn.execute(
                "INSERT INTO user_preferences (key, value, updated_at) VALUES (?, ?, ?)",
                (key, value, now),
            )
        self._conn.commit()
        logger.info("preference_saved", key=key)

    def save_session_log(
        self,
        session_id: str,
        summary: str,
        files_changed: list[str],
    ) -> int:
        cursor = self._conn.execute(
            "INSERT INTO session_logs (timestamp, session_id, summary, files_changed_json) VALUES (?, ?, ?, ?)",
            (self._now(), session_id, summary, json.dumps(files_changed, ensure_ascii=False)),
        )
        self._conn.commit()
        row_id = cursor.lastrowid
        logger.info("session_log_saved", id=row_id, session_id=session_id)
        return row_id

    def recover_context(self, recent_n: int = 10) -> dict[str, Any]:
        recent_decisions = [
            dict(row)
            for row in self._conn.execute(
                "SELECT * FROM decisions ORDER BY id DESC LIMIT ?",
                (recent_n,),
            ).fetchall()
        ]

        all_rules = [
            dict(row)
            for row in self._conn.execute("SELECT * FROM error_rules ORDER BY id DESC").fetchall()
        ]

        preferences_rows = self._conn.execute("SELECT key, value FROM user_preferences").fetchall()
        preferences = {row["key"]: row["value"] for row in preferences_rows}

        last_session_row = self._conn.execute(
            "SELECT * FROM session_logs ORDER BY id DESC LIMIT 1"
        ).fetchone()
        last_session = dict(last_session_row) if last_session_row else None

        logger.info(
            "context_recovered",
            decisions_count=len(recent_decisions),
            rules_count=len(all_rules),
            preferences_count=len(preferences),
            has_last_session=last_session is not None,
        )

        return {
            "recent_decisions": recent_decisions,
            "all_rules": all_rules,
            "preferences": preferences,
            "last_session": last_session,
        }

    def search_related(self, query: str, n_results: int = 5) -> list[dict[str, Any]]:
        results = self._collection.query(query_texts=[query], n_results=n_results)
        entries: list[dict[str, Any]] = []
        ids_list = results["ids"][0] if results["ids"] else []
        docs_list = results["documents"][0] if results["documents"] else []
        meta_list = results["metadatas"][0] if results["metadatas"] else []
        dist_list = results["distances"][0] if results["distances"] else []
        for i in range(len(ids_list)):
            entries.append({
                "id": ids_list[i],
                "document": docs_list[i],
                "metadata": meta_list[i] if meta_list else None,
                "distance": dist_list[i] if dist_list else None,
            })
        return entries

    def get_rules(self) -> list[dict[str, Any]]:
        return [
            dict(row)
            for row in self._conn.execute("SELECT * FROM error_rules ORDER BY id DESC").fetchall()
        ]

    def get_preferences(self) -> dict[str, str]:
        rows = self._conn.execute("SELECT key, value FROM user_preferences").fetchall()
        return {row["key"]: row["value"] for row in rows}

    def update_decision_outcome(self, decision_id: int, outcome: str) -> None:
        self._conn.execute(
            "UPDATE decisions SET outcome = ? WHERE id = ?",
            (outcome, decision_id),
        )
        self._conn.commit()
        logger.info("decision_outcome_updated", id=decision_id, outcome=outcome)

    def close(self) -> None:
        self._conn.close()
        logger.info("memory_engine_closed")
