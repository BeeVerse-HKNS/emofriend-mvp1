#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from harnessing.core.proactive_consistency_scanner import (
    ConsistencyGap,
    ProactiveConsistencyScanner,
)

_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
_SKILL_MD_PATH = _PROJECT_ROOT / "skills" / "harness-engine-copilot" / "SKILL.md"
_PROJECT_RULES_PATH = _PROJECT_ROOT / ".trae" / "rules" / "project_rules.md"
_MODELFILE_PATH = _PROJECT_ROOT / "config" / "Modelfile"
_MODELFILE_FULL_PATH = _PROJECT_ROOT / "config" / "Modelfile.full"

_RULE_NUM_PATTERN = re.compile(r"##\s*規則\s*(\d+)[：:]", re.IGNORECASE)
_RULE_LINE_PATTERN = re.compile(r"^##\s*(?:Rule\s*)?(\d+)[.:\s]", re.IGNORECASE | re.MULTILINE)
_CM_RULE_PATTERN = re.compile(r"CM-(\d+)")
_INV_RULE_PATTERN = re.compile(r"INV-(\d+)")


@dataclass
class HealingResult:
    gap: ConsistencyGap
    success: bool
    action_taken: str = ""
    error_message: str = ""


class SelfHealingSync:
    def __init__(self, project_root: Path | None = None) -> None:
        self.project_root = project_root or _PROJECT_ROOT
        self.skill_md_path = self.project_root / "skills" / "harness-engine-copilot" / "SKILL.md"
        self.project_rules_path = self.project_root / ".trae" / "rules" / "project_rules.md"
        self.modelfile_path = self.project_root / "config" / "Modelfile"
        self.modelfile_full_path = self.project_root / "config" / "Modelfile.full"

    def heal(self, gaps: list[ConsistencyGap]) -> list[HealingResult]:
        results: list[HealingResult] = []

        for gap in gaps:
            result = self._heal_single(gap)
            results.append(result)

        return results

    def heal_and_verify(self, gaps: list[ConsistencyGap]) -> dict[str, Any]:
        results = self.heal(gaps)

        scanner = ProactiveConsistencyScanner(project_root=self.project_root)
        remaining_gaps = scanner.scan()

        healed = [r for r in results if r.success]
        failed = [r for r in results if not r.success]

        still_present: list[ConsistencyGap] = []
        healed_descriptions = {r.gap.description for r in healed}
        for g in remaining_gaps:
            if g.description in healed_descriptions:
                still_present.append(g)

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_gaps": len(gaps),
            "healed": len(healed),
            "failed": len(failed),
            "still_present_after_verify": len(still_present),
            "results": results,
            "remaining_gaps": remaining_gaps,
        }

    def _heal_single(self, gap: ConsistencyGap) -> HealingResult:
        if gap.gap_type == "rule_gap":
            return self._sync_rule_to_skillmd(gap)
        if gap.gap_type in ("duplicate_lines", "duplicate_content"):
            return self._remove_duplicate_lines(gap)
        if gap.gap_type == "modelfile_sync":
            return self._update_modelfile(gap)

        return HealingResult(
            gap=gap,
            success=False,
            action_taken="skipped",
            error_message=f"No auto-heal handler for gap_type '{gap.gap_type}'",
        )

    def _sync_rule_to_skillmd(self, gap: ConsistencyGap) -> HealingResult:
        rule_number = gap.details.get("rule_number")
        if rule_number is None:
            return HealingResult(
                gap=gap,
                success=False,
                action_taken="skipped",
                error_message="Missing rule_number in gap details",
            )

        rules_content = self._read_file(self.project_rules_path)
        if not rules_content:
            return HealingResult(
                gap=gap,
                success=False,
                action_taken="read_failed",
                error_message=f"Cannot read {self.project_rules_path}",
            )

        rule_text = self._extract_rule_text(rules_content, rule_number)
        if not rule_text:
            return HealingResult(
                gap=gap,
                success=False,
                action_taken="extract_failed",
                error_message=f"Cannot extract Rule {rule_number} from project_rules.md",
            )

        skill_content = self._read_file(self.skill_md_path)
        if not skill_content:
            return HealingResult(
                gap=gap,
                success=False,
                action_taken="read_failed",
                error_message=f"Cannot read {self.skill_md_path}",
            )

        if rule_text.strip() in skill_content:
            return HealingResult(
                gap=gap,
                success=True,
                action_taken="already_present",
                error_message="",
            )

        try:
            append_text = f"\n\n{rule_text}\n"
            self._write_file(self.skill_md_path, skill_content + append_text)
            return HealingResult(
                gap=gap,
                success=True,
                action_taken=f"Appended Rule {rule_number} to SKILL.md",
                error_message="",
            )
        except Exception as e:
            return HealingResult(
                gap=gap,
                success=False,
                action_taken="write_failed",
                error_message=str(e),
            )

    def _remove_duplicate_lines(self, gap: ConsistencyGap) -> HealingResult:
        target_path = self.project_root / gap.target_file
        content = self._read_file(target_path)
        if not content:
            return HealingResult(
                gap=gap,
                success=False,
                action_taken="read_failed",
                error_message=f"Cannot read {target_path}",
            )

        original_lines = content.split("\n")
        seen: set[str] = set()
        deduplicated: list[str] = []
        removed_count = 0

        for line in original_lines:
            stripped = line.strip()
            if not stripped:
                deduplicated.append(line)
                continue
            if stripped in seen:
                removed_count += 1
                continue
            seen.add(stripped)
            deduplicated.append(line)

        if removed_count == 0:
            return HealingResult(
                gap=gap,
                success=True,
                action_taken="no_duplicates_found",
                error_message="",
            )

        try:
            self._write_file(target_path, "\n".join(deduplicated))
            return HealingResult(
                gap=gap,
                success=True,
                action_taken=f"Removed {removed_count} duplicate lines from {gap.target_file}",
                error_message="",
            )
        except Exception as e:
            return HealingResult(
                gap=gap,
                success=False,
                action_taken="write_failed",
                error_message=str(e),
            )

    def _update_modelfile(self, gap: ConsistencyGap) -> HealingResult:
        rules_content = self._read_file(self.project_rules_path)
        if not rules_content:
            return HealingResult(
                gap=gap,
                success=False,
                action_taken="read_failed",
                error_message=f"Cannot read {self.project_rules_path}",
            )

        rule_nums = self._extract_rule_numbers(rules_content)
        if not rule_nums:
            return HealingResult(
                gap=gap,
                success=False,
                action_taken="no_rules_found",
                error_message="No rules found in project_rules.md",
            )

        rules_summary = self._build_rules_summary(rules_content)

        target_path = self.modelfile_full_path
        mf_content = self._read_file(target_path)
        if not mf_content:
            mf_content = "FROM llama3.2\nSYSTEM \"\"\"\n\"\"\"\n"

        marker = "# === AUTO-SYNCED RULES START ==="
        end_marker = "# === AUTO-SYNCED RULES END ==="

        new_block = f"{marker}\n{rules_summary}\n{end_marker}"

        if marker in mf_content and end_marker in mf_content:
            start_idx = mf_content.index(marker)
            end_idx = mf_content.index(end_marker) + len(end_marker)
            updated = mf_content[:start_idx] + new_block + mf_content[end_idx:]
        else:
            updated = mf_content.rstrip() + "\n\n" + new_block + "\n"

        try:
            self._write_file(target_path, updated)
            return HealingResult(
                gap=gap,
                success=True,
                action_taken=f"Updated Modelfile with {len(rule_nums)} rules summary",
                error_message="",
            )
        except Exception as e:
            return HealingResult(
                gap=gap,
                success=False,
                action_taken="write_failed",
                error_message=str(e),
            )

    def _extract_rule_text(self, content: str, rule_number: Any) -> str:
        pattern = re.compile(
            rf"##\s*規則\s*{re.escape(str(rule_number))}[：:].*?(?=##\s*規則\s*\d+[：:]|$)",
            re.DOTALL | re.IGNORECASE,
        )
        match = pattern.search(content)
        if match:
            return match.group(0).rstrip()

        alt_pattern = re.compile(
            rf"^##\s*(?:Rule\s*)?{re.escape(str(rule_number))}[.:\s].*?(?=^##\s*(?:Rule\s*)?\d+[.:\s]|$)",
            re.DOTALL | re.MULTILINE | re.IGNORECASE,
        )
        match = alt_pattern.search(content)
        if match:
            return match.group(0).rstrip()

        return ""

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
        return numbers

    def _build_rules_summary(self, content: str) -> str:
        lines: list[str] = []
        lines.append(f"# Total Rules: {len(self._extract_rule_numbers(content))}")
        lines.append(f"# Synced: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
        lines.append("")

        headings = re.findall(r"^(#+\s+.+)$", content, re.MULTILINE)
        for h in headings[:50]:
            lines.append(h)

        return "\n".join(lines)

    def _read_file(self, path: Path) -> str:
        if not path.exists():
            return ""
        try:
            return path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return ""

    def _write_file(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def main() -> None:
    scanner = ProactiveConsistencyScanner(project_root=_PROJECT_ROOT)
    gaps = scanner.scan()

    print(f"Found {len(gaps)} consistency gaps")
    print("")

    healer = SelfHealingSync(project_root=_PROJECT_ROOT)
    report = healer.heal_and_verify(gaps)

    print(f"Healed: {report['healed']}")
    print(f"Failed: {report['failed']}")
    print(f"Still present after verify: {report['still_present_after_verify']}")
    print("")

    for r in report["results"]:
        status = "✅" if r.success else "❌"
        print(f"  {status} {r.gap.gap_type}: {r.action_taken or r.error_message}")

    print("")
    print(f"Remaining gaps after verify: {len(report['remaining_gaps'])}")

    if report["failed"] > 0 or report["still_present_after_verify"] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
