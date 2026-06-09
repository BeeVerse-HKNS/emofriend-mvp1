from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from harnessing.core.memory_engine import MemoryEngine

logger = structlog.get_logger()


class Scenario(str, Enum):
    GLM_FIRST = "glm_first"
    LOCAL_THEN_GLM = "local_then_glm"
    LOCAL_ONLY = "local_only"
    GLM_ONLY = "glm_only"
    BEEVERSE_ONLY = "beeverse_only"
    BEEVERSE_GEMMA4 = "beeverse_gemma4"
    BEEVERSE_QWEN36 = "beeverse_qwen36"


BEEVERSE_VARIANTS = {
    "default": "beeverse",
    "gemma4": "beeverse-gemma4",
    "qwen36": "beeverse-qwen36",
}

BEEVERSE_VARIANT_CONFIGS = {
    "default": {
        "model": "beeverse",
        "description": "BeeVerse based on Qwen3:8B",
        "vram": "8GB",
        "ctx": 8192,
    },
    "gemma4": {
        "model": "beeverse-gemma4",
        "description": "BeeVerse based on Gemma 4 12B",
        "vram": "8GB + CPU offload",
        "ctx": 8192,
    },
    "qwen36": {
        "model": "beeverse-qwen36",
        "description": "BeeVerse based on Qwen3.6 35B-A3B MoE",
        "vram": "8GB + CPU offload (MoE efficient)",
        "ctx": 16384,
    },
}


@dataclass
class MixedResult:
    scenario: Scenario
    final_content: str
    local_content: str | None = None
    cloud_content: str | None = None
    layer1_model: str = "none"
    layer1_speed: float = 0.0
    layer2_model: str = "none"
    layer2_speed: float = 0.0
    layer1_duration: float = 0.0
    layer2_duration: float = 0.0
    task: str = "general"
    timestamp: datetime = field(default_factory=datetime.now)
    decision_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    metadata: dict[str, Any] = field(default_factory=dict)


