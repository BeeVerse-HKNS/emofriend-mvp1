"""MD HKI Skill Router — Hierarchical Knowledge Indexer (INV-007) engine module.

Phase 5 deliverable of spec ``restructure-md-files-for-engine-efficiency``.

This module is a zero-dependency (Rule 15) Python engine that:

1. Lazily loads ``data/md_hki_index.json`` (the HKI index produced by
   ``scripts/hki_indexer.py`` — see spec Phase 2).
2. Builds in-memory indexes for O(log N) / O(1) lookup:
   - ``path_index`` — exact path (relative or absolute) → entry
   - ``l0_index`` — L0 string ``"<path> | <purpose> | updated=YYYY-MM-DD"``
   - ``topic_index`` — keyword → entries (extracted from L1)
   - ``id_index`` — ``D-NNN`` / ``IDEA-NNN`` / ``KB-NNN`` → entry
3. Exposes a stable, simple API used by ``skill_router.route_md_query``.

The router does NOT mutate the underlying HKI index; it is read-only and
is safe to call from any thread (after the first lazy load).

Per spec requirement: all public lookup methods are O(log N) or O(1).
"""

from __future__ import annotations

import json
import re
import time
from functools import lru_cache
from pathlib import Path
from typing import Any

# Repo layout assumption: this file lives at
#   src/harnessing/core/md_hki_skill_router.py
# The HKI index is at:
#   data/md_hki_index.json
_DEFAULT_INDEX_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "data"
    / "md_hki_index.json"
)

# ID patterns (D-NNN, IDEA-NNN, KB-NNN, IDEA-XXX) extracted from
# top_headings or query strings.
_D_ID_RE = re.compile(r"\bD-\d+\b")
_IDEA_ID_RE = re.compile(r"\bIDEA-\d+\b")
_KB_ID_RE = re.compile(r"\bKB-\d+\b")
_ID_RE = re.compile(r"\b(?:D|IDEA|KB)-\d+\b")

# Whitespace / punctuation splitter for fuzzy keyword scoring.
_WORD_RE = re.compile(r"[\w一-鿿]+", re.UNICODE)

# Chinese stop-words (minimal set; not a full NLP stack).
_STOPWORDS = frozenset(
    {
        "the", "a", "an", "is", "are", "of", "to", "in", "on", "for", "and",
        "or", "what", "is", "我", "你", "他", "她", "它", "的", "是", "在",
        "有", "咩", "咁", "點", "嗎", "呢", "啦", "嘅", "喺", "啦", "乜",
        "what", "where", "when", "why", "how", "does", "do", "tell", "me",
        "about", "give", "show", "find", "search", "look", "up",
    }
)


# ---------------------------------------------------------------------------
# Index loader (lazy + cached)
# ---------------------------------------------------------------------------


def _load_index_payload(index_path: Path) -> dict[str, Any]:
    """Load and return the HKI index JSON payload from disk.

    Caller is responsible for caching the result.
    """
    with open(index_path, "r", encoding="utf-8") as fh:
        return json.load(fh)


