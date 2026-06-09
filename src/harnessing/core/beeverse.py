from __future__ import annotations

import json
import time
import urllib.request
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import structlog

from harnessing.core.beeverse_amplifier import BeeVerseAmplifier, HardwareProfile
from harnessing.core.beeverse_core import BeeVerseCore, CoreVerdict, TaskContext
from harnessing.core.beeverse_engine import BeeVerseEngine, OptimizationTarget, Severity

logger = structlog.get_logger()


class BeeVerseScenario(str, Enum):
    LOCAL_FAST = "local_fast"
    LOCAL_STANDARD = "local_standard"
    LOCAL_DEEP = "local_deep"
    LOCAL_SPECULATIVE = "local_speculative"
    KB_ONLY = "kb_only"
    FALLBACK = "fallback"


@dataclass
class BeeVerseRequest:
    prompt: str
    task_type: str = "general"
    max_tokens: int = 2048
    temperature: float = 0.7
    stream: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class BeeVerseResponse:
    request_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    content: str = ""
    scenario: BeeVerseScenario = BeeVerseScenario.LOCAL_STANDARD
    model_used: str = ""
    core_verdict: CoreVerdict = CoreVerdict.SAFE
    creativity_boost: float = 1.0
    strategies_applied: list[str] = field(default_factory=list)
    prompt_enhancements: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    token_count: int = 0
    vram_used_gb: float = 0.0
    quality_score: float = 0.0
    error: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


_OLLAMA_BASE = "http://localhost:11434"

_TASK_MODEL_MAP: dict[str, str] = {
    "classify": "qwen3:4b",
    "keyword_extract": "qwen3:4b",
    "code_scan": "qwen3:8b",
    "text_analyze": "qwen3:8b",
    "complex_reasoning": "qwen3:8b",
    "content_create": "qwen3:8b",
    "general": "qwen3:8b",
}

_TASK_OPTIMIZATION_MAP: dict[str, OptimizationTarget] = {
    "classify": OptimizationTarget.SPEED,
    "keyword_extract": OptimizationTarget.SPEED,
    "code_scan": OptimizationTarget.RELIABILITY,
    "text_analyze": OptimizationTarget.QUALITY,
    "complex_reasoning": OptimizationTarget.QUALITY,
    "content_create": OptimizationTarget.CREATIVITY,
    "general": OptimizationTarget.QUALITY,
}