class MixedLLMEngine:
    def __init__(
        self,
        memory_engine: MemoryEngine | None = None,
        use_beeverse: bool = True,
        beeverse_variant: str = "default",
    ) -> None:
        self._router = None
        self._scanner = None
        self._llm = None
        self._memory = memory_engine
        self._use_beeverse = use_beeverse
        self._beeverse = None
        self._beeverse_variant = beeverse_variant
        self._variant_model = BEEVERSE_VARIANTS.get(beeverse_variant, "beeverse")

    def _ensure_components(self) -> None:
        if self._router is None:
            from harnessing.core.model_router import ModelRouter
            self._router = ModelRouter()
        if self._scanner is None:
            from harnessing.tools.local_scanner import LocalScanner
            self._scanner = LocalScanner()
        if self._llm is None:
            from harnessing.core.llm_router import LLMRouter
            self._llm = LLMRouter()
        if self._beeverse is None and self._use_beeverse:
            from harnessing.core.beeverse import BeeVerse
            self._beeverse = BeeVerse()

    def _glm_available(self) -> bool:
        self._ensure_components()
        return self._llm.is_ollama_available or len(self._llm.available_providers) > 0

    def _local_available(self) -> bool:
        self._ensure_components()
        return self._scanner.is_available()

    def process(self, content: str, task: str = "general") -> MixedResult:
        self._ensure_components()

        if self._use_beeverse and self._beeverse is not None:
            return self._beeverse_process(content, task)

        glm_busy = not self._glm_available()
        local_busy = not self._local_available()

        logger.info(
            "mixed_llm_orchestration",
            glm_available=not glm_busy,
            local_available=not local_busy,
            task=task,
        )

        if not glm_busy and local_busy:
            result = self._glm_only(content, task)
        elif not local_busy and not glm_busy:
            result = self._local_then_glm(content, task)
        elif not local_busy and glm_busy:
            result = self._local_only(content, task)
        else:
            result = self._local_only(content, task)

        if self._memory:
            self._save_decision(content, task, result)

        return result

    def _beeverse_process(self, content: str, task: str) -> MixedResult:
        from harnessing.core.beeverse import BeeVerseRequest

        variant_info = BEEVERSE_VARIANT_CONFIGS.get(
            self._beeverse_variant, BEEVERSE_VARIANT_CONFIGS["default"]
        )
        logger.info(
            "scenario_beeverse_variant",
            variant=self._beeverse_variant,
            model=self._variant_model,
            description=variant_info["description"],
            message="BeeVerse variant — pure local, zero API cost",
        )

        import time
        start = time.time()

        resp = self._beeverse.process(BeeVerseRequest(prompt=content, task_type=task))

        duration = time.time() - start
        speed = len(content.split()) / duration if duration > 0 else 0.0

        scenario_map = {
            "default": Scenario.BEEVERSE_ONLY,
            "gemma4": Scenario.BEEVERSE_GEMMA4,
            "qwen36": Scenario.BEEVERSE_QWEN36,
        }
        scenario = scenario_map.get(self._beeverse_variant, Scenario.BEEVERSE_ONLY)

        result = MixedResult(
            scenario=scenario,
            final_content=resp.content,
            local_content=resp.content,
            layer1_model=self._variant_model,
            layer1_speed=speed,
            layer1_duration=duration,
            layer2_model="none",
            task=task,
            metadata={
                "confidence": "verified",
                "note": f"BeeVerse {self._beeverse_variant} variant — zero API cost",
                "variant": self._beeverse_variant,
                "variant_model": self._variant_model,
                "creativity_boost": resp.creativity_boost,
                "strategies": resp.strategies_applied,
                "scenario": resp.scenario.value,
                "quality_score": resp.quality_score,
            },
        )

        if self._memory:
            self._save_decision(content, task, result)

        return result

    @staticmethod
    def list_variants() -> dict[str, dict]:
        return BEEVERSE_VARIANT_CONFIGS.copy()

    @staticmethod
    def get_variant_model(variant: str) -> str:
        return BEEVERSE_VARIANTS.get(variant, "beeverse")

    def _glm_only(self, content: str, task: str) -> MixedResult:
        logger.info("scenario_glm_first", message="GLM available, local busy - using GLM only")

        import time
        start = time.time()

        choice = self._router.route(task)
        cloud_model = choice.cloud_model or "glm-5.1"

        result_text = self._llm.generate(
            prompt=content,
            model=cloud_model if "/" in cloud_model else None,
        )

        duration = time.time() - start
        speed = len(content.split()) / duration if duration > 0 else 0.0

        return MixedResult(
            scenario=Scenario.GLM_FIRST,
            final_content=result_text,
            cloud_content=result_text,
            layer1_model="none",
            layer2_model=cloud_model,
            layer2_speed=speed,
            layer2_duration=duration,
            task=task,
            metadata={"confidence": "verified", "note": "GLM completed all"},
        )

    def _local_then_glm(self, content: str, task: str) -> MixedResult:
        logger.info(
            "scenario_local_then_glm",
            message="Both available - Local first, then GLM continues",
        )

        import time
        layer1_start = time.time()

        choice = self._router.route(task)

        if task == "code":
            local_result = self._scanner.scan_code(content)
        elif task == "text":
            local_result = self._scanner.scan_text(content)
        elif task == "classify":
            cat_result = self._scanner.classify(content, ["AI", "Code", "Text", "Other"])
            layer1_duration = time.time() - layer1_start
            return MixedResult(
                scenario=Scenario.LOCAL_THEN_GLM,
                final_content=str(cat_result),
                local_content=str(cat_result),
                layer1_model=local_result.model_used,
                layer1_speed=local_result.tokens_per_second,
                layer1_duration=layer1_duration,
                task=task,
                metadata={"confidence": "verified", "note": "Classify - no GLM needed"},
            )
        elif task == "keyword":
            kw_result = self._scanner.extract_keywords(content)
            layer1_duration = time.time() - layer1_start
            return MixedResult(
                scenario=Scenario.LOCAL_THEN_GLM,
                final_content=", ".join(kw_result),
                local_content=", ".join(kw_result),
                layer1_model=local_result.model_used,
                layer1_speed=local_result.tokens_per_second,
                layer1_duration=layer1_duration,
                task=task,
                metadata={"confidence": "verified", "note": "Keywords - no GLM needed"},
            )
        else:
            local_result = self._scanner.scan_text(content)

        layer1_duration = time.time() - layer1_start

        logger.info("local_completed", model=local_result.model_used, duration=layer1_duration)

        layer2_start = time.time()
        cloud_model = choice.cloud_model or "glm-5.1"

        enhance_prompt = (
            f"Here is the initial analysis from local model:\n\n{local_result.content}\n\n"
            "Please enhance and refine this analysis with deeper insights."
        )
        cloud_result = self._llm.generate(
            prompt=enhance_prompt,
            model=cloud_model if "/" in cloud_model else None,
        )

        layer2_duration = time.time() - layer2_start
        layer2_speed = len(cloud_result.split()) / layer2_duration if layer2_duration > 0 else 0.0

        logger.info("glm_continued", model=cloud_model, duration=layer2_duration)

        return MixedResult(
            scenario=Scenario.LOCAL_THEN_GLM,
            final_content=cloud_result,
            local_content=local_result.content,
            cloud_content=cloud_result,
            layer1_model=local_result.model_used,
            layer1_speed=local_result.tokens_per_second,
            layer1_duration=layer1_duration,
            layer2_model=cloud_model,
            layer2_speed=layer2_speed,
            layer2_duration=layer2_duration,
            task=task,
            metadata={
                "confidence": "verified",
                "note": "Local completed first, GLM continued",
            },
        )

    def _local_only(self, content: str, task: str) -> MixedResult:
        logger.info("scenario_local_only", message="GLM busy - using Local only")

        import time
        start = time.time()

        if task == "code":
            result = self._scanner.scan_code(content)
        elif task == "text":
            result = self._scanner.scan_text(content)
        elif task == "classify":
            result = self._scanner.classify(content, ["AI", "Code", "Text", "Other"])
        elif task == "keyword":
            kw_result = self._scanner.extract_keywords(content)
            duration = time.time() - start
            return MixedResult(
                scenario=Scenario.LOCAL_ONLY,
                final_content=", ".join(kw_result),
                local_content=", ".join(kw_result),
                layer1_model=self._scanner.get_loaded_model() or "qwen3:8b",
                layer1_speed=result.tokens_per_second if hasattr(result, "tokens_per_second") else 0.0,
                layer1_duration=duration,
                task=task,
                metadata={"confidence": "verified", "note": "Local only - GLM busy"},
            )
        else:
            result = self._scanner.scan_text(content)

        duration = time.time() - start

        return MixedResult(
            scenario=Scenario.LOCAL_ONLY,
            final_content=result.content,
            local_content=result.content,
            layer1_model=result.model_used,
            layer1_speed=result.tokens_per_second,
            layer1_duration=duration,
            task=task,
            metadata={"confidence": "verified", "note": "Local only - GLM busy"},
        )

    def _save_decision(self, content: str, task: str, result: MixedResult) -> None:
        if not self._memory:
            return

        alternatives = [
            {"scenario": Scenario.GLM_FIRST.value, "desc": "GLM only - when local is busy"},
            {"scenario": Scenario.LOCAL_THEN_GLM.value, "desc": "Local first, then GLM continues - optimal quality"},
            {"scenario": Scenario.LOCAL_ONLY.value, "desc": "Local only - when GLM is busy"},
            {"scenario": Scenario.GLM_ONLY.value, "desc": "GLM only - fallback scenario"},
        ]

        chosen = result.scenario.value
        rationale = (
            f"Task={task}, Layer1={result.layer1_model}, "
            f"Layer2={result.layer2_model}, Confidence={result.metadata.get('confidence', 'unknown')}"
        )

        try:
            self._memory.save_decision(
                task=f"mixed_llm_{task}",
                alternatives=alternatives,
                chosen=chosen,
                rationale=rationale,
            )
            logger.info("memory_decision_saved", decision_id=result.decision_id, scenario=chosen)
        except Exception as e:
            logger.warning("memory_decision_failed", error=str(e), decision_id=result.decision_id)
