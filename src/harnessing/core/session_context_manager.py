"""
Session-Context Manager (R-ERR-082)
D-100 Daily Learning Cycle 2026-06-03

實作 Session 同 Context 嘅清晰分離，基於 ByteDance DeerFlow 2.0 架構。
Session 結束後 Context 可獨立保存到 SQLite，Session 重啟時可恢復。

信心等級：🔍 已研究（基於 ByteDance DeerFlow 2.0 公開架構）
"""
from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Iterator, Optional


class SessionStatus(str, Enum):
    """Session 生命週期"""
    CREATED = "CREATED"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    CLOSED = "CLOSED"
    EXPIRED = "EXPIRED"


@dataclass
class Session:
    """Session 對象 — 只保存生命週期元數據"""
    id: str
    created_at: str
    last_active: str
    status: SessionStatus
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(cls, metadata: Optional[dict[str, Any]] = None) -> "Session":
        now = datetime.now(timezone.utc).isoformat()
        return cls(
            id=str(uuid.uuid4()),
            created_at=now,
            last_active=now,
            status=SessionStatus.CREATED,
            metadata=metadata or {},
        )

    def touch(self) -> None:
        """更新 last_active 時間"""
        self.last_active = datetime.now(timezone.utc).isoformat()


@dataclass
class SessionContext:
    """Context 對象 — 保存實際工作狀態，可獨立於 Session 持久化"""
    session_id: str
    state: dict[str, Any] = field(default_factory=dict)
    history: list[dict[str, Any]] = field(default_factory=list)
    working_memory: dict[str, Any] = field(default_factory=dict)

    def add_history(self, event: dict[str, Any]) -> None:
        event["timestamp"] = datetime.now(timezone.utc).isoformat()
        self.history.append(event)

    def serialize(self) -> str:
        return json.dumps(
            {
                "session_id": self.session_id,
                "state": self.state,
                "history": self.history,
                "working_memory": self.working_memory,
            },
            ensure_ascii=False,
            default=str,
        )

    @classmethod
    def deserialize(cls, blob: str) -> "SessionContext":
        data = json.loads(blob)
        return cls(
            session_id=data["session_id"],
            state=data.get("state", {}),
            history=data.get("history", []),
            working_memory=data.get("working_memory", {}),
        )


