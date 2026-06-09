from __future__ import annotations

import math
import re
import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class SpiralPhase(str, Enum):
    PROCESS = "process"
    REFLECT = "reflect"
    DEEPEN = "deepen"
    CRYSTALLIZE = "crystallize"


class LoopLevel(str, Enum):
    ACTION = "action"
    REFLECTION = "reflection"
    META_LEARNING = "meta_learning"


class MonitoringStatus(str, Enum):
    ON_TRACK = "on_track"
    ADJUST = "adjust"
    ESCALATE = "escalate"


class ConvergenceReason(str, Enum):
    MAX_DEPTH = "max_depth"
    LOW_GAIN = "low_gain"
    CONSECUTIVE_LOW = "consecutive_low"
    NOT_CONVERGED = "not_converged"


@dataclass
class KnowledgeCrystal:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    concept: str = ""
    level: int = 0
    crystallized_at: str = field(default_factory=lambda: datetime.now().isoformat())
    essence: str = ""
    connections: list[str] = field(default_factory=list)
    confidence: float = 0.0
    source_length: int = 0
    compression_ratio: float = 0.0


@dataclass
class Attractor:
    source_crystal_id: str = ""
    resonance_score: float = 0.0
    suggested_depth: int = 0
    trigger_reason: str = ""
    matched_terms: list[str] = field(default_factory=list)


@dataclass
class MonitoringResult:
    loop_level: LoopLevel = LoopLevel.ACTION
    status: MonitoringStatus = MonitoringStatus.ON_TRACK
    insight: str = ""
    recommended_action: str = ""
    learning_velocity: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class SpiralResult:
    level: int = 0
    phase: SpiralPhase = SpiralPhase.PROCESS
    insights: list[str] = field(default_factory=list)
    crystals_formed: list[KnowledgeCrystal] = field(default_factory=list)
    attractors_detected: list[Attractor] = field(default_factory=list)
    gain: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class HelicalLearningResult:
    final_crystals: list[KnowledgeCrystal] = field(default_factory=list)
    spiral_trace: list[SpiralResult] = field(default_factory=list)
    convergence_level: int = 0
    convergence_reason: ConvergenceReason = ConvergenceReason.NOT_CONVERGED
    meta_insights: list[MonitoringResult] = field(default_factory=list)
    total_spirals: int = 0
    total_insights: int = 0
    avg_gain: float = 0.0
    formula: str = "log(My * M) + (K^H) - L"
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class MetaReflectionResult:
    loop1_results: list[MonitoringResult] = field(default_factory=list)
    loop2_results: list[MonitoringResult] = field(default_factory=list)
    loop3_results: list[MonitoringResult] = field(default_factory=list)
    overall_learning_velocity: float = 0.0
    strategy_adjustments: list[str] = field(default_factory=list)
    process_improvements: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


_LEVEL_NAMES = {0: "surface", 1: "patterns", 2: "principles", 3: "meta_principles", 4: "foundational", 5: "transcendent", 6: "absolute"}

_STOP_WORDS = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "dare", "ought",
    "used", "to", "of", "in", "for", "on", "with", "at", "by", "from",
    "as", "into", "through", "during", "before", "after", "above", "below",
    "between", "out", "off", "over", "under", "again", "further", "then",
    "once", "here", "there", "when", "where", "why", "how", "all", "each",
    "every", "both", "few", "more", "most", "other", "some", "such", "no",
    "not", "only", "own", "same", "so", "than", "too", "very", "just",
    "because", "but", "and", "or", "if", "while", "about", "up", "its",
    "it", "this", "that", "these", "those", "i", "me", "my", "we", "our",
    "you", "your", "he", "him", "his", "she", "her", "they", "them", "their",
    "what", "which", "who", "whom", "whose", "also", "any",
})


def _tokenize(text: str) -> list[str]:
    tokens = re.findall(r"[a-z0-9]{2,}", text.lower())
    return [t for t in tokens if t not in _STOP_WORDS]


def _jaccard_similarity(tokens_a: list[str], tokens_b: list[str]) -> float:
    if not tokens_a or not tokens_b:
        return 0.0
    set_a = set(tokens_a)
    set_b = set(tokens_b)
    intersection = set_a & set_b
    union = set_a | set_b
    if not union:
        return 0.0
    return len(intersection) / len(union)