class BeeVerse:
    def __init__(self, hardware: HardwareProfile | None = None) -> None:
        self._core = BeeVerseCore()
        self._engine = BeeVerseEngine()
        self._amplifier = BeeVerseAmplifier(hardware)
        self._hardware = hardware or HardwareProfile()
        self._ollama_available: bool | None = None
        self._request_history: list[BeeVerseResponse] = []

    def process(self, request: BeeVerseRequest) -> BeeVerseResponse:
        start_time = time.time()
        request_id = uuid.uuid4().hex[:12]

        context = TaskContext(
            task_id=request_id,
            task_type=request.task_type,
            prompt=request.prompt,
            model=_TASK_MODEL_MAP.get(request.task_type, "qwen3:8b"),
            vram_available=self._hardware.vram_available_gb,
            ram_available=self._hardware.ram_available_gb,
            metadata=request.metadata,
        )

        assessment = self._core.assess(context)

        if assessment.verdict == CoreVerdict.BLOCKED:
            return BeeVerseResponse(
                request_id=request_id,
                scenario=BeeVerseScenario.FALLBACK,
                core_verdict=assessment.verdict,
                error="circuit_breaker_active",
                duration_seconds=time.time() - start_time,
            )

        optimization_target = _TASK_OPTIMIZATION_MAP.get(request.task_type, OptimizationTarget.QUALITY)
        self._engine.record_performance("request_count", 1)

        amplification = self._amplifier.amplify(request.task_type, request.prompt)

        model = amplification.model_recommendation
        if assessment.verdict == CoreVerdict.RISKY and "force_cpu_offload" in assessment.healing_applied:
            model = "qwen3:4b"

        scenario = self._determine_scenario(request, assessment, amplification)

        enhanced_prompt = self._enhance_prompt(request.prompt, amplification.prompt_enhancements)

        response = self._call_ollama(
            model=model,
            prompt=enhanced_prompt,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            stream=request.stream or "streaming" in context.metadata,
        )

        if response is None:
            self._core.report_failure(request_id, "ollama_unavailable")
            fallback_response = self._kb_fallback(request.prompt)
            result = BeeVerseResponse(
                request_id=request_id,
                content=fallback_response,
                scenario=BeeVerseScenario.KB_ONLY,
                model_used="knowledge_base",
                core_verdict=assessment.verdict,
                creativity_boost=amplification.creativity_boost,
                strategies_applied=[s.value for s in amplification.strategies_applied] + ["kb_fallback"],
                duration_seconds=time.time() - start_time,
                quality_score=0.5,
            )
            self._request_history.append(result)
            return result

        self._core.report_success(request_id)
        self._engine.record_performance("quality_score", amplification.quality_score)

        result = BeeVerseResponse(
            request_id=request_id,
            content=response,
            scenario=scenario,
            model_used=model,
            core_verdict=assessment.verdict,
            creativity_boost=amplification.creativity_boost,
            strategies_applied=[s.value for s in amplification.strategies_applied],
            prompt_enhancements=amplification.prompt_enhancements,
            duration_seconds=time.time() - start_time,
            vram_used_gb=amplification.estimated_vram_usage_gb,
            quality_score=amplification.quality_score,
        )

        self._request_history.append(result)
        return result

    def check_ollama(self) -> bool:
        try:
            req = urllib.request.Request(f"{_OLLAMA_BASE}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                models = [m.get("name", "") for m in data.get("models", [])]
                self._ollama_available = True
                logger.info("ollama_check", available=True, models=models)
                return True
        except Exception:
            self._ollama_available = False
            logger.warning("ollama_check", available=False)
            return False

    def get_status(self) -> dict[str, Any]:
        return {
            "ollama_available": self._ollama_available,
            "hardware": {
                "vram_total_gb": self._hardware.vram_total_gb,
                "vram_available_gb": self._hardware.vram_available_gb,
                "ram_total_gb": self._hardware.ram_total_gb,
                "ram_available_gb": self._hardware.ram_available_gb,
                "gpu_name": self._hardware.gpu_name,
            },
            "total_requests": len(self._request_history),
            "formula": "log(S+P) + F² + (C^H)",
            "layers": {
                "core": "log(S+P) — SelfHealing + Prediction universalized",
                "engine": "F² — Formula self-improvement squared",
                "amplifier": "(C^H) — Creativity amplified by hardware constraints",
            },
        }

    def self_improve(self, max_iterations: int = 10) -> dict[str, Any]:
        cycle = self._engine.self_improve(max_iterations=max_iterations)
        return {
            "baseline_score": cycle.baseline_score,
            "final_score": cycle.current_score,
            "iterations": cycle.iterations,
            "improvement": cycle.current_score - cycle.baseline_score,
        }

    def _determine_scenario(self, request: BeeVerseRequest, assessment: Any, amplification: Any) -> BeeVerseScenario:
        if "kb_fallback" in [s.value for s in amplification.strategies_applied]:
            return BeeVerseScenario.KB_ONLY

        model = amplification.model_recommendation
        if model == "qwen3:4b":
            return BeeVerseScenario.LOCAL_FAST
        if model == "qwen3:8b":
            if request.task_type in ("content_create", "complex_reasoning"):
                return BeeVerseScenario.LOCAL_DEEP
            return BeeVerseScenario.LOCAL_STANDARD
        if "speculative_decode" in [s.value for s in amplification.strategies_applied]:
            return BeeVerseScenario.LOCAL_SPECULATIVE
        return BeeVerseScenario.LOCAL_STANDARD

    def _enhance_prompt(self, prompt: str, enhancements: list[str]) -> str:
        if not enhancements:
            return prompt
        enhancement_text = "\n".join(f"- {e}" for e in enhancements[:3])
        return f"{prompt}\n\n[Constraint-Driven Creativity Guidelines]\n{enhancement_text}"

    def _call_ollama(self, model: str, prompt: str, max_tokens: int = 2048, temperature: float = 0.7, stream: bool = False) -> str | None:
        try:
            payload = json.dumps({
                "model": model,
                "prompt": prompt,
                "stream": stream,
                "options": {
                    "num_predict": max_tokens,
                    "temperature": temperature,
                },
            }).encode()

            req = urllib.request.Request(
                f"{_OLLAMA_BASE}/api/generate",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=120) as resp:
                if stream:
                    full_response = ""
                    for line in resp:
                        chunk = json.loads(line.decode())
                        if chunk.get("response"):
                            full_response += chunk["response"]
                        if chunk.get("done"):
                            break
                    return full_response
                else:
                    data = json.loads(resp.read().decode())
                    return data.get("response", "")

        except Exception as e:
            logger.error("ollama_call_failed", model=model, error=str(e))
            return None

    def _kb_fallback(self, prompt: str) -> str:
        kb_dir = "docs/knowledge-base"
        try:
            import os
            if os.path.exists(kb_dir):
                index_path = os.path.join(kb_dir, "00-index.md")
                if os.path.exists(index_path):
                    with open(index_path, "r", encoding="utf-8") as f:
                        return f"[KB Fallback] Ollama unavailable. Knowledge base index:\n\n{f.read()[:2000]}"
        except Exception:
            pass
        return "[KB Fallback] Ollama unavailable and knowledge base not accessible. Please check Ollama service."