class SessionContextManager:
    """Session-Context 分離管理器 — 從文字規則升級為可執行代碼 (R-ERR-082)"""

    def __init__(self, db_path: str | Path = "data/sessions.db", retention_days: int = 30) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.retention_days = retention_days
        self._locks: dict[str, threading.RLock] = {}
        self._global_lock = threading.Lock()
        self._init_schema()

    def _init_schema(self) -> None:
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    last_active TEXT NOT NULL,
                    status TEXT NOT NULL,
                    metadata_json TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_sessions_last_active ON sessions(last_active);
                CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status);

                CREATE TABLE IF NOT EXISTS contexts (
                    session_id TEXT PRIMARY KEY,
                    state_blob TEXT NOT NULL,
                    history_json TEXT NOT NULL,
                    working_memory_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(id)
                );
                CREATE INDEX IF NOT EXISTS idx_contexts_updated_at ON contexts(updated_at);
                """
            )
            conn.commit()

    def _get_lock(self, session_id: str) -> threading.RLock:
        with self._global_lock:
            if session_id not in self._locks:
                self._locks[session_id] = threading.RLock()
            return self._locks[session_id]

    @contextmanager
    def _session_lock(self, session_id: str) -> Iterator[threading.RLock]:
        lock = self._get_lock(session_id)
        with lock:
            yield lock

    def create_session(self, metadata: Optional[dict[str, Any]] = None) -> Session:
        """創建新 Session，自動創建對應 Context"""
        session = Session.create(metadata)
        with self._session_lock(session.id):
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.execute(
                    "INSERT INTO sessions (id, created_at, last_active, status, metadata_json) VALUES (?, ?, ?, ?, ?)",
                    (
                        session.id,
                        session.created_at,
                        session.last_active,
                        session.status.value,
                        json.dumps(session.metadata, ensure_ascii=False),
                    ),
                )
                context = SessionContext(session_id=session.id)
                conn.execute(
                    """INSERT INTO contexts
                    (session_id, state_blob, history_json,
                     working_memory_json, updated_at)
                    VALUES (?, ?, ?, ?, ?)""",
                    (
                        context.session_id,
                        json.dumps(context.state),
                        json.dumps(context.history),
                        json.dumps(context.working_memory),
                        session.last_active,
                    ),
                )
                conn.commit()
        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        """查詢 Session"""
        with sqlite3.connect(str(self.db_path)) as conn:
            row = conn.execute(
                "SELECT id, created_at, last_active, status, metadata_json FROM sessions WHERE id = ?",
                (session_id,),
            ).fetchone()
        if not row:
            return None
        return Session(
            id=row[0],
            created_at=row[1],
            last_active=row[2],
            status=SessionStatus(row[3]),
            metadata=json.loads(row[4]) if row[4] else {},
        )

    def get_context(self, session_id: str) -> Optional[SessionContext]:
        """查詢 Context"""
        with sqlite3.connect(str(self.db_path)) as conn:
            row = conn.execute(
                "SELECT state_blob, history_json, working_memory_json FROM contexts WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        if not row:
            return None
        return SessionContext(
            session_id=session_id,
            state=json.loads(row[0]),
            history=json.loads(row[1]),
            working_memory=json.loads(row[2]),
        )

    def update_context(self, context: SessionContext) -> None:
        """更新 Context（獨立於 Session 操作）"""
        with self._session_lock(context.session_id):
            now = datetime.now(timezone.utc).isoformat()
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.execute(
                    """UPDATE contexts SET state_blob = ?, history_json = ?,
                    working_memory_json = ?, updated_at = ?
                    WHERE session_id = ?""",
                    (
                        json.dumps(context.state, ensure_ascii=False),
                        json.dumps(context.history, ensure_ascii=False),
                        json.dumps(context.working_memory, ensure_ascii=False),
                        now,
                        context.session_id,
                    ),
                )
                conn.execute(
                    "UPDATE sessions SET last_active = ? WHERE id = ?",
                    (now, context.session_id),
                )
                conn.commit()

    def pause_session(self, session_id: str) -> bool:
        """暫停 Session（Context 仍然保存）"""
        with self._session_lock(session_id):
            now = datetime.now(timezone.utc).isoformat()
            with sqlite3.connect(str(self.db_path)) as conn:
                cur = conn.execute(
                    "UPDATE sessions SET status = ?, last_active = ? WHERE id = ?",
                    (SessionStatus.PAUSED.value, now, session_id),
                )
                conn.commit()
                return cur.rowcount > 0

    def resume_session(self, session_id: str) -> bool:
        """恢復 Session（從 Context 完全恢復狀態）"""
        with self._session_lock(session_id):
            now = datetime.now(timezone.utc).isoformat()
            with sqlite3.connect(str(self.db_path)) as conn:
                cur = conn.execute(
                    "UPDATE sessions SET status = ?, last_active = ? WHERE id = ?",
                    (SessionStatus.ACTIVE.value, now, session_id),
                )
                conn.commit()
                return cur.rowcount > 0

    def close_session(self, session_id: str) -> bool:
        """關閉 Session（Context 仍然保留供未來查詢）"""
        with self._session_lock(session_id):
            now = datetime.now(timezone.utc).isoformat()
            with sqlite3.connect(str(self.db_path)) as conn:
                cur = conn.execute(
                    "UPDATE sessions SET status = ?, last_active = ? WHERE id = ?",
                    (SessionStatus.CLOSED.value, now, session_id),
                )
                conn.commit()
                return cur.rowcount > 0

    def serialize_context(self, session_id: str) -> Optional[str]:
        """序列化 Context 為 JSON 字串（用於匯出/備份）"""
        ctx = self.get_context(session_id)
        if not ctx:
            return None
        return ctx.serialize()

    def deserialize_context(self, blob: str) -> SessionContext:
        """反序列化 Context"""
        return SessionContext.deserialize(blob)

    def cleanup_expired(self) -> int:
        """清理過期 Context（默認 30 日歸檔）"""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=self.retention_days)).isoformat()
        with sqlite3.connect(str(self.db_path)) as conn:
            cur = conn.execute(
                "UPDATE sessions SET status = ? WHERE status IN (?, ?) AND last_active < ?",
                (SessionStatus.EXPIRED.value, SessionStatus.CLOSED.value, SessionStatus.PAUSED.value, cutoff),
            )
            conn.commit()
            return cur.rowcount

    def list_sessions(self, status: Optional[SessionStatus] = None) -> list[Session]:
        """列出 Sessions（可選按狀態過濾）"""
        with sqlite3.connect(str(self.db_path)) as conn:
            if status:
                rows = conn.execute(
                    """SELECT id, created_at, last_active, status,
                    metadata_json FROM sessions
                    WHERE status = ? ORDER BY last_active DESC""",
                    (status.value,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT id, created_at, last_active, status, metadata_json FROM sessions ORDER BY last_active DESC"
                ).fetchall()
        return [
            Session(
                id=r[0],
                created_at=r[1],
                last_active=r[2],
                status=SessionStatus(r[3]),
                metadata=json.loads(r[4]) if r[4] else {},
            )
            for r in rows
        ]
