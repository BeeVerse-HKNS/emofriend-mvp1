#!/usr/bin/env python3
"""
Automation Skills — AI Agent 自動化技巧統一框架

整合 Phase 1 的 20 個共同技巧，統一封裝為可復用嘅模組。

架構分層：
1. Core Skills（核心技巧）— 已有 Self-Healing Engine 提供
2. Extended Skills（擴展技巧）— 新增以下模組

20 個共同技巧對應關係：
| # | 技巧 | 類別 | 狀態 | 實現位置 |
|---|------|------|------|---------|
| 1 | Checkpoint-Resume | 核心 | ✅ 已有 | self_healing_engine.CheckpointManager |
| 2 | Circuit Breaker | 核心 | ✅ 已有 | self_healing_engine.CircuitBreaker |
| 3 | Memory Engine | 核心 | ✅ 已有 | memory_engine.MemoryEngine |
| 4 | Self-Reflection | 核心 | ✅ 已有 | self_healing_engine.SelfReflection |
| 5 | Human-in-the-Loop | 核心 | ✅ 已有 | self_healing_engine.HumanInTheLoop |
| 6 | Goal Anchoring | 核心 | ✅ 已有 | self_healing_engine.GoalAnchor |
| 7 | Error Classification | 擴展 | ❌ 新增 | ErrorClassifier |
| 8 | Retry with Backoff | 擴展 | ⚠️ 增強 | RetryManager |
| 9 | Context Compression | 核心 | ⚠️ 增強 | ContextManager |
| 10 | Token Management | 擴展 | ❌ 新增 | TokenManager |
| 11 | Health Check | 擴展 | ❌ 新增 | HealthChecker |
| 12 | Alerting System | 擴展 | ❌ 新增 | AlertingSystem |
| 13 | Rollback | 擴展 | ❌ 新增 | RollbackManager |
| 14 | Fallback Strategy | 核心 | ⚠️ 增強 | FallbackManager |
| 15 | Monitoring | 擴展 | ❌ 新增 | MonitoringSystem |
| 16 | Rate Limiting | 擴展 | ❌ 新增 | RateLimiter |
| 17 | Input Validation | 擴展 | ❌ 新增 | InputValidator |
| 18 | Guardrails | 核心 | ⚠️ 增強 | harness_guardrails |
| 19 | Audit Trail | 擴展 | ❌ 新增 | AuditTrail |
| 20 | Learning from Errors | 核心 | ⚠️ 增強 | self_audit_engine |

遵循零外部依賴原則，全部使用標準庫實現
"""

from enum import Enum
from typing import Optional, Dict, Any, List, Callable, Type
from dataclasses import dataclass, field
from datetime import datetime
import time
import json
import logging
from pathlib import Path
import threading


class ErrorCategory(Enum):
    TRANSIENT = "transient"
    PERMANENT = "permanent"
    EXPECTED = "expected"
    UNKNOWN = "unknown"


class ErrorSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ClassifiedError:
    error: Exception
    category: ErrorCategory
    severity: ErrorSeverity
    retryable: bool
    message: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    context: Dict[str, Any] = field(default_factory=dict)


