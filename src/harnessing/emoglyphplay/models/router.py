"""MultiModelRouter — Multi-model routing and selection engine.

Routes tasks to the optimal AI model based on task complexity, cost budget,
latency requirements, and quality thresholds.
"""

from __future__ import annotations

from typing import Any


class MultiModelRouter:
    """MultiModelRouter — Multi-model routing and selection engine.

    Routes tasks to the optimal AI model based on multiple criteria
    including task complexity, cost budget, latency, and quality.

    Args:
        models: Optional list of model configuration dictionaries.
    """

    DEFAULT_MODELS: list[dict[str, Any]] = [
        {
            "id": "local-small",
            "provider": "local",
            "cost_per_1k_tokens": 0.0,
            "max_tokens": 4096,
            "quality_score": 0.6,
            "avg_latency_ms": 100,
        },
        {
            "id": "cloud-medium",
            "provider": "cloud",
            "cost_per_1k_tokens": 0.002,
            "max_tokens": 16384,
            "quality_score": 0.8,
            "avg_latency_ms": 500,
        },
        {
            "id": "cloud-large",
            "provider": "cloud",
            "cost_per_1k_tokens": 0.01,
            "max_tokens": 128000,
            "quality_score": 0.95,
            "avg_latency_ms": 1500,
        },
    ]

    def __init__(self, models: list[dict[str, Any]] | None = None) -> None:
        self.models = models or self.DEFAULT_MODELS

    def route(
        self,
        task_complexity: float,
        cost_budget: float = 1.0,
        max_latency_ms: float | None = None,
        min_quality: float = 0.0,
    ) -> dict:
        """Select the best model for a given task.

        Args:
            task_complexity: Task complexity from 0.0 (trivial) to 1.0 (very complex).
            cost_budget: Relative cost budget from 0.0 to 1.0.
            max_latency_ms: Optional maximum acceptable latency in milliseconds.
            min_quality: Minimum acceptable quality score.

        Returns:
            Dictionary with keys: model_id, provider, cost_per_1k_tokens,
            quality_score, avg_latency_ms, reasoning.
        """
        candidates = self.models

        if max_latency_ms is not None:
            candidates = [m for m in candidates if m["avg_latency_ms"] <= max_latency_ms]
        if min_quality > 0:
            candidates = [m for m in candidates if m["quality_score"] >= min_quality]

        if not candidates:
            candidates = self.models  # Fallback to all models

        # Score: balance quality and cost based on complexity and budget
        def score(m: dict) -> float:
            quality_weight = task_complexity
            cost_weight = 1.0 - cost_budget
            return m["quality_score"] * quality_weight - m["cost_per_1k_tokens"] * cost_weight * 100

        best = max(candidates, key=score)
        return {
            "model_id": best["id"],
            "provider": best["provider"],
            "cost_per_1k_tokens": best["cost_per_1k_tokens"],
            "quality_score": best["quality_score"],
            "avg_latency_ms": best["avg_latency_ms"],
            "reasoning": f"Selected {best['id']} based on complexity={task_complexity}, "
            f"budget={cost_budget}",
        }

    def list_models(self) -> list[dict]:
        """List all available models and their configurations.

        Returns:
            List of model configuration dictionaries.
        """
        return list(self.models)