def _bigram_overlap(text_a: str, text_b: str) -> float:
    def _bigrams(t: str) -> set[str]:
        clean = re.sub(r"[^a-z0-9]", "", t.lower())
        return {clean[i : i + 2] for i in range(len(clean) - 1)} if len(clean) > 1 else set()
    bg_a = _bigrams(text_a)
    bg_b = _bigrams(text_b)
    if not bg_a or not bg_b:
        return 0.0
    return len(bg_a & bg_b) / len(bg_a | bg_b)


def _extract_key_phrases(text: str, max_phrases: int = 5) -> list[str]:
    tokens = _tokenize(text)
    if not tokens:
        return []
    counter = Counter(tokens)
    return [word for word, _ in counter.most_common(max_phrases)]


def _compress_text(text: str, target_ratio: float = 0.1) -> tuple[str, float]:
    if not text:
        return "", 0.0
    sentences = re.split(r"[.!?]+", text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
    if not sentences:
        truncated = text[: max(1, int(len(text) * target_ratio))]
        return truncated, len(text) / max(len(truncated), 1)
    token_counts = []
    for s in sentences:
        tokens = _tokenize(s)
        token_counts.append((s, len(tokens), tokens))
    token_counts.sort(key=lambda x: x[1], reverse=True)
    target_len = max(1, int(len(text) * target_ratio))
    essence_parts: list[str] = []
    current_len = 0
    for s, tlen, _ in token_counts:
        if current_len + len(s) <= target_len * 1.5:
            essence_parts.append(s)
            current_len += len(s)
        if current_len >= target_len:
            break
    if not essence_parts:
        essence_parts = [token_counts[0][0]]
    essence = ". ".join(essence_parts) + "."
    ratio = len(text) / max(len(essence), 1)
    return essence, ratio


class HelicalIterator:
    def __init__(self) -> None:
        self._current_level: int = 0
        self._spiral_count: int = 0
        self._level_insights: dict[int, list[str]] = {}
        self._speed_factor: float = 1.0

    def iterate(self, context: str, current_level: int) -> SpiralResult:
        self._current_level = current_level
        self._spiral_count += 1
        level_name = _LEVEL_NAMES.get(current_level, f"level_{current_level}")
        insights = self._extract_level_insights(context, current_level)
        if current_level not in self._level_insights:
            self._level_insights[current_level] = []
        self._level_insights[current_level].extend(insights)
        phase = self._determine_phase(current_level)
        return SpiralResult(
            level=current_level,
            phase=phase,
            insights=insights,
            timestamp=datetime.now().isoformat(),
        )

    def _extract_level_insights(self, context: str, level: int) -> list[str]:
        sentences = re.split(r"[.!?]+", context)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 15]
        if not sentences:
            return [context[:200]] if context else []
        if level == 0:
            return sentences[:3]
        elif level == 1:
            return self._find_patterns(sentences)
        elif level == 2:
            return self._find_principles(sentences)
        elif level >= 3:
            return self._find_meta_principles(sentences, level)
        return sentences[:3]

    def _find_patterns(self, sentences: list[str]) -> list[str]:
        token_lists = [_tokenize(s) for s in sentences]
        all_tokens = [t for tl in token_lists for t in tl]
        if not all_tokens:
            return sentences[:3]
        counter = Counter(all_tokens)
        common = [w for w, c in counter.most_common(10) if c >= 2]
        patterns: list[str] = []
        for word in common[:3]:
            matching = [s for s in sentences if word in s.lower()]
            if matching:
                patterns.append(matching[0])
        return patterns if patterns else sentences[:3]

    def _find_principles(self, sentences: list[str]) -> list[str]:
        principle_indicators = [
            "always", "never", "must", "should", "rule", "principle",
            "law", "pattern", "fundamental", "core", "key", "essential",
            "critical", "important", "because", "therefore", "thus",
            "consequently", "hence", "implies",
        ]
        principles: list[str] = []
        for s in sentences:
            sl = s.lower()
            if any(ind in sl for ind in principle_indicators):
                principles.append(s)
        return principles[:3] if principles else sentences[:3]

    def _find_meta_principles(self, sentences: list[str], level: int) -> list[str]:
        meta_indicators = [
            "meta", "about", "reflect", "learn", "process", "system",
            "framework", "approach", "methodology", "paradigm", "model",
            "theory", "abstraction", "generalize", "universal",
        ]
        meta: list[str] = []
        for s in sentences:
            sl = s.lower()
            if any(ind in sl for ind in meta_indicators):
                meta.append(s)
        if not meta:
            longest = sorted(sentences, key=len, reverse=True)
            meta = longest[:2]
        return meta[:3]

    def _determine_phase(self, level: int) -> SpiralPhase:
        phase_cycle = level % 4
        if phase_cycle == 0:
            return SpiralPhase.PROCESS
        elif phase_cycle == 1:
            return SpiralPhase.REFLECT
        elif phase_cycle == 2:
            return SpiralPhase.DEEPEN
        else:
            return SpiralPhase.CRYSTALLIZE

    @property
    def spiral_count(self) -> int:
        return self._spiral_count

    @property
    def current_level(self) -> int:
        return self._current_level


