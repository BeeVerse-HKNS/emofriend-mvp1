"""Resilience Amplifier — 韌性放大器

KB-50 §十三 公式 2:
    Resilience = (R + G + A) * (P^2)

元素語義:
    R = Recovery Rate  (恢復率: Davidson 嘅韌性)
    G = Growth Mindset (成長心態: Dweck)
    A = Acceptance     (接受程度: Brach 嘅 Radical Acceptance)
    P = Practice       (練習頻率: Kabat-Zinn 嘅正念練習)
    ^2 = Square (自我改善質變: 對 P 嘅二次方效果)

EmoGlyph 整合點: Enactive Layer

預期新能力:
- 自動追蹤練習頻率，預測韌性提升曲線
- 提供個性化嘅練習建議
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from ..pulse import Pulse, PulseType
from ..current import Current


@dataclass
class ResilienceResult:
    """韌性計算結果"""
    raw_score: float
    normalized_score: float
    R: float
    G: float
    A: float
    P: float
    practice_amplification: float  # P^2
    explanation: str
    sources: List[str] = field(default_factory=list)
    layer: str = "enactive"
    confidence: str = "🔍 中"

    def __repr__(self) -> str:
        return (
            f"ResilienceResult(normalized={self.normalized_score:.3f}, "
            f"R={self.R:.2f}, G={self.G:.2f}, A={self.A:.2f}, P={self.P:.2f})"
        )


class ResilienceAmplifier:
    """韌性放大器 (KB-50 公式 2)"""

    SOURCE_BOOKS = [
        "Davidson 2012 (Emotional Life of Your Brain)",
        "Davidson & Goleman 2017 (Altered Traits)",
        "Dweck 2006 (Mindset)",
        "Brach 2003 (Radical Acceptance)",
        "Kabat-Zinn 1994 (Wherever You Go)",
        "Brown 2012 (Daring Greatly - Armour Hypothesis)",
    ]

    def __init__(self, baseline_practice: float = 0.3) -> None:
        self.baseline_practice = baseline_practice
        if not 0.0 <= baseline_practice <= 1.0:
            raise ValueError("baseline_practice must be in [0, 1]")

    def compute(
        self,
        pulse: Pulse,
        current: Current,
        recovery_rate: float = 0.5,
        growth_mindset: float = 0.5,
        acceptance: float = 0.5,
        practice_frequency: Optional[float] = None,
    ) -> ResilienceResult:
        """計算韌性

        Args:
            pulse: EmoGlyph Pulse
            current: EmoGlyph Current
            recovery_rate: 恢復率 (0-1)
            growth_mindset: 成長心態 (0-1)
            acceptance: 接受程度 (0-1)
            practice_frequency: 練習頻率 (0-1)，默認為 baseline

        Returns:
            ResilienceResult
        """
        if not isinstance(pulse, Pulse):
            raise TypeError("pulse must be a Pulse")
        if not isinstance(current, Current):
            raise TypeError("current must be a Current")
        for name, val in (
            ("recovery_rate", recovery_rate),
            ("growth_mindset", growth_mindset),
            ("acceptance", acceptance),
        ):
            if not isinstance(val, (int, float)):
                raise TypeError(f"{name} must be numeric")
            if not 0.0 <= val <= 1.0:
                raise ValueError(f"{name} must be in [0, 1]")

        R = self._adjust_recovery(recovery_rate, current)
        G = float(growth_mindset)
        A = float(acceptance)
        P = float(practice_frequency) if practice_frequency is not None else self.baseline_practice
        P = max(0.0, min(1.0, P))

        p_sq = P * P  # 練習嘅平方放大
        raw = (R + G + A) * p_sq
        # Normalize: max theoretical = (1+1+1) * 1^2 = 3
        normalized = max(0.0, min(1.0, raw / 3.0))

        return ResilienceResult(
            raw_score=raw,
            normalized_score=normalized,
            R=R,
            G=G,
            A=A,
            P=P,
            practice_amplification=p_sq,
            explanation=self._explain(R, G, A, P, p_sq, raw),
            sources=list(self.SOURCE_BOOKS),
            layer="enactive",
            confidence="✅ 強" if normalized > 0.6 else "🔍 中" if normalized > 0.3 else "⚠️ 弱",
        )

    def _adjust_recovery(self, base_recovery: float, current: Current) -> float:
        """根據 Current 狀態調整恢復率 (負面情緒會降低恢復)"""
        adjustment = 1.0 + current.valence * 0.3  # -30% to +30%
        return max(0.0, min(1.0, base_recovery * adjustment))

    def _explain(self, R: float, G: float, A: float, P: float, p_sq: float, raw: float) -> str:
        return (
            f"Resilience = (R={R:.2f} + G={G:.2f} + A={A:.2f}) * P^2({P:.2f}^2={p_sq:.2f}) "
            f"= {(R + G + A):.2f} * {p_sq:.2f} = {raw:.2f}"
        )


if __name__ == "__main__":
    amp = ResilienceAmplifier(baseline_practice=0.5)
    p = Pulse(pulse_type=PulseType.FEAR, valence=-0.5, arousal=0.7, dominance=-0.4, intensity=0.6)
    c = Current(valence=-0.3, arousal=0.5, dominance=-0.2)
    result = amp.compute(
        p, c,
        recovery_rate=0.6,
        growth_mindset=0.7,
        acceptance=0.65,
        practice_frequency=0.5,
    )
    print(result)
    print(f"Explanation: {result.explanation}")
    print(f"Practice amplification: {result.practice_amplification}")
