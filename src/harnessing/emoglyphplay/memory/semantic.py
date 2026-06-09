"""SemanticMemory — Knowledge graph-based long-term semantic memory.

Stores structured facts, concepts, and relationships as a semantic
knowledge graph for reasoning and retrieval.
"""

from __future__ import annotations

from typing import Any


class SemanticMemory:
    """SemanticMemory — Knowledge graph-based semantic memory.

    Stores facts, concepts, and their relationships in a graph structure,
    enabling semantic queries and knowledge inference.

    Args:
        max_facts: Maximum number of facts to retain.
    """

    def __init__(self, max_facts: int = 5000) -> None:
        self.max_facts = max_facts
        self._facts: dict[str, dict[str, Any]] = {}
        self._relations: list[dict[str, str]] = []

    def store_fact(self, fact_id: str, content: dict, category: str = "general") -> None:
        """Store a semantic fact.

        Args:
            fact_id: Unique identifier for the fact.
            content: The fact content dictionary.
            category: Category label for the fact.
        """
        if len(self._facts) >= self.max_facts:
            oldest = next(iter(self._facts))
            del self._facts[oldest]
        self._facts[fact_id] = {"id": fact_id, "content": content, "category": category}

    def retrieve_fact(self, fact_id: str) -> dict | None:
        """Retrieve a fact by its ID.

        Args:
            fact_id: The fact identifier.

        Returns:
            The fact dictionary, or None if not found.
        """
        return self._facts.get(fact_id)

    def add_relation(self, source: str, relation: str, target: str) -> None:
        """Add a semantic relation between two facts.

        Args:
            source: Source fact ID.
            relation: Relation type string.
            target: Target fact ID.
        """
        self._relations.append({"source": source, "relation": relation, "target": target})

    def query_relations(self, fact_id: str, direction: str = "outgoing") -> list[dict]:
        """Query relations for a given fact.

        Args:
            fact_id: The fact ID to query relations for.
            direction: "outgoing" (source→target) or "incoming" (target→source).

        Returns:
            List of matching relation dictionaries.
        """
        if direction == "outgoing":
            return [r for r in self._relations if r["source"] == fact_id]
        else:
            return [r for r in self._relations if r["target"] == fact_id]

    def search_by_category(self, category: str) -> list[dict]:
        """Search for facts by category.

        Args:
            category: The category to search for.

        Returns:
            List of matching fact dictionaries.
        """
        return [f for f in self._facts.values() if f["category"] == category]

    def clear(self) -> None:
        """Clear all facts and relations."""
        self._facts.clear()
        self._relations.clear()
