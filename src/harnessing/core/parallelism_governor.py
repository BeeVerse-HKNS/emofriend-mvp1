from __future__ import annotations

import logging
import os
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

try:
    import psutil

    _PSUTIL_AVAILABLE = True
except ImportError:
    _PSUTIL_AVAILABLE = False
    logger.warning("psutil_not_available falling_back_to_fixed_concurrency")


class GovernorState(Enum):
    IDLE = "idle"
    SCALING_UP = "scaling_up"
    SCALING_DOWN = "scaling_down"
    SATURATED = "saturated"
    THROTTLED = "throttled"


@dataclass
class ResourceSnapshot:
    timestamp: float
    ram_percent: float
    cpu_percent: float
    active_concurrent: int
    queue_depth: int
    state: GovernorState


@dataclass
class GovernorStats:
    total_acquires: int = 0
    total_releases: int = 0
    total_waits: int = 0
    scale_up_events: int = 0
    scale_down_events: int = 0
    throttle_events: int = 0
    max_concurrent_reached: int = 0
    history: deque = field(default_factory=lambda: deque(maxlen=200))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_acquires": self.total_acquires,
            "total_releases": self.total_releases,
            "total_waits": self.total_waits,
            "scale_up_events": self.scale_up_events,
            "scale_down_events": self.scale_down_events,
            "throttle_events": self.throttle_events,
            "max_concurrent_reached": self.max_concurrent_reached,
            "history_size": len(self.history),
        }


