from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class GuardAction(str, Enum):
    ALLOW = "allow"
    WARN = "warn"
    BLOCK = "block"
    QUARANTINE = "quarantine"


class ConflictResolution(str, Enum):
    MOST_RESTRICTIVE = "most_restrictive"
    PRIORITY_BASED = "priority_based"
    FIRST_MATCH = "first_match"


SEVERITY_PRIORITY: dict[str, int] = {
    Severity.CRITICAL.value: 0,
    Severity.HIGH.value: 1,
    Severity.MEDIUM.value: 2,
    Severity.LOW.value: 3,
}

ACTION_RESTRICTIVENESS: dict[str, int] = {
    GuardAction.QUARANTINE.value: 0,
    GuardAction.BLOCK.value: 1,
    GuardAction.WARN.value: 2,
    GuardAction.ALLOW.value: 3,
}


@dataclass
class GuardRule:
    rule_id: str
    category: str
    severity_threshold: Severity
    action: GuardAction
    enabled: bool = True
    description: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ThreatEvaluation:
    threat_id: str
    threat_info: dict[str, Any]
    matched_rules: list[str]
    resolved_action: GuardAction
    resolution_reason: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class GuardRegistry:
    def __init__(self):
        self._rules: dict[str, GuardRule] = {}
        self._category_index: dict[str, list[str]] = {}
        self.logger = logging.getLogger(__name__)

    def add_rule(self, rule: GuardRule) -> None:
        self._rules[rule.rule_id] = rule
        if rule.category not in self._category_index:
            self._category_index[rule.category] = []
        self._category_index[rule.category].append(rule.rule_id)
        self.logger.info(
            "guard_rule_added",
            extra={"rule_id": rule.rule_id, "category": rule.category, "action": rule.action.value},
        )

    def remove_rule(self, rule_id: str) -> bool:
        if rule_id not in self._rules:
            return False
        rule = self._rules[rule_id]
        if rule.category in self._category_index:
            self._category_index[rule.category] = [
                rid for rid in self._category_index[rule.category] if rid != rule_id
            ]
        del self._rules[rule_id]
        return True

    def get_rule(self, rule_id: str) -> GuardRule | None:
        return self._rules.get(rule_id)

    def get_rules_by_category(self, category: str) -> list[GuardRule]:
        rule_ids = self._category_index.get(category, [])
        return [self._rules[rid] for rid in rule_ids if rid in self._rules]

    def get_all_rules(self) -> list[GuardRule]:
        return list(self._rules.values())

    def get_enabled_rules(self) -> list[GuardRule]:
        return [r for r in self._rules.values() if r.enabled]

    def find_applicable_rules(self, threat_info: dict[str, Any]) -> list[GuardRule]:
        threat_category = threat_info.get("category", "")
        threat_severity = threat_info.get("severity", Severity.LOW.value)

        applicable = []
        for rule in self.get_enabled_rules():
            if rule.category and rule.category != threat_category:
                continue
            threat_priority = SEVERITY_PRIORITY.get(threat_severity, 99)
            rule_priority = SEVERITY_PRIORITY.get(rule.severity_threshold.value, 99)
            if threat_priority <= rule_priority:
                applicable.append(rule)

        return applicable


