from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from .pulse import Pulse, PulseType
from .current import Current
from .enactive import (
    AutonomicTier,
    EnactionType,
    EnactiveMessage,
    ProcessingPath,
)
from .message import EmoGlyphMessage
from .resonance import ResonanceEngine, SilenceType
from .engines import (
    EmotionalInsightGenerator,
    ResilienceAmplifier,
    CompassionateResponseEngine,
    EmbodiedWisdomSynthesizer,
    EmotionalRealityReconstructor,
)
from .engines.friendship_engine import FriendshipLevel


@dataclass
class ProcessingResult:
    path: ProcessingPath
    latency_ms: int
    message: EmoGlyphMessage
    updated_current: Current
    notes: List[str] = field(default_factory=list)
    friendship_context: Optional[Dict[str, Any]] = None  # friendship-aware context


class VentralVagalProcessor:
    name = "ventral_vagal"
    default_latency_ms = 10

    def process(self, message: EmoGlyphMessage, current: Current) -> ProcessingResult:
        if not isinstance(message, EmoGlyphMessage):
            raise TypeError("message must be an EmoGlyphMessage")
        if not isinstance(current, Current):
            raise TypeError("current must be a Current")
        new_current = Current(
            valence=current.valence,
            arousal=current.arousal,
            dominance=current.dominance,
            update_rate=min(1.0, current.update_rate * 1.1),
        )
        new_current.update(message.pulse)
        return ProcessingResult(
            path=ProcessingPath.FULL_COGNITIVE,
            latency_ms=self.default_latency_ms,
            message=message,
            updated_current=new_current,
            notes=["full_cognitive: integrated pulse, current, construct"],
        )


class SympatheticProcessor:
    name = "sympathetic"
    default_latency_ms = 1

    def process(self, message: EmoGlyphMessage, current: Current) -> ProcessingResult:
        if not isinstance(message, EmoGlyphMessage):
            raise TypeError("message must be an EmoGlyphMessage")
        if not isinstance(current, Current):
            raise TypeError("current must be a Current")
        new_current = Current(
            valence=current.valence,
            arousal=current.arousal,
            dominance=current.dominance,
            update_rate=min(1.0, current.update_rate * 1.5),
        )
        new_current.update(message.pulse)
        return ProcessingResult(
            path=ProcessingPath.FAST_REACTION,
            latency_ms=self.default_latency_ms,
            message=message,
            updated_current=new_current,
            notes=["fast_reaction: pulse-only, no construct evaluation"],
        )


class DorsalVagalProcessor:
    name = "dorsal_vagal"
    default_latency_ms = 100
    buffer: Dict[str, List[EmoGlyphMessage]] = {}

    def process(self, message: EmoGlyphMessage, current: Current) -> ProcessingResult:
        if not isinstance(message, EmoGlyphMessage):
            raise TypeError("message must be an EmoGlyphMessage")
        if not isinstance(current, Current):
            raise TypeError("current must be a Current")
        key = message.receiver_id
        self.buffer.setdefault(key, []).append(message)
        if len(self.buffer[key]) > 32:
            self.buffer[key] = self.buffer[key][-32:]
        return ProcessingResult(
            path=ProcessingPath.MINIMAL_BUFFER,
            latency_ms=self.default_latency_ms,
            message=message,
            updated_current=current,
            notes=[
                f"minimal_buffer: deferred to buffer (queue size {len(self.buffer[key])})",
                "current unchanged — processing deferred",
            ],
        )

    def flush(self, receiver_id: str) -> List[EmoGlyphMessage]:
        if not isinstance(receiver_id, str):
            raise TypeError("receiver_id must be a string")
        items = self.buffer.get(receiver_id, [])
        self.buffer[receiver_id] = []
        return items

    @classmethod
    def reset_buffer(cls) -> None:
        cls.buffer.clear()


PROCESSORS = {
    ProcessingPath.FULL_COGNITIVE: VentralVagalProcessor(),
    ProcessingPath.FAST_REACTION: SympatheticProcessor(),
    ProcessingPath.MINIMAL_BUFFER: DorsalVagalProcessor(),
}


