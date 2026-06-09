from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger()


class ConstraintType(str, Enum):
    VRAM_LIMIT = "vram_limit"
    RAM_LIMIT = "ram_limit"
    CPU_LIMIT = "cpu_limit"
    DISK_LIMIT = "disk_limit"
    TOKEN_LIMIT = "token_limit"
    TIME_LIMIT = "time_limit"


class CreativityStrategy(str, Enum):
    QUANTIZE_AND_COMPRESS = "quantize_and_compress"
    OFFLOAD_AND_STREAM = "offload_and_stream"
    CHUNK_AND_PARALLEL = "chunk_and_parallel"
    DISTILL_AND_MERGE = "distill_and_merge"
    ADAPTIVE_BATCHING = "adaptive_batching"
    KNOWLEDGE_SUBSTITUTE = "knowledge_substitute"
    SPECULATIVE_DECODE = "speculative_decode"
    CONSTRAINT_DRIVEN_PROMPT = "constraint_driven_prompt"


@dataclass
class HardwareProfile:
    vram_total_gb: float = 8.0
    vram_available_gb: float = 8.0
    ram_total_gb: float = 48.0
    ram_available_gb: float = 48.0
    cpu_cores: int = 16
    cpu_usage_pct: float = 0.0
    disk_free_gb: float = 100.0
    gpu_name: str = "unknown"
    supports_flash_attention: bool = False
    supports_kv_cache: bool = True


@dataclass
class AmplificationResult:
    amplification_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    strategies_applied: list[CreativityStrategy] = field(default_factory=list)
    creativity_boost: float = 1.0
    quality_score: float = 0.0
    dimensions_covered: set[str] = field(default_factory=set)
    constraint_transformations: list[dict[str, Any]] = field(default_factory=list)
    prompt_enhancements: list[str] = field(default_factory=list)
    model_recommendation: str = ""
    estimated_vram_usage_gb: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class CreativityDimension:
    name: str
    base_score: float
    amplified_score: float
    strategy_used: CreativityStrategy | None = None


_CONSTRAINT_STRATEGY_MAP: dict[ConstraintType, list[CreativityStrategy]] = {
    ConstraintType.VRAM_LIMIT: [
        CreativityStrategy.QUANTIZE_AND_COMPRESS,
        CreativityStrategy.OFFLOAD_AND_STREAM,
        CreativityStrategy.SPECULATIVE_DECODE,
        CreativityStrategy.KNOWLEDGE_SUBSTITUTE,
    ],
    ConstraintType.RAM_LIMIT: [
        CreativityStrategy.OFFLOAD_AND_STREAM,
        CreativityStrategy.CHUNK_AND_PARALLEL,
        CreativityStrategy.ADAPTIVE_BATCHING,
    ],
    ConstraintType.CPU_LIMIT: [
        CreativityStrategy.QUANTIZE_AND_COMPRESS,
        CreativityStrategy.DISTILL_AND_MERGE,
        CreativityStrategy.ADAPTIVE_BATCHING,
    ],
    ConstraintType.TOKEN_LIMIT: [
        CreativityStrategy.CONSTRAINT_DRIVEN_PROMPT,
        CreativityStrategy.KNOWLEDGE_SUBSTITUTE,
        CreativityStrategy.CHUNK_AND_PARALLEL,
    ],
    ConstraintType.TIME_LIMIT: [
        CreativityStrategy.SPECULATIVE_DECODE,
        CreativityStrategy.QUANTIZE_AND_COMPRESS,
        CreativityStrategy.KNOWLEDGE_SUBSTITUTE,
    ],
    ConstraintType.DISK_LIMIT: [
        CreativityStrategy.QUANTIZE_AND_COMPRESS,
        CreativityStrategy.DISTILL_AND_MERGE,
    ],
}

_MODEL_VRAM_MAP: dict[str, float] = {
    "qwen3:4b": 2.5,
    "qwen3:8b": 5.2,
    "qwen3.5:35b": 20.0,
    "deepseek-r1:8b": 5.0,
    "qwen3.5:9b": 6.0,
}


