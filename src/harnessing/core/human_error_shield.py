#!/usr/bin/env python3
"""
HumanErrorShield — 人為錯誤防護盾

【加法創新】IntentBasedGuard + InputValidator + GoalAnchor + SelfAuditEngine
= 4-技能組合，專門處理人為因素情景

核心價值鏈：
1. IntentBasedGuard — 分析用戶意圖的風險級別
2. InputValidator — 驗證輸入是否安全
3. GoalAnchor — 確認操作是否偏離目標
4. SelfAuditEngine — 審計操作是否違反規則

解決的情景：human (low/medium/high/critical) + security (low/medium)
"""

import logging
import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum
from datetime import datetime
from collections import defaultdict


class RiskLevel(Enum):
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorType(Enum):
    TYPO = "typo"
    MISCONFIGURATION = "misconfiguration"
    ACCIDENTAL_DELETE = "accidental_delete"
    WRONG_COMMAND = "wrong_command"
    UNAUTHORIZED_ACTION = "unauthorized_action"
    DATA_EXPOSURE = "data_exposure"
    OVER_PERMISSION = "over_permission"


@dataclass
class HumanAction:
    action_type: str
    description: str
    target: str
    parameters: Dict[str, str]
    user_intent: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ShieldResult:
    action: HumanAction
    allowed: bool
    risk_level: RiskLevel
    intent_risk: float
    input_valid: bool
    goal_deviation: float
    audit_violations: List[str]
    corrections: List[str]
    confidence: float


from src.harnessing.core.intent_based_guard import IntentBasedGuard


class InputValidator:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.dangerous_patterns = [
            (r";\s*rm\s", "危險的刪除命令"),
            (r"DROP\s+TABLE", "危險的 SQL 刪除操作"),
            (r"api[_-]?key\s*=\s*['\"]", "API Key 硬編碼"),
            (r"password\s*=\s*['\"]", "密碼硬編碼"),
            (r"token\s*=\s*['\"]", "Token 硬編碼"),
            (r"\.\.\/", "路徑遍歷攻擊"),
            (r"<script>", "XSS 攻擊模式"),
        ]

    def validate(self, action: HumanAction) -> Tuple[bool, List[str]]:
        all_text = f"{action.action_type} {action.description} {' '.join(action.parameters.values())}"
        is_valid = True
        violations = []

        for pattern, description in self.dangerous_patterns:
            if re.search(pattern, all_text, re.IGNORECASE):
                is_valid = False
                violations.append(f"檢測到危險模式: {description}")

        for key, value in action.parameters.items():
            if not value or not str(value).strip():
                violations.append(f"參數 '{key}' 為空")

        return is_valid, violations


class GoalAnchor:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.current_goal: Optional[str] = None
        self.goal_keywords: List[str] = []

    def set_goal(self, goal: str, keywords: List[str] = None):
        self.current_goal = goal
        self.goal_keywords = keywords or goal.lower().split()

    def check_deviation(self, action: HumanAction) -> Tuple[float, List[str]]:
        if not self.current_goal:
            return 0.0, []

        action_text = f"{action.action_type} {action.description} {action.user_intent}".lower()
        relevance_count = sum(1 for kw in self.goal_keywords if kw in action_text)
        relevance_ratio = relevance_count / max(len(self.goal_keywords), 1)

        deviation = 1.0 - relevance_ratio
        issues = []

        if deviation > 0.7:
            issues.append(f"操作與目標 '{self.current_goal}' 高度偏離")
        elif deviation > 0.4:
            issues.append(f"操作與目標 '{self.current_goal}' 部分偏離")

        return deviation, issues


class SelfAuditEngine:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.rules = [
            {"id": "R-001", "pattern": r"api[_-]?key", "message": "不得硬編碼 API Key", "severity": "critical"},
            {"id": "R-002", "pattern": r"password\s*=", "message": "不得硬編碼密碼", "severity": "critical"},
            {"id": "R-003", "pattern": r"delete\s+all", "message": "不得批量刪除", "severity": "high"},
            {"id": "R-004", "pattern": r"sudo\s+rm", "message": "不得使用 sudo rm", "severity": "critical"},
            {"id": "R-005", "pattern": r"git\s+push\s+--force", "message": "不得強制推送", "severity": "high"},
        ]
        self.violation_history: List[Dict] = []

    def audit(self, action: HumanAction) -> List[str]:
        all_text = f"{action.action_type} {action.description} {' '.join(action.parameters.values())}"
        violations = []

        for rule in self.rules:
            if re.search(rule["pattern"], all_text, re.IGNORECASE):
                violations.append(f"[{rule['id']}] {rule['message']} (嚴重程度: {rule['severity']})")
                self.violation_history.append({
                    "timestamp": datetime.now().isoformat(),
                    "rule_id": rule["id"],
                    "action": action.action_type,
                    "severity": rule["severity"]
                })

        return violations


