"""Embodied Wisdom Synthesizer — 體現智慧合成器

KB-50 §十三 公式 4:
    Embodied_Wisdom = (S × C) + (A - M) ^ P

元素語義:
    S = Somatic Awareness  (身體覺察: Damasio 嘅 Somatic Markers)
    C = Conceptual Understanding (概念理解: Barrett 嘅 Constructed Emotion)
    A = Action Tendency    (行動傾向: Frijda 嘅 Action Tendencies)
    M = Mental Chatter     (心智噪音: Tolle 嘅 Ego)
    P = Practice Integration (實踐整合: 所有 12 書嘅實踐元素)
    ^ = 放大 (突破維度)

EmoGlyph 整合點: 5 Layer 整合輸出

預期新能力:
- 自動將文字建議轉化為身體練習
- 整合心智同身體嘅雙向回饋
- 模擬「智慧」嘅身體維度
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from ..pulse import Pulse, PulseType
from ..current import Current


@dataclass
class EmbodiedResult:
    """體現智慧計算結果"""
    raw_score: float
    normalized_score: float
    S: float
    C: float
    A: float
    M: float
    P: float
    body_mind_product: float
    pure_action: float
    practice_amplification: float
    explanation: str
    sources: List[str] = field(default_factory=list)
    layer: str = "all_layers"
    confidence: str = "🔍 中"

    def __repr__(self) -> str:
        return (
            f"EmbodiedResult(normalized={self.normalized_score:.3f}, "
            f"S={self.S:.2f}, C={self.C:.2f}, A={self.A:.2f}, M={self.M:.2f}, P={self.P:.2f})"
        )


class EmbodiedWisdomSynthesizer:
    """體現智慧合成器 (KB-50 公式 4)"""

    SOURCE_BOOKS = [
        "Damasio 1994 (Descartes' Error) - Somatic Markers",
        "Damasio 1999 (Feeling of What Happens)",
        "Barrett 2017 (How Emotions Are Made) - Constructed Emotion",
        "Frijda 1986 (Emotions)",
        "Tolle 1997 (Power of Now) - Ego / Mental Chatter",
        "Varela, Thompson, Rosch 1991 (Embodied Mind)",
        "Clark 1997 (Being There)",
        "Kabat-Zinn 1994 (Wherever You Go) - Practice Integration",
    ]

    def __init__(self) -> None:
        pass

    def compute(
        self,
        pulse: Pulse,
        current: Current,
        somatic_awareness: float = 0.5,
        conceptual_understanding: float = 0.5,
        action_tendency: float = 0.5,
        mental_chatter: float = 0.5,
        practice_integration: float = 0.5,
    ) -> EmbodiedResult:
        """計算體現智慧

        Args:
            pulse: EmoGlyph Pulse
            current: EmoGlyph Current
            somatic_awareness: 身體覺察 (0-1)
            conceptual_understanding: 概念理解 (0-1)
            action_tendency: 行動傾向 (0-1)
            mental_chatter: 心智噪音 (0-1)
            practice_integration: 實踐整合 (0-1)

        Returns:
            EmbodiedResult
        """
        if not isinstance(pulse, Pulse):
            raise TypeError("pulse must be a Pulse")
        if not isinstance(current, Current):
            raise TypeError("current must be a Current")
        for name, val in (
            ("somatic_awareness", somatic_awareness),
            ("conceptual_understanding", conceptual_understanding),
            ("action_tendency", action_tendency),
            ("mental_chatter", mental_chatter),
            ("practice_integration", practice_integration),
        ):
            if not isinstance(val, (int, float)):
                raise TypeError(f"{name} must be numeric")
            if not 0.0 <= val <= 1.0:
                raise ValueError(f"{name} must be in [0, 1]")

        S = self._adjust_somatic(somatic_awareness, current)
        C = float(conceptual_understanding)
        A = float(action_tendency)
        M = float(mental_chatter)
        P = float(practice_integration)

        body_mind = S * C
        pure_action = A - M
        # Practice amplification: (pure_action) ^ P
        # If pure_action is negative, use abs + sign tracking
        if pure_action < 0:
            amplification = -((abs(pure_action)) ** P)
        else:
            amplification = pure_action ** P

        raw = body_mind + amplification
        # Normalize: max theoretical = (1*1) + 1^1 = 2
        normalized = max(0.0, min(1.0, (raw + 1) / 3))  # shift by 1 to handle negative

        return EmbodiedResult(
            raw_score=raw,
            normalized_score=normalized,
            S=S,
            C=C,
            A=A,
            M=M,
            P=P,
            body_mind_product=body_mind,
            pure_action=pure_action,
            practice_amplification=amplification,
            explanation=self._explain(S, C, A, M, P, body_mind, pure_action, amplification, raw),
            sources=list(self.SOURCE_BOOKS),
            layer="all_layers",
            confidence="✅ 強" if normalized > 0.6 else "🔍 中" if normalized > 0.3 else "⚠️ 弱",
        )

    def _adjust_somatic(self, base: float, current: Current) -> float:
        """身體覺察會被 Current 嘅 arousal 放大 (身體反應越強越易覺察)"""
        adjustment = 1.0 + abs(current.arousal) * 0.3
        return max(0.0, min(1.0, base * adjustment))

    def _explain(self, S: float, C: float, A: float, M: float, P: float,
                 bm: float, pa: float, amp: float, raw: float) -> str:
        return (
            f"Embodied_Wisdom = (S={S:.2f} × C={C:.2f}) + (A={A:.2f} - M={M:.2f})^P={P:.2f} "
            f"= {bm:.2f} + ({pa:.2f}^{P:.2f}={amp:.2f}) = {raw:.2f}"
        )


if __name__ == "__main__":
    synth = EmbodiedWisdomSynthesizer()
    p = Pulse(pulse_type=PulseType.PLAY, valence=0.7, arousal=0.5, dominance=0.3, intensity=0.6)
    c = Current(valence=0.4, arousal=0.5, dominance=0.3)
    result = synth.compute(
        p, c,
        somatic_awareness=0.65,
        conceptual_understanding=0.7,
        action_tendency=0.6,
        mental_chatter=0.3,
        practice_integration=0.55,
    )
    print(result)
    print(f"Explanation: {result.explanation}")
    print(f"Body-Mind product: {result.body_mind_product}")
    print(f"Pure action: {result.pure_action}")
    print(f"Practice amplification: {result.practice_amplification}")
