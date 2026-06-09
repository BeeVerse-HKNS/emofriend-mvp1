from __future__ import annotations

import random
import structlog
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

logger = structlog.get_logger()


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class ErrorType(Enum):
    TRANSIENT = "transient"
    PERMANENT = "permanent"
    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


@dataclass
class APIEndpoint:
    name: str
    base_url: str
    rate_limit: int = 100
    rate_window: int = 60
    timeout: float = 30.0
    max_retries: int = 3
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RateLimitInfo:
    limit: int
    remaining: int
    reset_time: float
    window: int


class RateLimitHandler:
    def __init__(self):
        self._limits: dict[str, RateLimitInfo] = {}
        self._request_history: dict[str, list[float]] = {}

    def check_limit(self, endpoint_name: str, limit: int, window: int) -> bool:
        current_time = time.time()
        if endpoint_name not in self._request_history:
            self._request_history[endpoint_name] = []
        self._request_history[endpoint_name] = [
            t for t in self._request_history[endpoint_name]
            if current_time - t < window
        ]
        current_count = len(self._request_history[endpoint_name])
        return current_count < limit

    def record_request(self, endpoint_name: str) -> None:
        current_time = time.time()
        if endpoint_name not in self._request_history:
            self._request_history[endpoint_name] = []
        self._request_history[endpoint_name].append(current_time)

    def get_wait_time(self, endpoint_name: str, limit: int, window: int) -> float:
        if endpoint_name not in self._request_history:
            return 0.0
        history = self._request_history[endpoint_name]
        if len(history) < limit:
            return 0.0
        oldest = min(history)
        return max(0.0, window - (time.time() - oldest))

    def update_from_headers(self, endpoint_name: str, headers: dict[str, str]) -> None:
        limit = int(headers.get("X-RateLimit-Limit", 0))
        remaining = int(headers.get("X-RateLimit-Remaining", 0))
        reset = float(headers.get("X-RateLimit-Reset", time.time()))
        if limit > 0:
            self._limits[endpoint_name] = RateLimitInfo(
                limit=limit,
                remaining=remaining,
                reset_time=reset,
                window=60
            )


class ExponentialBackoff:
    def __init__(
        self,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        multiplier: float = 2.0,
        jitter: bool = True
    ):
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.multiplier = multiplier
        self.jitter = jitter
        self._attempt_counts: dict[str, int] = {}

    def get_delay(self, operation_id: str) -> float:
        attempts = self._attempt_counts.get(operation_id, 0)
        delay = self.base_delay * (self.multiplier ** attempts)
        delay = min(delay, self.max_delay)
        if self.jitter:
            delay = delay * (0.5 + random.random())
        self._attempt_counts[operation_id] = attempts + 1
        return delay

    def reset(self, operation_id: str) -> None:
        self._attempt_counts[operation_id] = 0

    def get_attempt_count(self, operation_id: str) -> int:
        return self._attempt_counts.get(operation_id, 0)


class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_max_calls: int = 3
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        self._circuits: dict[str, dict[str, Any]] = {}

    def _init_circuit(self, endpoint_name: str) -> None:
        if endpoint_name not in self._circuits:
            self._circuits[endpoint_name] = {
                "state": CircuitState.CLOSED,
                "failure_count": 0,
                "last_failure_time": 0.0,
                "half_open_calls": 0
            }

    def can_execute(self, endpoint_name: str) -> bool:
        self._init_circuit(endpoint_name)
        circuit = self._circuits[endpoint_name]
        if circuit["state"] == CircuitState.CLOSED:
            return True
        if circuit["state"] == CircuitState.OPEN:
            elapsed = time.time() - circuit["last_failure_time"]
            if elapsed >= self.recovery_timeout:
                circuit["state"] = CircuitState.HALF_OPEN
                circuit["half_open_calls"] = 0
                return True
            return False
        if circuit["state"] == CircuitState.HALF_OPEN:
            return circuit["half_open_calls"] < self.half_open_max_calls
        return False

    def record_success(self, endpoint_name: str) -> None:
        self._init_circuit(endpoint_name)
        circuit = self._circuits[endpoint_name]
        if circuit["state"] == CircuitState.HALF_OPEN:
            circuit["state"] = CircuitState.CLOSED
            circuit["failure_count"] = 0

    def record_failure(self, endpoint_name: str) -> None:
        self._init_circuit(endpoint_name)
        circuit = self._circuits[endpoint_name]
        circuit["failure_count"] += 1
        circuit["last_failure_time"] = time.time()
        if circuit["state"] == CircuitState.HALF_OPEN:
            circuit["state"] = CircuitState.OPEN
        elif circuit["failure_count"] >= self.failure_threshold:
            circuit["state"] = CircuitState.OPEN

    def get_state(self, endpoint_name: str) -> CircuitState:
        self._init_circuit(endpoint_name)
        return self._circuits[endpoint_name]["state"]


