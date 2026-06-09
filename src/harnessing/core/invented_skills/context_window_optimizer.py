from __future__ import annotations

import math
import structlog
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = structlog.get_logger()


class Priority(Enum):
    CRITICAL = 1.0
    HIGH = 0.8
    MEDIUM = 0.6
    LOW = 0.4
    DISCARDABLE = 0.2


@dataclass
class ContextSegment:
    content: str
    token_count: int
    priority: Priority
    metadata: dict[str, Any] = field(default_factory=dict)


class ContextCompressor:
    def __init__(self, compression_ratio: float = 0.7):
        self.compression_ratio = compression_ratio

    def compress(self, segment: ContextSegment) -> ContextSegment:
        if segment.token_count <= 50:
            return segment
        compressed_content = self._apply_compression(segment.content)
        compressed_tokens = int(segment.token_count * self.compression_ratio)
        return ContextSegment(
            content=compressed_content,
            token_count=compressed_tokens,
            priority=segment.priority,
            metadata={**segment.metadata, "compressed": True, "original_tokens": segment.token_count}
        )

    def _apply_compression(self, content: str) -> str:
        lines = content.split("\n")
        if len(lines) <= 3:
            return content
        summary_lines = [lines[0]]
        if len(lines) > 2:
            summary_lines.append(f"... [{len(lines) - 2} lines omitted] ...")
            summary_lines.append(lines[-1])
        return "\n".join(summary_lines)


class PriorityScorer:
    def __init__(self):
        self._keyword_weights = {
            "error": 1.5,
            "critical": 1.5,
            "important": 1.3,
            "warning": 1.2,
            "note": 1.0,
            "debug": 0.7,
            "trace": 0.5
        }

    def score(self, segment: ContextSegment) -> float:
        base_score = segment.priority.value
        content_lower = segment.content.lower()
        keyword_boost = 0.0
        for keyword, weight in self._keyword_weights.items():
            if keyword in content_lower:
                keyword_boost = max(keyword_boost, weight - 1.0)
        recency_boost = segment.metadata.get("recency_boost", 0.0)
        return min(1.0, base_score + keyword_boost * 0.1 + recency_boost)


class TokenBudgetManager:
    def __init__(self, max_tokens: int = 4096, reserve_tokens: int = 512):
        self.max_tokens = max_tokens
        self.reserve_tokens = reserve_tokens
        self.available_tokens = max_tokens - reserve_tokens

    def allocate(self, segments: list[ContextSegment]) -> tuple[list[ContextSegment], list[ContextSegment]]:
        included = []
        excluded = []
        remaining_budget = self.available_tokens
        scored_segments = [(seg, seg.token_count) for seg in segments]
        scored_segments.sort(key=lambda x: x[1])
        for segment, token_count in scored_segments:
            if token_count <= remaining_budget:
                included.append(segment)
                remaining_budget -= token_count
            else:
                excluded.append(segment)
        return included, excluded

    def get_budget_status(self) -> dict[str, int]:
        return {
            "max_tokens": self.max_tokens,
            "reserve_tokens": self.reserve_tokens,
            "available_tokens": self.available_tokens
        }


class SlidingWindowHandler:
    def __init__(self, window_size: int = 10, overlap: int = 2):
        self.window_size = window_size
        self.overlap = overlap

    def slide(self, segments: list[ContextSegment], new_segment: ContextSegment) -> list[ContextSegment]:
        result = list(segments)
        result.append(new_segment)
        if len(result) > self.window_size:
            keep_count = self.window_size - self.overlap
            result = result[-(keep_count + 1):]
        return result

    def get_window_state(self, segments: list[ContextSegment]) -> dict[str, Any]:
        return {
            "current_size": len(segments),
            "window_size": self.window_size,
            "overlap": self.overlap,
            "is_full": len(segments) >= self.window_size
        }