class ErrorClassifier:
    """
    統一錯誤分類器
    將錯誤分為：暫時性/永久性/預期性/未知
    """

    TRANSIENT_PATTERNS = [
        "timeout", "timed out", "connection refused",
        "network", "unreachable", "temporary",
        "rate limit", "too many requests",
        "service unavailable", "503", "502", "429",
    ]

    PERMANENT_PATTERNS = [
        "not found", "404", "invalid", "unauthorized",
        "401", "403", "authentication", "permission denied",
        "schema", "validation", "parse", "access denied",
    ]

    EXPECTED_PATTERNS = [
        "expected", "intentional", "handled",
    ]

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._classification_cache: Dict[str, Dict] = {}
        self._lock = threading.Lock()

    def classify(self, error: Exception, context: Dict[str, Any] = None) -> ClassifiedError:
        error_msg = str(error).lower()
        error_type = type(error).__name__

        cache_key = f"{error_type}:{error_msg[:50]}"
        if cache_key in self._classification_cache:
            cached = self._classification_cache[cache_key]
            return ClassifiedError(
                error=error,
                category=ErrorCategory(cached["category"]),
                severity=ErrorSeverity(cached["severity"]),
                retryable=cached["retryable"],
                message=str(error),
                context=context or {},
            )

        category = self._classify_category(error_msg)
        severity = self._classify_severity(error, context)
        retryable = category == ErrorCategory.TRANSIENT

        result = ClassifiedError(
            error=error,
            category=category,
            severity=severity,
            retryable=retryable,
            message=str(error),
            context=context or {},
        )

        with self._lock:
            self._classification_cache[cache_key] = {
                "category": category.value,
                "severity": severity.value,
                "retryable": retryable,
            }

        return result

    def _classify_category(self, error_msg: str) -> ErrorCategory:
        for pattern in self.TRANSIENT_PATTERNS:
            if pattern in error_msg:
                return ErrorCategory.TRANSIENT

        for pattern in self.PERMANENT_PATTERNS:
            if pattern in error_msg:
                return ErrorCategory.PERMANENT

        for pattern in self.EXPECTED_PATTERNS:
            if pattern in error_msg:
                return ErrorCategory.EXPECTED

        return ErrorCategory.UNKNOWN

    def _classify_severity(self, error: Exception, context: Dict = None) -> ErrorSeverity:
        if context and context.get("consecutive_failures", 0) >= 5:
            return ErrorSeverity.CRITICAL
        if "timeout" in str(error).lower() or "memory" in str(error).lower():
            return ErrorSeverity.HIGH
        if "permission" in str(error).lower() or "auth" in str(error).lower():
            return ErrorSeverity.HIGH
        return ErrorSeverity.MEDIUM

    def should_retry(self, classified: ClassifiedError, retry_count: int, max_retries: int = 3) -> bool:
        if not classified.retryable:
            return False
        if retry_count >= max_retries:
            return False
        return True


class RetryManager:
    """
    重試管理器
    實現指數退避重試策略
    """

    def __init__(self, max_retries: int = 3, base_delay: float = 1.0,
                 max_delay: float = 60.0, jitter: bool = True):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter = jitter
        self.logger = logging.getLogger(__name__)

    def calculate_delay(self, retry_count: int) -> float:
        delay = min(self.base_delay * (2 ** retry_count), self.max_delay)
        if self.jitter:
            import random
            delay *= (0.5 + random.random() * 0.5)
        return delay

    def execute_with_retry(
        self,
        func: Callable,
        *args,
        error_classifier: ErrorClassifier = None,
        on_retry: Callable = None,
        **kwargs
    ) -> Any:
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_error = e
                if error_classifier:
                    classified = error_classifier.classify(e)
                    if not error_classifier.should_retry(classified, attempt, self.max_retries):
                        raise

                if attempt < self.max_retries:
                    delay = self.calculate_delay(attempt)
                    self.logger.warning(
                        f"Attempt {attempt + 1} failed: {e}. Retrying in {delay:.2f}s..."
                    )
                    if on_retry:
                        on_retry(attempt, e)
                    time.sleep(delay)
                else:
                    self.logger.error(f"All {self.max_retries + 1} attempts failed")

        raise last_error


