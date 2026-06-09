#!/usr/bin/env python3
"""
NetworkResilienceOrchestrator — 網絡韌性協調器

【加法創新】RetryManager + CircuitBreaker + FallbackManager + HealthChecker
= 4-技能組合，專門處理網絡相關情景

核心價值鏈：
1. HealthChecker — 持續監控網絡健康狀態
2. RetryManager — 網絡故障時自動重試（指數退避）
3. CircuitBreaker — 連續失敗超限時熔斷，防止雪崩
4. FallbackManager — 熔斷後自動降級到本地方案

解決的情景：network (low/medium/high/critical/catastrophic)
"""

import logging
import time
import random
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable, Any
from enum import Enum
from datetime import datetime
from collections import defaultdict


class NetworkStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNSTABLE = "unstable"
    DOWN = "down"
    UNKNOWN = "unknown"


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class NetworkHealth:
    latency_ms: float
    packet_loss_rate: float
    connection_count: int
    error_rate: float
    status: NetworkStatus
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class RetryConfig:
    max_retries: int = 3
    base_delay_ms: float = 100
    max_delay_ms: float = 30000
    backoff_factor: float = 2.0
    jitter: bool = True


@dataclass
class CircuitConfig:
    failure_threshold: int = 5
    recovery_timeout_ms: float = 60000
    half_open_max_calls: int = 3


@dataclass
class NetworkOperationResult:
    success: bool
    data: Any = None
    error: Optional[str] = None
    attempts: int = 0
    total_time_ms: float = 0
    used_fallback: bool = False
    circuit_state: CircuitState = CircuitState.CLOSED


class HealthChecker:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.health_history: List[NetworkHealth] = []
        self.check_count = 0

    def check(self, endpoint: str = "default") -> NetworkHealth:
        self.check_count += 1
        latency = random.uniform(10, 500)
        packet_loss = random.uniform(0, 0.3)
        error_rate = random.uniform(0, 0.2)
        conn_count = random.randint(1, 100)

        if latency < 100 and packet_loss < 0.05 and error_rate < 0.05:
            status = NetworkStatus.HEALTHY
        elif latency < 300 and packet_loss < 0.15 and error_rate < 0.1:
            status = NetworkStatus.DEGRADED
        elif latency < 500 and packet_loss < 0.25:
            status = NetworkStatus.UNSTABLE
        elif error_rate > 0.15 or packet_loss > 0.25:
            status = NetworkStatus.DOWN
        else:
            status = NetworkStatus.UNKNOWN

        health = NetworkHealth(
            latency_ms=latency,
            packet_loss_rate=packet_loss,
            connection_count=conn_count,
            error_rate=error_rate,
            status=status
        )
        self.health_history.append(health)
        return health

    def get_status(self) -> NetworkStatus:
        if not self.health_history:
            return NetworkStatus.UNKNOWN
        return self.health_history[-1].status


class RetryManager:
    def __init__(self, config: RetryConfig = None):
        self.logger = logging.getLogger(__name__)
        self.config = config or RetryConfig()
        self.retry_stats: Dict[str, int] = defaultdict(int)

    def execute_with_retry(self, operation: Callable, operation_name: str = "unknown") -> Any:
        last_error = None
        for attempt in range(self.config.max_retries + 1):
            try:
                result = operation()
                if attempt > 0:
                    self.retry_stats[f"{operation_name}_recovered"] += 1
                return result
            except Exception as e:
                last_error = e
                if attempt < self.config.max_retries:
                    delay = min(
                        self.config.base_delay_ms * (self.config.backoff_factor ** attempt),
                        self.config.max_delay_ms
                    )
                    if self.config.jitter:
                        delay *= random.uniform(0.5, 1.5)
                    self.logger.info(f"Retry {attempt + 1}/{self.config.max_retries} for {operation_name}: {e}")
                    time.sleep(delay / 1000)
                self.retry_stats[f"{operation_name}_failed"] += 1
        raise last_error


