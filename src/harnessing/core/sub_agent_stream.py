from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import sqlite3
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, AsyncIterator, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class StreamStatus(Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RESUMED = "resumed"


@dataclass
class ProgressEvent:
    percent: float
    partial: Any
    checkpoint_id: Optional[str]
    step: int
    total: int
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "percent": round(self.percent, 4),
            "partial": self.partial,
            "checkpoint_id": self.checkpoint_id,
            "step": self.step,
            "total": self.total,
            "timestamp": self.timestamp,
        }


@dataclass
class CheckpointRecord:
    task_id: str
    percent: float
    last_value: Any
    step: int
    total: int
    status: StreamStatus
    updated_at: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "percent": round(self.percent, 4),
            "last_value": self.last_value,
            "step": self.step,
            "total": self.total,
            "status": self.status.value,
            "updated_at": self.updated_at,
        }


@dataclass
class StreamerStats:
    streams_started: int = 0
    streams_completed: int = 0
    streams_failed: int = 0
    streams_resumed: int = 0
    events_emitted: int = 0
    checkpoints_written: int = 0
    history: deque = field(default_factory=lambda: deque(maxlen=200))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "streams_started": self.streams_started,
            "streams_completed": self.streams_completed,
            "streams_failed": self.streams_failed,
            "streams_resumed": self.streams_resumed,
            "events_emitted": self.events_emitted,
            "checkpoints_written": self.checkpoints_written,
            "history_size": len(self.history),
        }


