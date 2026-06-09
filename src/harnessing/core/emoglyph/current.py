from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, List, Optional, Tuple

from .pulse import Pulse, PulseType


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


@dataclass
class Current:
    valence: float = 0.0
    arousal: float = 0.0
    dominance: float = 0.0
    update_rate: float = 0.3
    retention: List[Tuple[float, float, float]] = field(default_factory=list)
    retention_size: int = 8

    def __post_init__(self) -> None:
        for name in ("valence", "arousal", "dominance"):
            v = getattr(self, name)
            if not isinstance(v, (int, float)):
                raise TypeError(f"{name} must be numeric")
            if v < -1.0 or v > 1.0:
                raise ValueError(f"{name}={v} out of [-1, 1]")
        if not 0.0 <= self.update_rate <= 1.0:
            raise ValueError(f"update_rate={self.update_rate} out of [0, 1]")
        if self.retention_size < 1:
            raise ValueError("retention_size must be >= 1")

    def _remember(self) -> None:
        self.retention.append((self.valence, self.arousal, self.dominance))
        if len(self.retention) > self.retention_size:
            self.retention = self.retention[-self.retention_size:]

    def update(self, pulse: Pulse) -> "Current":
        if not isinstance(pulse, Pulse):
            raise TypeError("pulse must be a Pulse")
        alpha = self.update_rate * pulse.intensity
        self.valence = _clamp(self.valence * (1 - alpha) + pulse.valence * alpha, -1.0, 1.0)
        self.arousal = _clamp(self.arousal * (1 - alpha) + pulse.arousal * alpha, -1.0, 1.0)
        self.dominance = _clamp(self.dominance * (1 - alpha) + pulse.dominance * alpha, -1.0, 1.0)
        self._remember()
        return self

    def protend(self) -> Tuple[float, float, float]:
        if not self.retention:
            return (self.valence, self.arousal, self.dominance)
        last_v = sum(p[0] for p in self.retention) / len(self.retention)
        last_a = sum(p[1] for p in self.retention) / len(self.retention)
        last_d = sum(p[2] for p in self.retention) / len(self.retention)
        return (
            _clamp(2 * self.valence - last_v, -1.0, 1.0),
            _clamp(2 * self.arousal - last_a, -1.0, 1.0),
            _clamp(2 * self.dominance - last_d, -1.0, 1.0),
        )

    def reset(self) -> "Current":
        self.valence = 0.0
        self.arousal = 0.0
        self.dominance = 0.0
        self.retention.clear()
        return self

    def as_tuple(self) -> Tuple[float, float, float]:
        return (self.valence, self.arousal, self.dominance)


@dataclass
class Emotion:
    name: str
    valence: float
    arousal: float
    dominance: float
    concept: str
    context: str = ""

    def __post_init__(self) -> None:
        for name in ("valence", "arousal", "dominance"):
            v = getattr(self, name)
            if not isinstance(v, (int, float)):
                raise TypeError(f"{name} must be numeric")
            if v < -1.0 or v > 1.0:
                raise ValueError(f"{name}={v} out of [-1, 1]")

    def __repr__(self) -> str:
        return f"Emotion({self.name!r}, ctx={self.context!r}, VAD=({self.valence:+.2f},{self.arousal:+.2f},{self.dominance:+.2f}))"


class EmotionCategory:
    def __init__(self, name: str, concept_vector: Tuple[float, float, float], description: str = "") -> None:
        self.name = name
        self.concept_vector = concept_vector
        self.description = description

    def distance(self, v: float, a: float, d: float) -> float:
        dv = self.concept_vector[0] - v
        da = self.concept_vector[1] - a
        dd = self.concept_vector[2] - d
        return (dv * dv + da * da + dd * dd) ** 0.5

    def __repr__(self) -> str:
        return f"EmotionCategory({self.name!r}, VAD={self.concept_vector})"


