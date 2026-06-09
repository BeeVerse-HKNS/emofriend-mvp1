from __future__ import annotations

import re
import structlog
import traceback
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

logger = structlog.get_logger()


class ErrorType(Enum):
    SYNTAX = "syntax"
    RUNTIME = "runtime"
    LOGIC = "logic"
    TYPE = "type"
    IMPORT = "import"
    CONFIGURATION = "configuration"
    NETWORK = "network"
    PERMISSION = "permission"
    RESOURCE = "resource"
    UNKNOWN = "unknown"


class ErrorSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CorrectionStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    APPLIED = "applied"
    VERIFIED = "verified"
    FAILED = "failed"


@dataclass
class DetectedError:
    error_type: ErrorType
    severity: ErrorSeverity
    message: str
    location: str | None = None
    stack_trace: str | None = None
    context: dict[str, Any] = field(default_factory=dict)
    raw_exception: Exception | None = None


@dataclass
class RootCause:
    primary_cause: str
    contributing_factors: list[str] = field(default_factory=list)
    affected_components: list[str] = field(default_factory=list)
    confidence: float = 0.0
    remediation_hints: list[str] = field(default_factory=list)


@dataclass
class Correction:
    description: str
    actions: list[str] = field(default_factory=list)
    code_changes: list[dict[str, str]] = field(default_factory=list)
    status: CorrectionStatus = CorrectionStatus.PENDING
    applied_at: str | None = None


@dataclass
class VerificationResult:
    is_successful: bool
    tests_passed: int = 0
    tests_failed: int = 0
    issues: list[str] = field(default_factory=list)
    metrics: dict[str, float] = field(default_factory=dict)


