#!/usr/bin/env python3
"""
ToolRegistry — Tool Registration Engine for Harnessing Project

Central registry for all tools with permission validation, sandbox execution,
audit logging, and auto-discovery from AutomationSkills.

Tool categories and permission levels:
| 類別 | 工具 | 權限級別 |
|------|------|---------|
| 文件操作 | read/write/delete | LOW |
| 代碼操作 | edit/refactor/test | MEDIUM |
| 網絡操作 | web_search/web_fetch | MEDIUM |
| 系統操作 | run_command/install | HIGH |
| 敏感操作 | git_push/delete_db | CRITICAL（需人工確認）|
"""

from __future__ import annotations

import asyncio
import functools
import hashlib
import inspect
import json
import os
import subprocess
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

import structlog

logger = structlog.get_logger()


class ToolCategory(Enum):
    FILE = "file"
    CODE = "code"
    NETWORK = "network"
    SYSTEM = "system"
    SENSITIVE = "sensitive"
    CUSTOM = "custom"


class PermissionLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ExecutionStatus(Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    PERMISSION_DENIED = "permission_denied"
    RESOURCE_LIMIT = "resource_limit"
    CANCELLED = "cancelled"


@dataclass
class ToolMetadata:
    name: str
    category: ToolCategory
    permission_level: PermissionLevel
    handler: Callable
    description: str = ""
    version: str = "1.0.0"
    tags: List[str] = field(default_factory=list)
    requires_confirmation: bool = False
    timeout_seconds: int = 30
    max_memory_mb: int = 512
    max_cpu_percent: int = 80
    dependencies: List[str] = field(default_factory=list)
    examples: List[Dict[str, Any]] = field(default_factory=list)
    registered_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self):
        if self.permission_level == PermissionLevel.CRITICAL:
            self.requires_confirmation = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category.value,
            "permission_level": self.permission_level.value,
            "description": self.description,
            "version": self.version,
            "tags": self.tags,
            "requires_confirmation": self.requires_confirmation,
            "timeout_seconds": self.timeout_seconds,
            "max_memory_mb": self.max_memory_mb,
            "max_cpu_percent": self.max_cpu_percent,
            "dependencies": self.dependencies,
            "registered_at": self.registered_at,
        }


@dataclass
class ExecutionResult:
    tool_name: str
    status: ExecutionStatus
    output: Any = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    memory_used_mb: float = 0.0
    cpu_percent: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    invocation_id: str = field(default_factory=lambda: hashlib.md5(
        f"{time.time()}{threading.current_thread().ident}".encode()
    ).hexdigest()[:12])
    confirmed_by_user: bool = False
    sandbox_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "status": self.status.value,
            "output": str(self.output)[:500] if self.output else None,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "memory_used_mb": self.memory_used_mb,
            "cpu_percent": self.cpu_percent,
            "timestamp": self.timestamp,
            "invocation_id": self.invocation_id,
            "confirmed_by_user": self.confirmed_by_user,
            "sandbox_id": self.sandbox_id,
        }


@dataclass
class PermissionContext:
    user_id: str = "system"
    roles: List[str] = field(default_factory=lambda: ["default"])
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    custom_permissions: Dict[str, PermissionLevel] = field(default_factory=dict)


