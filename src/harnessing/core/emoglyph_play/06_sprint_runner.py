"""
Sprint Runner — 8-Hour EmoGlyph Play Sprint

4-Phase Sprint Execution:
  Phase 1 (0-2h): Question — Assess sub-project health
  Phase 2 (2-4h): Build — Construct EmoGlyph Play abstraction layer
  Phase 3 (4-6h): Share — Fix highest-disconnection sub-projects
  Phase 4 (6-8h): Reflect — QA verification + Sprint Report

Sprint Formula: (P * E) + (C ^ S) - D
"""

from __future__ import annotations

import importlib as _importlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from .lsp_ai_engine import (
    LSPEngine,
    LSPPlayerTypeDetector,
    LSPStage,
    PlaySession,
    PlayerType,
)
from .model_config import ModelSelector

_PROJECT_ROOT = Path(r"d:\My_Code_Projects\Harnessing")

# Digit-prefixed modules require importlib — use parent package name
_PKG = __name__.rpartition(".")[0] or __name__
_play_formula_mod = _importlib.import_module(".05_play_formula", _PKG)
_PlayFormulaEngine = _play_formula_mod.PlayFormulaEngine
_PlayFormulaResult = _play_formula_mod.PlayFormulaResult
_SprintFormulaResult = _play_formula_mod.SprintFormulaResult


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

class SprintPhase(Enum):
    QUESTION = "QUESTION"
    BUILD = "BUILD"
    SHARE = "SHARE"
    REFLECT = "REFLECT"


@dataclass
class SubProject:
    name: str
    path: str
    priority: str  # P0 / P1 / P2
    health_scores: dict[str, float] = field(default_factory=dict)  # dimension → score
    overall_health: str = "YELLOW"  # GREEN / YELLOW / RED
    disconnection_severity: float = 0.0  # 0-1
    recommended_player_type: PlayerType = PlayerType.EXPLORER
    issues: list[str] = field(default_factory=list)


@dataclass
class SprintReport:
    sprint_id: str
    start_time: str
    end_time: str
    phases_completed: list[SprintPhase] = field(default_factory=list)
    sub_projects: list[SubProject] = field(default_factory=list)
    sessions: list[PlaySession] = field(default_factory=list)
    formula_result: _SprintFormulaResult | None = None
    health_report: dict[str, Any] = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Default sub-projects
# ---------------------------------------------------------------------------

_DEFAULT_SUB_PROJECTS: list[SubProject] = [
    SubProject(
        name="World Cup 2026",
        path=str(_PROJECT_ROOT / "projects" / "world-2026-deploy"),
        priority="P0",
        recommended_player_type=PlayerType.BUILDER,
    ),
    SubProject(
        name="Auditing SME",
        path=str(_PROJECT_ROOT / "projects" / "efficiency" / "audit-platform"),
        priority="P0",
        recommended_player_type=PlayerType.HEALER,
    ),
    SubProject(
        name="Social Media",
        path=str(_PROJECT_ROOT / "projects" / "ai-content-creator"),
        priority="P1",
        recommended_player_type=PlayerType.STORYTELLER,
    ),
    SubProject(
        name="Business Proposal",
        path=str(_PROJECT_ROOT / "projects" / "business-case-proposal"),
        priority="P1",
        recommended_player_type=PlayerType.STRATEGIST,
    ),
    SubProject(
        name="Auto Jobs",
        path=str(_PROJECT_ROOT / "projects" / "automation"),
        priority="P2",
        recommended_player_type=PlayerType.CONDUCTOR,
    ),
]


# ---------------------------------------------------------------------------
# Sprint Runner
# ---------------------------------------------------------------------------