class ErrorDetector:
    ERROR_PATTERNS: dict[ErrorType, list[tuple[str, ErrorSeverity]]] = {
        ErrorType.SYNTAX: [
            (r"SyntaxError:", ErrorSeverity.HIGH),
            (r"IndentationError:", ErrorSeverity.HIGH),
            (r"unexpected token", ErrorSeverity.MEDIUM),
        ],
        ErrorType.RUNTIME: [
            (r"RuntimeError:", ErrorSeverity.HIGH),
            (r"ZeroDivisionError:", ErrorSeverity.MEDIUM),
            (r"IndexError:", ErrorSeverity.MEDIUM),
            (r"KeyError:", ErrorSeverity.MEDIUM),
        ],
        ErrorType.TYPE: [
            (r"TypeError:", ErrorSeverity.HIGH),
            (r"AttributeError:", ErrorSeverity.MEDIUM),
            (r"ValueError:", ErrorSeverity.MEDIUM),
        ],
        ErrorType.IMPORT: [
            (r"ImportError:", ErrorSeverity.HIGH),
            (r"ModuleNotFoundError:", ErrorSeverity.HIGH),
        ],
        ErrorType.CONFIGURATION: [
            (r"ConfigError:", ErrorSeverity.HIGH),
            (r"EnvironmentError:", ErrorSeverity.MEDIUM),
            (r"missing configuration", ErrorSeverity.MEDIUM),
        ],
        ErrorType.NETWORK: [
            (r"ConnectionError:", ErrorSeverity.HIGH),
            (r"TimeoutError:", ErrorSeverity.MEDIUM),
            (r"HTTPError:", ErrorSeverity.MEDIUM),
        ],
        ErrorType.PERMISSION: [
            (r"PermissionError:", ErrorSeverity.HIGH),
            (r"AccessDenied", ErrorSeverity.HIGH),
        ],
        ErrorType.RESOURCE: [
            (r"MemoryError:", ErrorSeverity.CRITICAL),
            (r"OSError:", ErrorSeverity.HIGH),
            (r"Disk full", ErrorSeverity.CRITICAL),
        ],
    }

    EXCEPTION_TYPE_MAP: dict[type, ErrorType] = {
        ImportError: ErrorType.IMPORT,
        ModuleNotFoundError: ErrorType.IMPORT,
        TypeError: ErrorType.TYPE,
        AttributeError: ErrorType.TYPE,
        ValueError: ErrorType.TYPE,
        RuntimeError: ErrorType.RUNTIME,
        IndexError: ErrorType.RUNTIME,
        KeyError: ErrorType.RUNTIME,
        ZeroDivisionError: ErrorType.RUNTIME,
        SyntaxError: ErrorType.SYNTAX,
        IndentationError: ErrorType.SYNTAX,
        ConnectionError: ErrorType.NETWORK,
        TimeoutError: ErrorType.NETWORK,
        PermissionError: ErrorType.PERMISSION,
        OSError: ErrorType.RESOURCE,
        MemoryError: ErrorType.RESOURCE,
    }

    def detect(self, error: Exception | str, context: dict[str, Any] | None = None) -> DetectedError:
        if isinstance(error, Exception):
            return self._detect_from_exception(error, context)
        return self._detect_from_string(error, context)

    def _detect_from_exception(self, exc: Exception, context: dict[str, Any] | None = None) -> DetectedError:
        error_message = str(exc)
        
        error_type = self.EXCEPTION_TYPE_MAP.get(type(exc), ErrorType.UNKNOWN)
        if error_type == ErrorType.UNKNOWN:
            error_type, _ = self._classify_error(error_message)
        
        severity = ErrorSeverity.HIGH
        if error_type in (ErrorType.RESOURCE,):
            severity = ErrorSeverity.CRITICAL
        elif error_type in (ErrorType.SYNTAX, ErrorType.IMPORT, ErrorType.NETWORK):
            severity = ErrorSeverity.HIGH
        elif error_type in (ErrorType.TYPE, ErrorType.RUNTIME):
            severity = ErrorSeverity.MEDIUM

        tb = traceback.format_exc()
        location = self._extract_location(tb)

        return DetectedError(
            error_type=error_type,
            severity=severity,
            message=error_message,
            location=location,
            stack_trace=tb,
            context=context or {},
            raw_exception=exc,
        )

    def _detect_from_string(self, error_str: str, context: dict[str, Any] | None = None) -> DetectedError:
        error_type, severity = self._classify_error(error_str)
        location = self._extract_location(error_str)

        return DetectedError(
            error_type=error_type,
            severity=severity,
            message=error_str,
            location=location,
            stack_trace=None,
            context=context or {},
        )

    def _classify_error(self, message: str) -> tuple[ErrorType, ErrorSeverity]:
        for error_type, patterns in self.ERROR_PATTERNS.items():
            for pattern, severity in patterns:
                if re.search(pattern, message, re.IGNORECASE):
                    return error_type, severity
        return ErrorType.UNKNOWN, ErrorSeverity.MEDIUM

    def _extract_location(self, text: str) -> str | None:
        match = re.search(r'File "([^"]+)", line (\d+)', text)
        if match:
            return f"{match.group(1)}:{match.group(2)}"
        return None


