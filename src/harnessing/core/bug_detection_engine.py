"""
BugDetectionEngine — Bug 偵測引擎

整合四個偵測組件：
1. StaticAnalyzer — Ruff + mypy 靜態分析
2. GitChangeAnalyzer — Git diff 風險分析
3. DependencyScanner — 依賴漏洞掃描
4. SecurityScanner — 敏感信息偵測

公式：(S * G) + (D + Sec) — 靜態×Git 聯合 + 依賴+安全 聯合
"""

import os
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class BugSeverity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class BugCategory(Enum):
    STATIC_ANALYSIS = "static_analysis"
    GIT_CHANGE = "git_change"
    DEPENDENCY = "dependency"
    SECURITY = "security"


@dataclass
class BugFinding:
    category: BugCategory
    severity: BugSeverity
    title: str
    description: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    rule_id: Optional[str] = None
    fix_suggestion: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class BugDetectionResult:
    timestamp: datetime
    project_path: str
    findings: list[BugFinding]
    duration_seconds: float
    analyzers_run: list[str]
    summary: dict[str, int] = field(default_factory=dict)


class StaticAnalyzer:
    def __init__(self):
        self.ruff_available = self._check_command("ruff")
        self.mypy_available = self._check_command("mypy")

    def _check_command(self, cmd: str) -> bool:
        try:
            subprocess.run([cmd, "--version"], capture_output=True, timeout=5)
            return True
        except Exception:
            return False

    def analyze(self, project_path: str) -> list[BugFinding]:
        findings = []
        path = Path(project_path)
        
        if not path.exists():
            return findings
        
        if self.ruff_available:
            findings.extend(self._run_ruff(project_path))
        
        if self.mypy_available:
            findings.extend(self._run_mypy(project_path))
        
        return findings

    def _run_ruff(self, project_path: str) -> list[BugFinding]:
        findings = []
        try:
            result = subprocess.run(
                ["ruff", "check", project_path, "--output-format=json"],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.stdout:
                import json
                try:
                    issues = json.loads(result.stdout)
                    for issue in issues:
                        severity = BugSeverity.MEDIUM
                        if issue.get("severity") == "error":
                            severity = BugSeverity.HIGH
                        elif issue.get("severity") == "warning":
                            severity = BugSeverity.MEDIUM
                        
                        findings.append(BugFinding(
                            category=BugCategory.STATIC_ANALYSIS,
                            severity=severity,
                            title=f"Ruff: {issue.get('code', 'Unknown')}",
                            description=issue.get("message", ""),
                            file_path=issue.get("filename"),
                            line_number=issue.get("location", {}).get("row"),
                            rule_id=issue.get("code"),
                            fix_suggestion=issue.get("fix") if issue.get("fix") else None,
                        ))
                except json.JSONDecodeError:
                    pass
        except Exception:
            pass
        
        return findings

    def _run_mypy(self, project_path: str) -> list[BugFinding]:
        findings = []
        try:
            result = subprocess.run(
                ["mypy", project_path, "--no-error-summary", "--show-error-codes"],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.stdout:
                pattern = r"^(.+?):(\d+): error: (.+?) \[(.+?)\]$"
                for line in result.stdout.split("\n"):
                    match = re.match(pattern, line)
                    if match:
                        findings.append(BugFinding(
                            category=BugCategory.STATIC_ANALYSIS,
                            severity=BugSeverity.HIGH,
                            title=f"MyPy: {match.group(4)}",
                            description=match.group(3),
                            file_path=match.group(1),
                            line_number=int(match.group(2)),
                            rule_id=match.group(4),
                        ))
        except Exception:
            pass
        
        return findings


class GitChangeAnalyzer:
    def __init__(self, risk_threshold: float = 0.7):
        self.risk_threshold = risk_threshold
        self.git_available = self._check_git()

    def _check_git(self) -> bool:
        try:
            subprocess.run(["git", "--version"], capture_output=True, timeout=5)
            return True
        except Exception:
            return False

    def analyze(self, project_path: str) -> list[BugFinding]:
        findings = []
        
        if not self.git_available:
            return findings
        
        path = Path(project_path)
        if not path.exists():
            return findings
        
        findings.extend(self._check_uncommitted(project_path))
        findings.extend(self._check_large_changes(project_path))
        
        return findings

    def _check_uncommitted(self, project_path: str) -> list[BugFinding]:
        findings = []
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=project_path
            )
            
            if result.stdout:
                lines = result.stdout.strip().split("\n")
                for line in lines:
                    if line.strip():
                        status = line[:2]
                        file_path = line[3:].strip()
                        
                        if status.strip() in ("M", "A", "D", "R"):
                            severity = BugSeverity.LOW
                            if file_path.endswith(".py"):
                                severity = BugSeverity.MEDIUM
                            if file_path.endswith((".env", ".secret", "credentials.json")):
                                severity = BugSeverity.HIGH
                            
                            findings.append(BugFinding(
                                category=BugCategory.GIT_CHANGE,
                                severity=severity,
                                title="Uncommitted Change",
                                description=f"File {status.strip()}: {file_path}",
                                file_path=file_path,
                                metadata={"status": status.strip()},
                            ))
        except Exception:
            pass
        
        return findings

    def _check_large_changes(self, project_path: str) -> list[BugFinding]:
        findings = []
        try:
            result = subprocess.run(
                ["git", "diff", "--stat", "HEAD~1", "HEAD"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=project_path
            )
            
            if result.stdout:
                lines = result.stdout.strip().split("\n")
                for line in lines:
                    match = re.search(r"(\d+) insertion", line)
                    if match:
                        insertions = int(match.group(1))
                        if insertions > 500:
                            findings.append(BugFinding(
                                category=BugCategory.GIT_CHANGE,
                                severity=BugSeverity.MEDIUM,
                                title="Large Change Detected",
                                description=f"Recent commit has {insertions} insertions, may need review",
                                metadata={"insertions": insertions},
                            ))
        except Exception:
            pass
        
        return findings


class DependencyScanner:
    def __init__(self):
        self.pip_audit_available = self._check_pip_audit()

    def _check_pip_audit(self) -> bool:
        try:
            subprocess.run(["pip-audit", "--version"], capture_output=True, timeout=5)
            return True
        except Exception:
            return False

    def analyze(self, project_path: str) -> list[BugFinding]:
        findings = []
        path = Path(project_path)
        
        requirements_file = path / "requirements.txt"
        if requirements_file.exists():
            findings.extend(self._check_requirements(str(requirements_file)))
        
        pyproject_file = path / "pyproject.toml"
        if pyproject_file.exists():
            findings.extend(self._check_pyproject(str(pyproject_file)))
        
        return findings

    def _check_requirements(self, requirements_path: str) -> list[BugFinding]:
        findings = []
        
        if self.pip_audit_available:
            try:
                result = subprocess.run(
                    ["pip-audit", "-r", requirements_path, "--format=json"],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if result.stdout:
                    import json
                    try:
                        vulnerabilities = json.loads(result.stdout)
                        for vuln in vulnerabilities:
                            findings.append(BugFinding(
                                category=BugCategory.DEPENDENCY,
                                severity=BugSeverity.HIGH,
                                title=f"Vulnerability: {vuln.get('name', 'Unknown')}",
                                description=vuln.get("description", "Known vulnerability in dependency"),
                                metadata={
                                    "package": vuln.get("name"),
                                    "version": vuln.get("version"),
                                    "cve": vuln.get("cve"),
                                },
                                fix_suggestion=f"Upgrade to version {vuln.get('fix_version', 'latest')}",
                            ))
                    except json.JSONDecodeError:
                        pass
            except Exception:
                pass
        
        return findings

    def _check_pyproject(self, pyproject_path: str) -> list[BugFinding]:
        findings = []
        return findings


class SecurityScanner:
    SECRET_PATTERNS = [
        (r'api[_-]?key\s*=\s*["\']?([a-zA-Z0-9_\-]{20,})["\']?', "API Key"),
        (r'password\s*=\s*["\']?([^\s"\']+)["\']?', "Password"),
        (r'secret[_-]?key\s*=\s*["\']?([a-zA-Z0-9_\-]{20,})["\']?', "Secret Key"),
        (r'token\s*=\s*["\']?([a-zA-Z0-9_\-]{20,})["\']?', "Token"),
        (r'auth[_-]?token\s*=\s*["\']?([a-zA-Z0-9_\-]{20,})["\']?', "Auth Token"),
        (r'private[_-]?key\s*=\s*["\']?([a-zA-Z0-9_\-]{20,})["\']?', "Private Key"),
        (r'sk-[a-zA-Z0-9]{20,}', "OpenAI API Key"),
        (r'xox[baprs]-[a-zA-Z0-9\-]{10,}', "Slack Token"),
        (r'ghp_[a-zA-Z0-9]{36}', "GitHub Token"),
        (r'AKIA[0-9A-Z]{16}', "AWS Access Key"),
    ]

    def __init__(self):
        self.compiled_patterns = [
            (re.compile(pattern, re.IGNORECASE), name)
            for pattern, name in self.SECRET_PATTERNS
        ]

    def analyze(self, project_path: str) -> list[BugFinding]:
        findings = []
        path = Path(project_path)
        
        if not path.exists():
            return findings
        
        for py_file in path.rglob("*.py"):
            if ".venv" in str(py_file) or "__pycache__" in str(py_file):
                continue
            findings.extend(self._scan_file(py_file))
        
        for env_file in path.rglob(".env*"):
            findings.extend(self._scan_env_file(env_file))
        
        return findings

    def _scan_file(self, file_path: Path) -> list[BugFinding]:
        findings = []
        
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            lines = content.split("\n")
            
            for i, line in enumerate(lines, 1):
                for pattern, name in self.compiled_patterns:
                    if pattern.search(line):
                        findings.append(BugFinding(
                            category=BugCategory.SECURITY,
                            severity=BugSeverity.CRITICAL,
                            title=f"Potential {name} Exposure",
                            description=f"Possible {name} found in code",
                            file_path=str(file_path),
                            line_number=i,
                            fix_suggestion="Move to .env file and use os.environ.get()",
                        ))
        except Exception:
            pass
        
        return findings

    def _scan_env_file(self, env_path: Path) -> list[BugFinding]:
        findings = []
        
        try:
            if env_path.name == ".env.example" or env_path.name == ".env.template":
                return findings
            
            content = env_path.read_text(encoding="utf-8", errors="ignore")
            if content.strip():
                findings.append(BugFinding(
                    category=BugCategory.SECURITY,
                    severity=BugSeverity.INFO,
                    title="Environment File Present",
                    description=f"Environment file {env_path.name} exists",
                    file_path=str(env_path),
                    metadata={"note": "Ensure this file is in .gitignore"},
                ))
        except Exception:
            pass
        
        return findings


class BugDetectionEngine:
    def __init__(
        self,
        enable_static: bool = True,
        enable_git: bool = True,
        enable_dependency: bool = True,
        enable_security: bool = True,
    ):
        self.static_analyzer = StaticAnalyzer() if enable_static else None
        self.git_analyzer = GitChangeAnalyzer() if enable_git else None
        self.dependency_scanner = DependencyScanner() if enable_dependency else None
        self.security_scanner = SecurityScanner() if enable_security else None

    def analyze(self, project_path: str) -> BugDetectionResult:
        import time
        start_time = time.time()
        
        findings = []
        analyzers_run = []
        
        if self.static_analyzer:
            try:
                static_findings = self.static_analyzer.analyze(project_path)
                findings.extend(static_findings)
                analyzers_run.append("static")
            except Exception:
                pass
        
        if self.git_analyzer:
            try:
                git_findings = self.git_analyzer.analyze(project_path)
                findings.extend(git_findings)
                analyzers_run.append("git")
            except Exception:
                pass
        
        if self.dependency_scanner:
            try:
                dep_findings = self.dependency_scanner.analyze(project_path)
                findings.extend(dep_findings)
                analyzers_run.append("dependency")
            except Exception:
                pass
        
        if self.security_scanner:
            try:
                sec_findings = self.security_scanner.analyze(project_path)
                findings.extend(sec_findings)
                analyzers_run.append("security")
            except Exception:
                pass
        
        duration = time.time() - start_time
        
        summary = {
            "total": len(findings),
            "critical": sum(1 for f in findings if f.severity == BugSeverity.CRITICAL),
            "high": sum(1 for f in findings if f.severity == BugSeverity.HIGH),
            "medium": sum(1 for f in findings if f.severity == BugSeverity.MEDIUM),
            "low": sum(1 for f in findings if f.severity == BugSeverity.LOW),
            "info": sum(1 for f in findings if f.severity == BugSeverity.INFO),
        }
        
        return BugDetectionResult(
            timestamp=datetime.now(),
            project_path=project_path,
            findings=findings,
            duration_seconds=duration,
            analyzers_run=analyzers_run,
            summary=summary,
        )

    def analyze_multiple(self, project_paths: list[str]) -> dict[str, BugDetectionResult]:
        results = {}
        for path in project_paths:
            if Path(path).exists():
                results[path] = self.analyze(path)
        return results

    def get_fix_recommendations(self, result: BugDetectionResult) -> list[dict[str, Any]]:
        recommendations = []
        
        for finding in result.findings:
            if finding.fix_suggestion:
                recommendations.append({
                    "title": finding.title,
                    "severity": finding.severity.value,
                    "file": finding.file_path,
                    "line": finding.line_number,
                    "suggestion": finding.fix_suggestion,
                })
        
        return sorted(recommendations, key=lambda x: (
            {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}.get(x["severity"], 5)
        ))
