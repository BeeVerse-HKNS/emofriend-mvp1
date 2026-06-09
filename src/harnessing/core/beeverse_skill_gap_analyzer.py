from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path

import structlog

from .agentic_ai_capability_framework import (
    AgenticAICapabilityFramework,
    BeeVerseStatus,
    CapabilityDimension,
    RequiredLevel,
)
from .beeverse_capability_registry import BeeVerseCapabilityRegistry

logger = structlog.get_logger()

_FUZZY_THRESHOLD = 0.45

_DIMENSION_FORMULA_MAP: dict[str, str] = {
    CapabilityDimension.REASONING.value: "log(Reasoning) + Knowledge",
    CapabilityDimension.PLANNING.value: "Planning * Autonomy",
    CapabilityDimension.COLLABORATION.value: "Collaboration + Safety",
    CapabilityDimension.MULTI_MODAL.value: "(MultiModal ^ Adaptation)",
}


@dataclass
class GapReport:
    timestamp: str
    overall_coverage: float
    dimension_coverage: dict[str, float]
    total_capabilities: int
    installed_count: int
    partial_count: int
    missing_count: int
    critical_gaps: list = field(default_factory=list)
    important_gaps: list = field(default_factory=list)
    nice_to_have_gaps: list = field(default_factory=list)
    formula_suggestions: list[str] = field(default_factory=list)
    iteration: int = 0


