"""ContextCompressor — Context window compression engine.

Compresses context windows using semantic summarization, redundancy
elimination, and importance-based truncation to fit within token budgets.
"""

from __future__ import annotations


class ContextCompressor:
    """ContextCompressor — Context window compression engine.

    Provides multi-strategy context compression to reduce token usage
    while preserving the most important information.

    Args:
        default_strategy: Default compression strategy — "summarize",
            "truncate", or "hybrid".
    """

    STRATEGIES = {"summarize", "truncate", "hybrid"}
    STRATEGY_RATIOS: dict[str, float] = {
        "summarize": 0.60,
        "truncate": 0.50,
        "hybrid": 0.55,
    }

    def __init__(self, default_strategy: str = "hybrid") -> None:
        if default_strategy not in self.STRATEGIES:
            raise ValueError(
                f"Invalid strategy '{default_strategy}'. Choose from: {self.STRATEGIES}"
            )
        self.default_strategy = default_strategy

    def compress(
        self,
        context: str,
        target_tokens: int | None = None,
        strategy: str | None = None,
    ) -> dict:
        """Compress a context string to fit within a token budget.

        Args:
            context: The context string to compress.
            target_tokens: Optional target token count. If None, uses default ratio.
            strategy: Override compression strategy.

        Returns:
            Dictionary with keys: compressed, original_tokens, compressed_tokens,
            compression_ratio, strategy.
        """
        strat = strategy or self.default_strategy
        if strat not in self.STRATEGIES:
            strat = self.default_strategy

        original_tokens = len(context.split())
        ratio = self.STRATEGY_RATIOS[strat]
        target = target_tokens or max(1, int(original_tokens * ratio))

        # Stub: simple word-level truncation; real impl would use semantic compression
        words = context.split()
        if len(words) > target:
            compressed_words = words[:target]
        else:
            compressed_words = words

        compressed = " ".join(compressed_words)
        compressed_tokens = len(compressed_words)

        return {
            "compressed": compressed,
            "original_tokens": original_tokens,
            "compressed_tokens": compressed_tokens,
            "compression_ratio": round(compressed_tokens / max(1, original_tokens), 3),
            "strategy": strat,
        }

    def estimate_compressed_size(self, token_count: int, strategy: str | None = None) -> int:
        """Estimate the compressed size for a given token count.

        Args:
            token_count: Number of tokens in the original context.
            strategy: Override compression strategy.

        Returns:
            Estimated compressed token count.
        """
        strat = strategy or self.default_strategy
        ratio = self.STRATEGY_RATIOS.get(strat, 0.55)
        return max(1, int(token_count * ratio))