@dataclass
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class TokenManager:
    """
    Token 使用量管理器
    追蹤 API 使用量同成本
    """

    DEFAULT_COSTS = {
        "gpt-4": {"prompt": 0.03, "completion": 0.06},
        "gpt-3.5-turbo": {"prompt": 0.0015, "completion": 0.002},
        "claude-3": {"prompt": 0.015, "completion": 0.075},
        "glm-4": {"prompt": 0.001, "completion": 0.002},
        "qwen": {"prompt": 0.0, "completion": 0.0},
    }

    def __init__(self, base_path: Optional[Path] = None):
        if base_path is None:
            base_path = Path(__file__).parent.parent.parent / "data"
        self.base_path = Path(base_path)
        self.token_dir = self.base_path / "token_usage"
        self.token_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)
        self._daily_usage: Dict[str, List[TokenUsage]] = {}
        self._lock = threading.Lock()

    def record_usage(self, model: str, prompt_tokens: int, completion_tokens: int,
                    cost: float = None) -> TokenUsage:
        usage = TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            cost=cost or self._calculate_cost(model, prompt_tokens, completion_tokens),
        )

        with self._lock:
            today = datetime.now().strftime("%Y-%m-%d")
            if today not in self._daily_usage:
                self._daily_usage[today] = []
            self._daily_usage[today].append(usage)

        self._save_usage(today)
        return usage

    def _calculate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        costs = self.DEFAULT_COSTS.get(model, {"prompt": 0.0, "completion": 0.0})
        return (prompt_tokens / 1000 * costs["prompt"] +
                completion_tokens / 1000 * costs["completion"])

    def _save_usage(self, date: str) -> None:
        path = self.token_dir / f"{date}_usage.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump([
                {"prompt_tokens": u.prompt_tokens,
                 "completion_tokens": u.completion_tokens,
                 "total_tokens": u.total_tokens,
                 "cost": u.cost,
                 "timestamp": u.timestamp}
                for u in self._daily_usage.get(date, [])
            ], f, indent=2)

    def get_daily_usage(self, date: str = None) -> Dict[str, Any]:
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        path = self.token_dir / f"{date}_usage.json"
        if not path.exists():
            return {"date": date, "total_tokens": 0, "total_cost": 0.0, "requests": 0}

        with open(path, "r", encoding="utf-8") as f:
            usages = json.load(f)

        total_tokens = sum(u["total_tokens"] for u in usages)
        total_cost = sum(u["cost"] for u in usages)

        return {
            "date": date,
            "total_tokens": total_tokens,
            "total_cost": total_cost,
            "requests": len(usages),
        }

    def get_monthly_usage(self, year_month: str = None) -> Dict[str, Any]:
        if year_month is None:
            year_month = datetime.now().strftime("%Y-%m")

        total_tokens = 0
        total_cost = 0.0
        total_requests = 0

        for path in self.token_dir.glob(f"{year_month}*_usage.json"):
            with open(path, "r", encoding="utf-8") as f:
                usages = json.load(f)
            total_tokens += sum(u["total_tokens"] for u in usages)
            total_cost += sum(u["cost"] for u in usages)
            total_requests += len(usages)

        return {
            "year_month": year_month,
            "total_tokens": total_tokens,
            "total_cost": total_cost,
            "total_requests": total_requests,
        }


@dataclass
class HealthStatus:
    component: str
    status: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    details: Dict[str, Any] = field(default_factory=dict)


class HealthChecker:
    """
    健康檢查系統
    定期檢查各組件狀態
    """

    def __init__(self, base_path: Optional[Path] = None):
        if base_path is None:
            base_path = Path(__file__).parent.parent.parent
        self.base_path = Path(base_path)
        self.logger = logging.getLogger(__name__)
        self._checks: Dict[str, Callable] = {}
        self._last_results: Dict[str, HealthStatus] = {}

    def register_check(self, name: str, check_func: Callable) -> None:
        self._checks[name] = check_func

    def run_check(self, name: str) -> HealthStatus:
        if name not in self._checks:
            return HealthStatus(component=name, status="unknown", details={"error": "Check not registered"})

        try:
            result = self._checks[name]()
            status = HealthStatus(component=name, status="healthy" if result else "unhealthy", details={"result": result})
        except Exception as e:
            status = HealthStatus(component=name, status="error", details={"error": str(e)})

        self._last_results[name] = status
        return status

    def run_all_checks(self) -> Dict[str, HealthStatus]:
        results = {}
        for name in self._checks:
            results[name] = self.run_check(name)
        return results

    def get_overall_status(self) -> str:
        if not self._last_results:
            return "unknown"
        statuses = [r.status for r in self._last_results.values()]
        if all(s == "healthy" for s in statuses):
            return "healthy"
        if any(s == "error" for s in statuses):
            return "degraded"
        return "unhealthy"

    def get_system_health(self) -> Dict[str, Any]:
        results = self.run_all_checks()
        return {
            "overall_status": self.get_overall_status(),
            "components": {name: {"status": r.status, "details": r.details}
                         for name, r in results.items()},
            "timestamp": datetime.now().isoformat(),
        }


class AlertLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Alert:
    level: AlertLevel
    title: str
    message: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    context: Dict[str, Any] = field(default_factory=dict)
    acknowledged: bool = False


class AlertingSystem:
    """
    告警系統
    統一告警管理、通知、分級處理
    """

    def __init__(self, base_path: Optional[Path] = None):
        if base_path is None:
            base_path = Path(__file__).parent.parent.parent / "data"
        self.base_path = Path(base_path)
        self.alerts_dir = self.base_path / "alerts"
        self.alerts_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)
        self._handlers: Dict[AlertLevel, List[Callable]] = {
            level: [] for level in AlertLevel
        }
        self._pending_alerts: List[Alert] = []

    def register_handler(self, level: AlertLevel, handler: Callable) -> None:
        self._handlers[level].append(handler)

    def send_alert(self, level: AlertLevel, title: str, message: str,
                  context: Dict[str, Any] = None) -> Alert:
        alert = Alert(level=level, title=title, message=message, context=context or {})

        self._pending_alerts.append(alert)
        self._save_alert(alert)

        for handler in self._handlers[level]:
            try:
                handler(alert)
            except Exception as e:
                self.logger.error(f"Alert handler failed: {e}")

        self.logger.log(
            logging.WARNING if level == AlertLevel.WARNING else logging.ERROR,
            f"[{level.value.upper()}] {title}: {message}"
        )

        return alert

    def _save_alert(self, alert: Alert) -> None:
        filename = f"{alert.timestamp.replace(':', '-')}_{alert.level.value}.json"
        path = self.alerts_dir / filename
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "level": alert.level.value,
                "title": alert.title,
                "message": alert.message,
                "timestamp": alert.timestamp,
                "context": alert.context,
                "acknowledged": alert.acknowledged,
            }, f, indent=2, ensure_ascii=False)

    def get_pending_alerts(self, level: AlertLevel = None) -> List[Alert]:
        if level:
            return [a for a in self._pending_alerts if a.level == level and not a.acknowledged]
        return [a for a in self._pending_alerts if not a.acknowledged]

    def acknowledge_alert(self, timestamp: str) -> bool:
        for alert in self._pending_alerts:
            if alert.timestamp == timestamp:
                alert.acknowledged = True
                return True
        return False


@dataclass
class RollbackPoint:
    id: str
    timestamp: str
    data: Any
    description: str
    checksum: str = ""


class RollbackManager:
    """
    回滾管理器
    保存狀態快照，支持回滾到指定版本
    """

    def __init__(self, base_path: Optional[Path] = None, max_snapshots: int = 10):
        if base_path is None:
            base_path = Path(__file__).parent.parent.parent / "data"
        self.base_path = Path(base_path)
        self.rollback_dir = self.base_path / "rollback"
        self.rollback_dir.mkdir(parents=True, exist_ok=True)
        self.max_snapshots = max_snapshots
        self.logger = logging.getLogger(__name__)
        self._index: List[RollbackPoint] = []

    def create_snapshot(self, name: str, data: Any, description: str = "") -> RollbackPoint:
        import hashlib

        point = RollbackPoint(
            id=f"{name}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            timestamp=datetime.now().isoformat(),
            data=data,
            description=description,
            checksum="",
        )

        data_str = json.dumps(data, sort_keys=True, default=str)
        point.checksum = hashlib.md5(data_str.encode()).hexdigest()

        path = self.rollback_dir / f"{point.id}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"data": data, "description": description}, f, indent=2, ensure_ascii=False)

        self._index.append(point)
        self._prune_old_snapshots(name)

        self.logger.info(f"Created rollback snapshot: {point.id}")
        return point

    def _prune_old_snapshots(self, name: str) -> None:
        related = [p for p in self._index if p.id.startswith(name)]
        if len(related) > self.max_snapshots:
            to_remove = sorted(related, key=lambda p: p.timestamp)[:-self.max_snapshots]
            for p in to_remove:
                path = self.rollback_dir / f"{p.id}.json"
                if path.exists():
                    path.unlink()
                self._index.remove(p)

    def rollback_to(self, point_id: str) -> Any:
        path = self.rollback_dir / f"{point_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"Rollback point not found: {point_id}")

        with open(path, "r", encoding="utf-8") as f:
            content = json.load(f)

        self.logger.info(f"Rolled back to: {point_id}")
        return content["data"]

    def list_snapshots(self, name: str = None) -> List[RollbackPoint]:
        if name:
            return [p for p in self._index if p.id.startswith(name)]
        return sorted(self._index, key=lambda p: p.timestamp, reverse=True)


