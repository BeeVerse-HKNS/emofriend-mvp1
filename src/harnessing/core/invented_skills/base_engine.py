from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from .base_invention_engine import InventionResult


class BaseInventionEngine(ABC):
    name: str
    invention_id: str
    operator: str
    formula: str
    category: str
    description: str

    @abstractmethod
    def execute(self, context: dict[str, Any]) -> InventionResult:
        ...

    @abstractmethod
    def validate(self, result: InventionResult) -> bool:
        ...

    @abstractmethod
    def get_synergy_partners(self) -> list[str]:
        ...

    def get_info(self) -> dict[str, str]:
        return {
            "name": self.name,
            "invention_id": self.invention_id,
            "operator": self.operator,
            "formula": self.formula,
            "category": self.category,
            "description": self.description,
        }
