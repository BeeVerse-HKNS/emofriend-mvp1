from __future__ import annotations

import structlog
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable

logger = structlog.get_logger()


class StalenessLevel(Enum):
    FRESH = "fresh"
    SLIGHTLY_STALE = "slightly_stale"
    STALE = "stale"
    CRITICALLY_STALE = "critically_stale"


class ConflictResolutionStrategy(Enum):
    NEWEST_WINS = "newest_wins"
    SOURCE_PRIORITY = "source_priority"
    MERGE = "merge"
    MANUAL = "manual"


@dataclass
class KnowledgeSource:
    name: str
    url: str
    priority: int = 5
    last_fetched: float = 0.0
    reliability: float = 0.8
    fetch_func: Callable | None = None


@dataclass
class KnowledgeEntry:
    key: str
    value: Any
    source: str
    timestamp: float
    version: int = 1
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def age(self) -> float:
        return time.time() - self.timestamp


class StalenessDetector:
    def __init__(
        self,
        fresh_threshold: float = 3600.0,
        stale_threshold: float = 86400.0,
        critical_threshold: float = 604800.0
    ):
        self.fresh_threshold = fresh_threshold
        self.stale_threshold = stale_threshold
        self.critical_threshold = critical_threshold

    def detect(self, entry: KnowledgeEntry) -> StalenessLevel:
        age = entry.age
        if age <= self.fresh_threshold:
            return StalenessLevel.FRESH
        if age <= self.stale_threshold:
            return StalenessLevel.SLIGHTLY_STALE
        if age <= self.critical_threshold:
            return StalenessLevel.STALE
        return StalenessLevel.CRITICALLY_STALE

    def detect_batch(self, entries: list[KnowledgeEntry]) -> dict[str, StalenessLevel]:
        return {entry.key: self.detect(entry) for entry in entries}

    def get_stale_entries(self, entries: list[KnowledgeEntry]) -> list[KnowledgeEntry]:
        return [
            entry for entry in entries
            if self.detect(entry) != StalenessLevel.FRESH
        ]

    def get_update_priority(self, entry: KnowledgeEntry) -> float:
        staleness = self.detect(entry)
        priority_map = {
            StalenessLevel.FRESH: 0.0,
            StalenessLevel.SLIGHTLY_STALE: 0.3,
            StalenessLevel.STALE: 0.6,
            StalenessLevel.CRITICALLY_STALE: 1.0,
        }
        base_priority = priority_map.get(staleness, 0.5)
        importance = entry.metadata.get("importance", 0.5)
        return base_priority * 0.7 + importance * 0.3


class MultiSourceFetcher:
    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout
        self._sources: dict[str, KnowledgeSource] = {}
        self._fetch_history: list[dict[str, Any]] = []

    def register_source(self, source: KnowledgeSource) -> None:
        self._sources[source.name] = source

    def fetch(self, key: str, source_names: list[str] | None = None) -> dict[str, KnowledgeEntry]:
        results = {}
        sources_to_use = [
            self._sources[name] for name in (source_names or list(self._sources.keys()))
            if name in self._sources
        ]
        sources_to_use.sort(key=lambda s: s.priority, reverse=True)
        for source in sources_to_use:
            try:
                entry = self._fetch_from_source(key, source)
                if entry:
                    results[source.name] = entry
                    self._fetch_history.append({
                        "key": key,
                        "source": source.name,
                        "success": True,
                        "timestamp": time.time()
                    })
            except Exception as e:
                logger.warning("fetch_failed", key=key, source=source.name, error=str(e))
                self._fetch_history.append({
                    "key": key,
                    "source": source.name,
                    "success": False,
                    "error": str(e),
                    "timestamp": time.time()
                })
        return results

    def _fetch_from_source(self, key: str, source: KnowledgeSource) -> KnowledgeEntry | None:
        if source.fetch_func:
            value = source.fetch_func(key)
            if value is not None:
                return KnowledgeEntry(
                    key=key,
                    value=value,
                    source=source.name,
                    timestamp=time.time(),
                    metadata={"reliability": source.reliability}
                )
        return None

    def get_source_status(self) -> dict[str, dict[str, Any]]:
        return {
            name: {
                "priority": source.priority,
                "reliability": source.reliability,
                "last_fetched": source.last_fetched,
                "last_fetched_ago": time.time() - source.last_fetched
            }
            for name, source in self._sources.items()
        }