class FallbackRouter:
    def __init__(self):
        self._fallbacks: dict[str, list[Callable]] = {}
        self._fallback_endpoints: dict[str, list[str]] = {}

    def register_fallback(self, endpoint_name: str, fallback_func: Callable) -> None:
        if endpoint_name not in self._fallbacks:
            self._fallbacks[endpoint_name] = []
        self._fallbacks[endpoint_name].append(fallback_func)

    def register_fallback_endpoint(self, endpoint_name: str, fallback_endpoint: str) -> None:
        if endpoint_name not in self._fallback_endpoints:
            self._fallback_endpoints[endpoint_name] = []
        self._fallback_endpoints[endpoint_name].append(fallback_endpoint)

    def execute_fallback(self, endpoint_name: str, *args, **kwargs) -> Any:
        if endpoint_name in self._fallbacks:
            for fallback in self._fallbacks[endpoint_name]:
                try:
                    return fallback(*args, **kwargs)
                except Exception as e:
                    logger.warning("fallback_failed", endpoint=endpoint_name, error=str(e))
                    continue
        return None

    def get_fallback_endpoint(self, endpoint_name: str) -> str | None:
        fallbacks = self._fallback_endpoints.get(endpoint_name, [])
        return fallbacks[0] if fallbacks else None


class APIResilienceManager:
    def __init__(
        self,
        default_timeout: float = 30.0,
        max_retries: int = 3
    ) -> None:
        self._formula = "S * A + R - K"
        self._capability = "api_resilience_manager"
        self._id = "INV-009"
        self.default_timeout = default_timeout
        self.max_retries = max_retries
        self.rate_limit_handler = RateLimitHandler()
        self.backoff = ExponentialBackoff()
        self.circuit_breaker = CircuitBreaker()
        self.fallback_router = FallbackRouter()
        self._endpoints: dict[str, APIEndpoint] = {}

    def register_endpoint(self, endpoint: APIEndpoint) -> None:
        self._endpoints[endpoint.name] = endpoint

    def analyze(self, endpoint_name: str) -> dict[str, Any]:
        try:
            endpoint = self._endpoints.get(endpoint_name)
            if not endpoint:
                return {"status": "error", "error": f"Endpoint {endpoint_name} not registered"}
            circuit_state = self.circuit_breaker.get_state(endpoint_name)
            rate_available = self.rate_limit_handler.check_limit(
                endpoint_name,
                endpoint.rate_limit,
                endpoint.rate_window
            )
            wait_time = 0.0
            if not rate_available:
                wait_time = self.rate_limit_handler.get_wait_time(
                    endpoint_name,
                    endpoint.rate_limit,
                    endpoint.rate_window
                )
            result = {
                "endpoint": endpoint_name,
                "circuit_state": circuit_state.value,
                "can_execute": self.circuit_breaker.can_execute(endpoint_name) and rate_available,
                "rate_limit_available": rate_available,
                "wait_time_for_rate_limit": wait_time,
                "attempt_count": self.backoff.get_attempt_count(endpoint_name),
                "has_fallback": endpoint_name in self.fallback_router._fallbacks or endpoint_name in self.fallback_router._fallback_endpoints
            }
            logger.info("api_resilience_manager_success", capability=self._capability, endpoint=endpoint_name)
            return {"status": "success", "capability": self._capability, "result": result, "formula": self._formula}
        except Exception as exc:
            logger.error("api_resilience_manager_failed", capability=self._capability, error=str(exc))
            return {"status": "error", "capability": self._capability, "error": str(exc)}

    def execute(
        self,
        endpoint_name: str,
        operation: Callable,
        *args,
        **kwargs
    ) -> dict[str, Any]:
        endpoint = self._endpoints.get(endpoint_name)
        if not endpoint:
            return {"status": "error", "error": f"Endpoint {endpoint_name} not registered"}
        if not self.circuit_breaker.can_execute(endpoint_name):
            fallback_result = self.fallback_router.execute_fallback(endpoint_name, *args, **kwargs)
            if fallback_result is not None:
                return {"status": "fallback", "result": fallback_result}
            return {"status": "error", "error": "Circuit breaker is open"}
        if not self.rate_limit_handler.check_limit(endpoint_name, endpoint.rate_limit, endpoint.rate_window):
            wait_time = self.rate_limit_handler.get_wait_time(endpoint_name, endpoint.rate_limit, endpoint.rate_window)
            return {"status": "rate_limited", "wait_time": wait_time}
        return self._execute_with_retry(endpoint_name, operation, endpoint.max_retries, *args, **kwargs)

    def _execute_with_retry(
        self,
        endpoint_name: str,
        operation: Callable,
        max_retries: int,
        *args,
        **kwargs
    ) -> dict[str, Any]:
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                self.rate_limit_handler.record_request(endpoint_name)
                result = operation(*args, **kwargs)
                self.circuit_breaker.record_success(endpoint_name)
                self.backoff.reset(endpoint_name)
                return {"status": "success", "result": result, "attempts": attempt + 1}
            except Exception as exc:
                last_error = exc
                error_type = self._classify_error(exc)
                if error_type == ErrorType.PERMANENT:
                    self.circuit_breaker.record_failure(endpoint_name)
                    break
                if error_type == ErrorType.RATE_LIMIT:
                    self.circuit_breaker.record_failure(endpoint_name)
                    fallback_result = self.fallback_router.execute_fallback(endpoint_name, *args, **kwargs)
                    if fallback_result is not None:
                        return {"status": "fallback", "result": fallback_result}
                if attempt < max_retries:
                    delay = self.backoff.get_delay(endpoint_name)
                    time.sleep(delay)
        self.circuit_breaker.record_failure(endpoint_name)
        fallback_result = self.fallback_router.execute_fallback(endpoint_name, *args, **kwargs)
        if fallback_result is not None:
            return {"status": "fallback", "result": fallback_result}
        return {"status": "error", "error": str(last_error), "attempts": max_retries + 1}

    def _classify_error(self, error: Exception) -> ErrorType:
        error_str = str(error).lower()
        if "rate limit" in error_str or "429" in error_str:
            return ErrorType.RATE_LIMIT
        if "timeout" in error_str or "timed out" in error_str:
            return ErrorType.TIMEOUT
        if "401" in error_str or "403" in error_str or "unauthorized" in error_str:
            return ErrorType.PERMANENT
        if "500" in error_str or "502" in error_str or "503" in error_str:
            return ErrorType.TRANSIENT
        return ErrorType.UNKNOWN

    def register_fallback(self, endpoint_name: str, fallback_func: Callable) -> None:
        self.fallback_router.register_fallback(endpoint_name, fallback_func)


if __name__ == "__main__":
    manager = APIResilienceManager()
    endpoint = APIEndpoint(
        name="test_api",
        base_url="https://api.example.com",
        rate_limit=10,
        rate_window=60,
        max_retries=3
    )
    manager.register_endpoint(endpoint)
    result = manager.analyze("test_api")
    print(f"Status: {result['status']}")
    print(f"Circuit state: {result['result']['circuit_state']}")
    print(f"Can execute: {result['result']['can_execute']}")
    def mock_api_call():
        return {"data": "success"}
    exec_result = manager.execute("test_api", mock_api_call)
    print(f"Execution status: {exec_result['status']}")
    if exec_result['status'] == 'success':
        print(f"Result: {exec_result['result']}")
        print(f"Attempts: {exec_result['attempts']}")
    assert result["status"] == "success"
    assert exec_result["status"] in ["success", "fallback"]
    print("All tests passed!")