class HumanErrorShield:
    """
    人為錯誤防護盾
    
    【加法創新】4-技能組合：
    IntentBasedGuard + InputValidator + GoalAnchor + SelfAuditEngine
    
    解決：human (low/medium/high/critical) + security (low/medium)
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.intent_guard = IntentBasedGuard()
        self.input_validator = InputValidator()
        self.goal_anchor = GoalAnchor()
        self.audit_engine = SelfAuditEngine()
        self.shield_history: List[ShieldResult] = []

    def set_goal(self, goal: str, keywords: List[str] = None):
        self.goal_anchor.set_goal(goal, keywords)

    def evaluate(self, action: HumanAction) -> ShieldResult:
        prompt = f"{action.action_type} {action.description} {action.target} {action.user_intent}"
        intent_risk = self.intent_guard.analyze_intent(prompt)
        risk_level = intent_risk.risk_level
        intent_confidence = intent_risk.confidence
        input_valid, input_violations = self.input_validator.validate(action)
        goal_deviation, goal_issues = self.goal_anchor.check_deviation(action)
        audit_violations = self.audit_engine.audit(action)

        all_violations = input_violations + goal_issues + audit_violations

        allowed = True
        if risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            allowed = False
        if not input_valid:
            allowed = False
        if audit_violations:
            critical_violations = [v for v in audit_violations if "critical" in v]
            if critical_violations:
                allowed = False

        corrections = []
        if not allowed:
            if risk_level == RiskLevel.CRITICAL:
                corrections.append("操作被完全阻止，風險等級為嚴重")
            elif risk_level == RiskLevel.HIGH:
                corrections.append("建議先備份再執行此操作")
            if input_violations:
                corrections.append("請修正輸入中的危險模式")
            if goal_deviation > 0.7:
                corrections.append("此操作與當前目標偏離，請確認是否必要")

        confidence = (intent_confidence + (1.0 if input_valid else 0.0) + (1.0 - goal_deviation)) / 3.0

        result = ShieldResult(
            action=action,
            allowed=allowed,
            risk_level=risk_level,
            intent_risk=intent_confidence,
            input_valid=input_valid,
            goal_deviation=goal_deviation,
            audit_violations=all_violations,
            corrections=corrections,
            confidence=confidence
        )
        self.shield_history.append(result)
        return result

    def get_shield_summary(self) -> Dict:
        risk_counts = defaultdict(int)
        for r in self.shield_history:
            risk_counts[r.risk_level.value] += 1
        return {
            "total_evaluations": len(self.shield_history),
            "blocked": len([r for r in self.shield_history if not r.allowed]),
            "allowed": len([r for r in self.shield_history if r.allowed]),
            "by_risk_level": dict(risk_counts),
        }


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    print("=" * 80)
    print("HumanErrorShield — 人為錯誤防護盾")
    print("【加法創新】IntentBasedGuard + InputValidator + GoalAnchor + SelfAuditEngine")
    print("=" * 80)
    print()

    shield = HumanErrorShield()
    shield.set_goal("開發 Python 框架", ["python", "框架", "開發", "代碼"])

    test_actions = [
        HumanAction("delete", "刪除所有日誌文件", "logs/", {"pattern": "*.log"}, "清理磁盤空間"),
        HumanAction("config", "配置 API Key", "settings.py", {"api_key": "sk-abc123"}, "設置 API 連接"),
        HumanAction("create", "創建新的 Python 模組", "core/module.py", {"name": "new_module"}, "添加新功能"),
        HumanAction("deploy", "部署到生產環境", "production", {"env": "prod"}, "發布新版本"),
        HumanAction("delete", "刪除生產數據庫", "database", {"command": "DROP TABLE users"}, "清理測試數據"),
    ]

    for action in test_actions:
        print(f"操作: {action.action_type} - {action.description}")
        result = shield.evaluate(action)
        print(f"  允許: {'✅ 是' if result.allowed else '❌ 否'}")
        print(f"  風險級別: {result.risk_level.value}")
        print(f"  輸入有效: {'是' if result.input_valid else '否'}")
        print(f"  目標偏離: {result.goal_deviation:.2f}")
        if result.audit_violations:
            print(f"  審計違規: {result.audit_violations[0]}")
        if result.corrections:
            print(f"  修正建議: {result.corrections[0]}")
        print()

    print("=" * 80)
    print("防護摘要")
    print("=" * 80)
    summary = shield.get_shield_summary()
    for k, v in summary.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