class HKISkillRouter:
    """Read-only HKI-based router for MD file lookups.

    Construction is cheap; the underlying JSON is loaded lazily on the
    first call to ``_ensure_loaded()``. Once loaded, the indexes are
    memoised at the instance level (LRU-cached ``_index`` method).
    """

    def __init__(self, index_path: Path | str | None = None) -> None:
        self._index_path = Path(index_path) if index_path else _DEFAULT_INDEX_PATH
        self._loaded: bool = False
        self._loaded_at: float = 0.0
        self._schema_version: str = ""
        self._long_files_count: int = 0
        self._entries: list[dict[str, Any]] = []
        # Lookup indexes
        self._path_index: dict[str, dict[str, Any]] = {}
        self._l0_index: dict[str, dict[str, Any]] = {}
        self._topic_index: dict[str, list[dict[str, Any]]] = {}
        self._id_index: dict[str, dict[str, Any]] = {}
        self._dir_index: dict[str, list[dict[str, Any]]] = {}
        # Heuristic single-source-of-truth for ID lookups
        self._primary_decision_entry: dict[str, Any] | None = None
        self._primary_idea_entry: dict[str, Any] | None = None
        self._primary_kb_entry: dict[str, Any] | None = None

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        payload = _load_index_payload(self._index_path)
        self._schema_version = str(payload.get("schema_version", ""))
        self._long_files_count = int(payload.get("long_files_count", 0))
        self._entries = list(payload.get("entries", []))
        self._build_indexes()
        self._loaded = True
        self._loaded_at = time.time()

    def _build_indexes(self) -> None:
        for entry in self._entries:
            rel = str(entry.get("relative_path", ""))
            abs_ = str(entry.get("absolute_path", ""))
            l0 = entry.get("l0", {}) or {}
            l1 = entry.get("l1", {}) or {}

            # 1. path_index — store both relative and absolute keys
            if rel:
                self._path_index[rel] = entry
            if abs_:
                self._path_index[abs_] = entry
                # Windows backslash normalized lookup
                norm = abs_.replace("\\", "/").lower()
                self._path_index.setdefault(norm, entry)

            # 2. l0_index — L0 summary string
            l0_path = l0.get("path", rel)
            l0_purpose = l0.get("purpose", "")
            l0_updated = l0.get("updated", "")
            l0_str = f"{l0_path} | {l0_purpose} | updated={l0_updated}"
            self._l0_index[l0_str] = entry

            # 3. topic_index — extract keywords from L1
            self._add_topics_for_entry(entry, l1, l0)

            # 4. id_index — D-/IDEA-/KB- IDs from top_headings
            self._add_ids_for_entry(entry, l1)

            # 5. dir_index — by directory group / prefix
            grp = str(entry.get("directory_group", ""))
            if grp:
                self._dir_index.setdefault(grp, []).append(entry)
            if rel:
                prefix = rel.split("/", 1)[0] if "/" in rel else "."
                self._dir_index.setdefault(prefix, []).append(entry)
                # Also index by the full path prefix
                for depth in range(1, rel.count("/") + 1):
                    sub = "/".join(rel.split("/")[:depth])
                    if sub:
                        self._dir_index.setdefault(sub, []).append(entry)

        # Compute primary ID entries (highest count wins)
        self._primary_decision_entry = self._pick_primary("decision")
        self._primary_idea_entry = self._pick_primary("idea")
        self._primary_kb_entry = self._pick_primary("kb")

    def _add_topics_for_entry(
        self, entry: dict[str, Any], l1: dict[str, Any], l0: dict[str, Any]
    ) -> None:
        """Extract topic tokens from L1 + L0 and add to topic_index."""
        tokens: set[str] = set()
        for text in (
            str(l1.get("purpose_statement", "")),
            " ".join(l1.get("top_headings", []) or []),
            str(l0.get("purpose", "")),
            str(l0.get("path", "")),
        ):
            for tok in _WORD_RE.findall(text.lower()):
                if len(tok) < 3 or tok in _STOPWORDS:
                    continue
                tokens.add(tok)
        for tok in tokens:
            self._topic_index.setdefault(tok, []).append(entry)

    def _add_ids_for_entry(
        self, entry: dict[str, Any], l1: dict[str, Any]
    ) -> None:
        """Extract D-/IDEA-/KB- IDs from top_headings into id_index."""
        for heading in l1.get("top_headings", []) or []:
            for m in _ID_RE.findall(str(heading)):
                # Keep first-seen mapping (most recent IDs surface first
                # because the indexer stores top-N headings in recency
                # order)
                self._id_index.setdefault(m, entry)

    def _pick_primary(self, kind: str) -> dict[str, Any] | None:
        """Return the entry with the highest ID count for a given kind.

        ``kind`` is one of ``"decision"``, ``"idea"``, ``"kb"``.
        """
        best: dict[str, Any] | None = None
        best_count = -1
        for entry in self._entries:
            l1 = entry.get("l1", {}) or {}
            if kind == "decision":
                c = int(l1.get("decision_id_count", 0) or 0)
            elif kind == "idea":
                c = int(l1.get("idea_id_count", 0) or 0)
            elif kind == "kb":
                c = int(l1.get("kb_id_count", 0) or 0)
            else:
                c = 0
            if c > best_count:
                best_count = c
                best = entry
        return best

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def lookup_by_path(self, path: str) -> dict[str, Any] | None:
        """Return the HKI entry for ``path`` (relative or absolute)."""
        self._ensure_loaded()
        if not path:
            return None
        # Try exact match first
        if path in self._path_index:
            return self._path_index[path]
        # Try with forward-slash normalisation
        norm = path.replace("\\", "/")
        if norm in self._path_index:
            return self._path_index[norm]
        # Try case-insensitive suffix match on basename
        basename = norm.rsplit("/", 1)[-1].lower()
        for key, entry in self._path_index.items():
            if key.rsplit("/", 1)[-1].lower() == basename and "/" in key:
                # Prefer relative paths when ambiguous
                if "/" not in path or key.endswith(norm):
                    return entry
        return None

    def lookup_by_id(self, d_or_idea_id: str) -> dict[str, Any] | None:
        """Return the HKI entry containing ``D-NNN`` or ``IDEA-NNN``.

        Falls back to the primary decision / idea entry if the specific
        ID is not in the top_headings sample (the HKI indexer keeps only
        the most recent ~8 headings per file to keep L1 token-budget).
        """
        self._ensure_loaded()
        if not d_or_idea_id:
            return None
        key = d_or_idea_id.strip().upper()
        if key in self._id_index:
            return self._id_index[key]
        if key.startswith("D-") and self._primary_decision_entry is not None:
            return self._primary_decision_entry
        if key.startswith("IDEA-") and self._primary_idea_entry is not None:
            return self._primary_idea_entry
        if key.startswith("KB-") and self._primary_kb_entry is not None:
            return self._primary_kb_entry
        return None

    def get_l0(self, path: str) -> str | None:
        """Return the L0 summary string for ``path``, or None."""
        entry = self.lookup_by_path(path)
        if entry is None:
            return None
        l0 = entry.get("l0", {}) or {}
        return (
            f"{l0.get('path', path)} | {l0.get('purpose', '')}"
            f" | updated={l0.get('updated', '')}"
            f" | refs={l0.get('refs', 0)}"
        )

    def get_l1(self, path: str) -> str | None:
        """Return the L1 summary text (purpose + headings) for ``path``."""
        entry = self.lookup_by_path(path)
        if entry is None:
            return None
        l1 = entry.get("l1", {}) or {}
        purpose = str(l1.get("purpose_statement", ""))
        headings = l1.get("top_headings", []) or []
        bullets = "\n".join(f"- {h}" for h in headings)
        return f"{purpose}\n{bullets}".strip()

    def list_by_directory(self, dir_prefix: str) -> list[dict[str, Any]]:
        """Return all entries whose path starts with ``dir_prefix``."""
        self._ensure_loaded()
        if not dir_prefix:
            return list(self._entries)
        norm = dir_prefix.replace("\\", "/").rstrip("/")
        return list(self._dir_index.get(norm, []))

    def list_by_topic(self, topic: str) -> list[dict[str, Any]]:
        """Return entries matching the topic token (case-insensitive)."""
        self._ensure_loaded()
        if not topic:
            return []
        tok = topic.lower().strip()
        return list(self._topic_index.get(tok, []))

    def stats(self) -> dict[str, Any]:
        """Return router statistics — entries, loaded-at, etc."""
        self._ensure_loaded()
        return {
            "total_entries": len(self._entries),
            "long_files_count": self._long_files_count,
            "schema_version": self._schema_version,
            "index_path": str(self._index_path),
            "loaded_at": self._loaded_at,
            "topics_indexed": len(self._topic_index),
            "ids_indexed": len(self._id_index),
            "paths_indexed": len(self._path_index),
            "directory_groups": sorted(self._dir_index.keys()),
        }

    def route_query(
        self, query: str, top_k: int = 5
    ) -> list[dict[str, Any]]:
        """Score each entry by keyword overlap and return top-k results.

        Special handling:

        * If ``query`` contains a ``D-NNN`` / ``IDEA-NNN`` / ``KB-NNN``
          ID, that ID's primary entry is injected at the top.
        * Otherwise scoring is the count of shared tokens between the
          query and the entry's combined L0 + L1 text.
        """
        self._ensure_loaded()
        if not query:
            return []
        k = max(1, int(top_k))

        # 1. ID-driven fast path
        id_match = self._extract_first_id(query)
        results: list[dict[str, Any]] = []
        if id_match is not None:
            entry = self.lookup_by_id(id_match)
            if entry is not None:
                results.append(self._decorate(entry, score=1000.0, matched_id=id_match))

        # 2. Keyword scoring
        query_tokens = self._tokenize(query)
        if not query_tokens:
            # ID matched only; still return top result if we have one
            return results[:k]

        scored: list[tuple[float, dict[str, Any]]] = []
        for entry in self._entries:
            entry_tokens = self._entry_token_set(entry)
            if not entry_tokens:
                continue
            overlap = sum(1 for t in query_tokens if t in entry_tokens)
            if overlap == 0:
                continue
            # Boost: query token in L0 purpose (3x weight per token)
            l0 = entry.get("l0", {}) or {}
            l0_purpose = str(l0.get("purpose", "")).lower()
            boost = 0.0
            for t in query_tokens:
                if t in l0_purpose:
                    boost += 3.0
                # File-name substring match (e.g., "decision" in "decision-log.md")
                if t in str(l0.get("path", "")).lower():
                    boost += 2.0
            # Boost: query token in L1 purpose_statement
            l1 = entry.get("l1", {}) or {}
            l1_purpose = str(l1.get("purpose_statement", "")).lower()
            for t in query_tokens:
                if t in l1_purpose:
                    boost += 1.5
            score = float(overlap) + boost
            scored.append((score, entry))

        # Sort by score desc, then path asc for determinism
        scored.sort(key=lambda x: (-x[0], str((x[1].get("l0") or {}).get("path", ""))))

        # Combine: ID match first, then keyword results (skip duplicates)
        seen_paths: set[str] = set()
        for entry in results:
            seen_paths.add(str((entry.get("l0") or {}).get("path", "")))
        for score, entry in scored:
            path = str((entry.get("l0") or {}).get("path", ""))
            if path in seen_paths:
                continue
            results.append(self._decorate(entry, score=score))
            seen_paths.add(path)
            if len(results) >= k:
                break
        return results[:k]

    def lookup_by_query(
        self, query: str, top_k: int = 10
    ) -> list[dict[str, Any]]:
        """Alias for :meth:`route_query` with a higher default ``top_k``."""
        return self.route_query(query, top_k=top_k)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_first_id(query: str) -> str | None:
        m = _ID_RE.search(query or "")
        return m.group(0).upper() if m else None

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return [
            t.lower()
            for t in _WORD_RE.findall(text or "")
            if len(t) >= 2 and t.lower() not in _STOPWORDS
        ]

    @lru_cache(maxsize=512)
    def _entry_token_set_cached(self, entry_path: str) -> frozenset[str]:
        # Used as a per-entry memoisation; entry_path is the unique key
        for entry in self._entries:
            if str((entry.get("l0") or {}).get("path", "")) == entry_path:
                return self._entry_token_set(entry)
        return frozenset()

    def _entry_token_set(self, entry: dict[str, Any]) -> frozenset[str]:
        l0 = entry.get("l0", {}) or {}
        l1 = entry.get("l1", {}) or {}
        text = " ".join(
            [
                str(l0.get("path", "")),
                str(l0.get("purpose", "")),
                str(l1.get("purpose_statement", "")),
                " ".join(l1.get("top_headings", []) or []),
            ]
        )
        return frozenset(self._tokenize(text))

    def _decorate(
        self,
        entry: dict[str, Any],
        score: float,
        matched_id: str | None = None,
    ) -> dict[str, Any]:
        l0 = entry.get("l0", {}) or {}
        l1 = entry.get("l1", {}) or {}
        result: dict[str, Any] = {
            "path": l0.get("path", entry.get("relative_path", "")),
            "absolute_path": entry.get("absolute_path", ""),
            "l0": l0,
            "l1": l1,
            "purpose": l0.get("purpose", ""),
            "purpose_statement": l1.get("purpose_statement", ""),
            "top_headings": list(l1.get("top_headings", []) or []),
            "decision_id_count": int(l1.get("decision_id_count", 0) or 0),
            "idea_id_count": int(l1.get("idea_id_count", 0) or 0),
            "kb_id_count": int(l1.get("kb_id_count", 0) or 0),
            "score": float(score),
            "directory_group": entry.get("directory_group", ""),
            "line_count": int(entry.get("line_count", 0) or 0),
        }
        if matched_id is not None:
            result["matched_id"] = matched_id
        return result

    # ------------------------------------------------------------------
    # Dunder
    # ------------------------------------------------------------------

    def __len__(self) -> int:
        self._ensure_loaded()
        return len(self._entries)

    def __repr__(self) -> str:
        self._ensure_loaded()
        return (
            f"HKISkillRouter(entries={len(self._entries)}, "
            f"path={self._index_path!s})"
        )