class BeeVerseSkillGapAnalyzer:
    def __init__(self, project_root: str = r"d:\My_Code_Projects\Harnessing") -> None:
        self._root = project_root
        self._framework = AgenticAICapabilityFramework()
        self._registry = BeeVerseCapabilityRegistry(project_root)
        self._mapping: dict | None = None

    @staticmethod
    def _normalize_name(name: str) -> str:
        s1 = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
        s2 = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", s1)
        return re.sub(r"[-\s]+", "_", s2).lower()

    @staticmethod
    def _to_pascal_case(name: str) -> str:
        return "".join(part.capitalize() for part in re.split(r"[_\s]+", name))

    def analyze(self) -> GapReport:
        framework_caps = self._framework.get_all_capabilities()
        mapping = self._map_registry_to_framework()

        installed = 0
        partial = 0
        missing = 0
        critical_gaps: list[dict] = []
        important_gaps: list[dict] = []
        nice_to_have_gaps: list[dict] = []
        missing_caps: list[dict] = []

        for cap in framework_caps:
            match_info = mapping.get(cap.name)
            if match_info is not None:
                status = match_info["status"]
            else:
                status = cap.beeverse_status

            if status == BeeVerseStatus.INSTALLED:
                installed += 1
            elif status == BeeVerseStatus.PARTIAL:
                partial += 1
            else:
                missing += 1
                gap_entry = {
                    "name": cap.name,
                    "dimension": cap.dimension.value,
                    "description": cap.description,
                    "required_level": cap.required_level.value,
                }
                missing_caps.append(gap_entry)
                if cap.required_level == RequiredLevel.CRITICAL:
                    critical_gaps.append(gap_entry)
                elif cap.required_level == RequiredLevel.IMPORTANT:
                    important_gaps.append(gap_entry)
                else:
                    nice_to_have_gaps.append(gap_entry)

        total = len(framework_caps)
        overall = (installed + 0.5 * partial) / total * 100 if total > 0 else 0.0

        dim_coverage: dict[str, float] = {}
        for dim in CapabilityDimension:
            dim_coverage[dim.value] = self._calculate_dimension_coverage(dim)

        formula_suggestions = self._generate_formula_suggestions(missing_caps)

        return GapReport(
            timestamp=datetime.now().isoformat(),
            overall_coverage=round(overall, 2),
            dimension_coverage=dim_coverage,
            total_capabilities=total,
            installed_count=installed,
            partial_count=partial,
            missing_count=missing,
            critical_gaps=critical_gaps,
            important_gaps=important_gaps,
            nice_to_have_gaps=nice_to_have_gaps,
            formula_suggestions=formula_suggestions,
            iteration=0,
        )

    def _calculate_dimension_coverage(self, dimension_name: CapabilityDimension) -> float:
        caps = self._framework.get_capabilities_by_dimension(dimension_name)
        if not caps:
            return 0.0

        mapping = self._map_registry_to_framework()
        total_score = 0.0

        for cap in caps:
            match_info = mapping.get(cap.name)
            status = match_info["status"] if match_info else cap.beeverse_status

            if status == BeeVerseStatus.INSTALLED:
                total_score += 100.0
            elif status == BeeVerseStatus.PARTIAL:
                total_score += 50.0

        return round(total_score / len(caps), 2)

    def _generate_formula_suggestions(self, missing_capabilities: list[dict]) -> list[str]:
        suggestions: list[str] = []
        seen: set[str] = set()

        for cap in missing_capabilities:
            dim = cap["dimension"]
            name = cap["name"]

            formula = _DIMENSION_FORMULA_MAP.get(dim)
            if formula is None:
                formula = f"{dim.capitalize()} + Innovation"

            suggestion = f"{name}: {formula}"
            if suggestion not in seen:
                seen.add(suggestion)
                suggestions.append(suggestion)

        return suggestions

    def _map_registry_to_framework(self) -> dict:
        if self._mapping is not None:
            return self._mapping

        registry_caps = self._registry.get_all_capabilities()
        registry_names = [e.name for e in registry_caps]
        registry_name_set = {n.lower() for n in registry_names}

        registry_snake_map: dict[str, str] = {}
        for rn in registry_names:
            snake = self._normalize_name(rn)
            registry_snake_map[snake] = rn

        registry_pascal_map: dict[str, str] = {}
        for rn in registry_names:
            pascal = self._to_pascal_case(rn)
            registry_pascal_map[pascal.lower()] = rn

        framework_caps = self._framework.get_all_capabilities()
        mapping: dict[str, dict] = {}

        for cap in framework_caps:
            cap_lower = cap.name.lower()
            cap_snake = self._normalize_name(cap.name)
            cap_pascal = self._to_pascal_case(cap.name)

            if cap_lower in registry_name_set:
                mapping[cap.name] = {"status": BeeVerseStatus.INSTALLED, "match": cap.name}
                continue

            if cap_snake in registry_snake_map:
                mapping[cap.name] = {"status": BeeVerseStatus.INSTALLED, "match": registry_snake_map[cap_snake]}
                continue

            if cap_pascal.lower() in registry_pascal_map:
                mapping[cap.name] = {"status": BeeVerseStatus.INSTALLED, "match": registry_pascal_map[cap_pascal.lower()]}
                continue

            for rn in registry_names:
                rn_snake = self._normalize_name(rn)
                if rn_snake == cap_snake:
                    mapping[cap.name] = {"status": BeeVerseStatus.INSTALLED, "match": rn}
                    break
            else:
                for rn in registry_names:
                    rn_pascal = self._to_pascal_case(rn)
                    if rn_pascal.lower() == cap_pascal.lower():
                        mapping[cap.name] = {"status": BeeVerseStatus.INSTALLED, "match": rn}
                        break
                else:
                    best_score = 0.0
                    best_match = None
                    for reg_name in registry_names:
                        score = SequenceMatcher(None, cap_snake, self._normalize_name(reg_name)).ratio()
                        if score > best_score:
                            best_score = score
                            best_match = reg_name

                    if best_score >= _FUZZY_THRESHOLD and best_match:
                        mapping[cap.name] = {"status": BeeVerseStatus.INSTALLED, "match": best_match}
                    elif cap.beeverse_status == BeeVerseStatus.INSTALLED:
                        mapping[cap.name] = {"status": BeeVerseStatus.INSTALLED, "match": cap.beeverse_match or "framework_marked"}
                    elif cap.beeverse_status == BeeVerseStatus.PARTIAL:
                        mapping[cap.name] = {"status": BeeVerseStatus.PARTIAL, "match": cap.beeverse_match or "framework_marked"}
                    else:
                        mapping[cap.name] = None

        self._mapping = mapping
        return mapping

    def get_gap_summary(self) -> str:
        report = self.analyze()
        lines = [
            f"BeeVerse Skill Gap Analysis — {report.timestamp}",
            f"Overall Coverage: {report.overall_coverage:.2f}%",
            f"Total Capabilities: {report.total_capabilities}",
            f"  Installed: {report.installed_count}",
            f"  Partial:   {report.partial_count}",
            f"  Missing:   {report.missing_count}",
            "",
            "Dimension Coverage:",
        ]

        for dim, pct in sorted(report.dimension_coverage.items(), key=lambda x: x[1]):
            bar_len = int(pct / 5)
            bar = "█" * bar_len + "░" * (20 - bar_len)
            lines.append(f"  {dim:20s} {pct:6.2f}% {bar}")

        lines.append("")
        lines.append(f"Critical Gaps:   {len(report.critical_gaps)}")
        lines.append(f"Important Gaps:  {len(report.important_gaps)}")
        lines.append(f"Nice-to-Have:    {len(report.nice_to_have_gaps)}")

        if report.critical_gaps:
            lines.append("")
            lines.append("Top Critical Gaps:")
            for gap in report.critical_gaps[:10]:
                lines.append(f"  - {gap['name']} ({gap['dimension']})")

        if report.formula_suggestions:
            lines.append("")
            lines.append("Formula Suggestions (top 10):")
            for s in report.formula_suggestions[:10]:
                lines.append(f"  {s}")

        return "\n".join(lines)

    def export_report(self, filepath: str | Path) -> None:
        report = self.analyze()
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "timestamp": report.timestamp,
            "overall_coverage": report.overall_coverage,
            "dimension_coverage": report.dimension_coverage,
            "total_capabilities": report.total_capabilities,
            "installed_count": report.installed_count,
            "partial_count": report.partial_count,
            "missing_count": report.missing_count,
            "critical_gaps": report.critical_gaps,
            "important_gaps": report.important_gaps,
            "nice_to_have_gaps": report.nice_to_have_gaps,
            "formula_suggestions": report.formula_suggestions,
            "iteration": report.iteration,
        }

        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info("gap_report_exported", path=str(path))