@dataclass
class ValidationRule:
    name: str
    validator: Callable[[Any], bool]
    error_message: str


class InputValidator:
    """
    輸入驗證器
    統一驗證輸入數據，防止無效數據進入系統
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._rules: List[ValidationRule] = []

    def add_rule(self, name: str, validator: Callable[[Any], bool],
                error_message: str = "Validation failed") -> None:
        self._rules.append(ValidationRule(name=name, validator=validator, error_message=error_message))

    def add_string_rule(self, name: str, min_length: int = 0,
                       max_length: int = None, pattern: str = None) -> None:
        def validator(value):
            if not isinstance(value, str):
                return False
            if len(value) < min_length:
                return False
            if max_length and len(value) > max_length:
                return False
            if pattern and not __import__('re').match(pattern, value):
                return False
            return True

        self.add_rule(name, validator, f"String validation failed for {name}")

    def add_number_rule(self, name: str, min_value: float = None,
                       max_value: float = None) -> None:
        def validator(value):
            if not isinstance(value, (int, float)):
                return False
            if min_value is not None and value < min_value:
                return False
            if max_value is not None and value > max_value:
                return False
            return True

        self.add_rule(name, validator, f"Number validation failed for {name}")

    def validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        errors = {}
        for rule in self._rules:
            if rule.name in data:
                try:
                    if not rule.validator(data[rule.name]):
                        errors[rule.name] = rule.error_message
                except Exception as e:
                    errors[rule.name] = str(e)

        return {"valid": len(errors) == 0, "errors": errors}


class RateLimiter:
    """
    速率限制器
    防止 API 過度調用
    """

    def __init__(self, max_calls: int, window_seconds: int = 60):
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self._calls: List[float] = []
        self._lock = threading.Lock()
        self.logger = logging.getLogger(__name__)

    def is_allowed(self) -> bool:
        with self._lock:
            now = time.time()
            self._calls = [t for t in self._calls if now - t < self.window_seconds]

            if len(self._calls) >= self.max_calls:
                return False

            self._calls.append(now)
            return True

    def wait_if_needed(self) -> None:
        if not self.is_allowed():
            sleep_time = self.window_seconds - (time.time() - self._calls[0]) if self._calls else self.window_seconds
            self.logger.warning(f"Rate limit reached, waiting {sleep_time:.2f}s")
            time.sleep(sleep_time)

    def get_remaining(self) -> int:
        with self._lock:
            now = time.time()
            self._calls = [t for t in self._calls if now - t < self.window_seconds]
            return max(0, self.max_calls - len(self._calls))


@dataclass
class AuditEntry:
    timestamp: str
    action: str
    user: str
    resource: str
    details: Dict[str, Any]
    result: str


class AuditTrail:
    """
    審計日誌系統
    記錄所有操作，支持合規審計
    """

    def __init__(self, base_path: Optional[Path] = None):
        if base_path is None:
            base_path = Path(__file__).parent.parent.parent / "data"
        self.base_path = Path(base_path)
        self.audit_dir = self.base_path / "audit"
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)

    def log(self, action: str, user: str = "system",
           resource: str = "", details: Dict[str, Any] = None,
           result: str = "success") -> AuditEntry:
        entry = AuditEntry(
            timestamp=datetime.now().isoformat(),
            action=action,
            user=user,
            resource=resource,
            details=details or {},
            result=result,
        )

        date = datetime.now().strftime("%Y-%m-%d")
        path = self.audit_dir / f"{date}_audit.jsonl"

        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "timestamp": entry.timestamp,
                "action": entry.action,
                "user": entry.user,
                "resource": entry.resource,
                "details": entry.details,
                "result": entry.result,
            }, ensure_ascii=False) + "\n")

        return entry

    def query(self, start_date: str = None, end_date: str = None,
             action: str = None, user: str = None) -> List[AuditEntry]:
        if start_date is None:
            start_date = datetime.now().strftime("%Y-%m-%d")
        if end_date is None:
            end_date = start_date

        entries = []
        date_range = self._date_range(start_date, end_date)

        for date in date_range:
            path = self.audit_dir / f"{date}_audit.jsonl"
            if not path.exists():
                continue

            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    entry = json.loads(line)
                    if action and entry["action"] != action:
                        continue
                    if user and entry["user"] != user:
                        continue
                    entries.append(AuditEntry(**entry))

        return entries

    def _date_range(self, start: str, end: str) -> List[str]:
        from datetime import datetime, timedelta
        start_dt = datetime.strptime(start, "%Y-%m-%d")
        end_dt = datetime.strptime(end, "%Y-%m-%d")
        dates = []
        current = start_dt
        while current <= end_dt:
            dates.append(current.strftime("%Y-%m-%d"))
            current += timedelta(days=1)
        return dates


@dataclass
class FallbackOption:
    name: str
    func: Callable
    priority: int
    description: str = ""


class FallbackManager:
    """
    降級策略管理器
    主方案失敗時自動切換到備用方案
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._fallbacks: List[FallbackOption] = []

    def register(self, name: str, func: Callable, priority: int = 0,
                description: str = "") -> None:
        self._fallbacks.append(FallbackOption(
            name=name, func=func, priority=priority, description=description
        ))
        self._fallbacks.sort(key=lambda x: x.priority, reverse=True)

    def execute(self, primary_func: Callable, *args, **kwargs) -> Any:
        try:
            return primary_func(*args, **kwargs)
        except Exception as e:
            self.logger.warning(f"Primary function failed: {e}, trying fallbacks...")

            for fallback in self._fallbacks:
                try:
                    self.logger.info(f"Trying fallback: {fallback.name}")
                    return fallback.func(*args, **kwargs)
                except Exception as fallback_error:
                    self.logger.error(f"Fallback {fallback.name} failed: {fallback_error}")
                    continue

            raise Exception("All fallbacks failed")