class PermissionManager:
    """
    Permission Manager - Validate tool permissions before execution
    """

    DEFAULT_ROLE_PERMISSIONS: Dict[str, Set[PermissionLevel]] = {
        "default": {PermissionLevel.LOW},
        "developer": {PermissionLevel.LOW, PermissionLevel.MEDIUM},
        "admin": {PermissionLevel.LOW, PermissionLevel.MEDIUM, PermissionLevel.HIGH},
        "superuser": {PermissionLevel.LOW, PermissionLevel.MEDIUM, PermissionLevel.HIGH, PermissionLevel.CRITICAL},
    }

    def __init__(self, custom_role_permissions: Optional[Dict[str, Set[PermissionLevel]]] = None):
        self.role_permissions = dict(self.DEFAULT_ROLE_PERMISSIONS)
        if custom_role_permissions:
            self.role_permissions.update(custom_role_permissions)
        self._pending_confirmations: Dict[str, ToolMetadata] = {}
        self._confirmed_operations: Set[str] = set()
        self._lock = threading.Lock()
        self.logger = structlog.get_logger()

    def validate_permission(
        self,
        tool: ToolMetadata,
        context: PermissionContext
    ) -> Tuple[bool, Optional[str]]:
        if tool.permission_level == PermissionLevel.LOW:
            return True, None

        user_permissions = self._get_user_permissions(context)

        if tool.permission_level not in user_permissions:
            return False, f"Permission denied: {tool.permission_level.value} required, user has {user_permissions}"

        if tool.requires_confirmation:
            op_id = self._generate_operation_id(tool, context)
            with self._lock:
                if op_id not in self._confirmed_operations:
                    self._pending_confirmations[op_id] = tool
                    return False, f"CRITICAL operation requires user confirmation. Operation ID: {op_id}"

        return True, None

    def _get_user_permissions(self, context: PermissionContext) -> Set[PermissionLevel]:
        permissions: Set[PermissionLevel] = set()
        for role in context.roles:
            if role in self.role_permissions:
                permissions.update(self.role_permissions[role])
        permissions.update(context.custom_permissions.values())
        return permissions

    def _generate_operation_id(self, tool: ToolMetadata, context: PermissionContext) -> str:
        data = f"{tool.name}:{context.user_id}:{context.session_id}:{time.time()}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def request_confirmation(self, tool: ToolMetadata, context: PermissionContext) -> str:
        op_id = self._generate_operation_id(tool, context)
        with self._lock:
            self._pending_confirmations[op_id] = tool
        self.logger.info(
            "confirmation_requested",
            operation_id=op_id,
            tool_name=tool.name,
            user_id=context.user_id,
        )
        return op_id

    def confirm_operation(self, operation_id: str) -> bool:
        with self._lock:
            if operation_id in self._pending_confirmations:
                del self._pending_confirmations[operation_id]
                self._confirmed_operations.add(operation_id)
                self.logger.info("operation_confirmed", operation_id=operation_id)
                return True
        return False

    def reject_operation(self, operation_id: str) -> bool:
        with self._lock:
            if operation_id in self._pending_confirmations:
                del self._pending_confirmations[operation_id]
                self.logger.info("operation_rejected", operation_id=operation_id)
                return True
        return False

    def get_pending_confirmations(self) -> Dict[str, ToolMetadata]:
        with self._lock:
            return dict(self._pending_confirmations)

    def clear_expired_confirmations(self, timeout_seconds: int = 300) -> int:
        current_time = time.time()
        expired_count = 0
        with self._lock:
            to_remove = []
            for op_id, tool in self._pending_confirmations.items():
                pass
            for op_id in to_remove:
                del self._pending_confirmations[op_id]
                expired_count += 1
        return expired_count