class KnowledgeCrystallizer:
    def __init__(self, compression_target: float = 0.1) -> None:
        self._compression_target = compression_target
        self._crystals: dict[str, KnowledgeCrystal] = {}

    def crystallize(self, learning_items: list[str], level: int) -> list[KnowledgeCrystal]:
        if not learning_items:
            return []
        crystals: list[KnowledgeCrystal] = []
        for item in learning_items:
            essence, ratio = _compress_text(item, self._compression_target)
            if not essence:
                essence = item[:100]
                ratio = len(item) / max(len(essence), 1)
            crystal = KnowledgeCrystal(
                concept=_extract_key_phrases(item, 3)[0] if _extract_key_phrases(item, 3) else f"concept_l{level}",
                level=level,
                essence=essence,
                source_length=len(item),
                compression_ratio=round(ratio, 2),
                confidence=min(1.0, 0.3 + level * 0.15),
            )
            self._crystals[crystal.id] = crystal
            crystals.append(crystal)
        self._update_connections(crystals)
        return crystals

    def retrieve_crystals(self, query: str, min_level: int = 0) -> list[KnowledgeCrystal]:
        query_tokens = _tokenize(query)
        results: list[tuple[float, KnowledgeCrystal]] = []
        for crystal in self._crystals.values():
            if crystal.level < min_level:
                continue
            crystal_tokens = _tokenize(crystal.essence + " " + crystal.concept)
            sim = _jaccard_similarity(query_tokens, crystal_tokens)
            if sim > 0.05:
                results.append((sim, crystal))
        results.sort(key=lambda x: x[0], reverse=True)
        return [c for _, c in results[:20]]

    def _update_connections(self, new_crystals: list[KnowledgeCrystal]) -> None:
        for new_c in new_crystals:
            new_tokens = _tokenize(new_c.essence + " " + new_c.concept)
            for existing_id, existing_c in self._crystals.items():
                if existing_id == new_c.id:
                    continue
                ex_tokens = _tokenize(existing_c.essence + " " + existing_c.concept)
                sim = _jaccard_similarity(new_tokens, ex_tokens)
                if sim > 0.15:
                    if existing_id not in new_c.connections:
                        new_c.connections.append(existing_id)
                    if new_c.id not in existing_c.connections:
                        existing_c.connections.append(new_c.id)

    @property
    def crystal_count(self) -> int:
        return len(self._crystals)

    def get_all_crystals(self) -> dict[str, KnowledgeCrystal]:
        return dict(self._crystals)


class AttractorDetector:
    def __init__(self, resonance_threshold: float = 0.6) -> None:
        self._resonance_threshold = resonance_threshold
        self._detection_history: list[Attractor] = []

    def detect_attractors(
        self, new_context: str, existing_crystals: dict[str, KnowledgeCrystal]
    ) -> list[Attractor]:
        if not existing_crystals or not new_context:
            return []
        context_tokens = _tokenize(new_context)
        context_bigrams = _bigram_overlap(new_context, new_context)
        attractors: list[Attractor] = []
        for crystal_id, crystal in existing_crystals.items():
            crystal_text = crystal.essence + " " + crystal.concept
            crystal_tokens = _tokenize(crystal_text)
            token_sim = _jaccard_similarity(context_tokens, crystal_tokens)
            bigram_sim = _bigram_overlap(new_context, crystal_text)
            resonance = 0.6 * token_sim + 0.4 * bigram_sim
            if resonance >= self._resonance_threshold:
                matched = list(set(context_tokens) & set(crystal_tokens))
                suggested_depth = crystal.level + 1
                attractor = Attractor(
                    source_crystal_id=crystal_id,
                    resonance_score=round(resonance, 4),
                    suggested_depth=suggested_depth,
                    trigger_reason=f"resonance={resonance:.3f} with crystal '{crystal.concept}' at level {crystal.level}",
                    matched_terms=matched[:10],
                )
                attractors.append(attractor)
                self._detection_history.append(attractor)
        attractors.sort(key=lambda a: a.resonance_score, reverse=True)
        return attractors[:10]

    @property
    def total_detections(self) -> int:
        return len(self._detection_history)

    @property
    def threshold(self) -> float:
        return self._resonance_threshold


