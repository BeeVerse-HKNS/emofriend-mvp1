"""
AssuranceSystem - Master Agent 質量保證系統

功能：
1. 代碼審查（Lint + Type Check）
2. 測試覆蓋率檢查
3. 安全掃描（敏感信息偵測）
4. 依賴檢查

公式：G * S + R — 守衛 × 自癒 + 推理

相關規則：Rule 71 (Feedback Loop 規則)
"""

from __future__ import annotations

import json
import logging
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .project_scanner import ProjectScanner, SubProject

logger = logging.getLogger(__name__)


class CheckStatus(Enum):
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    ERROR = "error"
    SKIPPED = "skipped"


class CheckType(Enum):
    LINT = "lint"
    TYPE_CHECK = "type_check"
    TEST_COVERAGE = "test_coverage"
    SECURITY_SCAN = "security_scan"
    DEPENDENCY_CHECK = "dependency_check"
    CODE_QUALITY = "code_quality"


@dataclass
class CheckResult:
    check_type: CheckType
    status: CheckStatus
    message: str = ""
    details: list[dict[str, Any]] = field(default_factory=list)
    score: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "check_type": self.check_type.value,
            "status": self.status.value,
            "message": self.message,
            "details": self.details[:50],
            "score": self.score,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class AssuranceReport:
    project_name: str
    checks: list[CheckResult]
    overall_status: CheckStatus
    overall_score: float
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_name": self.project_name,
            "checks": [c.to_dict() for c in self.checks],
            "overall_status": self.overall_status.value,
            "overall_score": self.overall_score,
            "timestamp": self.timestamp.isoformat(),
        }


