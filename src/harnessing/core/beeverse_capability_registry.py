from __future__ import annotations

import ast
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Optional

import structlog

logger = structlog.get_logger()

try:
    import yaml

    _YAML_AVAILABLE = True
except ImportError:
    _YAML_AVAILABLE = False


@dataclass
class CapabilityEntry:
    name: str
    category: str
    source_file: str
    description: str
    coverage_dimensions: list[str] = field(default_factory=list)
    installed_at: str = field(default_factory=lambda: datetime.now().isoformat())


class BeeVerseCapabilityRegistry:
    def __init__(self, project_root: str = r"d:\My_Code_Projects\Harnessing") -> None:
        self._root = Path(project_root)
        self._capabilities: dict[str, CapabilityEntry] = {}
        self._scan_all()

    def _scan_all(self) -> None:
        self._scan_core_modules()
        self._scan_modelfile()
        self._scan_error_rules()
        self._scan_knowledge_base()
        self._scan_skill_md()

    def _scan_core_modules(self) -> None:
        core_dir = self._root / "src" / "harnessing" / "core"
        if not core_dir.is_dir():
            logger.warning("core_dir_not_found", path=str(core_dir))
            return

        for fname in os.listdir(core_dir):
            if not fname.endswith(".py") or fname.startswith("_"):
                continue

            fpath = core_dir / fname
            try:
                source = fpath.read_text(encoding="utf-8")
                tree = ast.parse(source)
            except (SyntaxError, UnicodeDecodeError, OSError):
                logger.warning("parse_failed", file=str(fpath))
                continue

            for node in ast.walk(tree):
                if not isinstance(node, ast.ClassDef):
                    continue
                if node.name.startswith("_"):
                    continue

                docstring = ast.get_docstring(node) or ""
                self._register_capability(
                    name=node.name,
                    category="skill",
                    source_file=str(fpath),
                    description=docstring.split("\n")[0] if docstring else "",
                )

    def _scan_modelfile(self) -> None:
        mf_path = self._root / "config" / "Modelfile.full"
        if not mf_path.is_file():
            logger.warning("modelfile_not_found", path=str(mf_path))
            return

        try:
            content = mf_path.read_text(encoding="utf-8")
        except OSError:
            logger.warning("modelfile_read_failed", path=str(mf_path))
            return

        section_patterns: list[tuple[str, str]] = [
            (r"=== ALL INVENTIONS.*?===\n(.*?)(?==== )", "invention"),
            (r"=== ALL SKILLS.*?===\n(.*?)(?==== )", "skill"),
            (r"=== KEY RULES.*?===\n(.*?)(?==== )", "rule"),
            (r"=== ALL ERROR LESSONS.*?===\n(.*?)(?==== )", "rule"),
        ]

        for pattern, category in section_patterns:
            match = re.search(pattern, content, re.DOTALL)
            if not match:
                continue
            section_text = match.group(1)
            for line in section_text.splitlines():
                line = line.strip()
                if not line or line.startswith("---"):
                    continue
                item_match = re.match(r"^(?:\d+\.|S\d+\.|R\d+\.|R-ERR-)\s*(.+?)(?:\s*[-—]\s*(.+))?$", line)
                if item_match:
                    name = item_match.group(1).strip()
                    desc = item_match.group(2).strip() if item_match.group(2) else ""
                    self._register_capability(
                        name=name,
                        category=category,
                        source_file=str(mf_path),
                        description=desc,
                    )

    def _scan_error_rules(self) -> None:
        er_path = self._root / "data" / "error-rules.yaml"
        if not er_path.is_file():
            logger.warning("error_rules_not_found", path=str(er_path))
            return

        if not _YAML_AVAILABLE:
            self._scan_error_rules_fallback(er_path)
            return

        try:
            content = er_path.read_text(encoding="utf-8")
            data = yaml.safe_load(content)
        except (OSError, yaml.YAMLError):
            logger.warning("error_rules_parse_failed", path=str(er_path))
            return

        if not isinstance(data, dict) or "rules" not in data:
            return

        for rule in data["rules"]:
            if not isinstance(rule, dict):
                continue
            rule_id = rule.get("id", "")
            if not rule_id:
                continue
            self._register_capability(
                name=rule_id,
                category="rule",
                source_file=str(er_path),
                description=rule.get("rule", ""),
            )

    def _scan_error_rules_fallback(self, er_path: Path) -> None:
        try:
            content = er_path.read_text(encoding="utf-8")
        except OSError:
            return

        for match in re.finditer(r'-\s*id:\s*["\']?(R-ERR-\d+)["\']?', content):
            rule_id = match.group(1)
            desc_match = re.search(
                rf'-\s*id:\s*["\']?{re.escape(rule_id)}["\']?.*?rule:\s*"([^"]*)"',
                content,
                re.DOTALL,
            )
            desc = desc_match.group(1) if desc_match else ""
            self._register_capability(
                name=rule_id,
                category="rule",
                source_file=str(er_path),
                description=desc,
            )

    def _scan_knowledge_base(self) -> None:
        kb_dir = self._root / "docs" / "knowledge-base"
        if not kb_dir.is_dir():
            logger.warning("kb_dir_not_found", path=str(kb_dir))
            return

        for fname in os.listdir(kb_dir):
            if not fname.endswith(".md"):
                continue

            fpath = kb_dir / fname
            try:
                first_lines = fpath.read_text(encoding="utf-8")[:200]
            except OSError:
                first_lines = ""

            title = fname.replace(".md", "")
            title_match = re.search(r"^#\s+(.+)$", first_lines, re.MULTILINE)
            if title_match:
                title = title_match.group(1).strip()

            self._register_capability(
                name=title,
                category="knowledge",
                source_file=str(fpath),
                description=first_lines.split("\n")[0][:120] if first_lines else "",
            )

    def _scan_skill_md(self) -> None:
        skill_path = self._root / "skills" / "emoglyphplay" / "SKILL.md"
        if not skill_path.is_file():
            logger.warning("skill_md_not_found", path=str(skill_path))
            return

        try:
            content = skill_path.read_text(encoding="utf-8")
        except OSError:
            logger.warning("skill_md_read_failed", path=str(skill_path))
            return

        for match in re.finditer(r"^##\s*規則\s*(\d+)\s*[：:]\s*(.+)$", content, re.MULTILINE):
            rule_num = match.group(1)
            rule_title = match.group(2).strip()
            self._register_capability(
                name=f"Rule-{rule_num}",
                category="rule",
                source_file=str(skill_path),
                description=rule_title,
            )

    def _register_capability(
        self,
        name: str,
        category: str,
        source_file: str,
        description: str,
        coverage_dimensions: list[str] | None = None,
    ) -> None:
        if name in self._capabilities:
            return
        self._capabilities[name] = CapabilityEntry(
            name=name,
            category=category,
            source_file=source_file,
            description=description,
            coverage_dimensions=coverage_dimensions or [],
        )

    def get_all_capabilities(self) -> list[CapabilityEntry]:
        return list(self._capabilities.values())

    def get_by_category(self, category: str) -> list[CapabilityEntry]:
        return [e for e in self._capabilities.values() if e.category == category]

    def get_by_name(self, name: str) -> Optional[CapabilityEntry]:
        return self._capabilities.get(name)

    def has_capability(self, name: str) -> bool:
        return name in self._capabilities

    def register(self, entry: CapabilityEntry) -> None:
        self._capabilities[entry.name] = entry

    def unregister(self, name: str) -> None:
        self._capabilities.pop(name, None)

    def get_statistics(self) -> dict:
        counts: dict[str, int] = {}
        for entry in self._capabilities.values():
            counts[entry.category] = counts.get(entry.category, 0) + 1
        return {
            "total": len(self._capabilities),
            "by_category": counts,
            "categories": list(counts.keys()),
        }

    def search(self, keyword: str) -> list[CapabilityEntry]:
        keyword_lower = keyword.lower()
        scored: list[tuple[float, CapabilityEntry]] = []
        for entry in self._capabilities.values():
            name_ratio = SequenceMatcher(None, keyword_lower, entry.name.lower()).ratio()
            desc_ratio = SequenceMatcher(None, keyword_lower, entry.description.lower()).ratio()
            best = max(name_ratio, desc_ratio)
            if keyword_lower in entry.name.lower() or keyword_lower in entry.description.lower():
                best = max(best, 0.6)
            if best >= 0.3:
                scored.append((best, entry))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [entry for _, entry in scored]