class MonitoringSystem:
    """
    監控系統
    收集指標、追蹤性能、支持告警
    """

    def __init__(self, base_path: Optional[Path] = None):
        if base_path is None:
            base_path = Path(__file__).parent.parent.parent / "data"
        self.base_path = Path(base_path)
        self.metrics_dir = self.base_path / "metrics"
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)
        self._metrics: Dict[str, List] = {}
        self._lock = threading.Lock()

    def record_metric(self, name: str, value: float, tags: Dict[str, str] = None) -> None:
        with self._lock:
            if name not in self._metrics:
                self._metrics[name] = []
            self._metrics[name].append({
                "value": value,
                "timestamp": datetime.now().isoformat(),
                "tags": tags or {},
            })

    def get_metrics(self, name: str, hours: int = 24) -> List[Dict]:
        from datetime import datetime, timedelta
        cutoff = datetime.now() - timedelta(hours=hours)

        if name not in self._metrics:
            return []

        return [
            m for m in self._metrics[name]
            if datetime.fromisoformat(m["timestamp"]) > cutoff
        ]

    def get_stats(self, name: str) -> Dict[str, Any]:
        metrics = self.get_metrics(name)
        if not metrics:
            return {"count": 0, "avg": 0, "min": 0, "max": 0}

        values = [m["value"] for m in metrics]
        return {
            "count": len(values),
            "avg": sum(values) / len(values),
            "min": min(values),
            "max": max(values),
        }


