from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class InventionCategory(Enum):
    SCI = "SCI"
    EWF = "EWF"


class ConfidenceLevel(Enum):
    VERIFIED = "✅"
    RESEARCHED = "🔍"
    INFERRED = "⚠️"
    UNCERTAIN = "❌"


@dataclass
class InventionResult:
    output: dict[str, Any]
    confidence: ConfidenceLevel = ConfidenceLevel.INFERRED
    synergy_detected: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    invention_id: str = ""
    execution_time_ms: float = 0.0

    def is_valid(self) -> bool:
        return bool(self.output) and self.confidence != ConfidenceLevel.UNCERTAIN
