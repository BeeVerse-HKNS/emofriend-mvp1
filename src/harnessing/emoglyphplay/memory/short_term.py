"""ShortTermMemory — Recent interaction memory with time-based decay.

Stores recent interactions and context with automatic decay, providing
a medium-duration memory layer between working and episodic memory.
"""

from __future__ import annotations

import time
from typing import Any


class ShortTermMemory:
    """ShortTermMemory — Recent interaction memory with time-based decay.

    Provides a time-decaying store for recent interactions. Items
    automatically expire after a configurable TTL.

    Args:
        ttl_seconds: Time-to-live for items in seconds. Default: 3600 (1 hour).
        max_items: Maximum number of items to store.
    """

    def __init__(self, ttl_seconds: float = 3600.0, max_items: int = 200) -> None:
        self.ttl_seconds = ttl_seconds
        self.max_items = max_items
        self._store: dict[str, tuple[Any, float]] = {}

    def store(self, key: str, value: Any) -> None:
        """Store a value with a timestamp for TTL tracking.

        Args:
            key: The key to store under.
            value: The value to store.
        """
        self._evict_expired()
        if len(self._store) >= self.max_items:
            oldest_key = min(self._store, key=lambda k: self._store[k][1])
            del self._store[oldest_key]
        self._store[key] = (value, time.time())

    def retrieve(self, key: str, default: Any = None) -> Any:
        """Retrieve a value if it hasn't expired.

        Args:
            key: The key to look up.
            default: Default value if key is not found or expired.

        Returns:
            The stored value, or default if not found/expired.
        """
        if key not in self._store:
            return default
        value, timestamp = self._store[key]
        if time.time() - timestamp > self.ttl_seconds:
            del self._store[key]
            return default
        return value

    def _evict_expired(self) -> None:
        """Remove all expired items."""
        now = time.time()
        expired = [k for k, (_, ts) in self._store.items() if now - ts > self.ttl_seconds]
        for k in expired:
            del self._store[k]

    def clear(self) -> None:
        """Clear all items from short-term memory."""
        self._store.clear()

    def size(self) -> int:
        """Return the number of non-expired items."""
        self._evict_expired()
        return len(self._store)