class MetaCognitiveMonitor:
    def __init__(self) -> None:
        self._velocity_history: list[float] = []
        self._insight_counts: list[int] = []
        self._adjustment_count: int = 0

    def monitor(self, spiral_result: SpiralResult, loop_level: LoopLevel) -> MonitoringResult:
        insight_count = len(spiral_result.insights)
        self._insight_counts.append(insight_count)
        velocity = self._compute_velocity()
        self._velocity_history.append(velocity)
        if loop_level == LoopLevel.ACTION:
            return self._monitor_action(spiral_result, velocity)
        elif loop_level == LoopLevel.REFLECTION:
            return self._monitor_reflection(spiral_result, velocity)
        else:
            return self._monitor_meta_learning(spiral_result, velocity)

    def _monitor_action(self, result: SpiralResult, velocity: float) -> MonitoringResult:
        if result.gain > 0.1:
            return MonitoringResult(
                loop_level=LoopLevel.ACTION,
                status=MonitoringStatus.ON_TRACK,
                insight=f"Gain={result.gain:.3f} at level {result.level}, on track",
                recommended_action="continue",
                learning_velocity=velocity,
            )
        elif result.gain > 0.03:
            return MonitoringResult(
                loop_level=LoopLevel.ACTION,
                status=MonitoringStatus.ADJUST,
                insight=f"Gain={result.gain:.3f} declining at level {result.level}",
                recommended_action="deepen_or_spiral_back",
                learning_velocity=velocity,
            )
        else:
            self._adjustment_count += 1
            return MonitoringResult(
                loop_level=LoopLevel.ACTION,
                status=MonitoringStatus.ESCALATE,
                insight=f"Gain={result.gain:.3f} too low at level {result.level}, escalate to reflection",
                recommended_action="escalate_to_loop2",
                learning_velocity=velocity,
            )

    def _monitor_reflection(self, result: SpiralResult, velocity: float) -> MonitoringResult:
        if velocity > 0.5:
            return MonitoringResult(
                loop_level=LoopLevel.REFLECTION,
                status=MonitoringStatus.ON_TRACK,
                insight=f"Learning velocity={velocity:.3f} healthy, approach is working",
                recommended_action="maintain_strategy",
                learning_velocity=velocity,
            )
        elif velocity > 0.2:
            return MonitoringResult(
                loop_level=LoopLevel.REFLECTION,
                status=MonitoringStatus.ADJUST,
                insight=f"Learning velocity={velocity:.3f} declining, consider strategy change",
                recommended_action="try_different_approach",
                learning_velocity=velocity,
            )
        else:
            return MonitoringResult(
                loop_level=LoopLevel.REFLECTION,
                status=MonitoringStatus.ESCALATE,
                insight=f"Learning velocity={velocity:.3f} critically low, process needs improvement",
                recommended_action="escalate_to_loop3",
                learning_velocity=velocity,
            )

    def _monitor_meta_learning(self, result: SpiralResult, velocity: float) -> MonitoringResult:
        recent_velocities = self._velocity_history[-5:] if self._velocity_history else [0.0]
        avg_velocity = sum(recent_velocities) / len(recent_velocities)
        if avg_velocity > 0.3:
            return MonitoringResult(
                loop_level=LoopLevel.META_LEARNING,
                status=MonitoringStatus.ON_TRACK,
                insight=f"Meta-learning healthy, avg velocity={avg_velocity:.3f}",
                recommended_action="no_process_change_needed",
                learning_velocity=avg_velocity,
            )
        else:
            return MonitoringResult(
                loop_level=LoopLevel.META_LEARNING,
                status=MonitoringStatus.ADJUST,
                insight=f"Meta-learning slow, avg velocity={avg_velocity:.3f}, process needs tuning",
                recommended_action="adjust_spiral_speed_or_depth",
                learning_velocity=avg_velocity,
            )

    def _compute_velocity(self) -> float:
        if len(self._insight_counts) < 2:
            return 1.0 if self._insight_counts and self._insight_counts[0] > 0 else 0.0
        recent = self._insight_counts[-5:]
        if not recent:
            return 0.0
        return sum(recent) / len(recent)

    @property
    def adjustment_count(self) -> int:
        return self._adjustment_count