class ConflictResolver:
    def __init__(self, default_strategy: ConflictResolutionStrategy = ConflictResolutionStrategy.NEWEST_WINS):
        self.default_strategy = default_strategy
        self._source_priorities: dict[str, int] = {}

    def set_source_priority(self, source: str, priority: int) -> None:
        self._source_priorities[source] = priority

    def resolve(
        self,
        entries: dict[str, KnowledgeEntry],
        strategy: ConflictResolutionStrategy | None = None
    ) -> KnowledgeEntry:
        if not entries:
            raise ValueError("No entries to resolve")
        if len(entries) == 1:
            return list(entries.values())[0]
        strategy = strategy or self.default_strategy
        if strategy == ConflictResolutionStrategy.NEWEST_WINS:
            return max(entries.values(), key=lambda e: e.timestamp)
        if strategy == ConflictResolutionStrategy.SOURCE_PRIORITY:
            return max(
                entries.values(),
                key=lambda e: self._source_priorities.get(e.source, 0)
            )
        if strategy == ConflictResolutionStrategy.MERGE:
            return self._merge_entries(entries)
        return list(entries.values())[0]

    def _merge_entries(self, entries: dict[str, KnowledgeEntry]) -> KnowledgeEntry:
        sorted_entries = sorted(entries.values(), key=lambda e: e.timestamp, reverse=True)
        base_entry = sorted_entries[0]
        merged_value = base_entry.value
        if isinstance(merged_value, dict):
            for entry in sorted_entries[1:]:
                if isinstance(entry.value, dict):
                    merged_value = {**entry.value, **merged_value}
        return KnowledgeEntry(
            key=base_entry.key,
            value=merged_value,
            source="merged",
            timestamp=time.time(),
            version=max(e.version for e in entries.values()) + 1,
            metadata={"merged_from": list(entries.keys())}
        )

    def detect_conflicts(self, entries: dict[str, KnowledgeEntry]) -> bool:
        if len(entries) <= 1:
            return False
        values = [e.value for e in entries.values()]
        return len(set(str(v) for v in values)) > 1


class KnowledgeMerger:
    def __init__(self):
        self._merged_count = 0
        self._conflict_count = 0

    def merge(
        self,
        existing: KnowledgeEntry,
        new: KnowledgeEntry,
        strategy: str = "update_if_newer"
    ) -> KnowledgeEntry:
        if strategy == "update_if_newer":
            if new.timestamp > existing.timestamp:
                self._merged_count += 1
                return KnowledgeEntry(
                    key=existing.key,
                    value=new.value,
                    source=new.source,
                    timestamp=new.timestamp,
                    version=existing.version + 1,
                    metadata={**existing.metadata, "previous_source": existing.source}
                )
            return existing
        if strategy == "always_update":
            self._merged_count += 1
            return KnowledgeEntry(
                key=existing.key,
                value=new.value,
                source=new.source,
                timestamp=new.timestamp,
                version=existing.version + 1,
                metadata={**existing.metadata, "previous_source": existing.source}
            )
        if strategy == "merge_values":
            merged_value = self._merge_values(existing.value, new.value)
            self._merged_count += 1
            return KnowledgeEntry(
                key=existing.key,
                value=merged_value,
                source=f"{existing.source}+{new.source}",
                timestamp=time.time(),
                version=existing.version + 1,
                metadata={**existing.metadata, "merged": True}
            )
        return existing

    def _merge_values(self, existing: Any, new: Any) -> Any:
        if isinstance(existing, dict) and isinstance(new, dict):
            return {**existing, **new}
        if isinstance(existing, list) and isinstance(new, list):
            return list(set(existing + new))
        return new

    def get_stats(self) -> dict[str, int]:
        return {
            "merged_count": self._merged_count,
            "conflict_count": self._conflict_count
        }


