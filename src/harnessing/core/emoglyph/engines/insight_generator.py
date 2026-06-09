"""Emotional Insight Generator — 情感洞察生成器

KB-50 §十三 公式 1:
    Emotional_Insight = (K * R) + (C / S)

元素語義:
    K = Knowledge  (情感概念庫: 12 本書嘅智慧)
    R = Reflection (元認知反思: Brach 嘅 Investigate)
    C = Context    (情境脈絡: Barrett 嘅情境預測)
    S = Self-Awareness (自我覺察: Salovey 嘅 Perceive)

EmoGlyph 整合點: Construct Layer + Resonance Layer

預期新能力:
- 自動從多源情感理論生成個人化洞察
- 將抽象嘅情感概念轉化為可操作嘅建議
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from ..pulse import Pulse, PulseType
from ..current import Current


@dataclass
class InsightResult:
    """情感洞察計算結果"""
    raw_score: float
    normalized_score: float
    K: float
    R: float
    C: float
    S: float
    explanation: str
    sources: List[str] = field(default_factory=list)
    layer: str = "construct"
    confidence: str = "🔍 中"

    def __repr__(self) -> str:
        return (
            f"InsightResult(normalized={self.normalized_score:.3f}, "
            f"K={self.K:.2f}, R={self.R:.2f}, C={self.C:.2f}, S={self.S:.2f})"
        )


class EmotionalInsightGenerator:
    """情感洞察生成器 (KB-50 公式 1)"""

    DEFAULT_KNOWLEDGE_BASE: Dict[str, float] = {
        # 從 12 本書摘要提取嘅知識庫評分 (KB-32 ~ KB-50)
        "Damasio_somatic_marker": 0.85,
        "Barrett_constructed": 0.90,
        "Goleman_EQ5": 0.80,
        "Brackett_RULER": 0.85,
        "Salovey_4branch": 0.75,
        "Gross_reappraisal": 0.80,
        "Davidson_6dim": 0.78,
        "Brach_RAIN": 0.82,
        "KabatZinn_mindfulness": 0.88,
        "Tolle_present": 0.70,
        "NhatHanh_interbeing": 0.85,
        "Chodron_impermance": 0.78,
        "Panksepp_7systems": 0.88,
    }

    SOURCE_BOOKS = [
        "Damasio 1994 (Descartes' Error)",
        "Damasio 2010 (Self Comes to Mind)",
        "Barrett 2017 (How Emotions Are Made)",
        "Goleman 1995 (Emotional Intelligence)",
        "Brackett 2019 (Permission to Feel)",
        "Salovey & Mayer 1990",
        "Gross 1998 (Emotion Regulation)",
        "Davidson 2012 (Emotional Life of Your Brain)",
        "Brach 2003 (Radical Acceptance)",
        "Kabat-Zinn 1994 (Wherever You Go)",
        "Tolle 1997 (Power of Now)",
        "Nhat Hanh 1998 (Heart of Buddha's Teaching)",
        "Chödrön 1996 (When Things Fall Apart)",
        "Panksepp 1998 (Affective Neuroscience)",
    ]

    def __init__(self, knowledge_base: Optional[Dict[str, float]] = None) -> None:
        self.kb = knowledge_base if knowledge_base is not None else dict(self.DEFAULT_KNOWLEDGE_BASE)
        if not isinstance(self.kb, dict):
            raise TypeError("knowledge_base must be a dict[str, float]")

    def compute(
        self,
        pulse: Pulse,
        current: Current,
        context: Optional[dict] = None,
        self_awareness_score: float = 0.5,
        reflection_depth: int = 5,
    ) -> InsightResult:
        """計算情感洞察

        Args:
            pulse: EmoGlyph Pulse 對象
            current: EmoGlyph Current 對象
            context: 情境脈絡 dict
            self_awareness_score: 自我覺察評分 (0-1)
            reflection_depth: 反思深度 (0-10)

        Returns:
            InsightResult 對象，包含 raw / normalized / 解釋 / 來源 / layer
        """
        if not isinstance(pulse, Pulse):
            raise TypeError("pulse must be a Pulse")
        if not isinstance(current, Current):
            raise TypeError("current must be a Current")
        if not isinstance(self_awareness_score, (int, float)):
            raise TypeError("self_awareness_score must be numeric")
        if not 0.0 <= self_awareness_score <= 1.0:
            raise ValueError("self_awareness_score must be in [0, 1]")
        if not isinstance(reflection_depth, int) or not 0 <= reflection_depth <= 10:
            raise ValueError("reflection_depth must be int in [0, 10]")

        K = self._knowledge_score(pulse, current)
        R = reflection_depth / 10.0
        C = self._context_score(context or {})
        S = max(float(self_awareness_score), 0.01)  # avoid div-by-zero

        raw = (K * R) + (C / S)
        normalized = max(0.0, min(1.0, raw / 2.0))

        return InsightResult(
            raw_score=raw,
            normalized_score=normalized,
            K=K,
            R=R,
            C=C,
            S=S,
            explanation=self._explain(K, R, C, S),
            sources=list(self.SOURCE_BOOKS),
            layer="construct",
            confidence="✅ 強" if normalized > 0.7 else "🔍 中" if normalized > 0.3 else "⚠️ 弱",
        )

    def _knowledge_score(self, pulse: Pulse, current: Current) -> float:
        """從知識庫評分 (K)"""
        if not self.kb:
            return 0.5
        relevant = []
        for key, score in self.kb.items():
            if not isinstance(score, (int, float)):
                continue
            if any(token in key.lower() for token in pulse.pulse_type.name.lower().split("_")):
                relevant.append(float(score))
        if not relevant:
            return sum(self.kb.values()) / len(self.kb)
        return sum(relevant) / len(relevant)

    def _context_score(self, context: dict) -> float:
        """情境評分 (C) — 0-1"""
        if not context:
            return 0.5
        score = 0.0
        weight = 0.0
        for key, value in context.items():
            if isinstance(value, (int, float)):
                v = max(0.0, min(1.0, float(value)))
                w = 1.0
                score += v * w
                weight += w
        if weight == 0:
            return 0.5
        return max(0.0, min(1.0, score / weight))

    def _explain(self, K: float, R: float, C: float, S: float) -> str:
        return (
            f"Emotional_Insight = (K={K:.2f} * R={R:.2f}) + (C={C:.2f} / S={S:.2f}) "
            f"= {K * R:.2f} + {C / S:.2f}"
        )


if __name__ == "__main__":
    gen = EmotionalInsightGenerator()
    p = Pulse.from_type(PulseType.FEAR, intensity=0.7) if hasattr(Pulse, "from_type") else Pulse(
        pulse_type=PulseType.FEAR, valence=-0.8, arousal=0.8, dominance=-0.7, intensity=0.7
    )
    c = Current(valence=-0.3, arousal=0.5, dominance=-0.2)
    result = gen.compute(p, c, context={"urgency": 0.8, "familiarity": 0.6}, self_awareness_score=0.7, reflection_depth=7)
    print(result)
    print(f"Explanation: {result.explanation}")
    print(f"Sources: {len(result.sources)} books")
