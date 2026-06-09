from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog
import yaml
from pydantic import BaseModel, Field

from harnessing.core.memory_engine import MemoryEngine
from harnessing.core.skill_router import SkillRouter

logger = structlog.get_logger()

_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
_SKILL_MD_PATH = _PROJECT_ROOT / "skills" / "emoglyphplay" / "SKILL.md"
_PROJECT_RULES_PATH = _PROJECT_ROOT / ".trae" / "rules" / "project_rules.md"
_ERROR_RULES_PATH = _PROJECT_ROOT / "data" / "error-rules.yaml"
_AGENTS_MD_PATH = _PROJECT_ROOT / "AGENTS.md"

_TWELVE_PAIN_POINTS = [
    "短期記憶",
    "單一方案",
    "過快執行",
    "外部依賴偏好",
    "忽略階段成果",
    "過度自信",
    "幻覺偽裝",
    "範圍蔓延",
    "過度工程",
    "忽略用戶意圖",
    "安全盲區",
    "反饋缺失",
]

_INSTANT_GUARD_KEYWORDS = {
    "external_api": [
        "api key",
        "api_key",
        "apikey",
        "register for",
        "sign up for",
        "create account",
        "付費",
        "註冊",
        "api.secret",
    ],
    "scope_creep": [
        "順便",
        "同時也",
        "while we're at it",
        "might as well",
        "bonus",
        "額外添加",
    ],
    "over_engineering": [
        "abstract layer",
        "factory pattern",
        "plugin system",
        "microservice",
        "design pattern",
        "可擴展",
        "未來可能",
    ],
    "security": [
        "password =",
        "secret =",
        "token =",
        "api_key =",
        "hardcode",
    ],
    "capability_gap": [
        "we need",
        "cannot do",
        "missing",
        "lacks",
        "no support",
    ],
}


class GuardViolation(BaseModel):
    category: str
    keyword: str
    context: str
    rule_ref: str


class AuditFinding(BaseModel):
    severity: str
    category: str
    description: str
    suggestion: str
    auto_fixable: bool = False


class LearningCurvePoint(BaseModel):
    timestamp: str
    total_error_rules: int
    verified_rules: int
    unverified_rules: int
    pain_points_covered: int
    pain_points_missing: list[str]
    project_rules_count: int
    skill_rules_count: int


class AuditReport(BaseModel):
    report_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    layer: str
    findings: list[AuditFinding] = Field(default_factory=list)
    learning_curve: LearningCurvePoint | None = None
    violations: list[GuardViolation] = Field(default_factory=list)
    files_updated: list[str] = Field(default_factory=list)
    summary: str = ""