class RootCauseAnalyzer:
    ROOT_CAUSE_PATTERNS: dict[ErrorType, list[tuple[str, str, list[str]]]] = {
        ErrorType.IMPORT: [
            (
                r"ModuleNotFoundError: No module named '(\w+)'",
                "Missing required dependency",
                ["Install the missing package", "Check requirements.txt"],
            ),
        ],
        ErrorType.TYPE: [
            (
                r"'(\w+)' object is not callable",
                "Object called as function but is not callable",
                ["Check object type before calling", "Verify function assignment"],
            ),
            (
                r"'NoneType' object has no attribute '(\w+)'",
                "Operation on None value",
                ["Add null check", "Initialize variable properly"],
            ),
        ],
        ErrorType.RUNTIME: [
            (
                r"IndexError: list index out of range",
                "Accessing list beyond its bounds",
                ["Check list length before access", "Use safe indexing"],
            ),
            (
                r"KeyError: '(\w+)'",
                "Dictionary key not found",
                ["Check key existence", "Use dict.get() with default"],
            ),
        ],
        ErrorType.NETWORK: [
            (
                r"ConnectionError",
                "Network connection failed",
                ["Check network connectivity", "Verify endpoint availability", "Add retry logic"],
            ),
        ],
    }

    def analyze(self, error: DetectedError) -> RootCause:
        primary_cause = self._identify_primary_cause(error)
        contributing_factors = self._identify_contributing_factors(error)
        affected_components = self._identify_affected_components(error)
        remediation_hints = self._generate_remediation_hints(error)

        confidence = self._calculate_confidence(error, primary_cause)

        return RootCause(
            primary_cause=primary_cause,
            contributing_factors=contributing_factors,
            affected_components=affected_components,
            confidence=confidence,
            remediation_hints=remediation_hints,
        )

    def _identify_primary_cause(self, error: DetectedError) -> str:
        if error.error_type in self.ROOT_CAUSE_PATTERNS:
            for pattern, cause, _ in self.ROOT_CAUSE_PATTERNS[error.error_type]:
                if re.search(pattern, error.message, re.IGNORECASE):
                    return cause

        return f"Unknown {error.error_type.value} error occurred"

    def _identify_contributing_factors(self, error: DetectedError) -> list[str]:
        factors: list[str] = []

        if error.stack_trace:
            if "recursive" in error.stack_trace.lower():
                factors.append("Potential infinite recursion detected")
            if len(re.findall(r"File ", error.stack_trace)) > 10:
                factors.append("Deep call stack may indicate complexity issue")

        if error.context:
            if error.context.get("memory_usage", 0) > 0.9:
                factors.append("High memory usage detected")
            if error.context.get("cpu_usage", 0) > 0.9:
                factors.append("High CPU usage detected")

        return factors

    def _identify_affected_components(self, error: DetectedError) -> list[str]:
        components: list[str] = []

        if error.location:
            components.append(error.location)

        if error.stack_trace:
            file_matches = re.findall(r'File "([^"]+)"', error.stack_trace)
            components.extend(file_matches[:5])

        return list(set(components))

    def _generate_remediation_hints(self, error: DetectedError) -> list[str]:
        if error.error_type in self.ROOT_CAUSE_PATTERNS:
            for pattern, _, hints in self.ROOT_CAUSE_PATTERNS[error.error_type]:
                if re.search(pattern, error.message, re.IGNORECASE):
                    return hints

        return ["Review error message for details", "Check recent code changes"]

    def _calculate_confidence(self, error: DetectedError, primary_cause: str) -> float:
        if "Unknown" in primary_cause:
            return 0.3
        if error.location:
            return 0.8
        return 0.6


class CorrectionGenerator:
    def generate(self, error: DetectedError, root_cause: RootCause) -> Correction:
        actions = self._generate_actions(error, root_cause)
        code_changes = self._generate_code_changes(error, root_cause)
        description = self._generate_description(error, root_cause)

        return Correction(
            description=description,
            actions=actions,
            code_changes=code_changes,
            status=CorrectionStatus.PENDING,
        )

    def _generate_actions(self, error: DetectedError, root_cause: RootCause) -> list[str]:
        actions = list(root_cause.remediation_hints)

        if error.error_type == ErrorType.IMPORT:
            match = re.search(r"module named '(\w+)'", error.message)
            if match:
                actions.append(f"pip install {match.group(1)}")

        elif error.error_type == ErrorType.TYPE:
            if "NoneType" in error.message:
                actions.append("Add null check before operation")
            elif "not callable" in error.message:
                actions.append("Verify object is callable before invoking")

        elif error.error_type == ErrorType.RUNTIME:
            if "IndexError" in error.message:
                actions.append("Add bounds checking")
            elif "KeyError" in error.message:
                actions.append("Use dict.get() with default value")

        return actions

    def _generate_code_changes(self, error: DetectedError, root_cause: RootCause) -> list[dict[str, str]]:
        changes: list[dict[str, str]] = []

        if error.error_type == ErrorType.TYPE and "NoneType" in error.message:
            attr_match = re.search(r"attribute '(\w+)'", error.message)
            if attr_match:
                attr = attr_match.group(1)
                changes.append({
                    "type": "null_check",
                    "suggestion": f"if obj is not None:\n    obj.{attr}",
                    "reason": "Prevent operation on None",
                })

        elif error.error_type == ErrorType.RUNTIME and "KeyError" in error.message:
            key_match = re.search(r"KeyError: '?(\w+)'?", error.message)
            if key_match:
                key = key_match.group(1)
                changes.append({
                    "type": "safe_access",
                    "suggestion": f"d.get('{key}', default_value)",
                    "reason": "Use safe dictionary access",
                })

        return changes

    def _generate_description(self, error: DetectedError, root_cause: RootCause) -> str:
        return f"Fix {error.error_type.value} error: {root_cause.primary_cause}"


