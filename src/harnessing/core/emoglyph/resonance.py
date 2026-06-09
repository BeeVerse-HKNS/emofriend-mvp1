from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Iterable, List, Optional, Sequence, Tuple

from .pulse import Pulse, PulseType
from .current import Current


class SilenceType(Enum):
    MA = "ma"
    MU = "mu"
    ZEN = "zen"


SILENCE_DESCRIPTIONS = {
    SilenceType.MA: "active contemplation — the meaningful interval between thoughts",
    SilenceType.MU: "no-answer — the Zen refusal that names the unnameable",
    SilenceType.ZEN: "presence — being-with, beyond words or absence",
}

DEFAULT_EMPATHY_FACTOR = 0.5
TRUSTED_EMPATHY_FACTOR = 0.8
STRANGER_EMPATHY_FACTOR = 0.2
ADVERSARY_EMPATHY_FACTOR = 0.0


def cosine_similarity(vec_a: Sequence[float], vec_b: Sequence[float]) -> float:
    if not isinstance(vec_a, (list, tuple)) or not isinstance(vec_b, (list, tuple)):
        raise TypeError("vec_a and vec_b must be sequences")
    if len(vec_a) != len(vec_b):
        raise ValueError("vectors must have same length")
    if len(vec_a) == 0:
        raise ValueError("vectors must be non-empty")
    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0
    for a, b in zip(vec_a, vec_b):
        dot += float(a) * float(b)
        norm_a += float(a) * float(a)
        norm_b += float(b) * float(b)
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (math.sqrt(norm_a) * math.sqrt(norm_b))


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


@dataclass
class ResonanceEngine:
    empathy_factor: float = DEFAULT_EMPATHY_FACTOR
    bias_negative: float = 0.1
    history: List[float] = None

    def __post_init__(self) -> None:
        if not isinstance(self.empathy_factor, (int, float)):
            raise TypeError("empathy_factor must be numeric")
        if not 0.0 <= self.empathy_factor <= 1.0:
            raise ValueError("empathy_factor must be in [0, 1]")
        if not isinstance(self.bias_negative, (int, float)):
            raise TypeError("bias_negative must be numeric")
        if self.history is None:
            self.history = []

    def calibrate(self, empathy_factor: float) -> None:
        if not 0.0 <= empathy_factor <= 1.0:
            raise ValueError("empathy_factor must be in [0, 1]")
        self.empathy_factor = float(empathy_factor)

    def induce_state(
        self,
        receiver_current: Current,
        sender_pulse: Pulse,
        empathy_factor: Optional[float] = None,
    ) -> Current:
        if not isinstance(receiver_current, Current):
            raise TypeError("receiver_current must be a Current")
        if not isinstance(sender_pulse, Pulse):
            raise TypeError("sender_pulse must be a Pulse")
        if empathy_factor is None:
            ef = self.empathy_factor
        else:
            if not 0.0 <= empathy_factor <= 1.0:
                raise ValueError("empathy_factor must be in [0, 1]")
            ef = float(empathy_factor)
        receiver_vec = list(receiver_current.as_tuple())
        sender_vec = [sender_pulse.valence, sender_pulse.arousal, sender_pulse.dominance]
        similarity = cosine_similarity(receiver_vec, sender_vec)
        mapping = 0.5 * (1.0 + similarity)
        bias = self.bias_negative if (sender_pulse.valence < 0 and sender_pulse.arousal > 0) else 0.0
        gain = ef * mapping + bias
        gain = _clamp(gain, 0.0, 1.0)
        new_valence = _clamp(
            receiver_current.valence * (1.0 - gain) + sender_pulse.valence * gain,
            -1.0, 1.0,
        )
        new_arousal = _clamp(
            receiver_current.arousal * (1.0 - gain) + sender_pulse.arousal * gain,
            -1.0, 1.0,
        )
        new_dominance = _clamp(
            receiver_current.dominance * (1.0 - gain) + sender_pulse.dominance * gain,
            -1.0, 1.0,
        )
        new_current = Current(
            valence=new_valence,
            arousal=new_arousal,
            dominance=new_dominance,
            update_rate=receiver_current.update_rate,
            retention_size=receiver_current.retention_size,
        )
        new_current.retention = list(receiver_current.retention)
        self.history.append(gain)
        return new_current

    def resonance_strength(self, current_a: Current, pulse_b: Pulse) -> float:
        if not isinstance(current_a, Current):
            raise TypeError("current_a must be a Current")
        if not isinstance(pulse_b, Pulse):
            raise TypeError("pulse_b must be a Pulse")
        return cosine_similarity(
            list(current_a.as_tuple()),
            [pulse_b.valence, pulse_b.arousal, pulse_b.dominance],
        )


def render_silence(silence: SilenceType) -> str:
    if not isinstance(silence, SilenceType):
        raise TypeError("silence must be a SilenceType")
    return f"⟨silence:{silence.value}⟩"


if __name__ == "__main__":
    def _expect(cond: bool, label: str) -> None:
        print(("PASS" if cond else "FAIL") + f" — {label}")

    _expect(abs(cosine_similarity([1, 0, 0], [1, 0, 0]) - 1.0) < 1e-9, "identical vectors cos = 1")
    _expect(abs(cosine_similarity([1, 0, 0], [-1, 0, 0]) + 1.0) < 1e-9, "opposite vectors cos = -1")
    _expect(abs(cosine_similarity([0, 0, 0], [1, 2, 3])) < 1e-9, "zero vector cos = 0")

    try:
        cosine_similarity([1, 0], [1, 0, 0])
    except ValueError:
        _expect(True, "mismatched length rejected")
    else:
        _expect(False, "mismatched length rejected")

    engine = ResonanceEngine(empathy_factor=0.5)
    recv = Current(valence=0.1, arousal=0.0, dominance=0.0, update_rate=0.4)
    pulse = Pulse(PulseType.FEAR, -0.5, 0.7, -0.4, intensity=0.8)
    new_state = engine.induce_state(recv, pulse)
    _expect(new_state.arousal > recv.arousal, "induction increases arousal toward sender")
    _expect(isinstance(new_state, Current), "induction returns Current")

    trusted = ResonanceEngine(empathy_factor=0.9)
    new_strong = trusted.induce_state(Current(0.0, 0.0, 0.0, 0.3), pulse)
    new_weak = ResonanceEngine(empathy_factor=0.1).induce_state(Current(0.0, 0.0, 0.0, 0.3), pulse)
    _expect(
        abs(new_strong.valence - new_weak.valence) > 0.01,
        "higher empathy_factor induces more strongly",
    )

    try:
        ResonanceEngine(empathy_factor=1.5)
    except ValueError:
        _expect(True, "out-of-range empathy rejected")
    else:
        _expect(False, "out-of-range empathy rejected")
    rs = engine.resonance_strength(Current(0.5, 0.5, 0.5, 0.3), Pulse(PulseType.SEEKING, 0.5, 0.5, 0.5, 0.5))
    _expect(rs > 0.99, "identical state+vector -> high resonance")

    _expect(render_silence(SilenceType.MA) == "⟨silence:ma⟩", "render silence MA")

    print("OK — resonance.py smoke tests done")
