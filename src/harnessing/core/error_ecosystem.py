#!/usr/bin/env python3
"""
ErrorEcosystem — 錯誤生態系統

【突破性發明】#1 TOP 組合
技能組合: ErrorClassifier + AlertingSystem + RollbackManager + InputValidator

核心價值鏈：
1. ErrorClassifier — 識別錯誤類型
2. AlertingSystem — 觸發相應級別的告警
3. RollbackManager — 執行狀態回滾
4. InputValidator — 防止同類錯誤再次發生

形成完整的錯誤處理生態圈。
"""

import logging
import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable, Any
from enum import Enum
from datetime import datetime
from pathlib import Path


class ErrorSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    VALIDATION = "validation"  # 輸入驗證錯誤
    RESOURCE = "resource"  # 資源相關錯誤
    AUTHENTICATION = "authentication"  # 認證錯誤
    AUTHORIZATION = "authorization"  # 授權錯誤
    NETWORK = "network"  # 網絡錯誤
    DATABASE = "database"  # 數據庫錯誤
    TIMEOUT = "timeout"  # 超時錯誤
    UNKNOWN = "unknown"  # 未知錯誤


@dataclass
class ErrorEvent:
    error_type: str
    message: str
    severity: ErrorSeverity
    category: ErrorCategory
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    context: Dict[str, Any] = field(default_factory=dict)
    root_cause: Optional[str] = None
    affected_component: Optional[str] = None


@dataclass
class ErrorHandlingResult:
    error: ErrorEvent
    category_assigned: ErrorCategory
    alerts_sent: List[str]
    rollback_executed: bool
    validation_added: bool
    total_time_ms: float
    prevented_future_errors: int