class ProgressiveDepthController:
    def __init__(self, max_depth: int = 6, convergence_threshold: float = 0.05) -> None:
        self._max_depth = max_depth
        self._convergence_threshold = convergence_threshold
        self._gain_history: list[float] = []
        self._consecutive_low: int = 0

    def should_continue(self, current_level: int, gain_history: list[float] | None = None) -> bool:
        if current_level >= self._max_depth:
            return False
        gains = gain_history if gain_history is not None else self._gain_history
        if len(gains) < 2:
            return True
        last_two = gains[-2:]
        if all(g < self._convergence_threshold for g in last_two):
            return False
        return True

    def compute_gain(self, current_result: SpiralResult, previous_result: SpiralResult | None) -> float:
        if previous_result is None:
            current_insight_count = len(current_result.insights)
            return min(1.0, current_insight_count / 3.0) if current_insight_count > 0 else 0.0
        current_info = len(current_result.insights) + len(current_result.crystals_formed)
        previous_info = len(previous_result.insights) + len(previous_result.crystals_formed)
        if previous_info == 0:
            return 1.0 if current_info > 0 else 0.0
        gain = (current_info - previous_info) / previous_info
        gain = max(0.0, min(1.0, gain))
        self._gain_history.append(gain)
        if gain < self._convergence_threshold:
            self._consecutive_low += 1
        else:
            self._consecutive_low = 0
        return gain

    def get_convergence_reason(self, current_level: int) -> ConvergenceReason:
        if current_level >= self._max_depth:
            return ConvergenceReason.MAX_DEPTH
        if self._consecutive_low >= 2:
            return ConvergenceReason.CONSECUTIVE_LOW
        if self._gain_history and self._gain_history[-1] < self._convergence_threshold:
            return ConvergenceReason.LOW_GAIN
        return ConvergenceReason.NOT_CONVERGED

    @property
    def max_depth(self) -> int:
        return self._max_depth

    @property
    def gain_history(self) -> list[float]:
        return list(self._gain_history)