class BeeVerseAmplifier:
    def __init__(self, hardware: HardwareProfile | None = None) -> None:
        self._hardware = hardware or HardwareProfile(
            vram_total_gb=8.0,
            vram_available_gb=8.0,
            ram_total_gb=48.0,
            ram_available_gb=48.0,
            cpu_cores=16,
            gpu_name="RTX 3070 Ti Laptop",
        )
        self._amplification_history: list[AmplificationResult] = []
        self._strategy_effectiveness: dict[str, list[float]] = {}

    def update_hardware(self, hardware: HardwareProfile) -> None:
        self._hardware = hardware

    def detect_constraints(self) -> list[ConstraintType]:
        constraints: list[ConstraintType] = []
        hw = self._hardware

        if hw.vram_available_gb < 6.0:
            constraints.append(ConstraintType.VRAM_LIMIT)
        if hw.ram_available_gb < 16.0:
            constraints.append(ConstraintType.RAM_LIMIT)
        if hw.cpu_usage_pct > 80.0:
            constraints.append(ConstraintType.CPU_LIMIT)
        if hw.disk_free_gb < 20.0:
            constraints.append(ConstraintType.DISK_LIMIT)

        return constraints

    def amplify(self, task_type: str = "general", prompt: str = "") -> AmplificationResult:
        constraints = self.detect_constraints()
        strategies = self._select_strategies(constraints, task_type)
        dimensions = self._compute_dimensions(constraints, strategies)
        transformations = self._generate_transformations(constraints, strategies)
        prompt_enhancements = self._generate_prompt_enhancements(constraints, task_type)
        model_rec = self._recommend_model(task_type)
        creativity_boost = self._compute_creativity_boost(constraints, strategies)
        quality_score = self._estimate_quality(strategies, task_type)
        vram_est = self._estimate_vram_usage(model_rec, strategies)

        result = AmplificationResult(
            strategies_applied=strategies,
            creativity_boost=creativity_boost,
            quality_score=quality_score,
            dimensions_covered=dimensions,
            constraint_transformations=transformations,
            prompt_enhancements=prompt_enhancements,
            model_recommendation=model_rec,
            estimated_vram_usage_gb=vram_est,
        )

        self._amplification_history.append(result)
        self._record_effectiveness(strategies, quality_score)

        logger.info(
            "beeverse_amplifier",
            constraints=[c.value for c in constraints],
            strategies=[s.value for s in strategies],
            creativity_boost=creativity_boost,
            model=model_rec,
        )

        return result

    def get_creativity_dimensions(self) -> list[CreativityDimension]:
        constraints = self.detect_constraints()
        strategies = self._select_strategies(constraints, "general")

        dimensions = [
            CreativityDimension(
                name="creativity_depth",
                base_score=0.5,
                amplified_score=0.9 if CreativityStrategy.CONSTRAINT_DRIVEN_PROMPT in strategies else 0.5,
                strategy_used=CreativityStrategy.CONSTRAINT_DRIVEN_PROMPT if CreativityStrategy.CONSTRAINT_DRIVEN_PROMPT in strategies else None,
            ),
            CreativityDimension(
                name="quality_requirement",
                base_score=0.6,
                amplified_score=0.95 if CreativityStrategy.SPECULATIVE_DECODE in strategies else 0.7,
                strategy_used=CreativityStrategy.SPECULATIVE_DECODE if CreativityStrategy.SPECULATIVE_DECODE in strategies else None,
            ),
            CreativityDimension(
                name="vram_constraint",
                base_score=0.3 if self._hardware.vram_available_gb < 6.0 else 0.8,
                amplified_score=0.85 if CreativityStrategy.QUANTIZE_AND_COMPRESS in strategies else 0.5,
                strategy_used=CreativityStrategy.QUANTIZE_AND_COMPRESS if CreativityStrategy.QUANTIZE_AND_COMPRESS in strategies else None,
            ),
            CreativityDimension(
                name="ram_constraint",
                base_score=0.4 if self._hardware.ram_available_gb < 16.0 else 0.8,
                amplified_score=0.8 if CreativityStrategy.OFFLOAD_AND_STREAM in strategies else 0.5,
                strategy_used=CreativityStrategy.OFFLOAD_AND_STREAM if CreativityStrategy.OFFLOAD_AND_STREAM in strategies else None,
            ),
        ]

        return dimensions

    def _select_strategies(self, constraints: list[ConstraintType], task_type: str) -> list[CreativityStrategy]:
        strategy_scores: dict[CreativityStrategy, float] = {}

        for constraint in constraints:
            for strategy in _CONSTRAINT_STRATEGY_MAP.get(constraint, []):
                effectiveness = self._get_strategy_effectiveness(strategy)
                strategy_scores[strategy] = strategy_scores.get(strategy, 0.0) + effectiveness

        if task_type in ("content_create", "story", "creative"):
            strategy_scores[CreativityStrategy.CONSTRAINT_DRIVEN_PROMPT] = strategy_scores.get(
                CreativityStrategy.CONSTRAINT_DRIVEN_PROMPT, 0.0
            ) + 1.5
        if task_type in ("code", "debug", "analyze"):
            strategy_scores[CreativityStrategy.SPECULATIVE_DECODE] = strategy_scores.get(
                CreativityStrategy.SPECULATIVE_DECODE, 0.0
            ) + 1.0

        sorted_strategies = sorted(strategy_scores.items(), key=lambda x: x[1], reverse=True)
        return [s for s, _ in sorted_strategies[:4]]

    def _compute_dimensions(self, constraints: list[ConstraintType], strategies: list[CreativityStrategy]) -> set[str]:
        dimensions: set[str] = {
            "latency", "throughput", "accuracy", "availability", "durability",
            "consistency", "partition_tolerance", "recovery_time", "error_rate",
            "cpu_constraint", "token_efficiency", "knowledge_coverage",
            "self_healing_depth", "prediction_accuracy", "formula_effectiveness",
        }

        if ConstraintType.VRAM_LIMIT in constraints:
            dimensions.add("vram_constraint")
        if ConstraintType.RAM_LIMIT in constraints:
            dimensions.add("ram_constraint")
        if CreativityStrategy.CONSTRAINT_DRIVEN_PROMPT in strategies:
            dimensions.add("creativity_depth")
        if CreativityStrategy.SPECULATIVE_DECODE in strategies:
            dimensions.add("quality_requirement")
        if CreativityStrategy.QUANTIZE_AND_COMPRESS in strategies:
            dimensions.add("constraint_amplification")

        return dimensions

    def _generate_transformations(self, constraints: list[ConstraintType], strategies: list[CreativityStrategy]) -> list[dict[str, Any]]:
        transformations: list[dict[str, Any]] = []

        for constraint in constraints:
            for strategy in _CONSTRAINT_STRATEGY_MAP.get(constraint, []):
                if strategy in strategies:
                    transformations.append({
                        "constraint": constraint.value,
                        "strategy": strategy.value,
                        "transformation": self._describe_transformation(constraint, strategy),
                    })

        return transformations

    def _describe_transformation(self, constraint: ConstraintType, strategy: CreativityStrategy) -> str:
        descriptions = {
            (ConstraintType.VRAM_LIMIT, CreativityStrategy.QUANTIZE_AND_COMPRESS): "4-bit quantization reduces VRAM by 75%, enabling larger models",
            (ConstraintType.VRAM_LIMIT, CreativityStrategy.OFFLOAD_AND_STREAM): "CPU offload for inactive layers, GPU for active computation",
            (ConstraintType.VRAM_LIMIT, CreativityStrategy.SPECULATIVE_DECODE): "Small model drafts, large model verifies — 2-3x speedup",
            (ConstraintType.VRAM_LIMIT, CreativityStrategy.KNOWLEDGE_SUBSTITUTE): "KB lookup replaces LLM generation for factual queries",
            (ConstraintType.RAM_LIMIT, CreativityStrategy.OFFLOAD_AND_STREAM): "Streaming generation avoids loading full model into RAM",
            (ConstraintType.RAM_LIMIT, CreativityStrategy.CHUNK_AND_PARALLEL): "Process input in chunks to reduce peak memory",
            (ConstraintType.TOKEN_LIMIT, CreativityStrategy.CONSTRAINT_DRIVEN_PROMPT): "Constraints force more creative, concise prompts",
            (ConstraintType.TOKEN_LIMIT, CreativityStrategy.KNOWLEDGE_SUBSTITUTE): "Pre-built KB answers for common queries, zero tokens",
        }
        return descriptions.get((constraint, strategy), f"{strategy.value} applied to {constraint.value}")

    def _generate_prompt_enhancements(self, constraints: list[ConstraintType], task_type: str) -> list[str]:
        enhancements: list[str] = []

        if ConstraintType.VRAM_LIMIT in constraints:
            enhancements.append("Use concise, high-density prompts to maximize per-token value")
            enhancements.append("Structure output requirements explicitly to reduce generation length")
        if ConstraintType.TOKEN_LIMIT in constraints:
            enhancements.append("Leverage KB context injection instead of long prompts")
            enhancements.append("Use few-shot examples from KB rather than lengthy instructions")
        if task_type in ("content_create", "story"):
            enhancements.append("Constraint-driven creativity: limits breed innovation")
            enhancements.append("Use structured templates to reduce free-form generation")

        return enhancements

    def _recommend_model(self, task_type: str) -> str:
        hw = self._hardware
        available_vram = hw.vram_available_gb

        if available_vram >= 20.0:
            return "qwen3.5:35b"
        if available_vram >= 6.0:
            if task_type in ("content_create", "complex_reasoning"):
                return "qwen3:8b"
            return "qwen3:4b"
        if available_vram >= 3.0:
            return "qwen3:4b"
        return "qwen3:4b"

    def _compute_creativity_boost(self, constraints: list[ConstraintType], strategies: list[CreativityStrategy]) -> float:
        base = 1.0
        constraint_boost = len(constraints) * 0.15
        strategy_boost = len(strategies) * 0.1
        return base + constraint_boost + strategy_boost

    def _estimate_quality(self, strategies: list[CreativityStrategy], task_type: str) -> float:
        base = 0.7
        for strategy in strategies:
            if strategy == CreativityStrategy.SPECULATIVE_DECODE:
                base += 0.1
            elif strategy == CreativityStrategy.KNOWLEDGE_SUBSTITUTE:
                base += 0.05
            elif strategy == CreativityStrategy.CONSTRAINT_DRIVEN_PROMPT:
                base += 0.08
            elif strategy == CreativityStrategy.QUANTIZE_AND_COMPRESS:
                base -= 0.02
        return min(1.0, base)

    def _estimate_vram_usage(self, model: str, strategies: list[CreativityStrategy]) -> float:
        base_vram = _MODEL_VRAM_MAP.get(model, 5.0)
        if CreativityStrategy.QUANTIZE_AND_COMPRESS in strategies:
            base_vram *= 0.4
        if CreativityStrategy.OFFLOAD_AND_STREAM in strategies:
            base_vram *= 0.6
        if CreativityStrategy.SPECULATIVE_DECODE in strategies:
            base_vram += 2.5
        return base_vram

    def _get_strategy_effectiveness(self, strategy: CreativityStrategy) -> float:
        history = self._strategy_effectiveness.get(strategy.value, [])
        if not history:
            return 1.0
        return sum(history[-10:]) / min(10, len(history))

    def _record_effectiveness(self, strategies: list[CreativityStrategy], quality: float) -> None:
        for strategy in strategies:
            if strategy.value not in self._strategy_effectiveness:
                self._strategy_effectiveness[strategy.value] = []
            self._strategy_effectiveness[strategy.value].append(quality)
            if len(self._strategy_effectiveness[strategy.value]) > 100:
                self._strategy_effectiveness[strategy.value] = self._strategy_effectiveness[strategy.value][-100:]
