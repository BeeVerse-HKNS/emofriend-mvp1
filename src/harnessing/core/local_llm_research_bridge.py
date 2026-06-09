from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import structlog

from harnessing.core.knowledge_base_engine import KnowledgeBaseEngine

logger = structlog.get_logger()

_DEFAULT_DB_PATH = Path(__file__).parent.parent.parent.parent / "data" / "research_cache.db"
_DEFAULT_KB_PATH = Path(__file__).parent.parent.parent.parent / "docs" / "knowledge-base"


class ConfidenceLevel(str, Enum):
    VERIFIED = "verified"
    RESEARCHED = "researched"
    INFERRED = "inferred"
    UNCERTAIN = "uncertain"


class ResearchMode(str, Enum):
    OFFLINE = "offline"
    LOCAL_FIRST = "local_first"
    HYBRID = "hybrid"


@dataclass
class ResearchResult:
    query: str
    content: str
    source: str
    confidence: ConfidenceLevel
    mode: ResearchMode
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)
    needs_external: bool = False
    pending_queue_id: str | None = None

    @property
    def confidence_symbol(self) -> str:
        symbols = {
            ConfidenceLevel.VERIFIED: "✅",
            ConfidenceLevel.RESEARCHED: "🔍",
            ConfidenceLevel.INFERRED: "⚠️",
            ConfidenceLevel.UNCERTAIN: "❌",
        }
        return symbols.get(self.confidence, "❓")


@dataclass
class PendingRequest:
    id: str
    query: str
    reason: str
    timestamp: datetime
    attempts: int = 0
    resolved: bool = False


class KnowledgeBaseSearcher:
    def __init__(self, kb_engine: KnowledgeBaseEngine | None = None) -> None:
        self._kb_engine = kb_engine or KnowledgeBaseEngine()
        self._search_count = 0

    def search(self, query: str, n_results: int = 5) -> list[tuple[str, ConfidenceLevel]]:
        self._search_count += 1
        fragments = self._kb_engine.search(query, n_results=n_results)
        results = []
        for frag in fragments:
            if frag.category == "definition":
                conf = ConfidenceLevel.VERIFIED
            elif frag.category == "case_study":
                conf = ConfidenceLevel.RESEARCHED
            else:
                conf = ConfidenceLevel.INFERRED
            results.append((frag.content, conf))
        return results

    def get_facts(self, topic: str, n: int = 5) -> list[tuple[str, ConfidenceLevel]]:
        fragments = self._kb_engine.get_facts(topic, n)
        return [(f.content, ConfidenceLevel.VERIFIED) for f in fragments]

    def stats(self) -> dict[str, Any]:
        return {
            "search_count": self._search_count,
            "kb_stats": self._kb_engine.stats(),
        }