class Streamer:
    DEFAULT_DB_PATH = "data/sub_agent_stream_checkpoints.db"
    DEFAULT_PROGRESS_INTERVAL = 0.05

    def __init__(
        self,
        db_path: str = DEFAULT_DB_PATH,
        progress_interval: float = DEFAULT_PROGRESS_INTERVAL,
    ) -> None:
        if not 0 < progress_interval <= 1:
            raise ValueError("progress_interval must be in (0, 1]")
        self.db_path = db_path
        self.progress_interval = progress_interval
        self._stats = StreamerStats()
        db_dir = Path(db_path).parent
        if str(db_dir) and not db_dir.exists():
            db_dir.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS stream_checkpoints (
                task_id TEXT PRIMARY KEY,
                percent REAL NOT NULL,
                last_value_json TEXT,
                step INTEGER NOT NULL,
                total INTEGER NOT NULL,
                status TEXT NOT NULL,
                updated_at REAL NOT NULL,
                metadata_json TEXT
            )
            """
        )
        self._conn.commit()
        logger.info(
            f"streamer_initialized db_path={db_path} progress_interval={progress_interval}"
        )

    @staticmethod
    def _make_task_id(task_fn: Callable, total: int) -> str:
        try:
            qualname = getattr(task_fn, "__qualname__", repr(task_fn))
        except Exception:
            qualname = repr(task_fn)
        try:
            src = f"{qualname}|{total}|{int(time.time() // 3600)}"
        except Exception:
            src = f"{qualname}|{total}"
        return hashlib.sha256(src.encode("utf-8")).hexdigest()[:32]

    def _save_checkpoint(
        self,
        task_id: str,
        percent: float,
        last_value: Any,
        step: int,
        total: int,
        status: StreamStatus,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        checkpoint_id = f"{task_id}-{uuid.uuid4().hex[:8]}"
        try:
            value_json = json.dumps(last_value, default=str, ensure_ascii=False)
        except (TypeError, ValueError):
            value_json = json.dumps({"unserializable": True, "repr": str(last_value)[:1000]})
        metadata_json = json.dumps(metadata or {}, default=str, ensure_ascii=False)
        now = time.time()
        self._conn.execute(
            """
            INSERT OR REPLACE INTO stream_checkpoints
            (task_id, percent, last_value_json, step, total, status, updated_at, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task_id,
                percent,
                value_json,
                step,
                total,
                status.value,
                now,
                metadata_json,
            ),
        )
        self._conn.commit()
        self._stats.checkpoints_written += 1
        logger.debug(
            f"streamer_checkpoint_saved task_id={task_id} percent={percent:.2f}% step={step}/{total}"
        )
        return checkpoint_id

    def resume(self, task_id: str) -> float:
        cursor = self._conn.execute(
            "SELECT percent, last_value_json, step, total, status, updated_at, metadata_json "
            "FROM stream_checkpoints WHERE task_id = ?",
            (task_id,),
        )
        row = cursor.fetchone()
        if row is None:
            self._stats.streams_failed += 1
            raise KeyError(f"no_checkpoint_found task_id={task_id}")
        percent = float(row[0])
        self._stats.streams_resumed += 1
        logger.info(f"streamer_resume task_id={task_id} percent={percent:.2f}%")
        return percent

    def get_checkpoint(self, task_id: str) -> Optional[CheckpointRecord]:
        cursor = self._conn.execute(
            "SELECT task_id, percent, last_value_json, step, total, status, updated_at, metadata_json "
            "FROM stream_checkpoints WHERE task_id = ?",
            (task_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        try:
            last_value = json.loads(row[2]) if row[2] is not None else None
        except (json.JSONDecodeError, TypeError):
            last_value = None
        try:
            metadata = json.loads(row[7]) if row[7] else {}
        except (json.JSONDecodeError, TypeError):
            metadata = {}
        return CheckpointRecord(
            task_id=row[0],
            percent=float(row[1]),
            last_value=last_value,
            step=int(row[3]),
            total=int(row[4]),
            status=StreamStatus(row[5]),
            updated_at=float(row[6]),
            metadata=metadata,
        )

    def list_checkpoints(self) -> List[str]:
        cursor = self._conn.execute("SELECT task_id FROM stream_checkpoints ORDER BY updated_at DESC")
        return [row[0] for row in cursor.fetchall()]

    def delete_checkpoint(self, task_id: str) -> bool:
        cursor = self._conn.execute("DELETE FROM stream_checkpoints WHERE task_id = ?", (task_id,))
        self._conn.commit()
        return cursor.rowcount > 0

    async def stream(
        self,
        task_fn: Callable[[int], Any],
        total: int,
        task_id: Optional[str] = None,
        resume_from: float = 0.0,
    ) -> AsyncIterator[ProgressEvent]:
        if total < 1:
            raise ValueError("total must be >= 1")
        if not (0.0 <= resume_from < 1.0):
            raise ValueError("resume_from must be in [0.0, 1.0)")
        if task_id is None:
            task_id = self._make_task_id(task_fn, total)
        self._stats.streams_started += 1
        start_step = int(resume_from * total)
        if start_step > 0:
            logger.info(f"streamer_stream_resume task_id={task_id} from_percent={resume_from * 100:.2f}%")
        last_emitted_percent = resume_from
        try:
            for step in range(start_step, total):
                try:
                    maybe_coro = task_fn(step)
                    if asyncio.iscoroutine(maybe_coro):
                        partial = await maybe_coro
                    else:
                        partial = maybe_coro
                except Exception as exc:
                    self._stats.streams_failed += 1
                    self._save_checkpoint(
                        task_id,
                        last_emitted_percent * 100.0,
                        None,
                        step,
                        total,
                        StreamStatus.FAILED,
                        {"error": f"{type(exc).__name__}: {exc}"},
                    )
                    logger.error(f"streamer_stream_failed task_id={task_id} step={step} error={exc}")
                    raise
                percent = (step + 1) / total
                should_emit = (
                    percent - last_emitted_percent >= self.progress_interval
                    or percent >= 1.0
                    or step == start_step
                )
                checkpoint_id: Optional[str] = None
                if should_emit:
                    checkpoint_id = self._save_checkpoint(
                        task_id,
                        percent * 100.0,
                        partial,
                        step + 1,
                        total,
                        StreamStatus.RUNNING,
                    )
                    last_emitted_percent = percent
                event = ProgressEvent(
                    percent=percent * 100.0,
                    partial=partial,
                    checkpoint_id=checkpoint_id,
                    step=step + 1,
                    total=total,
                    metadata={"task_id": task_id},
                )
                self._stats.events_emitted += 1
                self._stats.history.append({
                    "task_id": task_id,
                    "step": step + 1,
                    "total": total,
                    "percent": percent * 100.0,
                    "timestamp": event.timestamp,
                })
                yield event
                await asyncio.sleep(0)
            self._save_checkpoint(
                task_id,
                100.0,
                None,
                total,
                total,
                StreamStatus.COMPLETED,
            )
            self._stats.streams_completed += 1
            logger.info(f"streamer_stream_completed task_id={task_id} total_steps={total}")
        except asyncio.CancelledError:
            self._save_checkpoint(
                task_id,
                last_emitted_percent * 100.0,
                None,
                start_step,
                total,
                StreamStatus.CANCELLED,
            )
            logger.warning(f"streamer_stream_cancelled task_id={task_id} percent={last_emitted_percent * 100.0:.2f}%")
            raise

    def stats(self) -> Dict[str, Any]:
        base = self._stats.to_dict()
        base["db_path"] = self.db_path
        base["progress_interval"] = self.progress_interval
        cursor = self._conn.execute("SELECT COUNT(*) FROM stream_checkpoints")
        base["checkpoints_in_db"] = cursor.fetchone()[0]
        return base

    def close(self) -> None:
        self._conn.close()
        logger.info("streamer_closed")


async def _async_double(i: int) -> int:
    await asyncio.sleep(0.001)
    return i * 2


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(name)s | %(levelname)s | %(message)s")

    async def amain() -> None:
        s = Streamer(db_path="data/demo_stream.db", progress_interval=0.1)
        print("=== Sync task_fn ===")
        emitted = []
        async for ev in s.stream(lambda i: i * 2, total=20):
            emitted.append(ev.percent)
            if ev.percent >= 0.5:
                print(f"  Reached {ev.percent:.0%}, checkpoint={ev.checkpoint_id}")
        print(f"  Emitted percents: {[round(p, 2) for p in emitted]}")
        print(f"\n=== Async task_fn ===")
        async for ev in s.stream(_async_double, total=10):
            if ev.percent >= 1.0:
                print(f"  Completed: percent={ev.percent}, value={ev.partial}")
        task_ids = s.list_checkpoints()
        print(f"\n=== Checkpoints ===")
        for tid in task_ids:
            ck = s.get_checkpoint(tid)
            if ck:
                print(f"  {tid[:12]}... -> {ck.to_dict()}")
        print(f"\nFinal stats: {s.stats()}")
        s.close()

    asyncio.run(amain())


if __name__ == "__main__":
    main()
