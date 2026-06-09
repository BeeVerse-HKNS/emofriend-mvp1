from __future__ import annotations

import hashlib
import json
import logging
import os
import sqlite3
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class MemoEntry:
    fingerprint: str
    value: Any
    created_at: float
    last_access: float
    access_count: int


@dataclass
class CacheStats:
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    expiries: int = 0
    sets: int = 0
    errors: int = 0

    def to_dict(self) -> dict:
        return {
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "expiries": self.expiries,
            "sets": self.sets,
            "errors": self.errors,
            "total_requests": self.hits + self.misses,
            "hit_rate": round(self.hits / (self.hits + self.misses), 4) if (self.hits + self.misses) > 0 else 0.0,
        }


class MemoCache:
    DEFAULT_DB_PATH = "data/sub_agent_memo_cache.db"
    DEFAULT_MAX_SIZE = 10000
    DEFAULT_TTL_SECONDS = 3600

    def __init__(
        self,
        db_path: str = DEFAULT_DB_PATH,
        max_size: int = DEFAULT_MAX_SIZE,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
    ) -> None:
        self.db_path = db_path
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._lock = threading.RLock()
        self._stats = CacheStats()
        self._in_memory: "OrderedDict[str, MemoEntry]" = OrderedDict()
        db_dir = Path(db_path).parent
        if str(db_dir) and not db_dir.exists():
            db_dir.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS memo_entries (
                fingerprint TEXT PRIMARY KEY,
                value_json TEXT NOT NULL,
                created_at REAL NOT NULL,
                last_access REAL NOT NULL,
                access_count INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_memo_last_access ON memo_entries(last_access)"
        )
        self._conn.commit()
        self._load_from_disk()
        logger.info(
            f"memo_cache_initialized db_path={db_path} max_size={max_size} ttl={ttl_seconds}s loaded={len(self._in_memory)}"
        )

    def _load_from_disk(self) -> None:
        try:
            cursor = self._conn.execute(
                "SELECT fingerprint, value_json, created_at, last_access, access_count FROM memo_entries"
            )
            now = time.time()
            cutoff = now - self.ttl_seconds
            for row in cursor.fetchall():
                fingerprint, value_json, created_at, last_access, access_count = row
                if created_at < cutoff:
                    self._conn.execute("DELETE FROM memo_entries WHERE fingerprint = ?", (fingerprint,))
                    continue
                try:
                    value = json.loads(value_json)
                except (json.JSONDecodeError, TypeError):
                    continue
                entry = MemoEntry(
                    fingerprint=fingerprint,
                    value=value,
                    created_at=created_at,
                    last_access=last_access,
                    access_count=access_count,
                )
                self._in_memory[fingerprint] = entry
            self._conn.commit()
        except sqlite3.Error as exc:
            logger.error(f"memo_cache_load_failed error={exc}")
            self._stats.errors += 1

    @staticmethod
    def _fingerprint(prompt: str) -> str:
        normalized = prompt.strip().lower().encode("utf-8")
        return hashlib.sha256(normalized).hexdigest()

    def get(self, prompt: str) -> Optional[Any]:
        fingerprint = self._fingerprint(prompt)
        with self._lock:
            entry = self._in_memory.get(fingerprint)
            if entry is None:
                self._stats.misses += 1
                logger.debug(f"memo_cache_miss fingerprint={fingerprint[:12]}")
                return None
            now = time.time()
            if now - entry.created_at > self.ttl_seconds:
                self._stats.expiries += 1
                del self._in_memory[fingerprint]
                self._conn.execute("DELETE FROM memo_entries WHERE fingerprint = ?", (fingerprint,))
                self._conn.commit()
                logger.debug(f"memo_cache_expired fingerprint={fingerprint[:12]}")
                return None
            entry.last_access = now
            entry.access_count += 1
            self._in_memory.move_to_end(fingerprint)
            self._conn.execute(
                "UPDATE memo_entries SET last_access = ?, access_count = ? WHERE fingerprint = ?",
                (now, entry.access_count, fingerprint),
            )
            self._conn.commit()
            self._stats.hits += 1
            logger.debug(f"memo_cache_hit fingerprint={fingerprint[:12]} access_count={entry.access_count}")
            return entry.value

    def set(self, prompt: str, value: Any) -> None:
        fingerprint = self._fingerprint(prompt)
        with self._lock:
            now = time.time()
            try:
                value_json = json.dumps(value, default=str, ensure_ascii=False)
            except (TypeError, ValueError) as exc:
                logger.error(f"memo_cache_serialize_failed fingerprint={fingerprint[:12]} error={exc}")
                self._stats.errors += 1
                return
            if fingerprint in self._in_memory:
                self._in_memory.move_to_end(fingerprint)
                self._in_memory[fingerprint] = MemoEntry(
                    fingerprint=fingerprint,
                    value=value,
                    created_at=now,
                    last_access=now,
                    access_count=self._in_memory[fingerprint].access_count + 1,
                )
                self._conn.execute(
                    "UPDATE memo_entries SET value_json = ?, last_access = ?, access_count = access_count + 1 WHERE fingerprint = ?",
                    (value_json, now, fingerprint),
                )
            else:
                while len(self._in_memory) >= self.max_size:
                    evicted_fp, _ = self._in_memory.popitem(last=False)
                    self._conn.execute("DELETE FROM memo_entries WHERE fingerprint = ?", (evicted_fp,))
                    self._stats.evictions += 1
                    logger.debug(f"memo_cache_evicted fingerprint={evicted_fp[:12]}")
                entry = MemoEntry(
                    fingerprint=fingerprint,
                    value=value,
                    created_at=now,
                    last_access=now,
                    access_count=1,
                )
                self._in_memory[fingerprint] = entry
                self._conn.execute(
                    "INSERT INTO memo_entries (fingerprint, value_json, created_at, last_access, access_count) VALUES (?, ?, ?, ?, ?)",
                    (fingerprint, value_json, now, now, 1),
                )
            self._conn.commit()
            self._stats.sets += 1
            logger.debug(f"memo_cache_set fingerprint={fingerprint[:12]} size={len(self._in_memory)}")

    def get_or_compute(self, prompt: str, compute_fn: Callable[[], Any]) -> Tuple[Any, bool]:
        cached = self.get(prompt)
        if cached is not None:
            return cached, True
        try:
            value = compute_fn()
        except Exception as exc:
            logger.error(f"memo_cache_compute_failed fingerprint={self._fingerprint(prompt)[:12]} error={exc}")
            self._stats.errors += 1
            raise
        self.set(prompt, value)
        return value, False

    def invalidate(self, prompt: str) -> bool:
        fingerprint = self._fingerprint(prompt)
        with self._lock:
            if fingerprint in self._in_memory:
                del self._in_memory[fingerprint]
                self._conn.execute("DELETE FROM memo_entries WHERE fingerprint = ?", (fingerprint,))
                self._conn.commit()
                logger.info(f"memo_cache_invalidated fingerprint={fingerprint[:12]}")
                return True
            return False

    def clear(self) -> None:
        with self._lock:
            self._in_memory.clear()
            self._conn.execute("DELETE FROM memo_entries")
            self._conn.commit()
            logger.warning("memo_cache_cleared")

    def size(self) -> int:
        with self._lock:
            return len(self._in_memory)

    @property
    def stats(self) -> dict:
        with self._lock:
            snapshot = self._stats.to_dict()
            snapshot["size"] = len(self._in_memory)
            snapshot["max_size"] = self.max_size
            snapshot["ttl_seconds"] = self.ttl_seconds
            snapshot["db_path"] = self.db_path
            return snapshot

    def close(self) -> None:
        with self._lock:
            self._conn.close()
            logger.info("memo_cache_closed")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(name)s | %(levelname)s | %(message)s")

    cache = MemoCache(db_path="data/demo_memo.db", max_size=100, ttl_seconds=60)

    def expensive_compute():
        logger.info("expensive_compute_executed")
        return {"result": 42, "timestamp": time.time()}

    val1, hit1 = cache.get_or_compute("Analyze sentiment for: I love this!", expensive_compute)
    print(f"First call: hit={hit1} value={val1}")

    val2, hit2 = cache.get_or_compute("Analyze sentiment for: I love this!", expensive_compute)
    print(f"Second call (cache hit): hit={hit2} value={val2}")

    val3, hit3 = cache.get_or_compute("Translate to French: Hello world", expensive_compute)
    print(f"Third call (different key): hit={hit3}")

    print(f"\nCache stats: {cache.stats}")
    cache.close()


if __name__ == "__main__":
    main()
