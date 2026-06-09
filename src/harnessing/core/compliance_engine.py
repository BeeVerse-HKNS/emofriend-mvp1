from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class Severity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ComplianceStatus(Enum):
    COMPLIANT = "compliant"
    VIOLATION = "violation"


class EnforcementResult(Enum):
    ALLOWED = "allowed"
    BLOCKED = "blocked"


@dataclass
class Policy:
    policy_id: str
    name: str
    description: str
    rules: List[Dict[str, Any]]
    severity: Severity
    category: str = "general"
    enabled: bool = True
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class AuditEntry:
    timestamp: str
    event_type: str
    actor: str
    action: str
    resource: str
    result: str
    details: Optional[Dict[str, Any]] = None


@dataclass
class Violation:
    violation_id: str
    policy_id: str
    rule_id: str
    operation: str
    context: Dict[str, Any]
    severity: Severity
    timestamp: str
    reason: str


class PolicyStore:
    def __init__(self) -> None:
        self._policies: Dict[str, Policy] = {}

    def add_policy(
        self,
        policy_id: str,
        name: str,
        description: str,
        rules: List[Dict[str, Any]],
        severity: Severity,
        category: str = "general",
    ) -> Policy:
        policy = Policy(
            policy_id=policy_id,
            name=name,
            description=description,
            rules=rules,
            severity=severity,
            category=category,
        )
        self._policies[policy_id] = policy
        return policy

    def get_policy(self, policy_id: str) -> Optional[Policy]:
        return self._policies.get(policy_id)

    def list_policies(self, category: Optional[str] = None) -> List[Policy]:
        policies = list(self._policies.values())
        if category is not None:
            policies = [p for p in policies if p.category == category]
        return policies

    def remove_policy(self, policy_id: str) -> bool:
        if policy_id in self._policies:
            del self._policies[policy_id]
            return True
        return False

    def evaluate_policy(self, policy_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        policy = self._policies.get(policy_id)
        if policy is None:
            return {
                "policy_id": policy_id,
                "status": ComplianceStatus.VIOLATION.value,
                "reason": "Policy not found",
                "violated_rules": [],
            }
        if not policy.enabled:
            return {
                "policy_id": policy_id,
                "status": ComplianceStatus.COMPLIANT.value,
                "reason": "Policy is disabled",
                "violated_rules": [],
            }
        violated_rules = []
        for rule in policy.rules:
            rule_id = rule.get("rule_id", "unknown")
            field_name = rule.get("field")
            operator = rule.get("operator", "eq")
            expected = rule.get("value")
            actual = context.get(field_name)
            if not self._check_rule(operator, actual, expected):
                violated_rules.append({
                    "rule_id": rule_id,
                    "field": field_name,
                    "expected": expected,
                    "actual": actual,
                    "operator": operator,
                })
        status = ComplianceStatus.COMPLIANT.value if not violated_rules else ComplianceStatus.VIOLATION.value
        return {
            "policy_id": policy_id,
            "status": status,
            "severity": policy.severity.value,
            "violated_rules": violated_rules,
            "reason": f"{len(violated_rules)} rule(s) violated" if violated_rules else "All rules passed",
        }

    def _check_rule(self, operator: str, actual: Any, expected: Any) -> bool:
        if operator == "eq":
            return actual == expected
        elif operator == "neq":
            return actual != expected
        elif operator == "in":
            return actual in expected if expected else False
        elif operator == "not_in":
            return actual not in expected if expected else True
        elif operator == "contains":
            return expected in actual if actual is not None else False
        elif operator == "gt":
            return actual > expected if actual is not None else False
        elif operator == "lt":
            return actual < expected if actual is not None else False
        elif operator == "gte":
            return actual >= expected if actual is not None else False
        elif operator == "lte":
            return actual <= expected if actual is not None else False
        elif operator == "exists":
            return actual is not None
        elif operator == "not_exists":
            return actual is None
        elif operator == "regex_match":
            import re
            return bool(re.match(expected, str(actual))) if actual is not None else False
        return False


class AuditLogger:
    def __init__(self) -> None:
        self._logs: List[AuditEntry] = []
        self._resource_index: Dict[str, List[int]] = defaultdict(list)

    def log_event(
        self,
        event_type: str,
        actor: str,
        action: str,
        resource: str,
        result: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditEntry:
        entry = AuditEntry(
            timestamp=datetime.now().isoformat(),
            event_type=event_type,
            actor=actor,
            action=action,
            resource=resource,
            result=result,
            details=details,
        )
        idx = len(self._logs)
        self._logs.append(entry)
        self._resource_index[resource].append(idx)
        return entry

    def query_logs(self, filter_dict: Dict[str, Any]) -> List[AuditEntry]:
        results = []
        for entry in self._logs:
            match = True
            for key, value in filter_dict.items():
                if hasattr(entry, key):
                    if getattr(entry, key) != value:
                        match = False
                        break
                elif entry.details and key in entry.details:
                    if entry.details[key] != value:
                        match = False
                        break
                else:
                    match = False
                    break
            if match:
                results.append(entry)
        return results

    def get_audit_trail(self, resource: str) -> List[AuditEntry]:
        indices = self._resource_index.get(resource, [])
        return [self._logs[i] for i in indices]

    def export_logs(self, format: str = "dict") -> Any:
        if format == "dict":
            return [
                {
                    "timestamp": e.timestamp,
                    "event_type": e.event_type,
                    "actor": e.actor,
                    "action": e.action,
                    "resource": e.resource,
                    "result": e.result,
                    "details": e.details,
                }
                for e in self._logs
            ]
        elif format == "json":
            entries = [
                {
                    "timestamp": e.timestamp,
                    "event_type": e.event_type,
                    "actor": e.actor,
                    "action": e.action,
                    "resource": e.resource,
                    "result": e.result,
                    "details": e.details,
                }
                for e in self._logs
            ]
            return json.dumps(entries, indent=2, ensure_ascii=False)
        return []


class ComplianceChecker:
    def __init__(self, policy_store: PolicyStore, audit_logger: AuditLogger) -> None:
        self._policy_store = policy_store
        self._audit_logger = audit_logger
        self._rules: Dict[str, Dict[str, Any]] = {}
        self._violations: List[Violation] = []
        self._total_checks: int = 0
        self._compliant_checks: int = 0

    def register_rule(self, rule_id: str, check_fn: Callable, policy_id: str) -> None:
        self._rules[rule_id] = {
            "check_fn": check_fn,
            "policy_id": policy_id,
        }

    def check_operation(
        self, operation: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        self._total_checks += 1
        violations_found = []
        for rule_id, rule_data in self._rules.items():
            policy = self._policy_store.get_policy(rule_data["policy_id"])
            if policy is None or not policy.enabled:
                continue
            try:
                passed = rule_data["check_fn"](context)
            except Exception:
                passed = False
            if not passed:
                violation = Violation(
                    violation_id=f"V-{len(self._violations) + 1:04d}",
                    policy_id=rule_data["policy_id"],
                    rule_id=rule_id,
                    operation=operation,
                    context=context,
                    severity=policy.severity,
                    timestamp=datetime.now().isoformat(),
                    reason=f"Rule {rule_id} failed for operation {operation}",
                )
                self._violations.append(violation)
                violations_found.append(violation)

        if violations_found:
            result = EnforcementResult.BLOCKED.value
            reasons = [v.reason for v in violations_found]
            self._audit_logger.log_event(
                event_type="compliance_check",
                actor=context.get("actor", "system"),
                action=operation,
                resource=context.get("resource", "unknown"),
                result="blocked",
                details={"violations": [v.violation_id for v in violations_found]},
            )
        else:
            result = EnforcementResult.ALLOWED.value
            reasons = []
            self._compliant_checks += 1
            self._audit_logger.log_event(
                event_type="compliance_check",
                actor=context.get("actor", "system"),
                action=operation,
                resource=context.get("resource", "unknown"),
                result="allowed",
            )

        return {
            "operation": operation,
            "result": result,
            "reasons": reasons,
            "violations_count": len(violations_found),
        }

    def get_violations(self) -> List[Dict[str, Any]]:
        return [
            {
                "violation_id": v.violation_id,
                "policy_id": v.policy_id,
                "rule_id": v.rule_id,
                "operation": v.operation,
                "severity": v.severity.value,
                "timestamp": v.timestamp,
                "reason": v.reason,
            }
            for v in self._violations
        ]

    def get_compliance_score(self) -> float:
        if self._total_checks == 0:
            return 100.0
        return round((self._compliant_checks / self._total_checks) * 100, 2)


class ComplianceEngine:
    def __init__(self) -> None:
        self.policy_store = PolicyStore()
        self.audit_logger = AuditLogger()
        self.checker = ComplianceChecker(self.policy_store, self.audit_logger)
        self._register_default_policies()

    def _register_default_policies(self) -> None:
        self.policy_store.add_policy(
            policy_id="data_sovereignty",
            name="Data Sovereignty Policy",
            description="Ensures data remains within specified jurisdictions",
            rules=[
                {"rule_id": "ds-001", "field": "data_location", "operator": "in", "value": ["HK", "EU", "US"]},
                {"rule_id": "ds-002", "field": "cross_border_transfer", "operator": "eq", "value": False},
            ],
            severity=Severity.HIGH,
            category="data_governance",
        )
        self.policy_store.add_policy(
            policy_id="retention",
            name="Data Retention Policy",
            description="Enforces data retention and deletion schedules",
            rules=[
                {"rule_id": "rt-001", "field": "retention_days", "operator": "lte", "value": 365},
                {"rule_id": "rt-002", "field": "auto_delete", "operator": "eq", "value": True},
            ],
            severity=Severity.MEDIUM,
            category="data_governance",
        )
        self.policy_store.add_policy(
            policy_id="access_control",
            name="Access Control Policy",
            description="Manages access permissions and authentication",
            rules=[
                {"rule_id": "ac-001", "field": "authenticated", "operator": "eq", "value": True},
                {"rule_id": "ac-002", "field": "role", "operator": "in", "value": ["admin", "editor", "viewer"]},
                {"rule_id": "ac-003", "field": "mfa_enabled", "operator": "eq", "value": True},
            ],
            severity=Severity.CRITICAL,
            category="security",
        )
        self.policy_store.add_policy(
            policy_id="gdpr",
            name="GDPR Compliance Policy",
            description="General Data Protection Regulation compliance",
            rules=[
                {"rule_id": "gdpr-001", "field": "consent_given", "operator": "eq", "value": True},
                {"rule_id": "gdpr-002", "field": "data_minimization", "operator": "eq", "value": True},
                {"rule_id": "gdpr-003", "field": "right_to_erasure", "operator": "eq", "value": True},
                {"rule_id": "gdpr-004", "field": "dpo_appointed", "operator": "eq", "value": True},
            ],
            severity=Severity.CRITICAL,
            category="privacy",
        )
        self.policy_store.add_policy(
            policy_id="pipa",
            name="PIPA Compliance Policy",
            description="Personal Data (Privacy) Ordinance - Hong Kong compliance",
            rules=[
                {"rule_id": "pipa-001", "field": "purpose_specified", "operator": "eq", "value": True},
                {"rule_id": "pipa-002", "field": "lawful_collection", "operator": "eq", "value": True},
                {"rule_id": "pipa-003", "field": "data_accuracy", "operator": "eq", "value": True},
                {"rule_id": "pipa-004", "field": "retention_limit", "operator": "eq", "value": True},
            ],
            severity=Severity.HIGH,
            category="privacy",
        )

        self.checker.register_rule(
            rule_id="ds-001",
            check_fn=lambda ctx: ctx.get("data_location") in ["HK", "EU", "US"],
            policy_id="data_sovereignty",
        )
        self.checker.register_rule(
            rule_id="ds-002",
            check_fn=lambda ctx: ctx.get("cross_border_transfer") is False,
            policy_id="data_sovereignty",
        )
        self.checker.register_rule(
            rule_id="rt-001",
            check_fn=lambda ctx: ctx.get("retention_days", 999) <= 365,
            policy_id="retention",
        )
        self.checker.register_rule(
            rule_id="rt-002",
            check_fn=lambda ctx: ctx.get("auto_delete") is True,
            policy_id="retention",
        )
        self.checker.register_rule(
            rule_id="ac-001",
            check_fn=lambda ctx: ctx.get("authenticated") is True,
            policy_id="access_control",
        )
        self.checker.register_rule(
            rule_id="ac-002",
            check_fn=lambda ctx: ctx.get("role") in ["admin", "editor", "viewer"],
            policy_id="access_control",
        )
        self.checker.register_rule(
            rule_id="ac-003",
            check_fn=lambda ctx: ctx.get("mfa_enabled") is True,
            policy_id="access_control",
        )
        self.checker.register_rule(
            rule_id="gdpr-001",
            check_fn=lambda ctx: ctx.get("consent_given") is True,
            policy_id="gdpr",
        )
        self.checker.register_rule(
            rule_id="gdpr-002",
            check_fn=lambda ctx: ctx.get("data_minimization") is True,
            policy_id="gdpr",
        )
        self.checker.register_rule(
            rule_id="gdpr-003",
            check_fn=lambda ctx: ctx.get("right_to_erasure") is True,
            policy_id="gdpr",
        )
        self.checker.register_rule(
            rule_id="gdpr-004",
            check_fn=lambda ctx: ctx.get("dpo_appointed") is True,
            policy_id="gdpr",
        )
        self.checker.register_rule(
            rule_id="pipa-001",
            check_fn=lambda ctx: ctx.get("purpose_specified") is True,
            policy_id="pipa",
        )
        self.checker.register_rule(
            rule_id="pipa-002",
            check_fn=lambda ctx: ctx.get("lawful_collection") is True,
            policy_id="pipa",
        )
        self.checker.register_rule(
            rule_id="pipa-003",
            check_fn=lambda ctx: ctx.get("data_accuracy") is True,
            policy_id="pipa",
        )
        self.checker.register_rule(
            rule_id="pipa-004",
            check_fn=lambda ctx: ctx.get("retention_limit") is True,
            policy_id="pipa",
        )

    def enforce_compliance(
        self, operation: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        policy_results = {}
        for policy in self.policy_store.list_policies():
            evaluation = self.policy_store.evaluate_policy(policy.policy_id, context)
            policy_results[policy.policy_id] = evaluation

        check_result = self.checker.check_operation(operation, context)

        return {
            "operation": operation,
            "enforcement": check_result["result"],
            "reasons": check_result["reasons"],
            "policy_evaluations": policy_results,
            "violations_count": check_result["violations_count"],
        }

    def run_compliance_audit(self) -> Dict[str, Any]:
        audit_results = {}
        total_policies = 0
        compliant_policies = 0
        for policy in self.policy_store.list_policies():
            total_policies += 1
            evaluation = self.policy_store.evaluate_policy(policy.policy_id, {})
            audit_results[policy.policy_id] = {
                "name": policy.name,
                "severity": policy.severity.value,
                "category": policy.category,
                "enabled": policy.enabled,
                "rules_count": len(policy.rules),
            }
            if evaluation["status"] == ComplianceStatus.COMPLIANT.value:
                compliant_policies += 1

        violations = self.checker.get_violations()
        compliance_score = self.checker.get_compliance_score()

        return {
            "audit_timestamp": datetime.now().isoformat(),
            "total_policies": total_policies,
            "compliant_policies": compliant_policies,
            "compliance_score": compliance_score,
            "total_violations": len(violations),
            "violations_by_severity": self._count_violations_by_severity(violations),
            "policy_details": audit_results,
            "recent_violations": violations[-10:] if violations else [],
        }

    def get_compliance_status(self) -> Dict[str, Any]:
        violations = self.checker.get_violations()
        score = self.checker.get_compliance_score()
        policies = self.policy_store.list_policies()

        severity_order = {
            Severity.CRITICAL.value: 0,
            Severity.HIGH.value: 1,
            Severity.MEDIUM.value: 2,
            Severity.LOW.value: 3,
        }
        highest_severity = None
        if violations:
            severities = [v["severity"] for v in violations]
            highest_severity = min(severities, key=lambda s: severity_order.get(s, 99))

        return {
            "status": "compliant" if score >= 80 else "non_compliant",
            "compliance_score": score,
            "total_policies": len(policies),
            "total_violations": len(violations),
            "highest_violation_severity": highest_severity,
            "categories": list(set(p.category for p in policies)),
            "last_updated": datetime.now().isoformat(),
        }

    def _count_violations_by_severity(self, violations: List[Dict[str, Any]]) -> Dict[str, int]:
        counts: Dict[str, int] = defaultdict(int)
        for v in violations:
            counts[v["severity"]] += 1
        return dict(counts)


def main() -> None:
    engine = ComplianceEngine()

    print("=" * 60)
    print("ComplianceEngine Demo")
    print("=" * 60)

    print("\n--- 1. PolicyStore: List Default Policies ---")
    for p in engine.policy_store.list_policies():
        print(f"  [{p.severity.value.upper()}] {p.policy_id}: {p.name} ({p.category})")

    print("\n--- 2. PolicyStore: Evaluate Policy (GDPR - Violation) ---")
    gdpr_result = engine.policy_store.evaluate_policy("gdpr", {"consent_given": False})
    print(f"  Status: {gdpr_result['status']}")
    print(f"  Reason: {gdpr_result['reason']}")
    print(f"  Violated rules: {len(gdpr_result['violated_rules'])}")

    print("\n--- 3. PolicyStore: Evaluate Policy (GDPR - Compliant) ---")
    gdpr_ok = engine.policy_store.evaluate_policy("gdpr", {
        "consent_given": True,
        "data_minimization": True,
        "right_to_erasure": True,
        "dpo_appointed": True,
    })
    print(f"  Status: {gdpr_ok['status']}")
    print(f"  Reason: {gdpr_ok['reason']}")

    print("\n--- 4. PolicyStore: Add & Remove Custom Policy ---")
    engine.policy_store.add_policy(
        policy_id="custom_001",
        name="Custom Test Policy",
        description="A custom policy for testing",
        rules=[{"rule_id": "ct-001", "field": "test_field", "operator": "eq", "value": "ok"}],
        severity=Severity.LOW,
        category="testing",
    )
    print(f"  Added custom_001: {engine.policy_store.get_policy('custom_001').name}")
    removed = engine.policy_store.remove_policy("custom_001")
    print(f"  Removed custom_001: {removed}")
    print(f"  Get after removal: {engine.policy_store.get_policy('custom_001')}")

    print("\n--- 5. PolicyStore: List by Category ---")
    privacy_policies = engine.policy_store.list_policies(category="privacy")
    print(f"  Privacy policies: {[p.policy_id for p in privacy_policies]}")

    print("\n--- 6. AuditLogger: Log Events ---")
    engine.audit_logger.log_event(
        event_type="access", actor="user_alice", action="read",
        resource="customer_db", result="allowed",
    )
    engine.audit_logger.log_event(
        event_type="access", actor="user_bob", action="write",
        resource="customer_db", result="blocked",
        details={"reason": "insufficient_permissions"},
    )
    engine.audit_logger.log_event(
        event_type="export", actor="user_alice", action="export_csv",
        resource="report_2024", result="allowed",
    )
    print("  Logged 3 events")

    print("\n--- 7. AuditLogger: Query Logs ---")
    blocked_logs = engine.audit_logger.query_logs({"result": "blocked"})
    print(f"  Blocked events: {len(blocked_logs)}")
    for log in blocked_logs:
        print(f"    {log.actor} -> {log.action} on {log.resource}: {log.result}")

    print("\n--- 8. AuditLogger: Audit Trail ---")
    trail = engine.audit_logger.get_audit_trail("customer_db")
    print(f"  Audit trail for customer_db: {len(trail)} entries")
    for entry in trail:
        print(f"    [{entry.event_type}] {entry.actor} {entry.action} -> {entry.result}")

    print("\n--- 9. AuditLogger: Export Logs (JSON) ---")
    json_export = engine.audit_logger.export_logs(format="json")
    print(f"  Exported {len(json_export)} characters of JSON")

    print("\n--- 10. ComplianceChecker: Check Operation (Compliant) ---")
    compliant_ctx = {
        "data_location": "HK",
        "cross_border_transfer": False,
        "retention_days": 180,
        "auto_delete": True,
        "authenticated": True,
        "role": "admin",
        "mfa_enabled": True,
        "consent_given": True,
        "data_minimization": True,
        "right_to_erasure": True,
        "dpo_appointed": True,
        "purpose_specified": True,
        "lawful_collection": True,
        "data_accuracy": True,
        "retention_limit": True,
        "actor": "user_alice",
        "resource": "customer_db",
    }
    check_ok = engine.checker.check_operation("read_data", compliant_ctx)
    print(f"  Result: {check_ok['result']}")
    print(f"  Violations: {check_ok['violations_count']}")

    print("\n--- 11. ComplianceChecker: Check Operation (Violation) ---")
    violation_ctx = {
        "data_location": "CN",
        "cross_border_transfer": True,
        "retention_days": 999,
        "auto_delete": False,
        "authenticated": False,
        "role": "unknown",
        "mfa_enabled": False,
        "consent_given": False,
        "data_minimization": False,
        "right_to_erasure": False,
        "dpo_appointed": False,
        "purpose_specified": False,
        "lawful_collection": False,
        "data_accuracy": False,
        "retention_limit": False,
        "actor": "user_eve",
        "resource": "customer_db",
    }
    check_fail = engine.checker.check_operation("export_data", violation_ctx)
    print(f"  Result: {check_fail['result']}")
    print(f"  Violations: {check_fail['violations_count']}")
    for reason in check_fail["reasons"]:
        print(f"    - {reason}")

    print("\n--- 12. ComplianceChecker: Get Violations ---")
    violations = engine.checker.get_violations()
    print(f"  Total violations: {len(violations)}")
    for v in violations[:5]:
        print(f"    {v['violation_id']} | {v['policy_id']} | {v['severity']} | {v['reason']}")

    print("\n--- 13. ComplianceChecker: Compliance Score ---")
    score = engine.checker.get_compliance_score()
    print(f"  Compliance Score: {score}%")

    print("\n--- 14. ComplianceEngine: Enforce Compliance ---")
    enforce_result = engine.enforce_compliance("delete_data", compliant_ctx)
    print(f"  Operation: {enforce_result['operation']}")
    print(f"  Enforcement: {enforce_result['enforcement']}")
    print(f"  Violations: {enforce_result['violations_count']}")

    print("\n--- 15. ComplianceEngine: Run Full Audit ---")
    audit = engine.run_compliance_audit()
    print(f"  Audit timestamp: {audit['audit_timestamp']}")
    print(f"  Total policies: {audit['total_policies']}")
    print(f"  Compliance score: {audit['compliance_score']}%")
    print(f"  Total violations: {audit['total_violations']}")
    print(f"  Violations by severity: {audit['violations_by_severity']}")

    print("\n--- 16. ComplianceEngine: Get Compliance Status ---")
    status = engine.get_compliance_status()
    print(f"  Status: {status['status']}")
    print(f"  Score: {status['compliance_score']}%")
    print(f"  Total policies: {status['total_policies']}")
    print(f"  Total violations: {status['total_violations']}")
    print(f"  Highest severity: {status['highest_violation_severity']}")
    print(f"  Categories: {status['categories']}")

    print("\n" + "=" * 60)
    print("ComplianceEngine Demo Complete")
    print("=" * 60)


if __name__ == "__main__":
    main()