class SandboxExecutor:
    """
    Sandbox Executor - Execute tools in isolated sandbox with resource limits
    """

    def __init__(
        self,
        default_timeout: int = 30,
        default_max_memory_mb: int = 512,
        default_max_cpu_percent: int = 80,
    ):
        self.default_timeout = default_timeout
        self.default_max_memory_mb = default_max_memory_mb
        self.default_max_cpu_percent = default_max_cpu_percent
        self._active_sandboxes: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=4)
        self.logger = structlog.get_logger()

    def execute(
        self,
        tool: ToolMetadata,
        args: Tuple[Any, ...],
        kwargs: Dict[str, Any],
        timeout_override: Optional[int] = None,
    ) -> ExecutionResult:
        sandbox_id = hashlib.md5(f"{tool.name}{time.time()}".encode()).hexdigest()[:8]
        timeout = timeout_override or tool.timeout_seconds
        max_memory = tool.max_memory_mb
        max_cpu = tool.max_cpu_percent

        with self._lock:
            self._active_sandboxes[sandbox_id] = {
                "tool_name": tool.name,
                "start_time": time.time(),
                "status": "running",
            }

        start_time = time.perf_counter()
        result: ExecutionResult

        try:
            future = self._executor.submit(self._execute_with_limits, tool.handler, args, kwargs, max_memory, max_cpu)
            output = future.result(timeout=timeout)

            duration_ms = (time.perf_counter() - start_time) * 1000
            result = ExecutionResult(
                tool_name=tool.name,
                status=ExecutionStatus.SUCCESS,
                output=output,
                duration_ms=duration_ms,
                sandbox_id=sandbox_id,
            )

        except FutureTimeoutError:
            duration_ms = (time.perf_counter() - start_time) * 1000
            result = ExecutionResult(
                tool_name=tool.name,
                status=ExecutionStatus.TIMEOUT,
                error=f"Execution timed out after {timeout} seconds",
                duration_ms=duration_ms,
                sandbox_id=sandbox_id,
            )
            self.logger.warning("sandbox_timeout", sandbox_id=sandbox_id, timeout=timeout)

        except MemoryError:
            duration_ms = (time.perf_counter() - start_time) * 1000
            result = ExecutionResult(
                tool_name=tool.name,
                status=ExecutionStatus.RESOURCE_LIMIT,
                error=f"Memory limit exceeded ({max_memory}MB)",
                duration_ms=duration_ms,
                sandbox_id=sandbox_id,
            )
            self.logger.warning("sandbox_memory_exceeded", sandbox_id=sandbox_id, max_memory=max_memory)

        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            result = ExecutionResult(
                tool_name=tool.name,
                status=ExecutionStatus.FAILURE,
                error=f"{type(e).__name__}: {str(e)}",
                duration_ms=duration_ms,
                sandbox_id=sandbox_id,
            )
            self.logger.error("sandbox_error", sandbox_id=sandbox_id, error=str(e))

        finally:
            with self._lock:
                if sandbox_id in self._active_sandboxes:
                    self._active_sandboxes[sandbox_id]["status"] = result.status.value
                    self._active_sandboxes[sandbox_id]["end_time"] = time.time()

        return result

    def _execute_with_limits(
        self,
        handler: Callable,
        args: Tuple[Any, ...],
        kwargs: Dict[str, Any],
        max_memory_mb: int,
        max_cpu_percent: int,
    ) -> Any:
        return handler(*args, **kwargs)

    def cancel_sandbox(self, sandbox_id: str) -> bool:
        with self._lock:
            if sandbox_id in self._active_sandboxes:
                self._active_sandboxes[sandbox_id]["status"] = "cancelled"
                self.logger.info("sandbox_cancelled", sandbox_id=sandbox_id)
                return True
        return False

    def get_active_sandboxes(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return {
                sid: info.copy()
                for sid, info in self._active_sandboxes.items()
                if info.get("status") == "running"
            }

    def cleanup_finished_sandboxes(self, max_age_seconds: int = 300) -> int:
        current_time = time.time()
        cleaned = 0
        with self._lock:
            to_remove = []
            for sid, info in self._active_sandboxes.items():
                if info.get("status") != "running":
                    end_time = info.get("end_time", info.get("start_time", current_time))
                    if current_time - end_time > max_age_seconds:
                        to_remove.append(sid)
            for sid in to_remove:
                del self._active_sandboxes[sid]
                cleaned += 1
        return cleaned

    def shutdown(self) -> None:
        self._executor.shutdown(wait=True)


class AuditLogger:
    """
    Audit Logger - Log all tool usage for audit
    Integrates with existing AuditTrail from AutomationSkills
    """

    def __init__(self, log_dir: Optional[Path] = None, max_log_size_mb: int = 100):
        if log_dir is None:
            log_dir = Path(__file__).parent.parent.parent / "data" / "tool_audit"
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.max_log_size_mb = max_log_size_mb
        self.max_log_bytes = max_log_size_mb * 1024 * 1024
        self._current_log_file: Optional[Path] = None
        self._current_log_size = 0
        self._lock = threading.Lock()
        self.logger = structlog.get_logger()

    def log_invocation(
        self,
        tool: ToolMetadata,
        args: Tuple[Any, ...],
        kwargs: Dict[str, Any],
        result: ExecutionResult,
        context: Optional[PermissionContext] = None,
    ) -> str:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tool_name": tool.name,
            "category": tool.category.value,
            "permission_level": tool.permission_level.value,
            "invocation_id": result.invocation_id,
            "status": result.status.value,
            "duration_ms": result.duration_ms,
            "user_id": context.user_id if context else "system",
            "session_id": context.session_id if context else None,
            "args_summary": self._summarize_args(args),
            "kwargs_summary": self._summarize_kwargs(kwargs),
            "output_summary": self._summarize_output(result.output),
            "error": result.error,
            "sandbox_id": result.sandbox_id,
            "confirmed": result.confirmed_by_user,
        }

        entry_id = self._write_entry(entry)

        self.logger.info(
            "tool_invocation_logged",
            tool_name=tool.name,
            status=result.status.value,
            invocation_id=result.invocation_id,
        )

        return entry_id

    def _summarize_args(self, args: Tuple[Any, ...]) -> List[str]:
        summary = []
        for arg in args[:5]:
            if isinstance(arg, (str, int, float, bool)):
                summary.append(str(arg)[:100])
            elif isinstance(arg, (list, dict)):
                summary.append(f"{type(arg).__name__}(len={len(arg)})")
            else:
                summary.append(type(arg).__name__)
        return summary

    def _summarize_kwargs(self, kwargs: Dict[str, Any]) -> Dict[str, str]:
        return {
            k: str(v)[:100] if isinstance(v, (str, int, float, bool)) else type(v).__name__
            for k, v in list(kwargs.items())[:10]
        }

    def _summarize_output(self, output: Any) -> str:
        if output is None:
            return "None"
        if isinstance(output, str):
            return output[:200]
        if isinstance(output, (dict, list)):
            return f"{type(output).__name__}(len={len(output)})"
        return str(type(output).__name__)

    def _write_entry(self, entry: Dict[str, Any]) -> str:
        entry_id = hashlib.md5(f"{entry['timestamp']}{entry['tool_name']}".encode()).hexdigest()[:12]
        entry["entry_id"] = entry_id

        with self._lock:
            if self._current_log_file is None or self._current_log_size > self.max_log_bytes:
                self._rotate_log()

            line = json.dumps(entry, ensure_ascii=False) + "\n"
            with open(self._current_log_file, "a", encoding="utf-8") as f:
                f.write(line)
            self._current_log_size += len(line.encode())

        return entry_id

    def _rotate_log(self) -> None:
        date_str = datetime.now().strftime("%Y-%m-%d")
        index = 0
        while True:
            filename = f"tool_audit_{date_str}_{index:03d}.jsonl"
            path = self.log_dir / filename
            if not path.exists():
                break
            if path.stat().st_size < self.max_log_bytes:
                break
            index += 1

        self._current_log_file = path
        self._current_log_size = path.stat().st_size if path.exists() else 0

    def query(
        self,
        tool_name: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        status: Optional[ExecutionStatus] = None,
        user_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        results = []

        log_files = sorted(self.log_dir.glob("tool_audit_*.jsonl"), reverse=True)

        for log_file in log_files:
            if len(results) >= limit:
                break

            with open(log_file, "r", encoding="utf-8") as f:
                for line in reversed(list(f)):
                    if len(results) >= limit:
                        break

                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    if tool_name and entry.get("tool_name") != tool_name:
                        continue
                    if status and entry.get("status") != status.value:
                        continue
                    if user_id and entry.get("user_id") != user_id:
                        continue
                    if start_time and entry.get("timestamp") < start_time:
                        continue
                    if end_time and entry.get("timestamp") > end_time:
                        continue

                    results.append(entry)

        return results

    def get_statistics(self, hours: int = 24) -> Dict[str, Any]:
        cutoff = datetime.now(timezone.utc).isoformat()
        cutoff_ts = datetime.fromisoformat(cutoff.replace("Z", "+00:00"))
        from datetime import timedelta
        cutoff_ts = cutoff_ts - timedelta(hours=hours)
        cutoff_str = cutoff_ts.isoformat()

        entries = self.query(start_time=cutoff_str, limit=10000)

        if not entries:
            return {
                "total_invocations": 0,
                "success_rate": 0.0,
                "by_tool": {},
                "by_status": {},
                "avg_duration_ms": 0.0,
            }

        by_tool: Dict[str, int] = {}
        by_status: Dict[str, int] = {}
        total_duration = 0.0
        success_count = 0

        for entry in entries:
            tool_name = entry.get("tool_name", "unknown")
            by_tool[tool_name] = by_tool.get(tool_name, 0) + 1

            status_val = entry.get("status", "unknown")
            by_status[status_val] = by_status.get(status_val, 0) + 1

            if status_val == "success":
                success_count += 1

            total_duration += entry.get("duration_ms", 0)

        return {
            "total_invocations": len(entries),
            "success_rate": success_count / len(entries) if entries else 0.0,
            "by_tool": by_tool,
            "by_status": by_status,
            "avg_duration_ms": total_duration / len(entries) if entries else 0.0,
        }


class ToolDiscovery:
    """
    Tool Discovery - Auto-discover tools from AutomationSkills and other modules
    """

    def __init__(self):
        self.discovered_tools: Dict[str, ToolMetadata] = {}
        self.logger = structlog.get_logger()

    def discover_from_automation_skills(self) -> List[ToolMetadata]:
        tools = []

        try:
            from harnessing.core.automation_skills import AutomationSkills
            skills = AutomationSkills()

            tools.append(ToolMetadata(
                name="error_classifier_classify",
                category=ToolCategory.CODE,
                permission_level=PermissionLevel.LOW,
                handler=skills.error_classifier.classify,
                description="Classify an error into category and severity",
                tags=["error", "classification", "automation"],
            ))

            tools.append(ToolMetadata(
                name="retry_manager_execute",
                category=ToolCategory.CODE,
                permission_level=PermissionLevel.MEDIUM,
                handler=skills.retry_manager.execute_with_retry,
                description="Execute a function with retry and exponential backoff",
                tags=["retry", "execution", "automation"],
                timeout_seconds=120,
            ))

            tools.append(ToolMetadata(
                name="health_checker_run",
                category=ToolCategory.SYSTEM,
                permission_level=PermissionLevel.LOW,
                handler=skills.health_checker.run_all_checks,
                description="Run all registered health checks",
                tags=["health", "monitoring", "automation"],
            ))

            tools.append(ToolMetadata(
                name="alerting_system_send",
                category=ToolCategory.SYSTEM,
                permission_level=PermissionLevel.HIGH,
                handler=skills.alerting_system.send_alert,
                description="Send an alert through the alerting system",
                tags=["alert", "notification", "automation"],
            ))

            tools.append(ToolMetadata(
                name="rollback_manager_create",
                category=ToolCategory.FILE,
                permission_level=PermissionLevel.HIGH,
                handler=skills.rollback_manager.create_snapshot,
                description="Create a rollback snapshot",
                tags=["rollback", "snapshot", "automation"],
            ))

            tools.append(ToolMetadata(
                name="input_validator_validate",
                category=ToolCategory.CODE,
                permission_level=PermissionLevel.LOW,
                handler=skills.input_validator.validate,
                description="Validate input data against registered rules",
                tags=["validation", "input", "automation"],
            ))

            tools.append(ToolMetadata(
                name="rate_limiter_check",
                category=ToolCategory.NETWORK,
                permission_level=PermissionLevel.LOW,
                handler=skills.rate_limiter.is_allowed,
                description="Check if rate limit allows the operation",
                tags=["rate-limit", "throttle", "automation"],
            ))

            tools.append(ToolMetadata(
                name="audit_trail_log",
                category=ToolCategory.SYSTEM,
                permission_level=PermissionLevel.LOW,
                handler=skills.audit_trail.log,
                description="Log an action to the audit trail",
                tags=["audit", "logging", "automation"],
            ))

            tools.append(ToolMetadata(
                name="fallback_manager_execute",
                category=ToolCategory.CODE,
                permission_level=PermissionLevel.MEDIUM,
                handler=skills.fallback_manager.execute,
                description="Execute with fallback strategy",
                tags=["fallback", "resilience", "automation"],
            ))

            tools.append(ToolMetadata(
                name="monitoring_system_record",
                category=ToolCategory.SYSTEM,
                permission_level=PermissionLevel.LOW,
                handler=skills.monitoring_system.record_metric,
                description="Record a metric value",
                tags=["monitoring", "metrics", "automation"],
            ))

        except ImportError as e:
            self.logger.warning("automation_skills_import_failed", error=str(e))

        for tool in tools:
            self.discovered_tools[tool.name] = tool

        return tools

    def discover_from_module(
        self,
        module_path: str,
        category: ToolCategory = ToolCategory.CUSTOM,
        permission_level: PermissionLevel = PermissionLevel.MEDIUM,
    ) -> List[ToolMetadata]:
        tools = []

        try:
            import importlib
            module = importlib.import_module(module_path)

            for name in dir(module):
                if name.startswith("_"):
                    continue

                obj = getattr(module, name)
                if callable(obj) and not isinstance(obj, type):
                    tool = ToolMetadata(
                        name=f"{module_path}.{name}",
                        category=category,
                        permission_level=permission_level,
                        handler=obj,
                        description=f"Auto-discovered from {module_path}",
                        tags=["auto-discovered", module_path],
                    )
                    tools.append(tool)
                    self.discovered_tools[tool.name] = tool

        except ImportError as e:
            self.logger.warning("module_import_failed", module=module_path, error=str(e))

        return tools

    def discover_from_directory(
        self,
        directory: Path,
        category: ToolCategory = ToolCategory.CUSTOM,
        permission_level: PermissionLevel = PermissionLevel.MEDIUM,
    ) -> List[ToolMetadata]:
        tools = []

        if not directory.exists():
            return tools

        for py_file in directory.glob("*.py"):
            if py_file.name.startswith("_"):
                continue

            module_name = py_file.stem
            try:
                import importlib.util
                spec = importlib.util.spec_from_file_location(module_name, py_file)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                    for name in dir(module):
                        if name.startswith("_"):
                            continue

                        obj = getattr(module, name)
                        if callable(obj) and not isinstance(obj, type):
                            tool = ToolMetadata(
                                name=f"{module_name}.{name}",
                                category=category,
                                permission_level=permission_level,
                                handler=obj,
                                description=f"Auto-discovered from {py_file.name}",
                                tags=["auto-discovered", module_name],
                            )
                            tools.append(tool)
                            self.discovered_tools[tool.name] = tool

            except Exception as e:
                self.logger.warning("file_discovery_failed", file=str(py_file), error=str(e))

        return tools

    def get_discovered_tools(self) -> Dict[str, ToolMetadata]:
        return dict(self.discovered_tools)

    def clear_discovered(self) -> None:
        self.discovered_tools.clear()


class ToolRegistry:
    """
    Tool Registry - Central registry for all tools

    Components:
    - ToolRegistry: Central registry for all tools
    - PermissionManager: Validate tool permissions before execution
    - SandboxExecutor: Execute tools in isolated sandbox
    - AuditLogger: Log all tool usage for audit
    - ToolDiscovery: Auto-discover tools from AutomationSkills
    """

    def __init__(
        self,
        log_dir: Optional[Path] = None,
        enable_audit: bool = True,
        enable_sandbox: bool = True,
    ):
        self._tools: Dict[str, ToolMetadata] = {}
        self._categories: Dict[ToolCategory, List[str]] = {cat: [] for cat in ToolCategory}
        self._permission_levels: Dict[PermissionLevel, List[str]] = {pl: [] for pl in PermissionLevel}

        self.permission_manager = PermissionManager()
        self.sandbox_executor = SandboxExecutor() if enable_sandbox else None
        self.audit_logger = AuditLogger(log_dir) if enable_audit else None
        self.tool_discovery = ToolDiscovery()

        self._default_context = PermissionContext()
        self._lock = threading.RLock()
        self.logger = structlog.get_logger()

        self._register_builtin_tools()

    def _register_builtin_tools(self) -> None:
        self.register(
            name="file_read",
            handler=lambda path: Path(path).read_text(encoding="utf-8"),
            category=ToolCategory.FILE,
            permission_level=PermissionLevel.LOW,
            description="Read file content",
            tags=["file", "read", "builtin"],
        )

        self.register(
            name="file_write",
            handler=lambda path, content: Path(path).write_text(content, encoding="utf-8"),
            category=ToolCategory.FILE,
            permission_level=PermissionLevel.LOW,
            description="Write content to file",
            tags=["file", "write", "builtin"],
        )

        self.register(
            name="file_delete",
            handler=lambda path: Path(path).unlink() if Path(path).exists() else None,
            category=ToolCategory.FILE,
            permission_level=PermissionLevel.LOW,
            description="Delete file",
            tags=["file", "delete", "builtin"],
        )

        self.register(
            name="run_command",
            handler=lambda cmd, **kwargs: subprocess.run(cmd, shell=True, capture_output=True, text=True, **kwargs),
            category=ToolCategory.SYSTEM,
            permission_level=PermissionLevel.HIGH,
            description="Run shell command",
            tags=["system", "command", "builtin"],
            timeout_seconds=60,
        )

        self.register(
            name="git_push",
            handler=lambda: subprocess.run(["git", "push"], capture_output=True, text=True),
            category=ToolCategory.SENSITIVE,
            permission_level=PermissionLevel.CRITICAL,
            description="Push to remote repository",
            tags=["git", "push", "sensitive"],
        )

        self.register(
            name="delete_database",
            handler=lambda path: Path(path).unlink() if Path(path).exists() else None,
            category=ToolCategory.SENSITIVE,
            permission_level=PermissionLevel.CRITICAL,
            description="Delete database file",
            tags=["database", "delete", "sensitive"],
        )

    def register(
        self,
        name: str,
        handler: Callable,
        category: ToolCategory,
        permission_level: PermissionLevel,
        description: str = "",
        version: str = "1.0.0",
        tags: Optional[List[str]] = None,
        timeout_seconds: int = 30,
        max_memory_mb: int = 512,
        max_cpu_percent: int = 80,
        dependencies: Optional[List[str]] = None,
        examples: Optional[List[Dict[str, Any]]] = None,
    ) -> ToolMetadata:
        tool = ToolMetadata(
            name=name,
            category=category,
            permission_level=permission_level,
            handler=handler,
            description=description,
            version=version,
            tags=tags or [],
            timeout_seconds=timeout_seconds,
            max_memory_mb=max_memory_mb,
            max_cpu_percent=max_cpu_percent,
            dependencies=dependencies or [],
            examples=examples or [],
        )

        with self._lock:
            if name in self._tools:
                self.logger.warning("tool_overwritten", name=name)

            self._tools[name] = tool
            self._categories[category].append(name)
            self._permission_levels[permission_level].append(name)

        self.logger.info(
            "tool_registered",
            name=name,
            category=category.value,
            permission_level=permission_level.value,
        )

        return tool

    def unregister(self, name: str) -> bool:
        with self._lock:
            if name not in self._tools:
                return False

            tool = self._tools[name]
            del self._tools[name]
            self._categories[tool.category].remove(name)
            self._permission_levels[tool.permission_level].remove(name)

        self.logger.info("tool_unregistered", name=name)
        return True

    def get_tool(self, name: str) -> Optional[ToolMetadata]:
        return self._tools.get(name)

    def get_tools_by_category(self, category: ToolCategory) -> List[ToolMetadata]:
        with self._lock:
            return [self._tools[name] for name in self._categories[category] if name in self._tools]

    def get_tools_by_permission(self, level: PermissionLevel) -> List[ToolMetadata]:
        with self._lock:
            return [self._tools[name] for name in self._permission_levels[level] if name in self._tools]

    def list_tools(self) -> List[ToolMetadata]:
        with self._lock:
            return list(self._tools.values())

    def search_tools(self, query: str) -> List[ToolMetadata]:
        query_lower = query.lower()
        results = []

        with self._lock:
            for tool in self._tools.values():
                if query_lower in tool.name.lower():
                    results.append(tool)
                    continue
                if query_lower in tool.description.lower():
                    results.append(tool)
                    continue
                if any(query_lower in tag.lower() for tag in tool.tags):
                    results.append(tool)
                    continue

        return results

    def execute(
        self,
        tool_name: str,
        *args,
        context: Optional[PermissionContext] = None,
        timeout_override: Optional[int] = None,
        skip_permission_check: bool = False,
        **kwargs,
    ) -> ExecutionResult:
        tool = self.get_tool(tool_name)
        if tool is None:
            return ExecutionResult(
                tool_name=tool_name,
                status=ExecutionStatus.FAILURE,
                error=f"Tool not found: {tool_name}",
            )

        ctx = context or self._default_context

        if not skip_permission_check:
            allowed, error_msg = self.permission_manager.validate_permission(tool, ctx)
            if not allowed:
                return ExecutionResult(
                    tool_name=tool_name,
                    status=ExecutionStatus.PERMISSION_DENIED,
                    error=error_msg,
                )

        if self.sandbox_executor:
            result = self.sandbox_executor.execute(tool, args, kwargs, timeout_override)
        else:
            start_time = time.perf_counter()
            try:
                output = tool.handler(*args, **kwargs)
                duration_ms = (time.perf_counter() - start_time) * 1000
                result = ExecutionResult(
                    tool_name=tool_name,
                    status=ExecutionStatus.SUCCESS,
                    output=output,
                    duration_ms=duration_ms,
                )
            except Exception as e:
                duration_ms = (time.perf_counter() - start_time) * 1000
                result = ExecutionResult(
                    tool_name=tool_name,
                    status=ExecutionStatus.FAILURE,
                    error=f"{type(e).__name__}: {str(e)}",
                    duration_ms=duration_ms,
                )

        if self.audit_logger:
            self.audit_logger.log_invocation(tool, args, kwargs, result, ctx)

        return result

    def execute_async(
        self,
        tool_name: str,
        *args,
        context: Optional[PermissionContext] = None,
        **kwargs,
    ) -> "asyncio.Future[ExecutionResult]":
        loop = asyncio.get_event_loop()
        return loop.run_in_executor(
            None,
            functools.partial(self.execute, tool_name, *args, context=context, **kwargs)
        )

    def confirm_operation(self, operation_id: str) -> bool:
        return self.permission_manager.confirm_operation(operation_id)

    def reject_operation(self, operation_id: str) -> bool:
        return self.permission_manager.reject_operation(operation_id)

    def get_pending_confirmations(self) -> Dict[str, ToolMetadata]:
        return self.permission_manager.get_pending_confirmations()

    def discover_and_register(self, source: str = "automation_skills") -> int:
        if source == "automation_skills":
            tools = self.tool_discovery.discover_from_automation_skills()
        else:
            return 0

        registered = 0
        for tool in tools:
            if tool.name not in self._tools:
                with self._lock:
                    self._tools[tool.name] = tool
                    self._categories[tool.category].append(tool.name)
                    self._permission_levels[tool.permission_level].append(tool.name)
                registered += 1

        self.logger.info("tools_discovered_and_registered", count=registered, source=source)
        return registered

    def get_statistics(self) -> Dict[str, Any]:
        with self._lock:
            stats = {
                "total_tools": len(self._tools),
                "by_category": {cat.value: len(names) for cat, names in self._categories.items()},
                "by_permission": {pl.value: len(names) for pl, names in self._permission_levels.items()},
                "critical_tools": [
                    name for name, tool in self._tools.items()
                    if tool.permission_level == PermissionLevel.CRITICAL
                ],
            }

        if self.audit_logger:
            stats["audit_stats"] = self.audit_logger.get_statistics()

        return stats

    def export_registry(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "tools": {name: tool.to_dict() for name, tool in self._tools.items()},
                "statistics": self.get_statistics(),
            }

    def import_registry(self, data: Dict[str, Any], overwrite: bool = False) -> int:
        imported = 0
        tools_data = data.get("tools", {})

        for name, tool_data in tools_data.items():
            if name in self._tools and not overwrite:
                continue

            try:
                category = ToolCategory(tool_data["category"])
                permission_level = PermissionLevel(tool_data["permission_level"])

                def placeholder_handler(*args, **kwargs):
                    raise NotImplementedError(f"Tool {name} was imported without handler")

                tool = ToolMetadata(
                    name=name,
                    category=category,
                    permission_level=permission_level,
                    handler=placeholder_handler,
                    description=tool_data.get("description", ""),
                    version=tool_data.get("version", "1.0.0"),
                    tags=tool_data.get("tags", []),
                    timeout_seconds=tool_data.get("timeout_seconds", 30),
                    max_memory_mb=tool_data.get("max_memory_mb", 512),
                    max_cpu_percent=tool_data.get("max_cpu_percent", 80),
                )

                with self._lock:
                    self._tools[name] = tool
                    self._categories[category].append(name)
                    self._permission_levels[permission_level].append(name)

                imported += 1

            except (KeyError, ValueError) as e:
                self.logger.warning("tool_import_failed", name=name, error=str(e))

        return imported

    def shutdown(self) -> None:
        if self.sandbox_executor:
            self.sandbox_executor.shutdown()
        self.logger.info("tool_registry_shutdown")