class RollbackManager:
    """
    回滾管理器
    
    管理狀態快照並執行回滾操作。
    """
    
    def __init__(self, data_dir: str = "data"):
        self.logger = logging.getLogger(__name__)
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.snapshots: Dict[str, Dict] = {}
        self.rollback_history: List[Dict] = []
    
    def create_snapshot(self, component: str, state: Any, metadata: Dict = None) -> str:
        """創建狀態快照"""
        import hashlib
        import time
        
        snapshot_id = hashlib.md5(f"{component}{time.time()}".encode()).hexdigest()[:8]
        
        snapshot = {
            "id": snapshot_id,
            "component": component,
            "state": state,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        
        self.snapshots[f"{component}_{snapshot_id}"] = snapshot
        
        snapshot_path = self.data_dir / f"snapshot_{snapshot_id}.json"
        with open(snapshot_path, 'w', encoding='utf-8') as f:
            json.dump(snapshot, f, indent=2, default=str)
        
        self.logger.info(f"Created snapshot {snapshot_id} for {component}")
        return snapshot_id
    
    def rollback(self, component: str, snapshot_id: str = None) -> Optional[Any]:
        """執行回滾"""
        if snapshot_id:
            key = f"{component}_{snapshot_id}"
        else:
            matching = [k for k in self.snapshots if k.startswith(f"{component}_")]
            if not matching:
                self.logger.warning(f"No snapshots found for {component}")
                return None
            key = max(matching, key=lambda k: self.snapshots[k]["timestamp"])
        
        snapshot = self.snapshots.get(key)
        if not snapshot:
            self.logger.error(f"Snapshot not found: {key}")
            return None
        
        self.rollback_history.append({
            "timestamp": datetime.now().isoformat(),
            "component": component,
            "snapshot_id": snapshot_id,
            "state": snapshot["state"]
        })
        
        self.logger.info(f"Rolled back {component} to snapshot {snapshot.get('id')}")
        return snapshot["state"]
    
    def get_rollback_history(self, limit: int = 10) -> List[Dict]:
        """獲取回滾歷史"""
        return self.rollback_history[-limit:]


class InputValidator:
    """
    輸入驗證器
    
    防止同類錯誤再次發生。
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.validation_rules: Dict[ErrorCategory, Callable] = {}
        self.failure_patterns: Dict[str, List[str]] = {}
        self.statistics = {"total_validations": 0, "failures_prevented": 0}
    
    def add_validation_rule(self, category: ErrorCategory, validator: Callable):
        """添加驗證規則"""
        self.validation_rules[category] = validator
        self.logger.info(f"Added validation rule for {category.value}")
    
    def record_failure_pattern(self, error: ErrorEvent, input_data: Any):
        """記錄失敗模式"""
        pattern_key = error.category.value
        
        if pattern_key not in self.failure_patterns:
            self.failure_patterns[pattern_key] = []
        
        self.failure_patterns[pattern_key].append({
            "error_type": error.error_type,
            "input_type": type(input_data).__name__,
            "timestamp": error.timestamp
        })
        
        if len(self.failure_patterns[pattern_key]) > 100:
            self.failure_patterns[pattern_key] = self.failure_patterns[pattern_key][-100:]
    
    def validate(self, category: ErrorCategory, data: Any) -> tuple:
        """
        驗證輸入
        
        Returns:
            (is_valid, error_message)
        """
        self.statistics["total_validations"] += 1
        
        validator = self.validation_rules.get(category)
        if validator:
            try:
                is_valid = validator(data)
                if not is_valid:
                    self.statistics["failures_prevented"] += 1
                    return False, f"Validation failed for category {category.value}"
                return True, None
            except Exception as e:
                self.logger.error(f"Validation error: {e}")
                return False, str(e)
        
        return True, None
    
    def get_failure_patterns(self) -> Dict:
        """獲取失敗模式"""
        return self.failure_patterns.copy()
    
    def get_statistics(self) -> Dict:
        """獲取統計"""
        return self.statistics.copy()


class ErrorEcosystem:
    """
    錯誤生態系統
    
    整合 ErrorClassifier + AlertingSystem + RollbackManager + InputValidator
    形成完整的錯誤處理生態圈。
    """
    
    def __init__(self, data_dir: str = "data"):
        self.logger = logging.getLogger(__name__)
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)

        self._classification_rules = self._init_classification_rules()
        self._classifier_stats = {"total": 0, "by_category": {}}
        self._alert_channels = ["log", "console", "webhook"]
        self._alert_history: List[Dict] = []
        self.rollback = RollbackManager(data_dir)
        self.validator = InputValidator()

        self._setup_default_validators()
        self.processing_history: List[ErrorHandlingResult] = []

    def _init_classification_rules(self) -> Dict[ErrorCategory, List[str]]:
        return {
            ErrorCategory.VALIDATION: ["validation", "invalid", "format", "schema", "type mismatch"],
            ErrorCategory.RESOURCE: ["memory", "disk", "cpu", "resource", "capacity"],
            ErrorCategory.AUTHENTICATION: ["auth", "login", "credential", "token", "password"],
            ErrorCategory.AUTHORIZATION: ["permission", "denied", "forbidden", "access denied", "unauthorized"],
            ErrorCategory.NETWORK: ["network", "connection", "timeout", "refused", "unreachable"],
            ErrorCategory.DATABASE: ["database", "sql", "query", "transaction", "deadlock"],
            ErrorCategory.TIMEOUT: ["timeout", "timed out", "exceeded", "slow"],
        }

    def _classify_error(self, error: Exception) -> ErrorCategory:
        error_str = f"{type(error).__name__} {str(error)}".lower()
        for category, keywords in self._classification_rules.items():
            if any(kw in error_str for kw in keywords):
                self._classifier_stats["total"] += 1
                cat_name = category.value
                self._classifier_stats["by_category"][cat_name] = self._classifier_stats["by_category"].get(cat_name, 0) + 1
                return category
        self._classifier_stats["total"] += 1
        self._classifier_stats["by_category"]["unknown"] = self._classifier_stats["by_category"].get("unknown", 0) + 1
        return ErrorCategory.UNKNOWN

    def _get_severity(self, error: Exception) -> ErrorSeverity:
        error_str = f"{type(error).__name__} {str(error)}".lower()
        critical_keywords = ["memory", "disk full", "database", "deadlock", "corruption"]
        high_keywords = ["timeout", "connection refused", "permission denied"]
        medium_keywords = ["invalid", "format", "schema"]
        if any(kw in error_str for kw in critical_keywords):
            return ErrorSeverity.CRITICAL
        elif any(kw in error_str for kw in high_keywords):
            return ErrorSeverity.HIGH
        elif any(kw in error_str for kw in medium_keywords):
            return ErrorSeverity.MEDIUM
        return ErrorSeverity.LOW

    def _send_alert(self, error_event: ErrorEvent, channels: List[str] = None) -> List[str]:
        channels = channels or self._alert_channels
        alerts_sent = []
        alert_message = f"[{error_event.category.value.upper()}] {error_event.error_type}: {error_event.message} (Severity: {error_event.severity.value})"
        for channel in channels:
            if channel == "log":
                if error_event.severity == ErrorSeverity.CRITICAL:
                    self.logger.critical(alert_message)
                elif error_event.severity == ErrorSeverity.HIGH:
                    self.logger.error(alert_message)
                else:
                    self.logger.warning(alert_message)
                alerts_sent.append("log")
            elif channel == "console":
                prefix = "🔴" if error_event.severity in [ErrorSeverity.CRITICAL, ErrorSeverity.HIGH] else "⚠️"
                print(f"{prefix} [{error_event.severity.value.upper()}] {alert_message}")
                alerts_sent.append("console")
            elif channel == "webhook":
                self.logger.info(f"Webhook alert: {alert_message}")
                alerts_sent.append("webhook")
        self._alert_history.append({
            "timestamp": error_event.timestamp,
            "error_type": error_event.error_type,
            "severity": error_event.severity.value,
            "channels": alerts_sent
        })
        return alerts_sent

    def _get_classifier_stats(self) -> Dict:
        return self._classifier_stats.copy()

    def _get_alert_summary(self, limit: int = 10) -> Dict:
        recent = self._alert_history[-limit:]
        by_severity = {}
        for alert in self._alert_history:
            sev = alert["severity"]
            by_severity[sev] = by_severity.get(sev, 0) + 1
        return {
            "total_alerts": len(self._alert_history),
            "by_severity": by_severity,
            "recent": recent
        }
    
    def _setup_default_validators(self):
        """設置默認驗證器"""
        
        def validate_resource(data):
            if isinstance(data, dict):
                memory = data.get("memory_mb", 0)
                return memory < 10000
            return True
        
        def validate_input(data):
            if data is None:
                return False
            if isinstance(data, str) and len(data) > 1000000:
                return False
            return True
        
        self.validator.add_validation_rule(ErrorCategory.RESOURCE, validate_resource)
        self.validator.add_validation_rule(ErrorCategory.VALIDATION, validate_input)
    
    def handle_error(self, 
                    error: Exception, 
                    context: Dict[str, Any] = None,
                    input_data: Any = None,
                    should_rollback: bool = False,
                    component: str = None) -> ErrorHandlingResult:
        """
        完整錯誤處理流程
        
        1. 分類錯誤
        2. 發送告警
        3. 回滾（如需要）
        4. 添加驗證規則（如需要）
        """
        import time
        start_time = time.time()
        
        context = context or {}
        category = self._classify_error(error)
        severity = self._get_severity(error)
        
        error_event = ErrorEvent(
            error_type=type(error).__name__,
            message=str(error),
            severity=severity,
            category=category,
            context=context,
            affected_component=component
        )
        
        alerts_sent = self._send_alert(error_event)
        
        rollback_executed = False
        if should_rollback and component:
            snapshot_id = self.rollback.create_snapshot(
                component=component,
                state=context.get("state"),
                metadata={"error": str(error)}
            )
            self.rollback.rollback(component, snapshot_id)
            rollback_executed = True
        
        validation_added = False
        if input_data is not None:
            self.validator.record_failure_pattern(error_event, input_data)
            is_valid, _ = self.validator.validate(category, input_data)
            if not is_valid:
                validation_added = True
        
        total_time = (time.time() - start_time) * 1000
        
        result = ErrorHandlingResult(
            error=error_event,
            category_assigned=category,
            alerts_sent=alerts_sent,
            rollback_executed=rollback_executed,
            validation_added=validation_added,
            total_time_ms=total_time,
            prevented_future_errors=0
        )
        
        self.processing_history.append(result)
        
        self.logger.info(
            f"Error handled: {error_event.error_type} -> {category.value} "
            f"(severity: {severity.value}, time: {total_time:.1f}ms)"
        )
        
        return result
    
    def get_ecosystem_status(self) -> Dict:
        """獲取生態系統狀態"""
        return {
            "classifier_stats": self._get_classifier_stats(),
            "alert_summary": self._get_alert_summary(),
            "rollback_history": len(self.rollback.rollback_history),
            "validator_stats": self.validator.get_statistics(),
            "total_errors_handled": len(self.processing_history)
        }
    
    def save_state(self):
        """保存狀態"""
        state = {
            "timestamp": datetime.now().isoformat(),
            "classifier_stats": self._get_classifier_stats(),
            "alert_summary": self._get_alert_summary(100),
            "failure_patterns": self.validator.get_failure_patterns()
        }
        
        state_path = self.data_dir / "error_ecosystem_state.json"
        with open(state_path, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2, default=str, allow_nan=True)
        
        self.logger.info(f"State saved to {state_path}")


def main():
    """演示 ErrorEcosystem"""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    
    print("=" * 80)
    print("ErrorEcosystem — 錯誤生態系統")
    print("=" * 80)
    print()
    
    ecosystem = ErrorEcosystem()
    
    test_errors = [
        (ValueError("Invalid input format"), None, "test_input_1"),
        (MemoryError("Out of memory"), {"state": {"data": [1,2,3]}}, "test_input_2"),
        (TimeoutError("Connection timed out"), None, "test_input_3"),
    ]
    
    print("處理測試錯誤...\n")
    
    for error, context, input_data in test_errors:
        print(f"錯誤: {type(error).__name__}: {error}")
        result = ecosystem.handle_error(
            error=error,
            context=context,
            input_data=input_data,
            should_rollback=True,
            component="test_component"
        )
        
        print(f"  分類: {result.category_assigned.value}")
        print(f"  嚴重程度: {result.error.severity.value}")
        print(f"  告警發送: {', '.join(result.alerts_sent)}")
        print(f"  回滾執行: {'是' if result.rollback_executed else '否'}")
        print(f"  驗證添加: {'是' if result.validation_added else '否'}")
        print(f"  處理時間: {result.total_time_ms:.1f}ms")
        print()
    
    print("=" * 80)
    print("生態系統狀態")
    print("=" * 80)
    status = ecosystem.get_ecosystem_status()
    
    print(f"\n錯誤分類統計:")
    for cat, count in status["classifier_stats"]["by_category"].items():
        print(f"  {cat}: {count}")
    
    print(f"\n告警摘要:")
    print(f"  總告警數: {status['alert_summary']['total_alerts']}")
    print(f"  按嚴重程度: {status['alert_summary']['by_severity']}")
    
    print(f"\n回滾歷史: {status['rollback_history']} 次")
    print(f"驗證器統計: {status['validator_stats']}")
    print(f"總錯誤處理數: {status['total_errors_handled']}")
    
    ecosystem.save_state()


if __name__ == "__main__":
    main()

