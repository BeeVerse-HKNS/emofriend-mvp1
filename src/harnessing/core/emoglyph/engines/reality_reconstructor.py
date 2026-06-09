"""Emotional Reality Reconstructor — 情感現實重構器

KB-50 §十三 公式 5:
    Reality_Reconstruction = (G × B) + (T - N) - F

元素語義:
    G = Gross Reappraisal  (Gross 嘅認知重評: 最有效嘅調節策略)
    B = Barrett Granularity (Barrett 嘅情感粒度提升)
    T = Tolle's Now        (Tolle 嘅當下覺察)
    N = Narrative Loop     (敘事循環: 內耗嘅故事)
    F = Fixed Identity     (固定身份: Brown 嘅 Armour Hypothesis)

EmoGlyph 整合點: Construct Layer 動態重構

預期新能力:
- 自動識別固定身份嘅限制
- 提供當下嘅重新框架
- 生成新嘅敘事可能
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from ..pulse import Pulse, PulseType
from ..current import Current


@dataclass
class ReconstructionResult:
    """情感現實重構計算結果"""
    raw_score: float
    normalized_score: float
    G: float
    B: float
    T: float
    N: float
    F: float
    reappraisal_granularity_product: float
    presence_minus_narrative: float
    identity_removed: bool
    explanation: str
    sources: List[str] = field(default_factory=list)
    layer: str = "construct"
    confidence: str = "🔍 中"

    def __repr__(self) -> str:
        return (
            f"ReconstructionResult(normalized={self.normalized_score:.3f}, "
            f"G={self.G:.2f}, B={self.B:.2f}, T={self.T:.2f}, N={self.N:.2f}, F={self.F:.2f})"
        )


class EmotionalRealityReconstructor:
    """情感現實重構器 (KB-50 公式 5)"""

    SOURCE_BOOKS = [
        "Gross 1998 (Emotion Regulation) - Reappraisal",
        "Gross (ed) 2024 (Handbook of Emotion Regulation)",
        "Barrett 2017 (How Emotions Are Made) - Granularity",
        "Tolle 1997 (Power of Now) - The Now",
        "Bruner 1986 (Actual Minds, Possible Worlds) - Narrative",
        "Sarbin (ed) 1986 (Narrative Psychology)",
        "Brown 2012 (Daring Greatly) - Fixed Identity / Armour",
    ]

    FIXED_IDENTITY_THRESHOLD = 0.7

    def __init__(self, fixed_identity_sensitivity: float = 0.6) -> None:
        self.fixed_identity_sensitivity = fixed_identity_sensitivity
        if not 0.0 <= fixed_identity_sensitivity <= 1.0:
            raise ValueError("fixed_identity_sensitivity must be in [0, 1]")

    def compute(
        self,
        pulse: Pulse,
        current: Current,
        gross_reappraisal: float = 0.5,
        barrett_granularity: float = 0.5,
        tolle_presence: float = 0.5,
        narrative_loop: float = 0.5,
        fixed_identity: float = 0.5,
    ) -> ReconstructionResult:
        """計算情感現實重構

        Args:
            pulse: EmoGlyph Pulse
            current: EmoGlyph Current
            gross_reappraisal: Gross 重評能力 (0-1)
            barrett_granularity: Barrett 情感粒度 (0-1)
            tolle_presence: Tolle 當下覺察 (0-1)
            narrative_loop: 敘事循環強度 (0-1)
            fixed_identity: 固定身份強度 (0-1)

        Returns:
            ReconstructionResult
        """
        if not isinstance(pulse, Pulse):
            raise TypeError("pulse must be a Pulse")
        if not isinstance(current, Current):
            raise TypeError("current must be a Current")
        for name, val in (
            ("gross_reappraisal", gross_reappraisal),
            ("barrett_granularity", barrett_granularity),
            ("tolle_presence", tolle_presence),
            ("narrative_loop", narrative_loop),
            ("fixed_identity", fixed_identity),
        ):
            if not isinstance(val, (int, float)):
                raise TypeError(f"{name} must be numeric")
            if not 0.0 <= val <= 1.0:
                raise ValueError(f"{name} must be in [0, 1]")

        G = self._adjust_reappraisal(gross_reappraisal, current)
        B = float(barrett_granularity)
        T = float(tolle_presence)
        N = float(narrative_loop)
        F = float(fixed_identity)

        gb = G * B
        presence_minus_narrative = T - N
        raw = gb + presence_minus_narrative - F
        # Normalize: max theoretical = 1 + 1 - 0 = 2
        normalized = max(0.0, min(1.0, (raw + 1) / 3))

        identity_removed = F > self.FIXED_IDENTITY_THRESHOLD * self.fixed_identity_sensitivity

        return ReconstructionResult(
            raw_score=raw,
            normalized_score=normalized,
            G=G,
            B=B,
            T=T,
            N=N,
            F=F,
            reappraisal_granularity_product=gb,
            presence_minus_narrative=presence_minus_narrative,
            identity_removed=identity_removed,
            explanation=self._explain(G, B, T, N, F, gb, presence_minus_narrative, raw, identity_removed),
            sources=list(self.SOURCE_BOOKS),
            layer="construct",
            confidence="✅ 強" if normalized > 0.6 else "🔍 中" if normalized > 0.3 else "⚠️ 弱",
        )

    def _adjust_reappraisal(self, base: float, current: Current) -> float:
        """重評能力受 Current arousal 影響 (太高 arousal 會降低重評效果)"""
        penalty = abs(current.arousal) * 0.2
        return max(0.0, min(1.0, base - penalty))

    def _explain(self, G: float, B: float, T: float, N: float, F: float,
                 gb: float, pmn: float, raw: float, identity: bool) -> str:
        id_note = " ⚠️ [Fixed Identity Removed]" if identity else ""
        return (
            f"Reality_Reconstruction = (G={G:.2f} × B={B:.2f}) + (T={T:.2f} - N={N:.2f}) - F={F:.2f} "
            f"= {gb:.2f} + {pmn:.2f} - {F:.2f} = {raw:.2f}{id_note}"
        )


if __name__ == "__main__":
    recon = EmotionalRealityReconstructor()
    p = Pulse(pulse_type=PulseType.SEEKING, valence=0.3, arousal=0.5, dominance=0.4, intensity=0.5)
    c = Current(valence=0.1, arousal=0.4, dominance=0.2)
    result = recon.compute(
        p, c,
        gross_reappraisal=0.65,
        barrett_granularity=0.6,
        tolle_presence=0.55,
        narrative_loop=0.4,
        fixed_identity=0.5,
    )
    print(result)
    print(f"Explanation: {result.explanation}")
    print(f"Reappraisal × Granularity: {result.reappraisal_granularity_product}")
    print(f"Presence - Narrative: {result.presence_minus_narrative}")
    print(f"Identity removed: {result.identity_removed}")