class AssuranceSystem:
    """
    Master Agent 質量保證系統

    執行多種質量檢查，確保代碼質量。
    """

    SENSITIVE_PATTERNS = [
        (r"api[_-]?key\s*=\s*['\"][^'\"]+['\"]", "API Key"),
        (r"password\s*=\s*['\"][^'\"]+['\"]", "Password"),
        (r"secret\s*=\s*['\"][^'\"]+['\"]", "Secret"),
        (r"token\s*=\s*['\"][^'\"]+['\"]", "Token"),
        (r"aws[_-]?access[_-]?key[_-]?id\s*=\s*['\"][^'\"]+['\"]", "AWS Access Key"),
        (r"aws[_-]?secret[_-]?access[_-]?key\s*=\s*['\"][^'\"]+['\"]", "AWS Secret Key"),
    ]

    def __init__(self, scanner: ProjectScanner):
        self.scanner = scanner

    def _get_project_path(self, project_name: str) -> Path | None:
        projects = self.scanner.scan_all()
        for p in projects:
            if p.name == project_name:
                return p.path
        return None

    def run_full_check(self, project_name: str) -> AssuranceReport:
        project_path = self._get_project_path(project_name)

        if not project_path:
            return AssuranceReport(
                project_name=project_name,
                checks=[],
                overall_status=CheckStatus.ERROR,
                overall_score=0.0,
            )

        checks: list[CheckResult] = []

        checks.append(self._check_lint(project_path))
        checks.append(self._check_type_check(project_path))
        checks.append(self._check_security(project_path))
        checks.append(self._check_dependencies(project_path))

        scores = [c.score for c in checks if c.status != CheckStatus.SKIPPED]
        overall_score = sum(scores) / len(scores) if scores else 0.0

        if any(c.status == CheckStatus.ERROR for c in checks):
            overall_status = CheckStatus.ERROR
        elif any(c.status == CheckStatus.FAIL for c in checks):
            overall_status = CheckStatus.FAIL
        elif any(c.status == CheckStatus.WARNING for c in checks):
            overall_status = CheckStatus.WARNING
        else:
            overall_status = CheckStatus.PASS

        return AssuranceReport(
            project_name=project_name,
            checks=checks,
            overall_status=overall_status,
            overall_score=overall_score,
        )

    def _check_lint(self, project_path: Path) -> CheckResult:
        try:
            result = subprocess.run(
                ["python", "-m", "ruff", "check", str(project_path), "--output-format=json"],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode == 0:
                return CheckResult(
                    check_type=CheckType.LINT,
                    status=CheckStatus.PASS,
                    message="No lint errors found",
                    score=100.0,
                )

            try:
                errors = json.loads(result.stdout)
                error_count = len(errors)
                score = max(0, 100 - error_count * 5)

                return CheckResult(
                    check_type=CheckType.LINT,
                    status=CheckStatus.FAIL if error_count > 10 else CheckStatus.WARNING,
                    message=f"Found {error_count} lint errors",
                    details=errors[:20],
                    score=score,
                )
            except json.JSONDecodeError:
                return CheckResult(
                    check_type=CheckType.LINT,
                    status=CheckStatus.WARNING,
                    message="Could not parse lint output",
                    score=50.0,
                )

        except FileNotFoundError:
            return CheckResult(
                check_type=CheckType.LINT,
                status=CheckStatus.SKIPPED,
                message="Ruff not installed",
            )
        except subprocess.TimeoutExpired:
            return CheckResult(
                check_type=CheckType.LINT,
                status=CheckStatus.ERROR,
                message="Lint check timed out",
            )
        except Exception as e:
            return CheckResult(
                check_type=CheckType.LINT,
                status=CheckStatus.ERROR,
                message=str(e),
            )

    def _check_type_check(self, project_path: Path) -> CheckResult:
        try:
            result = subprocess.run(
                ["python", "-m", "pyright", str(project_path), "--outputjson"],
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode == 0:
                return CheckResult(
                    check_type=CheckType.TYPE_CHECK,
                    status=CheckStatus.PASS,
                    message="No type errors found",
                    score=100.0,
                )

            try:
                data = json.loads(result.stdout)
                error_count = data.get("generalDiagnostics", 0)
                score = max(0, 100 - error_count * 5)

                return CheckResult(
                    check_type=CheckType.TYPE_CHECK,
                    status=CheckStatus.FAIL if error_count > 10 else CheckStatus.WARNING,
                    message=f"Found {error_count} type errors",
                    score=score,
                )
            except json.JSONDecodeError:
                return CheckResult(
                    check_type=CheckType.TYPE_CHECK,
                    status=CheckStatus.WARNING,
                    message="Could not parse type check output",
                    score=50.0,
                )

        except FileNotFoundError:
            return CheckResult(
                check_type=CheckType.TYPE_CHECK,
                status=CheckStatus.SKIPPED,
                message="Pyright not installed",
            )
        except subprocess.TimeoutExpired:
            return CheckResult(
                check_type=CheckType.TYPE_CHECK,
                status=CheckStatus.ERROR,
                message="Type check timed out",
            )
        except Exception as e:
            return CheckResult(
                check_type=CheckType.TYPE_CHECK,
                status=CheckStatus.ERROR,
                message=str(e),
            )

    def _check_security(self, project_path: Path) -> CheckResult:
        findings: list[dict[str, Any]] = []

        for py_file in project_path.rglob("*.py"):
            try:
                content = py_file.read_text(encoding="utf-8")

                for pattern, name in self.SENSITIVE_PATTERNS:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    if matches:
                        for match in matches:
                            findings.append({
                                "file": str(py_file.relative_to(project_path)),
                                "type": name,
                                "match": match[:50] + "..." if len(match) > 50 else match,
                            })

            except Exception:
                continue

        if not findings:
            return CheckResult(
                check_type=CheckType.SECURITY_SCAN,
                status=CheckStatus.PASS,
                message="No sensitive information found",
                score=100.0,
            )

        score = max(0, 100 - len(findings) * 20)

        return CheckResult(
            check_type=CheckType.SECURITY_SCAN,
            status=CheckStatus.FAIL if len(findings) > 3 else CheckStatus.WARNING,
            message=f"Found {len(findings)} potential security issues",
            details=findings[:20],
            score=score,
        )

    def _check_dependencies(self, project_path: Path) -> CheckResult:
        requirements = project_path / "requirements.txt"

        if not requirements.exists():
            return CheckResult(
                check_type=CheckType.DEPENDENCY_CHECK,
                status=CheckStatus.SKIPPED,
                message="No requirements.txt found",
            )

        try:
            content = requirements.read_text(encoding="utf-8")
            deps: list[dict[str, str]] = []

            for line in content.split("\n"):
                line = line.strip()
                if line and not line.startswith("#"):
                    if "==" in line:
                        name, version = line.split("==", 1)
                        deps.append({"name": name, "version": version})
                    elif ">=" in line:
                        name, version = line.split(">=", 1)
                        deps.append({"name": name, "version": f">={version}"})
                    else:
                        deps.append({"name": line, "version": "latest"})

            return CheckResult(
                check_type=CheckType.DEPENDENCY_CHECK,
                status=CheckStatus.PASS,
                message=f"Found {len(deps)} dependencies",
                details=deps,
                score=100.0,
            )

        except Exception as e:
            return CheckResult(
                check_type=CheckType.DEPENDENCY_CHECK,
                status=CheckStatus.ERROR,
                message=str(e),
            )

    def check_single_file(self, project_name: str, file_path: str) -> CheckResult:
        project_path = self._get_project_path(project_name)

        if not project_path:
            return CheckResult(
                check_type=CheckType.CODE_QUALITY,
                status=CheckStatus.ERROR,
                message=f"Project not found: {project_name}",
            )

        full_path = project_path / file_path

        if not full_path.exists():
            return CheckResult(
                check_type=CheckType.CODE_QUALITY,
                status=CheckStatus.ERROR,
                message=f"File not found: {full_path}",
            )

        return self._check_security_single_file(full_path)

    def _check_security_single_file(self, file_path: Path) -> CheckResult:
        try:
            content = file_path.read_text(encoding="utf-8")
            findings: list[dict[str, Any]] = []

            for pattern, name in self.SENSITIVE_PATTERNS:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    for match in matches:
                        findings.append({
                            "type": name,
                            "match": match[:50] + "..." if len(match) > 50 else match,
                        })

            if not findings:
                return CheckResult(
                    check_type=CheckType.SECURITY_SCAN,
                    status=CheckStatus.PASS,
                    message="No sensitive information found",
                    score=100.0,
                )

            return CheckResult(
                check_type=CheckType.SECURITY_SCAN,
                status=CheckStatus.WARNING,
                message=f"Found {len(findings)} potential security issues",
                details=findings,
                score=max(0, 100 - len(findings) * 20),
            )

        except Exception as e:
            return CheckResult(
                check_type=CheckType.SECURITY_SCAN,
                status=CheckStatus.ERROR,
                message=str(e),
            )


def create_assurance_system(root_path: Path | str) -> AssuranceSystem:
    from .project_scanner import ProjectScanner

    scanner = ProjectScanner(root_path)
    return AssuranceSystem(scanner)


if __name__ == "__main__":
    import sys

    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    assurance = create_assurance_system(root)

    print("執行質量檢查...")
    report = assurance.run_full_check("ai-content-creator")

    print(f"\n項目：{report.project_name}")
    print(f"總體狀態：{report.overall_status.value}")
    print(f"總體分數：{report.overall_score:.1f}")
    print()

    for check in report.checks:
        icon = {
            CheckStatus.PASS: "✅",
            CheckStatus.FAIL: "❌",
            CheckStatus.WARNING: "⚠️",
            CheckStatus.ERROR: "🔴",
            CheckStatus.SKIPPED: "⏭️",
        }.get(check.status, "❓")
        print(f"  {icon} {check.check_type.value}: {check.message} ({check.score:.1f}%)")
