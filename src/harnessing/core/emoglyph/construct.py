from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

from .pulse import Pulse, PulseType
from .current import Current, Emotion, REGISTRY, EmotionCategory


class FiveElement(Enum):
    WOOD = "wood"
    FIRE = "fire"
    EARTH = "earth"
    METAL = "metal"
    WATER = "water"


SHENG_CYCLE: Dict[FiveElement, FiveElement] = {
    FiveElement.WOOD: FiveElement.FIRE,
    FiveElement.FIRE: FiveElement.EARTH,
    FiveElement.EARTH: FiveElement.METAL,
    FiveElement.METAL: FiveElement.WATER,
    FiveElement.WATER: FiveElement.WOOD,
}

KE_CYCLE: Dict[FiveElement, FiveElement] = {
    FiveElement.WOOD: FiveElement.EARTH,
    FiveElement.EARTH: FiveElement.WATER,
    FiveElement.WATER: FiveElement.FIRE,
    FiveElement.FIRE: FiveElement.METAL,
    FiveElement.METAL: FiveElement.WOOD,
}

PULSE_TO_ELEMENT: Dict[PulseType, FiveElement] = {
    PulseType.RAGE: FiveElement.WOOD,
    PulseType.PLAY: FiveElement.FIRE,
    PulseType.CARE: FiveElement.EARTH,
    PulseType.PANIC: FiveElement.METAL,
    PulseType.FEAR: FiveElement.WATER,
}


def element_of(pulse: Pulse) -> FiveElement:
    if pulse.pulse_type in PULSE_TO_ELEMENT:
        return PULSE_TO_ELEMENT[pulse.pulse_type]
    return FiveElement.EARTH


class TransitionPath(Enum):
    SHENG = "sheng"
    KE = "ke"
    STAY = "stay"


@dataclass
class FiveElementTransition:
    cycle_position: FiveElement = FiveElement.WOOD
    history: List[FiveElement] = field(default_factory=list)

    def next_sheng(self) -> FiveElement:
        return SHENG_CYCLE[self.cycle_position]

    def next_ke(self) -> FiveElement:
        return KE_CYCLE[self.cycle_position]

    def advance(self, path: TransitionPath) -> FiveElement:
        if path == TransitionPath.STAY:
            target = self.cycle_position
        elif path == TransitionPath.SHENG:
            target = self.next_sheng()
        elif path == TransitionPath.KE:
            target = self.next_ke()
        else:
            raise ValueError(f"unknown path {path!r}")
        self.history.append(self.cycle_position)
        self.cycle_position = target
        return target

    def element_for_pulse(self, pulse: Pulse) -> FiveElement:
        return element_of(pulse)

    def map_pulse(self, pulse: Pulse) -> Pulse:
        if pulse.pulse_type in PULSE_TO_ELEMENT:
            return pulse
        new_type = {
            FiveElement.WOOD: PulseType.RAGE,
            FiveElement.FIRE: PulseType.PLAY,
            FiveElement.EARTH: PulseType.CARE,
            FiveElement.METAL: PulseType.PANIC,
            FiveElement.WATER: PulseType.FEAR,
        }[self.cycle_position]
        return Pulse(
            pulse_type=new_type,
            valence=pulse.valence,
            arousal=pulse.arousal,
            dominance=pulse.dominance,
            intensity=pulse.intensity,
        )


@dataclass
class PredictiveProcessing:
    valence_prior: float = 0.0
    arousal_prior: float = 0.0
    dominance_prior: float = 0.0
    precision: float = 1.0
    free_energy: float = 0.0
    steps: int = 0

    def __post_init__(self) -> None:
        for name in ("valence_prior", "arousal_prior", "dominance_prior"):
            v = getattr(self, name)
            if not isinstance(v, (int, float)):
                raise TypeError(f"{name} must be numeric")
            if v < -1.0 or v > 1.0:
                raise ValueError(f"{name}={v} out of [-1, 1]")
        if not 0.0 < self.precision <= 10.0:
            raise ValueError("precision must be in (0, 10]")
        self._clamp_priors()

    def _clamp_priors(self) -> None:
        self.valence_prior = max(-1.0, min(1.0, self.valence_prior))
        self.arousal_prior = max(-1.0, min(1.0, self.arousal_prior))
        self.dominance_prior = max(-1.0, min(1.0, self.dominance_prior))

    def predict(self) -> Tuple[float, float, float]:
        return (self.valence_prior, self.arousal_prior, self.dominance_prior)

    def surprise(self, current: Current) -> Tuple[float, float, float]:
        if not isinstance(current, Current):
            raise TypeError("current must be a Current")
        cv, ca, cd = current.as_tuple()
        return (
            cv - self.valence_prior,
            ca - self.arousal_prior,
            cd - self.dominance_prior,
        )

    def adapt(self, current: Current) -> float:
        if not isinstance(current, Current):
            raise TypeError("current must be a Current")
        sv, sa, sd = self.surprise(current)
        gain = 1.0 / max(self.precision, 1e-6)
        self.valence_prior = max(-1.0, min(1.0, self.valence_prior + gain * sv))
        self.arousal_prior = max(-1.0, min(1.0, self.arousal_prior + gain * sa))
        self.dominance_prior = max(-1.0, min(1.0, self.dominance_prior + gain * sd))
        self.free_energy = math.sqrt(sv * sv + sa * sa + sd * sd)
        self.steps += 1
        return self.free_energy


