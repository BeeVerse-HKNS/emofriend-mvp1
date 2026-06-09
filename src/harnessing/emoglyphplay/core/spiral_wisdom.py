"""SpiralWisdom Engine — 螺旋智慧引擎.

Formula:
    SpiralWisdom = ∮ₜ[⊕(Light_τ, Dark_τ)^Ξ × Context_τ × EthicsGuard_τ] dτ - Σ Drift(τ)

Core innovation: Captures the DYNAMIC EVOLUTION of "知暗行明" (Know the dark, act in the light).
Unlike the static LightDarkBalance formula, SpiralWisdom models how repeated cycles of
dark-awareness and light-action create a self-reinforcing spiral that converges to
enlightened action over time.

Sub-formulas:
    Dark_{τ+1}   = Dark_τ + Resistance(Light_τ)         — Acting light reveals more dark
    Light_{τ+1}  = Light_τ + Wisdom(Dark_τ)              — Knowing dark improves light action
    Residue(τ)   = log(Dark_τ × Light_τ) × EthicsGuard_τ — Wisdom residue from each cycle
    Drift(τ)     = |Alignment(τ) - Alignment(0)| × e^(-λτ) — Value drift correction

New Operator:
    ∮ (Spiral Integral) — Temporal spiral accumulation across cycles.
    Unlike + (instant union), ∮ accumulates wisdom with FEEDBACK,
    creating a self-reinforcing spiral that converges or diverges.

Convergence:
    lim(t→∞) |SpiralWisdom(t) - SpiralWisdom(t-1)| < ε
    The spiral converges when wisdom gain per cycle becomes negligible.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from harnessing.emoglyphplay.core.context_engine import ContextEngine, ContextSnapshot
from harnessing.emoglyphplay.core.ethics_guard import EthicsGuard, ViolationSeverity
from harnessing.emoglyphplay.core.light_dark_balance import (
    LightDarkBalanceEngine,
    LightDarkBalanceResult,
    StrategyMode,
)


class SpiralPhase(Enum):
    """Phases of the wisdom spiral cycle."""

    KNOW_DARK = "know_dark"
    ACT_LIGHT = "act_light"
    ENCOUNTER_RESISTANCE = "encounter_resistance"
    EXTRACT_WISDOM = "extract_wisdom"


class SpiralStatus(Enum):
    """Status of the spiral convergence."""

    CONVERGING = "converging"
    DIVERGING = "diverging"
    STABLE = "stable"
    INITIALIZING = "initializing"


@dataclass
class WisdomResidue:
    """Wisdom residue from a single spiral cycle."""

    cycle: int
    dark_level: float
    light_level: float
    residue_value: float
    ethics_score: float
    context_hash: str
    timestamp: float = 0.0


@dataclass
class DriftMeasurement:
    """Value alignment drift measurement."""

    cycle: int
    alignment_current: float
    alignment_initial: float
    drift_raw: float
    drift_corrected: float
    decay_factor: float


@dataclass
class SpiralCycleResult:
    """Result of a single spiral cycle."""

    cycle: int
    phase: SpiralPhase
    dark_before: float
    dark_after: float
    light_before: float
    light_after: float
    resistance_encountered: float
    wisdom_gained: float
    residue: WisdomResidue | None = None
    drift: DriftMeasurement | None = None


@dataclass
class SpiralWisdomResult:
    """Complete result of the SpiralWisdom computation."""

    total_wisdom: float
    total_drift_correction: float
    net_wisdom: float
    status: SpiralStatus
    convergence_ratio: float
    cycles_completed: int
    residues: list[WisdomResidue] = field(default_factory=list)
    drifts: list[DriftMeasurement] = field(default_factory=list)
    cycle_results: list[SpiralCycleResult] = field(default_factory=list)


class SpiralWisdomEngine:
    """SpiralWisdom Engine — Temporal Spiral Dynamics for EmoGlyphPlay.

    Implements the SpiralWisdom formula that captures the dynamic evolution
    of the LightDarkBalance over time. Each cycle of "know dark → act light"
    creates a wisdom residue that amplifies subsequent cycles.

    Args:
        balance_engine: The LightDarkBalance engine for per-cycle balance.
        context_engine: The Context engine for environment sensing.
        ethics_guard: The Ethics guard for ethical filtering.
        decay_lambda: Decay rate for drift correction (default: 0.1).
        convergence_epsilon: Convergence threshold (default: 0.01).
        max_cycles: Maximum spiral cycles before forcing convergence check.
    """

    def __init__(
        self,
        balance_engine: LightDarkBalanceEngine | None = None,
        context_engine: ContextEngine | None = None,
        ethics_guard: EthicsGuard | None = None,
        decay_lambda: float = 0.1,
        convergence_epsilon: float = 0.01,
        max_cycles: int = 100,
    ) -> None:
        self.balance_engine = balance_engine or LightDarkBalanceEngine(
            context_engine or ContextEngine()
        )
        self.context_engine = context_engine or ContextEngine()
        self.ethics_guard = ethics_guard or EthicsGuard()
        self.decay_lambda = decay_lambda
        self.convergence_epsilon = convergence_epsilon
        self.max_cycles = max_cycles

        self._residues: list[WisdomResidue] = []
        self._drifts: list[DriftMeasurement] = []
        self._cycle_results: list[SpiralCycleResult] = []
        self._initial_alignment: float = 1.0
        self._current_dark: float = 0.5
        self._current_light: float = 0.5

    def compute_residue(
        self, dark: float, light: float, ethics_score: float, cycle: int
    ) -> WisdomResidue:
        """Compute wisdom residue for a cycle: Residue(τ) = log(Dark_τ × Light_τ) × EthicsGuard_τ.

        Args:
            dark: Current dark awareness level (0-1).
            light: Current light action level (0-1).
            ethics_score: Ethics guard score for this cycle (0-1).
            cycle: Cycle number.

        Returns:
            WisdomResidue with computed value.
        """
        product = max(dark * light, 1e-10)
        residue_value = math.log(product) * ethics_score
        return WisdomResidue(
            cycle=cycle,
            dark_level=dark,
            light_level=light,
            residue_value=residue_value,
            ethics_score=ethics_score,
            context_hash="",
        )

    def compute_drift(
        self, current_alignment: float, cycle: int
    ) -> DriftMeasurement:
        """Compute value drift: Drift(τ) = |Alignment(τ) - Alignment(0)| × e^(-λτ).

        Args:
            current_alignment: Current value alignment score (0-1).
            cycle: Cycle number.

        Returns:
            DriftMeasurement with raw and decay-corrected drift.
        """
        drift_raw = abs(current_alignment - self._initial_alignment)
        decay_factor = math.exp(-self.decay_lambda * cycle)
        drift_corrected = drift_raw * decay_factor
        return DriftMeasurement(
            cycle=cycle,
            alignment_current=current_alignment,
            alignment_initial=self._initial_alignment,
            drift_raw=drift_raw,
            drift_corrected=drift_corrected,
            decay_factor=decay_factor,
        )

    def compute_resistance(self, light_action: float, context: ContextSnapshot) -> float:
        """Compute resistance encountered when acting light.

        Dark_{τ+1} = Dark_τ + Resistance(Light_τ)
        Resistance is higher in competitive/strict environments.

        Args:
            light_action: Level of light action taken (0-1).
            context: Current context snapshot.

        Returns:
            Resistance level (0-1).
        """
        base_resistance = light_action * 0.3
        competition_factor = {
            "low": 0.5,
            "medium": 1.0,
            "high": 1.5,
            "intense": 2.0,
        }.get(context.competition.value if hasattr(context.competition, "value") else str(context.competition), 1.0)
        regulatory_factor = {
            "light": 0.8,
            "moderate": 1.0,
            "strict": 1.3,
            "restrictive": 1.6,
        }.get(context.law.value if hasattr(context.law, "value") else str(context.law), 1.0)
        return min(base_resistance * competition_factor * regulatory_factor, 1.0)

    def compute_wisdom(self, dark_awareness: float, ethics_score: float) -> float:
        """Compute wisdom gained from dark awareness.

        Light_{τ+1} = Light_τ + Wisdom(Dark_τ)
        Wisdom is proportional to dark awareness, filtered by ethics.

        Args:
            dark_awareness: Level of dark awareness (0-1).
            ethics_score: Ethics guard score (0-1).

        Returns:
            Wisdom gained (0-1).
        """
        return dark_awareness * ethics_score * 0.2

    def run_cycle(
        self,
        context: ContextSnapshot | None = None,
        user_signals: dict | None = None,
    ) -> SpiralCycleResult:
        """Run a single spiral cycle: Know Dark → Act Light → Encounter Resistance → Extract Wisdom.

        Args:
            context: Optional context snapshot (auto-sensed if None).
            user_signals: Optional user behavioral signals.

        Returns:
            SpiralCycleResult with cycle details.
        """
        cycle = len(self._cycle_results) + 1
        if context is None:
            input_text = ""
            if user_signals and isinstance(user_signals, dict):
                input_text = " ".join(str(v) for v in user_signals.values() if isinstance(v, str))
            context = self.context_engine.sense(input_text or "spiral cycle default context")

        dark_before = self._current_dark
        light_before = self._current_light

        balance_result = self.balance_engine.analyze(
            "spiral wisdom cycle analysis", context_override=None
        )

        ethics_result = self.ethics_guard.check(
            action="spiral_cycle",
            context={"dark": dark_before, "light": light_before, "cycle": cycle},
        )
        ethics_score = 1.0 if ethics_result.is_ethical else 0.0

        resistance = self.compute_resistance(light_before, context)
        dark_after = min(dark_before + resistance, 1.0)

        wisdom = self.compute_wisdom(dark_after, ethics_score)
        light_after = min(light_before + wisdom, 1.0)

        self._current_dark = dark_after
        self._current_light = light_after

        residue = self.compute_residue(dark_after, light_after, ethics_score, cycle)
        self._residues.append(residue)

        current_alignment = ethics_score * (1.0 - abs(dark_after - light_after))
        drift = self.compute_drift(current_alignment, cycle)
        self._drifts.append(drift)

        result = SpiralCycleResult(
            cycle=cycle,
            phase=SpiralPhase.EXTRACT_WISDOM,
            dark_before=dark_before,
            dark_after=dark_after,
            light_before=light_before,
            light_after=light_after,
            resistance_encountered=resistance,
            wisdom_gained=wisdom,
            residue=residue,
            drift=drift,
        )
        self._cycle_results.append(result)
        return result

    def compute_spiral(self, num_cycles: int = 10) -> SpiralWisdomResult:
        """Compute the full SpiralWisdom formula over multiple cycles.

        SpiralWisdom = ∮ₜ[⊕(Light_τ, Dark_τ)^Ξ × Context_τ × EthicsGuard_τ] dτ - Σ Drift(τ)

        Args:
            num_cycles: Number of spiral cycles to compute.

        Returns:
            SpiralWisdomResult with complete spiral analysis.
        """
        for _ in range(num_cycles):
            self.run_cycle()

        total_wisdom = sum(r.residue_value for r in self._residues)
        total_drift = sum(d.drift_corrected for d in self._drifts)
        net_wisdom = total_wisdom - total_drift

        convergence_ratio = 0.0
        if len(self._cycle_results) >= 2:
            last = self._cycle_results[-1]
            prev = self._cycle_results[-2]
            prev_wisdom = prev.residue.residue_value if prev.residue else 0.0
            last_wisdom = last.residue.residue_value if last.residue else 0.0
            if abs(prev_wisdom) > 1e-10:
                convergence_ratio = abs(last_wisdom - prev_wisdom) / abs(prev_wisdom)

        if convergence_ratio < self.convergence_epsilon:
            status = SpiralStatus.CONVERGING
        elif convergence_ratio > 0.5:
            status = SpiralStatus.DIVERGING
        elif convergence_ratio < 0.1:
            status = SpiralStatus.STABLE
        else:
            status = SpiralStatus.CONVERGING

        return SpiralWisdomResult(
            total_wisdom=total_wisdom,
            total_drift_correction=total_drift,
            net_wisdom=net_wisdom,
            status=status,
            convergence_ratio=convergence_ratio,
            cycles_completed=len(self._cycle_results),
            residues=list(self._residues),
            drifts=list(self._drifts),
            cycle_results=list(self._cycle_results),
        )

    def get_wisdom_trajectory(self) -> list[tuple[int, float]]:
        """Get the wisdom trajectory over all cycles.

        Returns:
            List of (cycle, cumulative_wisdom) tuples.
        """
        trajectory = []
        cumulative = 0.0
        for r in self._residues:
            cumulative += r.residue_value
            trajectory.append((r.cycle, cumulative))
        return trajectory

    def get_balance_evolution(self) -> list[tuple[int, float, float]]:
        """Get the dark/light balance evolution over all cycles.

        Returns:
            List of (cycle, dark_level, light_level) tuples.
        """
        return [
            (r.cycle, r.dark_before, r.light_before)
            for r in self._cycle_results
        ]

    def reset(self) -> None:
        """Reset the spiral to initial state."""
        self._residues.clear()
        self._drifts.clear()
        self._cycle_results.clear()
        self._current_dark = 0.5
        self._current_light = 0.5