class VerificationLoop:
    def __init__(self, max_iterations: int = 3) -> None:
        self._max_iterations = max_iterations
        self._iteration_count = 0

    def verify(
        self,
        correction: Correction,
        test_func: Callable[[], bool] | None = None,
        validation_rules: list[Callable[[], bool]] | None = None,
    ) -> VerificationResult:
        issues: list[str] = []
        tests_passed = 0
        tests_failed = 0

        if test_func is not None:
            try:
                if test_func():
                    tests_passed += 1
                else:
                    tests_failed += 1
                    issues.append("Primary test failed")
            except Exception as exc:
                tests_failed += 1
                issues.append(f"Test raised exception: {str(exc)}")

        if validation_rules:
            for i, rule in enumerate(validation_rules):
                try:
                    if rule():
                        tests_passed += 1
                    else:
                        tests_failed += 1
                        issues.append(f"Validation rule {i + 1} failed")
                except Exception as exc:
                    tests_failed += 1
                    issues.append(f"Validation rule {i + 1} raised exception: {str(exc)}")

        is_successful = tests_failed == 0 and len(issues) == 0

        metrics = {
            "success_rate": tests_passed / max(tests_passed + tests_failed, 1),
            "iteration": self._iteration_count,
        }

        return VerificationResult(
            is_successful=is_successful,
            tests_passed=tests_passed,
            tests_failed=tests_failed,
            issues=issues,
            metrics=metrics,
        )

    def run_loop(
        self,
        correction: Correction,
        apply_func: Callable[[Correction], bool],
        verify_func: Callable[[], VerificationResult],
    ) -> VerificationResult:
        self._iteration_count = 0

        while self._iteration_count < self._max_iterations:
            self._iteration_count += 1

            if apply_func(correction):
                correction.status = CorrectionStatus.APPLIED
            else:
                correction.status = CorrectionStatus.FAILED
                return VerificationResult(
                    is_successful=False,
                    issues=["Failed to apply correction"],
                )

            result = verify_func()

            if result.is_successful:
                correction.status = CorrectionStatus.VERIFIED
                return result

        correction.status = CorrectionStatus.FAILED
        return VerificationResult(
            is_successful=False,
            issues=[f"Max iterations ({self._max_iterations}) reached without verification"],
        )


