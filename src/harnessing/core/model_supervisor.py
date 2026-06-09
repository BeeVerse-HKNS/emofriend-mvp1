from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .agentic_ai_capability_framework import AgenticAICapabilityFramework

logger = logging.getLogger(__name__)


@dataclass
class ModelCapabilityProfile:
    model_name: str
    model_size: str
    capabilities: list[str] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    vram_requirement: int = 0
    is_available: bool = False
    last_assessed: str = ""


_TASK_CAPABILITY_MAP: dict[str, list[str]] = {
    "reasoning": ["reasoning", "math", "complex_reasoning"],
    "chinese": ["chinese", "chinese_culture", "dialogue", "knowledge"],
    "code": ["code", "reasoning", "math"],
    "fast": ["fast_scan", "fast", "instruction"],
    "english": ["english", "reasoning", "code"],
}


class ModelSupervisor:
    def __init__(self, project_root: str = "d:\\My_Code_Projects\\Harnessing") -> None:
        self.project_root = project_root
        self._known_models: dict[str, ModelCapabilityProfile] = self._init_known_models()
        self._framework = AgenticAICapabilityFramework()
        self._available_cache: list[str] = []
        self._refresh_available()

    def _init_known_models(self) -> dict[str, ModelCapabilityProfile]:
        now = datetime.now().isoformat()
        return {
            "qwen3:8b": ModelCapabilityProfile(
                model_name="qwen3:8b",
                model_size="8b",
                capabilities=["reasoning", "chinese", "code"],
                strengths=["reasoning", "chinese", "code"],
                weaknesses=["multimodal", "long_context"],
                vram_requirement=6144,
                last_assessed=now,
            ),
            "qwen3:4b": ModelCapabilityProfile(
                model_name="qwen3:4b",
                model_size="4b",
                capabilities=["fast_scan", "chinese"],
                strengths=["fast_scan", "chinese"],
                weaknesses=["complex_reasoning", "long_context"],
                vram_requirement=3072,
                last_assessed=now,
            ),
            "deepseek-r1:8b": ModelCapabilityProfile(
                model_name="deepseek-r1:8b",
                model_size="8b",
                capabilities=["reasoning", "math", "code"],
                strengths=["reasoning", "math", "code"],
                weaknesses=["chinese_culture", "multimodal"],
                vram_requirement=6144,
                last_assessed=now,
            ),
            "glm4:9b": ModelCapabilityProfile(
                model_name="glm4:9b",
                model_size="9b",
                capabilities=["chinese", "dialogue", "knowledge"],
                strengths=["chinese", "dialogue", "knowledge"],
                weaknesses=["code", "reasoning"],
                vram_requirement=7168,
                last_assessed=now,
            ),
            "llama3.1:8b": ModelCapabilityProfile(
                model_name="llama3.1:8b",
                model_size="8b",
                capabilities=["english", "reasoning", "code"],
                strengths=["english", "reasoning", "code"],
                weaknesses=["chinese", "multimodal"],
                vram_requirement=6144,
                last_assessed=now,
            ),
            "mistral:7b": ModelCapabilityProfile(
                model_name="mistral:7b",
                model_size="7b",
                capabilities=["english", "fast", "code"],
                strengths=["english", "fast", "code"],
                weaknesses=["chinese", "long_context"],
                vram_requirement=5120,
                last_assessed=now,
            ),
            "phi4:14b": ModelCapabilityProfile(
                model_name="phi4:14b",
                model_size="14b",
                capabilities=["reasoning", "code", "math"],
                strengths=["reasoning", "code", "math"],
                weaknesses=["chinese", "multimodal"],
                vram_requirement=10240,
                last_assessed=now,
            ),
            "gemma3:4b": ModelCapabilityProfile(
                model_name="gemma3:4b",
                model_size="4b",
                capabilities=["fast", "english", "instruction"],
                strengths=["fast", "english", "instruction"],
                weaknesses=["chinese", "complex_reasoning"],
                vram_requirement=3072,
                last_assessed=now,
            ),
        }

    def _refresh_available(self) -> None:
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                self._available_cache = self._parse_ollama_list(result.stdout)
                for name in self._available_cache:
                    if name in self._known_models:
                        self._known_models[name].is_available = True
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            logger.warning("Ollama not available: %s", e)
            self._available_cache = []

    @staticmethod
    def _parse_ollama_list(output: str) -> list[str]:
        models: list[str] = []
        for line in output.strip().split("\n"):
            parts = line.split()
            if parts and parts[0] not in ("NAME", ""):
                models.append(parts[0])
        return models

    def assess_model(self, model_name: str) -> ModelCapabilityProfile:
        if model_name in self._known_models:
            profile = self._known_models[model_name]
        else:
            profile = ModelCapabilityProfile(
                model_name=model_name,
                model_size="unknown",
                capabilities=[],
                strengths=[],
                weaknesses=[],
                vram_requirement=0,
                last_assessed=datetime.now().isoformat(),
            )
            self._known_models[model_name] = profile

        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                available = self._parse_ollama_list(result.stdout)
                profile.is_available = model_name in available
        except (FileNotFoundError, subprocess.TimeoutExpired):
            profile.is_available = False

        profile.last_assessed = datetime.now().isoformat()
        return profile

    def get_model_profile(self, model_name: str) -> Optional[ModelCapabilityProfile]:
        return self._known_models.get(model_name)

    def get_best_model_for_task(self, task_type: str) -> str:
        required_caps = _TASK_CAPABILITY_MAP.get(task_type, [])
        if not required_caps:
            return "qwen3:8b"

        best_model = "qwen3:8b"
        best_score = -1

        for name, profile in self._known_models.items():
            if not profile.is_available:
                continue
            score = sum(1 for cap in required_caps if cap in profile.strengths)
            if score > best_score:
                best_score = score
                best_model = name

        if best_score == 0:
            for name, profile in self._known_models.items():
                if profile.is_available:
                    return name

        return best_model

    def get_capability_gaps(self, model_name: str) -> list[str]:
        profile = self._known_models.get(model_name)
        if profile is None:
            return []

        model_caps = set(profile.strengths + profile.capabilities)

        dimension_map: dict[str, list[str]] = {}
        for cap in self._framework.get_all_capabilities():
            dim = cap.dimension.value
            dimension_map.setdefault(dim, []).append(cap)

        gaps: list[str] = []
        for dim, caps in dimension_map.items():
            dim_keywords = {dim}
            for cap in caps:
                dim_keywords.add(cap.name)
                parts = cap.name.split("_")
                dim_keywords.update(parts)
            covered = bool(model_caps & dim_keywords)
            if not covered:
                missing_critical = [
                    cap.name for cap in caps
                    if cap.required_level.value == "critical"
                ]
                if missing_critical:
                    gaps.extend(missing_critical)
                else:
                    gaps.append(dim)

        weakness_gaps = [f"weakness:{w}" for w in profile.weaknesses]
        return gaps + weakness_gaps

    def list_available_models(self) -> list[ModelCapabilityProfile]:
        self._refresh_available()
        return [
            profile
            for profile in self._known_models.values()
            if profile.is_available
        ]

    def refresh_models(self) -> None:
        self._refresh_available()
        for name in list(self._known_models.keys()):
            self.assess_model(name)