class Governor:
    def __init__(
        self,
        min_concurrent: int = 1,
        max_concurrent: int = 8,
        ram_high_watermark: float = 0.85,
        ram_low_watermark: float = 0.60,
        queue_high: int = 5,
        adjustment_interval_seconds: float = 1.0,
        wait_poll_interval: float = 0.05,
    ) -> None:
        self.min_concurrent = max(1, min_concurrent)
        self.max_concurrent = max(self.min_concurrent, max_concurrent)
        self.ram_high_watermark = ram_high_watermark
        self.ram_low_watermark = ram_low_watermark
        self.queue_high = queue_high
        self.adjustment_interval = adjustment_interval_seconds
        self.wait_poll_interval = wait_poll_interval

        self._current_max = self.max_concurrent
        self._active = 0
        self._queue_depth = 0
        self._lock = threading.RLock()
        self._condition = threading.Condition(self._lock)
        self._stats = GovernorStats()
        self._last_adjustment = 0.0
        self._state = GovernorState.IDLE
        self._psutil_available = _PSUTIL_AVAILABLE

        logger.info(
            f"governor_initialized min={self.min_concurrent} max={self.max_concurrent} "
            f"ram_high={ram_high_watermark} ram_low={ram_low_watermark} queue_high={queue_high} "
            f"psutil={self._psutil_available}"
        )

    def _read_ram_percent(self) -> float:
        if not self._psutil_available:
            return 0.5
        try:
            return psutil.virtual_memory().percent / 100.0
        except Exception as exc:
            logger.warning(f"governor_ram_read_failed error={exc}")
            return 0.5

    def _read_cpu_percent(self) -> float:
        if not self._psutil_available:
            return 0.3
        try:
            return psutil.cpu_percent(interval=None) / 100.0
        except Exception as exc:
            logger.warning(f"governor_cpu_read_failed error={exc}")
            return 0.3

    def _enqueue_request(self) -> None:
        with self._lock:
            self._queue_depth += 1

    def _dequeue_request(self) -> None:
        with self._lock:
            if self._queue_depth > 0:
                self._queue_depth -= 1

    def _maybe_adjust(self) -> None:
        now = time.time()
        if now - self._last_adjustment < self.adjustment_interval:
            return
        self._last_adjustment = now
        ram = self._read_ram_percent()
        cpu = self._read_cpu_percent()
        new_max = self._current_max
        new_state = self._state
        if ram >= self.ram_high_watermark:
            new_max = max(self.min_concurrent, self._current_max - 1)
            new_state = GovernorState.THROTTLED
            self._stats.throttle_events += 1
        elif self._queue_depth > self.queue_high and ram < self.ram_low_watermark:
            new_max = min(self.max_concurrent, self._current_max + 1)
            new_state = GovernorState.SCALING_UP
            self._stats.scale_up_events += 1
        elif self._queue_depth == 0 and ram < self.ram_low_watermark and cpu < 0.7:
            new_max = min(self.max_concurrent, self._current_max + 1)
            new_state = GovernorState.SCALING_UP
            self._stats.scale_up_events += 1
        elif self._queue_depth == 0 and ram > self.ram_low_watermark and self._current_max > self.min_concurrent:
            new_max = max(self.min_concurrent, self._current_max - 1)
            new_state = GovernorState.SCALING_DOWN
            self._stats.scale_down_events += 1
        if new_max != self._current_max:
            logger.info(
                f"governor_adjusted from={self._current_max} to={new_max} ram={ram:.2f} cpu={cpu:.2f} queue={self._queue_depth}"
            )
            self._current_max = new_max
        if self._active >= self._current_max:
            new_state = GovernorState.SATURATED
        elif self._active == 0:
            new_state = GovernorState.IDLE
        self._state = new_state
        snap = ResourceSnapshot(
            timestamp=now,
            ram_percent=round(ram, 4),
            cpu_percent=round(cpu, 4),
            active_concurrent=self._active,
            queue_depth=self._queue_depth,
            state=new_state,
        )
        self._stats.history.append(snap)

    def acquire(self, timeout: Optional[float] = None) -> bool:
        self._enqueue_request()
        deadline = None if timeout is None else time.time() + timeout
        try:
            with self._condition:
                self._maybe_adjust()
                while self._active >= self._current_max:
                    self._stats.total_waits += 1
                    if deadline is not None:
                        remaining = deadline - time.time()
                        if remaining <= 0:
                            logger.warning(
                                f"governor_acquire_timeout active={self._active} max={self._current_max}"
                            )
                            return False
                        self._condition.wait(timeout=min(remaining, 0.5))
                    else:
                        self._condition.wait(timeout=0.5)
                    self._maybe_adjust()
                self._active += 1
                if self._active > self._stats.max_concurrent_reached:
                    self._stats.max_concurrent_reached = self._active
                self._stats.total_acquires += 1
                return True
        finally:
            self._dequeue_request()

    def release(self) -> None:
        with self._condition:
            if self._active > 0:
                self._active -= 1
            self._stats.total_releases += 1
            self._condition.notify()

    def __enter__(self) -> "Governor":
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.release()

    def current_concurrent(self) -> int:
        with self._lock:
            return self._active

    def current_max(self) -> int:
        with self._lock:
            self._maybe_adjust()
            return self._current_max

    def queue_depth(self) -> int:
        with self._lock:
            return self._queue_depth

    def state(self) -> GovernorState:
        with self._lock:
            self._maybe_adjust()
            return self._state

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            self._maybe_adjust()
            base = self._stats.to_dict()
            base["current_active"] = self._active
            base["current_max"] = self._current_max
            base["min_concurrent"] = self.min_concurrent
            base["max_concurrent"] = self.max_concurrent
            base["ram_high_watermark"] = self.ram_high_watermark
            base["ram_low_watermark"] = self.ram_low_watermark
            base["queue_high"] = self.queue_high
            base["queue_depth"] = self._queue_depth
            base["state"] = self._state.value
            base["psutil_available"] = self._psutil_available
            base["ram_percent"] = round(self._read_ram_percent(), 4)
            base["cpu_percent"] = round(self._read_cpu_percent(), 4)
            return base

    def force_max(self, value: int) -> None:
        with self._condition:
            new_max = max(self.min_concurrent, min(self.max_concurrent, value))
            self._current_max = new_max
            self._condition.notify_all()
            logger.info(f"governor_max_forced to={new_max}")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(name)s | %(levelname)s | %(message)s")

    g = Governor(min_concurrent=2, max_concurrent=5)

    print("=== Single acquire/release ===")
    g.acquire()
    print(f"After acquire: active={g.current_concurrent()} max={g.current_max()}")
    g.release()
    print(f"After release: active={g.current_concurrent()}")

    print("\n=== Context manager ===")
    with g:
        print(f"Inside context: active={g.current_concurrent()}")
    print(f"After context: active={g.current_concurrent()}")

    print("\n=== Concurrent acquire test ===")
    import concurrent.futures

    def worker(i: int) -> int:
        with g:
            time.sleep(0.1)
            return i

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        results = list(pool.map(worker, range(8)))
    print(f"Completed {len(results)} tasks")
    print(f"Max concurrent reached: {g.stats()['max_concurrent_reached']}")

    print("\n=== Force max ===")
    g.force_max(3)
    print(f"After force_max(3): max={g.current_max()}")

    print(f"\nFinal stats: {g.stats()}")


if __name__ == "__main__":
    main()
