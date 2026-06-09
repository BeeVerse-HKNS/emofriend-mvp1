"""
LSP-AI Engine — LEGO Serious Play × AI

Emotion × Play × Structure = LSP-AI 4-step process

公式：log(C * E) + R * S
- log(C * E) — 抽象化（log）創造力（C）× 情感（E）嘅聯合
- R * S — 推理（R）× 驚喜發現（S）交叉協同
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class LSPStage(Enum):
    QUESTION = "QUESTION"
    BUILD = "BUILD"
    SHARE = "SHARE"
    REFLECT = "REFLECT"


class PlayerType(Enum):
    EXPLORER = "The Explorer"
    CREATOR = "The Creator"
    STRATEGIST = "The Strategist"
    STORYTELLER = "The Storyteller"
    HEALER = "The Healer"
    CONDUCTOR = "The Conductor"
    BUILDER = "The Builder"
    PLAYER = "The Player"


@dataclass
class PlayStep:
    stage: LSPStage
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    content: str = ""
    artifacts: list[str] = field(default_factory=list)
    confidence: float = 0.0
    notes: str = ""


@dataclass
class PlaySession:
    session_id: str
    player_type: PlayerType
    question: str
    steps: list[PlayStep] = field(default_factory=list)
    status: str = "active"
    surprise_score: float = 0.0
    resonance: float = 0.0

    def add_step(self, stage: LSPStage, content: str, confidence: float = 0.5, notes: str = "", artifacts: list[str] | None = None) -> PlayStep:
        step = PlayStep(stage=stage, content=content, confidence=confidence, notes=notes, artifacts=artifacts or [])
        self.steps.append(step)
        return step

    def complete(self) -> None:
        self.status = "completed"
        self.resonance = sum(s.confidence for s in self.steps) / max(len(self.steps), 1)


class LSPPlayerTypeDetector:
    KEYWORDS_MAP: dict[PlayerType, list[str]] = {
        PlayerType.EXPLORER: ["explore", "discover", "investigate", "find out", "research", "deep dive"],
        PlayerType.CREATOR: ["create", "build", "invent", "design", "make new", "innovate"],
        PlayerType.STRATEGIST: ["plan", "strategy", "compete", "advantage", "positioning", "go-to-market"],
        PlayerType.STORYTELLER: ["write", "tell story", "narrative", "content", "social media", "wechat", "weibo"],
        PlayerType.HEALER: ["fix", "debug", "repair", "heal", "recover", "restore", "troubleshoot"],
        PlayerType.CONDUCTOR: ["coordinate", "orchestrate", "multi-agent", "manage", "synchronize", "schedule"],
        PlayerType.BUILDER: ["construct", "implement", "develop", "engineer", "scaffold", "architecture"],
        PlayerType.PLAYER: ["game", "play", "gamify", "sprint", "experiment", "try"],
    }

    @classmethod
    def detect(cls, prompt: str) -> tuple[PlayerType, float]:
        prompt_lower = prompt.lower()
        scores: dict[PlayerType, float] = {pt: 0.0 for pt in PlayerType}

        for player_type, keywords in cls.KEYWORDS_MAP.items():
            for keyword in keywords:
                if keyword in prompt_lower:
                    scores[player_type] += 0.2

        best_type = max(scores, key=lambda pt: scores[pt])
        confidence = min(scores[best_type], 1.0)

        if confidence == 0.0:
            return PlayerType.EXPLORER, 0.3

        return best_type, confidence


class PlayModuleBridge:
    """Bridge between LSP-AI stages and existing play/ modules.

    Uses lazy imports so the engine degrades gracefully when the
    play modules (formula_engine, innovation_lab, strategy_explorer)
    are not available on the Python path.
    """

    _MODULE_MAP: dict[str, str] = {
        "formula_engine": "play.formula_engine",
        "innovation_lab": "play.innovation_lab",
        "strategy_explorer": "play.strategy_explorer",
    }

    def __init__(self) -> None:
        self._instances: dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Availability check
    # ------------------------------------------------------------------
    def is_available(self, module_name: str) -> bool:
        """Return True if *module_name* can be imported."""
        module_path = self._MODULE_MAP.get(module_name)
        if module_path is None:
            return False
        try:
            __import__(module_path)
            return True
        except ImportError:
            return False

    # ------------------------------------------------------------------
    # Lazy instance helpers
    # ------------------------------------------------------------------
    def _get_formula_engine(self) -> Any:
        if "formula_engine" not in self._instances:
            from play.formula_engine import FormulaEngineWrapper

            self._instances["formula_engine"] = FormulaEngineWrapper()
        return self._instances["formula_engine"]

    def _get_innovation_lab(self) -> Any:
        if "innovation_lab" not in self._instances:
            from play.innovation_lab import InnovationLabWrapper

            self._instances["innovation_lab"] = InnovationLabWrapper()
        return self._instances["innovation_lab"]

    def _get_strategy_explorer(self) -> Any:
        if "strategy_explorer" not in self._instances:
            from play.strategy_explorer import StrategyExplorer

            self._instances["strategy_explorer"] = StrategyExplorer()
        return self._instances["strategy_explorer"]

    # ------------------------------------------------------------------
    # Stage-based delegation
    # ------------------------------------------------------------------
    def delegate(self, stage: LSPStage, task: str, **kwargs: Any) -> dict:
        """Route an LSP stage + task to the appropriate play module.

        Parameters
        ----------
        stage : LSPStage
            Current LSP stage (BUILD or REFLECT are supported).
        task : str
            One of ``"predict"``, ``"invent"``, or ``"test"``.
        **kwargs
            Forwarded to the underlying module method.

        Returns
        -------
        dict
            Result from the play module, or an error dict on failure.
        """
        try:
            if stage == LSPStage.BUILD:
                if task == "predict":
                    engine = self._get_formula_engine()
                    return {"source": "formula_engine", "result": engine.predict(**kwargs)}
                if task == "invent":
                    lab = self._get_innovation_lab()
                    return {"source": "innovation_lab", "result": lab.invent(**kwargs)}
            elif stage == LSPStage.REFLECT:
                if task == "test":
                    explorer = self._get_strategy_explorer()
                    variant = kwargs.pop("variant", None)
                    actual_outcome = kwargs.pop("actual_outcome", "")
                    if variant is None:
                        return {"source": "strategy_explorer", "error": "variant is required"}
                    result = explorer.test(variant, actual_outcome)
                    return {
                        "source": "strategy_explorer",
                        "surprise_score": result.surprise_score,
                        "validated": result.validated,
                        "actual_outcome": result.actual_outcome,
                    }
            return {"error": f"Unsupported stage/task: {stage.value}/{task}"}
        except ImportError as exc:
            return {"error": f"Module not available: {exc}", "stage": stage.value, "task": task}
        except Exception as exc:  # noqa: BLE001
            return {"error": str(exc), "stage": stage.value, "task": task}


class LSPEngine:
    def __init__(self) -> None:
        self.sessions: dict[str, PlaySession] = {}

    def start_session(self, question: str, session_id: str | None = None) -> PlaySession:
        player_type, confidence = LSPPlayerTypeDetector.detect(question)
        if session_id is None:
            session_id = f"play-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"

        session = PlaySession(
            session_id=session_id,
            player_type=player_type,
            question=question,
        )
        session.add_step(
            LSPStage.QUESTION,
            question,
            confidence=confidence,
            notes=f"Detected Player Type: {player_type.value}",
        )
        self.sessions[session_id] = session
        return session

    def build(self, session_id: str, hypothesis: str, confidence: float = 0.5) -> PlayStep:
        session = self.sessions[session_id]
        return session.add_step(LSPStage.BUILD, hypothesis, confidence, "Hypothesis built")

    def share(self, session_id: str, narrative: str, confidence: float = 0.5) -> PlayStep:
        session = self.sessions[session_id]
        return session.add_step(LSPStage.SHARE, narrative, confidence, "Story shared")

    def reflect(self, session_id: str, learning: str, surprise_score: float = 0.0) -> PlayStep:
        session = self.sessions[session_id]
        session.surprise_score = surprise_score
        step = session.add_step(LSPStage.REFLECT, learning, confidence=1.0 - surprise_score, notes=f"Surprise: {surprise_score:.2f}")
        session.complete()
        return step

    def build_with_bridge(
        self,
        session_id: str,
        hypothesis: str,
        bridge_module: str | None = None,
        **kwargs: Any,
    ) -> PlayStep:
        """BUILD step that optionally delegates to a play module via PlayModuleBridge.

        Parameters
        ----------
        session_id : str
            Active session identifier.
        hypothesis : str
            The hypothesis to build.
        bridge_module : str | None
            One of ``"formula_engine"`` or ``"innovation_lab"``.
            When *None*, falls back to the simple :meth:`build` path.
        **kwargs
            Forwarded to the bridge module method.

        Returns
        -------
        PlayStep
            The recorded BUILD step, enriched with bridge artifacts when available.
        """
        session = self.sessions[session_id]

        if bridge_module is None:
            return self.build(session_id, hypothesis)

        bridge = PlayModuleBridge()
        task = "predict" if bridge_module == "formula_engine" else "invent"
        result = bridge.delegate(LSPStage.BUILD, task, **kwargs)

        artifacts: list[str] = []
        confidence = 0.5
        notes = "Bridge delegated"

        if "error" in result:
            notes = f"Bridge error: {result['error']}"
        else:
            artifacts.append(f"bridge:{result.get('source', bridge_module)}")
            confidence = 0.7
            notes = f"Bridge result from {result.get('source', bridge_module)}"

        return session.add_step(LSPStage.BUILD, hypothesis, confidence=confidence, notes=notes, artifacts=artifacts)

    def reflect_with_bridge(
        self,
        session_id: str,
        learning: str,
        expected_outcome: str | None = None,
        actual_outcome: str | None = None,
    ) -> PlayStep:
        """REFLECT step that optionally uses StrategyExplorer for surprise scoring.

        When both *expected_outcome* and *actual_outcome* are provided, the
        StrategyExplorer is used to compute a surprise score.  Otherwise the
        simple :meth:`reflect` path is taken with a default surprise of 0.0.

        Parameters
        ----------
        session_id : str
            Active session identifier.
        learning : str
            The learning / reflection text.
        expected_outcome : str | None
            What was expected (required for surprise scoring).
        actual_outcome : str | None
            What actually happened (required for surprise scoring).

        Returns
        -------
        PlayStep
            The recorded REFLECT step.
        """
        session = self.sessions[session_id]

        if expected_outcome is None or actual_outcome is None:
            return self.reflect(session_id, learning, surprise_score=0.0)

        bridge = PlayModuleBridge()
        try:
            from play.strategy_explorer import StrategyVariant, StrategyDimension

            variant = StrategyVariant(
                dimension=StrategyDimension.DIFFERENTIATION,
                name="reflect_with_bridge",
                hypothesis=learning,
                expected_outcome=expected_outcome,
            )
            result = bridge.delegate(
                LSPStage.REFLECT,
                "test",
                variant=variant,
                actual_outcome=actual_outcome,
            )
            surprise_score = result.get("surprise_score", 0.0)
        except ImportError:
            # StrategyExplorer not available — compute surprise inline
            overlap = len(set(expected_outcome.lower().split()) & set(actual_outcome.lower().split()))
            total = len(set(expected_outcome.lower().split()) | set(actual_outcome.lower().split()))
            surprise_score = 1.0 - (overlap / total) if total > 0 else 0.0
        except Exception:  # noqa: BLE001
            surprise_score = 0.0

        session.surprise_score = surprise_score
        step = session.add_step(
            LSPStage.REFLECT,
            learning,
            confidence=1.0 - surprise_score,
            notes=f"Surprise: {surprise_score:.2f} (expected: {expected_outcome}, actual: {actual_outcome})",
        )
        session.complete()
        return step

    def get_session(self, session_id: str) -> PlaySession | None:
        return self.sessions.get(session_id)

    def list_active_sessions(self) -> list[PlaySession]:
        return [s for s in self.sessions.values() if s.status == "active"]


def run_lsp_cycle(question: str, hypothesis: str, narrative: str, learning: str, surprise_score: float = 0.3) -> PlaySession:
    engine = LSPEngine()
    session = engine.start_session(question)
    engine.build(session.session_id, hypothesis, confidence=0.7)
    engine.share(session.session_id, narrative, confidence=0.7)
    engine.reflect(session.session_id, learning, surprise_score=surprise_score)
    return session


if __name__ == "__main__":
    session = run_lsp_cycle(
        question="How can we fix the disconnection with sub-projects?",
        hypothesis="Use LSP 4-step cycle to systematically improve each sub-project",
        narrative="Each sub-project goes through Question → Build → Share → Reflect, with EmoGlyph tracking emotional state",
        learning="LSP provides structure for AI agents to explore and improve systematically",
        surprise_score=0.2,
    )
    print(f"Session: {session.session_id}")
    print(f"Player Type: {session.player_type.value}")
    print(f"Status: {session.status}")
    print(f"Resonance: {session.resonance:.2f}")
    print(f"Steps: {len(session.steps)}")