class MetaHelicalLearningEngine:
    FORMULA = "log(My * M) + (K^H) - L"

    def __init__(self, memory_engine: Any | None = None) -> None:
        self.helical_iterator = HelicalIterator()
        self.crystallizer = KnowledgeCrystallizer()
        self.attractor_detector = AttractorDetector()
        self.meta_monitor = MetaCognitiveMonitor()
        self.depth_controller = ProgressiveDepthController()
        self.memory_engine = memory_engine
        self._crystal_store: dict[str, KnowledgeCrystal] = {}
        self._spiral_history: list[SpiralResult] = []
        self._learning_results: list[HelicalLearningResult] = []

    def learn(self, context: str, max_depth: int = 6) -> HelicalLearningResult:
        if not context or not context.strip():
            return HelicalLearningResult(
                convergence_reason=ConvergenceReason.NOT_CONVERGED,
                formula=self.FORMULA,
            )
        self.depth_controller = ProgressiveDepthController(max_depth=max_depth)
        spiral_trace: list[SpiralResult] = []
        all_crystals: list[KnowledgeCrystal] = []
        meta_insights: list[MonitoringResult] = []
        previous_result: SpiralResult | None = None
        convergence_level = 0
        convergence_reason = ConvergenceReason.NOT_CONVERGED
        current_context = context
        for level in range(max_depth + 1):
            spiral = self.helical_iterator.iterate(current_context, level)
            attractors = self.attractor_detector.detect_attractors(
                current_context, self._crystal_store
            )
            spiral.attractors_detected = attractors
            if attractors and level > 0:
                revisit_parts: list[str] = []
                for att in attractors[:3]:
                    crystal = self._crystal_store.get(att.source_crystal_id)
                    if crystal:
                        revisit_parts.append(crystal.essence)
                if revisit_parts:
                    current_context = current_context + " " + " ".join(revisit_parts)
                    revisit_spiral = self.helical_iterator.iterate(current_context, level)
                    spiral.insights.extend(revisit_spiral.insights)
            crystals = self.crystallizer.crystallize(spiral.insights, level)
            spiral.crystals_formed = crystals
            for c in crystals:
                self._crystal_store[c.id] = c
                all_crystals.append(c)
            gain = self.depth_controller.compute_gain(spiral, previous_result)
            spiral.gain = gain
            loop_level = self._determine_loop_level(level)
            monitoring = self.meta_monitor.monitor(spiral, loop_level)
            meta_insights.append(monitoring)
            if monitoring.status == MonitoringStatus.ESCALATE and loop_level == LoopLevel.ACTION:
                reflection = self.meta_monitor.monitor(spiral, LoopLevel.REFLECTION)
                meta_insights.append(reflection)
            spiral_trace.append(spiral)
            self._spiral_history.append(spiral)
            previous_result = spiral
            if not self.depth_controller.should_continue(level, self.depth_controller.gain_history):
                convergence_level = level
                convergence_reason = self.depth_controller.get_convergence_reason(level)
                break
            convergence_level = level
        else:
            convergence_reason = ConvergenceReason.MAX_DEPTH
        total_insights = sum(len(s.insights) for s in spiral_trace)
        gains = [s.gain for s in spiral_trace if s.gain > 0]
        avg_gain = sum(gains) / len(gains) if gains else 0.0
        result = HelicalLearningResult(
            final_crystals=all_crystals,
            spiral_trace=spiral_trace,
            convergence_level=convergence_level,
            convergence_reason=convergence_reason,
            meta_insights=meta_insights,
            total_spirals=len(spiral_trace),
            total_insights=total_insights,
            avg_gain=round(avg_gain, 4),
            formula=self.FORMULA,
        )
        self._learning_results.append(result)
        if self.memory_engine is not None:
            self._persist_to_memory(result)
        return result

    def recall(self, query: str, min_confidence: float = 0.5) -> list[KnowledgeCrystal]:
        from_crystallizer = self.crystallizer.retrieve_crystals(query)
        results = [c for c in from_crystallizer if c.confidence >= min_confidence]
        if not results:
            query_tokens = _tokenize(query)
            for crystal in self._crystal_store.values():
                if crystal.confidence < min_confidence:
                    continue
                crystal_tokens = _tokenize(crystal.essence + " " + crystal.concept)
                sim = _jaccard_similarity(query_tokens, crystal_tokens)
                if sim > 0.1:
                    results.append(crystal)
        results.sort(key=lambda c: c.confidence, reverse=True)
        return results[:20]

    def reflect(self) -> MetaReflectionResult:
        loop1: list[MonitoringResult] = []
        loop2: list[MonitoringResult] = []
        loop3: list[MonitoringResult] = []
        for result in self._learning_results:
            for mi in result.meta_insights:
                if mi.loop_level == LoopLevel.ACTION:
                    loop1.append(mi)
                elif mi.loop_level == LoopLevel.REFLECTION:
                    loop2.append(mi)
                else:
                    loop3.append(mi)
        velocities = [mi.learning_velocity for mi in loop1 + loop2 + loop3 if mi.learning_velocity > 0]
        overall_velocity = sum(velocities) / len(velocities) if velocities else 0.0
        strategy_adjustments: list[str] = []
        for mi in loop2:
            if mi.status in (MonitoringStatus.ADJUST, MonitoringStatus.ESCALATE):
                strategy_adjustments.append(mi.recommended_action)
        process_improvements: list[str] = []
        for mi in loop3:
            if mi.status in (MonitoringStatus.ADJUST, MonitoringStatus.ESCALATE):
                process_improvements.append(mi.recommended_action)
        return MetaReflectionResult(
            loop1_results=loop1,
            loop2_results=loop2,
            loop3_results=loop3,
            overall_learning_velocity=round(overall_velocity, 4),
            strategy_adjustments=strategy_adjustments,
            process_improvements=process_improvements,
        )

    def _determine_loop_level(self, level: int) -> LoopLevel:
        if level <= 1:
            return LoopLevel.ACTION
        elif level <= 3:
            return LoopLevel.REFLECTION
        else:
            return LoopLevel.META_LEARNING

    def _persist_to_memory(self, result: HelicalLearningResult) -> None:
        if self.memory_engine is None:
            return
        try:
            for crystal in result.final_crystals:
                self.memory_engine.store_semantic(
                    key=f"crystal_{crystal.id}",
                    value=crystal.essence,
                    metadata={
                        "concept": crystal.concept,
                        "level": crystal.level,
                        "confidence": crystal.confidence,
                        "compression_ratio": crystal.compression_ratio,
                    },
                )
        except Exception:
            pass

    @property
    def crystal_count(self) -> int:
        return len(self._crystal_store)

    @property
    def learning_count(self) -> int:
        return len(self._learning_results)

    def get_crystals_by_level(self, level: int) -> list[KnowledgeCrystal]:
        return [c for c in self._crystal_store.values() if c.level == level]

    def get_stats(self) -> dict[str, Any]:
        level_dist: dict[int, int] = {}
        for c in self._crystal_store.values():
            level_dist[c.level] = level_dist.get(c.level, 0) + 1
        return {
            "total_crystals": len(self._crystal_store),
            "total_learnings": len(self._learning_results),
            "total_spirals": len(self._spiral_history),
            "level_distribution": level_dist,
            "formula": self.FORMULA,
        }


