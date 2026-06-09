from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

import structlog
import yaml

logger = structlog.get_logger()

_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
_SKILL_MD_PATH = _PROJECT_ROOT / "skills" / "emoglyphplay" / "SKILL.md"
_PROJECT_RULES_PATH = _PROJECT_ROOT / ".trae" / "rules" / "project_rules.md"
_ERROR_RULES_PATH = _PROJECT_ROOT / "data" / "error-rules.yaml"
_AGENTS_MD_PATH = _PROJECT_ROOT / "AGENTS.md"
_MODELFILE_PATH = _PROJECT_ROOT / "config" / "Modelfile"
_MODELFILE_FULL_PATH = _PROJECT_ROOT / "config" / "Modelfile.full"

_RULE_NUM_PATTERN = re.compile(r"##\s*規則\s*(\d+)[：:]", re.IGNORECASE)
_RULE_LINE_PATTERN = re.compile(r"^##\s*(?:Rule\s*)?(\d+)[.:\s]", re.IGNORECASE | re.MULTILINE)
_MODELFILE_RULE_PATTERN = re.compile(r"^R(\d+)\.", re.MULTILINE)
_CM_RULE_PATTERN = re.compile(r"CM-(\d+)")
_INV_RULE_PATTERN = re.compile(r"INV-(\d+)")
_SCI_PATTERN = re.compile(r"SCI-(\d+)")
_EWF_PATTERN = re.compile(r"EWF-(\d+)")
_ERROR_RULE_ID_PATTERN = re.compile(r"R-ERR-(\w+)")
_HEADING_PATTERN = re.compile(r"^#+\s+(.+)$", re.MULTILINE)


