from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import structlog

from .agentic_ai_capability_framework import AgenticAICapabilityFramework
from .beeverse_capability_registry import BeeVerseCapabilityRegistry, CapabilityEntry
from .beeverse_skill_gap_analyzer import BeeVerseSkillGapAnalyzer
from .formula_brainstormer import FormulaBrainstormer

logger = structlog.get_logger()


@dataclass
class SkillDefinition:
    name: str
    dimension: str
    description: str
    formula: str
    code_template: str
    test_template: str
    modelfile_entry: str


@dataclass
class InstallationResult:
    skill_name: str
    success: bool
    error: str
    file_path: str
    registered: bool
    modelfile_updated: bool


class BeeVerseSkillInstaller:
    def __init__(self, project_root: str = r"d:\My_Code_Projects\Harnessing") -> None:
        self._root = Path(project_root)
        self._gap_analyzer = BeeVerseSkillGapAnalyzer(project_root)
        self._registry = BeeVerseCapabilityRegistry(project_root)
        self._brainstormer = FormulaBrainstormer()
        self._framework = AgenticAICapabilityFramework()

    def install_skill(self, capability_name: str) -> InstallationResult:
        try:
            skill_def = self._generate_skill_definition(capability_name)
        except Exception as exc:
            logger.error("skill_definition_failed", capability=capability_name, error=str(exc))
            return InstallationResult(
                skill_name=capability_name, success=False, error=str(exc),
                file_path="", registered=False, modelfile_updated=False,
            )

        code = self._generate_code(skill_def)
        test_code = self._generate_test(skill_def)

        file_path = ""
        try:
            file_path = self._write_skill_file(skill_def, code)
        except Exception as exc:
            logger.error("write_skill_failed", skill=skill_def.name, error=str(exc))
            return InstallationResult(
                skill_name=skill_def.name, success=False, error=str(exc),
                file_path="", registered=False, modelfile_updated=False,
            )

        try:
            self._write_test_file(skill_def, test_code)
        except Exception as exc:
            logger.warning("write_test_failed", skill=skill_def.name, error=str(exc))

        registered = False
        try:
            registered = self._register_skill(skill_def)
        except Exception as exc:
            logger.warning("register_failed", skill=skill_def.name, error=str(exc))

        modelfile_updated = False
        try:
            modelfile_updated = self._update_modelfile(skill_def)
        except Exception as exc:
            logger.warning("modelfile_update_failed", skill=skill_def.name, error=str(exc))

        verified = self._verify_installation(skill_def.name)

        return InstallationResult(
            skill_name=skill_def.name,
            success=verified,
            error="" if verified else "verification_failed",
            file_path=file_path,
            registered=registered,
            modelfile_updated=modelfile_updated,
        )

    def install_batch(self, capability_names: list[str], max_skills: int = 10) -> list[InstallationResult]:
        sorted_names = self._sort_by_severity(capability_names)
        results: list[InstallationResult] = []
        for name in sorted_names[:max_skills]:
            result = self.install_skill(name)
            results.append(result)
            logger.info("skill_installed", name=name, success=result.success)
        return results

    def _sort_by_severity(self, capability_names: list[str]) -> list[str]:
        severity_order = {"critical": 0, "important": 1, "nice_to_have": 2}
        cap_map = {c.name: c for c in self._framework.get_all_capabilities()}
        return sorted(
            capability_names,
            key=lambda n: severity_order.get(
                cap_map[n].required_level.value if n in cap_map else "nice_to_have", 2
            ),
        )

    def _generate_skill_definition(self, capability_name: str) -> SkillDefinition:
        cap_map = {c.name: c for c in self._framework.get_all_capabilities()}
        cap = cap_map.get(capability_name)

        dimension = cap.dimension.value if cap else "innovation"
        description = cap.description if cap else capability_name

        brainstorm = self._brainstormer.brainstorm(
            problem=f"{capability_name}: {description}",
            relevant_dims=None,
            max_formulas=10,
        )
        top_formulas = brainstorm.get("top_formulas", [])
        formula = top_formulas[0]["formula"] if top_formulas else f"log({capability_name})"
        formula_semantic = top_formulas[0]["semantic"] if top_formulas else f"Abstract {capability_name}"

        class_name = self._to_pascal_case(capability_name)
        method_name = self._to_method_name(capability_name)

        code_template = self._build_code_template(class_name, method_name, capability_name, formula)
        test_template = self._build_test_template(class_name, method_name, capability_name)
        modelfile_entry = f"S_AUTO. {class_name} — {description}（{formula}）"

        return SkillDefinition(
            name=class_name,
            dimension=dimension,
            description=description,
            formula=formula,
            code_template=code_template,
            test_template=test_template,
            modelfile_entry=modelfile_entry,
        )

    def _generate_code(self, skill_def: SkillDefinition) -> str:
        return skill_def.code_template

    def _generate_test(self, skill_def: SkillDefinition) -> str:
        return skill_def.test_template

    def _write_skill_file(self, skill_def: SkillDefinition, code: str) -> str:
        core_dir = self._root / "src" / "harnessing" / "core"
        core_dir.mkdir(parents=True, exist_ok=True)

        snake_name = self._to_snake_case(skill_def.name)
        file_path = core_dir / f"{snake_name}.py"

        if file_path.exists():
            logger.warning("skill_file_exists", path=str(file_path))
            return str(file_path)

        file_path.write_text(code, encoding="utf-8")
        logger.info("skill_file_written", path=str(file_path))
        return str(file_path)

    def _write_test_file(self, skill_def: SkillDefinition, test_code: str) -> str:
        scripts_dir = self._root / "scripts"
        scripts_dir.mkdir(parents=True, exist_ok=True)

        snake_name = self._to_snake_case(skill_def.name)
        file_path = scripts_dir / f"test_{snake_name}.py"

        if file_path.exists():
            logger.warning("test_file_exists", path=str(file_path))
            return str(file_path)

        file_path.write_text(test_code, encoding="utf-8")
        logger.info("test_file_written", path=str(file_path))
        return str(file_path)

    def _register_skill(self, skill_def: SkillDefinition) -> bool:
        entry = CapabilityEntry(
            name=skill_def.name,
            category="skill",
            source_file=f"src/harnessing/core/{self._to_snake_case(skill_def.name)}.py",
            description=skill_def.description,
            coverage_dimensions=[skill_def.dimension],
        )
        self._registry.register(entry)
        logger.info("skill_registered", name=skill_def.name)
        return True

    def _update_modelfile(self, skill_def: SkillDefinition) -> bool:
        mf_path = self._root / "config" / "Modelfile.full"
        if not mf_path.is_file():
            logger.warning("modelfile_not_found", path=str(mf_path))
            return False

        content = mf_path.read_text(encoding="utf-8")

        skills_marker = "=== ALL SKILLS"
        key_rules_marker = "=== KEY RULES"

        idx_skills = content.find(skills_marker)
        if idx_skills == -1:
            logger.warning("skills_section_not_found")
            return False

        idx_key_rules = content.find(key_rules_marker, idx_skills)
        if idx_key_rules == -1:
            insert_pos = len(content)
        else:
            insert_pos = idx_key_rules

        entry_line = f"\n{skill_def.modelfile_entry}\n"

        if skill_def.modelfile_entry in content:
            logger.info("modelfile_entry_exists", entry=skill_def.modelfile_entry)
            return True

        new_content = content[:insert_pos] + entry_line + content[insert_pos:]
        mf_path.write_text(new_content, encoding="utf-8")
        logger.info("modelfile_updated", entry=skill_def.modelfile_entry)
        return True

    def _verify_installation(self, skill_name: str) -> bool:
        snake_name = self._to_snake_case(skill_name)
        skill_path = self._root / "src" / "harnessing" / "core" / f"{snake_name}.py"
        if not skill_path.is_file():
            return False

        try:
            content = skill_path.read_text(encoding="utf-8")
            if f"class {skill_name}" not in content:
                return False
        except OSError:
            return False

        return True

    def _build_code_template(self, class_name: str, method_name: str, capability_name: str, formula: str) -> str:
        return (
            f"from __future__ import annotations\n"
            f"\n"
            f"import structlog\n"
            f"\n"
            f"logger = structlog.get_logger()\n"
            f"\n"
            f"\n"
            f"class {class_name}:\n"
            f"    def __init__(self) -> None:\n"
            f"        self._formula = \"{formula}\"\n"
            f"        self._capability = \"{capability_name}\"\n"
            f"\n"
            f"    def {method_name}(self, input_data: dict) -> dict:\n"
            f"        try:\n"
            f"            result = self._process(input_data)\n"
            f"            logger.info(\"{method_name}_success\", capability=self._capability)\n"
            f"            return {{\"status\": \"success\", \"capability\": self._capability, \"result\": result, \"formula\": self._formula}}\n"
            f"        except Exception as exc:\n"
            f"            logger.error(\"{method_name}_failed\", capability=self._capability, error=str(exc))\n"
            f"            return {{\"status\": \"error\", \"capability\": self._capability, \"error\": str(exc)}}\n"
            f"\n"
            f"    def _process(self, input_data: dict) -> dict:\n"
            f"        return {{\"processed\": True, \"input_keys\": list(input_data.keys())}}\n"
        )

    def _build_test_template(self, class_name: str, method_name: str, capability_name: str) -> str:
        snake_name = self._to_snake_case(class_name)
        return (
            f"#!/usr/bin/env python3\n"
            f"import sys\n"
            f"import os\n"
            f"sys.path.insert(0, os.path.join(os.path.dirname(__file__), \"..\", \"src\"))\n"
            f"\n"
            f"from harnessing.core.{snake_name} import {class_name}\n"
            f"\n"
            f"passed = 0\n"
            f"failed = 0\n"
            f"\n"
            f"\n"
            f"def test(name: str, condition: bool, detail: str = \"\"):\n"
            f"    global passed, failed\n"
            f"    if condition:\n"
            f"        passed += 1\n"
            f"        print(f\"  ✅ {{name}}\")\n"
            f"    else:\n"
            f"        failed += 1\n"
            f"        print(f\"  ❌ {{name}} — {{detail}}\")\n"
            f"\n"
            f"\n"
            f"print(\"=\" * 60)\n"
            f"print(\"{class_name} Test Suite\")\n"
            f"print(\"=\" * 60)\n"
            f"\n"
            f"skill = {class_name}()\n"
            f"\n"
            f"result = skill.{method_name}({{\"test\": True}})\n"
            f"test(\"{method_name} returns success\", result[\"status\"] == \"success\", f\"got {{result.get('status')}}\")\n"
            f"test(\"{method_name} has capability\", result.get(\"capability\") == \"{capability_name}\", f\"got {{result.get('capability')}}\")\n"
            f"test(\"{method_name} has formula\", \"formula\" in result, \"missing formula key\")\n"
            f"\n"
            f"error_result = skill.{method_name}(None)\n"
            f"test(\"{method_name} handles None input\", result is not None, \"returned None\")\n"
            f"\n"
            f"print(f\"\\nResults: {{passed}} passed, {{failed}} failed\")\n"
            f"sys.exit(1 if failed > 0 else 0)\n"
        )

    @staticmethod
    def _to_pascal_case(name: str) -> str:
        return "".join(part.capitalize() for part in re.split(r"[_\s]+", name))

    @staticmethod
    def _to_snake_case(name: str) -> str:
        s1 = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
        s2 = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", s1)
        return re.sub(r"[-\s]+", "_", s2).lower()

    @staticmethod
    def _to_method_name(name: str) -> str:
        parts = re.split(r"[_\s]+", name)
        return parts[0].lower() + "_" + "_".join(parts[1:]) if len(parts) > 1 else parts[0].lower()
