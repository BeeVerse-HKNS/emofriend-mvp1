from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple

from .pulse import Pulse, PulseType, VAD_BASELINES
from .current import Current
from .enactive import (
    AutonomicTier,
    EnactionType,
    EnactiveMessage,
    ProcessingPath,
    TIER_TO_PATH,
    default_enaction_for,
)


class CompositionType(Enum):
    PARALLEL = "parallel"
    SEQUENTIAL = "sequential"
    CONTRASTING = "contrasting"
    RECURSIVE = "recursive"


PULSE_KEYWORDS = {
    "SEEKING": PulseType.SEEKING,
    "RAGE": PulseType.RAGE,
    "FEAR": PulseType.FEAR,
    "LUST": PulseType.LUST,
    "CARE": PulseType.CARE,
    "PANIC": PulseType.PANIC,
    "PLAY": PulseType.PLAY,
    "NEUTRAL": PulseType.NEUTRAL,
}

TIER_KEYWORDS = {
    "VENTRAL": AutonomicTier.VENTRAL_VAGAL,
    "SYMPATHETIC": AutonomicTier.SYMPATHETIC,
    "DORSAL": AutonomicTier.DORSAL_VAGAL,
}

ENA_KEYWORDS = {
    "REACH": EnactionType.REACH,
    "GUARD": EnactionType.GUARD,
    "ALERT": EnactionType.ALERT,
    "DESIRE": EnactionType.DESIRE,
    "NURTURE": EnactionType.NURTURE,
    "MOURN": EnactionType.MOURN,
    "PLAY": EnactionType.PLAY,
}


@dataclass
class PulseTokenizer:
    text: str

    def tokenize(self) -> List[str]:
        if not isinstance(self.text, str):
            raise TypeError("text must be a string")
        text = self.text.strip()
        if not text:
            return []
        text = re.sub(r"\s+", " ", text)
        return text.split(" ")


@dataclass
class CurrentParser:
    alpha: float = 0.3
    valence: float = 0.0
    arousal: float = 0.0
    dominance: float = 0.0

    def __post_init__(self) -> None:
        for n in ("alpha", "valence", "arousal", "dominance"):
            v = getattr(self, n)
            if not isinstance(v, (int, float)):
                raise TypeError(f"{n} must be numeric")
        if not 0.0 <= self.alpha <= 1.0:
            raise ValueError("alpha must be in [0, 1]")

    def apply(self, pulse: Pulse) -> Current:
        if not isinstance(pulse, Pulse):
            raise TypeError("pulse must be a Pulse")
        cur = Current(
            valence=self.valence,
            arousal=self.arousal,
            dominance=self.dominance,
            update_rate=self.alpha,
        )
        cur.update(pulse)
        return cur


@dataclass
class ConstructAnalyzer:
    five_element_cycle_position: str = "wood"

    def analyze(self, pulse: Pulse) -> dict:
        if not isinstance(pulse, Pulse):
            raise TypeError("pulse must be a Pulse")
        return {
            "pulse_type": pulse.pulse_type.name,
            "intensity": pulse.intensity,
            "predicted_construct": f"construct_for_{pulse.pulse_type.name.lower()}",
            "five_element": _pulse_to_element(pulse.pulse_type),
        }


def _pulse_to_element(pt: PulseType) -> str:
    mapping = {
        PulseType.RAGE: "wood",
        PulseType.PLAY: "fire",
        PulseType.CARE: "earth",
        PulseType.PANIC: "metal",
        PulseType.FEAR: "water",
    }
    return mapping.get(pt, "earth")


@dataclass
class EnactionSynthesizer:
    default_tier: AutonomicTier = AutonomicTier.VENTRAL_VAGAL

    def synthesize(self, pulse: Pulse, tier: Optional[AutonomicTier] = None) -> EnactiveMessage:
        if not isinstance(pulse, Pulse):
            raise TypeError("pulse must be a Pulse")
        actual_tier = tier if tier is not None else self.default_tier
        if not isinstance(actual_tier, AutonomicTier):
            raise TypeError("tier must be an AutonomicTier")
        return EnactiveMessage(
            pulse=pulse,
            enaction=default_enaction_for(pulse),
            autonomic_tier=actual_tier,
            processing_path=TIER_TO_PATH[actual_tier],
        )


