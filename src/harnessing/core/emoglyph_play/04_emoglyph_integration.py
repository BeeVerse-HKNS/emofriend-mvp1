"""
EmoGlyph Integration Layer — 5-Layer × 4-Step Bridge

Maps EmoGlyph v2.1's 5-layer architecture to LSP 4-step process:
  Pulse (L1)    → Question  (detect emotional signal → formulate question)
  Current (L2)  → Build     (flow state → construct hypothesis)
  Construct (L3)→ Share     (structured build → share narrative)
  Enactive (L4) → Reflect   (action reflection → extract learning)
  Resonance (L5)→ Loop      (resonance check → restart if low)
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from .lsp_ai_engine import (
    LSPEngine,
    LSPStage,
    PlaySession,
    PlayerType,
)

# ---------------------------------------------------------------------------
# Lazy imports — graceful degradation when EmoGlyph modules are unavailable
# ---------------------------------------------------------------------------
_Pulse: Any = None
_PulseType: Any = None
_Current: Any = None
_ConstructEngine: Any = None
_FiveElement: Any = None
_EnactiveMessage: Any = None
_EnactionType: Any = None
_AutonomicTier: Any = None
_ResonanceRequest: Any = None

_emoglyph_available = False


def _try_import_emoglyph() -> bool:
    """Try to import EmoGlyph modules by adding the source path to sys.path."""
    _emoglyph_src = Path(r"d:\My_Code_Projects\Harnessing\projects\ai-opc-trainer\src")
    if _emoglyph_src.exists() and str(_emoglyph_src) not in sys.path:
        sys.path.insert(0, str(_emoglyph_src))
    try:
        global _Pulse, _PulseType, _Current, _ConstructEngine, _FiveElement
        global _EnactiveMessage, _EnactionType, _AutonomicTier, _ResonanceRequest, _emoglyph_available
        from emoglyph.pulse import Pulse as _Pulse, PulseType as _PulseType  # type: ignore[no-redef]
        from emoglyph.current import Current as _Current  # type: ignore[no-redef]
        from emoglyph.construct import ConstructEngine as _ConstructEngine, FiveElement as _FiveElement  # type: ignore[no-redef]
        from emoglyph.enactive import EnactiveMessage as _EnactiveMessage, EnactionType as _EnactionType, AutonomicTier as _AutonomicTier  # type: ignore[no-redef]
        from emoglyph.resonance import ResonanceRequest as _ResonanceRequest  # type: ignore[no-redef]
        _emoglyph_available = True
        return True
    except ImportError:
        _emoglyph_available = False
        return False


_try_import_emoglyph()


# ---------------------------------------------------------------------------
# Resonance threshold — below this score a new cycle is triggered
# ---------------------------------------------------------------------------
RESONANCE_THRESHOLD = 0.4
MAX_AUTO_CYCLES = 5


# ---------------------------------------------------------------------------
# EmoGlyphPlaySession
# ---------------------------------------------------------------------------
@dataclass
class EmoGlyphPlaySession(PlaySession):
    """PlaySession enriched with EmoGlyph emotional context."""

    emotional_context: dict = field(default_factory=dict)
    resonance_history: list[float] = field(default_factory=list)
    cycle_count: int = 0


# ---------------------------------------------------------------------------
# EmoGlyphLSPBridge
# ---------------------------------------------------------------------------
class EmoGlyphLSPBridge:
    """Bridge between EmoGlyph v2.1 5-layer architecture and LSP 4-step process.

    Each EmoGlyph layer maps to an LSP step:
        L1 Pulse    → Question
        L2 Current  → Build
        L3 Construct→ Share
        L4 Enactive → Reflect
        L5 Resonance→ Loop (auto-restart decision)
    """

    def __init__(self) -> None:
        self.engine = LSPEngine()
        self._emoglyph_available = _emoglyph_available

    # -- L1 Pulse → Question -------------------------------------------------

    def pulse_to_question(self, emotional_signal: dict) -> str:
        """Map Pulse (L1) data to an LSP question.

        Parameters
        ----------
        emotional_signal : dict
            Must contain ``pulse_type`` (str) and optionally ``intensity`` (float).
            If EmoGlyph is available, a Pulse object is constructed for richer
            analysis; otherwise a plain-text question is generated.
        """
        pulse_type_name = emotional_signal.get("pulse_type", "SEEKING")
        intensity = emotional_signal.get("intensity", 1.0)

        if self._emoglyph_available and _PulseType is not None:
            try:
                pt = _PulseType(pulse_type_name)
                pulse = _Pulse.from_type(pt, intensity)
                return (
                    f"What drives this {pt.value} impulse "
                    f"(V={pulse.valence:.2f}, A={pulse.arousal:.2f}, "
                    f"D={pulse.dominance:.2f}) and how should we respond?"
                )
            except (ValueError, TypeError):
                pass

        return f"What is the root cause behind this {pulse_type_name} emotional signal (intensity={intensity:.2f})?"

    # -- L2 Current → Build --------------------------------------------------

    def current_to_build(self, flow_state: dict) -> str:
        """Map Current (L2) data to a build hypothesis.

        Parameters
        ----------
        flow_state : dict
            Must contain ``valence`` (float) and ``arousal`` (float).
        """
        valence = flow_state.get("valence", 0.0)
        arousal = flow_state.get("arousal", 0.0)

        if self._emoglyph_available and _Current is not None:
            current = _Current(valence=valence, arousal=arousal)
            flow_label = "positive flow" if current.valence > 0 else "negative flow"
            engagement = "high" if current.arousal > 0.5 else "moderate" if current.arousal > 0.2 else "low"
        else:
            flow_label = "positive flow" if valence > 0 else "negative flow"
            engagement = "high" if arousal > 0.5 else "moderate" if arousal > 0.2 else "low"

        return (
            f"Given {flow_label} (V={valence:.2f}) with {engagement} engagement "
            f"(A={arousal:.2f}), construct a hypothesis that leverages this state."
        )

    # -- L3 Construct → Share ------------------------------------------------

    def construct_to_share(self, construct_data: dict) -> str:
        """Map Construct (L3) data to a share narrative.

        Parameters
        ----------
        construct_data : dict
            Must contain ``element`` (str, one of WOOD/FIRE/EARTH/METAL/WATER)
            and optionally ``surprise`` (float).
        """
        element_name = construct_data.get("element", "WOOD")
        surprise = construct_data.get("surprise", 0.0)

        if self._emoglyph_available and _FiveElement is not None and _ConstructEngine is not None:
            try:
                element = _FiveElement(element_name)
                engine = _ConstructEngine()
                next_gen = engine.transition_generating(element)
                next_ctrl = engine.transition_controlling(element)
                return (
                    f"The {element.value} element generates {next_gen.value} and "
                    f"controls {next_ctrl.value}. With surprise={surprise:.2f}, "
                    f"the narrative bridges expectation and discovery."
                )
            except (ValueError, TypeError):
                pass

        return (
            f"Element {element_name} with surprise={surprise:.2f} — "
            f"sharing the constructed insight as a narrative."
        )

    # -- L4 Enactive → Reflect -----------------------------------------------

    def enactive_to_reflect(self, action_data: dict) -> str:
        """Map Enactive (L4) data to a reflection.

        Parameters
        ----------
        action_data : dict
            Must contain ``enaction_type`` (str) and ``autonomic_tier`` (str).
            Optionally ``rational_payload`` (dict).
        """
        enaction_name = action_data.get("enaction_type", "REACH")
        tier_name = action_data.get("autonomic_tier", "VENTRAL_VAGAL")
        payload = action_data.get("rational_payload")

        if self._emoglyph_available and _EnactiveMessage is not None:
            try:
                et = _EnactionType(enaction_name)
                at = _AutonomicTier(tier_name)
                msg = _EnactiveMessage(enaction_type=et, autonomic_tier=at, rational_payload=payload)
                return (
                    f"Reflected on {et.value} action via {at.value} tier "
                    f"(latency={msg.latency_ms}ms): what did this enactment reveal?"
                )
            except (ValueError, TypeError):
                pass

        return f"Reflected on {enaction_name} action via {tier_name} tier: what did this enactment reveal?"

    # -- L5 Resonance → Loop -------------------------------------------------

    def check_resonance(self, session: PlaySession) -> tuple[bool, float]:
        """Check whether resonance is high enough to stop cycling.

        Returns
        -------
        (should_continue, resonance_score) : tuple[bool, float]
            *should_continue* is True when resonance is *below* the threshold,
            meaning another LSP cycle would be beneficial.
        """
        if self._emoglyph_available and _ResonanceRequest is not None and session.steps:
            # Derive sender V/A from the session's emotional context if present
            ctx: dict = getattr(session, "emotional_context", {})
            sender_v = ctx.get("valence", 0.0)
            sender_a = ctx.get("arousal", 0.0)
            req = _ResonanceRequest(sender_valence=sender_v, sender_arousal=sender_a)
            # Receiver is the aggregate of step confidences mapped to V/A space
            receiver_v = sum(s.confidence for s in session.steps) / max(len(session.steps), 1)
            receiver_a = session.surprise_score
            score = req.compute_resonance(receiver_v, receiver_a)
        else:
            # Fallback: use session's own resonance computation
            score = session.resonance if session.resonance > 0 else 0.0
            if score == 0.0 and session.steps:
                score = sum(s.confidence for s in session.steps) / max(len(session.steps), 1)

        should_continue = score < RESONANCE_THRESHOLD
        return should_continue, score

    # -- Full integrated cycle ------------------------------------------------

    def run_integrated_cycle(
        self,
        question: str,
        emotional_context: dict | None = None,
    ) -> EmoGlyphPlaySession:
        """Run a full integrated LSP cycle enriched with EmoGlyph context.

        The cycle proceeds through the 4 LSP steps, each informed by the
        corresponding EmoGlyph layer.  After the REFLECT step, resonance is
        checked; if it is below the threshold, additional cycles are
        automatically started with refined questions (up to *MAX_AUTO_CYCLES*).
        """
        if emotional_context is None:
            emotional_context = {}

        # --- Step 1: Question (Pulse L1) ---
        pulse_signal = emotional_context.get("pulse", {"pulse_type": "SEEKING", "intensity": 1.0})
        enriched_question = self.pulse_to_question(pulse_signal)
        if question:
            enriched_question = f"{question} — {enriched_question}"

        session_id = f"emoglyph-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
        base_session = self.engine.start_session(enriched_question, session_id=session_id)

        # Wrap into EmoGlyphPlaySession preserving base fields
        session = EmoGlyphPlaySession(
            session_id=base_session.session_id,
            player_type=base_session.player_type,
            question=enriched_question,
            steps=base_session.steps,
            emotional_context=dict(emotional_context),
        )
        # Re-register under the same id so engine lookups work
        self.engine.sessions[session.session_id] = session

        # --- Step 2: Build (Current L2) ---
        flow_state = emotional_context.get("current", {
            "valence": pulse_signal.get("intensity", 1.0) * 0.5,
            "arousal": pulse_signal.get("intensity", 1.0) * 0.6,
        })
        hypothesis = self.current_to_build(flow_state)
        self.engine.build(session.session_id, hypothesis, confidence=0.7)

        # --- Step 3: Share (Construct L3) ---
        construct_data = emotional_context.get("construct", {
            "element": "WOOD",
            "surprise": 0.0,
        })
        narrative = self.construct_to_share(construct_data)
        self.engine.share(session.session_id, narrative, confidence=0.7)

        # --- Step 4: Reflect (Enactive L4) ---
        action_data = emotional_context.get("enactive", {
            "enaction_type": "REACH",
            "autonomic_tier": "VENTRAL_VAGAL",
        })
        learning = self.enactive_to_reflect(action_data)
        surprise_score = construct_data.get("surprise", 0.3) if isinstance(construct_data, dict) else 0.3
        self.engine.reflect(session.session_id, learning, surprise_score=surprise_score)

        session.cycle_count = 1
        session.complete()

        # --- Resonance check & auto-restart (L5) ---
        should_continue, resonance_score = self.check_resonance(session)
        session.resonance_history.append(resonance_score)

        auto_cycles = 0
        while should_continue and auto_cycles < MAX_AUTO_CYCLES:
            auto_cycles += 1
            refined_question = self._refine_question(session, resonance_score)
            session = self._run_additional_cycle(session, refined_question, emotional_context)
            should_continue, resonance_score = self.check_resonance(session)
            session.resonance_history.append(resonance_score)

        return session

    # -- Helpers --------------------------------------------------------------

    @staticmethod
    def _refine_question(previous_session: EmoGlyphPlaySession, resonance_score: float) -> str:
        """Generate a refined question based on the previous cycle's gaps."""
        base = previous_session.question
        if previous_session.steps:
            last_reflect = None
            for step in reversed(previous_session.steps):
                if step.stage == LSPStage.REFLECT:
                    last_reflect = step
                    break
            if last_reflect:
                return (
                    f"[Refined, resonance={resonance_score:.2f}] "
                    f"Building on: {last_reflect.content[:80]}… — "
                    f"what deeper insight emerges?"
                )
        return f"[Refined, resonance={resonance_score:.2f}] {base}"

    def _run_additional_cycle(
        self,
        previous_session: EmoGlyphPlaySession,
        refined_question: str,
        emotional_context: dict,
    ) -> EmoGlyphPlaySession:
        """Run one additional LSP cycle, appending steps to the existing session."""
        # Re-open the session for a new cycle
        previous_session.status = "active"

        # Question step
        previous_session.add_step(
            LSPStage.QUESTION,
            refined_question,
            confidence=0.6,
            notes="Auto-restart cycle",
        )

        # Build step
        flow_state = emotional_context.get("current", {"valence": 0.5, "arousal": 0.6})
        hypothesis = self.current_to_build(flow_state)
        previous_session.add_step(LSPStage.BUILD, hypothesis, confidence=0.7, notes="Hypothesis built")

        # Share step
        construct_data = emotional_context.get("construct", {"element": "WOOD", "surprise": 0.0})
        narrative = self.construct_to_share(construct_data)
        previous_session.add_step(LSPStage.SHARE, narrative, confidence=0.7, notes="Story shared")

        # Reflect step
        action_data = emotional_context.get("enactive", {"enaction_type": "REACH", "autonomic_tier": "VENTRAL_VAGAL"})
        learning = self.enactive_to_reflect(action_data)
        surprise_score = construct_data.get("surprise", 0.3) if isinstance(construct_data, dict) else 0.3
        previous_session.surprise_score = surprise_score
        previous_session.add_step(
            LSPStage.REFLECT, learning, confidence=1.0 - surprise_score,
            notes=f"Surprise: {surprise_score:.2f}",
        )

        previous_session.cycle_count += 1
        previous_session.complete()

        # Keep engine in sync
        self.engine.sessions[previous_session.session_id] = previous_session

        return previous_session
