"""EpisodicMemory — Episode-based long-term memory for interaction sequences.

Stores and retrieves complete interaction episodes (conversations, workflows)
as structured records, enabling recall of past experiences.
"""

from __future__ import annotations

import time
import uuid
from typing import Any


class EpisodicMemory:
    """EpisodicMemory — Episode-based long-term memory.

    Stores complete interaction episodes as structured records with
    timestamps, tags, and metadata for later retrieval and replay.

    Args:
        max_episodes: Maximum number of episodes to retain.
    """

    def __init__(self, max_episodes: int = 1000) -> None:
        self.max_episodes = max_episodes
        self._episodes: dict[str, dict[str, Any]] = {}

    def store_episode(
        self,
        title: str,
        content: dict,
        tags: list[str] | None = None,
    ) -> str:
        """Store a new episode.

        Args:
            title: Human-readable title for the episode.
            content: The episode content dictionary.
            tags: Optional tags for categorization.

        Returns:
            The unique episode ID.
        """
        if len(self._episodes) >= self.max_episodes:
            oldest_id = min(self._episodes, key=lambda k: self._episodes[k]["timestamp"])
            del self._episodes[oldest_id]

        episode_id = f"ep-{uuid.uuid4().hex[:8]}"
        self._episodes[episode_id] = {
            "id": episode_id,
            "title": title,
            "content": content,
            "tags": tags or [],
            "timestamp": time.time(),
        }
        return episode_id

    def retrieve_episode(self, episode_id: str) -> dict | None:
        """Retrieve an episode by its ID.

        Args:
            episode_id: The episode identifier.

        Returns:
            The episode dictionary, or None if not found.
        """
        return self._episodes.get(episode_id)

    def search_by_tags(self, tags: list[str]) -> list[dict]:
        """Search for episodes matching any of the given tags.

        Args:
            tags: Tags to search for.

        Returns:
            List of matching episode dictionaries.
        """
        results = []
        for ep in self._episodes.values():
            if any(tag in ep["tags"] for tag in tags):
                results.append(ep)
        return results

    def list_episodes(self, limit: int = 50) -> list[dict]:
        """List recent episodes, newest first.

        Args:
            limit: Maximum number of episodes to return.

        Returns:
            List of episode summary dictionaries.
        """
        sorted_eps = sorted(
            self._episodes.values(),
            key=lambda ep: ep["timestamp"],
            reverse=True,
        )
        return [
            {"id": ep["id"], "title": ep["title"], "tags": ep["tags"], "timestamp": ep["timestamp"]}
            for ep in sorted_eps[:limit]
        ]

    def clear(self) -> None:
        """Clear all episodes."""
        self._episodes.clear()