class ResearchCache:
    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = Path(db_path) if db_path else _DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._cache_hits = 0
        self._cache_misses = 0

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS research_cache (
                    query_hash TEXT PRIMARY KEY,
                    query TEXT NOT NULL,
                    content TEXT NOT NULL,
                    source TEXT NOT NULL,
                    confidence TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    metadata TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS pending_requests (
                    id TEXT PRIMARY KEY,
                    query TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    attempts INTEGER DEFAULT 0,
                    resolved INTEGER DEFAULT 0
                )
            """)
            conn.commit()

    def _hash_query(self, query: str) -> str:
        return hashlib.sha256(query.lower().encode()).hexdigest()[:16]

    def get(self, query: str) -> ResearchResult | None:
        query_hash = self._hash_query(query)
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM research_cache WHERE query_hash = ?",
                (query_hash,),
            )
            row = cursor.fetchone()
            if row:
                self._cache_hits += 1
                return ResearchResult(
                    query=row["query"],
                    content=row["content"],
                    source=row["source"],
                    confidence=ConfidenceLevel(row["confidence"]),
                    mode=ResearchMode.OFFLINE,
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                )
        self._cache_misses += 1
        return None

    def set(self, result: ResearchResult) -> None:
        query_hash = self._hash_query(result.query)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO research_cache
                (query_hash, query, content, source, confidence, timestamp, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    query_hash,
                    result.query,
                    result.content,
                    result.source,
                    result.confidence.value,
                    result.timestamp.isoformat(),
                    json.dumps(result.metadata),
                ),
            )
            conn.commit()

    def add_pending(self, query: str, reason: str) -> str:
        import uuid
        req_id = uuid.uuid4().hex[:8]
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO pending_requests (id, query, reason, timestamp)
                VALUES (?, ?, ?, ?)
                """,
                (req_id, query, reason, datetime.now().isoformat()),
            )
            conn.commit()
        return req_id

    def get_pending(self) -> list[PendingRequest]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM pending_requests WHERE resolved = 0 ORDER BY timestamp"
            )
            return [
                PendingRequest(
                    id=row["id"],
                    query=row["query"],
                    reason=row["reason"],
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    attempts=row["attempts"],
                    resolved=bool(row["resolved"]),
                )
                for row in cursor.fetchall()
            ]

    def resolve_pending(self, req_id: str, result: ResearchResult) -> None:
        self.set(result)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE pending_requests SET resolved = 1 WHERE id = ?",
                (req_id,),
            )
            conn.commit()

    def stats(self) -> dict[str, Any]:
        with sqlite3.connect(self.db_path) as conn:
            cache_count = conn.execute(
                "SELECT COUNT(*) FROM research_cache"
            ).fetchone()[0]
            pending_count = conn.execute(
                "SELECT COUNT(*) FROM pending_requests WHERE resolved = 0"
            ).fetchone()[0]
        return {
            "cache_entries": cache_count,
            "pending_requests": pending_count,
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "hit_rate": (
                self._cache_hits / (self._cache_hits + self._cache_misses)
                if (self._cache_hits + self._cache_misses) > 0
                else 0.0
            ),
        }


class HybridResearcher:
    def __init__(
        self,
        kb_searcher: KnowledgeBaseSearcher,
        cache: ResearchCache,
    ) -> None:
        self._kb_searcher = kb_searcher
        self._cache = cache
        self._cloud_available = False

    def check_cloud_available(self) -> bool:
        try:
            from harnessing.core.llm_router import LLMRouter
            router = LLMRouter()
            self._cloud_available = len(router.available_providers) > 0
            return self._cloud_available
        except Exception:
            self._cloud_available = False
            return False

    def research(self, query: str, mode: ResearchMode = ResearchMode.LOCAL_FIRST) -> ResearchResult:
        cached = self._cache.get(query)
        if cached:
            logger.info("research_cache_hit", query=query[:50])
            return cached

        kb_results = self._kb_searcher.search(query, n_results=3)

        if kb_results:
            best_content, best_conf = kb_results[0]
            combined = "\n\n".join([c for c, _ in kb_results[:3]])
            result = ResearchResult(
                query=query,
                content=combined,
                source="knowledge_base",
                confidence=best_conf,
                mode=mode,
                metadata={"kb_results": len(kb_results)},
            )
            self._cache.set(result)
            logger.info("research_kb_success", query=query[:50], confidence=best_conf.value)
            return result

        if mode == ResearchMode.HYBRID and self._cloud_available:
            return self._cloud_research(query)

        pending_id = self._cache.add_pending(
            query, "Local resources insufficient, needs external research"
        )
        result = ResearchResult(
            query=query,
            content="[No local resources found. Research request queued for external processing.]",
            source="pending",
            confidence=ConfidenceLevel.UNCERTAIN,
            mode=mode,
            needs_external=True,
            pending_queue_id=pending_id,
        )
        logger.info("research_queued", query=query[:50], pending_id=pending_id)
        return result

    def _cloud_research(self, query: str) -> ResearchResult:
        try:
            from harnessing.core.llm_router import LLMRouter
            router = LLMRouter()
            content = router.generate(prompt=f"Research: {query}")
            result = ResearchResult(
                query=query,
                content=content,
                source="cloud_api",
                confidence=ConfidenceLevel.RESEARCHED,
                mode=ResearchMode.HYBRID,
                metadata={"provider": "cloud"},
            )
            self._cache.set(result)
            return result
        except Exception as e:
            logger.warning("cloud_research_failed", error=str(e))
            pending_id = self._cache.add_pending(query, f"Cloud research failed: {e}")
            return ResearchResult(
                query=query,
                content="[Cloud research failed. Request queued.]",
                source="pending",
                confidence=ConfidenceLevel.UNCERTAIN,
                mode=ResearchMode.HYBRID,
                needs_external=True,
                pending_queue_id=pending_id,
            )