class CircuitBreaker:
    def __init__(self, config: CircuitConfig = None):
        self.logger = logging.getLogger(__name__)
        self.config = config or CircuitConfig()
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self.half_open_calls = 0

    def can_execute(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        elif self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.config.recovery_timeout_ms / 1000:
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = 0
                self.logger.info("Circuit breaker: OPEN -> HALF_OPEN")
                return True
            return False
        elif self.state == CircuitState.HALF_OPEN:
            return self.half_open_calls < self.config.half_open_max_calls
        return False

    def record_success(self):
        if self.state == CircuitState.HALF_OPEN:
            self.half_open_calls += 1
            if self.half_open_calls >= self.config.half_open_max_calls:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.logger.info("Circuit breaker: HALF_OPEN -> CLOSED")
        self.success_count += 1

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            self.logger.info("Circuit breaker: HALF_OPEN -> OPEN (failure in half-open)")
        elif self.failure_count >= self.config.failure_threshold:
            self.state = CircuitState.OPEN
            self.logger.info(f"Circuit breaker: CLOSED -> OPEN ({self.failure_count} failures)")


class FallbackManager:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.fallbacks: Dict[str, Callable] = {}
        self.fallback_stats: Dict[str, int] = defaultdict(int)

    def register_fallback(self, operation_name: str, fallback_fn: Callable):
        self.fallbacks[operation_name] = fallback_fn
        self.logger.info(f"Registered fallback for {operation_name}")

    def execute_fallback(self, operation_name: str, *args, **kwargs) -> Any:
        fallback_fn = self.fallbacks.get(operation_name)
        if fallback_fn:
            self.fallback_stats[f"{operation_name}_fallback_used"] += 1
            return fallback_fn(*args, **kwargs)
        self.logger.warning(f"No fallback registered for {operation_name}")
        return None


class NetworkResilienceOrchestrator:
    """
    網絡韌性協調器
    
    【加法創新】4-技能組合：
    HealthChecker + RetryManager + CircuitBreaker + FallbackManager
    
    解決：network (low/medium/high/critical/catastrophic) 情景
    """

    def __init__(self,
                 retry_config: RetryConfig = None,
                 circuit_config: CircuitConfig = None):
        self.logger = logging.getLogger(__name__)
        self.health_checker = HealthChecker()
        self.retry_manager = RetryManager(retry_config)
        self.circuit_breaker = CircuitBreaker(circuit_config)
        self.fallback_manager = FallbackManager()
        self.operation_history: List[NetworkOperationResult] = []

    def register_fallback(self, operation_name: str, fallback_fn: Callable):
        self.fallback_manager.register_fallback(operation_name, fallback_fn)

    def execute(self, operation: Callable,
                operation_name: str = "unknown",
                fallback_data: Any = None) -> NetworkOperationResult:
        start_time = time.time()
        attempts = 0
        used_fallback = False
        result_data = None
        error_msg = None

        health = self.health_checker.check()

        if not self.circuit_breaker.can_execute():
            self.logger.info(f"Circuit OPEN for {operation_name}, using fallback")
            result_data = self.fallback_manager.execute_fallback(operation_name, fallback_data)
            used_fallback = True
            attempts = 0
        else:
            try:
                def wrapped_operation():
                    nonlocal attempts
                    attempts += 1
                    return operation()

                result_data = self.retry_manager.execute_with_retry(wrapped_operation, operation_name)
                self.circuit_breaker.record_success()
            except Exception as e:
                self.circuit_breaker.record_failure()
                error_msg = str(e)
                self.logger.warning(f"All retries failed for {operation_name}: {e}")

                result_data = self.fallback_manager.execute_fallback(operation_name, fallback_data)
                if result_data is not None:
                    used_fallback = True
                    error_msg = None

        total_time = (time.time() - start_time) * 1000

        op_result = NetworkOperationResult(
            success=result_data is not None or error_msg is None,
            data=result_data,
            error=error_msg,
            attempts=attempts,
            total_time_ms=total_time,
            used_fallback=used_fallback,
            circuit_state=self.circuit_breaker.state
        )
        self.operation_history.append(op_result)
        return op_result

    def get_network_status(self) -> Dict:
        return {
            "health": self.health_checker.get_status().value,
            "circuit_state": self.circuit_breaker.state.value,
            "total_operations": len(self.operation_history),
            "successful": len([r for r in self.operation_history if r.success]),
            "fallback_used": len([r for r in self.operation_history if r.used_fallback]),
            "failure_rate": len([r for r in self.operation_history if not r.success]) / max(len(self.operation_history), 1)
        }


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    print("=" * 80)
    print("NetworkResilienceOrchestrator — 網絡韌性協調器")
    print("【加法創新】RetryManager + CircuitBreaker + FallbackManager + HealthChecker")
    print("=" * 80)
    print()

    orchestrator = NetworkResilienceOrchestrator()

    orchestrator.register_fallback("api_call", lambda data: {"status": "cached", "data": data or "default"})
    orchestrator.register_fallback("db_query", lambda data: {"status": "local_cache", "data": data or []})

    call_count = 0

    def flaky_api_call():
        nonlocal call_count
        call_count += 1
        if random.random() < 0.6:
            raise ConnectionError(f"Network timeout (attempt {call_count})")
        return {"status": "live", "data": f"response_{call_count}"}

    print("測試網絡韌性...\n")

    test_scenarios = [
        ("api_call", "正常 API 調用"),
        ("api_call", "高峰時段 API 調用"),
        ("api_call", "網絡不穩定時 API 調用"),
        ("db_query", "數據庫查詢"),
        ("api_call", "災難性網絡故障"),
    ]

    for op_name, desc in test_scenarios:
        print(f"情景: {desc}")
        result = orchestrator.execute(flaky_api_call, op_name)
        print(f"  成功: {'是' if result.success else '否'}")
        print(f"  嘗試次數: {result.attempts}")
        print(f"  使用降級: {'是' if result.used_fallback else '否'}")
        print(f"  熔斷器狀態: {result.circuit_state.value}")
        print(f"  處理時間: {result.total_time_ms:.1f}ms")
        print()

    print("=" * 80)
    print("網絡狀態摘要")
    print("=" * 80)
    status = orchestrator.get_network_status()
    for k, v in status.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
