from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import structlog

logger = structlog.get_logger()


class Complexity(str, Enum):
    FAST = "fast"
    STANDARD = "standard"
    DEEP = "deep"
    PARALLEL = "parallel"


class TaskType(str, Enum):
    CLASSIFY = "classify"
    KEYWORD_EXTRACT = "keyword_extract"
    CODE_SCAN = "code_scan"
    TEXT_ANALYZE = "text_analyze"
    COMPLEX_REASONING = "complex_reasoning"
    CONTENT_CREATE = "content_create"
    GENERAL = "general"


@dataclass
class ModelChoice:
    layer: str
    local_model: str | None = None
    cloud_model: str | None = None
    needs_cloud_verification: bool = False

    @property
    def is_local_only(self) -> bool:
        return self.layer == "local"

    @property
    def is_cloud_only(self) -> bool:
        return self.layer == "cloud"

    @property
    def is_parallel(self) -> bool:
        return self.layer == "both"


_TASK_COMPLEXITY_MAP: dict[TaskType, Complexity] = {
    TaskType.CLASSIFY: Complexity.FAST,
    TaskType.KEYWORD_EXTRACT: Complexity.FAST,
    TaskType.CODE_SCAN: Complexity.STANDARD,
    TaskType.TEXT_ANALYZE: Complexity.STANDARD,
    TaskType.COMPLEX_REASONING: Complexity.DEEP,
    TaskType.CONTENT_CREATE: Complexity.DEEP,
    TaskType.GENERAL: Complexity.STANDARD,
}

_FAST_KEYWORDS = {"classify", "categorize", "tag", "label", "keyword"}
_DEEP_KEYWORDS = {"create", "write", "generate", "compose", "design", "story"}
_CODE_KEYWORDS = {"code", "bug", "debug", "scan", "review"}

_LOCAL_FAST_MODEL = "qwen3:4b"
_LOCAL_STANDARD_MODEL = "qwen3:8b"
_CLOUD_MODEL = "BeeVerse"


class ModelRouter:
    def __init__(self, local_available: bool = False, cloud_available: bool = False) -> None:
        self._local_available = local_available
        self._cloud_available = cloud_available

    def update_availability(self, local: bool, cloud: bool) -> None:
        self._local_available = local
        self._cloud_available = cloud

    def route(self, task: TaskType | str, complexity: Complexity | str | None = None) -> ModelChoice:
        task_type = self._resolve_task_type(task)
        resolved_complexity = self._resolve_complexity(task_type, complexity)
        choice = self._compute_route(task_type, resolved_complexity)
        logger.info(
            "model_routed",
            task=task_type.value,
            complexity=resolved_complexity.value,
            layer=choice.layer,
            local_model=choice.local_model,
            cloud_model=choice.cloud_model,
            needs_cloud_verification=choice.needs_cloud_verification,
        )
        return choice

    def route_prompt(self, prompt: str) -> ModelChoice:
        prompt_lower = prompt.lower()
        words = set(prompt_lower.split())

        if words & _FAST_KEYWORDS:
            task = TaskType.CLASSIFY
        elif words & _DEEP_KEYWORDS:
            task = TaskType.CONTENT_CREATE
        elif words & _CODE_KEYWORDS:
            task = TaskType.CODE_SCAN
        else:
            task = TaskType.GENERAL

        return self.route(task)

    def _resolve_task_type(self, task: TaskType | str) -> TaskType:
        if isinstance(task, TaskType):
            return task
        try:
            return TaskType(task)
        except ValueError:
            logger.warning("unknown_task_type", raw=task, fallback=TaskType.GENERAL.value)
            return TaskType.GENERAL

    def _resolve_complexity(self, task_type: TaskType, complexity: Complexity | str | None) -> Complexity:
        if complexity is None:
            return _TASK_COMPLEXITY_MAP.get(task_type, Complexity.STANDARD)
        if isinstance(complexity, Complexity):
            return complexity
        try:
            return Complexity(complexity)
        except ValueError:
            logger.warning("unknown_complexity", raw=complexity, fallback=Complexity.STANDARD.value)
            return Complexity.STANDARD

    def _compute_route(self, task_type: TaskType, complexity: Complexity) -> ModelChoice:
        if not self._local_available and not self._cloud_available:
            raise ValueError("No model available: both local and cloud are offline")

        if complexity == Complexity.FAST:
            return self._route_fast()
        if complexity == Complexity.STANDARD:
            return self._route_standard()
        if complexity == Complexity.DEEP:
            return self._route_deep()
        if complexity == Complexity.PARALLEL:
            return self._route_parallel()

        return self._route_standard()

    def _route_fast(self) -> ModelChoice:
        if self._local_available:
            return ModelChoice(
                layer="local",
                local_model=_LOCAL_FAST_MODEL,
                needs_cloud_verification=False,
            )
        return ModelChoice(
            layer="cloud",
            cloud_model=_CLOUD_MODEL,
            needs_cloud_verification=False,
        )

    def _route_standard(self) -> ModelChoice:
        if self._local_available:
            return ModelChoice(
                layer="local",
                local_model=_LOCAL_STANDARD_MODEL,
                needs_cloud_verification=self._cloud_available,
                cloud_model=_CLOUD_MODEL if self._cloud_available else None,
            )
        return ModelChoice(
            layer="cloud",
            cloud_model=_CLOUD_MODEL,
            needs_cloud_verification=False,
        )

    def _route_deep(self) -> ModelChoice:
        if self._cloud_available:
            return ModelChoice(
                layer="cloud",
                cloud_model=_CLOUD_MODEL,
                local_model=_LOCAL_STANDARD_MODEL if self._local_available else None,
                needs_cloud_verification=False,
            )
        return ModelChoice(
            layer="local",
            local_model=_LOCAL_STANDARD_MODEL,
            needs_cloud_verification=False,
        )

    def _route_parallel(self) -> ModelChoice:
        if self._local_available and self._cloud_available:
            return ModelChoice(
                layer="both",
                local_model=_LOCAL_STANDARD_MODEL,
                cloud_model=_CLOUD_MODEL,
                needs_cloud_verification=False,
            )
        if self._cloud_available:
            return ModelChoice(
                layer="cloud",
                cloud_model=_CLOUD_MODEL,
                needs_cloud_verification=False,
            )
        return ModelChoice(
            layer="local",
            local_model=_LOCAL_STANDARD_MODEL,
            needs_cloud_verification=False,
        )
