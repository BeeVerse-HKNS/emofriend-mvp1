"""
Play Formula Engine — EmoGlyph Play Scoring

Core Formula: (E × P) + (C ^ S) - D

E = EmoGlyph emotional depth (0-1, based on 5-layer coverage)
P = Play structure completeness (0-1, based on LSP 4-step coverage)
C = Creativity score (0-1, based on hypothesis novelty)
S = Surprise discovery score (0-1, based on unexpected findings)
D = Defensive defaults penalty (0-1, based on conservative bias)
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .lsp_ai_engine import LSPStage, PlaySession, PlayerType


@dataclass
class PlayFormulaResult:
    """Result of evaluating a single PlaySession against the play formula."""

    emotional_depth: float  # E
    play_structure: float  # P
    creativity: float  # C
    surprise: float  # S
    defensive_defaults: float  # D
    play_score: float  # final result
    formula_expression: str  # human-readable formula with values


@dataclass
class SprintFormulaResult:
    """Result of evaluating a sprint (multiple sessions) against the play formula."""

    session_results: list[PlayFormulaResult] = field(default_factory=list)
    avg_emotional_depth: float = 0.0
    avg_play_structure: float = 0.0
    avg_creativity: float = 0.0
    avg_surprise: float = 0.0
    avg_defensive_defaults: float = 0.0
    sprint_score: float = 0.0
    formula_expression: str = ""


# Player type → task relevance mapping for P bonus
_PLAYER_TYPE_TASK_KEYWORDS: dict[PlayerType, list[str]] = {
    PlayerType.EXPLORER: ["explore", "discover", "investigate", "find", "research"],
    PlayerType.CREATOR: ["create", "build", "invent", "design", "innovate"],
    PlayerType.STRATEGIST: ["plan", "strategy", "compete", "positioning", "market"],
    PlayerType.STORYTELLER: ["write", "story", "narrative", "content", "media"],
    PlayerType.HEALER: ["fix", "debug", "repair", "heal", "recover", "troubleshoot"],
    PlayerType.CONDUCTOR: ["coordinate", "orchestrate", "manage", "synchronize"],
    PlayerType.BUILDER: ["construct", "implement", "develop", "engineer", "architecture"],
    PlayerType.PLAYER: ["game", "play", "gamify", "sprint", "experiment"],
}

# Conservative / defensive keywords that indicate safe choices
_DEFENSIVE_KEYWORDS = [
    "safe", "standard", "default", "normal", "typical", "conventional",
    "usual", "traditional", "basic", "simple", "minimal", "conservative",
]


class PlayFormulaEngine:
    """Evaluates PlaySession instances using the EmoGlyph Play formula.

    Formula: (E × P) + (C ^ S) - D
    """

    def score_emotional_depth(self, session: PlaySession) -> float:
        """Score E: emotional depth based on 5-layer coverage.

        Layers are approximated by checking how many LSP steps carry
        meaningful emotional context (non-empty content + confidence > 0).
        The 5 layers map to: QUESTION, BUILD, SHARE, REFLECT, and
        a bonus layer when resonance is high.
        """
        layers_covered = 0

        # Each LSP stage with emotional content counts as one layer
        stages_with_content = set()
        for step in session.steps:
            if step.content and step.confidence > 0:
                stages_with_content.add(step.stage)

        layers_covered = len(stages_with_content)

        # Bonus 5th layer: resonance above 0.5 indicates deep emotional integration
        if session.resonance > 0.5:
            layers_covered += 1

        # Cap at 5
        layers_covered = min(layers_covered, 5)

        # Map layers to score: 5=1.0, 4=0.8, 3=0.6, 2=0.4, 1=0.2, 0=0.0
        base_score = layers_covered * 0.2

        # Factor in average confidence of steps as a modulation (0.5–1.0 range)
        if session.steps:
            avg_confidence = sum(s.confidence for s in session.steps) / len(session.steps)
            # Blend: 70% layer coverage, 30% confidence
            score = base_score * 0.7 + avg_confidence * 0.3
        else:
            score = base_score

        return round(min(max(score, 0.0), 1.0), 4)

    def score_play_structure(self, session: PlaySession) -> float:
        """Score P: play structure completeness based on LSP 4-step coverage.

        4 steps = 1.0, 3 = 0.75, 2 = 0.5, 1 = 0.25.
        Bonus if PlayerType matches the task question.
        """
        completed_stages = {step.stage for step in session.steps}
        lsp_stages = {LSPStage.QUESTION, LSPStage.BUILD, LSPStage.SHARE, LSPStage.REFLECT}
        covered = len(completed_stages & lsp_stages)

        base_score = covered * 0.25

        # Bonus: player type matches the task
        bonus = 0.0
        question_lower = session.question.lower()
        task_keywords = _PLAYER_TYPE_TASK_KEYWORDS.get(session.player_type, [])
        if any(kw in question_lower for kw in task_keywords):
            bonus = 0.1

        score = base_score + bonus
        return round(min(max(score, 0.0), 1.0), 4)

    def score_creativity(self, session: PlaySession) -> float:
        """Score C: creativity based on hypothesis novelty in the BUILD step.

        Novelty is approximated by content length and unique word ratio.
        InnovationLab usage is detected via artifacts.
        """
        build_steps = [s for s in session.steps if s.stage == LSPStage.BUILD]

        if not build_steps:
            return 0.5

        build_step = build_steps[-1]  # use the latest BUILD step
        content = build_step.content

        if not content:
            return 0.5

        # Novelty from unique word ratio
        words = content.lower().split()
        if not words:
            return 0.5

        unique_ratio = len(set(words)) / len(words)

        # Novelty from content length (longer = more detailed hypothesis)
        length_score = min(len(content) / 200.0, 1.0)

        # Base creativity from word novelty and length
        score = unique_ratio * 0.5 + length_score * 0.3

        # Bonus for InnovationLab usage (detected via artifacts)
        if any("innovation" in a.lower() or "lab" in a.lower() for a in build_step.artifacts):
            score += 0.2

        # Factor in confidence of the build step
        score += build_step.confidence * 0.1

        return round(min(max(score, 0.0), 1.0), 4)

    def score_surprise(self, session: PlaySession) -> float:
        """Score S: surprise discovery score.

        Direct from session.surprise_score.
        Default 0.3 if no surprise data.
        """
        if session.surprise_score > 0:
            return round(min(max(session.surprise_score, 0.0), 1.0), 4)
        return 0.3

    def score_defensive_defaults(self, session: PlaySession) -> float:
        """Score D: defensive defaults penalty.

        Based on how many steps have low confidence (< 0.5) and
        whether all steps use safe/conservative content.
        0.0 = no defensive bias, 1.0 = fully defensive.
        """
        if not session.steps:
            return 0.0

        # Low confidence ratio
        low_confidence_count = sum(1 for s in session.steps if s.confidence < 0.5)
        low_confidence_ratio = low_confidence_count / len(session.steps)

        # Conservative content ratio
        conservative_count = 0
        for step in session.steps:
            content_lower = step.content.lower()
            if any(kw in content_lower for kw in _DEFENSIVE_KEYWORDS):
                conservative_count += 1
        conservative_ratio = conservative_count / len(session.steps)

        # Blend both signals equally
        score = low_confidence_ratio * 0.5 + conservative_ratio * 0.5

        return round(min(max(score, 0.0), 1.0), 4)

    def evaluate(self, session: PlaySession) -> PlayFormulaResult:
        """Evaluate a single PlaySession against the play formula.

        Formula: (E × P) + (C ^ S) - D
        """
        e = self.score_emotional_depth(session)
        p = self.score_play_structure(session)
        c = self.score_creativity(session)
        s = self.score_surprise(session)
        d = self.score_defensive_defaults(session)

        play_score = (e * p) + (c ** s) - d
        play_score = round(min(max(play_score, 0.0), 2.0), 4)

        formula_expr = (
            f"({e:.4f} × {p:.4f}) + ({c:.4f} ^ {s:.4f}) - {d:.4f} = {play_score:.4f}"
        )

        return PlayFormulaResult(
            emotional_depth=e,
            play_structure=p,
            creativity=c,
            surprise=s,
            defensive_defaults=d,
            play_score=play_score,
            formula_expression=formula_expr,
        )

    def evaluate_sprint(self, sessions: list[PlaySession]) -> SprintFormulaResult:
        """Evaluate a sprint (multiple sessions) against the play formula.

        Averages all session scores, then applies:
        Sprint formula: (P * E) + (C ^ S) - D
        """
        if not sessions:
            return SprintFormulaResult(
                formula_expression="No sessions to evaluate",
            )

        session_results = [self.evaluate(s) for s in sessions]
        n = len(session_results)

        avg_e = sum(r.emotional_depth for r in session_results) / n
        avg_p = sum(r.play_structure for r in session_results) / n
        avg_c = sum(r.creativity for r in session_results) / n
        avg_s = sum(r.surprise for r in session_results) / n
        avg_d = sum(r.defensive_defaults for r in session_results) / n

        sprint_score = (avg_p * avg_e) + (avg_c ** avg_s) - avg_d
        sprint_score = round(min(max(sprint_score, 0.0), 2.0), 4)

        formula_expr = (
            f"({avg_p:.4f} * {avg_e:.4f}) + ({avg_c:.4f} ^ {avg_s:.4f}) - {avg_d:.4f} = {sprint_score:.4f}"
        )

        return SprintFormulaResult(
            session_results=session_results,
            avg_emotional_depth=round(avg_e, 4),
            avg_play_structure=round(avg_p, 4),
            avg_creativity=round(avg_c, 4),
            avg_surprise=round(avg_s, 4),
            avg_defensive_defaults=round(avg_d, 4),
            sprint_score=sprint_score,
            formula_expression=formula_expr,
        )
