from __future__ import annotations

import struct
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from .pulse import Pulse, PulseType
from .current import Current
from .enactive import (
    AutonomicTier,
    EnactionType,
    EnactiveMessage,
    ProcessingPath,
    TIER_TO_PATH,
)
from .resonance import SilenceType, render_silence


MAGIC_V21 = b"EG21"
MAGIC_V1 = b"EG01"
HEADER_SIZE = 24
TRAILER_SIZE = 4
MIN_MESSAGE_SIZE = HEADER_SIZE + TRAILER_SIZE


class CRC16:
    POLYNOMIAL = 0xA001

    def __init__(self) -> None:
        self.table = self._build_table()

    @staticmethod
    def _build_table() -> list:
        table = []
        for i in range(256):
            crc = i
            for _ in range(8):
                if crc & 1:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc >>= 1
            table.append(crc & 0xFFFF)
        return table

    def compute(self, data: bytes) -> int:
        crc = 0xFFFF
        for byte in data:
            crc = (crc >> 8) ^ self.table[(crc ^ byte) & 0xFF]
        return crc & 0xFFFF

    def verify(self, data: bytes, expected: int) -> bool:
        return self.compute(data) == expected


_CRC = CRC16()


def _silence_byte(silence: Optional[SilenceType]) -> int:
    if silence is None:
        return 0xFF
    order = [SilenceType.MA, SilenceType.MU, SilenceType.ZEN]
    return order.index(silence) & 0xFF


def _silence_from_byte(byte: int) -> Optional[SilenceType]:
    if byte == 0xFF:
        return None
    order = [SilenceType.MA, SilenceType.MU, SilenceType.ZEN]
    if 0 <= byte < len(order):
        return order[byte]
    return None


