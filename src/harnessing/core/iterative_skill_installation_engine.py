from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import structlog

from .agentic_ai_capability_framework import AgenticAICapabilityFramework, BeeVerseStatus
from .beeverse_skill_gap_analyzer import BeeVerseSkillGapAnalyzer
from .beeverse_skill_installer import BeeVerseSkillInstaller

logger = structlog.get_logger()


@dataclass
class IterationResult:
    iteration: int
    coverage_before: float
    coverage_after: float
    skills_installed: list[str] = field(default_factory=list)
    skills_failed: list[str] = field(default_factory=list)
    gaps_remaining: int = 0
    converged: bool = False
    timestamp: str = ""


@dataclass
class EngineReport:
    total_iterations: int
    initial_coverage: float
    final_coverage: float
    total_skills_installed: int
    total_skills_failed: int
    coverage_improvement: float
    converged: bool
    convergence_reason: str
    iteration_history: list[IterationResult] = field(default_factory=list)
    timestamp: str = ""


class IterativeSkillInstallationEngine:
    def __init__(
        self,
        project_root: str = r"d:\My_Code_Projects\Harnessing",
        max_iterations: int = 100,
        convergence_window: int = 3,
    ) -> None:
        self._root = project_root
        self._max_iterations = max_iterations
        self._convergence_window = convergence_window
        self._gap_analyzer = BeeVerseSkillGapAnalyzer(project_root)
        self._installer = BeeVerseSkillInstaller(project_root)
        self._failed_cache: set[str] = set()
        self._current_iteration: int = 0
        self._current_coverage: float = 0.0

    def run(self) -> EngineReport:
        initial_report = self._gap_analyzer.analyze()
        initial_coverage = initial_report.overall_coverage
        self._current_coverage = initial_coverage
        self._current_iteration = 0

        history: list[IterationResult] = []

        for i in range(1, self._max_iterations + 1):
            result = self._run_single_iteration(i)
            history.append(result)
            self._current_iteration = i
            self._current_coverage = result.coverage_after

            if result.coverage_after >= 100.0:
                logger.info("coverage_reached_100", iteration=i, coverage=result.coverage_after)
                break

            converged, reason = self._check_convergence(history)
            if converged:
                result.converged = True
                logger.info("convergence_detected", iteration=i, reason=reason)
                break

        final_coverage = history[-1].coverage_after if history else initial_coverage
        total_installed = sum(len(r.skills_installed) for r in history)
        total_failed = sum(len(r.skills_failed) for r in history)

        report = EngineReport(
            total_iterations=len(history),
            initial_coverage=initial_coverage,
            final_coverage=final_coverage,
            total_skills_installed=total_installed,
            total_skills_failed=total_failed,
            coverage_improvement=round(final_coverage - initial_coverage, 2),
            converged=history[-1].converged if history else False,
            convergence_reason=self._get_convergence_reason(history),
            iteration_history=history,
            timestamp=datetime.now().isoformat(),
        )

        logger.info(
            "engine_complete",
            iterations=report.total_iterations,
            initial=report.initial_coverage,
            final=report.final_coverage,
            improvement=report.coverage_improvement,
        )

        return report

    def _run_single_iteration(self, iteration_num: int) -> IterationResult:
        gap_report = self._gap_analyzer.analyze()
        coverage_before = gap_report.overall_coverage

        gaps_to_fill = self._select_gaps_to_fill(gap_report)

        if not gaps_to_fill:
            return IterationResult(
                iteration=iteration_num,
                coverage_before=coverage_before,
                coverage_after=coverage_before,
                gaps_remaining=gap_report.missing_count,
                converged=True,
                timestamp=datetime.now().isoformat(),
            )

        install_results = self._installer.install_batch(gaps_to_fill, max_skills=len(gaps_to_fill))

        skills_installed: list[str] = []
        skills_failed: list[str] = []

        for r in install_results:
            if r.success:
                skills_installed.append(r.skill_name)
            else:
                skills_failed.append(r.skill_name)
                self._failed_cache.add(r.skill_name)

        self._gap_analyzer._mapping = None
        self._update_framework_status(skills_installed)
        new_gap_report = self._gap_analyzer.analyze()
        coverage_after = new_gap_report.overall_coverage

        return IterationResult(
            iteration=iteration_num,
            coverage_before=coverage_before,
            coverage_after=coverage_after,
            skills_installed=skills_installed,
            skills_failed=skills_failed,
            gaps_remaining=new_gap_report.missing_count,
            timestamp=datetime.now().isoformat(),
        )

    def _check_convergence(self, history: list[IterationResult]) -> tuple[bool, str]:
        if len(history) < self._convergence_window:
            return False, ""

        window = history[-self._convergence_window:]
        coverages = [r.coverage_after for r in window]
        all_same = all(c == coverages[0] for c in coverages)

        if all_same:
            return True, f"No coverage improvement in {self._convergence_window} iterations"

        no_new_skills = all(len(r.skills_installed) == 0 for r in window)
        if no_new_skills:
            return True, f"No new skills installed in {self._convergence_window} iterations"

        return False, ""

    def _select_gaps_to_fill(self, gap_report) -> list[str]:
        selected: list[str] = []

        for gap in gap_report.critical_gaps:
            name = gap["name"]
            if name not in self._failed_cache and len(selected) < 5:
                selected.append(name)

        for gap in gap_report.important_gaps:
            name = gap["name"]
            if name not in self._failed_cache and len(selected) < 5:
                selected.append(name)

        return selected

    def _get_convergence_reason(self, history: list[IterationResult]) -> str:
        if not history:
            return "no_iterations"
        last = history[-1]
        if last.coverage_after >= 100.0:
            return "coverage_100_percent"
        if last.converged:
            _, reason = self._check_convergence(history)
            return reason
        return "max_iterations_reached"

    def get_progress(self) -> dict:
        return {
            "iteration": self._current_iteration,
            "coverage": self._current_coverage,
            "failed_cache_size": len(self._failed_cache),
        }

    def _update_framework_status(self, installed_skills: list[str]) -> None:
        framework = self._gap_analyzer._framework
        all_caps = framework.get_all_capabilities()
        cap_name_map = {cap.name: cap for cap in all_caps}

        cap_snake_map: dict[str, str] = {}
        for cap in all_caps:
            cap_snake_map[self._normalize_name(cap.name)] = cap.name

        for skill_name in installed_skills:
            skill_snake = self._normalize_name(skill_name)
            skill_pascal = self._to_pascal_case(skill_name)

            matched = False

            if skill_name in cap_name_map:
                framework.update_status(skill_name, BeeVerseStatus.INSTALLED, skill_name)
                matched = True
            elif skill_snake in cap_snake_map:
                framework.update_status(cap_snake_map[skill_snake], BeeVerseStatus.INSTALLED, skill_name)
                matched = True
            else:
                for cap in all_caps:
                    cap_pascal = self._to_pascal_case(cap.name)
                    if cap_pascal.lower() == skill_pascal.lower():
                        framework.update_status(cap.name, BeeVerseStatus.INSTALLED, skill_name)
                        matched = True
                        break

            if not matched:
                for cap in all_caps:
                    if cap.beeverse_status == BeeVerseStatus.MISSING:
                        cap_snake = self._normalize_name(cap.name)
                        from difflib import SequenceMatcher
                        score = SequenceMatcher(None, cap_snake, skill_snake).ratio()
                        if score >= 0.45:
                            framework.update_status(cap.name, BeeVerseStatus.INSTALLED, skill_name)
                            matched = True
                            break

            if matched:
                logger.info("framework_status_updated", skill=skill_name)

    @staticmethod
    def _normalize_name(name: str) -> str:
        s1 = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
        s2 = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", s1)
        return re.sub(r"[-\s]+", "_", s2).lower()

    @staticmethod
    def _to_pascal_case(name: str) -> str:
        return "".join(part.capitalize() for part in re.split(r"[_\s]+", name))
