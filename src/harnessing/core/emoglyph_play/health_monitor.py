"""
Sub-Project Health Monitor — EmoGlyph Play

Monitors 5 sub-projects across 4 dimensions:
  - Engine: Python modules, core logic
  - Interface: UI files, app entry points
  - Deployment: Config files, Docker, CI/CD
  - Testing: Test files, coverage

Classification: GREEN (≥70), YELLOW (40-69), RED (<40)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class HealthDimension(Enum):
    """Four health dimensions for sub-project monitoring."""

    ENGINE = "engine"
    INTERFACE = "interface"
    DEPLOYMENT = "deployment"
    TESTING = "testing"


def _classify(score: float) -> str:
    if score >= 70:
        return "GREEN"
    if score >= 40:
        return "YELLOW"
    return "RED"


@dataclass
class HealthScore:
    """Score for a single health dimension."""

    dimension: HealthDimension
    score: float  # 0-100
    status: str = ""  # GREEN / YELLOW / RED — computed in __post_init__
    details: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.score = max(0.0, min(100.0, self.score))
        self.status = _classify(self.score)


@dataclass
class ProjectHealthReport:
    """Aggregated health report for one sub-project."""

    project_name: str
    project_path: str
    scores: dict[HealthDimension, HealthScore]
    overall_score: float
    overall_status: str
    disconnection_severity: float  # 0-1, inverse of overall_score/100
    issues: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


# ── Sub-project registry ────────────────────────────────────────────

_PROJECT_ROOT = Path(r"d:\My_Code_Projects\Harnessing")

SUB_PROJECTS: dict[str, str] = {
    "World Cup 2026": str(_PROJECT_ROOT / "projects" / "world-2026-deploy"),
    "Auditing SME": str(_PROJECT_ROOT / "projects" / "efficiency" / "audit-platform"),
    "Social Media": str(_PROJECT_ROOT / "projects" / "ai-content-creator"),
    "Business Proposal": str(_PROJECT_ROOT / "projects" / "business-case-proposal"),
    "Auto Jobs": str(_PROJECT_ROOT / "projects" / "automation"),
}


# ── Scoring helpers ─────────────────────────────────────────────────

def _has_any(path: Path, *names: str) -> bool:
    return any((path / n).exists() for n in names)


def _has_glob(path: Path, pattern: str) -> bool:
    return bool(list(path.glob(pattern)))


def _has_glob_recursive(path: Path, pattern: str) -> bool:
    return bool(list(path.rglob(pattern)))


def _check_engine(p: Path) -> HealthScore:
    score = 0.0
    details: list[str] = []

    if p.exists():
        score += 20
        details.append("Project path exists (+20)")
    else:
        details.append("Project path missing (0)")

    if (p / "src").exists() or _has_glob(p, "*.py"):
        score += 30
        details.append("Has src/ or .py files (+30)")
    else:
        details.append("No src/ or .py files (0)")

    if _has_glob_recursive(p, "__init__.py"):
        score += 20
        details.append("Has __init__.py (+20)")
    else:
        details.append("No __init__.py (0)")

    if _has_any(p, "requirements.txt", "pyproject.toml"):
        score += 15
        details.append("Has requirements.txt or pyproject.toml (+15)")
    else:
        details.append("No requirements.txt or pyproject.toml (0)")

    if _has_any(p, "AGENTS.md"):
        score += 15
        details.append("Has AGENTS.md (+15)")
    else:
        details.append("No AGENTS.md (0)")

    return HealthScore(dimension=HealthDimension.ENGINE, score=score, details=details)


def _check_interface(p: Path) -> HealthScore:
    score = 0.0
    details: list[str] = []

    if _has_any(p, "app.py", "streamlit_app.py"):
        score += 30
        details.append("Has app.py or streamlit_app.py (+30)")
    else:
        details.append("No app.py or streamlit_app.py (0)")

    if _has_any(p, "pages", "templates"):
        score += 25
        details.append("Has pages/ or templates/ (+25)")
    else:
        details.append("No pages/ or templates/ (0)")

    if _has_any(p, "config.py", "config"):
        score += 20
        details.append("Has config.py or config/ (+20)")
    else:
        details.append("No config.py or config/ (0)")

    if _has_glob_recursive(p, "*.html") or _has_glob_recursive(p, "*.tsx"):
        score += 25
        details.append("Has .html or .tsx files (+25)")
    else:
        details.append("No .html or .tsx files (0)")

    return HealthScore(dimension=HealthDimension.INTERFACE, score=score, details=details)


def _check_deployment(p: Path) -> HealthScore:
    score = 0.0
    details: list[str] = []

    if _has_any(p, "Dockerfile", "docker-compose.yml"):
        score += 30
        details.append("Has Dockerfile or docker-compose.yml (+30)")
    else:
        details.append("No Dockerfile or docker-compose.yml (0)")

    if _has_any(p, "Procfile", "render.yaml"):
        score += 25
        details.append("Has Procfile or render.yaml (+25)")
    else:
        details.append("No Procfile or render.yaml (0)")

    if _has_any(p, ".env.example"):
        score += 20
        details.append("Has .env.example (+20)")
    else:
        details.append("No .env.example (0)")

    readme = p / "README.md"
    if readme.exists():
        try:
            text = readme.read_text(encoding="utf-8", errors="ignore").lower()
            if any(kw in text for kw in ("deploy", "docker", "installation", "setup")):
                score += 25
                details.append("README has deploy instructions (+25)")
            else:
                details.append("README exists but no deploy instructions (0)")
        except Exception:
            details.append("README unreadable (0)")
    else:
        details.append("No README.md (0)")

    return HealthScore(dimension=HealthDimension.DEPLOYMENT, score=score, details=details)


def _check_testing(p: Path) -> HealthScore:
    score = 0.0
    details: list[str] = []

    if (p / "tests").exists() or _has_glob(p, "test_*.py"):
        score += 35
        details.append("Has tests/ or test_*.py (+35)")
    else:
        details.append("No tests/ or test_*.py (0)")

    if _has_any(p, "pytest.ini"):
        score += 25
        details.append("Has pytest.ini (+25)")
    else:
        pyproject = p / "pyproject.toml"
        if pyproject.exists():
            try:
                text = pyproject.read_text(encoding="utf-8", errors="ignore").lower()
                if "pytest" in text or "[tool.pytest" in text:
                    score += 25
                    details.append("pyproject.toml has pytest config (+25)")
                else:
                    details.append("pyproject.toml exists but no pytest config (0)")
            except Exception:
                details.append("pyproject.toml unreadable (0)")
        else:
            details.append("No pytest.ini or pyproject.toml test config (0)")

    if _has_glob_recursive(p, "*_test.py") or _has_glob_recursive(p, "test_*.py"):
        score += 20
        details.append("Has *_test.py or test_*.py files (+20)")
    else:
        details.append("No *_test.py or test_*.py files (0)")

    if _has_glob_recursive(p, "*smoke_test*") or _has_glob_recursive(p, "*e2e_test*"):
        score += 20
        details.append("Has smoke_test or e2e_test (+20)")
    else:
        details.append("No smoke_test or e2e_test (0)")

    return HealthScore(dimension=HealthDimension.TESTING, score=score, details=details)


_CHECKERS = {
    HealthDimension.ENGINE: _check_engine,
    HealthDimension.INTERFACE: _check_interface,
    HealthDimension.DEPLOYMENT: _check_deployment,
    HealthDimension.TESTING: _check_testing,
}


class HealthMonitor:
    """Monitors sub-project health across four dimensions."""

    def __init__(self, projects: dict[str, str] | None = None) -> None:
        self.projects = projects if projects is not None else dict(SUB_PROJECTS)

    @classmethod
    def from_env(cls, project_root: str | Path | None = None) -> HealthMonitor:
        """Create a HealthMonitor with a custom project root."""
        root = Path(project_root) if project_root else _PROJECT_ROOT
        projects = {
            "World Cup 2026": str(root / "projects" / "world-2026-deploy"),
            "Auditing SME": str(root / "projects" / "efficiency" / "audit-platform"),
            "Social Media": str(root / "projects" / "ai-content-creator"),
            "Business Proposal": str(root / "projects" / "business-case-proposal"),
            "Auto Jobs": str(root / "projects" / "automation"),
        }
        return cls(projects=projects)

    def check_project(self, project_name: str, project_path: str) -> ProjectHealthReport:
        """Check a single project and return its health report."""
        p = Path(project_path)
        scores: dict[HealthDimension, HealthScore] = {}

        for dim, checker in _CHECKERS.items():
            scores[dim] = checker(p)

        overall = sum(s.score for s in scores.values()) / len(scores)
        overall_status = _classify(overall)
        severity = round(1.0 - overall / 100.0, 4)

        issues: list[str] = []
        recommendations: list[str] = []
        for dim_score in scores.values():
            if dim_score.status == "RED":
                issues.append(f"{dim_score.dimension.value}: score {dim_score.score:.0f}")
                recommendations.append(
                    f"Improve {dim_score.dimension.value} — critical gaps detected"
                )
            elif dim_score.status == "YELLOW":
                recommendations.append(
                    f"Strengthen {dim_score.dimension.value} — some gaps remain"
                )

        return ProjectHealthReport(
            project_name=project_name,
            project_path=project_path,
            scores=scores,
            overall_score=round(overall, 2),
            overall_status=overall_status,
            disconnection_severity=severity,
            issues=issues,
            recommendations=recommendations,
        )

    def check_all(self) -> list[ProjectHealthReport]:
        """Check all registered sub-projects."""
        return [
            self.check_project(name, path) for name, path in self.projects.items()
        ]

    @staticmethod
    def rank_by_severity(reports: list[ProjectHealthReport]) -> list[ProjectHealthReport]:
        """Sort reports by disconnection severity (highest first)."""
        return sorted(reports, key=lambda r: r.disconnection_severity, reverse=True)

    @staticmethod
    def generate_summary(reports: list[ProjectHealthReport]) -> dict:
        """Produce a summary dict with totals and averages."""
        if not reports:
            return {"total": 0, "average_score": 0.0, "by_status": {}, "most_severe": None}

        total = len(reports)
        avg_score = round(sum(r.overall_score for r in reports) / total, 2)
        avg_severity = round(sum(r.disconnection_severity for r in reports) / total, 4)

        by_status: dict[str, int] = {"GREEN": 0, "YELLOW": 0, "RED": 0}
        for r in reports:
            by_status[r.overall_status] = by_status.get(r.overall_status, 0) + 1

        dimension_avgs: dict[str, float] = {}
        for dim in HealthDimension:
            vals = [r.scores[dim].score for r in reports if dim in r.scores]
            dimension_avgs[dim.value] = round(sum(vals) / len(vals), 2) if vals else 0.0

        most_severe = max(reports, key=lambda r: r.disconnection_severity)

        return {
            "total": total,
            "average_score": avg_score,
            "average_severity": avg_severity,
            "by_status": by_status,
            "dimension_averages": dimension_avgs,
            "most_severe": most_severe.project_name,
        }