class SprintRunner:
    """8-Hour EmoGlyph Play Sprint runner.

    Executes 4 phases sequentially:
        Phase 1 (0-2h): QUESTION — Assess sub-project health
        Phase 2 (2-4h): BUILD   — Construct EmoGlyph Play abstraction layer
        Phase 3 (4-6h): SHARE   — Fix highest-disconnection sub-projects
        Phase 4 (6-8h): REFLECT — QA verification + Sprint Report
    """

    def __init__(self, sub_projects: list[SubProject] | None = None) -> None:
        self.sub_projects: list[SubProject] = (
            list(sub_projects) if sub_projects is not None else list(_DEFAULT_SUB_PROJECTS)
        )
        self.engine = LSPEngine()
        self.formula_engine = _PlayFormulaEngine()
        self.model_selector = ModelSelector()
        self._sessions: list[PlaySession] = []
        self._sprint_id = f"sprint-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
        self._start_time = ""

    # ------------------------------------------------------------------
    # Phase 1: QUESTION — Assess sub-project health
    # ------------------------------------------------------------------

    def run_phase_question(self) -> list[SubProject]:
        """Phase 1 (0-2h): Assess health of each sub-project using LSP Question."""
        assessed: list[SubProject] = []
        for sp in self.sub_projects:
            sp = self._assess_health(sp)
            sp = self._detect_player_type(sp)
            assessed.append(sp)

        self.sub_projects = assessed
        return assessed

    # ------------------------------------------------------------------
    # Phase 2: BUILD — Construct EmoGlyph Play abstraction layer
    # ------------------------------------------------------------------

    def run_phase_build(self, sub_projects: list[SubProject]) -> list[PlaySession]:
        """Phase 2 (2-4h): Build hypotheses for P0 fixes."""
        sessions: list[PlaySession] = []

        # Prioritise P0, then P1, then P2
        sorted_projects = sorted(sub_projects, key=lambda sp: sp.priority)

        for sp in sorted_projects:
            question = (
                f"How can we fix the disconnection with {sp.name} "
                f"(priority={sp.priority}, health={sp.overall_health})?"
            )
            session_id = f"sprint-{self._sprint_id}-{sp.name.replace(' ', '-').lower()}"
            session = self.engine.start_session(question, session_id=session_id)
            session.player_type = sp.recommended_player_type

            hypothesis = (
                f"Applying {sp.recommended_player_type.value} approach to {sp.name}: "
                f"address {len(sp.issues)} issue(s) — "
                + ("; ".join(sp.issues[:3]) if sp.issues else "no specific issues")
            )
            self.engine.build(session.session_id, hypothesis, confidence=0.7)
            sessions.append(session)

        self._sessions = sessions
        return sessions

    # ------------------------------------------------------------------
    # Phase 3: SHARE — Fix highest-disconnection sub-projects
    # ------------------------------------------------------------------

    def run_phase_share(self, sessions: list[PlaySession]) -> list[PlaySession]:
        """Phase 3 (4-6h): Share narratives and validate fixes."""
        for session in sessions:
            narrative = (
                f"Sprint narrative for {session.question[:60]}…: "
                f"Player {session.player_type.value} applied structured fix. "
                f"Resonance target: reduce disconnection severity."
            )
            self.engine.share(session.session_id, narrative, confidence=0.7)

        return sessions

    # ------------------------------------------------------------------
    # Phase 4: REFLECT — QA verification + Sprint Report
    # ------------------------------------------------------------------

    def run_phase_reflect(self, sessions: list[PlaySession]) -> SprintReport:
        """Phase 4 (6-8h): Reflect, evaluate formula, produce report."""
        for session in sessions:
            learning = (
                f"Sprint reflection: {session.player_type.value} completed cycle. "
                f"Steps: {len(session.steps)}, "
                f"confidence avg: {sum(s.confidence for s in session.steps) / max(len(session.steps), 1):.2f}."
            )
            surprise = 0.3  # default moderate surprise
            self.engine.reflect(session.session_id, learning, surprise_score=surprise)

        # Evaluate sprint formula
        formula_result: _SprintFormulaResult | None = None
        if sessions:
            formula_result = self.formula_engine.evaluate_sprint(sessions)

        # Build health report
        health_report = self._build_health_report()

        # Generate recommendations
        recommendations = self._generate_recommendations()

        end_time = datetime.utcnow().isoformat()

        return SprintReport(
            sprint_id=self._sprint_id,
            start_time=self._start_time,
            end_time=end_time,
            phases_completed=[SprintPhase.QUESTION, SprintPhase.BUILD, SprintPhase.SHARE, SprintPhase.REFLECT],
            sub_projects=self.sub_projects,
            sessions=sessions,
            formula_result=formula_result,
            health_report=health_report,
            recommendations=recommendations,
        )

    # ------------------------------------------------------------------
    # Full sprint
    # ------------------------------------------------------------------

    def run_full_sprint(self) -> SprintReport:
        """Run all 4 phases sequentially and produce a SprintReport."""
        self._start_time = datetime.utcnow().isoformat()

        # Phase 1: QUESTION
        assessed = self.run_phase_question()

        # Phase 2: BUILD
        sessions = self.run_phase_build(assessed)

        # Phase 3: SHARE
        sessions = self.run_phase_share(sessions)

        # Phase 4: REFLECT
        report = self.run_phase_reflect(sessions)

        return report

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _assess_health(self, sub_project: SubProject) -> SubProject:
        """Check sub-project path and score health dimensions 0-100.

        Dimensions:
            engine     — Python source files present and count
            interface  — UI / app.py present
            deployment — Deployment config present
            testing    — Test files present
        """
        project_path = Path(sub_project.path)
        scores: dict[str, float] = {
            "engine": 0.0,
            "interface": 0.0,
            "deployment": 0.0,
            "testing": 0.0,
        }
        issues: list[str] = []

        if not project_path.exists():
            # Path does not exist — all dimensions 0
            sub_project.health_scores = scores
            sub_project.overall_health = "RED"
            sub_project.disconnection_severity = 1.0
            sub_project.issues = [f"Path does not exist: {sub_project.path}"]
            return sub_project

        # --- engine dimension ---
        py_files = list(project_path.rglob("*.py"))
        if py_files:
            # Up to 5 files → 60, each additional file adds up to 40 more (capped at 10 extra)
            scores["engine"] = min(60 + len(py_files) * 4, 100)
        else:
            issues.append("No Python source files found")

        # --- interface dimension ---
        ui_files = list(project_path.rglob("app.py")) + list(project_path.rglob("ui.py"))
        ui_dirs = [d for d in project_path.rglob("*") if d.is_dir() and d.name in ("templates", "static", "frontend")]
        if ui_files or ui_dirs:
            scores["interface"] = min(60 + len(ui_files) * 20 + len(ui_dirs) * 10, 100)
        else:
            issues.append("No UI/app.py found")

        # --- deployment dimension ---
        deploy_files = (
            list(project_path.rglob("Dockerfile"))
            + list(project_path.rglob("docker-compose*.yml"))
            + list(project_path.rglob("docker-compose*.yaml"))
            + list(project_path.rglob(".github"))
            + list(project_path.rglob("vercel.json"))
            + list(project_path.rglob("requirements*.txt"))
            + list(project_path.rglob("pyproject.toml"))
        )
        if deploy_files:
            scores["deployment"] = min(50 + len(deploy_files) * 10, 100)
        else:
            issues.append("No deployment configuration found")

        # --- testing dimension ---
        test_files = (
            list(project_path.rglob("test_*.py"))
            + list(project_path.rglob("*_test.py"))
            + list(project_path.rglob("tests"))
        )
        if test_files:
            scores["testing"] = min(50 + len(test_files) * 10, 100)
        else:
            issues.append("No test files found")

        sub_project.health_scores = scores
        sub_project.issues = issues

        # Compute overall health and disconnection severity
        avg_score = sum(scores.values()) / len(scores)
        if avg_score >= 60:
            sub_project.overall_health = "GREEN"
            sub_project.disconnection_severity = round(max(1.0 - avg_score / 100, 0.0), 2)
        elif avg_score >= 30:
            sub_project.overall_health = "YELLOW"
            sub_project.disconnection_severity = round(max(1.0 - avg_score / 100, 0.0), 2)
        else:
            sub_project.overall_health = "RED"
            sub_project.disconnection_severity = round(max(1.0 - avg_score / 100, 0.0), 2)

        return sub_project

    def _detect_player_type(self, sub_project: SubProject) -> SubProject:
        """Use LSPPlayerTypeDetector on sub-project name + issues."""
        prompt = sub_project.name + " " + " ".join(sub_project.issues)
        player_type, _confidence = LSPPlayerTypeDetector.detect(prompt)
        sub_project.recommended_player_type = player_type
        return sub_project

    def _build_health_report(self) -> dict[str, Any]:
        """Build a summary health report from assessed sub-projects."""
        by_priority: dict[str, list[SubProject]] = {"P0": [], "P1": [], "P2": []}
        for sp in self.sub_projects:
            by_priority.setdefault(sp.priority, []).append(sp)

        health_summary: dict[str, Any] = {}
        for priority, projects in by_priority.items():
            health_summary[priority] = [
                {
                    "name": sp.name,
                    "overall_health": sp.overall_health,
                    "disconnection_severity": sp.disconnection_severity,
                    "health_scores": sp.health_scores,
                    "issues": sp.issues,
                    "recommended_player_type": sp.recommended_player_type.value,
                }
                for sp in projects
            ]

        # Aggregate stats
        all_scores = [sp.health_scores for sp in self.sub_projects if sp.health_scores]
        if all_scores:
            dimensions = list(all_scores[0].keys())
            avg_by_dim = {
                dim: round(sum(s.get(dim, 0) for s in all_scores) / len(all_scores), 2)
                for dim in dimensions
            }
            health_summary["aggregate_avg"] = avg_by_dim
        else:
            health_summary["aggregate_avg"] = {}

        red_count = sum(1 for sp in self.sub_projects if sp.overall_health == "RED")
        yellow_count = sum(1 for sp in self.sub_projects if sp.overall_health == "YELLOW")
        green_count = sum(1 for sp in self.sub_projects if sp.overall_health == "GREEN")
        health_summary["health_distribution"] = {
            "RED": red_count,
            "YELLOW": yellow_count,
            "GREEN": green_count,
        }

        return health_summary

    def _generate_recommendations(self) -> list[str]:
        """Generate actionable recommendations based on sprint assessment."""
        recommendations: list[str] = []

        # Prioritise RED sub-projects
        red_projects = [sp for sp in self.sub_projects if sp.overall_health == "RED"]
        for sp in red_projects:
            recommendations.append(
                f"[URGENT] {sp.name} ({sp.priority}): {sp.overall_health} health — "
                f"assign {sp.recommended_player_type.value} to address: "
                + ("; ".join(sp.issues[:3]) if sp.issues else "path missing")
            )

        # Yellow projects need attention
        yellow_projects = [sp for sp in self.sub_projects if sp.overall_health == "YELLOW"]
        for sp in yellow_projects:
            weakest_dim = ""
            if sp.health_scores:
                weakest_dim = min(sp.health_scores, key=sp.health_scores.get)  # type: ignore[arg-type]
            recommendations.append(
                f"[ATTENTION] {sp.name} ({sp.priority}): {sp.overall_health} health — "
                f"weakest dimension is '{weakest_dim}', "
                f"assign {sp.recommended_player_type.value}"
            )

        # General recommendations
        if red_projects:
            recommendations.append(
                "Focus sprint effort on RED sub-projects first; "
                "disconnection severity is critical."
            )

        p0_yellow = [sp for sp in yellow_projects if sp.priority == "P0"]
        if p0_yellow:
            recommendations.append(
                "P0 sub-projects in YELLOW state need immediate attention "
                "to prevent escalation to RED."
            )

        if not red_projects and not yellow_projects:
            recommendations.append(
                "All sub-projects are GREEN — consider this sprint for "
                "innovation and improvement rather than fixes."
            )

        return recommendations