@dataclass
class EmoGlyphMessage:
    sender_id: str
    receiver_id: str
    pulse: Pulse
    current: Current
    enactive: EnactiveMessage
    resonance_strength: float = 0.0
    silence: Optional[SilenceType] = None
    concept_label: str = ""
    version: int = 21

    def __post_init__(self) -> None:
        if not isinstance(self.sender_id, str) or not self.sender_id:
            raise ValueError("sender_id must be a non-empty string")
        if not isinstance(self.receiver_id, str) or not self.receiver_id:
            raise ValueError("receiver_id must be a non-empty string")
        if not isinstance(self.pulse, Pulse):
            raise TypeError("pulse must be a Pulse")
        if not isinstance(self.current, Current):
            raise TypeError("current must be a Current")
        if not isinstance(self.enactive, EnactiveMessage):
            raise TypeError("enactive must be an EnactiveMessage")
        if not isinstance(self.resonance_strength, (int, float)):
            raise TypeError("resonance_strength must be numeric")
        if not 0.0 <= self.resonance_strength <= 1.0:
            raise ValueError("resonance_strength must be in [0, 1]")
        if self.silence is not None and not isinstance(self.silence, SilenceType):
            raise TypeError("silence must be a SilenceType or None")
        if not isinstance(self.concept_label, str):
            raise TypeError("concept_label must be a string")
        if self.version not in (1, 21):
            raise ValueError("version must be 1 or 21")

    def _enactive_byte(self) -> int:
        enaction_order = [
            EnactionType.REACH,
            EnactionType.GUARD,
            EnactionType.ALERT,
            EnactionType.DESIRE,
            EnactionType.NURTURE,
            EnactionType.MOURN,
            EnactionType.PLAY,
        ]
        return enaction_order.index(self.enactive.enaction) & 0xFF

    def _enactive_from_byte(self, byte: int) -> EnactionType:
        enaction_order = [
            EnactionType.REACH,
            EnactionType.GUARD,
            EnactionType.ALERT,
            EnactionType.DESIRE,
            EnactionType.NURTURE,
            EnactionType.MOURN,
            EnactionType.PLAY,
        ]
        if 0 <= byte < len(enaction_order):
            return enaction_order[byte]
        return EnactionType.ALERT

    def _tier_byte(self) -> int:
        order = [AutonomicTier.VENTRAL_VAGAL, AutonomicTier.SYMPATHETIC, AutonomicTier.DORSAL_VAGAL]
        return order.index(self.enactive.autonomic_tier) & 0xFF

    def _tier_from_byte(self, byte: int) -> AutonomicTier:
        order = [AutonomicTier.VENTRAL_VAGAL, AutonomicTier.SYMPATHETIC, AutonomicTier.DORSAL_VAGAL]
        if 0 <= byte < len(order):
            return order[byte]
        return AutonomicTier.VENTRAL_VAGAL

    def to_bytes(self) -> bytes:
        sender = self.sender_id.encode("utf-8")[:8].ljust(8, b"\x00")
        receiver = self.receiver_id.encode("utf-8")[:8].ljust(8, b"\x00")
        header = bytearray(HEADER_SIZE)
        header[0:4] = MAGIC_V21 if self.version == 21 else MAGIC_V1
        header[4:12] = sender
        header[12:20] = receiver
        header[20] = self.pulse.pulse_type.value & 0xFF
        header[21] = self._enactive_byte()
        header[22] = self._tier_byte()
        header[23] = _silence_byte(self.silence)

        pulse_bytes = self.pulse.to_bytes()
        current_v = int(round((self.current.valence + 1.0) * 127.5)) & 0xFF
        current_a = int(round((self.current.arousal + 1.0) * 127.5)) & 0xFF
        current_d = int(round((self.current.dominance + 1.0) * 127.5)) & 0xFF
        current_rate = int(round(self.current.update_rate * 255.0)) & 0xFF
        resonance_b = int(round(self.resonance_strength * 255.0)) & 0xFF
        current_bytes = struct.pack(">BBBB", current_v, current_a, current_d, current_rate) + b"\x00" * 3 + struct.pack(">B", resonance_b)
        body = bytes(header) + pulse_bytes + current_bytes
        crc = _CRC.compute(body)
        return body + struct.pack(">H", crc) + b"\x00\x00"

    @classmethod
    def from_bytes(cls, data: bytes) -> "EmoGlyphMessage":
        if not isinstance(data, (bytes, bytearray)):
            raise TypeError("data must be bytes")
        if len(data) < MIN_MESSAGE_SIZE:
            raise ValueError(f"data too short ({len(data)} bytes) for header+trailer")
        magic = bytes(data[0:4])
        if magic not in (MAGIC_V1, MAGIC_V21):
            raise ValueError(f"bad magic {magic!r}")
        version = 1 if magic == MAGIC_V1 else 21
        sender = bytes(data[4:12]).rstrip(b"\x00").decode("utf-8", errors="replace") or "?"
        receiver = bytes(data[12:20]).rstrip(b"\x00").decode("utf-8", errors="replace") or "?"
        pulse_type_byte = data[20]
        enaction_byte = data[21]
        tier_byte = data[22]
        silence_byte = data[23]
        try:
            pulse_type = PulseType(pulse_type_byte)
        except ValueError:
            pulse_type = PulseType.NEUTRAL
        pulse = Pulse(
            pulse_type=pulse_type,
            valence=(data[24 + 1] / 127.5) - 1.0,
            arousal=(data[24 + 2] / 127.5) - 1.0,
            dominance=(data[24 + 3] / 127.5) - 1.0,
            intensity=data[24 + 15] / 255.0,
        )
        cv = (data[40] / 127.5) - 1.0
        ca = (data[41] / 127.5) - 1.0
        cd = (data[42] / 127.5) - 1.0
        rate = data[43] / 255.0
        resonance = data[48] / 255.0
        current = Current(valence=cv, arousal=ca, dominance=cd, update_rate=rate)
        enaction = cls._enactive_from_byte(None, enaction_byte) if False else EnactionType.ALERT
        order_enaction = [
            EnactionType.REACH,
            EnactionType.GUARD,
            EnactionType.ALERT,
            EnactionType.DESIRE,
            EnactionType.NURTURE,
            EnactionType.MOURN,
            EnactionType.PLAY,
        ]
        enaction = order_enaction[enaction_byte] if 0 <= enaction_byte < len(order_enaction) else EnactionType.ALERT
        order_tier = [AutonomicTier.VENTRAL_VAGAL, AutonomicTier.SYMPATHETIC, AutonomicTier.DORSAL_VAGAL]
        tier = order_tier[tier_byte] if 0 <= tier_byte < len(order_tier) else AutonomicTier.VENTRAL_VAGAL
        path = TIER_TO_PATH[tier]
        silence = _silence_from_byte(silence_byte)
        enactive = EnactiveMessage(
            pulse=pulse,
            enaction=enaction,
            autonomic_tier=tier,
            processing_path=path,
        )
        body_end = len(data) - TRAILER_SIZE
        body = bytes(data[:body_end])
        crc = struct.unpack(">H", data[body_end:body_end + 2])[0]
        if not _CRC.verify(body, crc):
            raise ValueError("CRC mismatch")
        return cls(
            sender_id=sender,
            receiver_id=receiver,
            pulse=pulse,
            current=current,
            enactive=enactive,
            resonance_strength=resonance,
            silence=silence,
            version=version,
        )

    def summary(self) -> str:
        silence_str = f" silence={self.silence.value}" if self.silence is not None else ""
        return (
            f"EmoGlyphMessage(v{self.version} {self.sender_id}->{self.receiver_id} "
            f"{self.pulse.pulse_type.name} {self.enactive.enaction.value} "
            f"tier={self.enactive.autonomic_tier.value}{silence_str})"
        )