@dataclass
class ResonanceOptimizer:
    empathy_factor: float = 0.5

    def __post_init__(self) -> None:
        if not 0.0 <= self.empathy_factor <= 1.0:
            raise ValueError("empathy_factor must be in [0, 1]")

    def optimize(self, pulse: Pulse) -> float:
        if not isinstance(pulse, Pulse):
            raise TypeError("pulse must be a Pulse")
        base = 0.5
        if pulse.valence < 0 and pulse.arousal > 0:
            base += 0.2
        if pulse.intensity > 0.7:
            base += 0.1
        return max(0.0, min(1.0, base))


class AffectiveCompositionGrammar:
    PARALLEL_SEP = "|"
    SEQUENTIAL_SEP = "->"
    CONTRASTING_SEP = "^"
    RECURSIVE_OPEN = "["
    RECURSIVE_CLOSE = "]"

    def __init__(self) -> None:
        self.tokenizer = PulseTokenizer("")
        self.current_parser = CurrentParser()
        self.construct_analyzer = ConstructAnalyzer()
        self.enaction_synthesizer = EnactionSynthesizer()
        self.resonance_optimizer = ResonanceOptimizer()

    def parse(self, dsl: str) -> List[Tuple[CompositionType, Pulse, AutonomicTier]]:
        if not isinstance(dsl, str):
            raise TypeError("dsl must be a string")
        if not dsl.strip():
            return []
        if self.RECURSIVE_OPEN in dsl and self.RECURSIVE_CLOSE in dsl:
            return self._parse_recursive(dsl)
        if self.CONTRASTING_SEP in dsl:
            return self._parse_contrasting(dsl)
        if self.SEQUENTIAL_SEP in dsl:
            return self._parse_sequential(dsl)
        if self.PARALLEL_SEP in dsl:
            return self._parse_parallel(dsl)
        pulse, tier = self._parse_single_token(dsl.strip())
        return [(CompositionType.PARALLEL, pulse, tier)]

    def _parse_single_token(self, token: str) -> Tuple[Pulse, AutonomicTier]:
        if not token:
            raise ValueError("empty token")
        upper = token.upper()
        if upper in PULSE_KEYWORDS:
            pulse = Pulse.from_type(PULSE_KEYWORDS[upper], intensity=1.0)
            return pulse, AutonomicTier.VENTRAL_VAGAL
        if upper in TIER_KEYWORDS:
            baseline = Pulse.from_type(PulseType.SEEKING, intensity=0.5)
            return baseline, TIER_KEYWORDS[upper]
        match = re.match(r"^([A-Za-z]+)@([A-Za-z]+)$", token)
        if match:
            pname, tname = match.group(1).upper(), match.group(2).upper()
            if pname in PULSE_KEYWORDS and tname in TIER_KEYWORDS:
                return (
                    Pulse.from_type(PULSE_KEYWORDS[pname], intensity=1.0),
                    TIER_KEYWORDS[tname],
                )
        match2 = re.match(r"^([A-Za-z]+):(\d*\.?\d+)$", token)
        if match2:
            pname, intensity = match2.group(1).upper(), float(match2.group(2))
            if pname in PULSE_KEYWORDS:
                return (
                    Pulse.from_type(PULSE_KEYWORDS[pname], intensity=intensity),
                    AutonomicTier.VENTRAL_VAGAL,
                )
        match3 = re.match(r"^V([+-]\d*\.?\d+)A([+-]\d*\.?\d+)D([+-]\d*\.?\d+)$", token)
        if match3:
            v, a, d = (float(x) for x in match3.groups())
            v = max(-1.0, min(1.0, v))
            a = max(-1.0, min(1.0, a))
            d = max(-1.0, min(1.0, d))
            return (
                Pulse(PulseType.NEUTRAL, v, a, d, intensity=1.0),
                AutonomicTier.VENTRAL_VAGAL,
            )
        raise ValueError(f"unrecognised token {token!r}")

    def _parse_parallel(self, dsl: str) -> List[Tuple[CompositionType, Pulse, AutonomicTier]]:
        results: List[Tuple[CompositionType, Pulse, AutonomicTier]] = []
        for tok in dsl.split(self.PARALLEL_SEP):
            tok = tok.strip()
            if tok:
                pulse, tier = self._parse_single_token(tok)
                results.append((CompositionType.PARALLEL, pulse, tier))
        return results

    def _parse_sequential(self, dsl: str) -> List[Tuple[CompositionType, Pulse, AutonomicTier]]:
        results: List[Tuple[CompositionType, Pulse, AutonomicTier]] = []
        for tok in dsl.split(self.SEQUENTIAL_SEP):
            tok = tok.strip()
            if tok:
                pulse, tier = self._parse_single_token(tok)
                results.append((CompositionType.SEQUENTIAL, pulse, tier))
        return results

    def _parse_contrasting(self, dsl: str) -> List[Tuple[CompositionType, Pulse, AutonomicTier]]:
        results: List[Tuple[CompositionType, Pulse, AutonomicTier]] = []
        for tok in dsl.split(self.CONTRASTING_SEP):
            tok = tok.strip()
            if tok:
                pulse, tier = self._parse_single_token(tok)
                results.append((CompositionType.CONTRASTING, pulse, tier))
        return results

    def _parse_recursive(self, dsl: str) -> List[Tuple[CompositionType, Pulse, AutonomicTier]]:
        results: List[Tuple[CompositionType, Pulse, AutonomicTier]] = []
        start = dsl.find(self.RECURSIVE_OPEN)
        end = dsl.rfind(self.RECURSIVE_CLOSE)
        if start < 0 or end < 0 or end <= start:
            raise ValueError(f"malformed recursive block: {dsl!r}")
        inner = dsl[start + 1:end]
        for tok in inner.split(","):
            tok = tok.strip()
            if not tok:
                continue
            pulse, tier = self._parse_single_token(tok)
            results.append((CompositionType.RECURSIVE, pulse, tier))
        if not results:
            raise ValueError(f"recursive parse produced no tokens for {dsl!r}")
        return results