class KnowledgeUpdateEngine:
    def __init__(
        self,
        stale_threshold_hours: float = 24.0,
        auto_update: bool = False
    ) -> None:
        self._formula = "K ^ P + M * S"
        self._capability = "knowledge_update_engine"
        self._id = "INV-010"
        self.stale_threshold = stale_threshold_hours * 3600
        self.auto_update = auto_update
        self.staleness_detector = StalenessDetector(
            stale_threshold=self.stale_threshold
        )
        self.multi_source_fetcher = MultiSourceFetcher()
        self.conflict_resolver = ConflictResolver()
        self.merger = KnowledgeMerger()
        self._knowledge_base: dict[str, KnowledgeEntry] = {}

    def register_source(self, source: KnowledgeSource) -> None:
        self.multi_source_fetcher.register_source(source)

    def add_entry(self, entry: KnowledgeEntry) -> None:
        self._knowledge_base[entry.key] = entry

    def get_entry(self, key: str) -> KnowledgeEntry | None:
        return self._knowledge_base.get(key)

    def analyze(self) -> dict[str, Any]:
        try:
            entries = list(self._knowledge_base.values())
            staleness_report = self.staleness_detector.detect_batch(entries)
            stale_entries = self.staleness_detector.get_stale_entries(entries)
            update_priorities = [
                {"key": e.key, "priority": self.staleness_detector.get_update_priority(e)}
                for e in stale_entries
            ]
            update_priorities.sort(key=lambda x: x["priority"], reverse=True)
            result = {
                "total_entries": len(entries),
                "staleness_distribution": {
                    level.value: sum(1 for s in staleness_report.values() if s == level)
                    for level in StalenessLevel
                },
                "stale_entries_count": len(stale_entries),
                "update_priorities": update_priorities[:10],
                "source_status": self.multi_source_fetcher.get_source_status(),
                "merger_stats": self.merger.get_stats()
            }
            logger.info(
                "knowledge_update_engine_success",
                capability=self._capability,
                stale_count=len(stale_entries)
            )
            return {"status": "success", "capability": self._capability, "result": result, "formula": self._formula}
        except Exception as exc:
            logger.error("knowledge_update_engine_failed", capability=self._capability, error=str(exc))
            return {"status": "error", "capability": self._capability, "error": str(exc)}

    def execute(self, keys: list[str] | None = None) -> dict[str, Any]:
        try:
            entries_to_update = (
                [self._knowledge_base[k] for k in keys if k in self._knowledge_base]
                if keys
                else self.staleness_detector.get_stale_entries(list(self._knowledge_base.values()))
            )
            updated = []
            conflicts = []
            for entry in entries_to_update:
                new_data = self.multi_source_fetcher.fetch(entry.key)
                if not new_data:
                    continue
                if len(new_data) > 1:
                    has_conflict = self.conflict_resolver.detect_conflicts(new_data)
                    if has_conflict:
                        conflicts.append(entry.key)
                        resolved = self.conflict_resolver.resolve(new_data)
                    else:
                        resolved = list(new_data.values())[0]
                else:
                    resolved = list(new_data.values())[0]
                merged = self.merger.merge(entry, resolved)
                self._knowledge_base[merged.key] = merged
                updated.append(merged.key)
            result = {
                "updated_count": len(updated),
                "updated_keys": updated,
                "conflicts_detected": len(conflicts),
                "conflict_keys": conflicts
            }
            logger.info("knowledge_update_executed", updated=len(updated), conflicts=len(conflicts))
            return {"status": "success", "capability": self._capability, "result": result, "formula": self._formula}
        except Exception as exc:
            logger.error("knowledge_update_execute_failed", capability=self._capability, error=str(exc))
            return {"status": "error", "capability": self._capability, "error": str(exc)}

    def force_update(self, key: str) -> dict[str, Any]:
        new_data = self.multi_source_fetcher.fetch(key)
        if not new_data:
            return {"status": "error", "error": f"No data found for key: {key}"}
        resolved = self.conflict_resolver.resolve(new_data)
        if key in self._knowledge_base:
            merged = self.merger.merge(self._knowledge_base[key], resolved)
        else:
            merged = resolved
        self._knowledge_base[merged.key] = merged
        return {"status": "success", "entry": {"key": merged.key, "source": merged.source, "timestamp": merged.timestamp}}


if __name__ == "__main__":
    engine = KnowledgeUpdateEngine(stale_threshold_hours=1.0)
    old_timestamp = time.time() - 7200
    engine.add_entry(KnowledgeEntry(
        key="api_version",
        value="1.0",
        source="initial",
        timestamp=old_timestamp,
        metadata={"importance": 0.8}
    ))
    engine.add_entry(KnowledgeEntry(
        key="config",
        value={"timeout": 30},
        source="initial",
        timestamp=time.time() - 300,
        metadata={"importance": 0.5}
    ))
    def mock_fetch(key):
        if key == "api_version":
            return "2.0"
        return None
    engine.register_source(KnowledgeSource(
        name="remote_api",
        url="https://api.example.com/knowledge",
        priority=10,
        reliability=0.9,
        fetch_func=mock_fetch
    ))
    result = engine.analyze()
    print(f"Status: {result['status']}")
    print(f"Total entries: {result['result']['total_entries']}")
    print(f"Staleness distribution: {result['result']['staleness_distribution']}")
    print(f"Stale entries: {result['result']['stale_entries_count']}")
    update_result = engine.execute()
    print(f"Update status: {update_result['status']}")
    print(f"Updated count: {update_result['result']['updated_count']}")
    print(f"Updated keys: {update_result['result']['updated_keys']}")
    assert result["status"] == "success"
    assert result["result"]["stale_entries_count"] >= 1
    print("All tests passed!")