class ContextManager:
    """
    上下文管理器
    優化上下文窗口，防止超出限制
    """

    def __init__(self, max_tokens: int = 100000):
        self.max_tokens = max_tokens
        self.logger = logging.getLogger(__name__)
        self._history: List[Dict] = []
        self._token_count = 0

    def add(self, role: str, content: str, tokens: int = None) -> None:
        if tokens is None:
            tokens = len(content) // 4

        if self._token_count + tokens > self.max_tokens:
            self._compress(tokens)

        self._history.append({"role": role, "content": content, "tokens": tokens})
        self._token_count += tokens

    def _compress(self, required_tokens: int) -> None:
        if len(self._history) <= 2:
            self.logger.warning("Cannot compress further, context limit may be exceeded")
            return

        keep = len(self._history) // 2
        removed = self._history[:keep]
        self._history = self._history[keep:]
        self._token_count -= sum(m["tokens"] for m in removed)
        self.logger.info(f"Compressed context: removed {len(removed)} messages")

    def get_context(self) -> List[Dict]:
        return self._history

    def get_token_count(self) -> int:
        return self._token_count

    def clear(self) -> None:
        self._history = []
        self._token_count = 0


class AutomationSkills:
    """
    Automation Skills 統一入口
    整合所有 20 個共同技巧
    """

    def __init__(self, base_path: Optional[Path] = None):
        if base_path is None:
            base_path = Path(__file__).parent.parent.parent

        self.base_path = Path(base_path)
        data_path = self.base_path / "data"

        self.error_classifier = ErrorClassifier()
        self.retry_manager = RetryManager()
        self.token_manager = TokenManager(data_path)
        self.health_checker = HealthChecker(self.base_path)
        self.alerting_system = AlertingSystem(data_path)
        self.rollback_manager = RollbackManager(data_path)
        self.input_validator = InputValidator()
        self.rate_limiter = RateLimiter(max_calls=100)
        self.audit_trail = AuditTrail(data_path)
        self.fallback_manager = FallbackManager()
        self.monitoring_system = MonitoringSystem(data_path)
        self.context_manager = ContextManager()

        self._register_default_health_checks()

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger(__name__)

    def _register_default_health_checks(self) -> None:
        self.health_checker.register_check("disk_space", self._check_disk_space)
        self.health_checker.register_check("data_dir", self._check_data_dir)

    def _check_disk_space(self) -> bool:
        import shutil
        try:
            total, used, free = shutil.disk_usage(self.base_path)
            return free > 1024 * 1024 * 1024
        except Exception:
            return True

    def _check_data_dir(self) -> bool:
        return self.base_path.exists()

    def execute_with_full_protection(
        self,
        func: Callable,
        task_name: str,
        *args,
        **kwargs
    ) -> Any:
        start_time = time.time()
        self.audit_trail.log(action="task_start", resource=task_name)

        try:
            result = self.retry_manager.execute_with_retry(
                func,
                *args,
                error_classifier=self.error_classifier,
                on_retry=lambda attempt, error: self.alerting_system.send_alert(
                    AlertLevel.WARNING,
                    f"Retry attempt {attempt + 1}",
                    str(error),
                    {"task": task_name}
                )
            )

            self.monitoring_system.record_metric(
                "task_success", 1.0, {"task": task_name}
            )
            self.audit_trail.log(action="task_success", resource=task_name)

            return result

        except Exception as e:
            duration = time.time() - start_time
            self.monitoring_system.record_metric(
                "task_failure", duration, {"task": task_name}
            )
            self.audit_trail.log(
                action="task_failure",
                resource=task_name,
                details={"error": str(e)},
                result="failure"
            )

            classified = self.error_classifier.classify(e)
            if classified.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
                self.alerting_system.send_alert(
                    AlertLevel.ERROR if classified.severity == ErrorSeverity.HIGH else AlertLevel.CRITICAL,
                    f"Task failed: {task_name}",
                    str(e),
                    {"task": task_name, "category": classified.category.value}
                )

            raise

    def get_skills_status(self) -> Dict[str, Any]:
        health = self.health_checker.get_system_health()
        return {
            "health": health,
            "metrics": {
                name: self.monitoring_system.get_stats(name)
                for name in self.monitoring_system._metrics.keys()
            },
            "alerts_pending": len(self.alerting_system.get_pending_alerts()),
            "token_usage": self.token_manager.get_daily_usage(),
        }


def main():
    skills = AutomationSkills()
    print("Automation Skills initialized")
    print(json.dumps(skills.get_skills_status(), indent=2, default=str))


if __name__ == "__main__":
    main()