class _EmotionCategoryRegistry:
    def __init__(self) -> None:
        self._items: Dict[str, EmotionCategory] = {}

    def register(self, category: EmotionCategory, *, overwrite: bool = False) -> None:
        if not isinstance(category, EmotionCategory):
            raise TypeError("category must be an EmotionCategory")
        if category.name in self._items and not overwrite:
            raise ValueError(f"category {category.name!r} already registered")
        self._items[category.name] = category

    def get(self, name: str) -> EmotionCategory:
        if name not in self._items:
            raise KeyError(name)
        return self._items[name]

    def find(self, name: str) -> Optional[EmotionCategory]:
        return self._items.get(name)

    def list(self) -> List[str]:
        return sorted(self._items.keys())

    def nearest(self, v: float, a: float, d: float) -> EmotionCategory:
        if not self._items:
            raise RuntimeError("no categories registered")
        best = min(self._items.values(), key=lambda c: c.distance(v, a, d))
        return best

    def remove(self, name: str) -> None:
        if name not in self._items:
            raise KeyError(name)
        del self._items[name]

    def clear(self) -> None:
        self._items.clear()

    def __len__(self) -> int:
        return len(self._items)

    def __contains__(self, name: object) -> bool:
        return name in self._items


REGISTRY = _EmotionCategoryRegistry()
REGISTRY.register(EmotionCategory("excitement", (0.6, 0.8, 0.4), "high-arousal positive"))
REGISTRY.register(EmotionCategory("anxiety", (0.0, 0.8, -0.4), "high-arousal neutral-negative"))
REGISTRY.register(EmotionCategory("calm", (0.4, -0.6, 0.2), "low-arousal positive"))
REGISTRY.register(EmotionCategory("grief", (-0.8, 0.3, -0.7), "low-valence low-dominance"))


def _build_context_default(context: object) -> str:
    if isinstance(context, dict):
        role = context.get("role", "neutral")
        scene = context.get("scene", "neutral")
        return f"role={role};scene={scene}"
    return str(context)


def construct(
    current: Current,
    concept: EmotionCategory,
    context: object = None,
) -> Emotion:
    if not isinstance(current, Current):
        raise TypeError("current must be a Current")
    if not isinstance(concept, EmotionCategory):
        raise TypeError("concept must be an EmotionCategory")
    v, a, d = current.as_tuple()
    cw_v, cw_a, cw_d = concept.concept_vector
    w_concept = 0.6
    w_state = 1.0 - w_concept
    blended_v = _clamp(v * w_state + cw_v * w_concept, -1.0, 1.0)
    blended_a = _clamp(a * w_state + cw_a * w_concept, -1.0, 1.0)
    blended_d = _clamp(d * w_state + cw_d * w_concept, -1.0, 1.0)
    ctx = _build_context_default(context) if context is not None else "neutral"
    return Emotion(
        name=concept.name,
        valence=blended_v,
        arousal=blended_a,
        dominance=blended_d,
        concept=concept.description or concept.name,
        context=ctx,
    )


if __name__ == "__main__":
    def _expect(cond: bool, label: str) -> None:
        print(("PASS" if cond else "FAIL") + f" — {label}")

    c = Current(valence=0.0, arousal=0.0, dominance=0.0, update_rate=0.4)
    p = Pulse.from_type(PulseType.FEAR, intensity=0.8)
    c.update(p)
    _expect(c.arousal > 0.0, "FEAR pulse raises arousal")

    c2 = Current(valence=0.5, arousal=0.5, dominance=0.0, update_rate=0.1)
    for _ in range(5):
        c2.update(Pulse.from_type(PulseType.PLAY, intensity=0.4))
    _expect(c2.arousal > 0.4, "EMA accumulates over multiple updates")

    excitement = REGISTRY.get("excitement")
    e1 = construct(Current(valence=0.6, arousal=0.7, dominance=0.5), excitement, {"role": "friend"})
    _expect(e1.context == "role=friend;scene=neutral", "context dict serialised")
    e2 = construct(Current(valence=0.6, arousal=0.7, dominance=0.5), excitement, "casual")
    _expect(e2.context == "casual", "context string passed through")

    e3 = construct(Current(valence=0.1, arousal=0.6, dominance=-0.4), REGISTRY.get("anxiety"), None)
    _expect(e3.name == "anxiety", "same current + anxiety concept = anxiety")

    near = REGISTRY.nearest(-0.7, 0.4, -0.6)
    _expect(near.name == "grief", "nearest finds grief for sad-pull")

    c3 = Current(valence=0.0, arousal=0.0, dominance=0.0, update_rate=0.5)
    c3.update(Pulse.from_type(PulseType.PANIC, 0.7))
    proto = c3.protend()
    _expect(isinstance(proto, tuple) and len(proto) == 3, "protend returns 3-tuple")

    try:
        Current(valence=2.0, arousal=0.0, dominance=0.0)
    except ValueError:
        _expect(True, "out-of-range valence rejected")
    else:
        _expect(False, "out-of-range valence rejected")

    print("OK — current.py smoke tests done")
