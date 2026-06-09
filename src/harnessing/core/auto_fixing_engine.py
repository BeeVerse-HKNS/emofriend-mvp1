#!/usr/bin/env python3
"""
AutoFixingEngine — 自動錯誤修復引擎

根據錯誤類型自動選擇修復策略，整合 AutomationSkills、SelfAuditEngine、MessageGateway。

修復策略表：
| 錯誤類型 | 修復策略 | 信心等級 |
|---------|---------|---------|
| ImportError | 安裝缺失依賴 | HIGH |
| SyntaxError | 自動修復語法 | HIGH |
| API Error | 重試 + 降級 | MEDIUM |
| DOM 變化 | 更新選擇器 | MEDIUM |
| 邏輯錯誤 | 需人工介入 | LOW |

遵循零外部依賴原則，核心功能使用標準庫實現
"""

import json
import logging
import re
import subprocess
import sys
import threading
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple


class ErrorType(Enum):
    IMPORT_ERROR = "import_error"
    SYNTAX_ERROR = "syntax_error"
    API_ERROR = "api_error"
    DOM_CHANGE = "dom_change"
    LOGIC_ERROR = "logic_error"
    UNKNOWN = "unknown"


class FixConfidence(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class FixStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    NEEDS_MANUAL = "needs_manual"


@dataclass
class FixResult:
    status: FixStatus
    error_type: ErrorType
    confidence: FixConfidence
    message: str
    actions_taken: List[str] = field(default_factory=list)
    original_error: Optional[str] = None
    fixed_code: Optional[str] = None
    test_result: Optional[Dict[str, Any]] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ErrorContext:
    error: Exception
    error_type: ErrorType
    error_message: str
    traceback_str: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    function_name: Optional[str] = None
    context_data: Dict[str, Any] = field(default_factory=dict)


class AutoFixErrorClassifier:
    """
    錯誤分類器
    將錯誤分類為 5 種類型
    """

    IMPORT_PATTERNS = [
        r"ImportError",
        r"ModuleNotFoundError",
        r"No module named",
        r"cannot import name",
        r"dynamic module does not define",
    ]

    SYNTAX_PATTERNS = [
        r"SyntaxError",
        r"IndentationError",
        r"TabError",
        r"unexpected indent",
        r"unindent does not match",
        r"invalid syntax",
        r"expected ':'",
        r"EOF while scanning triple-quoted string",
    ]

    API_PATTERNS = [
        r"ConnectionError",
        r"TimeoutError",
        r"HTTPError",
        r"requests\.exceptions",
        r"APIError",
        r"RateLimitError",
        r"401",
        r"403",
        r"429",
        r"500",
        r"502",
        r"503",
        r"timed out",
        r"connection refused",
    ]

    DOM_PATTERNS = [
        r"NoSuchElementException",
        r"ElementNotInteractableException",
        r"StaleElementReferenceException",
        r"TimeoutException.*element",
        r"element not found",
        r"element not visible",
        r"stale element reference",
        r"selector.*not found",
        r"xpath.*not found",
    ]

    LOGIC_PATTERNS = [
        r"AssertionError",
        r"ValueError",
        r"TypeError",
        r"KeyError",
        r"IndexError",
        r"AttributeError",
        r"ZeroDivisionError",
        r"RecursionError",
    ]

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._classification_cache: Dict[str, ErrorType] = {}
        self._lock = threading.Lock()

    def classify(self, error: Exception, context: Dict[str, Any] = None) -> ErrorContext:
        error_type = type(error).__name__
        error_msg = str(error)
        tb_str = traceback.format_exc()

        cache_key = f"{error_type}:{error_msg[:100]}"
        if cache_key in self._classification_cache:
            classified_type = self._classification_cache[cache_key]
        else:
            classified_type = self._classify_type(error_type, error_msg, tb_str)
            with self._lock:
                self._classification_cache[cache_key] = classified_type

        file_path, line_number, func_name = self._extract_location(tb_str)

        return ErrorContext(
            error=error,
            error_type=classified_type,
            error_message=error_msg,
            traceback_str=tb_str,
            file_path=file_path,
            line_number=line_number,
            function_name=func_name,
            context_data=context or {},
        )

    def _classify_type(self, error_type: str, error_msg: str, tb_str: str) -> ErrorType:
        combined = f"{error_type} {error_msg} {tb_str}".lower()

        for pattern in self.IMPORT_PATTERNS:
            if re.search(pattern, combined, re.IGNORECASE):
                return ErrorType.IMPORT_ERROR

        for pattern in self.SYNTAX_PATTERNS:
            if re.search(pattern, combined, re.IGNORECASE):
                return ErrorType.SYNTAX_ERROR

        for pattern in self.API_PATTERNS:
            if re.search(pattern, combined, re.IGNORECASE):
                return ErrorType.API_ERROR

        for pattern in self.DOM_PATTERNS:
            if re.search(pattern, combined, re.IGNORECASE):
                return ErrorType.DOM_CHANGE

        for pattern in self.LOGIC_PATTERNS:
            if re.search(pattern, combined, re.IGNORECASE):
                return ErrorType.LOGIC_ERROR

        return ErrorType.UNKNOWN

    def _extract_location(self, tb_str: str) -> Tuple[Optional[str], Optional[int], Optional[str]]:
        file_pattern = r'File "([^"]+)", line (\d+)(?:, in (\w+))?'
        matches = re.findall(file_pattern, tb_str)
        if matches:
            last_match = matches[-1]
            return last_match[0], int(last_match[1]) if last_match[1] else None, last_match[2] or None
        return None, None, None

    def get_confidence(self, error_type: ErrorType) -> FixConfidence:
        confidence_map = {
            ErrorType.IMPORT_ERROR: FixConfidence.HIGH,
            ErrorType.SYNTAX_ERROR: FixConfidence.HIGH,
            ErrorType.API_ERROR: FixConfidence.MEDIUM,
            ErrorType.DOM_CHANGE: FixConfidence.MEDIUM,
            ErrorType.LOGIC_ERROR: FixConfidence.LOW,
            ErrorType.UNKNOWN: FixConfidence.LOW,
        }
        return confidence_map.get(error_type, FixConfidence.LOW)


class FixStrategyLibrary:
    """
    修復策略庫
    為每種錯誤類型提供修復策略
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._strategies: Dict[ErrorType, Callable] = {
            ErrorType.IMPORT_ERROR: self._fix_import_error,
            ErrorType.SYNTAX_ERROR: self._fix_syntax_error,
            ErrorType.API_ERROR: self._fix_api_error,
            ErrorType.DOM_CHANGE: self._fix_dom_change,
            ErrorType.LOGIC_ERROR: self._fix_logic_error,
            ErrorType.UNKNOWN: self._fix_unknown,
        }
        self._custom_strategies: Dict[str, Callable] = {}

    def register_strategy(self, name: str, strategy: Callable, error_type: ErrorType = None) -> None:
        self._custom_strategies[name] = strategy
        if error_type:
            self._strategies[error_type] = strategy

    def get_strategy(self, error_type: ErrorType) -> Optional[Callable]:
        return self._strategies.get(error_type)

    def _fix_import_error(self, context: ErrorContext) -> FixResult:
        actions = []
        module_name = self._extract_module_name(context.error_message)

        if module_name:
            install_result = self._try_install_module(module_name)
            if install_result:
                actions.append(f"Installed module: {module_name}")
                return FixResult(
                    status=FixStatus.SUCCESS,
                    error_type=ErrorType.IMPORT_ERROR,
                    confidence=FixConfidence.HIGH,
                    message=f"Successfully installed missing module: {module_name}",
                    actions_taken=actions,
                    original_error=context.error_message,
                )

            actions.append(f"Failed to install module: {module_name}")

        return FixResult(
            status=FixStatus.FAILED,
            error_type=ErrorType.IMPORT_ERROR,
            confidence=FixConfidence.HIGH,
            message=f"Could not auto-fix import error for: {module_name or 'unknown module'}",
            actions_taken=actions,
            original_error=context.error_message,
        )

    def _extract_module_name(self, error_msg: str) -> Optional[str]:
        patterns = [
            r"No module named '([^']+)'",
            r"No module named \"([^\"]+)\"",
            r"cannot import name '([^']+)'",
            r"ImportError: ([^\s]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, error_msg)
            if match:
                return match.group(1).split(".")[0]
        return None

    def _try_install_module(self, module_name: str) -> bool:
        pip_names = {
            "PIL": "pillow",
            "cv2": "opencv-python",
            "sklearn": "scikit-learn",
            "yaml": "pyyaml",
            "dateutil": "python-dateutil",
            "dotenv": "python-dotenv",
        }
        install_name = pip_names.get(module_name, module_name)

        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", install_name],
                capture_output=True,
                text=True,
                timeout=60,
            )
            return result.returncode == 0
        except Exception as e:
            self.logger.error(f"Failed to install {install_name}: {e}")
            return False

    def _fix_syntax_error(self, context: ErrorContext) -> FixResult:
        actions = []

        if context.file_path and Path(context.file_path).exists():
            code = Path(context.file_path).read_text(encoding="utf-8")
            fixed_code = self._try_fix_syntax(code, context.line_number)

            if fixed_code and fixed_code != code:
                Path(context.file_path).write_text(fixed_code, encoding="utf-8")
                actions.append(f"Fixed syntax in {context.file_path}")
                return FixResult(
                    status=FixStatus.SUCCESS,
                    error_type=ErrorType.SYNTAX_ERROR,
                    confidence=FixConfidence.HIGH,
                    message="Syntax error auto-fixed",
                    actions_taken=actions,
                    original_error=context.error_message,
                    fixed_code=fixed_code,
                )

        return FixResult(
            status=FixStatus.NEEDS_MANUAL,
            error_type=ErrorType.SYNTAX_ERROR,
            confidence=FixConfidence.HIGH,
            message="Syntax error requires manual fix",
            actions_taken=actions,
            original_error=context.error_message,
        )

    def _try_fix_syntax(self, code: str, line_number: Optional[int]) -> Optional[str]:
        lines = code.split("\n")

        if line_number and 0 < line_number <= len(lines):
            line = lines[line_number - 1]

            if line.rstrip().endswith(":") and not line.rstrip().endswith("::"):
                pass

            if line.startswith(" ") and not line.startswith("\t"):
                pass

            if "\t" in line and "    " in line:
                lines[line_number - 1] = line.replace("\t", "    ")
                return "\n".join(lines)

        try:
            compile(code, "<string>", "exec")
            return code
        except SyntaxError:
            return None

    def _fix_api_error(self, context: ErrorContext) -> FixResult:
        actions = []

        actions.append("API error detected - retry with exponential backoff recommended")
        actions.append("Fallback to cached data or alternative endpoint recommended")

        return FixResult(
            status=FixStatus.NEEDS_MANUAL,
            error_type=ErrorType.API_ERROR,
            confidence=FixConfidence.MEDIUM,
            message="API error requires retry/fallback strategy",
            actions_taken=actions,
            original_error=context.error_message,
            metadata={
                "retry_recommended": True,
                "fallback_recommended": True,
                "error_category": self._categorize_api_error(context.error_message),
            },
        )

    def _categorize_api_error(self, error_msg: str) -> str:
        error_lower = error_msg.lower()
        if "401" in error_msg or "403" in error_msg:
            return "auth_error"
        if "429" in error_msg or "rate limit" in error_lower:
            return "rate_limit"
        if "500" in error_msg or "502" in error_msg or "503" in error_msg:
            return "server_error"
        if "timeout" in error_lower or "timed out" in error_lower:
            return "timeout"
        return "unknown"

    def _fix_dom_change(self, context: ErrorContext) -> FixResult:
        actions = []

        actions.append("DOM change detected - selector update recommended")
        actions.append("Use multiple selector strategies (data-testid > class > xpath)")

        return FixResult(
            status=FixStatus.NEEDS_MANUAL,
            error_type=ErrorType.DOM_CHANGE,
            confidence=FixConfidence.MEDIUM,
            message="DOM change requires selector update",
            actions_taken=actions,
            original_error=context.error_message,
            metadata={
                "selector_strategies": ["data-testid", "aria-label", "css", "xpath"],
                "wait_strategy": "explicit_wait",
            },
        )

    def _fix_logic_error(self, context: ErrorContext) -> FixResult:
        actions = []

        actions.append("Logic error detected - manual intervention required")
        actions.append("Review the code logic and add proper validation")

        suggestion = self._get_logic_suggestion(context)

        return FixResult(
            status=FixStatus.NEEDS_MANUAL,
            error_type=ErrorType.LOGIC_ERROR,
            confidence=FixConfidence.LOW,
            message="Logic error requires manual fix",
            actions_taken=actions,
            original_error=context.error_message,
            metadata={"suggestion": suggestion},
        )

    def _get_logic_suggestion(self, context: ErrorContext) -> str:
        error_type = type(context.error).__name__

        suggestions = {
            "ValueError": "Validate input values before processing",
            "TypeError": "Check type compatibility and add type guards",
            "KeyError": "Use .get() with default value or check key existence",
            "IndexError": "Check list/array bounds before access",
            "AttributeError": "Check attribute existence with hasattr()",
            "ZeroDivisionError": "Add zero check before division",
            "AssertionError": "Review assertion condition and expected values",
        }

        return suggestions.get(error_type, "Review the error context and fix the logic")

    def _fix_unknown(self, context: ErrorContext) -> FixResult:
        return FixResult(
            status=FixStatus.NEEDS_MANUAL,
            error_type=ErrorType.UNKNOWN,
            confidence=FixConfidence.LOW,
            message="Unknown error type requires manual investigation",
            actions_taken=["Manual investigation required"],
            original_error=context.error_message,
        )


class FixVerifier:
    """
    修復驗證器
    驗證修復是否成功
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def verify_fix(
        self,
        fix_result: FixResult,
        test_func: Optional[Callable] = None,
        test_command: Optional[str] = None,
    ) -> Dict[str, Any]:
        verification = {
            "fix_status": fix_result.status.value,
            "verified": False,
            "test_passed": None,
            "errors": [],
        }

        if fix_result.status == FixStatus.SUCCESS:
            if test_func:
                try:
                    test_result = test_func()
                    verification["test_passed"] = bool(test_result)
                    verification["verified"] = bool(test_result)
                except Exception as e:
                    verification["errors"].append(f"Test failed: {e}")
                    verification["test_passed"] = False

            elif test_command:
                try:
                    result = subprocess.run(
                        test_command,
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=120,
                    )
                    verification["test_passed"] = result.returncode == 0
                    verification["verified"] = result.returncode == 0
                    if result.returncode != 0:
                        verification["errors"].append(result.stderr)
                except Exception as e:
                    verification["errors"].append(f"Command failed: {e}")

            else:
                verification["verified"] = True

        elif fix_result.status == FixStatus.NEEDS_MANUAL:
            verification["verified"] = False
            verification["errors"].append("Fix requires manual intervention")

        return verification

    def verify_syntax(self, file_path: str) -> Tuple[bool, Optional[str]]:
        try:
            code = Path(file_path).read_text(encoding="utf-8")
            compile(code, file_path, "exec")
            return True, None
        except SyntaxError as e:
            return False, str(e)

    def verify_imports(self, file_path: str) -> Tuple[bool, List[str]]:
        try:
            code = Path(file_path).read_text(encoding="utf-8")
            import_pattern = r"^(?:from|import)\s+(\S+)"
            imports = re.findall(import_pattern, code, re.MULTILINE)

            failed = []
            for module in imports:
                module = module.split(".")[0]
                try:
                    __import__(module)
                except ImportError:
                    failed.append(module)

            return len(failed) == 0, failed
        except Exception as e:
            return False, [str(e)]


class FixReporter:
    """
    修復報告器
    向用戶報告修復結果
    """

    def __init__(self, message_gateway=None):
        self.logger = logging.getLogger(__name__)
        self.message_gateway = message_gateway
        self._fix_history: List[Dict[str, Any]] = []
        self._success_count = 0
        self._total_count = 0

    def report(self, fix_result: FixResult, verification: Dict[str, Any] = None) -> str:
        self._total_count += 1
        if fix_result.status == FixStatus.SUCCESS:
            self._success_count += 1

        report = self._generate_report(fix_result, verification)
        self._fix_history.append({
            "timestamp": fix_result.timestamp,
            "error_type": fix_result.error_type.value,
            "status": fix_result.status.value,
            "confidence": fix_result.confidence.value,
            "message": fix_result.message,
            "actions": fix_result.actions_taken,
        })

        self.logger.info(f"AutoFix Report: {fix_result.status.value} - {fix_result.message}")

        if self.message_gateway:
            self._send_notification(fix_result, verification)

        return report

    def _generate_report(self, fix_result: FixResult, verification: Dict[str, Any] = None) -> str:
        lines = [
            "=== AutoFix Report ===",
            f"Status: {fix_result.status.value}",
            f"Error Type: {fix_result.error_type.value}",
            f"Confidence: {fix_result.confidence.value}",
            f"Message: {fix_result.message}",
        ]

        if fix_result.actions_taken:
            lines.append("Actions Taken:")
            for action in fix_result.actions_taken:
                lines.append(f"  - {action}")

        if verification:
            lines.append(f"Verification: {'PASSED' if verification.get('verified') else 'FAILED'}")
            if verification.get("errors"):
                lines.append("Errors:")
                for error in verification["errors"]:
                    lines.append(f"  - {error}")

        lines.append(f"Timestamp: {fix_result.timestamp}")

        return "\n".join(lines)

    def _send_notification(self, fix_result: FixResult, verification: Dict[str, Any] = None) -> None:
        try:
            from harnessing.core.message_gateway import MessagePriority

            if fix_result.status == FixStatus.SUCCESS:
                priority = MessagePriority.NORMAL
            elif fix_result.status == FixStatus.NEEDS_MANUAL:
                priority = MessagePriority.HIGH
            else:
                priority = MessagePriority.HIGH

            self.message_gateway.notify(
                content=fix_result.message,
                title=f"AutoFix: {fix_result.error_type.value}",
                priority=priority,
            )
        except Exception as e:
            self.logger.error(f"Failed to send notification: {e}")

    def get_success_rate(self) -> float:
        if self._total_count == 0:
            return 0.0
        return self._success_count / self._total_count

    def get_statistics(self) -> Dict[str, Any]:
        return {
            "total_fixes": self._total_count,
            "successful_fixes": self._success_count,
            "success_rate": self.get_success_rate(),
            "fix_history": self._fix_history[-100:],
        }


class AutoFixingEngine:
    """
    自動錯誤修復引擎
    整合所有組件，提供統一嘅自動修復介面
    """

    def __init__(
        self,
        automation_skills=None,
        self_audit_engine=None,
        message_gateway=None,
        base_path: Optional[Path] = None,
    ):
        self.logger = logging.getLogger(__name__)

        self.automation_skills = automation_skills
        self.self_audit_engine = self_audit_engine
        self.message_gateway = message_gateway

        if base_path is None:
            base_path = Path(__file__).parent.parent.parent / "data"
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

        self.error_classifier = AutoFixErrorClassifier()
        self.strategy_library = FixStrategyLibrary()
        self.verifier = FixVerifier()
        self.reporter = FixReporter(message_gateway)

        self._lock = threading.Lock()

    def auto_fix(
        self,
        error: Exception,
        context: Dict[str, Any] = None,
        test_func: Callable = None,
        test_command: str = None,
    ) -> Tuple[FixResult, Dict[str, Any]]:
        error_context = self.error_classifier.classify(error, context)

        confidence = self.error_classifier.get_confidence(error_context.error_type)

        strategy = self.strategy_library.get_strategy(error_context.error_type)

        if strategy:
            fix_result = strategy(error_context)
        else:
            fix_result = FixResult(
                status=FixStatus.NEEDS_MANUAL,
                error_type=error_context.error_type,
                confidence=confidence,
                message="No fix strategy available",
                actions_taken=[],
                original_error=error_context.error_message,
            )

        verification = self.verifier.verify_fix(fix_result, test_func, test_command)

        self.reporter.report(fix_result, verification)

        if self.self_audit_engine:
            self._record_to_audit_engine(error_context, fix_result, verification)

        return fix_result, verification

    def _record_to_audit_engine(
        self,
        error_context: ErrorContext,
        fix_result: FixResult,
        verification: Dict[str, Any],
    ) -> None:
        try:
            self.self_audit_engine.record_action(
                action_type="auto_fix",
                details=f"{error_context.error_type.value}: {fix_result.message}",
                outcome=fix_result.status.value,
            )
        except Exception as e:
            self.logger.error(f"Failed to record to audit engine: {e}")

    def fix_with_retry(
        self,
        func: Callable,
        max_retries: int = 3,
        context: Dict[str, Any] = None,
    ) -> Tuple[Any, Optional[FixResult]]:
        last_error = None
        last_fix_result = None

        for attempt in range(max_retries + 1):
            try:
                return func(), None
            except Exception as e:
                last_error = e
                self.logger.warning(f"Attempt {attempt + 1} failed: {e}")

                if attempt < max_retries:
                    fix_result, verification = self.auto_fix(e, context)

                    if fix_result.status == FixStatus.SUCCESS and verification.get("verified"):
                        last_fix_result = fix_result
                        continue
                    else:
                        break

        if last_error:
            raise last_error

        return None, last_fix_result

    def register_custom_strategy(
        self,
        name: str,
        strategy: Callable,
        error_type: ErrorType = None,
    ) -> None:
        self.strategy_library.register_strategy(name, strategy, error_type)
        self.logger.info(f"Registered custom strategy: {name}")

    def get_fix_statistics(self) -> Dict[str, Any]:
        return self.reporter.get_statistics()

    def get_supported_error_types(self) -> List[str]:
        return [et.value for et in ErrorType]

    def classify_error(self, error: Exception) -> ErrorContext:
        return self.error_classifier.classify(error)

    def get_confidence_for_error(self, error: Exception) -> FixConfidence:
        context = self.error_classifier.classify(error)
        return self.error_classifier.get_confidence(context.error_type)

    def batch_fix(
        self,
        errors: List[Exception],
        context: Dict[str, Any] = None,
    ) -> List[Tuple[FixResult, Dict[str, Any]]]:
        results = []
        for error in errors:
            try:
                result = self.auto_fix(error, context)
                results.append(result)
            except Exception as e:
                self.logger.error(f"Batch fix failed for error: {e}")
                results.append((
                    FixResult(
                        status=FixStatus.FAILED,
                        error_type=ErrorType.UNKNOWN,
                        confidence=FixConfidence.LOW,
                        message=f"Fix failed: {e}",
                        original_error=str(error),
                    ),
                    {"verified": False, "errors": [str(e)]},
                ))
        return results

    def save_fix_history(self, path: Optional[Path] = None) -> None:
        if path is None:
            path = self.base_path / "fix_history.json"

        stats = self.get_fix_statistics()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2, ensure_ascii=False, default=str)

    def load_fix_history(self, path: Optional[Path] = None) -> Dict[str, Any]:
        if path is None:
            path = self.base_path / "fix_history.json"

        if not path.exists():
            return {}

        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)


def create_auto_fixing_engine(
    automation_skills=None,
    self_audit_engine=None,
    message_gateway=None,
) -> AutoFixingEngine:
    return AutoFixingEngine(
        automation_skills=automation_skills,
        self_audit_engine=self_audit_engine,
        message_gateway=message_gateway,
    )
