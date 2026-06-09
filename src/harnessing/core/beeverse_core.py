from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger()


class RiskCategory(str, Enum):
    FAILURE = "failure"
    RECOVERY = "recovery"
    SECURITY = "security"
    DATA = "data"
    HUMAN = "human"
    SYSTEM = "system"
    NETWORK = "network"
    RESOURCE = "resource"
    INTEGRATION = "integration"
    TIMING = "timing"
    COMPLIANCE = "compliance"
    SUPPLY_CHAIN = "supply_chain"
    ENVIRONMENTAL = "environmental"
    PRIVACY = "privacy"
    BUSINESS_CONTINUITY = "business_continuity"


class CoreVerdict(str, Enum):
    SAFE = "safe"
    RISKY = "risky"
    BLOCKED = "blocked"
    RECOVERED = "recovered"


@dataclass
class CoreAssessment:
    verdict: CoreVerdict
    risk_categories: list[RiskCategory]
    risk_score: float
    predictions: list[dict[str, Any]]
    checkpoint_id: str
    healing_applied: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class TaskContext:
    task_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    task_type: str = "general"
    prompt: str = ""
    model: str = ""
    vram_available: float = 0.0
    ram_available: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class BeeVerseCore:
    def __init__(self) -> None:
        self._error_history: list[dict[str, Any]] = []
        self._checkpoint_store: dict[str, dict[str, Any]] = {}
        self._pattern_db: dict[str, int] = {}
        self._circuit_open: bool = False
        self._failure_count: int = 0
        self._circuit_threshold: int = 5
        self._circuit_recovery_seconds: float = 60.0
        self._last_failure_time: float = 0.0

    def assess(self, context: TaskContext) -> CoreAssessment:
        checkpoint_id = self._create_checkpoint(context)
        predictions = self._predict_risks(context)
        risk_categories = self._classify_risks(predictions)
        risk_score = self._compute_risk_score(predictions)
        healing_applied: list[str] = []

        if self._circuit_open:
            if self._should_try_recovery():
                healing_applied.append("circuit_breaker_recovery")
                self._circuit_open = False
                self._failure_count = 0
            else:
                return CoreAssessment(
                    verdict=CoreVerdict.BLOCKED,
                    risk_categories=risk_categories,
                    risk_score=1.0,
                    predictions=predictions,
                    checkpoint_id=checkpoint_id,
                    healing_applied=["circuit_breaker_active"],
                )

        if risk_score > 0.8:
            healing_applied.extend(self._apply_preventive_healing(context, predictions))
            verdict = CoreVerdict.RISKY
        elif risk_score > 0.5:
            healing_applied.extend(self._apply_light_healing(context, predictions))
            verdict = CoreVerdict.RISKY
        else:
            verdict = CoreVerdict.SAFE

        self._record_patterns(predictions)

        return CoreAssessment(
            verdict=verdict,
            risk_categories=risk_categories,
            risk_score=risk_score,
            predictions=predictions,
            checkpoint_id=checkpoint_id,
            healing_applied=healing_applied,
        )

    def report_success(self, task_id: str) -> None:
        self._failure_count = max(0, self._failure_count - 1)
        if task_id in self._checkpoint_store:
            self._checkpoint_store[task_id]["status"] = "completed"

    def report_failure(self, task_id: str, error: str) -> None:
        self._failure_count += 1
        self._last_failure_time = datetime.now().timestamp()
        self._error_history.append({
            "task_id": task_id,
            "error": error,
            "timestamp": datetime.now().isoformat(),
        })
        if task_id in self._checkpoint_store:
            self._checkpoint_store[task_id]["status"] = "failed"
            self._checkpoint_store[task_id]["error"] = error
        if self._failure_count >= self._circuit_threshold:
            self._circuit_open = True
            logger.warning("circuit_breaker_opened", failure_count=self._failure_count)

    def recover(self, task_id: str) -> dict[str, Any] | None:
        checkpoint = self._checkpoint_store.get(task_id)
        if checkpoint and checkpoint.get("status") == "failed":
            checkpoint["status"] = "recovered"
            return checkpoint
        return None

    def _create_checkpoint(self, context: TaskContext) -> str:
        checkpoint_id = context.task_id
        self._checkpoint_store[checkpoint_id] = {
            "task_id": context.task_id,
            "task_type": context.task_type,
            "prompt_preview": context.prompt[:200],
            "model": context.model,
            "status": "running",
            "created_at": datetime.now().isoformat(),
            "context_snapshot": {
                "vram": context.vram_available,
                "ram": context.ram_available,
            },
        }
        return checkpoint_id

    def _predict_risks(self, context: TaskContext) -> list[dict[str, Any]]:
        predictions: list[dict[str, Any]] = []

        if context.vram_available > 0 and context.vram_available < 2.0:
            predictions.append({
                "category": RiskCategory.RESOURCE,
                "probability": 0.9,
                "description": "vram_critical",
                "action": "reduce_batch_or_offload",
            })

        if context.ram_available > 0 and context.ram_available < 4.0:
            predictions.append({
                "category": RiskCategory.RESOURCE,
                "probability": 0.7,
                "description": "ram_low",
                "action": "enable_streaming",
            })

        if self._circuit_open:
            predictions.append({
                "category": RiskCategory.SYSTEM,
                "probability": 1.0,
                "description": "circuit_breaker_active",
                "action": "wait_or_fallback",
            })

        if len(context.prompt) > 8000:
            predictions.append({
                "category": RiskCategory.DATA,
                "probability": 0.5,
                "description": "prompt_too_long",
                "action": "chunk_or_summarize",
            })

        recent_errors = len([e for e in self._error_history[-10:]])
        if recent_errors >= 3:
            predictions.append({
                "category": RiskCategory.FAILURE,
                "probability": 0.6,
                "description": "error_rate_high",
                "action": "review_recent_errors",
            })

        for cat in RiskCategory:
            if cat.value not in [p["category"].value if isinstance(p["category"], RiskCategory) else p["category"] for p in predictions]:
                base_prob = self._estimate_base_probability(context, cat)
                if base_prob > 0.1:
                    predictions.append({
                        "category": cat,
                        "probability": base_prob,
                        "description": f"{cat.value}_baseline_risk",
                        "action": "monitor",
                    })

        return predictions

    def _estimate_base_probability(self, context: TaskContext, category: RiskCategory) -> float:
        pattern_key = f"{context.task_type}:{category.value}"
        count = self._pattern_db.get(pattern_key, 0)
        if count > 5:
            return min(0.4, count * 0.05)
        return 0.05

    def _classify_risks(self, predictions: list[dict[str, Any]]) -> list[RiskCategory]:
        categories: list[RiskCategory] = []
        for p in predictions:
            cat = p["category"]
            if isinstance(cat, RiskCategory):
                categories.append(cat)
            else:
                try:
                    categories.append(RiskCategory(cat))
                except ValueError:
                    pass
        return list(set(categories))

    def _compute_risk_score(self, predictions: list[dict[str, Any]]) -> float:
        if not predictions:
            return 0.0
        max_prob = max(p["probability"] for p in predictions)
        avg_prob = sum(p["probability"] for p in predictions) / len(predictions)
        return 0.6 * max_prob + 0.4 * avg_prob

    def _apply_preventive_healing(self, context: TaskContext, predictions: list[dict[str, Any]]) -> list[str]:
        applied: list[str] = []
        for p in predictions:
            if p["probability"] > 0.7:
                action = p["action"]
                if action == "reduce_batch_or_offload":
                    context.metadata["force_offload"] = True
                    applied.append("force_cpu_offload")
                elif action == "enable_streaming":
                    context.metadata["streaming"] = True
                    applied.append("streaming_enabled")
                elif action == "chunk_or_summarize":
                    context.metadata["chunk_prompt"] = True
                    applied.append("prompt_chunked")
        return applied

    def _apply_light_healing(self, context: TaskContext, predictions: list[dict[str, Any]]) -> list[str]:
        applied: list[str] = []
        for p in predictions:
            if 0.5 < p["probability"] <= 0.7:
                action = p["action"]
                if action == "review_recent_errors":
                    applied.append("error_review_flagged")
                elif action == "monitor":
                    applied.append("monitoring_enhanced")
        return applied

    def _record_patterns(self, predictions: list[dict[str, Any]]) -> None:
        for p in predictions:
            cat = p["category"]
            key = f"general:{cat.value if isinstance(cat, RiskCategory) else cat}"
            self._pattern_db[key] = self._pattern_db.get(key, 0) + 1

    def _should_try_recovery(self) -> bool:
        elapsed = datetime.now().timestamp() - self._last_failure_time
        return elapsed > self._circuit_recovery_seconds
