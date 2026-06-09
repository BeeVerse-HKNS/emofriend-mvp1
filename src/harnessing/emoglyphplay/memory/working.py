"""WorkingMemory — Short-duration active processing memory.

Holds the current task context, active instructions, and immediate
scratchpad data for the EmoGlyphPlay engine.
"""

from __future__ import annotations

from typing import Any


class WorkingMemory:
    """WorkingMemory — Active processing memory for current task context.

    Provides a fast, ephemeral store for the current working context,
    similar to human working memory. Data is not persisted across sessions.

    Args:
        capacity: Maximum number of items the working memory can hold.
    """

    def __init__(self, capacity: int = 50) -> None:
        self.capacity = capacity
        self._store: dict[str, Any] = {}
        self._access_order: list[str] = []

    def store(self, key: str, value: Any) -> None:
        """Store a value in working memory.

        Args:
            key: The key to store under.
            value: The value to store.
        """
        if key in self._store:
            self._access_order.remove(key)
        elif len(self._store) >= self.capacity:
            evicted = self._access_order.pop(0)
            del self._store[evicted]
        self._store[key] = value
        self._access_order.append(key)

    def retrieve(self, key: str, default: Any = None) -> Any:
        """Retrieve a value from working memory.

        Args:
            key: The key to look up.
            default: Default value if key is not found.

        Returns:
            The stored value, or default if not found.
        """
        if key in self._store:
            self._access_order.remove(key)
            self._access_order.append(key)
            return self._store[key]
        return default

    def clear(self) -> None:
        """Clear all items from working memory."""
        self._store.clear()
        self._access_order.clear()

    def size(self) -> int:
        """Return the number of items currently stored."""
        return len(self._store)

    def keys(self) -> list[str]:
        """Return all keys in access order (most recent last)."""
        return list(self._access_order)
