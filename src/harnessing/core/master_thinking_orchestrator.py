from __future__ import annotations

import asyncio
import re
import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .multidimensional_thinking_engine import (
    MultidimensionalThinkingEngine,
    ThinkingMode,
    ThinkingResult,
)


@dataclass
class OrchestrationResult:
    query: str
    modes_used: List[ThinkingMode]
    results: List[ThinkingResult]
    merged: str
    consensus_confidence: float
    duration_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ModeExecutionTrace:
    mode: ThinkingMode
    started_at: float
    ended_at: float
    confidence: float
    summary: str


class MasterThinkingOrchestrator:
    DEFAULT_MAX_MODES = 3

    def __init__(
        self,
        engine: Optional[MultidimensionalThinkingEngine] = None,
        reporter: Optional[Any] = None,
    ) -> None:
        self.engine = engine or MultidimensionalThinkingEngine()
        self.reporter = reporter
        self._orchestrations = 0
        self._total_modes = 0
        self._trace: List[ModeExecutionTrace] = []
        self._last_result: Optional[OrchestrationResult] = None

    async def orchestrate(self, query: str, max_modes: int = DEFAULT_MAX_MODES) -> OrchestrationResult:
        started = time.time()
        modes = self.engine.select_modes(query, max_modes=max_modes)
        coros = [self._async_think(query, m) for m in modes]
        results = await asyncio.gather(*coros)
        merged = self._merge_results(query, results)
        avg_conf = self._consensus_confidence(results)
        ended = time.time()
        self._orchestrations += 1
        self._total_modes += len(modes)
        for r in results:
            self._trace.append(ModeExecutionTrace(
                mode=r.mode,
                started_at=r.timestamp,
                ended_at=r.timestamp,
                confidence=r.confidence,
                summary=(r.content[:60] + "...") if len(r.content) > 60 else r.content,
            ))
        if len(self._trace) > 1000:
            self._trace = self._trace[-1000:]
        result = OrchestrationResult(
            query=query,
            modes_used=modes,
            results=results,
            merged=merged,
            consensus_confidence=avg_conf,
            duration_ms=(ended - started) * 1000.0,
            metadata={
                "selected_mode_count": len(modes),
                "selected_modes": [m.value for m in modes],
            },
        )
        self._last_result = result
        return result

    def orchestrate_sync(self, query: str, max_modes: int = DEFAULT_MAX_MODES) -> OrchestrationResult:
        return asyncio.run(self.orchestrate(query, max_modes=max_modes))

    async def _async_think(self, query: str, mode: ThinkingMode) -> ThinkingResult:
        result = self.engine.think(query, mode)
        await asyncio.sleep(0)
        return result

    def _merge_results(self, query: str, results: List[ThinkingResult]) -> str:
        if not results:
            return f"No results for '{query}'"
        ranked = sorted(results, key=lambda r: r.confidence, reverse=True)
        winner = ranked[0]
        sentences: List[str] = []
        sentences.append(f"[Consensus for '{query}']")
        sentences.append("")
        sentences.append(f"Primary mode: {winner.mode.value} (confidence={winner.confidence:.2f})")
        sentences.append(winner.content)
        if len(ranked) > 1:
            sentences.append("")
            sentences.append("Supporting perspectives:")
            for r in ranked[1:]:
                snippet = self._first_sentence(r.content)
                sentences.append(f"- [{r.mode.value}] {snippet}")
        agreements = self._vote_on_keywords(results)
        if agreements:
            sentences.append("")
            sentences.append("Cross-mode agreements:")
            for kw, count in agreements:
                sentences.append(f"- '{kw}' mentioned by {count}/{len(results)} modes")
        return "\n".join(sentences)

    def _consensus_confidence(self, results: List[ThinkingResult]) -> float:
        if not results:
            return 0.0
        avg = sum(r.confidence for r in results) / len(results)
        spread = max(r.confidence for r in results) - min(r.confidence for r in results)
        penalty = spread * 0.3
        return round(max(0.0, min(1.0, avg - penalty)), 4)

    def _first_sentence(self, text: str) -> str:
        for sep in [". ", "。", "!\n", "?\n"]:
            if sep in text:
                return text.split(sep, 1)[0] + sep.rstrip()
        return text[:80]

    def _vote_on_keywords(self, results: List[ThinkingResult]) -> List[tuple]:
        if not results:
            return []
        word_counters: List[Counter] = []
        for r in results:
            tokens = re.findall(r"[A-Za-z']{4,}|[\u4e00-\u9fff]{2,}", r.content)
            word_counters.append(Counter(tokens))
        if not word_counters:
            return []
        all_keys = set()
        for c in word_counters:
            all_keys.update(c.keys())
        agreements = []
        for key in all_keys:
            count = sum(1 for c in word_counters if c.get(key, 0) > 0)
            if count >= max(2, len(results) // 2 + 1):
                agreements.append((key, count))
        agreements.sort(key=lambda kv: (-kv[1], kv[0]))
        return agreements[:5]

    def get_mode_trace(self) -> List[Dict[str, Any]]:
        return [
            {
                "mode": t.mode.value,
                "started_at": t.started_at,
                "ended_at": t.ended_at,
                "confidence": t.confidence,
                "summary": t.summary,
            }
            for t in self._trace
        ]

    def get_last_result(self) -> Optional[OrchestrationResult]:
        return self._last_result

    def stats(self) -> Dict[str, Any]:
        engine_stats = self.engine.stats() if self.engine else {}
        reporter_stats = self.reporter.stats() if self.reporter else {}
        return {
            "orchestrations": self._orchestrations,
            "total_modes_run": self._total_modes,
            "trace_length": len(self._trace),
            "engine_stats": engine_stats,
            "reporter_stats": reporter_stats,
        }
