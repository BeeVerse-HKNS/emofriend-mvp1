from __future__ import annotations

import struct
from dataclasses import dataclass
from enum import Enum
from typing import Union


class PulseType(Enum):
    SEEKING = 0
    RAGE = 1
    FEAR = 2
    LUST = 3
    CARE = 4
    PANIC = 5
    PLAY = 6
    NEUTRAL = 7
    VALENCE = 100
    AROUSAL = 101
    DOMINANCE = 102


VAD_BASELINES = {
    PulseType.SEEKING: (0.5, 0.6, 0.4),
    PulseType.RAGE: (-0.7, 0.9, 0.8),
    PulseType.FEAR: (-0.8, 0.8, -0.7),
    PulseType.LUST: (0.7, 0.7, 0.3),
    PulseType.CARE: (0.6, 0.3, 0.2),
    PulseType.PANIC: (-0.9, 0.7, -0.8),
    PulseType.PLAY: (0.8, 0.5, 0.3),
    PulseType.NEUTRAL: (0.0, 0.0, 0.0),
}

PULSE_BYTE_SIZE = 16


@dataclass
class Pulse:
    pulse_type: PulseType
    valence: float
    arousal: float
    dominance: float
    intensity: float = 1.0

    def __post_init__(self) -> None:
        for name, value in (
            ("valence", self.valence),
            ("arousal", self.arousal),
            ("dominance", self.dominance),
            ("intensity", self.intensity),
        ):
            if not isinstance(value, (int, float)):
                raise TypeError(f"{name} must be numeric, got {type(value).__name__}")
            lo, hi = (-1.0, 1.0) if name != "intensity" else (0.0, 1.0)
            if value < lo or value > hi:
                raise ValueError(
                    f"{name}={value} out of range [{lo}, {hi}]"
                )

    def modulate(self, factor: float) -> "Pulse":
        if not isinstance(factor, (int, float)):
            raise TypeError("factor must be numeric")
        factor = max(0.0, min(1.0, float(factor)))
        return Pulse(
            pulse_type=self.pulse_type,
            valence=self.valence * factor,
            arousal=self.arousal * factor,
            dominance=self.dominance * factor,
            intensity=self.intensity * factor,
        )

    def blend(self, other: "Pulse", weight: float = 0.5) -> "Pulse":
        if not isinstance(other, Pulse):
            raise TypeError("other must be a Pulse")
        if not isinstance(weight, (int, float)):
            raise TypeError("weight must be numeric")
        weight = max(0.0, min(1.0, float(weight)))
        inv = 1.0 - weight
        if self.pulse_type == other.pulse_type:
            merged_type = self.pulse_type
        else:
            merged_type = self.pulse_type if self.intensity >= other.intensity else other.pulse_type
        return Pulse(
            pulse_type=merged_type,
            valence=self.valence * inv + other.valence * weight,
            arousal=self.arousal * inv + other.arousal * weight,
            dominance=self.dominance * inv + other.dominance * weight,
            intensity=self.intensity * inv + other.intensity * weight,
        )

    def to_bytes(self) -> bytes:
        type_byte = self.pulse_type.value & 0xFF
        v = int(round((self.valence + 1.0) * 127.5)) & 0xFF
        a = int(round((self.arousal + 1.0) * 127.5)) & 0xFF
        d = int(round((self.dominance + 1.0) * 127.5)) & 0xFF
        i = int(round(max(0.0, min(1.0, self.intensity)) * 255.0)) & 0xFF
        return struct.pack(">BBBB", type_byte, v, a, d) + b"\x00" * 11 + struct.pack(">B", i)

    @classmethod
    def from_bytes(cls, data: bytes) -> "Pulse":
        if not isinstance(data, (bytes, bytearray)):
            raise TypeError("data must be bytes")
        if len(data) != PULSE_BYTE_SIZE:
            raise ValueError(
                f"Pulse requires exactly {PULSE_BYTE_SIZE} bytes, got {len(data)}"
            )
        type_byte, v, a, d, intensity = struct.unpack(">BBBBB", data[:5])
        try:
            pulse_type = PulseType(type_byte)
        except ValueError:
            pulse_type = PulseType.NEUTRAL
        return cls(
            pulse_type=pulse_type,
            valence=(v / 127.5) - 1.0,
            arousal=(a / 127.5) - 1.0,
            dominance=(d / 127.5) - 1.0,
            intensity=intensity / 255.0,
        )

    @classmethod
    def from_type(cls, pulse_type: PulseType, intensity: float = 1.0) -> "Pulse":
        v, a, d = VAD_BASELINES.get(pulse_type, (0.0, 0.0, 0.0))
        return cls(
            pulse_type=pulse_type,
            valence=v,
            arousal=a,
            dominance=d,
            intensity=intensity,
        )

    def __repr__(self) -> str:
        return (
            f"Pulse({self.pulse_type.name}, V={self.valence:+.2f}, "
            f"A={self.arousal:+.2f}, D={self.dominance:+.2f}, I={self.intensity:.2f})"
        )


if __name__ == "__main__":
    def _expect(cond: bool, label: str) -> None:
        print(("PASS" if cond else "FAIL") + f" — {label}")

    p1 = Pulse(PulseType.FEAR, -0.8, 0.8, -0.7, 0.9)
    _expect(p1.pulse_type == PulseType.FEAR, "pulse type preserved")
    _expect(-1.0 <= p1.valence <= 1.0, "valence in range")

    p_mod = p1.modulate(0.5)
    _expect(abs(p_mod.intensity - 0.45) < 1e-6, "modulate halves intensity")

    p2 = Pulse(PulseType.RAGE, -0.7, 0.9, 0.8, 0.6)
    p_blend = p1.blend(p2, 0.5)
    _expect(p_blend.pulse_type in (PulseType.FEAR, PulseType.RAGE), "blend keeps type or picks dominant")

    raw = p1.to_bytes()
    _expect(len(raw) == PULSE_BYTE_SIZE, f"to_bytes is {PULSE_BYTE_SIZE} bytes")
    p_round = Pulse.from_bytes(raw)
    _expect(abs(p_round.valence - p1.valence) < 0.02, "round-trip valence")
    _expect(p_round.pulse_type == p1.pulse_type, "round-trip type")

    try:
        Pulse(PulseType.FEAR, 2.0, 0.0, 0.0)
    except ValueError:
        _expect(True, "out-of-range valence raises ValueError")
    else:
        _expect(False, "out-of-range valence raises ValueError")

    p_seek = Pulse.from_type(PulseType.SEEKING, 0.5)
    _expect(p_seek.pulse_type == PulseType.SEEKING, "from_type uses SEEKING")
    _expect(p_seek.intensity == 0.5, "from_type intensity")

    print("OK — pulse.py smoke tests done")