class OfflineResearchMode:
    def __init__(
        self,
        kb_searcher: KnowledgeBaseSearcher,
        cache: ResearchCache,
    ) -> None:
        self._kb_searcher = kb_searcher
        self._cache = cache

    def research(self, query: str) -> ResearchResult:
        cached = self._cache.get(query)
        if cached:
            return cached

        kb_results = self._kb_searcher.search(query, n_results=5)

        if kb_results:
            best_content, best_conf = kb_results[0]
            combined = "\n\n".join([c for c, _ in kb_results[:5]])
            result = ResearchResult(
                query=query,
                content=combined,
                source="knowledge_base",
                confidence=best_conf,
                mode=ResearchMode.OFFLINE,
                metadata={"kb_results": len(kb_results)},
            )
            self._cache.set(result)
            return result

        return ResearchResult(
            query=query,
            content="[No local resources found. Offline mode cannot proceed.]",
            source="none",
            confidence=ConfidenceLevel.UNCERTAIN,
            mode=ResearchMode.OFFLINE,
            needs_external=True,
        )


class LocalLLMResearchBridge:
    def __init__(
        self,
        mode: ResearchMode = ResearchMode.LOCAL_FIRST,
        kb_path: Path | None = None,
        cache_path: Path | None = None,
    ) -> None:
        self.mode = mode
        self._kb_engine = KnowledgeBaseEngine(
            kb_path=kb_path,
        )
        self._kb_searcher = KnowledgeBaseSearcher(self._kb_engine)
        self._cache = ResearchCache(cache_path)
        self._hybrid = HybridResearcher(self._kb_searcher, self._cache)
        self._offline = OfflineResearchMode(self._kb_searcher, self._cache)
        self._research_count = 0
        self._success_count = 0

        logger.info(
            "local_llm_research_bridge_initialized",
            mode=mode.value,
            kb_stats=self._kb_searcher.stats(),
        )

    def research(self, query: str) -> ResearchResult:
        self._research_count += 1

        if self.mode == ResearchMode.OFFLINE:
            result = self._offline.research(query)
        else:
            result = self._hybrid.research(query, self.mode)

        if not result.needs_external:
            self._success_count += 1

        return result

    def batch_research(self, queries: list[str]) -> list[ResearchResult]:
        return [self.research(q) for q in queries]

    def get_pending_requests(self) -> list[PendingRequest]:
        return self._cache.get_pending()

    def resolve_pending(self, req_id: str, content: str, confidence: ConfidenceLevel = ConfidenceLevel.RESEARCHED) -> None:
        pending = next((p for p in self.get_pending_requests() if p.id == req_id), None)
        if pending:
            result = ResearchResult(
                query=pending.query,
                content=content,
                source="resolved",
                confidence=confidence,
                mode=self.mode,
            )
            self._cache.resolve_pending(req_id, result)

    def preload_common_research(self, topics: list[str]) -> int:
        preloaded = 0
        for topic in topics:
            result = self.research(topic)
            if not result.needs_external:
                preloaded += 1
        return preloaded

    def stats(self) -> dict[str, Any]:
        return {
            "mode": self.mode.value,
            "research_count": self._research_count,
            "success_count": self._success_count,
            "success_rate": (
                self._success_count / self._research_count
                if self._research_count > 0
                else 0.0
            ),
            "kb_searcher": self._kb_searcher.stats(),
            "cache": self._cache.stats(),
        }

    def set_mode(self, mode: ResearchMode) -> None:
        self.mode = mode
        logger.info("research_mode_changed", mode=mode.value)

    @staticmethod
    def list_modes() -> list[str]:
        return [m.value for m in ResearchMode]

    @staticmethod
    def list_confidence_levels() -> list[str]:
        return [c.value for c in ConfidenceLevel]