class SelfAuditEngine:
    def __init__(
        self,
        memory_engine: MemoryEngine,
        skill_md_path: Path | None = None,
        project_rules_path: Path | None = None,
        error_rules_path: Path | None = None,
        agents_md_path: Path | None = None,
    ) -> None:
        self.memory = memory_engine
        self.skill_md_path = skill_md_path or _SKILL_MD_PATH
        self.project_rules_path = project_rules_path or _PROJECT_RULES_PATH
        self.error_rules_path = error_rules_path or _ERROR_RULES_PATH
        self.agents_md_path = agents_md_path or _AGENTS_MD_PATH
        self._session_actions: list[dict[str, Any]] = []
        self._session_violations: list[GuardViolation] = []
        self._session_skills_used: list[str] = []
        self._prompt_enhanced: bool = False
        self.skill_router = SkillRouter()

    def check_before_action(self, action_text: str) -> tuple[bool, list[GuardViolation]]:
        violations: list[GuardViolation] = []
        action_lower = action_text.lower()

        if (
            not self._prompt_enhanced
            and "prompt_enhancement" not in action_lower
            and "enhance" not in action_lower
        ):
            violations.append(
                GuardViolation(
                    category="prompt_not_enhanced",
                    keyword="prompt",
                    context=action_text[:200],
                    rule_ref="規則 19（Prompt 增強協議）",
                )
            )

        for category, keywords in _INSTANT_GUARD_KEYWORDS.items():
            for kw in keywords:
                if kw.lower() in action_lower:
                    rule_ref = self._category_to_rule(category)
                    violations.append(
                        GuardViolation(
                            category=category,
                            keyword=kw,
                            context=action_text[:200],
                            rule_ref=rule_ref,
                        )
                    )

        self._session_violations.extend(violations)
        self._session_actions.append(
            {
                "action": action_text[:200],
                "violations": len(violations),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

        gap_result = self.check_capability_gap(action_text)
        if gap_result["violation"]:
            violations.append(
                GuardViolation(
                    category="capability_gap_detected",
                    keyword=", ".join(gap_result["gaps"]),
                    context=action_text[:200],
                    rule_ref="規則 48（缺口填補協議）",
                )
            )
            self._session_violations.append(violations[-1])

        if violations:
            logger.warning(
                "instant_guard_violation",
                violations=len(violations),
                categories=[v.category for v in violations],
            )

        return len(violations) == 0, violations

    def check_capability_gap(self, action_text: str) -> dict:
        gap_patterns = [
            r"we need (\w+) capability",
            r"BeeVerse cannot (\w+)",
            r"missing (\w+) skill",
            r"lacks (\w+) ability",
            r"no (\w+) support",
        ]
        detected_gaps = []
        for pattern in gap_patterns:
            matches = re.findall(pattern, action_text, re.IGNORECASE)
            detected_gaps.extend(matches)
        if detected_gaps:
            return {
                "violation": "capability_gap_detected",
                "gaps": detected_gaps,
                "suggestion": "Use IterativeSkillInstallationEngine to install missing capabilities",
                "severity": "MEDIUM",
            }
        return {"violation": None}

    def record_action(self, action_type: str, details: str, outcome: str = "") -> None:
        self._session_actions.append(
            {
                "type": action_type,
                "details": details[:200],
                "outcome": outcome,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

    def record_skill_used(self, skill_name: str) -> None:
        self._session_skills_used.append(skill_name)

    def mark_prompt_enhanced(self) -> None:
        self._prompt_enhanced = True

    def suggest_skills(self, prompt: str) -> list[dict[str, Any]]:
        matches = self.skill_router.get_recommended_skills(prompt)
        return [
            {
                "name": m.skill_name,
                "confidence": m.confidence,
                "reason": m.reason,
                "matched": m.matched_triggers + m.matched_phrases,
            }
            for m in matches
        ]

    def run_session_audit(self, session_id: str | None = None) -> AuditReport:
        sid = session_id or uuid.uuid4().hex[:8]
        findings: list[AuditFinding] = []

        findings.extend(self._audit_session_violations())
        findings.extend(self._audit_session_actions())
        findings.extend(self._audit_unverified_rules())
        findings.extend(self._audit_skill_usage())

        learning = self._capture_learning_curve()

        report = AuditReport(
            layer="session",
            findings=findings,
            learning_curve=learning,
            violations=list(self._session_violations),
            summary=self._generate_session_summary(findings, learning),
        )

        self.memory.save_session_log(
            session_id=sid,
            summary=report.summary,
            files_changed=report.files_updated,
        )

        if findings:
            self._apply_auto_fixes(findings)

        self._session_actions.clear()
        self._session_violations.clear()
        self._session_skills_used.clear()
        self._prompt_enhanced = False

        logger.info(
            "session_audit_complete",
            session_id=sid,
            findings=len(findings),
            auto_fixable=sum(1 for f in findings if f.auto_fixable),
        )

        return report

    def run_deep_audit(self) -> AuditReport:
        findings: list[AuditFinding] = []

        findings.extend(self._audit_consistency())
        findings.extend(self._audit_error_patterns())
        findings.extend(self._audit_coverage_gaps())
        findings.extend(self._audit_file_sync())

        learning = self._capture_learning_curve()

        report = AuditReport(
            layer="deep",
            findings=findings,
            learning_curve=learning,
            summary=self._generate_deep_summary(findings, learning),
        )

        if findings:
            self._apply_auto_fixes(findings)

        logger.info(
            "deep_audit_complete",
            findings=len(findings),
            auto_fixable=sum(1 for f in findings if f.auto_fixable),
        )

        return report

    def get_learning_curve(self, last_n: int = 30) -> list[LearningCurvePoint]:
        points: list[LearningCurvePoint] = []
        rules = self.memory.get_rules()
        if not rules:
            return points

        for i in range(min(last_n, len(rules))):
            subset = rules[: i + 1]
            verified = sum(1 for r in subset if r.get("verified", 0))
            unverified = len(subset) - verified
            covered = self._count_covered_pain_points(subset)
            missing = [
                pp for pp in _TWELVE_PAIN_POINTS if pp not in self._get_covered_pain_point_names(subset)
            ]

            points.append(
                LearningCurvePoint(
                    timestamp=subset[-1].get("timestamp", ""),
                    total_error_rules=len(subset),
                    verified_rules=verified,
                    unverified_rules=unverified,
                    pain_points_covered=covered,
                    pain_points_missing=missing,
                    project_rules_count=self._count_project_rules(),
                    skill_rules_count=self._count_skill_rules(),
                )
            )

        return points

    def _category_to_rule(self, category: str) -> str:
        mapping = {
            "external_api": "規則 4/15（知識優先/零外部依賴）",
            "scope_creep": "規則 8（需求邊界）",
            "over_engineering": "規則 9（YAGNI）",
            "security": "規則 11（安全優先）",
            "prompt_not_enhanced": "規則 19（Prompt 增強協議）",
            "capability_gap": "規則 48（缺口填補協議）",
            "capability_gap_detected": "規則 48（缺口填補協議）",
        }
        return mapping.get(category, "未知規則")

    def _audit_session_violations(self) -> list[AuditFinding]:
        findings: list[AuditFinding] = []
        if not self._session_violations:
            return findings

        category_counts: dict[str, int] = {}
        for v in self._session_violations:
            category_counts[v.category] = category_counts.get(v.category, 0) + 1

        for cat, count in category_counts.items():
            findings.append(
                AuditFinding(
                    severity="high",
                    category=f"repeated_violation_{cat}",
                    description=f"Session had {count} violations of {cat} guard",
                    suggestion=f"Review and strengthen {self._category_to_rule(cat)}",
                    auto_fixable=False,
                )
            )

        return findings

    def _audit_session_actions(self) -> list[AuditFinding]:
        findings: list[AuditFinding] = []
        if not self._session_actions:
            return findings

        actions_with_violations = sum(1 for a in self._session_actions if a.get("violations", 0) > 0)
        total = len(self._session_actions)

        if total > 0 and actions_with_violations / total > 0.3:
            pct = actions_with_violations / total * 100
            findings.append(
                AuditFinding(
                    severity="high",
                    category="high_violation_rate",
                    description=(
                        f"{actions_with_violations}/{total} actions"
                        f" triggered guard violations ({pct:.0f}%)"
                    ),
                    suggestion="Consider adding more specific rules to prevent recurring violations",
                    auto_fixable=False,
                )
            )

        return findings

    def _audit_unverified_rules(self) -> list[AuditFinding]:
        findings: list[AuditFinding] = []
        rules = self.memory.get_rules()
        unverified = [r for r in rules if not r.get("verified", 0)]

        if unverified:
            findings.append(
                AuditFinding(
                    severity="medium",
                    category="unverified_rules",
                    description=f"{len(unverified)} error rules are unverified",
                    suggestion="Verify unverified rules and mark them as verified in error-rules.yaml",
                    auto_fixable=False,
                )
            )

        return findings

    def _audit_skill_usage(self) -> list[AuditFinding]:
        findings: list[AuditFinding] = []
        if not self._session_actions:
            return findings

        last_action = self._session_actions[-1] if self._session_actions else {}
        action_text = last_action.get("action", "") or last_action.get("details", "")

        if not action_text:
            return findings

        audit = self.skill_router.audit_skill_usage(
            action_text, self._session_skills_used
        )

        if audit["skills_missed"]:
            missed_names = ", ".join(audit["skills_missed"][:5])
            findings.append(
                AuditFinding(
                    severity="medium",
                    category="skill_missed",
                    description=(
                        f"Skills that should have been used but weren't: {missed_names}"
                    ),
                    suggestion=(
                        "Consider invoking the missed skills for better results"
                    ),
                    auto_fixable=False,
                )
            )

        if audit["coverage_score"] < 0.5 and audit["skills_recommended"]:
            findings.append(
                AuditFinding(
                    severity="low",
                    category="low_skill_coverage",
                    description=(
                        f"Skill coverage: {audit['coverage_score']:.0%}"
                        f" ({len(set(audit['skills_used']) & set(audit['skills_recommended']))}"
                        f"/{len(audit['skills_recommended'])} recommended skills used)"
                    ),
                    suggestion="Review available skills and use relevant ones",
                    auto_fixable=False,
                )
            )

        return findings

    def _audit_consistency(self) -> list[AuditFinding]:
        findings: list[AuditFinding] = []

        yaml_rules = self._load_yaml_rules()
        db_rules = self.memory.get_rules()

        yaml_ids = {r.get("id", "") for r in yaml_rules}
        db_ids = {f"R-ERR-{r['id']:03d}" for r in db_rules if "id" in r}

        yaml_only = yaml_ids - db_ids
        if yaml_only:
            findings.append(
                AuditFinding(
                    severity="medium",
                    category="yaml_db_mismatch",
                    description=f"Rules in YAML but not in DB: {yaml_only}",
                    suggestion="Sync YAML rules to SQLite database",
                    auto_fixable=True,
                )
            )

        skill_content = self._read_file_safe(self.skill_md_path)
        for rule_id in yaml_ids:
            if rule_id and rule_id not in skill_content:
                findings.append(
                    AuditFinding(
                        severity="low",
                        category="skill_md_missing_rule",
                        description=f"Rule {rule_id} in YAML but not referenced in SKILL.md",
                        suggestion=f"Add {rule_id} to SKILL.md historical error lessons",
                        auto_fixable=True,
                    )
                )

        return findings

    def _audit_error_patterns(self) -> list[AuditFinding]:
        findings: list[AuditFinding] = []
        rules = self.memory.get_rules()

        root_causes: dict[str, list[str]] = {}
        for r in rules:
            rc = r.get("root_cause", "Unknown")
            key = rc.lower().strip()[:50]
            root_causes.setdefault(key, []).append(r.get("error_desc", ""))

        for rc_key, errors in root_causes.items():
            if len(errors) > 2:
                findings.append(
                    AuditFinding(
                        severity="medium",
                        category="repeated_root_cause",
                        description=f"Root cause '{rc_key}...' appeared {len(errors)} times: {errors[:3]}",
                        suggestion="Consider creating a stronger rule to prevent this recurring root cause",
                        auto_fixable=False,
                    )
                )

        return findings

    def _audit_coverage_gaps(self) -> list[AuditFinding]:
        findings: list[AuditFinding] = []
        rules = self.memory.get_rules()
        covered = self._get_covered_pain_point_names(rules)

        missing = [pp for pp in _TWELVE_PAIN_POINTS if pp not in covered]
        if missing:
            findings.append(
                AuditFinding(
                    severity="low",
                    category="coverage_gap",
                    description=f"Pain points without error rules: {missing}",
                    suggestion="Monitor for errors related to these pain points and create rules when they occur",
                    auto_fixable=False,
                )
            )

        project_rules = self._read_file_safe(self.project_rules_path)
        for i, pp in enumerate(_TWELVE_PAIN_POINTS, 1):
            rule_header = f"## {i + 15}."
            if pp not in project_rules and rule_header not in project_rules:
                findings.append(
                    AuditFinding(
                        severity="medium",
                        category="project_rules_gap",
                        description=f"Pain point '{pp}' (#{i}) may not have a corresponding project rule",
                        suggestion=f"Add a project rule for pain point #{i}: {pp}",
                        auto_fixable=True,
                    )
                )

        return findings

    def _audit_file_sync(self) -> list[AuditFinding]:
        findings: list[AuditFinding] = []

        skill_content = self._read_file_safe(self.skill_md_path)
        if "十二大" not in skill_content and "12" not in skill_content:
            findings.append(
                AuditFinding(
                    severity="high",
                    category="skill_md_outdated",
                    description="SKILL.md may not reflect the latest 12 pain points",
                    suggestion="Update SKILL.md to include all 12 pain points",
                    auto_fixable=True,
                )
            )

        agents_content = self._read_file_safe(self.agents_md_path)
        if "十二大" not in agents_content and "12" not in agents_content:
            findings.append(
                AuditFinding(
                    severity="medium",
                    category="agents_md_outdated",
                    description="AGENTS.md may not reflect the 12 pain points version",
                    suggestion="Update AGENTS.md pain points section",
                    auto_fixable=True,
                )
            )

        return findings

    def _apply_auto_fixes(self, findings: list[AuditFinding]) -> list[str]:
        updated: list[str] = []

        for f in findings:
            if not f.auto_fixable:
                continue

            if f.category == "yaml_db_mismatch":
                yaml_rules = self._load_yaml_rules()
                db_rules = self.memory.get_rules()
                db_ids = {r.get("id") for r in db_rules}
                for yr in yaml_rules:
                    rid = yr.get("id", "")
                    num = int(re.search(r"\d+", rid).group()) if re.search(r"\d+", rid) else None
                    if num and num not in db_ids:
                        self.memory.save_error_rule(
                            error_desc=yr.get("error", ""),
                            root_cause=yr.get("root_cause", ""),
                            rule_text=yr.get("rule", ""),
                            rule_source=yr.get("source", ""),
                        )
                        if yr.get("verified", False):
                            latest = self.memory.get_rules()[0]
                            self.memory.verify_error_rule(latest["id"])
                updated.append("error-rules.yaml → SQLite sync")

            elif f.category == "skill_md_missing_rule":
                updated.append(f"SKILL.md needs manual update for: {f.description}")

            elif f.category == "project_rules_gap":
                updated.append(f"project_rules.md needs manual update for: {f.description}")

            elif f.category in ("skill_md_outdated", "agents_md_outdated"):
                updated.append(f"File needs manual update: {f.description}")

        return updated

    def _capture_learning_curve(self) -> LearningCurvePoint:
        rules = self.memory.get_rules()
        verified = sum(1 for r in rules if r.get("verified", 0))
        covered = self._count_covered_pain_points(rules)
        missing = [
            pp for pp in _TWELVE_PAIN_POINTS if pp not in self._get_covered_pain_point_names(rules)
        ]

        return LearningCurvePoint(
            timestamp=datetime.now(timezone.utc).isoformat(),
            total_error_rules=len(rules),
            verified_rules=verified,
            unverified_rules=len(rules) - verified,
            pain_points_covered=covered,
            pain_points_missing=missing,
            project_rules_count=self._count_project_rules(),
            skill_rules_count=self._count_skill_rules(),
        )

    def _load_yaml_rules(self) -> list[dict[str, Any]]:
        if not self.error_rules_path.exists():
            return []
        try:
            with open(self.error_rules_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            return data.get("rules", []) if isinstance(data, dict) else []
        except Exception:
            logger.warning("yaml_load_failed", path=str(self.error_rules_path))
            return []

    def _read_file_safe(self, path: Path) -> str:
        if not path.exists():
            return ""
        try:
            return path.read_text(encoding="utf-8")
        except Exception:
            return ""

    def _count_project_rules(self) -> int:
        content = self._read_file_safe(self.project_rules_path)
        return len(re.findall(r"^## \d+\.", content, re.MULTILINE))

    def _count_skill_rules(self) -> int:
        content = self._read_file_safe(self.skill_md_path)
        return len(re.findall(r"^## 規則 \d+", content, re.MULTILINE))

    def _get_covered_pain_point_names(self, rules: list[dict[str, Any]]) -> set[str]:
        covered: set[str] = set()
        for r in rules:
            rule_text = r.get("rule_text", "") or r.get("rule", "")
            for pp in _TWELVE_PAIN_POINTS:
                if pp in rule_text:
                    covered.add(pp)
            error_desc = r.get("error_desc", "") or r.get("error", "")
            root_cause = r.get("root_cause", "")
            combined = f"{error_desc} {root_cause}"
            for pp in _TWELVE_PAIN_POINTS:
                if pp in combined:
                    covered.add(pp)
        return covered

    def _count_covered_pain_points(self, rules: list[dict[str, Any]]) -> int:
        return len(self._get_covered_pain_point_names(rules))

    def _generate_session_summary(
        self, findings: list[AuditFinding], learning: LearningCurvePoint
    ) -> str:
        parts = [
            f"Session Audit | Rules: {learning.total_error_rules} ({learning.verified_rules} verified)",
            f"Pain Points: {learning.pain_points_covered}/12 covered",
        ]
        if findings:
            high = sum(1 for f in findings if f.severity == "high")
            medium = sum(1 for f in findings if f.severity == "medium")
            low = sum(1 for f in findings if f.severity == "low")
            parts.append(f"Findings: {high}H/{medium}M/{low}L")
        if self._session_violations:
            parts.append(f"Violations: {len(self._session_violations)}")
        return " | ".join(parts)

    def _generate_deep_summary(
        self, findings: list[AuditFinding], learning: LearningCurvePoint
    ) -> str:
        parts = [
            f"Deep Audit | Rules: {learning.total_error_rules} ({learning.verified_rules} verified)",
            f"Pain Points: {learning.pain_points_covered}/12 covered",
            f"Project Rules: {learning.project_rules_count} | Skill Rules: {learning.skill_rules_count}",
        ]
        if findings:
            high = sum(1 for f in findings if f.severity == "high")
            medium = sum(1 for f in findings if f.severity == "medium")
            low = sum(1 for f in findings if f.severity == "low")
            auto = sum(1 for f in findings if f.auto_fixable)
            parts.append(f"Findings: {high}H/{medium}M/{low}L ({auto} auto-fixable)")
        if learning.pain_points_missing:
            parts.append(f"Missing: {', '.join(learning.pain_points_missing[:3])}")
        return " | ".join(parts)
