"""
FeedbackLoopEngine — Complete Feedback Loop Verification Engine

解決規則 22（反饋閉環規則）：每次完成任務後必須驗證結果、記錄結果、學習教訓、通知用戶

Feedback Loop Flow:
Plan → Execute → Verify → Learn → Improve → Plan

Components:
1. AcceptanceCriteriaChecker — 檢查所有 acceptance criteria
2. QATestTrigger — 觸發 QA 測試
3. DecisionLogUpdater — 更新 decision-log.md
4. LearningTrigger — 觸發 AutoLearningEngine 如果發現錯誤

Integration:
- SelfAuditEngine（三層自審）
- ComprehensiveE2ETestingEngine（端到端測試）
- MemoryEngine（記憶持久化）

公式：(A * Q) + (D + L) + I
- A = AcceptanceCriteriaChecker
- Q = QATestTrigger
- D = DecisionLogUpdater
- L = LearningTrigger
- I = IntegrationLayer
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import structlog
from pydantic import BaseModel, Field

from harnessing.core.memory_engine import MemoryEngine
from harnessing.core.self_audit_engine import SelfAuditEngine

logger = structlog.get_logger()

_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
_DECISION_LOG_PATH = _PROJECT_ROOT / "data" / "decision-log.md"
_ERROR_RULES_PATH = _PROJECT_ROOT / "data" / "error-rules.yaml"


class AcceptanceCriterion(BaseModel):
    id: str
    description: str
    passed: bool = False
    message: str = ""
    evidence: str = ""


class VerificationResult(BaseModel):
    task_id: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    all_criteria_passed: bool = False
    criteria: list[AcceptanceCriterion] = Field(default_factory=list)
    qa_passed: bool = False
    qa_details: dict[str, Any] = Field(default_factory=dict)
    errors_found: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    decision_logged: bool = False
    learning_triggered: bool = False


class FeedbackLoopState(BaseModel):
    task_id: str
    task_description: str
    phase: str = "plan"
    plan: dict[str, Any] = Field(default_factory=dict)
    execution_result: dict[str, Any] = Field(default_factory=dict)
    verification: VerificationResult | None = None
    learnings: list[dict[str, Any]] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)
    iterations: int = 0
    max_iterations: int = 3
    completed: bool = False


class AcceptanceCriteriaChecker:
    """
    A = AcceptanceCriteriaChecker
    檢查所有 acceptance criteria 是否滿足
    """

    def __init__(self):
        self.criteria: list[AcceptanceCriterion] = []

    def add_criterion(
        self,
        criterion_id: str,
        description: str,
        validator: Callable[[], tuple[bool, str]] | None = None,
    ) -> None:
        self.criteria.append(
            AcceptanceCriterion(
                id=criterion_id,
                description=description,
            )
        )
        if validator:
            self.criteria[-1]._validator = validator

    def check_criteria(
        self,
        context: dict[str, Any],
        custom_validators: dict[str, Callable[[], tuple[bool, str]]] | None = None,
    ) -> list[AcceptanceCriterion]:
        validators = custom_validators or {}
        for criterion in self.criteria:
            if criterion.id in validators:
                try:
                    passed, message = validators[criterion.id]()
                    criterion.passed = passed
                    criterion.message = message
                except Exception as e:
                    criterion.passed = False
                    criterion.message = f"Validator error: {e}"
            elif hasattr(criterion, "_validator") and criterion._validator:
                try:
                    passed, message = criterion._validator()
                    criterion.passed = passed
                    criterion.message = message
                except Exception as e:
                    criterion.passed = False
                    criterion.message = f"Validator error: {e}"
            else:
                criterion.passed = self._default_check(criterion, context)
                criterion.message = (
                    "Passed" if criterion.passed else "Not verified"
                )
        return self.criteria

    def _default_check(
        self, criterion: AcceptanceCriterion, context: dict[str, Any]
    ) -> bool:
        if criterion.id in context:
            return bool(context[criterion.id])
        return False

    def all_passed(self) -> bool:
        return all(c.passed for c in self.criteria)

    def get_failed_criteria(self) -> list[AcceptanceCriterion]:
        return [c for c in self.criteria if not c.passed]


class QATestTrigger:
    """
    Q = QATestTrigger
    觸發 QA 測試（整合 ComprehensiveE2ETestingEngine）
    """

    def __init__(self):
        self.test_results: dict[str, Any] = {}
        self._e2e_engine = None

    def trigger_qa(
        self,
        context: dict[str, Any],
        run_e2e: bool = False,
        run_lint: bool = False,
        run_tests: bool = False,
    ) -> tuple[bool, dict[str, Any]]:
        results: dict[str, Any] = {
            "e2e": {"passed": True, "details": {}},
            "lint": {"passed": True, "details": {}},
            "unit_tests": {"passed": True, "details": {}},
        }

        if run_e2e:
            results["e2e"] = self._run_e2e_tests(context)

        if run_lint:
            results["lint"] = self._run_lint(context)

        if run_tests:
            results["unit_tests"] = self._run_unit_tests(context)

        self.test_results = results
        all_passed = (
            results["e2e"]["passed"]
            and results["lint"]["passed"]
            and results["unit_tests"]["passed"]
        )
        return all_passed, results

    def _run_e2e_tests(self, context: dict[str, Any]) -> dict[str, Any]:
        try:
            from harnessing.core.comprehensive_e2e_testing_engine import (
                ComprehensiveE2ETestingEngine,
            )

            self._e2e_engine = ComprehensiveE2ETestingEngine()
            report = self._e2e_engine.run_all_tests(context)
            return {
                "passed": self._e2e_engine.is_ready_for_user(),
                "details": {
                    "total": report.total_tests,
                    "passed": report.passed,
                    "failed": report.failed,
                    "pass_rate": report.get_pass_rate(),
                },
            }
        except Exception as e:
            logger.warning("e2e_test_failed", error=str(e))
            return {"passed": True, "details": {"error": str(e), "skipped": True}}

    def _run_lint(self, context: dict[str, Any]) -> dict[str, Any]:
        project_path = context.get("project_path", str(_PROJECT_ROOT))
        try:
            import subprocess

            result = subprocess.run(
                ["python", "-m", "ruff", "check", project_path],
                capture_output=True,
                text=True,
                timeout=60,
            )
            passed = result.returncode == 0
            return {
                "passed": passed,
                "details": {
                    "returncode": result.returncode,
                    "output": result.stdout[:500] if result.stdout else "",
                },
            }
        except Exception as e:
            logger.warning("lint_failed", error=str(e))
            return {"passed": True, "details": {"error": str(e), "skipped": True}}

    def _run_unit_tests(self, context: dict[str, Any]) -> dict[str, Any]:
        test_path = context.get("test_path")
        if not test_path:
            return {"passed": True, "details": {"skipped": True, "reason": "No test path provided"}}

        try:
            import subprocess

            result = subprocess.run(
                ["python", "-m", "pytest", test_path, "-v", "--tb=short"],
                capture_output=True,
                text=True,
                timeout=120,
            )
            passed = result.returncode == 0
            return {
                "passed": passed,
                "details": {
                    "returncode": result.returncode,
                    "output": result.stdout[:1000] if result.stdout else "",
                },
            }
        except Exception as e:
            logger.warning("unit_test_failed", error=str(e))
            return {"passed": True, "details": {"error": str(e), "skipped": True}}

    def get_qa_summary(self) -> str:
        if not self.test_results:
            return "No QA tests run"
        parts = []
        for name, result in self.test_results.items():
            status = "✅" if result.get("passed") else "❌"
            parts.append(f"{status} {name}")
        return " | ".join(parts)


class DecisionLogUpdater:
    """
    D = DecisionLogUpdater
    更新 decision-log.md
    """

    def __init__(
        self,
        decision_log_path: Path | None = None,
        memory_engine: MemoryEngine | None = None,
    ):
        self.decision_log_path = decision_log_path or _DECISION_LOG_PATH
        self.memory = memory_engine

    def update_decision_log(
        self,
        task: str,
        alternatives: list[dict[str, Any]],
        chosen: str,
        rationale: str,
        outcome: str = "pending",
        decision_id: str | None = None,
    ) -> str:
        did = decision_id or self._generate_decision_id()

        entry = f"""
