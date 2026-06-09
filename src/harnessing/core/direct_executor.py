"""
DirectExecutor - Master Agent 直接執行引擎

功能：
1. 文件讀取/編輯
2. 腳本執行
3. 測試運行
4. Git 操作

公式：R * A - G — 推理 × 自動化 - 過度守衛

相關規則：Rule 67 (Master Orchestrator 調度規則)
"""

from __future__ import annotations

import logging
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .project_scanner import ProjectScanner, SubProject

logger = logging.getLogger(__name__)


class ExecutionStatus(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    NOT_FOUND = "not_found"
    PERMISSION_DENIED = "permission_denied"


@dataclass
class ExecutionResult:
    status: ExecutionStatus
    output: str = ""
    error: str = ""
    exit_code: int = 0
    duration_seconds: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "output": self.output[:2000] if self.output else "",
            "error": self.error,
            "exit_code": self.exit_code,
            "duration_seconds": self.duration_seconds,
            "timestamp": self.timestamp.isoformat(),
        }


class DirectExecutor:
    """
    Master Agent 直接執行引擎

    直接在子項目執行操作，無需用戶手動介入。
    """

    DEFAULT_TIMEOUT = 300
    GIT_TIMEOUT = 60

    def __init__(
        self,
        scanner: ProjectScanner,
        default_timeout: int = DEFAULT_TIMEOUT,
    ):
        self.scanner = scanner
        self.default_timeout = default_timeout

    def _get_project_path(self, project_name: str) -> Path | None:
        projects = self.scanner.scan_all()
        for p in projects:
            if p.name == project_name:
                return p.path
        return None

    def read_file(self, project_name: str, file_path: str) -> ExecutionResult:
        start = datetime.now()
        project_path = self._get_project_path(project_name)

        if not project_path:
            return ExecutionResult(
                status=ExecutionStatus.NOT_FOUND,
                error=f"Project not found: {project_name}",
            )

        full_path = project_path / file_path

        if not full_path.exists():
            return ExecutionResult(
                status=ExecutionStatus.NOT_FOUND,
                error=f"File not found: {full_path}",
            )

        try:
            content = full_path.read_text(encoding="utf-8")
            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                output=content,
                duration_seconds=(datetime.now() - start).total_seconds(),
            )
        except PermissionError:
            return ExecutionResult(
                status=ExecutionStatus.PERMISSION_DENIED,
                error=f"Permission denied: {full_path}",
            )
        except Exception as e:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                error=str(e),
            )

    def write_file(self, project_name: str, file_path: str, content: str) -> ExecutionResult:
        start = datetime.now()
        project_path = self._get_project_path(project_name)

        if not project_path:
            return ExecutionResult(
                status=ExecutionStatus.NOT_FOUND,
                error=f"Project not found: {project_name}",
            )

        full_path = project_path / file_path

        try:
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding="utf-8")

            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                output=f"Written {len(content)} bytes to {file_path}",
                duration_seconds=(datetime.now() - start).total_seconds(),
            )
        except PermissionError:
            return ExecutionResult(
                status=ExecutionStatus.PERMISSION_DENIED,
                error=f"Permission denied: {full_path}",
            )
        except Exception as e:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                error=str(e),
            )

    def execute_script(
        self,
        project_name: str,
        script_path: str,
        args: list[str] | None = None,
        timeout: int | None = None,
        env: dict[str, str] | None = None,
    ) -> ExecutionResult:
        start = datetime.now()
        project_path = self._get_project_path(project_name)

        if not project_path:
            return ExecutionResult(
                status=ExecutionStatus.NOT_FOUND,
                error=f"Project not found: {project_name}",
            )

        full_script_path = project_path / script_path

        if not full_script_path.exists():
            return ExecutionResult(
                status=ExecutionStatus.NOT_FOUND,
                error=f"Script not found: {full_script_path}",
            )

        cmd = ["python", str(full_script_path)] + (args or [])
        timeout = timeout or self.default_timeout

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(project_path),
                env={**dict(__import__("os").environ), **(env or {})},
            )

            status = ExecutionStatus.SUCCESS if result.returncode == 0 else ExecutionStatus.FAILED

            return ExecutionResult(
                status=status,
                output=result.stdout,
                error=result.stderr,
                exit_code=result.returncode,
                duration_seconds=(datetime.now() - start).total_seconds(),
            )

        except subprocess.TimeoutExpired:
            return ExecutionResult(
                status=ExecutionStatus.TIMEOUT,
                error=f"Script timed out after {timeout} seconds",
            )
        except Exception as e:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                error=str(e),
            )

    def run_tests(
        self,
        project_name: str,
        test_path: str = "tests/",
        test_framework: str = "pytest",
    ) -> ExecutionResult:
        start = datetime.now()
        project_path = self._get_project_path(project_name)

        if not project_path:
            return ExecutionResult(
                status=ExecutionStatus.NOT_FOUND,
                error=f"Project not found: {project_name}",
            )

        full_test_path = project_path / test_path

        if not full_test_path.exists():
            return ExecutionResult(
                status=ExecutionStatus.NOT_FOUND,
                error=f"Test path not found: {full_test_path}",
            )

        if test_framework == "pytest":
            cmd = ["python", "-m", "pytest", str(full_test_path), "-v", "--tb=short"]
        else:
            cmd = ["python", "-m", "unittest", "discover", "-s", str(full_test_path)]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.default_timeout,
                cwd=str(project_path),
            )

            status = ExecutionStatus.SUCCESS if result.returncode == 0 else ExecutionStatus.FAILED

            return ExecutionResult(
                status=status,
                output=result.stdout,
                error=result.stderr,
                exit_code=result.returncode,
                duration_seconds=(datetime.now() - start).total_seconds(),
            )

        except subprocess.TimeoutExpired:
            return ExecutionResult(
                status=ExecutionStatus.TIMEOUT,
                error=f"Tests timed out after {self.default_timeout} seconds",
            )
        except Exception as e:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                error=str(e),
            )

    def git_status(self, project_name: str) -> ExecutionResult:
        return self._git_command(project_name, ["status", "--short"])

    def git_pull(self, project_name: str) -> ExecutionResult:
        return self._git_command(project_name, ["pull"])

    def git_add(self, project_name: str, files: list[str] | None = None) -> ExecutionResult:
        args = ["add"] + (files or ["."])
        return self._git_command(project_name, args)

    def git_commit(self, project_name: str, message: str) -> ExecutionResult:
        return self._git_command(project_name, ["commit", "-m", message])

    def git_push(self, project_name: str, branch: str = "main") -> ExecutionResult:
        return self._git_command(project_name, ["push", "origin", branch])

    def _git_command(self, project_name: str, args: list[str]) -> ExecutionResult:
        start = datetime.now()
        project_path = self._get_project_path(project_name)

        if not project_path:
            return ExecutionResult(
                status=ExecutionStatus.NOT_FOUND,
                error=f"Project not found: {project_name}",
            )

        git_dir = project_path / ".git"
        if not git_dir.exists():
            return ExecutionResult(
                status=ExecutionStatus.NOT_FOUND,
                error="Not a git repository",
            )

        cmd = ["git"] + args

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.GIT_TIMEOUT,
                cwd=str(project_path),
            )

            status = ExecutionStatus.SUCCESS if result.returncode == 0 else ExecutionStatus.FAILED

            return ExecutionResult(
                status=status,
                output=result.stdout,
                error=result.stderr,
                exit_code=result.returncode,
                duration_seconds=(datetime.now() - start).total_seconds(),
            )

        except subprocess.TimeoutExpired:
            return ExecutionResult(
                status=ExecutionStatus.TIMEOUT,
                error=f"Git command timed out after {self.GIT_TIMEOUT} seconds",
            )
        except Exception as e:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                error=str(e),
            )

    def list_files(self, project_name: str, directory: str = ".") -> ExecutionResult:
        start = datetime.now()
        project_path = self._get_project_path(project_name)

        if not project_path:
            return ExecutionResult(
                status=ExecutionStatus.NOT_FOUND,
                error=f"Project not found: {project_name}",
            )

        full_path = project_path / directory

        if not full_path.exists():
            return ExecutionResult(
                status=ExecutionStatus.NOT_FOUND,
                error=f"Directory not found: {full_path}",
            )

        try:
            files: list[str] = []
            for item in full_path.iterdir():
                if item.is_file():
                    files.append(f"📄 {item.name}")
                elif item.is_dir():
                    files.append(f"📁 {item.name}/")

            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                output="\n".join(sorted(files)),
                duration_seconds=(datetime.now() - start).total_seconds(),
            )
        except PermissionError:
            return ExecutionResult(
                status=ExecutionStatus.PERMISSION_DENIED,
                error=f"Permission denied: {full_path}",
            )
        except Exception as e:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                error=str(e),
            )


def create_executor(root_path: Path | str) -> DirectExecutor:
    from .project_scanner import ProjectScanner

    scanner = ProjectScanner(root_path)
    return DirectExecutor(scanner)


if __name__ == "__main__":
    import sys

    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    executor = create_executor(root)

    print("測試 DirectExecutor...")
    print()

    result = executor.list_files("ai-content-creator")
    print(f"列出文件：{result.status.value}")
    if result.output:
        print(result.output[:500])

    result = executor.git_status("ai-content-creator")
    print(f"\nGit 狀態：{result.status.value}")
    if result.output:
        print(result.output)