class SelfCorrectionEngine:
    def __init__(self, max_verification_iterations: int = 3) -> None:
        self._formula = "S² + R*M"
        self._capability = "self_correction_engine"

        self._error_detector = ErrorDetector()
        self._root_cause_analyzer = RootCauseAnalyzer()
        self._correction_generator = CorrectionGenerator()
        self._verification_loop = VerificationLoop(max_verification_iterations)

        self._correction_history: list[dict[str, Any]] = []

    def analyze(self, error: Exception | str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            detected_error = self._error_detector.detect(error, context)
            root_cause = self._root_cause_analyzer.analyze(detected_error)
            correction = self._correction_generator.generate(detected_error, root_cause)

            logger.info(
                "self_correction_analysis_complete",
                capability=self._capability,
                error_type=detected_error.error_type.value,
                severity=detected_error.severity.value,
                confidence=root_cause.confidence,
            )

            return {
                "status": "analyzed",
                "capability": self._capability,
                "formula": self._formula,
                "error": {
                    "type": detected_error.error_type.value,
                    "severity": detected_error.severity.value,
                    "message": detected_error.message,
                    "location": detected_error.location,
                },
                "root_cause": {
                    "primary": root_cause.primary_cause,
                    "contributing_factors": root_cause.contributing_factors,
                    "affected_components": root_cause.affected_components,
                    "confidence": root_cause.confidence,
                },
                "correction": {
                    "description": correction.description,
                    "actions": correction.actions,
                    "code_changes": correction.code_changes,
                    "status": correction.status.value,
                },
            }

        except Exception as exc:
            logger.error("self_correction_analysis_failed", capability=self._capability, error=str(exc))
            return {
                "status": "error",
                "capability": self._capability,
                "error": str(exc),
            }

    def execute(
        self,
        error: Exception | str,
        context: dict[str, Any] | None = None,
        apply_func: Callable[[Correction], bool] | None = None,
        verify_func: Callable[[], bool] | None = None,
    ) -> dict[str, Any]:
        analysis = self.analyze(error, context)

        if analysis["status"] != "analyzed":
            return analysis

        if apply_func is None or verify_func is None:
            return {
                **analysis,
                "status": "pending_manual_correction",
                "message": "Apply and verify functions required for automatic correction",
            }

        correction_data = analysis["correction"]
        correction = Correction(
            description=correction_data["description"],
            actions=correction_data["actions"],
            code_changes=correction_data["code_changes"],
            status=CorrectionStatus.PENDING,
        )

        verification_result = self._verification_loop.run_loop(
            correction,
            apply_func,
            lambda: self._verification_loop.verify(correction, verify_func),
        )

        self._correction_history.append({
            "error": analysis["error"],
            "correction": correction.description,
            "result": verification_result.is_successful,
            "iterations": self._verification_loop._iteration_count,
        })

        return {
            "status": "corrected" if verification_result.is_successful else "failed",
            "capability": self._capability,
            "formula": self._formula,
            "correction_applied": correction.status.value == CorrectionStatus.VERIFIED.value,
            "verification": {
                "is_successful": verification_result.is_successful,
                "tests_passed": verification_result.tests_passed,
                "tests_failed": verification_result.tests_failed,
                "issues": verification_result.issues,
                "iterations": self._verification_loop._iteration_count,
            },
            "actions_taken": correction.actions,
        }

    def get_correction_history(self) -> list[dict[str, Any]]:
        return self._correction_history.copy()


if __name__ == "__main__":
    import json

    engine = SelfCorrectionEngine(max_verification_iterations=3)

    test_errors = [
        (ImportError("No module named 'numpy'"), "import_error"),
        (TypeError("'NoneType' object has no attribute 'name'"), "type_error"),
        (KeyError("user_id"), "key_error"),
        (IndexError("list index out of range"), "index_error"),
        ("SyntaxError: invalid syntax on line 42", "syntax_error"),
        (RuntimeError("Connection timeout"), "runtime_error"),
    ]

    print("=" * 60)
    print("SelfCorrectionEngine Unit Tests")
    print("=" * 60)

    passed = 0
    failed = 0

    for error, expected_type in test_errors:
        result = engine.analyze(error)

        is_correct = result["status"] == "analyzed" and result["error"]["type"] != "unknown"

        status = "PASS" if is_correct else "FAIL"
        if is_correct:
            passed += 1
        else:
            failed += 1

        print(f"\n[{status}] Error: {expected_type}")
        print(f"  Type: {result['error']['type']}")
        print(f"  Severity: {result['error']['severity']}")
        print(f"  Root Cause: {result['root_cause']['primary'][:50]}...")
        print(f"  Actions: {result['correction']['actions'][:2]}")

    print("\n" + "=" * 60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 60)

    assert failed == 0, f"{failed} tests failed"