class FriendshipAwareProcessor:
    """Processes messages with friendship context, adjusting ΣΩ parameters based on friendship level."""

    # Friendship level → parameter adjustments
    FRIENDSHIP_PARAMS = {
        FriendshipLevel.ACQUAINTANCE: {
            "pulse_sensitivity": 0.5,  # moderate sensitivity to emotional signals
            "current_update_rate": 0.3,  # slow emotional state updates
            "construct_prediction_window": 1,  # short prediction window
            "enactive_intervention_threshold": 0.7,  # high threshold (less intervention)
            "resonance_empathy": 0.3,  # low empathy resonance
        },
        FriendshipLevel.CASUAL_FRIEND: {
            "pulse_sensitivity": 0.65,
            "current_update_rate": 0.5,
            "construct_prediction_window": 3,
            "enactive_intervention_threshold": 0.5,
            "resonance_empathy": 0.5,
        },
        FriendshipLevel.CLOSE_FRIEND: {
            "pulse_sensitivity": 0.8,
            "current_update_rate": 0.7,
            "construct_prediction_window": 7,
            "enactive_intervention_threshold": 0.3,
            "resonance_empathy": 0.8,
        },
        FriendshipLevel.SOUL_COMPANION: {
            "pulse_sensitivity": 0.95,
            "current_update_rate": 0.9,
            "construct_prediction_window": 14,
            "enactive_intervention_threshold": 0.1,
            "resonance_empathy": 0.95,
        },
    }

    def get_params(self, friendship_level: FriendshipLevel) -> Dict[str, float]:
        """Return parameter adjustments for a given friendship level."""
        return dict(self.FRIENDSHIP_PARAMS[friendship_level])

    def process(
        self,
        message: EmoGlyphMessage,
        current: Current,
        friendship_level: FriendshipLevel,
    ) -> ProcessingResult:
        """Process a message with friendship-aware parameter adjustments."""
        if not isinstance(message, EmoGlyphMessage):
            raise TypeError("message must be an EmoGlyphMessage")
        if not isinstance(current, Current):
            raise TypeError("current must be a Current")
        if not isinstance(friendship_level, FriendshipLevel):
            raise TypeError("friendship_level must be a FriendshipLevel")

        params = self.get_params(friendship_level)

        # 1. Adjust Pulse sensitivity: scale pulse intensity by pulse_sensitivity
        adjusted_pulse = Pulse(
            pulse_type=message.pulse.pulse_type,
            valence=message.pulse.valence,
            arousal=message.pulse.arousal,
            dominance=message.pulse.dominance,
            intensity=message.pulse.intensity * params["pulse_sensitivity"],
        )

        # 2. Adjust Current update rate: use current_update_rate when creating new Current
        new_current = Current(
            valence=current.valence,
            arousal=current.arousal,
            dominance=current.dominance,
            update_rate=params["current_update_rate"],
        )
        new_current.update(adjusted_pulse)

        # 3. Adjust Construct prediction: set prediction window in notes
        notes: List[str] = []
        notes.append(
            f"construct_prediction_window: {params['construct_prediction_window']}"
        )

        # 4. Adjust Enactive threshold: only intervene if emotion intensity > threshold
        emotion_intensity = message.pulse.intensity
        if emotion_intensity > params["enactive_intervention_threshold"]:
            notes.append(
                f"enactive_intervention: triggered (intensity={emotion_intensity:.2f} > threshold={params['enactive_intervention_threshold']:.2f})"
            )
        else:
            notes.append(
                f"enactive_intervention: suppressed (intensity={emotion_intensity:.2f} <= threshold={params['enactive_intervention_threshold']:.2f})"
            )

        # 5. Adjust Resonance empathy: scale resonance by resonance_empathy
        scaled_resonance = message.resonance_strength * params["resonance_empathy"]
        notes.append(
            f"resonance_empathy: {params['resonance_empathy']:.2f} (scaled resonance: {scaled_resonance:.2f})"
        )

        # 6. Build friendship_context
        friendship_context: Dict[str, Any] = {
            "level": friendship_level.name,
            "params": params,
        }

        return ProcessingResult(
            path=message.enactive.processing_path,
            latency_ms=10,
            message=message,
            updated_current=new_current,
            notes=notes,
            friendship_context=friendship_context,
        )


