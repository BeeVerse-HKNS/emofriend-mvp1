"""Compassionate Response Engine — 慈悲回應引擎

KB-50 §十三 公式 3:
    Compassionate_Response = (E * T) + (R / D) - A

元素語義:
    E = Empathy                 (共情強度: Brackett 嘅 RULER + 12 書共情)
    T = Tonglen                 (施受法: Chödrön 嘅雙向實踐)
    R = Recognition of Suffering (識別痛苦: Nhat Hanh 嘅 Interbeing)
    D = Distance                (距離感: Tolle 嘅 Pain Body)
    A = Armor                   (盔甲強度: Brown 嘅盔甲假設)

EmoGlyph 整合點: Resonance Layer

預期新能力:
- 自動識別 Armour Response (盔甲反應)
- 提供 Tonglen 風格嘅雙向情感調節
- 為深度情感對話做準備
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from ..pulse import Pulse, PulseType
from ..current import Current


@dataclass
class CompassionResult:
    """慈悲回應計算結果"""
    raw_score: float
    normalized_score: float
    E: float
    T: float
    R: float
    D: float
    A: float
    armor_detected: bool
    explanation: str
    sources: List[str] = field(default_factory=list)
    layer: str = "resonance"
    confidence: str = "🔍 中"

    def __repr__(self) -> str:
        return (
            f"CompassionResult(normalized={self.normalized_score:.3f}, "
            f"E={self.E:.2f}, T={self.T:.2f}, R={self.R:.2f}, D={self.D:.2f}, A={self.A:.2f}, "
            f"armor={self.armor_detected})"
        )


class CompassionateResponseEngine:
    """慈悲回應引擎 (KB-50 公式 3)"""

    SOURCE_BOOKS = [
        "Brackett 2019 (Permission to Feel)",
        "Chödrön 1996 (When Things Fall Apart)",
        "Chödrön 2001 (Places That Scare You)",
        "Nhat Hanh 1998 (Heart of Buddha's Teaching)",
        "Tolle 1997 (Power of Now) - Pain Body",
        "Brown 2012 (Daring Greatly) - Armour Hypothesis",
        "Salovey & Mayer 1990 - Empathy",
    ]

    ARMOR_THRESHOLD = 0.6  # 高過呢個值視為有盔甲

    def __init__(self, armor_sensitivity: float = 0.5) -> None:
        self.armor_sensitivity = armor_sensitivity
        if not 0.0 <= armor_sensitivity <= 1.0:
            raise ValueError("armor_sensitivity must be in [0, 1]")

    def compute(
        self,
        pulse: Pulse,
        current: Current,
        empathy: float = 0.5,
        tonglen: float = 0.5,
        suffering_recognition: float = 0.5,
        distance: Optional[float] = None,
        armor: float = 0.5,
    ) -> CompassionResult:
        """計算慈悲回應

        Args:
            pulse: EmoGlyph Pulse
            current: EmoGlyph Current
            empathy: 共情強度 (0-1)
            tonglen: 施受法熟練度 (0-1)
            suffering_recognition: 識別痛苦能力 (0-1)
            distance: 距離感 (0-1)，None = 默認為 |current.dominance|
            armor: 盔甲強度 (0-1)

        Returns:
            CompassionResult
        """
        if not isinstance(pulse, Pulse):
            raise TypeError("pulse must be a Pulse")
        if not isinstance(current, Current):
            raise TypeError("current must be a Current")
        for name, val in (
            ("empathy", empathy),
            ("tonglen", tonglen),
            ("suffering_recognition", suffering_recognition),
            ("armor", armor),
        ):
            if not isinstance(val, (int, float)):
                raise TypeError(f"{name} must be numeric")
            if not 0.0 <= val <= 1.0:
                raise ValueError(f"{name} must be in [0, 1]")

        E = float(empathy)
        T = float(tonglen)
        R = float(suffering_recognition)
        D = float(distance) if distance is not None else abs(float(current.dominance))
        D = max(0.01, min(1.0, D))  # avoid div-by-zero
        A = float(armor)

        raw = (E * T) + (R / D) - A
        # Normalize: max theoretical = (1*1) + (1/0.01) - 0 = 1 + 100 = 101
        # Use sigmoid-like normalization
        normalized = max(0.0, min(1.0, raw / 2.0))

        armor_detected = A > self.ARMOR_THRESHOLD * self.armor_sensitivity

        return CompassionResult(
            raw_score=raw,
            normalized_score=normalized,
            E=E,
            T=T,
            R=R,
            D=D,
            A=A,
            armor_detected=armor_detected,
            explanation=self._explain(E, T, R, D, A, raw, armor_detected),
            sources=list(self.SOURCE_BOOKS),
            layer="resonance",
            confidence="✅ 強" if normalized > 0.6 else "🔍 中" if normalized > 0.3 else "⚠️ 弱",
        )

    def _explain(self, E: float, T: float, R: float, D: float, A: float, raw: float, armor: bool) -> str:
        armor_note = " ⚠️ [Armour Detected]" if armor else ""
        return (
            f"Compassionate_Response = (E={E:.2f} * T={T:.2f}) + (R={R:.2f} / D={D:.2f}) - A={A:.2f} "
            f"= {E * T:.2f} + {R / D:.2f} - {A:.2f} = {raw:.2f}{armor_note}"
        )


if __name__ == "__main__":
    eng = CompassionateResponseEngine()
    p = Pulse(pulse_type=PulseType.CARE, valence=0.6, arousal=0.3, dominance=0.2, intensity=0.5)
    c = Current(valence=0.2, arousal=0.4, dominance=0.3)
    result = eng.compute(
        p, c,
        empathy=0.75,
        tonglen=0.6,
        suffering_recognition=0.7,
        distance=0.4,
        armor=0.55,
    )
    print(result)
    print(f"Explanation: {result.explanation}")
    print(f"Armour Detected: {result.armor_detected}")
