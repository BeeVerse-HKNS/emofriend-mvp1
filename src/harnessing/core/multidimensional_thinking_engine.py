from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ThinkingMode(Enum):
    RATIONAL = "rational"
    EMOTIONAL = "emotional"
    HUMAN = "human"
    FORMULA = "formula"
    EMERGENT = "emergent"


MODE_FORMULAS: Dict[ThinkingMode, str] = {
    ThinkingMode.RATIONAL: "L * (D - B) + R",
    ThinkingMode.EMOTIONAL: "E * (V + A) + P",
    ThinkingMode.HUMAN: "H * sq(C) + M",
    ThinkingMode.FORMULA: "K * R + F - K",
    ThinkingMode.EMERGENT: "Xi(S) + ⊕(D) - L",
}


@dataclass
class ThinkingResult:
    mode: ThinkingMode
    content: str
    confidence: float
    mode_specific_data: Dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0
    timestamp: float = 0.0


@dataclass
class ModeTrace:
    mode: ThinkingMode
    started_at: float
    ended_at: float
    confidence: float
    summary: str


class MultidimensionalThinkingEngine:
    KEYWORDS_TECHNICAL = {
        "code", "bug", "function", "class", "import", "api", "database",
        "sql", "python", "compile", "deploy", "server", "endpoint",
        "test", "debug", "error", "stack", "trace", "refactor", "lint",
    }
    KEYWORDS_EMOTIONAL = {
        "feel", "feeling", "emotion", "happy", "sad", "angry", "love",
        "fear", "hope", "despair", "worry", "anxious", "joy", "grief",
        "empathy", "compassion", "hurt", "lonely",
    }
    KEYWORDS_HUMAN = {
        "act", "do", "perform", "experience", "embody", "live",
        "practice", "exercise", "movement", "body", "walk", "run",
        "touch", "sensation", "perception", "intuition", "somatic",
    }
    KEYWORDS_FORMULA = {
        "formula", "equation", "calculate", "compute", "derive", "optimize",
        "minimize", "maximize", "function", "operator", "variable",
        "coefficient", "matrix", "tensor", "gradient",
    }
    KEYWORDS_EMERGENT = {
        "innovation", "synergy", "cross-domain", "interdisciplinary",
        "novel", "breakthrough", "paradigm", "disrupt", "transform",
        "integrate", "combine", "synthesize", "evolve", "emerge",
    }

    def __init__(self, seed: int = 42) -> None:
        self._seed = seed
        self._trace: List[ModeTrace] = []
        self._call_counts: Dict[str, int] = {m.value: 0 for m in ThinkingMode}
        self._total_thinks = 0

    def think(
        self,
        query: str,
        mode: ThinkingMode,
        context: Optional[Dict[str, Any]] = None,
    ) -> ThinkingResult:
        started = time.time()
        ctx = context or {}
        if mode == ThinkingMode.RATIONAL:
            content, data = self._rational(query, ctx)
        elif mode == ThinkingMode.EMOTIONAL:
            content, data = self._emotional(query, ctx)
        elif mode == ThinkingMode.HUMAN:
            content, data = self._human(query, ctx)
        elif mode == ThinkingMode.FORMULA:
            content, data = self._formula(query, ctx)
        elif mode == ThinkingMode.EMERGENT:
            content, data = self._emergent(query, ctx)
        else:
            raise ValueError(f"Unknown thinking mode: {mode}")
        confidence = self._score_confidence(query, mode, ctx)
        ended = time.time()
        result = ThinkingResult(
            mode=mode,
            content=content,
            confidence=confidence,
            mode_specific_data=data,
            duration_ms=(ended - started) * 1000.0,
            timestamp=ended,
        )
        self._call_counts[mode.value] += 1
        self._total_thinks += 1
        self._trace.append(ModeTrace(
            mode=mode,
            started_at=started,
            ended_at=ended,
            confidence=confidence,
            summary=self._summarize(content),
        ))
        return result

    def _rational(self, query: str, ctx: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
        steps = [
            f"Step 1: Decompose '{query}' into premises",
            "Step 2: Apply logical operators (AND/OR/IMPLIES)",
            "Step 3: Chain of deduction with verifiable axioms",
            "Step 4: Verify against counter-examples",
        ]
        content = "Analysis of '" + query + "': logical steps:\n  - " + "\n  - ".join(steps)
        return content, {
            "formula": MODE_FORMULAS[ThinkingMode.RATIONAL],
            "steps": steps,
            "axioms": ctx.get("axioms", []),
        }

    def _emotional(self, query: str, ctx: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
        valence = self._emotional_valence(query)
        arousal = self._emotional_arousal(query)
        content = (
            f"Feeling about '{query}': empathic response — "
            f"valence={valence:+.2f}, arousal={arousal:.2f}. "
            "Acknowledging the affective stance before reasoning."
        )
        return content, {
            "formula": MODE_FORMULAS[ThinkingMode.EMOTIONAL],
            "valence": valence,
            "arousal": arousal,
        }

    def _human(self, query: str, ctx: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
        content = (
            f"Human act on '{query}': embodied perspective — "
            "what would I do, see, touch, hear? Sensorimotor grounding "
            "before symbol manipulation."
        )
        return content, {
            "formula": MODE_FORMULAS[ThinkingMode.HUMAN],
            "embodied_perspective": "sensorimotor + affective + enactive",
        }

    def _formula(self, query: str, ctx: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
        k = self._string_difficulty(query)
        r = len(query) % 9
        f = (k * r) % 7
        score = k * r + f - k
        content = (
            f"Formula K*R+F-K applied to '{query}': "
            f"K={k}, R={r}, F={f}, score={score}."
        )
        return content, {
            "formula": MODE_FORMULAS[ThinkingMode.FORMULA],
            "K": k, "R": r, "F": f, "score": score,
        }

    def _emergent(self, query: str, ctx: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
        domains = self._detect_domains(query)
        content = (
            f"Cross-domain synergy for '{query}': bridging "
            f"{', '.join(domains) if domains else 'multiple fields'} "
            "via emergent property detection."
        )
        return content, {
            "formula": MODE_FORMULAS[ThinkingMode.EMERGENT],
            "domains": domains,
            "synergy_score": len(domains) / 5.0,
        }

    def select_modes(self, query: str, max_modes: int = 3) -> List[ThinkingMode]:
        scores: Dict[ThinkingMode, float] = {}
        for mode in ThinkingMode:
            scores[mode] = self._mode_score(query, mode)
        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        chosen = [m for m, s in ranked[:max_modes] if s > 0]
        if not chosen:
            chosen = [ThinkingMode.RATIONAL]
        return chosen

    def _mode_score(self, query: str, mode: ThinkingMode) -> float:
        q_lower = query.lower()
        tokens = re.findall(r"[a-z']+", q_lower)
        if mode == ThinkingMode.RATIONAL:
            return sum(1 for t in tokens if t in self.KEYWORDS_TECHNICAL) * 1.5 + 0.2
        if mode == ThinkingMode.EMOTIONAL:
            return sum(1 for t in tokens if t in self.KEYWORDS_EMOTIONAL) * 1.5 + 0.2
        if mode == ThinkingMode.HUMAN:
            return sum(1 for t in tokens if t in self.KEYWORDS_HUMAN) * 1.5 + 0.2
        if mode == ThinkingMode.FORMULA:
            return sum(1 for t in tokens if t in self.KEYWORDS_FORMULA) * 1.5 + 0.5
        if mode == ThinkingMode.EMERGENT:
            return sum(1 for t in tokens if t in self.KEYWORDS_EMERGENT) * 1.5 + 0.3
        return 0.0

    def _score_confidence(self, query: str, mode: ThinkingMode, ctx: Dict[str, Any]) -> float:
        base = 0.5
        score = self._mode_score(query, mode)
        confidence = min(1.0, base + score * 0.1)
        if ctx.get("ground_truth"):
            confidence = min(1.0, confidence + 0.15)
        return round(confidence, 4)

    def _emotional_valence(self, query: str) -> float:
        positive = {"good", "great", "love", "happy", "joy", "wonderful", "excellent", "nice"}
        negative = {"bad", "hate", "sad", "angry", "fear", "terrible", "awful", "horrible"}
        q_lower = query.lower()
        pos = sum(1 for w in positive if w in q_lower)
        neg = sum(1 for w in negative if w in q_lower)
        total = pos + neg
        if total == 0:
            return 0.0
        return (pos - neg) / total

    def _emotional_arousal(self, query: str) -> float:
        exclam = query.count("!")
        question = query.count("?")
        caps = sum(1 for c in query if c.isupper())
        raw = exclam * 0.3 + question * 0.1 + caps * 0.05
        return min(1.0, raw)

    def _string_difficulty(self, query: str) -> int:
        h = hashlib.md5(query.encode("utf-8")).hexdigest()
        return int(h[:4], 16) % 10 + 1

    def _detect_domains(self, query: str) -> List[str]:
        domains: List[str] = []
        q_lower = query.lower()
        domain_keywords = {
            "math": ["equation", "matrix", "derivative", "integral"],
            "biology": ["cell", "gene", "protein", "dna"],
            "cs": ["code", "function", "algorithm", "data structure"],
            "psychology": ["feel", "emotion", "cognition", "behavior"],
            "business": ["market", "revenue", "customer", "profit"],
            "physics": ["force", "energy", "quantum", "relativity"],
        }
        for domain, kws in domain_keywords.items():
            if any(k in q_lower for k in kws):
                domains.append(domain)
        return domains

    def _summarize(self, content: str) -> str:
        if len(content) <= 80:
            return content
        return content[:77] + "..."

    def get_mode_trace(self) -> List[Dict[str, Any]]:
        return [
            {
                "mode": t.mode.value,
                "started_at": t.started_at,
                "ended_at": t.ended_at,
                "duration_ms": (t.ended_at - t.started_at) * 1000.0,
                "confidence": t.confidence,
                "summary": t.summary,
            }
            for t in self._trace
        ]

    def stats(self) -> Dict[str, Any]:
        return {
            "seed": self._seed,
            "total_thinks": self._total_thinks,
            "call_counts": dict(self._call_counts),
            "trace_length": len(self._trace),
            "available_modes": [m.value for m in ThinkingMode],
        }