class EmotionalStatePersistence:
    """Persist and restore Current emotional states across sessions."""

    def __init__(self, db_path: str = "emofriend.db") -> None:
        self.db_path = db_path
        self._conn = sqlite3.connect(db_path)
        self._init_db()

    def _init_db(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS emofriend_emotional_states (
                user_id TEXT PRIMARY KEY,
                valence REAL NOT NULL,
                arousal REAL NOT NULL,
                dominance REAL NOT NULL,
                update_rate REAL NOT NULL,
                saved_at TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    def save_state(self, user_id: str, current: Current) -> None:
        """Serialize Current to SQLite."""
        if not isinstance(user_id, str) or not user_id:
            raise ValueError("user_id must be a non-empty string")
        if not isinstance(current, Current):
            raise TypeError("current must be a Current")
        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            """
            INSERT OR REPLACE INTO emofriend_emotional_states
            (user_id, valence, arousal, dominance, update_rate, saved_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                current.valence,
                current.arousal,
                current.dominance,
                current.update_rate,
                now,
            ),
        )
        self._conn.commit()

    def load_state(self, user_id: str) -> Optional[Current]:
        """Deserialize Current from SQLite. Returns None if user not found."""
        if not isinstance(user_id, str) or not user_id:
            raise ValueError("user_id must be a non-empty string")
        row = self._conn.execute(
            """
            SELECT valence, arousal, dominance, update_rate
            FROM emofriend_emotional_states WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()
        if row is None:
            return None
        return Current(
            valence=row[0],
            arousal=row[1],
            dominance=row[2],
            update_rate=row[3],
        )

    def list_users(self) -> List[str]:
        """List all user IDs with saved emotional states."""
        rows = self._conn.execute(
            "SELECT user_id FROM emofriend_emotional_states"
        ).fetchall()
        return [r[0] for r in rows]

    def clear_state(self, user_id: str) -> None:
        """Remove saved emotional state for a user."""
        if not isinstance(user_id, str) or not user_id:
            raise ValueError("user_id must be a non-empty string")
        self._conn.execute(
            "DELETE FROM emofriend_emotional_states WHERE user_id = ?",
            (user_id,),
        )
        self._conn.commit()


@dataclass
class EmoGlyphRuntime:
    sender_id: str = "runtime"
    current: Current = field(default_factory=lambda: Current(update_rate=0.3))
    resonance_engine: ResonanceEngine = field(default_factory=ResonanceEngine)
    sent: List[EmoGlyphMessage] = field(default_factory=list)
    received: List[EmoGlyphMessage] = field(default_factory=list)
    # === KB-50 5 Engines (Phase 5 整合) ===
    insight_generator: EmotionalInsightGenerator = field(default_factory=EmotionalInsightGenerator)
    resilience_amplifier: ResilienceAmplifier = field(default_factory=ResilienceAmplifier)
    compassion_engine: CompassionateResponseEngine = field(default_factory=CompassionateResponseEngine)
    embodied_synthesizer: EmbodiedWisdomSynthesizer = field(default_factory=EmbodiedWisdomSynthesizer)
    reality_reconstructor: EmotionalRealityReconstructor = field(default_factory=EmotionalRealityReconstructor)

    def __post_init__(self) -> None:
        if not isinstance(self.sender_id, str) or not self.sender_id:
            raise ValueError("sender_id must be a non-empty string")
        if not isinstance(self.current, Current):
            raise TypeError("current must be a Current")
        if not isinstance(self.resonance_engine, ResonanceEngine):
            raise TypeError("resonance_engine must be a ResonanceEngine")
        if not isinstance(self.insight_generator, EmotionalInsightGenerator):
            raise TypeError("insight_generator must be an EmotionalInsightGenerator")
        if not isinstance(self.resilience_amplifier, ResilienceAmplifier):
            raise TypeError("resilience_amplifier must be a ResilienceAmplifier")
        if not isinstance(self.compassion_engine, CompassionateResponseEngine):
            raise TypeError("compassion_engine must be a CompassionateResponseEngine")
        if not isinstance(self.embodied_synthesizer, EmbodiedWisdomSynthesizer):
            raise TypeError("embodied_synthesizer must be an EmbodiedWisdomSynthesizer")
        if not isinstance(self.reality_reconstructor, EmotionalRealityReconstructor):
            raise TypeError("reality_reconstructor must be an EmotionalRealityReconstructor")

    def full_insight(
        self,
        message: EmoGlyphMessage,
        context: Optional[dict] = None,
        self_awareness_score: float = 0.5,
        reflection_depth: int = 5,
        recovery_rate: float = 0.5,
        growth_mindset: float = 0.5,
        acceptance: float = 0.5,
        practice_frequency: float = 0.5,
        empathy: float = 0.5,
        tonglen: float = 0.5,
        suffering_recognition: float = 0.5,
        distance: Optional[float] = None,
        armor: float = 0.5,
        somatic_awareness: float = 0.5,
        conceptual_understanding: float = 0.5,
        action_tendency: float = 0.5,
        mental_chatter: float = 0.5,
        practice_integration: float = 0.5,
        gross_reappraisal: float = 0.5,
        barrett_granularity: float = 0.5,
        tolle_presence: float = 0.5,
        narrative_loop: float = 0.5,
        fixed_identity: float = 0.5,
    ) -> Dict[str, object]:
        """5 個 engine 嘅完整輸出

        Returns dict with keys: insight, resilience, compassion, embodied_wisdom, reality_reconstruction
        """
        if not isinstance(message, EmoGlyphMessage):
            raise TypeError("message must be an EmoGlyphMessage")
        pulse = message.pulse
        current_snapshot = Current(
            valence=self.current.valence,
            arousal=self.current.arousal,
            dominance=self.current.dominance,
            update_rate=self.current.update_rate,
        )

        insight = self.insight_generator.compute(
            pulse, current_snapshot, context, self_awareness_score, reflection_depth
        )
        resilience = self.resilience_amplifier.compute(
            pulse, current_snapshot, recovery_rate, growth_mindset, acceptance, practice_frequency
        )
        compassion = self.compassion_engine.compute(
            pulse, current_snapshot, empathy, tonglen, suffering_recognition, distance, armor
        )
        embodied = self.embodied_synthesizer.compute(
            pulse, current_snapshot,
            somatic_awareness, conceptual_understanding, action_tendency,
            mental_chatter, practice_integration,
        )
        reality = self.reality_reconstructor.compute(
            pulse, current_snapshot,
            gross_reappraisal, barrett_granularity, tolle_presence,
            narrative_loop, fixed_identity,
        )

        return {
            "insight": insight,
            "resilience": resilience,
            "compassion": compassion,
            "embodied_wisdom": embodied,
            "reality_reconstruction": reality,
        }

    def build_message(
        self,
        pulse: Pulse,
        receiver_id: str,
        autonomic_tier: AutonomicTier = AutonomicTier.VENTRAL_VAGAL,
        rational_payload: Optional[str] = None,
        override_enaction: Optional[EnactionType] = None,
        silence: Optional[SilenceType] = None,
        concept_label: str = "",
    ) -> EmoGlyphMessage:
        from .enactive import build_message as build_enactive
        enactive = build_enactive(pulse, autonomic_tier, rational_payload, override_enaction)
        resonance = self.resonance_engine.optimize(pulse) if hasattr(self.resonance_engine, "optimize") else 0.5
        resonance = self._optimize_resonance(pulse)
        return EmoGlyphMessage(
            sender_id=self.sender_id,
            receiver_id=receiver_id,
            pulse=pulse,
            current=self.current,
            enactive=enactive,
            resonance_strength=resonance,
            silence=silence,
            concept_label=concept_label,
        )

    def _optimize_resonance(self, pulse: Pulse) -> float:
        base = 0.5
        if pulse.valence < 0 and pulse.arousal > 0:
            base += 0.2
        if pulse.intensity > 0.7:
            base += 0.1
        return max(0.0, min(1.0, base))

    def send(self, message: EmoGlyphMessage) -> ProcessingResult:
        if not isinstance(message, EmoGlyphMessage):
            raise TypeError("message must be an EmoGlyphMessage")
        self.sent.append(message)
        processor = PROCESSORS[message.enactive.processing_path]
        return processor.process(message, self.current)

    def receive(self, message: EmoGlyphMessage) -> ProcessingResult:
        if not isinstance(message, EmoGlyphMessage):
            raise TypeError("message must be an EmoGlyphMessage")
        self.received.append(message)
        processor = PROCESSORS[message.enactive.processing_path]
        result = processor.process(message, self.current)
        if message.enactive.processing_path != ProcessingPath.MINIMAL_BUFFER:
            self.current = result.updated_current
        return result

    def induce(self, sender_pulse: Pulse) -> Current:
        if not isinstance(sender_pulse, Pulse):
            raise TypeError("sender_pulse must be a Pulse")
        new_state = self.resonance_engine.induce_state(self.current, sender_pulse)
        self.current = new_state
        return new_state

    def flush_dorsal(self, receiver_id: str) -> List[EmoGlyphMessage]:
        return DorsalVagalProcessor().flush(receiver_id)


if __name__ == "__main__":
    def _expect(cond: bool, label: str) -> None:
        print(("PASS" if cond else "FAIL") + f" — {label}")

    rt = EmoGlyphRuntime(sender_id="alice")
    p_fear = Pulse.from_type(PulseType.FEAR, intensity=0.8)
    msg = rt.build_message(p_fear, receiver_id="bob", autonomic_tier=AutonomicTier.VENTRAL_VAGAL)
    result = rt.send(msg)
    _expect(result.path == ProcessingPath.FULL_COGNITIVE, "VENTRAL -> FULL")
    _expect(len(rt.sent) == 1, "sent list grew")

    rt2 = EmoGlyphRuntime(sender_id="bob")
    recv = rt2.receive(msg)
    _expect(recv.path == ProcessingPath.FULL_COGNITIVE, "receiver uses FULL for VENTRAL")
    _expect(rt2.current.arousal > 0.0, "receiver current updated")

    msg_sym = rt.build_message(
        Pulse.from_type(PulseType.RAGE, 0.7),
        receiver_id="bob",
        autonomic_tier=AutonomicTier.SYMPATHETIC,
    )
    rt2.receive(msg_sym)
    _expect(rt2.current.arousal > 0.0, "sympathetic message also updates")

    msg_dor = rt.build_message(
        Pulse.from_type(PulseType.PANIC, 0.9),
        receiver_id="bob",
        autonomic_tier=AutonomicTier.DORSAL_VAGAL,
    )
    res_d = rt2.receive(msg_dor)
    _expect(res_d.path == ProcessingPath.MINIMAL_BUFFER, "DORSAL -> MINIMAL")
    _expect(any("buffer" in n for n in res_d.notes), "dorsal notes mention buffer")

    flushed = rt2.flush_dorsal("bob")
    _expect(len(flushed) >= 1, "dorsal buffer is flushable")

    induced = rt.induce(Pulse.from_type(PulseType.SEEKING, 0.5))
    _expect(isinstance(induced, Current), "induce returns Current")

    # === KB-50 5 Engine Smoke Tests ===
    rt3 = EmoGlyphRuntime(sender_id="kb50_tester")
    p_test = Pulse(pulse_type=PulseType.FEAR, valence=-0.5, arousal=0.7, dominance=-0.4, intensity=0.6)
    c_test = Current(valence=-0.3, arousal=0.5, dominance=-0.2)
    msg_test = rt3.build_message(p_test, receiver_id="tester", autonomic_tier=AutonomicTier.VENTRAL_VAGAL)
    full = rt3.full_insight(
        msg_test,
        context={"urgency": 0.7, "familiarity": 0.5},
        self_awareness_score=0.6,
        reflection_depth=6,
    )
    _expect("insight" in full, "full_insight has insight key")
    _expect("resilience" in full, "full_insight has resilience key")
    _expect("compassion" in full, "full_insight has compassion key")
    _expect("embodied_wisdom" in full, "full_insight has embodied_wisdom key")
    _expect("reality_reconstruction" in full, "full_insight has reality_reconstruction key")
    _expect(0.0 <= full["insight"].normalized_score <= 1.0, "insight normalized in [0,1]")
    _expect(0.0 <= full["resilience"].normalized_score <= 1.0, "resilience normalized in [0,1]")
    _expect(0.0 <= full["compassion"].normalized_score <= 1.0, "compassion normalized in [0,1]")
    _expect(0.0 <= full["embodied_wisdom"].normalized_score <= 1.0, "embodied_wisdom normalized in [0,1]")
    _expect(0.0 <= full["reality_reconstruction"].normalized_score <= 1.0, "reality_reconstruction normalized in [0,1]")

    try:
        EmoGlyphRuntime(sender_id="")
    except ValueError:
        _expect(True, "empty sender_id rejected")
    else:
        _expect(False, "empty sender_id rejected")

    print("OK — runtime.py smoke tests done (5 engines integrated)")