class Severity(Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class ConsistencyGap:
    severity: Severity
    description: str
    source_file: str
    target_file: str
    suggested_fix: str
    gap_type: str = ""
    details: dict[str, Any] = field(default_factory=dict)


class ProactiveConsistencyScanner:
    def __init__(
        self,
        project_root: Path | None = None,
    ) -> None:
        self.project_root = project_root or _PROJECT_ROOT
        self.skill_md_path = self.project_root / "skills" / "emoglyphplay" / "SKILL.md"
        self.project_rules_path = self.project_root / ".trae" / "rules" / "project_rules.md"
        self.error_rules_path = self.project_root / "data" / "error-rules.yaml"
        self.agents_md_path = self.project_root / "AGENTS.md"
        self.modelfile_path = self.project_root / "config" / "Modelfile"
        self.modelfile_full_path = self.project_root / "config" / "Modelfile.full"

    def _read_file(self, path: Path) -> str:
        if not path.exists():
            logger.warning("file_not_found", path=str(path))
            return ""
        return path.read_text(encoding="utf-8", errors="replace")

    def _extract_rule_numbers(self, content: str) -> set[int]:
        numbers: set[int] = set()
        for m in _RULE_NUM_PATTERN.finditer(content):
            try:
                numbers.add(int(m.group(1)))
            except ValueError:
                pass
        for m in _RULE_LINE_PATTERN.finditer(content):
            try:
                numbers.add(int(m.group(1)))
            except ValueError:
                pass
        for m in _MODELFILE_RULE_PATTERN.finditer(content):
            try:
                numbers.add(int(m.group(1)))
            except ValueError:
                pass
        return numbers

    def _extract_cm_numbers(self, content: str) -> set[int]:
        return {int(m.group(1)) for m in _CM_RULE_PATTERN.finditer(content)}

    def _extract_inv_numbers(self, content: str) -> set[int]:
        return {int(m.group(1)) for m in _INV_RULE_PATTERN.finditer(content)}

    def _extract_sci_ids(self, content: str) -> set[str]:
        return {f"SCI-{m.group(1)}" for m in _SCI_PATTERN.finditer(content)}

    def _extract_ewf_ids(self, content: str) -> set[str]:
        return {f"EWF-{m.group(1)}" for m in _EWF_PATTERN.finditer(content)}

    def _extract_error_rule_ids(self, content: str) -> set[str]:
        return {f"R-ERR-{m.group(1)}" for m in _ERROR_RULE_ID_PATTERN.finditer(content)}

    def _extract_error_rule_count_from_yaml(self) -> tuple[int, set[str]]:
        content = self._read_file(self.error_rules_path)
        if not content:
            return 0, set()
        try:
            data = yaml.safe_load(content)
        except yaml.YAMLError:
            logger.error("yaml_parse_error", path=str(self.error_rules_path))
            return 0, set()
        rules = data.get("rules", []) if isinstance(data, dict) else []
        ids: set[str] = set()
        for rule in rules:
            if isinstance(rule, dict) and "id" in rule:
                ids.add(str(rule["id"]))
        return len(rules), ids

    def _check_rule_number_gaps(self) -> list[ConsistencyGap]:
        gaps: list[ConsistencyGap] = []
        rules_content = self._read_file(self.project_rules_path)
        skill_content = self._read_file(self.skill_md_path)
        if not rules_content or not skill_content:
            return gaps

        rules_nums = self._extract_rule_numbers(rules_content)
        skill_nums = self._extract_rule_numbers(skill_content)

        missing_in_skill = rules_nums - skill_nums
        for num in sorted(missing_in_skill):
            gaps.append(
                ConsistencyGap(
                    severity=Severity.HIGH,
                    description=f"Rule {num} exists in project_rules.md but missing from SKILL.md",
                    source_file=str(self.project_rules_path.relative_to(self.project_root)),
                    target_file=str(self.skill_md_path.relative_to(self.project_root)),
                    suggested_fix=f"Add Rule {num} to SKILL.md",
                    gap_type="rule_gap",
                    details={"rule_number": num},
                )
            )

        rules_cm = self._extract_cm_numbers(rules_content)
        skill_cm = self._extract_cm_numbers(skill_content)
        missing_cm = rules_cm - skill_cm
        for num in sorted(missing_cm):
            gaps.append(
                ConsistencyGap(
                    severity=Severity.HIGH,
                    description=f"CM-{num} exists in project_rules.md but missing from SKILL.md",
                    source_file=str(self.project_rules_path.relative_to(self.project_root)),
                    target_file=str(self.skill_md_path.relative_to(self.project_root)),
                    suggested_fix=f"Add CM-{num} to SKILL.md",
                    gap_type="cm_rule_gap",
                    details={"rule_number": f"CM-{num}"},
                )
            )

        rules_inv = self._extract_inv_numbers(rules_content)
        skill_inv = self._extract_inv_numbers(skill_content)
        missing_inv = rules_inv - skill_inv
        for num in sorted(missing_inv):
            gaps.append(
                ConsistencyGap(
                    severity=Severity.MEDIUM,
                    description=f"INV-{num:03d} exists in project_rules.md but missing from SKILL.md",
                    source_file=str(self.project_rules_path.relative_to(self.project_root)),
                    target_file=str(self.skill_md_path.relative_to(self.project_root)),
                    suggested_fix=f"Add INV-{num:03d} to SKILL.md",
                    gap_type="inv_rule_gap",
                    details={"rule_number": f"INV-{num:03d}"},
                )
            )

        return gaps

    def _check_engine_descriptions(self) -> list[ConsistencyGap]:
        gaps: list[ConsistencyGap] = []
        agents_content = self._read_file(self.agents_md_path)
        skill_content = self._read_file(self.skill_md_path)
        if not agents_content or not skill_content:
            return gaps

        agents_sci = self._extract_sci_ids(agents_content)
        agents_ewf = self._extract_ewf_ids(agents_content)
        skill_sci = self._extract_sci_ids(skill_content)
        skill_ewf = self._extract_ewf_ids(skill_content)

        missing_sci = agents_sci - skill_sci
        for sid in sorted(missing_sci):
            gaps.append(
                ConsistencyGap(
                    severity=Severity.MEDIUM,
                    description=f"{sid} engine exists in AGENTS.md but missing from SKILL.md",
                    source_file=str(self.agents_md_path.relative_to(self.project_root)),
                    target_file=str(self.skill_md_path.relative_to(self.project_root)),
                    suggested_fix=f"Add {sid} engine description to SKILL.md",
                    gap_type="engine_gap",
                    details={"engine_id": sid},
                )
            )

        missing_ewf = agents_ewf - skill_ewf
        for eid in sorted(missing_ewf):
            gaps.append(
                ConsistencyGap(
                    severity=Severity.MEDIUM,
                    description=f"{eid} engine exists in AGENTS.md but missing from SKILL.md",
                    source_file=str(self.agents_md_path.relative_to(self.project_root)),
                    target_file=str(self.skill_md_path.relative_to(self.project_root)),
                    suggested_fix=f"Add {eid} engine description to SKILL.md",
                    gap_type="engine_gap",
                    details={"engine_id": eid},
                )
            )

        return gaps

    def _check_error_rules_mismatch(self) -> list[ConsistencyGap]:
        gaps: list[ConsistencyGap] = []
        skill_content = self._read_file(self.skill_md_path)
        if not skill_content:
            return gaps

        yaml_count, yaml_ids = self._extract_error_rule_count_from_yaml()
        skill_error_ids = self._extract_error_rule_ids(skill_content)

        ids_in_yaml_not_skill = yaml_ids - skill_error_ids
        for eid in sorted(ids_in_yaml_not_skill):
            gaps.append(
                ConsistencyGap(
                    severity=Severity.HIGH,
                    description=f"{eid} exists in error-rules.yaml but missing from SKILL.md",
                    source_file=str(self.error_rules_path.relative_to(self.project_root)),
                    target_file=str(self.skill_md_path.relative_to(self.project_root)),
                    suggested_fix=f"Add {eid} to SKILL.md error rules section",
                    gap_type="error_rule_gap",
                    details={"error_rule_id": eid},
                )
            )

        ids_in_skill_not_yaml = skill_error_ids - yaml_ids
        for eid in sorted(ids_in_skill_not_yaml):
            gaps.append(
                ConsistencyGap(
                    severity=Severity.MEDIUM,
                    description=f"{eid} exists in SKILL.md but missing from error-rules.yaml",
                    source_file=str(self.skill_md_path.relative_to(self.project_root)),
                    target_file=str(self.error_rules_path.relative_to(self.project_root)),
                    suggested_fix=f"Add {eid} to error-rules.yaml or remove from SKILL.md",
                    gap_type="error_rule_gap",
                    details={"error_rule_id": eid},
                )
            )

        return gaps

    def _check_rule_continuity(self) -> list[ConsistencyGap]:
        gaps: list[ConsistencyGap] = []
        rules_content = self._read_file(self.project_rules_path)
        if not rules_content:
            return gaps

        rule_nums = self._extract_rule_numbers(rules_content)
        if not rule_nums:
            return gaps

        min_num = min(rule_nums)
        max_num = max(rule_nums)
        expected = set(range(min_num, max_num + 1))
        missing = expected - rule_nums

        for num in sorted(missing):
            gaps.append(
                ConsistencyGap(
                    severity=Severity.LOW,
                    description=f"Rule {num} is missing — gap in numbering between {min_num} and {max_num}",
                    source_file=str(self.project_rules_path.relative_to(self.project_root)),
                    target_file=str(self.project_rules_path.relative_to(self.project_root)),
                    suggested_fix=f"Add Rule {num} or renumber subsequent rules",
                    gap_type="numbering_gap",
                    details={"missing_rule": num, "range": (min_num, max_num)},
                )
            )

        cm_nums = self._extract_cm_numbers(rules_content)
        if cm_nums:
            cm_min = min(cm_nums)
            cm_max = max(cm_nums)
            cm_expected = set(range(cm_min, cm_max + 1))
            cm_missing = cm_expected - cm_nums
            for num in sorted(cm_missing):
                gaps.append(
                    ConsistencyGap(
                        severity=Severity.LOW,
                        description=f"CM-{num} is missing — gap in CM numbering between {cm_min} and {cm_max}",
                        source_file=str(self.project_rules_path.relative_to(self.project_root)),
                        target_file=str(self.project_rules_path.relative_to(self.project_root)),
                        suggested_fix=f"Add CM-{num} or renumber subsequent CM rules",
                        gap_type="cm_numbering_gap",
                        details={"missing_rule": f"CM-{num}", "range": (cm_min, cm_max)},
                    )
                )

        return gaps

    def _check_modelfile_sync(self) -> list[ConsistencyGap]:
        gaps: list[ConsistencyGap] = []
        rules_content = self._read_file(self.project_rules_path)
        modelfile_content = self._read_file(self.modelfile_path)
        modelfile_full_content = self._read_file(self.modelfile_full_path)

        if not rules_content:
            return gaps

        rules_nums = self._extract_rule_numbers(rules_content)
        total_rules = len(rules_nums)

        for mf_path, mf_content in [
            (self.modelfile_path, modelfile_content),
            (self.modelfile_full_path, modelfile_full_content),
        ]:
            if not mf_content:
                continue
            mf_rule_nums = self._extract_rule_numbers(mf_content)
            mf_total = len(mf_rule_nums)
            if mf_total < total_rules * 0.5 and total_rules > 0:
                gaps.append(
                    ConsistencyGap(
                        severity=Severity.CRITICAL,
                        description=(
                            f"Modelfile has {mf_total} rules"
                            f" but project_rules.md has {total_rules} — severe sync gap"
                        ),
                        source_file=str(mf_path.relative_to(self.project_root)),
                        target_file=str(self.project_rules_path.relative_to(self.project_root)),
                        suggested_fix="Sync Modelfile with project_rules.md using sync_beeverse_modelfile.py",
                        gap_type="modelfile_sync",
                        details={"modelfile_rules": mf_total, "project_rules": total_rules},
                    )
                )
            elif mf_total < total_rules and total_rules > 0:
                gaps.append(
                    ConsistencyGap(
                        severity=Severity.HIGH,
                        description=(
                            f"Modelfile has {mf_total} rules"
                            f" but project_rules.md has {total_rules} — partial sync gap"
                        ),
                        source_file=str(mf_path.relative_to(self.project_root)),
                        target_file=str(self.project_rules_path.relative_to(self.project_root)),
                        suggested_fix="Sync Modelfile with project_rules.md",
                        gap_type="modelfile_sync",
                        details={"modelfile_rules": mf_total, "project_rules": total_rules},
                    )
                )

        return gaps

    def scan(self) -> list[ConsistencyGap]:
        all_gaps: list[ConsistencyGap] = []
        all_gaps.extend(self._check_rule_number_gaps())
        all_gaps.extend(self._check_engine_descriptions())
        all_gaps.extend(self._check_error_rules_mismatch())
        all_gaps.extend(self._check_rule_continuity())
        all_gaps.extend(self._check_modelfile_sync())

        severity_order = {
            Severity.CRITICAL: 0,
            Severity.HIGH: 1,
            Severity.MEDIUM: 2,
            Severity.LOW: 3,
        }
        all_gaps.sort(key=lambda g: severity_order.get(g.severity, 99))
        return all_gaps

    def generate_report(self) -> str:
        gaps = self.scan()
        now = datetime.now(timezone.utc).isoformat()

        severity_counts: dict[str, int] = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        type_counts: dict[str, int] = {}
        for g in gaps:
            severity_counts[g.severity.value] += 1
            type_counts[g.gap_type] = type_counts.get(g.gap_type, 0) + 1

        lines: list[str] = []
        lines.append("# Proactive Consistency Scan Report")
        lines.append("")
        lines.append(f"**Generated**: {now}")
        lines.append(f"**Project Root**: `{self.project_root}`")
        lines.append(f"**Total Gaps Found**: {len(gaps)}")
        lines.append("")

        lines.append("## Severity Summary")
        lines.append("")
        lines.append("| Severity | Count |")
        lines.append("|----------|-------|")
        for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
            lines.append(f"| {sev} | {severity_counts[sev]} |")
        lines.append("")

        if type_counts:
            lines.append("## Gap Type Summary")
            lines.append("")
            lines.append("| Gap Type | Count |")
            lines.append("|----------|-------|")
            for gt, count in sorted(type_counts.items(), key=lambda x: -x[1]):
                lines.append(f"| {gt} | {count} |")
            lines.append("")

        if not gaps:
            lines.append("## Result")
            lines.append("")
            lines.append("✅ No consistency gaps detected. All systems are in sync.")
            lines.append("")
            return "\n".join(lines)

        current_severity = ""
        for g in gaps:
            if g.severity.value != current_severity:
                current_severity = g.severity.value
                lines.append(f"## {current_severity}")
                lines.append("")

            lines.append(f"### {g.gap_type}: {g.description[:80]}")
            lines.append("")
            lines.append(f"- **Severity**: {g.severity.value}")
            lines.append(f"- **Source**: `{g.source_file}`")
            lines.append(f"- **Target**: `{g.target_file}`")
            lines.append(f"- **Suggested Fix**: {g.suggested_fix}")
            if g.details:
                lines.append(f"- **Details**: `{g.details}`")
            lines.append("")

        return "\n".join(lines)


def main() -> None:
    scanner = ProactiveConsistencyScanner()
    report = scanner.generate_report()
    print(report)

    gaps = scanner.scan()
    critical_count = sum(1 for g in gaps if g.severity == Severity.CRITICAL)
    high_count = sum(1 for g in gaps if g.severity == Severity.HIGH)

    if critical_count > 0:
        logger.error("critical_gaps_found", count=critical_count)
        sys.exit(2)
    elif high_count > 0:
        logger.warning("high_gaps_found", count=high_count)
        sys.exit(1)
    else:
        logger.info("scan_complete", total_gaps=len(gaps))
        sys.exit(0)


if __name__ == "__main__":
    main()