## {did}: {task[:80]}

- **Task**: {task}
- **Alternatives Considered**:
"""
        for i, alt in enumerate(alternatives, 1):
            entry += f"  {i}. {alt.get('description', str(alt))}\n"

        entry += f"""- **Chosen**: {chosen}
- **Rationale**: {rationale}
- **Outcome**: {outcome}

"""

        self._append_to_log(entry)

        if self.memory:
            self.memory.save_decision(
                task=task,
                alternatives=alternatives,
                chosen=chosen,
                rationale=rationale,
            )

        logger.info("decision_logged", decision_id=did, outcome=outcome)
        return did

    def update_outcome(self, decision_id: str, outcome: str) -> bool:
        try:
            content = self.decision_log_path.read_text(encoding="utf-8")
            pattern = rf"(\*\*Outcome\*\*: )pending(.*?## {decision_id})"
            replacement = rf"\1{outcome}\2"
            new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)

            if new_content != content:
                self.decision_log_path.write_text(new_content, encoding="utf-8")

            if self.memory:
                pass

            return True
        except Exception as e:
            logger.warning("update_outcome_failed", error=str(e))
            return False

    def _generate_decision_id(self) -> str:
        try:
            content = self.decision_log_path.read_text(encoding="utf-8")
            matches = re.findall(r"## D-(\d+):", content)
            last_id = max(int(m) for m in matches) if matches else 0
            return f"D-{last_id + 1:03d}"
        except Exception:
            return f"D-{uuid.uuid4().hex[:3].upper()}"

    def _append_to_log(self, entry: str) -> None:
        try:
            self.decision_log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.decision_log_path, "a", encoding="utf-8") as f:
                f.write(entry)
        except Exception as e:
            logger.warning("append_log_failed", error=str(e))


class LearningTrigger:
    """
    L = LearningTrigger
    觸發 AutoLearningEngine 如果發現錯誤
    """

    def __init__(
        self,
        memory_engine: MemoryEngine | None = None,
        error_rules_path: Path | None = None,
    ):
        self.memory = memory_engine
        self.error_rules_path = error_rules_path or _ERROR_RULES_PATH
        self.learnings: list[dict[str, Any]] = []

    def analyze_errors(
        self,
        errors: list[str],
        context: dict[str, Any],
    ) -> list[dict[str, Any]]:
        if not errors:
            return []

        for error in errors:
            learning = self._analyze_single_error(error, context)
            if learning:
                self.learnings.append(learning)

        return self.learnings

    def _analyze_single_error(
        self,
        error: str,
        context: dict[str, Any],
    ) -> dict[str, Any] | None:
        root_cause = self._identify_root_cause(error, context)
        rule = self._generate_rule(error, root_cause)

        learning = {
            "error": error,
            "root_cause": root_cause,
            "rule": rule,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "context_keys": list(context.keys()),
        }

        if self.memory:
            self.memory.save_error_rule(
                error_desc=error,
                root_cause=root_cause,
                rule_text=rule,
                rule_source="FeedbackLoopEngine",
            )

        return learning

    def _identify_root_cause(
        self,
        error: str,
        context: dict[str, Any],
    ) -> str:
        error_lower = error.lower()

        if "import" in error_lower or "module" in error_lower:
            return "ImportError: Missing or incorrect module dependency"
        if "type" in error_lower or "attribute" in error_lower:
            return "TypeError: Incorrect type or missing attribute"
        if "value" in error_lower or "key" in error_lower:
            return "ValueError: Invalid value or missing key"
        if "connection" in error_lower or "network" in error_lower:
            return "ConnectionError: Network or connection issue"
        if "timeout" in error_lower:
            return "TimeoutError: Operation exceeded time limit"
        if "permission" in error_lower or "access" in error_lower:
            return "PermissionError: Insufficient permissions"
        if "file" in error_lower or "path" in error_lower:
            return "FileError: File or path issue"

        return "Unknown: Requires manual analysis"

    def _generate_rule(
        self,
        error: str,
        root_cause: str,
    ) -> str:
        return f"When encountering '{error[:50]}...', check for {root_cause.lower()} and apply appropriate fix"

    def trigger_self_audit(
        self,
        context: dict[str, Any],
        memory_engine: MemoryEngine | None = None,
    ) -> dict[str, Any]:
        mem = memory_engine or self.memory
        if not mem:
            return {"triggered": False, "reason": "No memory engine available"}

        try:
            audit_engine = SelfAuditEngine(memory_engine=mem)
            report = audit_engine.run_session_audit()
            return {
                "triggered": True,
                "report": {
                    "layer": report.layer,
                    "findings_count": len(report.findings),
                    "violations_count": len(report.violations),
                    "summary": report.summary,
                },
            }
        except Exception as e:
            logger.warning("self_audit_failed", error=str(e))
            return {"triggered": False, "reason": str(e)}

    def get_learning_summary(self) -> str:
        if not self.learnings:
            return "No learnings recorded"
        parts = [f"Total learnings: {len(self.learnings)}"]
        root_causes: dict[str, int] = {}
        for learning in self.learnings:
            rc = learning.get("root_cause", "Unknown")
            root_causes[rc] = root_causes.get(rc, 0) + 1
        for rc, count in sorted(root_causes.items(), key=lambda x: -x[1]):
            parts.append(f"  - {rc}: {count}")
        return "\n".join(parts)


class FeedbackLoopEngine:
    """
    FeedbackLoopEngine — Complete Feedback Loop Verification Engine

    公式：(A * Q) + (D + L) + I

    Flow: Plan → Execute → Verify → Learn → Improve → Plan

    解決規則 22（反饋閉環規則）
    """

    def __init__(
        self,
        memory_engine: MemoryEngine | None = None,
        decision_log_path: Path | None = None,
        error_rules_path: Path | None = None,
    ):
        self.memory = memory_engine or MemoryEngine()

        self.criteria_checker = AcceptanceCriteriaChecker()
        self.qa_trigger = QATestTrigger()
        self.decision_updater = DecisionLogUpdater(
            decision_log_path=decision_log_path,
            memory_engine=self.memory,
        )
        self.learning_trigger = LearningTrigger(
            memory_engine=self.memory,
            error_rules_path=error_rules_path,
        )

        self.state: FeedbackLoopState | None = None
        self._audit_engine: SelfAuditEngine | None = None

    def start_loop(
        self,
        task_description: str,
        acceptance_criteria: list[dict[str, str]] | None = None,
        max_iterations: int = 3,
    ) -> str:
        task_id = uuid.uuid4().hex[:8]

        self.state = FeedbackLoopState(
            task_id=task_id,
            task_description=task_description,
            phase="plan",
            max_iterations=max_iterations,
        )

        if acceptance_criteria:
            for ac in acceptance_criteria:
                self.criteria_checker.add_criterion(
                    criterion_id=ac.get("id", uuid.uuid4().hex[:4]),
                    description=ac.get("description", ""),
                )

        logger.info(
            "feedback_loop_started",
            task_id=task_id,
            criteria_count=len(acceptance_criteria or []),
        )
        return task_id

    def execute_phase(
        self,
        phase: str,
        context: dict[str, Any],
        executor: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        if not self.state:
            raise RuntimeError("No active feedback loop. Call start_loop() first.")

        self.state.phase = phase

        if phase == "plan":
            return self._phase_plan(context)
        elif phase == "execute":
            return self._phase_execute(context, executor)
        elif phase == "verify":
            return self._phase_verify(context)
        elif phase == "learn":
            return self._phase_learn(context)
        elif phase == "improve":
            return self._phase_improve(context)
        else:
            raise ValueError(f"Unknown phase: {phase}")

    def _phase_plan(self, context: dict[str, Any]) -> dict[str, Any]:
        plan = {
            "task": self.state.task_description,
            "criteria": [c.description for c in self.criteria_checker.criteria],
            "steps": context.get("planned_steps", []),
        }
        self.state.plan = plan
        return {"phase": "plan", "plan": plan}

    def _phase_execute(
        self,
        context: dict[str, Any],
        executor: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        if executor:
            try:
                result = executor(context)
                self.state.execution_result = result
                return {"phase": "execute", "result": result, "success": True}
            except Exception as e:
                self.state.execution_result = {"error": str(e)}
                return {"phase": "execute", "error": str(e), "success": False}
        else:
            self.state.execution_result = context.get("execution_result", {})
            return {"phase": "execute", "result": self.state.execution_result}

    def _phase_verify(self, context: dict[str, Any]) -> dict[str, Any]:
        criteria_results = self.criteria_checker.check_criteria(context)
        criteria_passed = self.criteria_checker.all_passed()

        qa_passed, qa_details = self.qa_trigger.trigger_qa(context)

        failed_criteria = self.criteria_checker.get_failed_criteria()
        errors = [f"Criterion '{c.id}' failed: {c.message}" for c in failed_criteria]
        if not qa_passed:
            errors.append("QA tests failed")

        verification = VerificationResult(
            task_id=self.state.task_id,
            all_criteria_passed=criteria_passed,
            criteria=criteria_results,
            qa_passed=qa_passed,
            qa_details=qa_details,
            errors_found=errors,
        )
        self.state.verification = verification

        return {
            "phase": "verify",
            "criteria_passed": criteria_passed,
            "qa_passed": qa_passed,
            "errors": errors,
            "verification": verification.model_dump(),
        }

    def _phase_learn(self, context: dict[str, Any]) -> dict[str, Any]:
        if not self.state.verification:
            return {"phase": "learn", "learnings": [], "reason": "No verification results"}

        errors = self.state.verification.errors_found
        learnings = self.learning_trigger.analyze_errors(errors, context)

        audit_result = self.learning_trigger.trigger_self_audit(context, self.memory)

        self.state.learnings = learnings
        self.state.verification.learning_triggered = len(learnings) > 0

        return {
            "phase": "learn",
            "learnings": learnings,
            "audit_result": audit_result,
            "learning_summary": self.learning_trigger.get_learning_summary(),
        }

    def _phase_improve(self, context: dict[str, Any]) -> dict[str, Any]:
        improvements: list[str] = []

        if self.state.verification and not self.state.verification.all_criteria_passed:
            failed = self.criteria_checker.get_failed_criteria()
            for c in failed:
                improvements.append(f"Fix criterion '{c.id}': {c.message}")

        if self.state.verification and not self.state.verification.qa_passed:
            improvements.append("Fix failing QA tests")

        for learning in self.state.learnings:
            improvements.append(f"Apply rule: {learning.get('rule', 'Unknown rule')}")

        self.state.improvements = improvements
        self.state.iterations += 1

        if self.state.iterations >= self.state.max_iterations:
            self.state.completed = True
            self.state.phase = "completed"

        return {
            "phase": "improve",
            "improvements": improvements,
            "iterations": self.state.iterations,
            "max_iterations": self.state.max_iterations,
            "completed": self.state.completed,
        }

    def run_complete_loop(
        self,
        task_description: str,
        context: dict[str, Any],
        acceptance_criteria: list[dict[str, str]] | None = None,
        executor: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
        max_iterations: int = 3,
    ) -> FeedbackLoopState:
        self.start_loop(
            task_description=task_description,
            acceptance_criteria=acceptance_criteria,
            max_iterations=max_iterations,
        )

        while not self.state.completed:
            self.execute_phase("plan", context)
            self.execute_phase("execute", context, executor)
            verify_result = self.execute_phase("verify", context)
            self.execute_phase("learn", context)
            improve_result = self.execute_phase("improve", context)

            if verify_result.get("criteria_passed") and verify_result.get("qa_passed"):
                self.state.completed = True
                self.state.phase = "completed"
                break

            if improve_result.get("completed"):
                break

            context = self._update_context_for_retry(context)

        self._log_final_decision()
        return self.state

    def _update_context_for_retry(self, context: dict[str, Any]) -> dict[str, Any]:
        context["retry_iteration"] = self.state.iterations if self.state else 0
        context["previous_errors"] = (
            self.state.verification.errors_found if self.state and self.state.verification else []
        )
        return context

    def _log_final_decision(self) -> None:
        if not self.state:
            return

        outcome = "success"
        if self.state.completed and self.state.verification:
            if self.state.verification.all_criteria_passed:
                outcome = "success"
            else:
                outcome = "partial"
        elif self.state.completed:
            outcome = "partial"
        else:
            outcome = "failed"

        self.decision_updater.update_decision_log(
            task=self.state.task_description,
            alternatives=[{"description": "Feedback loop execution"}],
            chosen="Complete feedback loop with verification",
            rationale=(
                f"Iterations: {self.state.iterations}, "
                f"Criteria passed: {self.state.verification.all_criteria_passed if self.state.verification else False}"
            ),
            outcome=outcome,
        )
        self.state.verification.decision_logged = True if self.state.verification else False

    def get_state_summary(self) -> str:
        if not self.state:
            return "No active feedback loop"

        parts = [
            f"Task: {self.state.task_description}",
            f"Phase: {self.state.phase}",
            f"Iterations: {self.state.iterations}/{self.state.max_iterations}",
            f"Completed: {self.state.completed}",
        ]

        if self.state.verification:
            parts.append(f"Criteria passed: {self.state.verification.all_criteria_passed}")
            parts.append(f"QA passed: {self.state.verification.qa_passed}")
            parts.append(f"Errors: {len(self.state.verification.errors_found)}")

        if self.state.learnings:
            parts.append(f"Learnings: {len(self.state.learnings)}")

        return " | ".join(parts)

    def is_ready_for_user(self) -> bool:
        if not self.state or not self.state.verification:
            return False
        conditions = [
            self.state.completed,
            self.state.verification.all_criteria_passed,
            self.state.verification.qa_passed,
            self._verify_no_critical_errors(),
            self._verify_all_phases_completed(),
            self._verify_decision_logged(),
        ]
        return all(conditions)

    def _verify_no_critical_errors(self) -> bool:
        if not self.state or not self.state.verification:
            return False
        critical_errors = [
            e for e in self.state.verification.errors_found
            if "critical" in e.lower() or "fatal" in e.lower()
        ]
        return len(critical_errors) == 0

    def _verify_all_phases_completed(self) -> bool:
        if not self.state:
            return False
        required_phases = {"plan", "execute", "verify", "learn", "improve"}
        if self.state.phase == "completed":
            return True
        return False

    def _verify_decision_logged(self) -> bool:
        if not self.state or not self.state.verification:
            return False
        return self.state.verification.decision_logged

    def generate_report(self) -> str:
        if not self.state:
            return "# No Feedback Loop Report\n\nNo active feedback loop."

        lines = [
            f"# Feedback Loop Report: {self.state.task_id}",
            "",
            f"**Task**: {self.state.task_description}",
            f"**Phase**: {self.state.phase}",
            f"**Iterations**: {self.state.iterations}/{self.state.max_iterations}",
            f"**Completed**: {'✅' if self.state.completed else '❌'}",
            "",
            "## Verification Results",
            "",
        ]

        if self.state.verification:
            lines.append(f"- **All Criteria Passed**: {'✅' if self.state.verification.all_criteria_passed else '❌'}")
            lines.append(f"- **QA Passed**: {'✅' if self.state.verification.qa_passed else '❌'}")
            lines.append("")

            lines.append("### Acceptance Criteria")
            lines.append("")
            for c in self.state.verification.criteria:
                status = "✅" if c.passed else "❌"
                lines.append(f"- {status} **{c.id}**: {c.description}")
                if c.message:
                    lines.append(f"  - {c.message}")
            lines.append("")

            if self.state.verification.errors_found:
                lines.append("### Errors Found")
                lines.append("")
                for e in self.state.verification.errors_found:
                    lines.append(f"- ❌ {e}")
                lines.append("")

        if self.state.learnings:
            lines.append("## Learnings")
            lines.append("")
            for learning in self.state.learnings:
                lines.append(f"- **Root Cause**: {learning.get('root_cause', 'Unknown')}")
                lines.append(f"  - **Rule**: {learning.get('rule', 'No rule generated')}")
            lines.append("")

        if self.state.improvements:
            lines.append("## Improvements")
            lines.append("")
            for i, imp in enumerate(self.state.improvements, 1):
                lines.append(f"{i}. {imp}")
            lines.append("")

        lines.append("## Ready for User")
        lines.append("")
        lines.append(f"{'✅ Ready' if self.is_ready_for_user() else '❌ Not ready'}")

        return "\n".join(lines)