if __name__ == "__main__":
    def _expect(cond: bool, label: str) -> None:
        print(("PASS" if cond else "FAIL") + f" — {label}")

    g = AffectiveCompositionGrammar()
    out = g.parse("FEAR@SYMPATHETIC")
    _expect(len(out) == 1, "single token parsed as one item")
    _expect(out[0][1].pulse_type == PulseType.FEAR, "FEAR token -> FEAR pulse")
    _expect(out[0][2] == AutonomicTier.SYMPATHETIC, "SYMPATHETIC tier preserved")

    out_p = g.parse("FEAR@SYMPATHETIC | CARE@VENTRAL")
    _expect(len(out_p) == 2, "parallel yields 2 items")
    _expect(out_p[0][0] == CompositionType.PARALLEL, "first item is PARALLEL")

    out_s = g.parse("FEAR@SYMPATHETIC -> CARE@VENTRAL")
    _expect(len(out_s) == 2, "sequential yields 2 items")
    _expect(out_s[0][0] == CompositionType.SEQUENTIAL, "first item is SEQUENTIAL")

    out_c = g.parse("FEAR@SYMPATHETIC ^ PLAY@VENTRAL")
    _expect(len(out_c) == 2, "contrasting yields 2 items")
    _expect(out_c[0][0] == CompositionType.CONTRASTING, "first item is CONTRASTING")

    out_r = g.parse("[FEAR@SYMPATHETIC , CARE@VENTRAL]")
    _expect(len(out_r) == 2, "recursive yields 2 items")
    _expect(out_r[0][0] == CompositionType.RECURSIVE, "first item is RECURSIVE")

    out_v = g.parse("V+0.5A+0.7D+0.3")
    _expect(out_v[0][1].valence > 0.4, "VAD string parsed")

    out_i = g.parse("FEAR:0.6")
    _expect(abs(out_i[0][1].intensity - 0.6) < 1e-6, "intensity-suffixed pulse")

    tk = PulseTokenizer("FEAR@SYMPATHETIC | CARE@VENTRAL")
    tokens = tk.tokenize()
    _expect(len(tokens) == 3, "tokenizer splits on space (not on inner symbols)")

    cp = CurrentParser(alpha=0.5, valence=0.0)
    p = Pulse.from_type(PulseType.PLAY, intensity=0.8)
    cur = cp.apply(p)
    _expect(cur.arousal > 0.0, "current parser applies pulse")

    try:
        g.parse("BOGUS_TOKEN")
    except ValueError:
        _expect(True, "bogus token raises ValueError")
    else:
        _expect(False, "bogus token raises ValueError")

    print("OK — compiler.py smoke tests done")