class ConflictResolver:
    def __init__(self, strategy: ConflictResolution = ConflictResolution.PRIORITY_BASED):
        self.strategy = strategy
        self.logger = logging.getLogger(__name__)

    def resolve(self, rules: list[GuardRule]) -> tuple[GuardAction, str]:
        if not rules:
            return GuardAction.ALLOW, "no_rules_matched"

        if self.strategy == ConflictResolution.MOST_RESTRICTIVE:
            return self._resolve_most_restrictive(rules)
        elif self.strategy == ConflictResolution.PRIORITY_BASED:
            return self._resolve_priority_based(rules)
        elif self.strategy == ConflictResolution.FIRST_MATCH:
            return self._resolve_first_match(rules)

        return GuardAction.ALLOW, "unknown_strategy"

    def _resolve_most_restrictive(self, rules: list[GuardRule]) -> tuple[GuardAction, str]:
        most_restrictive = rules[0]
        for rule in rules[1:]:
            if ACTION_RESTRICTIVENESS.get(rule.action.value, 99) < ACTION_RESTRICTIVENESS.get(
                most_restrictive.action.value, 99
            ):
                most_restrictive = rule

        return most_restrictive.action, f"most_restrictive: rule {most_restrictive.rule_id}"

    def _resolve_priority_based(self, rules: list[GuardRule]) -> tuple[GuardAction, str]:
        highest_priority = rules[0]
        for rule in rules[1:]:
            rule_sev = SEVERITY_PRIORITY.get(rule.severity_threshold.value, 99)
            highest_sev = SEVERITY_PRIORITY.get(highest_priority.severity_threshold.value, 99)
            if rule_sev < highest_sev:
                highest_priority = rule
            elif rule_sev == highest_sev:
                if ACTION_RESTRICTIVENESS.get(rule.action.value, 99) < ACTION_RESTRICTIVENESS.get(
                    highest_priority.action.value, 99
                ):
                    highest_priority = rule

        return highest_priority.action, f"priority_based: rule {highest_priority.rule_id}"

    def _resolve_first_match(self, rules: list[GuardRule]) -> tuple[GuardAction, str]:
        first = rules[0]
        return first.action, f"first_match: rule {first.rule_id}"


class UnifiedGuardSystem:
    def __init__(self, conflict_strategy: ConflictResolution = ConflictResolution.PRIORITY_BASED):
        self.registry = GuardRegistry()
        self.conflict_resolver = ConflictResolver(strategy=conflict_strategy)
        self.audit_log: list[dict[str, Any]] = []
        self._threat_counter: int = 0
        self.logger = logging.getLogger(__name__)

    def register_guard(self, rule: GuardRule) -> None:
        self.registry.add_rule(rule)

    def remove_guard(self, rule_id: str) -> bool:
        return self.registry.remove_rule(rule_id)

    def evaluate_threat(self, threat_info: dict[str, Any]) -> dict[str, Any]:
        self._threat_counter += 1
        threat_id = f"T-{self._threat_counter:04d}"

        applicable_rules = self.registry.find_applicable_rules(threat_info)

        if not applicable_rules:
            evaluation = ThreatEvaluation(
                threat_id=threat_id,
                threat_info=threat_info,
                matched_rules=[],
                resolved_action=GuardAction.ALLOW,
                resolution_reason="no_applicable_rules",
            )
        else:
            resolved_action, reason = self.conflict_resolver.resolve(applicable_rules)
            evaluation = ThreatEvaluation(
                threat_id=threat_id,
                threat_info=threat_info,
                matched_rules=[r.rule_id for r in applicable_rules],
                resolved_action=resolved_action,
                resolution_reason=reason,
            )

        log_entry = {
            "threat_id": evaluation.threat_id,
            "threat_info": evaluation.threat_info,
            "matched_rules": evaluation.matched_rules,
            "resolved_action": evaluation.resolved_action.value,
            "resolution_reason": evaluation.resolution_reason,
            "timestamp": evaluation.timestamp,
        }
        self.audit_log.append(log_entry)

        self.logger.info(
            "threat_evaluated",
            extra={
                "threat_id": threat_id,
                "action": evaluation.resolved_action.value,
                "matched_rules": len(evaluation.matched_rules),
            },
        )

        return log_entry

    def batch_evaluate(self, threats: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [self.evaluate_threat(threat) for threat in threats]

    def get_audit_log(self, limit: int = 100) -> list[dict[str, Any]]:
        return self.audit_log[-limit:]

    def get_stats(self) -> dict[str, Any]:
        action_counts: dict[str, int] = {}
        for entry in self.audit_log:
            action = entry["resolved_action"]
            action_counts[action] = action_counts.get(action, 0) + 1

        return {
            "total_threats_evaluated": len(self.audit_log),
            "action_distribution": action_counts,
            "total_rules": len(self.registry.get_all_rules()),
            "enabled_rules": len(self.registry.get_enabled_rules()),
            "categories": list(self.registry._category_index.keys()),
        }