class EmotionTransition:
    @staticmethod
    def transition(
        emotion: Emotion,
        path: TransitionPath,
        engine: FiveElementTransition,
    ) -> Emotion:
        if not isinstance(emotion, Emotion):
            raise TypeError("emotion must be an Emotion")
        if not isinstance(engine, FiveElementTransition):
            raise TypeError("engine must be a FiveElementTransition")
        new_element = engine.advance(path)
        new_concept_vec = {
            FiveElement.WOOD: (0.6, 0.8, 0.5),
            FiveElement.FIRE: (0.9, 0.7, 0.3),
            FiveElement.EARTH: (0.4, -0.3, 0.6),
            FiveElement.METAL: (-0.6, 0.2, -0.4),
            FiveElement.WATER: (-0.7, 0.5, -0.6),
        }[new_element]
        name = f"{emotion.name}+{path.value}"
        return Emotion(
            name=name,
            valence=new_concept_vec[0],
            arousal=new_concept_vec[1],
            dominance=new_concept_vec[2],
            concept=f"transition:{new_element.value}",
            context=emotion.context,
        )


def _seed_concept_for(pulse: Pulse) -> EmotionCategory:
    element = element_of(pulse)
    name = f"seed_{element.value}"
    if REGISTRY.find(name) is None:
        REGISTRY.register(EmotionCategory(name, (pulse.valence, pulse.arousal, pulse.dominance), f"seed for {element.value}"))
    return REGISTRY.get(name)


def construct_from_pulse(
    pulse: Pulse,
    current: Current,
    context: Optional[object] = None,
    engine: Optional[FiveElementTransition] = None,
    pp: Optional[PredictiveProcessing] = None,
) -> Emotion:
    if not isinstance(pulse, Pulse):
        raise TypeError("pulse must be a Pulse")
    if not isinstance(current, Current):
        raise TypeError("current must be a Current")
    if engine is not None and not isinstance(engine, FiveElementTransition):
        raise TypeError("engine must be a FiveElementTransition")
    if pp is not None:
        if not isinstance(pp, PredictiveProcessing):
            raise TypeError("pp must be a PredictiveProcessing")
        pp.adapt(current)
    seed = _seed_concept_for(pulse)
    if engine is not None:
        element = engine.element_for_pulse(pulse)
        engine.cycle_position = element
    emotion = Emotion(
        name=seed.name,
        valence=current.valence,
        arousal=current.arousal,
        dominance=current.dominance,
        concept=seed.description,
        context=str(context) if context is not None else "neutral",
    )
    return emotion


if __name__ == "__main__":
    def _expect(cond: bool, label: str) -> None:
        print(("PASS" if cond else "FAIL") + f" — {label}")

    fe = FiveElementTransition(cycle_position=FiveElement.WOOD)
    _expect(fe.next_sheng() == FiveElement.FIRE, "wood sheng -> fire")
    _expect(fe.next_ke() == FiveElement.EARTH, "wood ke -> earth")

    fe.advance(TransitionPath.SHENG)
    _expect(fe.cycle_position == FiveElement.FIRE, "advance SHENG moves cycle")
    fe.advance(TransitionPath.KE)
    _expect(fe.cycle_position == FiveElement.METAL, "fire ke -> metal")

    p_fear = Pulse.from_type(PulseType.FEAR, intensity=0.7)
    _expect(element_of(p_fear) == FiveElement.WATER, "FEAR -> water element")

    p_neutral = Pulse(PulseType.NEUTRAL, 0.0, 0.0, 0.0, 0.5)
    fe2 = FiveElementTransition(cycle_position=FiveElement.FIRE)
    mapped = fe2.map_pulse(p_neutral)
    _expect(mapped.pulse_type in (PulseType.PLAY, PulseType.RAGE, PulseType.CARE, PulseType.PANIC, PulseType.FEAR), "neutral pulse mapped to a TCM element")

    pp = PredictiveProcessing(valence_prior=0.1, arousal_prior=0.1, dominance_prior=0.0, precision=1.0)
    c = Current(valence=0.6, arousal=0.7, dominance=0.2)
    fe_pred = pp.predict()
    _expect(len(fe_pred) == 3, "predict returns 3-tuple")
    surprise = pp.surprise(c)
    _expect(surprise[0] > 0.0, "surprise > 0 for state above prior")
    fe_before = pp.free_energy
    pp.adapt(c)
    _expect(pp.free_energy > 0.0, "free_energy computed after adapt")
    _expect(pp.valence_prior != 0.1, "priors updated after adapt")
    _expect(fe_before == 0.0, "free_energy is 0 before any adapt")

    e = Emotion(name="joy", valence=0.6, arousal=0.7, dominance=0.2, concept="happiness")
    new_e = EmotionTransition.transition(e, TransitionPath.SHENG, FiveElementTransition(cycle_position=FiveElement.WOOD))
    _expect("+sheng" in new_e.name, "transition name includes path")
    new_e2 = EmotionTransition.transition(e, TransitionPath.KE, FiveElementTransition(cycle_position=FiveElement.WOOD))
    _expect("+ke" in new_e2.name, "transition ke name includes path")

    try:
        PredictiveProcessing(valence_prior=2.0)
    except ValueError:
        _expect(True, "out-of-range prior rejected")
    else:
        _expect(False, "out-of-range prior rejected")

    print("OK — construct.py smoke tests done")