class ContextWindowOptimizer:
    def __init__(
        self,
        max_tokens: int = 4096,
        compression_ratio: float = 0.7,
        window_size: int = 10
    ) -> None:
        self._formula = "log(M) + K / R"
        self._capability = "context_window_optimizer"
        self._id = "INV-005"
        self.compressor = ContextCompressor(compression_ratio)
        self.priority_scorer = PriorityScorer()
        self.budget_manager = TokenBudgetManager(max_tokens)
        self.window_handler = SlidingWindowHandler(window_size)

    def analyze(self, context: list[dict[str, Any]], model_limit: int | None = None) -> dict[str, Any]:
        try:
            if model_limit:
                self.budget_manager = TokenBudgetManager(model_limit)
            segments = self._parse_context(context)
            scored_segments = self._score_segments(segments)
            compressed_segments = self._compress_if_needed(scored_segments)
            included, excluded = self.budget_manager.allocate(compressed_segments)
            result = {
                "optimized_context": [self._segment_to_dict(s) for s in included],
                "excluded_count": len(excluded),
                "total_tokens_used": sum(s.token_count for s in included),
                "budget_status": self.budget_manager.get_budget_status(),
                "compression_applied": any(s.metadata.get("compressed") for s in included)
            }
            logger.info("context_window_optimizer_success", capability=self._capability, tokens_used=result["total_tokens_used"])
            return {"status": "success", "capability": self._capability, "result": result, "formula": self._formula}
        except Exception as exc:
            logger.error("context_window_optimizer_failed", capability=self._capability, error=str(exc))
            return {"status": "error", "capability": self._capability, "error": str(exc)}

    def execute(self, context: list[dict[str, Any]], model_limit: int | None = None) -> dict[str, Any]:
        return self.analyze(context, model_limit)

    def _parse_context(self, context: list[dict[str, Any]]) -> list[ContextSegment]:
        segments = []
        for item in context:
            content = item.get("content", "")
            token_count = item.get("token_count", len(content.split()))
            priority_str = item.get("priority", "MEDIUM")
            try:
                priority = Priority[priority_str.upper()]
            except KeyError:
                priority = Priority.MEDIUM
            metadata = item.get("metadata", {})
            segments.append(ContextSegment(content=content, token_count=token_count, priority=priority, metadata=metadata))
        return segments

    def _score_segments(self, segments: list[ContextSegment]) -> list[ContextSegment]:
        for segment in segments:
            score = self.priority_scorer.score(segment)
            segment.metadata["priority_score"] = score
        return sorted(segments, key=lambda s: s.metadata.get("priority_score", 0), reverse=True)

    def _compress_if_needed(self, segments: list[ContextSegment]) -> list[ContextSegment]:
        total_tokens = sum(s.token_count for s in segments)
        if total_tokens <= self.budget_manager.available_tokens:
            return segments
        result = []
        for segment in segments:
            if segment.metadata.get("priority_score", 0) < 0.5:
                result.append(self.compressor.compress(segment))
            else:
                result.append(segment)
        return result

    def _segment_to_dict(self, segment: ContextSegment) -> dict[str, Any]:
        return {
            "content": segment.content,
            "token_count": segment.token_count,
            "priority": segment.priority.name,
            "metadata": segment.metadata
        }


if __name__ == "__main__":
    optimizer = ContextWindowOptimizer(max_tokens=1000)
    test_context = [
        {"content": "Critical error in module A", "token_count": 50, "priority": "CRITICAL"},
        {"content": "Warning: deprecated function used", "token_count": 40, "priority": "HIGH"},
        {"content": "Debug: variable x = 5", "token_count": 30, "priority": "LOW"},
        {"content": "Note: processing complete", "token_count": 25, "priority": "MEDIUM"},
        {"content": "Trace: entering function foo", "token_count": 35, "priority": "LOW"},
    ]
    result = optimizer.analyze(test_context)
    print(f"Status: {result['status']}")
    print(f"Tokens used: {result['result']['total_tokens_used']}")
    print(f"Excluded: {result['result']['excluded_count']}")
    print(f"Compression applied: {result['result']['compression_applied']}")
    assert result["status"] == "success"
    assert result["result"]["total_tokens_used"] <= 1000
    print("All tests passed!")
