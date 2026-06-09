"""Model selection configuration for EmoGlyph Play.

Provides ModelConfig for model capability metadata and ModelSelector
for task-aware model routing with A/B testing rationale.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class ModelConfig:
    """Configuration for primary and fallback LLM models."""

    primary_model: str = "minimax-m3"
    fallback_model: str = "glm-5.1"

    primary_context_window: int = 1_000_000
    fallback_context_window: int = 128_000

    primary_multimodal: bool = True
    fallback_multimodal: bool = False

    primary_coding_tier: str = "top"
    fallback_coding_tier: str = "high"

    primary_cost: str = "free_on_trae"
    fallback_cost: str = "free_on_trae"


class ModelSelector:
    """Task-aware model selector with A/B testing rationale.

    Routes to the best model based on task requirements such as
    multimodal support, context size, and coding capability tier.
    """

    def __init__(self, config: ModelConfig | None = None) -> None:
        self._config = config or ModelConfig()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def select_model(
        self,
        task_type: str,
        requires_multimodal: bool = False,
        context_size: int = 0,
    ) -> str:
        """Return the best model name for the given task constraints.

        Parameters
        ----------
        task_type:
            High-level category (e.g. ``"coding"``, ``"analysis"``,
            ``"multimodal"``, ``"general"``).
        requires_multimodal:
            Whether the task needs native multimodal input.
        context_size:
            Estimated token count required.  ``0`` means "unknown / default".

        Returns
        -------
        str
            The model name to use.
        """
        cfg = self._config

        # Multimodal requirement can only be satisfied by the primary model
        if requires_multimodal and not cfg.primary_multimodal:
            # Neither model supports multimodal — still pick primary as best effort
            return cfg.primary_model

        if requires_multimodal and cfg.primary_multimodal:
            return cfg.primary_model

        # Context window check
        if context_size > 0 and context_size > cfg.primary_context_window:
            # Primary cannot fit — fallback won't either, but report primary
            # (caller should chunk the input instead)
            return cfg.primary_model

        if context_size > 0 and context_size > cfg.fallback_context_window:
            # Needs primary's larger window
            return cfg.primary_model

        # Coding-heavy tasks prefer primary (top-tier)
        if task_type == "coding" and cfg.primary_coding_tier in ("top", "high"):
            return cfg.primary_model

        # Default: primary for most tasks
        return cfg.primary_model

    def get_model_info(self, model_name: str) -> dict:
        """Return capability metadata for *model_name*.

        Raises
        ------
        ValueError
            If *model_name* is not the primary or fallback model.
        """
        cfg = self._config
        if model_name == cfg.primary_model:
            return {
                "name": cfg.primary_model,
                "context_window": cfg.primary_context_window,
                "multimodal": cfg.primary_multimodal,
                "coding_tier": cfg.primary_coding_tier,
                "cost": cfg.primary_cost,
            }
        if model_name == cfg.fallback_model:
            return {
                "name": cfg.fallback_model,
                "context_window": cfg.fallback_context_window,
                "multimodal": cfg.fallback_multimodal,
                "coding_tier": cfg.fallback_coding_tier,
                "cost": cfg.fallback_cost,
            }
        raise ValueError(
            f"Unknown model: {model_name!r}. "
            f"Expected {cfg.primary_model!r} or {cfg.fallback_model!r}."
        )

    def ab_test_rationale(self) -> str:
        """Return the A/B testing rationale for model selection.

        Explains why MiniMax-M3 is preferred as primary and GLM-5.1
        serves as fallback.
        """
        return (
            "A/B Testing Rationale — Model Selection\n"
            "========================================\n"
            "\n"
            "Primary: MiniMax-M3\n"
            "  • 1M context window — handles very large codebases, long conversations, "
            "and extensive prompt chains without chunking.\n"
            "  • Native multimodal — processes images, diagrams, and visual artifacts "
            "alongside text in a single pass.\n"
            "  • Top-tier coding — state-of-the-art code generation, refactoring, and "
            "debugging performance.\n"
            "  • TRAE Solo free — zero marginal cost within the TRAE IDE environment.\n"
            "\n"
            "Fallback: GLM-5.1\n"
            "  • ~128K context window — sufficient for most single-file and mid-size tasks.\n"
            "  • Open-source ecosystem — transparent weights, community-driven improvements.\n"
            "  • Stable and reliable — well-tested production deployment history.\n"
            "  • TRAE Solo free — also available at zero cost.\n"
            "\n"
            "Recommendation:\n"
            "  Use MiniMax-M3 as the primary model for tasks requiring large context "
            "(>128K tokens), native multimodal input, or top-tier coding capability. "
            "Fall back to GLM-5.1 when the primary is unavailable, rate-limited, or "
            "when an open-source model is explicitly preferred for transparency."
        )


__all__ = ["ModelConfig", "ModelSelector"]