if __name__ == "__main__":
    def _expect(cond: bool, label: str) -> None:
        print(("PASS" if cond else "FAIL") + f" — {label}")

    pulse = Pulse.from_type(PulseType.SEEKING, intensity=0.7)
    current = Current(valence=0.4, arousal=0.6, dominance=0.3, update_rate=0.3)
    enactive = EnactiveMessage(
        pulse=pulse,
        enaction=EnactionType.REACH,
        autonomic_tier=AutonomicTier.VENTRAL_VAGAL,
        processing_path=ProcessingPath.FULL_COGNITIVE,
        rational_payload="hello",
    )
    msg = EmoGlyphMessage(
        sender_id="alice",
        receiver_id="bob",
        pulse=pulse,
        current=current,
        enactive=enactive,
        resonance_strength=0.5,
    )
    raw = msg.to_bytes()
    _expect(raw.startswith(MAGIC_V21), "v21 magic prefix")
    _expect(len(raw) >= MIN_MESSAGE_SIZE, "min size enforced")

    parsed = EmoGlyphMessage.from_bytes(raw)
    _expect(parsed.sender_id == "alice", "sender_id round-trip")
    _expect(parsed.receiver_id == "bob", "receiver_id round-trip")
    _expect(parsed.pulse.pulse_type == PulseType.SEEKING, "pulse type round-trip")
    _expect(parsed.enactive.autonomic_tier == AutonomicTier.VENTRAL_VAGAL, "tier round-trip")
    _expect(parsed.version == 21, "version 21 round-trip")

    pulse2 = Pulse.from_type(PulseType.MA, intensity=0.5) if hasattr(PulseType, "MA") else Pulse.from_type(PulseType.PANIC, intensity=0.5)
    msg_v1 = EmoGlyphMessage(
        sender_id="a",
        receiver_id="b",
        pulse=pulse2,
        current=current,
        enactive=EnactiveMessage(
            pulse=pulse2,
            enaction=EnactionType.MOURN,
            autonomic_tier=AutonomicTier.DORSAL_VAGAL,
            processing_path=ProcessingPath.MINIMAL_BUFFER,
        ),
        silence=SilenceType.ZEN,
        version=1,
    )
    raw_v1 = msg_v1.to_bytes()
    _expect(raw_v1.startswith(MAGIC_V1), "v1 magic prefix")
    parsed_v1 = EmoGlyphMessage.from_bytes(raw_v1)
    _expect(parsed_v1.version == 1, "v1 version detected")
    _expect(parsed_v1.silence == SilenceType.ZEN, "silence ZEN round-trip")

    bad = bytearray(raw)
    bad[10] = (bad[10] + 1) & 0xFF
    try:
        EmoGlyphMessage.from_bytes(bytes(bad))
    except ValueError:
        _expect(True, "CRC mismatch detected")
    else:
        _expect(False, "CRC mismatch detected")

    try:
        EmoGlyphMessage(
            sender_id="",
            receiver_id="bob",
            pulse=pulse,
            current=current,
            enactive=enactive,
        )
    except ValueError:
        _expect(True, "empty sender_id rejected")
    else:
        _expect(False, "empty sender_id rejected")

    print("OK — message.py smoke tests done")