def demo() -> None:
    engine = MetaHelicalLearningEngine()
    context = (
        "Harness Engineering is a methodology for building reliable AI systems. "
        "It uses feedforward constraints and feedback verification to create closed-loop iteration. "
        "The core formula is Agent = Model + Harness. "
        "Every error must be captured and converted into a rule that prevents recurrence. "
        "The system follows the principle that humans steer while agents execute. "
        "Knowledge priority means using existing resources before seeking external dependencies. "
        "The spiral curriculum approach revisits topics at increasing depth. "
        "Triple-loop learning questions not just actions but the learning process itself. "
        "LLMs suffer from linear thinking and short-term memory loss. "
        "Meta-helical learning overcomes these by spiraling through concepts at increasing depth. "
        "Knowledge crystals compress learning into dense, retrievable structures. "
        "Attractor detection finds resonance between new and existing knowledge. "
        "Progressive depth control prevents overthinking while ensuring convergence. "
    )
    print("=" * 60)
    print("Meta-Helical Learning Engine Demo")
    print(f"Formula: {engine.FORMULA}")
    print("=" * 60)
    result = engine.learn(context, max_depth=4)
    print(f"\nConvergence: Level {result.convergence_level} ({result.convergence_reason.value})")
    print(f"Total spirals: {result.total_spirals}")
    print(f"Total insights: {result.total_insights}")
    print(f"Average gain: {result.avg_gain:.4f}")
    print(f"Crystals formed: {len(result.final_crystals)}")
    print("\n--- Spiral Trace ---")
    for spiral in result.spiral_trace:
        print(
            f"  Level {spiral.level} ({spiral.phase.value}): "
            f"{len(spiral.insights)} insights, gain={spiral.gain:.4f}, "
            f"{len(spiral.crystals_formed)} crystals, "
            f"{len(spiral.attractors_detected)} attractors"
        )
    print("\n--- Knowledge Crystals ---")
    for crystal in result.final_crystals:
        print(
            f"  [{crystal.level}] {crystal.concept}: "
            f"essence='{crystal.essence[:80]}...' "
            f"compression={crystal.compression_ratio:.1f}x "
            f"confidence={crystal.confidence:.2f}"
        )
    print("\n--- Recall Test ---")
    recalled = engine.recall("spiral learning methodology")
    print(f"  Query: 'spiral learning methodology' -> {len(recalled)} crystals")
    for c in recalled[:3]:
        print(f"    [{c.level}] {c.concept} (confidence={c.confidence:.2f})")
    print("\n--- Meta Reflection ---")
    reflection = engine.reflect()
    print(f"  Loop 1 (Action): {len(reflection.loop1_results)} results")
    print(f"  Loop 2 (Reflection): {len(reflection.loop2_results)} results")
    print(f"  Loop 3 (Meta-Learning): {len(reflection.loop3_results)} results")
    print(f"  Overall velocity: {reflection.overall_learning_velocity:.4f}")
    print(f"  Strategy adjustments: {len(reflection.strategy_adjustments)}")
    print(f"  Process improvements: {len(reflection.process_improvements)}")
    print("\n--- Engine Stats ---")
    stats = engine.get_stats()
    for k, v in stats.items():
        print(f"  {k}: {v}")
    print("\n" + "=" * 60)
    print("Demo complete.")


if __name__ == "__main__":
    demo()