# ---------------------------------------------------------------------------
# Module-level singleton (lazy)
# ---------------------------------------------------------------------------


_DEFAULT_ROUTER: HKISkillRouter | None = None


def get_default_router() -> HKISkillRouter:
    """Return the process-wide default :class:`HKISkillRouter`."""
    global _DEFAULT_ROUTER
    if _DEFAULT_ROUTER is None:
        _DEFAULT_ROUTER = HKISkillRouter()
    return _DEFAULT_ROUTER


# ---------------------------------------------------------------------------
# Public functional API (delegates to default router)
# ---------------------------------------------------------------------------


def lookup_by_path(path: str) -> dict[str, Any] | None:
    return get_default_router().lookup_by_path(path)


def lookup_by_query(query: str, top_k: int = 10) -> list[dict[str, Any]]:
    return get_default_router().lookup_by_query(query, top_k=top_k)


def lookup_by_id(d_or_idea_id: str) -> dict[str, Any] | None:
    return get_default_router().lookup_by_id(d_or_idea_id)


def get_l0(path: str) -> str | None:
    return get_default_router().get_l0(path)


def get_l1(path: str) -> str | None:
    return get_default_router().get_l1(path)


def list_by_directory(dir_prefix: str) -> list[dict[str, Any]]:
    return get_default_router().list_by_directory(dir_prefix)


def list_by_topic(topic: str) -> list[dict[str, Any]]:
    return get_default_router().list_by_topic(topic)


def route_query(query: str, top_k: int = 5) -> list[dict[str, Any]]:
    return get_default_router().route_query(query, top_k=top_k)


def stats() -> dict[str, Any]:
    return get_default_router().stats()


__all__ = [
    "HKISkillRouter",
    "get_default_router",
    "lookup_by_path",
    "lookup_by_query",
    "lookup_by_id",
    "get_l0",
    "get_l1",
    "list_by_directory",
    "list_by_topic",
    "route_query",
    "stats",
]
