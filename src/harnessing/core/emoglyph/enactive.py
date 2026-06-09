from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from .pulse import Pulse, PulseType
from .current import Current


class EnactionType(Enum):
    REACH = "reach"
    GUARD = "guard"
    ALERT = "alert"
    DESIRE = "desire"
    NURTURE = "nurture"
    MOURN = "mourn"
    PLAY = "play"


class AutonomicTier(Enum):
    VENTRAL_VAGAL = "ventral_vagal"
    SYMPATHETIC = "sympathetic"
    DORSAL_VAGAL = "dorsal_vagal"


class ProcessingPath(Enum):
    FULL_COGNITIVE = "full_cognitive"
    FAST_REACTION = "fast_reaction"
    MINIMAL_BUFFER = "minimal_buffer"


TIER_TO_PATH = {
    AutonomicTier.VENTRAL_VAGAL: ProcessingPath.FULL_COGNITIVE,
    AutonomicTier.SYMPATHETIC: ProcessingPath.FAST_REACTION,
    AutonomicTier.DORSAL_VAGAL: ProcessingPath.MINIMAL_BUFFER,
}

PULSE_TO_ENACTION = {
    PulseType.SEEKING: EnactionType.REACH,
    PulseType.RAGE: EnactionType.GUARD,
    PulseType.FEAR: EnactionType.ALERT,
    PulseType.LUST: EnactionType.DESIRE,
    PulseType.CARE: EnactionType.NURTURE,
    PulseType.PANIC: EnactionType.MOURN,
    PulseType.PLAY: EnactionType.PLAY,
}

PATH_LATENCY_TARGETS_MS = {
    ProcessingPath.FULL_COGNITIVE: 10,
    ProcessingPath.FAST_REACTION: 1,
    ProcessingPath.MINIMAL_BUFFER: 100,
}


@dataclass
class EnactiveMessage:
    pulse: Pulse
    enaction: EnactionType
    autonomic_tier: AutonomicTier
    processing_path: ProcessingPath
    rational_payload: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.pulse, Pulse):
            raise TypeError("pulse must be a Pulse")
        if not isinstance(self.enaction, EnactionType):
            raise TypeError("enaction must be an EnactionType")
        if not isinstance(self.autonomic_tier, AutonomicTier):
            raise TypeError("autonomic_tier must be an AutonomicTier")
        if not isinstance(self.processing_path, ProcessingPath):
            raise TypeError("processing_path must be a ProcessingPath")
        expected_path = TIER_TO_PATH[self.autonomic_tier]
        if self.processing_path != expected_path:
            raise ValueError(
                f"processing_path {self.processing_path} does not match "
                f"autonomic_tier {self.autonomic_tier} (expected {expected_path})"
            )
        if self.rational_payload is not None and not isinstance(self.rational_payload, str):
            raise TypeError("rational_payload must be a string or None")
        if not isinstance(self.metadata, dict):
            raise TypeError("metadata must be a dict")

    @property
    def latency_target_ms(self) -> int:
        return PATH_LATENCY_TARGETS_MS[self.processing_path]

    @property
    def needs_buffer(self) -> bool:
        return self.processing_path == ProcessingPath.MINIMAL_BUFFER

    def to_dict(self) -> dict:
        return {
            "pulse_type": self.pulse.pulse_type.name,
            "enaction": self.enaction.value,
            "autonomic_tier": self.autonomic_tier.value,
            "processing_path": self.processing_path.value,
            "rational_payload": self.rational_payload,
            "metadata": self.metadata,
        }


def default_enaction_for(pulse: Pulse) -> EnactionType:
    if pulse.pulse_type in PULSE_TO_ENACTION:
        return PULSE_TO_ENACTION[pulse.pulse_type]
    return EnactionType.ALERT


def build_message(
    pulse: Pulse,
    autonomic_tier: AutonomicTier,
    rational_payload: Optional[str] = None,
    override_enaction: Optional[EnactionType] = None,
    metadata: Optional[dict] = None,
) -> EnactiveMessage:
    if not isinstance(pulse, Pulse):
        raise TypeError("pulse must be a Pulse")
    if not isinstance(autonomic_tier, AutonomicTier):
        raise TypeError("autonomic_tier must be an AutonomicTier")
    enaction = override_enaction if override_enaction is not None else default_enaction_for(pulse)
    return EnactiveMessage(
        pulse=pulse,
        enaction=enaction,
        autonomic_tier=autonomic_tier,
        processing_path=TIER_TO_PATH[autonomic_tier],
        rational_payload=rational_payload,
        metadata=metadata or {},
    )


def route_to_processor(autonomic_tier: AutonomicTier) -> ProcessingPath:
    if not isinstance(autonomic_tier, AutonomicTier):
        raise TypeError("autonomic_tier must be an AutonomicTier")
    return TIER_TO_PATH[autonomic_tier]


if __name__ == "__main__":
    def _expect(cond: bool, label: str) -> None:
        print(("PASS" if cond else "FAIL") + f" — {label}")

    p_fear = Pulse.from_type(PulseType.FEAR, intensity=0.8)
    msg = build_message(p_fear, AutonomicTier.SYMPATHETIC, rational_payload="step back")
    _expect(msg.enaction == EnactionType.ALERT, "FEAR pulse -> ALERT enaction")
    _expect(msg.processing_path == ProcessingPath.FAST_REACTION, "SYMPATHETIC -> FAST_REACTION path")
    _expect(msg.latency_target_ms == 1, "FAST_REACTION latency 1ms")
    _expect(msg.rational_payload == "step back", "rational_payload preserved")

    msg_v = build_message(p_fear, AutonomicTier.VENTRAL_VAGAL)
    _expect(msg_v.processing_path == ProcessingPath.FULL_COGNITIVE, "VENTRAL -> FULL")
    _expect(msg_v.latency_target_ms == 10, "FULL latency 10ms")

    msg_d = build_message(p_fear, AutonomicTier.DORSAL_VAGAL)
    _expect(msg_d.processing_path == ProcessingPath.MINIMAL_BUFFER, "DORSAL -> MINIMAL")
    _expect(msg_d.needs_buffer is True, "DORSAL needs buffer")
    _expect(msg_d.latency_target_ms == 100, "MINIMAL latency 100ms")

    try:
        EnactiveMessage(
            pulse=p_fear,
            enaction=EnactionType.ALERT,
            autonomic_tier=AutonomicTier.VENTRAL_VAGAL,
            processing_path=ProcessingPath.FAST_REACTION,
        )
    except ValueError:
        _expect(True, "tier/path mismatch rejected")
    else:
        _expect(False, "tier/path mismatch rejected")

    _expect(default_enaction_for(Pulse.from_type(PulseType.SEEKING)) == EnactionType.REACH, "SEEKING -> REACH")
    _expect(default_enaction_for(Pulse.from_type(PulseType.CARE)) == EnactionType.NURTURE, "CARE -> NURTURE")
    _expect(default_enaction_for(Pulse.from_type(PulseType.PANIC)) == EnactionType.MOURN, "PANIC -> MOURN")

    d = msg.to_dict()
    _expect(d["processing_path"] == "fast_reaction", "to_dict includes processing_path")
    _expect(d["autonomic_tier"] == "sympathetic", "to_dict includes autonomic_tier")

    print("OK — enactive.py smoke tests done")
